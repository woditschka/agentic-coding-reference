"""Shared test scaffolding for the scripts runtime (stdlib only).

Extracted from test_handoff.py when the tests became a package tree (ADR
2026-07-17 runtime-package-layout). Every handoff suite imports its fixtures,
base cases, and the loaded modules from here.

Two module handles: `handoff` is the package — the public API surface every
`handoff.<name>` access resolves against. `entry` is handoff.py, the CLI
launcher, loaded under the name "handoff_entry" so its own `from handoff.…`
imports resolve to the real package, not to itself. CLI tests call entry.main;
the append-clock patch targets entry.ts_now (the binding cmd_append uses).
"""

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import handoff as handoff  # re-exported to the suites; the API surface

_HERE = Path(__file__).resolve().parent.parent  # the scripts dir
_REPO_SCHEMAS = _HERE.parent / "schemas" / "scratch"


def _load_entry():
    """Load handoff.py as "handoff_entry" so `from handoff.…` in it resolves to
    the installed package, not to the entry file being executed."""
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    spec = importlib.util.spec_from_file_location("handoff_entry", _HERE / "handoff.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["handoff_entry"] = mod
    spec.loader.exec_module(mod)
    return mod


entry = _load_entry()


REQ = "REQ-DEMO-001"
TS = "2026-06-11T10:00:00Z"

TEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["type", "req_id", "ts", "author"],
    "properties": {
        "type": {"const": "test-rec"},
        "req_id": {"type": "string", "pattern": "^REQ-[A-Z]+-[0-9]{3}$"},
        "ts": {"type": "string", "format": "date-time"},
        "author": {"enum": ["tester"]},
        "note": {"type": "string", "minLength": 1},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "nested": {
            "type": "object",
            "required": ["zee"],
            "properties": {"zee": {"type": "string"}, "aye": {"type": "string"}},
        },
        "retry": {"type": "integer", "minimum": 1, "maximum": 3},
    },
}

STRICT_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {"type": {"const": "strict-rec"}, "ts": {"type": "string"}},
    "additionalProperties": False,
}

REF_SCHEMA = {
    "type": "object",
    "required": ["type", "facet"],
    "properties": {
        "type": {"const": "ref-rec"},
        "facet": {"$ref": "#/definitions/facet"},
    },
    "definitions": {"facet": {"enum": ["clear", "concern"]}},
}

BAD_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "bad-rec"}, "x": {"anyOf": [{"type": "string"}]}},
}

NUM_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"const": "num-rec"},
        "n": {"enum": [1, 2]},
        "flag": {"const": True},
    },
}

BADTYPE_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "badtype-rec"}, "x": {"type": "strin"}},
}

BOOLSUB_SCHEMA = {
    "type": "object",
    "properties": {"type": {"const": "boolsub-rec"}, "x": True},
}

TUPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "tuple-rec"},
        "x": {"type": "array", "items": [{"type": "string"}]},
    },
}

PATTERNFROM_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"const": "pf-rec"},
        "tname": {"type": "string", "patternFrom": "test_name_pattern"},
    },
}

ENUMFROM_SCHEMA = {
    "type": "object",
    "required": ["type"],
    "properties": {
        "type": {"const": "ef-rec"},
        "verbs": {
            "type": "array",
            "items": {"type": "string", "enumFrom": "gate.verbs"},
        },
    },
}


def base_record(**overrides):
    record = {"type": "test-rec", "req_id": REQ, "ts": TS, "author": "tester"}
    record.update(overrides)
    return record


class HandoffCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.log = root / "handoff.jsonl"
        self.schemas = root / "schemas"
        self.schemas.mkdir()
        for name, schema in (
            ("test-rec", TEST_SCHEMA),
            ("strict-rec", STRICT_SCHEMA),
            ("ref-rec", REF_SCHEMA),
            ("bad-rec", BAD_SCHEMA),
            ("num-rec", NUM_SCHEMA),
            ("badtype-rec", BADTYPE_SCHEMA),
            ("boolsub-rec", BOOLSUB_SCHEMA),
            ("tuple-rec", TUPLE_SCHEMA),
            ("pf-rec", PATTERNFROM_SCHEMA),
            ("ef-rec", ENUMFROM_SCHEMA),
        ):
            (self.schemas / f"{name}.schema.json").write_text(json.dumps(schema))
        stamp = unittest.mock.patch.object(entry, "ts_now", return_value=TS)
        stamp.start()
        self.addCleanup(stamp.stop)
        # Pin the CLI's layout default inside the fixture root: the shipped
        # default is cwd-relative, so a run from a project root would leak the
        # real scripts/layout.toml (extra_reviewers, review config) into every
        # suite that never passes --layout.
        self.layout = root / "layout.toml"
        pin = unittest.mock.patch.object(entry, "DEFAULT_LAYOUT", str(self.layout))
        pin.start()
        self.addCleanup(pin.stop)

    def run_cli(self, *argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    code = entry.main(list(argv))
                except SystemExit as exc:
                    code = exc.code
        finally:
            sys.stdin = old_stdin
        return code, out.getvalue(), err.getvalue()

    def append(self, record, rtype=None, schemas=None):
        return self.run_cli(
            "append",
            rtype or record.get("type", "test-rec"),
            "--file",
            str(self.log),
            "--schemas",
            str(schemas or self.schemas),
            stdin=json.dumps(record),
        )

    def log_lines(self):
        return self.log.read_text().splitlines()

    def write_log(self, *records):
        self.log.write_text("".join(json.dumps(r) + "\n" for r in records))


# Route fixtures use permissive schemas: route's own decisions are under test,
# not the validator (TestAppendValidation covers that). Gate-failure tests
# override one schema with a strict variant.
PERMISSIVE = {"type": "object", "required": ["type"]}
PIPELINE_TYPES = (
    "prd-entry",
    "design-block",
    "build-pass",
    "build-failure",
    "review-feedback",
    "consultation-request",
    "consultation-response",
    "dispatch-start",
    "design-doc-autofix",
    "prd-autofix",
    "grader-features",
    "grader-verdict",
    "review-plan",
    "intake-decision",
)
FLOOR = ["code-quality-reviewer", "test-reviewer", "security-reviewer", "doc-reviewer"]


def rec(rtype, **fields):
    record = {"type": rtype, "req_id": "REQ-A-001", "ts": TS, "author": "tester"}
    record.update(fields)
    return record


class RouteCase(HandoffCase):
    def setUp(self):
        super().setUp()
        for name in PIPELINE_TYPES:
            (self.schemas / f"{name}.schema.json").write_text(json.dumps(PERMISSIVE))

    def route(self, *extra):
        code, out, err = self.run_cli(
            "route", "--file", str(self.log), "--schemas", str(self.schemas), *extra
        )
        self.assertEqual(code, 0, err)
        return json.loads(out)


# --- view --------------------------------------------------------------------
# Characterization of the human-facing renderer: append-position ordering
# (never ts), round grouping by reviewer reappearance, graceful degradation
# on partial/dirty logs, and a byte-stable plain snapshot.

VIEW_SNAPSHOT = """\
╭──────────────────────────────────────────────────────────────────╮
│ REQ-DEMO-001  Rate-limit the API                                 │
│ 3 review rounds · 2 build-passes · 1 build-failure · grade CLEAR │
│ ladder round 2 of 4                                              │
╰──────────────────────────────────────────────────────────────────╯

              R1     R2     R3
code-quality  ✎ (2)  ✎ (1)  ✔
test          ·      ·      ·
security      ✔ (1)  ·      ·
doc           ·      ·      ·

◇ prd-entry  Rate-limit the API  (prd-expert)
◈ design-block  minor  (design)
◆ implement  (implementer)  ◷ 15m
  ├ ↳ consult  → design  Per-tenant or per-endpoint?
  ├ ↲ consult  ← design  Per-tenant.
  ├ ▲ build  ✗ unit-test failed  retry 1
  └ ▲ build  ✓ clean   fmt · test
✎ review  code-quality  changes_requested  (2 findings)
  ├ [blocked] limiter.py:42  The bucket refill races with allow(); two workers can both observe a singl…
  └ [autofix] limiter.py:12  The Limiter type lacks a doc comment.
✔ review  security  approved  (1 finding)
  └ [clarify] prd.md:9  Is the burst size a hard product number?
✎ review  code-quality  changes_requested  (1 finding)
  └ [escalate] limiter.py:88  Persisting bucket state was not in the PRD; scope call for a human.
✚ doc-autofix  docs/system-design.md  stale-reference  (claude)
↻ implement  (implementer)  ← code-quality  (1 finding)  ◷ 4m
  └ ▲ build  ✓ clean   fmt · test
✔ review  code-quality  approved
◆ grade  CLEAR  Small, well-tested limiter.
  · blast_radius     clear    one package
  · scope_deviation  concern  persistence escalated
• mystery-record  (someone-new)
"""


def vrec(rtype, author, ts, **fields):
    record = {"type": rtype, "req_id": REQ, "ts": ts, "author": author}
    record.update(fields)
    return record


def view_fixture():
    """Every record type in append order, across two implement sessions and
    three review rounds. Session 1 (a fresh ◆ implement) owns a mid-work
    consult, a build retry, and its clean build; session 2 (a ↻ implement fix
    answering code-quality) owns its rebuild. The design-block ts is one hour
    BEFORE the prd-entry's, so any ts sort would scramble the append order."""
    return [
        vrec(
            "prd-entry",
            "product-requirements-expert",
            "2026-07-06T10:00:00Z",
            title="Rate-limit the API",
        ),  # L1
        vrec(
            "design-block",
            "system-design-expert",
            "2026-07-06T09:00:00Z",
            verdict="minor",
        ),  # L2
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T10:15:00Z",
            responding_to=[2],
        ),  # L3 opener
        vrec(
            "consultation-request",
            "feature-implementer",
            "2026-07-06T10:16:00Z",
            target="system-design-expert",
            context="granularity",
            question="Per-tenant or per-endpoint?",
        ),  # L4
        vrec(
            "consultation-response",
            "system-design-expert",
            "2026-07-06T10:18:00Z",
            in_response_to=4,
            answer="Per-tenant.",
        ),  # L5
        vrec(
            "build-failure",
            "feature-implementer",
            "2026-07-06T10:20:00Z",
            retry=1,
            failed_check="unit-test",
        ),  # L6
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T10:30:00Z",
            gate_checks_run=["fmt", "test"],
        ),  # L7 closes S1
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T10:40:00Z",
            verdict="changes_requested",
            findings=[
                {
                    "tag": "blocked",
                    "location": "src/ingest/limiter.py:42 (allow)",
                    "description": "The bucket refill races with allow(); two workers can"
                    " both observe a single remaining token and pass.",
                    "fix": "Hold the lock across the refill and the take.",
                },
                {
                    "tag": "autofix",
                    "location": "src/ingest/limiter.py:12",
                    "description": "The Limiter type lacks a doc comment.",
                    "fix": "Add the standard comment.",
                },
            ],
        ),  # L8
        vrec(
            "review-feedback",
            "security-reviewer",
            "2026-07-06T10:41:00Z",
            verdict="approved",
            findings=[
                {
                    "tag": "clarify",
                    "location": "docs/prd.md:9",
                    "description": "Is the burst size a hard product number?",
                    "clarify_target": "product-requirements-expert",
                }
            ],
        ),  # L9
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T11:00:00Z",
            verdict="changes_requested",
            findings=[
                {
                    "tag": "escalate",
                    "location": "src/ingest/limiter.py:88",
                    "description": "Persisting bucket state was not in the PRD;"
                    " scope call for a human.",
                }
            ],
        ),  # L10
        vrec(
            "design-doc-autofix",
            "claude",
            "2026-07-06T11:05:00Z",
            file="docs/system-design.md",
            category="stale-reference",
            source_finding="x",
            old_content="a",
            new_content="b",
            lines_changed=1,
            chars_changed=2,
        ),  # L11
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T11:05:30Z",
            responding_to=[10],
        ),  # L12 fix opener
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T11:10:00Z",
            gate_checks_run=["fmt", "test"],
        ),  # L13 closes S2
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T11:20:00Z",
            verdict="approved",
            findings=[],
        ),  # L14
        vrec(
            "grader-features",
            "change-grader",
            "2026-07-06T11:30:00Z",
            features={"loc": 12},
        ),
        vrec(
            "grader-verdict",
            "change-grader",
            "2026-07-06T11:31:00Z",
            verdict="clear",
            summary="Small, well-tested limiter.",
            rationale="r",
            facets={
                "blast_radius": {"verdict": "clear", "note": "one package"},
                "scope_deviation": {
                    "verdict": "concern",
                    "note": "persistence escalated",
                },
            },
        ),
        vrec("mystery-record", "someone-new", "2026-07-06T11:40:00Z"),
    ]


