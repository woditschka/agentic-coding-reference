"""grading.handoff_facts — the grading engine's handoff-log gateway.

All traffic between the grading context and the handoff log crosses here, and
only through the handoff package's validator API — the sanctioned dynamic
edge the import-boundary gate names. Reads degrade (a malformed line is
skipped, an unreadable log nulls the row); writes go through the same schema
check and canonical serializer as `handoff.py append`, so one malformed
append can never wedge the gate queries.

Stdlib only.
"""

import os
import sys
from pathlib import Path
from typing import Any

from .config import REVIEWERS

SCRATCH = Path(".scratch")
HANDOFF = SCRATCH / "handoff.jsonl"
SCHEMAS = "schemas/scratch"
LAYOUT_FOR_SCHEMAS = "scripts/layout.toml"


def load_handoff() -> Any:
    """Import the handoff package — the validator API — for a compatible append.

    The grader owns the grader-features append, but the record must not bypass
    the log's validation: one malformed append would wedge every validated gate
    query until the log is hand-repaired. Reusing the package's schema check and
    canonical serializer keeps this writer byte-compatible with `handoff.py
    append`. The package (not the entry launcher) is the API surface — ts_now,
    load_schema, validate_record, canonicalize, dumps_canonical, read_layout are
    all re-exported by handoff/__init__.py (ADR 2026-07-17 runtime-package-layout).
    The composition root (this package's parent directory) carries the handoff
    package, so put it on sys.path when a non-script load left it off; imported
    lazily so `changeset` runs never need it.
    """
    import importlib

    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module("handoff")


def read_handoff(req_id: Any) -> dict[str, Any]:
    """Read .scratch/handoff.jsonl records for req_id.

    Returns a dict of deterministic facts, every field null when the log is
    absent or unreadable. The records are append-only, so build-failure counts
    are never lost on success — the retry trail is the diagnostic. The log is
    streamed line by line and a single malformed line is skipped (not allowed
    to null the whole row).
    """
    null: dict[str, Any] = {
        "build_passed": None,
        "reviewers": None,
        "review_roster": None,
        "build_retries": None,
        "consultations": None,
        "design_revisions": None,
    }
    if not HANDOFF.exists():
        return null

    records: list[dict[str, Any]] = []
    try:
        handoff = load_handoff()
        # newline="\n": the readers' shared \n-only domain — see load_records.
        with HANDOFF.open(encoding="utf-8", newline="\n") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = handoff.loads_strict(line)
                except ValueError:
                    # Skip one bad line (invalid JSON, NaN, duplicate key);
                    # don't null the whole row. loads_strict matches handoff.py's
                    # parse definition, so this reader and the log agree.
                    continue
                if isinstance(obj, dict) and obj.get("req_id") == req_id:
                    records.append(obj)
    except (OSError, UnicodeDecodeError):
        return null

    if not records:
        return null

    def indices_of_type(t: str) -> list[int]:
        return [i for i, r in enumerate(records) if r.get("type") == t]

    # Latest design-block line bounds the current retry cycle.
    db_lines = indices_of_type("design-block")
    last_db = db_lines[-1] if db_lines else -1

    bf_lines = indices_of_type("build-failure")
    bp_lines = indices_of_type("build-pass")
    # build_passed: a build-pass exists that post-dates every build-failure in
    # the current cycle. Absent => null (the grader reads null as not gated).
    if bp_lines:
        last_bp = bp_lines[-1]
        later_bf = [i for i in bf_lines if i > last_bp]
        build_passed = len(later_bf) == 0
    else:
        build_passed = None

    build_retries = sum(1 for i in bf_lines if i > last_db)
    consultations = len(indices_of_type("consultation-request"))
    design_revisions = sum(
        1
        for r in records
        if r.get("type") == "design-block" and r.get("supersedes_record_at")
    )

    # Floor reviewers are always present (null when silent); every other
    # review-feedback author — a declared extra reviewer gates the change too —
    # is added as encountered. Last verdict per author wins in both cases.
    reviewers_map: dict[str, Any] = {who: None for who in REVIEWERS}
    for r in records:
        if r.get("type") != "review-feedback":
            continue
        who = r.get("author")
        if isinstance(who, str) and who:
            reviewers_map[who] = r.get("verdict")
    reviewers: dict[str, Any] | None = reviewers_map
    if all(v is None for v in reviewers_map.values()):
        reviewers = None

    # The latest review-plan's roster is the set of reviewers this pass actually
    # dispatched. The grader reads it so a floor reviewer silent because a
    # focused plan scoped it out is not misread as a hedge (change-grading
    # § reviewer_hedging). Null when no plan was recorded (full-battery default).
    review_roster: list[Any] | None = None
    for r in records:
        if r.get("type") == "review-plan":
            roster = r.get("roster")
            review_roster = roster if isinstance(roster, list) else None

    return {
        "build_passed": build_passed,
        "reviewers": reviewers,
        "review_roster": review_roster,
        "build_retries": build_retries,
        "consultations": consultations,
        "design_revisions": design_revisions,
    }


