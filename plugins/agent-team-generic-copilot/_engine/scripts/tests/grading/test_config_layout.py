"""The loaded placeholder layout.toml of the generic stack, asserting only what the loader decides; skips on a pre-init tree."""

import unittest
from pathlib import Path

from grading import config

# The scripts dir (tests/grading/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class ProjectLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = config.load_layout(_LAYOUT.parent)

    def test_the_placeholder_layout_loads_and_its_review_table_validates(self):
        self.assertIsInstance(self.layout.review_config(), config.ReviewConfig)

    def test_the_roster_starts_with_the_floor(self):
        self.assertEqual(self.layout.roster[: len(config.REVIEWERS)], config.REVIEWERS)

    def test_the_security_surface_probe_is_empty_until_the_project_declares_one(self):
        self.assertEqual(self.layout.review_config().security_surface, ())


if __name__ == "__main__":
    unittest.main(verbosity=2)
