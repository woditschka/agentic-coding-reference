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
  view        render one slice as a terminal status view: header,
              review-convergence matrix, timeline in append order

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
schemas in schemas/scratch/ use (see SUPPORTED below). Any other keyword is a
loud error, never a silent pass. Extending a schema beyond the subset means
extending this validator first; test_handoff.py sweeps every repo schema to
enforce that.

One non-standard keyword, `patternFrom`, sources a string `pattern` from project
data instead of hard-coding it: a node carrying `patternFrom: "<key>"` resolves
<key> from scripts/layout.toml and validates as if that value were its `pattern`.
This keeps a single source for facts engines and layout share — e.g. the test
name shape lives once in layout.toml's `test_name_pattern`. If layout.toml is
absent or the key is unset, the shape check is simply skipped — never block on a
missing optional source.

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
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    sys.stderr.write("handoff.py requires Python 3.11+ (tomllib)\n")
    raise SystemExit(2)

DEFAULT_LOG = ".scratch/handoff.jsonl"
DEFAULT_SCHEMAS = "schemas/scratch"
DEFAULT_LAYOUT = "scripts/layout.toml"

# The mandatory reviewer floor (handoff-routing skill, Gate 4). layout.toml
# [harness].extra_reviewers extends it; nothing removes a floor reviewer.
ROSTER_FLOOR = ("code-quality-reviewer", "test-reviewer", "security-reviewer", "doc-reviewer")
# Substantive record types (handoff-routing skill, Dispatch Truncation Detection).
SUBSTANTIVE = frozenset((
    "build-pass", "build-failure", "review-feedback", "prd-entry", "design-block",
    "consultation-response",
))
IMPLEMENTER = "feature-implementer"
DESIGNER = "system-design-expert"
PRODUCT = "product-requirements-expert"

# Keywords that carry no validation semantics.
ANNOTATIONS = {"$schema", "$id", "title", "description", "default", "examples", "definitions"}
# The closed validation vocabulary. Anything else fails loudly.
SUPPORTED = {
    "$ref", "type", "const", "enum", "required", "properties",
    "additionalProperties", "items", "minItems", "maxItems",
    "pattern", "patternFrom", "format", "minLength", "maxLength", "minimum", "maximum",
}
SUPPORTED_FORMATS = {"date-time"}

DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaError(Exception):
    pass


def _reject_constant(name):
    raise ValueError(f"{name} is not valid JSON")


def loads_strict(text):
    """json.loads that rejects NaN/Infinity — the log must stay RFC 8259-parseable."""
    return json.loads(text, parse_constant=_reject_constant)


def _decode_error(exc):
    return exc.msg if isinstance(exc, json.JSONDecodeError) else str(exc)


