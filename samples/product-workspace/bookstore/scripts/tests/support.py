"""Shared test scaffolding for the scripts runtime: the loaded modules, fixtures, and named defaults.

`handoff` is the package under test; `entry` is handoff.py loaded as "handoff_entry" so its own
`from handoff.…` imports resolve to the package rather than to itself.
"""

import contextlib
import dataclasses
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from handoff import (
    ROSTER_FLOOR,
    Baseline,
    CostFigures,
    LogEntry,
    RouteInput,
    route_decision,
    typed_log,
)

_HERE = Path(__file__).resolve().parent.parent  # the scripts dir
_REPO_SCHEMAS = _HERE.parent / "schemas" / "scratch"


def _load_entry():
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    spec = importlib.util.spec_from_file_location("handoff_entry", _HERE / "handoff.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["handoff_entry"] = mod
    spec.loader.exec_module(mod)
    return mod


entry = _load_entry()


SOME_REQ_ID = "REQ-DEMO-001"
A_DESIGN_DOC = "docs/system-design.md"
SOME_TS = "2026-06-11T10:00:00Z"
SOME_AUTHOR = "tester"

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
    "properties": {
        "type": {"const": "strict-rec"},
        "ts": {"type": "string"},
    },
    "additionalProperties": False,
}

REF_SCHEMA = {
    "type": "object",
    "required": ["type", "facet"],
    "properties": {
        "type": {"const": "ref-rec"},
        "facet": {"$ref": "#/definitions/facet"},
    },
    "definitions": {"facet": {"enum": ["skim", "scrutinize"]}},
}

BAD_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "bad-rec"},
        "x": {"anyOf": [{"type": "string"}]},
    },
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


def a_record(record_type="test-rec", **fields):
    """Return one raw record with irrelevant common fields, overridden by `fields`."""
    record = {
        "type": record_type,
        "req_id": SOME_REQ_ID,
        "ts": SOME_TS,
        "author": SOME_AUTHOR,
    }
    record.update(fields)
    return record


def entries(*raws):
    """Return the typed ledger lines for raw records numbered from one."""
    return typed_log(LogEntry(no, raw) for no, raw in enumerate(raws, 1))


SOME_FIGURES = CostFigures("1.2M", "7k", "2.50", "88", "71")
SOME_COST_TEXT = " │ Σ ▲1.2M ▼7k $2.50 │ ⛁ 88% $71%"


class FakeCostLookup:
    """A cost overlay that answers every window with the same figures and tiers."""

    def __init__(self, figures=SOME_FIGURES, tiers=None):
        self._figures = figures
        self._tiers = tiers

    def window(self, _agent, _start, _end):
        return self._figures

    def slice_window(self, _agents, _start, _end):
        return self._figures

    def window_types(self, _start, _end):
        return self._tiers


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
        stamp = unittest.mock.patch.object(entry, "ts_now", return_value=SOME_TS)
        stamp.start()
        self.addCleanup(stamp.stop)
        # The shipped layout default is cwd-relative, so a run from a project
        # root would leak the real scripts/layout.toml into every suite that
        # never passes --layout.
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
# not the validator. Gate-failure tests override one schema with a strict variant.
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
FLOOR = list(ROSTER_FLOOR)


A_SLICE = "REQ-A-001"


def a_slice_record(record_type, **fields):
    """Return one raw record of the routed slice with irrelevant common fields, overridden by `fields`."""
    record = {"type": record_type, "req_id": A_SLICE, "ts": SOME_TS, "author": "tester"}
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


A_READABLE_BASELINE = Baseline(True, None)


@dataclasses.dataclass
class FakeRepository:
    """A repository whose answers are the configured values."""

    repo_state: str | None = "ok"
    dirty: tuple[str, ...] | None = ()
    baseline: Baseline = A_READABLE_BASELINE
    prd_lines: list[str] | None = dataclasses.field(default_factory=list)
    prd_text: str | None = ""

    def state(self):
        return self.repo_state

    def committed_prd_lines(self):
        return self.prd_lines

    def worktree_prd_text(self):
        return self.prd_text

    def dirty_design_doc_paths(self):
        return None if self.dirty is None else list(self.dirty)

    def design_docs_baseline(self):
        return self.baseline


