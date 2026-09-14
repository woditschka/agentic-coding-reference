#!/usr/bin/env python3
"""Give every agent one deterministic tool over the ledger: append, validate, query, route, show, view.

The composition root of the handoff package; it imports the package in submodule
form only. Exit codes: 0 success, 1 a validation, parse, or I/O failure, 2 usage,
3 no matching record. Route and view report their state in the output, not the code.
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

if importlib.util.find_spec("tomllib") is None:  # pragma: no cover
    sys.stderr.write("handoff.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2)

# A load by path from another working directory has no entry for this
# directory on sys.path; the package imports below need one.
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

from handoff.autofix import audit_log
from handoff.board import BoardOptions
from handoff.cost import build_cost_lookup
from handoff.gates import (
    design_block_uncovered,
    design_sync_missing,
    responding_to_dangling,
    review_anchor_missing,
)
from handoff.ledger import (
    Entry,
    failures_since,
    latest_of,
    typed_log,
    unstarted_substantive,
)
from handoff.non_goals import non_goal_delta
from handoff.records import (
    IMPLEMENTER,
    ROSTER_FLOOR,
    BuildPass,
    DesignBlock,
    DispatchStart,
    ReviewFeedback,
    parse_record,
)
from handoff.repository import GitRepository
from handoff.roster import auto_grade, reviewer_roster
from handoff.routing import (
    Decision,
    RouteInput,
    blocked,
    escalate,
    route_decision,
)
from handoff.schema import (
    LogEntry,
    SchemaError,
    canonicalize,
    decode_error,
    dumps_canonical,
    load_schema,
    loads_strict,
    log_schema_errors,
    only_missing_log,
    parse_log,
    parse_log_lenient,
    read_layout,
    sanitize,
    ts_now,
    validate_record,
)
from handoff.tiers import implementer_tier, window_tiers
from handoff.view import render_view, render_view_md

DEFAULT_LOG = ".scratch/handoff.jsonl"
DEFAULT_SCHEMAS = "schemas/scratch"
DEFAULT_LAYOUT = "scripts/layout.toml"
NO_MATCH_EXIT = 3
ENGINE_TIMEOUT_SECONDS = 120
ENGINE_TAIL_LINES = 3
# One bounded re-read outlasts a concurrent append caught before its newline landed.
ROUTE_REREAD_DELAY_SECONDS = 0.05


def report(message: str) -> None:
    """Print one message on the tool's stderr channel."""
    print(f"handoff.py: {message}", file=sys.stderr)


def fail(message: str) -> int:
    """Report the message and return the failure exit code."""
    report(message)
    return 1


class AppendRefusedError(Exception):
    """An append the gates refuse; the messages name the fix."""

    def __init__(self, *messages: str) -> None:
        """Carry one message per problem, in the order the gate found them."""
        super().__init__(messages[0] if messages else "")
        self.messages = list(messages)


def require_clean_log(path: str) -> list[LogEntry] | None:
    """Parse the log, or report every problem and return None."""
    entries, errors = parse_log(path)
    if errors:
        for error in errors:
            report(error)
        report("log is not clean — run validate")
        return None
    return entries


# --- append ------------------------------------------------------------------


def _line_count(path: Path) -> int:
    """Count the log's lines; a last line missing its newline is still a line."""
    if not path.exists():
        return 0
    data = path.read_bytes()
    return data.count(b"\n") + (0 if not data or data.endswith(b"\n") else 1)


def _clean_log(file_arg: str) -> tuple[Entry, ...]:
    """Type the whole log, or refuse the append while the log is not clean."""
    entries, parse_errors = parse_log(file_arg)
    if not only_missing_log(parse_errors):
        raise AppendRefusedError(*parse_errors, "log is not clean — run validate")
    return typed_log(entries)


def _append_gates(args: argparse.Namespace, raw: dict[str, Any]) -> None:
    """Run the append-time gate of the record's type; a refusal raises."""
    path = Path(args.file)
    record = parse_record(raw)
    refusal: str | None = None
    if isinstance(record, ReviewFeedback) and path.exists():
        refusal = review_anchor_missing(typed_log(parse_log_lenient(args.file)), record)
    elif isinstance(record, BuildPass) and path.exists():
        refusal = design_sync_missing(typed_log(parse_log_lenient(args.file)), record)
    elif isinstance(record, DispatchStart):
        refusal = responding_to_dangling(record, _line_count(path))
    elif isinstance(record, DesignBlock):
        log = _clean_log(args.file)
        candidate = Entry(len(log) + 1, raw, record)
        refusal = design_block_uncovered(log, candidate, GitRepository())
    if refusal:
        raise AppendRefusedError(refusal)


