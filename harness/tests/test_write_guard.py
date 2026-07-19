#!/usr/bin/env python3
"""Tests for write_guard.py (stdlib only).

Run: python3 harness/tests/test_write_guard.py

Pins the runtime half of the confinement pairing (ADR 2026-07-19
network-write-confinement-gate): fail-closed with no scope open, resolved-path
containment (no sibling-prefix confusion, no symlink escape), inner scope
REPLACES outer (narrowing) with restore on exit — normal or raised — and the
atomic write_text (replace onto the target preserving its mode, temp cleaned
up on failure). Deletes act on the entry itself, never through a link. The
static half (battery steps 1h/1i) is pinned in test_confinement.py.
"""

import tempfile
import unittest
from pathlib import Path

from _loader import load

wg = load("write_guard", "write_guard.py")


class WriteGuardTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.base = Path(self.td.name)
        self.inside = self.base / "in"
        self.outside = self.base / "out"
        self.inside.mkdir()
        self.outside.mkdir()

    def tearDown(self):
        self.td.cleanup()

    def test_no_scope_fails_closed(self):
        # The default scope is empty: every verb raises until an entry point
        # declares its roots.
        with self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(self.inside / "f.txt", "x")

    def test_write_inside_scope_lands(self):
        with wg.write_scope(self.inside):
            wg.write_text(self.inside / "f.txt", "x")
        self.assertEqual((self.inside / "f.txt").read_text(), "x")

    def test_every_verb_is_guarded(self):
        # A delete is a write too: all five verbs reject an out-of-scope target.
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

    def test_sibling_prefix_is_not_confused(self):
        # Containment is path-component-based, not a string prefix: a scope on
        # …/in must not admit …/in-evil.
        evil = self.base / "in-evil"
        evil.mkdir()
        with wg.write_scope(self.inside), self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(evil / "f.txt", "x")

    def test_symlink_escape_is_rejected(self):
        # The guard confines the RESOLVED destination: a link inside the scope
        # pointing outside is an escape, not a sanctioned write.
        link = self.inside / "link"
        link.symlink_to(self.outside)
        with wg.write_scope(self.inside), self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(link / "f.txt", "x")

    def test_inner_scope_replaces_outer_and_restores(self):
        # Narrowing, not union: inside the inner scope the outer root is
        # rejected; on exit the outer scope is back.
        sub = self.inside / "sub"
        sub.mkdir()
        with wg.write_scope(self.inside):
            with wg.write_scope(sub):
                with self.assertRaises(wg.WriteOutsideScopeError):
                    wg.write_text(self.inside / "top.txt", "x")
                wg.write_text(sub / "deep.txt", "x")
            wg.write_text(self.inside / "top.txt", "x")

    def test_scope_restores_after_a_raise(self):
        # An exception inside the block must not leak the scope open.
        with self.assertRaises(RuntimeError), wg.write_scope(self.inside):
            raise RuntimeError("boom")
        with self.assertRaises(wg.WriteOutsideScopeError):
            wg.write_text(self.inside / "f.txt", "x")

    def test_write_text_replaces_existing_content(self):
        target = self.inside / "f.txt"
        target.write_text("old")
        with wg.write_scope(self.inside):
            wg.write_text(target, "new")
        self.assertEqual(target.read_text(), "new")

    def test_write_text_preserves_the_target_mode(self):
        # An executable skeleton filled in place must keep its +x — the temp
        # is staged with umask defaults, so the mode is copied before replace.
        target = self.inside / "stack.sh"
        target.write_text("#!/bin/sh\n")
        target.chmod(0o755)
        with wg.write_scope(self.inside):
            wg.write_text(target, "#!/bin/sh\necho filled\n")
        self.assertEqual(target.stat().st_mode & 0o777, 0o755)

    def test_unlink_removes_the_link_not_the_target(self):
        # Deletes act on the entry itself: pruning a symlink must never
        # dereference into (or past) the scope.
        target = self.outside / "kept.txt"
        target.write_text("keep")
        link = self.inside / "link.txt"
        link.symlink_to(target)
        with wg.write_scope(self.inside):
            wg.unlink(link)
        self.assertFalse(link.is_symlink())
        self.assertEqual(target.read_text(), "keep")

    def test_write_text_failure_leaves_no_temp(self):
        # Staging fails (parent missing) — the sibling temp must not survive.
        with wg.write_scope(self.inside), self.assertRaises(OSError):
            wg.write_text(self.inside / "nodir" / "f.txt", "x")
        self.assertEqual(list(self.inside.rglob("*.tmp")), [])

    def test_remove_tree_inside_scope(self):
        doomed = self.inside / "doomed"
        doomed.mkdir()
        (doomed / "f.txt").write_text("x")
        with wg.write_scope(self.inside):
            wg.remove_tree(doomed)
        self.assertFalse(doomed.exists())

    def test_multiple_roots_all_writable(self):
        with wg.write_scope(self.inside, self.outside):
            wg.write_text(self.inside / "a.txt", "x")
            wg.write_text(self.outside / "b.txt", "x")
        self.assertTrue((self.outside / "b.txt").is_file())


if __name__ == "__main__":
    unittest.main()