def schema_equal(a, b):
    """Draft-07 equality: booleans never equal numbers (Python's True == 1 must not)."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def unsupported_keywords(schema, path="#"):
    """Walk a schema document; return locations of keywords outside the subset."""
    found = []
    if not isinstance(schema, dict):
        return found
    for key, val in schema.items():
        here = f"{path}/{key}"
        if key not in ANNOTATIONS and key not in SUPPORTED:
            found.append(here)
        if key == "format" and val not in SUPPORTED_FORMATS:
            found.append(f"{here}={val}")
    for key in ("items", "additionalProperties"):
        if key not in schema:
            continue
        sub = schema[key]
        if isinstance(sub, dict):
            found += unsupported_keywords(sub, f"{path}/{key}")
        elif not (key == "additionalProperties" and isinstance(sub, bool)):
            found.append(f"{path}/{key} (unsupported schema form: {type(sub).__name__})")
    for container in ("properties", "definitions"):
        sub = schema.get(container)
        if isinstance(sub, dict):
            for name, subschema in sub.items():
                if isinstance(subschema, dict):
                    found += unsupported_keywords(subschema, f"{path}/{container}/{name}")
                else:
                    found.append(
                        f"{path}/{container}/{name} (unsupported schema form:"
                        f" {type(subschema).__name__})"
                    )
    return found


def resolve_ref(schema, root):
    hops = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/definitions/"
        if not isinstance(ref, str) or not ref.startswith(prefix):
            raise SchemaError(f"unsupported $ref '{ref}' (only {prefix}<name> is supported)")
        name = ref[len(prefix):]
        definitions = root.get("definitions", {})
        if name not in definitions:
            raise SchemaError(f"$ref '{ref}' has no matching definition")
        schema = definitions[name]
        hops += 1
        if hops > 10:
            raise SchemaError("$ref chain too deep")
    return schema


def validate_value(value, schema, root, path, errors):
    schema = resolve_ref(schema, root)
    if not isinstance(schema, dict):
        raise SchemaError(f"unsupported schema form at {path}: {type(schema).__name__}")
    if "const" in schema and not schema_equal(value, schema["const"]):
        errors.append(
            f"{path}: expected const {json.dumps(schema['const'])}, got {json.dumps(value)}"
        )
        return
    if "enum" in schema and not any(schema_equal(value, m) for m in schema["enum"]):
        errors.append(f"{path}: {json.dumps(value)} not in enum {json.dumps(schema['enum'])}")
        return
    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        unknown = [t for t in allowed if t not in TYPE_CHECKS]
        if unknown:
            raise SchemaError(f"unknown type {unknown} in schema at {path}")
        if not any(TYPE_CHECKS[t](value) for t in allowed):
            errors.append(
                f"{path}: expected type {'/'.join(allowed)}, got {type(value).__name__}"
            )
            return
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {json.dumps(value)} does not match pattern {schema['pattern']}")
        if schema.get("format") == "date-time" and not DATE_TIME_RE.match(value):
            errors.append(f"{path}: {json.dumps(value)} is not an ISO 8601 date-time")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} above maximum {schema['maximum']}")
    elif isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}: missing required field '{req}'")
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties")
        for key, val in value.items():
            if key in props:
                validate_value(val, props[key], root, f"{path}.{key}", errors)
            elif extra is False:
                errors.append(f"{path}: unexpected field '{key}' (additionalProperties: false)")
            elif isinstance(extra, dict):
                validate_value(val, extra, root, f"{path}.{key}", errors)
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems {schema['maxItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                validate_value(item, items, root, f"{path}[{i}]", errors)


def validate_record(record, schema):
    errors = [
        f"schema: unsupported keyword at {kw} — extend the handoff.py mini-validator first"
        for kw in unsupported_keywords(schema)
    ]
    if errors:
        return errors
    try:
        validate_value(record, schema, schema, "$", errors)
    except SchemaError as exc:
        errors.append(f"schema: {exc}")
    return errors


def canonicalize(value, schema, root):
    """Reorder fields to schema declaration order; unknown keys sort last."""
    if isinstance(schema, dict):
        try:
            schema = resolve_ref(schema, root)
        except SchemaError:
            schema = {}
    else:
        schema = {}
    if isinstance(value, dict):
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties")
        extra_schema = extra if isinstance(extra, dict) else {}
        ordered = {}
        for key in props:
            if key in value:
                ordered[key] = canonicalize(value[key], props[key], root)
        for key in sorted(k for k in value if k not in props):
            ordered[key] = canonicalize(value[key], extra_schema, root)
        return ordered
    if isinstance(value, list):
        items = schema.get("items", {})
        return [canonicalize(v, items, root) for v in value]
    return value


def dumps_canonical(record):
    return json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(", ", ": "))


def read_layout(layout_path):
    """Parse scripts/layout.toml into a dict. Absence is not an error: a missing
    or unreadable file yields {}, so any `patternFrom` simply goes unenforced."""
    try:
        return tomllib.loads(Path(layout_path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def layout_lookup(data, dotted):
    """Resolve a dotted key (e.g. 'test_name_pattern' or 'section.key') in the
    parsed layout; return None if any segment is missing."""
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def apply_pattern_from(schema, layout):
    """Resolve every `patternFrom` in the schema tree into a concrete `pattern`
    sourced from layout.toml. The node keeps its `patternFrom` (it documents the
    dependency and stays in the supported vocabulary); it gains a `pattern` only
    when the referenced key resolves to a string. An unresolved key leaves no
    pattern, so the shape check is skipped — never block on a missing source."""
    if not isinstance(schema, dict):
        return
    key = schema.get("patternFrom")
    if isinstance(key, str):
        val = layout_lookup(layout, key)
        if isinstance(val, str):
            schema.setdefault("pattern", val)
    for sub in schema.get("properties", {}).values():
        apply_pattern_from(sub, layout)
    for sub in schema.get("definitions", {}).values():
        apply_pattern_from(sub, layout)
    for container in ("items", "additionalProperties"):
        apply_pattern_from(schema.get(container), layout)


def load_schema(schemas_dir, rtype, layout=None):
    path = Path(schemas_dir) / f"{rtype}.schema.json"
    if not path.is_file():
        known = sorted(
            p.name[: -len(".schema.json")] for p in Path(schemas_dir).glob("*.schema.json")
        )
        raise SchemaError(
            f"no schema for record type '{rtype}' in {schemas_dir}"
            f" (known types: {', '.join(known) or 'none'})"
        )
    try:
        with open(path, encoding="utf-8") as fh:
            schema = json.load(fh)
    except OSError as exc:
        # The file passed is_file() above but vanished/failed before the read
        # (TOCTOU). Surface it as a SchemaError so every caller's existing
        # SchemaError handling reports it cleanly instead of an opaque traceback.
        raise SchemaError(f"cannot read schema for '{rtype}': {exc}") from exc
    if layout:
        apply_pattern_from(schema, layout)
    return schema


def parse_log(path):
    """Strict parse. Returns (entries, errors); entries are (line_no, record)."""
    entries, errors = [], []
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return [], [f"no handoff log at {path}"]
    except OSError as exc:
        # Any other I/O failure (a directory at the log path, permissions)
        # is a dirty-log error, not a crash: route must keep its
        # exit-0-with-decision contract and emit `blocked`.
        return [], [f"cannot read {path}: {exc}"]
    if raw and not raw.endswith("\n"):
        errors.append(f"line {raw.count(chr(10)) + 1}: missing trailing newline")
    # Split on "\n" only: str.splitlines() also breaks on U+0085/U+2028/U+2029,
    # which json.dumps(ensure_ascii=False) leaves unescaped inside strings.
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    for no, line in enumerate(lines, 1):
        if not line.strip():
            errors.append(f"line {no}: blank line")
            continue
        try:
            record = loads_strict(line)
        except ValueError as exc:
            errors.append(f"line {no}: invalid JSON ({_decode_error(exc)})")
            continue
        if not isinstance(record, dict):
            errors.append(f"line {no}: not a JSON object")
            continue
        entries.append((no, record))
    return entries, errors


def fail(msg):
    print(f"handoff.py: {msg}", file=sys.stderr)
    return 1


def require_clean_log(path):
    entries, errors = parse_log(path)
    if errors:
        for err in errors:
            print(f"handoff.py: {err}", file=sys.stderr)
        print("handoff.py: log is not clean — run validate", file=sys.stderr)
        return None
    return entries


def cmd_append(args):
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


def cmd_validate(args):
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
    print(f"{len(entries)} records valid")
    return 0


def cmd_latest(args):
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    match = None
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


def cmd_next_retry(args):
    entries = require_clean_log(args.file)
    if entries is None:
        return 1
    design_idx = None
    for i, (_, record) in enumerate(entries):
        if record.get("type") == "design-block" and record.get("req_id") == args.req_id:
            design_idx = i
    if design_idx is None:
        print(f"handoff.py: no design-block record for {args.req_id}", file=sys.stderr)
        return 3
    count = sum(
        1
        for _, record in entries[design_idx + 1:]
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


def _dispatch(next_agents, rule, reason, req_id, **context):
    out = {"decision": "dispatch", "next": list(next_agents), "rule": rule, "reason": reason}
    if req_id:
        out["req_id"] = req_id
    if context:
        out["context"] = context
    return out


def _blocked(rule, reason, req_id=None, errors=None, **context):
    out = {"decision": "blocked", "rule": rule, "reason": reason}
    if req_id:
        out["req_id"] = req_id
    if errors:
        out["errors"] = errors
    if context:
        out["context"] = context
    return out


def _bounce(upstream, rule, reason, req_id, errors):
    """A failed gate bounces upstream: a dispatch of the producing agent with
    the exact errors, consuming no downstream dispatch."""
    return _dispatch([upstream], rule, reason, req_id, errors=errors)


def _finding_owner(finding):
    """Artifact owner for one review finding (Gate 4 split). None means the
    finding is a root-applied design-doc autofix, not a dispatch target."""
    location = finding.get("location", "") if isinstance(finding, dict) else ""
    path = location.split(":", 1)[0]
    if path.startswith("docs/prd.md"):
        return PRODUCT
    if path.startswith("docs/system-design.md") or path.startswith("docs/adr/"):
        return None if finding.get("tag") == "autofix" else DESIGNER
    return IMPLEMENTER


def _unresolved_refactor(entries):
    """req_ids whose latest design-block verdict is refactor-first (no
    superseding design-block yet) — the original slices awaiting re-triage.

    Scans every req_id in the log. The pipeline runs one feature at a time
    (new-feature clears .scratch/), so cross-feature leftovers cannot occur
    in a well-run log; a stale record from a never-cleared feature would
    surface here and is the operator's cue to run /new-feature."""
    latest = {}
    for _, rec_ in entries:
        if rec_.get("type") == "design-block" and isinstance(rec_.get("req_id"), str):
            latest[rec_["req_id"]] = rec_.get("verdict")
    return sorted(r for r, v in latest.items() if v == "refactor-first")


