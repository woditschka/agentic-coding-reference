"""Hold the ledger's byte contract: strict JSON in, canonical bytes out, and the schema subset between.

The lowest layer of the handoff package; imports nothing project-local.
"""

import datetime
import json
import re
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple, TypeGuard

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
# The closed validation vocabulary; anything else fails loudly.
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
    "enumFrom",
    "format",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
}
SUPPORTED_FORMATS = {"date-time"}
DEFINITIONS_PREFIX = "#/definitions/"
MAX_REF_HOPS = 10

DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

TYPE_CHECKS: dict[str, Callable[[object], bool]] = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}

# Ledger strings are agent-authored and render in the reader's terminal, so
# no control, direction, or invisible-formatting character survives; the
# joiners stay because emoji sequences and several scripts spell with them.
_BREAK_RE = re.compile(r"[\t\n\r\v\f]+")
_CONTROL_RE = re.compile(
    r"[\x00-\x1f\x7f-\x9f\u200b\u200e\u200f\u2028-\u202e\u2066-\u2069\ufeff]"
)


class LogEntry(NamedTuple):
    """One raw log line: its 1-based number and the parsed object."""

    no: int
    raw: dict[str, Any]


class SchemaError(Exception):
    """A schema that cannot be loaded, resolved, or understood."""


# --- the log -----------------------------------------------------------------


def parse_log(path: str) -> tuple[list[LogEntry], list[str]]:
    """Parse the log strictly into (entries, errors); every line problem is an error, never a raise."""
    text, errors = _read_log(path)
    if text is None:
        return [], errors
    if text and not text.endswith("\n"):
        last_line = text.count("\n") + 1
        errors.append(f"line {last_line}: missing trailing newline")
    entries: list[LogEntry] = []
    for no, line in enumerate(_lines(text), 1):
        parsed = _parse_line(no, line)
        if isinstance(parsed, LogEntry):
            entries.append(parsed)
        else:
            errors.append(parsed)
    return entries, errors


MISSING_LOG = "no handoff log"


def only_missing_log(errors: Sequence[str]) -> bool:
    """Return whether every parse error says the log does not exist yet."""
    return all(MISSING_LOG in error for error in errors)


def parse_log_lenient(path: str) -> list[LogEntry]:
    """Return the parseable object lines of the log with their numbers, skipping the rest."""
    raw_text, _errors = _read_log(path)
    if raw_text is None:
        return []
    entries: list[LogEntry] = []
    for no, line in enumerate(_lines(raw_text), start=1):
        try:
            record = loads_strict(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            entries.append(LogEntry(no, record))
    return entries


def _read_log(path: str) -> tuple[str | None, list[str]]:
    """Read the log's raw text, or return the one error that stands for a log that cannot be read."""
    try:
        # newline="" keeps the readers on the same raw "\n" line domain the
        # append receipt counts.
        with Path(path).open(encoding="utf-8", newline="") as handle:
            return handle.read(), []
    except FileNotFoundError:
        return None, [f"{MISSING_LOG} at {path}"]
    except UnicodeDecodeError as exc:
        return None, [f"log is not valid UTF-8: {exc}"]
    except OSError as exc:
        return None, [f"cannot read {path}: {exc}"]


def _lines(text: str) -> list[str]:
    """Split on the newline only: splitlines() also breaks on separators json.dumps leaves unescaped."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _parse_line(no: int, line: str) -> LogEntry | str:
    """Parse one line into its entry, or return the error that describes the line."""
    if not line.strip():
        return f"line {no}: blank line"
    try:
        record = loads_strict(line)
    except ValueError as exc:
        return f"line {no}: invalid JSON ({decode_error(exc)})"
    except RecursionError:
        return f"line {no}: invalid JSON (nesting too deep)"
    if not isinstance(record, dict):
        return f"line {no}: not a JSON object"
    return LogEntry(no, record)


def loads_strict(text: str) -> Any:  # noqa: ANN401 — the parse boundary yields any JSON value
    """Parse JSON, rejecting NaN, Infinity, and duplicate object keys."""
    return json.loads(
        text, parse_constant=_reject_constant, object_pairs_hook=_reject_duplicate_keys
    )


def _reject_constant(name: str) -> object:
    raise ValueError(f"{name} is not valid JSON")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build an object from its pairs, refusing a duplicate key at any depth."""
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'duplicate key: "{sanitize(key)}"')
        obj[key] = value
    return obj


