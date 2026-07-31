#!/usr/bin/env python3
"""Tests for accounting.py (stdlib only).

Run (from scripts/): python3 -m unittest tests.test_accounting

Covers the pricing table (family rates, the Sonnet 5 override precedence, an
unknown model priced at zero), the usage fold (token totals, list-price cost,
cache-hit and cache-savings percentages, the 5m/1h TTL fallback), timestamp
parsing, transcript reading under malformed input, session discovery, and the
window index the board queries — including whole-file attribution (a window
selects dispatches and sums each whole), the roll-up's deliberate
message-windowing, and the premise the whole model rests on: no two dispatches
of one agentType overlap in time.

All fixtures are synthetic: round token counts, invented agentTypes and session
ids. No real Claude Code transcript is read here.
"""

import importlib.util
import io
import json
import os
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent  # the scripts dir (tests live under it)


def _load():
    spec = importlib.util.spec_from_file_location("accounting", _HERE / "accounting.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load()


def usage(inp=0, out=0, read=0, cc5=None, cc1=None, flat=None):
    """A synthetic usage dict. When cc5/cc1 are given the TTL split is written;
    when only `flat` is given the pre-split cache_creation_input_tokens form is
    written (no cache_creation dict)."""
    u = {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read}
    if flat is not None:
        u["cache_creation_input_tokens"] = flat
    if cc5 is not None or cc1 is not None:
        c5, c1 = cc5 or 0, cc1 or 0
        u["cache_creation_input_tokens"] = c5 + c1
        u["cache_creation"] = {
            "ephemeral_5m_input_tokens": c5,
            "ephemeral_1h_input_tokens": c1,
        }
    return u


class TestPricing(unittest.TestCase):
    def test_family_rates(self):
        self.assertEqual(cc._rate("claude-opus-4-8"), (5.00, 25.00))
        self.assertEqual(cc._rate("claude-opus-5"), (5.00, 25.00))
        self.assertEqual(cc._rate("claude-sonnet-4-6"), (3.00, 15.00))
        self.assertEqual(cc._rate("claude-haiku-4-5"), (1.00, 5.00))
        self.assertEqual(cc._rate("claude-fable-5"), (10.00, 50.00))

    def test_display_name_casing(self):
        # Claude Code's display_name form ("Opus 4.8") must price like the id.
        self.assertEqual(cc._rate("Opus 4.8"), (5.00, 25.00))

    def test_sonnet5_override_beats_family(self):
        # sonnet-5 carries the intro rate; a plain sonnet does not.
        self.assertEqual(cc._rate("claude-sonnet-5-20260101"), (2.00, 10.00))
        self.assertEqual(cc._rate("claude-sonnet-4-6"), (3.00, 15.00))

    def test_unknown_model_prices_zero(self):
        # A new model surfaces as $0, never a wrong guess.
        self.assertEqual(cc._rate("gpt-9"), (0.0, 0.0))
        self.assertEqual(cc._rate(None), (0.0, 0.0))


class TestUsageFields(unittest.TestCase):
    def test_ttl_split_read_when_present(self):
        ci, co, cr, ccx, c5, c1 = cc._usage_fields(usage(read=10, cc5=400, cc1=100))
        self.assertEqual((c5, c1, ccx), (400, 100, 500))

    def test_flat_cache_creation_treated_as_5m(self):
        # No cache_creation dict: the flat total is a 5-minute write.
        _, _, _, ccx, c5, c1 = cc._usage_fields(usage(flat=700))
        self.assertEqual((c5, c1, ccx), (700, 0, 700))

    def test_missing_5m_key_derives_from_flat_minus_1h(self):
        # The 5m count is the flat total minus the 1h count — falling back to
        # the flat total would price the 1h tokens twice (once at 1.25x, once
        # at 2.0x) and double the write volume in the savings baseline.
        u = {
            "cache_creation_input_tokens": 700,
            "cache_creation": {"ephemeral_1h_input_tokens": 100},
        }
        _, _, _, ccx, c5, c1 = cc._usage_fields(u)
        self.assertEqual((c5, c1), (600, 100))
        self.assertEqual(c5 + c1, ccx)  # the documented invariant

    def test_absent_fields_default_zero(self):
        self.assertEqual(cc._usage_fields({}), (0, 0, 0, 0, 0, 0))

    def test_non_numeric_counts_read_as_zero(self):
        # A malformed transcript value (string, float, bool, negative) must
        # degrade to 0, never raise mid-render — accounting reads, it never
        # gates the consumer.
        u = {
            "input_tokens": "1200",
            "output_tokens": 3.5,
            "cache_read_input_tokens": True,
            "cache_creation_input_tokens": -5,
        }
        self.assertEqual(cc._usage_fields(u), (0, 0, 0, 0, 0, 0))
        t = cc.aggregate([("claude-opus-4-8", u)])  # must not raise
        self.assertEqual(t["cost"], 0.0)


class TestAggregate(unittest.TestCase):
    def test_single_opus_message_cost_and_percentages(self):
        # (1000*5 + 500*25 + 2000*5*.10 + 400*5*1.25 + 100*5*2.0)/1e6
        # = (5000 + 12500 + 1000 + 2500 + 1000)/1e6 = 0.022
        t = cc.aggregate(
            [("claude-opus-4-8", usage(inp=1000, out=500, read=2000, cc5=400, cc1=100))]
        )
        self.assertAlmostEqual(t["cost"], 0.022, places=9)
        self.assertEqual(t["total_input"], 3500)  # 1000 + 2000 + 500
        self.assertEqual(t["hit_pct"], 57)  # round(2000*100/3500)
        # base 2500, actual 200+500+200=900 -> round(1600*100/2500)=64
        self.assertEqual(t["savings_pct"], 64)

    def test_mixed_fleet_prices_per_row(self):
        # Opus row (0.022) + a no-cache Haiku row (1000*1 + 1000*5)/1e6 = 0.006.
        t = cc.aggregate(
            [
                (
                    "claude-opus-4-8",
                    usage(inp=1000, out=500, read=2000, cc5=400, cc1=100),
                ),
                ("claude-haiku-4-5", usage(inp=1000, out=1000)),
            ]
        )
        self.assertAlmostEqual(t["cost"], 0.028, places=9)
        self.assertEqual(t["output"], 1500)
        self.assertEqual(t["total_input"], 4500)  # +1000 plain input

    def test_no_cache_activity_savings_is_none(self):
        t = cc.aggregate([("claude-opus-4-8", usage(inp=100, out=100))])
        self.assertIsNone(t["savings_pct"])

    def test_hit_pct_zero_when_no_cache_read(self):
        t = cc.aggregate([("claude-opus-4-8", usage(inp=100, out=100))])
        self.assertEqual(t["hit_pct"], 0)

    def test_empty_rows(self):
        t = cc.aggregate([])
        self.assertEqual(t["cost"], 0.0)
        self.assertEqual(t["hit_pct"], 0)
        self.assertIsNone(t["savings_pct"])


class TestParseTs(unittest.TestCase):
    def test_zulu_and_offset_and_bare(self):
        a = cc.parse_ts("2026-07-06T10:00:00Z")
        b = cc.parse_ts("2026-07-06T10:00:00+00:00")
        d = cc.parse_ts("2026-07-06T10:00:00")  # bare -> UTC
        self.assertEqual(a, b)
        self.assertEqual(a, d)

    def test_ordering(self):
        self.assertLess(
            cc.parse_ts("2026-07-06T10:00:00Z"), cc.parse_ts("2026-07-06T10:05:00Z")
        )

    def test_invalid(self):
        self.assertIsNone(cc.parse_ts("not-a-time"))
        self.assertIsNone(cc.parse_ts(None))
        self.assertIsNone(cc.parse_ts(1234))


class TranscriptCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write_transcript(self, path, messages):
        """messages: list of (model, usage, ts) -> assistant lines, plus a
        stray user line and a blank line to prove they are skipped."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ['{"type":"user","message":{"role":"user"}}', ""]
        for model, u, ts in messages:
            lines.append(
                json.dumps(
                    {
                        "type": "assistant",
                        "timestamp": ts,
                        "message": {"model": model, "usage": u},
                    }
                )
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_meta(self, transcript, agent_type):
        meta = Path(str(transcript)[: -len(".jsonl")] + ".meta.json")
        payload = {} if agent_type is None else {"agentType": agent_type}
        meta.write_text(json.dumps(payload), encoding="utf-8")


class TestIterAssistant(TranscriptCase):
    def test_yields_only_assistant_with_usage(self):
        p = self.root / "t.jsonl"
        self.write_transcript(
            p, [("claude-opus-4-8", usage(inp=5), "2026-07-06T10:00:00Z")]
        )
        rows = list(cc.iter_assistant(p))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "claude-opus-4-8")

    def test_skips_malformed_lines(self):
        p = self.root / "t.jsonl"
        p.write_text(
            '{"type":"assistant"\nnot json\n'
            '{"type":"assistant","message":{"model":"claude-opus-4-8",'
            '"usage":{"input_tokens":7}},"timestamp":"2026-07-06T10:00:00Z"}\n',
            encoding="utf-8",
        )
        rows = list(cc.iter_assistant(p))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]["input_tokens"], 7)

    def test_missing_file_yields_nothing(self):
        self.assertEqual(list(cc.iter_assistant(self.root / "nope.jsonl")), [])


class TestSession(TranscriptCase):
    def test_discovers_parent_and_subagents(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(
            parent, [("claude-opus-4-8", usage(inp=10), "2026-07-06T10:00:00Z")]
        )
        sub = self.root / "sess" / "subagents"
        self.write_transcript(
            sub / "agent-a.jsonl",
            [("claude-haiku-4-5", usage(inp=20), "2026-07-06T10:01:00Z")],
        )
        # A non-agent file in the subagents dir is ignored.
        (sub / "notes.txt").write_text("x", encoding="utf-8")
        files = cc.session_transcripts(str(parent), "sess")
        self.assertEqual(len(files), 2)

    def test_session_totals_sums_tree(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(
            parent,
            [("claude-opus-4-8", usage(inp=1000, out=100), "2026-07-06T10:00:00Z")],
        )
        sub = self.root / "sess" / "subagents"
        self.write_transcript(
            sub / "agent-a.jsonl",
            [("claude-haiku-4-5", usage(inp=1000, out=1000), "2026-07-06T10:01:00Z")],
        )
        t = cc.session_totals(str(parent), "sess")
        # opus (1000*5+100*25)/1e6=0.0075 + haiku (1000+5000)/1e6=0.006
        self.assertAlmostEqual(t["cost"], 0.0135, places=9)
        self.assertEqual(t["input"], 2000)


class TestWindowIndex(TranscriptCase):
    SLUG = "-proj-x"

    def _agent(self, session, agent_id, agent_type, messages):
        sub = self.root / self.SLUG / session / "subagents"
        path = sub / f"agent-{agent_id}.jsonl"
        self.write_transcript(path, messages)
        self.write_meta(path, agent_type)
        return path

    def index(self):
        return cc.WindowIndex(projects_root=str(self.root), slug=self.SLUG)

    def test_window_attributes_by_type_and_time(self):
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000, out=500), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s1",
            "rev",
            "code-quality-reviewer",
            [("claude-opus-4-8", usage(inp=9999), "2026-07-06T10:05:30Z")],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        # (1000*5 + 500*25)/1e6 = 0.0175 — the reviewer's 9999 is excluded.
        self.assertAlmostEqual(t["cost"], 0.0175, places=9)
        self.assertEqual(t["output"], 500)

    def test_dispatch_overlapping_the_window_sums_whole_file(self):
        # The window bounds a step; the transcript bounds the dispatch. One
        # dispatch straddling the window's end attributes in full — summing
        # only the messages between the bounds is what undercounted a step.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z"),  # inside
                ("claude-opus-4-8", usage(inp=8000), "2026-07-06T11:00:00Z"),  # after
            ],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 9000)

    def test_dispatch_front_before_the_window_attributes(self):
        # The shape that motivated whole-file attribution: an agent's first
        # message (system prompt + context — its most expensive) lands before
        # its first tool call can append dispatch-start, so the window opens
        # mid-dispatch. That front is the step's cost, not nobody's.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=7000), "2026-07-06T10:04:00Z"),  # before
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:06:00Z"),  # inside
            ],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:05:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 8000)

    def test_dispatch_wholly_outside_the_window_excluded(self):
        # The exclusion that survives: a dispatch whose transcript lies wholly
        # outside the window belongs to another step and never attributes here.
        self._agent(
            "s1",
            "impl1",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s1",
            "impl2",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=8000), "2026-07-06T11:00:00Z")],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 1000)

    def test_retries_within_one_session_sum(self):
        # An implementer re-dispatched (a build retry) writes a second
        # transcript in the SAME session; the window total sums both.
        self._agent(
            "s1",
            "impl1",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s1",
            "impl2",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:08:00Z")],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 3000)

    def test_cross_session_window_sums(self):
        # A slice resumed in a later session: its dispatches live under two
        # session dirs. Sessions are sequential (two at once is outside the
        # harness's design space), so a file is its dispatch's whatever
        # session wrote it, and the window sums both rather than declining.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s2",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:06:00Z")],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 3000)

    def test_unparseable_stamp_still_counts_toward_its_file(self):
        # The file is the unit: once overlap selects a dispatch, a message it
        # could not place still belongs to it. Dropping the row here would
        # reinstate the undercount whole-file attribution exists to remove —
        # and a dispatch's costly first message is exactly what carries it.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=50000), None),  # unplaceable
                (
                    "claude-opus-4-8",
                    usage(inp=1000),
                    "2026-07-06T10:05:00Z",
                ),  # places the file
            ],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 51000)
        # rows stays the timestamped-message view: the unplaceable one is absent.
        self.assertEqual(len(idx.rows), 1)

    def test_file_with_no_placeable_stamp_is_dropped(self):
        # No parseable timestamp anywhere means no span, so no window can
        # select the file. Dropping it beats guessing where it belongs.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=9000), None)],
        )
        idx = self.index()
        self.assertIsNone(
            idx.totals(
                "feature-implementer",
                cc.parse_ts("2026-07-06T10:00:00Z"),
                cc.parse_ts("2026-07-06T10:10:00Z"),
            )
        )

    def test_slice_totals_aggregates_across_types(self):
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000, out=500), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s1",
            "rev",
            "code-quality-reviewer",
            [("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:06:00Z")],
        )
        idx = self.index()
        t = idx.slice_totals(
            ["feature-implementer", "code-quality-reviewer", "review-plan-engine"],
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        # Both types sum; the engine author has no transcript and adds nothing.
        self.assertEqual(t["input"], 3000)
        self.assertEqual(t["output"], 500)

    def test_slice_totals_counts_duplicate_types_once(self):
        # The caller passes the slice's raw author column — repeats are expected.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        t = idx.slice_totals(
            ["feature-implementer", "feature-implementer"],
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 1000)

    def test_slice_totals_stays_message_windowed(self):
        # The roll-up is deliberately NOT whole-file (see slice_totals): its
        # window bounds a SLICE, not a dispatch, so whole-file selection would
        # price a dispatch that also served a batched sibling on both boards.
        # The out-of-window message stays out, so the header prices a dispatch
        # by a different rule than the lines and the two do not reconcile.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z"),  # inside
                ("claude-opus-4-8", usage(inp=8000), "2026-07-06T11:00:00Z"),  # outside
            ],
        )
        idx = self.index()
        t = idx.slice_totals(
            ["feature-implementer"],
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 1000)
        # The same dispatch, priced as a STEP, does sum whole.
        s = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(s["input"], 9000)

    def test_slice_totals_cross_session_sums(self):
        # The roll-up's half of test_cross_session_window_sums: the retired
        # multi-session decline used to null this whole figure.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        self._agent(
            "s2",
            "impl2",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:06:00Z")],
        )
        self._agent(
            "s1",
            "rev",
            "code-quality-reviewer",
            [("claude-opus-4-8", usage(inp=100), "2026-07-06T10:07:00Z")],
        )
        idx = self.index()
        t = idx.slice_totals(
            ["feature-implementer", "code-quality-reviewer"],
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:10:00Z"),
        )
        self.assertEqual(t["input"], 3100)

    def test_slice_totals_nothing_matched_returns_none(self):
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        self.assertIsNone(
            idx.slice_totals(
                ["review-plan-engine"],
                cc.parse_ts("2026-07-06T10:00:00Z"),
                cc.parse_ts("2026-07-06T10:10:00Z"),
            )
        )
        self.assertIsNone(
            idx.slice_totals(
                [],
                cc.parse_ts("2026-07-06T10:00:00Z"),
                cc.parse_ts("2026-07-06T10:10:00Z"),
            )
        )
        self.assertIsNone(
            idx.slice_totals(
                ["feature-implementer"], None, cc.parse_ts("2026-07-06T10:10:00Z")
            )
        )

    def test_no_match_returns_none(self):
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        self.assertIsNone(
            idx.totals(
                "change-grader",
                cc.parse_ts("2026-07-06T10:00:00Z"),
                cc.parse_ts("2026-07-06T10:10:00Z"),
            )
        )

    def test_bad_window_returns_none(self):
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        self.assertIsNone(idx.totals("feature-implementer", None, 10.0))
        self.assertIsNone(idx.totals("feature-implementer", 10.0, 5.0))  # out of order

    def test_missing_agent_type_is_dropped(self):
        # A transcript whose meta has no agentType cannot be attributed.
        self._agent(
            "s1",
            "impl",
            None,
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        self.assertEqual(idx.rows, [])

    def test_missing_project_dir(self):
        idx = cc.WindowIndex(projects_root=str(self.root), slug="-nope")
        self.assertEqual(idx.rows, [])
        self.assertIsNone(idx.totals("feature-implementer", 0.0, 10.0))

    def test_since_secs_prunes_transcripts_older_than_the_window(self):
        # A transcript whose file mtime predates since_secs cannot hold
        # in-window messages (messages cannot postdate the last write) — it
        # is skipped unread, keeping the build proportional to recent
        # activity instead of the project's whole history.
        path = self._agent(
            "s1",
            "old",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        os.utime(path, (1000.0, 1000.0))
        idx = cc.WindowIndex(
            projects_root=str(self.root), slug=self.SLUG, since_secs=2000.0
        )
        self.assertEqual(idx.rows, [])
        # Without the bound the same transcript is indexed.
        self.assertEqual(len(self.index().rows), 1)

    def test_since_secs_keeps_a_dispatch_that_began_before_the_bound(self):
        # ADR 2026-07-15 calls this invariant load-bearing: the bound prunes on
        # mtime (the LAST write), so a dispatch that started before the
        # earliest window but ran into it survives with its front intact. A
        # refactor to prune on the first message would silently restore the
        # undercount whole-file attribution exists to remove, so pin it here.
        path = self._agent(
            "s1",
            "straddler",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=50000), "2026-07-06T09:55:00Z"),  # before
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z"),  # inside
            ],
        )
        start = cc.parse_ts("2026-07-06T10:00:00Z")
        last_write = cc.parse_ts("2026-07-06T10:05:00Z")
        os.utime(path, (last_write, last_write))
        idx = cc.WindowIndex(
            projects_root=str(self.root), slug=self.SLUG, since_secs=start
        )
        t = idx.totals(
            "feature-implementer", start, cc.parse_ts("2026-07-06T10:10:00Z")
        )
        self.assertEqual(t["input"], 51000)

    def test_concurrent_same_type_dispatches_double_count(self):
        # The premise whole-file attribution rests on, pinned by the case that
        # breaks it: two dispatches of ONE type overlapping in time. Every
        # window over either selects both, so each line prints their sum. The
        # pipeline fans out across DISTINCT types, so its boards never render
        # this — a property of the roster, not of this code. Pinned so a roster
        # that fans out two of one type fails here first, loudly, instead of
        # printing identical figures on every line.
        self._agent(
            "s1",
            "rev1",
            "doc-reviewer",
            [
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z"),
                ("claude-opus-4-8", usage(inp=1), "2026-07-06T10:07:00Z"),
            ],
        )
        self._agent(
            "s1",
            "rev2",
            "doc-reviewer",
            [
                ("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:06:00Z"),
                ("claude-opus-4-8", usage(inp=2), "2026-07-06T10:08:00Z"),
            ],
        )
        idx = self.index()
        # rev1's own window (10:05 → its record) returns BOTH dispatches.
        t = idx.totals(
            "doc-reviewer",
            cc.parse_ts("2026-07-06T10:05:00Z"),
            cc.parse_ts("2026-07-06T10:07:00Z"),
        )
        self.assertEqual(t["input"], 3003)
        # ...and so does rev2's. Both lines print the same figure — the two
        # dispatches are unrankable, not merely mispriced.
        t2 = idx.totals(
            "doc-reviewer",
            cc.parse_ts("2026-07-06T10:06:00Z"),
            cc.parse_ts("2026-07-06T10:08:00Z"),
        )
        self.assertEqual(t2["input"], 3003)

    def test_window_touching_the_span_edge_selects_the_file(self):
        # Overlap is closed at both ends: a window ending exactly at the file's
        # first message still names that dispatch. One second earlier does not.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:05:00Z")],
        )
        idx = self.index()
        t = idx.totals(
            "feature-implementer",
            cc.parse_ts("2026-07-06T10:00:00Z"),
            cc.parse_ts("2026-07-06T10:05:00Z"),
        )
        self.assertEqual(t["input"], 1000)
        self.assertIsNone(
            idx.totals(
                "feature-implementer",
                cc.parse_ts("2026-07-06T10:00:00Z"),
                cc.parse_ts("2026-07-06T10:04:59Z"),
            )
        )

    def test_zero_width_window_inside_a_span_selects_the_file(self):
        # A step whose dispatch-start and record share a timestamp still prices:
        # the window is a point, and a point inside the span overlaps it.
        self._agent(
            "s1",
            "impl",
            "feature-implementer",
            [
                ("claude-opus-4-8", usage(inp=1000), "2026-07-06T10:00:00Z"),
                ("claude-opus-4-8", usage(inp=2000), "2026-07-06T10:10:00Z"),
            ],
        )
        idx = self.index()
        at = cc.parse_ts("2026-07-06T10:05:00Z")
        t = idx.totals("feature-implementer", at, at)
        self.assertEqual(t["input"], 3000)

    def test_projects_root_env_override(self):
        # default_projects_root honors CLAUDE_PROJECTS_ROOT (the seam the board
        # tests use to stay hermetic and non-default configs use to relocate).
        with unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": "/some/where/projects"}
        ):
            self.assertEqual(cc.default_projects_root(), "/some/where/projects")


class TestSlugAndFormat(unittest.TestCase):
    def test_slug_encoding(self):
        self.assertEqual(
            cc.slug_for("/home/user/work/my-project"), "-home-user-work-my-project"
        )

    def test_format_tokens(self):
        self.assertEqual(cc.format_tokens(567), "567")
        self.assertEqual(cc.format_tokens(34000), "34k")
        self.assertEqual(cc.format_tokens(1_200_000), "1.2M")

    def test_format_cost(self):
        self.assertEqual(cc.format_cost(1.7138), "1.71")
        self.assertEqual(cc.format_cost(0), "0.00")


class TestCli(TranscriptCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cc._main(argv)
        return rc, json.loads(buf.getvalue())

    def test_session_cli_emits_json(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(
            parent,
            [("claude-opus-4-8", usage(inp=1000, out=100), "2026-07-06T10:00:00Z")],
        )
        rc, out = self._run(
            ["session", "--parent", str(parent), "--session-id", "sess"]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out["input"], 1000)
        self.assertIn("cost", out)

    def test_window_cli_emits_null_on_no_match(self):
        # --cwd derives the slug (its leading '/' keeps argparse from reading
        # the value as a flag, unlike a bare --slug beginning with '-').
        rc, out = self._run(
            [
                "window",
                "--agent-type",
                "feature-implementer",
                "--start",
                "2026-07-06T10:00:00Z",
                "--end",
                "2026-07-06T10:10:00Z",
                "--projects-root",
                str(self.root),
                "--cwd",
                "/no/such/project",
            ]
        )
        self.assertEqual(rc, 0)
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
