#!/usr/bin/env python3
"""Render the eval-trend figure source from the machine-readable trend data.

Every mark derives from the recorded cells; the composition contract lives
in the update-diagrams skill. The figure is a dated snapshot redrawn at
story changes, and the PNG export needs the draw.io desktop app, so the
renderer stays outside summarize.py.
"""

import argparse
import datetime
import json
import math
import re
import statistics
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from summarize import JUDGE_FACETS

HERE = Path(__file__).resolve().parent
TREND_DATA = HERE / "results" / "trend-data.json"
FIGURE = HERE.parent / "docs" / "images" / "eval-trend.drawio"
DRAWIO_CLI = Path("/Applications/draw.io.app/Contents/MacOS/draw.io")

# The one stroke width that carries the accent; its label renders bold.
ACCENT_WIDTH = 2.4

# Known series styles; unknown tasks cycle the muted fallbacks.
TASK_STYLE = {
    "specialty-directory": ("#2F5D8A", ACCENT_WIDTH),
    "vets-specialty-filter": ("#6E86A6", 1.6),
    "visit-edit": ("#6E7883", 1.6),
    "owners-page-param": ("#A2ACB8", 1.6),
}
FALLBACK_STYLES = (("#8A94A0", 1.6), ("#5C6B7A", 1.6))

# Facet styles are assigned by position over the judge roster summarize.py
# owns, so a facet rename cannot strand a style; the first facet carries the
# accent.
_FACET_PALETTE = (
    ("#2F5D8A", ACCENT_WIDTH),
    ("#6E86A6", 1.6),
    ("#6E7883", 1.6),
    ("#A2ACB8", 1.6),
)
FACET_STYLE = {
    facet: _FACET_PALETTE[i % len(_FACET_PALETTE)]
    for i, facet in enumerate(JUDGE_FACETS)
}
DEFECT_STYLE = ("#5C7A99", 1.6)
DEFECT_LABEL = "known-defect clear"
BAR_LABEL = "bar cleared"
BAR_STYLE = ("#6E7883", 1.8)

SECONDS_PER_MINUTE = 60
ROLLING_RADIUS = 1
MIN_SPLINE_POINTS = 3
SPLINE_STEPS = 12
QUALITY_FLOOR = 1.0  # the rubric's lowest score
QUALITY_TOP = 5.0
RELIABILITY_FLOOR = 0.0
COST_TOP_MINIMUM = 20.0
WALL_TOP_MINIMUM = 10.0
BURN_TOP_MINIMUM = 0.2
LABEL_GAP = 13.0
LABEL_LIFT = 7.0

PLOT_LEFT = 80
PLOT_RIGHT = 740
PLOT_WIDTH = PLOT_RIGHT - PLOT_LEFT
LABEL_COLUMN = 745
TICK_COLUMN = 24
GRID_TOP = 66
GRID_BOTTOM = 880

# The panels' vertical bands, top to bottom on the page.
COST_BAND = (70, 240)
WALL_BAND = (270, 440)
BURN_BAND = (470, 640)
RELIABILITY_BAND = (670, 730)
QUALITY_BAND = (760, 880)
BANDS = (COST_BAND, WALL_BAND, BURN_BAND, RELIABILITY_BAND, QUALITY_BAND)
PANEL_NAMES = ("A", "D", "E", "B", "C")

GRID_STYLE = "endArrow=none;startArrow=none;html=1;strokeColor=#E7EBF0;strokeWidth=1;dashed=1;dashPattern=3 3;"
AXIS_STYLE = "endArrow=none;startArrow=none;html=1;strokeColor=#DDE4EE;strokeWidth=1;"
RULE_STYLE = (
    "endArrow=none;startArrow=none;html=1;strokeColor=#8A96A6;strokeWidth=1.2;"
    "dashed=1;dashPattern=6 4;"
)
LEAD_STYLE = "endArrow=none;startArrow=none;html=1;strokeColor=#C7CDD6;strokeWidth=1;"
TICK_LABEL_STYLE = (
    "text;html=1;align=right;verticalAlign=middle;fontSize=9;fontColor=#9AA5B1;"
)
PANEL_LABEL_STYLE = "text;html=1;align=center;verticalAlign=middle;fontSize=9;fontStyle=2;fontColor=#6B7280;"
LINE_STYLE = (
    "edgeStyle=none;rounded=0;curved=0;html=1;jettySize=0;endArrow=none;"
    "startArrow=none;strokeColor={color};strokeWidth={width};"
)
DASHED_LINE_STYLE = LINE_STYLE + "dashed=1;dashPattern=6 3;"
REFUSAL_WIDTH = 1.4