def decode_error(exc: Exception) -> str:
    """Return the message of a parse failure without its position suffix."""
    return exc.msg if isinstance(exc, json.JSONDecodeError) else str(exc)


def dumps_canonical(record: object) -> str:
    """Serialize a canonical record to its one-line JSON form."""
    return json.dumps(
        record, ensure_ascii=False, allow_nan=False, separators=(", ", ": ")
    )


def sanitize(text: str) -> str:
    """Fold line breaks to spaces and drop every control and direction character."""
    return _CONTROL_RE.sub("", _BREAK_RE.sub(" ", text))


def ts_now() -> str:
    """Return the log's one clock: the current UTC time, stamped on every appended record."""
    return datetime.datetime.now(datetime.UTC).isoformat()


# --- schemas and the layout ----------------------------------------------------


def load_schema(
    schemas_dir: str, record_type: str, layout: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Load a record type's schema with its layout-sourced constraints applied."""
    path = Path(schemas_dir) / f"{record_type}.schema.json"
    if not path.is_file():
        raise SchemaError(
            f"no schema for record type '{record_type}' in {schemas_dir}"
            f" (known types: {_known_types(schemas_dir)})"
        )
    try:
        schema = loads_strict(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SchemaError(f"cannot read schema for '{record_type}': {exc}") from exc
    except ValueError as exc:
        raise SchemaError(
            f"schema for '{record_type}' is not valid JSON: {decode_error(exc)}"
        ) from exc
    if not isinstance(schema, dict):
        raise SchemaError(f"schema for '{record_type}' is not a JSON object")
    return with_layout_sources(schema, layout) if layout else schema


def _known_types(schemas_dir: str) -> str:
    known = sorted(
        p.name[: -len(".schema.json")] for p in Path(schemas_dir).glob("*.schema.json")
    )
    return ", ".join(known) or "none"


def with_layout_sources(
    schema: dict[str, Any], layout: dict[str, Any]
) -> dict[str, Any]:
    """Return the schema with every patternFrom and enumFrom resolved from the layout."""
    resolved = dict(schema)
    pattern = layout_pattern(layout, schema.get("patternFrom"))
    if pattern is not None:
        resolved.setdefault("pattern", pattern)
    members = layout_enum(layout, schema.get("enumFrom"))
    if members is not None:
        resolved.setdefault("enum", members)
    for container in ("properties", "definitions"):
        named = schema.get(container)
        if isinstance(named, dict):
            resolved[container] = {
                name: _sourced(subschema, layout) for name, subschema in named.items()
            }
    for container in ("items", "additionalProperties"):
        if container in schema:
            resolved[container] = _sourced(schema[container], layout)
    return resolved


def _sourced(node: object, layout: dict[str, Any]) -> object:
    return with_layout_sources(node, layout) if isinstance(node, dict) else node


def layout_pattern(layout: dict[str, Any], key: object) -> str | None:
    """Return the layout string a patternFrom key names, or None."""
    if not isinstance(key, str):
        return None
    value = layout_lookup(layout, key)
    return value if isinstance(value, str) else None


def layout_enum(layout: dict[str, Any], key: object) -> list[str] | None:
    """Return the layout list an enumFrom key names when it is a non-empty list of strings, or None."""
    if not isinstance(key, str):
        return None
    members = layout_lookup(layout, key)
    if (
        isinstance(members, list)
        and members
        and all(isinstance(m, str) for m in members)
    ):
        return members
    return None


def layout_lookup(data: dict[str, Any], dotted: str) -> object:
    """Resolve a dotted key in the parsed layout, or None when any segment is missing."""
    current: object = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def read_layout(layout_path: str) -> dict[str, Any]:
    """Parse the layout file; a missing file is an empty layout, an unreadable or unparseable one a SchemaError."""
    path = Path(layout_path)
    if not path.is_file():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise SchemaError(f"{layout_path} exists but cannot be parsed: {exc}") from exc


# --- validation ----------------------------------------------------------------


@dataclass(slots=True)
class _Validation:
    """One validation run: the root schema for references and the errors found so far."""

    root: dict[str, Any]
    errors: list[str] = field(default_factory=list)


def log_schema_errors(
    entries: Sequence[LogEntry], schemas_dir: str, layout: dict[str, Any]
) -> list[str]:
    """Check every record of the log against its schema, each error prefixed with its line."""
    errors: list[str] = []
    for no, record in entries:
        record_type = record.get("type")
        if not isinstance(record_type, str):
            errors.append(f"line {no}: missing 'type' discriminator")
            continue
        try:
            schema = load_schema(schemas_dir, record_type, layout)
        except SchemaError as exc:
            errors.append(f"line {no}: {exc}")
            continue
        errors.extend(f"line {no}: {err}" for err in validate_record(record, schema))
    return errors


def validate_record(record: object, schema: dict[str, Any]) -> list[str]:
    """Return every violation of the schema, or the unsupported keywords that stop the check."""
    errors = [
        f"schema: unsupported keyword at {keyword} — extend the handoff.py mini-validator first"
        for keyword in unsupported_keywords(schema)
    ]
    if errors:
        return errors
    run = _Validation(schema)
    try:
        _validate_value(record, schema, "$", run)
    except SchemaError as exc:
        run.errors.append(f"schema: {exc}")
    return run.errors


def _validate_value(value: object, schema: object, path: str, run: _Validation) -> None:
    """Check one value against its schema, appending every violation to the run."""
    schema = resolve_ref(schema, run.root)
    if not isinstance(schema, dict):
        raise SchemaError(f"unsupported schema form at {path}: {type(schema).__name__}")
    errors = run.errors
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
    if not _type_matches(value, schema, path, errors):
        return
    if isinstance(value, str):
        _check_string(value, schema, path, errors)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        _check_number(value, schema, path, errors)
    elif isinstance(value, dict):
        _check_object(value, schema, path, run)
    elif isinstance(value, list):
        _check_array(value, schema, path, run)


def _type_matches(
    value: object, schema: dict[str, Any], path: str, errors: list[str]
) -> bool:
    """Check the declared type; an unknown type name is a schema error, a mismatch a violation."""
    expected = schema.get("type")
    if expected is None:
        return True
    allowed = expected if isinstance(expected, list) else [expected]
    unknown = [t for t in allowed if t not in TYPE_CHECKS]
    if unknown:
        raise SchemaError(f"unknown type {unknown} in schema at {path}")
    if any(TYPE_CHECKS[t](value) for t in allowed):
        return True
    errors.append(
        f"{path}: expected type {'/'.join(allowed)}, got {type(value).__name__}"
    )
    return False


def _check_string(
    value: str, schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    if "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path}: shorter than minLength {schema['minLength']}")
    if "maxLength" in schema and len(value) > schema["maxLength"]:
        errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
    if "pattern" in schema:
        _check_pattern(value, schema["pattern"], path, errors)
    if schema.get("format") == "date-time" and not DATE_TIME_RE.match(value):
        errors.append(f"{path}: {json.dumps(value)} is not an ISO 8601 date-time")


def _check_pattern(value: str, pattern: object, path: str, errors: list[str]) -> None:
    """Match the value against a pattern that may come from the consumer's layout."""
    if not _is_valid_pattern(pattern):
        errors.append(
            f"{path}: schema pattern {sanitize(str(pattern))!r} "
            "is not a valid regex (check its patternFrom source in "
            "scripts/layout.toml)"
        )
    elif re.search(pattern, value) is None:
        errors.append(
            f"{path}: {json.dumps(value)} does not match pattern {sanitize(pattern)}"
        )


def _is_valid_pattern(pattern: object) -> TypeGuard[str]:
    if not isinstance(pattern, str):
        return False
    try:
        re.compile(pattern)
    except re.error:
        return False
    return True


def _check_number(
    value: float, schema: dict[str, Any], path: str, errors: list[str]
) -> None:
    if "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path}: {value} below minimum {schema['minimum']}")
    if "maximum" in schema and value > schema["maximum"]:
        errors.append(f"{path}: {value} above maximum {schema['maximum']}")


def _check_object(
    value: dict[Any, Any], schema: dict[str, Any], path: str, run: _Validation
) -> None:
    run.errors.extend(
        f"{path}: missing required field '{required}'"
        for required in schema.get("required", [])
        if required not in value
    )
    properties = schema.get("properties", {})
    extra = schema.get("additionalProperties")
    for key, item in value.items():
        if key in properties:
            _validate_value(item, properties[key], f"{path}.{key}", run)
        elif extra is False:
            run.errors.append(
                f"{path}: unexpected field '{sanitize(key)}' (additionalProperties: false)"
            )
        elif isinstance(extra, dict):
            _validate_value(item, extra, f"{path}.{sanitize(key)}", run)


def _check_array(
    value: list[Any], schema: dict[str, Any], path: str, run: _Validation
) -> None:
    if "minItems" in schema and len(value) < schema["minItems"]:
        run.errors.append(f"{path}: fewer than minItems {schema['minItems']}")
    if "maxItems" in schema and len(value) > schema["maxItems"]:
        run.errors.append(f"{path}: more than maxItems {schema['maxItems']}")
    items = schema.get("items")
    if isinstance(items, dict):
        for index, item in enumerate(value):
            _validate_value(item, items, f"{path}[{index}]", run)


def unsupported_keywords(schema: object, path: str = "#") -> list[str]:
    """List the locations of every keyword outside the supported subset."""
    if not isinstance(schema, dict):
        return []
    found: list[str] = []
    for key, value in schema.items():
        here = f"{path}/{key}"
        if key not in ANNOTATIONS and key not in SUPPORTED:
            found.append(here)
        if key == "format" and value not in SUPPORTED_FORMATS:
            found.append(f"{here}={value}")
    found += _unsupported_in_subschemas(schema, path)
    found += _unsupported_in_containers(schema, path)
    return found


def _unsupported_in_subschemas(schema: dict[str, Any], path: str) -> list[str]:
    """Walk the single-subschema keywords, items and additionalProperties."""
    found: list[str] = []
    for key in ("items", "additionalProperties"):
        if key not in schema:
            continue
        subschema = schema[key]
        if isinstance(subschema, dict):
            found += unsupported_keywords(subschema, f"{path}/{key}")
        elif not (key == "additionalProperties" and isinstance(subschema, bool)):
            found.append(
                f"{path}/{key} (unsupported schema form: {type(subschema).__name__})"
            )
    return found


def _unsupported_in_containers(schema: dict[str, Any], path: str) -> list[str]:
    """Walk the named-subschema containers, properties and definitions."""
    found: list[str] = []
    for container in ("properties", "definitions"):
        named = schema.get(container)
        if not isinstance(named, dict):
            continue
        for name, subschema in named.items():
            if isinstance(subschema, dict):
                found += unsupported_keywords(subschema, f"{path}/{container}/{name}")
            else:
                found.append(
                    f"{path}/{container}/{name} (unsupported schema form:"
                    f" {type(subschema).__name__})"
                )
    return found


def resolve_ref(schema: object, root: dict[str, Any]) -> object:
    """Follow a chain of local definition references to the schema it names."""
    hops = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith(DEFINITIONS_PREFIX):
            raise SchemaError(
                f"unsupported $ref '{ref}' (only {DEFINITIONS_PREFIX}<name> is supported)"
            )
        name = ref[len(DEFINITIONS_PREFIX) :]
        definitions = root.get("definitions", {})
        if name not in definitions:
            raise SchemaError(f"$ref '{ref}' has no matching definition")
        schema = definitions[name]
        hops += 1
        if hops > MAX_REF_HOPS:
            raise SchemaError("$ref chain too deep")
    return schema


def schema_equal(a: object, b: object) -> bool:
    """Compare two JSON values the way draft-07 does: a boolean never equals a number."""
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return bool(a == b)


# --- canonical form ------------------------------------------------------------


def canonicalize(value: object, schema: object, root: dict[str, Any]) -> object:
    """Reorder object fields into schema declaration order; unknown keys sort last."""
    shape = _resolved_shape(schema, root)
    if isinstance(value, dict):
        properties = shape.get("properties", {})
        extra = shape.get("additionalProperties")
        extra_schema = extra if isinstance(extra, dict) else {}
        ordered: dict[str, Any] = {}
        for key in properties:
            if key in value:
                ordered[key] = canonicalize(value[key], properties[key], root)
        for key in sorted(k for k in value if k not in properties):
            ordered[key] = canonicalize(value[key], extra_schema, root)
        return ordered
    if isinstance(value, list):
        items = shape.get("items", {})
        return [canonicalize(v, items, root) for v in value]
    return value


def _resolved_shape(schema: object, root: dict[str, Any]) -> dict[str, Any]:
    """Resolve the schema to the object that shapes the value; anything unresolvable shapes nothing."""
    if not isinstance(schema, dict):
        return {}
    try:
        resolved = resolve_ref(schema, root)
    except SchemaError:
        return {}
    return resolved if isinstance(resolved, dict) else {}
