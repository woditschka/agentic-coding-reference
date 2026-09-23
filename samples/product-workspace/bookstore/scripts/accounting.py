#!/usr/bin/env python3
"""Turn Claude Code transcript usage into token totals, cache figures, and list-price cost.

The one pricing source for the statusline and the handoff board. The canonical
home is tools/harness-stats/accounting.py; the runtime copy is a plain cp of
it, byte-identical, and the battery fails on drift.
"""

import argparse
import datetime
import json
import os
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any, NamedTuple

# ── API pricing ($ per million tokens) ─────────────────────────────────────
# Source: platform.claude.com pricing, current as of 2026-09-23. This block is
# the single edit point when Anthropic changes prices; no consumer copies a
# rate into shell, skill, or doc prose.
#
# Priced by model family, not exact id: every Fable tier (5 and 5.1) is
# $10/$50, every served Opus tier from 4.5 through Opus 5 is $5/$25, every
# Sonnet tier through 4.6 lists at $3/$15, and Haiku 4.5 is $1/$5, so the
# family rate is exact today and survives a new same-price tier. A tier priced
# apart from its family on a durable basis takes a PRICE_OVERRIDE entry. These
# are list API prices: for a subscription user the figure is notional, not a
# bill.
PRICE = {
    #          ($ / Mtok input, $ / Mtok output)
    "fable": (10.00, 50.00),
    "opus": (5.00, 25.00),
    "sonnet": (3.00, 15.00),
    "haiku": (1.00, 5.00),
}

# Per-model overrides, matched as a lowercase substring (id or display-name
# form) before the family table. Sonnet 5 lists at $2/$10: announced as
# introductory pricing through 2026-08-31 and made the standard price on
# 2026-08-22 (platform.claude.com pricing: "the previously scheduled increase
# to $3/$15 ... will not occur"). Opus 5.5 lists at $4/$20, below the Opus
# family. Each needle set is tested ahead of its family.
PRICE_OVERRIDE = (
    (("sonnet-5", "sonnet 5"), (2.00, 10.00)),
    (("opus-5-5", "opus 5.5"), (4.00, 20.00)),
)

# An effort variant's transcript carries its own agentType (<type>-routine)
# while its ledger records carry the base author, so a window lookup joins a
# variant's rows to its base type.
VARIANT_SUFFIX = "-routine"

# Cache multipliers relative to the family's base input price. The 5m/1h
# write split is read from usage.cache_creation when present.
CACHE_READ_MULT = 0.10
CACHE_WRITE_5M_MULT = 1.25
CACHE_WRITE_1H_MULT = 2.00

# Per-model cache-read overrides, matched as a lowercase substring (id or
# display-name form) before the flat multiplier: Fable 5.1 and Mythos 5.1
# price cache reads at 0.025x base input ($0.25/MTok) and Opus 5.5 at 0.05x
# ($0.20/MTok), both per platform.claude.com pricing. The write multipliers
# carry no per-model split.
CACHE_READ_MULT_OVERRIDE = (
    (("fable-5-1", "fable 5.1"), 0.025),
    (("mythos-5-1", "mythos 5.1"), 0.025),
    (("opus-5-5", "opus 5.5"), 0.05),
)

TOKENS_PER_MILLION = 1_000_000
TOKENS_PER_THOUSAND = 1_000
TRANSCRIPT_PREFIX = "agent-"
TRANSCRIPT_SUFFIX = ".jsonl"
META_SUFFIX = ".meta.json"

Row = tuple[object, dict[str, Any]]


def _model_name(model: object) -> str:
    return model.lower() if isinstance(model, str) else ""


def _rate(model: object) -> tuple[float, float]:
    """Return the (input, output) $/Mtok rate of a model; an unrecognized model prices at zero."""
    # An override wins over the family table. PRICE's insertion order fixes
    # the scan; the family names are disjoint substrings, so order never
    # changes a match.
    name = _model_name(model)
    for needles, rate in PRICE_OVERRIDE:
        if any(needle in name for needle in needles):
            return rate
    for family, rate in PRICE.items():
        if family in name:
            return rate
    return (0.0, 0.0)


