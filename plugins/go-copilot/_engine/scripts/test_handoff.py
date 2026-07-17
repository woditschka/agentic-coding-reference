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
    "properties": {
        "type": {"const": "ref-rec"},
        "facet": {"$ref": "#/definitions/facet"},
    },
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
        shuffled = {
            "author": "tester",
            "note": "n",
            "type": "test-rec",
            "ts": TS,
            "req_id": REQ,
        }
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

    def test_production_format_is_offset_isoformat_with_microseconds(self):
        # The goldens pin a mocked "...Z" ts; production writes isoformat with a
        # numeric UTC offset and microseconds. Freeze that shape deterministically
        # (a fixed clock avoids the 1-in-1e6 microsecond==0 edge).
        fixed = datetime.datetime(2026, 7, 17, 12, 34, 56, 789012, tzinfo=datetime.UTC)
        with unittest.mock.patch.object(handoff.datetime, "datetime") as dt:
            dt.now.return_value = fixed
            ts = handoff.ts_now()
        self.assertEqual(ts, "2026-07-17T12:34:56.789012+00:00")


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
            "append",
            "test-rec",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
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
            "append",
            "test-rec",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
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
        (self.schemas / "build-failure.schema.json").write_text(
            json.dumps(retry_schema)
        )
        self.write_log(
            {"type": "design-block", "req_id": "REQ-A-001"},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 1},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 2},
            {"type": "build-failure", "req_id": "REQ-A-001", "retry": 3},
        )
        code, out, err = self.run_cli(
            "next-retry",
            "--req-id",
            "REQ-A-001",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
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
            "latest",
            "--type",
            "design-block",
            "--req-id",
            "REQ-A-001",
            "--file",
            str(self.log),
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

    def test_show_directory_at_log_path_fails_clean(self):
        # Every other reader degrades to the clean error form on a directory
        # at the log path (parse_log's broad OSError); show must too, not
        # traceback with IsADirectoryError.
        self.log.unlink(missing_ok=True)
        self.log.mkdir()
        code, _, err = self.run_cli("show", "--file", str(self.log))
        self.assertNotEqual(code, 0)
        self.assertIn("cannot read", err)
        self.assertNotIn("Traceback", err)

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


class TestGoldenCanonicalBytes(unittest.TestCase):
    """Byte-identity golden tests (ADR 2026-07-17, slice 1): freeze the append
    path's canonical serialization of one representative record per
    schemas/scratch/ type before the typed-core refactor. Each expected value
    is an exact byte literal derived from current output — field order follows
    the schema's property declaration order, separators are ", "/": ", and the
    line is newline-terminated. ts is the append-stamped TS, so the bytes are
    fully determined. These freeze behavior; the later refactor must reproduce
    them byte-for-byte."""

    # (rtype, input record sans ts, exact expected file bytes incl trailing \n).
    # Records are shuffled/partial on input; canonicalize reorders to the bytes
    # below. Eyeball each literal against its schema's property order.
    GOLDEN = (
        (
            # Multibyte content pins ensure_ascii=False: the expected literal
            # carries the raw UTF-8 bytes (ü -> \xc3\xbc, ✓ -> \xe2\x9c\x93), so a
            # refactor flipping to \uXXXX escapes changes these bytes and fails.
            "consultation-request",
            {
                "type": "consultation-request",
                "req_id": REQ,
                "author": "feature-implementer",
                "target": "system-design-expert",
                "context": "red-green transition for behavior X in slice Y",
                "question": "Which package owns the adapter? Prüfung: ✓ done",
                "stop_state": "widget.py:42, awaiting answer",
            },
            b'{"type": "consultation-request", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "feature-implementer", "target": '
            b'"system-design-expert", "context": "red-green transition for behavior '
            b'X in slice Y", "question": "Which package owns the adapter? '
            b'Pr\xc3\xbcfung: \xe2\x9c\x93 done", '
            b'"stop_state": "widget.py:42, awaiting answer"}\n',
        ),
        (
            "consultation-response",
            {
                "type": "consultation-response",
                "req_id": REQ,
                "author": "system-design-expert",
                "in_response_to": 1,
                "answer": "Place the adapter in the boundary package.",
                "memory_updates": [
                    {
                        "path": "docs/system-design.md",
                        "summary": "Note adapter placement.",
                    }
                ],
                "notes": "See the adapter ADR.",
            },
            b'{"type": "consultation-response", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "system-design-expert", '
            b'"in_response_to": 1, "answer": "Place the adapter in the boundary '
            b'package.", "memory_updates": [{"path": "docs/system-design.md", '
            b'"summary": "Note adapter placement."}], "notes": "See the adapter '
            b'ADR."}\n',
        ),
        (
            "design-block",
            {
                "type": "design-block",
                "req_id": REQ,
                "author": "system-design-expert",
                "verdict": "covered",
                "architectural_fit": "Fits the existing adapter pattern.",
                "primary_paths": ["src/widget.py"],
                "supporting_paths": ["tests/test_widget.py"],
                "patterns": [
                    {"ref": "src/base.py:10", "description": "Follow the base adapter."}
                ],
            },
            b'{"type": "design-block", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "system-design-expert", "verdict": '
            b'"covered", "architectural_fit": "Fits the existing adapter pattern.", '
            b'"primary_paths": ["src/widget.py"], "supporting_paths": '
            b'["tests/test_widget.py"], "patterns": [{"ref": "src/base.py:10", '
            b'"description": "Follow the base adapter."}]}\n',
        ),
        (
            "design-doc-autofix",
            {
                "type": "design-doc-autofix",
                "req_id": REQ,
                "author": "root",
                "file": "docs/system-design.md",
                "category": "writing-standards",
                "source_finding": {
                    "review_feedback_author": "doc-reviewer",
                    "review_feedback_ts": TS,
                    "tag": "autofix",
                    "location": "docs/system-design.md:7",
                    "description": "Tighten the sentence.",
                    "fix": "The adapter owns serialization.",
                },
                "old_content": "The adapter is responsible for owning serialization.",
                "new_content": "The adapter owns serialization.",
                "lines_changed": 1,
                "chars_changed": 20,
            },
            b'{"type": "design-doc-autofix", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "root", "file": '
            b'"docs/system-design.md", "category": "writing-standards", '
            b'"source_finding": {"review_feedback_author": "doc-reviewer", '
            b'"review_feedback_ts": "2026-06-11T10:00:00Z", "tag": "autofix", '
            b'"location": "docs/system-design.md:7", "description": "Tighten the '
            b'sentence.", "fix": "The adapter owns serialization."}, "old_content": '
            b'"The adapter is responsible for owning serialization.", "new_content": '
            b'"The adapter owns serialization.", "lines_changed": 1, "chars_changed": '
            b"20}\n",
        ),
        (
            "dispatch-start",
            {
                "type": "dispatch-start",
                "req_id": REQ,
                "author": "feature-implementer",
                "responding_to": [0],
            },
            b'{"type": "dispatch-start", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "feature-implementer", '
            b'"responding_to": [0]}\n',
        ),
        (
            "grader-features",
            {
                "type": "grader-features",
                "req_id": REQ,
                "author": "change-grader",
                "features": {
                    "base_ref": "main",
                    "head_ref": "0f1e2d3c",
                    "head_kind": "worktree",
                    "files_changed": 2,
                    "module_count": 1,
                    "test_prod_ratio": 1.5,
                    "hunks": 3,
                    "build_passed": True,
                    "reviewers": None,
                    "build_retries": 0,
                    "consultations": 0,
                    "design_revisions": 0,
                },
            },
            b'{"type": "grader-features", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "change-grader", "features": '
            b'{"base_ref": "main", "head_ref": "0f1e2d3c", "head_kind": "worktree", '
            b'"files_changed": 2, "module_count": 1, "test_prod_ratio": 1.5, "hunks": '
            b'3, "build_passed": true, "reviewers": null, "build_retries": 0, '
            b'"consultations": 0, "design_revisions": 0}}\n',
        ),
        (
            "grader-verdict",
            {
                "type": "grader-verdict",
                "req_id": REQ,
                "author": "change-grader",
                "responding_to": [1],
                "summary": "relabel unknown-activity bucket",
                "facets": {
                    "blast_radius": {"verdict": "clear", "note": "One module touched."},
                    "semantic_surprise": {
                        "verdict": "clear",
                        "note": "No behavior change.",
                    },
                    "test_adequacy": {
                        "verdict": "clear",
                        "note": "Tests cover the path.",
                    },
                    "reviewer_hedging": {
                        "verdict": "clear",
                        "note": "No hedged approvals.",
                    },
                    "scope_deviation": {
                        "verdict": "clear",
                        "note": "Matches the slice.",
                    },
                },
                "rationale": "Small, well-tested change with no surprises.",
                "verdict": "clear",
            },
            b'{"type": "grader-verdict", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "change-grader", "responding_to": '
            b'[1], "summary": "relabel unknown-activity bucket", "facets": '
            b'{"blast_radius": {"verdict": "clear", "note": "One module touched."}, '
            b'"semantic_surprise": {"verdict": "clear", "note": "No behavior '
            b'change."}, "test_adequacy": {"verdict": "clear", "note": "Tests cover '
            b'the path."}, "reviewer_hedging": {"verdict": "clear", "note": "No '
            b'hedged approvals."}, "scope_deviation": {"verdict": "clear", "note": '
            b'"Matches the slice."}}, "rationale": "Small, well-tested change with no '
            b'surprises.", "verdict": "clear"}\n',
        ),
        (
            "review-feedback",
            {
                "type": "review-feedback",
                "req_id": REQ,
                "author": "code-quality-reviewer",
                "verdict": "changes_requested",
                "findings": [
                    {
                        "tag": "blocked",
                        "location": "src/widget.py:1",
                        "description": "Extract the duplicated helper.",
                        "severity": "critical",
                    }
                ],
            },
            b'{"type": "review-feedback", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "code-quality-reviewer", "verdict": '
            b'"changes_requested", "findings": [{"tag": "blocked", "location": '
            b'"src/widget.py:1", "description": "Extract the duplicated helper.", '
            b'"severity": "critical"}]}\n',
        ),
        (
            "review-plan",
            {
                "type": "review-plan",
                "req_id": REQ,
                "author": "review-plan-engine",
                "risk": "low",
                "roster": ["code-quality-reviewer", "test-reviewer"],
                "scope": "full-diff",
                "basis": {"tree_sha": "a" * 40, "pass": "first"},
                "rationale": "Small surface-matched change.",
            },
            b'{"type": "review-plan", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "review-plan-engine", "risk": "low", '
            b'"roster": ["code-quality-reviewer", "test-reviewer"], "scope": '
            b'"full-diff", "basis": {"tree_sha": '
            b'"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "pass": "first"}, '
            b'"rationale": "Small surface-matched change."}\n',
        ),
    )

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        stamp = unittest.mock.patch.object(handoff, "ts_now", return_value=TS)
        stamp.start()
        self.addCleanup(stamp.stop)

    def _append(self, rtype, record):
        log = self.root / f"{rtype}.jsonl"
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(record))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = handoff.main(
                    [
                        "append",
                        rtype,
                        "--file",
                        str(log),
                        "--schemas",
                        str(_REPO_SCHEMAS),
                    ]
                )
        finally:
            sys.stdin = old_stdin
        self.assertEqual(code, 0, err.getvalue())
        return log.read_bytes()

    def test_every_golden_type_resolves_to_a_schema(self):
        # Every pinned record maps to a real schema in whatever tree this runs
        # (core carries the nine below; a materialized sample adds stack types,
        # so this is a subset check, not equality). A golden entry naming a
        # deleted schema fails here.
        covered = {rtype for rtype, _, _ in self.GOLDEN}
        on_disk = {
            p.name[: -len(".schema.json")] for p in _REPO_SCHEMAS.glob("*.schema.json")
        }
        self.assertTrue(covered <= on_disk, covered - on_disk)

    def test_canonical_bytes_are_frozen(self):
        for rtype, record, expected in self.GOLDEN:
            with self.subTest(schema=rtype):
                self.assertEqual(self._append(rtype, record), expected)


