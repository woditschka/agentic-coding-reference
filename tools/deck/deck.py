#!/usr/bin/env python3
"""Generate the conference deck's derived files: ledger replays, the casts bundle, and the slide figures."""

import argparse
import json
import re
import sys
import textwrap
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import figures

DECK = Path(__file__).resolve().parents[2] / "docs" / "deck"

# Recorded terminal size: the largest legible type on a 16:9 demo slide.
COLS = 90
ROWS = 24
INDENT = "    "
DETAIL_LINES = 4
AUTHOR_WIDTH = 29
# Replay pacing: a real minute between records plays as one second, capped,
# plus a fixed beat so back-to-back records stay readable.
SECONDS_PER_REAL_MINUTE = 1.0
MAX_GAP = 1.5
RECORD_BEAT = 0.35
MARKER_OFFSET = 0.05

RESET = "\x1b[0m"
DIM = "\x1b[2m"
BOLD = "\x1b[1m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"

Record = dict[str, object]


def _text(record: Record, key: str) -> str:
    """Return one record field as a single line of text."""
    value = record.get(key, "")
    return " ".join(str(value).split())


def _verdict_color(verdict: str) -> str:
    """Color a verdict by how it routes: approval green, a stop red, the rest yellow."""
    if verdict in {"approved", "covered", "pass", "clear"}:
        return GREEN
    if verdict in {"changes_requested", "blocked", "fail", "concern"}:
        return RED
    return YELLOW


def _first_finding(record: Record) -> str:
    """Summarize a review's first finding as tag, location, and description."""
    findings = record.get("findings")
    if not isinstance(findings, list) or not findings:
        return ""
    first = findings[0]
    if not isinstance(first, dict):
        return str(first)
    return f"[{first.get('tag', '')}] {first.get('location', '')}: {first.get('description', '')}"


def _gate_checks(record: Record) -> str:
    """List the gate checks a build-pass record ran."""
    checks = record.get("gate_checks_run")
    return "gate: " + ", ".join(map(str, checks)) if isinstance(checks, list) else ""


DETAIL: dict[str, Callable[[Record], str]] = {
    "intake-decision": lambda r: _text(r, "request"),
    "prd-entry": lambda r: _text(r, "title"),
    "design-block": lambda r: _text(r, "architectural_fit"),
    "build-pass": _gate_checks,
    "review-feedback": _first_finding,
    "consultation-request": lambda r: _text(r, "question"),
    "consultation-response": lambda r: _text(r, "answer"),
    "grader-verdict": lambda r: _text(r, "summary"),
}

MARKERS = {
    "prd-entry": "requirements",
    "design-block": "design",
    "build-pass": "build green",
    "consultation-request": "consultation",
    "grader-verdict": "graded",
}


def marker_label(record: Record) -> str | None:
    """Name the pause point a record ends, or None when playback runs on."""
    if record.get("type") == "review-feedback":
        return "review catch" if record.get("verdict") == "changes_requested" else None
    return MARKERS.get(str(record.get("type")))


def record_lines(record: Record) -> list[str]:
    """Render one ledger record as its heading line plus wrapped detail lines."""
    stamp = str(record.get("ts", ""))[11:19]
    author = str(record.get("author", "")).ljust(AUTHOR_WIDTH)
    head = f"{DIM}{stamp}{RESET}  {GREEN}{author}{RESET}{BOLD}{record.get('type', '')}{RESET}"
    verdict = record.get("verdict")
    if isinstance(verdict, str):
        head += f"  {_verdict_color(verdict)}{verdict}{RESET}"
    render = DETAIL.get(str(record.get("type")))
    detail = render(record) if render else ""
    wrapped = textwrap.wrap(detail, width=COLS - 2 * len(INDENT))
    if len(wrapped) > DETAIL_LINES:
        wrapped = [*wrapped[: DETAIL_LINES - 1], wrapped[DETAIL_LINES - 1] + " …"]
    return [head, *(f"{INDENT}{line}" for line in wrapped)]


def _stamp(record: Record) -> datetime | None:
    """Parse a record's ISO timestamp, or None when it has none."""
    try:
        return datetime.fromisoformat(str(record["ts"]))
    except (KeyError, ValueError):
        return None


