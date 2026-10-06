#!/usr/bin/env python3
"""Tests for claude_dev_scrub: only cwd-overlapping projects cross, every defect degrades to {}."""

import json
import pathlib
import tempfile
import unittest

import claude_dev_scrub as s

SOME_ANCESTOR = "/home/u"
SOME_CWD = SOME_ANCESTOR + "/work/proj"
SOME_SIBLING = SOME_ANCESTOR + "/work/other"
SOME_DESCENDANT = SOME_CWD + "/worktree"
# A path-string prefix of the cwd that is not one of its ancestors.
STRING_PREFIX_TWIN = SOME_CWD + "2"
SOME_SETTINGS = {"theme": "dark"}
SOME_PROJECT_STATE = {"trust": True}
SOME_IDE_ENDPOINT = {"type": "sse", "url": "http://127.0.0.1:64342/sse"}
# Written without whitespace: the replica of a projects-free file is its bytes.
SOME_COMPACT_JSON = '{"a":1,"b":[1,2]}'


class Overlaps(unittest.TestCase):
    def test_the_cwd_its_ancestor_and_its_descendant_overlap(self):
        self.assertTrue(s.overlaps(SOME_CWD, SOME_CWD))
        self.assertTrue(s.overlaps(SOME_ANCESTOR, SOME_CWD))
        self.assertTrue(s.overlaps(SOME_DESCENDANT, SOME_CWD))

    def test_a_sibling_and_a_string_prefix_twin_do_not_overlap(self):
        self.assertFalse(s.overlaps(SOME_SIBLING, SOME_CWD))
        self.assertFalse(s.overlaps(STRING_PREFIX_TWIN, SOME_CWD))


class ScrubReplica(unittest.TestCase):
    def test_only_cwd_ancestors_and_subtrees_cross_and_other_keys_pass_through(self):
        data = {
            **SOME_SETTINGS,
            "projects": {
                SOME_ANCESTOR: SOME_PROJECT_STATE,
                SOME_CWD: SOME_PROJECT_STATE,
                SOME_DESCENDANT: {},
                SOME_SIBLING: SOME_PROJECT_STATE,
            },
        }
        out = s.scrub_replica(data, SOME_CWD)
        self.assertEqual(
            set(out["projects"]), {SOME_ANCESTOR, SOME_CWD, SOME_DESCENDANT}
        )
        self.assertEqual({k: out[k] for k in SOME_SETTINGS}, SOME_SETTINGS)

    def test_a_session_on_a_peer_loses_every_credential_bearing_key(self):
        data = {
            **SOME_SETTINGS,
            "primaryApiKey": "a-stored-key",
            "mcpServers": {"x": {"headers": {"Authorization": "a-token"}}},
            "projects": {
                SOME_CWD: {**SOME_PROJECT_STATE, "mcpServers": {"y": {"env": {}}}},
                SOME_SIBLING: {"mcpServers": {"z": {}}},
            },
        }
        self.assertEqual(
            s.scrub_replica(data, SOME_CWD, open_weight=True),
            {**SOME_SETTINGS, "projects": {SOME_CWD: SOME_PROJECT_STATE}},
        )

    def test_a_bare_loopback_endpoint_reaches_a_session_on_a_peer(self):
        # The entry an IDE writes for its own MCP server: nothing in it can
        # hold a token, and --ide needs it inside the session.
        data = {"mcpServers": {"ide": SOME_IDE_ENDPOINT, "x": {"command": "x"}}}
        self.assertEqual(
            s.scrub_replica(data, SOME_CWD, open_weight=True),
            {"mcpServers": {"ide": SOME_IDE_ENDPOINT}},
        )

    def test_only_a_type_and_a_plain_loopback_url_count_as_bare(self):
        for server in (
            {"type": "sse", "url": "http://example.com:64342/sse"},
            {"type": "sse", "url": "https://127.0.0.1:64342/sse"},
            {"type": "sse", "url": "http://user:secret@127.0.0.1:64342/sse"},
            {"type": "sse", "url": "http://127.0.0.1:64342/sse?token=secret"},
            {"type": "sse", "url": "http://127.0.0.1:64342/sse#secret"},
            {"type": "sse", "url": "http://127.0.0.1.example.com/sse"},
            {**SOME_IDE_ENDPOINT, "headers": {"Authorization": "a-token"}},
            {"type": "sse", "url": 64342},
            "not a table",
        ):
            with self.subTest(server=server):
                self.assertFalse(s.is_bare_loopback_endpoint(server))

    def test_a_credentialed_session_keeps_them(self):
        data = {"primaryApiKey": "a-stored-key", "mcpServers": {"x": {}}}
        self.assertEqual(s.scrub_replica(data, SOME_CWD), data)

    def test_a_project_entry_that_is_no_table_survives_the_peer_scrub(self):
        data = {"projects": {SOME_CWD: "not a table"}}
        self.assertEqual(s.scrub_replica(data, SOME_CWD, open_weight=True), data)

    def test_a_non_dict_projects_value_passes_through(self):
        data = {**SOME_SETTINGS, "projects": "corrupt"}
        self.assertEqual(s.scrub_replica(data, SOME_CWD), data)


class ReplicaText(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)

    def _write(self, text):
        path = self.dir / "claude.json"
        path.write_text(text, encoding="utf-8")
        return path

    def test_the_replica_drops_foreign_projects_and_compacts(self):
        src = self._write(
            json.dumps({"projects": {SOME_CWD: {}, SOME_SIBLING: {}}, **SOME_SETTINGS})
        )
        out = json.loads(s.replica_text(src, SOME_CWD))
        self.assertEqual(out, {"projects": {SOME_CWD: {}}, **SOME_SETTINGS})

    def test_a_projects_free_file_is_byte_identical(self):
        self.assertEqual(
            s.replica_text(self._write(SOME_COMPACT_JSON), SOME_CWD), SOME_COMPACT_JSON
        )

    def test_an_absent_unparseable_or_non_object_file_degrades_to_empty(self):
        missing = self.dir / "absent.json"
        for src in (missing, self._write("not json"), self._write("[1,2]")):
            self.assertEqual(s.replica_text(src, SOME_CWD), "{}")


if __name__ == "__main__":
    unittest.main()