def _escalate(rule, reason, req_id=None, **context):
    out = {"decision": "escalate", "rule": rule, "reason": reason}
    if req_id:
        out["req_id"] = req_id
    if context:
        out["context"] = context
    return out


def _gate_errors(record, rtype, schemas_dir, layout):
    """Schema-check one gating record; any loading failure is a gate failure."""
    try:
        schema = load_schema(schemas_dir, rtype, layout)
    except (SchemaError, json.JSONDecodeError) as exc:
        return [str(exc)]
    return validate_record(record, schema)


def _roster(layout):
    """The reviewer roster, or an error string. Gate 4 makes declared extras
    part of the gate, so a malformed declaration fails closed."""
    extras = layout_lookup(layout, "harness.extra_reviewers")
    if extras is None:
        return list(ROSTER_FLOOR), None
    if not isinstance(extras, list) or any(not isinstance(e, str) or not e for e in extras):
        return None, "harness.extra_reviewers in scripts/layout.toml must be a list of reviewer names"
    roster = list(ROSTER_FLOOR)
    for extra in extras:
        if extra not in roster:
            roster.append(extra)
    return roster, None


def _latest(recs, rtype):
    """Latest (line, record) of rtype in an already req_id-filtered list."""
    match = None
    for no, rec in recs:
        if rec.get("type") == rtype:
            match = (no, rec)
    return match


def _consultation_dispatch(no, request, schemas_dir, layout, req_id):
    errors = _gate_errors(request, "consultation-request", schemas_dir, layout)
    target = request.get("target")
    if not isinstance(target, str) or not target:
        errors.append("consultation-request names no target specialist")
    if errors:
        author = request.get("author")
        if isinstance(author, str) and author:
            return _bounce(
                author, "consultation-invalid",
                f"consultation-request at line {no} failed its gate; re-dispatch its author",
                req_id, errors,
            )
        return _blocked("consultation-invalid", f"consultation-request at line {no} failed its gate", req_id, errors)
    return _dispatch(
        [target], "consultation-dispatch",
        "pending consultation-request; dispatch the target in consultation mode",
        req_id, requester=request.get("author"),
    )


def _consultation_return(recs, resp_no, resp, schemas_dir, layout, req_id):
    errors = _gate_errors(resp, "consultation-response", schemas_dir, layout)
    request = next((rec for no, rec in recs if no == resp.get("in_response_to")), None)
    if request is None or request.get("type") != "consultation-request":
        errors.append(
            f"in_response_to ({resp.get('in_response_to')}) does not point at a consultation-request line"
        )
    elif resp.get("author") != request.get("target"):
        errors.append("consultation-response author does not match the request's target")
    elif not isinstance(request.get("author"), str) or not request.get("author"):
        errors.append("the corresponding consultation-request names no author to return to")
    if errors:
        # A failed gate is a dispatch of the upstream agent (the responder),
        # like the request side — blocked only when the dangling
        # in_response_to leaves no identifiable responder to re-dispatch.
        target = request.get("target") if request is not None else None
        if isinstance(target, str) and target:
            return _bounce(
                target, "consultation-invalid",
                f"consultation-response at line {resp_no} failed its gate; re-dispatch the responder",
                req_id, errors,
            )
        return _blocked("consultation-invalid", f"consultation-response at line {resp_no} failed its gate", req_id, errors)
    return _dispatch(
        [request["author"]], "consultation-return",
        "route control back to the requesting specialist; do not advance the pipeline",
        req_id, resume=True,
    )


