#!/usr/bin/env python3
"""backlog.py — the outer loop's candidate set: which requirements are open.

  scripts/backlog.py candidates [--json] [--no-connector]
  scripts/backlog.py claim REQ-XX-NNN

The deterministic half of the `next` skill. `candidates` computes the set the
skill ranks and annotates: every REQ id in docs/prd.md minus the ids git
history records as delivered, the ids the PRD's Non-Goals section declines,
and the ids its Superseded list retires. Git history is the authority for
"done": a REQ named in a commit subject or body is delivered, whatever the
PRD says beside it.

The project-owned connector, scripts/backlog.sh, adds what git cannot know:
who holds which requirement, and the team's order. Its `backlog_items`
function prints one tab-separated row per open board item — `REQ-ID`, owner,
title — in rank order; an empty REQ-ID marks a board item the PRD does not
carry yet (intake work), and an empty owner marks an unclaimed one. Absent
connector or absent function (the shipped skeleton) is the solo default and
the report says so on its first line; zero rows is a bound, empty board. A connector that exits non-zero fails this command:
offering a requirement someone already holds is the defect the connector
exists to prevent, so a broken read never degrades silently to solo.
`--no-connector` is the explicit override.

`claim` runs the connector's `backlog_claim` with the confirmed pick, so the
next person's `candidates` already sees the claim. A failed claim exits
non-zero with the connector's message and changes nothing else: the pick is
already recorded in the ledger, and the human claims by hand.

Runs from the project root (or --root). Stdlib only.
"""

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

PRD_PATH = "docs/prd.md"
CONNECTOR_PATH = "scripts/backlog.sh"

# Extraction is deliberately wider than the schema's three-digit form so a
# drifted id (REQ-X-1) surfaces in the report instead of vanishing; a claim
# is passed to the shell, so it is held to the exact schema shape.
REQ_RE = re.compile(r"REQ-[A-Z]+-[0-9]+")
REQ_STRICT_RE = re.compile(r"^REQ-[A-Z]+-[0-9]{3}$")
TITLE_WIDTH = 80

ConnectorMode = Literal["none", "unbound", "bound", "skipped"]

# One bash program per verb. `_` fills $0; $1 is the connector path, $2 the
# claimed id — never interpolated into the program text, so a hostile path or
# id cannot become shell syntax. The two probe failures, a connector that
# fails to source and a verb that is not defined, exit 3 and 4 and print a
# sentinel to stderr; the engine requires both, so a verb whose own status
# happens to be 3 or 4 is reported as the verb's failure, never as unbound.
_SOURCE_FAILED = "__backlog_source_failed__"
_NO_FUNCTION = "__backlog_no_function__"
_ITEMS_PROGRAM = (
    'set -u; . "$1" >/dev/null || { echo __backlog_source_failed__ >&2; exit 3; }; '
    "declare -F backlog_items >/dev/null 2>&1 "
    "|| { echo __backlog_no_function__ >&2; exit 4; }; backlog_items"
)
_CLAIM_PROGRAM = (
    'set -u; . "$1" >/dev/null || { echo __backlog_source_failed__ >&2; exit 3; }; '
    "declare -F backlog_claim >/dev/null 2>&1 "
    '|| { echo __backlog_no_function__ >&2; exit 4; }; backlog_claim "$2"'
)

# Connector output and the board's text are untrusted: control bytes and
# escape sequences never reach the terminal or a message. Tab and newline
# survive, since they carry the row shape.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")


def _scrub(text: str) -> str:
    return _CONTROL_RE.sub("", text)


class BacklogError(Exception):
    """A failure the command reports and exits on: bad input, broken connector."""


@dataclass(frozen=True)
class BoardItem:
    """One row the connector printed: rank is its 1-based line position."""

    rank: int
    req_id: str | None
    owner: str | None
    title: str


@dataclass(frozen=True)
class Candidate:
    """One requirement in the report, with what the board says about it."""

    req_id: str
    title: str
    rank: int | None = None
    owner: str | None = None
    board_title: str | None = None


@dataclass(frozen=True)
class Report:
    connector: ConnectorMode
    board_items: int
    open: list[Candidate] = field(default_factory=list)
    claimed: list[Candidate] = field(default_factory=list)
    needs_intake: list[BoardItem] = field(default_factory=list)
    stale: list[Candidate] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    non_goal: list[str] = field(default_factory=list)
    superseded: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Prd:
    """The ids docs/prd.md carries, split by where they appear."""

    requirements: dict[str, str]  # id -> title hint, in document order
    non_goal: list[str]
    superseded: list[str]