class Box(NamedTuple):
    """The geometry of one text cell."""

    x: float
    y: float
    w: int
    h: int


@dataclass(frozen=True)
class Cell:
    """One (task, version) cell of the machine-readable trend data."""

    cleared: int
    reps: int
    spend: float
    waste: float
    bound: bool = False
    wall: float | None = None
    burn: float | None = None

    @property
    def success_cost(self) -> float | None:
        """Return the mean spend of the clearing reps alone, or None without one."""
        if self.cleared == 0:
            return None
        return round((self.spend - self.waste) / self.cleared, 2)


@dataclass(frozen=True)
class TrendData:
    """The figure's input: cells, refusal tasks, and the per-version series."""

    versions: tuple[str, ...]
    cells: dict[tuple[str, str], Cell]
    refusal_tasks: frozenset[str]
    # Per facet, the mean of the per-rep judge medians over each version's
    # judged reps: a pooled median of a five-point scale saturates at 4 and
    # shows no drift inside the top band.
    quality: dict[str, list[float | None]]
    # Per version, the share of probed reps clearing every named defect
    # their task declares; reps of unprobed tasks stay out of the denominator.
    defect_clear: tuple[float | None, ...] = ()
    # The requested root pins per version; a change between neighbours is
    # the one condition boundary the figure draws.
    pins: tuple[frozenset[str], ...] = ()
    # The API models per version, since the whole pipeline's models move
    # with an era.
    models: tuple[frozenset[str], ...] = ()

    @property
    def tasks(self) -> tuple[str, ...]:
        """Return every task on record, sorted."""
        return tuple(sorted({task for task, _ in self.cells}))

    @property
    def facets(self) -> tuple[str, ...]:
        """Return the rubric facets in the tables' order."""
        return tuple(self.quality)

    @property
    def pin_boundaries(self) -> tuple[int, ...]:
        """Return the indexes whose version ran under a different root pin than its predecessor."""
        return tuple(
            i
            for i in range(1, len(self.pins))
            if self.pins[i - 1] and self.pins[i] and self.pins[i - 1] != self.pins[i]
        )


def _wall_minutes(reps: list[dict[str, Any]]) -> float | None:
    """Return the median delivery wall of the clearing reps, in minutes."""
    walls = [
        float(rep["delivery_wall_seconds"])
        for rep in reps
        if rep["cleared"] and rep["delivery_wall_seconds"] is not None
    ]
    return round(statistics.median(walls) / SECONDS_PER_MINUTE, 1) if walls else None


def _burn_rate(reps: list[dict[str, Any]]) -> float | None:
    """Return the median spend per delivery minute of the clearing reps of known spend."""
    # A refusal delivers no change, so it has no delivery minute; the
    # tables show its burn as a dash and the panel draws no refusal line.
    # A median of per-rep ratios, never a ratio of medians, so one slow rep
    # cannot move the figure through the denominator.
    rates = [
        float(rep["agent_spend_usd"])
        / (float(rep["delivery_wall_seconds"]) / SECONDS_PER_MINUTE)
        for rep in reps
        if rep["task_kind"] != "refusal"
        and rep["cleared"]
        and rep["spend_known"]
        and rep["delivery_wall_seconds"]
    ]
    return round(statistics.median(rates), 3) if rates else None


def _cell(reps: list[dict[str, Any]]) -> Cell:
    """Aggregate the reps of one (task, version) into a cell."""
    return Cell(
        sum(1 for rep in reps if rep["cleared"]),
        len(reps),
        sum(rep["agent_spend_usd"] for rep in reps),
        sum(rep["agent_spend_usd"] for rep in reps if not rep["cleared"]),
        any(not rep["spend_known"] for rep in reps),
        _wall_minutes(reps),
        _burn_rate(reps),
    )


def _quality_series(
    reps: list[dict[str, Any]], versions: tuple[str, ...]
) -> dict[str, list[float | None]]:
    """Build the per-facet series of per-version means, styled facets first."""
    scores: dict[str, dict[str, list[float]]] = {}
    for rep in reps:
        for facet, score in (rep["judge_facet_medians"] or {}).items():
            scores.setdefault(facet, {}).setdefault(rep["version"], []).append(
                float(score)
            )
    facets = [facet for facet in FACET_STYLE if facet in scores] + sorted(
        facet for facet in scores if facet not in FACET_STYLE
    )
    return {
        facet: [
            round(statistics.mean(scores[facet][version]), 2)
            if scores[facet].get(version)
            else None
            for version in versions
        ]
        for facet in facets
    }


