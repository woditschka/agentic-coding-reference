#!/usr/bin/env python3
"""The per-tool facts of the agent-dev engine: one Profile for each supported agent tool.

A profile is shipped code, never operator policy: the engine knows none of it, and the launcher reads it through the `profile` verb.
"""

import json
from dataclasses import dataclass
from typing import Literal, Protocol

from agent_dev_config import OW_PROXY_PORT, OW_TIMEOUT_MS, Config, ConfigError


class SessionSettings(Protocol):
    """Render the settings document a session receives, for or without --ow."""

    def __call__(self, config: Config, *, open_weight: bool) -> str:
        """Return the document as one string."""


@dataclass(frozen=True, slots=True)
class Overlay:
    """A private writable directory beneath a read-only share."""

    under: str
    sub: str
    # The shadow directory that backs it, beside the root's other shadow paths.
    shadow: str
    # How `access` describes it.
    note: str


# How long a root's private shadow lives. "project" is one per project path,
# and a separate one under --ow. "run" is created fresh for the launch and
# discarded on exit. No shadow outlives its project: a tool loads code or
# config from its roots, and one shared across projects would carry one
# hostile project's plant into every later session.
Lifetime = Literal["project", "run"]


@dataclass(frozen=True, slots=True)
class StateRoot:
    """One home-relative directory the session sees as a private shadow plus named shares."""

    path: str
    # The shadow's name under the data dir's state/ directory.
    shadow: str
    lifetime: Lifetime
    share_rw_dirs: tuple[str, ...] = ()
    share_rw_files: tuple[str, ...] = ()
    share_ro: tuple[str, ...] = ()
    # A directory under the root holding one subdirectory per project, keyed by
    # the workdir. Shared read-write for this project's key only.
    project_dir: str = ""
    overlays: tuple[Overlay, ...] = ()


@dataclass(frozen=True, slots=True)
class Profile:
    """Everything the engine needs to know about one agent tool."""

    name: str
    command: str
    binary: str
    # The Dockerfile stage this tool's image is built from.
    image_target: str
    # The build argument that pins the tool's version, the one that busts the
    # tool layer's cache on update, and the env var that sets the version.
    build_arg: str
    cache_bust_arg: str
    version_env: str
    roots: tuple[StateRoot, ...]
    # Home-relative paths that decide how the tool runs on the host. Every
    # tool's session refuses each of them as a writable mount, as a path
    # containing one, and as the project directory; read-only they are shareable.
    protected: tuple[str, ...]
    # The tool's own config file in the home directory, replicated per launch
    # and scrubbed to the project; empty when the tool keeps none.
    replica: str
    replica_scrubber: str
    # The env var that relocates the credential store, and the unmounted path
    # that stands in for it under --ow. Empty when the tool keeps its
    # credential inside one of its own state roots.
    credential_env: str
    credential_ow_path: str
    credential_file: str
    # What a first run prints. With a relocated store, "first" means the store
    # holds no credential file; otherwise it means a project-lifetime shadow
    # is still empty.
    login_hint: str
    # The env declaration that turns the tool's telemetry off; empty when the
    # tool has none to declare.
    telemetry_off: str
    # The proxy env variables the session receives, each set to the proxy URL.
    # A tool that reads HTTP_PROXY would route its plain-HTTP model call to the
    # forward port, which refuses plaintext, so such a tool names HTTPS only.
    proxy_env: tuple[str, ...]
    # A shell snippet run inside the session before the tool starts, with the
    # tool's argv as "$@": it ends by exec-ing "$@" itself. Empty for none.
    prepare: str
    # Permission flags the launcher injects unless the operator passes an
    # argument matching one of the override patterns (shell globs); empty means
    # the tool has no such posture to inject.
    permission_default: tuple[str, ...]
    permission_overrides: tuple[str, ...]
    # How the settings document reaches the session: an argv flag or an env var.
    settings_flag: str
    settings_env: str
    # The one host the session cannot work without when it reaches the vendor
    # API; empty when the provider is the operator's choice.
    mandatory_host: str
    # The one request shape the --ow reverse port admits, and how to name it.
    inference_path_regex: str
    inference_allow: str
    inference_short: str
    credential_vendor: str
    # Whether the JetBrains IDE bridge is offered.
    ide: bool
    session_settings: SessionSettings


# The capability tiers of the Claude family, top first. Every tool's agents
# pin names of this family, so the tiers order the names that share a target
# and pick the small model.
PIN_FAMILY_RANK = ("fable", "opus", "sonnet", "haiku")
# The query string an admitted request may carry: plain key=value characters.
# squid's urlpath_regex sees the query, and Claude Code posts to
# /v1/messages?beta=true. A slash, a dot or a percent sign would let the query
# spell a second path past the anchors, whether or not squid decodes first.
PLAIN_QUERY = r"(\?[A-Za-z0-9_=&-]*)?"


