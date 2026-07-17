#!/usr/bin/env python3
"""Byte-contract suite: strict parse, the draft-07 subset validator,
patternFrom, and duplicate-key rejection — handoff_schema, exercised through
the CLI entry point."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_handoff import (
    _REPO_SCHEMAS,
    TS,
    HandoffCase,
    handoff,
)


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
                    [
                        "append",
                        "dispatch-start",
                        "--file",
                        str(log),
                        "--schemas",
                        str(_REPO_SCHEMAS),
                    ]
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
                    [
                        "append",
                        "dispatch-start",
                        "--file",
                        str(log),
                        "--schemas",
                        str(_REPO_SCHEMAS),
                    ]
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
            "append",
            "pf-rec",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
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


class TestDuplicateKeyRejection(unittest.TestCase):
    """loads_strict rejects duplicate object keys at any depth (ADR 2026-07-17
    strict-parsing hardening). The last-wins default would hide an ambiguous
    record; fail closed instead and name the offending key."""

    def test_top_level_duplicate_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            handoff.loads_strict('{"req_id": "REQ-A-001", "req_id": "REQ-A-002"}')
        self.assertIn('duplicate key: "req_id"', str(ctx.exception))

    def test_nested_duplicate_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            handoff.loads_strict('{"features": {"hunks": 1, "hunks": 2}}')
        self.assertIn('duplicate key: "hunks"', str(ctx.exception))

    def test_duplicate_inside_array_element_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            handoff.loads_strict('{"findings": [{"tag": "blocked", "tag": "autofix"}]}')
        self.assertIn('duplicate key: "tag"', str(ctx.exception))

    def test_valid_log_line_still_parses(self):
        # Regression: distinct keys, including nested ones, are unaffected.
        line = (
            '{"type": "build-pass", "req_id": "REQ-A-001", "nested": {"x": 1, "y": 2}}'
        )
        self.assertEqual(
            handoff.loads_strict(line),
            {"type": "build-pass", "req_id": "REQ-A-001", "nested": {"x": 1, "y": 2}},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
