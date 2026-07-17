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
skeletons, a BUILD_BINDINGS row in check-sync.py, the
STACK_LABELS/PLUGIN_STACK_TOKENS rows in package-marketplace.py, and the
install_sim list in test-marketplace.sh. Conditional rows: PH_ALLOW in
check-sync.py when the stack keeps template tokens in a committed file, and
the stack's distinctive build tokens in check-sync.py CORE_STACK_TOKENS and
test-generic-stack.sh's leak regex, so the stack-agnostic guards see it.
Adding a tool is one TOOLS row — every
producer-side tool→directory mapping (materialize surfaces, marketplace agent
sources, check-sync parity list, refresh-agent-bodies mirror list) derives
from it — plus two authored steps: the per-agent mirror frontmatters, and the
shipped doctor roster (brief_doctor RUNTIME_PATHS + the .gitignore skeleton).
test_materialize.py gates the registry↔roster coverage.
"""

import os
from pathlib import Path

# --- rosters --------------------------------------------------------------
STACKS = ("go", "java-spring-boot", "generic")

# One row per AI tool — the single source for every tool→directory mapping.
#   agents_dir  the tool's agent directory (relative to a layer/project root)
#   suffix      the tool's agent-file suffix inside agents_dir
#   surfaces    runtime path prefixes installed only when the tool is selected
#   plugin      True when the tool is a marketplace plugin target
#   label       human-readable name for plugin descriptions
TOOLS = {
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
# (core/scripts/brief-expectations.toml channel_values); test_check_sync
# gates the pair.
CHANNELS = ("copy", "manifest", "marketplace")

# The engine sliver — the runtime subtrees that are NOT tool-discovered
# surfaces. Under the marketplace channel materialize.py installs exactly this
# sliver project-side, and package-marketplace.py bundles the same subtrees
# into each plugin's _engine/ payload; one definition keeps the two channels
# from drifting.
ENGINE_SLIVER = ("scripts", "schemas/scratch", ".claude/templates")


def mirror_surfaces():
    """(agents_dir, suffix) per non-claude tool: the mirror surfaces the
    renderer (refresh-agent-bodies.py) writes and check-sync's parity step
    gates. Shared DATA only — checker and renderer keep their own parsing
    logic on purpose, so one parsing bug cannot pass both."""
    return tuple(
        (row["agents_dir"], row["suffix"])
        for tool, row in TOOLS.items()
        if tool != "claude"
    )


def marketplace_excludes():
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


def detect_stack(target):
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


def runtime_files(root):
    """Relative paths of every runtime file under root — regular files only
    (symlinks excluded, `find -type f` parity), pyc/pycache excluded."""
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.suffix == ".pyc":
            continue
        rel = path.relative_to(root).as_posix()
        if "__pycache__" in rel:
            continue
        yield rel


def read_stamp(path, caller):
    """A VERSION/VERSION-DATE stamp, whitespace-stripped; loud on absence."""
    path = Path(path)
    if not path.is_file():
        raise SystemExit(f"{caller}: missing {path}")
    value = "".join(path.read_text(encoding="utf-8").split())
    if not value:
        raise SystemExit(f"{caller}: {path} is empty")
    return value


def logical_abspath(arg):
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
