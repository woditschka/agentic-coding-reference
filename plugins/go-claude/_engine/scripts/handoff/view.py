#!/usr/bin/env python3
"""handoff/view.py — the human-facing board renderer (ADR 2026-07-17 runtime-package-layout).

Trust class: a middle layer over handoff.records and handoff.schema, beside
handoff.routing. It owns the entire board: the TTY renderer (render_view), its
Markdown twin (render_view_md), the shared grouping (rounds, implement sessions,
hoisted siblings, the slice walk), and the cost-overlay glue — the guarded
accounting import and _build_cost_lookup, whose only consumers are this
module's overlay and the CLI's view command. The board reads; it never gates.

This module stays whole: the primitives/composition seam is deferred to the
typed-view decision (parked in ADR 2026-07-17 runtime-package-layout). Imports
handoff.records and handoff.schema only; never handoff.routing. Stdlib only,
Python 3.11+.
"""

import datetime
import re
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Any, Protocol, TypeAlias, cast

from .records import DESIGNER, GRADER, IMPLEMENTER, PRODUCT
from .schema import LogEntry, _sanitize

# The board's optional cost overlay (view). accounting.py is vendored
# alongside this script; when it or the Claude Code transcripts it reads are
# absent (another tool, swept history), the board simply omits per-step cost —
# it never gates on it. Every other subcommand runs without it, so the guard
# catches any import-time failure, not just a missing module: a truncated or
# corrupted vendored copy (SyntaxError) must not take the writer path down.
# Typed module-or-None: now that the vendored accounting module is strict-clean
# and followed for real (ADR 2026-07-17 tail slice), the fallback needs an
# explicit ModuleType | None so the None branch type-checks. The name stays a
# module global (re-exported by handoff/__init__.py), so `handoff.accounting`
# and `from handoff.view import accounting` keep working. The import stays
# absolute: accounting.py sits at the scripts root, on sys.path in every
# execution context (ADR 2026-07-17 runtime-package-layout).
accounting: ModuleType | None
try:
    import accounting as _accounting
except Exception:  # noqa: BLE001  # pragma: no cover
    accounting = None
else:
    accounting = _accounting

# One rendered view span: display text paired with its ANSI code, or None for
# an uncoded span. Span-building locals are annotated list[Span] so a literal
# stays covariantly assignable and concatenates with the shared tail spans.
Span: TypeAlias = tuple[str, str | None]


class _SliceLookup(Protocol):
    """The header roll-up: total cost of many authors over one slice window."""

    def __call__(
        self, agent_types: Any, start_rec: Any, end_rec: Any
    ) -> list[Span] | None: ...


class _CostLookup(Protocol):
    """The board's cost overlay: one author over one window, callable, plus the
    whole-slice roll-up hung off it as slice_lookup (see _build_cost_lookup)."""

    slice_lookup: _SliceLookup

    def __call__(
        self, agent_type: Any, start_rec: Any, end_rec: Any
    ) -> list[Span] | None: ...


# --- view: one-screen slice status — header, convergence matrix, timeline ---

COORDINATOR = "pipeline-coordinator"

# Short display labels. Reviewers not named here fall back to stripping the
# -reviewer suffix, so a layout.toml extra reviewer gets a sensible label;
# any other unknown author renders by its raw name.
AGENT_LABELS = {
    IMPLEMENTER: "implementer",
    DESIGNER: "design",
    PRODUCT: "prd-expert",
    COORDINATOR: "coord",
    GRADER: "grader",
}

VERDICT_GLYPHS: dict[str | None, tuple[str, str]] = {
    "approved": ("✔", "32"),
    "changes_requested": ("✎", "33"),
    "blocked": ("✖", "31"),
}
TAG_COLORS = {
    "autofix": "33",
    "blocked": "31",
    "escalate": "1;31",
    "clarify": "36",
    "truncation": "90",
}
FACET_COLORS = {"clear": "32", "concern": "31", "unknown": "33"}
GRADE_COLORS = {"clear": "32", "concern": "31"}
GREEN = "32"
DIM = "90"
BOLD = "1"
VIEW_WIDTH = 72
# Topic-anchor glyph for an elapsed-time value; the cost tail, when present,
# joins it (it never renders without the duration).
DUR_MARK = "◷"


# `_style` is the view renderer's single choke point — every line it emits is
# built through `_style`, which runs the imported `_sanitize` before adding any
# escape codes, so no unsanitized text ever leaves the view. Span builders
# sanitize again ahead of their alignment math; `_style` is the backstop that
# makes a bypass impossible, not a redundant second pass.


def _style(text: str, code: str | None, color: bool) -> str:
    text = _sanitize(text)
    if not color or not code:
        return text
    return f"\033[{code}m{text}\033[0m"


def _line(spans: Sequence[Span], color: bool) -> str:
    """Join (text, code) spans into one line; trailing blanks are stripped
    so plain and colored output stay byte-alignable."""
    clean: list[Span] = [(_sanitize(t), c) for t, c in spans if t]
    while clean and not clean[-1][0].strip():
        clean.pop()
    if clean:
        text, code = clean[-1]
        clean[-1] = (text.rstrip(), code)
    return "".join(_style(t, c, color) for t, c in clean if t)


def _pad(spans: Sequence[Span], width: int, color: bool) -> str:
    """Render spans and pad on plain-text length — pad first, color after,
    so columns align identically with and without escapes."""
    spans = [(_sanitize(t), c) for t, c in spans]
    plain_len = sum(len(t) for t, _ in spans)
    rendered = "".join(_style(t, c, color) for t, c in spans)
    return rendered + " " * max(0, width - plain_len)


def agent_label(author: Any) -> str:
    if not isinstance(author, str) or not author:
        return "?"
    if author in AGENT_LABELS:
        return AGENT_LABELS[author]
    if author.endswith("-reviewer"):
        return _sanitize(author[: -len("-reviewer")])
    return _sanitize(author)


def short_location(location: Any, limit: int = 38) -> str:
    if not isinstance(location, str):
        return ""
    loc = location.split(" (")[0].strip()
    loc = re.sub(r"^.*/", "", loc)
    return loc[:limit]


def gist(text: Any, limit: int = 75) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[: limit - 1] + "…" if len(cleaned) > limit else cleaned


def review_rounds(recs: list[dict[str, Any]]) -> list[dict[str, dict[str, Any]]]:
    """Group review-feedback into rounds by append order: a reviewer
    reappearing starts a new round. Re-reviews usually follow a fresh
    build-pass, but a doc-only round may not — reappearance covers both."""
    rounds: list[dict[str, dict[str, Any]]] = []
    current: dict[str, dict[str, Any]] = {}
    for rec in recs:
        if rec.get("type") != "review-feedback":
            continue
        author_val = rec.get("author")
        author = author_val if isinstance(author_val, str) else "?"
        if author in current:
            rounds.append(current)
            current = {}
        current[author] = rec
    if current:
        rounds.append(current)
    return rounds


def _findings_of(rec: dict[str, Any]) -> list[dict[str, Any]]:
    findings = rec.get("findings")
    return (
        [f for f in findings if isinstance(f, dict)]
        if isinstance(findings, list)
        else []
    )


def _verdict_glyph(verdict: Any) -> tuple[str, str]:
    """Glyph + color for a review verdict. Record data is untrusted: a
    non-string (unhashable) verdict must fall through, never raise."""
    if not isinstance(verdict, str):
        verdict = None
    return VERDICT_GLYPHS.get(verdict, ("•", DIM))


def _plural(n: int, word: str) -> str:
    if n == 1:
        return f"1 {word}"
    return f"{n} {word}" + ("es" if word.endswith("s") else "s")


