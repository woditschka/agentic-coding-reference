#!/usr/bin/env python3
"""cc_accounting.py — Claude Code usage accounting and list-price costing.

Single source of truth for turning Claude Code transcript `usage` blocks into
token totals, cache figures, and list-price dollar cost. Two consumers:

  * the harness-stats statusline — session-wide totals across parent +
    subagents (the `session` CLI mode below).
  * the handoff board (scripts/handoff.py) — one agentType's dispatches, via
    the WindowIndex API. A window does not bound spend; it selects the
    dispatches to sum, and each is summed whole. Claude Code writes one
    subagent transcript per dispatch, so a file is a dispatch and a step's
    figure is that dispatch's real cost.

Cost is NOT stored in transcripts; it is computed here from usage x the pricing
table. THE PRICING TABLE BELOW IS THE SINGLE DOCUMENTED EDIT POINT — update it
when Anthropic changes prices. Do not copy rate values into shell, skill, or
doc prose (portability invariant); every consumer reads them from here.

CANONICAL COPY: tools/harness-stats/cc_accounting.py. A byte-identical copy is
vendored into harness/core/scripts/cc_accounting.py (and materialized into every
sample's scripts/) so the board stays self-contained across all four tools.
Edit this file, then re-sync with a plain copy:

    cp tools/harness-stats/cc_accounting.py harness/core/scripts/cc_accounting.py

harness/check-sync.py fails if the two copies drift. There is no build step —
the copy is manual, the gate is automatic.
"""

import datetime
import json
import os
import re

# ── API pricing ($ per million tokens) ─────────────────────────────────────
# The list-price API spend for a token volume. Source: platform.claude.com
# pricing, current as of 2026-07-01. UPDATE THIS BLOCK when Anthropic changes
# prices — it is the single edit point for every consumer.
#
# Priced by model FAMILY, not exact ID: Fable 5 is $10/$50, every currently
# served Opus tier (4.5/4.6/4.7/4.8) is $5/$25, Sonnet 4.x is $3/$15, and
# Haiku 4.5 is $1/$5 — so the family rate is exact today and survives new
# same-price tiers. If Anthropic ever prices two tiers of one family
# differently on a durable basis, add a per-model-ID override to PRICE_OVERRIDE
# (the Sonnet 5 case below is the template).
#
# These are list API prices. Subscription (Max/Pro) users don't pay per token,
# so for them the figure is a notional "what this would cost on the API"
# number, not a bill.
PRICE = {
    #          ($ / Mtok input, $ / Mtok output)
    "fable":  (10.00, 50.00),
    "opus":   (5.00, 25.00),
    "sonnet": (3.00, 15.00),
    "haiku":  (1.00, 5.00),
}

# Per-model-ID overrides, matched (as a lowercase substring of the model
# string) BEFORE the family table. Sonnet 5 carries an introductory $2/$10
# through 2026-08-31, then reverts to the Sonnet family $3/$15 on 2026-09-01.
# The "sonnet-5" needle is tested ahead of the "sonnet" family so the intro
# rate applies to Sonnet 5 only. ⚠ MANUAL REVERT on 2026-09-01: delete the
# "sonnet-5" entry (or set it to (3.00, 15.00)) — after that date the override
# over-discounts Sonnet 5 by ~33%.
PRICE_OVERRIDE = (
    ("sonnet-5", (2.00, 10.00)),
)

# Cache multipliers, relative to the family's base input price: a cache READ
# costs 0.10x input, a 5-minute cache WRITE 1.25x, a 1-hour cache WRITE 2.0x.
# The 5m/1h split is read from usage.cache_creation when present.
CACHE_READ_MULT = 0.10
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00

