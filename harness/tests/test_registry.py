#!/usr/bin/env python3
"""Pin registry.read_harness_layout: tomllib grammar parity and fail-loud validation."""

import os
import tempfile
import tomllib
import unittest
from pathlib import Path

from _loader import load

registry = load("registry", "registry.py")

DEFAULT_CHANNEL = "copy"
UNREADABLE_MODE = 0o000
READABLE_MODE = 0o644

MULTILINE_ARRAY_LAYOUT = """\
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
SINGLE_LINE_LAYOUT = (
    '[harness]\nchannel = "copy"\ntools = ["claude"]\nextensions = []\n'
)
EMPTY_CHANNEL_LAYOUT = '[harness]\nchannel = ""\n'
UNKNOWN_TOOL_LAYOUT = '[harness]\ntools = ["claude", "bogus-tool"]\n'
NON_STRING_EXTENSION_LAYOUT = "[harness]\nextensions = [123]\n"
CONTROL_CHARACTER_EXTENSION_LAYOUT = '[harness]\nextensions = ["\\u001b[2Jpwned"]\n'
TRAVERSING_EXTENSION_LAYOUT = '[harness]\nextensions = ["../outside"]\n'


def _target_with_layout(td, text):
    target = Path(td)
    (target / "scripts").mkdir()
    (target / "scripts" / "layout.toml").write_text(text, encoding="utf-8")
    return target


class ReaderGrammarParity(unittest.TestCase):
    """The reader accepts exactly what a raw tomllib parse of the same text accepts."""

    def _assert_parity(self, text):
        expected = tomllib.loads(text).get("harness", {})
        with tempfile.TemporaryDirectory() as td:
            layout = registry.read_harness_layout(_target_with_layout(td, text))
        self.assertEqual(layout.channel, expected.get("channel", DEFAULT_CHANNEL))
        self.assertEqual(layout.tools, expected.get("tools"))
        self.assertEqual(list(layout.extensions), expected.get("extensions", []))

    def test_multiline_arrays_match_the_doctor_grammar(self):
        self._assert_parity(MULTILINE_ARRAY_LAYOUT)

    def test_a_single_line_layout_matches_the_doctor_grammar(self):
        self._assert_parity(SINGLE_LINE_LAYOUT)

    def test_a_missing_file_reads_as_the_greenfield_default(self):
        with tempfile.TemporaryDirectory() as td:
            layout = registry.read_harness_layout(td)
        self.assertEqual(
            (layout.channel, layout.channel_declared, layout.tools, layout.extensions),
            (DEFAULT_CHANNEL, False, None, ()),
        )

    def test_an_empty_channel_takes_the_default_without_counting_as_declared(self):
        with tempfile.TemporaryDirectory() as td:
            layout = registry.read_harness_layout(
                _target_with_layout(td, EMPTY_CHANNEL_LAYOUT)
            )
        self.assertEqual(layout.channel, DEFAULT_CHANNEL)
        self.assertFalse(layout.channel_declared)


class ReaderFailsLoud(unittest.TestCase):
    """Every rejected declaration raises LayoutError instead of a silent default."""

    def _err(self, text):
        with (
            tempfile.TemporaryDirectory() as td,
            self.assertRaises(registry.LayoutError) as ctx,
        ):
            registry.read_harness_layout(_target_with_layout(td, text))
        return str(ctx.exception)

    def test_an_unknown_tool_is_named_in_the_error(self):
        msg = self._err(UNKNOWN_TOOL_LAYOUT)
        self.assertIn("unknown tool(s) bogus-tool", msg)

    def test_a_non_string_extension_entry_is_rejected(self):
        msg = self._err(NON_STRING_EXTENSION_LAYOUT)
        self.assertIn("extensions must be a list of strings", msg)

    def test_a_control_character_extension_is_rejected_and_kept_out_of_the_message(
        self,
    ):
        msg = self._err(CONTROL_CHARACTER_EXTENSION_LAYOUT)
        self.assertIn("unsafe characters", msg)
        self.assertNotIn("\x1b", msg)

    def test_a_traversing_extension_is_rejected(self):
        msg = self._err(TRAVERSING_EXTENSION_LAYOUT)
        self.assertIn("unsafe characters", msg)

    @unittest.skipIf(os.geteuid() == 0, "root reads through chmod 000")
    def test_an_unreadable_file_reports_unreadable(self):
        with tempfile.TemporaryDirectory() as td:
            target = _target_with_layout(td, SINGLE_LINE_LAYOUT)
            lt = target / "scripts" / "layout.toml"
            lt.chmod(UNREADABLE_MODE)
            try:
                with self.assertRaises(registry.LayoutError) as ctx:
                    registry.read_harness_layout(target)
            finally:
                lt.chmod(READABLE_MODE)
        self.assertIn("unreadable", str(ctx.exception))


class UnsafeExtensionPath(unittest.TestCase):
    def test_plain_relative_paths_are_safe(self):
        for ok in ("scripts/deploy.sh", ".claude/skills/mine", "docs/x.md"):
            self.assertFalse(registry.unsafe_extension_path(ok), ok)

    def test_empty_separator_padded_control_traversing_and_absolute_paths_are_unsafe(
        self,
    ):
        bad = ["", ".", "a,b", 'a"b', "a\\b", " padded ", "a\x1bb", "../up", "/abs"]
        for p in bad:
            self.assertTrue(registry.unsafe_extension_path(p), repr(p))


if __name__ == "__main__":
    unittest.main()