def name_rank(name: str) -> tuple[int, str]:
    """Rank a pinned name by its Claude family tier, top first; other names sort after."""
    lowered = name.lower()
    for rank, family in enumerate(PIN_FAMILY_RANK):
        if family in lowered:
            return rank, lowered
    return len(PIN_FAMILY_RANK), lowered


# Claude's in-process sandbox stays off: under Docker's default seccomp profile
# bubblewrap cannot create a user namespace, and turning it on would mean
# seccomp=unconfined for the whole container.
SANDBOX_OFF = {"sandbox": {"enabled": False, "failIfUnavailable": False}}
# The session's bearer token under --ow. A placeholder: the peer ignores it
# and the real credential is never mounted, so nothing inside can leak it.
CLAUDE_PLACEHOLDER_TOKEN = "claude-dev"
# The Messages endpoint and its token-count sibling.
CLAUDE_INFERENCE_PATH = rf"^/v1/messages(/count_tokens)?{PLAIN_QUERY}$"


def claude_session_settings(config: Config, *, open_weight: bool) -> str:
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
            "ANTHROPIC_AUTH_TOKEN": CLAUDE_PLACEHOLDER_TOKEN,
            "API_TIMEOUT_MS": str(OW_TIMEOUT_MS),
        }
        # The map is a settings key, not an environment variable: the pinned
        # names in every agent's frontmatter are rewritten on the way out.
        settings["modelOverrides"] = dict(config.open_weight.models)
        # The root session follows the `model` key; without it the session
        # names a model the map does not cover.
        settings["model"] = config.open_weight.model
    return json.dumps(settings, separators=(",", ":"))


# The OpenCode agents pin models as openrouter/anthropic/<name>, so the --ow
# map overrides that one provider and keeps the pins unchanged. The endpoint is
# OpenAI-compatible, the one chat path the reverse port admits.
OPENCODE_PROVIDER = "openrouter"
OPENCODE_MODEL_PREFIX = "anthropic/"
OPENCODE_INFERENCE_PATH = rf"^/v1/chat/completions{PLAIN_QUERY}$"
# The provider's apiKey under --ow: a placeholder the peer ignores.
OPENCODE_PLACEHOLDER_KEY = "opencode-dev"
# Runs inside the session before opencode starts. The image carries the plugin
# SDK that opencode would otherwise fetch from the npm registry at startup. The
# config shadow is created fresh for each launch, so the seed is copied every
# time and nothing a session writes there outlives it.
OPENCODE_PREPARE = (
    'd="$HOME/.config/opencode"; mkdir -p "$d"; '
    'cp -R /opt/opencode-seed/. "$d/"; exec "$@"'
)


def opencode_session_settings(config: Config, *, open_weight: bool) -> str:
    """Render the JSON the launcher passes as OPENCODE_CONFIG_CONTENT, one document."""
    # The inline config outranks the project's, so a project's own provider
    # entry cannot redirect the session past the proxy. Sharing is disabled
    # because a shared session uploads its transcript, and auto-update because
    # the session has no route to the release channel.
    settings: dict[str, object] = {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "share": "disabled",
    }
    if open_weight:
        if config.open_weight is None:
            raise ConfigError("--ow needs an [open-weight] table in the config")
        names = [name for name, _ in config.open_weight.models]
        # Title generation uses the small model; unpinned it names a model the
        # map does not cover and the request reaches the peer unmapped. The
        # lowest tier among the mapped names serves it.
        ranked = [n for n in names if name_rank(n)[0] < len(PIN_FAMILY_RANK)]
        small = max(ranked, key=name_rank) if ranked else config.open_weight.model
        settings["provider"] = {
            OPENCODE_PROVIDER: {
                "npm": "@ai-sdk/openai-compatible",
                "options": {
                    "baseURL": f"http://proxy:{OW_PROXY_PORT}/v1",
                    "apiKey": OPENCODE_PLACEHOLDER_KEY,
                    "timeout": OW_TIMEOUT_MS,
                },
                "models": {
                    f"{OPENCODE_MODEL_PREFIX}{name}": {"id": tag}
                    for name, tag in config.open_weight.models
                },
            }
        }
        prefix = f"{OPENCODE_PROVIDER}/{OPENCODE_MODEL_PREFIX}"
        settings["model"] = f"{prefix}{config.open_weight.model}"
        settings["small_model"] = f"{prefix}{small}"
    return json.dumps(settings, separators=(",", ":"))