# Route fixtures use permissive schemas: route's own decisions are under test,
# not the validator (TestAppendValidation covers that). Gate-failure tests
# override one schema with a strict variant.
PERMISSIVE = {"type": "object", "required": ["type"]}
PIPELINE_TYPES = (
    "prd-entry",
    "design-block",
    "build-pass",
    "build-failure",
    "review-feedback",
    "consultation-request",
    "consultation-response",
    "dispatch-start",
    "design-doc-autofix",
    "grader-features",
    "grader-verdict",
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
        vrec(
            "prd-entry",
            "product-requirements-expert",
            "2026-07-06T10:00:00Z",
            title="Rate-limit the API",
        ),  # L1
        vrec(
            "design-block",
            "system-design-expert",
            "2026-07-06T09:00:00Z",
            verdict="minor",
        ),  # L2
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T10:15:00Z",
            responding_to=[2],
        ),  # L3 opener
        vrec(
            "consultation-request",
            "feature-implementer",
            "2026-07-06T10:16:00Z",
            target="system-design-expert",
            context="granularity",
            question="Per-tenant or per-endpoint?",
        ),  # L4
        vrec(
            "consultation-response",
            "system-design-expert",
            "2026-07-06T10:18:00Z",
            in_response_to=4,
            answer="Per-tenant.",
        ),  # L5
        vrec(
            "build-failure",
            "feature-implementer",
            "2026-07-06T10:20:00Z",
            retry=1,
            failed_check="unit-test",
        ),  # L6
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T10:30:00Z",
            gate_checks_run=["fmt", "test"],
        ),  # L7 closes S1
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T10:40:00Z",
            verdict="changes_requested",
            findings=[
                {
                    "tag": "blocked",
                    "location": "src/ingest/limiter.py:42 (allow)",
                    "description": "The bucket refill races with allow(); two workers can"
                    " both observe a single remaining token and pass.",
                    "fix": "Hold the lock across the refill and the take.",
                },
                {
                    "tag": "autofix",
                    "location": "src/ingest/limiter.py:12",
                    "description": "The Limiter type lacks a doc comment.",
                    "fix": "Add the standard comment.",
                },
            ],
        ),  # L8
        vrec(
            "review-feedback",
            "security-reviewer",
            "2026-07-06T10:41:00Z",
            verdict="approved",
            findings=[
                {
                    "tag": "clarify",
                    "location": "docs/prd.md:9",
                    "description": "Is the burst size a hard product number?",
                    "clarify_target": "product-requirements-expert",
                }
            ],
        ),  # L9
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T11:00:00Z",
            verdict="changes_requested",
            findings=[
                {
                    "tag": "escalate",
                    "location": "src/ingest/limiter.py:88",
                    "description": "Persisting bucket state was not in the PRD;"
                    " scope call for a human.",
                }
            ],
        ),  # L10
        vrec(
            "design-doc-autofix",
            "claude",
            "2026-07-06T11:05:00Z",
            file="docs/system-design.md",
            category="stale-reference",
            source_finding="x",
            old_content="a",
            new_content="b",
            lines_changed=1,
            chars_changed=2,
        ),  # L11
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T11:05:30Z",
            responding_to=[10],
        ),  # L12 fix opener
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T11:10:00Z",
            gate_checks_run=["fmt", "test"],
        ),  # L13 closes S2
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T11:20:00Z",
            verdict="approved",
            findings=[],
        ),  # L14
        vrec(
            "grader-features",
            "change-grader",
            "2026-07-06T11:30:00Z",
            features={"loc": 12},
        ),
        vrec(
            "grader-verdict",
            "change-grader",
            "2026-07-06T11:31:00Z",
            verdict="clear",
            summary="Small, well-tested limiter.",
            rationale="r",
            facets={
                "blast_radius": {"verdict": "clear", "note": "one package"},
                "scope_deviation": {
                    "verdict": "concern",
                    "note": "persistence escalated",
                },
            },
        ),
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
        vrec(
            "dispatch-start",
            "product-requirements-expert",
            "2026-07-06T10:00:00Z",
            responding_to=[0],
        ),  # L1
        vrec(
            "prd-entry",
            "product-requirements-expert",
            "2026-07-06T10:03:00Z",
            title="t",
        ),  # L2 → 3m
        vrec(
            "dispatch-start",
            "system-design-expert",
            "2026-07-06T10:03:00Z",
            responding_to=[2],
        ),  # L3
        vrec(
            "design-block",
            "system-design-expert",
            "2026-07-06T10:05:00Z",
            verdict="covered",
        ),  # L4 → 2m
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T10:05:00Z",
            responding_to=[4],
        ),  # L5
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T10:20:00Z",
            gate_checks_run=["test"],
        ),  # L6 → 15m
        vrec(
            "dispatch-start",
            "code-quality-reviewer",
            "2026-07-06T10:20:00Z",
            responding_to=[6],
        ),  # L7
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T10:22:00Z",
            verdict="approved",
            findings=[],
        ),  # L8 → 2m
        vrec(
            "grader-verdict",
            "change-grader",
            "2026-07-06T10:26:00Z",
            verdict="clear",
            summary="done",
        ),  # L9, untimed
    ]


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
        env = {
            **os.environ,
            "GIT_COMMITTER_DATE": self.COMMIT_DATE,
            "GIT_AUTHOR_DATE": self.COMMIT_DATE,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }

        def git(*argv):
            subprocess.run(
                ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
                check=True,
                env=env,
                capture_output=True,
            )

        (repo / "docs" / "adr").mkdir(parents=True)
        (repo / "docs" / "system-design.md").write_text("design\n", encoding="utf-8")
        (repo / "docs" / "adr" / "0001-x.md").write_text("adr\n", encoding="utf-8")
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "init")

    def audit(self, *extra):
        return self.run_cli("audit-autofix", "--file", str(self.log), *extra)

    def autofix_rec(self, **over):
        base = {
            "type": "design-doc-autofix",
            "req_id": "REQ-A-001",
            "ts": TS,
            "author": "root",
            "file": "docs/system-design.md",
            "category": "writing-standards",
            "source_finding": {
                "review_feedback_author": "doc-reviewer",
                "review_feedback_ts": TS,
                "tag": "autofix",
                "location": "docs/system-design.md:1",
                "description": "d",
                "fix": "new text",
            },
            "old_content": "old text",
            "new_content": "new text",
            "lines_changed": 1,
            "chars_changed": 8,
        }
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
        rec_ = self.autofix_rec(
            old_content="## Heading\nold", new_content="## Heading\nnew"
        )
        rec_["source_finding"]["fix"] = rec_["new_content"]
        self.write_log(rec_)
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("heading", err)

    def test_req_token_change_fails(self):
        rec_ = self.autofix_rec(
            old_content="see REQ-A-001", new_content="see REQ-A-002"
        )
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
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
        self.write_log(rec("build-pass"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("no covering", err)

    def test_dirty_path_with_recent_autofix_record_passes(self):
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_design_block_covers_listed_path(self):
        (self.repo / "docs" / "adr" / "0001-x.md").write_text(
            "edited\n", encoding="utf-8"
        )
        self.write_log(rec("design-block", primary_paths=["docs/adr/0001-x.md"]))
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_record_older_than_last_commit_does_not_cover(self):
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
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
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
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
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
        self.write_log(
            self.autofix_rec(), rec("design-block", primary_paths=["docs/other.md"])
        )
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("no covering", err)

    def test_untracked_new_design_doc_needs_coverage(self):
        # File creation is the most drastic direct edit; ls-files --others
        # feeds the detector alongside the tracked diff.
        (self.repo / "docs" / "adr" / "0002-rogue.md").write_text(
            "r\n", encoding="utf-8"
        )
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
        (sub / "docs" / "system-design.md").write_text("design\n", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_COMMITTER_DATE": self.COMMIT_DATE,
            "GIT_AUTHOR_DATE": self.COMMIT_DATE,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."],
            check=True,
            env=env,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                "svc",
            ],
            check=True,
            env=env,
            capture_output=True,
        )
        os.chdir(sub)
        self.addCleanup(os.chdir, self.repo)
        (sub / "docs" / "system-design.md").write_text("edited\n", encoding="utf-8")
        self.write_log(self.autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_unrelated_commit_does_not_expire_covering_record(self):
        # Baseline is the last commit touching the audited docs: a newer
        # commit elsewhere in the repo must not invalidate a record that
        # still covers the only docs change since their last commit.
        (self.repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
        env = {
            **os.environ,
            "GIT_COMMITTER_DATE": "2026-06-12T00:00:00Z",
            "GIT_AUTHOR_DATE": "2026-06-12T00:00:00Z",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        }
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "add",
                "unrelated.txt",
            ],
            check=True,
            env=env,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@t",
                "-c",
                "user.name=t",
                "commit",
                "-q",
                "-m",
                "unrelated",
            ],
            check=True,
            env=env,
            capture_output=True,
        )
        (self.repo / "docs" / "system-design.md").write_text(
            "edited\n", encoding="utf-8"
        )
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


class TestAccountingDegradation(unittest.TestCase):
    def test_broken_accounting_module_never_gates_the_writer(self):
        # A present-but-broken vendored cc_accounting.py (an interrupted copy)
        # must not take handoff.py down: the overlay's import guard catches
        # any import-time error, not just a missing module — SyntaxError is
        # not an ImportError subclass.
        with tempfile.TemporaryDirectory() as td:
            scripts = Path(td)
            # handoff.py composes its sibling modules; ship the whole runtime
            # so startup runs.
            for mod in (
                "handoff.py",
                "handoff_schema.py",
                "handoff_records.py",
                "handoff_route.py",
                "handoff_view.py",
            ):
                shutil.copy(_HERE / mod, scripts / mod)
            (scripts / "cc_accounting.py").write_text(
                "def broken(:\n", encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, str(scripts / "handoff.py"), "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
