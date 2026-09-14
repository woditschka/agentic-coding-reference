"""Hold Gate 1's scope lock: every changed Non-Goals row needs an override quoting the owner's decision.

A leaf over handoff.ledger and handoff.records.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, NamedTuple

from .ledger import Entry, entry_at
from .records import HUMAN, ConsultationResponse, HandoffRecord, IntakeDecision

# The digit run is bounded so the source never trips CPython's int-parse cap.
_OVERRIDE_SOURCE_RE = re.compile(r"^(consultation|intake):([1-9][0-9]{0,8})$")
DISPATCH_SOURCE = "dispatch"
INTAKE_SOURCE = "intake"


class OverrideSources(NamedTuple):
    """Where an override's cited source may live: the slice, its lines, and whether an intake exists."""

    req_id: str
    has_intake: bool
    by_line: Mapping[int, Entry]


@dataclass(frozen=True, slots=True)
class _CitedSource:
    """One override's cited source line, the record found there, and the quote."""

    non_goal: str
    line_no: int
    record: HandoffRecord | None
    quote: str


def scope_lock_errors(
    raw_overrides: object, delta: tuple[str, ...] | None, sources: OverrideSources
) -> list[str]:
    """Return every scope-lock error of a prd-entry's overrides against the Non-Goals delta."""
    if delta is None:
        return [
            "cannot read the docs/prd.md scope-lock baseline; the check fails closed"
        ]
    items = raw_overrides if isinstance(raw_overrides, list) else []
    errors: list[str] = []
    covered: set[str] = set()
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            errors.append(f"scope_overrides item {index} is not an object")
            continue
        non_goal = item.get("non_goal_id")
        if not isinstance(non_goal, str) or not non_goal:
            errors.append(f"scope_overrides item {index}: non_goal_id missing")
            continue
        covered.add(non_goal)
        errors.extend(_override_errors(non_goal, item, delta, sources))
    errors.extend(
        f"Non-Goals row {non_goal} changed in docs/prd.md with no "
        "scope_overrides entry recording the owner's decision"
        for non_goal in delta
        if non_goal not in covered
    )
    return errors


def _override_errors(
    non_goal: str,
    item: dict[str, Any],
    delta: tuple[str, ...],
    sources: OverrideSources,
) -> list[str]:
    """Check one scope override against the delta, its quote, and its source."""
    errors: list[str] = []
    if non_goal not in delta:
        errors.append(
            f"scope_overrides names {non_goal}, but no such Non-Goals row changed in docs/prd.md"
        )
    decision_text = item.get("owner_decision")
    quote = decision_text.strip() if isinstance(decision_text, str) else ""
    if not quote:
        errors.append(f"scope_overrides {non_goal}: owner_decision quote is empty")
    source = item.get("source")
    if source == DISPATCH_SOURCE:
        # The legacy "dispatch" source is legal only until a human
        # intake-decision exists anywhere on the log.
        if sources.has_intake:
            errors.append(
                f"scope_overrides {non_goal}: source 'dispatch' is not valid "
                "once a human intake-decision exists on the log; cite "
                "intake:<line>"
            )
        return errors
    match = _OVERRIDE_SOURCE_RE.match(source) if isinstance(source, str) else None
    if match is None:
        errors.append(
            f"scope_overrides {non_goal}: source must be 'dispatch', "
            "'consultation:<line>', or 'intake:<line>'"
        )
        return errors
    line_no = int(match.group(2))
    target = entry_at(sources.by_line, line_no)
    cited = _CitedSource(non_goal, line_no, target.record if target else None, quote)
    if match.group(1) == INTAKE_SOURCE:
        errors.extend(_intake_source_errors(cited, sources.req_id))
    else:
        errors.extend(_consultation_source_errors(cited, sources.req_id))
    return errors


def _intake_source_errors(cited: _CitedSource, req_id: str) -> list[str]:
    """Require the quote to be a decision of a human intake-decision for this slice."""
    record = cited.record
    if (
        not isinstance(record, IntakeDecision)
        or record.author != HUMAN
        or record.req_id != req_id
    ):
        return [
            f"scope_overrides {cited.non_goal}: intake:{cited.line_no} is not a "
            "human intake-decision for this req_id"
        ]
    # Only a decisions item can be quoted: the request is never the override,
    # and a note authorizes nothing.
    decisions = [d for d in record.decisions if isinstance(d, str)]
    if cited.quote and not any(cited.quote in d for d in decisions):
        return [
            f"scope_overrides {cited.non_goal}: owner_decision quote not found in "
            f"intake:{cited.line_no}'s decisions"
        ]
    return []


def _consultation_source_errors(cited: _CitedSource, req_id: str) -> list[str]:
    """Require the quote to appear in a human consultation-response for this slice."""
    record = cited.record
    if (
        not isinstance(record, ConsultationResponse)
        or record.author != HUMAN
        or record.req_id != req_id
    ):
        return [
            f"scope_overrides {cited.non_goal}: consultation:{cited.line_no} is not a "
            "human consultation-response for this req_id"
        ]
    if cited.quote and (
        not isinstance(record.answer, str) or cited.quote not in record.answer
    ):
        return [
            f"scope_overrides {cited.non_goal}: owner_decision quote not found in "
            f"consultation:{cited.line_no}'s answer"
        ]
    return []