def _defect_clear(
    reps: list[dict[str, Any]], versions: tuple[str, ...]
) -> tuple[float | None, ...]:
    """Return the per-version share of probed reps clearing every named defect."""
    probed: dict[str, list[bool]] = {version: [] for version in versions}
    for rep in reps:
        defects = rep.get("known_defects")
        if isinstance(defects, dict) and defects:
            probed[rep["version"]].append(not any(defects.values()))
    return tuple(
        round(100 * sum(probed[version]) / len(probed[version]), 1)
        if probed[version]
        else None
        for version in versions
    )


def from_payload(payload: dict[str, Any]) -> TrendData:
    """Aggregate the per-rep records of trend-data.json into the figure's input."""
    # The aggregation crosses model pins: the bench rarely varies the pin,
    # and the figure accepts the mix as its own simplification.
    reps: list[dict[str, Any]] = payload["reps"]
    carried = {rep["version"] for rep in reps}
    # The schema does not cross-validate the rep versions against the axis;
    # a rep outside it would vanish from every panel.
    undeclared = carried - set(payload["versions"])
    if undeclared:
        raise ValueError(
            "render_figure: rep version(s) missing from the versions axis: "
            + ", ".join(sorted(undeclared))
        )
    # A phantom version no row carries must never reach the panel arithmetic.
    versions = tuple(v for v in payload["versions"] if v in carried)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    kinds: dict[str, str] = {}
    pins: dict[str, set[str]] = {version: set() for version in versions}
    models: dict[str, set[str]] = {version: set() for version in versions}
    for rep in reps:
        grouped.setdefault((rep["task"], rep["version"]), []).append(rep)
        pins[rep["version"]].add(str(rep["model_pin"]))
        models[rep["version"]].update(str(m) for m in rep.get("models", []))
        kinds[rep["task"]] = rep["task_kind"]
    return TrendData(
        versions,
        {key: _cell(group) for key, group in grouped.items()},
        frozenset(task for task, kind in kinds.items() if kind == "refusal"),
        _quality_series(reps, versions),
        _defect_clear(reps, versions),
        tuple(frozenset(pins[version]) for version in versions),
        tuple(frozenset(models[version]) for version in versions),
    )


def rolling_mean(vals: list[float | None]) -> list[tuple[int, float]]:
    """Return the centered three-version rolling mean, symmetric windows only."""
    # An edge point or a point beside an unrecorded version collapses to
    # the recorded cell itself, so the line starts and ends on the data.
    out: list[tuple[int, float]] = []
    recorded = [i for i, v in enumerate(vals) if v is not None]
    if not recorded:
        return out
    first, last = recorded[0], recorded[-1]
    for i, v in enumerate(vals):
        if v is None:
            continue
        symmetric = (
            first < i < last and vals[i - 1] is not None and vals[i + 1] is not None
        )
        radius = ROLLING_RADIUS if symmetric else 0
        window = [w for w in vals[i - radius : i + radius + 1] if w is not None]
        out.append((i, sum(window) / len(window)))
    return out


def _slopes(x: list[float], y: list[float]) -> tuple[list[float], list[float]]:
    """Return the interval widths and the Fritsch-Carlson tangents of the anchors."""
    n = len(x)
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
    return h, m


def pchip(
    pts: list[tuple[float, float]], steps: int = SPLINE_STEPS
) -> list[tuple[float, float]]:
    """Densify a polyline into a monotone cubic through its points, which cannot overshoot."""
    if len(pts) < MIN_SPLINE_POINTS:
        return pts
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]
    h, m = _slopes(x, y)
    out: list[tuple[float, float]] = []
    for i in range(len(pts) - 1):
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


_XML_ILLEGAL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _attr(value: str) -> str:
    """Escape a string for a double-quoted XML attribute, dropping illegal control characters."""
    value = _XML_ILLEGAL_RE.sub("", value)
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _edge(eid: str, style: str, pts: list[tuple[float, float]]) -> str:
    """Render one polyline edge cell."""
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
    """Render one filled data dot."""
    return (
        f'    <mxCell id="{_attr(eid)}" value="" style="ellipse;html=1;fillColor={color};'
        f'strokeColor=none;opacity=55;" vertex="1" parent="1">'
        f'<mxGeometry x="{x - 2.5}" y="{y - 2.5}" width="5" height="5" as="geometry"/></mxCell>'
    )


