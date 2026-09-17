#!/usr/bin/env python3
"""Compute the outer loop's candidate set: the open requirements, in the board's order.

  scripts/backlog.py candidates [--json] [--no-connector]
  scripts/backlog.py claim REQ-XX-NNN

The deterministic half of the `next` skill: every requirement id in the PRD
minus the ids git history delivered, the Non-Goals declined, and the Superseded
list retired, folded with what the project-owned connector prints. Runs from
the project root or --root; stdlib only.
"""

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, NamedTuple, assert_never

PRD_PATH = "docs/prd.md"
CONNECTOR_PATH = "scripts/backlog.sh"

# Extraction is wider than the schema's three-digit form so a drifted id
# surfaces in the report instead of vanishing; a claim reaches the shell, so
# it is held to the exact shape.
REQ_RE = re.compile(r"REQ-[A-Z]+-[0-9]+")
REQ_STRICT_RE = re.compile(r"^REQ-[A-Z]+-[0-9]{3}$")
TITLE_WIDTH = 80
ROW_CELLS = 3

ConnectorMode = Literal["none", "unbound", "bound", "skipped"]
ProbeFailure = Literal["source-failed", "no-function"]

# One bash program per verb. `_` fills $0; $1 is the connector path and $2 the
# claimed id, never interpolated into the program text, so a hostile path or
# id cannot become shell syntax. Each probe failure exits with its own status
# and prints a sentinel; the engine requires both, so a verb whose own status
# happens to match is reported as the verb's failure, never as unbound.
SOURCE_FAILED_STATUS = 3
NO_FUNCTION_STATUS = 4
_SOURCE_FAILED = "__backlog_source_failed__"
_NO_FUNCTION = "__backlog_no_function__"


def _verb_program(verb: str, call: str) -> str:
    return (
        f'set -u; . "$1" >/dev/null || {{ echo {_SOURCE_FAILED} >&2; exit {SOURCE_FAILED_STATUS}; }}; '
        f"declare -F {verb} >/dev/null 2>&1 "
        f"|| {{ echo {_NO_FUNCTION} >&2; exit {NO_FUNCTION_STATUS}; }}; {call}"
    )


_ITEMS_PROGRAM = _verb_program("backlog_items", "backlog_items")
_CLAIM_PROGRAM = _verb_program("backlog_claim", 'backlog_claim "$2"')

# Connector output and the board's text are untrusted: control bytes and
# escape sequences never reach the terminal or a message. Tab and newline
# survive, since they carry the row shape.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u2028\u2029]")


def _scrub(text: str) -> str:
    return _CONTROL_RE.sub("", text)


def warn(message: str) -> None:
    """Write one message to stderr."""
    print(message, file=sys.stderr)


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
    """The candidate set and every exclusion behind it, as the `next` skill reads them."""

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


class Board(NamedTuple):
    """What the connector answered: its binding state and the rows it printed."""

    mode: ConnectorMode
    items: list[BoardItem]


def _sections(text: str) -> dict[str, str]:
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
    text = line.replace(f"[{req_id}]", " ").replace(req_id, " ")
    text = re.sub(r"[`*_#|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -:—")
    if len(text) > TITLE_WIDTH:
        text = text[: TITLE_WIDTH - 1].rstrip() + "…"
    return text


def parse_prd(text: str) -> Prd:
    """Collect every requirement id with its title hint, and the ids the PRD declines or retires."""
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
    # The first id per line; the rest of a line names a successor or a related
    # requirement, which stays a candidate.
    ids: list[str] = []
    for line in section.splitlines():
        match = REQ_RE.search(line)
        if match and match.group(0) not in ids:
            ids.append(match.group(0))
    return ids


