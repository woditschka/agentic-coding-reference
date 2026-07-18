#!/usr/bin/env python3
"""Shared rosters and helpers for the harness/*.py tooling. Import it, never
run it. Producer-side only: nothing here ships to a sample or a plugin.

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import helpers

The rosters are the single source for stack/tool enumeration: every script
that loops over stacks or tools reads these tuples (helpers.sh mirrors only
STACKS for the remaining bash orchestrators; check-sync guards the parity).
Adding a stack touches the STACKS rosters here and in helpers.sh, a
STACK_MARKERS row below (without it detect_stack silently falls back to
generic), its harness/stacks/<stack>/ tree, its harness/init/stacks/<stack>/
skeletons, a BUILD_BINDINGS row in check_sync/checks/suites.py, the
STACK_LABELS/PLUGIN_STACK_TOKENS rows in package-marketplace.py, and the
install_sim list in test-marketplace.sh. Conditional rows: PH_ALLOW in
check_sync/checks/faithful.py when the stack keeps template tokens in a
committed file, and the stack's distinctive build tokens in that module's
CORE_STACK_TOKENS and
test-generic-stack.sh's leak regex, so the stack-agnostic guards see it.
Adding a tool is one TOOLS row — every
producer-side tool→directory mapping (materialize surfaces, marketplace agent
sources, check-sync parity list, refresh-agent-bodies mirror list) derives
from it — plus two authored steps: the per-agent mirror frontmatters, and the
shipped doctor roster (doctor RUNTIME_PATHS + the .gitignore skeleton).
test_materialize.py gates the registry↔roster coverage.
"""

import os
import tomllib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

# --- rosters --------------------------------------------------------------
STACKS = ("go", "java-spring-boot", "generic")


# One row per AI tool — the single source for every tool→directory mapping.
# A TypedDict, not a frozen dataclass: TOOLS is a static config table every
# producer script reads by subscript (row["agents_dir"]), not a record routed
# through match/assert_never (the ADR 2026-07-17 dataclass rule targets those).
# TypedDict keeps the subscript syntax every caller uses while giving mypy
# precise per-key types.
#   agents_dir  the tool's agent directory (relative to a layer/project root)
#   suffix      the tool's agent-file suffix inside agents_dir
#   surfaces    runtime path prefixes installed only when the tool is selected
#   plugin      True when the tool is a marketplace plugin target
#   label       human-readable name for plugin descriptions
class ToolSpec(TypedDict):
    agents_dir: str
    suffix: str
    surfaces: tuple[str, ...]
    plugin: bool
    label: str


TOOLS: dict[str, ToolSpec] = {
    "claude": {
        "agents_dir": ".claude/agents",
        "suffix": ".md",
        "surfaces": (".claude/agents/", ".claude/hooks/"),
        "plugin": True,
        "label": "Claude Code",
    },
    "copilot": {
        "agents_dir": ".github/agents",
        "suffix": ".agent.md",
        "surfaces": (".github/agents/",),
        "plugin": True,
        "label": "Copilot CLI",
    },
    "opencode": {
        "agents_dir": ".opencode/agents",
        "suffix": ".md",
        "surfaces": (".opencode/agents/",),
        "plugin": False,
        "label": "OpenCode",
    },
    "junie": {
        "agents_dir": ".junie/agents",
        "suffix": ".md",
        "surfaces": (".junie/",),
        "plugin": True,
        "label": "Junie CLI",
    },
}

ALL_TOOLS = tuple(TOOLS)
PLUGIN_TOOLS = tuple(t for t, row in TOOLS.items() if row["plugin"])

# The distribution channels a project may declare in scripts/layout.toml
# [harness].channel. The consumer-side copy lives in the doctor manifest
# (core/scripts/doctor-expectations.toml channel_values); test_check_sync
# gates the pair.
CHANNELS = ("copy", "manifest", "marketplace")

# The engine sliver — the runtime subtrees that are NOT tool-discovered
# surfaces. Under the marketplace channel materialize.py installs exactly this
# sliver project-side, and package-marketplace.py bundles the same subtrees
# into each plugin's _engine/ payload; one definition keeps the two channels
# from drifting.
ENGINE_SLIVER = ("scripts", "schemas/scratch", ".claude/templates")


def mirror_surfaces() -> tuple[tuple[str, str], ...]:
    """(agents_dir, suffix) per non-claude tool: the mirror surfaces the
    renderer (refresh-agent-bodies.py) writes and check-sync's parity step
    gates. Shared DATA only — checker and renderer keep their own parsing
    logic on purpose, so one parsing bug cannot pass both."""
    return tuple(
        (row["agents_dir"], row["suffix"])
        for tool, row in TOOLS.items()
        if tool != "claude"
    )


def marketplace_excludes() -> tuple[str, ...]:
    """The tool-discovered surface prefixes a marketplace-channel materialize
    skips (the plugin delivers them): skills, the claude hooks, and every
    tool's agents dir — the complement of ENGINE_SLIVER plus tool config
    inside the runtime."""
    return (".claude/skills/", ".claude/hooks/") + tuple(
        row["agents_dir"] + "/" for row in TOOLS.values()
    )


# --- helpers ---------------------------------------------------------------
# Build-marker detection table, in priority order (go.mod wins on a target
# carrying more than one marker). Adding a stack is one row.
STACK_MARKERS = (
    ("go", ("go.mod",)),
    ("java-spring-boot", ("build.gradle", "build.gradle.kts", "pom.xml")),
)


