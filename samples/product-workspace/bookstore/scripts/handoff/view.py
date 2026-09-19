"""Render the board to the terminal or as Markdown from one shared model.

A middle layer over handoff.board and the leaves it reads; never imports handoff.routing.
"""

import functools
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .board import (
    Board,
    BoardOptions,
    Session,
    Step,
    Tail,
    agent_label,
    build_board,
    facet_rows,
    findings_of,
    grade_word,
    matrix_authors,
    slice_order,
)
from .cost import CostFigures
from .ledger import Entry
from .records import (
    IMPLEMENTER,
    REVIEW_ROUND_CAP,
    BuildFailure,
    BuildPass,
    ConsultationRequest,
    ConsultationResponse,
    DesignBlock,
    DesignDocAutofix,
    DispatchStart,
    GraderVerdict,
    HandoffRecord,
    IntakeDecision,
    PrdAutofix,
    PrdEntry,
    ReviewFeedback,
)
from .schema import sanitize
from .text import full_or_gist, gist, plural, short_location
from .timestamps import hhmm_of

# One styled fragment: display text and its ANSI code, None for an uncoded span.
Span: TypeAlias = tuple[str, str | None]

BOLD = "1"
RED = "31"
GREEN = "32"
YELLOW = "33"
MAGENTA = "35"
CYAN = "36"
DIM = "90"
BOLD_RED = "1;31"
DURATION_MARK = "◷"
VIEW_WIDTH = 72
NO_RECORDS_EXIT = 3
FACET_WIDTH = 10
TITLE_LIMIT = 52
NOTE_LIMIT = 48
VERDICT_GLYPHS: dict[str | None, tuple[str, str]] = {
    "approved": ("✔", GREEN),
    "changes_requested": ("✎", YELLOW),
    "blocked": ("✖", RED),
}
TAG_COLORS = {
    "autofix": YELLOW,
    "blocked": RED,
    "escalate": BOLD_RED,
    "clarify": CYAN,
    "truncation": DIM,
}
GRADE_COLORS = {"skim": GREEN, "scrutinize": YELLOW}
# Green says a glance confirms it; amber says read closely.
FACET_COLORS = {"skim": GREEN, "scrutinize": YELLOW, "unknown": YELLOW}
RED_TAG_COLORS = (RED, BOLD_RED)


@dataclass(frozen=True, slots=True)
class _Format:
    """The parts of the render flow that differ between the two views."""

    board: Callable[[Board, BoardOptions], list[str]]
    no_records: Callable[[str, BoardOptions], list[str]]
    in_log: Callable[[str, BoardOptions], list[str]]
    empty_log: Callable[[BoardOptions], list[str]]
    separator: tuple[str, ...]
    footer: Callable[[Sequence[str], BoardOptions], list[str]]


def render_view(
    log: Sequence[Entry], errors: Sequence[str], options: BoardOptions
) -> tuple[list[str], int]:
    """Render the terminal board as (lines, exit code); pure, no I/O, no clock."""
    return _render(log, errors, options, _TERMINAL)


def render_view_md(
    log: Sequence[Entry], errors: Sequence[str], options: BoardOptions
) -> tuple[list[str], int]:
    """Render the Markdown board as (lines, exit code): the same slices, grouping, and exit codes."""
    return _render(log, errors, options, _MARKDOWN)


def _render(
    log: Sequence[Entry], errors: Sequence[str], options: BoardOptions, view: _Format
) -> tuple[list[str], int]:
    """Render the slices, then the footer of skipped lines."""
    lines, code = _slice_lines(log, options, view)
    if errors:
        lines += view.footer(errors, options)
    return lines, code


def _slice_lines(
    log: Sequence[Entry], options: BoardOptions, view: _Format
) -> tuple[list[str], int]:
    """Render the requested slice, or every slice in append order, with the exit code."""
    order = slice_order(log)
    named = [req_id for req_id in order if req_id is not None]
    if options.req_id is None:
        lines = view.empty_log(options) if not order else []
        for index, req_id in enumerate(order):
            if index:
                lines += view.separator
            lines += view.board(build_board(log, req_id, options, []), options)
        return lines, 0
    if not any(entry.req_id == options.req_id for entry in log):
        lines = view.no_records(options.req_id, options)
        if named:
            lines += view.in_log(", ".join(named), options)
        return lines, NO_RECORDS_EXIT
    other_slices = [req_id for req_id in named if req_id != options.req_id]
    board = build_board(log, options.req_id, options, other_slices)
    return view.board(board, options), 0


# --- spans shared by both views ------------------------------------------------


def _summary_spans(board: Board, options: BoardOptions) -> list[Span]:
    """Return the header's summary spans; both views render these texts."""
    spans: list[Span] = [
        (plural(len(board.rounds), "review round"), DIM),
        (" · " + plural(board.passes, "build-pass"), DIM),
    ]
    if board.failures:
        spans += [(" · ", DIM), (plural(board.failures, "build-failure"), RED)]
    if board.grade is not None:
        color = GRADE_COLORS.get(board.grade, DIM)
        spans += [(" · grade ", DIM), (board.grade.upper(), f"{BOLD};{color}")]
    elif options.auto_grade:
        spans += [(" · no grade yet", DIM)]
    else:
        spans += [(" · grading disabled", DIM)]
    return spans


