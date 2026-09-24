"""Render the deck's slide figures as draw.io sources: the memory figure and the agent-team figure."""

import html
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import NamedTuple

# The deck's paper look, as deck.css defines it, with the rule one step darker
# so a box edge survives projection. Color is semantic: the accent marks the
# control elements on a slide, every memory element is grey.
INK = "#16161d"
INK_SOFT = "#3a3a45"
MUTED = "#6c6f85"
RULE = "#c9c7bf"
RULE_SOFT = "#b5b3ab"
PAPER = "#f6f5f1"
SUNKEN = "#ecebe6"
WHITE = "#FFFFFF"
ACCENT = "#1f7a3a"
LINE = "#8f8e87"
MONO = "Courier New"
SANS = "Helvetica"

# The border the draw.io export adds around a figure's drawn extent.
EXPORT_BORDER = 12

Style = dict[str, str | int | float | None]


class Box(NamedTuple):
    """A vertex's position and size on the canvas."""

    x: int
    y: int
    w: int
    h: int


class Point(NamedTuple):
    """A canvas position."""

    x: int
    y: int


class Size(NamedTuple):
    """A canvas size."""

    w: int
    h: int


class Route(NamedTuple):
    """An edge's waypoints, label, and label offset."""

    points: tuple[Point, ...] = ()
    label: str = ""
    label_offset: Point | None = None


STRAIGHT = Route()


class Loop(NamedTuple):
    """A nested loop band: its id, the name at its corner, its box, and its tint."""

    key: str
    name: str
    box: Box
    fill: str
    stroke: str


# Outermost first. The bands step 34 apart vertically; horizontally each hugs
# the cards it holds, so the request pill sits outside every loop and the
# merge pill inside the outermost one. The tints run lightest outward, so the
# innermost loop reads as the most concrete.
LOOPS = (
    Loop("arch", "codebase", Box(130, 108, 1134, 372), "#f2f7f3", "#cfe0d4"),
    Loop("outer", "slice", Box(142, 142, 996, 304), "#e8f2ea", "#b4d3bd"),
    Loop("middle", "review", Box(344, 176, 592, 236), "#dcece0", "#98c4a5"),
    Loop("inner", "TDD", Box(546, 210, 188, 168), "#cfe5d5", "#7ab48b"),
)
# The middle loop's tint fills the return labels' knockout and the router.
# The memory figure's agent-team box wears it too, so that box reads as the
# loops it opens into on the next slide.
MIDDLE_LOOP = next(loop for loop in LOOPS if loop.key == "middle")
LOOP_FILL, LOOP_STROKE = MIDDLE_LOOP.fill, MIDDLE_LOOP.stroke


# The sizes both figures share, so the slides read as one series when each
# image renders at the same scale.
BOX_HEIGHT = 80
NAME_SIZE = 19
TITLE_SIZE = 16
ARROW_LABEL_SIZE = 17

