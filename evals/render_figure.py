#!/usr/bin/env python3
"""Render the eval-trend figure source from the trend tables.

Usage: evals/render_figure.py [--out <path>]

Reads evals/results/trend-data.json — the machine-readable derived view
summarize.py regenerates and drift-gates with the pages — and writes
docs/images/eval-trend.drawio, the dated data triptych the README and the
trend page embed. Every mark derives from the recorded cells: the cost
panel is cell spend minus waste over clearing reps, reliability is the
per-version share of reps clearing the bar, quality is the blind-judge
median. The composition contract lives in the update-diagrams skill.
The panels carry no in-plot annotations: the recorded facts they would
restate live in the trend page's notes and the ADRs. When the draw.io desktop CLI
is present the PNG exports too; otherwise the command prints for a manual
run. Review the PNG against the skill's checklist before committing.
Deliberately not part of summarize.py: the figure is a dated snapshot
redrawn at story changes, and the export needs the desktop app. Stdlib
only.
"""

from __future__ import annotations

import datetime
import json
import math
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
TREND_DATA = HERE / "results" / "trend-data.json"
FIGURE = HERE.parent / "docs" / "images" / "eval-trend.drawio"
PNG = FIGURE.with_suffix(".drawio.png")
DRAWIO_CLI = Path("/Applications/draw.io.app/Contents/MacOS/draw.io")

# Known series styles; unknown tasks cycle the muted fallbacks.
TASK_STYLE = {
    "specialty-directory": ("#2F5D8A", 2.4),
    "vets-specialty-filter": ("#6E86A6", 1.6),
    "visit-edit": ("#6E7883", 1.6),
    "owners-page-param": ("#A2ACB8", 1.6),
}
FALLBACK_STYLES = (("#8A94A0", 1.6), ("#5C6B7A", 1.6))


@dataclass(frozen=True)
class Cell:
    """One (task, version) cell of the machine-readable trend data."""

    cleared: int
    reps: int
    spend: float
    waste: float
    bound: bool = False
    # Median delivery wall of the clearing reps, in minutes — the tables'
    # Wall column; None without a clearing rep.
    wall: float | None = None
    # Median over the clearing reps of spend per delivery minute ($/min):
    # cost of a clearing rep ≈ wall × burn rate, the figure's second
    # identity. None without a clearing rep of known spend and wall.
    burn: float | None = None

    @property
    def success_cost(self) -> float | None:
        """Mean spend of the clearing reps alone — the same arithmetic the
        tables print as cost per pass minus the waste share."""
        if self.cleared == 0:
            return None
        return round((self.spend - self.waste) / self.cleared, 2)


@dataclass(frozen=True)
class TrendData:
    versions: tuple[str, ...]
    cells: dict[tuple[str, str], Cell]
    refusal_tasks: frozenset[str]
    quality: dict[str, float | None]
    # The requested root pins each version's reps ran under, aligned to
    # `versions`. A change between neighbours is the one condition boundary
    # the figure draws — derived from the record, never curated.
    pins: tuple[frozenset[str], ...] = ()
    # The API models each version's reps resolved, aligned to `versions`:
    # the rule's label names the later side's set, since the root pin is
    # the trigger but the whole pipeline's models move with an era.
    models: tuple[frozenset[str], ...] = ()

    @property
    def tasks(self) -> tuple[str, ...]:
        return tuple(sorted({t for t, _ in self.cells}))

    @property
    def pin_boundaries(self) -> tuple[int, ...]:
        """Indexes i where versions[i-1] and versions[i] ran under different
        root-pin sets — the rule draws between the two columns."""
        return tuple(
            i
            for i in range(1, len(self.pins))
            if self.pins[i - 1] and self.pins[i] and self.pins[i - 1] != self.pins[i]
        )