def _validated_record(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read the record from stdin, stamp its time, and validate it against its schema."""
    try:
        record = loads_strict(sys.stdin.read())
    except ValueError as exc:
        raise AppendRefusedError(
            f"stdin is not valid JSON: {decode_error(exc)}"
        ) from exc
    if not isinstance(record, dict):
        raise AppendRefusedError("record must be a JSON object")
    if record.get("type") != args.type:
        raise AppendRefusedError(
            f"record type {json.dumps(record.get('type'))} does not match argument '{args.type}'"
        )
    record["ts"] = ts_now()
    try:
        schema = load_schema(args.schemas, args.type, read_layout(args.layout))
    except SchemaError as exc:
        raise AppendRefusedError(str(exc)) from exc
    errors = validate_record(record, schema)
    if errors:
        raise AppendRefusedError(*errors)
    return record, schema


def _append_line(path: Path, line: str) -> int:
    """Append one canonical line and return its line number, exact under concurrent appends."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = line.encode("utf-8") + b"\n"
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
        descriptor = os.open(path, flags, 0o644)
        try:
            written = os.write(descriptor, payload)
            end = os.lseek(descriptor, 0, os.SEEK_CUR)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise AppendRefusedError(f"cannot append to {path}: {exc}") from exc
    if written != len(payload):
        raise AppendRefusedError(
            f"short write ({written} of {len(payload)} bytes) — the record is "
            "damaged; run validate before appending further"
        )
    # Bytes before this descriptor's end never change in an append-only log,
    # so the newline count of that prefix is this record's line number.
    prefix = path.read_bytes()[:end]
    start = end - len(payload)
    if start > 0 and prefix[start - 1 : start] != b"\n":
        report(
            "prior record was truncated — this record landed on the same line; "
            "run validate and repair"
        )
    return prefix.count(b"\n")


def _after_build_pass(args: argparse.Namespace, record: dict[str, Any]) -> None:
    """Run the review-plan engine after a build-pass on the default ledger."""
    if _targets_default_log(args.file):
        _run_review_plan_engine(record)
    else:
        report(
            "build-pass appended to a redirected ledger — no review-plan appended; "
            "route falls back to the full battery"
        )


def cmd_append(args: argparse.Namespace) -> int:
    """Validate a record from stdin and append it in canonical form."""
    try:
        record, schema = _validated_record(args)
        _append_gates(args, record)
        line = dumps_canonical(canonicalize(record, schema, schema))
        line_no = _append_line(Path(args.file), line)
    except AppendRefusedError as refused:
        for message in refused.messages:
            report(message)
        return 1
    print(f"appended {args.type} at line {line_no}")
    if args.type == "build-pass":
        _after_build_pass(args, record)
    return 0


_REQ_ID_ARGV = re.compile(r"REQ-[A-Z]+-[0-9]{3}")


def _targets_default_log(file_arg: str) -> bool:
    """Return whether the append landed on the default ledger, however spelled."""
    if file_arg == DEFAULT_LOG:
        return True
    try:
        return Path(file_arg).resolve() == Path(DEFAULT_LOG).resolve()
    except OSError:
        return False


def _run_review_plan_engine(record: dict[str, Any]) -> None:
    """Run the review-plan engine as a child; every defect degrades to the full battery."""
    engine = Path(__file__).resolve().parent / "grading.py"
    if not engine.is_file():
        report(
            "scripts/grading.py not found — no review-plan appended; "
            "route falls back to the full battery"
        )
        return
    req_id = record.get("req_id")
    # The one variable argv element is re-checked here: a caller-supplied
    # schema may be permissive, and fullmatch rejects the trailing newline.
    if not isinstance(req_id, str) or not _REQ_ID_ARGV.fullmatch(req_id):
        report(
            "build-pass req_id is not a clean REQ-XX-NNN token — "
            "no review-plan appended; route falls back to the full battery"
        )
        return
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-E",
                "-B",
                str(engine),
                "review-plan",
                "--feature",
                req_id,
            ],
            capture_output=True,
            text=True,
            timeout=ENGINE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report(
            f"review-plan engine did not run ({exc}) — route falls back to the full battery"
        )
        return
    if result.returncode != 0:
        tail = (
            (result.stderr or result.stdout).strip().splitlines()[-ENGINE_TAIL_LINES:]
        )
        for line in tail:
            report(sanitize(line))
        report(
            "review-plan engine failed — no plan appended; route falls back to the full battery"
        )
        return
    summary = result.stdout.strip()
    if summary:
        print(sanitize(summary))


