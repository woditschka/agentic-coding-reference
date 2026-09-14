#!/usr/bin/env python3
"""Render the consumer .gitignore runtime block from the doctor's runtime roster.

Usage: harness/render-gitignore-block.py [--check]

Reads RUNTIME_PATHS in harness/core/scripts/doctor.py and writes
harness/init/core/gitignore-runtime.txt: the fixed header, the .scratch/
ledger line, then one line per runtime path, a directory in its /* form so a
declared extension can be re-included beneath it. --check compares instead of
writing and exits 1 on drift (battery step 3m). The roster is the one place a
shipped file is registered; the block follows it.

The default mode writes only when the content changed. Stdlib only.
Tested by tests/test_render_gitignore_block.py.
"""

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import write_guard  # noqa: E402

DOCTOR = HERE / "core" / "scripts" / "doctor.py"
OUTPUT = HERE / "init" / "core" / "gitignore-runtime.txt"
USAGE = "usage: harness/render-gitignore-block.py [--check]"
CHECK_ARGV_LENGTH = 2
LEDGER_LINE = ".scratch/"

HEADER = """\
# Handoff ledger (per-session, never committed)
.scratch/

# Harness runtime — delivered out-of-band, not committed. Manifest materializes
# all of it from /harness; marketplace ships the tool surfaces as a plugin and
# materializes only the engine sliver (scripts, schemas, templates).
# Project-owned files (settings.json, scripts/layout.toml, docs/) stay tracked.
# Runtime dirs use the /* form so declared extensions (scripts/layout.toml
# [harness] extensions) can be re-included below — /materialize adds a
# "!path/" line per extension so the project's own skills/agents stay tracked.
# A bare "dir/" form would defeat that: git never descends into an ignored
# directory, so a re-include under it cannot take effect.
"""


def runtime_paths(doctor_path: Path) -> list[str]:
    """Read RUNTIME_PATHS from the doctor module without running its command line."""
    spec = importlib.util.spec_from_file_location("harness_doctor", doctor_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load {doctor_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = getattr(module, "RUNTIME_PATHS", None)
    if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
        raise ValueError("doctor.RUNTIME_PATHS is not a list of strings")
    return list(paths)


def ignore_line(path: str) -> str:
    """Return the block line for one runtime path: a directory ignores its contents."""
    name = path.rsplit("/", 1)[-1]
    return path if "." in name else f"{path}/*"


def render(paths: list[str]) -> str:
    """Render the whole block: the header, then one line per runtime path."""
    return HEADER + "".join(f"{ignore_line(path)}\n" for path in paths)


def main(argv: list[str]) -> int:
    """Render the block, or compare it under --check; return the exit code."""
    check = False
    if len(argv) == CHECK_ARGV_LENGTH and argv[1] == "--check":
        check = True
    elif len(argv) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        content = render(runtime_paths(DOCTOR))
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"cannot read the doctor roster: {exc}", file=sys.stderr)
        return 1
    committed = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    shown = (
        str(OUTPUT.relative_to(HERE.parent))
        if OUTPUT.is_relative_to(HERE.parent)
        else str(OUTPUT)
    )
    if check:
        if committed != content:
            print(
                f"{shown} drifted from doctor.RUNTIME_PATHS — regenerate with "
                "harness/render-gitignore-block.py",
                file=sys.stderr,
            )
            return 1
        return 0
    if committed != content:
        with write_guard.write_scope(OUTPUT.parent):
            write_guard.write_text(OUTPUT, content)
        print(f"wrote {shown}")
    else:
        print(f"{shown} already current")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
