#!/usr/bin/env python3
"""Hold the rosters of stacks, tools, and channels, and the helpers every producer script shares.

Producer-side only, imported and never run: every script that loops over
stacks or tools reads these tuples, and the bash orchestrators shell out for
them. Adding a stack or a tool starts here; harness/README.md lists the
other surfaces each addition touches.
"""

import os
import re
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

# The exit codes every producer script shares: a usage error and a failure.
USAGE_EXIT = 2
FAILURE_EXIT = 1

# --- rosters --------------------------------------------------------------
STACKS = ("go", "java-spring-boot", "generic")


# A TypedDict rather than a record: TOOLS is a static table every producer
# script reads by subscript, never a value routed through a match.
class ToolSpec(TypedDict):
    """One AI tool: its agent directory and file suffix, the surfaces it alone installs, and its labels."""

    agents_dir: str
    suffix: str
    surfaces: tuple[str, ...]
    plugin: bool
    label: str
    compat: str


TOOLS: dict[str, ToolSpec] = {
    "claude": {
        "agents_dir": ".claude/agents",
        "suffix": ".md",
        "surfaces": (".claude/agents/", ".claude/hooks/"),
        "plugin": True,
        "label": "Claude Code",
        "compat": "claude-code",
    },
    "copilot": {
        "agents_dir": ".github/agents",
        "suffix": ".agent.md",
        "surfaces": (".github/agents/",),
        "plugin": True,
        "label": "Copilot CLI",
        "compat": "github-copilot",
    },
    "opencode": {
        "agents_dir": ".opencode/agents",
        "suffix": ".md",
        "surfaces": (".opencode/agents/",),
        "plugin": False,
        "label": "OpenCode",
        "compat": "opencode",
    },
}

ALL_TOOLS = tuple(TOOLS)
# The `compatibility:` frontmatter names a skill may declare — one per tool.
COMPATIBILITY_NAMES = frozenset(row["compat"] for row in TOOLS.values())
PLUGIN_TOOLS = tuple(t for t, row in TOOLS.items() if row["plugin"])

# The skill namespace every plugin shares: plugin.json `name`, which the tool
# uses as the user-typed prefix (/agent-team:doctor). Distinct from the
# marketplace ENTRY name (`agent-team-<stack>` for Claude, the primary target;
# `agent-team-<stack>-<tool>` for the others — unique per manifest) that keys
# installs and enabledPlugins. A consumer enables one plugin per project, so
# the shared prefix never collides. See ADR 2026-08-01-shared-plugin-namespace.
PLUGIN_NAMESPACE = "agent-team"

# Documentation files sanctioned inside .claude/agents/ — and only there.
# The producer tooling (mirror renderer, parity/vocabulary/roster gates)
# skips exactly these in that directory; any other file there —
# README-prefixed included — is checked as an agent, because Claude Code
# and OpenCode load every matching file in their agent dirs and an unlisted
# doc would otherwise ship as a live, ungated agent. In a tool mirror dir
# even these stems are strays: the reverse parity sweep fails them, since
# the renderer's prune never deletes a doc. The packager independently
# drops the README* prefix (never ships a doc into a plugin's agent
# discovery).
AGENT_DOC_STEMS = frozenset({"README"})


# The distribution channels a project may declare in scripts/layout.toml
# [harness].channel. The consumer-side copy lives in the doctor manifest
# (core/scripts/doctor-expectations.toml channel_values); test_verify_harness
# gates the pair.
CHANNELS = ("copy", "manifest", "marketplace")

# The engine sliver — the runtime subtrees that are NOT tool-discovered
# surfaces. Under the marketplace channel materialize.py installs exactly this
# sliver project-side, and package-marketplace.py bundles the same subtrees
# into each plugin's _engine/ payload; one definition keeps the two channels
# from drifting.
ENGINE_SLIVER = ("scripts", "schemas/scratch", ".claude/templates")


def mirror_surfaces() -> tuple[tuple[str, str], ...]:
    """Return the (agents_dir, suffix) pair of every tool but Claude: the mirror surfaces."""
    # Shared data only: the checker and the renderer keep their own parsing,
    # so one parsing bug cannot pass both.
    return tuple(
        (row["agents_dir"], row["suffix"])
        for tool, row in TOOLS.items()
        if tool != "claude"
    )


def marketplace_excludes() -> tuple[str, ...]:
    """Return the tool-discovered surface prefixes the marketplace plugin delivers instead of an install."""
    return (
        ".claude/skills/",
        ".claude/hooks/",
        *(row["agents_dir"] + "/" for row in TOOLS.values()),
    )


# --- helpers ---------------------------------------------------------------
# Build-marker detection table, in priority order (go.mod wins on a target
# carrying more than one marker). Adding a stack is one row.
STACK_MARKERS = (
    ("go", ("go.mod",)),
    ("java-spring-boot", ("build.gradle", "build.gradle.kts", "pom.xml")),
)


def detect_stack(target: str | Path) -> str:
    """Return the stack a target's build marker selects, generic when none is recognized."""
    target = Path(target)
    return next(
        (
            stack
            for stack, markers in STACK_MARKERS
            if any((target / m).is_file() for m in markers)
        ),
        "generic",
    )


def runtime_files(root: Path) -> Iterator[str]:
    """Yield the relative path of every regular runtime file under root, caches and symlinks excluded."""
    cache_dirs = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix == ".pyc":
            continue
        relpath = path.relative_to(root)
        if cache_dirs.intersection(relpath.parts):
            continue
        yield relpath.as_posix()