def _hollow_dot(eid: str, x: float, y: float, color: str) -> str:
    """Render one hollow dot, the mark of a lower-bound cell."""
    return (
        f'    <mxCell id="{_attr(eid)}" value="" '
        f'style="ellipse;html=1;fillColor=none;strokeColor={color};'
        'strokeWidth=1.2;" vertex="1" parent="1">'
        f'<mxGeometry x="{x - 3}" y="{y - 3}" width="6" height="6"'
        ' as="geometry"/></mxCell>'
    )


def text_cell(eid: str, value: str, style: str, box: Box) -> str:
    """Render one text cell."""
    return (
        f'    <mxCell id="{_attr(eid)}" value="{_attr(value)}" style="{style}" vertex="1" parent="1">'
        f'<mxGeometry x="{box.x}" y="{box.y}" width="{box.w}" height="{box.h}" as="geometry"/></mxCell>'
    )


@dataclass(frozen=True, slots=True)
class _Axis:
    """One panel's vertical scale from a value range onto a page band."""

    bottom: float
    height: float
    low: float
    high: float

    def y(self, value: float) -> float:
        """Map a value onto the page."""
        return round(
            self.bottom - (value - self.low) * self.height / (self.high - self.low), 1
        )


Series = dict[str, list[float | None]]
Styles = dict[str, tuple[str, float]]


def _series(data: TrendData, measure: Callable[[Cell], float | None]) -> Series:
    """Return one cell measure per task, aligned to the versions."""
    return {
        task: [
            measure(data.cells[(task, version)])
            if (task, version) in data.cells
            else None
            for version in data.versions
        ]
        for task in data.tasks
    }


def _series_max(series: Series) -> float:
    """Return the largest recorded value across a series, or 0."""
    return max(
        (v for values in series.values() for v in values if v is not None), default=0.0
    )


def _styled(keys: tuple[str, ...], known: Styles) -> Styles:
    """Assign the known styles, cycling the fallbacks over the unknown keys."""
    styles = dict(known)
    for i, unstyled in enumerate(key for key in keys if key not in styles):
        styles[unstyled] = FALLBACK_STYLES[i % len(FALLBACK_STYLES)]
    return styles


def _reliability(data: TrendData) -> list[float]:
    """Return the per-version share of reps clearing the bar."""
    shares = []
    for version in data.versions:
        cells = [
            data.cells[(task, version)]
            for task in data.tasks
            if (task, version) in data.cells
        ]
        shares.append(100 * sum(c.cleared for c in cells) / sum(c.reps for c in cells))
    return shares


@dataclass(frozen=True, slots=True)
class _Figure:
    """Every derived series, scale, and style the panels draw from."""

    data: TrendData
    xs: tuple[float, ...]
    styles: Styles
    facet_styles: Styles
    cost_series: Series
    wall_series: Series
    burn_series: Series
    reliability: list[float]
    defects: list[float | None]
    cost: _Axis
    wall: _Axis
    burn: _Axis
    reliability_axis: _Axis
    quality: _Axis

    @property
    def has_defects(self) -> bool:
        """Tell whether any version carries a known-defect clear rate."""
        return any(d is not None for d in self.defects)

    @property
    def feature_tasks(self) -> list[str]:
        """Return the tasks that are not refusal tasks."""
        return [task for task in self.data.tasks if task not in self.data.refusal_tasks]


