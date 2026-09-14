"""Audit the autofix lane: re-validate the open autofix records and find design-doc edits no record covers.

A leaf over handoff.ledger, handoff.records, handoff.non_goals, and handoff.repository.
"""

import re
from collections.abc import Sequence
from typing import NamedTuple, TypeAlias

from .ledger import Entry
from .non_goals import NG_ROW_RE
from .records import (
    ConsultationResponse,
    DesignBlock,
    DesignDocAutofix,
    HandoffRecord,
    PrdAutofix,
    PrdEntry,
)
from .repository import ADR_INDEX, PRD_PATH, Repository
from .timestamps import seconds_of

AutofixRecord: TypeAlias = DesignDocAutofix | PrdAutofix

DESIGN_DOC_PATH_RE = re.compile(r"^docs/(?:system-design\.md|adr/[^/]+\.md)$")
AUTOFIX_LINE_CAP = 5
AUTOFIX_CHAR_CAP = 200
AUTOFIX_CATEGORIES = ("writing-standards", "structural")
_REQ_TOKEN_RE = re.compile(r"REQ-[A-Z]+-\d{3}")
_ANCHOR_ID_RE = re.compile(r'<a id="([^"]*)"')
_LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")
_NON_GOAL_ADR = re.compile(r"^docs/adr/[^/]*-non-goal-[^/]*\.md$")
UNCOVERED_MESSAGE = (
    "uncommitted change with no covering design-doc-autofix, design-block, "
    "consultation-response, or scope-overriding prd-entry record since the last commit"
)


class DesignDocAudit(NamedTuple):
    """The dirty design-doc paths no record covers, and the note the clean report prints."""

    uncovered: tuple[str, ...]
    note: str


class AutofixAudit(NamedTuple):
    """The audit's findings, the count of records it validated, and the worktree note when git could be read."""

    failures: tuple[str, ...]
    validated: int
    note: str | None


def audit_log(log: Sequence[Entry], repository: Repository) -> AutofixAudit:
    """Re-validate the open autofix records and detect uncovered design-doc edits, log-wide."""
    audited_lines = audited_autofix_lines(log)
    failures = [
        f"line {entry.no}: {error}"
        for entry in log
        if entry.no in audited_lines and isinstance(entry.record, AutofixRecord)
        for error in static_errors(entry.record)
    ]
    coverage = uncovered_design_doc_paths(log, repository)
    if coverage is None:
        return AutofixAudit(tuple(failures), len(audited_lines), None)
    failures.extend(f"{path}: {UNCOVERED_MESSAGE}" for path in coverage.uncovered)
    return AutofixAudit(tuple(failures), len(audited_lines), coverage.note)


def static_errors(record: AutofixRecord) -> list[str]:
    """Re-validate one autofix record against the allowlist, as the append did."""
    return bound_errors(record) + content_errors(record)


def bound_errors(record: AutofixRecord) -> list[str]:
    """Check an autofix record's path, category, and size against the allowlist bounds."""
    errors: list[str] = []
    file = record.file if isinstance(record.file, str) else ""
    if isinstance(record, PrdAutofix):
        if file != PRD_PATH:
            errors.append("file is not the autofix-eligible PRD path (docs/prd.md)")
    elif not DESIGN_DOC_PATH_RE.match(file):
        errors.append("file is not an autofix-eligible design-doc path")
    if record.category not in AUTOFIX_CATEGORIES:
        errors.append("category is not autofix-eligible")
    lines = record.lines_changed
    if not (isinstance(lines, int) and 1 <= lines <= AUTOFIX_LINE_CAP):
        errors.append(f"lines_changed outside the 1-{AUTOFIX_LINE_CAP} autofix cap")
    chars = record.chars_changed
    if not (isinstance(chars, int) and 1 <= chars <= AUTOFIX_CHAR_CAP):
        errors.append(f"chars_changed outside the 1-{AUTOFIX_CHAR_CAP} autofix cap")
    return errors


