#!/usr/bin/env python3
"""Refresh every trend surface in one command: the derived views, then the figure."""

import sys
from collections.abc import Callable, Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render_figure  # noqa: E402
import summarize  # noqa: E402

Step = Callable[[], int]


def default_steps() -> tuple[Step, ...]:
    """Return the two steps in order: summarize, then render the figure."""
    return (
        lambda: summarize.main([]),
        lambda: render_figure.main(["render_figure.py"]),
    )


def main(steps: Sequence[Step] | None = None) -> int:
    """Run the steps in order, stopping at the first failing one with its exit code."""
    # The human still chooses when the figure regenerates and reviews the
    # exported PNG before committing.
    for step in default_steps() if steps is None else steps:
        code = step()
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
