#!/usr/bin/env python3
"""handoff.py — deterministic access to the .scratch/handoff.jsonl handoff log.

Every write of the handoff log and every gate query over it goes through this
tool. Hand-built appends (shell redirection, editor tools) corrupt the log: a
missing trailing newline glues two records onto one line and the whole file
stops parsing. Hand-built queries (ad-hoc grep/jq) answer the same gate
question inconsistently across agents. This tool gives every agent the same
seven operations with the same semantics:

  append      validate a record against its schema, write it in canonical form
  validate    parse and schema-check every line of the log
  latest      the gate query: latest record matching (type, req_id)
  next-retry  the Build-Failure Recovery counter: build-failure records for
              the req_id after the latest design-block line, plus one
  route       execute the Handoff Conditions table: print the routing decision
              as one JSON object — decision "dispatch", "blocked", or "escalate"
  show        pretty-print recent records for human inspection (raw records)
  view        render each slice as a terminal board: header,
              review-convergence matrix, timeline in append order

This file is the CLI entry point. The
logic lives in four siblings it composes and re-exports:

  handoff_schema   the byte contract — loads_strict, the draft-07 subset
                   validator, canonicalize/dumps_canonical, layout + schema
                   loading, parse_log
  handoff_records  the typed record model — the dataclasses, lenient lifts,
                   registries, parse_record, and the pipeline vocabulary
  handoff_route    the deterministic routing core — Entry, the states, and
                   _route_decision (the Handoff Conditions table)
  handoff_view     the human-facing board renderer and the cost overlay

The public names those siblings own are re-exported here (see the re-export
block below), so `import handoff; handoff.dumps_canonical` and every existing
`handoff.<name>` access keeps working — score-change.py and the test suite
rely on it.

Route is fail-closed: it never repairs a log and never guesses past a failed
check. A dirty log or an unroutable slice yields decision "blocked" carrying
the exact errors; "blocked" always means halt for a human. A failed gate is a
"dispatch" decision naming the upstream agent with the errors in context —
the documented bounce, expressed as the re-dispatch it is. States the table
does not decide unambiguously (fresh intake, a refactor-first design-block
with no sibling prd-entry, truncation of an agent with no recovery row, any
state matching no table row) yield decision "escalate": the
pipeline-coordinator owns those judgment calls. Route exits 0 whenever a
decision was computed, including blocked and escalate.

Canonical form (append): fields in schema declaration order — type, req_id,
ts, author first, payload next, optional fields last. Nested objects follow
their subschema's order; fields the schema does not name sort last
alphabetically. One record per line, newline-terminated. The order serves
humans who open the raw file; the schema check serves the gates. Same logical
record in, same bytes out.

Validation is a deliberately minimal draft-07 subset: exactly the keywords the
schemas in schemas/scratch/ use (see SUPPORTED in handoff_schema). Any other
keyword is a loud error, never a silent pass. Extending a schema beyond the
subset means extending that validator first; test_handoff_schema.py sweeps
every repo schema to enforce that. Parsing is strict too: loads_strict rejects
NaN, Infinity, and duplicate object keys at any depth, before any schema check.

View is the human-facing reader: read-only, never a routing input. Like
route, it orders by file position — timestamps are model-authored and never
a clock. It degrades gracefully: unknown record types, missing fields, and a
partial or dirty log all render, with the parse errors as a footer.

Stdlib only, Python 3.11+ (tomllib, to read layout.toml).

Exit codes: 0 success; 1 validation, parse, or I/O error; 2 usage error;
3 no matching record (latest / next-retry / view --req-id with no hit).
Route always exits 0 with the decision JSON; the decision field carries the
state. View exits 0 on a missing or dirty log — it renders what parses and
lists the problems — and 3 only for --req-id with no records.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("handoff.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None

# The sibling modules resolve via this script's own directory — the directory
# python already puts on sys.path when handoff.py is run as a script. When it is
# loaded by path instead (score-change.py's importlib load, a test loader) from
# another cwd, that entry is absent, so add it here; this keeps the single-file
# tool's cwd-independence.
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

# --- Re-exports --------------------
# The siblings own the logic; this entry point re-exports their public names so
# `import handoff; handoff.<name>` stays stable for score-change.py and the test
# suite. Names the cmd_* layer uses directly are plain imports; names re-exported
# only for callers are listed in __all__ so the linter reads them as the intended
# public surface, not dead imports.
from handoff_records import (
    _MAPPERS,
    _RECORD_TYPES,
    GRADER,
    HUMAN,
    PLAN_ENGINE,
    RETRY_CAP,
    ROSTER_FLOOR,
    SUBSTANTIVE,
    BuildFailure,
    BuildPass,
    ConsultationRequest,
    ConsultationResponse,
    DesignBlock,
    DesignDocAutofix,
    DispatchStart,
    Facet,
    Facets,
    Features,
    Finding,
    GraderFeatures,
    GraderVerdict,
    HandoffRecord,
    MemoryUpdate,
    Pattern,
    PlanBasis,
    PrdEntry,
    ReviewFeedback,
    ReviewPlan,
    Risk,
    SourceFinding,
    UnknownRecord,
    parse_record,
)
from handoff_route import (
    Decision,
    _auto_grade,
    _blocked,
    _escalate,
    _roster,
    _route_decision,
)
from handoff_schema import (
    LogEntry,
    SchemaError,
    _decode_error,
    _sanitize,
    canonicalize,
    dumps_canonical,
    load_schema,
    loads_strict,
    parse_log,
    read_layout,
    resolve_ref,
    unsupported_keywords,
    validate_record,
)
from handoff_view import (
    DIM,
    GREEN,
    _build_cost_lookup,
    _parse_iso_seconds,
    _ts_seconds,
    cc_accounting,
    render_view,
    render_view_md,
)

# Re-export-only names (used by score-change.py or the split test suites via
# `handoff.<name>`, not by the cmd_* layer here). Listing them keeps the linter
# from reading the imports as unused while documenting the public surface.
__all__ = [
    "DIM",
    "GREEN",
    "BuildFailure",
    "BuildPass",
    "ConsultationRequest",
    "ConsultationResponse",
    "Decision",
    "DesignBlock",
    "DesignDocAutofix",
    "DispatchStart",
    "Facet",
    "Facets",
    "Features",
    "Finding",
    "GraderFeatures",
    "GraderVerdict",
    "HandoffRecord",
    "LogEntry",
    "MemoryUpdate",
    "Pattern",
    "PlanBasis",
    "PrdEntry",
    "RETRY_CAP",
    "ReviewFeedback",
    "ReviewPlan",
    "Risk",
    "SchemaError",
    "SourceFinding",
    "UnknownRecord",
    "_MAPPERS",
    "_RECORD_TYPES",
    "canonicalize",
    "cc_accounting",
    "dumps_canonical",
    "load_schema",
    "loads_strict",
    "parse_record",
    "read_layout",
    "resolve_ref",
    "unsupported_keywords",
    "validate_record",
]

DEFAULT_LOG = ".scratch/handoff.jsonl"
DEFAULT_SCHEMAS = "schemas/scratch"
DEFAULT_LAYOUT = "scripts/layout.toml"


def fail(msg: str) -> int:
    print(f"handoff.py: {msg}", file=sys.stderr)
    return 1


def require_clean_log(path: str) -> list[LogEntry] | None:
    entries, errors = parse_log(path)
    if errors:
        for err in errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        print("handoff.py: log is not clean — run validate", file=sys.stderr)
        return None
    return entries


def ts_now() -> str:
    """The log's one clock: every appended record's ts is stamped here.

    An agent composing a record cannot read the clock, so a supplied ts is
    fiction — and the board's durations and cost windows key on ts. append
    overwrites any supplied value with this stamp.
    """
    return datetime.datetime.now(datetime.UTC).isoformat()


def cmd_append(args: argparse.Namespace) -> int:
    raw = sys.stdin.read()
    try:
        record = loads_strict(raw)
    except ValueError as exc:
        return fail(f"stdin is not valid JSON: {_decode_error(exc)}")
    if not isinstance(record, dict):
        return fail("record must be a JSON object")
    if record.get("type") != args.type:
        return fail(
            f"record type {json.dumps(record.get('type'))} does not match argument '{args.type}'"
        )
    record["ts"] = ts_now()
    try:
        schema = load_schema(args.schemas, args.type, read_layout(args.layout))
    except SchemaError as exc:
        return fail(str(exc))
    except json.JSONDecodeError as exc:
        return fail(f"schema for '{args.type}' is not valid JSON: {exc.msg}")
    errors = validate_record(record, schema)
    if errors:
        for err in errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        return 1
    line = dumps_canonical(canonicalize(record, schema, schema))
    path = Path(args.file)
    # dispatch-start responding_to points at existing log lines ([0] is the
    # documented fresh-intake sentinel). A dangling pointer silently degrades
    # the board's fix-attribution lines, so bound it at append time — the one
    # moment the referent set is known.
    if args.type == "dispatch-start" and isinstance(record.get("responding_to"), list):
        existing = 0
        if path.exists():
            with open(path, "rb") as fh:
                data = fh.read()
            # A last line missing its newline is still a record — the same
            # state the write path below detects and repairs.
            existing = data.count(b"\n") + (
                0 if not data or data.endswith(b"\n") else 1
            )
        bad = [
            r
            for r in record["responding_to"]
            if not isinstance(r, int) or isinstance(r, bool) or r < 0 or r > existing
        ]
        if bad:
            return fail(
                f"responding_to references non-existent log line(s) {bad} "
                f"(log has {existing} line(s))"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = line.encode("utf-8") + b"\n"
    if path.exists() and path.stat().st_size > 0:
        with open(path, "rb") as fh:
            fh.seek(-1, os.SEEK_END)
            if fh.read(1) != b"\n":
                payload = b"\n" + payload
                print(
                    "handoff.py: repaired missing trailing newline on prior record",
                    file=sys.stderr,
                )
    with open(path, "ab") as fh:
        fh.write(payload)
    with open(path, "rb") as fh:
        line_no = fh.read().count(b"\n")
    print(f"appended {args.type} at line {line_no}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    entries, errors = parse_log(args.file)
    layout = read_layout(args.layout)
    for no, record in entries:
        rtype = record.get("type")
        if not isinstance(rtype, str):
            errors.append(f"line {no}: missing 'type' discriminator")
            continue
        try:
            schema = load_schema(args.schemas, rtype, layout)
        except (SchemaError, json.JSONDecodeError) as exc:
            errors.append(f"line {no}: {exc}")
            continue
        errors += [f"line {no}: {err}" for err in validate_record(record, schema)]
    if errors:
        for err in errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        return 1
    # Deterministic dispatch-start audit (handoff-routing § Dispatch Truncation
    # Detection): a substantive record whose author never appended a
    # dispatch-start for the same req_id starves truncation detection and the
    # stall ladder of their anchor. Warning, not error — the record itself is
    # valid; the discipline gap is the dispatched agent's to fix. Exempt: the
    # plan engine (never dispatched), human responses, and the terminal grader.
    exempt = {PLAN_ENGINE, HUMAN, GRADER}
    started: set[tuple[Any, Any]] = set()
    for no, record in entries:
        rtype, author, req = (
            record.get("type"),
            record.get("author"),
            record.get("req_id"),
        )
        if rtype == "dispatch-start":
            started.add((req, author))
        elif (
            rtype in SUBSTANTIVE
            and author not in exempt
            and (req, author) not in started
        ):
            # Every interpolated field is agent-authored: sanitize before the
            # terminal render, like the board (ADR: security lens in audit).
            print(
                f"handoff.py: warning: line {no}: {_sanitize(str(rtype))} by "
                f"{_sanitize(str(author))} has no prior dispatch-start for "
                f"{_sanitize(str(req))} — truncation detection is blind to "
                "that dispatch",
                file=sys.stderr,
            )
    print(f"{len(entries)} records valid")
    return 0


# Design-doc paths eligible for root-applied autofix. The prose home for the
# eligibility rules is the document-writing skill's review-checks.md § Autofix
# on Design-Doc Paths; this audit re-validates records against the same list.
DESIGN_DOC_PATH_RE = re.compile(r"^docs/(?:system-design\.md|adr/[^/]+\.md)$")
_REQ_TOKEN_RE = re.compile(r"REQ-[A-Z]+-\d{3}")
_ANCHOR_ID_RE = re.compile(r'<a id="([^"]*)"')
_LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")


def _autofix_static_errors(rec: dict[str, Any]) -> list[str]:
    """Step 1 of the autofix audit: one design-doc-autofix record against the
    allowlist bounds. The schema caps (category enum, size maxima) are
    re-checked so a hand-written log fails exactly like an appended one."""
    old = rec.get("old_content")
    new = rec.get("new_content")
    old = old if isinstance(old, str) else ""
    new = new if isinstance(new, str) else ""
    errs: list[str] = []
    if not DESIGN_DOC_PATH_RE.match(rec.get("file") or ""):
        errs.append("file is not an autofix-eligible design-doc path")
    if rec.get("category") not in ("writing-standards", "structural"):
        errs.append("category is not autofix-eligible")
    lines = rec.get("lines_changed")
    if not (isinstance(lines, int) and 1 <= lines <= 5):
        errs.append("lines_changed outside the 1-5 autofix cap")
    chars = rec.get("chars_changed")
    if not (isinstance(chars, int) and 1 <= chars <= 200):
        errs.append("chars_changed outside the 1-200 autofix cap")
    if any(ln.startswith("## ") for text in (old, new) for ln in text.splitlines()):
        errs.append("content touches a '## ' heading line")
    if sorted(_ANCHOR_ID_RE.findall(old)) != sorted(_ANCHOR_ID_RE.findall(new)):
        errs.append("anchor ids differ between old_content and new_content")
    if sorted(_REQ_TOKEN_RE.findall(old)) != sorted(_REQ_TOKEN_RE.findall(new)):
        errs.append("REQ-ID tokens differ between old_content and new_content")
    if any(
        ln.lstrip().startswith("```") for text in (old, new) for ln in text.splitlines()
    ):
        errs.append("content touches a code-fence line")
    if sorted(_LINK_TARGET_RE.findall(old)) != sorted(_LINK_TARGET_RE.findall(new)):
        errs.append("markdown link targets differ between old_content and new_content")
    if new != (rec.get("source_finding") or {}).get("fix"):
        errs.append("new_content is not byte-identical to source_finding.fix")
    return errs


def _git_lines(*argv: str) -> list[str] | None:
    """Run git; stdout lines on success, None on any failure (fail closed)."""
    try:
        proc = subprocess.run(
            ["git", *argv], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


def _covers_path(rec: dict[str, Any], path: str, since_seconds: float | None) -> bool:
    """Does this record authorise an uncommitted change to `path`?

    A design-doc-autofix names the file directly; a design-block covers every
    path it lists. Only records newer than the last commit count — an older
    record authorised a change that commit already absorbed."""
    if since_seconds is not None:
        ts = _ts_seconds(rec)
        if ts is None or ts <= since_seconds:
            return False
    if rec.get("type") == "design-doc-autofix":
        return bool(rec.get("file") == path)
    if rec.get("type") == "design-block":
        return any(
            isinstance(rec.get(k), list) and path in rec[k]
            for k in ("primary_paths", "supporting_paths")
        )
    return False


def cmd_audit_autofix(args: argparse.Namespace) -> int:
    """The autofix audit (code-quality-gate § Autofix Audit Procedure).

    Log-global by design: design docs are shared state, so records of every
    slice are audited — a per-slice scope would let a record appended under
    another req_id cover a dirty path while escaping validation. Step 1
    statically re-validates every design-doc-autofix record not superseded
    by a later design-block of its own slice. Step 2 confirms every
    uncommitted design-doc change — tracked edits and new untracked files —
    has a covering, non-superseded record newer than the last commit. Exit 0
    only when both pass. This command reads, never writes: on exit 1 the
    caller appends the failed_check="autofix-audit" build-failure per the
    gate skill.
    """
    entries, parse_errors = parse_log(args.file)
    missing_log = all(e.startswith("no handoff log") for e in parse_errors)
    if parse_errors and not missing_log:
        for err in parse_errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        print("handoff.py: log is not clean — run validate", file=sys.stderr)
        return 1

    # Per-slice supersession: the latest design-block line per req_id closes
    # that slice's audit loop (the reconciliation contract in the gate skill).
    last_db: dict[Any, int] = {}
    for no, rec in entries:
        if rec.get("type") == "design-block":
            last_db[rec.get("req_id")] = no
    failures: list[str] = []
    audited_lines: set[int] = set()
    for no, rec in entries:
        if rec.get("type") != "design-doc-autofix":
            continue
        if no <= last_db.get(rec.get("req_id"), 0):
            continue
        audited_lines.add(no)
        failures += [f"line {no}: {err}" for err in _autofix_static_errors(rec)]

    def finish(dirty_note: str) -> int:
        if failures:
            for f in failures:
                print(f"handoff.py: {f}", file=sys.stderr)
            return 1
        print(
            f"autofix audit clean: {len(audited_lines)} record(s) validated, "
            f"{dirty_note}"
        )
        return 0

    def fail_closed() -> int:
        # Step-1 findings still print: a fail-closed exit must not swallow
        # the record-level failures already established.
        for f in failures:
            print(f"handoff.py: {f}", file=sys.stderr)
        print(
            "handoff.py: cannot read the git worktree state; the audit fails closed",
            file=sys.stderr,
        )
        return 1

    if _git_lines("rev-parse", "--verify", "HEAD") is None:
        if _git_lines("rev-parse", "--git-dir") is not None:
            # Unborn HEAD: nothing is committed, so there is no baseline to
            # diff against. Step 1 ran; direct-edit detection starts at the
            # first commit rather than false-blocking a fresh scaffold.
            return finish(
                "no commit yet — direct-edit detection starts at the first commit"
            )
        return fail_closed()
    # --relative keeps diff output cwd-relative like ls-files: in a nested
    # checkout (project root below the git root) records carry project-relative
    # paths, and repo-root-relative diff output would never match a covering
    # record — a permanent false block.
    dirty = _git_lines(
        "diff",
        "--relative",
        "--name-only",
        "HEAD",
        "--",
        "docs/system-design.md",
        "docs/adr/",
    )
    untracked = _git_lines(
        "ls-files",
        "--others",
        "--exclude-standard",
        "--",
        "docs/system-design.md",
        "docs/adr/",
    )
    if dirty is None or untracked is None:
        return fail_closed()
    dirty = sorted({p for p in dirty + untracked if p})
    if dirty:
        # Baseline: the last commit touching the audited docs, not the last
        # commit anywhere — in a monorepo an unrelated commit must not expire
        # a still-covering record. No such commit → no baseline to expire
        # against (mirrors the unborn-HEAD path). An unreadable or unparsable
        # timestamp fails closed like the worktree reads above.
        head_ts = _git_lines(
            "log", "-1", "--format=%cI", "--", "docs/system-design.md", "docs/adr/"
        )
        if head_ts is None:
            return fail_closed()
        since: float | None = None
        if head_ts and head_ts[0].strip():
            since = _parse_iso_seconds(head_ts[0])
            if since is None:
                return fail_closed()
        for path in dirty:
            # A superseded autofix record does not cover: the superseding
            # design-block took ownership of the path (and itself covers).
            covered = any(
                _covers_path(rec, path, since)
                and (rec.get("type") != "design-doc-autofix" or no in audited_lines)
                for no, rec in entries
            )
            if not covered:
                failures.append(
                    f"{path}: uncommitted change with no covering design-doc-autofix "
                    "or design-block record since the last commit"
                )
    return finish(f"{len(dirty)} dirty design-doc path(s) covered")


def cmd_latest(args: argparse.Namespace) -> int:
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    match: LogEntry | None = None
    for no, record in entries:
        if record.get("type") != args.type:
            continue
        if args.req_id and record.get("req_id") != args.req_id:
            continue
        match = (no, record)
    if match is None:
        scope = f" for {args.req_id}" if args.req_id else ""
        print(f"handoff.py: no {args.type} record{scope}", file=sys.stderr)
        return 3
    no, record = match
    prefix = f"{no}\t" if args.with_line else ""
    if args.pretty:
        print(f"line {no}:")
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(prefix + dumps_canonical(record))
    return 0


def cmd_next_retry(args: argparse.Namespace) -> int:
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    design_idx: int | None = None
    for i, (_, record) in enumerate(entries):
        if record.get("type") == "design-block" and record.get("req_id") == args.req_id:
            design_idx = i
    if design_idx is None:
        print(f"handoff.py: no design-block record for {args.req_id}", file=sys.stderr)
        return 3
    count = sum(
        1
        for _, record in entries[design_idx + 1 :]
        if record.get("type") == "build-failure" and record.get("req_id") == args.req_id
    )
    value = count + 1
    try:
        retry_schema = load_schema(args.schemas, "build-failure")
        maximum = retry_schema.get("properties", {}).get("retry", {}).get("maximum")
    except (SchemaError, json.JSONDecodeError):
        maximum = None
    if isinstance(maximum, int) and value > maximum:
        print(
            f"handoff.py: retry {value} exceeds the schema maximum ({maximum})"
            " — escalate per Build-Failure Recovery instead of appending",
            file=sys.stderr,
        )
    print(value)
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    entries, errors = parse_log(args.file)
    if errors and not entries and all("no handoff log" in e for e in errors):
        decision: Decision | None = _escalate(
            "no-active-slice",
            "no handoff log; classify the request per the Agent Selection table",
        )
    elif errors:
        decision = _blocked(
            "dirty-log",
            "handoff log failed strict parse; run validate and repair upstream",
            errors=errors,
        )
    else:
        layout: dict[str, Any] = {}
        layout_path = Path(args.layout)
        decision = None
        if layout_path.is_file():
            try:
                layout = tomllib.loads(layout_path.read_text(encoding="utf-8"))
            except (OSError, tomllib.TOMLDecodeError) as exc:
                decision = _blocked(
                    "layout-unreadable",
                    f"{args.layout} exists but cannot be parsed; the roster gate fails closed: {exc}",
                )
        if decision is None:
            decision = _route_decision(entries, args.req_id, args.schemas, layout)
    # ensure_ascii: decisions embed agent-authored text (question, errors);
    # escaping non-ASCII keeps C1 controls from reaching the terminal raw.
    print(json.dumps(decision))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        with open(args.file, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return fail(f"no handoff log at {args.file}")
    except UnicodeDecodeError as exc:
        # Degrade like parse_log: a non-UTF-8 byte is a clean error, never a
        # UnicodeDecodeError traceback out of show.
        return fail(f"log is not valid UTF-8: {exc}")
    except OSError as exc:
        # Same hardening as parse_log: a directory at the log path or a
        # permissions error degrades to the clean error form, not a traceback.
        return fail(f"cannot read {args.file}: {exc}")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    rows: list[tuple[int, dict[str, Any] | None, str]] = []
    for no, line in enumerate(lines, 1):
        record: dict[str, Any] | None = None
        if line.strip():
            try:
                parsed = loads_strict(line)
                record = parsed if isinstance(parsed, dict) else None
            except ValueError:
                record = None
        rows.append((no, record, line))
    if args.type:
        rows = [r for r in rows if r[1] is not None and r[1].get("type") == args.type]
    if args.req_id:
        rows = [
            r for r in rows if r[1] is not None and r[1].get("req_id") == args.req_id
        ]
    if args.last > 0:
        rows = rows[-args.last :]
    for no, record, line in rows:
        # The log is agent-authored: never let its bytes drive the reader's
        # terminal (see _sanitize). The plain-text lines are cleaned here; the
        # JSON body relies on json.dumps, which escapes every C0 control byte.
        if record is None:
            print(f"-- line {no}: UNPARSEABLE")
            print(f"   {_sanitize(line)}")
        else:
            header = " · ".join(
                _sanitize(str(record[k]))
                for k in ("type", "req_id", "ts")
                if record.get(k) is not None
            )
            print(f"-- line {no}: {header}")
            print(json.dumps(record, ensure_ascii=False, indent=2))
    if not rows:
        print("no matching records")
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    # A non-UTF-8 stdout must degrade (replacement characters), never
    # traceback: the glyphs are cosmetic, the log content is what matters.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
    entries, errors = parse_log(args.file)
    if (
        not entries
        and any("no handoff log" in e for e in errors)
        and args.req_id is None
    ):
        print(f"no handoff log at {args.file}")
        return 0
    layout = read_layout(args.layout)
    roster, _roster_error = _roster(layout)
    if roster is None:
        roster = list(ROSTER_FLOOR)  # reader, not gate: fall back, never block
    # No --req-id renders every slice, oldest to newest; --req-id focuses one.
    if args.markdown:
        lines, code = render_view_md(
            entries,
            errors,
            args.req_id,
            roster,
            args.verbose,
            auto_grade=_auto_grade(layout),
            cost_lookup=_build_cost_lookup(entries),
        )
        print("\n".join(lines))
        return code
    # --color is an explicit request and beats the NO_COLOR env (per the
    # NO_COLOR spec); --no-color, --color, and --markdown are mutually
    # exclusive in argparse.
    color = args.color or (
        not args.no_color and os.environ.get("NO_COLOR") is None and sys.stdout.isatty()
    )
    lines, code = render_view(
        entries,
        errors,
        args.req_id,
        roster,
        color,
        args.verbose,
        auto_grade=_auto_grade(layout),
        cost_lookup=_build_cost_lookup(entries),
    )
    print("\n".join(lines))
    return code


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--file", default=DEFAULT_LOG, help=f"handoff log path (default: {DEFAULT_LOG})"
    )
    common.add_argument(
        "--schemas",
        default=DEFAULT_SCHEMAS,
        help=f"schema directory (default: {DEFAULT_SCHEMAS})",
    )
    common.add_argument(
        "--layout",
        default=DEFAULT_LAYOUT,
        help=f"project data file backing patternFrom (default: {DEFAULT_LAYOUT})",
    )
    parser = argparse.ArgumentParser(
        prog="handoff.py",
        description="Deterministic access to the .scratch/handoff.jsonl handoff log.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "append",
        parents=[common],
        help="stamp ts, validate a record from stdin, and append it in canonical form",
    )
    p.add_argument(
        "type", help="record type; selects schemas/scratch/<type>.schema.json"
    )
    p.set_defaults(func=cmd_append)
    p = sub.add_parser(
        "validate",
        parents=[common],
        help="parse and schema-check every record in the log",
    )
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser(
        "audit-autofix",
        parents=[common],
        help="re-validate design-doc-autofix records and detect uncovered "
        "design-doc edits (the quality gate's autofix audit; log-global)",
    )
    p.set_defaults(func=cmd_audit_autofix)
    p = sub.add_parser(
        "latest",
        parents=[common],
        help="print the latest record matching --type (and --req-id)",
    )
    p.add_argument("--type", required=True)
    p.add_argument("--req-id")
    p.add_argument("--pretty", action="store_true")
    p.add_argument(
        "--with-line", action="store_true", help="prefix output with '<line>\\t'"
    )
    p.set_defaults(func=cmd_latest)
    p = sub.add_parser(
        "next-retry",
        parents=[common],
        help="print the next build-failure retry value for --req-id",
    )
    p.add_argument("--req-id", required=True)
    p.set_defaults(func=cmd_next_retry)
    p = sub.add_parser(
        "route",
        parents=[common],
        help="execute the Handoff Conditions table; print the decision as JSON",
    )
    p.add_argument(
        "--req-id", help="route this slice (default: the latest record's req_id)"
    )
    p.set_defaults(func=cmd_route)
    p = sub.add_parser(
        "show",
        parents=[common],
        help="pretty-print recent records for human inspection",
    )
    p.add_argument("--last", type=int, default=10)
    p.add_argument("--type")
    p.add_argument("--req-id")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser(
        "view",
        parents=[common],
        help="render slice boards: header, review matrix, timeline",
    )
    p.add_argument(
        "--req-id",
        help="render just this slice (default: every slice, oldest to newest)",
    )
    p.add_argument(
        "--verbose", action="store_true", help="full finding descriptions and fixes"
    )
    color_group = p.add_mutually_exclusive_group()
    color_group.add_argument(
        "--color",
        action="store_true",
        help="force ANSI output even when stdout is not a TTY "
        "(e.g. an agent rendering the view into a conversation)",
    )
    color_group.add_argument(
        "--no-color",
        action="store_true",
        help="force plain output (automatic when stdout is not a TTY or NO_COLOR is set)",
    )
    color_group.add_argument(
        "--markdown",
        action="store_true",
        help="render the same board as Markdown (for transcripts that strip "
        "ANSI but render Markdown)",
    )
    p.set_defaults(func=cmd_view)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # args.func is set via set_defaults; type the local so the dispatch returns
    # int cleanly instead of Any (each cmd_* is annotated -> int).
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