def _tail_spans(tail: Tail | None) -> list[Span]:
    """Return the duration and cost spans a timed line carries; cost never rides alone."""
    if tail is None:
        return []
    spans: list[Span] = [("  ", DIM), (DURATION_MARK + " " + tail.elapsed, GREEN)]
    if tail.cost is not None:
        spans += _cost_spans(tail.cost)
    return spans


def _slice_tail_spans(tail: Tail | None) -> list[Span]:
    """Return the header's whole-slice roll-up spans."""
    if tail is None or tail.cost is None:
        return []
    return [(DURATION_MARK + " " + tail.elapsed, GREEN), *_cost_spans(tail.cost)]


def _cost_spans(figures: CostFigures) -> list[Span]:
    """Return one window's usage in the statusline's cell vocabulary."""
    spans: list[Span] = [
        (f" │ Σ ▲{figures.tokens_in} ▼{figures.tokens_out} ", DIM),
        (f"${figures.cost}", GREEN),
        (f" │ ⛁ {figures.hit_pct}%", DIM),
    ]
    if figures.savings_pct is not None:
        spans.append((f" ${figures.savings_pct}%", DIM))
    return spans


def _verdict_glyph(verdict: object) -> tuple[str, str]:
    """Return the glyph and color of a review verdict; an unknown or unhashable one is neutral."""
    key = verdict if isinstance(verdict, str) else None
    return VERDICT_GLYPHS.get(key, ("•", DIM))


def _matrix_cell(entry: Entry | None) -> list[Span]:
    """Return the verdict glyph and finding count of one matrix cell."""
    if entry is None:
        return [("·", DIM)]
    verdict = entry.record.verdict if isinstance(entry.record, ReviewFeedback) else None
    glyph, color = _verdict_glyph(verdict)
    spans: list[Span] = [(glyph, color)]
    count = len(findings_of(entry))
    if count:
        spans.append((f" ({count})", DIM))
    return spans


def _author_note(entry: Entry) -> str:
    return f"  ({agent_label(entry.author)})"


# --- the terminal view ---------------------------------------------------------


def _text_board(board: Board, options: BoardOptions) -> list[str]:
    """Render one slice: header, matrix, timeline."""
    lines = _text_header(board, options)
    matrix = _text_matrix(board, options)
    if matrix:
        lines.append("")
        lines += matrix
    lines.append("")
    for item in board.timeline:
        lines += (
            _text_session(item, options)
            if isinstance(item, Session)
            else _text_step(item, options)
        )
    return lines


def _text_header(board: Board, options: BoardOptions) -> list[str]:
    """Render the slice header box."""
    tail = _slice_tail_spans(board.slice_tail)
    # Round 1 is the quiet default; the ladder shows once it starts climbing.
    if board.ladder_round > 1:
        bar = " · critical-only" if board.ladder_round >= REVIEW_ROUND_CAP else ""
        ladder: list[Span] = [
            (f"ladder round {board.ladder_round} of {REVIEW_ROUND_CAP + 1}{bar}", DIM)
        ]
        tail = tail + ([(" · ", DIM)] if tail else []) + ladder
    line1: list[Span] = [(board.req_id or "(no req_id)", BOLD)]
    if board.title:
        line1 += [("  ", None), (gist(board.title, TITLE_LIMIT), None)]
    span_lines = [line1, _summary_spans(board, options)]
    if tail:
        span_lines.append(tail)
    if board.other_slices:
        span_lines.append([("also in log: " + ", ".join(board.other_slices), DIM)])
    return _box(span_lines, color=options.color)


def _text_matrix(board: Board, options: BoardOptions) -> list[str]:
    """Render the review-convergence matrix: one row per reviewer, one column per round."""
    rounds = board.rounds
    if not rounds:
        return []
    authors = matrix_authors(rounds, options.roster)
    label_width = max(len(agent_label(author)) for author in authors)
    cells: dict[tuple[str, int], list[Span]] = {}
    column_widths: list[int] = []
    for index, round_ in enumerate(rounds):
        width = len(f"R{index + 1}")
        for author in authors:
            spans = _matrix_cell(round_.get(author))
            cells[(author, index)] = spans
            width = max(width, sum(len(text) for text, _ in spans))
        column_widths.append(width)
    header = " " * (label_width + 2) + "  ".join(
        f"R{index + 1}".ljust(column_widths[index]) for index in range(len(rounds))
    )
    lines = [_style(header.rstrip(), DIM, color=options.color)]
    for author in authors:
        row = agent_label(author).ljust(label_width) + "  "
        row += "  ".join(
            _pad(cells[(author, index)], column_widths[index], color=options.color)
            for index in range(len(rounds))
        )
        lines.append(row.rstrip())
    return lines