def _read_mult(model: object) -> float:
    """Return the cache-read multiplier of a model; a per-model override wins over the flat rate."""
    name = _model_name(model)
    for needles, mult in CACHE_READ_MULT_OVERRIDE:
        if any(needle in name for needle in needles):
            return mult
    return CACHE_READ_MULT


def _count(value: object) -> int:
    # Any shape but a positive int reads as 0, so a malformed transcript
    # value degrades instead of raising mid-render.
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
        else 0
    )


class Usage(NamedTuple):
    """The six token counts of one usage dict."""

    input: int
    output: int
    cache_read: int
    cache_creation: int
    write_5m: int
    write_1h: int


def _usage_fields(usage: dict[str, Any]) -> Usage:
    """Read the six token counts from one usage dict."""
    # With the TTL split present, a missing 5m key derives as the flat total
    # minus the 1h count, never negative; falling back to the flat total would
    # count the 1h tokens twice. Without the split, the flat total is a
    # 5-minute write. Either way write_5m + write_1h == cache_creation.
    cache_creation = _count(usage.get("cache_creation_input_tokens"))
    split = usage.get("cache_creation")
    if isinstance(split, dict):
        write_1h = _count(split.get("ephemeral_1h_input_tokens"))
        write_5m = split.get("ephemeral_5m_input_tokens")
        write_5m = (
            max(cache_creation - write_1h, 0) if write_5m is None else _count(write_5m)
        )
    else:
        write_5m, write_1h = cache_creation, 0
    return Usage(
        _count(usage.get("input_tokens")),
        _count(usage.get("output_tokens")),
        _count(usage.get("cache_read_input_tokens")),
        cache_creation,
        write_5m,
        write_1h,
    )


def aggregate(rows: Iterable[Row]) -> dict[str, Any]:
    """Fold (model, usage) rows into the totals a consumer renders: tokens, cost, and cache percentages."""
    # Each row prices at its own model's rate, so a mixed fleet is billed per
    # message. savings_pct measures the cache-eligible spend against a
    # no-cache baseline and is None without cache activity. Pure: no I/O.
    total: dict[str, Any] = {
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_creation": 0,
        "cc5": 0,
        "cc1": 0,
        "cost": 0.0,
    }
    cache_actual = 0.0
    for model, usage in rows:
        counts = _usage_fields(usage)
        total["input"] += counts.input
        total["output"] += counts.output
        total["cache_read"] += counts.cache_read
        total["cache_creation"] += counts.cache_creation
        total["cc5"] += counts.write_5m
        total["cc1"] += counts.write_1h
        input_rate, output_rate = _rate(model)
        read_mult = _read_mult(model)
        total["cost"] += (
            counts.input * input_rate
            + counts.output * output_rate
            + counts.cache_read * input_rate * read_mult
            + counts.write_5m * input_rate * CACHE_WRITE_5M_MULT
            + counts.write_1h * input_rate * CACHE_WRITE_1H_MULT
        ) / TOKENS_PER_MILLION
        cache_actual += (
            counts.cache_read * read_mult
            + counts.write_5m * CACHE_WRITE_5M_MULT
            + counts.write_1h * CACHE_WRITE_1H_MULT
        )
    total_input = total["input"] + total["cache_read"] + total["cache_creation"]
    total["total_input"] = total_input
    total["hit_pct"] = (
        round(total["cache_read"] * 100 / total_input) if total_input > 0 else 0
    )
    base = total["cache_read"] + total["cc5"] + total["cc1"]
    total["savings_pct"] = (
        round((base - cache_actual) * 100 / base) if base > 0 else None
    )
    return total


def parse_ts(ts: object) -> float | None:
    """Parse an ISO-8601 timestamp to POSIX seconds, or None; a bare stamp reads as UTC."""
    # Mirrors the ledger's timestamp reading, so a board window and a
    # transcript message compare on one clock.
    if not isinstance(ts, str):
        return None
    text = ts.strip()
    if text[-1:] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        stamp = datetime.datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.UTC)
    return stamp.timestamp()


