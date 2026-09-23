#!/usr/bin/env python3
"""The accounting module over synthetic transcripts: pricing, the usage fold, and the window index."""

import importlib.util
import io
import json
import os
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("accounting", _HERE / "accounting.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load()

OPUS = "claude-opus-4-8"
OPUS_5 = "claude-opus-5"
OPUS_5_5 = "claude-opus-5-5"
OPUS_5_5_DISPLAY_NAME = "Opus 5.5"
OPUS_DISPLAY_NAME = "Opus 4.8"
SONNET = "claude-sonnet-4-6"
SONNET_5 = "claude-sonnet-5-20260101"
SONNET_5_DISPLAY_NAME = "Sonnet 5"
HAIKU = "claude-haiku-4-5"
FABLE = "claude-fable-5"
FABLE_5_1 = "claude-fable-5-1"
FABLE_5_1_DISPLAY_NAME = "Fable 5.1"
MYTHOS_5_1 = "claude-mythos-5-1"
AN_UNKNOWN_MODEL = "gpt-9"

# The published list prices ($ per million input, output tokens) and cache
# multipliers, pinned here independently of the production table.
OPUS_RATE = (5.00, 25.00)
SONNET_RATE = (3.00, 15.00)
HAIKU_RATE = (1.00, 5.00)
FABLE_RATE = (10.00, 50.00)
SONNET_5_RATE = (2.00, 10.00)
OPUS_5_5_RATE = (4.00, 20.00)
NO_RATE = (0.0, 0.0)
CACHE_READ_MULT = 0.10
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00
FABLE_5_1_READ_MULT = 0.025
OPUS_5_5_READ_MULT = 0.05
MTOK = 1_000_000
PERCENT = 100
COST_PLACES = 9

INPUT_TOKENS = 1000
OUTPUT_TOKENS = 500
CACHE_READ_TOKENS = 2000
WRITE_5M_TOKENS = 400
WRITE_1H_TOKENS = 100
FLAT_WRITE_TOKENS = 700
SOME_TOKENS = 100

IMPLEMENTER = "feature-implementer"
IMPLEMENTER_VARIANT = IMPLEMENTER + cc.VARIANT_SUFFIX
REVIEWER = "code-quality-reviewer"
DOC_REVIEWER = "doc-reviewer"
AN_UNDISPATCHED_TYPE = "review-plan-engine"
SOME_SESSION = "s1"
A_LATER_SESSION = "s2"
SOME_TS = "2026-07-06T10:00:00Z"
A_LATER_TS = "2026-07-06T10:05:00Z"
A_NON_STRING = 1234

WINDOW_START = "2026-07-06T10:00:00Z"
WINDOW_END = "2026-07-06T10:10:00Z"
INSIDE_WINDOW = "2026-07-06T10:05:00Z"
ALSO_INSIDE_WINDOW = "2026-07-06T10:06:00Z"
BEFORE_WINDOW = "2026-07-06T09:55:00Z"
AFTER_WINDOW = "2026-07-06T11:00:00Z"
INSIDE_INPUT = 1000
OTHER_INSIDE_INPUT = 2000
OUTSIDE_INPUT = 8000
UNPLACEABLE_INPUT = 50000
STALE_MTIME = 1000.0


def a_usage(inp=0, out=0, read=0, **cache):
    """A synthetic usage dict; cc5 and cc1 write the TTL split, flat writes the pre-split form."""
    assert set(cache) <= {"cc5", "cc1", "flat"}, cache
    cc5, cc1, flat = cache.get("cc5"), cache.get("cc1"), cache.get("flat")
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


def a_mixed_opus_usage():
    return a_usage(
        inp=INPUT_TOKENS,
        out=OUTPUT_TOKENS,
        read=CACHE_READ_TOKENS,
        cc5=WRITE_5M_TOKENS,
        cc1=WRITE_1H_TOKENS,
    )


def mixed_opus_cost():
    input_rate, output_rate = OPUS_RATE
    return (
        INPUT_TOKENS * input_rate
        + OUTPUT_TOKENS * output_rate
        + CACHE_READ_TOKENS * input_rate * CACHE_READ_MULT
        + WRITE_5M_TOKENS * input_rate * CACHE_WRITE_5M_MULT
        + WRITE_1H_TOKENS * input_rate * CACHE_WRITE_1H_MULT
    ) / MTOK


def plain_cost(rate, inp, out):
    input_rate, output_rate = rate
    return (inp * input_rate + out * output_rate) / MTOK


def savings_pct(base, actual):
    return round((base - actual) * PERCENT / base)


class Pricing(unittest.TestCase):
    def test_the_table_carries_the_published_rates_and_multipliers(self):
        self.assertEqual(
            cc.PRICE,
            {
                "fable": FABLE_RATE,
                "opus": OPUS_RATE,
                "sonnet": SONNET_RATE,
                "haiku": HAIKU_RATE,
            },
        )
        self.assertEqual(
            {needle: rate for needles, rate in cc.PRICE_OVERRIDE for needle in needles},
            {
                "sonnet-5": SONNET_5_RATE,
                "sonnet 5": SONNET_5_RATE,
                "opus-5-5": OPUS_5_5_RATE,
                "opus 5.5": OPUS_5_5_RATE,
            },
        )
        self.assertEqual(cc.CACHE_READ_MULT, CACHE_READ_MULT)
        self.assertEqual(cc.CACHE_WRITE_5M_MULT, CACHE_WRITE_5M_MULT)
        self.assertEqual(cc.CACHE_WRITE_1H_MULT, CACHE_WRITE_1H_MULT)
        self.assertEqual(
            {
                needle: mult
                for needles, mult in cc.CACHE_READ_MULT_OVERRIDE
                for needle in needles
            },
            {
                "fable-5-1": FABLE_5_1_READ_MULT,
                "fable 5.1": FABLE_5_1_READ_MULT,
                "mythos-5-1": FABLE_5_1_READ_MULT,
                "mythos 5.1": FABLE_5_1_READ_MULT,
                "opus-5-5": OPUS_5_5_READ_MULT,
                "opus 5.5": OPUS_5_5_READ_MULT,
            },
        )
        self.assertEqual(cc.TOKENS_PER_MILLION, MTOK)

    def test_each_family_prices_at_its_rate(self):
        self.assertEqual(cc._rate(OPUS), OPUS_RATE)
        self.assertEqual(cc._rate(OPUS_5), OPUS_RATE)
        self.assertEqual(cc._rate(SONNET), SONNET_RATE)
        self.assertEqual(cc._rate(HAIKU), HAIKU_RATE)
        self.assertEqual(cc._rate(FABLE), FABLE_RATE)
        self.assertEqual(cc._rate(FABLE_5_1), FABLE_RATE)

    def test_a_display_name_prices_like_its_id(self):
        self.assertEqual(cc._rate(OPUS_DISPLAY_NAME), OPUS_RATE)

    def test_sonnet5_override_beats_family(self):
        self.assertEqual(cc._rate(SONNET_5), SONNET_5_RATE)
        self.assertEqual(cc._rate(SONNET_5_DISPLAY_NAME), SONNET_5_RATE)
        self.assertEqual(cc._rate(SONNET), SONNET_RATE)

    def test_opus_5_5_override_beats_family(self):
        self.assertEqual(cc._rate(OPUS_5_5), OPUS_5_5_RATE)
        self.assertEqual(cc._rate(OPUS_5_5_DISPLAY_NAME), OPUS_5_5_RATE)
        self.assertEqual(cc._rate(OPUS_5), OPUS_RATE)

    def test_unknown_model_prices_zero(self):
        self.assertEqual(cc._rate(AN_UNKNOWN_MODEL), NO_RATE)
        self.assertEqual(cc._rate(None), NO_RATE)


class CacheReadMultiplier(unittest.TestCase):
    def test_standard_models_read_at_flat_mult(self):
        self.assertEqual(cc._read_mult(FABLE), CACHE_READ_MULT)
        self.assertEqual(cc._read_mult(OPUS_5), CACHE_READ_MULT)
        self.assertEqual(cc._read_mult(None), CACHE_READ_MULT)

    def test_fable_5_1_reads_at_its_override_by_id_and_display_name(self):
        self.assertEqual(cc._read_mult(FABLE_5_1), FABLE_5_1_READ_MULT)
        self.assertEqual(cc._read_mult(FABLE_5_1_DISPLAY_NAME), FABLE_5_1_READ_MULT)
        self.assertEqual(cc._read_mult(MYTHOS_5_1), FABLE_5_1_READ_MULT)

    def test_opus_5_5_reads_at_its_override_by_id_and_display_name(self):
        self.assertEqual(cc._read_mult(OPUS_5_5), OPUS_5_5_READ_MULT)
        self.assertEqual(cc._read_mult(OPUS_5_5_DISPLAY_NAME), OPUS_5_5_READ_MULT)


class UsageFields(unittest.TestCase):
    def test_ttl_split_read_when_present(self):
        _, _, _, ccx, c5, c1 = cc._usage_fields(
            a_usage(read=SOME_TOKENS, cc5=WRITE_5M_TOKENS, cc1=WRITE_1H_TOKENS)
        )
        self.assertEqual(
            (c5, c1, ccx),
            (WRITE_5M_TOKENS, WRITE_1H_TOKENS, WRITE_5M_TOKENS + WRITE_1H_TOKENS),
        )

    def test_flat_cache_creation_treated_as_5m(self):
        _, _, _, ccx, c5, c1 = cc._usage_fields(a_usage(flat=FLAT_WRITE_TOKENS))
        self.assertEqual((c5, c1, ccx), (FLAT_WRITE_TOKENS, 0, FLAT_WRITE_TOKENS))

    def test_missing_5m_key_derives_from_flat_minus_1h(self):
        # Falling back to the flat total would price the 1h tokens twice and
        # double the write volume in the savings baseline.
        u = {
            "cache_creation_input_tokens": FLAT_WRITE_TOKENS,
            "cache_creation": {"ephemeral_1h_input_tokens": WRITE_1H_TOKENS},
        }
        _, _, _, ccx, c5, c1 = cc._usage_fields(u)
        self.assertEqual(
            (c5, c1), (FLAT_WRITE_TOKENS - WRITE_1H_TOKENS, WRITE_1H_TOKENS)
        )
        self.assertEqual(c5 + c1, ccx)

    def test_absent_fields_default_zero(self):
        self.assertEqual(cc._usage_fields({}), (0, 0, 0, 0, 0, 0))

    def test_non_numeric_counts_read_as_zero(self):
        # Accounting reads, it never gates the consumer, so a malformed value
        # degrades to zero instead of raising mid-render.
        u = {
            "input_tokens": "1200",
            "output_tokens": 3.5,
            "cache_read_input_tokens": True,
            "cache_creation_input_tokens": -5,
        }
        self.assertEqual(cc._usage_fields(u), (0, 0, 0, 0, 0, 0))
        t = cc.aggregate([(OPUS, u)])
        self.assertEqual(t["cost"], 0.0)


class Aggregate(unittest.TestCase):
    def test_one_message_prices_each_token_class_at_its_multiplier(self):
        t = cc.aggregate([(OPUS, a_mixed_opus_usage())])
        total_input = (
            INPUT_TOKENS + CACHE_READ_TOKENS + WRITE_5M_TOKENS + WRITE_1H_TOKENS
        )
        cache_base = CACHE_READ_TOKENS + WRITE_5M_TOKENS + WRITE_1H_TOKENS
        cache_actual = (
            CACHE_READ_TOKENS * CACHE_READ_MULT
            + WRITE_5M_TOKENS * CACHE_WRITE_5M_MULT
            + WRITE_1H_TOKENS * CACHE_WRITE_1H_MULT
        )
        self.assertAlmostEqual(t["cost"], mixed_opus_cost(), places=COST_PLACES)
        self.assertEqual(t["total_input"], total_input)
        self.assertEqual(t["hit_pct"], round(CACHE_READ_TOKENS * PERCENT / total_input))
        self.assertEqual(t["savings_pct"], savings_pct(cache_base, cache_actual))

    def test_mixed_fleet_prices_per_row(self):
        t = cc.aggregate(
            [
                (OPUS, a_mixed_opus_usage()),
                (HAIKU, a_usage(inp=INPUT_TOKENS, out=INPUT_TOKENS)),
            ]
        )
        haiku_cost = plain_cost(HAIKU_RATE, INPUT_TOKENS, INPUT_TOKENS)
        self.assertAlmostEqual(
            t["cost"], mixed_opus_cost() + haiku_cost, places=COST_PLACES
        )
        self.assertEqual(t["output"], OUTPUT_TOKENS + INPUT_TOKENS)
        self.assertEqual(
            t["total_input"],
            INPUT_TOKENS * 2 + CACHE_READ_TOKENS + WRITE_5M_TOKENS + WRITE_1H_TOKENS,
        )

    def test_fable_5_1_row_prices_reads_at_override(self):
        t = cc.aggregate([(FABLE_5_1, a_usage(read=MTOK))])
        input_rate, _ = FABLE_RATE
        self.assertAlmostEqual(
            t["cost"], input_rate * FABLE_5_1_READ_MULT, places=COST_PLACES
        )
        self.assertEqual(
            t["savings_pct"], savings_pct(MTOK, MTOK * FABLE_5_1_READ_MULT)
        )

    def test_savings_baseline_uses_per_row_read_mult(self):
        t = cc.aggregate(
            [
                (FABLE_5_1, a_usage(read=SOME_TOKENS)),
                (FABLE, a_usage(read=SOME_TOKENS)),
            ]
        )
        actual = SOME_TOKENS * FABLE_5_1_READ_MULT + SOME_TOKENS * CACHE_READ_MULT
        self.assertEqual(t["savings_pct"], savings_pct(SOME_TOKENS * 2, actual))

    def test_no_cache_activity_savings_is_none(self):
        t = cc.aggregate([(OPUS, a_usage(inp=SOME_TOKENS, out=SOME_TOKENS))])
        self.assertIsNone(t["savings_pct"])

    def test_hit_pct_zero_when_no_cache_read(self):
        t = cc.aggregate([(OPUS, a_usage(inp=SOME_TOKENS, out=SOME_TOKENS))])
        self.assertEqual(t["hit_pct"], 0)

    def test_no_rows_total_to_zero(self):
        t = cc.aggregate([])
        self.assertEqual(t["cost"], 0.0)
        self.assertEqual(t["hit_pct"], 0)
        self.assertIsNone(t["savings_pct"])


class TimestampParsing(unittest.TestCase):
    def test_zulu_offset_and_bare_forms_parse_alike(self):
        zulu = cc.parse_ts("2026-07-06T10:00:00Z")
        offset = cc.parse_ts("2026-07-06T10:00:00+00:00")
        bare = cc.parse_ts("2026-07-06T10:00:00")
        self.assertEqual(zulu, offset)
        self.assertEqual(zulu, bare)

    def test_a_later_stamp_parses_larger(self):
        self.assertLess(cc.parse_ts(SOME_TS), cc.parse_ts(A_LATER_TS))

    def test_an_invalid_stamp_parses_to_none(self):
        self.assertIsNone(cc.parse_ts("not-a-time"))
        self.assertIsNone(cc.parse_ts(None))
        self.assertIsNone(cc.parse_ts(A_NON_STRING))


class TranscriptCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write_transcript(self, path, messages):
        """Write (model, usage, ts[, request_id]) assistant lines behind a user line and a blank line."""
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ['{"type":"user","message":{"role":"user"}}', ""]
        for entry in messages:
            model, u, ts = entry[0], entry[1], entry[2]
            rec = {
                "type": "assistant",
                "timestamp": ts,
                "message": {"model": model, "usage": u},
            }
            if len(entry) > 3:
                rec["requestId"] = entry[3]
            lines.append(json.dumps(rec))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def write_meta(self, transcript, agent_type):
        meta = Path(str(transcript)[: -len(cc.TRANSCRIPT_SUFFIX)] + cc.META_SUFFIX)
        payload = {} if agent_type is None else {"agentType": agent_type}
        meta.write_text(json.dumps(payload), encoding="utf-8")


class AssistantCalls(TranscriptCase):
    def test_only_an_assistant_record_with_usage_yields(self):
        p = self.root / "t.jsonl"
        self.write_transcript(p, [(OPUS, a_usage(inp=SOME_TOKENS), SOME_TS)])
        rows = list(cc.iter_assistant(p))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], OPUS)

    def test_a_malformed_line_is_skipped(self):
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

    def test_a_missing_file_yields_nothing(self):
        self.assertEqual(list(cc.iter_assistant(self.root / "nope.jsonl")), [])

    def test_records_sharing_a_request_id_price_one_call(self):
        # The runtime writes one record per content block, each repeating the
        # call's usage with a partial output count; the per-field maximum is
        # the call's full figure.
        p = self.root / "t.jsonl"
        request = "req_1"
        partial_output, final_output = SOME_TOKENS, OUTPUT_TOKENS
        blocks = [
            a_usage(out=partial_output, read=CACHE_READ_TOKENS, cc1=WRITE_1H_TOKENS),
            a_usage(out=final_output, read=CACHE_READ_TOKENS, cc1=WRITE_1H_TOKENS),
            a_usage(out=partial_output, read=CACHE_READ_TOKENS, cc1=WRITE_1H_TOKENS),
        ]
        self.write_transcript(p, [(OPUS, u, SOME_TS, request) for u in blocks])
        rows = list(cc.iter_assistant(p))
        self.assertEqual(len(rows), 1)
        u = rows[0][1]
        self.assertEqual(u["output_tokens"], final_output)
        self.assertEqual(u["cache_read_input_tokens"], CACHE_READ_TOKENS)
        self.assertEqual(
            u["cache_creation"]["ephemeral_1h_input_tokens"], WRITE_1H_TOKENS
        )

    def test_distinct_request_ids_stay_separate(self):
        p = self.root / "t.jsonl"
        self.write_transcript(
            p,
            [
                (OPUS, a_usage(inp=SOME_TOKENS), SOME_TS, "req_1"),
                (OPUS, a_usage(inp=SOME_TOKENS), SOME_TS, "req_2"),
            ],
        )
        self.assertEqual(len(list(cc.iter_assistant(p))), 2)

    def test_records_without_ids_each_count_alone(self):
        p = self.root / "t.jsonl"
        self.write_transcript(
            p,
            [
                (OPUS, a_usage(inp=SOME_TOKENS), SOME_TS),
                (OPUS, a_usage(inp=SOME_TOKENS), SOME_TS),
            ],
        )
        self.assertEqual(len(list(cc.iter_assistant(p))), 2)