def detect_stack(target: str | Path) -> str:
    """The stack a target's build marker selects; the one code home for the
    detection that bootstrap.sh runs and the /init and /materialize skills
    document. No recognized marker falls back to generic. The interactive
    skills ask the user on a multi-marker target; this function never asks."""
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
    """Relative paths of every runtime file under root — regular files only
    (symlinks excluded, `find -type f` parity), tool-cache dirs excluded by
    path segment (a mypy/ruff/pytest run from inside a scripts dir drops a
    cache there, and a cache must never ship as runtime)."""
    cache_dirs = {"__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix == ".pyc":
            continue
        relpath = path.relative_to(root)
        if cache_dirs.intersection(relpath.parts):
            continue
        yield relpath.as_posix()


def read_stamp(path: str | Path, caller: str) -> str:
    """A VERSION/VERSION-DATE stamp, whitespace-stripped; loud on absence."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{caller}: missing {path}")
    value = "".join(path.read_text(encoding="utf-8").split())
    if not value:
        raise SystemExit(f"{caller}: {path} is empty")
    return value


# --- layout.toml [harness] reader -----------------------------------------
# One parse+validate of scripts/layout.toml's [harness] table, shared by every
# producer script that reads it (init.py, materialize.py). Before this, the two
# scripts each interpreted the table separately — read_layout via tomllib, init
# via its own tomllib read plus two regex scans — and the extensions grammars
# had already diverged. See docs/adr/2026-07-18-materialize-previewable-plan.md.
# The reader is producer-side only: the consumer-shipped doctor keeps its own
# reader (it cannot import this module), and check-sync keeps its checker
# regexes; the shared vocabulary is parity-gated, not rendered.


class LayoutError(Exception):
    """A scripts/layout.toml [harness] table that fails to parse or validate.
    The message names the defect without a caller prefix; each caller adds its
    own and picks its exit convention — materialize raises SystemExit, init
    prints and returns 1."""


@dataclass(frozen=True)
class HarnessLayout:
    """The parsed [harness] table. `channel` is resolved (the declared value or
    the "copy" default); `channel_declared` records whether an explicit
    non-empty channel was present — the distinction init's never-flip conflict
    check needs. `tools` is the declared list or None (absent → the caller
    auto-detects). `extensions` is the declared tuple or ()."""

    channel: str
    channel_declared: bool
    tools: list[str] | None
    extensions: tuple[str, ...]


def unsafe_extension_path(ext_path: str) -> bool:
    """True when an extension path cannot land verbatim in layout.toml's
    extensions array, a .gitignore line, or a terminal: empty or ".", TOML- or
    array-corrupting characters, surrounding whitespace, control characters
    (tomllib decodes \\uXXXX escapes into real bytes — a terminal-injection
    vector), dot-dot traversal, or an absolute path. One predicate serves the
    reader (reject a hostile declaration) and materialize.record_extension
    (reject before the textual splice)."""
    return (
        not ext_path
        or ext_path == "."
        or any(ch in ext_path for ch in '"[],\\')
        or ext_path != ext_path.strip()
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in ext_path)
        or ".." in Path(ext_path).parts
        or Path(ext_path).is_absolute()
    )


def read_harness_layout(target: str | Path) -> HarnessLayout:
    """Parse and validate the [harness] table of target/scripts/layout.toml.

    A missing file is the greenfield default (copy channel, nothing declared).
    A file the parser or a per-field check rejects raises LayoutError — never a
    silent default, which would install plugin-delivered surfaces into a
    marketplace project whose declaration just went unreadable. This reads
    only; the extensions write-back stays a textual splice in
    materialize.record_extension so a re-write keeps the file's comments."""
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

    raw_tools = harness.get("tools")
    tools: list[str] | None
    if raw_tools is None:
        tools = None
    elif not (
        isinstance(raw_tools, list)
        and raw_tools
        and all(isinstance(t, str) for t in raw_tools)
    ):
        raise LayoutError(
            f"{lt} [harness] tools must be a non-empty list of strings — fix "
            "the declaration or remove the key"
        )
    else:
        unknown = sorted(set(raw_tools) - set(ALL_TOOLS))
        if unknown:
            raise LayoutError(
                f"{lt} [harness] tools names unknown tool(s) "
                f"{', '.join(unknown)} (valid: {', '.join(ALL_TOOLS)}) — an "
                "unknown name would silently drop that tool's surfaces"
            )
        tools = raw_tools

    raw_exts = harness.get("extensions", [])
    if not (isinstance(raw_exts, list) and all(isinstance(e, str) for e in raw_exts)):
        raise LayoutError(
            f"{lt} [harness] extensions must be a list of strings — fix the declaration"
        )
    bad = [e for e in raw_exts if unsafe_extension_path(e)]
    if bad:
        raise LayoutError(
            f"{lt} [harness] extensions entry {bad[0]!r} is empty, absolute, "
            "traversing, or carries unsafe characters — declare plain "
            "target-relative paths"
        )

    return HarnessLayout(channel, channel_declared, tools, tuple(raw_exts))


def logical_abspath(arg: str | Path) -> Path:
    """Absolute path with shell `pwd` semantics: the shell's logical cwd
    ($PWD, symlinks kept as entered) wins over the physical getcwd(), so
    report lines print the path the caller typed — e.g. /tmp/…, not macOS's
    /private/tmp/…."""
    path = Path(arg)
    if path.is_absolute():
        return path
    pwd = os.environ.get("PWD")
    try:
        if pwd and os.path.samefile(pwd, os.getcwd()):
            return Path(os.path.normpath(os.path.join(pwd, arg)))
    except OSError:
        pass
    return path.absolute()
