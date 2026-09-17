#!/usr/bin/env python3
"""Run identical synthetic ledgers through a baseline tree and this one, and diff every command.

Usage: harness/fuzz-handoff.py --baseline TREE [--seed N] [--count N]

Each ledger is a random mix of well-formed and malformed records over one or
two slices, with garbage lines, a missing final newline, and a stray CRLF
sprinkled in. Every reading command runs on the ledger through both trees,
then one random append lands on each tree's own copy and the copies compare.
A refactor that preserves behavior prints no difference and exits 0; a named
fix prints exactly the differences it names. Stdlib only. Tested by
tests/test_fuzz_handoff.py.
"""

import argparse
import json
import random
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import differential  # noqa: E402

ROOT = HERE.parent
Raw = dict[str, Any]
DEFAULT_COUNT = 250
MAX_LINES = 14
DROP_ABSENT = 0.5
FIELD_CHANCE = 0.5
RARE_FIELD_CHANCE = 0.3
TRAILING_NEWLINE = 0.95
GARBAGE_LINE = 0.1
BLANK_LINE = 0.05
CRLF_LINE = 0.05

AUTHORS: list[Any] = [
    "feature-implementer",
    "system-design-expert",
    "product-requirements-expert",
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
    "change-grader",
    "review-planner",
    "review-plan-engine",
    "human",
    "pipeline-coordinator",
    "extra-reviewer",
    "",
    None,
    5,
    ["x"],
    "\u202ereviewer",
    "a\tb",
]
REQS: list[Any] = ["REQ-A-001", "REQ-A-001", "REQ-A-001", "REQ-B-002", None, "", 7]
STAMPS: list[Any] = [
    "2026-07-06T10:00:00Z",
    "2026-07-06T10:05:00Z",
    "2026-07-06T11:00:00+00:00",
    "bogus",
    None,
    12,
]
TAGS: list[Any] = [
    "autofix",
    "blocked",
    "escalate",
    "clarify",
    "truncation",
    "polish",
    None,
    3,
]
VERDICTS: list[Any] = [
    "approved",
    "changes_requested",
    "blocked",
    "skim",
    "scrutinize",
    "clear",
    None,
    ["approved"],
    {"v": 1},
    7,
]
KINDS = [
    "prd-entry",
    "design-block",
    "dispatch-start",
    "build-pass",
    "build-failure",
    "review-feedback",
    "review-plan",
    "grader-verdict",
    "grader-features",
    "consultation-request",
    "consultation-response",
    "intake-decision",
    "design-doc-autofix",
    "prd-autofix",
]
UNKNOWN_KIND = "unknown-kind"
READ_COMMANDS: list[list[str]] = [
    ["route"],
    ["view", "--no-color"],
    ["view", "--no-color", "--verbose"],
    ["view", "--markdown"],
    ["validate"],
    ["show", "--last", "5"],
    ["tier"],
    ["latest", "--type", "build-pass"],
    ["next-retry", "--req-id", "REQ-A-001"],
    ["audit-autofix"],
    ["route", "--req-id", "REQ-B-002"],
    ["view", "--no-color", "--req-id", "REQ-A-001"],
]


class Generator:
    """Random records, ledgers, and append candidates from one seeded source."""

    def __init__(self, seed: int) -> None:
        """Seed the source so a run is reproducible by its seed."""
        self.rng = random.Random(seed)

    def pick(self, options: list[Any]) -> Any:  # noqa: ANN401
        """Return one option."""
        return self.rng.choice(options)

    def finding(self) -> Any:  # noqa: ANN401
        """Return one finding, sometimes a non-object."""
        finding: Raw = {
            "tag": self.pick(TAGS),
            "location": self.pick(
                [
                    "src/a.py:1",
                    "docs/prd.md:3",
                    "docs/system-design.md:9",
                    "docs/adr/x.md",
                    None,
                    7,
                ]
            ),
            "description": self.pick(
                ["fix it", "x" * 120, "", None, "\u200bhidden", "a\nb"]
            ),
        }
        if self.rng.random() < FIELD_CHANCE:
            finding["severity"] = self.pick(["critical", "fixable", None, 2])
        if self.rng.random() < RARE_FIELD_CHANCE:
            finding["clarify_target"] = self.pick(["system-design-expert", "", None])
        if self.rng.random() < RARE_FIELD_CHANCE:
            finding["fix"] = self.pick(["do this", "", None])
        return self.pick([finding, finding, finding, "not-a-dict", 3])

    def record(self, kind: str, line_no: int) -> Raw:
        """Return one record of the kind, with its fields sometimes malformed or absent."""
        raw: Raw = {
            "type": kind,
            "req_id": self.pick(REQS),
            "ts": self.pick(STAMPS),
            "author": self.pick(AUTHORS),
        }
        fields = _FIELDS.get(kind)
        if fields is not None:
            raw.update(fields(self, line_no))
        elif kind == UNKNOWN_KIND:
            raw["type"] = self.pick(["mystery", None, 4, ""])
        for key in list(raw):
            if raw[key] is None and self.rng.random() < DROP_ABSENT:
                del raw[key]
        return raw

    def ledger(self) -> str:
        """Return one ledger text with the damage modes a real log can carry."""
        count = self.rng.randint(0, MAX_LINES)
        lines = [
            json.dumps(
                self.record(self.pick([*KINDS, UNKNOWN_KIND]), no), ensure_ascii=False
            )
            for no in range(1, count + 1)
        ]
        text = "\n".join(lines)
        if lines and self.rng.random() < TRAILING_NEWLINE:
            text += "\n"
        if self.rng.random() < GARBAGE_LINE:
            text += "not json\n"
        if self.rng.random() < BLANK_LINE:
            text += "\n"
        if self.rng.random() < CRLF_LINE:
            text = text.replace("\n", "\r\n", 1)
        return text

    def candidate(self) -> tuple[str, str]:
        """Return an append candidate: its type argument and the stdin text."""
        raw = self.record(self.pick(KINDS), 99)
        text = self.pick(
            [
                json.dumps(raw),
                "not json",
                "[1]",
                json.dumps({**raw, "type": "prd-entry"}),
            ]
        )
        return str(raw.get("type", "prd-entry")), text