class SessionTree(TranscriptCase):
    def test_the_parent_and_its_subagents_are_discovered(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(parent, [(OPUS, a_usage(inp=SOME_TOKENS), SOME_TS)])
        sub = self.root / "sess" / "subagents"
        self.write_transcript(
            sub / "agent-a.jsonl", [(HAIKU, a_usage(inp=SOME_TOKENS), A_LATER_TS)]
        )
        (sub / "notes.txt").write_text("x", encoding="utf-8")
        files = cc.session_transcripts(str(parent), "sess")
        self.assertEqual(len(files), 2)

    def test_session_totals_sum_the_whole_tree(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(
            parent, [(OPUS, a_usage(inp=INPUT_TOKENS, out=OUTPUT_TOKENS), SOME_TS)]
        )
        sub = self.root / "sess" / "subagents"
        self.write_transcript(
            sub / "agent-a.jsonl",
            [(HAIKU, a_usage(inp=INPUT_TOKENS, out=OUTPUT_TOKENS), A_LATER_TS)],
        )
        t = cc.session_totals(str(parent), "sess")
        expected = plain_cost(OPUS_RATE, INPUT_TOKENS, OUTPUT_TOKENS) + plain_cost(
            HAIKU_RATE, INPUT_TOKENS, OUTPUT_TOKENS
        )
        self.assertAlmostEqual(t["cost"], expected, places=COST_PLACES)
        self.assertEqual(t["input"], INPUT_TOKENS * 2)


class WindowQueries(TranscriptCase):
    SLUG = "-proj-x"

    def _agent(self, session, agent_id, agent_type, messages):
        sub = self.root / self.SLUG / session / "subagents"
        path = sub / f"{cc.TRANSCRIPT_PREFIX}{agent_id}{cc.TRANSCRIPT_SUFFIX}"
        self.write_transcript(path, messages)
        self.write_meta(path, agent_type)
        return path

    def index(self):
        return cc.WindowIndex(projects_root=str(self.root), slug=self.SLUG)

    def totals(self, agent_type, start=WINDOW_START, end=WINDOW_END, idx=None):
        idx = idx or self.index()
        return idx.totals(agent_type, cc.parse_ts(start), cc.parse_ts(end))

    def slice_totals(self, agent_types, start=WINDOW_START, end=WINDOW_END):
        return self.index().slice_totals(
            agent_types, cc.parse_ts(start), cc.parse_ts(end)
        )

    def test_window_attributes_by_type_and_time(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INPUT_TOKENS, out=OUTPUT_TOKENS), INSIDE_WINDOW)],
        )
        self._agent(
            SOME_SESSION,
            "rev",
            REVIEWER,
            [(OPUS, a_usage(inp=OUTSIDE_INPUT), INSIDE_WINDOW)],
        )
        t = self.totals(IMPLEMENTER)
        self.assertAlmostEqual(
            t["cost"],
            plain_cost(OPUS_RATE, INPUT_TOKENS, OUTPUT_TOKENS),
            places=COST_PLACES,
        )
        self.assertEqual(t["output"], OUTPUT_TOKENS)

    def test_effort_variant_attributes_to_its_base_type(self):
        # The variant's transcript carries its own agentType while the ledger
        # records keep the base author, so the join folds it into the base.
        self._agent(
            SOME_SESSION,
            "impl-routine",
            IMPLEMENTER_VARIANT,
            [(OPUS, a_usage(inp=INPUT_TOKENS, out=OUTPUT_TOKENS), INSIDE_WINDOW)],
        )
        self.assertEqual(self.totals(IMPLEMENTER)["output"], OUTPUT_TOKENS)
        self.assertIsNone(self.totals(DOC_REVIEWER))
        self.assertEqual(self.slice_totals([IMPLEMENTER])["output"], OUTPUT_TOKENS)

    def test_dispatch_overlapping_the_window_sums_whole_file(self):
        # The window bounds a step; the transcript bounds the dispatch, so one
        # dispatch straddling the window's end attributes in full.
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW),
                (OPUS, a_usage(inp=OUTSIDE_INPUT), AFTER_WINDOW),
            ],
        )
        self.assertEqual(
            self.totals(IMPLEMENTER)["input"], INSIDE_INPUT + OUTSIDE_INPUT
        )

    def test_dispatch_front_before_the_window_attributes(self):
        # An agent's first message lands before its first tool call can append
        # dispatch-start, so the window opens mid-dispatch; that front is the
        # step's cost.
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=OUTSIDE_INPUT), BEFORE_WINDOW),
                (OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW),
            ],
        )
        self.assertEqual(
            self.totals(IMPLEMENTER)["input"], OUTSIDE_INPUT + INSIDE_INPUT
        )

    def test_dispatch_wholly_outside_the_window_excluded(self):
        self._agent(
            SOME_SESSION,
            "impl1",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self._agent(
            SOME_SESSION,
            "impl2",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=OUTSIDE_INPUT), AFTER_WINDOW)],
        )
        self.assertEqual(self.totals(IMPLEMENTER)["input"], INSIDE_INPUT)

    def test_retries_within_one_session_sum(self):
        self._agent(
            SOME_SESSION,
            "impl1",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self._agent(
            SOME_SESSION,
            "impl2",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=OTHER_INSIDE_INPUT), ALSO_INSIDE_WINDOW)],
        )
        self.assertEqual(
            self.totals(IMPLEMENTER)["input"], INSIDE_INPUT + OTHER_INSIDE_INPUT
        )

    def test_cross_session_window_sums(self):
        # Sessions are sequential, so a file is its dispatch's whatever session
        # wrote it, and a slice resumed in a later session sums both.
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self._agent(
            A_LATER_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=OTHER_INSIDE_INPUT), ALSO_INSIDE_WINDOW)],
        )
        self.assertEqual(
            self.totals(IMPLEMENTER)["input"], INSIDE_INPUT + OTHER_INSIDE_INPUT
        )

    def test_unparseable_stamp_still_counts_toward_its_file(self):
        # The file is the unit: once overlap selects a dispatch, a message it
        # could not place still belongs to it.
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=UNPLACEABLE_INPUT), None),
                (OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW),
            ],
        )
        idx = self.index()
        t = self.totals(IMPLEMENTER, idx=idx)
        self.assertEqual(t["input"], UNPLACEABLE_INPUT + INSIDE_INPUT)
        self.assertEqual(len(idx.rows), 1)

    def test_file_with_no_placeable_stamp_is_dropped(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=UNPLACEABLE_INPUT), None)],
        )
        self.assertIsNone(self.totals(IMPLEMENTER))

    def test_slice_totals_aggregates_across_types(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT, out=OUTPUT_TOKENS), INSIDE_WINDOW)],
        )
        self._agent(
            SOME_SESSION,
            "rev",
            REVIEWER,
            [(OPUS, a_usage(inp=OTHER_INSIDE_INPUT), ALSO_INSIDE_WINDOW)],
        )
        t = self.slice_totals([IMPLEMENTER, REVIEWER, AN_UNDISPATCHED_TYPE])
        self.assertEqual(t["input"], INSIDE_INPUT + OTHER_INSIDE_INPUT)
        self.assertEqual(t["output"], OUTPUT_TOKENS)

    def test_slice_totals_counts_duplicate_types_once(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        t = self.slice_totals([IMPLEMENTER, IMPLEMENTER])
        self.assertEqual(t["input"], INSIDE_INPUT)

    def test_slice_totals_stays_message_windowed(self):
        # The roll-up's window bounds a slice, not a dispatch, so whole-file
        # selection would price a dispatch that also served a batched sibling
        # on both boards.
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW),
                (OPUS, a_usage(inp=OUTSIDE_INPUT), AFTER_WINDOW),
            ],
        )
        self.assertEqual(self.slice_totals([IMPLEMENTER])["input"], INSIDE_INPUT)
        self.assertEqual(
            self.totals(IMPLEMENTER)["input"], INSIDE_INPUT + OUTSIDE_INPUT
        )

    def test_slice_totals_cross_session_sums(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self._agent(
            A_LATER_SESSION,
            "impl2",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=OTHER_INSIDE_INPUT), ALSO_INSIDE_WINDOW)],
        )
        self._agent(
            SOME_SESSION,
            "rev",
            REVIEWER,
            [(OPUS, a_usage(inp=SOME_TOKENS), ALSO_INSIDE_WINDOW)],
        )
        t = self.slice_totals([IMPLEMENTER, REVIEWER])
        self.assertEqual(t["input"], INSIDE_INPUT + OTHER_INSIDE_INPUT + SOME_TOKENS)

    def test_slice_totals_nothing_matched_returns_none(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        idx = self.index()
        self.assertIsNone(self.slice_totals([AN_UNDISPATCHED_TYPE]))
        self.assertIsNone(self.slice_totals([]))
        self.assertIsNone(
            idx.slice_totals([IMPLEMENTER], None, cc.parse_ts(WINDOW_END))
        )

    def test_no_matching_dispatch_returns_none(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self.assertIsNone(self.totals(AN_UNDISPATCHED_TYPE))

    def test_an_unbounded_or_reversed_window_returns_none(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        idx = self.index()
        start, end = cc.parse_ts(WINDOW_START), cc.parse_ts(WINDOW_END)
        self.assertIsNone(idx.totals(IMPLEMENTER, None, end))
        self.assertIsNone(idx.totals(IMPLEMENTER, end, start))

    def test_missing_agent_type_is_dropped(self):
        self._agent(
            SOME_SESSION,
            "impl",
            None,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        self.assertEqual(self.index().rows, [])

    def test_a_missing_project_dir_indexes_nothing(self):
        idx = cc.WindowIndex(projects_root=str(self.root), slug="-nope")
        self.assertEqual(idx.rows, [])
        self.assertIsNone(self.totals(IMPLEMENTER, idx=idx))

    def test_since_secs_prunes_transcripts_older_than_the_window(self):
        # A transcript last written before the bound cannot hold in-window
        # messages, so it is skipped unread.
        path = self._agent(
            SOME_SESSION,
            "old",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        os.utime(path, (STALE_MTIME, STALE_MTIME))
        idx = cc.WindowIndex(
            projects_root=str(self.root), slug=self.SLUG, since_secs=STALE_MTIME + 1
        )
        self.assertEqual(idx.rows, [])
        self.assertEqual(len(self.index().rows), 1)

    def test_since_secs_keeps_a_dispatch_that_began_before_the_bound(self):
        # The bound prunes on the last write, so a dispatch that started before
        # the earliest window but ran into it survives with its front intact.
        path = self._agent(
            SOME_SESSION,
            "straddler",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=UNPLACEABLE_INPUT), BEFORE_WINDOW),
                (OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW),
            ],
        )
        start = cc.parse_ts(WINDOW_START)
        last_write = cc.parse_ts(INSIDE_WINDOW)
        os.utime(path, (last_write, last_write))
        idx = cc.WindowIndex(
            projects_root=str(self.root), slug=self.SLUG, since_secs=start
        )
        t = idx.totals(IMPLEMENTER, start, cc.parse_ts(WINDOW_END))
        self.assertEqual(t["input"], UNPLACEABLE_INPUT + INSIDE_INPUT)

    def test_concurrent_same_type_dispatches_double_count(self):
        # Two dispatches of one type overlapping in time are unrankable: every
        # window over either selects both. The roster fans out across distinct
        # types, so a roster that fans out two of one type fails here first.
        first_start, first_end = "2026-07-06T10:05:00Z", "2026-07-06T10:07:00Z"
        second_start, second_end = "2026-07-06T10:06:00Z", "2026-07-06T10:08:00Z"
        first_inputs = (INSIDE_INPUT, 1)
        second_inputs = (OTHER_INSIDE_INPUT, 2)
        self._agent(
            SOME_SESSION,
            "rev1",
            DOC_REVIEWER,
            [
                (OPUS, a_usage(inp=first_inputs[0]), first_start),
                (OPUS, a_usage(inp=first_inputs[1]), first_end),
            ],
        )
        self._agent(
            SOME_SESSION,
            "rev2",
            DOC_REVIEWER,
            [
                (OPUS, a_usage(inp=second_inputs[0]), second_start),
                (OPUS, a_usage(inp=second_inputs[1]), second_end),
            ],
        )
        both = sum(first_inputs) + sum(second_inputs)
        idx = self.index()
        self.assertEqual(
            self.totals(DOC_REVIEWER, first_start, first_end, idx=idx)["input"], both
        )
        self.assertEqual(
            self.totals(DOC_REVIEWER, second_start, second_end, idx=idx)["input"], both
        )

    def test_window_touching_the_span_edge_selects_the_file(self):
        # Overlap is closed at both ends: a window ending exactly at the file's
        # first message still names that dispatch; one second earlier does not.
        one_second_before = "2026-07-06T10:04:59Z"
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [(OPUS, a_usage(inp=INSIDE_INPUT), INSIDE_WINDOW)],
        )
        idx = self.index()
        t = self.totals(IMPLEMENTER, WINDOW_START, INSIDE_WINDOW, idx=idx)
        self.assertEqual(t["input"], INSIDE_INPUT)
        self.assertIsNone(
            self.totals(IMPLEMENTER, WINDOW_START, one_second_before, idx=idx)
        )

    def test_zero_width_window_inside_a_span_selects_the_file(self):
        self._agent(
            SOME_SESSION,
            "impl",
            IMPLEMENTER,
            [
                (OPUS, a_usage(inp=INSIDE_INPUT), WINDOW_START),
                (OPUS, a_usage(inp=OTHER_INSIDE_INPUT), WINDOW_END),
            ],
        )
        t = self.totals(IMPLEMENTER, INSIDE_WINDOW, INSIDE_WINDOW)
        self.assertEqual(t["input"], INSIDE_INPUT + OTHER_INSIDE_INPUT)

    def test_the_projects_root_honors_the_environment_override(self):
        with unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": "/some/where/projects"}
        ):
            self.assertEqual(cc.default_projects_root(), "/some/where/projects")


