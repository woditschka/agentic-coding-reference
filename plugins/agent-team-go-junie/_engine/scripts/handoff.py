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

This file is the CLI entry point — a launcher over the handoff package (ADR
2026-07-17 runtime-package-layout). The logic lives in four package modules it
composes:

  handoff.schema   the byte contract — loads_strict, the draft-07 subset
                   validator, canonicalize/dumps_canonical, layout + schema
                   loading, parse_log, ts_now (the log's one clock)
  handoff.records  the typed record model — the dataclasses, lenient lifts,
                   registries, parse_record, and the pipeline vocabulary
  handoff.routing  the deterministic routing core — Entry, the states, and
                   _route_decision (the Handoff Conditions table)
  handoff.view     the human-facing board renderer and the cost overlay

The package's public surface is declared once in handoff/__init__.py, so
`import handoff; handoff.dumps_canonical` and every `handoff.<name>` access
keeps working — grading.py and the tests rely on it. This launcher never
does bare `import handoff`; it imports submodule-form only.

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
schemas in schemas/scratch/ use (see SUPPORTED in handoff.schema). Any other
keyword is a loud error, never a silent pass. Extending a schema beyond the
subset means extending that validator first; tests/handoff/test_schema.py sweeps
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
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("handoff.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2) from None

# The handoff package resolves via this script's own directory — the directory
# python already puts on sys.path when handoff.py is run as a script. When it is
# loaded by path instead (the grading engine's importlib load, a test loader) from
# another cwd, that entry is absent, so add it here before the package imports
# below; this keeps the tool's cwd-independence (ADR 2026-07-17
# runtime-package-layout).
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

# --- Composition (ADR 2026-07-17 runtime-package-layout) --------------------
# This entry point is a launcher: it composes the handoff package. It imports
# only the names its cmd_* layer uses, submodule-form (never bare `import
# handoff`, which a solo strict run would resolve to this file). The full
# public surface — `import handoff; handoff.<name>` for grading.py and the
# tests — is declared once in handoff/__init__.py, not here.
from handoff.records import (
    GRADER,
    HUMAN,
    IMPLEMENTER,
    PLAN_ENGINE,
    ROSTER_FLOOR,
    SUBSTANTIVE,
    parse_record,
)
from handoff.routing import (
    Decision,
    Entry,
    _auto_grade,
    _blocked,
    _escalate,
    _roster,
    _route_decision,
    implementer_tier,
    implementer_window_tiers,
)
from handoff.schema import (
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
    ts_now,
    validate_record,
)
from handoff.view import (
    _build_cost_lookup,
    _parse_iso_seconds,
    _ts_seconds,
    render_view,
    render_view_md,
)

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
    # moment the referent set is known. Under a concurrent append the count
    # can only lag, so the check may over-reject a referent written an
    # instant ago — never accept a dangling one (the log only grows), and a
    # real referent was written before its responder was dispatched.
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
    # Lock-free append (ADR 2026-08-16 lock-free-ledger-appends in the
    # reference): one write() on an O_APPEND descriptor lands atomically at
    # EOF — the kernel serializes regular-file writes on the inode lock —
    # so concurrent records never interleave. There is deliberately no
    # pre-write tail check: a reader cannot tell a crash-damaged tail from
    # a concurrent write still landing, so any check-then-act here could
    # dirty a healthy log. O_NOFOLLOW refuses a planted symlink at the log
    # path; O_BINARY keeps Windows from translating newlines (both 0 where
    # the platform lacks them). A short write (disk full) must not be
    # continued — a second write could interleave with another writer.
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        fd = os.open(path, flags, 0o644)
        try:
            written = os.write(fd, payload)
            end = os.lseek(fd, 0, os.SEEK_CUR)
        finally:
            os.close(fd)
    except OSError as exc:
        return fail(f"cannot append to {path}: {exc}")
    if written != len(payload):
        return fail(
            f"short write ({written} of {len(payload)} bytes) — the record is "
            "damaged; run validate before appending further"
        )
    # The receipt is exact under concurrency: this descriptor's offset ends
    # at OUR write, and bytes before it never change in an append-only log,
    # so the newline count of that prefix is this record's line number no
    # matter what other writers append afterwards.
    with open(path, "rb") as fh:
        prefix = fh.read(end)
    start = end - len(payload)
    if start > 0 and prefix[start - 1 : start] != b"\n":
        # Only a crash-damaged tail lacks its newline (disk full, OS crash);
        # this record just glued onto the fragment. The log was already
        # dirty — warn, and route/validate block until it is repaired.
        print(
            "handoff.py: prior record was truncated — this record landed on "
            "the same line; run validate and repair",
            file=sys.stderr,
        )
    line_no = prefix.count(b"\n")
    print(f"appended {args.type} at line {line_no}")
    if args.type == "build-pass":
        if _targets_default_log(args.file):
            _run_review_plan_engine(record)
        else:
            print(
                "handoff.py: build-pass appended to a redirected ledger — no "
                "review-plan appended; route falls back to the full battery",
                file=sys.stderr,
            )
    return 0


_REQ_ID_ARGV = re.compile(r"REQ-[A-Z]+-[0-9]{3}")


def _targets_default_log(file_arg: str) -> bool:
    """True when the append landed on the default ledger, however spelled.
    Resolved-path comparison, not string equality: `./.scratch/handoff.jsonl`
    and absolute spellings still trigger the engine; only a genuine redirect
    to another path skips it."""
    if file_arg == DEFAULT_LOG:
        return True
    try:
        return Path(file_arg).resolve() == Path(DEFAULT_LOG).resolve()
    except OSError:
        return False


def _run_review_plan_engine(record: dict[str, Any]) -> None:
    """Run the review-plan engine the moment a build-pass lands on the
    default ledger — a child process sharing the append's cwd and tree
    state, the exact moment the plan's basis must snapshot. The eval record
    showed the two-command contract skipped on ~13% of gate-passes, each
    skip silently buying a full battery; composing the engine into the
    append makes the plan exist by construction. Fail-open on every defect
    — a missing engine, a bad req_id, a non-zero exit, a hang — because the
    append already succeeded and `route` fails closed to the full battery,
    the pre-plan behavior. A `--file`-redirected append never triggers it:
    the redirect is harness-internal by design, and the engine writes only
    the default ledger. The trigger compares resolved paths, so an
    equivalent spelling of the default still fires; a genuine redirect
    announces the skip on stderr.

    Spawn safety (the confinement policy's sanction rests on all three):
    the target is the constant sibling path — never input-derived; the one
    variable argv element, req_id, is re-checked with fullmatch here even
    though the shipped schema already patterns it (a caller-supplied
    --schemas can be permissive; fullmatch also rejects the trailing
    newline `$` tolerates); and the child runs -E -B so PYTHON* env never
    shapes its imports. List argv, no shell; stdout and the stderr tail are
    _sanitize-d before echo — record-derived bytes never reach the terminal
    raw (handoff.schema's choke-point doctrine)."""
    engine = Path(__file__).resolve().parent / "grading.py"
    if not engine.is_file():
        print(
            "handoff.py: scripts/grading.py not found — no review-plan "
            "appended; route falls back to the full battery",
            file=sys.stderr,
        )
        return
    req_id = record.get("req_id")
    if not isinstance(req_id, str) or not _REQ_ID_ARGV.fullmatch(req_id):
        print(
            "handoff.py: build-pass req_id is not a clean REQ-XX-NNN token — "
            "no review-plan appended; route falls back to the full battery",
            file=sys.stderr,
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
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(
            f"handoff.py: review-plan engine did not run ({exc}) — "
            "route falls back to the full battery",
            file=sys.stderr,
        )
        return
    if result.returncode != 0:
        tail = (result.stderr or result.stdout).strip().splitlines()[-3:]
        for ln in tail:
            print(f"handoff.py: {_sanitize(ln)}", file=sys.stderr)
        print(
            "handoff.py: review-plan engine failed — no plan appended; "
            "route falls back to the full battery",
            file=sys.stderr,
        )
        return
    summary = result.stdout.strip()
    if summary:
        print(_sanitize(summary))


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


# Doc paths eligible for root-applied autofix, per record type. The prose home
# for the eligibility rules is the document-writing skill's autofix-protocol.md
# § Autofix on Design-Doc Paths (and its PRD extension); this audit re-validates
# records against the same lists. A design-doc-autofix record names a design-doc
# path; a prd-autofix record names exactly docs/prd.md.
DESIGN_DOC_PATH_RE = re.compile(r"^docs/(?:system-design\.md|adr/[^/]+\.md)$")
PRD_PATH = "docs/prd.md"
_REQ_TOKEN_RE = re.compile(r"REQ-[A-Z]+-\d{3}")
_ANCHOR_ID_RE = re.compile(r'<a id="([^"]*)"')
_LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")


def _autofix_static_errors(rec: dict[str, Any]) -> list[str]:
    """Step 1 of the autofix audit: one autofix record (design-doc-autofix or
    prd-autofix) against the allowlist bounds. The schema caps (category enum,
    size maxima) are re-checked so a hand-written log fails exactly like an
    appended one. The path predicate follows the record type: a prd-autofix
    names exactly docs/prd.md; a design-doc-autofix names a design-doc path."""
    old = rec.get("old_content")
    new = rec.get("new_content")
    old = old if isinstance(old, str) else ""
    new = new if isinstance(new, str) else ""
    errs: list[str] = []
    if rec.get("type") == "prd-autofix":
        if (rec.get("file") or "") != PRD_PATH:
            errs.append("file is not the autofix-eligible PRD path (docs/prd.md)")
    elif not DESIGN_DOC_PATH_RE.match(rec.get("file") or ""):
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
    if rec.get("type") == "prd-autofix" and any(
        _NG_ROW_RE.match(ln) for text in (old, new) for ln in text.splitlines()
    ):
        errs.append(
            "content touches a Non-Goals table row — never autofix-eligible; "
            "scope stays with product-requirements-expert (Gate 1 scope-lock)"
        )
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
    """Run git; stdout lines on success, None on any failure (fail closed).
    ValueError covers a non-UTF-8 blob surfacing as UnicodeDecodeError from
    the text-mode decode — route must degrade, never traceback."""
    try:
        proc = subprocess.run(
            ["git", *argv], capture_output=True, text=True, check=False
        )
    except (OSError, ValueError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


# Up to 3 leading spaces: still a table row when rendered, so still guarded.
_NG_ROW_RE = re.compile(r"^ {0,3}\|\s*(NG-[0-9]+)\s*\|")

# Scope-lock reads docs/prd.md on the route hot path; a pathological file
# fails closed rather than being loaded.
_PRD_SIZE_CAP = 4_000_000


def _ng_rows(text: str) -> dict[str, str]:
    """Non-Goals table rows of a prd.md text, keyed by NG id. The stripped
    whole line is the compared value: any reword of a row is a change."""
    rows: dict[str, str] = {}
    for line in text.splitlines():
        m = _NG_ROW_RE.match(line)
        if m:
            rows[m.group(1)] = line.strip()
    return rows


def _ng_delta() -> tuple[str, ...] | None:
    """Non-Goals rows in docs/prd.md changed or removed against HEAD — the
    scope-lock input to Gate 1 (route-spec.md § Gate 1), computed here so the
    routing core stays deterministic over its inputs.

    Grace states return (): no repository, an unborn HEAD, or a prd.md
    untracked at HEAD — no recorded baseline exists to protect. Added rows
    never enter the delta: recording newly declined scope is normal scoping
    work. Everything else returns None and the gate fails closed on it: a git
    binary that fails to launch, any read failing past the grace states, a
    non-UTF-8 blob or worktree file, an oversized prd.md. The repository and
    unborn-HEAD probes run git directly so an OSError (git unavailable) stays
    distinguishable from a nonzero exit (the grace states)."""
    try:
        repo = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if repo.returncode != 0:
        return ()
    if head.returncode != 0:
        return ()
    # --show-prefix maps the cwd-relative docs/prd.md to its repo-relative
    # path, so a nested checkout (project root below the git root) reads the
    # same file the pipeline edits.
    prefix_lines = _git_lines("rev-parse", "--show-prefix")
    if prefix_lines is None:
        return None
    prefix = prefix_lines[0].strip() if prefix_lines else ""
    repo_path = f"{prefix}docs/prd.md"
    # --full-tree: ls-tree resolves pathspecs against the cwd by default, so
    # the repo-relative prefix path would silently miss in a nested checkout.
    tracked = _git_lines(
        "ls-tree", "--full-tree", "--name-only", "HEAD", "--", repo_path
    )
    if tracked is None:
        return None
    if not any(p.strip() for p in tracked):
        return ()
    old_lines = _git_lines("show", f"HEAD:{repo_path}")
    if old_lines is None:
        return None
    prd = Path("docs/prd.md")
    try:
        if prd.is_file() and prd.stat().st_size > _PRD_SIZE_CAP:
            return None
        new_text = prd.read_text(encoding="utf-8")
    except FileNotFoundError:
        new_text = ""
    except (OSError, ValueError):
        return None
    new_rows = _ng_rows(new_text)
    return tuple(
        sorted(
            ng
            for ng, line in _ng_rows("\n".join(old_lines)).items()
            if new_rows.get(ng) != line
        )
    )


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

    Log-global by design: the audited docs are shared state, so records of
    every slice are audited — a per-slice scope would let a record appended
    under another req_id cover a dirty path while escaping validation. Step 1
    statically re-validates every autofix record not superseded by its
    slice's later owning-expert record: a design-doc-autofix by a later
    design-block, a prd-autofix by a later prd-entry. Step 2 confirms every
    uncommitted design-doc change — tracked edits and new untracked files —
    has a covering, non-superseded record newer than the last commit; the
    dirty scan stays design-doc-scoped (docs/prd.md is deliberately outside
    it — see the prd-autofix ADR). Exit 0 only when both pass. This command
    reads, never writes: on exit 1 the caller appends the
    failed_check="autofix-audit" build-failure per the gate skill.
    """
    entries, parse_errors = parse_log(args.file)
    missing_log = all(e.startswith("no handoff log") for e in parse_errors)
    if parse_errors and not missing_log:
        for err in parse_errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        print("handoff.py: log is not clean — run validate", file=sys.stderr)
        return 1

    # Per-slice supersession: the latest owning-expert record line per req_id
    # closes that slice's audit loop (the reconciliation contract in the gate
    # skill) — design-block for design-doc autofixes, prd-entry for PRD ones.
    last_db: dict[Any, int] = {}
    last_pe: dict[Any, int] = {}
    for no, rec in entries:
        if rec.get("type") == "design-block":
            last_db[rec.get("req_id")] = no
        elif rec.get("type") == "prd-entry":
            last_pe[rec.get("req_id")] = no
    superseder = {"design-doc-autofix": last_db, "prd-autofix": last_pe}
    failures: list[str] = []
    audited_lines: set[int] = set()
    for no, rec in entries:
        rtype = rec.get("type")
        closing = superseder.get(rtype) if isinstance(rtype, str) else None
        if closing is None:
            continue
        if no <= closing.get(rec.get("req_id"), 0):
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
    if errors and not all("no handoff log" in e for e in errors):
        # A parse error can be an append caught in flight: a concurrent
        # writer's multi-page write is reader-visible before its final
        # newline lands. One bounded re-read outlasts any in-flight write;
        # damage that persists is real and blocks below (fail-closed).
        time.sleep(0.05)
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
            # The delta is consumed only when a prd-entry gates (Gate 1). The
            # condition deliberately over-approximates — any prd-entry in the
            # log — because mirroring routing's latest-substantive selection
            # here would diverge on records the lenient lift degrades, and a
            # crafted record must never suppress the delta on a log Gate 1
            # reads. Cost when it over-fires: a few git subprocesses.
            ng_delta: tuple[str, ...] | None = ()
            if any(r.get("type") == "prd-entry" for _, r in entries):
                ng_delta = _ng_delta()
            decision = _route_decision(
                entries, args.req_id, args.schemas, layout, ng_delta
            )
    # ensure_ascii: decisions embed agent-authored text (question, errors);
    # escaping non-ASCII keeps C1 controls from reaching the terminal raw.
    print(json.dumps(decision))
    return 0


def cmd_tier(args: argparse.Namespace) -> int:
    """Print the effort ladder's derivation for one slice as JSON.

    The queryable half of the tier trace: {"req_id", "agent", "reason"} from
    routing.implementer_tier — the same fold route uses to name the
    implementer dispatch. Read-only and fail-closed like the board: any
    problem (missing or dirty log, no records, no req_id) reports the base
    IMPLEMENTER with the problem as the reason, exit 0."""
    entries, errors = parse_log(args.file)
    req_id = args.req_id
    if req_id is None and entries:
        latest = entries[-1][1].get("req_id")
        req_id = latest if isinstance(latest, str) and latest else None
    out = {"req_id": req_id, "agent": IMPLEMENTER, "reason": "no-records"}
    if errors and not all("no handoff log" in e for e in errors):
        out["reason"] = "dirty-log"
    elif req_id is not None:
        recs = [
            Entry(no, raw, parse_record(raw))
            for no, raw in entries
            if raw.get("req_id") == req_id
        ]
        if recs:
            out["agent"], out["reason"] = implementer_tier(recs)
    print(json.dumps(out))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        # newline="": the readers' shared \n-only domain — see parse_log.
        with open(args.file, encoding="utf-8", newline="") as fh:
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


def _stamp_window_tiers(entries: list[LogEntry]) -> None:
    """Annotate implementer dispatch-start records with their window's
    effort tier for the board (routing.implementer_window_tiers is the single
    derivation source). In-memory only, and the stamp key is scrubbed from
    every record first — a ledger record carrying a literal `_tier` field is
    agent-authored input, and the board must render only the derivation,
    never a self-claimed tier. The fold's activation gate keeps unrated
    slices all-base, so a pre-ladder ledger never shows a counterfactual
    annotation; the base tier stays unstamped so boards read quiet."""
    by_req: dict[str, list[Entry]] = {}
    raw_by_no = dict(entries)
    for no, raw in entries:
        raw.pop("_tier", None)
        rid = raw.get("req_id")
        if isinstance(rid, str) and rid:
            by_req.setdefault(rid, []).append(Entry(no, raw, parse_record(raw)))
    for recs in by_req.values():
        for no, tier in implementer_window_tiers(recs).items():
            if tier != IMPLEMENTER:
                raw_by_no[no]["_tier"] = "routine"


def cmd_view(args: argparse.Namespace) -> int:
    # A non-UTF-8 stdout must degrade (replacement characters), never
    # traceback: the glyphs are cosmetic, the log content is what matters.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
    entries, errors = parse_log(args.file)
    _stamp_window_tiers(entries)
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
        help="re-validate design-doc-autofix and prd-autofix records and detect "
        "uncovered design-doc edits (the quality gate's autofix audit; log-global)",
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
        "tier",
        parents=[common],
        help="print the effort ladder's implementer tier for a slice as JSON",
    )
    p.add_argument(
        "--req-id", help="derive this slice (default: the latest record's req_id)"
    )
    p.set_defaults(func=cmd_tier)
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