def _prd_entry(g: Generator, _line_no: int) -> Raw:
    override = {
        "non_goal_id": "NG-1",
        "owner_decision": "ok",
        "source": g.pick(["dispatch", "intake:1", "consultation:2", "bad", 9]),
    }
    return {
        "title": g.pick(["Title", "", None, "t" * 90, 5]),
        "acceptance_criteria": g.pick([["a"], [], None, "x"]),
        "scope_overrides": g.pick([None, [], [override], "x", [7, {"non_goal_id": 3}]]),
    }


def _design_block(g: Generator, line_no: int) -> Raw:
    return {
        "verdict": g.pick(
            [
                "covered",
                "minor",
                "new",
                "foundational",
                "conflicting",
                "refactor-first",
                "weird",
                None,
                3,
            ]
        ),
        "supersedes_record_at": g.pick(
            [None, None, 1, 2, line_no - 1, line_no + 5, True, "1", 0, -1]
        ),
        "escalations": g.pick([[], ["e"], None, "x"]),
        "implementation_effort": g.pick([None, "routine", "moderate", 3]),
        "primary_paths": g.pick([[], ["docs/system-design.md"], None, "p"]),
    }


def _dispatch_start(g: Generator, line_no: int) -> Raw:
    return {
        "responding_to": g.pick(
            [[], [0], [1], [line_no - 1], [line_no + 3], None, "x", [True], [1, "a"]]
        )
    }


def _build_pass(g: Generator, _line_no: int) -> Raw:
    return {
        "gate_checks_run": g.pick([["fmt", "test"], [], None, "x", [1, None]]),
        "duration_seconds": g.pick([1, None, "x"]),
    }


def _build_failure(g: Generator, _line_no: int) -> Raw:
    return {
        "retry": g.pick([1, 2, 3, None, "2", True]),
        "failed_check": g.pick(["unit", None, 4]),
        "abort_reason": g.pick(
            [
                None,
                None,
                "wrong-shape-slice",
                "design-mismatch",
                "prd-mismatch",
                "prerequisite-missing",
                "odd",
                5,
            ]
        ),
        "partial": g.pick([True, False, None, "y"]),
    }


def _review_feedback(g: Generator, _line_no: int) -> Raw:
    return {
        "verdict": g.pick(VERDICTS),
        "findings": g.pick(
            [
                [],
                [g.finding()],
                [g.finding(), g.finding()],
                None,
                "x",
                [g.finding()] * 3,
            ]
        ),
        "recommendations": g.pick([None, [], ["r"], ["", 3], "x"]),
    }


def _review_plan(g: Generator, _line_no: int) -> Raw:
    return {
        "risk": g.pick(["low", "high", "gray", None, 4]),
        "roster": g.pick([None, [], ["code-quality-reviewer"], ["nobody"], "x"]),
        "scope": g.pick(["surface", "full-diff", None]),
    }


