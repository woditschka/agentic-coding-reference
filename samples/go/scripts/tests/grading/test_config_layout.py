"""The project's layout.toml through the loader, and the stack defaults the Go slice ships; the project half skips on a pre-init tree."""

import unittest
from pathlib import Path

from grading import config

# The scripts dir (tests/grading/ lives two levels under it).
_SCRIPTS = Path(__file__).resolve().parent.parent.parent
_LAYOUT = _SCRIPTS / "layout.toml"


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class ProjectLayout(unittest.TestCase):
    """What holds for every project's layout; its globs and roots are the project's own and never asserted here."""

    @classmethod
    def setUpClass(cls):
        cls.layout = config.load_layout(_SCRIPTS)

    def test_the_layout_loads_and_its_review_table_validates(self):
        self.assertIsInstance(self.layout.review_config(), config.ReviewConfig)

    def test_the_conventions_table_validates(self):
        self.assertIsInstance(self.layout.conventions_config(), config.Conventions)


class StackDefaults(unittest.TestCase):
    """The harness-owned layout-defaults.toml beside the layout, read without the project's overrides."""

    @classmethod
    def setUpClass(cls):
        defaults = config.load_stack_defaults(_SCRIPTS)
        cls.layout = config.Layout(
            test_globs=(),
            prod_roots=(),
            sensitive=(),
            module_rules=(),
            extra_reviewers=(),
            review=defaults.get("review", {}),
            conventions=defaults.get("conventions", {}),
        )

    def test_the_security_surface_probe_names_the_http_handlers(self):
        probe = self.layout.review_config().security_surface

        self.assertTrue(any("HandleFunc" in p for p in probe))

    def test_the_construction_pattern_ships_with_the_stack(self):
        construction = self.layout.conventions_config().construction

        self.assertIsNotNone(construction)
        self.assertIn("{", construction.pattern)


if __name__ == "__main__":
    unittest.main(verbosity=2)