def _figure(data: TrendData) -> _Figure:
    """Derive the series and scales of one figure."""
    n = len(data.versions)
    xs = tuple(PLOT_LEFT + i * (PLOT_WIDTH / max(1, n - 1)) for i in range(n))
    cost_series = _series(data, lambda cell: cell.success_cost)
    wall_series = _series(data, lambda cell: cell.wall)
    burn_series = _series(data, lambda cell: cell.burn)
    reliability = _reliability(data)
    defects: list[float | None] = list(data.defect_clear)
    cost_top = max(COST_TOP_MINIMUM, math.ceil(_series_max(cost_series) / 5) * 5.0)
    wall_top = max(WALL_TOP_MINIMUM, math.ceil(_series_max(wall_series) / 10) * 10.0)
    burn_top = max(BURN_TOP_MINIMUM, math.ceil(_series_max(burn_series) * 10) / 10)
    # Every floor is fixed: reliability at 0 and quality at the rubric's
    # lowest score. Only a ceiling adapts to the series, since a moving
    # ceiling keeps the ratio between points and a moving floor does not.
    return _Figure(
        data=data,
        xs=xs,
        styles=_styled(data.tasks, TASK_STYLE),
        facet_styles=_styled(data.facets, FACET_STYLE),
        cost_series=cost_series,
        wall_series=wall_series,
        burn_series=burn_series,
        reliability=reliability,
        defects=defects,
        cost=_Axis(COST_BAND[1], 170, 0.0, cost_top),
        wall=_Axis(WALL_BAND[1], 170, 0.0, wall_top),
        burn=_Axis(BURN_BAND[1], 170, 0.0, burn_top),
        reliability_axis=_Axis(RELIABILITY_BAND[1], 60, RELIABILITY_FLOOR, 100.0),
        quality=_Axis(QUALITY_BAND[1], 120, QUALITY_FLOOR, QUALITY_TOP),
    )


def _header(fig: _Figure, stamp_date: datetime.date) -> list[str]:
    """Open the model with the title and the dated subtitle."""
    latest = fig.data.versions[-1]
    return [
        '<mxGraphModel dx="900" dy="1110" grid="0" gridSize="10" guides="1" tooltips="1"'
        ' connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="900"'
        ' pageHeight="1090" math="0" shadow="0" adaptiveColors="auto">',
        "  <root>",
        '    <mxCell id="0"/>',
        '    <mxCell id="1" parent="0"/>',
        text_cell(
            "title",
            "The Eval Bench — Cost, Reliability, and Quality by Version",
            "text;html=1;align=center;verticalAlign=middle;fontSize=15;fontStyle=1;fontColor=#1F2933;",
            Box(0, 12, 900, 24),
        ),
        text_cell(
            "subtitle",
            "the recorded series decomposed — what a success costs, how often reps"
            " succeed, what the blind judge scores, and how long a success takes"
            f" — snapshot through {latest}"
            f" ({stamp_date.isoformat()})",
            "text;html=1;align=center;verticalAlign=middle;fontSize=10;fontColor=#6B7280;",
            Box(0, 37, 900, 14),
        ),
    ]


def _frame(fig: _Figure) -> list[str]:
    """Draw the version grid, the root-model rules, and the panel axes."""
    out = [
        _edge(f"grid{i}", GRID_STYLE, [(x, GRID_TOP), (x, GRID_BOTTOM)])
        for i, x in enumerate(fig.xs)
    ]
    # A root-model change draws one dashed rule between the two columns,
    # one segment per panel so it never crosses a caption; its label sits
    # in the cost panel's headroom and names the later side's models.
    for k, i in enumerate(fig.data.pin_boundaries):
        x = (fig.xs[i - 1] + fig.xs[i]) / 2
        for segment, (top, bottom) in zip("abcde", BANDS, strict=True):
            out.append(_edge(f"pin{k}{segment}", RULE_STYLE, [(x, top), (x, bottom)]))
        named = fig.data.models[i] or fig.data.pins[i]
        label = " · ".join(sorted(m.removeprefix("claude-") for m in named))
        out.append(
            text_cell(
                f"pinlabel{k}",
                f"models → {label}",
                "text;html=1;align=left;verticalAlign=middle;fontSize=8;fontStyle=2;"
                "fontColor=#6B7785;fillColor=#FFFFFF;strokeColor=none;spacingLeft=2;",
                Box(x + 3, 72, 150, 12),
            )
        )
    for name, (top, bottom) in zip(PANEL_NAMES, BANDS, strict=True):
        out.append(
            _edge(f"yax{name}", AXIS_STYLE, [(PLOT_LEFT, top), (PLOT_LEFT, bottom)])
        )
        out.append(
            _edge(f"xax{name}", AXIS_STYLE, [(PLOT_LEFT, bottom), (PLOT_RIGHT, bottom)])
        )
    return out


def _panel_label(name: str, text: str, y: float) -> str:
    """Render one panel's caption line."""
    return text_cell(f"pl{name}", text, PANEL_LABEL_STYLE, Box(PLOT_LEFT, y, 660, 12))