# --- validate ----------------------------------------------------------------


def _schema_errors(entries: list[LogEntry], args: argparse.Namespace) -> list[str]:
    """Check every record against its schema."""
    try:
        layout = read_layout(args.layout)
    except SchemaError as exc:
        return [str(exc)]
    return log_schema_errors(entries, args.schemas, layout)


def _dispatch_start_warnings(entries: list[LogEntry]) -> list[str]:
    """Warn about a substantive record whose author never appended a dispatch-start for its slice."""
    return [
        f"warning: line {entry.no}: {sanitize(str(entry.type_name))} by "
        f"{sanitize(str(entry.author))} has no prior dispatch-start for "
        f"{sanitize(str(entry.req_id))} — truncation detection is blind to that dispatch"
        for entry in unstarted_substantive(typed_log(entries))
    ]


def cmd_validate(args: argparse.Namespace) -> int:
    """Parse and schema-check every record in the log."""
    entries, errors = parse_log(args.file)
    errors += _schema_errors(entries, args)
    if errors:
        for error in errors:
            report(error)
        return 1
    for warning in _dispatch_start_warnings(entries):
        report(warning)
    print(f"{len(entries)} records valid")
    return 0


# --- the autofix audit -------------------------------------------------------


def cmd_audit_autofix(args: argparse.Namespace) -> int:
    """Re-validate the open autofix records and detect uncovered design-doc edits, log-wide."""
    entries, parse_errors = parse_log(args.file)
    if not only_missing_log(parse_errors):
        for error in parse_errors:
            report(error)
        return fail("log is not clean — run validate")
    audit = audit_log(typed_log(entries), GitRepository())
    for failure in audit.failures:
        report(sanitize(failure))
    if audit.note is None:
        return fail("cannot read the git worktree state; the audit fails closed")
    if audit.failures:
        return 1
    print(f"autofix audit clean: {audit.validated} record(s) validated, {audit.note}")
    return 0


# --- queries -----------------------------------------------------------------


def cmd_latest(args: argparse.Namespace) -> int:
    """Print the latest record matching the type and, when given, the slice."""
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    match: LogEntry | None = None
    for no, record in entries:
        if record.get("type") != args.type:
            continue
        if args.req_id and record.get("req_id") != args.req_id:
            continue
        match = LogEntry(no, record)
    if match is None:
        scope = f" for {args.req_id}" if args.req_id else ""
        report(f"no {args.type} record{scope}")
        return NO_MATCH_EXIT
    no, record = match
    if args.pretty:
        print(f"line {no}:")
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        prefix = f"{no}\t" if args.with_line else ""
        print(prefix + dumps_canonical(record))
    return 0


def _retry_maximum(schemas_dir: str) -> int | None:
    """Return the build-failure schema's retry maximum, or None when it cannot be read."""
    try:
        schema = load_schema(schemas_dir, "build-failure")
    except SchemaError:
        return None
    maximum = schema.get("properties", {}).get("retry", {}).get("maximum")
    return maximum if isinstance(maximum, int) else None


def cmd_next_retry(args: argparse.Namespace) -> int:
    """Print the next build-failure retry value for the slice."""
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    records = [entry for entry in typed_log(entries) if entry.req_id == args.req_id]
    design = latest_of(records, DesignBlock)
    if design is None:
        report(f"no design-block record for {args.req_id}")
        return NO_MATCH_EXIT
    failures = failures_since(records, design[0].no)
    value = failures + 1
    maximum = _retry_maximum(args.schemas)
    if maximum is not None and value > maximum:
        report(
            f"retry {value} exceeds the schema maximum ({maximum})"
            " — escalate per Build-Failure Recovery instead of appending"
        )
    print(value)
    return 0


def _route_layout(layout_arg: str) -> tuple[dict[str, Any], Decision | None]:
    """Read the layout for routing; an unparseable file blocks the roster gate closed."""
    try:
        return read_layout(layout_arg), None
    except SchemaError as exc:
        return {}, blocked("layout-unreadable", f"{exc}; the roster gate fails closed")