def _gap(previous: Record | None, record: Record) -> float:
    """Return the compressed playback gap between two consecutive records."""
    before = _stamp(previous) if previous else None
    after = _stamp(record)
    if before is None or after is None:
        return RECORD_BEAT
    real_minutes = max((after - before).total_seconds(), 0.0) / 60
    return RECORD_BEAT + min(real_minutes * SECONDS_PER_REAL_MINUTE, MAX_GAP)


def ledger_cast(records: list[Record], source: str) -> str:
    """Render a handoff ledger as an asciicast v2 replay with a marker per pipeline stage."""
    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "title": f"Ledger replay: {source}",
    }
    intro = (
        f"{DIM}# Replay of the committed handoff ledger\r\n# {source}{RESET}\r\n\r\n"
    )
    events: list[list[object]] = [[0.0, "o", intro]]
    clock = RECORD_BEAT
    previous: Record | None = None
    for record in records:
        clock = round(clock + _gap(previous, record), 3)
        events.append([clock, "o", "\r\n".join(record_lines(record)) + "\r\n"])
        label = marker_label(record)
        if label:
            events.append([round(clock + MARKER_OFFSET, 3), "m", label])
        previous = record
    closing = f"\r\n{DIM}# ledger closed: {len(records)} records{RESET}\r\n"
    events.append([round(clock + RECORD_BEAT, 3), "o", closing])
    lines = [
        json.dumps(header),
        *(json.dumps(event, ensure_ascii=False) for event in events),
    ]
    return "\n".join(lines) + "\n"


def read_ledger(run_dir: Path) -> list[Record]:
    """Read a committed run folder's handoff.jsonl, one record per line."""
    text = (run_dir / "handoff.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _script_safe(text: str) -> str:
    """Keep a cast's text from closing the bundle's script element early."""
    # Only "</script" ends a script element; "<\/" reads the same inside the
    # JS strings, regex literals, and JSON where the sequence can occur.
    return re.sub(r"</(script)", r"<\\/\1", text, flags=re.IGNORECASE)


def casts_js(casts: dict[str, str]) -> str:
    """Wrap every cast's text in one script that works from file:// without fetch."""
    body = json.dumps(dict(sorted(casts.items())), ensure_ascii=False, indent=1)
    return (
        "// Generated by tools/deck/deck.py build; never hand-edit.\n"
        f"window.DECK_CASTS = {_script_safe(body)};\n"
    )


def derived_files(deck: Path) -> dict[Path, str]:
    """Compute every generated file from its sources: the casts bundle under the deck, the slide figures beside it under images."""
    casts = {
        path.stem: path.read_text(encoding="utf-8")
        for path in sorted((deck / "casts").glob("*.cast"))
    }
    return {
        deck / "casts" / "casts.js": casts_js(casts),
        **figures.derived_figures(deck.parent / "images"),
    }


def build(deck: Path, *, check: bool) -> list[Path]:
    """Write the stale generated files, or with check=True only list them."""
    derived = derived_files(deck)
    stale = [
        path
        for path, text in derived.items()
        if not path.exists() or path.read_text(encoding="utf-8") != text
    ]
    if not check:
        for path in stale:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(derived[path], encoding="utf-8")
    return stale


def main(argv: list[str] | None = None) -> int:
    """Dispatch the ledger-cast and build subcommands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    replay = commands.add_parser(
        "ledger-cast", help="render a committed run's ledger as a cast"
    )
    replay.add_argument("run_dir", type=Path)
    replay.add_argument("out", type=Path)
    make = commands.add_parser(
        "build", help="regenerate casts.js and the slide figures' draw.io sources"
    )
    make.add_argument(
        "--check", action="store_true", help="report stale files, write nothing"
    )
    args = parser.parse_args(argv)
    if args.command == "ledger-cast":
        source = args.run_dir.resolve().relative_to(DECK.parents[1]).as_posix()
        args.out.write_text(
            ledger_cast(read_ledger(args.run_dir), source), encoding="utf-8"
        )
        return 0
    stale = build(DECK, check=args.check)
    for path in stale:
        verb = "stale" if args.check else "wrote"
        print(f"{verb}: {path.relative_to(DECK.parents[1])}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
