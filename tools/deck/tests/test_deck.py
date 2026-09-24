#!/usr/bin/env python3
"""Tests for deck: the ledger replay's shape, the script escape, and the drift check over the casts bundle and the slide figures."""

import json
import pathlib
import tempfile
import unittest

import deck as d
import figures

INTAKE = {
    "type": "intake-decision",
    "ts": "2026-08-15T20:22:16+00:00",
    "author": "human",
    "request": "Bug report: page zero renders the error page.",
}
PRD = {
    "type": "prd-entry",
    "ts": "2026-08-15T20:24:51+00:00",
    "author": "product-requirements-expert",
    "title": "Owner listing treats a page below the first as the first page",
}
CATCH = {
    "type": "review-feedback",
    "ts": "2026-08-15T20:34:10+00:00",
    "author": "doc-reviewer",
    "verdict": "changes_requested",
    "findings": [
        {
            "tag": "blocked",
            "location": "docs/prd.md:79",
            "description": "Edge case 5 contradicts edge case 4.",
        }
    ],
}
APPROVAL = {**CATCH, "verdict": "approved", "findings": []}
# A timestamp an hour after the previous record: far past the replay's cap.
LONG_AFTER = {**PRD, "ts": "2026-08-15T21:24:51+00:00"}
LONG_DETAIL = {**INTAKE, "request": "word " * 400}


def cast_events(text):
    lines = text.splitlines()
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]


class LedgerCast(unittest.TestCase):
    def test_the_header_names_the_source_and_the_terminal_size(self):
        header, _ = cast_events(d.ledger_cast([INTAKE], "runs/x"))
        self.assertEqual(header["version"], 2)
        self.assertEqual((header["width"], header["height"]), (d.COLS, d.ROWS))
        self.assertIn("runs/x", header["title"])

    def test_event_times_never_run_backwards(self):
        _, events = cast_events(d.ledger_cast([INTAKE, PRD, CATCH, APPROVAL], "runs/x"))
        times = [event[0] for event in events]
        self.assertEqual(times, sorted(times))

    def test_stage_records_and_a_blocking_review_become_markers_and_an_approval_does_not(
        self,
    ):
        _, events = cast_events(d.ledger_cast([INTAKE, PRD, CATCH, APPROVAL], "runs/x"))
        self.assertEqual(
            [e[2] for e in events if e[1] == "m"], ["requirements", "review catch"]
        )

    def test_a_long_real_gap_plays_back_capped(self):
        _, events = cast_events(d.ledger_cast([PRD, LONG_AFTER], "runs/x"))
        outputs = [e[0] for e in events if e[1] == "o"]
        self.assertLessEqual(outputs[2] - outputs[1], d.RECORD_BEAT + d.MAX_GAP)

    def test_a_long_detail_is_cut_to_its_line_budget(self):
        lines = d.record_lines(LONG_DETAIL)
        self.assertEqual(len(lines), 1 + d.DETAIL_LINES)
        self.assertTrue(lines[-1].endswith("…"))

    def test_the_first_finding_of_a_review_shows_under_its_heading(self):
        lines = d.record_lines(CATCH)
        self.assertIn("changes_requested", lines[0])
        self.assertIn("docs/prd.md:79", " ".join(lines[1:]))


class ScriptSafe(unittest.TestCase):
    def test_a_closing_script_tag_is_escaped_in_any_case(self):
        self.assertEqual(
            d._script_safe("a</script>b</SCRIPT>"), "a<\\/script>b<\\/SCRIPT>"
        )

    def test_other_closing_tags_pass_through(self):
        self.assertEqual(d._script_safe("</div>"), "</div>")

    def test_casts_js_embeds_a_cast_holding_a_closing_script_tag_safely(self):
        text = d.casts_js({"x": "</script>"})
        self.assertNotIn("</script>", text)
        self.assertTrue(text.startswith("// Generated"))


class Build(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.deck = pathlib.Path(self.tmp.name) / "deck"
        (self.deck / "casts").mkdir(parents=True)
        (self.deck / "casts" / "demo.cast").write_text('{"version": 2}\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_check_lists_every_missing_derived_file_and_writes_nothing(self):
        stale = d.build(self.deck, check=True)
        images = self.deck.parent / "images"
        self.assertEqual(
            set(stale),
            {
                self.deck / "casts" / "casts.js",
                images / "pipeline-slide-memory.drawio",
                images / "pipeline-slide-routing.drawio",
            },
        )
        self.assertFalse((self.deck / "casts" / "casts.js").exists())
        self.assertFalse((self.deck.parent / "images").exists())

    def test_a_build_leaves_nothing_stale(self):
        d.build(self.deck, check=False)
        self.assertEqual(d.build(self.deck, check=True), [])

    def test_an_edited_cast_makes_the_bundle_stale(self):
        d.build(self.deck, check=False)
        (self.deck / "casts" / "demo.cast").write_text(
            '{"version": 2, "title": "new"}\n'
        )
        self.assertEqual(
            d.build(self.deck, check=True), [self.deck / "casts" / "casts.js"]
        )

    def test_a_build_writes_the_figures_beside_the_deck_under_images(self):
        d.build(self.deck, check=False)
        sources = sorted((self.deck.parent / "images").glob("*.drawio"))
        self.assertEqual(len(sources), len(figures.FIGURES))
        self.assertTrue(all("<mxGraphModel" in s.read_text() for s in sources))

    def test_a_hand_edited_figure_source_is_listed_stale(self):
        d.build(self.deck, check=False)
        source = sorted((self.deck.parent / "images").glob("*.drawio"))[0]
        source.write_text(source.read_text() + "\n")
        self.assertEqual(d.build(self.deck, check=True), [source])

    def test_the_committed_tree_carries_no_stale_derived_file(self):
        self.assertEqual(d.build(d.DECK, check=True), [])

    def test_the_bundle_holds_every_cast_by_name(self):
        d.build(self.deck, check=False)
        text = (self.deck / "casts" / "casts.js").read_text()
        self.assertIn('"demo":', text)


if __name__ == "__main__":
    unittest.main()
