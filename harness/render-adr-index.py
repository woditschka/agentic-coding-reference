#!/usr/bin/env python3
"""Render the ADR index table from the ADR files.

Usage: harness/render-adr-index.py [--check]

Each row of the § Index table in docs/adr/README.md derives from its ADR
file: the date from the filename, the decision title from the H1, the
status from the `**Status:**` line. The table was hand-mirrored before
(the README's old dual-write rule); by 94 ADRs three live drifts had
shipped, so the file's status line is now the single source and this
renders the mirror (the route-rule inventory's pattern). --check compares
instead of writing and exits 1 on drift (battery step 3l).

An ADR missing its H1 or `**Status:**` line is an error, never a silent
row gap. The default mode writes only when the content changed. Stdlib
only. Tested by tests/test_render_adr_index.py.
"""

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import write_guard  # noqa: E402

ADR_DIR = HERE.parent / "docs" / "adr"
README = ADR_DIR / "README.md"

USAGE = "usage: harness/render-adr-index.py [--check]"

_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9-]+\.md$")
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+(.+?)\s*$")
_HEADER = "| Date | Decision | Status |\n|------|----------|--------|"


def adr_rows(adr_dir: Path = ADR_DIR) -> list[str]:
    """One index row per ADR file, date order (filename order equals date
    order because the date leads the name)."""
    rows = []
    for path in sorted(adr_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        m = _NAME_RE.match(path.name)
        if not m:
            raise SystemExit(
                f"render-adr-index: {path.name!r} does not match "
                "YYYY-MM-DD-title-in-kebab-case.md"
            )
        title = status = None
        for line in path.read_text(encoding="utf-8").splitlines():
            if title is None and line.startswith("# "):
                title = line[2:].strip()
                continue
            s = _STATUS_RE.match(line)
            if s:
                status = s.group(1)
                break
        if title is None or status is None:
            raise SystemExit(
                f"render-adr-index: {path.name} lacks an H1 title or a "
                "'**Status:** …' line — the index derives from both"
            )
        if "|" in title or "|" in status:
            raise SystemExit(
                f"render-adr-index: {path.name} carries '|' in its title or "
                "status line — it would split the table row; rephrase"
            )
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in title + status):
            raise SystemExit(
                f"render-adr-index: {path.name} carries a control character "
                "in its title or status line; remove it"
            )
        if "[" in title or "]" in title:
            raise SystemExit(
                f"render-adr-index: {path.name} carries '[' or ']' in its H1 "
                "title — it would break the index row's link; rephrase"
            )
        if "![" in status:
            raise SystemExit(
                f"render-adr-index: {path.name} carries image syntax in its "
                "status line — the index renders text and links only"
            )
        rows.append(f"| {m.group(1)} | [{title}]({path.name}) | {status} |")
    return rows


def render(adr_dir: Path = ADR_DIR, readme: Path = README) -> str:
    """The README with its § Index table regenerated in place. The table
    runs from the header line after '## Index' to the end of the file —
    the section is last by construction; a section added below the table
    would silently vanish, so refuse text after it instead."""
    text = readme.read_text(encoding="utf-8")
    head, sep, tail = text.partition("## Index")
    if not sep:
        raise SystemExit("render-adr-index: docs/adr/README.md lacks '## Index'")
    for line in tail.splitlines():
        stripped = line.strip()
        # Only blank lines and the table itself may follow the heading:
        # render() rebuilds this region from adr_rows() alone, so any other
        # line shape must refuse — an allowance here is a silent delete.
        if not stripped or stripped.startswith("|"):
            continue
        if stripped.startswith("#"):
            raise SystemExit(
                "render-adr-index: a heading sits below '## Index' — the "
                "renderer owns everything after it and would drop that section"
            )
        raise SystemExit(
            "render-adr-index: prose sits below '## Index' — the renderer "
            "owns everything after it and a regenerate would drop that text; "
            "move it above the section"
        )
    return head + sep + "\n\n" + _HEADER + "\n" + "\n".join(adr_rows(adr_dir)) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) > 2 or (len(argv) == 2 and argv[1] != "--check"):
        print(USAGE, file=sys.stderr)
        return 2
    rendered = render()
    current = README.read_text(encoding="utf-8")
    if len(argv) == 2:
        if rendered != current:
            print(
                "render-adr-index: docs/adr/README.md § Index drifted from "
                "the ADR files' status lines — regenerate with "
                "harness/render-adr-index.py",
                file=sys.stderr,
            )
            return 1
        print("adr index matches the ADR files")
        return 0
    if rendered == current:
        print("adr index unchanged")
        return 0
    with write_guard.write_scope(ADR_DIR):
        write_guard.write_text(README, rendered, encoding="utf-8")
    print("adr index regenerated")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
