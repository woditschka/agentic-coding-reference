"""Hold the append-time gates: the refusals that keep a record off the ledger until its precondition holds.

A leaf over handoff.ledger, handoff.records, handoff.autofix, and handoff.repository. Each gate
returns the refusal naming the fix, or None when the record may land.
"""

from collections.abc import Sequence

from .autofix import uncovered_design_doc_paths
from .ledger import Entry
from .records import (
    DESIGNER,
    PRODUCT,
    BuildPass,
    ConsultationResponse,
    DesignBlock,
    DispatchStart,
    ReviewFeedback,
)
from .repository import PRD_PATH, Repository
from .schema import sanitize


def review_anchor_missing(log: Sequence[Entry], record: ReviewFeedback) -> str | None:
    """Refuse a review-feedback whose author has no dispatch-start since the slice's last build-pass."""
    last_build_pass: int | None = None
    anchored = False
    for entry in log:
        if entry.req_id != record.req_id:
            continue
        if isinstance(entry.record, BuildPass):
            last_build_pass, anchored = entry.no, False
        elif isinstance(entry.record, DispatchStart) and entry.author == record.author:
            anchored = True
    if last_build_pass is None or anchored:
        return None
    return (
        f"review-feedback by {sanitize(str(record.author))} has no dispatch-start since the "
        f"build-pass at line {last_build_pass}; append a dispatch-start "
        "(handoff-append skill § Dispatch-Start) and retry"
    )


def design_sync_missing(log: Sequence[Entry], record: BuildPass) -> str | None:
    """Refuse a build-pass while a PRD-changing product response awaits its design response."""
    pending: int | None = None
    for entry in log:
        if entry.req_id != record.req_id:
            continue
        prior = entry.record
        if isinstance(prior, DesignBlock) or (
            isinstance(prior, ConsultationResponse) and prior.author == DESIGNER
        ):
            pending = None
        elif (
            isinstance(prior, ConsultationResponse)
            and prior.author == PRODUCT
            and changes_prd(prior)
        ):
            pending = entry.no
    if pending is None:
        return None
    return (
        f"build-pass follows the product-requirements-expert's consultation-response "
        f"at line {pending}, which changed docs/prd.md, with no system-design-expert "
        "response or design-block since; append a consultation-request to "
        "system-design-expert to carry the change into docs/system-design.md "
        "(tdd-workflow skill § TDD Cycle, step 2), then stop; the build-pass "
        "lands on resume after the consultation returns"
    )


def changes_prd(response: ConsultationResponse) -> bool:
    """Return whether a consultation-response's memory updates name the PRD."""
    return any(
        isinstance(update.path, str)
        and (
            update.path.removeprefix("./") == PRD_PATH
            or update.path.removeprefix("./").startswith(f"{PRD_PATH}#")
        )
        for update in response.memory_updates
    )


def responding_to_dangling(record: DispatchStart, line_count: int) -> str | None:
    """Refuse a dispatch-start whose responding_to names a line the log does not have."""
    bad = [
        target
        for target in record.responding_to
        if not isinstance(target, int)
        or isinstance(target, bool)
        or target < 0
        or target > line_count
    ]
    if not bad:
        return None
    return (
        f"responding_to references non-existent log line(s) {sanitize(str(bad))} "
        f"(log has {line_count} line(s))"
    )


def design_block_uncovered(
    log: Sequence[Entry], candidate: Entry, repository: Repository
) -> str | None:
    """Refuse a design-block that leaves an uncommitted design-doc path with no covering record."""
    audit = uncovered_design_doc_paths([*log, candidate], repository)
    if audit is None or not audit.uncovered:
        return None
    shown = ", ".join(sanitize(p) for p in audit.uncovered)
    return (
        "design-block leaves uncommitted design-doc path(s) with no "
        f"covering record: {shown} — list every design-doc path this "
        "dispatch wrote in primary_paths or supporting_paths and "
        "re-append; a path this dispatch did not write is an unrecorded "
        "design-doc edit the autofix audit fails at the gate: record it "
        "(a design-doc-autofix for a mechanical fix) or revert it"
    )
