#!/usr/bin/env python3
"""Refresh every trend surface in one command.

Usage: evals/refresh_trend.py

Runs the two steps of the terminal loop in order: summarize (the derived
views — pages and trend-data.json) and render_figure (the figure source
plus the PNG export). One deliberate invocation replaces the two-command
ceremony; the design line holds because the human still chooses when the
figure regenerates, and the review step stays human — check the exported
PNG against the update-diagrams checklist before committing. A failing
step stops the chain with its exit code. Stdlib only.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_figure  # noqa: E402
import summarize  # noqa: E402

Step = Callable[[], int]


def default_steps() -> tuple[Step, ...]:
    return (
        lambda: summarize.main([]),
        lambda: render_figure.main(["render_figure.py"]),
    )


def main(steps: Sequence[Step] | None = None) -> int:
    for step in default_steps() if steps is None else steps:
        rc = step()
        if rc != 0:
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
