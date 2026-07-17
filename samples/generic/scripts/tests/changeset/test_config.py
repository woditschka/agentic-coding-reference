"""Tests for changeset.config — the change-set exclude-filter ACL.

TestExcludeConfig reads this project's own scripts/layout.toml, so it skips on a
pre-init tree (marketplace setup.sh runs before the scaffold); every scaffolded
project runs it in full. TestExcludeInjection injects a synthetic filter and
runs everywhere.

Run (from the scripts dir): python3 -m unittest tests.changeset.test_config
Stdlib only.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

from changeset import config

# The scripts dir (tests/changeset/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class TestExcludeConfig(unittest.TestCase):
    """The loader surfaces exclude_globs as a list so the pathspec builder never
    crashes — whether or not the project declared any."""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so this test reads
        # a populated `layout` regardless of test ordering or isolation.
        config.get_layout()

    def test_exclude_is_a_list(self):
        self.assertIsInstance(config.layout.EXCLUDE, list)


class TestExcludeInjection(unittest.TestCase):
    """get_layout caches lazily and a test may pre-set the module global, so the
    change-set layer imports without a sibling layout.toml."""

    def setUp(self):
        self._saved = config.layout
        self.addCleanup(lambda: setattr(config, "layout", self._saved))

    def test_injected_layout_is_returned(self):
        config.layout = SimpleNamespace(EXCLUDE=["vendor/**"])
        self.assertEqual(config.get_layout().EXCLUDE, ["vendor/**"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
