#!/usr/bin/env python3
"""Tests for the slide figures: well-formed sources, the conventions the two figures share, and their place in the build."""

import pathlib
import re
import unittest
from xml.parsers import expat

import figures as f

DECK_CSS = pathlib.Path(__file__).resolve().parents[3] / "docs" / "deck" / "deck.css"
RETURN_ARROWS = {("fi", "sde"), ("fi", "pre"), ("rev", "fi")}
PALETTE_VARIABLES = {
    f.INK: "fg",
    f.INK_SOFT: "fg-soft",
    f.MUTED: "muted",
    f.PAPER: "bg",
    f.SUNKEN: "bg-sunken",
    f.WHITE: "bg-raised",
    f.ACCENT: "accent",
}


class Cell:
    """One mxCell as the parser saw it: its attributes, its geometry's, and its waypoints."""

    def __init__(self, attrs):
        self.attrs = attrs
        self.geometry = None
        self.points = []

    def get(self, name):
        return self.attrs.get(name, "")

    def style(self):
        return dict(
            part.split("=", 1) if "=" in part else (part, None)
            for part in self.get("style").split(";")
            if part
        )


def cells(text):
    """Parse a rendered figure into its cells by id; malformed XML raises."""
    drawn = {}
    current = []

    def start(name, attrs):
        if name == "mxCell":
            cell = Cell(attrs)
            drawn[attrs["id"]] = cell
            current.append(cell)
        elif name == "mxGeometry" and current:
            current[-1].geometry = attrs
        elif name == "mxPoint" and current and "as" not in attrs:
            current[-1].points.append((int(attrs["x"]), int(attrs["y"])))

    parser = expat.ParserCreate()
    parser.StartElementHandler = start
    parser.Parse(text, True)
    return drawn


def words_on(drawn):
    return {c.get("value") for c in drawn.values() if c.get("value")}


def exported_height(drawn):
    """The height the draw.io export gives a figure: its drawn extent plus the border."""
    tops = [
        float(c.geometry["y"])
        for c in drawn.values()
        if c.geometry and "y" in c.geometry
    ]
    bottoms = [
        float(c.geometry["y"]) + float(c.geometry["height"])
        for c in drawn.values()
        if c.geometry and "height" in c.geometry
    ]
    return max(bottoms) - min(tops) + 2 * f.EXPORT_BORDER


def css_cap(css, selector):
    return int(
        re.search(re.escape(selector) + r" \{[^}]*max-height: (\d+)px", css).group(1)
    )


def css_variable(css, name):
    return re.search(rf"--{name}: (#[0-9a-fA-F]{{6}});", css).group(1)


class FigureSource(unittest.TestCase):
    def test_every_figure_parses_as_xml_with_the_two_root_cells(self):
        for stem, render in f.FIGURES.items():
            with self.subTest(stem):
                self.assertLessEqual({"0", "1"}, set(cells(render())))

    def test_cell_ids_are_unique_within_a_figure(self):
        for stem, render in f.FIGURES.items():
            with self.subTest(stem):
                text = render()
                self.assertEqual(text.count("<mxCell "), len(cells(text)))

    def test_every_edge_joins_two_drawn_cells_and_carries_a_geometry(self):
        for stem, render in f.FIGURES.items():
            with self.subTest(stem):
                drawn = cells(render())
                edges = [c for c in drawn.values() if c.get("edge") == "1"]
                self.assertTrue(edges)
                for edge in edges:
                    self.assertIn(edge.get("source"), drawn)
                    self.assertIn(edge.get("target"), drawn)
                    self.assertIsNotNone(edge.geometry)

    def test_a_line_break_in_a_name_is_escaped_for_the_attribute(self):
        text = f.agent_team_figure()
        self.assertIn("product&lt;br&gt;requirements&lt;br&gt;expert", text)
        self.assertNotIn("<br>", text)