def _render_box(span_lines: Sequence[Sequence[Span]], color: bool) -> list[str]:
    width = max(sum(len(t) for t, _ in spans) for spans in span_lines)
    out = [_style("╭" + "─" * (width + 2) + "╮", DIM, color)]
    for spans in span_lines:
        out.append(
            _style("│ ", DIM, color)
            + _pad(spans, width, color)
            + _style(" │", DIM, color)
        )
    out.append(_style("╰" + "─" * (width + 2) + "╯", DIM, color))
    return out


def _slice_tail_spans(
    recs: list[dict[str, Any]], cost_lookup: _CostLookup | None
) -> list[Span]:
    """The header's whole-slice roll-up spans, or []. Elapsed runs first
    record to last; the cost aggregates every author the slice's own records
    name over that window, so a foreign agent type active in the same span
    never pollutes the figure. The line renders only when the cost
    attributes: unlike a step, a duration-only roll-up would add a header
    line that restates what the timeline already shows."""
    timed = [rec for rec in recs if _ts_seconds(rec) is not None]
    if len(timed) < 2:
        return []

    def _secs(rec: dict[str, Any]) -> float:
        # timed holds only records with a parseable ts, so this never fires.
        s = _ts_seconds(rec)
        assert s is not None
        return s

    first = min(timed, key=_secs)
    last = max(timed, key=_secs)
    dur = _duration(first, last)
    slice_lookup = getattr(cost_lookup, "slice_lookup", None)
    if not dur or slice_lookup is None:
        return []
    authors = [rec.get("author") for rec in recs if isinstance(rec.get("author"), str)]
    ctail = slice_lookup(authors, first, last)
    if not ctail:
        return []
    return [(DUR_MARK + " " + dur, GREEN)] + list(ctail)


def _slice_stats(
    recs: list[dict[str, Any]],
) -> tuple[str | None, Any, int, int]:
    """The header's slice facts — (title, grade, passes, failures) — shared by
    the box and the Markdown header."""
    title: str | None = None
    grade: Any = None
    for rec in recs:
        if rec.get("type") == "prd-entry" and isinstance(rec.get("title"), str):
            title = rec["title"]
        elif rec.get("type") == "grader-verdict":
            grade = rec.get("verdict")
    passes = sum(1 for r in recs if r.get("type") == "build-pass")
    failures = sum(1 for r in recs if r.get("type") == "build-failure")
    return title, grade, passes, failures


def _summary_spans(
    rounds: Sequence[dict[str, dict[str, Any]]],
    passes: int,
    failures: int,
    grade: Any,
    auto_grade: bool,
) -> list[Span]:
    """The header's summary spans (box line 2); the Markdown header joins the
    same span texts, so the two renderers cannot drift."""
    line2: list[Span] = [
        (_plural(len(rounds), "review round"), DIM),
        ((" · " + _plural(passes, "build-pass")), DIM),
    ]
    if failures:
        line2 += [(" · ", DIM), (_plural(failures, "build-failure"), "31")]
    if isinstance(grade, str):
        line2 += [
            (" · grade ", DIM),
            (grade.upper(), f"{BOLD};{GRADE_COLORS.get(grade, DIM)}"),
        ]
    elif auto_grade:
        line2 += [(" · no grade yet", DIM)]
    else:
        # auto_grade = false: no grade is coming; "yet" would read as pending.
        line2 += [(" · grading disabled", DIM)]
    return line2


def _render_header(
    req_id: str | None,
    recs: list[dict[str, Any]],
    rounds: Sequence[dict[str, dict[str, Any]]],
    others: Sequence[str],
    color: bool,
    auto_grade: bool = True,
    slice_tail: Sequence[Span] = (),
) -> list[str]:
    title, grade, passes, failures = _slice_stats(recs)
    line1: list[Span] = [(req_id or "(no req_id)", BOLD)]
    if title:
        line1 += [("  ", None), (gist(title, 52), None)]
    span_lines = [line1, _summary_spans(rounds, passes, failures, grade, auto_grade)]
    if slice_tail:
        span_lines.append(list(slice_tail))
    if others:
        span_lines.append([("also in log: " + ", ".join(others), DIM)])
    return _render_box(span_lines, color)


def _matrix_cell(rec: dict[str, Any] | None) -> list[Span]:
    if rec is None:
        return [("·", DIM)]
    glyph, vcol = _verdict_glyph(rec.get("verdict"))
    spans: list[Span] = [(glyph, vcol)]
    n = len(_findings_of(rec))
    if n:
        spans.append((f" ({n})", DIM))
    return spans


def _matrix_authors(
    rounds: Sequence[dict[str, dict[str, Any]]], roster: Sequence[str]
) -> list[str]:
    """Matrix row order: the roster first, then off-roster authors in round
    appearance order. Shared by both renderers."""
    authors = list(roster)
    for rnd in rounds:
        for author in rnd:
            if author not in authors:
                authors.append(author)
    return authors


def _render_matrix(
    rounds: Sequence[dict[str, dict[str, Any]]], roster: Sequence[str], color: bool
) -> list[str]:
    if not rounds:
        return []
    authors = _matrix_authors(rounds, roster)
    label_w = max(len(agent_label(a)) for a in authors)
    cells: dict[tuple[str, int], list[Span]] = {}
    col_w: list[int] = []
    for i, rnd in enumerate(rounds):
        width = len(f"R{i + 1}")
        for author in authors:
            spans = _matrix_cell(rnd.get(author))
            cells[(author, i)] = spans
            width = max(width, sum(len(t) for t, _ in spans))
        col_w.append(width)
    header = " " * (label_w + 2) + "  ".join(
        f"R{i + 1}".ljust(col_w[i]) for i in range(len(rounds))
    )
    lines = [_style(header.rstrip(), DIM, color)]
    for author in authors:
        row = agent_label(author).ljust(label_w) + "  "
        row += "  ".join(
            _pad(cells[(author, i)], col_w[i], color) for i in range(len(rounds))
        )
        lines.append(row.rstrip())
    return lines


def _ts_hhmm(rec: dict[str, Any]) -> str | None:
    """HH:MM from an ISO ts, or None. Distinguishes consecutive gate
    separators that are otherwise identical (same checks, same author)."""
    ts = rec.get("ts")
    if isinstance(ts, str) and len(ts) >= 16 and ts[10] == "T":
        return ts[11:16]
    return None


def _parse_iso_seconds(ts: str) -> float | None:
    """ISO-8601 string → POSIX seconds, or None. Pure — parses the fixed
    string (no wall-clock); a bare ts with no offset is read as UTC so the
    diff stays deterministic across machines. Fallback only: with the
    vendored accounting module present, its parse_ts (the same contract) is used
    instead, so board windows and transcript timestamps share one parser."""
    t = ts.strip()
    if t[-1:] in ("Z", "z"):  # accept either Zulu casing before fromisoformat
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    return dt.timestamp()


def _ts_seconds(rec: dict[str, Any]) -> float | None:
    """A record's ts as POSIX seconds, or None."""
    ts = rec.get("ts")
    if not isinstance(ts, str):
        return None
    if accounting is not None:
        secs: float | None = accounting.parse_ts(ts)
        return secs
    return _parse_iso_seconds(ts)


