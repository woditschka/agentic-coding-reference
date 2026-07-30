#!/usr/bin/env python3
"""claude_dev_config — read claude-dev.toml; emit the proxy policy and the
launcher's settings.

The config is DATA: parsed with ``tomllib``, never executed, and a file that
will not parse is refused by name rather than read as an absent policy.

**Scope tripwire.** This module emits *documents and values* — the squid
configuration and ``KEY=VALUE`` lines. It must never build or run a docker
command: argv construction stays in the launcher, where bash arrays handle
quoting (ADR 2026-07-06). Both public emitters are pure functions of parsed
input so the suite can pin them.

Usage:
    claude_dev_config.py settings <config.toml>
    claude_dev_config.py squid-conf <config.toml> --subnet CIDR
        [--mode allow-list|open] [--allow DOMAIN ...]
        [--ide-gateway HOST --ide-port N] [--label TEXT]
    claude_dev_config.py allowlist <config.toml> [--allow DOMAIN ...]
"""

from __future__ import annotations

import argparse
import ipaddress
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The proxy listens here. Single source: the launcher reads it back from
# `settings` rather than keeping a copy that could drift.
PROXY_PORT = 3128

# Destinations refused above the allow-list, in both modes. Loopback and the
# RFC1918 ranges are the host and the LAN; 169.254/16 carries cloud instance
# metadata; 100.64/10 is carrier NAT; 0.0.0.0/8 is "this network".
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
# The v6 list must NOT carry ::ffff:0:0/96: squid stores every IPv4 destination
# in exactly that mapped form, so the range matches ALL of them and denies every
# egress (measured 2026-07-29). Its case is already covered — squid normalizes
# `CONNECT [::ffff:169.254.169.254]` to the v4 form before the ACL runs. 6to4
# gets no such normalization, so 2002::/16 does the work the mapped range cannot.
PRIVATE_V6 = (
    "::/128",
    "::1/128",
    "64:ff9b::/96",
    "2002::/16",
    "fc00::/7",
    "fe80::/10",
)

MODES = ("allow-list", "open")

# Every table and key the file may carry. Anything else is refused by name: a
# typo or retired key would otherwise sit in the file looking like policy.
SCHEMA = {
    "mounts": ("rw", "ro"),
    "egress": ("mode", "allow"),
    "telemetry": ("enabled",),
}


class ConfigError(Exception):
    """A defect in the config file, phrased for the operator."""


@dataclass(frozen=True)
class Config:
    """One parsed claude-dev.toml. Paths are already $HOME-expanded."""

    rw: tuple[str, ...] = ()
    ro: tuple[str, ...] = ()
    mode: str = "allow-list"
    allow: tuple[str, ...] = ()
    # False declares Claude Code's optional telemetry off inside the session.
    # It is NOT an egress rule: turning it on opens nothing by itself, because
    # the intake hosts still have to clear the allow-list like any other name.
    telemetry: bool = False


def expand_home(entry: str, home: str) -> str:
    """The path a config entry denotes. $HOME is the one expansion there is —
    a config value is data, so it gets no shell, no globbing, no command
    substitution."""
    if entry == "$HOME" or entry.startswith("$HOME/"):
        return home + entry.removeprefix("$HOME")
    return entry


def _table(data: dict[str, object], name: str) -> dict[str, object]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    return value


def _check_schema(data: dict[str, object], where: str) -> None:
    """Refuse anything the file may not carry, naming it.

    Silently ignoring an unknown key is the one failure mode a config reader
    must not have: the operator writes a policy, the tool reads none.
    """
    for table, keys in sorted(data.items()):
        if table not in SCHEMA:
            # A scalar at file scope is the "forgot the [egress] header" typo,
            # not an unknown table — naming it a table sends the operator to
            # look for the wrong mistake.
            kind = f"table [{table}]" if isinstance(keys, dict) else f"key {table!r}"
            raise ConfigError(
                f"unknown {kind} at the top level of {where} — this version has "
                f"{', '.join('[' + t + ']' for t in sorted(SCHEMA))}"
            )
        if not isinstance(keys, dict):
            continue  # _table reports the type error with its own wording
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


