"""Tests for the grading application's own composition: the review-plan
basis the engine records. The ladder itself is tested under grading/."""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent  # the scripts dir (tests live under it)
_SCHEMAS = _HERE.parent / "schemas" / "scratch"


def _load():
    """Load grading.py as "grading_entry" so `from grading.…` in it resolves to
    the installed package, not to the entry file being executed."""
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    spec = importlib.util.spec_from_file_location("grading_entry", _HERE / "grading.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["grading_entry"] = mod
    spec.loader.exec_module(mod)
    return mod


grading = _load()

from dataclasses import replace  # noqa: E402

from grading.config import REVIEWERS, Layout, validate_review  # noqa: E402
from grading.planner import Plan, PlanContext, PlanInputs  # noqa: E402
from handoff import schema  # noqa: E402


def _features(**overrides):
    base = {
        "files": [
            {"path": "src/a.txt", "kind": "prod", "module": "src", "sensitive": False}
        ],
        "prod_lines": 5,
        "test_lines": 3,
        "hunks": 2,
        "module_count": 1,
        "security_surface_paths": [],
    }
    base.update(overrides)
    return base


SOME_REQ_ID = "REQ-XX-001"
THE_LAYOUT_FAULT = (
    "layout.toml: test must be a list of non-empty strings (got 'not a list')"
)
_HISTORY = {"build_retries": 0, "design_revisions": 0, "consultations": 0}
_CTX = PlanContext("first")
_PLAN = Plan("low", (), "full-diff", "r", ())
_LAYOUT = Layout(
    test_globs=("**/*_test.txt", "*_test.txt"),
    prod_roots=("src/",),
    sensitive=("**/auth/**",),
    module_rules=(),
    extra_reviewers=(),
    review={},
    conventions={},
)
_REVIEW = validate_review(
    {"docs": ["docs/*"], "config": ["*.toml"], "security_surface": [r"@\w+Mapping\("]},
    REVIEWERS,
)


class PlanBasisSecuritySurface(unittest.TestCase):
    """The basis carries the probe's result on every plan (ADR 2026-09-07,
    amendment 2026-09-09) so the planner reads the fact the high-plan rule
    reads instead of re-deriving it."""

    def _basis(self, features, review=_REVIEW):
        inputs = PlanInputs(features, _HISTORY, _CTX, _LAYOUT, review, "a" * 40)
        return grading.plan_basis(inputs, _PLAN)

    def test_declared_probe_with_no_hit_records_an_empty_list(self):
        surface = self._basis(_features())["security_surface"]
        self.assertEqual(surface, {"declared": True, "paths": []})

    def test_probe_hits_ride_through(self):
        surface = self._basis(_features(security_surface_paths=["src/a.txt"]))[
            "security_surface"
        ]
        self.assertEqual(surface, {"declared": True, "paths": ["src/a.txt"]})

    def test_undeclared_probe_reads_declared_false(self):
        review = replace(_REVIEW, security_surface=())
        surface = self._basis(_features(), review)["security_surface"]
        self.assertEqual(surface, {"declared": False, "paths": []})

    def test_unreadable_diff_keeps_paths_null(self):
        # A null probe result is a hit for the planner: the field never
        # collapses None into an empty list.
        surface = self._basis(_features(security_surface_paths=None))[
            "security_surface"
        ]
        self.assertEqual(surface, {"declared": True, "paths": None})

    def test_basis_validates_against_the_shipped_schema(self):
        record = {
            "type": "review-plan",
            "req_id": "REQ-XX-001",
            "ts": "2026-09-09T00:00:00Z",
            "author": "review-plan-engine",
            "risk": "gray",
            "scope": "full-diff",
            "basis": self._basis(_features()),
            "rationale": "small clean production change; planner judges the roster",
        }
        loaded = schema.load_schema(str(_SCHEMAS), "review-plan")
        self.assertEqual(schema.validate_record(record, loaded), [])
        bad = dict(record, basis={**record["basis"], "security_surface": {"paths": []}})
        self.assertTrue(schema.validate_record(bad, loaded))

    def test_schema_rejects_a_host_path_in_the_surface(self):
        # The ledger is published: a path is repo-relative as the change set
        # names it, never a host path. The schema pins the invariant at
        # append time, ahead of the eval bench's leak gate.
        loaded = schema.load_schema(str(_SCHEMAS), "review-plan")
        for leaked in (
            "/Users/someone/repo/src/a.txt",
            "C:\\repo\\src\\a.txt",
            "../outside/a.txt",
            "src/../../a.txt",
            "src/a\nb.txt",
        ):
            with self.subTest(path=leaked):
                record = {
                    "type": "review-plan",
                    "req_id": "REQ-XX-001",
                    "ts": "2026-09-09T00:00:00Z",
                    "author": "review-plan-engine",
                    "risk": "gray",
                    "scope": "full-diff",
                    "basis": self._basis(_features(security_surface_paths=[leaked])),
                    "rationale": "small clean production change; planner judges the roster",
                }
                self.assertTrue(schema.validate_record(record, loaded))
        relative = self._basis(_features(security_surface_paths=["src/a.txt"]))
        self.assertEqual(
            schema.validate_record(
                {
                    "type": "review-plan",
                    "req_id": "REQ-XX-001",
                    "ts": "2026-09-09T00:00:00Z",
                    "author": "review-plan-engine",
                    "risk": "gray",
                    "scope": "full-diff",
                    "basis": relative,
                    "rationale": "small clean production change; planner judges the roster",
                },
                loaded,
            ),
            [],
        )


class BrokenLayoutFailsLoud(unittest.TestCase):
    """An install whose layout does not parse as the engine needs, beside a copy of the entry.

    The command also carries a committed head with no base, an argument fault
    on its own; the install fault must win.
    """

    def setUp(self):
        self.tree = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tree)
        scripts = self.tree / "scripts"
        shutil.copytree(
            _HERE,
            scripts,
            ignore=shutil.ignore_patterns("tests", "__pycache__", "layout*.toml"),
        )
        (scripts / "layout.toml").write_text('test = "not a list"\n', encoding="utf-8")
        self.entry = scripts / "grading.py"

    def _run(self, command):
        return subprocess.run(
            [
                sys.executable,
                "-B",
                str(self.entry),
                command,
                "--feature",
                SOME_REQ_ID,
                "--head",
                "HEAD",
            ],
            cwd=self.tree,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_extract_reports_one_line_and_appends_nothing(self):
        done = self._run("extract")

        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr.splitlines(), [f"extract: {THE_LAYOUT_FAULT}"])
        self.assertFalse((self.tree / ".scratch" / "handoff.jsonl").exists())

    def test_review_plan_reports_one_line_and_appends_nothing(self):
        done = self._run("review-plan")

        self.assertEqual(done.returncode, 1)
        self.assertEqual(done.stderr.splitlines(), [f"review-plan: {THE_LAYOUT_FAULT}"])
        self.assertFalse((self.tree / ".scratch" / "handoff.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