def load_records(req_id: Any) -> list[tuple[int, dict[str, Any]]]:
    """Ordered (lineno, record) for req_id from the handoff log; [] if absent.

    A single malformed line is skipped, never allowed to drop the whole log —
    the same tolerance read_handoff applies. 1-based line numbers so a record's
    position can anchor an ordering comparison (a plan is 'fix' when a prior
    review-plan sits before the current build-pass)."""
    if not HANDOFF.exists():
        return []
    out: list[tuple[int, dict[str, Any]]] = []
    try:
        handoff = load_handoff()
        # newline="\n": one line-number domain for every reader. The append
        # receipt counts raw b"\n", so no reader may let universal newlines
        # split on a bare \r and shift the numbers (parse_log reads
        # newline="" for the same reason).
        with HANDOFF.open(encoding="utf-8", newline="\n") as fh:
            for no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = handoff.loads_strict(line)
                except ValueError:
                    # Same tolerance as read_handoff: skip a bad line (invalid
                    # JSON, NaN, duplicate key), matching handoff.py's parser.
                    continue
                if isinstance(obj, dict) and obj.get("req_id") == req_id:
                    out.append((no, obj))
    except (OSError, UnicodeDecodeError):
        return []
    return out


def append_validated(record: dict[str, Any], rtype: str, prefix: str) -> str | None:
    """Append one record to the handoff log through handoff.py's validator.

    Both engine writers here (grader-features, review-plan) are records the
    grader/router own, so they append directly rather than through handoff.py's
    stdin CLI — but they must not bypass the log's validation: one malformed
    append wedges every gate query until the log is hand-repaired. This routes
    through handoff.py's schema check and canonical serializer so the write is
    byte-compatible with `handoff.py append`, and mirrors its lock-free
    single-write append and glued-tail warning.
    Returns None on success, or an error message (already printed) on failure.
    It also mirrors the append-boundary ts stamp: handoff.ts_now() is the
    log's one clock, so the engine writers supply no ts of their own.
    """
    handoff = load_handoff()
    record["ts"] = handoff.ts_now()
    try:
        schema = handoff.load_schema(
            SCHEMAS, rtype, handoff.read_layout(LAYOUT_FOR_SCHEMAS)
        )
    except handoff.SchemaError as exc:
        print(f"{prefix}: {exc}", file=sys.stderr)
        return str(exc)
    schema_errors = handoff.validate_record(record, schema)
    if schema_errors:
        for err in schema_errors:
            print(f"{prefix}: {err}", file=sys.stderr)
        print(f"{prefix}: record failed validation — nothing appended", file=sys.stderr)
        return "record failed validation"
    line = handoff.dumps_canonical(handoff.canonicalize(record, schema, schema))
    SCRATCH.mkdir(exist_ok=True)
    payload = (line + "\n").encode("utf-8")
    # Lock-free append, mirroring handoff.py's writer (ADR 2026-08-16
    # lock-free-ledger-appends in the reference): one write() on an O_APPEND
    # descriptor lands atomically at EOF, so this engine writer never
    # interleaves with a concurrent agent append. No pre-write tail check —
    # a reader cannot tell a crash-damaged tail from a write still landing.
    # A short write fails hard rather than continuing.
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(HANDOFF, flags, 0o644)
        try:
            written = os.write(fd, payload)
            end = os.lseek(fd, 0, os.SEEK_CUR)
        finally:
            os.close(fd)
    except OSError as exc:
        msg = f"cannot append to {HANDOFF}: {exc}"
        print(f"{prefix}: {msg}", file=sys.stderr)
        return msg
    if written != len(payload):
        msg = f"short write ({written} of {len(payload)} bytes) — record damaged"
        print(f"{prefix}: {msg}", file=sys.stderr)
        return msg
    start = end - len(payload)
    if start > 0:
        with HANDOFF.open("rb") as fh:
            fh.seek(start - 1)
            if fh.read(1) != b"\n":
                # Crash damage only: the fragment glued this record onto its
                # line. Warn like handoff.py's writer; validate blocks.
                print(
                    f"{prefix}: prior record was truncated — this record "
                    "landed on the same line; run validate and repair",
                    file=sys.stderr,
                )
    return None