def _bool(table: dict[str, object], key: str, default: bool, where: str) -> bool:
    """A boolean key. TOML has real booleans, so a quoted "true" is a mistake
    worth naming: it would otherwise read as a truthy string and silently mean
    the opposite of the file's plain sense."""
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{where}.{key} must be true or false (unquoted)")
    return value


def _str_list(table: dict[str, object], key: str, where: str) -> tuple[str, ...]:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{where}.{key} must be an array of strings")
    return tuple(str(v) for v in value)


_TOKEN_OK = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_:"
)


def validate_token(value: str, what: str) -> str:
    """A value interpolated raw into squid.conf. Letters, digits, `.-_:` only.

    A newline in an interpolated value forges a directive line ABOVE the
    denies — one injected `http_access allow all` defeats every rule under it.
    The launcher passes constants today; this makes that an invariant of the
    emitter rather than of its caller (ADR 2026-07-06).
    """
    if not value or any(c not in _TOKEN_OK for c in value):
        raise ConfigError(
            f"invalid {what}: {value!r} — letters, digits, dot, hyphen, "
            "underscore and colon only"
        )
    return value


def validate_domain(entry: str, where: str) -> str:
    """An allow-list entry names a host or a domain — never a URL, port or CIDR.

    A leading dot means "this domain and its subdomains"; without it the entry
    matches that host exactly. Anything else is refused by name at launch: a
    malformed entry squid silently ignores would read as allowed.
    """
    body = entry[1:] if entry.startswith(".") else entry
    if not body or body != body.strip():
        raise ConfigError(f"empty allow-list entry in {where}")
    if any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
        for c in body
    ):
        raise ConfigError(
            f"invalid allow-list entry in {where}: {entry!r} — letters, digits, "
            "dots and hyphens only; this is a domain list, not a URL, port or CIDR"
        )
    # One leading dot is the subdomain wildcard and was stripped above; any
    # further empty label ("..x.com", ".x.com." after the strip) is malformed.
    if ".." in body or body.startswith((".", "-")) or body.endswith((".", "-")):
        raise ConfigError(f"invalid allow-list entry in {where}: {entry!r}")
    try:
        ipaddress.ip_address(body)
    except ValueError:
        return entry
    # An IP literal in a dstdomain list never matches, so it would look allowed
    # and behave denied. Refuse it rather than ship that gap.
    raise ConfigError(
        f"invalid allow-list entry in {where}: {entry!r} — an address never "
        "matches a domain rule; name the host instead"
    )


def load(path: Path, home: str) -> Config:
    """Parse and validate one config file. Every defect names the file."""
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
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
        telemetry=_bool(telemetry, "enabled", False, "telemetry"),
    )


def shell_settings(cfg: Config) -> str:
    """The launcher's view: one KEY=VALUE per line, list values repeated.

    The launcher reads these with a read loop and never evals, so shell
    metacharacters stay inert text. Newlines are the record separator, so a
    value may not contain one.
    """
    lines = [
        f"EGRESS={cfg.mode}",
        f"PROXY_PORT={PROXY_PORT}",
        f"TELEMETRY={'1' if cfg.telemetry else '0'}",
    ]
    lines += [f"RW={p}" for p in cfg.rw]
    lines += [f"RO={p}" for p in cfg.ro]
    for line in lines:
        if "\n" in line:
            raise ConfigError(f"config value contains a newline: {line!r}")
    return "\n".join(lines) + "\n"