def _review_state(recs, roster, schemas_dir, layout, req_id, unresolved):
    """Route the post-build-pass phase: reviewer dispatch, stall handling,
    findings processing by artifact owner, grading, completion. Deterministic
    from the log: feedback older than the reviewer's latest dispatch-start is
    stale; one silent dispatch-start earns the single stall retry, a second
    blocks."""
    bp = _latest(recs, "build-pass")
    if bp is None:
        return _escalate("review-without-build-pass", "review activity with no build-pass record for this slice", req_id)
    bp_line, bp_rec = bp
    errors = _gate_errors(bp_rec, "build-pass", schemas_dir, layout)
    if errors:
        return _bounce(
            IMPLEMENTER, "build-record-invalid",
            f"build-pass at line {bp_line} failed its gate; re-dispatch the implementer",
            req_id, errors,
        )
    prev_bp_line = 0
    for no, rec in recs:
        if no < bp_line and rec.get("type") == "build-pass":
            prev_bp_line = no
    prior_escalate = any(
        prev_bp_line < no < bp_line
        and rec.get("type") == "review-feedback"
        and any(isinstance(f, dict) and f.get("tag") == "escalate" for f in rec.get("findings", []))
        for no, rec in recs
    )
    any_fb_since_bp = any(
        no > bp_line and rec.get("type") == "review-feedback" for no, rec in recs
    )
    if prior_escalate and not any_fb_since_bp:
        return _blocked(
            "escalate-finding-halt",
            "an escalate finding preceded this build-pass; the human decides before reviews re-run",
            req_id,
        )
    feedback, retry_once, stalled, undispatched = {}, [], [], []
    for reviewer in roster:
        fb = None
        starts = 0
        for no, rec in recs:
            if no <= bp_line or rec.get("author") != reviewer:
                continue
            if rec.get("type") == "review-feedback":
                fb = (no, rec)
                starts = 0
            elif rec.get("type") == "dispatch-start":
                starts += 1
        if starts == 0 and fb is not None:
            feedback[reviewer] = fb
        elif starts == 0:
            undispatched.append(reviewer)
        elif starts == 1:
            retry_once.append(reviewer)
        else:
            stalled.append(reviewer)
    if stalled:
        return _blocked(
            "reviewer-stalled",
            "reviewer(s) produced no current review-feedback record after the stall retry; append the escalation and stop",
            req_id, stalled=stalled,
        )
    if undispatched and not feedback and not retry_once:
        return _dispatch(roster, "reviews-needed", "build-pass gated; dispatch the full reviewer roster in parallel", req_id)
    if retry_once:
        return _dispatch(
            retry_once + undispatched, "reviewer-stall-retry",
            "reviewer(s) returned without a current review-feedback record; re-dispatch once per the Reviewer Stall Check",
            req_id,
        )
    if undispatched:
        return _dispatch(undispatched, "reviews-needed", "roster reviewer(s) have not been dispatched since build-pass", req_id)
    for reviewer, (no, rec) in feedback.items():
        errors = _gate_errors(rec, "review-feedback", schemas_dir, layout)
        # Gate 4: a clarify finding without its target is unroutable.
        errors.extend(
            f"finding {i} has tag 'clarify' but no clarify_target"
            for i, f in enumerate(rec.get("findings", []), 1)
            if isinstance(f, dict) and f.get("tag") == "clarify"
            and not f.get("clarify_target")
        )
        if errors:
            return _bounce(
                reviewer, "review-record-invalid",
                f"review-feedback at line {no} failed its gate; re-dispatch the reviewer",
                req_id, errors,
            )
    non_approved = {r: fb for r, (no, fb) in feedback.items() if fb.get("verdict") != "approved"}
    empty = [r for r in roster if r in non_approved and not non_approved[r].get("findings")]
    if empty:
        return _dispatch(
            empty, "reviewer-empty-findings",
            "non-approved verdict with no findings is not actionable; re-dispatch the reviewer",
            req_id,
        )
    escalate_tags = sum(
        1 for _, (no, fb) in feedback.items()
        for f in fb.get("findings", []) if isinstance(f, dict) and f.get("tag") == "escalate"
    )
    if non_approved:
        owners = []
        root_autofix = 0
        for fb in non_approved.values():
            for f in fb.get("findings", []):
                owner = _finding_owner(f)
                if owner is None:
                    root_autofix += 1
                elif owner not in owners:
                    owners.append(owner)
        # Escalate findings cross the approved boundary: an APPROVED record's
        # escalate-tagged finding still joins the split, and the implementer
        # always rides an escalate round — it appends the entry to
        # .scratch/escalations.md while processing findings (Gate 4).
        for reviewer, (no, fb) in feedback.items():
            if reviewer in non_approved:
                continue
            for f in fb.get("findings", []):
                if isinstance(f, dict) and f.get("tag") == "escalate":
                    owner = _finding_owner(f) or IMPLEMENTER
                    if owner not in owners:
                        owners.append(owner)
        if escalate_tags and owners and IMPLEMENTER not in owners:
            owners.append(IMPLEMENTER)
        owners = [o for o in (IMPLEMENTER, PRODUCT, DESIGNER) if o in owners]
        if not owners:
            return _escalate(
                "autofix-only-round",
                "every finding is a root-applied design-doc autofix; root applies them and the coordinator decides the re-review",
                req_id, root_autofix=root_autofix,
            )
        context = {
            "reviewers": sorted(non_approved),
            "escalate_findings": escalate_tags,
            "root_autofix": root_autofix,
        }
        if escalate_tags:
            context["halt_after"] = True
        return _dispatch(
            owners, "process-findings",
            "findings dispatch to their artifact owners; halt after processing when an escalate finding is present",
            req_id, **context,
        )
    if escalate_tags:
        return _blocked(
            "escalate-on-approved",
            "approved verdicts carry escalate-tagged finding(s); root appends the escalation entry and halts",
            req_id, escalate_findings=escalate_tags,
        )
    gv = _latest(recs, "grader-verdict")
    if gv is not None and gv[0] > bp_line:
        if unresolved:
            return _dispatch(
                [DESIGNER], "refactor-resume",
                "refactor slice complete; re-triage the original slice with supersedes_record_at",
                req_id, original_req_id=unresolved[0], verdict=gv[1].get("verdict"),
            )
        return _blocked(
            "feature-complete",
            "all roster reviewers approved and the change-grader recorded its advisory verdict; human merge decision",
            req_id, verdict=gv[1].get("verdict"),
        )
    return _dispatch(
        ["change-grader"], "grade",
        "all roster reviewers approved; dispatch the terminal advisory change-grader",
        req_id,
    )


def _build_failure_state(recs, req_id, schemas_dir, layout):
    bf_no, bf = _latest(recs, "build-failure")
    errors = _gate_errors(bf, "build-failure", schemas_dir, layout)
    if errors:
        return _bounce(
            IMPLEMENTER, "build-record-invalid",
            f"build-failure at line {bf_no} failed its gate; re-dispatch the implementer",
            req_id, errors,
        )
    abort = bf.get("abort_reason")
    if abort == "wrong-shape-slice":
        return _dispatch([PRODUCT], "abort-wrong-shape", "implementer aborted: slice cannot be implemented as scoped; re-split", req_id)
    if abort == "design-mismatch":
        return _dispatch([DESIGNER], "abort-design-mismatch", "implementer aborted: design does not match reality; re-triage with supersedes_record_at", req_id)
    if abort == "prerequisite-missing":
        return _blocked("abort-prerequisite", "implementer aborted on a missing external prerequisite; root appends the escalation and halts", req_id)
    if abort:
        return _escalate("abort-unknown", f"build-failure carries unrecognized abort_reason '{abort}'", req_id)
    db = _latest(recs, "design-block")
    if db is None:
        return _escalate("failure-without-design", "build-failure exists but no design-block precedes it", req_id)
    count = sum(
        1 for no, rec in recs
        if no > db[0] and rec.get("type") == "build-failure"
    )
    if count < 3:
        return _dispatch(
            [IMPLEMENTER], "build-retry",
            f"quality gate failed; re-dispatch with error context (this is retry {count} of 3)",
            req_id, retry=count, partial=bool(bf.get("partial")),
        )
    return _dispatch(
        [DESIGNER], "build-non-convergence",
        "three gate failures since the latest design-block; re-triage with supersedes_record_at",
        req_id, failures=count,
    )