def _tick(eid: str, label: str, y: float) -> str:
    """Render one axis tick label."""
    return text_cell(eid, label, TICK_LABEL_STYLE, Box(TICK_COLUMN, y - 6, 50, 12))


def _captions(fig: _Figure) -> list[str]:
    """Render every panel's caption and tick labels."""
    cost, wall, burn = fig.cost, fig.wall, fig.burn
    reliability, quality = fig.reliability_axis, fig.quality
    out = [_panel_label("A", "cost of a clearing rep — successful reps only ($)", 56)]
    out.extend(
        _tick(f"ytA{tick:g}", f"${tick:g}", cost.y(tick))
        for tick in (0.0, cost.high / 2, cost.high)
    )
    defect_note = (
        ", and of probed reps clearing every named defect (dashed, rolling mean)"
        if fig.has_defects
        else ""
    )
    out.append(
        _panel_label(
            "B",
            "reliability — share of reps clearing the machine-verified bar (%)"
            + defect_note,
            654,
        )
    )
    out.extend(
        _tick(f"ytB{int(tick)}", f"{int(tick)}%", reliability.y(tick))
        for tick in (reliability.low, 100.0)
    )
    out.append(
        _panel_label(
            "C",
            "quality — blind-judge mean per rubric facet over the version's judged reps"
            f" ({quality.low:g}–5)",  # noqa: RUF001
            744,
        )
    )
    quality_ticks = [quality.low, QUALITY_TOP]
    if ((quality.low + QUALITY_TOP) / 2).is_integer():
        quality_ticks.insert(1, (quality.low + QUALITY_TOP) / 2)
    out.extend(
        _tick(f"ytC{int(tick)}", f"{int(tick)}", quality.y(tick))
        for tick in quality_ticks
    )
    out.append(
        _panel_label("D", "wall — median delivery wall of the clearing reps (min)", 254)
    )
    out.extend(
        _tick(f"ytD{tick:g}", f"{tick:g}m", wall.y(tick))
        for tick in (0.0, wall.high / 2, wall.high)
    )
    out.append(
        _panel_label(
            "E",
            "burn rate — spend per delivery minute of the clearing reps ($/min)",
            454,
        )
    )
    out.extend(
        _tick(f"ytE{tick:g}", f"${tick:.2f}", burn.y(tick))
        for tick in (0.0, burn.high / 2, burn.high)
    )
    return out


@dataclass(frozen=True, slots=True)
class _TaskPanel:
    """One panel keyed by task: its series, its scale, and its cell id prefixes."""

    series: Series
    axis: _Axis
    trend_id: str
    dot_id: str
    line_id: str
    hollow_bounds: bool = False


def _task_panel(fig: _Figure, panel: _TaskPanel) -> list[str]:
    """Draw the feature trends, the recorded dots, and the raw refusal lines of one panel."""
    out = []
    for task in fig.feature_tasks:
        color, width = fig.styles[task]
        trend = rolling_mean(panel.series[task])
        if len(trend) > 1:
            out.append(
                _edge(
                    f"{panel.trend_id}{task}",
                    LINE_STYLE.format(color=color, width=width),
                    pchip([(fig.xs[i], panel.axis.y(v)) for i, v in trend]),
                )
            )
    for task in fig.data.tasks:
        color, _ = fig.styles[task]
        for i, value in enumerate(panel.series[task]):
            if value is None:
                continue
            cell = fig.data.cells.get((task, fig.data.versions[i]))
            # The tables mark an unrecorded-spend cell ">="; the figure's
            # equivalent is a hollow dot.
            mark = (
                _hollow_dot
                if panel.hollow_bounds and cell is not None and cell.bound
                else _dot
            )
            out.append(
                mark(f"{panel.dot_id}{task}_{i}", fig.xs[i], panel.axis.y(value), color)
            )
    for task in sorted(fig.data.refusal_tasks):
        color, _ = fig.styles[task]
        pts = pchip(
            [
                (fig.xs[i], panel.axis.y(v))
                for i, v in enumerate(panel.series[task])
                if v is not None
            ]
        )
        if len(pts) > 1:
            out.append(
                _edge(
                    f"{panel.line_id}{task}",
                    DASHED_LINE_STYLE.format(color=color, width=REFUSAL_WIDTH),
                    pts,
                )
            )
    return out


