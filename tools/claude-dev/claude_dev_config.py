#!/usr/bin/env python3
"""Read claude-dev.toml and emit the proxy policy and the launcher's settings.

The config is data: parsed with tomllib, never executed. This module emits
documents and values only; argv construction stays in the launcher.
"""

import argparse
import ipaddress
import json
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

# The launcher reads the port back from `settings` rather than keeping a copy.
PROXY_PORT = 3128
# The one port the forward listener tunnels to.
SSL_PORT = 443
# The proxy's second listener, --ow only: a reverse proxy with one fixed
# origin, the [open-weight] peer. The session sends it ordinary requests, so
# the proxy reads method and path instead of tunnelling bytes.
OW_PROXY_PORT = 3129
MAX_PORT = 65535
# What `peer` means by default: the host machine, reached through the engine's
# gateway name the launcher passes in.
OW_PEER_HOST = "host"
OW_DEFAULT_PORT = 11434
# The one request shape the reverse port admits: the Messages endpoint and its
# token-count sibling, with or without a query string. squid's urlpath_regex
# sees the query, and Claude Code posts to /v1/messages?beta=true. Not a
# setting: the client chooses the path, no peer needs another, and a wider
# shape would be the model-management API the port exists to refuse.
OW_PATH_REGEX = r"^/v1/messages(/count_tokens)?(\?.*)?$"
# API_TIMEOUT_MS for the session under --ow. One value: a local model answers
# in tens of seconds, and a ceiling nobody reaches costs nothing.
OW_TIMEOUT_MS = 1_800_000
# The session's bearer token under --ow. A placeholder: the peer ignores it
# and the real credential is never mounted, so nothing inside can leak it.
OW_PLACEHOLDER_TOKEN = "claude-dev"
# Display order of pinned names that share a target: the Claude family's
# capability tiers, top first; a name outside the family sorts after them.
OW_NAME_RANK = ("fable", "opus", "sonnet", "haiku")
# squid matches the path after percent-decoding; a decoded NUL ends the match
# early while the raw bytes reach the peer. No admitted path carries a
# percent sign, so the whole class is refused.
OW_ESCAPE_REGEX = "%"

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
    "open-weight": ("peer", "port", "model", "models"),
}

_TOKEN_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_:"
)
_DOMAIN_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
)


class ConfigError(Exception):
    """A defect in the config file, phrased for the operator."""


@dataclass(frozen=True, slots=True)
class OpenWeightConfig:
    """The [open-weight] table: one open-weight peer and the model map the session gets."""

    peer: str = OW_PEER_HOST
    port: int = OW_DEFAULT_PORT
    # Pinned model name -> the tag the peer serves; injected as modelOverrides.
    models: tuple[tuple[str, str], ...] = ()
    # The root session's model: one of the mapped names, the first by default.
    # The agents name their pins; the session itself runs whatever /model or
    # a settings file says, and an unmapped name reaches the peer as is.
    model: str = ""

    def __post_init__(self) -> None:
        """Default the root model to the first mapping."""
        if not self.model and self.models:
            object.__setattr__(self, "model", self.models[0][0])


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
    # None: no [open-weight] table, and --ow refuses to launch.
    open_weight: OpenWeightConfig | None = None


@dataclass(frozen=True, slots=True)
class OpenWeightPolicy:
    """The reverse port's inputs: the peer already resolved to a name or address."""

    gateway: str
    port: int


@dataclass(frozen=True, slots=True)
class ProxyPolicy:
    """The inputs of one launch's proxy configuration."""

    subnet: str
    mode: str
    allow: tuple[str, ...]
    ide_gateway: str | None = None
    ide_port: int | None = None
    open_weight: OpenWeightPolicy | None = None
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


def _int(
    table: dict[str, object], key: str, default: int | None, where: str
) -> int | None:
    # bool is an int subclass; `port = true` must not read as 1.
    value = table.get(key, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{where}.{key} must be an integer")
    return value


def validate_peer(value: str, where: str) -> str:
    """Refuse a peer that is not a host name or an IPv4 address."""
    # The peer lands in squid.conf raw and in a command line: a URL or a
    # host:port would read as another directive shape, `port` has its own key,
    # and a leading dash would read as an option. A colon also rules out an
    # IPv6 literal; the squid directives would need bracket forms for it.
    if value == OW_PEER_HOST:
        return value
    if (
        not value
        or value != value.strip()
        or value.startswith("-")
        or ":" in value
        or "/" in value
        or any(c not in _TOKEN_CHARS for c in value)
    ):
        raise ConfigError(
            f'invalid {where}.peer: {value!r} — "{OW_PEER_HOST}" (the host '
            "machine), a host name or an IPv4 address; the port is a separate key"
        )
    return value


def validate_model_token(value: object, what: str) -> str:
    """Refuse a model name or tag that is not one printable, option-safe token."""
    # Both sides reach the session as JSON, the launcher's output and a
    # command line: printable ASCII keeps a control byte off the terminal, no
    # whitespace keeps it one token, no leading dash keeps it an argument.
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("-")
        or any(c.isspace() or not (" " < c <= "~") for c in value)
    ):
        raise ConfigError(
            f"invalid {what}: {value!r} — one token of printable ASCII, no "
            "whitespace, no leading dash"
        )
    return value