def _grader_verdict(g: Generator, _line_no: int) -> Raw:
    full = {
        "blast_radius": {"verdict": "skim", "note": "n"},
        "semantic_surprise": {"verdict": "scrutinize", "note": "m"},
        "test_adequacy": {"verdict": "skim", "note": ""},
        "reviewer_hedging": {"verdict": "skim", "note": "n"},
        "scope_deviation": {"verdict": "unknown", "note": "n"},
    }
    return {
        "verdict": g.pick(VERDICTS),
        "summary": g.pick(["ok", None, "s" * 100]),
        "rationale": g.pick([None, "because"]),
        "facets": g.pick(
            [
                None,
                {},
                {"blast_radius": {"verdict": "skim", "note": "n"}},
                {"blast_radius": "not-a-dict"},
                {"reviewer_hedging": {"verdict": ["x"], "note": 3}},
                "x",
                full,
            ]
        ),
    }


def _grader_features(g: Generator, _line_no: int) -> Raw:
    return {"features": g.pick([{}, None, "x"])}


def _consultation_request(g: Generator, _line_no: int) -> Raw:
    return {
        "target": g.pick([*AUTHORS, "Human", " human "]),
        "question": g.pick(["why?", None, "q" * 90]),
    }


def _consultation_response(g: Generator, line_no: int) -> Raw:
    return {
        "in_response_to": g.pick([1, 2, line_no - 1, 0, None, "1", [1], True]),
        "answer": g.pick(["ans", None, 4]),
        "memory_updates": g.pick(
            [
                None,
                [],
                [{"path": "docs/prd.md"}],
                [{"path": "docs/system-design.md"}],
                "x",
                [3],
            ]
        ),
    }


def _intake_decision(g: Generator, _line_no: int) -> Raw:
    return {
        "request": g.pick(["do x", None, "r" * 80]),
        "decisions": g.pick([["d1"], [], None, "x", [3]]),
    }


def _autofix(g: Generator, _line_no: int) -> Raw:
    return {
        "file": g.pick(["docs/prd.md", "docs/system-design.md", None, 3]),
        "category": g.pick(["structural", "writing-standards", None]),
    }


_FIELDS: dict[str, Callable[[Generator, int], Raw]] = {
    "prd-entry": _prd_entry,
    "design-block": _design_block,
    "dispatch-start": _dispatch_start,
    "build-pass": _build_pass,
    "build-failure": _build_failure,
    "review-feedback": _review_feedback,
    "review-plan": _review_plan,
    "grader-verdict": _grader_verdict,
    "grader-features": _grader_features,
    "consultation-request": _consultation_request,
    "consultation-response": _consultation_response,
    "intake-decision": _intake_decision,
    "design-doc-autofix": _autofix,
    "prd-autofix": _autofix,
}


def compare_ledger(
    generator: Generator, index: int, trees: differential.Trees, scratch: Path
) -> list[differential.Difference]:
    """Run every command on one synthetic ledger through both trees and collect the differences."""
    text = generator.ledger()
    log = scratch / "handoff.jsonl"
    log.write_text(text, encoding="utf-8", newline="")
    layout = scratch / "layout.toml"
    found: list[differential.Difference] = []
    for command in READ_COMMANDS:
        argv = [*command, "--file", str(log), "--layout", str(layout)]
        difference = differential.compare(
            f"ledger {index} {' '.join(command)}", trees, argv
        )
        if difference is not None:
            found.append(difference)
    record_type, stdin = generator.candidate()
    outcomes: list[tuple[differential.Outcome, str | None]] = []
    for tree, tag in zip(trees, ("baseline", "candidate"), strict=True):
        copy = scratch / f"{tag}.jsonl"
        copy.write_text(text, encoding="utf-8", newline="")
        argv = ["append", record_type, "--file", str(copy), "--layout", str(layout)]
        outcome = differential.run_handoff(tree, argv, stdin)
        body = differential.normalize(_raw_text(copy)) if copy.exists() else None
        outcomes.append((outcome, body))
    if outcomes[0] != outcomes[1]:
        found.append(
            differential.Difference(
                f"ledger {index} append {record_type}", outcomes[0][0], outcomes[1][0]
            )
        )
    return found


def _raw_text(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def main(argv: list[str]) -> int:
    """Fuzz both trees and print every difference; exit 1 when any exists."""
    parser = argparse.ArgumentParser(description="differential fuzz of handoff.py")
    parser.add_argument(
        "--baseline", required=True, help="a checkout to compare against"
    )
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--count", type=int, default=DEFAULT_COUNT, help="ledgers to generate"
    )
    args = parser.parse_args(argv[1:])
    try:
        baseline = differential.resolve_tree(args.baseline)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    generator = Generator(args.seed)
    trees = differential.Trees(baseline, ROOT)
    differences = 0
    with tempfile.TemporaryDirectory() as scratch:
        for index in range(args.count):
            for difference in compare_ledger(generator, index, trees, Path(scratch)):
                differences += 1
                print(differential.report(difference))
    print(f"seed {args.seed}: {args.count} ledgers, {differences} differences")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
