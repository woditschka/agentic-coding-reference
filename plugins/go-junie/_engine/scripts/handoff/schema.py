#!/usr/bin/env python3
"""handoff/schema.py — the handoff log's byte contract (ADR 2026-07-17 runtime-package-layout).

Trust class: the lowest layer. It owns strict JSON parsing (loads_strict, with
NaN/Infinity and duplicate-key rejection), the deliberately minimal draft-07
subset validator, canonical serialization (canonicalize / dumps_canonical), the
layout.toml reader and patternFrom resolution, schema loading, and the read side
of the log (parse_log). Same logical record in, same bytes out.

_sanitize lives here, not in handoff.view, because the parse boundary itself
must never let agent-authored bytes reach a terminal: _reject_duplicate_keys
sanitizes the offending key before raising. Every higher layer (records, route,
view, the CLI) imports _sanitize from here, keeping imports one-directional.

Imported by handoff.routing, handoff.view, and the handoff.py entry point; imports
nothing project-local. Stdlib only, Python 3.11+ (tomllib, to read layout.toml).
"""

import datetime
import json
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeAlias

# A raw log line: its 1-based number and the parsed dict. The routing core lifts
# these into typed Entry records; the cmd and view layers read the dict.
LogEntry: TypeAlias = tuple[int, dict[str, Any]]

# Keywords that carry no validation semantics.
ANNOTATIONS = {
    "$schema",
    "$id",
    "title",
    "description",
    "default",
    "examples",
    "definitions",
}
# The closed validation vocabulary. Anything else fails loudly.
SUPPORTED = {
    "$ref",
    "type",
    "const",
    "enum",
    "required",
    "properties",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "pattern",
    "patternFrom",
    "format",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
}
SUPPORTED_FORMATS = {"date-time"}

DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