def from_payload(payload: dict[str, Any]) -> TrendData:
    """The figure's input from trend-data.json (contract:
    evals/trend-data.schema.json) — per-rep records aggregated here to
    (task, version) cells. The aggregation crosses model pins: the bench
    rarely varies the pin, and this figure accepts the mix as its own
    simplification rather than baking it into the contract."""
    carried = {rep["version"] for rep in payload["reps"]}
    # The schema does not cross-validate reps[].version against the declared
    # axis; a rep outside it would vanish from every panel — fail loud.
    undeclared = carried - set(payload["versions"])
    if undeclared:
        raise SystemExit(
            "render_figure: rep version(s) missing from the versions axis: "
            + ", ".join(sorted(undeclared))
        )
    # A schema-legal payload may declare a version no row carries; a phantom
    # version must never reach the panel arithmetic (division by zero).
    versions = tuple(v for v in payload["versions"] if v in carried)
    kinds: dict[str, str] = {}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    scores: dict[str, list[float]] = {v: [] for v in versions}
    pins: dict[str, set[str]] = {v: set() for v in versions}
    models: dict[str, set[str]] = {v: set() for v in versions}
    for rep in payload["reps"]:
        grouped.setdefault((rep["task"], rep["version"]), []).append(rep)
        pins[rep["version"]].add(str(rep["model_pin"]))
        models[rep["version"]].update(str(m) for m in rep.get("models", []))
        kinds[rep["task"]] = rep["task_kind"]
        if rep["judge_facet_medians"]:
            scores[rep["version"]] += rep["judge_facet_medians"].values()
    cells = {
        key: Cell(
            sum(1 for r in reps if r["cleared"]),
            len(reps),
            sum(r["agent_spend_usd"] for r in reps),
            sum(r["agent_spend_usd"] for r in reps if not r["cleared"]),
            any(not r["spend_known"] for r in reps),
            _wall_minutes(reps),
            _burn_rate(reps),
        )
        for key, reps in grouped.items()
    }
    refusal = frozenset(task for task, kind in kinds.items() if kind == "refusal")
    quality = {v: statistics.median(s) if s else None for v, s in scores.items()}
    return TrendData(
        versions,
        cells,
        refusal,
        quality,
        tuple(frozenset(pins[v]) for v in versions),
        tuple(frozenset(models[v]) for v in versions),
    )


def _wall_minutes(reps: list[dict[str, Any]]) -> float | None:
    """The cell's median delivery wall over its clearing reps, in minutes —
    the same figure the trend table's Wall column carries."""
    walls = [
        float(r["delivery_wall_seconds"])
        for r in reps
        if r["cleared"] and r["delivery_wall_seconds"] is not None
    ]
    return round(statistics.median(walls) / 60, 1) if walls else None


def _burn_rate(reps: list[dict[str, Any]]) -> float | None:
    """The cell's median spend per delivery minute over its clearing reps
    of known spend — a median of per-rep ratios, never a ratio of medians,
    so one slow rep cannot move the figure through the denominator."""
    rates = [
        float(r["agent_spend_usd"]) / (float(r["delivery_wall_seconds"]) / 60)
        for r in reps
        if r["cleared"] and r["spend_known"] and r["delivery_wall_seconds"]
    ]
    return round(statistics.median(rates), 3) if rates else None


def _roll(vals: list[float | None]) -> list[tuple[int, float]]:
    """Centered three-version rolling mean with symmetric windows only:
    an edge point has no neighbor on one side, and a point beside an
    unrecorded version has no symmetric pair — either window collapses to
    the recorded cell itself. The line starts and ends exactly on the
    data, never at a half-window blend hovering off the final dot. A
    version with no recorded value contributes no point."""
    out: list[tuple[int, float]] = []
    recorded = [i for i, v in enumerate(vals) if v is not None]
    if not recorded:
        return out
    first, last = recorded[0], recorded[-1]
    for i, v in enumerate(vals):
        if v is None:
            continue
        radius = (
            1
            if first < i < last and vals[i - 1] is not None and vals[i + 1] is not None
            else 0
        )
        window = [w for w in vals[i - radius : i + radius + 1] if w is not None]
        out.append((i, sum(window) / len(window)))
    return out