def _truncation_state(recs, req_id):
    db = _latest(recs, "design-block")
    if db is None:
        return _escalate("truncation-before-design", "implementer dispatch-start with no design-block on record", req_id)
    run = 0
    for no, rec in recs:
        if no <= db[0] or rec.get("author") != IMPLEMENTER:
            continue
        if rec.get("type") == "dispatch-start":
            run += 1
        else:
            run = 0
    if run < 3:
        return _dispatch(
            [IMPLEMENTER], "truncation-continue",
            f"dispatch truncated before a substantive record; continue the same slice (continuation {run} of 3)",
            req_id, continuation=run,
        )
    return _dispatch(
        [DESIGNER], "truncation-non-convergence",
        "three consecutive truncated dispatches with no implementer record; re-triage per Truncation Recovery",
        req_id, continuations=run,
    )


def _route_decision(entries, req_id_arg, schemas_dir, layout):
    if not entries:
        return _escalate("no-active-slice", "handoff log has no records; classify the request per the Agent Selection table")
    req_id = req_id_arg or entries[-1][1].get("req_id")
    if not isinstance(req_id, str) or not req_id:
        return _blocked("missing-req-id", f"latest record (line {entries[-1][0]}) carries no req_id")
    recs = [(no, rec) for no, rec in entries if rec.get("req_id") == req_id]
    if not recs:
        return _blocked("unknown-req-id", f"no records for {req_id}", req_id)
    roster, roster_error = _roster(layout)
    if roster_error:
        return _blocked("layout-invalid", roster_error, req_id)
    unresolved = [r for r in _unresolved_refactor(entries) if r != req_id]
    last_no, last = recs[-1]
    last_type = last.get("type")

    if last_type == "consultation-request":
        return _consultation_dispatch(last_no, last, schemas_dir, layout, req_id)
    if last_type == "consultation-response":
        return _consultation_return(recs, last_no, last, schemas_dir, layout, req_id)

    if last_type == "grader-verdict":
        if unresolved:
            return _dispatch(
                [DESIGNER], "refactor-resume",
                "refactor slice complete; re-triage the original slice with supersedes_record_at",
                req_id, original_req_id=unresolved[0], verdict=last.get("verdict"),
            )
        return _blocked("feature-complete", "change-grader recorded its advisory verdict; human merge decision", req_id, verdict=last.get("verdict"))
    if last_type == "grader-features":
        return _dispatch(["change-grader"], "grade-continue", "grader-features recorded without a grader-verdict; re-dispatch the change-grader", req_id)

    latest_substantive = None
    for no, rec in recs:
        if rec.get("type") in SUBSTANTIVE:
            latest_substantive = (no, rec)
    latest_request = _latest(recs, "consultation-request")
    latest_response = _latest(recs, "consultation-response")
    sub_line = latest_substantive[0] if latest_substantive else 0
    req_line = latest_request[0] if latest_request else 0
    resp_line = latest_response[0] if latest_response else 0

    # Truncation detection follows the table trigger — a dispatch-start with
    # no subsequent substantive record — not "dispatch-start is the last
    # record": a trailing non-substantive root record (a design-doc autofix
    # note, an escalation entry) must not mask a truncated dispatch. Grader
    # records count as subsequent output here: a grader-verdict after the
    # grader's own dispatch-start is a completed dispatch, not a truncation.
    grader_line = max((no for no, rec in recs
                       if rec.get("type") in ("grader-verdict", "grader-features")),
                      default=0)
    latest_ds = _latest(recs, "dispatch-start")
    if latest_ds is not None and latest_ds[0] > max(sub_line, req_line, resp_line,
                                                    grader_line):
        author = latest_ds[1].get("author")
        if author == IMPLEMENTER:
            return _truncation_state(recs, req_id)
        if author in roster:
            return _review_state(recs, roster, schemas_dir, layout, req_id, unresolved)
        return _escalate(
            "truncation-undefined",
            f"dispatch-start from {author} with no subsequent substantive record; no recovery row is defined for this agent",
            req_id, author=author,
        )

    if latest_request is not None and req_line > sub_line and req_line > resp_line:
        return _consultation_dispatch(req_line, latest_request[1], schemas_dir, layout, req_id)
    if latest_substantive is None:
        return _escalate("no-substantive-record", "records exist but none is substantive; classify the state manually", req_id)
    sub_no, sub = latest_substantive
    sub_type = sub.get("type")

    if sub_type in ("build-pass", "review-feedback"):
        return _review_state(recs, roster, schemas_dir, layout, req_id, unresolved)
    if sub_type == "build-failure":
        return _build_failure_state(recs, req_id, schemas_dir, layout)
    if sub_type == "design-block":
        verdict = sub.get("verdict")
        if verdict == "conflicting":
            escalations = sub.get("escalations", [])
            # Gate 2: a conflicting verdict must carry its escalations — an
            # empty array leaves the human nothing to decide on. Still
            # blocked either way; the error names the gap.
            gap = None if escalations else [
                "conflicting design-block carries no escalations (Gate 2 requires a non-empty array)"]
            return _blocked("design-conflict", "design-block verdict is conflicting; halt and surface the escalations to the user", req_id, errors=gap, escalations=escalations)
        if verdict == "refactor-first":
            return _escalate("refactor-first", "refactor-first verdict: the coordinator orders the refactor slice ahead of this one", req_id)
        errors = _gate_errors(sub, "design-block", schemas_dir, layout)
        # Gate 2: a supersedes_record_at pointer must reference a prior
        # design-block line of this slice.
        sup = sub.get("supersedes_record_at")
        if sup is not None:
            target_rec = next((rec for no, rec in recs if no == sup), None)
            if (not isinstance(sup, int) or sup >= sub_no or target_rec is None
                    or target_rec.get("type") != "design-block"):
                errors.append(f"supersedes_record_at ({sup!r}) does not point "
                              "at a prior design-block line for this slice")
        if errors or verdict not in ("covered", "minor", "new", "foundational"):
            if not errors:
                errors = [f"unknown design-block verdict '{verdict}'"]
            return _bounce(
                DESIGNER, "design-gate-failed",
                f"design-block at line {sub_no} failed its gate; re-dispatch upstream",
                req_id, errors,
            )
        return _dispatch([IMPLEMENTER], "design-approved", f"design-block verdict '{verdict}' passed its gate; dispatch the implementer", req_id, verdict=verdict)
    if sub_type == "prd-entry":
        if sub.get("author") == DESIGNER:
            return _escalate(
                "refactor-first",
                "designer-authored sibling prd-entry: the coordinator orders the refactor slice ahead of the original",
                req_id,
            )
        errors = _gate_errors(sub, "prd-entry", schemas_dir, layout)
        if errors:
            return _bounce(
                PRODUCT, "prd-gate-failed",
                f"prd-entry at line {sub_no} failed its gate; re-dispatch upstream",
                req_id, errors,
            )
        return _dispatch([DESIGNER], "prd-approved", "prd-entry passed its gate; dispatch the system-design-expert for triage", req_id)
    if sub_type == "consultation-response":
        return _consultation_return(recs, sub_no, sub, schemas_dir, layout, req_id)
    return _escalate("unroutable-state", f"latest substantive record type '{sub_type}' matched no table row", req_id)