PAPER_BOX: Style = {
    "rounded": 1,
    "arcSize": 6,
    "html": 1,
    "fillColor": PAPER,
    "strokeColor": RULE,
    "strokeWidth": 1.6,
}
SUNKEN_BOX: Style = {**PAPER_BOX, "fillColor": SUNKEN, "strokeColor": RULE_SOFT}
DASHED: Style = {"dashed": 1, "dashPattern": "10 6"}
# A dash says transient: the loop bands and the short-term memory carry it,
# the long-term memory never does.
LOOP_BAND: Style = {**PAPER_BOX, **DASHED}
LONG_TERM_BAND: Style = PAPER_BOX
SHORT_TERM_BAND: Style = {**SUNKEN_BOX, **DASHED}
CARD: Style = {
    "rounded": 1,
    "arcSize": 12,
    "whiteSpace": "wrap",
    "html": 1,
    "fillColor": WHITE,
    "strokeColor": RULE,
    "strokeWidth": 1.6,
    "fontSize": NAME_SIZE,
    "fontStyle": 1,
    "fontFamily": MONO,
    "fontColor": INK,
    "verticalAlign": "middle",
    "spacingLeft": 4,
    "spacingRight": 4,
}
PILL: Style = {
    **CARD,
    "arcSize": 50,
    "fillColor": SUNKEN,
    "strokeColor": RULE_SOFT,
    "fontStyle": 0,
    "fontFamily": SANS,
    "fontSize": 17,
}
FILE: Style = {
    "rounded": 1,
    "arcSize": 30,
    "whiteSpace": "wrap",
    "html": 1,
    "fillColor": WHITE,
    "strokeColor": RULE,
    "strokeWidth": 1.3,
    "fontColor": INK_SOFT,
    "fontSize": 16,
    "fontFamily": MONO,
}
TEXT: Style = {
    "text": None,
    "html": 1,
    "verticalAlign": "middle",
    "strokeColor": "none",
}
BAND_TITLE: Style = {
    **TEXT,
    "align": "center",
    "fontSize": TITLE_SIZE,
    "fontStyle": 1,
    "fontColor": MUTED,
    "letterSpacing": 1.5,
    "fillColor": "none",
}
FOLDER_NAME: Style = {
    **TEXT,
    "align": "left",
    "fontSize": 15,
    "fontColor": MUTED,
    "fontFamily": MONO,
    "spacingLeft": 10,
}
ARROW_LABEL: Style = {
    **TEXT,
    "align": "center",
    "fontSize": ARROW_LABEL_SIZE,
    "fontStyle": 1,
    "fontColor": ACCENT,
}
FORWARD: Style = {
    "edgeStyle": "orthogonalEdgeStyle",
    "rounded": 0,
    "html": 1,
    "endArrow": "block",
    "endSize": 8,
    "strokeColor": LINE,
    "strokeWidth": 2.2,
}
RETURN: Style = {
    **FORWARD,
    "strokeColor": ACCENT,
    "strokeWidth": 2,
    "dashed": 1,
    "dashPattern": "4 4",
}
MEMORY_LINK: Style = {
    "edgeStyle": "none",
    "rounded": 0,
    "html": 1,
    "endArrow": "block",
    "startArrow": "block",
    "endFill": 1,
    "startFill": 1,
    "endSize": 8,
    "startSize": 8,
    "strokeColor": LINE,
    "strokeWidth": 2,
}
CONVERSATION: Style = {
    **MEMORY_LINK,
    "endSize": 9,
    "startSize": 9,
    "strokeColor": ACCENT,
    "strokeWidth": 2.4,
    "fontSize": ARROW_LABEL_SIZE,
    "fontStyle": 1,
    "fontColor": ACCENT,
    "verticalAlign": "bottom",
}


def _style(props: Style, **overrides: str | int | float | None) -> str:
    """Serialize a style table, a bare key for a flag such as `text`."""
    merged = {**props, **overrides}
    return "".join(
        f"{key};" if value is None else f"{key}={value};"
        for key, value in merged.items()
    )


def _label(text: str) -> str:
    """Escape a label for an attribute; `html=1` styles render `<br>` as a break."""
    return html.escape(text, quote=True)


def _anchors(exit_at: tuple[float, float], entry_at: tuple[float, float]) -> str:
    """Pin an edge's ends to fractions of its source and target boxes."""
    return (
        f"exitX={exit_at[0]};exitY={exit_at[1]};"
        f"entryX={entry_at[0]};entryY={entry_at[1]};"
    )


def _x_at(box: Box, fraction: float) -> int:
    """Return the canvas x at a fraction of a box's width."""
    return box.x + round(box.w * fraction)


def _fraction_across(box: Box, x: int) -> float:
    """Express a canvas x as a fraction of a box's width, for an edge anchor."""
    return round((x - box.x) / box.w, 4)


def _vertex(cell_id: str, value: str, style: str, box: Box) -> str:
    """Emit one vertex cell."""
    return (
        f'    <mxCell id="{cell_id}" value="{_label(value)}" style="{style}"'
        ' vertex="1" parent="1">\n'
        f'      <mxGeometry x="{box.x}" y="{box.y}" width="{box.w}"'
        f' height="{box.h}" as="geometry"/>\n'
        "    </mxCell>\n"
    )


def _edge(
    cell_id: str, style: str, ends: tuple[str, str], route: Route = STRAIGHT
) -> str:
    """Emit one edge cell; every edge carries a relative geometry."""
    points = "".join(
        f'          <mxPoint x="{p.x}" y="{p.y}"/>\n' for p in route.points
    )
    array = f'        <Array as="points">\n{points}        </Array>\n'
    offset = (
        f'        <mxPoint x="{route.label_offset.x}" y="{route.label_offset.y}"'
        ' as="offset"/>\n'
        if route.label_offset
        else ""
    )
    return (
        f'    <mxCell id="{cell_id}" value="{_label(route.label)}" style="{style}"'
        f' edge="1" parent="1" source="{ends[0]}" target="{ends[1]}">\n'
        '      <mxGeometry relative="1" as="geometry">\n'
        f"{array if route.points else ''}{offset}"
        "      </mxGeometry>\n"
        "    </mxCell>\n"
    )