def _text_session(session: Session, options: BoardOptions) -> list[str]:
    """Render an implement session: the opener, its nested children, then the hoisted siblings."""
    label = "(" + agent_label(IMPLEMENTER) + ")"
    if session.routine:
        label = label[:-1] + " · routine)"
    audit: list[Span] = (
        [(f"  ✗ tier mismatch: {session.tier_note}", RED)] if session.tier_note else []
    )
    if session.fix:
        spans: list[Span] = [
            ("↻ ", YELLOW),
            ("implement  ", DIM),
            (label, DIM),
            ("  ← ", DIM),
            (", ".join(session.fix.reviewers), DIM),
        ]
        if session.fix.findings:
            spans.append((f"  ({plural(session.fix.findings, 'finding')})", DIM))
    else:
        spans = [("◆ ", MAGENTA), ("implement  ", DIM), (label, DIM)]
    lines = [_line([*spans, *audit, *_tail_spans(session.tail)], color=options.color)]
    for index, child in enumerate(session.children):
        connector = "└" if index == len(session.children) - 1 else "├"
        lines += _text_child(child, connector, options)
    for sibling in session.siblings:
        lines += _text_step(sibling, options)
    return lines


def _text_child(entry: Entry, connector: str, options: BoardOptions) -> list[str]:
    """Render one nested row of an implement session: a build attempt or the implementer's consult."""
    color = options.color
    lead: list[Span] = [("  ", None), (connector + " ", DIM)]
    match entry.record:
        case BuildPass() as record:
            spans: list[Span] = [*lead, ("▲ build", GREEN), ("  ✓ clean", GREEN)]
            if record.gate_checks_run:
                checks = " · ".join(str(check) for check in record.gate_checks_run)
                spans.append(("   " + checks, DIM))
            return [_line(spans, color=color)]
        case BuildFailure() as record:
            return [_line([*lead, *_build_failure_spans(record)], color=color)]
        case ConsultationRequest() as record:
            spans = [
                *lead,
                ("↳ consult  → ", DIM),
                (agent_label(record.target), BOLD),
                ("  ", None),
                (full_or_gist(record.question, verbose=options.verbose), DIM),
            ]
            return [_line(spans, color=color)]
        case ConsultationResponse() as record:
            spans = [
                *lead,
                ("↲ consult  ← ", DIM),
                (agent_label(entry.author), BOLD),
                ("  ", None),
                (full_or_gist(record.answer, verbose=options.verbose), DIM),
            ]
            return [_line(spans, color=color)]
        case _:
            return _text_step(Step(entry), options)


def _build_failure_spans(record: BuildFailure) -> list[Span]:
    """Return the nested build-failure row after its connector."""
    spans: list[Span] = [("▲ build", RED)]
    if isinstance(record.abort_reason, str):
        spans.append(("  ✗ aborted: " + record.abort_reason, BOLD_RED))
        return spans
    failed = record.failed_check
    outcome = failed + " failed" if isinstance(failed, str) else "failed"
    spans.append(("  ✗ " + outcome, RED))
    if record.retry is not None:
        spans.append((f"  retry {record.retry}", DIM))
    return spans


def _text_step(step: Step, options: BoardOptions) -> list[str]:
    """Render one flat timeline row."""
    return _text_row(step.entry.record, step, options)


@functools.singledispatch
def _text_row(_record: HandoffRecord, step: Step, options: BoardOptions) -> list[str]:
    """Render a flat row by its record type; a type with no renderer is the unknown row."""
    return _text_unknown(step, options)


@_text_row.register
def _text_fix(_record: DispatchStart, step: Step, options: BoardOptions) -> list[str]:
    """Render a doc-owner fix dispatch as a flat row linking it to the reviews it answers."""
    if step.fix is None:
        return []
    spans: list[Span] = [
        ("↻ ", YELLOW),
        ("fix  ", DIM),
        (agent_label(step.entry.author), BOLD),
        ("  ← ", DIM),
        (", ".join(step.fix.reviewers), DIM),
    ]
    if step.fix.findings:
        spans.append((f"  ({plural(step.fix.findings, 'finding')})", DIM))
    return [_line(spans, color=options.color)]


@_text_row.register
def _text_intake(
    record: IntakeDecision, step: Step, options: BoardOptions
) -> list[str]:
    request = full_or_gist(record.request, verbose=options.verbose, limit=TITLE_LIMIT)
    spans: list[Span] = [
        ("◇ ", MAGENTA),
        ("intake  ", DIM),
        (request or "(no request)", BOLD),
    ]
    if record.decisions:
        spans.append((f"  ({plural(len(record.decisions), 'decision')})", DIM))
    spans.append((_author_note(step.entry), DIM))
    return [_line(spans, color=options.color)]


@_text_row.register
def _text_prd_entry(record: PrdEntry, step: Step, options: BoardOptions) -> list[str]:
    title = full_or_gist(record.title, verbose=options.verbose, limit=TITLE_LIMIT)
    spans: list[Span] = [
        ("◇ ", MAGENTA),
        ("prd-entry  ", DIM),
        (title or "(untitled)", BOLD),
        (_author_note(step.entry), DIM),
        *_tail_spans(step.tail),
    ]
    return [_line(spans, color=options.color)]


@_text_row.register
def _text_design_block(
    record: DesignBlock, step: Step, options: BoardOptions
) -> list[str]:
    spans: list[Span] = [
        ("◈ ", MAGENTA),
        ("design-block  ", DIM),
        (str(record.verdict or "?"), BOLD),
        (_author_note(step.entry), DIM),
    ]
    if isinstance(record.supersedes_record_at, int):
        spans.append((f"  supersedes L{record.supersedes_record_at}", DIM))
    return [_line([*spans, *_tail_spans(step.tail)], color=options.color)]