def cmd_route(args):
    entries, errors = parse_log(args.file)
    if errors and not entries and all("no handoff log" in e for e in errors):
        decision = _escalate("no-active-slice", "no handoff log; classify the request per the Agent Selection table")
    elif errors:
        decision = _blocked("dirty-log", "handoff log failed strict parse; run validate and repair upstream", errors=errors)
    else:
        layout = {}
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
    print(json.dumps(decision, ensure_ascii=False))
    return 0


def cmd_show(args):
    try:
        with open(args.file, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return fail(f"no handoff log at {args.file}")
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    rows = []
    for no, line in enumerate(lines, 1):
        record = None
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
        rows = [r for r in rows if r[1] is not None and r[1].get("req_id") == args.req_id]
    if args.last > 0:
        rows = rows[-args.last:]
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
                for k in ("type", "req_id", "ts") if record.get(k) is not None
            )
            print(f"-- line {no}: {header}")
            print(json.dumps(record, ensure_ascii=False, indent=2))
    if not rows:
        print("no matching records")
    return 0


# --- view: one-screen slice status — header, convergence matrix, timeline ---

GRADER = "change-grader"
COORDINATOR = "pipeline-coordinator"

# Short display labels. Reviewers not named here fall back to stripping the
# -reviewer suffix, so a layout.toml extra reviewer gets a sensible label;
# any other unknown author renders by its raw name.
AGENT_LABELS = {
    IMPLEMENTER: "implementer",
    DESIGNER: "design",
    PRODUCT: "prd-expert",
    COORDINATOR: "coord",
    GRADER: "grader",
}

VERDICT_GLYPHS = {
    "approved": ("✔", "32"),
    "changes_requested": ("✎", "33"),
    "blocked": ("✖", "31"),
}
TAG_COLORS = {"autofix": "33", "blocked": "31", "escalate": "1;31",
              "clarify": "36", "truncation": "90"}
FACET_COLORS = {"clear": "32", "concern": "31", "unknown": "33"}
GRADE_COLORS = {"clear": "32", "concern": "31"}
DIM = "90"
BOLD = "1"
VIEW_WIDTH = 72


# Log strings render in the reader's terminal, and the log is agent-authored:
# a record must never inject escape sequences (window title, cursor moves,
# hidden text) into that terminal. `_style` is the view renderer's single
# choke point — every line it emits is built through `_style` — so sanitizing
# there (tabs and newlines to spaces, every other C0/C1 control byte dropped)
# leaves no unsanitized path out of the view. The terminating escape codes it
# adds wrap the already-cleaned text. Span builders sanitize again ahead of
# their alignment math; `_style` is the backstop that makes a bypass
# impossible, not a redundant second pass. (`show` sanitizes its own plain
# text separately; it does not route through the view renderer.)
_BREAK_RE = re.compile(r"[\t\n\r\v\f]+")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize(text):
    return _CONTROL_RE.sub("", _BREAK_RE.sub(" ", text))


def _style(text, code, color):
    text = _sanitize(text)
    if not color or not code:
        return text
    return f"\033[{code}m{text}\033[0m"


def _line(spans, color):
    """Join (text, code) spans into one line; trailing blanks are stripped
    so plain and colored output stay byte-alignable."""
    spans = [(_sanitize(t), c) for t, c in spans if t]
    while spans and not spans[-1][0].strip():
        spans.pop()
    if spans:
        text, code = spans[-1]
        spans[-1] = (text.rstrip(), code)
    return "".join(_style(t, c, color) for t, c in spans if t)


def _pad(spans, width, color):
    """Render spans and pad on plain-text length — pad first, color after,
    so columns align identically with and without escapes."""
    spans = [(_sanitize(t), c) for t, c in spans]
    plain_len = sum(len(t) for t, _ in spans)
    rendered = "".join(_style(t, c, color) for t, c in spans)
    return rendered + " " * max(0, width - plain_len)


def agent_label(author):
    if not isinstance(author, str) or not author:
        return "?"
    if author in AGENT_LABELS:
        return AGENT_LABELS[author]
    if author.endswith("-reviewer"):
        return _sanitize(author[: -len("-reviewer")])
    return _sanitize(author)


def short_location(location, limit=38):
    if not isinstance(location, str):
        return ""
    loc = location.split(" (")[0].strip()
    loc = re.sub(r"^.*/", "", loc)
    return loc[:limit]


def gist(text, limit=75):
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[: limit - 1] + "…" if len(text) > limit else text


def review_rounds(recs):
    """Group review-feedback into rounds by append order: a reviewer
    reappearing starts a new round. Re-reviews usually follow a fresh
    build-pass, but a doc-only round may not — reappearance covers both."""
    rounds, current = [], {}
    for rec in recs:
        if rec.get("type") != "review-feedback":
            continue
        author = rec.get("author") if isinstance(rec.get("author"), str) else "?"
        if author in current:
            rounds.append(current)
            current = {}
        current[author] = rec
    if current:
        rounds.append(current)
    return rounds


def _findings_of(rec):
    findings = rec.get("findings")
    return [f for f in findings if isinstance(f, dict)] if isinstance(findings, list) else []


