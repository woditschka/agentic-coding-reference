#!/usr/bin/env python3
"""Pin the write guard: fail-closed scope, resolved-path containment, atomic replace."""

import tempfile
import unittest
from pathlib import Path

from _loader import load

wg = load("write_guard", "write_guard.py")

ANY_TEXT = "x"
EXECUTABLE_MODE = 0o755


class WriteScope(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)
        self.inside = self.base / "in"
        self.outside = self.base / "out"
        self.inside.mkdir()
        self.outside.mkdir()

    def test_no_open_scope_rejects_every_write(self):
        with self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(self.inside / "f.txt", ANY_TEXT)

    def test_a_write_inside_the_scope_lands(self):
        with wg.write_scope(self.inside):
            wg.write_text(self.inside / "f.txt", ANY_TEXT)
        self.assertEqual((self.inside / "f.txt").read_text(), ANY_TEXT)

    def test_every_verb_rejects_an_out_of_scope_target(self):
        victim = self.outside / "v.txt"
        victim.write_text("keep")
        with wg.write_scope(self.inside):
            for verb in (
                lambda: wg.mkdir(self.outside / "d"),
                lambda: wg.copy(victim, self.outside / "c.txt"),
                lambda: wg.write_text(victim, "clobber"),
                lambda: wg.remove_tree(self.outside),
                lambda: wg.unlink(victim),
            ):
                with self.assertRaises(wg.WriteOutsideScopeError):
                    verb()
        self.assertEqual(victim.read_text(), "keep")

    def test_a_sibling_sharing_the_scope_prefix_is_outside(self):
        sibling = self.base / "in-sibling"
        sibling.mkdir()
        with wg.write_scope(self.inside), self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(sibling / "f.txt", ANY_TEXT)

    def test_a_symlink_pointing_outside_the_scope_is_rejected(self):
        link = self.inside / "link"
        link.symlink_to(self.outside)
        with wg.write_scope(self.inside), self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(link / "f.txt", ANY_TEXT)

    def test_an_inner_scope_replaces_the_outer_and_restores_it_on_exit(self):
        sub = self.inside / "sub"
        sub.mkdir()
        with wg.write_scope(self.inside):
            with wg.write_scope(sub):
                with self.assertRaises(wg.WriteOutsideScopeError):
                    wg.write_text(self.inside / "top.txt", ANY_TEXT)
                wg.write_text(sub / "deep.txt", ANY_TEXT)
            wg.write_text(self.inside / "top.txt", ANY_TEXT)

    def test_the_scope_closes_after_a_raise_inside_the_block(self):
        with self.assertRaises(RuntimeError), wg.write_scope(self.inside):
            raise RuntimeError("boom")
        with self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(self.inside / "f.txt", ANY_TEXT)

    def test_write_text_replaces_existing_content(self):
        target = self.inside / "f.txt"
        target.write_text("old")
        with wg.write_scope(self.inside):
            wg.write_text(target, "new")
        self.assertEqual(target.read_text(), "new")

    def test_write_text_preserves_the_target_mode(self):
        # The temp is staged under umask defaults; the mode is copied before replace.
        target = self.inside / "stack.sh"
        target.write_text("#!/bin/sh\n")
        target.chmod(EXECUTABLE_MODE)
        with wg.write_scope(self.inside):
            wg.write_text(target, "#!/bin/sh\necho filled\n")
        self.assertEqual(target.stat().st_mode & 0o777, EXECUTABLE_MODE)

    def test_unlink_removes_the_link_and_keeps_its_target(self):
        target = self.outside / "kept.txt"
        target.write_text("keep")
        link = self.inside / "link.txt"
        link.symlink_to(target)
        with wg.write_scope(self.inside):
            wg.unlink(link)
        self.assertFalse(link.is_symlink())
        self.assertEqual(target.read_text(), "keep")

    def test_a_failed_write_text_leaves_no_temp_file(self):
        with wg.write_scope(self.inside), self.assertRaises(OSError):
            wg.write_text(self.inside / "nodir" / "f.txt", ANY_TEXT)
        self.assertEqual(list(self.inside.rglob("*.tmp")), [])

    def test_remove_tree_inside_the_scope_deletes_the_tree(self):
        doomed = self.inside / "doomed"
        doomed.mkdir()
        (doomed / "f.txt").write_text(ANY_TEXT)
        with wg.write_scope(self.inside):
            wg.remove_tree(doomed)
        self.assertFalse(doomed.exists())

    def test_every_root_of_a_multi_root_scope_is_writable(self):
        with wg.write_scope(self.inside, self.outside):
            wg.write_text(self.inside / "a.txt", ANY_TEXT)
            wg.write_text(self.outside / "b.txt", ANY_TEXT)
        self.assertTrue((self.outside / "b.txt").is_file())


if __name__ == "__main__":
    unittest.main()