class FakeGate:
    """A gate that answers each record type with its configured errors and every other with none."""

    def __init__(self, **errors_by_type):
        self._errors = {k.replace("_", "-"): list(v) for k, v in errors_by_type.items()}

    def errors(self, _entry, record_type):
        return list(self._errors.get(record_type, ()))


NO_SCHEMAS_DIR = ""


def route(*raws, req_id=None, layout=None, delta=(), gate=None):
    """Route raw records numbered from one, in process, under a fake gate."""
    request = RouteInput(
        [LogEntry(no, raw) for no, raw in enumerate(raws, 1)],
        req_id,
        NO_SCHEMAS_DIR,
        layout or {},
        delta,
    )
    return route_decision(request, gate or FakeGate())


# One representative record per core schema type and the exact bytes the append
# path writes for it: field order follows the schema's property declaration
# order, ts is the stamped SOME_TS.
GOLDEN_RECORDS = (
    (
        # Multibyte content pins ensure_ascii=False: the literal carries raw UTF-8 bytes.
        "consultation-request",
        {
            "type": "consultation-request",
            "req_id": SOME_REQ_ID,
            "author": "feature-implementer",
            "target": "system-design-expert",
            "context": "red-green transition for behavior X in slice Y",
            "question": "Which package owns the adapter? Prüfung: ✓ done",
            "stop_state": "widget.py:42, awaiting answer",
        },
        b'{"type": "consultation-request", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "feature-implementer", "target": '
        b'"system-design-expert", "context": "red-green transition for behavior '
        b'X in slice Y", "question": "Which package owns the adapter? '
        b'Pr\xc3\xbcfung: \xe2\x9c\x93 done", '
        b'"stop_state": "widget.py:42, awaiting answer"}\n',
    ),
    (
        "consultation-response",
        {
            "type": "consultation-response",
            "req_id": SOME_REQ_ID,
            "author": "system-design-expert",
            "in_response_to": 1,
            "answer": "Place the adapter in the boundary package.",
            "memory_updates": [
                {
                    "path": "docs/system-design.md",
                    "summary": "Note adapter placement.",
                }
            ],
            "notes": "See the adapter ADR.",
        },
        b'{"type": "consultation-response", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "system-design-expert", '
        b'"in_response_to": 1, "answer": "Place the adapter in the boundary '
        b'package.", "memory_updates": [{"path": "docs/system-design.md", '
        b'"summary": "Note adapter placement."}], "notes": "See the adapter '
        b'ADR."}\n',
    ),
    (
        "design-block",
        {
            "type": "design-block",
            "req_id": SOME_REQ_ID,
            "author": "system-design-expert",
            "verdict": "covered",
            "architectural_fit": "Fits the existing adapter pattern.",
            "primary_paths": ["src/widget.py"],
            "supporting_paths": ["tests/test_widget.py"],
            "patterns": [
                {"ref": "src/base.py:10", "description": "Follow the base adapter."}
            ],
        },
        b'{"type": "design-block", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "system-design-expert", "verdict": '
        b'"covered", "architectural_fit": "Fits the existing adapter pattern.", '
        b'"primary_paths": ["src/widget.py"], "supporting_paths": '
        b'["tests/test_widget.py"], "patterns": [{"ref": "src/base.py:10", '
        b'"description": "Follow the base adapter."}]}\n',
    ),
    (
        "design-doc-autofix",
        {
            "type": "design-doc-autofix",
            "req_id": SOME_REQ_ID,
            "author": "root",
            "file": "docs/system-design.md",
            "category": "writing-standards",
            "source_finding": {
                "review_feedback_author": "doc-reviewer",
                "review_feedback_ts": SOME_TS,
                "tag": "autofix",
                "location": "docs/system-design.md:7",
                "description": "Tighten the sentence.",
                "fix": "The adapter owns serialization.",
            },
            "old_content": "The adapter is responsible for owning serialization.",
            "new_content": "The adapter owns serialization.",
            "lines_changed": 1,
            "chars_changed": 20,
        },
        b'{"type": "design-doc-autofix", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "root", "file": '
        b'"docs/system-design.md", "category": "writing-standards", '
        b'"source_finding": {"review_feedback_author": "doc-reviewer", '
        b'"review_feedback_ts": "2026-06-11T10:00:00Z", "tag": "autofix", '
        b'"location": "docs/system-design.md:7", "description": "Tighten the '
        b'sentence.", "fix": "The adapter owns serialization."}, "old_content": '
        b'"The adapter is responsible for owning serialization.", "new_content": '
        b'"The adapter owns serialization.", "lines_changed": 1, "chars_changed": '
        b"20}\n",
    ),
    (
        "prd-autofix",
        {
            "type": "prd-autofix",
            "req_id": SOME_REQ_ID,
            "author": "root",
            "file": "docs/prd.md",
            "category": "writing-standards",
            "source_finding": {
                "review_feedback_author": "doc-reviewer",
                "review_feedback_ts": SOME_TS,
                "tag": "autofix",
                "location": "docs/prd.md:12",
                "description": "Split the sentence.",
                "fix": "The export runs nightly. It writes one file.",
            },
            "old_content": "The export runs nightly and writes one file.",
            "new_content": "The export runs nightly. It writes one file.",
            "lines_changed": 1,
            "chars_changed": 6,
        },
        b'{"type": "prd-autofix", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "root", "file": '
        b'"docs/prd.md", "category": "writing-standards", '
        b'"source_finding": {"review_feedback_author": "doc-reviewer", '
        b'"review_feedback_ts": "2026-06-11T10:00:00Z", "tag": "autofix", '
        b'"location": "docs/prd.md:12", "description": "Split the '
        b'sentence.", "fix": "The export runs nightly. It writes one file."}, '
        b'"old_content": "The export runs nightly and writes one file.", '
        b'"new_content": "The export runs nightly. It writes one file.", '
        b'"lines_changed": 1, "chars_changed": 6}\n',
    ),
    (
        "dispatch-start",
        {
            "type": "dispatch-start",
            "req_id": SOME_REQ_ID,
            "author": "feature-implementer",
            "responding_to": [0],
        },
        b'{"type": "dispatch-start", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "feature-implementer", '
        b'"responding_to": [0]}\n',
    ),
    (
        "grader-features",
        {
            "type": "grader-features",
            "req_id": SOME_REQ_ID,
            "author": "change-grader",
            "features": {
                "base_ref": "main",
                "head_ref": "0f1e2d3c",
                "head_kind": "worktree",
                "files_changed": 2,
                "module_count": 1,
                "test_prod_ratio": 1.5,
                "hunks": 3,
                "build_passed": True,
                "reviewers": None,
                "build_retries": 0,
                "consultations": 0,
                "design_revisions": 0,
            },
        },
        b'{"type": "grader-features", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "change-grader", "features": '
        b'{"base_ref": "main", "head_ref": "0f1e2d3c", "head_kind": "worktree", '
        b'"files_changed": 2, "module_count": 1, "test_prod_ratio": 1.5, "hunks": '
        b'3, "build_passed": true, "reviewers": null, "build_retries": 0, '
        b'"consultations": 0, "design_revisions": 0}}\n',
    ),
    (
        "grader-verdict",
        {
            "type": "grader-verdict",
            "req_id": SOME_REQ_ID,
            "author": "change-grader",
            "responding_to": [1],
            "summary": "relabel unknown-activity bucket",
            "facets": {
                "blast_radius": {"verdict": "skim", "note": "One module touched."},
                "semantic_surprise": {
                    "verdict": "skim",
                    "note": "No behavior change.",
                },
                "test_adequacy": {
                    "verdict": "skim",
                    "note": "Tests cover the path.",
                },
                "reviewer_hedging": {
                    "verdict": "skim",
                    "note": "No hedged approvals.",
                },
                "scope_deviation": {
                    "verdict": "skim",
                    "note": "Matches the slice.",
                },
            },
            "rationale": "Small, well-tested change with no surprises.",
            "verdict": "skim",
        },
        b'{"type": "grader-verdict", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "change-grader", "responding_to": '
        b'[1], "summary": "relabel unknown-activity bucket", "facets": '
        b'{"blast_radius": {"verdict": "skim", "note": "One module touched."}, '
        b'"semantic_surprise": {"verdict": "skim", "note": "No behavior '
        b'change."}, "test_adequacy": {"verdict": "skim", "note": "Tests cover '
        b'the path."}, "reviewer_hedging": {"verdict": "skim", "note": "No '
        b'hedged approvals."}, "scope_deviation": {"verdict": "skim", "note": '
        b'"Matches the slice."}}, "rationale": "Small, well-tested change with no '
        b'surprises.", "verdict": "skim"}\n',
    ),
    (
        "review-feedback",
        {
            "type": "review-feedback",
            "req_id": SOME_REQ_ID,
            "author": "code-quality-reviewer",
            "verdict": "changes_requested",
            "findings": [
                {
                    "tag": "blocked",
                    "location": "src/widget.py:1",
                    "description": "Extract the duplicated helper.",
                    "severity": "critical",
                }
            ],
        },
        b'{"type": "review-feedback", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "code-quality-reviewer", "verdict": '
        b'"changes_requested", "findings": [{"tag": "blocked", "location": '
        b'"src/widget.py:1", "description": "Extract the duplicated helper.", '
        b'"severity": "critical"}]}\n',
    ),
    (
        "review-plan",
        {
            "type": "review-plan",
            "req_id": SOME_REQ_ID,
            "author": "review-plan-engine",
            "risk": "low",
            "roster": ["code-quality-reviewer", "test-reviewer"],
            "scope": "full-diff",
            "basis": {"tree_sha": "a" * 40, "pass": "first"},
            "rationale": "Small surface-matched change.",
        },
        b'{"type": "review-plan", "req_id": "REQ-DEMO-001", "ts": '
        b'"2026-06-11T10:00:00Z", "author": "review-plan-engine", "risk": "low", '
        b'"roster": ["code-quality-reviewer", "test-reviewer"], "scope": '
        b'"full-diff", "basis": {"tree_sha": '
        b'"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "pass": "first"}, '
        b'"rationale": "Small surface-matched change."}\n',
    ),
)


def golden_record(record_type):
    """Return the golden raw record of one type, ts included."""
    return next(
        {**record, "ts": SOME_TS}
        for name, record, _ in GOLDEN_RECORDS
        if name == record_type
    )


# --- view --------------------------------------------------------------------


def vrec(rtype, author, ts, **fields):
    record = {"type": rtype, "req_id": SOME_REQ_ID, "ts": ts, "author": author}
    record.update(fields)
    return record


def view_fixture():
    """Every record type in append order across two implement sessions and three review rounds."""
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
        ),  # L2, an hour before the prd-entry so a ts sort would scramble the order
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
            verdict="skim",
            summary="Small, well-tested limiter.",
            rationale="r",
            facets={
                "blast_radius": {"verdict": "skim", "note": "one package"},
                "scope_deviation": {
                    "verdict": "scrutinize",
                    "note": "persistence escalated",
                },
            },
        ),
        vrec("mystery-record", "someone-new", "2026-07-06T11:40:00Z"),
    ]


def timed_fixture():
    """A dispatch-start before each timeable step, so every step carries a duration; the grade stays untimed."""
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
            verdict="skim",
            summary="done",
        ),  # L9, untimed
    ]