def _open_weight(data: dict[str, object], where: str) -> OpenWeightConfig | None:
    """Read the [open-weight] table; absent means the reverse port does not exist."""
    # Read on every launch, flag or not: a table that will not validate is
    # refused by name rather than left looking like policy.
    if "open-weight" not in data:
        return None
    table = _table(data, "open-weight")
    peer = validate_peer(
        _str(table, "peer", OW_PEER_HOST, "open-weight"), "open-weight"
    )
    port = _int(table, "port", OW_DEFAULT_PORT, "open-weight")
    assert port is not None
    if not 0 < port <= MAX_PORT:
        raise ConfigError(f"open-weight.port out of range: {port}")
    if port == SSL_PORT:
        # The forward port tunnels CONNECT to 443 for any allowed public name,
        # so a peer there would also be reachable with its whole API.
        raise ConfigError(
            "open-weight.port 443 is also the forward port's tunnel port — serve the "
            "peer on another port"
        )
    raw_models = table.get("models", {})
    if not isinstance(raw_models, dict):
        raise ConfigError(
            "[open-weight.models] must be a table of pinned name = served tag"
        )
    models: list[tuple[str, str]] = []
    # File order: the first mapping is the root session's default model.
    for name, tag in raw_models.items():
        validate_model_token(name, "pinned model name in [open-weight.models]")
        models.append((name, validate_model_token(tag, f"open-weight.models.{name}")))
    if not models:
        # Without the map every dispatch names a pinned Anthropic model the
        # peer does not serve, and fails one request at a time.
        raise ConfigError(
            f"[open-weight.models] in {where} is empty — map each pinned model name to "
            "the tag the peer serves"
        )
    model = _str(table, "model", models[0][0], "open-weight")
    if model not in dict(models):
        raise ConfigError(
            f"open-weight.model {model!r} is not a key of [open-weight.models] — the root "
            "session's model must be a mapped name"
        )
    return OpenWeightConfig(peer=peer, port=port, models=tuple(models), model=model)


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
        open_weight=_open_weight(data, str(path)),
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
    # The token and the timeout reach the session through claude_settings
    # alone; the launcher only displays the peer and the map.
    if config.open_weight is not None:
        lines += [
            f"OW_PEER={config.open_weight.peer}",
            f"OW_PORT={config.open_weight.port}",
            f"OW_PROXY_PORT={OW_PROXY_PORT}",
            *(f"OW_TAG={tag}" for tag in served_tags(config.open_weight)),
            *(f"OW_TARGET={line}" for line in target_lines(config.open_weight)),
        ]
    for line in lines:
        if "\n" in line:
            raise ConfigError(f"config value contains a newline: {line!r}")
    return "\n".join(lines) + "\n"


def served_tags(open_weight: OpenWeightConfig) -> list[str]:
    """Name each distinct target once, in first-appearance order."""
    return list(dict.fromkeys(tag for _, tag in open_weight.models))


def _name_rank(name: str) -> tuple[int, str]:
    lowered = name.lower()
    for rank, family in enumerate(OW_NAME_RANK):
        if family in lowered:
            return rank, lowered
    return len(OW_NAME_RANK), lowered


def target_lines(open_weight: OpenWeightConfig) -> list[str]:
    """Render one line per target: the names that map to it, ranked, session marked."""
    lines = []
    for tag in served_tags(open_weight):
        names = sorted((n for n, t in open_weight.models if t == tag), key=_name_rank)
        shown = [f"{n} (session)" if n == open_weight.model else n for n in names]
        lines.append(f"{tag} <- {', '.join(shown)}")
    return lines


# Claude's in-process sandbox stays off: under Docker's default seccomp profile
# bubblewrap cannot create a user namespace (README § Process has the matrix),
# and turning it on would mean seccomp=unconfined for the whole container.
SANDBOX_OFF = {"sandbox": {"enabled": False, "failIfUnavailable": False}}


def claude_settings(config: Config, *, open_weight: bool) -> str:
    """Render the JSON the launcher passes as `--settings`, one document."""
    settings: dict[str, object] = dict(SANDBOX_OFF)
    if open_weight:
        if config.open_weight is None:
            raise ConfigError("--ow needs an [open-weight] table in the config")
        # The endpoint rides in the settings `env` block, not in the container
        # environment. A settings-file env block overrides the process
        # environment, and --settings sits above every project file. So a
        # project's own base URL cannot redirect the session past the proxy.
        settings["env"] = {
            "ANTHROPIC_BASE_URL": f"http://proxy:{OW_PROXY_PORT}",
            "ANTHROPIC_AUTH_TOKEN": OW_PLACEHOLDER_TOKEN,
            "API_TIMEOUT_MS": str(OW_TIMEOUT_MS),
        }
        # The map is a settings key, not an environment variable: the pinned
        # names in every agent's frontmatter are rewritten on the way out.
        settings["modelOverrides"] = dict(config.open_weight.models)
        # The root session follows the `model` key; without it the session
        # names a model the map does not cover.
        settings["model"] = config.open_weight.model
    return json.dumps(settings, separators=(",", ":"))


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