def _verdict_glyph(verdict):
    """Glyph + color for a review verdict. Record data is untrusted: a
    non-string (unhashable) verdict must fall through, never raise."""
    if not isinstance(verdict, str):
        verdict = None
    return VERDICT_GLYPHS.get(verdict, ("•", DIM))


def _plural(n, word):
    if n == 1:
        return f"1 {word}"
    return f"{n} {word}" + ("es" if word.endswith("s") else "s")


def _render_box(span_lines, color):
    width = max(sum(len(t) for t, _ in spans) for spans in span_lines)
    out = [_style("╭" + "─" * (width + 2) + "╮", DIM, color)]
    for spans in span_lines:
        out.append(_style("│ ", DIM, color) + _pad(spans, width, color) + _style(" │", DIM, color))
    out.append(_style("╰" + "─" * (width + 2) + "╯", DIM, color))
    return out


def _render_header(req_id, recs, rounds, others, color):
    title = None
    grade = None
    for rec in recs:
        if rec.get("type") == "prd-entry" and isinstance(rec.get("title"), str):
            title = rec["title"]
        elif rec.get("type") == "grader-verdict":
            grade = rec.get("verdict")
    passes = sum(1 for r in recs if r.get("type") == "build-pass")
    failures = sum(1 for r in recs if r.get("type") == "build-failure")
    line1 = [(req_id or "(no req_id)", BOLD)]
    if title:
        line1 += [("  ", None), (gist(title, 52), None)]
    line2 = [(_plural(len(rounds), "review round"), DIM),
             ((" · " + _plural(passes, "build-pass")), DIM)]
    if failures:
        line2 += [(" · ", DIM), (_plural(failures, "build-failure"), "31")]
    if isinstance(grade, str):
        line2 += [(" · grade ", DIM), (grade.upper(), f"{BOLD};{GRADE_COLORS.get(grade, DIM)}")]
    else:
        line2 += [(" · no grade yet", DIM)]
    span_lines = [line1, line2]
    if others:
        span_lines.append([("also in log: " + ", ".join(others), DIM)])
    return _render_box(span_lines, color)


def _matrix_cell(rec):
    if rec is None:
        return [("·", DIM)]
    glyph, vcol = _verdict_glyph(rec.get("verdict"))
    spans = [(glyph, vcol)]
    n = len(_findings_of(rec))
    if n:
        spans.append((f" ({n})", DIM))
    return spans


def _render_matrix(rounds, roster, color):
    if not rounds:
        return []
    authors = list(roster)
    for rnd in rounds:
        for author in rnd:
            if author not in authors:
                authors.append(author)
    label_w = max(len(agent_label(a)) for a in authors)
    cells, col_w = {}, []
    for i, rnd in enumerate(rounds):
        width = len(f"R{i + 1}")
        for author in authors:
            spans = _matrix_cell(rnd.get(author))
            cells[(author, i)] = spans
            width = max(width, sum(len(t) for t, _ in spans))
        col_w.append(width)
    header = " " * (label_w + 2) + "  ".join(
        f"R{i + 1}".ljust(col_w[i]) for i in range(len(rounds))
    )
    lines = [_style(header.rstrip(), DIM, color)]
    for author in authors:
        row = agent_label(author).ljust(label_w) + "  "
        row += "  ".join(_pad(cells[(author, i)], col_w[i], color) for i in range(len(rounds)))
        lines.append(row.rstrip())
    return lines


def _rule_line(core, color):
    core = [(_sanitize(t), c) for t, c in core]
    plain_len = sum(len(t) for t, _ in core)
    body = "".join(_style(t, c, color) for t, c in core)
    fill = "─" * max(0, VIEW_WIDTH - plain_len - 4)
    return _style("── ", DIM, color) + body + " " + _style(fill, DIM, color)


def _finding_lines(rec, color, verbose):
    lines = []
    findings = _findings_of(rec)
    for i, finding in enumerate(findings):
        last = i == len(findings) - 1
        conn = "└" if last else "├"
        tag = finding.get("tag")
        tag_text = tag if isinstance(tag, str) and tag else "?"
        desc = finding.get("description")
        spans = [("  ", None), (conn + " ", DIM),
                 (f"[{tag_text}]", TAG_COLORS.get(tag_text, DIM)), (" ", None),
                 (short_location(finding.get("location")), BOLD), ("  ", None),
                 (desc if verbose and isinstance(desc, str) else gist(desc), DIM)]
        lines.append(_line(spans, color))
        if verbose and isinstance(finding.get("fix"), str) and finding["fix"].strip():
            bar = "  " if last else "│ "
            lines.append(_line([("  " + bar + "  ", DIM),
                                ("fix: " + finding["fix"].strip(), DIM)], color))
    return lines


def _facet_lines(rec, color):
    facets = rec.get("facets")
    if not isinstance(facets, dict) or not facets:
        return []
    name_w = max(len(str(name)) for name in facets)
    lines = []
    for name, facet in facets.items():
        facet = facet if isinstance(facet, dict) else {}
        verdict = facet.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        lines.append(_line([
            ("  · ", DIM), (str(name).ljust(name_w), None), ("  ", None),
            (verdict_text.ljust(7), FACET_COLORS.get(verdict_text, DIM)), ("  ", None),
            (gist(facet.get("note"), 48), DIM),
        ], color))
    return lines


def _consultation_peer(entries, response):
    """The requesting author a consultation-response returns to, via its
    in_response_to line pointer; None when the pointer dangles."""
    target = response.get("in_response_to")
    for no, rec in entries:
        if no == target and rec.get("type") == "consultation-request":
            return rec.get("author")
    return None