def _fmt_duration(seconds: float) -> str:
    """Compact elapsed: seconds under a minute, whole minutes under an hour,
    then hours and minutes. A status board wants the magnitude, not precision."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def _duration(start_rec: Any, end_rec: Any) -> str | None:
    """Elapsed from start_rec to end_rec, formatted, or None when either ts is
    missing/unparseable or the pair is out of order (a clock skew guard)."""
    if not (isinstance(start_rec, dict) and isinstance(end_rec, dict)):
        return None
    a, b = _ts_seconds(start_rec), _ts_seconds(end_rec)
    if a is None or b is None or b < a:
        return None
    return _fmt_duration(b - a)


def _producer_dispatch(
    rec: dict[str, Any], entries: list[LogEntry], line: int
) -> dict[str, Any] | None:
    """The dispatch-start that spawned rec's author — the nearest preceding
    dispatch-start with the same author IN THE SAME SLICE, whose ts is the
    step's start. The req_id match keeps a step from pairing with an earlier
    slice's dispatch when its own is missing. `line` is rec's own line number
    (the caller holds it from the slice walk).

    A dispatch times only the FIRST record of rec's type it produces: a
    re-engaged author (a SendMessage continue) appends no fresh dispatch, so
    pairing its round-2 record with the round-1 dispatch would span other
    steps' work and re-sum spend already shown on the round-1 line. An
    intervening same-author, same-type record therefore unpairs rec — no
    duration, matching the discipline of a missing timestamp."""
    author = rec.get("author")
    if not author:
        return None
    req_id = rec.get("req_id")
    rtype = rec.get("type")
    best: dict[str, Any] | None = None
    best_no: int | None = None
    for no, r in entries:
        if no >= line:
            break
        if (
            r.get("type") == "dispatch-start"
            and r.get("author") == author
            and r.get("req_id") == req_id
        ):
            best, best_no = r, no
    if best is None:
        return None
    # best and best_no are assigned together, so a non-None best means a
    # non-None best_no; assert it to narrow before the comparison.
    assert best_no is not None
    for no, r in entries:
        if no <= best_no:
            continue
        if no >= line:
            break
        if (
            r.get("type") == rtype
            and r.get("author") == author
            and r.get("req_id") == req_id
        ):
            return None  # the dispatch already timed that earlier record
    return best


def _rule_line(core: Sequence[Span], color: bool) -> str:
    core = [(_sanitize(t), c) for t, c in core]
    plain_len = sum(len(t) for t, _ in core)
    body = "".join(_style(t, c, color) for t, c in core)
    fill = "─" * max(0, VIEW_WIDTH - plain_len - 4)
    return _style("── ", DIM, color) + body + " " + _style(fill, DIM, color)


def _finding_lines(rec: dict[str, Any], color: bool, verbose: bool) -> list[str]:
    lines: list[str] = []
    findings = _findings_of(rec)
    for i, finding in enumerate(findings):
        last = i == len(findings) - 1
        conn = "└" if last else "├"
        tag = finding.get("tag")
        tag_text = tag if isinstance(tag, str) and tag else "?"
        desc = finding.get("description")
        spans: list[Span] = [
            ("  ", None),
            (conn + " ", DIM),
            (f"[{tag_text}]", TAG_COLORS.get(tag_text, DIM)),
            (" ", None),
            (short_location(finding.get("location")), BOLD),
            ("  ", None),
            (desc if verbose and isinstance(desc, str) else gist(desc), DIM),
        ]
        lines.append(_line(spans, color))
        if verbose and isinstance(finding.get("fix"), str) and finding["fix"].strip():
            bar = "  " if last else "│ "
            lines.append(
                _line(
                    [("  " + bar + "  ", DIM), ("fix: " + finding["fix"].strip(), DIM)],
                    color,
                )
            )
    return lines


def _facet_lines(rec: dict[str, Any], color: bool) -> list[str]:
    facets = rec.get("facets")
    if not isinstance(facets, dict) or not facets:
        return []
    name_w = max(len(str(name)) for name in facets)
    lines: list[str] = []
    for name, facet in facets.items():
        facet = facet if isinstance(facet, dict) else {}
        verdict = facet.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        lines.append(
            _line(
                [
                    ("  · ", DIM),
                    (str(name).ljust(name_w), None),
                    ("  ", None),
                    (verdict_text.ljust(7), FACET_COLORS.get(verdict_text, DIM)),
                    ("  ", None),
                    (gist(facet.get("note"), 48), DIM),
                ],
                color,
            )
        )
    return lines


def _consultation_peer(entries: list[LogEntry], response: dict[str, Any]) -> Any:
    """The requesting author a consultation-response returns to, via its
    in_response_to line pointer; None when the pointer dangles."""
    target = response.get("in_response_to")
    for no, rec in entries:
        if no == target and rec.get("type") == "consultation-request":
            return rec.get("author")
    return None


def _fix_sources(
    rec: dict[str, Any], by_no: dict[int, dict[str, Any]]
) -> tuple[list[str], int] | None:
    """The non-approved review-feedback records a dispatch answers, as
    (reviewer labels, finding count) — or None when it answers none. A fresh
    implement dispatch, reviewer fan-out, and the designer's triage all answer
    no review and return None; only a fix (the implementer or a doc-owner)
    returns sources. `by_no` is the render's one line→record map, built once
    in render_view."""
    targets = rec.get("responding_to")
    if not isinstance(targets, list):
        return None
    sources = [
        by_no[t]
        for t in targets
        if isinstance(t, int)
        and isinstance(by_no.get(t), dict)
        and by_no[t].get("type") == "review-feedback"
        and by_no[t].get("verdict") != "approved"
    ]
    if not sources:
        return None
    reviewers: list[str] = []
    for s in sources:
        label = agent_label(s.get("author"))
        if label not in reviewers:
            reviewers.append(label)
    return reviewers, sum(len(_findings_of(s)) for s in sources)


def _fix_dispatch_lines(
    rec: dict[str, Any], by_no: dict[int, dict[str, Any]], color: bool
) -> list[str]:
    """A non-implementer fix — a doc-owner (prd-expert, designer) spawned to
    answer a reviewer's findings — renders as a flat `↻ fix` line linking it to
    that reviewer, the one causal link the timeline would otherwise lose. The
    implementer's fix is not flat: it opens an implement session (see
    `_implement_session`). Reviewer fan-out and the designer's triage dispatch
    answer no review, so they stay suppressed as noise."""
    src = _fix_sources(rec, by_no)
    if not src:
        return []
    reviewers, n = src
    spans: list[Span] = [
        ("↻ ", "33"),
        ("fix  ", DIM),
        (agent_label(rec.get("author")), BOLD),
        ("  ← ", DIM),
        (", ".join(reviewers), DIM),
    ]
    if n:
        spans.append((f"  ({_plural(n, 'finding')})", DIM))
    # No duration: a doc-owner fix emits no record, so it has no dispatch →
    # output span like the timed steps. Its findings → re-approval latency is a
    # different measure (it folds in the rebuild and re-review), so pairing it
    # with the same ◷ marker would misread as work time — left off by design.
    return [_line(spans, color)]


def _tail_spans(duration: str | None, cost_tail: Sequence[Span] | None) -> list[Span]:
    """The `◷<duration>` (plus optional cost) spans every timed line shares.
    The cost overlay never rides without the duration: both derive from the
    same dispatch→record window, so a step with no duration has no comparable
    spend to show."""
    if not duration:
        return []
    spans: list[Span] = [("  ", DIM), (DUR_MARK + " " + duration, GREEN)]
    if cost_tail:
        spans.extend(cost_tail)
    return spans


# Record types timed from their author's dispatch (the implement session
# times itself, opener → clean build). Other types never carry a tail, so
# the dispatch pairing is skipped for them entirely. grader-verdict is
# absent by contract: the change-grader is dispatch-exempt (the
# dispatch-start schema rejects it as author), so a grade has no start to
# time from and never carries a tail.
_TIMED_TYPES = ("prd-entry", "design-block", "review-feedback")


def _step_tail(
    rec: dict[str, Any],
    entries: list[LogEntry],
    line: int,
    cost_lookup: _CostLookup | None,
) -> list[Span]:
    """The duration+cost tail spans for one timed record, or []. cost_lookup
    may return None (off Claude Code, absent transcripts, ambiguity) — the
    step then shows its duration alone."""
    start_rec = _producer_dispatch(rec, entries, line)
    dur = _duration(start_rec, rec)
    if not dur:
        return []
    ctail = cost_lookup(rec.get("author"), start_rec, rec) if cost_lookup else None
    return _tail_spans(dur, ctail)


def _implement_parent_line(
    rec: dict[str, Any],
    by_no: dict[int, dict[str, Any]],
    color: bool,
    duration: str | None = None,
    cost_tail: Sequence[Span] | None = None,
) -> str:
    """The opener of an implement session. A fresh dispatch renders
    `◆ implement`; a fix dispatch (answering non-approved review) renders
    `↻ implement ← <reviewers>` with the finding count. `duration` is the
    session elapsed (opener to clean build); the build inside names no author,
    so this parent is where the implementer surfaces. `cost_tail` is the
    session's cost overlay string, joined after the ◷ marker like the timed
    steps — present only when the session closed with a clean build."""
    tail = _tail_spans(duration, cost_tail)
    src = _fix_sources(rec, by_no)
    if src:
        reviewers, n = src
        spans: list[Span] = [
            ("↻ ", "33"),
            ("implement  ", DIM),
            ("(" + agent_label(IMPLEMENTER) + ")", DIM),
            ("  ← ", DIM),
            (", ".join(reviewers), DIM),
        ]
        if n:
            spans.append((f"  ({_plural(n, 'finding')})", DIM))
        return _line(spans + tail, color)
    spans = [
        ("◆ ", "35"),
        ("implement  ", DIM),
        ("(" + agent_label(IMPLEMENTER) + ")", DIM),
    ]
    return _line(spans + tail, color)


def _child_lines(
    rec: dict[str, Any],
    conn: str,
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    color: bool,
    verbose: bool,
) -> list[str]:
    """One child line under an implement session, `├`/`└`-connected like a
    review's findings: a build attempt (pass = `✓ clean`, failure = `✗ <check>
    failed`) or the implementer's own mid-work consult (`↳`/`↲`)."""
    pre: list[Span] = [("  ", None), (conn + " ", DIM)]
    t = rec.get("type")
    if t == "build-pass":
        # No per-build timestamp — the session's elapsed sits on the parent.
        spans: list[Span] = [*pre, ("▲ build", "32"), ("  ✓ clean", "32")]
        checks = rec.get("gate_checks_run")
        if isinstance(checks, list) and checks:
            spans.append(("   " + " · ".join(str(c) for c in checks), DIM))
        return [_line(spans, color)]
    if t == "build-failure":
        spans = [*pre, ("▲ build", "31")]
        if isinstance(rec.get("abort_reason"), str):
            spans.append(("  ✗ aborted: " + rec["abort_reason"], "1;31"))
        else:
            fc = rec.get("failed_check")
            spans.append(
                (
                    "  ✗ " + (str(fc) + " failed" if isinstance(fc, str) else "failed"),
                    "31",
                )
            )
            if rec.get("retry") is not None:
                spans.append((f"  retry {rec['retry']}", DIM))
        return [_line(spans, color)]
    if t == "consultation-request":
        return [
            _line(
                pre
                + [
                    ("↳ consult  → ", DIM),
                    (agent_label(rec.get("target")), BOLD),
                    ("  ", None),
                    (gist(rec.get("question")), DIM),
                ],
                color,
            )
        ]
    if t == "consultation-response":
        return [
            _line(
                pre
                + [
                    ("↲ consult  ← ", DIM),
                    (agent_label(rec.get("author")), BOLD),
                    ("  ", None),
                    (gist(rec.get("answer")), DIM),
                ],
                color,
            )
        ]
    # Defensive: every _SESSION_CHILD type is handled above, so this is
    # unreached today. It keeps a future child type rendering (flat) instead of
    # returning None into the caller's `lines +=` — never delete it as dead.
    return _timeline_lines(rec, entries, by_no, color, verbose)


# An open implement session nests these as `├`/`└` children; every other
# record ends it. A dispatch-start inside the window is plumbing (an interior
# retry or consult resume, or the consult target) — absorbed, no line.
_SESSION_CHILD = (
    "build-failure",
    "build-pass",
    "consultation-request",
    "consultation-response",
)


def _own_consult(rec: dict[str, Any], by_no: dict[int, dict[str, Any]]) -> bool:
    """Whether a consult record inside a session window is the implementer's
    own: a request the implementer authored, or the response answering one. A
    sibling doc-owner's consult (its author working the same fix round) is
    neither — nesting it under the session would misattribute the question to
    the implementer."""
    if rec.get("type") == "consultation-request":
        return bool(rec.get("author") == IMPLEMENTER)
    ref: Any = rec.get("in_response_to")
    req = by_no.get(ref)
    return bool(isinstance(req, dict) and req.get("author") == IMPLEMENTER)


def _session_group(
    slice_entries: list[LogEntry], start_i: int, by_no: dict[int, dict[str, Any]]
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any] | None,
    int,
]:
    """Group one implement session — the opener at slice_entries[start_i], its
    child records, the hoisted siblings, and the closer — as (opener,
    children, siblings, closer, next_index). The closer ends the session: the
    first build-pass (the clean build), or an aborting build-failure — the
    abort ends the implementer's dispatch too (routing dispatches elsewhere;
    see the abort rules in _build_failure_state). A plain retry failure stays
    a child; interior dispatch-starts are absorbed; a truncated session with
    no closer closes at whatever it consumed. Both renderers consume this
    grouping — the session boundary logic lives once."""
    opener = slice_entries[start_i][1]
    children: list[dict[str, Any]] = []
    siblings: list[dict[str, Any]] = []
    closer: dict[str, Any] | None = None
    j = start_i + 1
    while j < len(slice_entries):
        rec = slice_entries[j][1]
        t = rec.get("type")
        if t == "dispatch-start":
            # A doc-owner's fix (a prd-expert or designer answering a review)
            # dispatched in the same fix round interleaves into this window but
            # is a SIBLING, not part of the session — hoist it to a flat line
            # after the session so it stays visible. Every other dispatch-start
            # is the implementer's own plumbing (a retry or consult resume) or
            # the consult target — absorbed, no line.
            if rec.get("author") != IMPLEMENTER and _fix_sources(rec, by_no):
                siblings.append(rec)
            j += 1
            continue
        if t == "design-doc-autofix":
            # A root-applied doc tweak interleaving into the window is a
            # sibling like the doc-owner's dispatch: hoist it flat after the
            # session rather than truncating the session at it.
            siblings.append(rec)
            j += 1
            continue
        if t not in _SESSION_CHILD:
            break  # a review, design, or grade record ends the session
        if t in ("consultation-request", "consultation-response") and not _own_consult(
            rec, by_no
        ):
            # A sibling's consult interleaving into the window: hoist it to a
            # flat line (with its real author) after the session.
            siblings.append(rec)
            j += 1
            continue
        children.append(rec)
        j += 1
        if t == "build-pass" or (
            t == "build-failure" and isinstance(rec.get("abort_reason"), str)
        ):
            closer = rec
            break  # the clean build or the abort closes the session
    return opener, children, siblings, closer, j


def _implement_session(
    slice_entries: list[LogEntry],
    start_i: int,
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    color: bool,
    verbose: bool,
    cost_lookup: _CostLookup | None = None,
) -> tuple[list[str], int]:
    """Render one implement session — the opener plus the build attempts and
    its own mid-work consults, `├`/`└`-nested, then the hoisted siblings —
    and return (lines, next_index)."""
    opener, children, siblings, closer, j = _session_group(
        slice_entries, start_i, by_no
    )
    duration = _duration(opener, closer) if closer else None
    # Session cost spans the implementer's whole window (opener → closer: the
    # clean build, or the aborting failure), so it sums every implementer
    # transcript inside it — the original dispatch and any retry re-dispatch.
    # Only computed when the session closed: timing a truncated session would
    # guess at an unfinished span.
    cost_tail = (
        cost_lookup(IMPLEMENTER, opener, closer) if cost_lookup and closer else None
    )
    lines = [_implement_parent_line(opener, by_no, color, duration, cost_tail)]
    for k, child in enumerate(children):
        conn = "└" if k == len(children) - 1 else "├"
        lines += _child_lines(child, conn, entries, by_no, color, verbose)
    for sib in siblings:
        # Flat rendering: a dispatch-start sibling becomes its `↻ fix` line, a
        # consult sibling its flat `↳`/`↲` line naming its author.
        lines += _timeline_lines(sib, entries, by_no, color, verbose)
    return lines, j


def _timeline_lines(
    rec: dict[str, Any],
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    color: bool,
    verbose: bool,
    cost_lookup: _CostLookup | None = None,
    line: int | None = None,
) -> list[str]:
    rtype = rec.get("type")
    if rtype == "dispatch-start":
        # A dispatch-start reaching the flat timeline (not consumed by an
        # implement session) surfaces only as a non-implementer `↻ fix`;
        # reviewer fan-out and prd/design triage stay suppressed as noise.
        return _fix_dispatch_lines(rec, by_no, color)
    author = f"  ({agent_label(rec.get('author'))})"
    # The duration+cost tail is computed only for the timed types — every
    # other branch below ignores it, so the dispatch pairing and the cost
    # lookup are skipped for them. `line` is None for a record rendered
    # outside the slice walk (a hoisted sibling): no tail there either.
    tail: list[Span] = (
        _step_tail(rec, entries, line, cost_lookup)
        if line is not None and rtype in _TIMED_TYPES
        else []
    )
    if rtype == "prd-entry":
        return [
            _line(
                [
                    ("◇ ", "35"),
                    ("prd-entry  ", DIM),
                    (gist(rec.get("title"), 52) or "(untitled)", BOLD),
                    (author, DIM),
                    *tail,
                ],
                color,
            )
        ]
    if rtype == "design-block":
        spans: list[Span] = [
            ("◈ ", "35"),
            ("design-block  ", DIM),
            (str(rec.get("verdict") or "?"), BOLD),
            (author, DIM),
        ]
        if isinstance(rec.get("supersedes_record_at"), int):
            spans.append((f"  supersedes L{rec['supersedes_record_at']}", DIM))
        return [_line(spans + tail, color)]
    if rtype == "build-pass":
        core: list[Span] = [("▲ build-pass", "32")]
        hhmm = _ts_hhmm(rec)
        if hhmm:
            core.append((" " + hhmm, DIM))
        checks = rec.get("gate_checks_run")
        if isinstance(checks, list) and checks:
            core.append(("  " + ", ".join(str(c) for c in checks), DIM))
        return [_rule_line(core, color)]
    if rtype == "build-failure":
        core = [("▲ build-failure", "31")]
        hhmm = _ts_hhmm(rec)
        if hhmm:
            core.append((" " + hhmm, DIM))
        if isinstance(rec.get("abort_reason"), str):
            core.append((f"  abort: {rec['abort_reason']}", "1;31"))
        else:
            if isinstance(rec.get("failed_check"), str):
                core.append(("  " + rec["failed_check"], DIM))
            if rec.get("retry") is not None:
                core.append((f"  retry {rec['retry']}", DIM))
        return [_rule_line(core, color)]
    if rtype == "review-feedback":
        verdict = rec.get("verdict")
        glyph, vcol = _verdict_glyph(verdict)
        n = len(_findings_of(rec))
        spans = [
            (glyph + " ", vcol),
            ("review  ", DIM),
            (agent_label(rec.get("author")), BOLD),
            ("  ", None),
            (str(verdict or "?"), vcol),
        ]
        if n:
            spans.append((f"  ({_plural(n, 'finding')})", DIM))
        return [_line(spans + tail, color)] + _finding_lines(rec, color, verbose)
    if rtype == "grader-verdict":
        verdict = rec.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        spans = [
            ("◆ ", "36"),
            ("grade  ", DIM),
            (verdict_text.upper(), f"{BOLD};{GRADE_COLORS.get(verdict_text, DIM)}"),
            ("  ", None),
            (gist(rec.get("summary")), DIM),
        ]
        return [_line(spans + tail, color)] + _facet_lines(rec, color)
    if rtype == "consultation-request":
        return [
            _line(
                [
                    ("↳ ", "36"),
                    ("consult  ", DIM),
                    (agent_label(rec.get("author")), BOLD),
                    (" → ", DIM),
                    (agent_label(rec.get("target")), BOLD),
                    ("  ", None),
                    (gist(rec.get("question")), DIM),
                ],
                color,
            )
        ]
    if rtype == "consultation-response":
        return [
            _line(
                [
                    ("↲ ", "36"),
                    ("consult  ", DIM),
                    (agent_label(rec.get("author")), BOLD),
                    (" → ", DIM),
                    (agent_label(_consultation_peer(entries, rec)), BOLD),
                    ("  ", None),
                    (gist(rec.get("answer")), DIM),
                ],
                color,
            )
        ]
    if rtype == "design-doc-autofix":
        return [
            _line(
                [
                    ("✚ ", "33"),
                    ("doc-autofix  ", DIM),
                    (str(rec.get("file") or "?"), BOLD),
                    ("  " + str(rec.get("category") or ""), DIM),
                    (author, DIM),
                ],
                color,
            )
        ]
    return [
        _line(
            [
                ("• ", DIM),
                (str(rtype or "?") + "  ", DIM),
                ("(" + agent_label(rec.get("author")) + ")", DIM),
            ],
            color,
        )
    ]


def _in_slice(rec: dict[str, Any], req_id: str | None) -> bool:
    """Slice membership. req_id None is the group of records carrying no
    string req_id, kept distinct from any named slice."""
    rid = rec.get("req_id")
    if req_id is None:
        return not (isinstance(rid, str) and rid)
    return bool(rid == req_id)


def _slice_order(entries: list[LogEntry]) -> list[str | None]:
    """Slice keys in first-appearance (append) order — append position is the
    only clock, matching the within-slice timeline. A trailing None marks a
    group of records with no req_id, rendered last."""
    order: list[str | None] = []
    seen: set[str] = set()
    has_none = False
    for _, rec in entries:
        rid = rec.get("req_id")
        if isinstance(rid, str) and rid:
            if rid not in seen:
                seen.add(rid)
                order.append(rid)
        else:
            has_none = True
    if has_none:
        order.append(None)
    return order


def _timeline_blocks(
    slice_entries: list[LogEntry],
    step: Callable[[dict[str, Any], int], list[str]],
    session: Callable[[int], tuple[list[str], int]],
) -> list[str]:
    """Walk one slice's records in append order: an implementer dispatch-start
    opens an implement session that consumes the records it owns; every other
    record renders flat (grader-features is filtered). Both renderers share
    this walk; `step(rec, no)` and `session(i)` do the line composition."""
    lines: list[str] = []
    i = 0
    while i < len(slice_entries):
        no, rec = slice_entries[i]
        rtype = rec.get("type")
        if rtype == "grader-features":
            i += 1
            continue
        if rtype == "dispatch-start" and rec.get("author") == IMPLEMENTER:
            block, i = session(i)
            lines += block
            continue
        lines += step(rec, no)
        i += 1
    return lines


def _render_slice(
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    req_id: str | None,
    roster: Sequence[str],
    color: bool,
    verbose: bool,
    auto_grade: bool,
    others: Sequence[str],
    cost_lookup: _CostLookup | None = None,
) -> list[str]:
    """Header, matrix, and timeline for one slice. `entries` stays the full log
    so a fix dispatch resolves its responding_to pointers across slices;
    `by_no` is its line→record map, built once in render_view."""
    slice_entries = [(no, rec) for no, rec in entries if _in_slice(rec, req_id)]
    recs = [rec for _, rec in slice_entries]
    rounds = review_rounds(recs)
    lines = _render_header(
        req_id,
        recs,
        rounds,
        others,
        color,
        auto_grade,
        slice_tail=_slice_tail_spans(recs, cost_lookup),
    )
    matrix = _render_matrix(rounds, roster, color)
    if matrix:
        lines.append("")
        lines += matrix
    lines.append("")
    lines += _timeline_blocks(
        slice_entries,
        lambda rec, no: _timeline_lines(
            rec, entries, by_no, color, verbose, cost_lookup, line=no
        ),
        lambda i: _implement_session(
            slice_entries, i, entries, by_no, color, verbose, cost_lookup
        ),
    )
    return lines


def render_view(
    entries: list[LogEntry],
    errors: list[str],
    req_id: str | None,
    roster: Sequence[str],
    color: bool,
    verbose: bool,
    auto_grade: bool = True,
    cost_lookup: _CostLookup | None = None,
) -> tuple[list[str], int]:
    """Render the view as (lines, exit_code). Pure: no I/O, no clock.

    req_id None renders every slice in append order, each its own board; an
    explicit req_id renders just that slice (exit 3 if it has no records).

    cost_lookup, when given, is a (agent_type, start_rec, end_rec) →
    cost-tail-spans-or-None closure over a transcript index the caller built
    at its I/O boundary. It only reads the passed-in data and never raises, so
    render_view stays pure; None (the default) renders no cost overlay."""
    lines: list[str] = []
    code = 0
    by_no = dict(entries)
    named = [rid for rid in _slice_order(entries) if rid is not None]
    if req_id is not None:
        recs = [rec for _, rec in entries if _in_slice(rec, req_id)]
        if not recs:
            lines.append(_style(f"no records for {req_id}", DIM, color))
            code = 3
            if named:
                lines.append(_style("in log: " + ", ".join(named), DIM, color))
        else:
            others = [rid for rid in named if rid != req_id]
            lines += _render_slice(
                entries,
                by_no,
                req_id,
                roster,
                color,
                verbose,
                auto_grade,
                others,
                cost_lookup,
            )
    else:
        order = _slice_order(entries)
        if not order:
            lines.append(_style("handoff log is empty", DIM, color))
        for i, rid in enumerate(order):
            if i:
                lines.append("")
            lines += _render_slice(
                entries,
                by_no,
                rid,
                roster,
                color,
                verbose,
                auto_grade,
                others=[],
                cost_lookup=cost_lookup,
            )
    if errors:
        lines.append("")
        lines.append(
            _style(f"! {_plural(len(errors), 'problem line')} skipped:", "31", color)
        )
        lines += [_style("  " + err, DIM, color) for err in errors]
    return lines, code


# --- view --markdown: the same board rendered as Markdown -------------------
# For AI-agent transcripts that strip ANSI but render Markdown. Grouping —
# rounds, sessions, hoisted siblings, the walk — is shared with the TTY
# renderer above; only line composition differs. Emphasis has two layers:
# the ANSI importance map is the floor (what VERDICT_GLYPHS, TAG_COLORS,
# FACET_COLORS and the colored spans highlight renders bold; DIM stays plain;
# DIM tails render italic), and on top of it a user-requested anchor layer
# bolds the known step kinds — fused with their actor on review/fix/grade
# lines — so the flow reads off the emphasized words. The anchors only work
# because the deliberate noise (agent parentheticals, gate lists, retry
# notes, `supersedes Ln`, `←` fix sources, consult scaffolding, unknown-kind
# rows) stays quiet. Record text must not break the document: escaping is
# minimal but structural.

_MD_LEAD = "#*->"


def _md_escape(text: Any) -> str:
    """Neutralize record text for a Markdown line: strip controls (via
    _sanitize), escape `<` (raw HTML), and backslash a structure-forming
    leading character."""
    s = _sanitize(str(text)).replace("<", "\\<")
    if s and s[0] in _MD_LEAD:
        s = "\\" + s
    return s


def _md_cell(text: Any) -> str:
    """A table cell: `|` would end it early."""
    return _md_escape(text).replace("|", "\\|")


def _md_code(text: Any) -> str:
    """Inline code: backticks cannot nest, so they are replaced (ʼ)."""
    text = _sanitize(str(text)).replace("`", "ʼ").strip()
    return f"`{text}`" if text else ""


