"""Read the handoff log for the grading engine, and write its records through the log's own validator.

The grading context's one gateway to the log: reads degrade to null facts, writes go
through the handoff package's validator, loaded lazily as the sanctioned dynamic edge.
"""

import os
import sys
from pathlib import Path
from typing import Any, TypeAlias

from .config import REVIEWERS

Raw: TypeAlias = dict[str, Any]
Line: TypeAlias = tuple[int, Raw]

SCRATCH = Path(".scratch")
HANDOFF = SCRATCH / "handoff.jsonl"
SCHEMAS = "schemas/scratch"
LAYOUT_FOR_SCHEMAS = "scripts/layout.toml"
NULL_FACTS: Raw = {
    "build_passed": None,
    "reviewers": None,
    "review_roster": None,
    "build_retries": None,
    "consultations": None,
    "design_revisions": None,
}


def load_handoff() -> Any:  # noqa: ANN401
    """Import the handoff package lazily; it is the validator API this gateway writes through."""
    import importlib  # noqa: PLC0415

    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("handoff")


def read_handoff(req_id: object) -> Raw:
    """Return the slice's deterministic history facts; every field null when the log cannot be read."""
    lines = _slice_lines(req_id)
    if not lines:
        return dict(NULL_FACTS)
    records = [raw for _no, raw in lines]
    by_line = dict(lines)
    return {
        "build_passed": _build_passed(records),
        "reviewers": _reviewer_verdicts(records),
        "review_roster": _plan_roster(records),
        "build_retries": _build_retries(records),
        "consultations": len(_indexes_of(records, "consultation-request")),
        "design_revisions": _design_revisions(records, by_line),
    }


def load_records(req_id: object) -> list[Line]:
    """Return the slice's records with their global line numbers; empty when the log cannot be read."""
    return _slice_lines(req_id) or []


def _slice_lines(req_id: object) -> list[Line] | None:
    """Stream the log and keep the object lines of one slice; None when the log cannot be read."""
    if not HANDOFF.exists():
        return None
    lines: list[Line] = []
    try:
        handoff = load_handoff()
        # newline="\n" keeps every reader on the raw "\n" line domain the
        # append receipt counts, so a bare "\r" never shifts a line number.
        with HANDOFF.open(encoding="utf-8", newline="\n") as handle:
            for no, text in enumerate(handle, 1):
                stripped = text.strip()
                if not stripped:
                    continue
                try:
                    raw = handoff.loads_strict(stripped)
                except ValueError:
                    continue
                if isinstance(raw, dict) and raw.get("req_id") == req_id:
                    lines.append((no, raw))
    except (OSError, UnicodeDecodeError):
        return None
    return lines


def _indexes_of(records: list[Raw], record_type: str) -> list[int]:
    return [i for i, raw in enumerate(records) if raw.get("type") == record_type]


def _build_passed(records: list[Raw]) -> bool | None:
    """Return whether a build-pass post-dates every build-failure; None with no build-pass at all."""
    passes = _indexes_of(records, "build-pass")
    if not passes:
        return None
    return not any(i > passes[-1] for i in _indexes_of(records, "build-failure"))


def _build_retries(records: list[Raw]) -> int:
    """Count the build-failures since the latest design-block."""
    blocks = _indexes_of(records, "design-block")
    last_block = blocks[-1] if blocks else -1
    return sum(1 for i in _indexes_of(records, "build-failure") if i > last_block)


def _design_revisions(records: list[Raw], by_line: dict[int, Raw]) -> int:
    """Count the superseding design-blocks that could void review history."""
    passes = _indexes_of(records, "build-pass")
    first_pass = passes[0] if passes else None
    revisions = 0
    for i, raw in enumerate(records):
        if raw.get("type") != "design-block" or not raw.get("supersedes_record_at"):
            continue
        before_first_build = first_pass is not None and i < first_pass
        if before_first_build and _corrects_the_record(raw, by_line):
            continue
        revisions += 1
    return revisions


def _corrects_the_record(raw: Raw, by_line: dict[int, Raw]) -> bool:
    """Return whether a superseding design-block re-issues its target unchanged in verdict and effort."""
    pointer = raw.get("supersedes_record_at")
    if not isinstance(pointer, int) or isinstance(pointer, bool):
        return False
    target = by_line.get(pointer)
    if not isinstance(target, dict) or target.get("type") != "design-block":
        return False
    return bool(
        raw.get("verdict") == target.get("verdict")
        and raw.get("implementation_effort", "involved")
        == target.get("implementation_effort", "involved")
    )


def _reviewer_verdicts(records: list[Raw]) -> Raw | None:
    """Return the latest verdict per review author over the floor's keys; None when no reviewer spoke."""
    verdicts: Raw = dict.fromkeys(REVIEWERS)
    for raw in records:
        author = raw.get("author")
        if raw.get("type") == "review-feedback" and isinstance(author, str) and author:
            verdicts[author] = raw.get("verdict")
    if all(v is None for v in verdicts.values()):
        return None
    return verdicts


def _plan_roster(records: list[Raw]) -> list[Any] | None:
    """Return the latest review-plan's roster, the reviewers this pass dispatched; None without a plan."""
    roster: list[Any] | None = None
    for raw in records:
        if raw.get("type") == "review-plan":
            plan_roster = raw.get("roster")
            roster = plan_roster if isinstance(plan_roster, list) else None
    return roster


def append_validated(record: Raw, rtype: str, prefix: str) -> str | None:
    """Append one record through the log's validator; return the error already printed, or None."""
    handoff = load_handoff()
    record["ts"] = handoff.ts_now()
    try:
        schema = handoff.load_schema(
            SCHEMAS, rtype, handoff.read_layout(LAYOUT_FOR_SCHEMAS)
        )
    except handoff.SchemaError as exc:
        _report(prefix, str(exc))
        return str(exc)
    schema_errors = handoff.validate_record(record, schema)
    if schema_errors:
        for err in schema_errors:
            _report(prefix, err)
        _report(prefix, "record failed validation — nothing appended")
        return "record failed validation"
    line = handoff.dumps_canonical(handoff.canonicalize(record, schema, schema))
    SCRATCH.mkdir(exist_ok=True)
    return _append_line((line + "\n").encode("utf-8"), prefix)


def _append_line(payload: bytes, prefix: str) -> str | None:
    """Land one line with a single append-only write, the same way the handoff writer does."""
    # One write on an append-only descriptor lands atomically at the end; a
    # pre-write tail check could mistake a concurrent write for damage.
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(HANDOFF, flags, 0o644)
        try:
            written = os.write(descriptor, payload)
            end = os.lseek(descriptor, 0, os.SEEK_CUR)
        finally:
            os.close(descriptor)
    except OSError as exc:
        message = f"cannot append to {HANDOFF}: {exc}"
        _report(prefix, message)
        return message
    if written != len(payload):
        message = f"short write ({written} of {len(payload)} bytes) — record damaged"
        _report(prefix, message)
        return message
    start = end - len(payload)
    if start > 0 and _byte_before(start) != b"\n":
        _report(
            prefix,
            "prior record was truncated — this record landed on the same line; "
            "run validate and repair",
        )
    return None


def _report(prefix: str, message: str) -> None:
    print(f"{prefix}: {message}", file=sys.stderr)


def _byte_before(offset: int) -> bytes:
    with HANDOFF.open("rb") as handle:
        handle.seek(offset - 1)
        return handle.read(1)
