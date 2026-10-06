#!/usr/bin/env python3
"""The per-tool facts of the agent-dev engine: one Profile for each supported agent tool.

A profile is shipped code, never operator policy. It names what differs
between tools: the command and image, the directories the session sees as a
private shadow, the credential store, the permission posture, the one request
shape the --ow reverse port admits, and the settings document the session
receives. The engine knows none of it; the launcher reads it through the
`profile` verb as KEY=VALUE lines.
"""

import json
from dataclasses import dataclass
from typing import Protocol

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


@dataclass(frozen=True, slots=True)
class StateRoot:
    """One home-relative directory the session sees as a private shadow plus named shares."""

    path: str
    # The shadow's name under the data dir's state/ directory.
    shadow: str
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
    # Home-relative paths that decide how the tool runs on the host: refused as
    # a writable mount, as a path containing one, and as the project directory.
    protected: tuple[str, ...]
    # The tool's own config file in the home directory, replicated per launch
    # and scrubbed to the project; empty when the tool keeps none.
    replica: str
    replica_scrubber: str
    # The env var that relocates the credential store, and the unmounted path
    # that stands in for it under --ow.
    credential_env: str
    credential_ow_path: str
    credential_file: str
    login_hint: str
    # The env declaration that turns the tool's telemetry off.
    telemetry_off: str
    # Permission flags the launcher injects unless the operator passes one of
    # the override flags; empty means the tool has no such posture to inject.
    permission_default: tuple[str, ...]
    permission_overrides: tuple[str, ...]
    # How the settings document reaches the session: an argv flag or an env var.
    settings_flag: str
    settings_env: str
    # The one host the session cannot work without when it reaches the vendor API.
    mandatory_host: str
    # The one request shape the --ow reverse port admits, and how to name it.
    inference_path_regex: str
    inference_allow: str
    inference_short: str
    credential_vendor: str
    # Whether the JetBrains IDE bridge is offered.
    ide: bool
    session_settings: SessionSettings


# Claude's in-process sandbox stays off: under Docker's default seccomp profile
# bubblewrap cannot create a user namespace (README § Process has the matrix),
# and turning it on would mean seccomp=unconfined for the whole container.
SANDBOX_OFF = {"sandbox": {"enabled": False, "failIfUnavailable": False}}
# The session's bearer token under --ow. A placeholder: the peer ignores it
# and the real credential is never mounted, so nothing inside can leak it.
CLAUDE_PLACEHOLDER_TOKEN = "claude-dev"
# The Messages endpoint and its token-count sibling, with or without a query
# string. squid's urlpath_regex sees the query, and Claude Code posts to
# /v1/messages?beta=true.
CLAUDE_INFERENCE_PATH = r"^/v1/messages(/count_tokens)?(\?.*)?$"


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


CLAUDE = Profile(
    name="claude",
    command="claude-dev",
    binary="claude",
    image_target="claude",
    build_arg="CLAUDE_VERSION",
    cache_bust_arg="CLAUDE_CACHE_BUST",
    version_env="CLAUDE_DEV_CLAUDE_VERSION",
    roots=(
        StateRoot(
            path=".claude",
            shadow="claude",
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
    protected=(".claude",),
    replica=".claude.json",
    replica_scrubber="claude_dev_scrub.py",
    credential_env="CLAUDE_SECURESTORAGE_CONFIG_DIR",
    credential_ow_path=".config/claude-dev-ow-auth",
    credential_file=".credentials.json",
    login_hint="type '/login' once inside",
    telemetry_off="DISABLE_TELEMETRY=1",
    permission_default=("--permission-mode", "auto"),
    permission_overrides=("--permission-mode", "--dangerously-skip-permissions"),
    settings_flag="--settings",
    settings_env="",
    mandatory_host="api.anthropic.com",
    inference_path_regex=CLAUDE_INFERENCE_PATH,
    inference_allow="POST /v1/messages (and /count_tokens), any query string",
    inference_short="POST /v1/messages",
    credential_vendor="Anthropic",
    ide=True,
    session_settings=claude_session_settings,
)

PROFILES: dict[str, Profile] = {CLAUDE.name: CLAUDE}


def profile_for(name: str) -> Profile:
    """Return the named profile, or refuse naming the ones that exist."""
    try:
        return PROFILES[name]
    except KeyError:
        known = ", ".join(sorted(PROFILES))
        raise ConfigError(f"unknown tool {name!r} (known: {known})") from None


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
        f"SETTINGS_FLAG={profile.settings_flag}",
        f"SETTINGS_ENV={profile.settings_env}",
        f"MANDATORY_HOST={profile.mandatory_host}",
        f"INFERENCE_ALLOW={profile.inference_allow}",
        f"INFERENCE_SHORT={profile.inference_short}",
        f"CREDENTIAL_VENDOR={profile.credential_vendor}",
        f"IDE={'1' if profile.ide else '0'}",
        *(f"PERM_DEFAULT={flag}" for flag in profile.permission_default),
        *(f"PERM_OVERRIDE={flag}" for flag in profile.permission_overrides),
        *(f"PROTECTED={path}" for path in profile.protected),
    ]
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
        lines.append(f"ROOT={root.path}|{root.shadow}|{root.project_dir}")
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