def _rate(model):
    """(input, output) $/Mtok for a model string. Overrides win over the
    family table; an unrecognized model prices at zero (no guess) so a new
    model surfaces as $0.00 rather than a wrong number. PRICE's insertion
    order fixes the scan (the family names are disjoint substrings, so order
    never changes a match — it only keeps the scan deterministic)."""
    m = (model or "").lower()
    for needle, rate in PRICE_OVERRIDE:
        if needle in m:
            return rate
    for fam, rate in PRICE.items():
        if fam in m:
            return rate
    return (0.0, 0.0)


def _count(v):
    """A token count as a non-negative int; any other shape (a malformed
    transcript value: string, float, bool, None) reads as 0 so accounting
    degrades instead of raising mid-render."""
    return v if isinstance(v, int) and not isinstance(v, bool) and v > 0 else 0


def _usage_fields(u):
    """The six token counts from one usage dict. When usage.cache_creation
    carries the TTL split, a missing 5m key derives as the flat total minus
    the 1h count (never negative) — falling back to the flat total there
    would double-count the 1h tokens. Without the split dict, the flat total
    reads as a 5-minute write. cc5 + cc1 == cache_creation either way."""
    ci = _count(u.get("input_tokens"))
    co = _count(u.get("output_tokens"))
    cr = _count(u.get("cache_read_input_tokens"))
    cc = _count(u.get("cache_creation_input_tokens"))
    split = u.get("cache_creation")
    if isinstance(split, dict):
        cc1 = _count(split.get("ephemeral_1h_input_tokens"))
        cc5 = split.get("ephemeral_5m_input_tokens")
        cc5 = max(cc - cc1, 0) if cc5 is None else _count(cc5)
    else:
        cc5, cc1 = cc, 0
    return ci, co, cr, cc, cc5, cc1


def aggregate(rows):
    """Fold (model, usage_dict) rows into the accounting totals a consumer
    renders: token counts, list-price cost (per-row family pricing, so a mixed
    fleet is billed at each message's own rate), cache-hit %, and cache-savings
    % vs a no-cache baseline. savings_pct is None when there is no cache
    activity to rate. Pure: no I/O, no clock."""
    total = {"input": 0, "output": 0, "cache_read": 0, "cache_creation": 0,
             "cc5": 0, "cc1": 0, "cost": 0.0}
    for model, usage in rows:
        ci, co, cr, cc, cc5, cc1 = _usage_fields(usage)
        total["input"] += ci
        total["output"] += co
        total["cache_read"] += cr
        total["cache_creation"] += cc
        total["cc5"] += cc5
        total["cc1"] += cc1
        ip, op = _rate(model)
        total["cost"] += (ci * ip + co * op
                          + cr * ip * CACHE_READ_MULT
                          + cc5 * ip * CACHE_WRITE_5M_MULT
                          + cc1 * ip * CACHE_WRITE_1H_MULT) / 1e6
    ti = total["input"] + total["cache_read"] + total["cache_creation"]
    total["total_input"] = ti
    total["hit_pct"] = round(total["cache_read"] * 100 / ti) if ti > 0 else 0
    base = total["cache_read"] + total["cc5"] + total["cc1"]
    if base > 0:
        actual = (total["cache_read"] * CACHE_READ_MULT
                  + total["cc5"] * CACHE_WRITE_5M_MULT
                  + total["cc1"] * CACHE_WRITE_1H_MULT)
        total["savings_pct"] = round((base - actual) * 100 / base)
    else:
        total["savings_pct"] = None
    return total


