#!/usr/bin/env python3
"""The route-rules renderer: extraction from the routing source, and the render-then-check contract."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load

rrr = load("render_route_rules", "render-route-rules.py")

RENDERED = 0
DRIFT_EXIT = 1
USAGE_EXIT = 2
RULE_COUNT_FLOOR = 40
SENTINEL_RULES = ("feature-complete", "intake-ready", "review-non-convergence")
SOME_AGENT = "fixture-agent"

FIXTURE = f'''
TARGET = "{SOME_AGENT}"

def _dispatch(next_agents, rule, reason, req_id, **context):
    return {{}}

def _bounce(upstream, rule, reason, req_id, errors, **context):
    return _dispatch([upstream], rule, reason, req_id)

def _blocked(rule, reason, req_id=None, errors=None, **context):
    return {{}}

def _escalate(rule, reason, req_id=None, **context):
    return {{}}

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
'''

METHOD_FIXTURE = (
    FIXTURE
    + """
class Ctx:
    def dispatch(self, next_agents, rule, reason, **context):
        return _dispatch(next_agents, rule, reason, "REQ", **context)

    def bounce(self, upstream, rule, reason, errors, **context):
        return _dispatch([upstream], rule, reason, "REQ", errors=errors)

    def blocked(self, rule, reason, errors=None, **context):
        return _blocked(rule, reason, "REQ", errors)

    def escalate(self, rule, reason, **context):
        return _escalate(rule, reason, "REQ")


def method_handler(ctx):
    if 1:
        return ctx.dispatch([TARGET], "method-go", "r")
    if 2:
        return ctx.bounce(TARGET, "method-bad", "r", [])
    if 3:
        return ctx.blocked("method-halted", "r")
    return ctx.escalate("method-stuck", "r")
"""
)


def rules_of(source):
    return rrr.extract(source, rrr.module_constants(source))


class Extraction(unittest.TestCase):
    def test_every_constructor_is_read_and_a_name_constant_resolves(self):
        rules = rules_of(FIXTURE)
        self.assertEqual(set(rules), {"go-on", "bad-record", "halted", "stuck"})
        self.assertEqual(
            rules["go-on"],
            {("dispatch", f"`{SOME_AGENT}`"), ("dispatch", "`a`, `b`")},
        )
        self.assertEqual(
            rules["bad-record"], {("dispatch (bounce)", f"`{SOME_AGENT}`")}
        )
        self.assertEqual(rules["halted"], {("blocked", "—")})
        self.assertEqual(rules["stuck"], {("escalate", "—")})

    def test_a_non_literal_rule_argument_fails_extraction(self):
        source = FIXTURE + '\ndef bad(r):\n    return _blocked(r, "reason")\n'
        with self.assertRaises(ValueError):
            rules_of(source)

    def test_forwarding_inside_a_constructor_body_is_skipped(self):
        # _bounce's own body calls _dispatch with parameter names; read as a
        # call site it would fail as non-literal.
        rules_of(FIXTURE)

    def test_an_unresolved_name_target_renders_as_computed(self):
        source = FIXTURE + (
            '\ndef dyn(who):\n    return _dispatch([who], "dyn-rule", "r", "REQ")\n'
        )
        rules = rules_of(source)
        self.assertEqual(rules["dyn-rule"], {("dispatch", "(computed)")})


class MethodFormExtraction(unittest.TestCase):
    def test_context_method_calls_are_extracted_like_module_calls(self):
        rules = rules_of(METHOD_FIXTURE)
        self.assertEqual(rules["method-go"], {("dispatch", f"`{SOME_AGENT}`")})
        self.assertEqual(
            rules["method-bad"], {("dispatch (bounce)", f"`{SOME_AGENT}`")}
        )
        self.assertEqual(rules["method-halted"], {("blocked", "—")})
        self.assertEqual(rules["method-stuck"], {("escalate", "—")})

    def test_forwarding_inside_the_method_definitions_is_skipped(self):
        rules = rules_of(METHOD_FIXTURE)
        self.assertEqual(
            set(rules),
            {
                "go-on",
                "bad-record",
                "halted",
                "stuck",
                "method-go",
                "method-bad",
                "method-halted",
                "method-stuck",
            },
        )


class RealSource(unittest.TestCase):
    def test_the_routing_source_yields_the_sentinel_rules_above_the_floor(self):
        source = rrr.ROUTING.read_text(encoding="utf-8")
        constants = rrr.module_constants(
            rrr.RECORDS.read_text(encoding="utf-8")
        ) | rrr.module_constants(source)
        rules = rrr.extract(source, constants)
        for sentinel in SENTINEL_RULES:
            self.assertIn(sentinel, rules)
        self.assertGreaterEqual(len(rules), RULE_COUNT_FLOOR)


class WriteAndCheck(unittest.TestCase):
    def test_a_fresh_render_passes_check_and_a_drifted_copy_fails_it(self):
        original = rrr.OUTPUT
        try:
            with tempfile.TemporaryDirectory() as tmp:
                rrr.OUTPUT = Path(tmp) / "route-rules.md"
                self.assertEqual(rrr.main(["render-route-rules.py"]), RENDERED)
                self.assertTrue(rrr.OUTPUT.exists())
                self.assertEqual(
                    rrr.main(["render-route-rules.py", "--check"]), RENDERED
                )
                rrr.OUTPUT.write_text("drifted\n", encoding="utf-8")
                self.assertEqual(
                    rrr.main(["render-route-rules.py", "--check"]), DRIFT_EXIT
                )
        finally:
            rrr.OUTPUT = original

    def test_an_unknown_flag_is_a_usage_error(self):
        self.assertEqual(rrr.main(["render-route-rules.py", "--bogus"]), USAGE_EXIT)


if __name__ == "__main__":
    unittest.main()
