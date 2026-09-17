#!/usr/bin/env python3
"""Read claude-dev.toml and emit the proxy policy and the launcher's settings.

The config is data: parsed with tomllib, never executed. This module emits
documents and values only; argv construction stays in the launcher.
"""

import argparse
import ipaddress
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The launcher reads the port back from `settings` rather than keeping a copy.
PROXY_PORT = 3128
MAX_PORT = 65535

# Destinations refused above the allow-list in both modes: the host, the LAN,
# cloud instance metadata, carrier NAT, and "this network".
PRIVATE_V4 = (
    "0.0.0.0/8",
    "10.0.0.0/8",
    "100.64.0.0/10",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.0.0.0/24",
    "192.88.99.0/24",
    "192.168.0.0/16",
    "198.18.0.0/15",
)
# ::ffff:0:0/96 is absent on purpose: squid stores every IPv4 destination in
# that mapped form, so the range would deny all egress, and it normalizes a
# mapped CONNECT to the v4 form before the ACL runs. 6to4 gets no such
# normalization, so 2002::/16 does the work the mapped range cannot.
PRIVATE_V6 = (
    "::/128",
    "::1/128",
    "64:ff9b::/96",
    "2002::/16",
    "fc00::/7",
    "fe80::/10",
)

MODES = ("allow-list", "open")

# Every table and key the file may carry; anything else is refused by name.
SCHEMA = {
    "mounts": ("rw", "ro"),
    "egress": ("mode", "allow"),
    "telemetry": ("enabled",),
}

_TOKEN_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_:"
)
_DOMAIN_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
)


class ConfigError(Exception):
    """A defect in the config file, phrased for the operator."""


@dataclass(frozen=True)
class Config:
    """One parsed claude-dev.toml with its paths already $HOME-expanded."""

    rw: tuple[str, ...] = ()
    ro: tuple[str, ...] = ()
    mode: str = "allow-list"
    allow: tuple[str, ...] = ()
    # Telemetry off is a declaration inside the session, not an egress rule:
    # the intake hosts still have to clear the allow-list.
    telemetry: bool = False


@dataclass(frozen=True, slots=True)
class ProxyPolicy:
    """The inputs of one launch's proxy configuration."""

    subnet: str
    mode: str
    allow: tuple[str, ...]
    ide_gateway: str | None = None
    ide_port: int | None = None
    label: str = "claude-dev"


def expand_home(entry: str, home: str) -> str:
    """Expand a leading $HOME, the one expansion a config path gets."""
    if entry == "$HOME" or entry.startswith("$HOME/"):
        return home + entry.removeprefix("$HOME")
    return entry