def _decide(args: argparse.Namespace) -> Decision:
    """Compute the routing decision for the log, including the two states routing never sees."""
    entries, errors = parse_log(args.file)
    if not only_missing_log(errors):
        time.sleep(ROUTE_REREAD_DELAY_SECONDS)
        entries, errors = parse_log(args.file)
    if errors and not entries and only_missing_log(errors):
        return escalate(
            "no-active-slice",
            "no handoff log; classify the request per the Agent Selection table",
        )
    if errors:
        return blocked(
            "dirty-log",
            "handoff log failed strict parse; run validate and repair upstream",
            errors=errors,
        )
    layout, unreadable = _route_layout(args.layout)
    if unreadable is not None:
        return unreadable
    # Any prd-entry in the log computes the delta: the over-approximation
    # keeps a degraded record from suppressing the input Gate 1 reads.
    delta: tuple[str, ...] | None = ()
    if any(r.get("type") == "prd-entry" for _, r in entries):
        delta = non_goal_delta(GitRepository())
    return route_decision(RouteInput(entries, args.req_id, args.schemas, layout, delta))


def cmd_route(args: argparse.Namespace) -> int:
    """Print the routing decision as one JSON object; the exit code is always 0."""
    # ASCII escaping keeps agent-authored text from reaching the terminal raw.
    print(json.dumps(_decide(args).as_json()))
    return 0


def cmd_tier(args: argparse.Namespace) -> int:
    """Print the effort ladder's implementer tier for a slice as JSON, failing closed to the base."""
    entries, errors = parse_log(args.file)
    req_id = args.req_id
    if req_id is None and entries:
        latest = entries[-1][1].get("req_id")
        req_id = latest if isinstance(latest, str) and latest else None
    out = {"req_id": req_id, "agent": IMPLEMENTER, "reason": "no-records"}
    if not only_missing_log(errors):
        out["reason"] = "dirty-log"
    elif req_id is not None:
        records = [entry for entry in typed_log(entries) if entry.req_id == req_id]
        if records:
            tier = implementer_tier(records)
            out["agent"], out["reason"] = tier.agent, tier.reason
    print(json.dumps(out))
    return 0


def _show_rows(raw: str) -> list[tuple[int, dict[str, Any] | None, str]]:
    """Pair every raw line with its parsed object, None when the line does not parse."""
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    rows: list[tuple[int, dict[str, Any] | None, str]] = []
    for no, line in enumerate(lines, 1):
        record: dict[str, Any] | None = None
        if line.strip():
            try:
                parsed = loads_strict(line)
            except ValueError:
                parsed = None
            record = parsed if isinstance(parsed, dict) else None
        rows.append((no, record, line))
    return rows


def _print_row(no: int, record: dict[str, Any] | None, line: str) -> None:
    """Print one record for human inspection; plain text is sanitized, JSON escapes itself."""
    if record is None:
        print(f"-- line {no}: UNPARSEABLE")
        print(f"   {sanitize(line)}")
        return
    header = " · ".join(
        sanitize(str(record[k]))
        for k in ("type", "req_id", "ts")
        if record.get(k) is not None
    )
    print(f"-- line {no}: {header}")
    print(json.dumps(record, ensure_ascii=False, indent=2))


def cmd_show(args: argparse.Namespace) -> int:
    """Pretty-print recent records for human inspection."""
    try:
        with Path(args.file).open(encoding="utf-8", newline="") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return fail(f"no handoff log at {args.file}")
    except UnicodeDecodeError as exc:
        return fail(f"log is not valid UTF-8: {exc}")
    except OSError as exc:
        return fail(f"cannot read {args.file}: {exc}")
    rows = _show_rows(raw)
    if args.type:
        rows = [r for r in rows if r[1] is not None and r[1].get("type") == args.type]
    if args.req_id:
        rows = [
            r for r in rows if r[1] is not None and r[1].get("req_id") == args.req_id
        ]
    if args.last > 0:
        rows = rows[-args.last :]
    for no, record, line in rows:
        _print_row(no, record, line)
    if not rows:
        print("no matching records")
    return 0


def _window_tiers(log: Sequence[Entry]) -> dict[int, str]:
    """Map each implementer dispatch-start line to the effort tier the router derives for it."""
    by_req: dict[str, list[Entry]] = {}
    for entry in log:
        if isinstance(entry.req_id, str) and entry.req_id:
            by_req.setdefault(entry.req_id, []).append(entry)
    tiers: dict[int, str] = {}
    for records in by_req.values():
        tiers.update(window_tiers(records))
    return tiers


