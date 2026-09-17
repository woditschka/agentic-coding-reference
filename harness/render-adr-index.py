#!/usr/bin/env python3
"""Render the ADR index table from the ADR files.

Usage: harness/render-adr-index.py [--check]

Each row derives from its ADR file: the date from the filename, the title
from the H1, the status from the `**Status:**` line, so the file is the single
source and the table its mirror. --check compares instead of writing and
exits 1 on drift. Stdlib only.
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
CHECK_ARGV_LENGTH = 2

_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9-]+\.md$")
_STATUS_RE = re.compile(r"^\*\*Status:\*\*\s+(.+?)\s*$")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_HEADER = "| Date | Decision | Status |\n|------|----------|--------|"


def adr_rows(adr_dir: Path = ADR_DIR) -> list[str]:
    """Return one index row per ADR file in date order, which is filename order."""
    return [
        _adr_row(path)
        for path in sorted(adr_dir.glob("*.md"))
        if path.name != "README.md"
    ]


def _adr_row(path: Path) -> str:
    m = _NAME_RE.match(path.name)
    if not m:
        raise SystemExit(
            f"render-adr-index: {path.name!r} does not match "
            "YYYY-MM-DD-title-in-kebab-case.md"
        )
    title, status = _title_and_status(path)
    _check_row_text(path, title, status)
    return f"| {m.group(1)} | [{title}]({path.name}) | {status} |"


def _title_and_status(path: Path) -> tuple[str, str]:
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
    return title, status


def _check_row_text(path: Path, title: str, status: str) -> None:
    # The row is a table line with a link: a pipe splits it, a bracket breaks
    # the link, and image syntax has no place in a status.
    if "|" in title or "|" in status:
        raise SystemExit(
            f"render-adr-index: {path.name} carries '|' in its title or "
            "status line — it would split the table row; rephrase"
        )
    if _CONTROL_RE.search(title + status):
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


def render(adr_dir: Path = ADR_DIR, readme: Path = README) -> str:
    """Return the README with its Index table regenerated in place."""
    # The table runs from the heading to the end of the file, so a section
    # added below it would silently vanish; text after it is refused instead.
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
    """Render the index, or compare it under --check, and return the exit code."""
    check = len(argv) == CHECK_ARGV_LENGTH
    if len(argv) > CHECK_ARGV_LENGTH or (check and argv[1] != "--check"):
        print(USAGE, file=sys.stderr)
        return 2
    rendered = render()
    current = README.read_text(encoding="utf-8")
    if check:
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
    raise SystemExit(main(sys.argv))
