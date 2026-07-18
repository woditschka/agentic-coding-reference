#!/usr/bin/env python3
"""Tests for helpers.read_harness_layout (stdlib only).

Run: python3 harness/test_helpers.py

Covers:
  1. Grammar parity — the battery gate ADR 2026-07-18 names: the producer
     reader accepts exactly what the doctor's tomllib parse accepts, pinned
     on the multi-line-array fixture that split the two pre-reader grammars
     (init's regex returned [], materialize's comma-split errored).
  2. Fail-loud validation — unknown tools, malformed or unsafe extensions,
     and an unreadable file each raise LayoutError with a clean message;
     no silent default, no traceback.
  3. The unsafe_extension_path predicate shared with record_extension.
"""

import importlib.util
import os
import tempfile
import tomllib
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


helpers = _load("helpers", _HERE / "helpers.py")


def _target_with_layout(td, text):
    target = Path(td)
    (target / "scripts").mkdir()
    (target / "scripts" / "layout.toml").write_text(text, encoding="utf-8")
    return target


MULTILINE = """\
[harness]
channel = "manifest"
tools = [
  "claude",
  "copilot",  # a trailing comment tomllib accepts
]
extensions = [
  "scripts/deploy.sh",
  "docs/runbook.md",
]
"""


class TestReaderGrammarParity(unittest.TestCase):
    """The reader's grammar is the doctor's grammar: both are tomllib. Each
    fixture is parsed twice — raw tomllib (what the doctor accepts) and
    read_harness_layout — and the [harness] fields must agree."""

    def _assert_parity(self, text):
        expected = tomllib.loads(text).get("harness", {})
        with tempfile.TemporaryDirectory() as td:
            layout = helpers.read_harness_layout(_target_with_layout(td, text))
        self.assertEqual(layout.channel, expected.get("channel", "copy"))
        self.assertEqual(layout.tools, expected.get("tools"))
        self.assertEqual(list(layout.extensions), expected.get("extensions", []))

    def test_multiline_arrays_match_doctor_grammar(self):
        # The motivating divergence: init's old regex read this as [],
        # materialize's old comma-split errored. tomllib accepts it.
        self._assert_parity(MULTILINE)

    def test_single_line_layout_matches_doctor_grammar(self):
        self._assert_parity(
            '[harness]\nchannel = "copy"\ntools = ["claude"]\nextensions = []\n'
        )

    def test_missing_file_is_greenfield_default(self):
        with tempfile.TemporaryDirectory() as td:
            layout = helpers.read_harness_layout(td)
        self.assertEqual(
            (layout.channel, layout.channel_declared, layout.tools, layout.extensions),
            ("copy", False, None, ()),
        )

    def test_empty_channel_defaults_but_is_not_declared(self):
        with tempfile.TemporaryDirectory() as td:
            layout = helpers.read_harness_layout(
                _target_with_layout(td, '[harness]\nchannel = ""\n')
            )
        self.assertEqual(layout.channel, "copy")
        self.assertFalse(layout.channel_declared)


class TestReaderFailsLoud(unittest.TestCase):
    """Every rejected declaration raises LayoutError — never a silent default
    (a swallowed declaration would install the wrong surfaces)."""

    def _err(self, text):
        with (
            tempfile.TemporaryDirectory() as td,
            self.assertRaises(helpers.LayoutError) as ctx,
        ):
            helpers.read_harness_layout(_target_with_layout(td, text))
        return str(ctx.exception)

    def test_unknown_tool_fails_loud(self):
        msg = self._err('[harness]\ntools = ["claude", "bogus-tool"]\n')
        self.assertIn("unknown tool(s) bogus-tool", msg)

    def test_non_string_extension_entry_fails_loud(self):
        msg = self._err("[harness]\nextensions = [123]\n")
        self.assertIn("extensions must be a list of strings", msg)

    def test_control_character_extension_rejected_and_repr_escaped(self):
        # tomllib decodes  into a real ESC byte; the reader must reject
        # it AND keep the byte out of its own error message (terminal safety).
        msg = self._err('[harness]\nextensions = ["\\u001b[2Jpwned"]\n')
        self.assertIn("unsafe characters", msg)
        self.assertNotIn("\x1b", msg)

    def test_traversing_extension_rejected(self):
        msg = self._err('[harness]\nextensions = ["../outside"]\n')
        self.assertIn("unsafe characters", msg)

    @unittest.skipIf(os.geteuid() == 0, "root reads through chmod 000")
    def test_unreadable_file_reports_cleanly(self):
        with tempfile.TemporaryDirectory() as td:
            target = _target_with_layout(td, '[harness]\nchannel = "copy"\n')
            lt = target / "scripts" / "layout.toml"
            lt.chmod(0o000)
            try:
                with self.assertRaises(helpers.LayoutError) as ctx:
                    helpers.read_harness_layout(target)
            finally:
                lt.chmod(0o644)
        self.assertIn("unreadable", str(ctx.exception))


class TestUnsafeExtensionPath(unittest.TestCase):
    def test_plain_relative_paths_pass(self):
        for ok in ("scripts/deploy.sh", ".claude/skills/mine", "docs/x.md"):
            self.assertFalse(helpers.unsafe_extension_path(ok), ok)

    def test_unsafe_paths_rejected(self):
        bad = ["", ".", "a,b", 'a"b', "a\\b", " padded ", "a\x1bb", "../up", "/abs"]
        for p in bad:
            self.assertTrue(helpers.unsafe_extension_path(p), repr(p))


if __name__ == "__main__":
    unittest.main()
