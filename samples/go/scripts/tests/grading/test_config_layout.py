"""The loaded layout of this stack's real layout.toml (Go); skips on a pre-init tree."""

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

    def test_the_three_go_trees_are_production_roots(self):
        for root in ("internal/", "cmd/", "pkg/"):
            with self.subTest(root=root):
                self.assertIn(root, self.layout.prod_roots)

    def test_test_files_match_at_any_depth(self):
        self.assertIn("**/*_test.go", self.layout.test_globs)
        self.assertIn("*_test.go", self.layout.test_globs)

    def test_the_internal_tree_derives_modules_by_directory(self):
        self.assertIn(config.ModuleRule("internal/**", "dir"), self.layout.module_rules)

    def test_auth_packages_are_sensitive(self):
        self.assertTrue(any("auth" in g for g in self.layout.sensitive))

    def test_the_security_surface_probe_ships_with_the_stack(self):
        probe = self.layout.review_config().security_surface

        self.assertTrue(any("HandleFunc" in p for p in probe))

    def test_the_construction_pattern_ships_with_the_stack(self):
        self.assertIsNotNone(self.layout.conventions_config().construction)


if __name__ == "__main__":
    unittest.main(verbosity=2)
