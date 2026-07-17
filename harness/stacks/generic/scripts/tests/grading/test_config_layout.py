"""Tests for grading.config against this stack's real layout.toml (generic).

TestLayoutConfig reads this project's own scripts/layout.toml, so it skips on
a pre-init tree (marketplace setup.sh runs before the scaffold). The generic
stack ships a placeholder layout.toml the project replaces, so it asserts only
that the loaded attributes are lists, never any particular globs, and stays
green after the project fills in its real layout. The stack-agnostic
module-rule and review-config validation lives in core
(tests/grading/test_config.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_config_layout
Stdlib only.
"""

import unittest
from pathlib import Path

from grading import config

# The scripts dir (tests/grading/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class TestLayoutConfig(unittest.TestCase):
    """The engine exposes the loaded layout as `layout` with four list-valued
    classification attributes, whatever values the project filled in. Value
    assertions stay out: the shipped layout.toml is a placeholder the project
    edits, and this suite must stay green after it does. (The exclude filter is
    a separate slice owned by the change-set ACL, changeset.config.)"""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so these tests
        # read a populated `layout` regardless of test ordering or isolation.
        config.get_layout()

    def test_four_attributes_are_lists(self):
        for attr in ("TEST", "PROD_ROOTS", "SENSITIVE", "MODULE"):
            self.assertIsInstance(getattr(config.layout, attr), list, attr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
