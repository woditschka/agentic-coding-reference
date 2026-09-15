"""The change-set launcher run as a consumer runs it, beside a copy of the shipped scripts."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent

THE_LAYOUT_FAULT = (
    "layout.toml: exclude_globs must be a list of non-empty glob strings (got 'x')"
)


class BrokenExcludeFilterFailsLoud(unittest.TestCase):
    """An install whose exclude filter is not a list, with a committed head and no base."""

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree)
        scripts = self.tree / "scripts"
        shutil.copytree(
            _HERE,
            scripts,
            ignore=shutil.ignore_patterns("tests", "__pycache__", "layout*.toml"),
        )
        (scripts / "layout.toml").write_text('exclude_globs = "x"\n', encoding="utf-8")
        self.entry = scripts / "changeset.py"

    def test_the_install_fault_wins_and_no_diff_is_emitted(self):
        done = subprocess.run(
            [sys.executable, "-B", str(self.entry), "--head", "HEAD"],
            cwd=self.tree,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr.splitlines(), [f"changeset: {THE_LAYOUT_FAULT}"])
        self.assertEqual(done.stdout, "")


if __name__ == "__main__":
    unittest.main()