def _md_span_text(spans: Sequence[Span]) -> str:
    """The plain text of a span list — the box's separators ride along."""
    return "".join(t for t, _ in spans).strip()


def _md_tail(spans: Sequence[Span]) -> str:
    """A duration+cost tail: italic overall (DIM in ANSI), with the spans the
    color mode highlights — the elapsed and the $ cost, both GREEN — bold
    inside it, so the flow reads off the emphasized words."""
    parts: list[str] = []
    for text, code in spans:
        text = _sanitize(text)
        if code == GREEN and text.strip():
            text = f"**{text.strip()}**"
        parts.append(text)
    body = "".join(parts).strip()
    return f"*{body}*" if body else ""


def _md_step(
    glyph: str, kind: str, lead: str, *parts: str, bold_kind: bool = False
) -> str:
    """One top-level timeline bullet: the type glyph, the kind token, the lead
    token, then the line's remaining tokens ` · `-joined (the Markdown
    stand-in for the board's column gaps). bold_kind is the anchor layer:
    known step kinds bold (the build gates also carry the outcome color in
    ANSI); unknown-kind rows and consult scaffolding stay plain."""
    kind_md = _md_escape(kind)
    if bold_kind:
        kind_md = f"**{kind_md}**"
    head = f"- {glyph} {kind_md}"
    if lead:
        head += " " + lead
    return " · ".join([head] + [p for p in parts if p])