CLAUDE = Profile(
    name="claude",
    command="claude-dev",
    binary="claude",
    image_target="claude",
    build_arg="CLAUDE_VERSION",
    cache_bust_arg="CLAUDE_CACHE_BUST",
    version_env="CLAUDE_DEV_CLAUDE_VERSION",
    roots=(
        # Claude Code loads rules, settings and per-project memory from this
        # root, so the shadow is per project and separate under --ow: a file
        # one project writes there never reaches another project's session.
        StateRoot(
            path=".claude",
            shadow="claude-state",
            lifetime="project",
            # Session state shares read-write, behavior config read-only;
            # anything not named stays private, so the failure direction is
            # state loss, never exposure.
            share_rw_dirs=("paste-cache", "plans", "tasks", "todos"),
            share_rw_files=("history.jsonl",),
            share_ro=(
                "CLAUDE.md",
                "agents",
                "commands",
                "hooks",
                "output-styles",
                "plugins",
                "rules",
                "settings.json",
                "settings.local.json",
                "skills",
                "workflows",
            ),
            project_dir="projects",
            # Claude Code creates plugins/data/<plugin> before executing a
            # plugin hook; under the read-only plugins share that mkdir fails.
            overlays=(
                Overlay(
                    under="plugins",
                    sub="data",
                    shadow="plugins-data",
                    note="private plugin state (persists across runs)",
                ),
            ),
        ),
    ),
    protected=(".claude", ".claude.json"),
    replica=".claude.json",
    replica_scrubber="claude_dev_scrub.py",
    credential_env="CLAUDE_SECURESTORAGE_CONFIG_DIR",
    credential_ow_path=".config/claude-dev-ow-auth",
    credential_file=".credentials.json",
    login_hint="type '/login' once inside",
    telemetry_off="DISABLE_TELEMETRY=1",
    proxy_env=("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"),
    prepare="",
    permission_default=("--permission-mode", "auto"),
    permission_overrides=(
        "--permission-mode",
        "--permission-mode=*",
        "--dangerously-skip-permissions",
    ),
    settings_flag="--settings",
    settings_env="",
    mandatory_host="api.anthropic.com",
    inference_path_regex=CLAUDE_INFERENCE_PATH,
    inference_allow="POST /v1/messages (and /count_tokens), plain query string only",
    inference_short="POST /v1/messages",
    credential_vendor="Anthropic",
    ide=True,
    session_settings=claude_session_settings,
)

OPENCODE = Profile(
    name="opencode",
    command="opencode-dev",
    binary="opencode",
    image_target="opencode",
    build_arg="OPENCODE_VERSION",
    cache_bust_arg="OPENCODE_CACHE_BUST",
    version_env="OPENCODE_DEV_OPENCODE_VERSION",
    roots=(
        # OpenCode loads plugins, agents, commands and MCP servers from its
        # config directory and runs provider SDKs from its cache. Those roots
        # are per-run, so a plant in one launch cannot reach another. Host
        # config the session may read shares read-only; the plugin SDK seeds
        # from the image.
        StateRoot(
            path=".config/opencode",
            shadow="opencode-config",
            lifetime="run",
            share_ro=(
                "AGENTS.md",
                "agents",
                "commands",
                "opencode.json",
                "plugins",
                "skills",
                "tui.json",
            ),
        ),
        # Sessions, the database and the stored credential persist per project,
        # and separately under --ow, so a session on a peer starts apart from
        # the project's stored login and one project's state never reaches
        # another's.
        StateRoot(
            path=".local/share/opencode",
            shadow="opencode-data",
            lifetime="project",
        ),
        StateRoot(
            path=".local/state/opencode", shadow="opencode-state", lifetime="run"
        ),
        StateRoot(path=".cache/opencode", shadow="opencode-cache", lifetime="run"),
        # opencode falls back to Claude Code's rules file and skills, so the
        # same two paths are shared read-only and nothing else of ~/.claude.
        StateRoot(
            path=".claude",
            shadow="opencode-claude",
            lifetime="run",
            share_ro=("CLAUDE.md", "skills"),
        ),
    ),
    protected=(".config/opencode", ".local/share/opencode", ".claude"),
    replica="",
    replica_scrubber="",
    credential_env="",
    credential_ow_path="",
    credential_file="",
    login_hint=(
        "run /connect once inside (each project keeps its own login); the "
        "provider's hosts must be on the [egress] allow-list"
    ),
    telemetry_off="",
    proxy_env=("HTTPS_PROXY", "https_proxy"),
    prepare=OPENCODE_PREPARE,
    permission_default=(),
    permission_overrides=(),
    settings_flag="",
    settings_env="OPENCODE_CONFIG_CONTENT",
    mandatory_host="",
    inference_path_regex=OPENCODE_INFERENCE_PATH,
    inference_allow="POST /v1/chat/completions, plain query string only",
    inference_short="POST /v1/chat/completions",
    credential_vendor="provider",
    ide=False,
    session_settings=opencode_session_settings,
)

