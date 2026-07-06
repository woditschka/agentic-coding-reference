#!/usr/bin/env python3
"""Refresh the harness-managed chapters of a consumer's CLAUDE.md in place.

    refresh-chapters.py <claude-md> <harness-root> [version-date]

CLAUDE.md is project-owned — scaffolded once, never overwritten. But several of
its chapters are stack-agnostic harness doctrine: Agent Usage, Memory, Writing
Standards, the Scratch Directory, Documentation Updates. They are single-sourced
in one file, harness/claude-md/managed-chapters.md, whose chapters are the
managed set — add a chapter by adding a `## ` section, remove one by deleting
it. That file mirrors the shipped CLAUDE.md: what you read here, in this order,
is what materializes. Each chapter is identified by its `## ` heading and
replaced in the target in place: from that heading to the next `## ` heading (or
end of file). Only the managed chapters are rewritten; every other chapter is
the project's, including the per-stack `## Stack-specific skills` chapter and all
build/toolchain/convention chapters. Chapters stay interleaved in the project's
own order — each is found and replaced independently by its heading.

Heading detection is fence-aware: a `## ` line inside a ```fenced``` block is
illustrative text, not a chapter boundary, and is never matched or treated as a
boundary — matching the doctor's check_required_chapters. Without this a
consumer that quotes a managed heading inside an example fence would be
corrupted by the replace.

A heading that is absent in the target (a greenfield or legacy file with a
renamed/missing chapter) is reported and left untouched for the /init fill
(greenfield) or the /materialize migration (legacy).

This tree is source-only: not under core/ or stacks/, so materialize never
copies it into a target as runtime.

Besides the chapters, this also stamps the harness release date as CLAUDE.md's
first line (see stamp_date) — a greppable token that lands in every session's
context for downstream version attribution.

All replacements compose in memory; the target is written once, by a temp file
in its own directory and an atomic same-filesystem rename. A malformed source
or a mid-run failure therefore never leaves a half-refreshed target.

Stdlib only. Tested by test_refresh_chapters.py.
"""

import os
import re
import sys
import tempfile
from pathlib import Path

USAGE = "usage: refresh-chapters.py <claude-md> <harness-root> [version-date]"

# The harness-reserved stamp-line prefix: the upsert removes any line matching
# this, so a consumer must not author their own comment with that prefix.
STAMP_LINE = re.compile(r"^[ \t]*<!--[ \t]*harness:")


def _is_fence(line):
    return line.lstrip(" \t").startswith("```")


def chapter_titles(lines):
    """Each real (non-fenced) `## ` heading, in order."""
    titles, fence = [], False
    for line in lines:
        if _is_fence(line):
            fence = not fence
            continue
        if not fence and line.startswith("## "):
            titles.append(line)
    return titles


def heading_present(lines, title):
    """Is the title present as a real (non-fenced) heading line?"""
    fence = False
    for line in lines:
        if _is_fence(line):
            fence = not fence
            continue
        if not fence and line == title:
            return True
    return False


def extract_chapter(lines, title):
    """The chapter named title: its heading line through the line before the
    next real `## ` heading (or end of file), fence-aware. Trailing blank
    lines are trimmed so replace_chapter controls the single separating blank."""
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


def replace_chapter(lines, chapter, title):
    """The target lines with the heading-bounded chapter replaced by `chapter`.
    Assumes the title is present as a real heading. Fence-aware: the title is
    matched and the chapter boundary (next `## `) is recognized only outside
    fenced blocks."""
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


def stamp_date(lines, version_date):
    """The lines with the harness release date stamped as the first line.

    A single greppable token — `<!-- harness: <YYYY-MM-DD> -->` — lands in the
    system-prompt context of EVERY session, because CLAUDE.md is the one file
    injected into all of them. The date is the release date of the materialized
    version (single-sourced from VERSION-DATE): orderable, and a one-to-one
    stand-in for the version. Unlike a wall-clock stamp it stays stable across
    re-materialize, so the samples' faithfulness check holds. Upsert: drop any
    existing stamp line (leading whitespace tolerated, matching the doctor's
    detector), then prepend the current one — an upgrade replaces it in place
    and never duplicates or accumulates it."""
    kept = [l for l in lines if not STAMP_LINE.match(l)]
    return [f"<!-- harness: {version_date} -->"] + kept