def _md_summary(spans: Sequence[Span]) -> str:
    """The header summary with the ANSI emphasis mirrored: a colored or bold
    span (the failure count, the grade) renders bold; DIM spans stay plain."""
    return "".join(
        f"**{_md_escape(t)}**" if c and c != DIM else _md_escape(t) for t, c in spans
    )


def _md_header(
    req_id: str | None,
    recs: list[dict[str, Any]],
    rounds: Sequence[dict[str, dict[str, Any]]],
    others: Sequence[str],
    auto_grade: bool,
    slice_tail: Sequence[Span],
) -> list[str]:
    title, grade, passes, failures = _slice_stats(recs)
    head = "### " + _md_escape(req_id or "(no req_id)")
    if title:
        head += " — " + _md_escape(gist(title, 52))
    summary = _md_summary(_summary_spans(rounds, passes, failures, grade, auto_grade))
    lines = [head, ""]
    if slice_tail:
        # One paragraph: the roll-up rides the summary via a hard break.
        lines += [summary + "  ", _md_tail(slice_tail)]
    else:
        lines.append(summary)
    if others:
        lines += ["", "*also in log: " + _md_escape(", ".join(others)) + "*"]
    return lines


def _md_matrix_cell(rec: dict[str, Any] | None) -> str:
    """One verdict cell. Anchor layer: the settled outcomes (✔ approved,
    ✖ blocked) pop bold; ✎ rounds-in-progress and absent · stay plain."""
    parts: list[str] = []
    for text, _code in _matrix_cell(rec):
        cell = _md_cell(text)
        if text in ("✔", "✖"):
            cell = f"**{cell}**"
        parts.append(cell)
    return "".join(parts)