@_text_row.register
def _text_build_pass(record: BuildPass, step: Step, options: BoardOptions) -> list[str]:
    core: list[Span] = [("▲ build-pass", GREEN)]
    hhmm = hhmm_of(step.entry.ts)
    if hhmm:
        core.append((" " + hhmm, DIM))
    if record.gate_checks_run:
        core.append(("  " + ", ".join(str(c) for c in record.gate_checks_run), DIM))
    return [_rule_line(core, color=options.color)]


@_text_row.register
def _text_build_failure(
    record: BuildFailure, step: Step, options: BoardOptions
) -> list[str]:
    core: list[Span] = [("▲ build-failure", RED)]
    hhmm = hhmm_of(step.entry.ts)
    if hhmm:
        core.append((" " + hhmm, DIM))
    if isinstance(record.abort_reason, str):
        core.append((f"  abort: {record.abort_reason}", BOLD_RED))
    else:
        if isinstance(record.failed_check, str):
            core.append(("  " + record.failed_check, DIM))
        if record.retry is not None:
            core.append((f"  retry {record.retry}", DIM))
    return [_rule_line(core, color=options.color)]


@_text_row.register
def _text_review(
    record: ReviewFeedback, step: Step, options: BoardOptions
) -> list[str]:
    glyph, color = _verdict_glyph(record.verdict)
    spans: list[Span] = [
        (glyph + " ", color),
        ("review  ", DIM),
        (agent_label(step.entry.author), BOLD),
        ("  ", None),
        (str(record.verdict or "?"), color),
    ]
    count = len(record.findings)
    if count:
        spans.append((f"  ({plural(count, 'finding')})", DIM))
    return [
        _line([*spans, *_tail_spans(step.tail)], color=options.color),
        *_text_findings(step.entry, options),
        *_text_recommendations(record, options),
    ]


def _text_findings(entry: Entry, options: BoardOptions) -> list[str]:
    """Render a review's findings as a connected list, with the fix under --verbose."""
    lines: list[str] = []
    findings = findings_of(entry)
    for index, finding in enumerate(findings):
        last = index == len(findings) - 1
        connector = "└" if last else "├"
        tag = finding.tag
        tag_text = tag if isinstance(tag, str) and tag else "?"
        description = finding.description
        spans: list[Span] = [
            ("  ", None),
            (connector + " ", DIM),
            (f"[{tag_text}]", TAG_COLORS.get(tag_text, DIM)),
            (" ", None),
            (short_location(finding.location), BOLD),
            ("  ", None),
            (
                description
                if options.verbose and isinstance(description, str)
                else gist(description),
                DIM,
            ),
        ]
        lines.append(_line(spans, color=options.color))
        if options.verbose and isinstance(finding.fix, str) and finding.fix.strip():
            bar = "  " if last else "│ "
            lines.append(
                _line(
                    [("  " + bar + "  ", DIM), ("fix: " + finding.fix.strip(), DIM)],
                    color=options.color,
                )
            )
    return lines


def _text_recommendations(record: ReviewFeedback, options: BoardOptions) -> list[str]:
    """Render a review's recommendations, the residual channel of a critical-only round."""
    return [
        _line(
            [
                ("  ", None),
                ("▹ rec  ", DIM),
                (full_or_gist(text, verbose=options.verbose), DIM),
            ],
            color=options.color,
        )
        for text in record.recommendations
        if isinstance(text, str) and text
    ]


@_text_row.register
def _text_grade(record: GraderVerdict, step: Step, options: BoardOptions) -> list[str]:
    verdict = grade_word(record.verdict)
    verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
    spans: list[Span] = [
        ("◆ ", CYAN),
        ("grade  ", DIM),
        (verdict_text.upper(), f"{BOLD};{GRADE_COLORS.get(verdict_text, DIM)}"),
        ("  ", None),
        (full_or_gist(record.summary, verbose=options.verbose), DIM),
    ]
    return [
        _line([*spans, *_tail_spans(step.tail)], color=options.color),
        *_text_facets(step, record, options),
    ]


def _text_facets(step: Step, record: GraderVerdict, options: BoardOptions) -> list[str]:
    """Render the grade's per-facet verdicts, then the rationale under --verbose."""
    rows = facet_rows(step.entry)
    if not rows:
        return []
    names = {name: sanitize(name) for name, _ in rows}
    name_width = max(len(name) for name in names.values())
    lines: list[str] = []
    for name, facet in rows:
        verdict = grade_word(facet.get("verdict"))
        clean = sanitize(verdict)[:FACET_WIDTH] if isinstance(verdict, str) else ""
        verdict_text = clean or "?"
        note = full_or_gist(
            facet.get("note"), verbose=options.verbose, limit=NOTE_LIMIT
        )
        spans: list[Span] = [
            ("  · ", DIM),
            (names[name].ljust(name_width), None),
            ("  ", None),
            (verdict_text.ljust(FACET_WIDTH), FACET_COLORS.get(verdict_text, DIM)),
            ("  ", None),
            (note, DIM),
        ]
        lines.append(_line(spans, color=options.color))
    rationale = record.rationale
    if options.verbose and isinstance(rationale, str) and rationale.strip():
        lines.append(
            _line(
                [("  · ", DIM), ("why: ", DIM), (rationale.strip(), DIM)],
                color=options.color,
            )
        )
    return lines


