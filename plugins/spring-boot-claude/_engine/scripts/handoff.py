#!/usr/bin/env python3
"""handoff.py — deterministic access to the .scratch/handoff.jsonl handoff log.

Every write of the handoff log and every gate query over it goes through this
tool. Hand-built appends (shell redirection, editor tools) corrupt the log: a
missing trailing newline glues two records onto one line and the whole file
stops parsing. Hand-built queries (ad-hoc grep/jq) answer the same gate
question inconsistently across agents. This tool gives every agent the same
five operations with the same semantics:

  append      validate a record against its schema, write it in canonical form
  validate    parse and schema-check every line of the log
  latest      the gate query: latest record matching (type, req_id)
  next-retry  the Build-Failure Recovery counter: build-failure records for
              the req_id after the latest design-block line, plus one
  show        pretty-print recent records for human inspection

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

Stdlib only, Python 3.11+ (tomllib, to read layout.toml).

Exit codes: 0 success; 1 validation, parse, or I/O error; 2 usage error;
3 no matching record (latest / next-retry with no hit).
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
        if record is None:
            print(f"-- line {no}: UNPARSEABLE")
            print(f"   {line}")
        else:
            header = " · ".join(
                str(record[k]) for k in ("type", "req_id", "ts") if record.get(k) is not None
            )
            print(f"-- line {no}: {header}")
            print(json.dumps(record, ensure_ascii=False, indent=2))
    if not rows:
        print("no matching records")
    return 0


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
        "show", parents=[common], help="pretty-print recent records for human inspection"
    )
    p.add_argument("--last", type=int, default=10)
    p.add_argument("--type")
    p.add_argument("--req-id")
    p.set_defaults(func=cmd_show)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