def _ow_listener(open_weight: OpenWeightPolicy) -> list[str]:
    """Render the reverse port: one fixed origin, reached only through the peer."""
    # The listener is named so its rules match on the port, not on the
    # destination: the session chooses nothing about where this port leads.
    # no-vhost: the request's Host header (proxy:3129) is ignored and the URL
    # is rebuilt from defaultsite, so the path is the only session-chosen part.
    return [
        f"http_port {OW_PROXY_PORT} accel defaultsite={open_weight.gateway} no-vhost name=ow",
        f"cache_peer {open_weight.gateway} parent {open_weight.port} 0 no-query originserver "
        "no-digest name=ow",
    ]


def _ow_rules() -> list[str]:
    """Render the rules that admit exactly the one request shape."""
    return [
        "acl ow_port myportname ow",
        f"acl ow_paths urlpath_regex {OW_PATH_REGEX}",
        f"acl ow_escaped urlpath_regex {OW_ESCAPE_REGEX}",
        "acl POST method POST",
        # squid resolves an ACL at the line that names it, so the peer routing
        # follows the definitions. The reverse port goes to the peer and
        # nowhere else; the peer serves the reverse port alone.
        "never_direct allow ow_port",
        "cache_peer_access ow allow ow_port",
        "cache_peer_access ow deny all",
        "http_access deny ow_port ow_escaped",
        "http_access allow session ow_port POST ow_paths",
        # Everything else on the reverse port: model management (/api/pull,
        # /api/delete, /api/push), listings, other methods.
        "http_access deny ow_port",
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
    if policy.open_weight is not None:
        validate_token(policy.open_weight.gateway, "open-weight peer")
        if policy.open_weight.gateway == OW_PEER_HOST:
            raise ConfigError("the open-weight peer must be resolved to a gateway name")
        if not 0 < policy.open_weight.port <= MAX_PORT:
            raise ConfigError(
                f"open-weight port out of range: {policy.open_weight.port}"
            )


def emit_squid_conf(policy: ProxyPolicy) -> str:
    """Render the proxy's whole policy for one launch."""
    # http_access is first-match-wins, so the order is the policy. Only the
    # session's subnet may ask. The reverse port admits its one request shape
    # and then nothing else, so no later rule can see that port. CONNECT only.
    # The one IDE port sits above the private-range deny, since the host is at
    # a private address. Every other private destination is refused, so a name
    # resolving or rebinding into the host or LAN does not connect. Port 443
    # only. The allow-list, or under "open" whatever is left. Deny all.
    _validate_policy(policy)
    lines = [
        f"# generated by claude-dev for {policy.label} — regenerated every launch",
        f"http_port {PROXY_PORT}",
        *(_ow_listener(policy.open_weight) if policy.open_weight is not None else []),
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
        f"acl SSL_ports port {SSL_PORT}",
        "http_access deny !session",
    ]
    if policy.open_weight is not None:
        lines.extend(_ow_rules())
    lines.append("http_access deny !CONNECT")
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
    # --ow opens the reverse port to the [open-weight] peer; --host-gateway is what
    # a peer of "host" resolves to (the engine's name for the host machine).
    conf.add_argument("--ow", action="store_true")
    conf.add_argument("--host-gateway")
    conf.add_argument("--label", default="claude-dev")
    allowlist = verbs.add_parser(
        "allowlist", help="the effective allow-list, one per line"
    )
    allowlist.add_argument("config")
    allowlist.add_argument("--allow", action="append", default=[])
    claude = verbs.add_parser("claude-settings", help="the JSON for claude --settings")
    claude.add_argument("config")
    claude.add_argument("--ow", action="store_true")
    return parser.parse_args(argv)


def open_weight_policy(config: Config, host_gateway: str | None) -> OpenWeightPolicy:
    """Resolve the [open-weight] table into the reverse port's inputs."""
    if config.open_weight is None:
        raise ConfigError("--ow needs an [open-weight] table in the config")
    gateway = config.open_weight.peer
    if gateway == OW_PEER_HOST:
        if not host_gateway:
            raise ConfigError(
                'an [open-weight] peer of "host" needs the engine\'s host gateway'
            )
        gateway = host_gateway
    return OpenWeightPolicy(gateway=gateway, port=config.open_weight.port)


def _render(args: argparse.Namespace, config: Config) -> str:
    """Render the document one verb asks for."""
    if args.verb == "settings":
        return shell_settings(config)
    if args.verb == "claude-settings":
        return claude_settings(config, open_weight=args.ow)
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
            open_weight=open_weight_policy(config, args.host_gateway)
            if args.ow
            else None,
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
