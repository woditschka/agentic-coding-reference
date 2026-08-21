#!/usr/bin/env python3
"""Entry-level characterization tests for the handoff CLI (stdlib only).

Run (from the scripts dir):
    python3 -m unittest discover -s tests -t .
    python3 -m unittest tests.test_handoff

Covers the determinism contract at the CLI boundary: canonical field order
(schema declaration order, unknown keys last), byte-identical output for
identical logical records, append-side validation against the schema subset,
damaged-tail handling, the gate queries (latest, next-retry), the golden
bytes, and concurrent-append exactness (spawns subprocesses; asserts the
host filesystem's O_APPEND atomicity — ADR 2026-08-16
lock-free-ledger-appends). The per-module suites live under tests/handoff/;
shared scaffolding is in tests.support (ADR 2026-07-17
runtime-package-layout).
"""

import concurrent.futures
import contextlib
import datetime
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

from tests.support import (
    _HERE,
    _REPO_SCHEMAS,
    REQ,
    TS,
    HandoffCase,
    base_record,
    entry,
    handoff,
    rec,
)


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

    def test_append_onto_truncated_tail_warns_and_lands_glued(self):
        # No pre-write repair: a reader cannot tell crash damage from a
        # concurrent write still landing (ADR 2026-08-16
        # lock-free-ledger-appends). The append lands on the damaged line,
        # warns, and validate blocks the log until it is repaired.
        self.log.write_text(json.dumps(base_record()))  # no trailing newline
        code, out, err = self.append(base_record(note="second"))
        self.assertEqual(code, 0)
        self.assertIn("truncated", err)
        self.assertIn("at line 1", out)  # the glued line is line 1
        self.assertEqual(len(self.log_lines()), 1)
        code, _, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)


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
        with unittest.mock.patch.object(handoff.schema.datetime, "datetime") as dt:
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
            "prd-autofix",
            {
                "type": "prd-autofix",
                "req_id": REQ,
                "author": "root",
                "file": "docs/prd.md",
                "category": "writing-standards",
                "source_finding": {
                    "review_feedback_author": "doc-reviewer",
                    "review_feedback_ts": TS,
                    "tag": "autofix",
                    "location": "docs/prd.md:12",
                    "description": "Split the sentence.",
                    "fix": "The export runs nightly. It writes one file.",
                },
                "old_content": "The export runs nightly and writes one file.",
                "new_content": "The export runs nightly. It writes one file.",
                "lines_changed": 1,
                "chars_changed": 6,
            },
            b'{"type": "prd-autofix", "req_id": "REQ-DEMO-001", "ts": '
            b'"2026-06-11T10:00:00Z", "author": "root", "file": '
            b'"docs/prd.md", "category": "writing-standards", '
            b'"source_finding": {"review_feedback_author": "doc-reviewer", '
            b'"review_feedback_ts": "2026-06-11T10:00:00Z", "tag": "autofix", '
            b'"location": "docs/prd.md:12", "description": "Split the '
            b'sentence.", "fix": "The export runs nightly. It writes one file."}, '
            b'"old_content": "The export runs nightly and writes one file.", '
            b'"new_content": "The export runs nightly. It writes one file.", '
            b'"lines_changed": 1, "chars_changed": 6}\n',
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
        stamp = unittest.mock.patch.object(entry, "ts_now", return_value=TS)
        stamp.start()
        self.addCleanup(stamp.stop)

    def _append(self, rtype, record):
        log = self.root / f"{rtype}.jsonl"
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps(record))
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = entry.main(
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
        (repo / "docs" / "prd.md").write_text("prd\n", encoding="utf-8")
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

    def test_prd_autofix_touching_ng_row_fails(self):
        # Non-Goals rows are judgment by definition: the mechanical-fix lane
        # must never dirty the scope-lock delta (Gate 1).
        rec_ = self.autofix_rec(
            type="prd-autofix",
            file="docs/prd.md",
            old_content="| NG-4 | Deleting a record | Old reason |",
            new_content="| NG-4 | Deleting a record | New reason |",
        )
        rec_["source_finding"]["fix"] = rec_["new_content"]
        self.write_log(rec_)
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("Non-Goals table row", err)

    def test_ineligible_path_fails(self):
        self.write_log(self.autofix_rec(file="docs/prd.md"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("design-doc path", err)

    def prd_autofix_rec(self, **over):
        base = self.autofix_rec(
            type="prd-autofix",
            file="docs/prd.md",
            source_finding={
                "review_feedback_author": "doc-reviewer",
                "review_feedback_ts": TS,
                "tag": "autofix",
                "location": "docs/prd.md:1",
                "description": "d",
                "fix": "new text",
            },
        )
        base.update(over)
        return base

    def test_prd_record_clean_log_passes(self):
        self.write_log(self.prd_autofix_rec())
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)
        self.assertIn("autofix audit clean", out)

    def test_prd_record_on_design_path_fails(self):
        # The path predicate follows the record type: a prd-autofix naming a
        # design-doc path is mis-typed, not eligible.
        self.write_log(self.prd_autofix_rec(file="docs/system-design.md"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("PRD path", err)

    def test_prd_record_shares_the_static_bounds(self):
        self.write_log(self.prd_autofix_rec(lines_changed=6))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("autofix cap", err)

    def test_prd_record_fix_mismatch_fails(self):
        self.write_log(self.prd_autofix_rec(new_content="paraphrased"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("byte-identical", err)

    def test_prd_records_before_prd_entry_are_superseded(self):
        # A prd-entry closes the PRD audit loop for its slice, exactly as a
        # design-block closes the design-doc loop.
        self.write_log(self.prd_autofix_rec(lines_changed=6), rec("prd-entry"))
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

    def test_prd_entry_does_not_supersede_design_records(self):
        # Supersession is per record type: the PRD owner's record must not
        # close the design-doc audit loop, nor vice versa.
        self.write_log(self.autofix_rec(lines_changed=6), rec("prd-entry"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("autofix cap", err)

    def test_design_block_does_not_supersede_prd_records(self):
        self.write_log(self.prd_autofix_rec(lines_changed=6), rec("design-block"))
        code, out, err = self.audit()
        self.assertEqual(code, 1)
        self.assertIn("autofix cap", err)

    def test_dirty_prd_without_covering_record_passes(self):
        # Pins the deliberate deferral (prd-autofix ADR): the direct-edit
        # dirty scan stays design-doc-scoped; docs/prd.md is outside it.
        (self.repo / "docs" / "prd.md").write_text("edited\n", encoding="utf-8")
        self.write_log(rec("build-pass"))
        code, out, err = self.audit()
        self.assertEqual(code, 0, err)

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
        # A present-but-broken vendored accounting.py (an interrupted copy)
        # must not take handoff.py down: the overlay's import guard catches
        # any import-time error, not just a missing module — SyntaxError is
        # not an ImportError subclass.
        with tempfile.TemporaryDirectory() as td:
            scripts = Path(td)
            # handoff.py composes the handoff package (ADR 2026-07-17
            # runtime-package-layout); ship the entry and the whole package so
            # startup runs, then break the vendored accounting module beside them.
            shutil.copy(_HERE / "handoff.py", scripts / "handoff.py")
            shutil.copytree(_HERE / "handoff", scripts / "handoff")
            (scripts / "accounting.py").write_text("def broken(:\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(scripts / "handoff.py"), "--help"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)


class TestConcurrentAppends(HandoffCase):
    """Lock-free append under real multi-process concurrency (ADR 2026-08-16
    in the reference): parallel writers through the CLI must land every
    record exactly once, keep the log validate-clean, and report receipts
    naming each record's true line. This also proves the host filesystem
    honors O_APPEND write atomicity — the property the parallel reviewer
    fan-out rests on. A failure here means parallel appends are unsafe on
    this filesystem (network mounts are the known offender)."""

    WORKERS = 4
    APPENDS = 6

    def test_interleaved_descriptors_yield_exact_offsets(self):
        # The receipt mechanism, deterministically: two O_APPEND descriptors
        # interleave; each lseek(SEEK_CUR) bounds its own write, so each
        # prefix count names that writer's true line — the property the
        # probabilistic test below can only sample.
        fd_a = os.open(self.log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        fd_b = os.open(self.log, os.O_WRONLY | os.O_APPEND)
        try:
            os.write(fd_a, b'{"one":1}\n')
            os.write(fd_b, b'{"two":2}\n')
            end_a = os.lseek(fd_a, 0, os.SEEK_CUR)
            end_b = os.lseek(fd_b, 0, os.SEEK_CUR)
        finally:
            os.close(fd_a)
            os.close(fd_b)
        raw = self.log.read_bytes()
        self.assertEqual(raw[:end_a].count(b"\n"), 1)
        self.assertEqual(raw[:end_b].count(b"\n"), 2)

    def test_parallel_appends_land_exactly_with_exact_receipts(self):
        """Needs O_APPEND write atomicity — a failure here means this
        filesystem (network mounts are the known offender) cannot run the
        parallel reviewer fan-out safely."""
        (self.schemas / "stress-rec.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type"]})
        )

        def worker(w):
            # Odd workers append multi-page records: real review-feedback
            # runs to tens of KB, and page-crossing writes are the size
            # class where atomicity is not free.
            pad = "x" * 6000 if w % 2 else ""
            receipts = []
            for seq in range(self.APPENDS):
                record = {"type": "stress-rec", "worker": w, "seq": seq, "pad": pad}
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(_HERE / "handoff.py"),
                        "append",
                        "stress-rec",
                        "--file",
                        str(self.log),
                        "--schemas",
                        str(self.schemas),
                        "--layout",
                        str(self.layout),
                    ],
                    input=json.dumps(record),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                match = re.search(r"at line (\d+)", proc.stdout)
                self.assertIsNotNone(match, proc.stdout)
                receipts.append((w, seq, int(match.group(1))))
            return receipts

        with concurrent.futures.ThreadPoolExecutor(self.WORKERS) as pool:
            receipts = [
                r for chunk in pool.map(worker, range(self.WORKERS)) for r in chunk
            ]

        total = self.WORKERS * self.APPENDS
        lines = self.log_lines()
        self.assertEqual(len(lines), total, "every append lands exactly once")
        code, _, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(
            sorted(line_no for _, _, line_no in receipts),
            list(range(1, total + 1)),
            "receipts are a permutation of the physical lines",
        )
        for w, seq, line_no in receipts:
            record = json.loads(lines[line_no - 1])
            self.assertEqual(
                (record["worker"], record["seq"]),
                (w, seq),
                f"receipt line {line_no} names another writer's record",
            )


class TestBuildPassRunsPlanEngine(HandoffCase):
    """A build-pass append on the default ledger composes the review-plan
    engine (route-spec § Gate 5): the plan exists by construction, at the
    append's own tree state. Pins: the spawn and its argv, the fail-open
    contract (a failed engine warns, the append stays green), and the two
    non-trigger paths — a --file-redirected append (harness-internal by
    design; the skip announces itself on stderr) and every other record
    type. The trigger compares resolved paths, never spellings."""

    def setUp(self):
        super().setUp()
        (self.schemas / "build-pass.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type", "req_id"]})
        )
        (self.schemas / "prd-entry.schema.json").write_text(
            json.dumps({"type": "object", "required": ["type", "req_id"]})
        )
        # Point the CLI's default ledger into the fixture, so an append
        # without --file (the runtime shape) lands here, not in the repo.
        pin = unittest.mock.patch.object(entry, "DEFAULT_LOG", str(self.log))
        pin.start()
        self.addCleanup(pin.stop)

    def _append_default_file(self, rtype, spawn):
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=spawn
        ) as spawned:
            code, out, err = self.run_cli(
                "append",
                rtype,
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": rtype, "req_id": "REQ-XX-001"}),
            )
        return code, out, err, spawned

    def test_build_pass_on_the_default_ledger_spawns_the_engine(self):
        ok = subprocess.CompletedProcess(
            [], 0, stdout="review-plan: appended low plan for REQ-XX-001\n", stderr=""
        )
        code, out, err, spawned = self._append_default_file(
            "build-pass", lambda *a, **k: ok
        )
        self.assertEqual(0, code, err)
        spawned.assert_called_once()
        argv = spawned.call_args.args[0]
        self.assertEqual(sys.executable, argv[0])
        # -E -B: PYTHON* env never shapes the child's imports; no bytecode.
        self.assertEqual(["-E", "-B"], argv[1:3])
        self.assertTrue(argv[3].endswith("grading.py"))
        self.assertEqual(["review-plan", "--feature", "REQ-XX-001"], argv[4:])
        self.assertIn("review-plan: appended low plan", out)

    def test_a_failed_engine_leaves_the_append_green_and_warns(self):
        bad = subprocess.CompletedProcess([], 1, stdout="", stderr="boom\n")
        code, out, err, _ = self._append_default_file("build-pass", lambda *a, **k: bad)
        self.assertEqual(0, code)
        self.assertIn("appended build-pass", out)
        self.assertIn("falls back to the full battery", err)

    def test_an_engine_that_cannot_start_leaves_the_append_green(self):
        def raise_oserror(*a, **k):
            raise OSError("no interpreter")

        code, out, err, _ = self._append_default_file("build-pass", raise_oserror)
        self.assertEqual(0, code)
        self.assertIn("appended build-pass", out)
        self.assertIn("falls back to the full battery", err)

    def test_a_file_redirected_append_never_spawns(self):
        other = self.log.parent / "redirected.jsonl"
        with unittest.mock.patch.object(entry.subprocess, "run") as spawned:
            code, _, err = self.run_cli(
                "append",
                "build-pass",
                "--file",
                str(other),
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": "build-pass", "req_id": "REQ-XX-001"}),
            )
        self.assertEqual(0, code, err)
        spawned.assert_not_called()
        self.assertIn("redirected ledger", err)
        self.assertIn("falls back to the full battery", err)

    def test_an_equivalent_spelling_of_the_default_still_spawns(self):
        # `--file` naming the default ledger by another spelling is not a
        # redirect: string equality alone would silently skip the engine
        # on every such gate-pass — the exact skip class the composed
        # trigger exists to close.
        spelled = self.log.parent / "." / self.log.name
        ok = subprocess.CompletedProcess(
            [], 0, stdout="review-plan: appended low plan for REQ-XX-001\n", stderr=""
        )
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=lambda *a, **k: ok
        ) as spawned:
            code, _, err = self.run_cli(
                "append",
                "build-pass",
                "--file",
                str(spelled),
                "--schemas",
                str(self.schemas),
                stdin=json.dumps({"type": "build-pass", "req_id": "REQ-XX-001"}),
            )
        self.assertEqual(0, code, err)
        spawned.assert_called_once()

    def test_other_record_types_never_spawn(self):
        code, _, err, spawned = self._append_default_file(
            "prd-entry", unittest.mock.MagicMock()
        )
        self.assertEqual(0, code, err)
        spawned.assert_not_called()

    def test_an_unclean_req_id_never_reaches_argv(self):
        # The permissive fixture schema admits shapes the shipped pattern
        # rejects; the spawn's own fullmatch re-check must refuse them —
        # including the trailing newline a `$` pattern tolerates.
        for req in ("REQ-XX-001\n", "--evil", "REQ-XX-001 extra", 7):
            with self.subTest(req=req):
                with unittest.mock.patch.object(entry.subprocess, "run") as spawned:
                    code, out, err = self.run_cli(
                        "append",
                        "build-pass",
                        "--schemas",
                        str(self.schemas),
                        stdin=json.dumps({"type": "build-pass", "req_id": req}),
                    )
                self.assertEqual(0, code, err)
                self.assertIn("appended build-pass", out)
                spawned.assert_not_called()
                self.assertIn("falls back to the full battery", err)

    def test_engine_output_is_sanitized_before_echo(self):
        evil = subprocess.CompletedProcess(
            [], 0, stdout="review-plan: appended \x1b[31mlow\x1b[0m plan\n", stderr=""
        )
        code, out, _, _ = self._append_default_file("build-pass", lambda *a, **k: evil)
        self.assertEqual(0, code)
        self.assertNotIn("\x1b", out)
        bad = subprocess.CompletedProcess([], 1, stdout="", stderr="x\x1b]0;t\x07y\n")
        code, _, err, _ = self._append_default_file("build-pass", lambda *a, **k: bad)
        self.assertEqual(0, code)
        self.assertNotIn("\x1b", err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