def _reliability_panel(fig: _Figure) -> list[str]:
    """Draw the bar-clearing share and, when recorded, the known-defect clear rate."""
    axis = fig.reliability_axis
    out = []
    if len(fig.reliability) > 1:
        out.append(
            _edge(
                "line_rel",
                LINE_STYLE.format(color=BAR_STYLE[0], width=BAR_STYLE[1]),
                pchip([(fig.xs[i], axis.y(p)) for i, p in enumerate(fig.reliability)]),
            )
        )
    out.extend(
        _dot(f"d_rel_{i}", fig.xs[i], axis.y(p), BAR_STYLE[0])
        for i, p in enumerate(fig.reliability)
    )
    if not fig.has_defects:
        return out
    # Three reps a cell would make a raw curve move one lucky rep apart, so
    # the line is the cost panel's rolling mean while the dots stay raw.
    trend = rolling_mean(fig.defects)
    if len(trend) > 1:
        out.append(
            _edge(
                "dline",
                DASHED_LINE_STYLE.format(color=DEFECT_STYLE[0], width=DEFECT_STYLE[1]),
                pchip([(fig.xs[i], axis.y(v)) for i, v in trend]),
            )
        )
    out.extend(
        _dot(f"dd_{i}", fig.xs[i], axis.y(d), DEFECT_STYLE[0])
        for i, d in enumerate(fig.defects)
        if d is not None
    )
    return out


def _quality_panel(fig: _Figure) -> list[str]:
    """Draw one raw line per rubric facet through the per-version means."""
    # No rolling mean: the version-level datum is the mean itself, and
    # rolling it would hide the single-version move a targeted change makes.
    out = []
    for facet in fig.data.facets:
        color, width = fig.facet_styles[facet]
        values = fig.data.quality[facet]
        pts = pchip(
            [
                (fig.xs[i], fig.quality.y(q))
                for i, q in enumerate(values)
                if q is not None
            ]
        )
        if len(pts) > 1:
            out.append(
                _edge(
                    f"qline_{facet}", LINE_STYLE.format(color=color, width=width), pts
                )
            )
        out.extend(
            _dot(f"qd_{facet}_{i}", fig.xs[i], fig.quality.y(q), color)
            for i, q in enumerate(values)
            if q is not None
        )
    return out


@dataclass(frozen=True, slots=True)
class _LabelGroup:
    """The keyed series one panel labels at its right margin."""

    prefix: str
    series: Series
    axis: _Axis
    styles: Styles


def _end_labels(fig: _Figure, group: _LabelGroup) -> list[str]:
    """Label each series at its endpoint, nudging labels apart when they touch."""
    facet_labels = {facet: facet.replace("_", "-") for facet in fig.data.facets}
    ends: list[tuple[float, str, str, bool]] = []
    for key, values in group.series.items():
        last = next((v for v in reversed(values) if v is not None), None)
        if last is None:
            continue
        color, width = group.styles[key]
        label = (
            f"{key} (refusal)"
            if key in fig.data.refusal_tasks
            else facet_labels.get(key, key)
        )
        ends.append((group.axis.y(last), label, color, width == ACCENT_WIDTH))
    ends.sort(key=lambda end: end[0])
    out = []
    placed: list[float] = []
    for y, label, color, bold in ends:
        lifted = y - LABEL_LIFT
        if placed and lifted < placed[-1] + LABEL_GAP:
            lifted = placed[-1] + LABEL_GAP
        placed.append(lifted)
        weight = "fontStyle=1;" if bold else ""
        out.append(
            text_cell(
                f"{group.prefix}_{label}",
                label,
                f"text;html=1;align=left;verticalAlign=middle;fontSize=10;{weight}fontColor={color};",
                Box(LABEL_COLUMN, lifted, 150, 14),
            )
        )
    return out


def _label_groups(fig: _Figure) -> tuple[_LabelGroup, ...]:
    """List the right-margin label groups in panel order."""
    reliability_series: Series = (
        {BAR_LABEL: [float(p) for p in fig.reliability], DEFECT_LABEL: fig.defects}
        if fig.has_defects
        else {}
    )
    return (
        _LabelGroup("rl", fig.cost_series, fig.cost, fig.styles),
        _LabelGroup("wrl", fig.wall_series, fig.wall, fig.styles),
        _LabelGroup("brl", fig.burn_series, fig.burn, fig.styles),
        _LabelGroup("qrl", fig.data.quality, fig.quality, fig.facet_styles),
        _LabelGroup(
            "prl",
            reliability_series,
            fig.reliability_axis,
            {BAR_LABEL: BAR_STYLE, DEFECT_LABEL: DEFECT_STYLE},
        ),
    )