def _table(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    return value


def _check_schema(data: dict[str, object], where: str) -> None:
    """Refuse anything the file may not carry, naming it."""
    for table, keys in sorted(data.items()):
        if table not in SCHEMA:
            # A scalar at file scope is the forgotten-header typo, not an
            # unknown table; naming it a table would misdirect the operator.
            kind = f"table [{table}]" if isinstance(keys, dict) else f"key {table!r}"
            raise ConfigError(
                f"unknown {kind} at the top level of {where} — this version has "
                f"{', '.join('[' + t + ']' for t in sorted(SCHEMA))}"
            )
        if not isinstance(keys, dict):
            continue
        for key in sorted(keys):
            if key not in SCHEMA[table]:
                raise ConfigError(
                    f"unknown key {table}.{key} in {where} — [{table}] takes "
                    f"{', '.join(SCHEMA[table])}"
                )


def _str(table: dict[str, object], key: str, default: str, where: str) -> str:
    value = table.get(key, default)
    if not isinstance(value, str):
        raise ConfigError(f"{where}.{key} must be a string")
    return value


def _bool(table: dict[str, object], key: str, where: str, *, default: bool) -> bool:
    # A quoted "true" would read as a truthy string and silently mean the
    # opposite of the file's plain sense.
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{where}.{key} must be true or false (unquoted)")
    return value


def _str_list(table: dict[str, object], key: str, where: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}.{key} must be an array of strings")
    return tuple(str(v) for v in value)


def validate_token(value: str, what: str) -> str:
    """Refuse a value interpolated raw into squid.conf unless it is a plain token."""
    # A newline in an interpolated value forges a directive line above the
    # denies, so the invariant belongs to the emitter, not its caller.
    if not value or any(c not in _TOKEN_CHARS for c in value):
        raise ConfigError(
            f"invalid {what}: {value!r} — letters, digits, dot, hyphen, "
            "underscore and colon only"
        )
    return value


def validate_domain(entry: str, where: str) -> str:
    """Refuse an allow-list entry that is not a host or a dot-prefixed domain."""
    # A malformed entry squid silently ignores would read as allowed.
    body = entry.removeprefix(".")
    if not body or body != body.strip():
        raise ConfigError(f"empty allow-list entry in {where}")
    if any(c not in _DOMAIN_CHARS for c in body):
        raise ConfigError(
            f"invalid allow-list entry in {where}: {entry!r} — letters, digits, "
            "dots and hyphens only; this is a domain list, not a URL, port or CIDR"
        )
    if ".." in body or body.startswith((".", "-")) or body.endswith((".", "-")):
        raise ConfigError(f"invalid allow-list entry in {where}: {entry!r}")
    try:
        ipaddress.ip_address(body)
    except ValueError:
        return entry
    # An IP literal in a dstdomain list never matches, so it would look
    # allowed and behave denied.
    raise ConfigError(
        f"invalid allow-list entry in {where}: {entry!r} — an address never "
        "matches a domain rule; name the host instead"
    )


def load(path: Path, home: str) -> Config:
    """Parse and validate one config file, naming the file in every defect."""
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path} is not valid TOML: {exc}") from exc
    _check_schema(data, str(path))
    mounts = _table(data, "mounts")
    egress = _table(data, "egress")
    telemetry = _table(data, "telemetry")
    mode = _str(egress, "mode", "allow-list", "egress")
    if mode not in MODES:
        raise ConfigError(
            f"egress.mode must be one of {', '.join(MODES)} (got {mode!r})"
        )
    allow = tuple(
        validate_domain(entry, str(path))
        for entry in _str_list(egress, "allow", "egress")
    )
    return Config(
        rw=tuple(expand_home(p, home) for p in _str_list(mounts, "rw", "mounts")),
        ro=tuple(expand_home(p, home) for p in _str_list(mounts, "ro", "mounts")),
        mode=mode,
        allow=allow,
        telemetry=_bool(telemetry, "enabled", "telemetry", default=False),
    )


def shell_settings(config: Config) -> str:
    """Render the launcher's view: one KEY=VALUE per line, list values repeated."""
    # The launcher reads these in a loop and never evals; newlines are the
    # record separator, so a value may not contain one.
    lines = [
        f"EGRESS={config.mode}",
        f"PROXY_PORT={PROXY_PORT}",
        f"TELEMETRY={'1' if config.telemetry else '0'}",
        *(f"RW={path}" for path in config.rw),
        *(f"RO={path}" for path in config.ro),
    ]
    for line in lines:
        if "\n" in line:
            raise ConfigError(f"config value contains a newline: {line!r}")
    return "\n".join(lines) + "\n"


def _ide_pinhole(gateway: str, port: int) -> list[str]:
    """Render the rules that admit the one preflighted IDE port."""
    if not 0 < port <= MAX_PORT:
        raise ConfigError(f"IDE port out of range: {port}")
    # dstdomain never matches an IP literal, so an address gateway needs a
    # dst rule; getting this wrong closes the pinhole while looking bridged.
    try:
        ipaddress.ip_address(gateway)
    except ValueError:
        host_rule = f"acl ide_host dstdomain {gateway}"
    else:
        host_rule = f"acl ide_host dst {gateway}"
    return [
        host_rule,
        f"acl ide_port port {port}",
        "http_access allow session ide_host ide_port",
    ]


def _validate_policy(policy: ProxyPolicy) -> None:
    """Refuse a policy squid would misread."""
    if policy.mode not in MODES:
        raise ConfigError(f"unknown egress mode: {policy.mode!r}")
    ipaddress.ip_network(policy.subnet, strict=False)
    if policy.mode == "allow-list" and not policy.allow:
        raise ConfigError(
            "the allow-list is empty — add at least api.anthropic.com, or "
            "launch with --open-egress"
        )
    if (policy.ide_gateway is None) != (policy.ide_port is None):
        raise ConfigError("the IDE bridge needs both a gateway and a port")
    validate_token(policy.label, "proxy config label")
    if policy.ide_gateway is not None:
        validate_token(policy.ide_gateway, "IDE gateway")