def _document(size: Size, cells: Iterable[str]) -> str:
    """Wrap cells in a page-sized mxGraphModel."""
    head = (
        f'<mxGraphModel dx="{size.w}" dy="{size.h}" grid="0" gridSize="10"'
        ' guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1"'
        f' pageScale="1" pageWidth="{size.w}" pageHeight="{size.h}" math="0"'
        ' shadow="0" adaptiveColors="auto">\n'
        "  <root>\n"
        '    <mxCell id="0"/>\n'
        '    <mxCell id="1" parent="0"/>\n'
    )
    return head + "".join(cells) + "  </root>\n</mxGraphModel>\n"


def _band_title(cell_id: str, text: str, band: Box) -> str:
    """Title a band, centered, in the strip under its top edge."""
    return _vertex(
        cell_id, text, _style(BAND_TITLE), Box(band.x, band.y + 9, band.w, 22)
    )


# --- the memory figure -------------------------------------------------------
#
# Human and agent-team side by side, joined by the conversation. Long-term
# memory, the repository, spans under both; short-term memory, the handoff
# log, sits under the agent-team alone. A folder is a box in the tone that
# contrasts its band, named in mono; a file is a white chip; the code box is
# distinct by its border only.

MEMORY_SIZE = Size(1010, 490)
HUMAN = Box(250, 40, 180, BOX_HEIGHT)
AGENT_TEAM = Box(600, 40, 220, BOX_HEIGHT)
LONG_TERM = Box(40, 180, 660, 280)
DOCS = Box(56, 222, 260, 224)
CODE = Box(340, 222, 344, 224)
SHORT_TERM = Box(730, 180, 240, 280)
SCRATCH = Box(746, 222, 208, 224)
SPEC_FILES = ("prd.md", "system-design.md", "ubiquitous-language.md", "adr/")
FILE_PITCH = 46
# Where each memory link leaves its box, as a fraction of the box's width.
HUMAN_DROP = 0.5
TEAM_DROP_LEFT = 0.2
TEAM_DROP_RIGHT = 0.8


def _memory_row() -> list[str]:
    """Draw the human, the agent-team, and the conversation between them."""
    return [
        _vertex("person", "Human", _style(PILL, fontSize=NAME_SIZE), HUMAN),
        _vertex(
            "fi",
            "agent-team",
            _style(CARD, fillColor=LOOP_FILL, strokeColor=LOOP_STROKE),
            AGENT_TEAM,
        ),
        _edge(
            "talk",
            _style(CONVERSATION) + _anchors((1, 0.5), (0, 0.5)),
            ("person", "fi"),
            Route(label="conversation", label_offset=Point(0, -6)),
        ),
    ]


def _folder(cell_id: str, name: str, style: str, box: Box) -> list[str]:
    """Draw a folder box with its name in the top-left corner."""
    return [
        _vertex(cell_id, "", style, box),
        _vertex(
            f"{cell_id}_name",
            name,
            _style(FOLDER_NAME),
            Box(box.x, box.y + 4, 140, 24),
        ),
    ]


def _file(cell_id: str, name: str, folder: Box, slot: int) -> str:
    """Draw a file chip in a folder's numbered slot below its name."""
    return _vertex(
        cell_id,
        name,
        _style(FILE),
        Box(folder.x + 12, folder.y + 32 + slot * FILE_PITCH, folder.w - 24, 38),
    )


def _memory_long_term() -> list[str]:
    """Draw the repository band: the docs folder with its files, and the code box."""
    folder = _style(SUNKEN_BOX, arcSize=8, strokeColor=RULE, strokeWidth=1.3)
    code = _style(FILE, arcSize=8, strokeColor=MUTED, strokeWidth=1.6, fontSize=18)
    return [
        _vertex("band_ltm", "", _style(LONG_TERM_BAND), LONG_TERM),
        *_folder("fold_docs", "docs/", folder, DOCS),
        *(
            _file(f"doc{slot}", name, DOCS, slot)
            for slot, name in enumerate(SPEC_FILES)
        ),
        _vertex("doc4", "code · tests", code, CODE),
    ]


def _memory_short_term() -> list[str]:
    """Draw the handoff band: the scratch folder holding its one file."""
    folder = _style(PAPER_BOX, arcSize=8, strokeWidth=1.3)
    return [
        _vertex("band_stm", "", _style(SHORT_TERM_BAND), SHORT_TERM),
        *_folder("fold_scratch", ".scratch/", folder, SCRATCH),
        _file("rec0", "handoff.jsonl", SCRATCH, 0),
    ]