def _version_labels(fig: _Figure) -> list[str]:
    """Label the ordinal version axis, alternating rows with leader lines."""
    out = []
    for i, (x, version) in enumerate(zip(fig.xs, fig.data.versions, strict=True)):
        y = 888 if i % 2 == 0 else 914
        if i % 2:
            out.append(_edge(f"lead{i}", LEAD_STYLE, [(x, GRID_BOTTOM), (x, 912)]))
        out.append(
            text_cell(
                f"x{i}",
                version,
                "text;html=1;align=center;verticalAlign=top;fontSize=9;fontColor=#3B4252;",
                Box(x - 22, y, 44, 12),
            )
        )
    return out


def _caption(fig: _Figure) -> str:
    """Render the three-line key beneath the panels: how to read the marks, and where the method lives."""
    defect_note = (
        " the dashed reliability line is the known-defect clear rate, a rolling mean."
        if fig.has_defects
        else ""
    )
    return text_cell(
        "caption",
        "Dots are recorded cells from evals/results/trend-data.json; feature lines"
        " are three-version rolling means, refusal and quality lines are raw; the"
        " x-axis is ordinal, only measured versions appear."
        " A hollow dot is a lower bound (part of its spend went unrecorded); a"
        " dashed vertical rule is a change of the requested root model;"
        + defect_note
        + " Method and definitions: evals/README.md § Reading the figure; every"
        " score: evals/results/TREND.md.",
        "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;fontSize=10;fontStyle=2;fontColor=#9AA5B1;",
        Box(100, 940, 700, 60),
    )


def render_figure(data: TrendData, stamp_date: datetime.date) -> str:
    """Render the five-panel mxGraphModel the update-diagrams skill specifies."""
    have_success = any(c.success_cost is not None for c in data.cells.values())
    if not data.versions or not have_success:
        raise ValueError("render_figure: no clearing rep on record — nothing to draw")
    fig = _figure(data)
    out = _header(fig, stamp_date)
    out.extend(_frame(fig))
    out.extend(_captions(fig))
    out.extend(
        _task_panel(
            fig,
            _TaskPanel(
                fig.cost_series, fig.cost, "trend_", "d_", "line_", hollow_bounds=True
            ),
        )
    )
    out.extend(_reliability_panel(fig))
    out.extend(_quality_panel(fig))
    out.extend(
        _task_panel(
            fig, _TaskPanel(fig.wall_series, fig.wall, "wtrend_", "wd_", "wline_")
        )
    )
    out.extend(
        _task_panel(
            fig, _TaskPanel(fig.burn_series, fig.burn, "btrend_", "bd_", "bline_")
        )
    )
    for group in _label_groups(fig):
        out.extend(_end_labels(fig, group))
    out.extend(_version_labels(fig))
    out.append(_caption(fig))
    out += ["  </root>", "</mxGraphModel>"]
    return "\n".join(out) + "\n"


def _export_png(source: Path, png: Path) -> int:
    """Export the PNG through the draw.io CLI when it is installed, else print the command."""
    command = [
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
        str(source),
    ]
    if not DRAWIO_CLI.is_file():
        print("draw.io CLI not found — export manually:\n  " + " ".join(command))
        return 0
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        tail = (err.stderr or "").strip().splitlines()[-3:]
        print("render_figure: draw.io export failed:", file=sys.stderr)
        for line in tail:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(
        f"png exported: {png} — review it against the update-diagrams checklist, then commit both files"
    )
    return 0


def main(argv: list[str]) -> int:
    """Render the figure source, then export its PNG."""
    parser = argparse.ArgumentParser(prog="evals/render_figure.py", allow_abbrev=False)
    parser.add_argument("--out", type=Path, default=FIGURE)
    args = parser.parse_args(argv[1:])
    out: Path = args.out
    try:
        payload = json.loads(TREND_DATA.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"render_figure: {TREND_DATA}: {exc}", file=sys.stderr)
        return 1
    try:
        data = from_payload(payload)
        text = render_figure(data, datetime.datetime.now().astimezone().date())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    out.write_text(text, encoding="utf-8")
    print(f"figure source written: {out}")
    png = out.with_suffix(".drawio.png") if out == FIGURE else out.with_suffix(".png")
    return _export_png(out, png)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