# --- docs/prd.md ---------------------------------------------------------


def _sections(text: str) -> dict[str, str]:
    """Map each '## ' heading to its body text (up to the next '## ')."""
    sections: dict[str, str] = {}
    current: str | None = None
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(lines)
            current = line[3:].strip()
            lines = []
        else:
            lines.append(line)
    if current is not None:
        sections[current] = "\n".join(lines)
    return sections


def _title_hint(line: str, req_id: str) -> str:
    """The line that carries the tag, minus the tag and markdown furniture."""
    text = line.replace(f"[{req_id}]", " ").replace(req_id, " ")
    text = re.sub(r"[`*_#|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:—")
    if len(text) > TITLE_WIDTH:
        text = text[: TITLE_WIDTH - 1].rstrip() + "…"
    return text


def parse_prd(text: str) -> Prd:
    """Every REQ id in the PRD in first-appearance order with a title hint;
    the first id per Non-Goals line and per Superseded line. The rest of a
    line names a successor or a related requirement, which stays a candidate."""
    requirements: dict[str, str] = {}
    for line in text.splitlines():
        for req_id in REQ_RE.findall(line):
            if req_id not in requirements:
                requirements[req_id] = _title_hint(line, req_id)
    sections = _sections(text)
    return Prd(
        requirements,
        _first_ids(sections.get("Non-Goals", "")),
        _first_ids(sections.get("Superseded", "")),
    )


def _first_ids(section: str) -> list[str]:
    ids: list[str] = []
    for line in section.splitlines():
        m = REQ_RE.search(line)
        if m and m.group(0) not in ids:
            ids.append(m.group(0))
    return ids


