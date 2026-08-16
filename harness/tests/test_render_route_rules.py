#!/usr/bin/env python3
"""Tests for render-route-rules.py (stdlib only).

Run: python3 harness/tests/test_render_route_rules.py

Pins the generator guards:
  1. Extraction reads all four constructors, resolves name constants,
     and merges duplicate rules into one row.
  2. A non-literal rule argument fails extraction — never a partial table.
  3. Calls inside the constructor definitions (internal forwarding) are
     skipped, not misread as call sites.
  4. The real routing source yields the sentinel rules and a plausible count.
  5. Write and --check agree: a fresh render passes --check; a corrupted
     copy fails it.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load  # noqa: E402

rrr = load("render_route_rules", "render-route-rules.py")

FIXTURE = """
TARGET = "fixture-agent"

def _dispatch(next_agents, rule, reason, req_id, **context):
    return {}

def _bounce(upstream, rule, reason, req_id, errors, **context):
    return _dispatch([upstream], rule, reason, req_id)

def _blocked(rule, reason, req_id=None, errors=None, **context):
    return {}

def _escalate(rule, reason, req_id=None, **context):
    return {}

def handler():
    if 1:
        return _dispatch([TARGET], "go-on", "r", "REQ")
    if 2:
        return _dispatch(["a", "b"], "go-on", "r", "REQ")
    if 3:
        return _bounce(TARGET, "bad-record", "r", "REQ", [])
    if 4:
        return _blocked("halted", "r")
    return _escalate("stuck", "r")
"""


class TestExtraction(unittest.TestCase):
    def rules(self, source):
        return rrr.extract(source, rrr.module_constants(source))

    def test_all_four_constructors_and_constant_resolution(self):
        rules = self.rules(FIXTURE)
        self.assertEqual(set(rules), {"go-on", "bad-record", "halted", "stuck"})
        self.assertEqual(
            rules["go-on"],
            {("dispatch", "`fixture-agent`"), ("dispatch", "`a`, `b`")},
        )
        self.assertEqual(
            rules["bad-record"], {("dispatch (bounce)", "`fixture-agent`")}
        )
        self.assertEqual(rules["halted"], {("blocked", "—")})
        self.assertEqual(rules["stuck"], {("escalate", "—")})

    def test_non_literal_rule_fails(self):
        source = FIXTURE + '\ndef bad(r):\n    return _blocked(r, "reason")\n'
        with self.assertRaises(ValueError):
            self.rules(source)

    def test_internal_forwarding_is_skipped(self):
        # _bounce's own body calls _dispatch with parameter names; without
        # the constructor-body skip that call would fail as non-literal.
        self.rules(FIXTURE)

    def test_unresolved_name_target_is_computed(self):
        source = FIXTURE + (
            '\ndef dyn(who):\n    return _dispatch([who], "dyn-rule", "r", "REQ")\n'
        )
        rules = self.rules(source)
        self.assertEqual(rules["dyn-rule"], {("dispatch", "(computed)")})


class TestRealSource(unittest.TestCase):
    def test_sentinel_rules_and_count(self):
        source = rrr.ROUTING.read_text(encoding="utf-8")
        constants = rrr.module_constants(
            rrr.RECORDS.read_text(encoding="utf-8")
        ) | rrr.module_constants(source)
        rules = rrr.extract(source, constants)
        for sentinel in ("feature-complete", "intake-ready", "review-non-convergence"):
            self.assertIn(sentinel, rules)
        self.assertGreaterEqual(len(rules), 40)


class TestWriteAndCheck(unittest.TestCase):
    def test_render_then_check_roundtrip(self):
        original = rrr.OUTPUT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                rrr.OUTPUT = Path(tmp) / "route-rules.md"
                self.assertEqual(rrr.main(["render-route-rules.py"]), 0)
                self.assertTrue(rrr.OUTPUT.exists())
                self.assertEqual(rrr.main(["render-route-rules.py", "--check"]), 0)
                rrr.OUTPUT.write_text("drifted\n", encoding="utf-8")
                self.assertEqual(rrr.main(["render-route-rules.py", "--check"]), 1)
        finally:
            rrr.OUTPUT = original

    def test_usage_error(self):
        self.assertEqual(rrr.main(["render-route-rules.py", "--bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