def resolve_symlink(path):
    """The backing file of a (possibly chained) symlink, so the write-and-rename
    updates the real file and preserves the link instead of clobbering the
    symlink with a regular file."""
    path = Path(path)
    while path.is_symlink():
        link = Path(os.readlink(path))
        path = link if link.is_absolute() else path.parent / link
    return path


def atomic_write(path, text):
    """Write via a temp file in the target's own directory, then an atomic
    same-filesystem rename — never a cross-device copy that an interruption
    could leave half-written."""
    fd, tmp = tempfile.mkstemp(prefix=".claude-md.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def apply(claude_md, root, version_date=""):
    """Refresh every managed chapter, stamp the date, print the report line.

    Returns the exit code. Nothing is written until every replacement has
    composed cleanly in memory."""
    claude = Path(claude_md)
    src = Path(root) / "claude-md" / "managed-chapters.md"
    if not claude.is_file():
        print(f"refresh: no CLAUDE.md at {claude}", file=sys.stderr)
        return 1
    if not src.is_file():
        print(f"refresh: missing chapter source {src}", file=sys.stderr)
        return 1

    src_lines = src.read_text(encoding="utf-8").splitlines()
    if not src_lines or not src_lines[0].startswith("## "):
        print(f"refresh: {src} must start with a '## ' heading", file=sys.stderr)
        return 1

    claude = resolve_symlink(claude)

    # CRLF guard. Heading matching is exact, so a CRLF target (`## Memory\r`)
    # would match no managed heading and silently refresh nothing — and the
    # marketplace setup runs no doctor to catch it. Refuse loudly instead.
    # Normalizing here would either still miss the match or mix line endings
    # on write; the consumer normalizes to LF (the harness convention) and
    # re-runs.
    # read_bytes, not read_text: universal-newline translation would hide the
    # very CRLF this guard exists to refuse.
    raw = claude.read_bytes().decode("utf-8")
    if "\r" in raw:
        print(f"refresh: {claude} has CRLF line endings — normalize to LF, then re-run",
              file=sys.stderr)
        print("0 refreshed (CRLF — normalize to LF)")
        return 0

    # Pre-flight, before any write: the managed set is the source's `## `
    # headings. It must be non-empty and duplicate-free. A duplicate would
    # replace the same target chapter twice; validating here (not mid-loop)
    # means a malformed source fails loud and never half-refreshes the target.
    titles = chapter_titles(src_lines)
    if not titles:
        print(f"refresh: {src} has no '## ' chapters", file=sys.stderr)
        return 1
    seen = set()
    for title in titles:
        if title in seen:
            print(f"refresh: {src} has a duplicate '{title}' chapter", file=sys.stderr)
            return 1
        seen.add(title)

    # Apply: replace each chapter present in the target, report the absent ones.
    lines = raw.splitlines()
    refreshed, absent = 0, []
    for title in titles:
        if heading_present(lines, title):
            lines = replace_chapter(lines, extract_chapter(src_lines, title), title)
            refreshed += 1
        else:
            absent.append(title)

    # Resolve the harness release date and stamp it as CLAUDE.md's first line.
    # An explicit argument wins; otherwise the VERSION-DATE file at the
    # harness/plugin root — the same dir that holds claude-md/. So materialize
    # and init (root = harness/) and the marketplace setup (root = the plugin,
    # which bundles VERSION-DATE) all resolve it without passing it. A bare
    # direct call with no VERSION-DATE leaves the stamp untouched rather than
    # failing the refresh.
    stamp_note = ", date not stamped (no VERSION-DATE)"
    stamp_file = Path(root) / "VERSION-DATE"
    if not version_date and stamp_file.is_file():
        version_date = "".join(stamp_file.read_text(encoding="utf-8").split())
    if version_date:
        lines = stamp_date(lines, version_date)
        stamp_note = f", date {version_date} stamped"

    # Nothing replaced and nothing to stamp is a no-op: leave the target's
    # bytes (and mtime) alone.
    if refreshed or version_date:
        atomic_write(claude, "\n".join(lines) + "\n")

    if absent:
        print(f"{refreshed} refreshed, {len(absent)} absent: {' '.join(absent)}{stamp_note}")
    else:
        print(f"{refreshed} refreshed{stamp_note}")
    return 0


def main(argv):
    if len(argv) not in (3, 4):
        print(USAGE, file=sys.stderr)
        return 2
    return apply(*argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