@_text_row.register
def _text_consult_request(
    record: ConsultationRequest, step: Step, options: BoardOptions
) -> list[str]:
    spans: list[Span] = [
        ("↳ ", CYAN),
        ("consult  ", DIM),
        (agent_label(step.entry.author), BOLD),
        (" → ", DIM),
        (agent_label(record.target), BOLD),
        ("  ", None),
        (full_or_gist(record.question, verbose=options.verbose), DIM),
    ]
    return [_line(spans, color=options.color)]


@_text_row.register
def _text_consult_response(
    record: ConsultationResponse, step: Step, options: BoardOptions
) -> list[str]:
    spans: list[Span] = [
        ("↲ ", CYAN),
        ("consult  ", DIM),
        (agent_label(step.entry.author), BOLD),
        (" → ", DIM),
        (agent_label(step.requester), BOLD),
        ("  ", None),
        (full_or_gist(record.answer, verbose=options.verbose), DIM),
    ]
    return [_line(spans, color=options.color)]


@_text_row.register
def _text_autofix(
    record: DesignDocAutofix | PrdAutofix, step: Step, options: BoardOptions
) -> list[str]:
    label = "prd-autofix  " if isinstance(record, PrdAutofix) else "doc-autofix  "
    spans: list[Span] = [
        ("✚ ", YELLOW),
        (label, DIM),
        (str(record.file or "?"), BOLD),
        ("  " + str(record.category or ""), DIM),
        (_author_note(step.entry), DIM),
    ]
    return [_line(spans, color=options.color)]


def _text_unknown(step: Step, options: BoardOptions) -> list[str]:
    spans: list[Span] = [
        ("• ", DIM),
        (str(step.entry.type_name or "?") + "  ", DIM),
        ("(" + agent_label(step.entry.author) + ")", DIM),
    ]
    return [_line(spans, color=options.color)]


def _text_no_records(req_id: str, options: BoardOptions) -> list[str]:
    return [_style(f"no records for {req_id}", DIM, color=options.color)]


def _text_in_log(named: str, options: BoardOptions) -> list[str]:
    return [_style("in log: " + named, DIM, color=options.color)]


def _text_empty_log(options: BoardOptions) -> list[str]:
    return [_style("handoff log is empty", DIM, color=options.color)]


def _text_footer(errors: Sequence[str], options: BoardOptions) -> list[str]:
    lines = [
        "",
        _style(
            f"! {plural(len(errors), 'problem line')} skipped:",
            RED,
            color=options.color,
        ),
    ]
    lines += [_style("  " + err, DIM, color=options.color) for err in errors]
    return lines


# --- terminal primitives -------------------------------------------------------


def _style(text: str, code: str | None, *, color: bool) -> str:
    """Return the text sanitized, wrapped in its ANSI code when color is on."""
    text = sanitize(text)
    if not color or not code:
        return text
    return f"\033[{code}m{text}\033[0m"


def _line(spans: Sequence[Span], *, color: bool) -> str:
    """Join spans into one line with trailing blanks stripped, so plain and colored output align."""
    clean: list[Span] = [(sanitize(t), c) for t, c in spans if t]
    while clean and not clean[-1][0].strip():
        clean.pop()
    if clean:
        text, code = clean[-1]
        clean[-1] = (text.rstrip(), code)
    return "".join(_style(t, c, color=color) for t, c in clean if t)


def _pad(spans: Sequence[Span], width: int, *, color: bool) -> str:
    """Render spans padded on their plain-text length, so columns align with and without escapes."""
    spans = [(sanitize(t), c) for t, c in spans]
    plain_length = sum(len(t) for t, _ in spans)
    rendered = "".join(_style(t, c, color=color) for t, c in spans)
    return rendered + " " * max(0, width - plain_length)


def _box(span_lines: Sequence[Sequence[Span]], *, color: bool) -> list[str]:
    """Draw the header box around its span lines."""
    width = max(sum(len(t) for t, _ in spans) for spans in span_lines)
    out = [_style("╭" + "─" * (width + 2) + "╮", DIM, color=color)]
    out.extend(
        _style("│ ", DIM, color=color)
        + _pad(spans, width, color=color)
        + _style(" │", DIM, color=color)
        for spans in span_lines
    )
    out.append(_style("╰" + "─" * (width + 2) + "╯", DIM, color=color))
    return out


def _rule_line(core: Sequence[Span], *, color: bool) -> str:
    """Render a gate separator: the core spans, then a rule filled to the view width."""
    core = [(sanitize(t), c) for t, c in core]
    plain_length = sum(len(t) for t, _ in core)
    body = "".join(_style(t, c, color=color) for t, c in core)
    fill = "─" * max(0, VIEW_WIDTH - plain_length - 4)
    return _style("── ", DIM, color=color) + body + " " + _style(fill, DIM, color=color)


# --- the Markdown view ---------------------------------------------------------
# Emphasis has two layers: what the terminal colors render bold, and the known
# step kinds are bolded as anchors so the flow reads off the emphasized words.

_MD_LEAD = "#*->"