def content_errors(record: AutofixRecord) -> list[str]:
    """Check that an autofix touched nothing structural and changed no reference."""
    old = record.old_content if isinstance(record.old_content, str) else ""
    new = record.new_content if isinstance(record.new_content, str) else ""
    lines = [line for text in (old, new) for line in text.splitlines()]
    errors: list[str] = []
    if any(line.startswith("## ") for line in lines):
        errors.append("content touches a '## ' heading line")
    if isinstance(record, PrdAutofix) and any(NG_ROW_RE.match(line) for line in lines):
        errors.append(
            "content touches a Non-Goals table row — never autofix-eligible; "
            "scope stays with product-requirements-expert (Gate 1 scope-lock)"
        )
    if sorted(_ANCHOR_ID_RE.findall(old)) != sorted(_ANCHOR_ID_RE.findall(new)):
        errors.append("anchor ids differ between old_content and new_content")
    if sorted(_REQ_TOKEN_RE.findall(old)) != sorted(_REQ_TOKEN_RE.findall(new)):
        errors.append("REQ-ID tokens differ between old_content and new_content")
    if any(line.lstrip().startswith("```") for line in lines):
        errors.append("content touches a code-fence line")
    if sorted(_LINK_TARGET_RE.findall(old)) != sorted(_LINK_TARGET_RE.findall(new)):
        errors.append(
            "markdown link targets differ between old_content and new_content"
        )
    fix = record.source_finding.fix if record.source_finding is not None else None
    if new != fix:
        errors.append("new_content is not byte-identical to source_finding.fix")
    return errors


def audited_autofix_lines(log: Sequence[Entry]) -> set[int]:
    """Return the lines of the autofix records not yet superseded by their slice's owning record."""
    last_design_block: dict[object, int] = {}
    last_prd_entry: dict[object, int] = {}
    for entry in log:
        if isinstance(entry.record, DesignBlock):
            last_design_block[entry.req_id] = entry.no
        elif isinstance(entry.record, PrdEntry):
            last_prd_entry[entry.req_id] = entry.no
    audited: set[int] = set()
    for entry in log:
        if isinstance(entry.record, DesignDocAutofix):
            closing = last_design_block
        elif isinstance(entry.record, PrdAutofix):
            closing = last_prd_entry
        else:
            continue
        if entry.no > closing.get(entry.req_id, 0):
            audited.add(entry.no)
    return audited


def uncovered_design_doc_paths(
    log: Sequence[Entry], repository: Repository
) -> DesignDocAudit | None:
    """Return the uncovered design-doc paths and the clean report's note; None when git fails."""
    state = repository.state()
    if state == "unborn":
        return DesignDocAudit(
            (), "no commit yet — direct-edit detection starts at the first commit"
        )
    if state != "ok":
        return None
    paths = repository.dirty_design_doc_paths()
    if paths is None:
        return None
    uncovered: list[str] = []
    if paths:
        baseline = repository.design_docs_baseline()
        if not baseline.readable:
            return None
        uncovered = uncovered_paths(
            paths, log, audited_autofix_lines(log), baseline.seconds
        )
    return DesignDocAudit(
        tuple(uncovered), f"{len(paths)} dirty design-doc path(s) covered"
    )


def uncovered_paths(
    paths: Sequence[str],
    log: Sequence[Entry],
    audited_lines: set[int],
    since_seconds: float | None,
) -> list[str]:
    """Return the dirty paths no non-superseded record newer than the baseline covers."""

    def covered(path: str) -> bool:
        return any(
            covers_path(entry, path, since_seconds)
            and (
                not isinstance(entry.record, DesignDocAutofix)
                or entry.no in audited_lines
            )
            for entry in log
        )

    uncovered = [p for p in paths if p != ADR_INDEX and not covered(p)]
    # The ADR index follows its files: it is covered when every other dirty
    # ADR path is, and no record names it.
    if ADR_INDEX in paths and not covered(ADR_INDEX):
        adr_paths = [p for p in paths if p.startswith("docs/adr/") and p != ADR_INDEX]
        if not adr_paths or any(p in uncovered for p in adr_paths):
            uncovered.append(ADR_INDEX)
    return sorted(uncovered)


def covers_path(entry: Entry, path: str, since_seconds: float | None) -> bool:
    """Return whether a record newer than the baseline commit covers the path."""
    if since_seconds is not None:
        ts = seconds_of(entry.ts)
        if ts is None or ts <= since_seconds:
            return False
    return record_covers(entry.record, path)


def record_covers(record: HandoffRecord, path: str) -> bool:
    """Return whether the record authorizes an uncommitted change to the path."""
    match record:
        case DesignDocAutofix(file=file):
            return file == path
        case DesignBlock(primary_paths=primary, supporting_paths=supporting):
            return path in primary or path in supporting
        case ConsultationResponse(memory_updates=updates):
            return any(update.path == path for update in updates)
        case PrdEntry(scope_overrides=overrides):
            # The non-goal ADR recording the owner's decision rides the
            # prd-entry that carries the scope override.
            return bool(overrides) and _NON_GOAL_ADR.match(path) is not None
        case _:
            return False