def timed_fixture():
    """A dispatch-start before each of prd, design, implement, and review, so
    every timeable step carries a duration — the gate the cost tail rides. The
    grade stays untimed by contract (the change-grader is dispatch-exempt; the
    dispatch-start schema rejects it as author). Shared by the duration tests
    (TestView) and the cost-overlay tests (TestBoardCost) so both assert
    against one timeline."""
    return [
        vrec(
            "dispatch-start",
            "product-requirements-expert",
            "2026-07-06T10:00:00Z",
            responding_to=[0],
        ),  # L1
        vrec(
            "prd-entry",
            "product-requirements-expert",
            "2026-07-06T10:03:00Z",
            title="t",
        ),  # L2 → 3m
        vrec(
            "dispatch-start",
            "system-design-expert",
            "2026-07-06T10:03:00Z",
            responding_to=[2],
        ),  # L3
        vrec(
            "design-block",
            "system-design-expert",
            "2026-07-06T10:05:00Z",
            verdict="covered",
        ),  # L4 → 2m
        vrec(
            "dispatch-start",
            "feature-implementer",
            "2026-07-06T10:05:00Z",
            responding_to=[4],
        ),  # L5
        vrec(
            "build-pass",
            "feature-implementer",
            "2026-07-06T10:20:00Z",
            gate_checks_run=["test"],
        ),  # L6 → 15m
        vrec(
            "dispatch-start",
            "code-quality-reviewer",
            "2026-07-06T10:20:00Z",
            responding_to=[6],
        ),  # L7
        vrec(
            "review-feedback",
            "code-quality-reviewer",
            "2026-07-06T10:22:00Z",
            verdict="approved",
            findings=[],
        ),  # L8 → 2m
        vrec(
            "grader-verdict",
            "change-grader",
            "2026-07-06T10:26:00Z",
            verdict="clear",
            summary="done",
        ),  # L9, untimed
    ]