def _unique(ids: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for i in ids:
        if i not in seen:
            seen.append(i)
    return seen


# --- git history ---------------------------------------------------------


def delivered_ids(root: Path) -> set[str]:
    """REQ ids named in any commit subject or body, case-folded to upper.
    An unborn HEAD delivers nothing; an unusable repo fails the command."""
    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "--quiet", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        inside = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        if inside.returncode != 0:
            raise BacklogError(
                f"not a git repository: {root} — git history is the authority "
                "for delivered requirements"
            )
        return set()
    log = subprocess.run(
        ["git", "-C", str(root), "log", "--pretty=%s%n%b"],
        capture_output=True,
        text=True,
        check=False,
    )
    if log.returncode != 0:
        raise BacklogError(f"git log failed: {log.stderr.strip()}")
    return {m.upper() for m in re.findall(REQ_RE.pattern, log.stdout, re.IGNORECASE)}


# --- the connector -------------------------------------------------------


def _run_connector(
    program: str, connector: Path, root: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    """Run one verb program with the project root as its working directory,
    so a binding that reads a project-relative file behaves the same under
    --root as it does in place."""
    return subprocess.run(
        ["bash", "-c", program, "_", str(connector), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(root),
    )


def _probe(proc: subprocess.CompletedProcess[str]) -> str | None:
    """Which probe failed, when the exit code and its sentinel agree."""
    if proc.returncode == 3 and _SOURCE_FAILED in proc.stderr:
        return "source-failed"
    if proc.returncode == 4 and _NO_FUNCTION in proc.stderr:
        return "no-function"
    return None


def _detail(proc: subprocess.CompletedProcess[str]) -> str:
    text = _scrub(proc.stderr).replace(_SOURCE_FAILED, "").replace(_NO_FUNCTION, "")
    return text.strip() or _scrub(proc.stdout).strip() or f"exit {proc.returncode}"


def _relay_stderr(proc: subprocess.CompletedProcess[str]) -> None:
    """A verb that succeeded may still warn; the warning reaches the terminal."""
    text = _scrub(proc.stderr).strip()
    if text:
        print(text, file=sys.stderr)


def parse_items(text: str) -> list[BoardItem]:
    """Rows are `REQ-ID<TAB>owner<TAB>title`. Blank lines and lines whose first
    character is `#` are skipped; a title keeps any further tabs. Control
    bytes are stripped before the split, so a title can never forge a row.
    A present id must be a REQ id — a board that prints ticket keys in that
    column is a binding error, reported, never silently treated as intake.
    Two rows naming one id: the first, higher-ranked row counts."""
    items: list[BoardItem] = []
    for raw in _scrub(text).split("\n"):
        line = raw.rstrip("\r")
        if not line.strip() or line.startswith("#"):
            continue
        cells = (line.split("\t", 2) + ["", "", ""])[:3]
        req_id, owner, title = (c.strip() for c in cells)
        req_id = req_id.upper()
        if req_id and not REQ_RE.fullmatch(req_id):
            raise BacklogError(
                f"connector row {len(items) + 1}: first column is not a REQ id "
                f"({req_id!r}); print the requirement id, or leave it empty for "
                "a board item the PRD does not carry yet"
            )
        items.append(BoardItem(len(items) + 1, req_id or None, owner or None, title))
    return items


def board_items(connector: Path, root: Path) -> tuple[ConnectorMode, list[BoardItem]]:
    """Run the connector's backlog_items. An absent file is `none` and a file
    that defines no backlog_items is `unbound`, the shipped solo default; any
    other non-zero exit is a failure the caller reports."""
    if not connector.is_file():
        return "none", []
    proc = _run_connector(_ITEMS_PROGRAM, connector, root)
    probe = _probe(proc)
    if probe == "no-function":
        return "unbound", []
    if probe == "source-failed":
        raise BacklogError(f"{connector} failed to source: {_detail(proc)}")
    if proc.returncode != 0:
        raise BacklogError(
            f"{connector} backlog_items failed ({_detail(proc)}); the board is "
            "unreadable, so no candidate set is offered — fix the connector, "
            "or pass --no-connector to rank from git alone"
        )
    _relay_stderr(proc)
    return "bound", parse_items(proc.stdout)


# --- the report ----------------------------------------------------------


def build_report(
    prd: Prd, done: set[str], connector: ConnectorMode, items: list[BoardItem]
) -> Report:
    """Fold the three sources into one report. Board order ranks the open
    set; a requirement the board omits follows in PRD order; a board item
    whose requirement the repo already delivered or declined is stale."""
    non_goal = [i for i in prd.non_goal if i not in done]
    superseded = [i for i in prd.superseded if i not in done and i not in non_goal]
    closed = done | set(non_goal) | set(superseded)
    by_id: dict[str, BoardItem] = {}
    for row in items:
        if row.req_id is not None and row.req_id not in by_id:
            by_id[row.req_id] = row

    open_: list[Candidate] = []
    claimed: list[Candidate] = []
    stale: list[Candidate] = []
    for req_id, title in prd.requirements.items():
        if req_id in closed:
            if req_id in by_id:
                stale.append(_candidate(req_id, title, by_id[req_id]))
            continue
        item = by_id.get(req_id)
        cand = _candidate(req_id, title, item)
        if item is not None and item.owner is not None:
            claimed.append(cand)
        else:
            open_.append(cand)
    # Board items naming an id the PRD never carried: stale too — the board
    # points at a requirement that does not exist.
    for req_id, item in by_id.items():
        if req_id not in prd.requirements:
            stale.append(_candidate(req_id, "", item))
    open_.sort(key=lambda c: (c.rank is None, c.rank or 0))
    claimed.sort(key=lambda c: (c.rank is None, c.rank or 0))
    return Report(
        connector=connector,
        board_items=len(items),
        open=open_,
        claimed=claimed,
        needs_intake=[i for i in items if i.req_id is None],
        stale=stale,
        done=sorted(i for i in prd.requirements if i in done),
        non_goal=non_goal,
        superseded=superseded,
    )


def _candidate(req_id: str, title: str, item: BoardItem | None) -> Candidate:
    if item is None:
        return Candidate(req_id, title)
    return Candidate(req_id, title, item.rank, item.owner, item.title or None)


def render(report: Report, connector: Path) -> str:
    """The terminal form the `next` skill reads."""
    out: list[str] = []
    if report.connector == "bound":
        out.append(f"connector: {connector} ({report.board_items} board items)")
    elif report.connector == "skipped":
        out.append("connector: skipped (--no-connector); ranking from git alone")
    elif report.connector == "unbound":
        out.append(f"connector: {connector} unbound (solo); ranking from git alone")
    else:
        out.append("connector: none (solo); ranking from git alone")
    out.append(f"open ({len(report.open)}):")
    for c in report.open:
        rank = f"{c.rank:>3}" if c.rank is not None else "  -"
        note = (
            ""
            if c.rank is not None or report.board_items == 0
            else "  (not on the board)"
        )
        out.append(f"{rank}  {c.req_id}  {c.title}{note}")
    if report.claimed:
        out.append(f"claimed ({len(report.claimed)}):")
        for c in report.claimed:
            out.append(f"     {c.req_id}  {c.owner}  {c.title}")
    if report.needs_intake:
        out.append(
            f"needs intake ({len(report.needs_intake)}): board items with no REQ id"
        )
        for i in report.needs_intake:
            owner = f"  ({i.owner})" if i.owner else ""
            out.append(f"{i.rank:>3}  {i.title}{owner}")
    if report.stale:
        out.append(
            f"stale on the board ({len(report.stale)}): the repo records these as closed or unknown"
        )
        for c in report.stale:
            state = _state(c.req_id, report)
            out.append(f"     {c.req_id}  {state}")
    out.append(
        f"excluded: done {len(report.done)}, "
        f"non-goal {_counted(report.non_goal)}, "
        f"superseded {_counted(report.superseded)}"
    )
    return "\n".join(out) + "\n"


def _counted(ids: list[str]) -> str:
    """A count, and the ids behind it when there are any: an exclusion the
    PRD's prose caused is visible, never a silent number."""
    return f"{len(ids)} ({', '.join(ids)})" if ids else "0"


def _state(req_id: str, report: Report) -> str:
    if req_id in report.done:
        return "delivered in git history"
    if req_id in report.non_goal:
        return "declined in the PRD's Non-Goals"
    if req_id in report.superseded:
        return "retired in the PRD's Superseded list"
    return "not in the PRD"


# --- commands ------------------------------------------------------------


def cmd_candidates(
    root: Path, prd_path: Path, connector: Path, use_connector: bool, as_json: bool
) -> int:
    if not prd_path.is_file():
        raise BacklogError(f"{prd_path} not found — the PRD is the candidate source")
    prd = parse_prd(prd_path.read_text(encoding="utf-8"))
    done = delivered_ids(root)
    mode: ConnectorMode
    if use_connector:
        mode, items = board_items(connector, root)
    else:
        mode, items = "skipped", []
    report = build_report(prd, done, mode, items)
    if as_json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(render(report, connector), end="")
    return 0


def cmd_claim(connector: Path, req_id: str, root: Path) -> int:
    req_id = req_id.upper()
    if not REQ_STRICT_RE.fullmatch(req_id):
        raise BacklogError(f"not a requirement id: {req_id!r} (expected REQ-XX-NNN)")
    if not connector.is_file():
        print(f"claim {req_id}: no connector at {connector}; record the claim by hand")
        return 0
    proc = _run_connector(_CLAIM_PROGRAM, connector, root, req_id)
    probe = _probe(proc)
    if probe == "no-function":
        print(
            f"claim {req_id}: {connector} defines no backlog_claim; record the claim by hand"
        )
        return 0
    if probe == "source-failed":
        raise BacklogError(f"{connector} failed to source: {_detail(proc)}")
    if proc.returncode != 0:
        raise BacklogError(
            f"claim {req_id} failed ({_detail(proc)}); the pick stays recorded — "
            "claim it on the board by hand"
        )
    _relay_stderr(proc)
    text = _scrub(proc.stdout).strip()
    # The engine reports what the connector answered, never a recording it
    # cannot see: a silent success is confirmed on the board.
    print(
        f"claim {req_id}: backlog_claim accepted it"
        + (
            f" — {text}"
            if text
            else "; it said nothing, so confirm the move on the board"
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--root",
        default=".",
        help="project root holding docs/prd.md, scripts/backlog.sh, and the git history (default: cwd)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    cands = sub.add_parser(
        "candidates", help="the open requirements, board order first"
    )
    cands.add_argument("--json", action="store_true", help="emit the report as JSON")
    cands.add_argument(
        "--no-connector",
        action="store_true",
        help="rank from git alone, ignoring scripts/backlog.sh (an explicit override)",
    )
    claim = sub.add_parser("claim", help="notify the board that the pick is taken")
    claim.add_argument("req_id")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    connector = root / CONNECTOR_PATH
    try:
        if args.cmd == "candidates":
            return cmd_candidates(
                root, root / PRD_PATH, connector, not args.no_connector, args.json
            )
        return cmd_claim(connector, args.req_id, root)
    except BacklogError as exc:
        print(f"backlog.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