def _md_matrix(
    rounds: Sequence[dict[str, dict[str, Any]]], roster: Sequence[str]
) -> list[str]:
    if not rounds:
        return []
    authors = _matrix_authors(rounds, roster)
    lines = [
        "| reviewer | " + " | ".join(f"R{i + 1}" for i in range(len(rounds))) + " |",
        "|" + " --- |" * (len(rounds) + 1),
    ]
    for author in authors:
        cells = [_md_matrix_cell(rnd.get(author)) for rnd in rounds]
        # Reviewer names bold: the row anchors, like the timeline kinds.
        lines.append(
            "| **" + _md_cell(agent_label(author)) + "** | " + " | ".join(cells) + " |"
        )
    return lines


def _md_finding_lines(rec: dict[str, Any], verbose: bool) -> list[str]:
    lines: list[str] = []
    for finding in _findings_of(rec):
        tag = finding.get("tag")
        tag_text = tag if isinstance(tag, str) and tag else "?"
        desc = finding.get("description")
        desc_text = desc if verbose and isinstance(desc, str) else gist(desc)
        tag_md = "[" + _md_escape(tag_text) + "]"
        # Red-family tags in ANSI carry the emphasis; the rest stay plain.
        if TAG_COLORS.get(tag_text) in ("31", "1;31"):
            tag_md = f"**{tag_md}**"
        parts = [
            tag_md,
            _md_code(short_location(finding.get("location"))),
            _md_escape(desc_text) if desc_text else "",
        ]
        lines.append("  - " + " ".join(p for p in parts if p))
        if verbose and isinstance(finding.get("fix"), str) and finding["fix"].strip():
            lines.append("    - fix: " + _md_escape(finding["fix"].strip()))
    return lines