PROFILES: dict[str, Profile] = {CLAUDE.name: CLAUDE, OPENCODE.name: OPENCODE}


def profile_for(name: str) -> Profile:
    """Return the named profile, or refuse naming the ones that exist."""
    try:
        return PROFILES[name]
    except KeyError:
        known = ", ".join(sorted(PROFILES))
        raise ConfigError(f"unknown tool {name!r} (known: {known})") from None


def _others(profile: Profile) -> list[Profile]:
    """List every profile except the given one, in registry order."""
    return [o for o in PROFILES.values() if o.name != profile.name]


def protected_paths(profile: Profile) -> list[tuple[str, str]]:
    """Pair every tool's protected path with the binary it configures, this tool's first."""
    # A fence that knew only its own tool would let one tool's session rewrite
    # the files that decide how another runs on the host.
    owners: dict[str, str] = {}
    for owner in (profile, *_others(profile)):
        for path in owner.protected:
            owners.setdefault(path, owner.binary)
    return list(owners.items())


def shell_profile(profile: Profile) -> str:
    """Render the launcher's view of a profile: one KEY=VALUE per line, lists repeated."""
    # Read in a loop and never evaluated. Newlines separate records, and a
    # record's own fields are separated by '|', so neither may appear in a value.
    lines = [
        f"NAME={profile.name}",
        f"COMMAND={profile.command}",
        f"BINARY={profile.binary}",
        f"IMAGE_TARGET={profile.image_target}",
        f"BUILD_ARG={profile.build_arg}",
        f"CACHE_BUST_ARG={profile.cache_bust_arg}",
        f"VERSION_ENV={profile.version_env}",
        f"REPLICA={profile.replica}",
        f"REPLICA_SCRUBBER={profile.replica_scrubber}",
        f"CREDENTIAL_ENV={profile.credential_env}",
        f"CREDENTIAL_OW_PATH={profile.credential_ow_path}",
        f"CREDENTIAL_FILE={profile.credential_file}",
        f"LOGIN_HINT={profile.login_hint}",
        f"TELEMETRY_OFF={profile.telemetry_off}",
        f"PREPARE={profile.prepare}",
        f"SETTINGS_FLAG={profile.settings_flag}",
        f"SETTINGS_ENV={profile.settings_env}",
        f"MANDATORY_HOST={profile.mandatory_host}",
        f"INFERENCE_ALLOW={profile.inference_allow}",
        f"INFERENCE_SHORT={profile.inference_short}",
        f"CREDENTIAL_VENDOR={profile.credential_vendor}",
        f"IDE={'1' if profile.ide else '0'}",
        *(f"PERM_DEFAULT={flag}" for flag in profile.permission_default),
        *(f"PERM_OVERRIDE={flag}" for flag in profile.permission_overrides),
        *(f"PROXY_ENV={name}" for name in profile.proxy_env),
        *(f"PROTECTED={path}|{binary}" for path, binary in protected_paths(profile)),
        # Every other tool's command: its data directory holds host-run code
        # and credentials, so no session may mount it.
        *(f"OTHER_COMMAND={o.command}" for o in _others(profile)),
    ]
    for path, binary in protected_paths(profile):
        if "|" in path or "|" in binary:
            raise ConfigError(f"protected path record contains '|': {path!r}")
    for root in profile.roots:
        fields = [
            root.path,
            root.shadow,
            root.project_dir,
            *root.share_rw_dirs,
            *root.share_rw_files,
            *root.share_ro,
            *(f for o in root.overlays for f in (o.under, o.sub, o.shadow, o.note)),
        ]
        for field in fields:
            if "|" in field:
                raise ConfigError(f"profile record field contains '|': {field!r}")
        lines.append(
            f"ROOT={root.path}|{root.shadow}|{root.project_dir}|{root.lifetime}"
        )
        lines += [f"RW_DIR={root.path}|{name}" for name in root.share_rw_dirs]
        lines += [f"RW_FILE={root.path}|{name}" for name in root.share_rw_files]
        lines += [f"RO={root.path}|{name}" for name in root.share_ro]
        lines += [
            f"OVERLAY={root.path}|{o.under}|{o.sub}|{o.shadow}|{o.note}"
            for o in root.overlays
        ]
    for line in lines:
        if "\n" in line:
            raise ConfigError(f"profile value contains a newline: {line!r}")
    return "\n".join(lines) + "\n"