def _md_board(board: Board, options: BoardOptions) -> list[str]:
    """Render one slice as Markdown: heading, table, bullets."""
    lines = _md_header(board, options)
    matrix = _md_matrix(board, options)
    if matrix:
        lines.append("")
        lines += matrix
    lines.append("")
    for item in board.timeline:
        lines += (
            _md_session(item, options)
            if isinstance(item, Session)
            else _md_step(item, options)
        )
    return lines


def _md_header(board: Board, options: BoardOptions) -> list[str]:
    """Render the slice heading and summary paragraph."""
    head = "### " + _md_escape(board.req_id or "(no req_id)")
    if board.title:
        title = full_or_gist(board.title, verbose=options.verbose, limit=TITLE_LIMIT)
        head += " — " + _md_escape(title)
    summary = _md_summary(_summary_spans(board, options))
    lines = [head, ""]
    slice_tail = _slice_tail_spans(board.slice_tail)
    if slice_tail:
        lines += [summary + "  ", _md_tail(slice_tail)]
    else:
        lines.append(summary)
    if board.other_slices:
        lines += [
            "",
            "*also in log: " + _md_escape(", ".join(board.other_slices)) + "*",
        ]
    return lines


def _md_matrix(board: Board, options: BoardOptions) -> list[str]:
    """Render the review-convergence matrix as a table."""
    rounds = board.rounds
    if not rounds:
        return []
    lines = [
        "| reviewer | " + " | ".join(f"R{i + 1}" for i in range(len(rounds))) + " |",
        "|" + " --- |" * (len(rounds) + 1),
    ]
    for author in matrix_authors(rounds, options.roster):
        cells = [_md_matrix_cell(round_.get(author)) for round_ in rounds]
        lines.append(
            "| **" + _md_cell(agent_label(author)) + "** | " + " | ".join(cells) + " |"
        )
    return lines


def _md_matrix_cell(entry: Entry | None) -> str:
    """Render one verdict cell; the settled outcomes pop bold."""
    parts: list[str] = []
    for text, _code in _matrix_cell(entry):
        cell = _md_cell(text)
        if text in ("✔", "✖"):
            cell = f"**{cell}**"
        parts.append(cell)
    return "".join(parts)


def _md_session(session: Session, options: BoardOptions) -> list[str]:
    """Render an implement session as a bullet with nested children, then the hoisted siblings."""
    tail = _md_tail(_tail_spans(session.tail))
    label = "(" + _md_escape(agent_label(IMPLEMENTER)) + ")"
    if session.routine:
        label = label[:-1] + " · routine)"
    audit = f"**✗ tier mismatch: {session.tier_note}**" if session.tier_note else ""
    if session.fix:
        parent = _md_step_line(
            "↻",
            "implement",
            label + " ← " + _md_escape(", ".join(session.fix.reviewers)),
            f"({plural(session.fix.findings, 'finding')})"
            if session.fix.findings
            else "",
            audit,
            tail,
            bold_kind=True,
        )
    else:
        parent = _md_step_line("◆", "implement", label, audit, tail, bold_kind=True)
    lines = [parent]
    for child in session.children:
        lines += _md_child(child, options)
    for sibling in session.siblings:
        lines += _md_step(sibling, options)
    return lines


def _md_child(entry: Entry, options: BoardOptions) -> list[str]:
    """Render one nested bullet of an implement session."""
    match entry.record:
        case BuildPass() as record:
            line = "  - ▲ **build ✓ clean**"
            if record.gate_checks_run:
                line += " · " + " · ".join(
                    _md_escape(str(c)) for c in record.gate_checks_run
                )
            return [line]
        case BuildFailure() as record:
            if isinstance(record.abort_reason, str):
                return [
                    "  - ▲ **build ✗ aborted: " + _md_escape(record.abort_reason) + "**"
                ]
            failed = record.failed_check
            outcome = (
                _md_escape(failed) + " failed" if isinstance(failed, str) else "failed"
            )
            line = "  - ▲ **build ✗ " + outcome + "**"
            if record.retry is not None:
                line += f" · retry {_md_escape(str(record.retry))}"
            return [line]
        case ConsultationRequest() as record:
            question = _md_escape(
                full_or_gist(record.question, verbose=options.verbose)
            )
            target = _md_escape(agent_label(record.target))
            return [
                "  - ↳ consult → **"
                + target
                + "**"
                + (" · " + question if question else "")
            ]
        case ConsultationResponse() as record:
            answer = _md_escape(full_or_gist(record.answer, verbose=options.verbose))
            author = _md_escape(agent_label(entry.author))
            return [
                "  - ↲ consult ← **"
                + author
                + "**"
                + (" · " + answer if answer else "")
            ]
        case _:
            return ["  " + line for line in _md_step(Step(entry), options)]


def _md_step(step: Step, options: BoardOptions) -> list[str]:
    """Render one flat timeline bullet."""
    return _md_row(step.entry.record, step, options)


@functools.singledispatch
def _md_row(_record: HandoffRecord, step: Step, _options: BoardOptions) -> list[str]:
    """Render a flat bullet by its record type; a type with no renderer is the unknown bullet."""
    return _md_unknown(step)


