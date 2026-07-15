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
import datetime
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
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
    "properties": {"type": {"const": "strict-rec"}, "ts": {"type": "string"}},
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
        stamp = unittest.mock.patch.object(handoff, "ts_now", return_value=TS)
        stamp.start()
        self.addCleanup(stamp.stop)

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

    def test_overwrites_supplied_ts(self):
        code, _, err = self.append(base_record(ts="2020-01-01T00:00:00Z"))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], TS)

    def test_fills_missing_ts(self):
        record = base_record()
        del record["ts"]
        code, _, err = self.append(record)
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], TS)

    def test_repairs_missing_trailing_newline(self):
        self.log.write_text(json.dumps(base_record()))  # no trailing newline
        code, _, err = self.append(base_record(note="second"))
        self.assertEqual(code, 0)
        self.assertIn("repaired", err)
        lines = self.log_lines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)


class TestTsNow(unittest.TestCase):
    # Outside HandoffCase: the stamp must come from the real clock, unpatched.
    def test_utc_iso_8601(self):
        parsed = datetime.datetime.fromisoformat(handoff.ts_now())
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))


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

    def test_bad_supplied_timestamp_is_overwritten(self):
        code, _, err = self.append(base_record(ts="yesterday"))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(self.log_lines()[0])["ts"], TS)

    def test_validate_rejects_bad_timestamp_in_log(self):
        # The format check still guards the log sweep: a legacy or raw-written
        # record with a bad ts fails validate even though append now stamps.
        self.write_log(base_record(ts="yesterday"))
        code, _, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
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

    def test_show_plain_text_cannot_inject_terminal_escapes(self):
        # show prints an unparseable line raw and builds a header from record
        # fields; neither may carry an escape byte to the reader's terminal.
        # (The JSON body escapes C0 controls via json.dumps.)
        self.log.write_text(
            json.dumps(base_record(type="test-rec")) + "\n"
            "raw \x1b]0;pwned\x07\x1b[2J line\n"
        )
        code, out, _ = self.run_cli("show", "--file", str(self.log))
        self.assertEqual(code, 0)
        self.assertNotIn("\x1b", out)
        self.assertIn("UNPARSEABLE", out)


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
        # Three prior lines so the [3] pointer has a referent — append bounds
        # responding_to against the existing log.
        log.write_text('{"type": "prd-entry"}\n' * 3)
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


# Route fixtures use permissive schemas: route's own decisions are under test,
# not the validator (TestAppendValidation covers that). Gate-failure tests
# override one schema with a strict variant.
PERMISSIVE = {"type": "object", "required": ["type"]}
PIPELINE_TYPES = (
    "prd-entry", "design-block", "build-pass", "build-failure",
    "review-feedback", "consultation-request", "consultation-response",
    "dispatch-start", "design-doc-autofix", "grader-features", "grader-verdict",
    "review-plan",
)
FLOOR = ["code-quality-reviewer", "test-reviewer", "security-reviewer", "doc-reviewer"]


def rec(rtype, **fields):
    record = {"type": rtype, "req_id": "REQ-A-001", "ts": TS, "author": "tester"}
    record.update(fields)
    return record


class RouteCase(HandoffCase):
    def setUp(self):
        super().setUp()
        for name in PIPELINE_TYPES:
            (self.schemas / f"{name}.schema.json").write_text(json.dumps(PERMISSIVE))

    def route(self, *extra):
        code, out, err = self.run_cli(
            "route", "--file", str(self.log), "--schemas", str(self.schemas), *extra
        )
        self.assertEqual(code, 0, err)
        return json.loads(out)


class TestRouteDamageModes(RouteCase):
    def test_missing_log_escalates_no_active_slice(self):
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_dirty_log_blocks_with_parse_errors(self):
        self.log.write_text(json.dumps(rec("prd-entry")) + "\ngarbage\n")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("line 2: invalid JSON (Expecting value)", decision["errors"][0])

    def test_truncated_final_line_blocks(self):
        # An agent dying mid-append leaves no trailing newline; route must
        # refuse to guess over it.
        self.log.write_text(json.dumps(rec("prd-entry")) + "\n" + '{"type": "desi')
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")

    def test_missing_req_id_blocks(self):
        self.write_log({"type": "prd-entry", "ts": TS, "author": "tester"})
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "missing-req-id")

    def test_empty_existing_log_escalates_no_active_slice(self):
        self.log.write_text("")
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_unreadable_log_path_blocks_with_exit_zero(self):
        # A directory at the log path is a dirty-log error, not a traceback:
        # route keeps its exit-0-with-decision contract.
        self.log.mkdir()
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("cannot read", decision["errors"][0])

    def test_unknown_req_id_blocks(self):
        self.write_log(rec("prd-entry"))
        decision = self.route("--req-id", "REQ-Z-999")
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "unknown-req-id")