def delivered_ids(root: Path) -> set[str]:
    """Return the ids named in any commit subject or body; an unborn HEAD delivers nothing."""
    if _git(root, "rev-parse", "--verify", "--quiet", "HEAD").returncode != 0:
        if _git(root, "rev-parse", "--git-dir").returncode != 0:
            raise BacklogError(
                f"not a git repository: {root} — git history is the authority "
                "for delivered requirements"
            )
        return set()
    log = _git(root, "log", "--pretty=%s%n%b")
    if log.returncode != 0:
        raise BacklogError(f"git log failed: {log.stderr.strip()}")
    return {m.upper() for m in re.findall(REQ_RE.pattern, log.stdout, re.IGNORECASE)}


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _run_connector(
    program: str, connector: Path, root: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    # The project root is the working directory, so a binding that reads a
    # project-relative file behaves the same under --root as in place.
    return subprocess.run(
        ["bash", "-c", program, "_", str(connector), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(root),
    )


def _probe_failure(proc: subprocess.CompletedProcess[str]) -> ProbeFailure | None:
    if proc.returncode == SOURCE_FAILED_STATUS and _SOURCE_FAILED in proc.stderr:
        return "source-failed"
    if proc.returncode == NO_FUNCTION_STATUS and _NO_FUNCTION in proc.stderr:
        return "no-function"
    return None


def _detail(proc: subprocess.CompletedProcess[str]) -> str:
    text = _scrub(proc.stderr).replace(_SOURCE_FAILED, "").replace(_NO_FUNCTION, "")
    return text.strip() or _scrub(proc.stdout).strip() or f"exit {proc.returncode}"


def _relay_stderr(proc: subprocess.CompletedProcess[str]) -> None:
    # A verb that succeeded may still warn.
    text = _scrub(proc.stderr).strip()
    if text:
        warn(text)


def parse_items(text: str) -> list[BoardItem]:
    """Parse the connector's `REQ-ID<TAB>owner<TAB>title` rows into board items."""
    # Control bytes are stripped before the split, so a title can never forge
    # a row. A present id must be a REQ id: a board that prints ticket keys in
    # that column is a binding error, never silently intake work.
    items: list[BoardItem] = []
    for raw in _scrub(text).split("\n"):
        line = raw.rstrip("\r")
        if not line.strip() or line.startswith("#"):
            continue
        req_id, owner, title = _cells(line)
        req_id = req_id.upper()
        if req_id and not REQ_RE.fullmatch(req_id):
            raise BacklogError(
                f"connector row {len(items) + 1}: first column is not a REQ id "
                f"({req_id!r}); print the requirement id, or leave it empty for "
                "a board item the PRD does not carry yet"
            )
        items.append(BoardItem(len(items) + 1, req_id or None, owner or None, title))
    return items


def _cells(line: str) -> tuple[str, str, str]:
    # A title keeps any further tabs.
    cells = line.split("\t", ROW_CELLS - 1)
    cells += [""] * (ROW_CELLS - len(cells))
    req_id, owner, title = (cell.strip() for cell in cells)
    return req_id, owner, title


def board_items(connector: Path, root: Path) -> Board:
    """Run the connector's backlog_items; an absent file or function is the solo default."""
    if not connector.is_file():
        return Board("none", [])
    proc = _run_connector(_ITEMS_PROGRAM, connector, root)
    failure = _probe_failure(proc)
    if failure == "no-function":
        return Board("unbound", [])
    if failure == "source-failed":
        raise BacklogError(f"{connector} failed to source: {_detail(proc)}")
    if proc.returncode != 0:
        raise BacklogError(
            f"{connector} backlog_items failed ({_detail(proc)}); the board is "
            "unreadable, so no candidate set is offered — fix the connector, "
            "or pass --no-connector to rank from git alone"
        )
    _relay_stderr(proc)
    return Board("bound", parse_items(proc.stdout))


def build_report(prd: Prd, done: set[str], board: Board) -> Report:
    """Fold the PRD, the delivered ids, and the board into one report."""
    # Board order ranks the open set; a requirement the board omits follows in
    # PRD order; a board item whose requirement is closed or unknown is stale.
    non_goal = [i for i in prd.non_goal if i not in done]
    superseded = [i for i in prd.superseded if i not in done and i not in non_goal]
    closed = done | set(non_goal) | set(superseded)
    by_id = _first_row_per_id(board.items)
    open_: list[Candidate] = []
    claimed: list[Candidate] = []
    stale: list[Candidate] = []
    for req_id, title in prd.requirements.items():
        item = by_id.get(req_id)
        if req_id in closed:
            if item is not None:
                stale.append(_candidate(req_id, title, item))
        elif item is not None and item.owner is not None:
            claimed.append(_candidate(req_id, title, item))
        else:
            open_.append(_candidate(req_id, title, item))
    stale.extend(
        _candidate(req_id, "", item)
        for req_id, item in by_id.items()
        if req_id not in prd.requirements
    )
    return Report(
        connector=board.mode,
        board_items=len(board.items),
        open=sorted(open_, key=_board_order),
        claimed=sorted(claimed, key=_board_order),
        needs_intake=[i for i in board.items if i.req_id is None],
        stale=stale,
        done=sorted(i for i in prd.requirements if i in done),
        non_goal=non_goal,
        superseded=superseded,
    )


def _first_row_per_id(items: Sequence[BoardItem]) -> dict[str, BoardItem]:
    by_id: dict[str, BoardItem] = {}
    for row in items:
        if row.req_id is not None and row.req_id not in by_id:
            by_id[row.req_id] = row
    return by_id


def _board_order(candidate: Candidate) -> tuple[bool, int]:
    return candidate.rank is None, candidate.rank or 0


def _candidate(req_id: str, title: str, item: BoardItem | None) -> Candidate:
    if item is None:
        return Candidate(req_id, title)
    return Candidate(req_id, title, item.rank, item.owner, item.title or None)


def render(report: Report, connector: Path) -> str:
    """Render the terminal form the `next` skill reads."""
    lines = [_connector_line(report, connector), f"open ({len(report.open)}):"]
    lines.extend(_open_line(candidate, report) for candidate in report.open)
    if report.claimed:
        lines.append(f"claimed ({len(report.claimed)}):")
        lines.extend(f"     {c.req_id}  {c.owner}  {c.title}" for c in report.claimed)
    if report.needs_intake:
        lines.append(
            f"needs intake ({len(report.needs_intake)}): board items with no REQ id"
        )
        lines.extend(_intake_line(item) for item in report.needs_intake)
    if report.stale:
        lines.append(
            f"stale on the board ({len(report.stale)}): the repo records these as closed or unknown"
        )
        lines.extend(
            f"     {c.req_id}  {_state(c.req_id, report)}" for c in report.stale
        )
    lines.append(
        f"excluded: done {len(report.done)}, "
        f"non-goal {_counted(report.non_goal)}, "
        f"superseded {_counted(report.superseded)}"
    )
    return "\n".join(lines) + "\n"


def _connector_line(report: Report, connector: Path) -> str:
    match report.connector:
        case "bound":
            return f"connector: {connector} ({report.board_items} board items)"
        case "skipped":
            return "connector: skipped (--no-connector); ranking from git alone"
        case "unbound":
            return f"connector: {connector} unbound (solo); ranking from git alone"
        case "none":
            return "connector: none (solo); ranking from git alone"
        case _:
            assert_never(report.connector)


def _open_line(candidate: Candidate, report: Report) -> str:
    rank = f"{candidate.rank:>3}" if candidate.rank is not None else "  -"
    note = (
        ""
        if candidate.rank is not None or report.board_items == 0
        else "  (not on the board)"
    )
    return f"{rank}  {candidate.req_id}  {candidate.title}{note}"


def _intake_line(item: BoardItem) -> str:
    owner = f"  ({item.owner})" if item.owner else ""
    return f"{item.rank:>3}  {item.title}{owner}"


def _counted(ids: list[str]) -> str:
    # The ids behind a count stay visible: an exclusion the PRD's prose caused
    # is never a silent number.
    return f"{len(ids)} ({', '.join(ids)})" if ids else "0"


def _state(req_id: str, report: Report) -> str:
    if req_id in report.done:
        return "delivered in git history"
    if req_id in report.non_goal:
        return "declined in the PRD's Non-Goals"
    if req_id in report.superseded:
        return "retired in the PRD's Superseded list"
    return "not in the PRD"


def cmd_candidates(root: Path, *, use_connector: bool, as_json: bool) -> int:
    """Print the candidate report for the project at root."""
    prd_path = root / PRD_PATH
    connector = root / CONNECTOR_PATH
    if not prd_path.is_file():
        raise BacklogError(f"{prd_path} not found — the PRD is the candidate source")
    prd = parse_prd(prd_path.read_text(encoding="utf-8"))
    done = delivered_ids(root)
    board = board_items(connector, root) if use_connector else Board("skipped", [])
    report = build_report(prd, done, board)
    if as_json:
        print(json.dumps(asdict(report), indent=2))
    else:
        print(render(report, connector), end="")
    return 0


def cmd_claim(root: Path, req_id: str) -> int:
    """Tell the connector the confirmed pick is taken, and print what it answered."""
    connector = root / CONNECTOR_PATH
    req_id = req_id.upper()
    if not REQ_STRICT_RE.fullmatch(req_id):
        raise BacklogError(f"not a requirement id: {req_id!r} (expected REQ-XX-NNN)")
    if not connector.is_file():
        print(f"claim {req_id}: no connector at {connector}; record the claim by hand")
        return 0
    proc = _run_connector(_CLAIM_PROGRAM, connector, root, req_id)
    failure = _probe_failure(proc)
    if failure == "no-function":
        print(
            f"claim {req_id}: {connector} defines no backlog_claim; record the claim by hand"
        )
        return 0
    if failure == "source-failed":
        raise BacklogError(f"{connector} failed to source: {_detail(proc)}")
    if proc.returncode != 0:
        raise BacklogError(
            f"claim {req_id} failed ({_detail(proc)}); the pick stays recorded — "
            "claim it on the board by hand"
        )
    _relay_stderr(proc)
    print(f"claim {req_id}: backlog_claim accepted it{_claim_answer(proc)}")
    return 0


def _claim_answer(proc: subprocess.CompletedProcess[str]) -> str:
    # The engine reports what the connector answered, never a recording it
    # cannot see: a silent success is confirmed on the board.
    text = _scrub(proc.stdout).strip()
    if text:
        return f" — {text}"
    return "; it said nothing, so confirm the move on the board"


def main(argv: list[str] | None = None) -> int:
    """Run the backlog from the command line and return its exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--root",
        default=".",
        help="project root holding docs/prd.md, scripts/backlog.sh, and the git history (default: cwd)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    candidates = sub.add_parser(
        "candidates", help="the open requirements, board order first"
    )
    candidates.add_argument(
        "--json", action="store_true", help="emit the report as JSON"
    )
    candidates.add_argument(
        "--no-connector",
        action="store_true",
        help="rank from git alone, ignoring scripts/backlog.sh (an explicit override)",
    )
    claim = sub.add_parser("claim", help="notify the board that the pick is taken")
    claim.add_argument("req_id")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        if args.cmd == "candidates":
            return cmd_candidates(
                root, use_connector=not args.no_connector, as_json=args.json
            )
        return cmd_claim(root, args.req_id)
    except BacklogError as exc:
        warn(f"backlog.py: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