def _timeline_lines(rec, entries, color, verbose):
    rtype = rec.get("type")
    author = f"  ({agent_label(rec.get('author'))})"
    if rtype == "prd-entry":
        return [_line([("◇ ", "35"), ("prd-entry  ", DIM),
                       (gist(rec.get("title"), 52) or "(untitled)", BOLD),
                       (author, DIM)], color)]
    if rtype == "design-block":
        spans = [("◈ ", "35"), ("design-block  ", DIM),
                 (str(rec.get("verdict") or "?"), BOLD), (author, DIM)]
        if isinstance(rec.get("supersedes_record_at"), int):
            spans.append((f"  supersedes L{rec['supersedes_record_at']}", DIM))
        return [_line(spans, color)]
    if rtype == "build-pass":
        core = [("▲ build-pass", "32")]
        checks = rec.get("gate_checks_run")
        if isinstance(checks, list) and checks:
            core.append(("  " + ", ".join(str(c) for c in checks), DIM))
        return [_rule_line(core, color)]
    if rtype == "build-failure":
        core = [("▲ build-failure", "31")]
        if isinstance(rec.get("abort_reason"), str):
            core.append((f"  abort: {rec['abort_reason']}", "1;31"))
        else:
            if isinstance(rec.get("failed_check"), str):
                core.append(("  " + rec["failed_check"], DIM))
            if rec.get("retry") is not None:
                core.append((f"  retry {rec['retry']}", DIM))
        return [_rule_line(core, color)]
    if rtype == "review-feedback":
        verdict = rec.get("verdict")
        glyph, vcol = _verdict_glyph(verdict)
        n = len(_findings_of(rec))
        spans = [(glyph + " ", vcol), ("review  ", DIM),
                 (agent_label(rec.get("author")), BOLD), ("  ", None),
                 (str(verdict or "?"), vcol)]
        if n:
            spans.append((f"  ({_plural(n, 'finding')})", DIM))
        return [_line(spans, color)] + _finding_lines(rec, color, verbose)
    if rtype == "grader-verdict":
        verdict = rec.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        spans = [("◆ ", "36"), ("grade  ", DIM),
                 (verdict_text.upper(), f"{BOLD};{GRADE_COLORS.get(verdict_text, DIM)}"),
                 ("  ", None), (gist(rec.get("summary")), DIM)]
        return [_line(spans, color)] + _facet_lines(rec, color)
    if rtype == "consultation-request":
        return [_line([("↳ ", "36"), ("consult  ", DIM),
                       (agent_label(rec.get("author")), BOLD), (" → ", DIM),
                       (agent_label(rec.get("target")), BOLD), ("  ", None),
                       (gist(rec.get("question")), DIM)], color)]
    if rtype == "consultation-response":
        return [_line([("↲ ", "36"), ("consult  ", DIM),
                       (agent_label(rec.get("author")), BOLD), (" → ", DIM),
                       (agent_label(_consultation_peer(entries, rec)), BOLD), ("  ", None),
                       (gist(rec.get("answer")), DIM)], color)]
    if rtype == "design-doc-autofix":
        return [_line([("✚ ", "33"), ("doc-autofix  ", DIM),
                       (str(rec.get("file") or "?"), BOLD),
                       ("  " + str(rec.get("category") or ""), DIM),
                       (author, DIM)], color)]
    return [_line([("• ", DIM), (str(rtype or "?") + "  ", DIM),
                   ("(" + agent_label(rec.get("author")) + ")", DIM)], color)]


def render_view(entries, errors, req_id, roster, color, verbose):
    """Render the view as (lines, exit_code). Pure: no I/O, no clock."""
    lines = []
    recs = [rec for _, rec in entries
            if req_id is None or rec.get("req_id") == req_id]
    others = sorted({rec.get("req_id") for _, rec in entries
                     if isinstance(rec.get("req_id"), str)} - {req_id})
    code = 0
    if not recs:
        if req_id is not None:
            lines.append(_style(f"no records for {req_id}", DIM, color))
            code = 3
        else:
            lines.append(_style("handoff log is empty", DIM, color))
        if others:
            lines.append(_style("in log: " + ", ".join(others), DIM, color))
    else:
        rounds = review_rounds(recs)
        lines += _render_header(req_id, recs, rounds, others, color)
        matrix = _render_matrix(rounds, roster, color)
        if matrix:
            lines.append("")
            lines += matrix
        lines.append("")
        for rec in recs:
            if rec.get("type") in ("dispatch-start", "grader-features"):
                continue
            lines += _timeline_lines(rec, entries, color, verbose)
    if errors:
        lines.append("")
        lines.append(_style(f"! {_plural(len(errors), 'problem line')} skipped:", "31", color))
        lines += [_style("  " + err, DIM, color) for err in errors]
    return lines, code


def cmd_view(args):
    # A non-UTF-8 stdout must degrade (replacement characters), never
    # traceback: the glyphs are cosmetic, the log content is what matters.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
    entries, errors = parse_log(args.file)
    if not entries and any("no handoff log" in e for e in errors) and args.req_id is None:
        print(f"no handoff log at {args.file}")
        return 0
    color = (not args.no_color and os.environ.get("NO_COLOR") is None
             and sys.stdout.isatty())
    roster, _roster_error = _roster(read_layout(args.layout))
    if roster is None:
        roster = list(ROSTER_FLOOR)  # reader, not gate: fall back, never block
    req_id = args.req_id
    if req_id is None and entries:
        candidate = entries[-1][1].get("req_id")
        if isinstance(candidate, str) and candidate:
            req_id = candidate
    lines, code = render_view(entries, errors, req_id, roster, color, args.verbose)
    print("\n".join(lines))
    return code


def build_parser():
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
        help="validate a record from stdin and append it in canonical form",
    )
    p.add_argument("type", help="record type; selects schemas/scratch/<type>.schema.json")
    p.set_defaults(func=cmd_append)
    p = sub.add_parser(
        "validate", parents=[common], help="parse and schema-check every record in the log"
    )
    p.set_defaults(func=cmd_validate)
    p = sub.add_parser(
        "latest",
        parents=[common],
        help="print the latest record matching --type (and --req-id)",
    )
    p.add_argument("--type", required=True)
    p.add_argument("--req-id")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--with-line", action="store_true", help="prefix output with '<line>\\t'")
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
    p.add_argument("--req-id", help="route this slice (default: the latest record's req_id)")
    p.set_defaults(func=cmd_route)
    p = sub.add_parser(
        "show", parents=[common], help="pretty-print recent records for human inspection"
    )
    p.add_argument("--last", type=int, default=10)
    p.add_argument("--type")
    p.add_argument("--req-id")
    p.set_defaults(func=cmd_show)
    p = sub.add_parser(
        "view",
        parents=[common],
        help="render one slice as a status view: header, review matrix, timeline",
    )
    p.add_argument("--req-id", help="slice to render (default: the latest record's req_id)")
    p.add_argument(
        "--verbose", action="store_true", help="full finding descriptions and fixes"
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="force plain output (automatic when stdout is not a TTY or NO_COLOR is set)",
    )
    p.set_defaults(func=cmd_view)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