class TestRouteHappyPath(RouteCase):
    def test_prd_routes_to_designer(self):
        self.write_log(rec("prd-entry", author="product-requirements-expert"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "prd-approved")

    def test_prd_gate_failure_bounces_upstream(self):
        strict = {"type": "object", "required": ["type", "title"]}
        (self.schemas / "prd-entry.schema.json").write_text(json.dumps(strict))
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["product-requirements-expert"])
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertTrue(decision["context"]["errors"])

    def test_unknown_design_verdict_bounces_upstream(self):
        self.write_log(rec("design-block", verdict="bogus"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "design-gate-failed")

    def test_invalid_build_pass_bounces_to_implementer(self):
        strict = {"type": "object", "required": ["type", "gate_checks_run"]}
        (self.schemas / "build-pass.schema.json").write_text(json.dumps(strict))
        self.write_log(rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "build-record-invalid")

    def test_refactor_sibling_prd_escalates(self):
        # The realistic two-record shape: refactor-first design-block plus the
        # designer-authored sibling prd-entry appended last. Route must not
        # advance the sibling on its own; ordering is the coordinator's call.
        self.write_log(
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("prd-entry", req_id="REQ-B-001", author="system-design-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "refactor-first")

    def test_refactor_resume_after_sibling_completes(self):
        records = [
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("build-pass", req_id="REQ-B-001"),
        ]
        records += [
            rec("review-feedback", req_id="REQ-B-001", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        records.append(rec("grader-verdict", req_id="REQ-B-001", author="change-grader", verdict="clear"))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "refactor-resume")
        self.assertEqual(decision["context"]["original_req_id"], "REQ-A-001")

    def test_refactor_resume_on_approval_when_grading_disabled(self):
        # With auto_grade = false the refactor sibling has no grader-verdict to
        # resume on; roster approval is the completion signal instead.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = false\n')
        records = [
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("build-pass", req_id="REQ-B-001"),
        ]
        records += [
            rec("review-feedback", req_id="REQ-B-001", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        self.write_log(*records)
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "refactor-resume")
        self.assertEqual(decision["context"]["original_req_id"], "REQ-A-001")
        self.assertNotIn("verdict", decision["context"])

    def test_grader_features_without_verdict_redispatches_grader(self):
        records = [rec("build-pass")]
        records += [rec("review-feedback", author=r, verdict="approved", findings=[]) for r in FLOOR]
        records.append(rec("grader-features", author="change-grader", features=[]))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade-continue")

    def test_partial_failure_carries_partial_context(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1, partial=True),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "build-retry")
        self.assertTrue(decision["context"]["partial"])

    def test_unreadable_layout_blocks(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness\nbroken = ")
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route", "--file", str(self.log), "--schemas", str(self.schemas),
            "--layout", str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "layout-unreadable")

    def test_non_list_extra_reviewers_blocks(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = "perf-reviewer"\n')
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route", "--file", str(self.log), "--schemas", str(self.schemas),
            "--layout", str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "layout-invalid")

    def test_approved_design_routes_to_implementer(self):
        self.write_log(rec("prd-entry"), rec("design-block", verdict="covered"))
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "design-approved")

    def test_conflicting_design_blocks(self):
        self.write_log(rec("design-block", verdict="conflicting", escalations=["e1"]))
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "design-conflict")
        self.assertEqual(decision["context"]["escalations"], ["e1"])
        self.assertNotIn("errors", decision)

    def test_conflicting_without_escalations_names_the_gap(self):
        # Gate 2: conflicting requires a non-empty escalations array. Still
        # blocked; the error tells the human what the record failed to carry.
        self.write_log(rec("design-block", verdict="conflicting"))
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "design-conflict")
        self.assertIn("no escalations", decision["errors"][0])

    def test_dangling_supersedes_pointer_fails_the_design_gate(self):
        self.write_log(
            rec("prd-entry"),
            rec("design-block", verdict="covered", supersedes_record_at=99),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "design-gate-failed")
        self.assertIn("supersedes_record_at", decision["context"]["errors"][0])

    def test_valid_supersedes_pointer_passes_the_design_gate(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1),
            rec("design-block", verdict="minor", supersedes_record_at=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "design-approved")

    def test_refactor_first_escalates_to_coordinator(self):
        self.write_log(rec("design-block", verdict="refactor-first"))
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "refactor-first")

    def test_build_pass_dispatches_full_roster(self):
        self.write_log(rec("design-block", verdict="covered"), rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")

    def test_build_pass_postdating_a_build_failure_gates_reviews(self):
        # The table row: the latest build-pass post-dates any build-failure
        # for the slice — the earlier failure must not re-enter recovery.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")

    def test_extra_reviewer_from_layout_joins_roster(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route", "--file", str(self.log), "--schemas", str(self.schemas),
            "--layout", str(layout),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["next"], FLOOR + ["perf-reviewer"])

    def test_all_approved_dispatches_grader(self):
        records = [rec("build-pass")]
        records += [rec("review-feedback", author=r, verdict="approved", findings=[]) for r in FLOOR]
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_grader_verdict_completes_feature(self):
        records = [rec("build-pass")]
        records += [rec("review-feedback", author=r, verdict="approved", findings=[]) for r in FLOOR]
        records.append(rec("grader-verdict", author="change-grader", verdict="clear"))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertEqual(decision["context"]["verdict"], "clear")

    def _approved_records(self):
        records = [rec("build-pass")]
        records += [rec("review-feedback", author=r, verdict="approved", findings=[]) for r in FLOOR]
        return records

    def test_auto_grade_false_completes_without_grader(self):
        # auto_grade = false: the approved state is terminal with no grader run.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = false\n')
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertNotIn("verdict", decision.get("context", {}))
        self.assertIn("grading disabled", decision["reason"])

    def test_auto_grade_false_still_honors_manual_grader_verdict(self):
        # A hand-run grader appends a grader-verdict; it still routes to
        # feature-complete carrying the verdict, grading toggle notwithstanding.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = false\n')
        records = self._approved_records()
        records.append(rec("grader-verdict", author="change-grader", verdict="clear"))
        self.write_log(*records)
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertEqual(decision["context"]["verdict"], "clear")

    def test_auto_grade_true_explicit_dispatches_grader(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = true\n')
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_auto_grade_non_bool_fails_open_to_grading(self):
        # The router fails open: a malformed value keeps grading on. The doctor
        # is the layer that flags the typo.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = "false"\n')
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_req_id_flag_selects_slice(self):
        self.write_log(
            rec("prd-entry"),
            rec("prd-entry", req_id="REQ-B-001"),
        )
        decision = self.route("--req-id", "REQ-A-001")
        self.assertEqual(decision["req_id"], "REQ-A-001")
        self.assertEqual(decision["next"], ["system-design-expert"])


class TestRouteReviewCycle(RouteCase):
    def approved(self, reviewer):
        return rec("review-feedback", author=reviewer, verdict="approved", findings=[])

    def test_changes_requested_routes_to_implementer(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d",
                   "clarify_target": "system-design-expert"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["reviewers"], ["doc-reviewer"])

    def test_blocked_verdict_routes_like_changes_requested(self):
        finding = {"tag": "blocked", "location": "src/widget:1", "description": "d",
                   "severity": "critical"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="blocked", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "process-findings")

    def test_escalate_finding_in_approved_record_joins_the_split(self):
        # The escalate tag crosses the approved boundary: the implementer
        # must receive it to append .scratch/escalations.md, and the round
        # halts after processing.
        escalate = {"tag": "escalate", "location": "src/auth/session:10", "description": "sev"}
        prd = {"tag": "blocked", "location": "docs/prd.md:9", "description": "prd",
               "severity": "critical"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:2]],
            rec("review-feedback", author="security-reviewer", verdict="approved", findings=[escalate]),
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[prd]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertIn("feature-implementer", decision["next"])
        self.assertIn("product-requirements-expert", decision["next"])
        self.assertTrue(decision["context"]["halt_after"])
        self.assertEqual(decision["context"]["escalate_findings"], 1)

    def test_clarify_finding_without_target_bounces_the_reviewer(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertIn("clarify_target", decision["context"]["errors"][0])

    def test_routable_finding_without_severity_bounces_the_reviewer(self):
        # severity feeds the next review-plan's prior-critical trigger; a
        # record that omits it on an autofix/blocked finding must not gate.
        finding = {"tag": "blocked", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="blocked", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertIn("no severity", decision["context"]["errors"][0])

    def test_findings_split_by_artifact_owner(self):
        findings = [
            {"tag": "clarify", "location": "src/widget:1", "description": "code",
             "clarify_target": "system-design-expert"},
            {"tag": "blocked", "location": "docs/prd.md:9", "description": "prd",
             "severity": "critical"},
            {"tag": "clarify", "location": "docs/adr/x.md:3", "description": "adr",
             "clarify_target": "system-design-expert"},
            {"tag": "autofix", "location": "docs/system-design.md:7", "description": "typo", "fix": "x",
             "severity": "fixable"},
        ]
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=findings),
        )
        decision = self.route()
        self.assertEqual(
            decision["next"],
            ["feature-implementer", "product-requirements-expert", "system-design-expert"],
        )
        self.assertEqual(decision["context"]["root_autofix"], 1)

    def test_autofix_only_round_escalates(self):
        finding = {"tag": "autofix", "location": "docs/system-design.md:7", "description": "typo", "fix": "x",
                   "severity": "fixable"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "autofix-only-round")

    def test_escalate_finding_on_changes_requested_flags_halt(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["escalate_findings"], 1)
        self.assertTrue(decision["context"]["halt_after"])

    def test_escalate_round_halts_before_rereview(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "escalate-finding-halt")

    def test_stale_feedback_after_silent_start_retries(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR],
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-stall-retry")

    def test_stale_feedback_after_two_silent_starts_stalls(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR],
            rec("dispatch-start", author="doc-reviewer"),
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "reviewer-stalled")

    def test_non_approved_empty_findings_redispatches_reviewer(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[]),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-empty-findings")

    def test_missing_feedback_after_one_start_retries_once(self):
        self.write_log(
            rec("build-pass"),
            *[rec("dispatch-start", author=r) for r in FLOOR],
            *[self.approved(r) for r in FLOOR[:3]],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-stall-retry")

    def test_two_silent_starts_blocks_as_stalled(self):
        self.write_log(
            rec("build-pass"),
            *[rec("dispatch-start", author=r) for r in FLOOR],
            *[self.approved(r) for r in FLOOR[:3]],
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "reviewer-stalled")
        self.assertEqual(decision["context"]["stalled"], ["doc-reviewer"])

    def test_escalate_finding_on_approved_blocks(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[finding]),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "escalate-on-approved")

    def test_second_round_resets_on_new_build_pass(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec("review-feedback", author="doc-reviewer", verdict="changes_requested", findings=[finding]),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")


class TestRouteReviewPlan(RouteCase):
    """Risk-proportional review: the active review-plan names the pass's roster;
    a gray plan dispatches the planner; absent/invalid plans fail closed to the
    full battery."""

    def _plan(self, **fields):
        base = {"author": "review-plan-engine", "scope": "full-diff",
                "basis": {"tree_sha": "t1", "pass": "first"}, "rationale": "x"}
        base.update(fields)
        return rec("review-plan", **base)

    def test_low_plan_dispatches_only_its_roster(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], ["doc-reviewer"])

    def test_no_plan_fails_closed_to_full_battery(self):
        self.write_log(rec("build-pass", author="feature-implementer"))
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], FLOOR)

    def test_gray_plan_dispatches_planner(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "plan-gray")
        self.assertEqual(decision["next"], ["review-planner"])

    def test_gray_from_planner_bounces(self):
        # Only the engine may defer; a planner record with risk gray is invalid.
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["rule"], "plan-gray-invalid")
        self.assertEqual(decision["next"], ["review-planner"])

    def test_planner_stall_retry_then_block(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "planner-stall-retry")
        self.assertEqual(decision["next"], ["review-planner"])
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
            rec("dispatch-start", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "planner-stalled")

    def test_planner_resolution_dispatches_its_roster(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
            self._plan(risk="low", author="review-planner",
                       roster=["code-quality-reviewer", "test-reviewer", "security-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"],
                         ["code-quality-reviewer", "test-reviewer", "security-reviewer"])

    def test_plan_roster_completion_grades(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "grade")
        self.assertEqual(decision["next"], ["change-grader"])

    def test_invalid_plan_roster_fails_closed(self):
        # A plan naming a non-roster reviewer cannot gate; full battery instead.
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["ghost-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], FLOOR)

    def test_plan_dropping_a_prior_dissenter_reruns_it(self):
        # Completion invariant: a fix plan that drops a reviewer still holding a
        # non-approved verdict must not grade — route re-dispatches the dissenter.
        finding = {"tag": "blocked", "location": "x:1", "description": "y",
                   "severity": "critical"}
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="code-quality-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="test-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="security-reviewer",
                verdict="changes_requested", findings=[finding]),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),  # drops the dissenter
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "outstanding-dissent")
        self.assertEqual(decision["next"], ["security-reviewer"])

    def test_outstanding_dissenter_stalls_after_two_redispatches(self):
        # The outstanding-dissent re-dispatch has its own stall ceiling: a
        # dropped dissenter re-dispatched twice with no fresh feedback blocks,
        # rather than looping the router forever.
        finding = {"tag": "blocked", "location": "x:1", "description": "y",
                   "severity": "critical"}
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="code-quality-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="test-reviewer", verdict="approved", findings=[]),
            rec("review-feedback", author="security-reviewer",
                verdict="changes_requested", findings=[finding]),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),  # drops the dissenter
            rec("review-feedback", author="doc-reviewer", verdict="approved", findings=[]),
            # Two re-dispatches of the outstanding dissenter, no fresh feedback.
            rec("dispatch-start", author="security-reviewer"),
            rec("dispatch-start", author="security-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviewer-stalled")
        self.assertEqual(decision["context"]["stalled"], ["security-reviewer"])