TYPE_CHECKS: dict[str, Callable[[Any], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


# Log strings render in the reader's terminal, and the log is agent-authored:
# a record must never inject escape sequences (window title, cursor moves,
# hidden text) into that terminal. `_sanitize` (tabs and newlines to spaces,
# every other C0/C1 control byte dropped) is the shared choke point: the parse
# boundary sanitizes offending keys before raising, the view renderer routes
# every span through `_style`, and `show` sanitizes its own plain text.
_BREAK_RE = re.compile(r"[\t\n\r\v\f]+")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize(text: str) -> str:
    return _CONTROL_RE.sub("", _BREAK_RE.sub(" ", text))


class SchemaError(Exception):
    pass


def _reject_constant(name: str) -> Any:
    raise ValueError(f"{name} is not valid JSON")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """object_pairs_hook that rejects a duplicate key at any nesting depth.

    json's default keeps the last of a duplicated pair silently; a record that
    reached this log with duplicate keys is ambiguous, so fail closed on it.
    """
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            # The key is agent/attacker-authored log content; sanitize it like
            # every other terminal-bound field (see _sanitize) so no error sink
            # prints a raw control byte.
            raise ValueError(f'duplicate key: "{_sanitize(key)}"')
        obj[key] = value
    return obj


def loads_strict(text: str) -> Any:
    """json.loads that rejects NaN/Infinity and duplicate object keys.

    The log must stay RFC 8259-parseable, and duplicate keys make a record
    ambiguous — the last-wins default would hide the collision, so reject it.
    """
    return json.loads(
        text, parse_constant=_reject_constant, object_pairs_hook=_reject_duplicate_keys
    )


def _decode_error(exc: Exception) -> str:
    return exc.msg if isinstance(exc, json.JSONDecodeError) else str(exc)


def schema_equal(a: Any, b: Any) -> bool:
    """Draft-07 equality: booleans never equal numbers (Python's True == 1 must not)."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return bool(a == b)


def unsupported_keywords(schema: Any, path: str = "#") -> list[str]:
    """Walk a schema document; return locations of keywords outside the subset."""
    found: list[str] = []
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
            found.append(
                f"{path}/{key} (unsupported schema form: {type(sub).__name__})"
            )
    for container in ("properties", "definitions"):
        sub = schema.get(container)
        if isinstance(sub, dict):
            for name, subschema in sub.items():
                if isinstance(subschema, dict):
                    found += unsupported_keywords(
                        subschema, f"{path}/{container}/{name}"
                    )
                else:
                    found.append(
                        f"{path}/{container}/{name} (unsupported schema form:"
                        f" {type(subschema).__name__})"
                    )
    return found


def resolve_ref(schema: Any, root: dict[str, Any]) -> Any:
    hops = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/definitions/"
        if not isinstance(ref, str) or not ref.startswith(prefix):
            raise SchemaError(
                f"unsupported $ref '{ref}' (only {prefix}<name> is supported)"
            )
        name = ref[len(prefix) :]
        definitions = root.get("definitions", {})
        if name not in definitions:
            raise SchemaError(f"$ref '{ref}' has no matching definition")
        schema = definitions[name]
        hops += 1
        if hops > 10:
            raise SchemaError("$ref chain too deep")
    return schema


def validate_value(
    value: Any,
    schema: Any,
    root: dict[str, Any],
    path: str,
    errors: list[str],
) -> None:
    schema = resolve_ref(schema, root)
    if not isinstance(schema, dict):
        raise SchemaError(f"unsupported schema form at {path}: {type(schema).__name__}")
    if "const" in schema and not schema_equal(value, schema["const"]):
        errors.append(
            f"{path}: expected const {json.dumps(schema['const'])}, got {json.dumps(value)}"
        )
        return
    if "enum" in schema and not any(schema_equal(value, m) for m in schema["enum"]):
        errors.append(
            f"{path}: {json.dumps(value)} not in enum {json.dumps(schema['enum'])}"
        )
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
        if "pattern" in schema:
            # The pattern may come from the consumer-edited layout.toml (via
            # patternFrom): an invalid regex must surface as a validation
            # error, never as an uncaught re.error out of validate_record.
            try:
                matched = re.search(schema["pattern"], value) is not None
            except re.error:
                matched = None
            if matched is None:
                errors.append(
                    f"{path}: schema pattern {_sanitize(str(schema['pattern']))!r} "
                    "is not a valid regex (check its patternFrom source in "
                    "scripts/layout.toml)"
                )
            elif not matched:
                errors.append(
                    f"{path}: {json.dumps(value)} does not match pattern "
                    f"{_sanitize(str(schema['pattern']))}"
                )
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
            # Keys are agent-authored: sanitize before they reach a message
            # path, same contract as the parse boundary's duplicate-key raise.
            if key in props:
                validate_value(val, props[key], root, f"{path}.{key}", errors)
            elif extra is False:
                errors.append(
                    f"{path}: unexpected field '{_sanitize(key)}' "
                    "(additionalProperties: false)"
                )
            elif isinstance(extra, dict):
                validate_value(val, extra, root, f"{path}.{_sanitize(key)}", errors)
    elif isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: more than maxItems {schema['maxItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                validate_value(item, items, root, f"{path}[{i}]", errors)


def validate_record(record: Any, schema: dict[str, Any]) -> list[str]:
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


def canonicalize(value: Any, schema: Any, root: dict[str, Any]) -> Any:
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
        ordered: dict[str, Any] = {}
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


def dumps_canonical(record: Any) -> str:
    return json.dumps(
        record, ensure_ascii=False, allow_nan=False, separators=(", ", ": ")
    )


def read_layout(layout_path: str) -> dict[str, Any]:
    """Parse scripts/layout.toml into a dict. Absence is not an error: a missing
    or unreadable file yields {}, so any `patternFrom` simply goes unenforced."""
    try:
        return tomllib.loads(Path(layout_path).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def layout_lookup(data: dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted key (e.g. 'test_name_pattern' or 'section.key') in the
    parsed layout; return None if any segment is missing."""
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def apply_pattern_from(schema: Any, layout: dict[str, Any]) -> None:
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


def load_schema(
    schemas_dir: str, rtype: str, layout: dict[str, Any] | None = None
) -> dict[str, Any]:
    path = Path(schemas_dir) / f"{rtype}.schema.json"
    if not path.is_file():
        known = sorted(
            p.name[: -len(".schema.json")]
            for p in Path(schemas_dir).glob("*.schema.json")
        )
        raise SchemaError(
            f"no schema for record type '{rtype}' in {schemas_dir}"
            f" (known types: {', '.join(known) or 'none'})"
        )
    try:
        with open(path, encoding="utf-8") as fh:
            schema: dict[str, Any] = json.load(fh)
    except OSError as exc:
        # The file passed is_file() above but vanished/failed before the read
        # (TOCTOU). Surface it as a SchemaError so every caller's existing
        # SchemaError handling reports it cleanly instead of an opaque traceback.
        raise SchemaError(f"cannot read schema for '{rtype}': {exc}") from exc
    if layout:
        apply_pattern_from(schema, layout)
    return schema


def parse_log(path: str) -> tuple[list[LogEntry], list[str]]:
    """Strict parse. Returns (entries, errors); entries are (line_no, record)."""
    entries: list[LogEntry] = []
    errors: list[str] = []
    try:
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
    except FileNotFoundError:
        return [], [f"no handoff log at {path}"]
    except UnicodeDecodeError as exc:
        # A non-UTF-8 byte is a dirty-log error, not a crash: route keeps its
        # exit-0-with-decision contract and view renders the problem footer.
        return [], [f"log is not valid UTF-8: {exc}"]
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


def ts_now() -> str:
    """The log's one clock: every appended record's ts is stamped here.

    An agent composing a record cannot read the clock, so a supplied ts is
    fiction — and the board's durations and cost windows key on ts. append
    overwrites any supplied value with this stamp. It lives at the byte
    boundary beside the canonical serializer, so every append path — the CLI
    and the grading engine's grader-features writer — reaches one clock through the
    validator API (ADR 2026-07-17 runtime-package-layout).
    """
    return datetime.datetime.now(datetime.UTC).isoformat()