def cmd_view(args: argparse.Namespace) -> int:
    """Render the slice boards to the terminal or as Markdown."""
    # A non-UTF-8 stdout degrades to replacement characters; the glyphs are
    # cosmetic and the log content is what matters.
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
    log = typed_log(entries)
    try:
        layout = read_layout(args.layout)
    except SchemaError as exc:
        return fail(str(exc))
    roster = reviewer_roster(layout).roster
    # An explicit --color beats the NO_COLOR environment, per its spec.
    color = args.color or (
        not args.no_color and os.environ.get("NO_COLOR") is None and sys.stdout.isatty()
    )
    options = BoardOptions(
        req_id=args.req_id,
        roster=roster if roster is not None else list(ROSTER_FLOOR),
        color=color,
        verbose=args.verbose,
        auto_grade=auto_grade(layout),
        cost_lookup=build_cost_lookup(log),
        window_tiers=_window_tiers(log),
    )
    render = render_view_md if args.markdown else render_view
    lines, code = render(log, errors, options)
    print("\n".join(lines))
    return code


# --- the command line --------------------------------------------------------


def _common_options() -> argparse.ArgumentParser:
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
    return common


def _add_write_commands(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    common: argparse.ArgumentParser,
) -> None:
    append = sub.add_parser(
        "append",
        parents=[common],
        help="stamp ts, validate a record from stdin, and append it in canonical form",
    )
    append.add_argument(
        "type", help="record type; selects schemas/scratch/<type>.schema.json"
    )
    append.set_defaults(func=cmd_append)
    validate = sub.add_parser(
        "validate",
        parents=[common],
        help="parse and schema-check every record in the log",
    )
    validate.set_defaults(func=cmd_validate)
    audit = sub.add_parser(
        "audit-autofix",
        parents=[common],
        help="re-validate design-doc-autofix and prd-autofix records and detect "
        "uncovered design-doc edits (the quality gate's autofix audit; log-global)",
    )
    audit.set_defaults(func=cmd_audit_autofix)


def _add_query_commands(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    common: argparse.ArgumentParser,
) -> None:
    latest = sub.add_parser(
        "latest",
        parents=[common],
        help="print the latest record matching --type (and --req-id)",
    )
    latest.add_argument("--type", required=True)
    latest.add_argument("--req-id")
    latest.add_argument("--pretty", action="store_true")
    latest.add_argument(
        "--with-line", action="store_true", help="prefix output with '<line>\\t'"
    )
    latest.set_defaults(func=cmd_latest)
    next_retry = sub.add_parser(
        "next-retry",
        parents=[common],
        help="print the next build-failure retry value for --req-id",
    )
    next_retry.add_argument("--req-id", required=True)
    next_retry.set_defaults(func=cmd_next_retry)
    route = sub.add_parser(
        "route",
        parents=[common],
        help="execute the Handoff Conditions table; print the decision as JSON",
    )
    route.add_argument(
        "--req-id", help="route this slice (default: the latest record's req_id)"
    )
    route.set_defaults(func=cmd_route)
    tier = sub.add_parser(
        "tier",
        parents=[common],
        help="print the effort ladder's implementer tier for a slice as JSON",
    )
    tier.add_argument(
        "--req-id", help="derive this slice (default: the latest record's req_id)"
    )
    tier.set_defaults(func=cmd_tier)


def _add_reader_commands(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    common: argparse.ArgumentParser,
) -> None:
    show = sub.add_parser(
        "show",
        parents=[common],
        help="pretty-print recent records for human inspection",
    )
    show.add_argument("--last", type=int, default=10)
    show.add_argument("--type")
    show.add_argument("--req-id")
    show.set_defaults(func=cmd_show)
    view = sub.add_parser(
        "view",
        parents=[common],
        help="render slice boards: header, review matrix, timeline",
    )
    view.add_argument(
        "--req-id",
        help="render just this slice (default: every slice, oldest to newest)",
    )
    view.add_argument(
        "--verbose", action="store_true", help="full finding descriptions and fixes"
    )
    color_group = view.add_mutually_exclusive_group()
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
    view.set_defaults(func=cmd_view)


def build_parser() -> argparse.ArgumentParser:
    """Build the command line: the shared options and the nine subcommands."""
    common = _common_options()
    parser = argparse.ArgumentParser(
        prog="handoff.py",
        description="Deterministic access to the .scratch/handoff.jsonl handoff log.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_write_commands(sub, common)
    _add_query_commands(sub, common)
    _add_reader_commands(sub, common)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the chosen subcommand."""
    args = build_parser().parse_args(argv)
    func: Callable[[argparse.Namespace], int] = args.func
    return func(args)


if __name__ == "__main__":
    sys.exit(main())
