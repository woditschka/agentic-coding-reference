#!/usr/bin/env python3
"""Tests for claude_dev_scrub — the container-private ~/.claude.json replica.

The scrub is the mount boundary's one transformation, so the suite pins its
two load-bearing properties: only cwd-overlapping ``projects`` entries cross,
and every input defect degrades to ``{}`` (state loss, never exposure).
"""

import json
import pathlib
import tempfile
import unittest

import claude_dev_scrub as s

CWD = "/home/u/work/proj"


class Overlaps(unittest.TestCase):
    def test_equal_ancestor_descendant(self):
        self.assertTrue(s.overlaps(CWD, CWD))
        self.assertTrue(s.overlaps("/home/u", CWD))
        self.assertTrue(s.overlaps(CWD + "/sub", CWD))

    def test_sibling_and_prefix_confusion(self):
        self.assertFalse(s.overlaps("/home/u/work/other", CWD))
        # A path-string prefix that is not a path ancestor must not overlap.
        self.assertFalse(s.overlaps("/home/u/work/proj2", CWD))


class ScrubReplica(unittest.TestCase):
    def test_keeps_cwd_ancestors_and_subtrees_only(self):
        data = {
            "theme": "dark",
            "projects": {
                "/home/u": {"trust": True},
                CWD: {"mcpServers": {"ide": {}}},
                CWD + "/worktree": {},
                "/home/u/work/other": {"secret": "sibling"},
            },
        }
        out = s.scrub_replica(data, CWD)
        self.assertEqual(set(out["projects"]), {"/home/u", CWD, CWD + "/worktree"})
        self.assertEqual(out["theme"], "dark")

    def test_non_dict_projects_passes_through(self):
        data = {"projects": "corrupt", "theme": "dark"}
        self.assertEqual(s.scrub_replica(data, CWD), data)


class ReplicaText(unittest.TestCase):
    def _write(self, text):
        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / "claude.json"
        p.write_text(text, encoding="utf-8")
        return p

    def test_scrubs_and_compacts(self):
        src = self._write(json.dumps({"projects": {CWD: {}, "/elsewhere": {}}, "a": 1}))
        out = json.loads(s.replica_text(src, CWD))
        self.assertEqual(out, {"projects": {CWD: {}}, "a": 1})

    def test_projects_free_file_is_byte_identical(self):
        text = json.dumps({"a": 1, "b": [1, 2]}, separators=(",", ":"))
        self.assertEqual(s.replica_text(self._write(text), CWD), text)

    def test_absent_unparseable_and_non_object_degrade_to_empty(self):
        missing = pathlib.Path(tempfile.mkdtemp()) / "absent.json"
        for src in (missing, self._write("not json"), self._write("[1,2]")):
            self.assertEqual(s.replica_text(src, CWD), "{}")


if __name__ == "__main__":
    unittest.main()