def _merge_usage(held: dict[str, Any], usage: dict[str, Any]) -> None:
    # Input and cache fields repeat identically across a call's records while
    # interim records carry partial output counts, so the per-field maximum
    # is the call's full figure. Nested dicts (the TTL split) merge the same way.
    for field, value in usage.items():
        prev = held.get(field)
        if isinstance(value, dict):
            if not isinstance(prev, dict):
                held[field] = dict(value)
            else:
                _merge_usage(prev, value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            if (
                not isinstance(prev, (int, float))
                or isinstance(prev, bool)
                or value > prev
            ):
                held[field] = value
        elif field not in held:
            held[field] = value


def iter_assistant(
    path: str | os.PathLike[str],
) -> Iterator[tuple[object, dict[str, Any], object]]:
    """Yield (model, usage, timestamp) once per API call in a transcript; an unreadable file yields nothing."""
    # The runtime writes one assistant record per content block, each
    # repeating the call's usage under one request id; counting every record
    # would price a call once per block. Records sharing a request id (or,
    # without one, a message id) merge; a record with neither counts alone.
    try:
        handle = Path(path).open(encoding="utf-8", errors="replace")
    except OSError:
        return
    calls: dict[str, tuple[object, dict[str, Any], object]] = {}
    unkeyed = 0
    with handle:
        for line in handle:
            call = _assistant_call(line)
            if call is None:
                continue
            key, model, usage, stamp = call
            if key is None:
                unkeyed += 1
                key = f"~unkeyed-{unkeyed}"
            held = calls.get(key)
            if held is None:
                merged: dict[str, Any] = {}
                _merge_usage(merged, usage)
                calls[key] = (model, merged, stamp)
            else:
                _merge_usage(held[1], usage)
    yield from calls.values()


def _assistant_call(
    line: str,
) -> tuple[str | None, object, dict[str, Any], object] | None:
    stripped = line.strip()
    if not stripped:
        return None
    try:
        record = json.loads(stripped)
    except ValueError:
        return None
    if not isinstance(record, dict) or record.get("type") != "assistant":
        return None
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None
    key = record.get("requestId") or message.get("id")
    keyed = key if isinstance(key, str) and key else None
    return keyed, message.get("model"), usage, record.get("timestamp")


def _is_transcript(name: str) -> bool:
    return name.startswith(TRANSCRIPT_PREFIX) and name.endswith(TRANSCRIPT_SUFFIX)


def _sorted_names(directory: Path) -> list[str]:
    return sorted(entry.name for entry in directory.iterdir())


def session_transcripts(parent_path: str, session_id: str) -> list[str]:
    """List the parent transcript and every subagent transcript of its session; a missing piece is absent."""
    files: list[str] = []
    if parent_path and Path(parent_path).is_file():
        files.append(parent_path)
    if parent_path and session_id:
        subagents = Path(parent_path).parent / session_id / "subagents"
        if subagents.is_dir():
            files.extend(
                str(subagents / name)
                for name in _sorted_names(subagents)
                if _is_transcript(name)
            )
    return files


def session_totals(parent_path: str, session_id: str) -> dict[str, Any]:
    """Return the totals across the whole session tree, parent and subagents."""
    rows: list[Row] = [
        (model, usage)
        for path in session_transcripts(parent_path, session_id)
        for model, usage, _stamp in iter_assistant(path)
    ]
    return aggregate(rows)


def default_projects_root() -> str:
    """Return the Claude Code projects directory, or the CLAUDE_PROJECTS_ROOT override when set."""
    override = os.environ.get("CLAUDE_PROJECTS_ROOT")
    if override:
        return override
    try:
        home = Path.home()
    except RuntimeError:
        home = Path("~")
    return str(home / ".claude" / "projects")


def slug_for(cwd: str) -> str:
    """Encode a project path the way Claude Code names its project directory."""
    # Every non-alphanumeric character maps to '-'; the statusline and
    # cache-report resolvers use the same rule.
    return re.sub(r"[^a-zA-Z0-9]", "-", cwd)


def subagent_transcripts(
    projects_root: str, slug: str
) -> list[tuple[str, str | None, str]]:
    """List (transcript path, agent type, session id) for every subagent transcript of a project."""
    base = Path(projects_root) / slug
    if not base.is_dir():
        return []
    found: list[tuple[str, str | None, str]] = []
    for session in _sorted_names(base):
        subagents = base / session / "subagents"
        if not subagents.is_dir():
            continue
        found.extend(
            (str(subagents / name), _agent_type(subagents / name), session)
            for name in _sorted_names(subagents)
            if _is_transcript(name)
        )
    return found


def _agent_type(transcript: Path) -> str | None:
    # The agent-*.meta.json sidecar names the type; without a readable one
    # the transcript cannot be attributed and the index drops it.
    meta = transcript.with_suffix(META_SUFFIX)
    try:
        parsed = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    agent_type: str | None = (
        parsed.get("agentType") if isinstance(parsed, dict) else None
    )
    return agent_type


class Dispatch(NamedTuple):
    """One subagent transcript: the span of its placeable stamps and every row it holds."""

    first: float
    last: float
    rows: list[Row]


def _window(
    start_secs: float | None, end_secs: float | None
) -> tuple[float, float] | None:
    # An unbounded or reversed window selects nothing.
    if start_secs is None or end_secs is None or end_secs < start_secs:
        return None
    return start_secs, end_secs


def _last_written_before(path: str, since_secs: float | None) -> bool:
    # A file's messages cannot postdate its last write, so a transcript
    # finished before the earliest window of interest can never overlap one.
    # Pruning on the last write, never the first message, keeps a dispatch
    # that began before the bound but ran into it.
    if since_secs is None:
        return False
    try:
        return Path(path).stat().st_mtime < since_secs
    except OSError:
        return True


class WindowIndex:
    """Subagent usage across a project's transcripts, indexed once and queried by agent type and window."""

    def __init__(
        self,
        projects_root: str | None = None,
        slug: str | None = None,
        cwd: str | None = None,
        since_secs: float | None = None,
    ) -> None:
        """Index every attributable subagent transcript of the project, skipping those last written before since_secs."""
        projects_root = projects_root or default_projects_root()
        if slug is None:
            slug = slug_for(cwd if cwd is not None else str(Path.cwd()))
        self.rows: list[tuple[str, str, float, object, dict[str, Any]]] = []
        self._by_type: dict[str, list[Dispatch]] = {}
        self._rows_by_type: dict[str, list[tuple[float, object, dict[str, Any]]]] = {}
        for path, agent_type, session in subagent_transcripts(projects_root, slug):
            if not agent_type or _last_written_before(path, since_secs):
                continue
            self._index(path, agent_type, session)

    def _index(self, path: str, agent_type: str, session: str) -> None:
        # The file is the unit: a message with an unparseable stamp still
        # counts toward its dispatch, it only cannot help place it. A file
        # with no placeable stamp has no span and no window can select it.
        file_rows: list[Row] = []
        stamps: list[float] = []
        for model, usage, stamp in iter_assistant(path):
            file_rows.append((model, usage))
            secs = parse_ts(stamp)
            if secs is None:
                continue
            self.rows.append((agent_type, session, secs, model, usage))
            self._rows_by_type.setdefault(agent_type, []).append((secs, model, usage))
            stamps.append(secs)
        if stamps:
            self._by_type.setdefault(agent_type, []).append(
                Dispatch(min(stamps), max(stamps), file_rows)
            )

    def _overlapping(
        self, agent_type: str, start_secs: float, end_secs: float
    ) -> list[Row]:
        # Whole-file attribution: a dispatch's first message carries the
        # inbound context and lands before its dispatch-start, so a window
        # selects the files it overlaps and sums each whole. Exact only while
        # no two dispatches of one agent type overlap in time, which the
        # roster's fan-out across distinct types is what guarantees.
        rows: list[Row] = []
        for key in (agent_type, agent_type + VARIANT_SUFFIX):
            for dispatch in self._by_type.get(key, ()):
                if dispatch.first <= end_secs and dispatch.last >= start_secs:
                    rows.extend(dispatch.rows)
        return rows

    def window_types(
        self, agent_type: str, start_secs: float | None, end_secs: float | None
    ) -> tuple[str, ...] | None:
        """Return the exact agent types, base or effort variant, with a transcript overlapping the window."""
        # The ledger cannot say which tier ran, since the variant claims the
        # base author; the transcript's agentType can. Two entries mean both
        # tiers ran, and the caller draws no single verdict.
        window = _window(start_secs, end_secs)
        if window is None:
            return None
        start, end = window
        present = []
        for key in (agent_type, agent_type + VARIANT_SUFFIX):
            dispatches = self._by_type.get(key, ())
            if any(d.first <= end and d.last >= start for d in dispatches):
                present.append(key)
        return tuple(present)

    def totals(
        self, agent_type: str, start_secs: float | None, end_secs: float | None
    ) -> dict[str, Any] | None:
        """Return the totals of one agent type's dispatches overlapping the window, or None."""
        window = _window(start_secs, end_secs)
        if window is None:
            return None
        rows = self._overlapping(agent_type, *window)
        if not rows:
            return None
        return aggregate(rows)

    def slice_totals(
        self,
        agent_types: Iterable[Any],
        start_secs: float | None,
        end_secs: float | None,
    ) -> dict[str, Any] | None:
        """Return the totals of the named agent types' messages inside the window, or None."""
        # Message-windowed, not whole-file: this window bounds a slice, and a
        # dispatch may serve a batched sibling slice, so whole files would
        # price it on both boards. The header therefore prices a dispatch by
        # a different rule than the lines.
        window = _window(start_secs, end_secs)
        if window is None:
            return None
        start, end = window
        rows: list[Row] = []
        expanded = [
            key
            for agent_type in dict.fromkeys(agent_types)
            for key in (agent_type, str(agent_type) + VARIANT_SUFFIX)
        ]
        for agent_type in expanded:
            rows.extend(
                (model, usage)
                for secs, model, usage in self._rows_by_type.get(agent_type, ())
                if start <= secs <= end
            )
        if not rows:
            return None
        return aggregate(rows)


def format_tokens(n: float) -> str:
    """Format a token count compactly: 1.2M, 34k, 567."""
    # The statusline formats the same way, so the board and the statusline read alike.
    count = int(n)
    if count >= TOKENS_PER_MILLION:
        return f"{count / TOKENS_PER_MILLION:.1f}M"
    if count >= TOKENS_PER_THOUSAND:
        return f"{count / TOKENS_PER_THOUSAND:.0f}k"
    return str(count)


def format_cost(x: float) -> str:
    """Format list-price dollars to the cent, without a symbol."""
    return f"{x:.2f}"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="accounting.py",
        description="Claude Code usage accounting; emits JSON totals.",
    )
    sub = parser.add_subparsers(dest="mode", required=True)
    session = sub.add_parser(
        "session", help="totals across a session tree (parent + subagents)"
    )
    session.add_argument("--parent", required=True, help="the parent transcript path")
    session.add_argument(
        "--session-id", default="", help="the session id (subagent dir name)"
    )
    window = sub.add_parser(
        "window", help="totals for one agentType within a time window"
    )
    window.add_argument("--agent-type", required=True)
    window.add_argument("--start", required=True, help="ISO-8601 window start")
    window.add_argument("--end", required=True, help="ISO-8601 window end")
    window.add_argument(
        "--slug",
        help="project slug; pass as --slug=<value> since a "
        "real slug begins with '-' (default: derived from --cwd)",
    )
    window.add_argument(
        "--cwd", help="project dir to derive the slug from (default: cwd)"
    )
    window.add_argument("--projects-root", help="default: ~/.claude/projects")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Print the requested totals as JSON and return the exit code."""
    args = _parser().parse_args(argv)
    result: dict[str, Any] | None
    if args.mode == "session":
        result = session_totals(args.parent, args.session_id)
    else:
        index = WindowIndex(
            projects_root=args.projects_root, slug=args.slug, cwd=args.cwd
        )
        result = index.totals(args.agent_type, parse_ts(args.start), parse_ts(args.end))
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