def parse_ts(ts):
    """An ISO-8601 timestamp as POSIX seconds, or None. A bare ts with no
    offset is read as UTC (deterministic across machines). Mirrors handoff.py's
    _ts_seconds so a board window and a transcript message compare on one
    clock."""
    if not isinstance(ts, str):
        return None
    t = ts.strip()
    if t[-1:] in ("Z", "z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


def iter_assistant(path):
    """Yield (model, usage_dict, timestamp) for each assistant message in a
    transcript. Malformed lines are skipped and an unreadable file yields
    nothing — the accounting degrades on a partial or absent transcript, it
    never raises."""
    try:
        fh = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not isinstance(rec, dict) or rec.get("type") != "assistant":
                continue
            msg = rec.get("message")
            if not isinstance(msg, dict):
                continue
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            yield msg.get("model"), usage, rec.get("timestamp")


# ── session mode (statusline) ──────────────────────────────────────────────

def session_transcripts(parent_path, session_id):
    """The parent transcript plus every subagent transcript in its session
    dir: <dir>/<session_id>/subagents/agent-*.jsonl. Missing pieces are simply
    absent from the list."""
    files = []
    if parent_path and os.path.isfile(parent_path):
        files.append(parent_path)
    if parent_path and session_id:
        sub = os.path.join(os.path.dirname(parent_path), session_id, "subagents")
        if os.path.isdir(sub):
            for name in sorted(os.listdir(sub)):
                if name.startswith("agent-") and name.endswith(".jsonl"):
                    files.append(os.path.join(sub, name))
    return files


def session_totals(parent_path, session_id):
    """Accounting totals across the whole session tree (parent + subagents)."""
    rows = []
    for path in session_transcripts(parent_path, session_id):
        for model, usage, _ts in iter_assistant(path):
            rows.append((model, usage))
    return aggregate(rows)


# ── window mode (board) ────────────────────────────────────────────────────

def default_projects_root():
    """The Claude Code projects directory: ~/.claude/projects, or the
    CLAUDE_PROJECTS_ROOT environment override when set (a non-default config
    layout, or a test pointing at a synthetic tree)."""
    override = os.environ.get("CLAUDE_PROJECTS_ROOT")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".claude", "projects")


def slug_for(cwd):
    """Claude Code's project-dir encoding: every non-alphanumeric character in
    the absolute path maps to '-'. Matches the statusline / cache-report
    resolvers and install.sh's smoke test."""
    return re.sub(r"[^a-zA-Z0-9]", "-", cwd)


def subagent_transcripts(projects_root, slug):
    """(transcript_path, agentType, session_id) for every subagent transcript
    under any session of this project slug. agentType comes from the
    agent-*.meta.json sidecar; None when the sidecar is missing or unreadable
    (such a transcript cannot be attributed and is dropped by the index)."""
    base = os.path.join(projects_root, slug)
    out = []
    if not os.path.isdir(base):
        return out
    for session in sorted(os.listdir(base)):
        sub = os.path.join(base, session, "subagents")
        if not os.path.isdir(sub):
            continue
        for name in sorted(os.listdir(sub)):
            if not (name.startswith("agent-") and name.endswith(".jsonl")):
                continue
            path = os.path.join(sub, name)
            meta = path[:-len(".jsonl")] + ".meta.json"
            agent_type = None
            try:
                with open(meta, encoding="utf-8") as fh:
                    parsed = json.load(fh)
                if isinstance(parsed, dict):
                    agent_type = parsed.get("agentType")
            except (OSError, ValueError):
                agent_type = None
            out.append((path, agent_type, session))
    return out