def read_stamp(path: str | Path, caller: str) -> str:
    """Read a VERSION or VERSION-DATE stamp, whitespace-stripped, and exit loud on absence."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{caller}: missing {path}")
    value = "".join(path.read_text(encoding="utf-8").split())
    if not value:
        raise SystemExit(f"{caller}: {path} is empty")
    return value


# The one reader of the [harness] table for every producer script. The
# consumer-shipped doctor keeps its own, since it cannot import this module.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class LayoutError(Exception):
    """A scripts/layout.toml [harness] table that fails to parse or validate; the message carries no caller prefix."""


@dataclass(frozen=True)
class HarnessLayout:
    """The parsed [harness] table: the channel in force, whether it was declared, the tools, the extensions."""

    # tools is None when absent, so the caller auto-detects.

    channel: str
    channel_declared: bool
    tools: list[str] | None
    extensions: tuple[str, ...]


def unsafe_extension_path(ext_path: str) -> bool:
    """Report whether an extension path cannot land verbatim in the layout array, a .gitignore line, or a terminal."""
    # tomllib decodes escapes into real bytes, so a control character is a
    # terminal-injection vector; the reader and the recorder share one predicate.
    return (
        not ext_path
        or ext_path == "."
        or any(ch in ext_path for ch in '"[],\\')
        or ext_path != ext_path.strip()
        or _CONTROL_RE.search(ext_path) is not None
        or ".." in Path(ext_path).parts
        or Path(ext_path).is_absolute()
    )


def read_harness_layout(target: str | Path) -> HarnessLayout:
    """Parse and validate the [harness] table of the target's layout; a missing file is the greenfield default."""
    # A file the parser or a field check rejects raises rather than defaulting,
    # which would install plugin-delivered surfaces into a marketplace project
    # whose declaration just went unreadable.
    lt = Path(target) / "scripts" / "layout.toml"
    if not lt.is_file():
        return HarnessLayout("copy", False, None, ())
    try:
        raw = lt.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LayoutError(
            f"{lt} unreadable: {exc} — fix the file (its channel/tools/"
            "extensions declaration could not be read)"
        ) from None
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        raise LayoutError(
            f"{lt} unparseable: {exc} — fix the layout (its channel/tools/"
            "extensions declaration is unreadable)"
        ) from None
    harness = data.get("harness", {})
    if not isinstance(harness, dict):
        raise LayoutError(f"{lt} [harness] is not a table — fix the declaration")

    raw_channel = harness.get("channel")
    channel_declared = isinstance(raw_channel, str) and bool(raw_channel)
    channel = raw_channel if channel_declared else "copy"
    if channel not in CHANNELS:
        raise LayoutError(
            f"{lt} [harness] channel {channel!r} is not one of "
            f"{', '.join(CHANNELS)} — fix the declaration"
        )

    tools = _declared_tools(lt, harness.get("tools"))
    extensions = _declared_extensions(lt, harness.get("extensions", []))
    return HarnessLayout(channel, channel_declared, tools, extensions)


def _declared_tools(layout: Path, raw_tools: object) -> list[str] | None:
    if raw_tools is None:
        return None
    if not (
        isinstance(raw_tools, list)
        and raw_tools
        and all(isinstance(t, str) for t in raw_tools)
    ):
        raise LayoutError(
            f"{layout} [harness] tools must be a non-empty list of strings — fix "
            "the declaration or remove the key"
        )
    unknown = sorted(set(raw_tools) - set(ALL_TOOLS))
    if unknown:
        raise LayoutError(
            f"{layout} [harness] tools names unknown tool(s) "
            f"{', '.join(unknown)} (valid: {', '.join(ALL_TOOLS)}) — an "
            "unknown name would silently drop that tool's surfaces"
        )
    return raw_tools


def _declared_extensions(layout: Path, raw_exts: object) -> tuple[str, ...]:
    if not (isinstance(raw_exts, list) and all(isinstance(e, str) for e in raw_exts)):
        raise LayoutError(
            f"{layout} [harness] extensions must be a list of strings — fix the declaration"
        )
    bad = [e for e in raw_exts if unsafe_extension_path(e)]
    if bad:
        raise LayoutError(
            f"{layout} [harness] extensions entry {bad[0]!r} is empty, absolute, "
            "traversing, or carries unsafe characters — declare plain "
            "target-relative paths"
        )
    return tuple(raw_exts)


def _lexically_normalized(path: Path) -> Path:
    """Collapse `.` and `..` segments without touching the filesystem."""
    parts: list[str] = []
    for part in path.parts:
        if part == ".":
            continue
        if part == ".." and parts and parts[-1] != "..":
            parts.pop()
            continue
        parts.append(part)
    return Path(*parts)


def logical_abspath(arg: str | Path) -> Path:
    """Return the absolute path with the shell's logical cwd, so a report prints the path as typed."""
    # $PWD keeps symlinks as entered, where the physical cwd would print
    # /private/tmp on macOS for a /tmp argument.
    path = Path(arg)
    if path.is_absolute():
        return path
    pwd = os.environ.get("PWD")
    try:
        if pwd and Path(pwd).samefile(Path.cwd()):
            return _lexically_normalized(Path(pwd) / arg)
    except OSError:
        pass
    return path.absolute()
