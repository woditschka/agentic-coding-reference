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
import os
import re
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
        finding = {"tag": "blocked", "location": "src/widget:1", "description": "d"}
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
        prd = {"tag": "blocked", "location": "docs/prd.md:9", "description": "prd"}
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

    def test_findings_split_by_artifact_owner(self):
        findings = [
            {"tag": "clarify", "location": "src/widget:1", "description": "code",
             "clarify_target": "system-design-expert"},
            {"tag": "blocked", "location": "docs/prd.md:9", "description": "prd"},
            {"tag": "clarify", "location": "docs/adr/x.md:3", "description": "adr",
             "clarify_target": "system-design-expert"},
            {"tag": "autofix", "location": "docs/system-design.md:7", "description": "typo", "fix": "x"},
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
        finding = {"tag": "autofix", "location": "docs/system-design.md:7", "description": "typo", "fix": "x"}
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
↳ consult  implementer → design  Per-tenant or per-endpoint?
↲ consult  design → implementer  Per-tenant.
── ▲ build-failure  unit-test  retry 1 ─────────────────────────────────
── ▲ build-pass  fmt, test ─────────────────────────────────────────────
✎ review  code-quality  changes_requested  (2 findings)
  ├ [blocked] limiter.py:42  The bucket refill races with allow(); two workers can both observe a singl…
  └ [autofix] limiter.py:12  The Limiter type lacks a doc comment.
✔ review  security  approved  (1 finding)
  └ [clarify] prd.md:9  Is the burst size a hard product number?
✎ review  code-quality  changes_requested  (1 finding)
  └ [escalate] limiter.py:88  Persisting bucket state was not in the PRD; scope call for a human.
✚ doc-autofix  docs/system-design.md  stale-reference  (claude)
── ▲ build-pass  fmt, test ─────────────────────────────────────────────
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
    """Every record type, three review rounds, a changes_requested with two
    findings, an approved-with-finding, a facets dict, an unknown type — and
    a design-block ts one hour BEFORE the prd-entry's, so any ts sort would
    scramble the timeline."""
    return [
        vrec("dispatch-start", "feature-implementer", "2026-07-06T10:00:00Z", responding_to=0),
        vrec("prd-entry", "product-requirements-expert", "2026-07-06T10:00:00Z",
             title="Rate-limit the API"),
        vrec("design-block", "system-design-expert", "2026-07-06T09:00:00Z", verdict="minor"),
        vrec("consultation-request", "feature-implementer", "2026-07-06T10:10:00Z",
             target="system-design-expert", context="granularity",
             question="Per-tenant or per-endpoint?"),
        vrec("consultation-response", "system-design-expert", "2026-07-06T10:12:00Z",
             in_response_to=4, answer="Per-tenant."),
        vrec("build-failure", "feature-implementer", "2026-07-06T10:20:00Z",
             retry=1, failed_check="unit-test"),
        vrec("build-pass", "feature-implementer", "2026-07-06T10:30:00Z",
             gate_checks_run=["fmt", "test"]),
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T10:40:00Z",
             verdict="changes_requested", findings=[
                 {"tag": "blocked", "location": "src/ingest/limiter.py:42 (allow)",
                  "description": "The bucket refill races with allow(); two workers can"
                                 " both observe a single remaining token and pass.",
                  "fix": "Hold the lock across the refill and the take."},
                 {"tag": "autofix", "location": "src/ingest/limiter.py:12",
                  "description": "The Limiter type lacks a doc comment.",
                  "fix": "Add the standard comment."}]),
        vrec("review-feedback", "security-reviewer", "2026-07-06T10:41:00Z",
             verdict="approved", findings=[
                 {"tag": "clarify", "location": "docs/prd.md:9",
                  "description": "Is the burst size a hard product number?",
                  "clarify_target": "product-requirements-expert"}]),
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T11:00:00Z",
             verdict="changes_requested", findings=[
                 {"tag": "escalate", "location": "src/ingest/limiter.py:88",
                  "description": "Persisting bucket state was not in the PRD;"
                                 " scope call for a human."}]),
        vrec("design-doc-autofix", "claude", "2026-07-06T11:05:00Z",
             file="docs/system-design.md", category="stale-reference", source_finding="x",
             old_content="a", new_content="b", lines_changed=1, chars_changed=2),
        vrec("build-pass", "feature-implementer", "2026-07-06T11:10:00Z",
             gate_checks_run=["fmt", "test"]),
        vrec("review-feedback", "code-quality-reviewer", "2026-07-06T11:20:00Z",
             verdict="approved", findings=[]),
        vrec("grader-features", "change-grader", "2026-07-06T11:30:00Z", features={"loc": 12}),
        vrec("grader-verdict", "change-grader", "2026-07-06T11:31:00Z", verdict="clear",
             summary="Small, well-tested limiter.", rationale="r", facets={
                 "blast_radius": {"verdict": "clear", "note": "one package"},
                 "scope_deviation": {"verdict": "concern", "note": "persistence escalated"}}),
        vrec("mystery-record", "someone-new", "2026-07-06T11:40:00Z"),
    ]


class TestView(HandoffCase):
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

    def test_req_id_defaults_to_latest_record(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec("prd-entry", req_id="REQ-B-002", title="Refactor sibling",
                author="system-design-expert"),
        )
        _, out, _ = self.view()
        self.assertIn("REQ-B-002", out.splitlines()[1])
        self.assertIn("also in log: REQ-A-001", out)

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
                findings=[{"tag": "blocked", "location": "x", "description": "d"}]),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