class MemoryLink(NamedTuple):
    """A drop from a box on the row into a memory band, at a fraction of the box."""

    cell_id: str
    source: str
    box: Box
    leave: float
    target: str
    band: Box


MEMORY_LINKS = (
    MemoryLink("mem_person", "person", HUMAN, HUMAN_DROP, "band_ltm", LONG_TERM),
    MemoryLink("mem_up", "fi", AGENT_TEAM, TEAM_DROP_LEFT, "band_ltm", LONG_TERM),
    MemoryLink("mem_down", "fi", AGENT_TEAM, TEAM_DROP_RIGHT, "band_stm", SHORT_TERM),
)


def _memory_links() -> list[str]:
    """Link the human to long-term memory and the agent-team to both memories."""
    link = _style(MEMORY_LINK)
    return [
        _edge(
            drop.cell_id,
            link
            + _anchors(
                (drop.leave, 1),
                (_fraction_across(drop.band, _x_at(drop.box, drop.leave)), 0),
            ),
            (drop.source, drop.target),
        )
        for drop in MEMORY_LINKS
    ]


def _memory_titles() -> list[str]:
    """Draw the band titles last, so they sit above every line."""
    return [
        _band_title("lab_ltm", "LONG-TERM MEMORY · the repository", LONG_TERM),
        _band_title("lab_stm", "SHORT-TERM MEMORY", SHORT_TERM),
    ]


def memory_figure() -> str:
    """Render the memory figure: one shared long-term memory, one private log."""
    cells = [
        *_memory_row(),
        *_memory_long_term(),
        *_memory_short_term(),
        *_memory_links(),
        *_memory_titles(),
    ]
    return _document(MEMORY_SIZE, cells)


# --- the agent-team figure ----------------------------------------------------
#
# The specialist flow left to right inside four nested loop bands, each named
# once at its corner. Only the two return arrows the audience needs are drawn:
# consultation and rework. The router is a slim accent layer between the flow
# and the log it reads. Both memories are one slim band each; the memory
# figure has already shown what is inside them.


class Specialist(NamedTuple):
    """A specialist card: its left edge and the name on it."""

    x: int
    name: str


TEAM_SIZE = Size(1280, 662)
CARD_Y = 254
CARD_W = 164
PILL_W = 92
SPECIALISTS = {
    "pre": Specialist(154, "product<br>requirements<br>expert"),
    "sde": Specialist(356, "system<br>design<br>expert"),
    "fi": Specialist(558, "feature<br>implementer"),
    "rev": Specialist(760, "reviewers"),
    "grad": Specialist(962, "change<br>grader"),
}
REQUEST = Box(24, CARD_Y + 4, PILL_W, BOX_HEIGHT - 8)
MERGE = Box(1164, CARD_Y + 4, PILL_W, BOX_HEIGHT - 8)
LONG_TERM_STRIP = Box(24, 24, 1232, 44)
ROUTER = Box(24, 520, 1232, 44)
SHORT_TERM_STRIP = Box(24, 594, 1232, 44)
LOOP_NAME: Style = {
    **ARROW_LABEL,
    "align": "right",
    "fontSize": 18,
    "spacingRight": 8,
}
# Return lanes: the consultation lanes run above the row, rework below.
LANE_TO_DESIGN = 232
LANE_TO_REQUIREMENTS = 194
LANE_REWORK = 356


def _card(key: str) -> Box:
    """Return a specialist's card box."""
    return Box(SPECIALISTS[key].x, CARD_Y, CARD_W, BOX_HEIGHT)


def _team_long_term_strip() -> list[str]:
    """Draw the long-term memory as one slim band above the loops."""
    return [_vertex("band_ltm", "", _style(LONG_TERM_BAND, arcSize=8), LONG_TERM_STRIP)]


def _team_router_and_log() -> list[str]:
    """Draw the accent router between the flow and the slim short-term band it reads."""
    router = _style(
        CARD,
        arcSize=24,
        fillColor=LOOP_FILL,
        strokeColor=ACCENT,
        strokeWidth=2,
        fontSize=22,
        fontFamily=SANS,
    )
    reads = _style(
        MEMORY_LINK,
        endArrow="classicThin",
        startArrow="classicThin",
        endSize=7,
        startSize=7,
        strokeWidth=1.8,
        dashed=1,
        dashPattern="5 5",
    )
    return [
        _vertex("router", "Router", router, ROUTER),
        _edge("reads", reads + _anchors((0.5, 1), (0.5, 0)), ("router", "band_stm")),
        _vertex("band_stm", "", _style(SHORT_TERM_BAND, arcSize=8), SHORT_TERM_STRIP),
    ]