def _md_facet_lines(rec: dict[str, Any]) -> list[str]:
    facets = rec.get("facets")
    if not isinstance(facets, dict) or not facets:
        return []
    lines: list[str] = []
    for name, facet in facets.items():
        facet = facet if isinstance(facet, dict) else {}
        verdict = facet.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        parts = [_md_escape(str(name)), f"**{_md_escape(verdict_text)}**"]
        note = gist(facet.get("note"), 48)
        if note:
            parts.append(_md_escape(note))
        lines.append("  - " + " — ".join(parts))
    return lines


def _md_child_lines(
    rec: dict[str, Any],
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    verbose: bool,
) -> list[str]:
    """One nested bullet under an implement session — the `├`/`└` children,
    without the tree glyphs."""
    t = rec.get("type")
    if t == "build-pass":
        # `build` shares the outcome's color in ANSI, so it rides the bold
        # span; the gate list stays plain.
        line = "  - ▲ **build ✓ clean**"
        checks = rec.get("gate_checks_run")
        if isinstance(checks, list) and checks:
            line += " · " + " · ".join(_md_escape(str(c)) for c in checks)
        return [line]
    if t == "build-failure":
        if isinstance(rec.get("abort_reason"), str):
            return [
                "  - ▲ **build ✗ aborted: " + _md_escape(rec["abort_reason"]) + "**"
            ]
        fc = rec.get("failed_check")
        line = (
            "  - ▲ **build ✗ "
            + (_md_escape(fc) + " failed" if isinstance(fc, str) else "failed")
            + "**"
        )
        if rec.get("retry") is not None:
            line += f" · retry {_md_escape(str(rec['retry']))}"
        return [line]
    if t == "consultation-request":
        # The consult peer is BOLD in ANSI; the scaffolding is DIM.
        q = _md_escape(gist(rec.get("question")))
        return [
            "  - ↳ consult → **"
            + _md_escape(agent_label(rec.get("target")))
            + "**"
            + (" · " + q if q else "")
        ]
    if t == "consultation-response":
        a = _md_escape(gist(rec.get("answer")))
        return [
            "  - ↲ consult ← **"
            + _md_escape(agent_label(rec.get("author")))
            + "**"
            + (" · " + a if a else "")
        ]
    # Defensive, mirroring _child_lines: a future child type still renders.
    return ["  " + line for line in _md_timeline_lines(rec, entries, by_no, verbose)]


def _md_timeline_lines(
    rec: dict[str, Any],
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    verbose: bool,
    cost_lookup: _CostLookup | None = None,
    line: int | None = None,
) -> list[str]:
    rtype = rec.get("type")
    if rtype == "dispatch-start":
        src = _fix_sources(rec, by_no)
        if not src:
            return []
        reviewers, n = src
        # Anchor: kind + fixer as one bold unit; the `←` source stays plain.
        return [
            _md_step(
                "↻",
                "fix " + agent_label(rec.get("author")),
                "← " + _md_escape(", ".join(reviewers)),
                f"({_plural(n, 'finding')})" if n else "",
                bold_kind=True,
            )
        ]
    author = "(" + _md_escape(agent_label(rec.get("author"))) + ")"
    tail = (
        _md_tail(_step_tail(rec, entries, line, cost_lookup))
        if line is not None and rtype in _TIMED_TYPES
        else ""
    )
    if rtype == "prd-entry":
        return [
            _md_step(
                "◇",
                "prd-entry",
                _md_escape(gist(rec.get("title"), 52) or "(untitled)"),
                author,
                tail,
                bold_kind=True,
            )
        ]
    if rtype == "design-block":
        sup = rec.get("supersedes_record_at")
        return [
            _md_step(
                "◈",
                "design-block",
                f"**{_md_escape(str(rec.get('verdict') or '?'))}**",
                author,
                f"supersedes L{sup}" if isinstance(sup, int) else "",
                tail,
                bold_kind=True,
            )
        ]
    if rtype == "build-pass":
        checks = rec.get("gate_checks_run")
        return [
            _md_step(
                "▲",
                "build-pass",
                _ts_hhmm(rec) or "",
                ", ".join(_md_escape(str(c)) for c in checks)
                if isinstance(checks, list) and checks
                else "",
                bold_kind=True,
            )
        ]
    if rtype == "build-failure":
        parts: list[str] = []
        if isinstance(rec.get("abort_reason"), str):
            parts.append("**abort: " + _md_escape(rec["abort_reason"]) + "**")
        else:
            if isinstance(rec.get("failed_check"), str):
                parts.append(_md_escape(rec["failed_check"]))
            if rec.get("retry") is not None:
                parts.append(f"retry {_md_escape(str(rec['retry']))}")
        return [
            _md_step("▲", "build-failure", _ts_hhmm(rec) or "", *parts, bold_kind=True)
        ]
    if rtype == "review-feedback":
        verdict = rec.get("verdict")
        glyph, vcol = _verdict_glyph(verdict)
        verdict_text = _md_escape(str(verdict or "?"))
        if vcol != DIM:
            # A known verdict is colored in ANSI; an unknown one is DIM.
            verdict_text = f"**{verdict_text}**"
        n = len(_findings_of(rec))
        # Anchor: kind + reviewer as one bold unit.
        return [
            _md_step(
                glyph,
                "review " + agent_label(rec.get("author")),
                "",
                verdict_text,
                f"({_plural(n, 'finding')})" if n else "",
                tail,
                bold_kind=True,
            )
        ] + _md_finding_lines(rec, verbose)
    if rtype == "grader-verdict":
        verdict = rec.get("verdict")
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        # Anchor: kind + grade verdict as one bold unit.
        return [
            _md_step(
                "◆",
                "grade " + verdict_text.upper(),
                "",
                _md_escape(gist(rec.get("summary"))),
                bold_kind=True,
            )
        ] + _md_facet_lines(rec)
    if rtype == "consultation-request":
        # Both consult parties are BOLD in ANSI; the arrow is DIM.
        lead = (
            "**"
            + _md_escape(agent_label(rec.get("author")))
            + "** → **"
            + _md_escape(agent_label(rec.get("target")))
            + "**"
        )
        return [_md_step("↳", "consult", lead, _md_escape(gist(rec.get("question"))))]
    if rtype == "consultation-response":
        lead = (
            "**"
            + _md_escape(agent_label(rec.get("author")))
            + "** → **"
            + _md_escape(agent_label(_consultation_peer(entries, rec)))
            + "**"
        )
        return [_md_step("↲", "consult", lead, _md_escape(gist(rec.get("answer"))))]
    if rtype == "design-doc-autofix":
        return [
            _md_step(
                "✚",
                "doc-autofix",
                _md_code(str(rec.get("file") or "?")),
                _md_escape(str(rec.get("category") or "")),
                author,
                bold_kind=True,
            )
        ]
    # Unknown kinds get no anchor: a DIM `•` row in ANSI stays fully plain.
    return [_md_step("•", str(rtype or "?"), author)]


