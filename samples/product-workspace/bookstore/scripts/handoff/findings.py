"""Read review findings: their artifact owners, the gate's shape errors, and the dissent they carry.

A leaf over handoff.ledger and handoff.records.
"""

from collections.abc import Mapping
from typing import Any, NamedTuple

from .ledger import APPROVED, Entry
from .records import DESIGNER, IMPLEMENTER, PRODUCT, Finding, ReviewFeedback

CRITICAL = "critical"
AUTOFIX_TAG = "autofix"
BLOCKED_TAG = "blocked"
CLARIFY_TAG = "clarify"
ESCALATE_TAG = "escalate"
TRUNCATION_TAG = "truncation"
FIX_ROUTABLE_TAGS = frozenset({AUTOFIX_TAG, BLOCKED_TAG})
CHANNEL_TAGS = frozenset({TRUNCATION_TAG, CLARIFY_TAG, ESCALATE_TAG})
# Findings dispatch to their owners in this order, however the records list them.
OWNER_ORDER = (IMPLEMENTER, PRODUCT, DESIGNER)


class OwnerSplit(NamedTuple):
    """The artifact owners dissenting findings dispatch to, and the count root applies itself."""

    owners: tuple[str, ...]
    root_autofix: int


def finding_owner(finding: Finding) -> str | None:
    """Name the agent that owns a finding's artifact; None marks a root-applied doc autofix."""
    location = finding.location if isinstance(finding.location, str) else ""
    path = location.split(":", 1)[0]
    if path.startswith("docs/prd.md"):
        return None if finding.tag == AUTOFIX_TAG else PRODUCT
    if path.startswith(("docs/system-design.md", "docs/adr/")):
        return None if finding.tag == AUTOFIX_TAG else DESIGNER
    return IMPLEMENTER


def owner_split(
    verdicts: Mapping[str, ReviewFeedback], non_approved: Mapping[str, ReviewFeedback]
) -> OwnerSplit:
    """Split dissenting findings by owner and count the root-applied autofixes."""
    owners: list[str] = []
    root_autofix = 0
    for feedback in non_approved.values():
        for finding in feedback.findings:
            owner = finding_owner(finding)
            if owner is None:
                root_autofix += 1
            elif owner not in owners:
                owners.append(owner)
    approved = {r: fb for r, fb in verdicts.items() if r not in non_approved}
    owners.extend(o for o in _approved_escalate_owners(approved) if o not in owners)
    # The implementer rides every escalate round that dispatches at all.
    if owners and IMPLEMENTER not in owners and escalate_count(verdicts):
        owners.append(IMPLEMENTER)
    return OwnerSplit(tuple(owners), root_autofix)


def _approved_escalate_owners(approved: Mapping[str, ReviewFeedback]) -> list[str]:
    """List the owners of escalate findings riding approved records; they still join the split."""
    owners: list[str] = []
    for feedback in approved.values():
        for finding in feedback.findings:
            owner = finding_owner(finding)
            if (
                finding.tag == ESCALATE_TAG
                and owner is not None
                and owner not in owners
            ):
                owners.append(owner)
    return owners


def escalate_count(verdicts: Mapping[str, ReviewFeedback]) -> int:
    """Count the escalate-tagged findings across the verdicts."""
    return sum(
        1
        for feedback in verdicts.values()
        for finding in feedback.findings
        if finding.tag == ESCALATE_TAG
    )


def raw_findings(entry: Entry) -> list[Any]:
    """Return the entry's raw findings list, or an empty list for any other shape."""
    findings = entry.raw.get("findings", [])
    return findings if isinstance(findings, list) else []


def finding_shape_errors(entry: Entry, findings: list[Any]) -> list[str]:
    """Return the Gate 4 shape errors of one feedback record's raw findings."""
    # Raw findings keep the 1-based indexes the messages name; the lenient
    # lift drops non-object items.
    approved = (
        isinstance(entry.record, ReviewFeedback) and entry.record.verdict == APPROVED
    )
    objects = [(i, f) for i, f in enumerate(findings, 1) if isinstance(f, dict)]
    errors = [
        f"finding {i} has tag 'clarify' but no clarify_target"
        for i, f in objects
        if f.get("tag") == CLARIFY_TAG and not f.get("clarify_target")
    ]
    errors.extend(
        f"finding {i} has tag '{f.get('tag')}' but no severity"
        for i, f in objects
        if f.get("tag") in FIX_ROUTABLE_TAGS and not f.get("severity")
    )
    errors.extend(
        f"finding {i} is tag '{f.get('tag')}' on an approved verdict; "
        "record changes_requested or drop the finding"
        for i, f in objects
        if approved and f.get("tag") in FIX_ROUTABLE_TAGS
    )
    return errors


def carries_capped_dissent(findings: list[Any]) -> bool:
    """Return whether a raw findings list earns dissent on a critical-only round."""
    return any(
        isinstance(f, dict)
        and (
            (f.get("tag") in FIX_ROUTABLE_TAGS and f.get("severity") == CRITICAL)
            or f.get("tag") in CHANNEL_TAGS
        )
        for f in findings
    )