class WindowIndex:
    """Subagent usage across a project's transcripts, pre-parsed once and
    queryable by (agentType, [start, end]) time window. The board builds one
    per render at its I/O boundary, then keeps render_view a pure function of
    the log plus this overlay.

    The unit of attribution is the transcript file, not the message: Claude
    Code writes one subagent transcript per dispatch, so a file IS a dispatch
    and its whole cost belongs to the dispatch a window names. A window
    therefore selects the files it OVERLAPS and sums each in full — including
    the messages outside the window's bounds. That is deliberate. A window
    runs dispatch-start → the closing record, but a dispatch's first message
    carries the system prompt and the whole inbound context, so it dominates
    the dispatch's cost — and it lands before the agent's first tool call can
    append dispatch-start. A trailing message can land after the closing
    record. Summing only the messages between the bounds drops both ends and
    undercounts every step; whole-file summing is what makes a step's figure
    the dispatch's real cost.

    Files are grouped by agentType as (first_secs, last_secs, [(model, usage)])
    so a per-step lookup scans only its own author's dispatches. A transcript
    with no attributable agentType is dropped, as is one whose every timestamp
    is unparseable — with no span it cannot be placed, so no window can select
    it. A single unparseable timestamp only withholds that message from the
    span; the message still counts toward its file's total, because the file
    is the unit and its dispatch is what the window selects. `rows` keeps every
    timestamped message flat as (agentType, session_id, ts_seconds, model,
    usage), independent of the file grouping.

    A file's span is its own messages' timestamps, which nothing here controls
    and nothing bounds. A stamp skewed either way widens the span into windows
    the dispatch never ran in. Ordinary clock skew is harmless — the ledger's
    timestamps come from the same clock, so windows and spans move together —
    but a single corrupt stamp can pull a whole dispatch onto a step that did
    not spend it. The file's mtime bounds only the forward half, and binding
    the span to a second clock the ledger never reads costs more than the half
    it buys.

    Step attribution is exact only while no two dispatches of one agentType
    overlap in time; `_overlapping` carries that premise and what breaks it.

    Session identity is deliberately absent from attribution. Two Claude Code
    sessions over one project are outside the harness's design space — they
    would collide on the handoff ledger and the working tree long before their
    spend was ambiguous — so sessions are sequential, and a dispatch's file is
    its own whatever session wrote it. Summing a slice that was resumed in a
    later session is therefore exact, not a guess.

    since_secs, when given, skips transcripts whose file mtime predates it: a
    file's messages cannot postdate its last write, so a transcript that
    finished before the earliest window of interest can never overlap one.
    Pruning on mtime (the last write) rather than on the first message is what
    makes it correct under whole-file attribution: a dispatch that began before
    the earliest window but ran into it survives, front intact. Pruning on a
    first message would silently restore the undercount this index exists to
    avoid."""

    def __init__(self, projects_root=None, slug=None, cwd=None, since_secs=None):
        projects_root = projects_root or default_projects_root()
        if slug is None:
            slug = slug_for(cwd if cwd is not None else os.getcwd())
        self.rows = []
        self._by_type = {}
        self._rows_by_type = {}
        for path, agent_type, session in subagent_transcripts(projects_root, slug):
            if not agent_type:
                continue
            if since_secs is not None:
                try:
                    if os.path.getmtime(path) < since_secs:
                        continue
                except OSError:
                    continue
            file_rows, stamps = [], []
            for model, usage, ts in iter_assistant(path):
                file_rows.append((model, usage))
                secs = parse_ts(ts)
                if secs is None:
                    continue
                self.rows.append((agent_type, session, secs, model, usage))
                self._rows_by_type.setdefault(agent_type, []).append((secs, model, usage))
                stamps.append(secs)
            if not stamps:
                continue
            self._by_type.setdefault(agent_type, []).append(
                (min(stamps), max(stamps), file_rows))

    def _overlapping(self, agent_type, start_secs, end_secs):
        """The rows of every agent_type dispatch whose transcript overlaps
        [start, end], each file summed whole (see the class docstring).

        EXACT ONLY WHILE NO TWO agent_type DISPATCHES OVERLAP IN TIME. That
        premise is not enforced here, and no log content can enforce it: two
        concurrent dispatches of one type write two files whose spans overlap,
        every window over either selects both, and each line then prints their
        sum — identical figures on every line, the misranking this index exists
        to end. The pipeline's fan-out is across DISTINCT types (the reviewer
        roster), which is the only reason its boards are unaffected. That is a
        property of the roster, not of this code. A roster that fanned out two
        of one type would double-count in silence.

        A window that spans several SEQUENTIAL dispatches — an implement
        session over the implementer's retries — selects each one's file. That
        is the intended sum, not a double count.

        A dispatch that also served a batched sibling slice attributes in full
        to the slice it was dispatched for: a timed record pairs only with a
        dispatch-start of its own author AND req_id (handoff.py
        `_producer_dispatch`), so the sibling's record pairs with nothing and
        carries no tail."""
        rows = []
        for first, last, file_rows in self._by_type.get(agent_type, ()):
            if first <= end_secs and last >= start_secs:
                rows.extend(file_rows)
        return rows

    def totals(self, agent_type, start_secs, end_secs):
        """Accounting totals for agent_type within [start, end] seconds, or
        None on an out-of-order or None-bounded window, or when no dispatch
        overlaps it — nothing spent, or a step whose author ran no subagent
        (an engine). Multiple overlapping transcripts (an implementer's
        retries) sum correctly; so does a slice resumed in a later session."""
        if start_secs is None or end_secs is None or end_secs < start_secs:
            return None
        rows = self._overlapping(agent_type, start_secs, end_secs)
        if not rows:
            return None
        return aggregate(rows)

    def slice_totals(self, agent_types, start_secs, end_secs):
        """Accounting totals across every named agent type within [start, end]
        seconds — the whole-slice roll-up — or None. A type with no message in
        the window contributes nothing (an engine author, a step run by the
        main loop). None when no type matched anything.

        Deliberately NOT whole-file, unlike totals(). A step's window bounds
        one dispatch, so widening it to that dispatch's file is exact. This
        window bounds a whole SLICE, and a dispatch may serve a batched sibling
        slice as well: selecting whole files here would price such a dispatch
        on both slices' boards. Pricing the roll-up per dispatch needs an
        anchor naming the dispatches the slice actually raised, which this
        signature does not carry. Until it does the header keeps the
        message-window figure, so it prices a dispatch differently from the
        lines and the two do not reconcile."""
        if start_secs is None or end_secs is None or end_secs < start_secs:
            return None
        rows = []
        for agent_type in dict.fromkeys(agent_types):
            rows.extend((model, usage)
                        for secs, model, usage in self._rows_by_type.get(agent_type, ())
                        if start_secs <= secs <= end_secs)
        if not rows:
            return None
        return aggregate(rows)