@_md_row.register
def _md_fix(_record: DispatchStart, step: Step, _options: BoardOptions) -> list[str]:
    if step.fix is None:
        return []
    return [
        _md_step_line(
            "↻",
            "fix " + agent_label(step.entry.author),
            "← " + _md_escape(", ".join(step.fix.reviewers)),
            f"({plural(step.fix.findings, 'finding')})" if step.fix.findings else "",
            bold_kind=True,
        )
    ]


@_md_row.register
def _md_intake(record: IntakeDecision, step: Step, options: BoardOptions) -> list[str]:
    request = full_or_gist(record.request, verbose=options.verbose, limit=TITLE_LIMIT)
    return [
        _md_step_line(
            "◇",
            "intake",
            _md_escape(request or "(no request)"),
            f"({plural(len(record.decisions), 'decision')})"
            if record.decisions
            else "",
            _md_author(step.entry),
            bold_kind=True,
        )
    ]


@_md_row.register
def _md_prd_entry(record: PrdEntry, step: Step, options: BoardOptions) -> list[str]:
    title = full_or_gist(record.title, verbose=options.verbose, limit=TITLE_LIMIT)
    return [
        _md_step_line(
            "◇",
            "prd-entry",
            _md_escape(title or "(untitled)"),
            _md_author(step.entry),
            _md_tail(_tail_spans(step.tail)),
            bold_kind=True,
        )
    ]


@_md_row.register
def _md_design_block(
    record: DesignBlock, step: Step, _options: BoardOptions
) -> list[str]:
    superseded = record.supersedes_record_at
    return [
        _md_step_line(
            "◈",
            "design-block",
            f"**{_md_escape(str(record.verdict or '?'))}**",
            _md_author(step.entry),
            f"supersedes L{superseded}" if isinstance(superseded, int) else "",
            _md_tail(_tail_spans(step.tail)),
            bold_kind=True,
        )
    ]


@_md_row.register
def _md_build_pass(record: BuildPass, step: Step, _options: BoardOptions) -> list[str]:
    checks = ", ".join(_md_escape(str(c)) for c in record.gate_checks_run)
    return [
        _md_step_line(
            "▲", "build-pass", hhmm_of(step.entry.ts) or "", checks, bold_kind=True
        )
    ]


@_md_row.register
def _md_build_failure(
    record: BuildFailure, step: Step, _options: BoardOptions
) -> list[str]:
    parts: list[str] = []
    if isinstance(record.abort_reason, str):
        parts.append("**abort: " + _md_escape(record.abort_reason) + "**")
    else:
        if isinstance(record.failed_check, str):
            parts.append(_md_escape(record.failed_check))
        if record.retry is not None:
            parts.append(f"retry {_md_escape(str(record.retry))}")
    return [
        _md_step_line(
            "▲", "build-failure", hhmm_of(step.entry.ts) or "", *parts, bold_kind=True
        )
    ]


@_md_row.register
def _md_review(record: ReviewFeedback, step: Step, options: BoardOptions) -> list[str]:
    glyph, color = _verdict_glyph(record.verdict)
    verdict_text = _md_escape(str(record.verdict or "?"))
    if color != DIM:
        verdict_text = f"**{verdict_text}**"
    count = len(record.findings)
    head = _md_step_line(
        glyph,
        "review " + agent_label(step.entry.author),
        "",
        verdict_text,
        f"({plural(count, 'finding')})" if count else "",
        _md_tail(_tail_spans(step.tail)),
        bold_kind=True,
    )
    return [head, *_md_findings(step.entry, options), *_md_recommendations(record)]


def _md_findings(entry: Entry, options: BoardOptions) -> list[str]:
    """Render a review's findings as nested bullets, with the fix under --verbose."""
    lines: list[str] = []
    for finding in findings_of(entry):
        tag = finding.tag
        tag_text = tag if isinstance(tag, str) and tag else "?"
        description = finding.description
        description_text = (
            description
            if options.verbose and isinstance(description, str)
            else gist(description)
        )
        tag_md = "[" + _md_escape(tag_text) + "]"
        if TAG_COLORS.get(tag_text) in RED_TAG_COLORS:
            tag_md = f"**{tag_md}**"
        parts = [
            tag_md,
            _md_code(short_location(finding.location)),
            _md_escape(description_text) if description_text else "",
        ]
        lines.append("  - " + " ".join(p for p in parts if p))
        if options.verbose and isinstance(finding.fix, str) and finding.fix.strip():
            lines.append("    - fix: " + _md_escape(finding.fix.strip()))
    return lines


def _md_recommendations(record: ReviewFeedback) -> list[str]:
    return [
        "  - ▹ rec: " + _md_escape(text)
        for text in record.recommendations
        if isinstance(text, str) and text
    ]


@_md_row.register
def _md_grade(record: GraderVerdict, step: Step, options: BoardOptions) -> list[str]:
    verdict = grade_word(record.verdict)
    verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
    head = _md_step_line(
        "◆",
        "grade " + verdict_text.upper(),
        "",
        _md_escape(full_or_gist(record.summary, verbose=options.verbose)),
        bold_kind=True,
    )
    return [head, *_md_facets(step, record, options)]