class SlugAndFormatting(unittest.TestCase):
    def test_every_non_alphanumeric_character_maps_to_a_dash(self):
        self.assertEqual(
            cc.slug_for("/home/user/work/my-project"), "-home-user-work-my-project"
        )

    def test_tokens_format_compactly(self):
        self.assertEqual(cc.format_tokens(567), "567")
        self.assertEqual(cc.format_tokens(34 * cc.TOKENS_PER_THOUSAND), "34k")
        self.assertEqual(cc.format_tokens(1.2 * MTOK), "1.2M")

    def test_cost_formats_to_the_cent(self):
        self.assertEqual(cc.format_cost(1.7138), "1.71")
        self.assertEqual(cc.format_cost(0), "0.00")


class CommandLine(TranscriptCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cc.main(argv)
        return rc, json.loads(buf.getvalue())

    def test_the_session_mode_emits_json_totals(self):
        parent = self.root / "sess.jsonl"
        self.write_transcript(
            parent, [(OPUS, a_usage(inp=INPUT_TOKENS, out=OUTPUT_TOKENS), SOME_TS)]
        )
        rc, out = self._run(
            ["session", "--parent", str(parent), "--session-id", "sess"]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(out["input"], INPUT_TOKENS)
        self.assertIn("cost", out)

    def test_the_window_mode_emits_null_on_no_match(self):
        # --cwd derives the slug; its leading '/' keeps argparse from reading
        # the value as a flag, unlike a bare --slug beginning with '-'.
        rc, out = self._run(
            [
                "window",
                "--agent-type",
                IMPLEMENTER,
                "--start",
                WINDOW_START,
                "--end",
                WINDOW_END,
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
