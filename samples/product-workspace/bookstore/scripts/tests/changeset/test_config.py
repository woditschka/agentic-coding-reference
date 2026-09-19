"""The change set's exclude filter, read from a real layout file."""

import tempfile
import unittest
from pathlib import Path

from changeset.config import ChangeSetError, load_exclude_globs

SOME_GLOBS = ("vendor/**", "gen/*.generated")


def load_from_text(text):
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "layout.toml").write_text(text, encoding="utf-8")
        return load_exclude_globs(Path(tmp))


class ExcludeGlobs(unittest.TestCase):
    def test_an_absent_key_excludes_nothing(self):
        self.assertEqual(load_from_text("test = []\n"), ())

    def test_declared_globs_are_kept_in_order(self):
        self.assertEqual(
            load_from_text(f"exclude_globs = {list(SOME_GLOBS)!r}\n"), SOME_GLOBS
        )

    def test_a_non_list_value_is_rejected(self):
        with self.assertRaises(ChangeSetError):
            load_from_text('exclude_globs = "vendor/**"\n')

    def test_a_glob_with_a_control_byte_is_rejected_before_git_sees_it(self):
        with self.assertRaises(ChangeSetError):
            load_from_text('exclude_globs = ["a\\u0000b"]\n')

    def test_an_empty_glob_is_rejected_since_it_would_drop_every_path(self):
        with self.assertRaises(ChangeSetError):
            load_from_text('exclude_globs = [""]\n')

    def test_a_missing_layout_is_a_broken_install(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ChangeSetError):
            load_exclude_globs(Path(tmp))

    def test_an_unparsable_layout_is_a_broken_install(self):
        with self.assertRaises(ChangeSetError):
            load_from_text("exclude_globs = [\n")


if __name__ == "__main__":
    unittest.main()