def emit_squid_conf(
    *,
    subnet: str,
    mode: str,
    allow: tuple[str, ...],
    ide_gateway: str | None = None,
    ide_port: int | None = None,
    label: str = "claude-dev",
) -> str:
    """The proxy's whole policy for one launch.

    http_access is first-match-wins, top to bottom, so THE ORDER IS THE POLICY:

      1. only the session's own subnet may ask;
      2. CONNECT only — HTTPS tunnels, no plaintext, nothing to cache;
      3. the one preflighted IDE port, ABOVE the private-range deny, because
         the host is reached at a private address by definition;
      4. every other private destination is refused — an allow-listed name
         that resolves or rebinds into the host or LAN does not connect;
      5. port 443 only, so an allowed name buys HTTPS and nothing else;
      6. the allow-list, or under "open" whatever is left;
      7. deny all.

    Reordering any of these changes what the session can reach, which is why
    this function is pinned by the suite rather than written inline in bash.
    """
    if mode not in MODES:
        raise ConfigError(f"unknown egress mode: {mode!r}")
    ipaddress.ip_network(subnet, strict=False)  # raises ValueError on junk
    if mode == "allow-list" and not allow:
        raise ConfigError(
            "the allow-list is empty — add at least api.anthropic.com, or "
            "launch with --open-egress"
        )
    if (ide_gateway is None) != (ide_port is None):
        raise ConfigError("the IDE bridge needs both a gateway and a port")
    validate_token(label, "proxy config label")
    if ide_gateway is not None:
        validate_token(ide_gateway, "IDE gateway")

    out = [
        f"# generated by claude-dev for {label} — regenerated every launch",
        f"http_port {PROXY_PORT}",
        # squid aborts at startup when it cannot derive an FQDN; naming it here
        # keeps a container with no resolvable hostname from failing to boot.
        "visible_hostname claude-dev-proxy",
        "pid_filename none",
        "coredump_dir /tmp",
        # The pinger opens raw ICMP sockets, which cap-drop=ALL denies — it
        # logged "FATAL: Unable to open any ICMP sockets" on every launch
        # (observed 2026-07-29). It only ranks cache peers, and there are none.
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
        f"acl session src {subnet}",
        "acl CONNECT method CONNECT",
        "acl SSL_ports port 443",
        "http_access deny !session",
        "http_access deny !CONNECT",
    ]
    if ide_gateway is not None and ide_port is not None:
        if not 0 < ide_port < 65536:
            raise ConfigError(f"IDE port out of range: {ide_port}")
        # dstdomain never matches an IP literal, so an address gateway needs a
        # dst rule. Getting this wrong closes the pinhole rather than widening
        # it, but it would look like a working bridge.
        try:
            ipaddress.ip_address(ide_gateway)
        except ValueError:
            out.append(f"acl ide_host dstdomain {ide_gateway}")
        else:
            out.append(f"acl ide_host dst {ide_gateway}")
        out.append(f"acl ide_port port {ide_port}")
        out.append("http_access allow session ide_host ide_port")
    out.append(f"acl to_private dst {' '.join(PRIVATE_V4)}")
    out.append(f"acl to_private6 dst {' '.join(PRIVATE_V6)}")
    out.append("http_access deny to_private")
    out.append("http_access deny to_private6")
    out.append("http_access deny CONNECT !SSL_ports")
    if mode == "allow-list":
        out.append('acl allowed dstdomain "/etc/claude-dev/allowlist.txt"')
        out.append("http_access allow session allowed")
    else:
        out.append("http_access allow session")
    out.append("http_access deny all")
    return "\n".join(out) + "\n"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="verb", required=True)

    settings = sub.add_parser("settings", help="KEY=VALUE lines for the launcher")
    settings.add_argument("config")

    conf = sub.add_parser("squid-conf", help="the proxy policy for one launch")
    conf.add_argument("config")
    conf.add_argument("--subnet", required=True)
    conf.add_argument("--mode", choices=MODES)
    conf.add_argument("--allow", action="append", default=[])
    conf.add_argument("--ide-gateway")
    conf.add_argument("--ide-port", type=int)
    conf.add_argument("--label", default="claude-dev")

    allowlist = sub.add_parser(
        "allowlist", help="the effective allow-list, one per line"
    )
    allowlist.add_argument("config")
    allowlist.add_argument("--allow", action="append", default=[])
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    home = str(Path.home())
    try:
        cfg = load(Path(args.config), home)
        if args.verb == "settings":
            sys.stdout.write(shell_settings(cfg))
            return 0
        # Per-run --allow entries are validated exactly like file entries and
        # apply to this launch only; the config file is never rewritten.
        extra = tuple(validate_domain(a, "--allow") for a in args.allow)
        if args.verb == "allowlist":
            sys.stdout.write("".join(f"{d}\n" for d in cfg.allow + extra))
            return 0
        sys.stdout.write(
            emit_squid_conf(
                subnet=args.subnet,
                mode=args.mode or cfg.mode,
                allow=cfg.allow + extra,
                ide_gateway=args.ide_gateway,
                ide_port=args.ide_port,
                label=args.label,
            )
        )
    except (ConfigError, ValueError) as exc:
        print(f"claude-dev: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
