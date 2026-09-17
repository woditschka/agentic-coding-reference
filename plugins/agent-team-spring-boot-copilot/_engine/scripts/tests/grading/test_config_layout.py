"""The loaded layout of this stack's real layout.toml (Java Spring Boot); skips on a pre-init tree."""

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

    def test_the_source_sets_are_production_roots(self):
        self.assertIn("src/main/java/", self.layout.prod_roots)
        self.assertIn("src/main/", self.layout.prod_roots)

    def test_every_test_naming_convention_is_a_test_glob(self):
        for glob in ("**/*Test.java", "**/*Tests.java", "**/*IT.java", "src/test/**"):
            with self.subTest(glob=glob):
                self.assertIn(glob, self.layout.test_globs)

    def test_the_main_tree_derives_modules_by_the_gradle_layout(self):
        self.assertIn(
            config.ModuleRule("src/main/java/**", "gradle"), self.layout.module_rules
        )

    def test_security_packages_are_sensitive(self):
        self.assertTrue(any("security" in g for g in self.layout.sensitive))

    def test_the_security_surface_probe_ships_with_the_stack(self):
        probe = self.layout.review_config().security_surface

        self.assertTrue(any("Mapping" in p for p in probe))

    def test_the_construction_pattern_ships_with_the_stack(self):
        construction = self.layout.conventions_config().construction

        self.assertIsNotNone(construction)
        self.assertIn("new", construction.pattern)


if __name__ == "__main__":
    unittest.main(verbosity=2)