# ── formatting (shared with the board's tail rendering) ────────────────────

def format_tokens(n):
    """Compact token count: 1.2M / 34k / 567. Matches the statusline's
    fmt_tokens so the board and statusline read the same."""
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1e6:.1f}M"
    if n >= 1_000:
        return f"{n / 1e3:.0f}k"
    return str(n)


def format_cost(x):
    """List-price dollars to the cent, no symbol (the caller supplies $)."""
    return f"{x:.2f}"


# ── CLI (statusline consumer + manual inspection) ──────────────────────────

def _main(argv=None):
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="cc_accounting.py",
        description="Claude Code usage accounting; emits JSON totals.")
    sub = parser.add_subparsers(dest="mode", required=True)

    s = sub.add_parser("session", help="totals across a session tree (parent + subagents)")
    s.add_argument("--parent", required=True, help="the parent transcript path")
    s.add_argument("--session-id", default="", help="the session id (subagent dir name)")

    w = sub.add_parser("window", help="totals for one agentType within a time window")
    w.add_argument("--agent-type", required=True)
    w.add_argument("--start", required=True, help="ISO-8601 window start")
    w.add_argument("--end", required=True, help="ISO-8601 window end")
    w.add_argument("--slug", help="project slug; pass as --slug=<value> since a "
                   "real slug begins with '-' (default: derived from --cwd)")
    w.add_argument("--cwd", help="project dir to derive the slug from (default: cwd)")
    w.add_argument("--projects-root", help="default: ~/.claude/projects")

    args = parser.parse_args(argv)
    if args.mode == "session":
        result = session_totals(args.parent, args.session_id)
    else:
        index = WindowIndex(projects_root=args.projects_root, slug=args.slug,
                            cwd=args.cwd)
        result = index.totals(args.agent_type, parse_ts(args.start),
                              parse_ts(args.end))
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