class SharedConventions(unittest.TestCase):
    def setUp(self):
        self.memory = cells(f.memory_figure())
        self.team = cells(f.agent_team_figure())

    def test_the_accent_marks_the_control_elements_and_memory_stays_grey(self):
        self.assertEqual(self.memory["talk"].style()["strokeColor"], f.ACCENT)
        for cell_id in ("mem_person", "mem_up", "mem_down"):
            self.assertEqual(self.memory[cell_id].style()["strokeColor"], f.LINE)
        for cell_id in ("c_sde", "c_pre", "r_work", "router"):
            self.assertEqual(self.team[cell_id].style()["strokeColor"], f.ACCENT)

    def test_the_agent_team_box_wears_the_loop_tint_of_the_next_slide(self):
        box, band = self.memory["fi"].style(), self.team["band_middle"].style()
        self.assertEqual(box["fillColor"], band["fillColor"])
        self.assertEqual(box["strokeColor"], band["strokeColor"])

    def test_the_long_term_band_is_solid_and_the_short_term_band_dashed(self):
        for drawn in (self.memory, self.team):
            self.assertNotIn("dashed", drawn["band_ltm"].style())
            self.assertEqual(drawn["band_stm"].style()["dashed"], "1")

    def test_every_box_renders_at_the_shared_height(self):
        boxes = [self.memory["person"], self.memory["fi"]]
        boxes.extend(self.team[key] for key in ("pre", "sde", "fi", "rev", "grad"))
        for box in boxes:
            self.assertEqual(box.geometry["height"], str(f.BOX_HEIGHT))

    def test_names_titles_and_arrow_labels_render_at_the_shared_sizes(self):
        for cell in (self.memory["fi"], self.team["fi"], self.team["pre"]):
            self.assertEqual(cell.style()["fontSize"], str(f.NAME_SIZE))
        titles = ("lab_ltm", "lab_stm")
        for drawn in (self.memory, self.team):
            for cell_id in titles:
                self.assertEqual(drawn[cell_id].style()["fontSize"], str(f.TITLE_SIZE))
        for cell in (self.memory["talk"], self.team["l_cons"], self.team["l_work"]):
            self.assertEqual(cell.style()["fontSize"], str(f.ARROW_LABEL_SIZE))

    def test_the_stylesheet_caps_both_images_at_one_scale(self):
        css = DECK_CSS.read_text(encoding="utf-8")
        team_scale = css_cap(css, ".figure img") / exported_height(self.team)
        memory_scale = css_cap(css, "#memory img") / exported_height(self.memory)
        self.assertAlmostEqual(team_scale, memory_scale, delta=0.01)

    def test_the_palette_mirrors_the_deck_stylesheet(self):
        css = DECK_CSS.read_text(encoding="utf-8")
        for color, variable in PALETTE_VARIABLES.items():
            with self.subTest(variable):
                self.assertEqual(color.lower(), css_variable(css, variable).lower())

    def test_the_memory_slide_carries_only_the_agreed_words(self):
        self.assertEqual(
            words_on(self.memory),
            {
                "Human",
                "agent-team",
                "conversation",
                "docs/",
                "prd.md",
                "system-design.md",
                "ubiquitous-language.md",
                "adr/",
                "code · tests",
                ".scratch/",
                "handoff.jsonl",
                "LONG-TERM MEMORY · the repository",
                "SHORT-TERM MEMORY",
            },
        )

    def test_the_agent_team_slide_carries_only_the_agreed_words(self):
        self.assertEqual(
            words_on(self.team),
            {
                "Feature request",
                "product<br>requirements<br>expert",
                "system<br>design<br>expert",
                "feature<br>implementer",
                "reviewers",
                "change<br>grader",
                "Human merges",
                "↺ codebase",
                "↺ slice",
                "↺ review",
                "↺ TDD",
                "consultation",
                "rework",
                "Router",
                "LONG-TERM MEMORY · the repository",
                "SHORT-TERM MEMORY · .scratch/handoff.jsonl",
            },
        )

    def test_the_human_reaches_only_long_term_memory_and_the_team_reaches_both(self):
        links = [c for c in self.memory.values() if c.get("id").startswith("mem_")]
        self.assertEqual(
            {c.get("target") for c in links if c.get("source") == "person"},
            {"band_ltm"},
        )
        self.assertEqual(
            {c.get("target") for c in links if c.get("source") == "fi"},
            {"band_ltm", "band_stm"},
        )

    def test_a_return_lane_leaves_its_card_at_the_anchor_and_runs_along_its_lane(self):
        lane, card = self.team["c_sde"], self.team["fi"].geometry
        exit_x = int(card["x"]) + round(
            int(card["width"]) * float(lane.style()["exitX"])
        )
        self.assertEqual(lane.points[0], (exit_x, f.LANE_TO_DESIGN))
        self.assertEqual(lane.points[1][1], f.LANE_TO_DESIGN)

    def test_only_the_consultation_and_rework_returns_are_drawn(self):
        returns = {
            (c.get("source"), c.get("target"))
            for c in self.team.values()
            if c.get("edge") == "1"
            and c.style().get("dashed") == "1"
            and c.style().get("strokeColor") == f.ACCENT
        }
        self.assertEqual(returns, RETURN_ARROWS)


class DerivedFigures(unittest.TestCase):
    def test_each_figure_lands_as_a_drawio_source_under_images(self):
        images = pathlib.Path("images")
        self.assertEqual(
            sorted(f.derived_figures(images)),
            [
                images / "pipeline-slide-memory.drawio",
                images / "pipeline-slide-routing.drawio",
            ],
        )


if __name__ == "__main__":
    unittest.main()