def _team_loops() -> list[str]:
    """Draw the four nested loop bands, each named once at a corner."""
    cells = [
        _vertex(
            f"band_{loop.key}",
            "",
            _style(LOOP_BAND, fillColor=loop.fill, strokeColor=loop.stroke),
            loop.box,
        )
        for loop in LOOPS
    ]
    # The names follow every band, so no inner band paints over an outer name.
    for loop in LOOPS:
        box = loop.box
        if loop.key == "inner":
            # The innermost name sits bottom-left, clear of the consultation lanes.
            style = _style(LOOP_NAME, align="left", spacingLeft=8)
            place = Box(box.x + 2, box.y + box.h - 32, 100, 30)
        else:
            style = _style(LOOP_NAME)
            place = Box(box.x + box.w - 150, box.y + 2, 142, 30)
        cells.append(_vertex(f"m_{loop.key}", f"↺ {loop.name}", style, place))
    return cells


def _team_flow() -> list[str]:
    """Draw the request, the five specialists, and the merge, joined in order."""
    cells = [_vertex("user", "Feature request", _style(PILL), REQUEST)]
    cells.extend(
        _vertex(key, specialist.name, _style(CARD), _card(key))
        for key, specialist in SPECIALISTS.items()
    )
    cells.append(_vertex("human", "Human merges", _style(PILL), MERGE))
    chain = ["user", *SPECIALISTS, "human"]
    cells.extend(
        _edge(f"e{index}", _style(FORWARD), (chain[index], chain[index + 1]))
        for index in range(len(chain) - 1)
    )
    return cells


def _return(
    cell_id: str, ends: tuple[str, str], fractions: tuple[float, float], lane: int
) -> str:
    """Draw a return arrow out of one card at a fraction, along a lane, into another."""
    source, target = ends
    exit_fraction, entry_fraction = fractions
    side = 0 if lane < CARD_Y else 1
    return _edge(
        cell_id,
        _style(RETURN) + _anchors((exit_fraction, side), (entry_fraction, side)),
        ends,
        Route(
            (
                Point(_x_at(_card(source), exit_fraction), lane),
                Point(_x_at(_card(target), entry_fraction), lane),
            )
        ),
    )


def _team_returns() -> list[str]:
    """Draw the consultation lanes and the rework lane, each labeled in its gap."""
    design, reviewers = _card("sde"), _card("rev")
    return [
        _return("c_sde", ("fi", "sde"), (0.35, 0.65), LANE_TO_DESIGN),
        _return("c_pre", ("fi", "pre"), (0.65, 0.35), LANE_TO_REQUIREMENTS),
        _return("r_work", ("rev", "fi"), (0.5, 0.5), LANE_REWORK),
        _vertex(
            "l_cons",
            "consultation",
            _style(ARROW_LABEL, fillColor=LOOP_FILL),
            Box(design.x + 24, LANE_TO_REQUIREMENTS + 7, 116, 24),
        ),
        _vertex(
            "l_work",
            "rework",
            _style(ARROW_LABEL, fillColor=LOOP_FILL),
            Box(reviewers.x - 24, LANE_REWORK + 6, 96, 24),
        ),
    ]


def _team_titles() -> list[str]:
    """Draw the two memory titles in their strips."""
    return [
        _band_title("lab_ltm", "LONG-TERM MEMORY · the repository", LONG_TERM_STRIP),
        _band_title(
            "lab_stm", "SHORT-TERM MEMORY · .scratch/handoff.jsonl", SHORT_TERM_STRIP
        ),
    ]


def agent_team_figure() -> str:
    """Render the agent-team figure: specialists in nested loops over a routed log."""
    cells = [
        *_team_long_term_strip(),
        *_team_loops(),
        *_team_flow(),
        *_team_returns(),
        *_team_router_and_log(),
        *_team_titles(),
    ]
    return _document(TEAM_SIZE, cells)


FIGURES: dict[str, Callable[[], str]] = {
    "pipeline-slide-memory": memory_figure,
    "pipeline-slide-routing": agent_team_figure,
}


def derived_figures(images: Path) -> dict[Path, str]:
    """Map each figure's draw.io source under the images directory to its text."""
    return {images / f"{stem}.drawio": render() for stem, render in FIGURES.items()}