def _pchip(
    pts: list[tuple[float, float]], steps: int = 12
) -> list[tuple[float, float]]:
    """Monotone cubic interpolation (Fritsch-Carlson) through the exact
    anchor points, densified into short segments: the drawn line is smooth,
    passes through every computed mean, and can never overshoot — no
    extremum appears that the means do not carry."""
    if len(pts) < 3:
        return pts
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]
    n = len(pts)
    h = [x[i + 1] - x[i] for i in range(n - 1)]
    delta = [(y[i + 1] - y[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = delta[0], delta[-1]
    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0:
            m[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])
    out: list[tuple[float, float]] = []
    for i in range(n - 1):
        for s in range(steps):
            u = s / steps
            h00 = (1 + 2 * u) * (1 - u) ** 2
            h10 = u * (1 - u) ** 2
            h01 = u * u * (3 - 2 * u)
            h11 = u * u * (u - 1)
            out.append(
                (
                    round(x[i] + u * h[i], 1),
                    round(
                        h00 * y[i]
                        + h10 * h[i] * m[i]
                        + h01 * y[i + 1]
                        + h11 * h[i] * m[i + 1],
                        1,
                    ),
                )
            )
    out.append(pts[-1])
    return out


def _edge(eid: str, style: str, pts: list[tuple[float, float]]) -> str:
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    mid = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts[1:-1])
    arr = f'<Array as="points">{mid}</Array>' if mid else ""
    return (
        f'    <mxCell id="{_attr(eid)}" style="{style}" edge="1" parent="1">'
        f'<mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>'
        f'<mxPoint x="{x2}" y="{y2}" as="targetPoint"/>{arr}</mxGeometry></mxCell>'
    )


def _dot(eid: str, x: float, y: float, color: str) -> str:
    return (
        f'    <mxCell id="{_attr(eid)}" value="" style="ellipse;html=1;fillColor={color};'
        f'strokeColor=none;opacity=55;" vertex="1" parent="1">'
        f'<mxGeometry x="{x - 2.5}" y="{y - 2.5}" width="5" height="5" as="geometry"/></mxCell>'
    )


def _attr(value: str) -> str:
    """Escape a string for a double-quoted XML attribute — the context every
    emitted id and value lands in. The quote matters most: without it a task
    id or label breaks out of the attribute into markup."""
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _text(eid: str, value: str, style: str, x: float, y: float, w: int, h: int) -> str:
    return (
        f'    <mxCell id="{_attr(eid)}" value="{_attr(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'
    )


def render_figure(data: TrendData, stamp_date: datetime.date) -> str:
    """The triptych mxGraphModel; the update-diagrams skill holds the
    composition contract this realizes."""
    have_success = any(c.success_cost is not None for c in data.cells.values())
    if not data.versions or not have_success:
        raise SystemExit("render_figure: no clearing rep on record — nothing to draw")
    n = len(data.versions)
    xs = [80 + i * (660 / max(1, n - 1)) for i in range(n)]
    feature_tasks = [t for t in data.tasks if t not in data.refusal_tasks]
    succ = {
        t: [
            data.cells[(t, v)].success_cost if (t, v) in data.cells else None
            for v in data.versions
        ]
        for t in data.tasks
    }
    cmax = max(v for series in succ.values() for v in series if v is not None)
    ctop = max(20.0, math.ceil(cmax / 5) * 5.0)

    def yc(c: float) -> float:
        return round(240 - c * 170 / ctop, 1)

    rel = []
    for v in data.versions:
        pairs = [data.cells[(t, v)] for t in data.tasks if (t, v) in data.cells]
        rel.append(100 * sum(c.cleared for c in pairs) / sum(c.reps for c in pairs))
    rfloor = min(70.0, math.floor(min(rel) / 10) * 10.0)

    def yr(p: float) -> float:
        return round(730 - (p - rfloor) * 60 / (100 - rfloor), 1)

    def yq(q: float) -> float:
        return round(820 - (q - 1) * 15, 1)

    walls = {
        t: [
            data.cells[(t, v)].wall if (t, v) in data.cells else None
            for v in data.versions
        ]
        for t in data.tasks
    }
    wmax = max(
        (w for series in walls.values() for w in series if w is not None), default=0.0
    )
    wtop = max(10.0, math.ceil(wmax / 10) * 10.0)

    def yw(m: float) -> float:
        return round(440 - m * 170 / wtop, 1)

    burns = {
        t: [
            data.cells[(t, v)].burn if (t, v) in data.cells else None
            for v in data.versions
        ]
        for t in data.tasks
    }
    bmax = max(
        (b for series in burns.values() for b in series if b is not None), default=0.0
    )
    btop = max(0.2, math.ceil(bmax * 10) / 10)

    def yburn(b: float) -> float:
        return round(640 - b * 170 / btop, 1)

    latest = data.versions[-1]
    out: list[str] = [
        '<mxGraphModel dx="900" dy="1030" grid="0" gridSize="10" guides="1" tooltips="1"'
        ' connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="900"'
        ' pageHeight="1010" math="0" shadow="0" adaptiveColors="auto">',
        "  <root>",
        '    <mxCell id="0"/>',
        '    <mxCell id="1" parent="0"/>',
        _text(
            "title",
            "The Eval Bench — Cost, Reliability, and Quality by Version",
            "text;html=1;align=center;verticalAlign=middle;fontSize=15;fontStyle=1;fontColor=#1F2933;",
            0,
            12,
            900,
            24,
        ),
        _text(
            "subtitle",
            "the recorded series decomposed — what a success costs, how often reps"
            " succeed, what the blind judge scores, and how long a success takes"
            f" — snapshot through {latest}"
            f" ({stamp_date.isoformat()})",
            "text;html=1;align=center;verticalAlign=middle;fontSize=10;fontColor=#6B7280;",
            0,
            37,
            900,
            14,
        ),
    ]
    grid = "endArrow=none;startArrow=none;html=1;strokeColor=#E7EBF0;strokeWidth=1;dashed=1;dashPattern=3 3;"
    ax = "endArrow=none;startArrow=none;html=1;strokeColor=#DDE4EE;strokeWidth=1;"
    for i, x in enumerate(xs):
        out.append(_edge(f"grid{i}", grid, [(x, 66), (x, 820)]))
    # A root-model change draws one dashed rule between the two columns,
    # one segment per panel so it never crosses a panel caption or the
    # tick labels. Its label sits at the top of the cost panel beside the
    # rule on solid ground — the panel's headroom above the tallest cell —
    # and names the models the later version resolved; the text is derived.
    rule = (
        "endArrow=none;startArrow=none;html=1;strokeColor=#8A96A6;strokeWidth=1.2;"
        "dashed=1;dashPattern=6 4;"
    )
    for k, i in enumerate(data.pin_boundaries):
        x = (xs[i - 1] + xs[i]) / 2
        for seg, (ya, yb) in zip(
            "abcde",
            ((70, 240), (270, 440), (470, 640), (670, 730), (760, 820)),
            strict=True,
        ):
            out.append(_edge(f"pin{k}{seg}", rule, [(x, ya), (x, yb)]))
        named = data.models[i] or data.pins[i]
        label = " · ".join(sorted(m.removeprefix("claude-") for m in named))
        out.append(
            _text(
                f"pinlabel{k}",
                f"models → {label}",
                "text;html=1;align=left;verticalAlign=middle;fontSize=8;fontStyle=2;"
                "fontColor=#6B7785;fillColor=#FFFFFF;strokeColor=none;spacingLeft=2;",
                x + 3,
                72,
                150,
                12,
            )
        )
    panels = (
        ("A", (70, 240)),
        ("D", (270, 440)),
        ("E", (470, 640)),
        ("B", (670, 730)),
        ("C", (760, 820)),
    )
    for name, (ya, yb) in panels:
        out.append(_edge(f"yax{name}", ax, [(80, ya), (80, yb)]))
        out.append(_edge(f"xax{name}", ax, [(80, yb), (740, yb)]))
    ylab = "text;html=1;align=right;verticalAlign=middle;fontSize=9;fontColor=#9AA5B1;"
    plab = "text;html=1;align=center;verticalAlign=middle;fontSize=9;fontStyle=2;fontColor=#6B7280;"
    out.append(
        _text(
            "plA",
            "cost of a clearing rep — successful reps only ($)",
            plab,
            80,
            56,
            660,
            12,
        )
    )
    for tick in (0.0, ctop / 2, ctop):
        out.append(_text(f"ytA{tick:g}", f"${tick:g}", ylab, 24, yc(tick) - 6, 50, 12))
    out.append(
        _text(
            "plB",
            "reliability — share of reps clearing the machine-verified bar (%)",
            plab,
            80,
            654,
            660,
            12,
        )
    )
    for ptick in (rfloor, 100.0):
        out.append(
            _text(f"ytB{int(ptick)}", f"{int(ptick)}%", ylab, 24, yr(ptick) - 6, 50, 12)
        )
    out.append(
        _text(
            "plC",
            "quality — blind-judge median across facets and tasks (1–5)",
            plab,
            80,
            744,
            660,
            12,
        )
    )
    for qtick in (1.0, 5.0):
        out.append(
            _text(f"ytC{int(qtick)}", f"{int(qtick)}", ylab, 24, yq(qtick) - 6, 50, 12)
        )
    out.append(
        _text(
            "plD",
            "wall — median delivery wall of the clearing reps (min)",
            plab,
            80,
            254,
            660,
            12,
        )
    )
    for wtick in (0.0, wtop / 2, wtop):
        out.append(
            _text(f"ytD{wtick:g}", f"{wtick:g}m", ylab, 24, yw(wtick) - 6, 50, 12)
        )
    out.append(
        _text(
            "plE",
            "burn rate — spend per delivery minute of the clearing reps ($/min)",
            plab,
            80,
            454,
            660,
            12,
        )
    )
    for btick in (0.0, btop / 2, btop):
        out.append(
            _text(f"ytE{btick:g}", f"${btick:.2f}", ylab, 24, yburn(btick) - 6, 50, 12)
        )
    styles = dict(TASK_STYLE)
    for i, unstyled in enumerate(t for t in data.tasks if t not in styles):
        styles[unstyled] = FALLBACK_STYLES[i % len(FALLBACK_STYLES)]
    for task in feature_tasks:
        color, width = styles[task]
        trend = _roll(succ[task])
        if len(trend) > 1:
            out.append(
                _edge(
                    f"trend_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth={width};",
                    _pchip([(xs[i], yc(v)) for i, v in trend]),
                )
            )
    for task in data.tasks:
        color, _w = styles[task]
        for i, v in enumerate(data.versions):
            cell = data.cells.get((task, v))
            if cell is None or cell.success_cost is None:
                continue
            y = yc(cell.success_cost)
            if cell.bound:
                # The tables mark an unrecorded-spend cell ">="; the figure's
                # equivalent is a hollow dot — the value is a lower bound.
                out.append(
                    f'    <mxCell id="{_attr(f"d_{task}_{i}")}" value="" '
                    f'style="ellipse;html=1;fillColor=none;strokeColor={color};'
                    'strokeWidth=1.2;" vertex="1" parent="1">'
                    f'<mxGeometry x="{xs[i] - 3}" y="{y - 3}" width="6" height="6"'
                    ' as="geometry"/></mxCell>'
                )
            else:
                out.append(_dot(f"d_{task}_{i}", xs[i], yc(cell.success_cost), color))
    for task in sorted(data.refusal_tasks):
        color, _w = styles[task]
        pts = _pchip(
            [(xs[i], yc(v)) for i, v in enumerate(succ[task]) if v is not None]
        )
        if len(pts) > 1:
            out.append(
                _edge(
                    f"line_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth=1.4;dashed=1;dashPattern=6 3;",
                    pts,
                )
            )
    if len(rel) > 1:
        out.append(
            _edge(
                "line_rel",
                "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;startArrow=none;strokeColor=#6E7883;strokeWidth=1.8;",
                _pchip([(xs[i], yr(p)) for i, p in enumerate(rel)]),
            )
        )
    for i, p in enumerate(rel):
        out.append(_dot(f"d_rel_{i}", xs[i], yr(p), "#6E7883"))
    qpts = [
        (xs[i], yq(q))
        for i, q in enumerate(data.quality[v] for v in data.versions)
        if q is not None
    ]
    qpts = _pchip(qpts)
    if len(qpts) > 1:
        out.append(
            _edge(
                "line_qual",
                "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;startArrow=none;strokeColor=#6E86A6;strokeWidth=1.8;",
                qpts,
            )
        )
    for i, v in enumerate(data.versions):
        qval = data.quality[v]
        if qval is not None:
            out.append(_dot(f"d_qual_{i}", xs[i], yq(qval), "#6E86A6"))
    # The wall panel, second, mirrors the cost panel's encoding — same series
    # styles, smoother, and dashed raw refusal line — so it reads without
    # a second legend; the tasks differ by an order of magnitude in wall,
    # which is why each keeps its own line.
    for task in feature_tasks:
        color, width = styles[task]
        trend = _roll(walls[task])
        if len(trend) > 1:
            out.append(
                _edge(
                    f"wtrend_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth={width};",
                    _pchip([(xs[i], yw(v)) for i, v in trend]),
                )
            )
    for task in data.tasks:
        color, _w = styles[task]
        for i, w in enumerate(walls[task]):
            if w is not None:
                out.append(_dot(f"wd_{task}_{i}", xs[i], yw(w), color))
    for task in sorted(data.refusal_tasks):
        color, _w = styles[task]
        pts = _pchip(
            [(xs[i], yw(v)) for i, v in enumerate(walls[task]) if v is not None]
        )
        if len(pts) > 1:
            out.append(
                _edge(
                    f"wline_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth=1.4;dashed=1;dashPattern=6 3;",
                    pts,
                )
            )
    # Burn rate closes the second identity beneath wall: cost of a clearing
    # rep ≈ wall × burn rate. A flat line means cost tracks time; a rising
    # one, dearer minutes; a falling one, cheaper minutes.
    for task in feature_tasks:
        color, width = styles[task]
        trend = _roll(burns[task])
        if len(trend) > 1:
            out.append(
                _edge(
                    f"btrend_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth={width};",
                    _pchip([(xs[i], yburn(v)) for i, v in trend]),
                )
            )
    for task in data.tasks:
        color, _w = styles[task]
        for i, b in enumerate(burns[task]):
            if b is not None:
                out.append(_dot(f"bd_{task}_{i}", xs[i], yburn(b), color))
    for task in sorted(data.refusal_tasks):
        color, _w = styles[task]
        pts = _pchip(
            [(xs[i], yburn(v)) for i, v in enumerate(burns[task]) if v is not None]
        )
        if len(pts) > 1:
            out.append(
                _edge(
                    f"bline_{task}",
                    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
                    f"startArrow=none;strokeColor={color};strokeWidth=1.4;dashed=1;dashPattern=6 3;",
                    pts,
                )
            )
    # Right-margin labels at each series endpoint, nudged apart when close,
    # once per panel that carries the task series.
    for prefix, series, scale in (
        ("rl", succ, yc),
        ("wrl", walls, yw),
        ("brl", burns, yburn),
    ):
        ends: list[tuple[float, str, str, bool]] = []
        for task in data.tasks:
            last = next((v for v in reversed(series[task]) if v is not None), None)
            if last is None:
                continue
            color, _w = styles[task]
            label = f"{task} (refusal)" if task in data.refusal_tasks else task
            ends.append((scale(last), label, color, styles[task][1] > 2))
        ends.sort(key=lambda e: e[0])
        placed: list[float] = []
        for y, label, color, bold in ends:
            yy = y - 7.0
            if placed and yy < placed[-1] + 13:
                yy = placed[-1] + 13
            placed.append(yy)
            fs = "fontStyle=1;" if bold else ""
            out.append(
                _text(
                    f"{prefix}_{label}",
                    label,
                    f"text;html=1;align=left;verticalAlign=middle;fontSize=10;{fs}fontColor={color};",
                    745,
                    yy,
                    150,
                    14,
                )
            )
    lead = "endArrow=none;startArrow=none;html=1;strokeColor=#C7CDD6;strokeWidth=1;"
    for i, (x, v) in enumerate(zip(xs, data.versions, strict=True)):
        yl = 828 if i % 2 == 0 else 854
        if i % 2:
            out.append(_edge(f"lead{i}", lead, [(x, 820), (x, 852)]))
        out.append(
            _text(
                f"x{i}",
                v,
                "text;html=1;align=center;verticalAlign=top;fontSize=9;fontColor=#3B4252;",
                x - 22,
                yl,
                44,
                12,
            )
        )
    out.append(
        _text(
            "caption",
            "Cost and reliability decompose the trend tables' headline metric: cost per pass"
            " ≈ cost of a clearing rep ÷ share of reps clearing. Dots are recorded cells"
            " from evals/results/trend-data.json, the machine-readable view the tables"
            " render from — the cost value is cell spend minus waste over clearing"
            " reps. Feature-task trends are"
            " centered three-version rolling means with symmetric windows, so the"
            " line starts and ends exactly on the recorded first and last cells."
            " Every line is drawn as a monotone cubic through its points, which"
            " cannot overshoot them."
            " Refusal lines are raw"
            " and dashed (their bar inverts — a correct outcome is a refusal; a cell"
            " with no clearing rep renders no point; a hollow dot marks a"
            " lower-bound cell — part of its spend went unrecorded). Failures"
            " live in the reliability"
            " panel, so no waste hides. The x-axis is ordinal — only measured"
            " versions"
            " appear. A dashed vertical rule marks a change of the requested"
            " root model between adjacent versions; its label names the models"
            " the later version resolved, read from the same data. The wall"
            " panel is context beside the cost: each task's median delivery"
            " wall over its clearing reps, the grader hop excluded — it absorbs"
            " API latency and retries that cost does not. Burn rate closes a"
            " second identity, cost of a clearing rep ≈ wall × burn rate: each"
            " cell is the median over its clearing reps of spend per delivery"
            " minute. A flat line means cost tracks time; a rising one, dearer"
            " minutes (concurrency, context, model era); a falling one, cheaper"
            " minutes (cache).",
            "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=9;fontStyle=2;fontColor=#9AA5B1;",
            100,
            880,
            700,
            120,
        )
    )
    out += ["  </root>", "</mxGraphModel>"]
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    out = FIGURE
    if len(argv) == 3 and argv[1] == "--out":
        out = Path(argv[2])
    elif len(argv) != 1:
        print("usage: evals/render_figure.py [--out <path>]", file=sys.stderr)
        return 2
    data = from_payload(json.loads(TREND_DATA.read_text(encoding="utf-8")))
    out.write_text(render_figure(data, datetime.date.today()), encoding="utf-8")
    print(f"figure source written: {out}")
    png = out.with_suffix(".drawio.png") if out == FIGURE else out.with_suffix(".png")
    cmd = [
        str(DRAWIO_CLI),
        "-x",
        "-f",
        "png",
        "-e",
        "-b",
        "12",
        "-s",
        "2",
        "-o",
        str(png),
        str(out),
    ]
    if DRAWIO_CLI.is_file():
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as err:
            tail = (err.stderr or "").strip().splitlines()[-3:]
            print("render_figure: draw.io export failed:", file=sys.stderr)
            for line in tail:
                print(f"  {line}", file=sys.stderr)
            return 1
        print(
            f"png exported: {png} — review it against the update-diagrams checklist, then commit both files"
        )
    else:
        print("draw.io CLI not found — export manually:\n  " + " ".join(cmd))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