class TestRouteRecovery(RouteCase):
    def test_retry_below_three_redispatches_implementer(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", author="feature-implementer", retry=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "build-retry")
        self.assertEqual(decision["context"]["retry"], 1)

    def test_three_failures_retriage_designer(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("build-failure", retry=i) for i in (1, 2, 3)],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "build-non-convergence")

    def test_superseding_design_block_resets_retry_counter(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("build-failure", retry=i) for i in (1, 2, 3)],
            rec("design-block", verdict="minor", supersedes_record_at=1),
            rec("build-failure", retry=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["context"]["retry"], 1)

    def test_abort_reasons_route_deterministically(self):
        cases = (
            ("wrong-shape-slice", "dispatch", ["product-requirements-expert"]),
            ("design-mismatch", "dispatch", ["system-design-expert"]),
            ("prerequisite-missing", "blocked", None),
        )
        for reason, expected_decision, expected_next in cases:
            with self.subTest(abort_reason=reason):
                self.write_log(
                    rec("design-block", verdict="covered"),
                    rec("build-failure", retry=1, abort_reason=reason),
                )
                decision = self.route()
                self.assertEqual(decision["decision"], expected_decision)
                if expected_next:
                    self.assertEqual(decision["next"], expected_next)

    def test_truncation_continues_same_slice(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_truncation_survives_a_trailing_root_record(self):
        # The table trigger is "no subsequent SUBSTANTIVE record", not
        # "dispatch-start is the last record": a root design-doc-autofix note
        # appended after the truncated dispatch must not mask it.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_grader_verdict_completes_its_own_dispatch_start(self):
        # A grader-verdict after the grader's dispatch-start is a completed
        # dispatch — a trailing root record must not turn it into a
        # truncation-undefined escalate.
        records = [rec("build-pass")]
        records += [rec("review-feedback", author=r, verdict="approved", findings=[]) for r in FLOOR]
        records += [
            rec("dispatch-start", author="change-grader"),
            rec("grader-verdict", author="change-grader", verdict="clear"),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        ]
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")

    def test_three_consecutive_truncations_retriage(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("dispatch-start", author="feature-implementer") for _ in range(3)],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "truncation-non-convergence")

    def test_implementer_record_resets_truncation_run(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
            rec("dispatch-start", author="feature-implementer"),
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("consultation-response", author="system-design-expert", in_response_to=4),
            rec("dispatch-start", author="feature-implementer"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_designer_truncation_escalates(self):
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "truncation-undefined")


class TestRouteConsultation(RouteCase):
    def test_request_dispatches_target(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-dispatch")
        self.assertEqual(decision["context"]["requester"], "feature-implementer")

    def test_response_returns_to_requester(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("consultation-response", author="system-design-expert", in_response_to=2),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "consultation-return")
        self.assertTrue(decision["context"]["resume"])

    def test_human_request_blocks_for_conversation(self):
        # A fresh-dispatch pushback: PRE asked the human before any
        # substantive record exists. Route halts for the conversation.
        self.write_log(
            rec("dispatch-start", author="product-requirements-expert"),
            rec("consultation-request", author="product-requirements-expert",
                target="human", question="Is REQ-XX-001's scope one behavior?"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")
        self.assertEqual(decision["context"]["requester"], "product-requirements-expert")
        self.assertEqual(decision["context"]["question"],
                         "Is REQ-XX-001's scope one behavior?")

    def test_human_request_gate_failure_bounces_author(self):
        # The gate runs before the human branch: a malformed human request
        # bounces to its author, never blocks with a null question.
        strict = {"type": "object", "required": ["type", "question"]}
        (self.schemas / "consultation-request.schema.json").write_text(json.dumps(strict))
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="product-requirements-expert", target="human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["product-requirements-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_target_variant_bounces_author(self):
        # "Human"/" human" must not silently become an agent dispatch.
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="system-design-expert", target="Human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_request_fails_closed(self):
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target="human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_variant_request_fails_closed(self):
        # The author guard precedes the exact-match bounce: a variant target
        # authored by "human" must block, never bounce to a "human" agent.
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target=" human "),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_request_response_fails_closed(self):
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target="human"),
            rec("consultation-response", author="human", in_response_to=2),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_stale_human_request_does_not_refire(self):
        # Root re-dispatched after the conversation without appending the
        # response; the newer substantive record wins.
        self.write_log(
            rec("dispatch-start", author="product-requirements-expert"),
            rec("consultation-request", author="product-requirements-expert", target="human"),
            rec("prd-entry"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])

    def test_human_request_shields_truncation_detection(self):
        # The elicitation pause: a dispatch-start followed only by a
        # consultation-request targeting the human is a designed halt,
        # never truncation-undefined.
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
            rec("consultation-request", author="system-design-expert", target="human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")

    def test_human_response_returns_to_requester(self):
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
            rec("consultation-request", author="system-design-expert", target="human"),
            rec("consultation-response", author="human", in_response_to=3),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-return")

    def test_response_from_wrong_author_bounces_the_responder(self):
        # A failed gate is a dispatch of the upstream agent (SKILL Routing
        # Rules): the request names the legitimate responder, so re-dispatch
        # it instead of halting.
        self.write_log(
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("consultation-response", author="doc-reviewer", in_response_to=1),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")
        self.assertTrue(decision["context"]["errors"])

    def test_response_with_dangling_pointer_blocks(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("consultation-response", author="system-design-expert", in_response_to=9),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_pending_request_survives_trailing_root_record(self):
        # Root's design-doc-autofix append must not orphan a live consultation.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-dispatch")

    def test_stale_response_validation_applies_off_last_position(self):
        # A wrong-author response trailed by a root record must still fail its
        # gate — the latest-substantive path validates like the last-record
        # path — and bounce the legitimate responder.
        self.write_log(
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("consultation-response", author="doc-reviewer", in_response_to=1),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_response_failing_its_schema_gate_bounces_the_responder(self):
        strict = {"type": "object", "required": ["type", "answer"]}
        (self.schemas / "consultation-response.schema.json").write_text(json.dumps(strict))
        self.write_log(
            rec("consultation-request", author="feature-implementer", target="system-design-expert"),
            rec("consultation-response", author="system-design-expert", in_response_to=1),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")


# --- view --------------------------------------------------------------------
# Characterization of the human-facing renderer: append-position ordering
# (never ts), round grouping by reviewer reappearance, graceful degradation
# on partial/dirty logs, and a byte-stable plain snapshot.

VIEW_SNAPSHOT = """\
╭──────────────────────────────────────────────────────────────────╮
│ REQ-DEMO-001  Rate-limit the API                                 │
│ 3 review rounds · 2 build-passes · 1 build-failure · grade CLEAR │
╰──────────────────────────────────────────────────────────────────╯

              R1     R2     R3
code-quality  ✎ (2)  ✎ (1)  ✔
test          ·      ·      ·
security      ✔ (1)  ·      ·
doc           ·      ·      ·

◇ prd-entry  Rate-limit the API  (prd-expert)
◈ design-block  minor  (design)
◆ implement  (implementer)  ◷ 15m
  ├ ↳ consult  → design  Per-tenant or per-endpoint?
  ├ ↲ consult  ← design  Per-tenant.
  ├ ▲ build  ✗ unit-test failed  retry 1
  └ ▲ build  ✓ clean   fmt · test
✎ review  code-quality  changes_requested  (2 findings)
  ├ [blocked] limiter.py:42  The bucket refill races with allow(); two workers can both observe a singl…
  └ [autofix] limiter.py:12  The Limiter type lacks a doc comment.
✔ review  security  approved  (1 finding)
  └ [clarify] prd.md:9  Is the burst size a hard product number?
✎ review  code-quality  changes_requested  (1 finding)
  └ [escalate] limiter.py:88  Persisting bucket state was not in the PRD; scope call for a human.
✚ doc-autofix  docs/system-design.md  stale-reference  (claude)
↻ implement  (implementer)  ← code-quality  (1 finding)  ◷ 4m
  └ ▲ build  ✓ clean   fmt · test
✔ review  code-quality  approved
◆ grade  CLEAR  Small, well-tested limiter.
  · blast_radius     clear    one package
  · scope_deviation  concern  persistence escalated
• mystery-record  (someone-new)
"""


def vrec(rtype, author, ts, **fields):
    record = {"type": rtype, "req_id": REQ, "ts": ts, "author": author}
    record.update(fields)
    return record


def view_fixture():
    """Every record type in append order, across two implement sessions and
    three review rounds. Session 1 (a fresh ◆ implement) owns a mid-work
    consult, a build retry, and its clean build; session 2 (a ↻ implement fix
    answering code-quality) owns its rebuild. The design-block ts is one hour
    BEFORE the prd-entry's, so any ts sort would scramble the append order."""
    return [
        vrec("prd-entry", "product-requirements-expert", "2026-07-06T10:00:00Z",
             title="Rate-limit the API"),                                    # L1
        vrec("design-block", "system-design-expert", "2026-07-06T09:00:00Z",
             verdict="minor"),                                               # L2
        vrec("dispatch-start", "feature-implementer", "2026-07-06T10:15:00Z",
             responding_to=[2]),                                             # L3 opener
        vrec("consultation-request", "feature-implementer", "2026-07-06T10:16:00Z",
             target="system-design-expert", context="granularity",
             question="Per-tenant or per-endpoint?"),                        # L4
        vrec("consultation-response", "system-design-expert", "2026-07-06T10:18:00Z",
             in_response_to=4, answer="Per-tenant."),                        # L5
        vrec("build-failure", "feature-implementer", "2026-07-06T10:20:00Z",
             retry=1, failed_check="unit-test"),                             # L6
        vrec("build-pass", "feature-implementer", "2026-07-06T10:30:00Z",
             gate_checks_run=["fmt", "test"]),                              # L7 closes S1
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T10:40:00Z",
             verdict="changes_requested", findings=[
                 {"tag": "blocked", "location": "src/ingest/limiter.py:42 (allow)",
                  "description": "The bucket refill races with allow(); two workers can"
                                 " both observe a single remaining token and pass.",
                  "fix": "Hold the lock across the refill and the take."},
                 {"tag": "autofix", "location": "src/ingest/limiter.py:12",
                  "description": "The Limiter type lacks a doc comment.",
                  "fix": "Add the standard comment."}]),                     # L8
        vrec("review-feedback", "security-reviewer", "2026-07-06T10:41:00Z",
             verdict="approved", findings=[
                 {"tag": "clarify", "location": "docs/prd.md:9",
                  "description": "Is the burst size a hard product number?",
                  "clarify_target": "product-requirements-expert"}]),        # L9
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T11:00:00Z",
             verdict="changes_requested", findings=[
                 {"tag": "escalate", "location": "src/ingest/limiter.py:88",
                  "description": "Persisting bucket state was not in the PRD;"
                                 " scope call for a human."}]),              # L10
        vrec("design-doc-autofix", "claude", "2026-07-06T11:05:00Z",
             file="docs/system-design.md", category="stale-reference", source_finding="x",
             old_content="a", new_content="b", lines_changed=1, chars_changed=2),  # L11
        vrec("dispatch-start", "feature-implementer", "2026-07-06T11:05:30Z",
             responding_to=[10]),                                            # L12 fix opener
        vrec("build-pass", "feature-implementer", "2026-07-06T11:10:00Z",
             gate_checks_run=["fmt", "test"]),                             # L13 closes S2
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T11:20:00Z",
             verdict="approved", findings=[]),                              # L14
        vrec("grader-features", "change-grader", "2026-07-06T11:30:00Z", features={"loc": 12}),
        vrec("grader-verdict", "change-grader", "2026-07-06T11:31:00Z", verdict="clear",
             summary="Small, well-tested limiter.", rationale="r", facets={
                 "blast_radius": {"verdict": "clear", "note": "one package"},
                 "scope_deviation": {"verdict": "concern", "note": "persistence escalated"}}),
        vrec("mystery-record", "someone-new", "2026-07-06T11:40:00Z"),
    ]


def timed_fixture():
    """A dispatch-start before each of prd, design, implement, and review, so
    every timeable step carries a duration — the gate the cost tail rides. The
    grade stays untimed by contract (the change-grader is dispatch-exempt; the
    dispatch-start schema rejects it as author). Shared by the duration tests
    (TestView) and the cost-overlay tests (TestBoardCost) so both assert
    against one timeline."""
    return [
        vrec("dispatch-start", "product-requirements-expert",
             "2026-07-06T10:00:00Z", responding_to=[0]),            # L1
        vrec("prd-entry", "product-requirements-expert",
             "2026-07-06T10:03:00Z", title="t"),                     # L2 → 3m
        vrec("dispatch-start", "system-design-expert",
             "2026-07-06T10:03:00Z", responding_to=[2]),            # L3
        vrec("design-block", "system-design-expert",
             "2026-07-06T10:05:00Z", verdict="covered"),            # L4 → 2m
        vrec("dispatch-start", "feature-implementer",
             "2026-07-06T10:05:00Z", responding_to=[4]),            # L5
        vrec("build-pass", "feature-implementer",
             "2026-07-06T10:20:00Z", gate_checks_run=["test"]),      # L6 → 15m
        vrec("dispatch-start", "code-quality-reviewer",
             "2026-07-06T10:20:00Z", responding_to=[6]),            # L7
        vrec("review-feedback", "code-quality-reviewer",
             "2026-07-06T10:22:00Z", verdict="approved", findings=[]),  # L8 → 2m
        vrec("grader-verdict", "change-grader", "2026-07-06T10:26:00Z",
             verdict="clear", summary="done"),                       # L9, untimed
    ]


class TestView(HandoffCase):
    def setUp(self):
        super().setUp()
        # Hermetic cost overlay: point the transcript index at an empty tree so
        # the board's per-step cost never depends on the host's real Claude
        # Code history. TestBoardCost supplies its own synthetic transcripts.
        patcher = unittest.mock.patch.dict(
            os.environ,
            {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "no-projects")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def view(self, *extra):
        # --layout points at a nonexistent file so a real scripts/layout.toml
        # in the invoking project cannot leak extra reviewers into the matrix.
        return self.run_cli(
            "view", "--file", str(self.log), "--no-color",
            "--layout", str(self.log.parent / "layout.toml"), *extra,
        )

    def test_missing_log_renders_a_message(self):
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertIn("no handoff log", out)

    def test_empty_log_renders_without_error(self):
        self.log.write_text("")
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("handoff log is empty", out)

    def test_plain_output_is_byte_stable(self):
        self.write_log(*view_fixture())
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertEqual(out, VIEW_SNAPSHOT)

    def test_orders_by_append_position_not_ts(self):
        # The design-block carries the earliest ts in the fixture yet must
        # render after the prd-entry: file position is the only clock.
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertLess(out.index("◇ prd-entry"), out.index("◈ design-block"))

    def test_rounds_group_by_reviewer_reappearance(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertIn("R1     R2     R3", out)
        self.assertIn("code-quality  ✎ (2)  ✎ (1)  ✔", out)
        self.assertIn("security      ✔ (1)  ·      ·", out)

    def test_dispatch_start_and_grader_features_are_filtered(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertNotIn("dispatch-start", out)
        self.assertNotIn("grader-features", out)

    def test_implementer_fix_opens_a_session_sibling_doc_fix_stays_flat(self):
        # In a fix round the coordinator dispatches the implementer AND a
        # doc-owner concurrently, so the doc-owner's dispatch interleaves INTO
        # the implementer's session window (between its opener and its build).
        # It is a SIBLING, not session plumbing: it must hoist to a flat ↻ fix
        # line, not be absorbed. The implementer's fix opens the session; the
        # reviewer fan-out dispatch stays suppressed.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:05:00Z", responding_to=[1]),            # L2 S1 opener
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:10:00Z", gate_checks_run=["test"]),      # L3 closes S1
            vrec("review-feedback", "code-quality-reviewer",
                 "2026-07-06T10:20:00Z", verdict="changes_requested",
                 findings=[{"tag": "blocked", "location": "limiter.py:42",
                            "description": "race"}]),                    # L4
            vrec("review-feedback", "doc-reviewer",
                 "2026-07-06T10:21:00Z", verdict="changes_requested",
                 findings=[{"tag": "autofix", "location": "prd.md:9",
                            "description": "stale"}]),                   # L5
            vrec("dispatch-start", "security-reviewer",
                 "2026-07-06T10:30:00Z", responding_to=[3]),            # L6 noise
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:31:00Z", responding_to=[4]),            # L7 S2 fix opener
            vrec("dispatch-start", "product-requirements-expert",
                 "2026-07-06T10:32:00Z", responding_to=[5]),            # L8 sibling doc fix
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:40:00Z", gate_checks_run=["test"]),      # L9 closes S2
        )
        _, out, _ = self.view()
        self.assertIn("↻ implement  (implementer)  ← code-quality", out)
        # The interleaved sibling survives, hoisted flat after the session. Its
        # dimension is never re-approved here, so it carries no duration — the
        # line ends at the finding count.
        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)
        self.assertGreater(out.index("↻ fix  prd-expert"),
                           out.index("↻ implement  (implementer)  ← code-quality"))
        self.assertEqual(out.count("↻ fix"), 1)          # only the doc-owner
        self.assertEqual(out.count("◆ implement"), 1)     # only the fresh S1
        self.assertNotIn("↻ fix  security", out)          # reviewer dispatch suppressed

    def test_fresh_implement_opens_a_session_with_its_clean_build(self):
        # A fresh implementer dispatch opens a ◆ implement session; its
        # build-pass renders as the closing └ ▲ build ✓ clean child — the build
        # names no author, so the parent is where the implementer surfaces.
        self.write_log(
            vrec("prd-entry", "product-requirements-expert",
                 "2026-07-06T10:00:00Z", title="t"),                     # L1
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:05:00Z", verdict="covered"),            # L2
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z", responding_to=[2]),            # opener
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:10:00Z", gate_checks_run=["test"]),      # L4
        )
        _, out, _ = self.view()
        # The parent carries the session elapsed (10:06 → 10:10 = 4m), not a
        # start time; the build child carries no timestamp.
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertEqual(out.count("◆ implement"), 1)
        # The clean build is the session's closing child, below its opener.
        self.assertGreater(out.index("└ ▲ build"), out.index("◆ implement"))
        self.assertGreater(out.index("◆ implement"), out.index("design-block"))

    def test_retry_nests_under_one_implement_session(self):
        # A build retry re-dispatches the implementer, but that interior
        # dispatch is absorbed: the session shows ONE ◆ implement opener with
        # the failed build as a ├ child and the clean build as the └ child.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:05:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z", responding_to=[1]),            # opener
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:08:00Z", retry=1, failed_check="test"),  # L3
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:09:00Z", responding_to=[3]),            # retry (absorbed)
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:10:00Z", gate_checks_run=["test"]),      # L5
        )
        _, out, _ = self.view()
        self.assertEqual(out.count("◆ implement"), 1)
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)  # 10:06 → 10:10
        self.assertIn("  ├ ▲ build  ✗ test failed  retry 1", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)

    def test_abort_closed_session_carries_duration_and_stops_absorption(self):
        # An aborting build-failure closes the session like a clean build: the
        # parent carries the opener → abort elapsed (and the cost when a lookup
        # attributes), and nothing after the abort is absorbed — the
        # implementer's own trailing consult renders flat, not as a child.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z", responding_to=[1]),            # opener
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:11:00Z", abort_reason="design-mismatch"),  # closes
            vrec("consultation-request", "feature-implementer",
                 "2026-07-06T10:12:00Z", target="system-design-expert",
                 context="c", question="Re-triage?"),                    # after close
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)  ◷ 5m", out)
        self.assertIn("  └ ▲ build  ✗ aborted: design-mismatch", out)
        self.assertIn("↳ consult  implementer → design", out)   # flat
        self.assertNotIn("└ ↳ consult", out)
        cost = " │ Σ ▲7.5M ▼17k $4.66 │ ⛁ 99% $89%"
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view(
            entries, errors, REQ, list(handoff.ROSTER_FLOOR), color=False,
            verbose=False, cost_lookup=lambda at, s, e: [(cost, handoff.DIM)])
        self.assertIn("◆ implement  (implementer)  ◷ 5m" + cost,
                      "\n".join(lines))

    def test_retry_only_session_stays_bare(self):
        # A plain retry failure does not close the session; with no closer in
        # the log (truncated/still running) the parent keeps the omission —
        # timing it would guess at an unfinished span.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z", responding_to=[1]),            # opener
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:11:00Z", retry=1, failed_check="test"),  # child
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)\n", out)
        self.assertNotIn("(implementer)  ◷", out)

    def test_record_producing_steps_show_dispatch_to_output_duration(self):
        # Every step that emits a record is timed from its author's
        # dispatch-start to that record: prd-entry, design-block, the implement
        # session, and each review. The grade stays untimed by contract.
        self.write_log(*timed_fixture())
        _, out, _ = self.view()
        self.assertIn("(prd-expert)  ◷ 3m", out)
        self.assertIn("(design)  ◷ 2m", out)
        self.assertIn("◆ implement  (implementer)  ◷ 15m", out)
        self.assertIn("review  code-quality  approved  ◷ 2m", out)
        # The grade is untimed by contract — no dispatch can name its author.
        self.assertIn("◆ grade  CLEAR  done", out)
        self.assertNotIn("done  ◷", out)

    def test_producer_dispatch_does_not_pair_across_slices(self):
        # A step's start is a dispatch in its OWN slice. A code-quality review
        # in slice B whose only same-author dispatch lives in slice A must show
        # no duration, not borrow slice A's dispatch for an inflated span.
        self.write_log(
            vrec("dispatch-start", "code-quality-reviewer",
                 "2026-07-06T09:00:00Z", req_id="REQ-A", responding_to=[0]),
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T09:05:00Z", req_id="REQ-A", gate_checks_run=["test"]),
            vrec("review-feedback", "code-quality-reviewer",
                 "2026-07-06T10:00:00Z", req_id="REQ-B", verdict="approved",
                 findings=[]),
        )
        _, out, _ = self.view()
        self.assertNotIn("code-quality  approved  ◷", out)

    def test_doc_fix_carries_no_duration(self):
        # A doc-owner fix emits no record, so it has no dispatch → output span
        # like the timed steps; ◷ means work time everywhere, so the fix line
        # stays bare even when its dimension is later re-approved.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:00:00Z", responding_to=[1]),            # L2
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:05:00Z", gate_checks_run=["test"]),      # L3
            vrec("review-feedback", "doc-reviewer",
                 "2026-07-06T10:10:00Z", verdict="changes_requested",
                 findings=[{"tag": "autofix", "location": "prd.md:9",
                            "description": "stale"}]),                   # L4 findings
            vrec("dispatch-start", "product-requirements-expert",
                 "2026-07-06T10:11:00Z", responding_to=[4]),            # L5 doc fix
            vrec("review-feedback", "doc-reviewer",
                 "2026-07-06T10:25:00Z", verdict="approved", findings=[]),  # L6
        )
        _, out, _ = self.view()
        # No ◷ on the fix line — it ends at the finding count.
        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)
        self.assertNotIn("← doc  (1 finding)  ◷", out)

    def test_sibling_consult_stays_flat_with_its_author(self):
        # A sibling doc-owner's mid-window consult is not the implementer's:
        # it hoists out of the session as a flat line naming its author. A
        # `├ ↳` child would misattribute the question to the implementer.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("review-feedback", "doc-reviewer",
                 "2026-07-06T10:20:00Z", verdict="changes_requested",
                 findings=[{"tag": "autofix", "location": "prd.md:9",
                            "description": "stale"}]),                   # L2
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:31:00Z", responding_to=[2]),            # opener
            vrec("dispatch-start", "product-requirements-expert",
                 "2026-07-06T10:32:00Z", responding_to=[2]),            # sibling fix
            vrec("consultation-request", "product-requirements-expert",
                 "2026-07-06T10:33:00Z", target="system-design-expert",
                 context="c", question="Fixed burst size?"),             # sibling consult
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:40:00Z", gate_checks_run=["test"]),      # closes session
        )
        _, out, _ = self.view()
        self.assertIn("↳ consult  prd-expert → design", out)   # flat, real author
        self.assertNotIn("├ ↳ consult", out)                    # not a session child
        self.assertIn("↻ fix  prd-expert  ← doc", out)          # sibling fix survives

    def test_doc_autofix_inside_session_hoists_instead_of_truncating(self):
        # A root-applied design-doc-autofix interleaving between the opener
        # and the clean build is a sibling, not a session ender: the session
        # keeps its duration and its └ ✓ clean child, and the autofix renders
        # flat after it.
        self.write_log(
            vrec("design-block", "system-design-expert",
                 "2026-07-06T10:00:00Z", verdict="covered"),            # L1
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z", responding_to=[1]),            # opener
            vrec("design-doc-autofix", "claude", "2026-07-06T10:08:00Z",
                 file="docs/system-design.md", category="stale-reference",
                 source_finding="x", old_content="a", new_content="b",
                 lines_changed=1, chars_changed=2),                      # interleaved
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:10:00Z", gate_checks_run=["test"]),      # L4
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertIn("✚ doc-autofix", out)                # hoisted, still visible
        self.assertNotIn("── ▲ build-pass", out)           # no flat fallback

    def test_re_engaged_review_carries_no_duration(self):
        # A reviewer re-engaged for round 2 (a SendMessage continue) appends
        # no fresh dispatch-start. Pairing review#2 with the round-1 dispatch
        # would span the implementer's rework and re-sum round-1 spend, so
        # the dispatch times only the first record of a type: review#2 shows
        # no ◷ rather than a wrong one.
        self.write_log(
            vrec("dispatch-start", "code-quality-reviewer",
                 "2026-07-06T10:00:00Z", responding_to=[0]),            # L1
            vrec("review-feedback", "code-quality-reviewer",
                 "2026-07-06T10:05:00Z", verdict="changes_requested",
                 findings=[{"tag": "blocked", "location": "a.py:1",
                            "description": "x"}]),                       # L2 → 5m
            vrec("review-feedback", "code-quality-reviewer",
                 "2026-07-06T10:35:00Z", verdict="approved", findings=[]),  # L3 re-engaged
        )
        _, out, _ = self.view()
        self.assertIn("changes_requested  (1 finding)  ◷ 5m", out)
        self.assertNotIn("approved  ◷", out)

    def test_consecutive_identical_gates_are_distinguished_by_time(self):
        # Two build-passes with the same checks (e.g. one per findings-owner
        # dispatch) must not render as an inexplicable doubled line.
        self.write_log(
            rec("prd-entry", title="t"),
            rec("build-pass", ts="2026-07-06T13:32:00Z", gate_checks_run=["test"]),
            rec("build-pass", ts="2026-07-06T14:10:00Z", gate_checks_run=["test"]),
        )
        _, out, _ = self.view()
        self.assertIn("▲ build-pass 13:32", out)
        self.assertIn("▲ build-pass 14:10", out)

    def test_no_grader_verdict_renders_no_grade_yet_by_default(self):
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.view()
        self.assertIn("no grade yet", out)

    def test_auto_grade_false_renders_grading_disabled(self):
        # With grading off no grade is coming; "yet" would read as pending.
        (self.log.parent / "layout.toml").write_text(
            '[harness]\nauto_grade = false\n')
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.view()
        self.assertIn("grading disabled", out)
        self.assertNotIn("no grade yet", out)

    def test_color_flag_forces_ansi_through_a_pipe(self):
        # An agent's shell tool pipes stdout (no TTY); --color must still
        # emit ANSI so the conversation terminal can render the styling.
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        code, out, err = self.run_cli(
            "view", "--file", str(self.log), "--color",
            "--layout", str(self.log.parent / "layout.toml"),
        )
        self.assertEqual(code, 0, err)
        self.assertIn("\x1b[", out)

    def test_color_flag_beats_no_color_env(self):
        # NO_COLOR suppresses auto-detection; an explicit --color is the
        # user requesting color and wins (per the NO_COLOR spec).
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        old = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            code, out, err = self.run_cli(
                "view", "--file", str(self.log), "--color",
                "--layout", str(self.log.parent / "layout.toml"),
            )
        finally:
            if old is None:
                del os.environ["NO_COLOR"]
            else:
                os.environ["NO_COLOR"] = old
        self.assertEqual(code, 0, err)
        self.assertIn("\x1b[", out)

    def test_color_and_no_color_are_mutually_exclusive(self):
        self.write_log(rec("prd-entry", title="t"))
        code, _, err = self.run_cli(
            "view", "--file", str(self.log), "--color", "--no-color",
        )
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", err)

    def test_verbose_prints_full_description_then_fix(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view("--verbose")
        self.assertLess(
            out.index("observe a single remaining token and pass."),
            out.index("fix: Hold the lock across the refill and the take."),
        )

    def test_no_req_id_renders_every_slice_oldest_first(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec("prd-entry", req_id="REQ-B-002", title="Refactor sibling",
                author="system-design-expert"),
        )
        _, out, _ = self.view()
        # Both slices render as their own board, in append order — the older
        # REQ-A-001 first — and no "also in log" pointer survives.
        self.assertLess(out.index("REQ-A-001"), out.index("REQ-B-002"))
        self.assertIn("Original", out)
        self.assertIn("Refactor sibling", out)
        self.assertNotIn("also in log", out)

    def test_no_req_id_gives_each_slice_its_own_header_box(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec("prd-entry", req_id="REQ-B-002", title="Refactor sibling",
                author="system-design-expert"),
        )
        _, out, _ = self.view()
        self.assertEqual(out.count("╭"), 2)

    def test_req_id_flag_selects_a_slice(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec("prd-entry", req_id="REQ-B-002", title="Refactor sibling",
                author="system-design-expert"),
        )
        _, out, _ = self.view("--req-id", "REQ-A-001")
        self.assertIn("Original", out)
        self.assertNotIn("Refactor sibling", out)

    def test_unknown_req_id_exits_three(self):
        self.write_log(rec("prd-entry", title="T"))
        code, out, _ = self.view("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)
        self.assertIn("in log: REQ-A-001", out)

    def test_req_id_against_empty_log_exits_three(self):
        self.log.write_text("")
        code, out, _ = self.view("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)

    def test_extra_reviewer_from_layout_gets_a_lane(self):
        # The extra reviewer files no review: only the roster wiring can put
        # its idle lane in the matrix, so this cannot pass vacuously.
        (self.log.parent / "layout.toml").write_text(
            '[harness]\nextra_reviewers = ["perf-reviewer"]\n'
        )
        self.write_log(
            rec("review-feedback", author="code-quality-reviewer",
                verdict="approved", findings=[]),
        )
        _, out, _ = self.view()
        perf_lane = [l for l in out.splitlines() if l.startswith("perf")]
        self.assertEqual(len(perf_lane), 1, out)
        self.assertIn("·", perf_lane[0])
        self.assertNotIn("✔", perf_lane[0])

    def test_malformed_layout_falls_back_to_the_floor(self):
        (self.log.parent / "layout.toml").write_text('[harness]\nextra_reviewers = "oops"\n')
        self.write_log(rec("review-feedback", verdict="approved", findings=[]))
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("code-quality", out)

    def test_missing_fields_and_unknown_types_render(self):
        self.write_log(
            rec("review-feedback", author="code-quality-reviewer",
                verdict="changes_requested", findings=["not-a-dict", {"location": 7}]),
            # Unhashable verdicts must fall through the glyph lookup, not raise.
            rec("review-feedback", author="test-reviewer",
                verdict=["approved"], findings=[]),
            rec("review-feedback", author="doc-reviewer",
                verdict={"v": "approved"}, findings=[]),
            rec("grader-verdict", author="change-grader",
                facets={"blast_radius": "not-a-dict"}),
            {"type": "prd-entry", "req_id": "REQ-A-001", "ts": TS},
            {"type": None, "req_id": "REQ-A-001"},
        )
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertIn("(untitled)", out)
        self.assertIn("blast_radius", out)
        self.assertEqual(out.count("review  "), 3)

    def test_dirty_log_renders_parsed_records_with_a_footer(self):
        self.log.write_text(
            json.dumps(rec("prd-entry", title="T")) + "\nnot json\n"
        )
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("prd-entry", out)
        self.assertIn("problem line", out)
        self.assertIn("line 2", out)

    def test_remaining_renderer_branches(self):
        self.write_log(
            rec("design-block", author="system-design-expert", verdict="minor",
                supersedes_record_at=1),
            rec("build-failure", author="feature-implementer",
                abort_reason="design-mismatch"),
            rec("consultation-response", author="system-design-expert",
                in_response_to=99, answer="a"),
            rec("review-feedback", author="doc-reviewer", verdict="blocked",
                findings=[{"tag": "blocked", "location": "x", "description": "d",
                           "severity": "critical"}]),
        )
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("supersedes L1", out)
        self.assertIn("abort: design-mismatch", out)
        self.assertIn("design → ?", out)  # dangling in_response_to
        self.assertIn("✖", out)

    def test_records_without_req_id_render_unfiltered(self):
        self.write_log({"type": "prd-entry", "ts": TS, "author": "tester", "title": "T"})
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("(no req_id)", out)
        self.assertIn("T", out)

    def test_color_follows_tty_and_no_color_env(self):
        self.write_log(rec("prd-entry", title="T"))

        class Tty(io.StringIO):
            def isatty(self):
                return True

        argv = ["view", "--file", str(self.log),
                "--layout", str(self.log.parent / "layout.toml")]
        saved = os.environ.pop("NO_COLOR", None)
        try:
            out = Tty()
            with contextlib.redirect_stdout(out):
                handoff.main(argv)
            self.assertIn("\x1b[", out.getvalue())
            os.environ["NO_COLOR"] = "1"
            out = Tty()
            with contextlib.redirect_stdout(out):
                handoff.main(argv)
            self.assertNotIn("\x1b[", out.getvalue())
        finally:
            os.environ.pop("NO_COLOR", None)
            if saved is not None:
                os.environ["NO_COLOR"] = saved

    def test_log_content_cannot_inject_terminal_escapes(self):
        # The log is agent-authored: a record embedding raw escape bytes
        # (window title, hidden text) must never reach the terminal.
        hostile = "Innocent\x1b]0;pwned\x07\x1b[8m hidden\x00\ttail"
        self.write_log(
            rec("prd-entry", title=hostile),
            rec("build-pass", gate_checks_run=[hostile]),
            rec("review-feedback", author="evil\x1b[2Jer-reviewer",
                verdict="changes_requested",
                findings=[{"tag": "autofix", "location": hostile,
                           "description": hostile, "fix": hostile}]),
        )
        for flags in ((), ("--verbose",)):
            code, out, _ = self.view(*flags)
            self.assertEqual(code, 0)
            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)

    def test_hostile_req_id_cannot_inject_via_the_in_log_line(self):
        # The "in log:" and "no records for" lines print agent-authored
        # req_ids: an escape byte there must not reach the terminal either.
        self.write_log(
            {"type": "prd-entry", "req_id": "\x1b]0;pwned\x07\x1b[2Jgood",
             "ts": TS, "author": "tester", "title": "x"},
        )
        code, out, _ = self.view("--req-id", "REQ-MISSING-000")
        self.assertEqual(code, 3)
        self.assertNotIn("\x1b", out)
        self.assertIn("in log:", out)

    def test_colored_output_aligns_with_plain(self):
        # Padding is computed on plain text before escapes are added, so
        # stripping the escapes must reproduce the plain rendering exactly.
        self.write_log(*view_fixture())
        entries, errors = handoff.parse_log(str(self.log))
        roster = list(handoff.ROSTER_FLOOR)
        plain, _ = handoff.render_view(entries, errors, REQ, roster, color=False, verbose=False)
        colored, _ = handoff.render_view(entries, errors, REQ, roster, color=True, verbose=False)
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        self.assertEqual([ansi.sub("", line) for line in colored], plain)
        self.assertTrue(any("\x1b[" in line for line in colored))


class TestViewMarkdown(HandoffCase):
    """view --markdown: the same board as Markdown, for agent transcripts that
    strip ANSI but render Markdown. Grouping is shared with the TTY renderer;
    these tests pin the Markdown line composition and the escaping rules."""

    def setUp(self):
        super().setUp()
        patcher = unittest.mock.patch.dict(
            os.environ,
            {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "no-projects")})
        patcher.start()
        self.addCleanup(patcher.stop)

    def mdview(self, *extra):
        return self.run_cli(
            "view", "--file", str(self.log), "--markdown",
            "--layout", str(self.log.parent / "layout.toml"), *extra,
        )

    def test_header_is_h3_with_selective_bold_summary(self):
        # Only what ANSI highlights is bold: the failure count and the grade.
        self.write_log(*view_fixture())
        code, out, err = self.mdview()
        self.assertEqual(code, 0, err)
        self.assertIn("### REQ-DEMO-001 — Rate-limit the API\n", out)
        self.assertIn("3 review rounds · 2 build-passes · **1 build-failure**"
                      " · grade **CLEAR**\n", out)
        self.assertNotIn("**3 review rounds", out)
        self.assertNotIn("╭", out)
        self.assertNotIn("\x1b[", out)

    def test_grade_line_variants(self):
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.mdview()
        self.assertIn("0 review rounds · 1 build-pass · no grade yet\n", out)
        # The flat gate line is colored in ANSI: its kind token is bold here.
        self.assertIn("- ▲ **build-pass** 10:00\n", out)
        (self.log.parent / "layout.toml").write_text(
            '[harness]\nauto_grade = false\n')
        _, out, _ = self.mdview()
        self.assertIn("· grading disabled\n", out)
        self.assertNotIn("no grade yet", out)

    def test_matrix_renders_as_table(self):
        # Anchor layer: reviewer names bold, settled ✔/✖ outcomes bold;
        # ✎ rounds-in-progress and absent · stay plain.
        self.write_log(*view_fixture())
        _, out, _ = self.mdview()
        self.assertIn("| reviewer | R1 | R2 | R3 |\n", out)
        self.assertIn("| --- | --- | --- | --- |\n", out)
        self.assertIn("| **code-quality** | ✎ (2) | ✎ (1) | **✔** |\n", out)
        self.assertIn("| **security** | **✔** (1) | · | · |\n", out)
        self.assertIn("| **test** | · | · | · |\n", out)      # absent cells

    def test_timeline_bullets_with_nested_children(self):
        self.write_log(*view_fixture())
        _, out, _ = self.mdview()
        # Anchor layer: known step kinds bold — fused with their actor on
        # review/grade lines; the ANSI floor keeps verdicts and outcomes bold.
        self.assertIn("- ◇ **prd-entry** Rate-limit the API · (prd-expert)\n", out)
        self.assertIn("- ◈ **design-block** **minor** · (design)\n", out)
        # The implement session keeps its grouping: the parent bullet carries
        # the session elapsed italic, the children nest without glyphs.
        self.assertIn("- ◆ **implement** (implementer) · ***◷ 15m***\n", out)
        # The consult peer is the bold token (BOLD in ANSI), scaffolding plain.
        self.assertIn("  - ↳ consult → **design** · Per-tenant or per-endpoint?\n", out)
        self.assertIn("  - ↲ consult ← **design** · Per-tenant.\n", out)
        # `build` shares the outcome's ANSI color, so it rides the bold span.
        self.assertIn("  - ▲ **build ✗ unit-test failed** · retry 1\n", out)
        self.assertIn("  - ▲ **build ✓ clean** · fmt · test\n", out)
        self.assertIn("- ✎ **review code-quality** · **changes_requested**"
                      " · (2 findings)\n", out)
        self.assertIn("- ✔ **review security** · **approved** · (1 finding)\n", out)
        # Findings nest under the review: [tag] + code location + gist; only
        # the red-family tags (blocked, escalate) carry bold.
        self.assertIn("  - **[blocked]** `limiter.py:42` The bucket refill races", out)
        self.assertIn("  - **[escalate]** `limiter.py:88`", out)
        self.assertIn("  - [autofix] `limiter.py:12`", out)
        self.assertIn("  - [clarify] `prd.md:9`", out)
        # The rework anchor is the kind; its `←` source stays plain.
        self.assertIn("- ↻ **implement** (implementer) ← code-quality"
                      " · (1 finding) · ***◷ 4m***\n", out)
        self.assertIn("- ✚ **doc-autofix** `docs/system-design.md`"
                      " · stale-reference · (claude)\n", out)
        # Grade: kind + verdict as one bold unit; facet verdicts bold.
        self.assertIn("- ◆ **grade CLEAR** · Small, well-tested limiter.\n", out)
        self.assertIn("  - blast_radius — **clear** — one package\n", out)
        self.assertIn("  - scope_deviation — **concern** — persistence escalated\n", out)
        # Unknown kinds get no anchor: the fallback row stays fully plain.
        self.assertIn("- • mystery-record (someone-new)\n", out)
        self.assertNotIn("├", out)
        self.assertNotIn("└", out)

    def test_fix_anchor_bolds_kind_and_fixer(self):
        # A doc-owner fix dispatch: kind + fixer one bold unit, source plain.
        self.write_log(
            vrec("review-feedback", "doc-reviewer", "2026-07-06T10:20:00Z",
                 verdict="changes_requested",
                 findings=[{"tag": "autofix", "location": "prd.md:9",
                            "description": "stale"}]),
            vrec("dispatch-start", "product-requirements-expert",
                 "2026-07-06T10:32:00Z", responding_to=[1]),
        )
        _, out, _ = self.mdview()
        self.assertIn("- ↻ **fix prd-expert** ← doc · (1 finding)\n", out)

    def test_cost_tail_renders_italic_with_bold_highlights(self):
        # The tails are DIM in ANSI overall (italic here), but the elapsed and
        # the $ cost are GREEN there — bold inside the italic, on the steps
        # AND as the header roll-up riding the summary line via a hard break.
        cost_dim = " │ Σ ▲1.2M ▼7k "
        cache_dim = " │ ⛁ 88% $71%"

        def spans():
            return [(cost_dim, handoff.DIM), ("$2.50", handoff.GREEN),
                    (cache_dim, handoff.DIM)]

        def lookup(agent_type, start_rec, end_rec):
            return spans()

        lookup.slice_lookup = lambda agent_types, s, e: spans()
        self.write_log(*timed_fixture())
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries, errors, REQ, list(handoff.ROSTER_FLOOR), verbose=False,
            cost_lookup=lookup)
        out = "\n".join(lines)
        self.assertIn("· ***◷ 3m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out)
        self.assertIn("- ◆ **implement** (implementer)"
                      " · ***◷ 15m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out)
        self.assertIn("grade **CLEAR**  \n"
                      "***◷ 26m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out)

    def test_abort_closed_session_carries_its_tail(self):
        # The shared grouping closes a session on an aborting build-failure, so
        # the Markdown parent carries the opener → abort elapsed and cost too;
        # a plain retry failure closes nothing and its parent stays bare.
        cost = [(" │ Σ ▲7.5M ▼17k ", handoff.DIM), ("$4.66", handoff.GREEN),
                (" │ ⛁ 99% $89%", handoff.DIM)]
        self.write_log(
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z"),
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:11:00Z", abort_reason="design-mismatch"),
        )
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries, errors, REQ, list(handoff.ROSTER_FLOOR), verbose=False,
            cost_lookup=lambda at, s, e: cost)
        self.assertIn("- ◆ **implement** (implementer)"
                      " · ***◷ 5m** │ Σ ▲7.5M ▼17k **$4.66** │ ⛁ 99% $89%*",
                      "\n".join(lines))

        self.write_log(
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:06:00Z"),
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:11:00Z", retry=1),
        )
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries, errors, REQ, list(handoff.ROSTER_FLOOR), verbose=False,
            cost_lookup=lambda at, s, e: cost)
        self.assertIn("- ◆ **implement** (implementer)\n", "\n".join(lines) + "\n")

    def test_record_text_is_escaped(self):
        # A `|` in a table cell, a backtick in a code span, raw HTML, and a
        # structure-forming leading character must all stay inert.
        self.write_log(
            rec("prd-entry", title="# fake heading"),
            rec("review-feedback", author="weird|name-reviewer",
                verdict="changes_requested",
                findings=[{"tag": "blocked", "location": "a`b.py:7",
                           "description": "uses <script> here"}]),
        )
        code, out, err = self.mdview()
        self.assertEqual(code, 0, err)
        self.assertIn("— \\# fake heading", out)
        self.assertIn("| **weird\\|name** | ✎ (1) |", out)
        self.assertIn("`aʼb.py:7`", out)
        self.assertIn("uses \\<script> here", out)

    def test_markdown_and_color_are_mutually_exclusive(self):
        self.write_log(rec("prd-entry", title="t"))
        for flag in ("--color", "--no-color"):
            code, _, err = self.run_cli(
                "view", "--file", str(self.log), "--markdown", flag)
            self.assertEqual(code, 2)
            self.assertIn("not allowed with", err)

    def test_unknown_req_id_exits_three(self):
        self.write_log(rec("prd-entry", title="T"))
        code, out, _ = self.mdview("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)
        self.assertIn("in log: REQ-A-001", out)

    def test_slices_separate_with_a_rule(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec("prd-entry", req_id="REQ-B-002", title="Refactor sibling",
                author="system-design-expert"),
        )
        _, out, _ = self.mdview()
        self.assertIn("### REQ-A-001 — Original", out)
        self.assertIn("### REQ-B-002 — Refactor sibling", out)
        self.assertIn("\n\n---\n\n", out)
        self.assertLess(out.index("REQ-A-001"), out.index("REQ-B-002"))

    def test_dirty_log_lists_problems_as_plain_lines(self):
        self.log.write_text(json.dumps(rec("prd-entry", title="T")) + "\nnot json\n")
        code, out, _ = self.mdview()
        self.assertEqual(code, 0)
        self.assertIn("! 1 problem line skipped:", out)
        self.assertIn("- line 2:", out)

    def test_control_bytes_never_reach_the_document(self):
        hostile = "Innocent\x1b]0;pwned\x07\x1b[8m hidden\x00\ttail"
        self.write_log(
            rec("prd-entry", title=hostile),
            rec("review-feedback", author="evil\x1b[2Jer-reviewer",
                verdict="changes_requested",
                findings=[{"tag": "autofix", "location": hostile,
                           "description": hostile, "fix": hostile}]),
        )
        for flags in ((), ("--verbose",)):
            code, out, _ = self.mdview(*flags)
            self.assertEqual(code, 0)
            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)


class TestBoardCost(HandoffCase):
    """The per-step cost overlay on the timeline. The render-level tests inject
    a cost_lookup directly (render_view stays pure); the end-to-end test drives
    cmd_view against a synthetic Claude Code projects tree so the whole wiring
    — slug derivation, window match, tail formatting — is exercised once."""

    COST = " │ Σ ▲1.2M ▼7k $2.50 │ ⛁ 88% $71%"

    def _render(self, records, cost_lookup):
        self.write_log(*records)
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view(
            entries, errors, REQ, list(handoff.ROSTER_FLOOR),
            color=False, verbose=False, cost_lookup=cost_lookup)
        return "\n".join(lines)

    def test_cost_tail_rides_every_timed_step(self):
        out = self._render(timed_fixture(), lambda at, s, e: [(self.COST, handoff.DIM)])
        # prd, design, the implement session, review — four timed steps (the
        # grade is untimed by contract, so no tail can ride it).
        self.assertEqual(out.count(self.COST.strip()), 4)
        # Glued right after the ◷ duration marker.
        self.assertIn("◆ implement  (implementer)  ◷ 15m" + self.COST, out)
        self.assertIn("(prd-expert)  ◷ 3m" + self.COST, out)

    def test_no_lookup_renders_no_cost(self):
        out = self._render(timed_fixture(), None)
        self.assertNotIn("$2.50", out)
        self.assertNotIn("⛁", out)
        self.assertIn("◷ 15m", out)          # duration still renders

    def test_lookup_returning_none_omits_cost(self):
        # Off Claude Code, or an ambiguous window: durations show, cost does not
        # — the same degradation as a missing bounding timestamp.
        out = self._render(timed_fixture(), lambda at, s, e: None)
        self.assertNotIn("⛁", out)
        self.assertIn("◷ 3m", out)

    def test_cost_only_on_dispatched_steps(self):
        # view_fixture's prd/design/reviews carry no dispatch-start, so no
        # duration and no cost; only the two implement sessions are timed.
        out = self._render(view_fixture(), lambda at, s, e: [(self.COST, handoff.DIM)])
        self.assertEqual(out.count(self.COST.strip()), 2)

    def test_cost_on_parent_not_build_children(self):
        out = self._render([
            vrec("dispatch-start", "feature-implementer",
                 "2026-07-06T10:00:00Z", responding_to=[0]),
            vrec("build-failure", "feature-implementer",
                 "2026-07-06T10:02:00Z", retry=1, failed_check="test"),
            vrec("build-pass", "feature-implementer",
                 "2026-07-06T10:05:00Z", gate_checks_run=["test"]),
        ], lambda at, s, e: [(self.COST, handoff.DIM)])
        self.assertEqual(out.count(self.COST.strip()), 1)   # the parent only
        for line in out.splitlines():
            if "▲ build" in line:
                self.assertNotIn(self.COST.strip(), line)

    def _synthetic_project(self, usage_dict):
        """A synthetic ~/.claude/projects tree keyed on this process's own cwd
        slug — derived via the module's slug_for so the test tracks Claude
        Code's real encoding — holding one implementer message at 10:10."""
        slug = handoff.cc_accounting.slug_for(os.getcwd())
        sub = self.log.parent / "projects" / slug / "sess1" / "subagents"
        sub.mkdir(parents=True)
        msg = {"type": "assistant", "timestamp": "2026-07-06T10:10:00Z",
               "message": {"model": "claude-opus-4-8", "usage": usage_dict}}
        (sub / "agent-x.jsonl").write_text(json.dumps(msg) + "\n")
        (sub / "agent-x.meta.json").write_text(
            json.dumps({"agentType": "feature-implementer"}))

    def _view_with_projects(self):
        with unittest.mock.patch.dict(
                os.environ,
                {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "projects")}):
            self.write_log(
                vrec("dispatch-start", "feature-implementer",
                     "2026-07-06T10:05:00Z", responding_to=[0]),
                vrec("build-pass", "feature-implementer",
                     "2026-07-06T10:20:00Z", gate_checks_run=["test"]),
            )
            return self.run_cli(
                "view", "--file", str(self.log), "--no-color",
                "--layout", str(self.log.parent / "layout.toml"))

    def test_end_to_end_cost_from_synthetic_transcripts(self):
        # Drive cmd_view against a synthetic projects tree so the whole wiring
        # — slug derivation, window match, tail formatting — is exercised once.
        self._synthetic_project({"input_tokens": 1000, "output_tokens": 500,
                                 "cache_read_input_tokens": 0})
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        # opus (1000*5 + 500*25)/1e6 = 0.0175 -> $0.02; total_input 1000 -> 1k.
        self.assertIn("◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_header_shows_whole_slice_roll_up(self):
        # The header's third line aggregates the slice's own authors over the
        # first→last record window. A foreign agent type active in the same
        # window (here: Explore, never a record author) must not pollute it —
        # the figure stays ▲1k, not ▲78k.
        self._synthetic_project({"input_tokens": 1000, "output_tokens": 500,
                                 "cache_read_input_tokens": 0})
        slug = handoff.cc_accounting.slug_for(os.getcwd())
        sub = self.log.parent / "projects" / slug / "sess1" / "subagents"
        msg = {"type": "assistant", "timestamp": "2026-07-06T10:11:00Z",
               "message": {"model": "claude-opus-4-8",
                           "usage": {"input_tokens": 77000}}}
        (sub / "agent-y.jsonl").write_text(json.dumps(msg) + "\n")
        (sub / "agent-y.meta.json").write_text(json.dumps({"agentType": "Explore"}))
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertIn("│ ◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_malformed_usage_degrades_never_crashes(self):
        # A transcript message whose usage carries a non-numeric count must
        # drop into the degraded figures, never traceback the render — the
        # board reads, it never gates, and the transcripts are host data the
        # project does not control.
        self._synthetic_project({"input_tokens": "1200", "output_tokens": 500})
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertNotIn("Traceback", err)
        self.assertIn("◷ 15m", out)          # the duration still renders


class TestAuditAutofix(HandoffCase):
    """audit-autofix: the quality gate's mechanical autofix audit."""

    COMMIT_DATE = "2026-01-01T00:00:00Z"  # record TS (2026-06-11) is newer

    def setUp(self):
        super().setUp()
        repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        old_cwd = os.getcwd()
        os.chdir(repo)
        self.addCleanup(os.chdir, old_cwd)
        self.repo = repo
        env = {**os.environ,
               "GIT_COMMITTER_DATE": self.COMMIT_DATE,
               "GIT_AUTHOR_DATE": self.COMMIT_DATE,
               "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        def git(*argv):
            subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
                           check=True, env=env, capture_output=True)
        (repo / "docs" / "adr").mkdir(parents=True)
        (repo / "docs" / "system-design.md").write_text("design\n", encoding="utf-8")
        (repo / "docs" / "adr" / "0001-x.md").write_text("adr\n", encoding="utf-8")
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "init")

    def audit(self, *extra):
        return self.run_cli("audit-autofix", "--file", str(self.log), *extra)

    def autofix_rec(self, **over):
        base = {"type": "design-doc-autofix", "req_id": "REQ-A-001", "ts": TS,
                "author": "root", "file": "docs/system-design.md",
                "category": "writing-standards",
                "source_finding": {"review_feedback_author": "doc-reviewer",
                                   "review_feedback_ts": TS, "tag": "autofix",
                                   "location": "docs/system-design.md:1",
                                   "description": "d", "fix": "new text"},
                "old_content": "old text", "new_content": "new text",
                "lines_changed": 1, "chars_changed": 8}
        base.update(over)
        return base

    def test_clean_log_and_clean_tree_passes(self):
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)
        self.assertIn("autofix audit clean", out)

    def test_missing_log_and_clean_tree_passes(self):
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_oversize_record_fails_statically(self):
        # write_log bypasses append's schema gate — the audit must still
        # catch a hand-written record outside the caps.
        self.write_log(self.autofix_rec(lines_changed=6))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("autofix cap", err)

    def test_fix_mismatch_fails(self):
        self.write_log(self.autofix_rec(new_content="paraphrased"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("byte-identical", err)

    def test_heading_touch_fails(self):
        rec_ = self.autofix_rec(old_content="## Heading\nold",
                                new_content="## Heading\nnew")
        rec_["source_finding"]["fix"] = rec_["new_content"]
        self.write_log(rec_)
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("heading", err)

    def test_req_token_change_fails(self):
        rec_ = self.autofix_rec(old_content="see REQ-A-001",
                                new_content="see REQ-A-002")
        rec_["source_finding"]["fix"] = rec_["new_content"]
        self.write_log(rec_)
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("REQ-ID", err)

    def test_ineligible_path_fails(self):
        self.write_log(self.autofix_rec(file="docs/prd.md"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("design-doc path", err)

    def test_dirty_path_without_covering_record_fails(self):
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(rec("build-pass"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("no covering", err)

    def test_dirty_path_with_recent_autofix_record_passes(self):
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_design_block_covers_listed_path(self):
        (self.repo / "docs" / "adr" / "0001-x.md").write_text("edited\n",
                                                              encoding="utf-8")
        self.write_log(rec("design-block", primary_paths=["docs/adr/0001-x.md"]))
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_record_older_than_last_commit_does_not_cover(self):
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(self.autofix_rec(ts="2025-01-01T00:00:00Z"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("no covering", err)

    def test_records_before_design_block_are_superseded(self):
        # An out-of-bounds record at or before the latest design-block is
        # closed history — the superseding design-block ended that audit loop.
        self.write_log(self.autofix_rec(lines_changed=6), rec("design-block"))
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_other_slice_record_cannot_whitewash(self):
        # The audit is log-global: a record appended under another req_id is
        # audited too — it must not cover a path while escaping validation.
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(
            self.autofix_rec(req_id="REQ-B-002", lines_changed=6),
            rec("dispatch-start", req_id="REQ-A-001", responding_to=[0]),
        )
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("autofix cap", err)

    def test_superseded_record_does_not_cover_a_dirty_path(self):
        # The superseding design-block took ownership; only the paths it
        # lists stay covered.
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(self.autofix_rec(),
                       rec("design-block", primary_paths=["docs/other.md"]))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("no covering", err)

    def test_untracked_new_design_doc_needs_coverage(self):
        # File creation is the most drastic direct edit; ls-files --others
        # feeds the detector alongside the tracked diff.
        (self.repo / "docs" / "adr" / "0002-rogue.md").write_text("r\n",
                                                                  encoding="utf-8")
        self.write_log(rec("build-pass"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("docs/adr/0002-rogue.md", err)

    def test_nested_checkout_matches_project_relative_paths(self):
        # Project root below the git root (a monorepo sample): diff output
        # must stay cwd-relative so records' project-relative paths match —
        # without --relative every legitimate edit false-blocks forever.
        sub = self.repo / "apps" / "svc"
        (sub / "docs").mkdir(parents=True)
        (sub / "docs" / "system-design.md").write_text("design\n",
                                                       encoding="utf-8")
        env = {**os.environ, "GIT_COMMITTER_DATE": self.COMMIT_DATE,
               "GIT_AUTHOR_DATE": self.COMMIT_DATE,
               "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "add", "."], check=True, env=env, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "svc"],
                       check=True, env=env, capture_output=True)
        os.chdir(sub)
        self.addCleanup(os.chdir, self.repo)
        (sub / "docs" / "system-design.md").write_text("edited\n",
                                                       encoding="utf-8")
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_unrelated_commit_does_not_expire_covering_record(self):
        # Baseline is the last commit touching the audited docs: a newer
        # commit elsewhere in the repo must not invalidate a record that
        # still covers the only docs change since their last commit.
        (self.repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
        env = {**os.environ, "GIT_COMMITTER_DATE": "2026-06-12T00:00:00Z",
               "GIT_AUTHOR_DATE": "2026-06-12T00:00:00Z",
               "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"}
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "add", "unrelated.txt"],
                       check=True, env=env, capture_output=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-q", "-m", "unrelated"],
                       check=True, env=env, capture_output=True)
        (self.repo / "docs" / "system-design.md").write_text("edited\n",
                                                             encoding="utf-8")
        self.write_log(self.autofix_rec())  # TS 2026-06-11, after docs commit
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_unborn_head_skips_direct_edit_detection(self):
        # A fresh scaffold has no commit: step 1 still runs; step 2 starts
        # at the first commit instead of false-blocking the first slice.
        fresh = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, fresh, ignore_errors=True)
        old_cwd = os.getcwd()
        os.chdir(fresh)
        self.addCleanup(os.chdir, old_cwd)
        subprocess.run(["git", "init", "-q"], check=True, capture_output=True)
        (fresh / "docs").mkdir()
        (fresh / "docs" / "system-design.md").write_text("new\n", encoding="utf-8")
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)
        self.assertIn("no commit yet", out)


class TestValidateDispatchDiscipline(RouteCase):
    def validate(self):
        return self.run_cli("validate", "--file", str(self.log),
                            "--schemas", str(self.schemas))

    def test_substantive_without_dispatch_start_warns(self):
        self.write_log(rec("build-pass", author="feature-implementer"))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)

    def test_dispatch_start_silences_the_warning(self):
        self.write_log(
            rec("dispatch-start", author="feature-implementer", responding_to=[0]),
            rec("build-pass", author="feature-implementer"),
        )
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertNotIn("no prior dispatch-start", err)

    def test_engine_and_human_authors_are_exempt(self):
        self.write_log(
            rec("review-plan", author="review-plan-engine"),
            rec("consultation-response", author="human"),
        )
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertNotIn("warning", err)

    def test_warning_sanitizes_agent_authored_fields(self):
        # author is agent-authored; an embedded ESC/BEL must not reach the
        # terminal raw (same discipline as the board's _sanitize).
        hostile = "\x1b]0;PWNED\x07\x1b[31mevil\x1b[0m"
        self.write_log(rec("build-pass", author=hostile))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("\x07", err)


class TestAppendRespondingTo(RouteCase):
    def test_dangling_pointer_is_rejected(self):
        # A pointer past the end of the log silently degrades the board's
        # fix-attribution; append is the one moment the referent set is known.
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[5]), rtype="dispatch-start")
        self.assertEqual(code, 1)
        self.assertIn("non-existent log line", err)

    def test_sentinel_zero_and_existing_lines_pass(self):
        self.write_log(rec("prd-entry"))
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[0, 1]), rtype="dispatch-start")
        self.assertEqual(code, 0, err)

    def test_unterminated_last_line_still_counts_as_a_referent(self):
        # The missing-trailing-newline state the writer repairs 15 lines
        # later must not undercount the referent set here.
        self.log.write_text('{"a":1}\n{"b":2}\n{"c":3}', encoding="utf-8")
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[3]), rtype="dispatch-start")
        self.assertEqual(code, 0, err)


class TestAccountingDegradation(unittest.TestCase):
    def test_broken_accounting_module_never_gates_the_writer(self):
        # A present-but-broken vendored cc_accounting.py (an interrupted copy)
        # must not take handoff.py down: the overlay's import guard catches
        # any import-time error, not just a missing module — SyntaxError is
        # not an ImportError subclass.
        with tempfile.TemporaryDirectory() as td:
            scripts = Path(td)
            shutil.copy(_HERE / "handoff.py", scripts / "handoff.py")
            (scripts / "cc_accounting.py").write_text("def broken(:\n",
                                                      encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(scripts / "handoff.py"), "--help"],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
