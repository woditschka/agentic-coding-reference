#!/usr/bin/env python3
"""Shared rosters and helpers for the harness/*.py tooling. Import it, never
run it. Producer-side only: nothing here ships to a sample or a plugin.

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import helpers

The rosters are the single source for stack/tool enumeration: every script
that loops over stacks or tools reads these tuples (helpers.sh mirrors them
for the remaining bash orchestrators; check-sync guards the parity). Adding a
stack is one edit here plus helpers.sh (plus its harness/stacks/<stack>/
tree). Adding a tool starts here but also needs the tool→directory mappings:
materialize.py (surface detection/exclusion), package-marketplace.py
(agents mapping — fails loud when missing), check-sync.py's parity step
(sibling dir list), and refresh-agent-bodies.py (mirror list).
"""

import os
from pathlib import Path

# --- rosters --------------------------------------------------------------
STACKS = ("go", "java-spring-boot", "generic")
PLUGIN_TOOLS = ("claude", "copilot", "junie")   # OpenCode is not a plugin target
ALL_TOOLS = ("claude", "copilot", "opencode", "junie")


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
        (stack for stack, markers in STACK_MARKERS
         if any((target / m).is_file() for m in markers)),
        "generic",
    )


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