def _md_facets(step: Step, record: GraderVerdict, options: BoardOptions) -> list[str]:
    """Render the grade's facets as nested bullets, then the rationale under --verbose."""
    rows = facet_rows(step.entry)
    if not rows:
        return []
    lines: list[str] = []
    for name, facet in rows:
        verdict = grade_word(facet.get("verdict"))
        verdict_text = verdict if isinstance(verdict, str) and verdict else "?"
        parts = [_md_escape(name), f"**{_md_escape(verdict_text)}**"]
        note = full_or_gist(
            facet.get("note"), verbose=options.verbose, limit=NOTE_LIMIT
        )
        if note:
            parts.append(_md_escape(note))
        lines.append("  - " + " — ".join(parts))
    rationale = record.rationale
    if options.verbose and isinstance(rationale, str) and rationale.strip():
        lines.append(f"  - why — {_md_escape(rationale.strip())}")
    return lines


@_md_row.register
def _md_consult_request(
    record: ConsultationRequest, step: Step, options: BoardOptions
) -> list[str]:
    lead = (
        "**"
        + _md_escape(agent_label(step.entry.author))
        + "** → **"
        + _md_escape(agent_label(record.target))
        + "**"
    )
    question = _md_escape(full_or_gist(record.question, verbose=options.verbose))
    return [_md_step_line("↳", "consult", lead, question)]


@_md_row.register
def _md_consult_response(
    record: ConsultationResponse, step: Step, options: BoardOptions
) -> list[str]:
    lead = (
        "**"
        + _md_escape(agent_label(step.entry.author))
        + "** → **"
        + _md_escape(agent_label(step.requester))
        + "**"
    )
    answer = _md_escape(full_or_gist(record.answer, verbose=options.verbose))
    return [_md_step_line("↲", "consult", lead, answer)]


@_md_row.register
def _md_autofix(
    record: DesignDocAutofix | PrdAutofix, step: Step, _options: BoardOptions
) -> list[str]:
    return [
        _md_step_line(
            "✚",
            "prd-autofix" if isinstance(record, PrdAutofix) else "doc-autofix",
            _md_code(str(record.file or "?")),
            _md_escape(str(record.category or "")),
            _md_author(step.entry),
            bold_kind=True,
        )
    ]


def _md_unknown(step: Step) -> list[str]:
    return [
        _md_step_line("•", str(step.entry.type_name or "?"), _md_author(step.entry))
    ]


def _md_no_records(req_id: str, _options: BoardOptions) -> list[str]:
    return [_md_escape(f"no records for {req_id}")]


def _md_in_log(named: str, _options: BoardOptions) -> list[str]:
    return ["", _md_escape("in log: " + named)]


def _md_empty_log(_options: BoardOptions) -> list[str]:
    return ["handoff log is empty"]


def _md_footer(errors: Sequence[str], _options: BoardOptions) -> list[str]:
    lines = ["", _md_escape(f"! {plural(len(errors), 'problem line')} skipped:"), ""]
    lines += ["- " + _md_escape(err) for err in errors]
    return lines


# --- Markdown primitives -------------------------------------------------------


def _md_step_line(
    glyph: str, kind: str, lead: str, *parts: str, bold_kind: bool = False
) -> str:
    """Render one top-level bullet: glyph, kind, lead, then the remaining parts joined by a dot."""
    kind_md = _md_escape(kind)
    if bold_kind:
        kind_md = f"**{kind_md}**"
    head = f"- {glyph} {kind_md}"
    if lead:
        head += " " + lead
    return " · ".join([head] + [p for p in parts if p])


def _md_summary(spans: Sequence[Span]) -> str:
    """Render the header summary with colored spans bold and dim spans plain."""
    return "".join(
        f"**{_md_escape(t)}**" if c and c != DIM else _md_escape(t) for t, c in spans
    )


def _md_tail(spans: Sequence[Span]) -> str:
    """Render a duration and cost tail italic, with the green spans bold inside it."""
    parts: list[str] = []
    for text, code in spans:
        clean = sanitize(text)
        if code == GREEN and clean.strip():
            clean = f"**{clean.strip()}**"
        parts.append(clean)
    body = "".join(parts).strip()
    return f"*{body}*" if body else ""


def _md_author(entry: Entry) -> str:
    return "(" + _md_escape(agent_label(entry.author)) + ")"


def _md_escape(text: object) -> str:
    """Neutralize record text for a Markdown line."""
    escaped = sanitize(str(text)).replace("<", "\\<")
    if escaped and escaped[0] in _MD_LEAD:
        escaped = "\\" + escaped
    return escaped


def _md_cell(text: object) -> str:
    """Escape a table cell, where a pipe would end it early."""
    return _md_escape(text).replace("|", "\\|")


def _md_code(text: object) -> str:
    """Render inline code; backticks cannot nest, so they are replaced."""
    clean = sanitize(str(text)).replace("`", "\u02bc").strip()
    return f"`{clean}`" if clean else ""


_TERMINAL = _Format(
    board=_text_board,
    no_records=_text_no_records,
    in_log=_text_in_log,
    empty_log=_text_empty_log,
    separator=("",),
    footer=_text_footer,
)
_MARKDOWN = _Format(
    board=_md_board,
    no_records=_md_no_records,
    in_log=_md_in_log,
    empty_log=_md_empty_log,
    separator=("", "---", ""),
    footer=_md_footer,
)