def _md_implement_parent(
    rec: dict[str, Any],
    by_no: dict[int, dict[str, Any]],
    duration: str | None,
    cost_tail: Sequence[Span] | None,
) -> str:
    tail = _md_tail(_tail_spans(duration, cost_tail))
    label = "(" + _md_escape(agent_label(IMPLEMENTER)) + ")"
    src = _fix_sources(rec, by_no)
    if src:
        reviewers, n = src
        return _md_step(
            "↻",
            "implement",
            label + " ← " + _md_escape(", ".join(reviewers)),
            f"({_plural(n, 'finding')})" if n else "",
            tail,
            bold_kind=True,
        )
    return _md_step("◆", "implement", label, tail, bold_kind=True)


def _md_implement_session(
    slice_entries: list[LogEntry],
    start_i: int,
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    verbose: bool,
    cost_lookup: _CostLookup | None = None,
) -> tuple[list[str], int]:
    opener, children, siblings, closer, j = _session_group(
        slice_entries, start_i, by_no
    )
    duration = _duration(opener, closer) if closer else None
    cost_tail = (
        cost_lookup(IMPLEMENTER, opener, closer) if cost_lookup and closer else None
    )
    lines = [_md_implement_parent(opener, by_no, duration, cost_tail)]
    for child in children:
        lines += _md_child_lines(child, entries, by_no, verbose)
    for sib in siblings:
        lines += _md_timeline_lines(sib, entries, by_no, verbose)
    return lines, j


def _md_slice(
    entries: list[LogEntry],
    by_no: dict[int, dict[str, Any]],
    req_id: str | None,
    roster: Sequence[str],
    verbose: bool,
    auto_grade: bool,
    others: Sequence[str],
    cost_lookup: _CostLookup | None = None,
) -> list[str]:
    slice_entries = [(no, rec) for no, rec in entries if _in_slice(rec, req_id)]
    recs = [rec for _, rec in slice_entries]
    rounds = review_rounds(recs)
    lines = _md_header(
        req_id, recs, rounds, others, auto_grade, _slice_tail_spans(recs, cost_lookup)
    )
    matrix = _md_matrix(rounds, roster)
    if matrix:
        lines.append("")
        lines += matrix
    lines.append("")
    lines += _timeline_blocks(
        slice_entries,
        lambda rec, no: _md_timeline_lines(
            rec, entries, by_no, verbose, cost_lookup, line=no
        ),
        lambda i: _md_implement_session(
            slice_entries, i, entries, by_no, verbose, cost_lookup
        ),
    )
    return lines


def render_view_md(
    entries: list[LogEntry],
    errors: list[str],
    req_id: str | None,
    roster: Sequence[str],
    verbose: bool,
    auto_grade: bool = True,
    cost_lookup: _CostLookup | None = None,
) -> tuple[list[str], int]:
    """render_view's Markdown twin: same slices, same grouping, same exit
    codes — Markdown lines instead of the TTY board."""
    lines: list[str] = []
    code = 0
    by_no = dict(entries)
    named = [rid for rid in _slice_order(entries) if rid is not None]
    if req_id is not None:
        recs = [rec for _, rec in entries if _in_slice(rec, req_id)]
        if not recs:
            lines.append(_md_escape(f"no records for {req_id}"))
            code = 3
            if named:
                lines += ["", _md_escape("in log: " + ", ".join(named))]
        else:
            others = [rid for rid in named if rid != req_id]
            lines += _md_slice(
                entries, by_no, req_id, roster, verbose, auto_grade, others, cost_lookup
            )
    else:
        order = _slice_order(entries)
        if not order:
            lines.append("handoff log is empty")
        for i, rid in enumerate(order):
            if i:
                lines += ["", "---", ""]
            lines += _md_slice(
                entries,
                by_no,
                rid,
                roster,
                verbose,
                auto_grade,
                others=[],
                cost_lookup=cost_lookup,
            )
    if errors:
        lines += [
            "",
            _md_escape(f"! {_plural(len(errors), 'problem line')} skipped:"),
            "",
        ]
        lines += ["- " + _md_escape(err) for err in errors]
    return lines, code


def _build_cost_lookup(entries: list[LogEntry]) -> _CostLookup | None:
    """Build the board's cost-overlay lookup from Claude Code transcripts, or
    return None. The one I/O boundary for the overlay: discovery and parsing
    happen here so render_view stays pure. The build is skipped outright when
    the log holds no parseable dispatch-start — no step can be timed, so no
    cost can render — and transcripts whose file mtime predates the earliest
    dispatch are pruned (a file's messages cannot postdate its last write),
    keeping the scan proportional to the log's own time span rather than the
    project's whole history.

    Any failure — building the index or answering a lookup — degrades to
    None: the board reads, it never gates, so a missing module, absent
    transcripts (another tool, swept history), a malformed usage record, or
    an unreadable projects dir just drops the cost figures."""
    if accounting is None:
        return None
    dispatch_secs = [
        s
        for s in (
            _ts_seconds(rec)
            for _, rec in entries
            if rec.get("type") == "dispatch-start"
        )
        if s is not None
    ]
    if not dispatch_secs:
        return None
    try:
        index = accounting.WindowIndex(since_secs=min(dispatch_secs))
    except Exception:  # noqa: BLE001 — the reader must never gate on the overlay
        return None

    def _tail(figs: Any) -> list[Span] | None:
        if not figs:
            return None
        # The statusline's cell vocabulary and grouping: │-separated groups,
        # Σ for the spend group (cost emphasized green, like the duration),
        # ⛁ for the cache group with the $N% savings cell — suppressed like
        # there when the window has no cache activity.
        spans: list[Span] = [
            (
                f" │ Σ ▲{accounting.format_tokens(figs['total_input'])}"
                f" ▼{accounting.format_tokens(figs['output'])} ",
                DIM,
            ),
            (f"${accounting.format_cost(figs['cost'])}", GREEN),
            (f" │ ⛁ {figs['hit_pct']}%", DIM),
        ]
        if figs.get("savings_pct") is not None:
            spans.append((f" ${figs['savings_pct']}%", DIM))
        return spans

    def _lookup(agent_type: Any, start_rec: Any, end_rec: Any) -> list[Span] | None:
        if (
            not agent_type
            or not isinstance(start_rec, dict)
            or not isinstance(end_rec, dict)
        ):
            return None
        try:
            return _tail(
                index.totals(agent_type, _ts_seconds(start_rec), _ts_seconds(end_rec))
            )
        except Exception:  # noqa: BLE001 — the same rule at lookup time
            return None

    def _slice(agent_types: Any, start_rec: Any, end_rec: Any) -> list[Span] | None:
        if (
            not agent_types
            or not isinstance(start_rec, dict)
            or not isinstance(end_rec, dict)
        ):
            return None
        try:
            return _tail(
                index.slice_totals(
                    agent_types, _ts_seconds(start_rec), _ts_seconds(end_rec)
                )
            )
        except Exception:  # noqa: BLE001 — the same rule at lookup time
            return None

    # One attribute, not a second threaded parameter: only the header uses the
    # roll-up, and every render signature already carries cost_lookup. The cast
    # types the callable-plus-attribute shape as the _CostLookup protocol so the
    # attribute assignment type-checks; the runtime object is unchanged.
    lookup = cast(_CostLookup, _lookup)
    lookup.slice_lookup = _slice
    return lookup
