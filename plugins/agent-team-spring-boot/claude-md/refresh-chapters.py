#!/usr/bin/env python3
"""Refresh the harness-managed chapters of a consumer's CLAUDE.md in place, and stamp the release date.

    refresh-chapters.py <claude-md> <harness-root> [version-date]

Each chapter of harness/claude-md/managed-chapters.md is found in the target
by its `## ` heading outside code fences and replaced through the next such
heading; every other chapter is the project's, and an absent heading is
reported and left for init or the materialize migration. Source-only, never
materialized as runtime; stdlib only.
"""

import os
import re
import sys
import tempfile
from pathlib import Path

USAGE = "usage: refresh-chapters.py <claude-md> <harness-root> [version-date]"
ARG_COUNTS = (3, 4)
USAGE_EXIT = 2
FAILURE_EXIT = 1
# The bound keeps a symlink cycle from hanging the refresh.
MAX_SYMLINK_CHAIN = 10

# The harness-reserved stamp-line prefix: the upsert removes any line matching
# it, so a consumer must not author a comment with that prefix.
STAMP_LINE = re.compile(r"^[ \t]*<!--[ \t]*harness:")


class RefreshError(Exception):
    """A source or target defect the refresh reports on stderr and exits on."""


def _is_fence(line: str) -> bool:
    return line.lstrip(" \t").startswith("```")


def chapter_titles(lines: list[str]) -> list[str]:
    """Return each `## ` heading outside a code fence, in order."""
    titles, fence = [], False
    for line in lines:
        if _is_fence(line):
            fence = not fence
            continue
        if not fence and line.startswith("## "):
            titles.append(line)
    return titles


def heading_present(lines: list[str], title: str) -> bool:
    """Report whether the title is present as a heading outside a code fence."""
    fence = False
    for line in lines:
        if _is_fence(line):
            fence = not fence
            continue
        if not fence and line == title:
            return True
    return False


def extract_chapter(lines: list[str], title: str) -> list[str]:
    """Return the chapter from its heading through the line before the next heading, trailing blanks trimmed."""
    out, started, fence = [], False, False
    for line in lines:
        if _is_fence(line):
            if started:
                out.append(line)
            fence = not fence
            continue
        if not fence and not started and line == title:
            started = True
            out.append(line)
            continue
        if started and not fence and line.startswith("## "):
            break
        if started:
            out.append(line)
    while out and not out[-1].strip():
        out.pop()
    return out


def replace_chapter(lines: list[str], chapter: list[str], title: str) -> list[str]:
    """Return the lines with the heading-bounded chapter replaced, fence-aware."""
    out, fence, skip, done = [], False, False, False
    for line in lines:
        if _is_fence(line):
            fence = not fence
            if not skip:
                out.append(line)
            continue
        if not fence and not done and line == title:
            out.extend(chapter)
            skip = True
            done = True
            continue
        if skip and not fence and line.startswith("## "):
            skip = False
            out.append("")
            out.append(line)
            continue
        if skip:
            continue
        out.append(line)
    return out


def stamp_date(lines: list[str], version_date: str) -> list[str]:
    """Return the lines with the release date stamped as the first line, replacing any prior stamp."""
    # The stamp lands in the context of every session, since CLAUDE.md is the
    # one file injected into all of them; the release date stays stable across
    # re-materialize where a wall-clock stamp would not.
    kept = [line for line in lines if not STAMP_LINE.match(line)]
    return [f"<!-- harness: {version_date} -->", *kept]


def resolve_symlink(path: Path) -> Path:
    """Return the backing file of a possibly chained symlink, so the rename updates the real file."""
    orig = path
    for _ in range(MAX_SYMLINK_CHAIN + 1):
        if not path.is_symlink():
            return path
        link = path.readlink()
        path = link if link.is_absolute() else path.parent / link
    raise SystemExit(
        f"refresh-chapters: symlink chain at {orig} exceeds {MAX_SYMLINK_CHAIN} links — cycle?"
    )


def atomic_write(path: Path, text: str) -> None:
    """Write through a temp file in the target's directory and an atomic same-filesystem rename."""
    fd, tmp = tempfile.mkstemp(prefix=".claude-md.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        Path(tmp).replace(path)
    except BaseException:
        Path(tmp).unlink()
        raise


def _managed_titles(src: Path, src_lines: list[str]) -> list[str]:
    # A duplicate would replace the same target chapter twice, so the source
    # is validated before any write.
    titles = chapter_titles(src_lines)
    if not titles:
        raise RefreshError(f"{src} has no '## ' chapters")
    seen: set[str] = set()
    for title in titles:
        if title in seen:
            raise RefreshError(f"{src} has a duplicate '{title}' chapter")
        seen.add(title)
    return titles


def _release_date(root: Path, version_date: str) -> str:
    # An explicit argument wins; otherwise VERSION-DATE at the harness or
    # plugin root, the directory that holds claude-md/.
    stamp_file = root / "VERSION-DATE"
    if not version_date and stamp_file.is_file():
        return "".join(stamp_file.read_text(encoding="utf-8").split())
    return version_date


def _refresh(claude: Path, root: Path, version_date: str) -> int:
    src = root / "claude-md" / "managed-chapters.md"
    if not claude.is_file():
        raise RefreshError(f"no CLAUDE.md at {claude}")
    if not src.is_file():
        raise RefreshError(f"missing chapter source {src}")
    src_lines = src.read_text(encoding="utf-8").splitlines()
    if not src_lines or not src_lines[0].startswith("## "):
        raise RefreshError(f"{src} must start with a '## ' heading")
    claude = resolve_symlink(claude)
    # read_bytes, not read_text: newline translation would hide the CRLF.
    # Heading matching is exact, so a CRLF target would match nothing and
    # silently refresh nothing; it is refused instead.
    raw = claude.read_bytes().decode("utf-8")
    if "\r" in raw:
        print(
            f"refresh: {claude} has CRLF line endings — normalize to LF, then re-run",
            file=sys.stderr,
        )
        print("0 refreshed (CRLF — normalize to LF)")
        return 0
    titles = _managed_titles(src, src_lines)
    lines = raw.splitlines()
    refreshed, absent = 0, []
    for title in titles:
        if heading_present(lines, title):
            lines = replace_chapter(lines, extract_chapter(src_lines, title), title)
            refreshed += 1
        else:
            absent.append(title)
    version_date = _release_date(root, version_date)
    stamp_note = ", date not stamped (no VERSION-DATE)"
    if version_date:
        lines = stamp_date(lines, version_date)
        stamp_note = f", date {version_date} stamped"
    # Nothing replaced and nothing to stamp leaves the target's bytes alone.
    if refreshed or version_date:
        atomic_write(claude, "\n".join(lines) + "\n")
    if absent:
        print(
            f"{refreshed} refreshed, {len(absent)} absent: {' '.join(absent)}{stamp_note}"
        )
    else:
        print(f"{refreshed} refreshed{stamp_note}")
    return 0


def apply(claude_md: str | Path, root: str | Path, version_date: str = "") -> int:
    """Refresh every managed chapter, stamp the date, print the report line, and return the exit code."""
    try:
        return _refresh(Path(claude_md), Path(root), version_date)
    except RefreshError as exc:
        print(f"refresh: {exc}", file=sys.stderr)
        return FAILURE_EXIT


def main(argv: list[str]) -> int:
    """Refresh from the command line and return the exit code."""
    if len(argv) not in ARG_COUNTS:
        print(USAGE, file=sys.stderr)
        return USAGE_EXIT
    return apply(*argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
