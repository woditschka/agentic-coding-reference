#!/usr/bin/env python3
"""Characterization tests for handoff.py (stdlib only).

Run: python3 scripts/test_handoff.py

Covers the determinism contract: canonical field order (schema declaration
order, unknown keys last), byte-identical output for identical logical
records, append-side validation against the schema subset, newline repair,
and the gate queries (latest, next-retry). The real-schema sweep pins every
schema in schemas/scratch/ to the validator's supported vocabulary, so a
schema edit that introduces an unsupported keyword fails here, not at
append time.
"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO_SCHEMAS = _HERE.parent / "schemas" / "scratch"


def _load():
    spec = importlib.util.spec_from_file_location("handoff", _HERE / "handoff.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


handoff = _load()

REQ = "REQ-DEMO-001"
TS = "2026-06-11T10:00:00Z"

TEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["type", "req_id", "ts", "author"],
    "properties": {
        "type": {"const": "test-rec"},
        "req_id": {"type": "string", "pattern": "^REQ-[A-Z]+-[0-9]{3}$"},
        "ts": {"type": "string", "format": "date-time"},
        "author": {"enum": ["tester"]},
        "note": {"type": "string", "minLength": 1},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "nested": {
            "type": "object",
            "required": ["zee"],
            "properties": {"zee": {"type": "string"}, "aye": {"type": "string"}},
        },
        "retry": {"type": "integer", "minimum": 1, "maximum": 3},
    },
}

STRICT_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {"type": {"const": "strict-rec"}},
    "additionalProperties": False,
}

REF_SCHEMA = {
    "type": "object",
    "required": ["type", "facet"],
    "properties": {"type": {"const": "ref-rec"}, "facet": {"$ref": "#/definitions/facet"}},
    "definitions": {"facet": {"enum": ["clear", "concern"]}},
}

BAD_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "bad-rec"}, "x": {"anyOf": [{"type": "string"}]}},
}

NUM_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"const": "num-rec"},
        "n": {"enum": [1, 2]},
        "flag": {"const": True},
    },
}

BADTYPE_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "badtype-rec"}, "x": {"type": "strin"}},
}

BOOLSUB_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "boolsub-rec"}, "x": True},
}

TUPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "tuple-rec"},
        "x": {"type": "array", "items": [{"type": "string"}]},
    },
}

PATTERNFROM_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"const": "pf-rec"},
        "tname": {"type": "string", "patternFrom": "test_name_pattern"},
    },
}


def base_record(**overrides):
    record = {"type": "test-rec", "req_id": REQ, "ts": TS, "author": "tester"}
    record.update(overrides)
    return record


class HandoffCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.log = root / "handoff.jsonl"
        self.schemas = root / "schemas"
        self.schemas.mkdir()
        for name, schema in (
            ("test-rec", TEST_SCHEMA),
            ("strict-rec", STRICT_SCHEMA),
            ("ref-rec", REF_SCHEMA),
            ("bad-rec", BAD_SCHEMA),
            ("num-rec", NUM_SCHEMA),
            ("badtype-rec", BADTYPE_SCHEMA),
            ("boolsub-rec", BOOLSUB_SCHEMA),
            ("tuple-rec", TUPLE_SCHEMA),
            ("pf-rec", PATTERNFROM_SCHEMA),
        ):
            (self.schemas / f"{name}.schema.json").write_text(json.dumps(schema))

    def run_cli(self, *argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = handoff.main(list(argv))
                except SystemExit as exc:
                    code = exc.code
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue(), err.getvalue()

    def append(self, record, rtype=None, schemas=None):
        return self.run_cli(
            "append",
            rtype or record.get("type", "test-rec"),
            "--file",
            str(self.log),
            "--schemas",
            str(schemas or self.schemas),
            stdin=json.dumps(record),
        )

    def log_lines(self):
        return self.log.read_text().splitlines()

    def write_log(self, *records):
        self.log.write_text("".join(json.dumps(r) + "\n" for r in records))


class TestAppendCanonicalForm(HandoffCase):
    def test_orders_fields_by_schema_declaration(self):
        shuffled = {"author": "tester", "note": "n", "type": "test-rec", "ts": TS, "req_id": REQ}
        code, out, err = self.append(shuffled)
        self.assertEqual(code, 0, err)
        expected = (
            '{"type": "test-rec", "req_id": "REQ-DEMO-001",'
            ' "ts": "2026-06-11T10:00:00Z", "author": "tester", "note": "n"}'
        )
        self.assertEqual(self.log_lines(), [expected])

    def test_same_logical_record_same_bytes(self):
        a = {"type": "test-rec", "req_id": REQ, "ts": TS, "author": "tester"}
        b = {"author": "tester", "ts": TS, "req_id": REQ, "type": "test-rec"}
        self.append(a)
        self.append(b)
        lines = self.log_lines()
        self.assertEqual(lines[0], lines[1])

    def test_nested_object_ordered_by_subschema(self):
        code, _, err = self.append(base_record(nested={"aye": "a", "zee": "z"}))
        self.assertEqual(code, 0, err)
        line = self.log_lines()[0]
        self.assertLess(line.index('"zee"'), line.index('"aye"'))

    def test_unknown_fields_sort_last(self):
        code, _, err = self.append(base_record(zzz=1, aaa=2))
        self.assertEqual(code, 0, err)
        line = self.log_lines()[0]
        self.assertLess(line.index('"author"'), line.index('"aaa"'))
        self.assertLess(line.index('"aaa"'), line.index('"zzz"'))

    def test_reports_appended_line_number(self):
        _, out, _ = self.append(base_record())
        self.assertEqual(out, "appended test-rec at line 1\n")
        _, out, _ = self.append(base_record())
        self.assertEqual(out, "appended test-rec at line 2\n")

    def test_repairs_missing_trailing_newline(self):
        self.log.write_text(json.dumps(base_record()))  # no trailing newline
        code, _, err = self.append(base_record(note="second"))
        self.assertEqual(code, 0)
        self.assertIn("repaired", err)
        lines = self.log_lines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)


class TestAppendValidation(HandoffCase):
    def test_rejects_missing_required(self):
        record = base_record()
        del record["author"]
        code, _, err = self.append(record)
        self.assertEqual(code, 1)
        self.assertIn("missing required field 'author'", err)
        self.assertFalse(self.log.exists())

    def test_rejects_enum_violation(self):
        code, _, err = self.append(base_record(author="impostor"))
        self.assertEqual(code, 1)
        self.assertIn("not in enum", err)

    def test_rejects_pattern_violation(self):
        code, _, err = self.append(base_record(req_id="REQ-1"))
        self.assertEqual(code, 1)
        self.assertIn("pattern", err)

    def test_rejects_bad_timestamp(self):
        code, _, err = self.append(base_record(ts="yesterday"))
        self.assertEqual(code, 1)
        self.assertIn("date-time", err)

    def test_rejects_retry_out_of_bounds(self):
        code, _, err = self.append(base_record(retry=0))
        self.assertEqual(code, 1)
        self.assertIn("minimum", err)
        code, _, err = self.append(base_record(retry=4))
        self.assertEqual(code, 1)
        self.assertIn("maximum", err)
        code, _, err = self.append(base_record(retry=2))
        self.assertEqual(code, 0, err)

    def test_rejects_empty_tags(self):
        code, _, err = self.append(base_record(tags=[]))
        self.assertEqual(code, 1)
        self.assertIn("minItems", err)
        code, _, err = self.append(base_record(tags=["a"]))
        self.assertEqual(code, 0, err)

    def test_rejects_type_argument_mismatch(self):
        code, _, err = self.append(base_record(), rtype="strict-rec")
        self.assertEqual(code, 1)
        self.assertIn("does not match", err)

    def test_rejects_unknown_record_type(self):
        code, _, err = self.append({"type": "nope"}, rtype="nope")
        self.assertEqual(code, 1)
        self.assertIn("known types", err)
        self.assertIn("test-rec", err)

    def test_rejects_additional_properties_false(self):
        code, _, err = self.append({"type": "strict-rec", "x": 1})
        self.assertEqual(code, 1)
        self.assertIn("unexpected field 'x'", err)

    def test_rejects_non_object_record(self):
        code, _, err = self.run_cli(
            "append", "test-rec", "--file", str(self.log), "--schemas", str(self.schemas),
            stdin="[1, 2]",
        )
        self.assertEqual(code, 1)
        self.assertIn("JSON object", err)

    def test_ref_resolution(self):
        code, _, err = self.append({"type": "ref-rec", "facet": "clear"})
        self.assertEqual(code, 0, err)
        code, _, err = self.append({"type": "ref-rec", "facet": "nope"})
        self.assertEqual(code, 1)
        self.assertIn("not in enum", err)

    def test_unsupported_keyword_fails_loudly(self):
        code, _, err = self.append({"type": "bad-rec"})
        self.assertEqual(code, 1)
        self.assertIn("anyOf", err)
        self.assertIn("unsupported keyword", err)


class TestHardening(HandoffCase):
    def test_unicode_line_separators_do_not_corrupt_log(self):
        note = "a\u2028b\u2029c\u0085d"  # LS, PS, NEL pass through ensure_ascii=False unescaped
        code, _, err = self.append(base_record(note=note))
        self.assertEqual(code, 0, err)
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "1 records valid\n")
        code, out, _ = self.run_cli(
            "latest", "--type", "test-rec", "--file", str(self.log)
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["note"], note)

    def test_booleans_do_not_satisfy_numeric_const_or_enum(self):
        code, _, err = self.append({"type": "num-rec", "n": True})
        self.assertEqual(code, 1)
        self.assertIn("not in enum", err)
        code, _, err = self.append({"type": "num-rec", "flag": 1})
        self.assertEqual(code, 1)
        self.assertIn("const", err)
        code, _, err = self.append({"type": "num-rec", "n": 1, "flag": True})
        self.assertEqual(code, 0, err)

    def test_unknown_type_name_fails_cleanly(self):
        code, _, err = self.append({"type": "badtype-rec", "x": "y"})
        self.assertEqual(code, 1)
        self.assertIn("unknown type", err)
        self.assertNotIn("Traceback", err)

    def test_boolean_subschema_fails_loudly(self):
        code, _, err = self.append({"type": "boolsub-rec"})
        self.assertEqual(code, 1)
        self.assertIn("unsupported schema form", err)

    def test_tuple_form_items_fails_loudly(self):
        code, _, err = self.append({"type": "tuple-rec", "x": ["a"]})
        self.assertEqual(code, 1)
        self.assertIn("unsupported schema form", err)

    def test_nan_rejected_on_stdin(self):
        code, _, err = self.run_cli(
            "append", "test-rec", "--file", str(self.log), "--schemas", str(self.schemas),
            stdin='{"type": "test-rec", "extra": NaN}',
        )
        self.assertEqual(code, 1)
        self.assertIn("not valid JSON", err)
        self.assertFalse(self.log.exists())

    def test_next_retry_warns_above_schema_maximum(self):
        retry_schema = {
            "type": "object",
            "properties": {"retry": {"type": "integer", "minimum": 1, "maximum": 3}},
        }
        (self.schemas / "build-failure.schema.json").write_text(json.dumps(retry_schema))
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001"},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 2},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 3},
        )
        code, out, err = self.run_cli(
            "next-retry", "--req-id", "REQ-A-001",
            "--file", str(self.log), "--schemas", str(self.schemas),
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "4\n")
        self.assertIn("exceeds the schema maximum", err)


class TestValidate(HandoffCase):
    def validate(self):
        return self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )

    def test_clean_log(self):
        self.append(base_record())
        self.append({"type": "ref-rec", "facet": "clear"})
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "2 records valid\n")

    def test_detects_glued_records(self):
        line = json.dumps(base_record())
        self.log.write_text(line + line + "\n")
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("invalid JSON", err)

    def test_detects_blank_line(self):
        self.log.write_text(json.dumps(base_record()) + "\n\n")
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("blank line", err)

    def test_detects_unknown_type(self):
        self.write_log({"type": "mystery"})
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("no schema for record type 'mystery'", err)

    def test_missing_file_fails(self):
        code, _, err = self.validate()
        self.assertEqual(code, 1)
        self.assertIn("no handoff log", err)


class TestQueries(HandoffCase):
    def test_latest_returns_last_match(self):
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001", "verdict": "covered"},
            {"type": "design-block", "req_id": "REQ-A-001", "verdict": "minor"},
            {"type": "design-block", "req_id": "REQ-B-001", "verdict": "new"},
        )
        code, out, err = self.run_cli(
            "latest", "--type", "design-block", "--req-id", "REQ-A-001",
            "--file", str(self.log),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["verdict"], "minor")

    def test_latest_with_line_prefix(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, out, _ = self.run_cli(
            "latest", "--type", "design-block", "--with-line", "--file", str(self.log)
        )
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("1\t"))

    def test_latest_no_match_exits_3(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, _, err = self.run_cli(
            "latest", "--type", "build-pass", "--file", str(self.log)
        )
        self.assertEqual(code, 3)
        self.assertIn("no build-pass record", err)

    def test_latest_refuses_corrupt_log(self):
        self.log.write_text("not json\n")
        code, _, err = self.run_cli(
            "latest", "--type", "design-block", "--file", str(self.log)
        )
        self.assertEqual(code, 1)
        self.assertIn("run validate", err)

    def test_next_retry_counts_after_latest_design_block(self):
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001"},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-B-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 2},
            {"type": "design-block", "req_id": "REQ-A-001", "supersedes_record_at": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
        )
        code, out, err = self.run_cli(
            "next-retry", "--req-id", "REQ-A-001", "--file", str(self.log)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "2\n")

    def test_next_retry_without_design_block_exits_3(self):
        self.write_log({"type": "build-failure", "req_id": "REQ-A-001", "retry": 1})
        code, _, err = self.run_cli(
            "next-retry", "--req-id", "REQ-A-001", "--file", str(self.log)
        )
        self.assertEqual(code, 3)
        self.assertIn("no design-block", err)


class TestShow(HandoffCase):
    def test_show_marks_unparseable_lines(self):
        self.log.write_text(json.dumps(base_record()) + "\nnot json\n")
        code, out, _ = self.run_cli("show", "--file", str(self.log))
        self.assertEqual(code, 0)
        self.assertIn("UNPARSEABLE", out)
        self.assertIn("test-rec · REQ-DEMO-001", out)

    def test_show_empty_filter(self):
        self.write_log({"type": "design-block", "req_id": "REQ-A-001"})
        code, out, _ = self.run_cli(
            "show", "--type", "build-pass", "--file", str(self.log)
        )
        self.assertEqual(code, 0)
        self.assertIn("no matching records", out)


class TestRealSchemas(unittest.TestCase):
    def test_every_repo_schema_within_validator_subset(self):
        paths = sorted(_REPO_SCHEMAS.glob("*.schema.json"))
        self.assertTrue(paths, f"no schemas found at {_REPO_SCHEMAS}")
        for path in paths:
            with self.subTest(schema=path.name):
                schema = json.loads(path.read_text())
                self.assertEqual(handoff.unsupported_keywords(schema), [])

    def test_dispatch_start_roundtrip_against_real_schema(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = Path(tmp.name) / "handoff.jsonl"
        record = {
            "responding_to": [0],
            "author": "feature-implementer",
            "ts": TS,
            "req_id": "REQ-DEMO-001",
            "type": "dispatch-start",
        }
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(record))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = handoff.main(
                    ["append", "dispatch-start", "--file", str(log),
                     "--schemas", str(_REPO_SCHEMAS)]
                )
        finally:
            sys.stdin = old_stdin
        self.assertEqual(code, 0, err.getvalue())
        line = log.read_text().splitlines()[0]
        self.assertLess(line.index('"type"'), line.index('"req_id"'))
        self.assertLess(line.index('"author"'), line.index('"responding_to"'))

    def test_dispatch_start_accepts_declared_extra_reviewer(self):
        # The roster is the floor plus extra_reviewers; every roster reviewer
        # carries the dispatch-start contract, so the schema must accept
        # *-reviewer names beyond the floor (roster membership is the doctor's
        # check, not the schema's).
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = Path(tmp.name) / "handoff.jsonl"
        record = {
            "responding_to": [3],
            "author": "perf-reviewer",
            "ts": TS,
            "req_id": "REQ-DEMO-001",
            "type": "dispatch-start",
        }
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(record))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = handoff.main(
                    ["append", "dispatch-start", "--file", str(log),
                     "--schemas", str(_REPO_SCHEMAS)]
                )
        finally:
            sys.stdin = old_stdin
        self.assertEqual(code, 0, err.getvalue())


class TestPatternFrom(HandoffCase):
    """`patternFrom` sources a string pattern from layout.toml — the single
    source shared with the engines (e.g. the test-name shape)."""

    def _layout(self, body):
        path = self.schemas.parent / "layout.toml"
        path.write_text(body)
        return path

    def _append_pf(self, tname, layout):
        return self.run_cli(
            "append", "pf-rec",
            "--file", str(self.log),
            "--schemas", str(self.schemas),
            "--layout", str(layout),
            stdin=json.dumps({"type": "pf-rec", "tname": tname}),
        )

    def test_layout_pattern_accepts_match(self):
        layout = self._layout("test_name_pattern = '^Test[A-Z]'\n")
        code, _, err = self._append_pf("TestFoo", layout)
        self.assertEqual(code, 0, err)

    def test_layout_pattern_rejects_violation(self):
        layout = self._layout("test_name_pattern = '^Test[A-Z]'\n")
        code, _, err = self._append_pf("notATest", layout)
        self.assertEqual(code, 1)
        self.assertIn("pattern", err)
        self.assertFalse(self.log.exists())

    def test_missing_key_skips_shape_check(self):
        # Key absent from layout: never block on a missing optional source.
        layout = self._layout("other = 'x'\n")
        code, _, err = self._append_pf("notATest", layout)
        self.assertEqual(code, 0, err)

    def test_absent_layout_skips_shape_check(self):
        # Layout file does not exist: patternFrom goes unenforced.
        missing = self.schemas.parent / "nonexistent.toml"
        code, _, err = self._append_pf("notATest", missing)
        self.assertEqual(code, 0, err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