def emit_squid_conf(policy: ProxyPolicy) -> str:
    """Render the proxy's whole policy for one launch."""
    # http_access is first-match-wins, so the order is the policy: only the
    # session's subnet may ask; CONNECT only; the one IDE port above the
    # private-range deny, since the host sits at a private address; every
    # other private destination refused, so a name resolving or rebinding
    # into the host or LAN does not connect; port 443 only; the allow-list,
    # or under "open" whatever is left; deny all.
    _validate_policy(policy)
    lines = [
        f"# generated by claude-dev for {policy.label} — regenerated every launch",
        f"http_port {PROXY_PORT}",
        # squid aborts at startup when it cannot derive an FQDN.
        "visible_hostname claude-dev-proxy",
        "pid_filename none",
        "coredump_dir /tmp",
        # The pinger opens raw ICMP sockets, which cap-drop=ALL denies; it
        # only ranks cache peers, and there are none.
        "pinger_enable off",
        "cache deny all",
        "cache_mem 8 MB",
        "access_log stdio:/dev/stdout squid",
        "cache_log stdio:/dev/stderr",
        "cache_store_log none",
        "logfile_rotate 0",
        "httpd_suppress_version_string on",
        "via off",
        "forwarded_for delete",
        "shutdown_lifetime 1 second",
        "",
        f"acl session src {policy.subnet}",
        "acl CONNECT method CONNECT",
        "acl SSL_ports port 443",
        "http_access deny !session",
        "http_access deny !CONNECT",
    ]
    if policy.ide_gateway is not None and policy.ide_port is not None:
        lines.extend(_ide_pinhole(policy.ide_gateway, policy.ide_port))
    lines.extend(
        [
            f"acl to_private dst {' '.join(PRIVATE_V4)}",
            f"acl to_private6 dst {' '.join(PRIVATE_V6)}",
            "http_access deny to_private",
            "http_access deny to_private6",
            "http_access deny CONNECT !SSL_ports",
        ]
    )
    if policy.mode == "allow-list":
        lines.append('acl allowed dstdomain "/etc/claude-dev/allowlist.txt"')
        lines.append("http_access allow session allowed")
    else:
        lines.append("http_access allow session")
    lines.append("http_access deny all")
    return "\n".join(lines) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    verbs = parser.add_subparsers(dest="verb", required=True)
    settings = verbs.add_parser("settings", help="KEY=VALUE lines for the launcher")
    settings.add_argument("config")
    conf = verbs.add_parser("squid-conf", help="the proxy policy for one launch")
    conf.add_argument("config")
    conf.add_argument("--subnet", required=True)
    conf.add_argument("--mode", choices=MODES)
    conf.add_argument("--allow", action="append", default=[])
    conf.add_argument("--ide-gateway")
    conf.add_argument("--ide-port", type=int)
    conf.add_argument("--label", default="claude-dev")
    allowlist = verbs.add_parser(
        "allowlist", help="the effective allow-list, one per line"
    )
    allowlist.add_argument("config")
    allowlist.add_argument("--allow", action="append", default=[])
    return parser.parse_args(argv)


def _render(args: argparse.Namespace, config: Config) -> str:
    """Render the document one verb asks for."""
    if args.verb == "settings":
        return shell_settings(config)
    # Per-run --allow entries apply to this launch only; the file is never
    # rewritten.
    extra = tuple(validate_domain(entry, "--allow") for entry in args.allow)
    if args.verb == "allowlist":
        return "".join(f"{domain}\n" for domain in config.allow + extra)
    return emit_squid_conf(
        ProxyPolicy(
            subnet=args.subnet,
            mode=args.mode or config.mode,
            allow=config.allow + extra,
            ide_gateway=args.ide_gateway,
            ide_port=args.ide_port,
            label=args.label,
        )
    )


def main(argv: list[str] | None = None) -> int:
    """Run one verb and write its document to stdout."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        config = load(Path(args.config), str(Path.home()))
        sys.stdout.write(_render(args, config))
    except (ConfigError, ValueError) as exc:
        print(f"claude-dev: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
