"""The grading application's own composition: the review-plan basis the engine records."""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
_SCHEMAS = _HERE.parent / "schemas" / "scratch"


def _load():
    """Load grading.py under a name that keeps its `from grading.…` imports on the package."""
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

SOME_REQ_ID = "REQ-XX-001"
SOME_TS = "2026-09-09T00:00:00Z"
SOME_TREE = "a" * 40
A_PROD_FILE = "src/a.txt"
SOME_LINES = 3
SOME_HUNKS = 2
HOST_PATHS = (
    "/Users/someone/repo/src/a.txt",
    "C:\\repo\\src\\a.txt",
    "../outside/a.txt",
    "src/../../a.txt",
    "src/a\nb.txt",
)
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


def a_features(**overrides):
    return {
        "files": [
            {"path": A_PROD_FILE, "kind": "prod", "module": "src", "sensitive": False}
        ],
        "prod_lines": SOME_LINES,
        "test_lines": SOME_LINES,
        "hunks": SOME_HUNKS,
        "module_count": 1,
        "security_surface_paths": [],
        **overrides,
    }


def a_review_plan_record(basis):
    return {
        "type": "review-plan",
        "req_id": SOME_REQ_ID,
        "ts": SOME_TS,
        "author": "review-plan-engine",
        "risk": "gray",
        "scope": "full-diff",
        "basis": basis,
        "rationale": "small clean production change; planner judges the roster",
    }


class PlanBasisSecuritySurface(unittest.TestCase):
    """The basis carries the probe's result on every plan, so the planner reads the fact instead of re-deriving it."""

    def _basis(self, features, review=_REVIEW):
        inputs = PlanInputs(features, _HISTORY, _CTX, _LAYOUT, review, SOME_TREE)
        return grading.plan_basis(inputs, _PLAN)

    def test_declared_probe_with_no_hit_records_an_empty_list(self):
        surface = self._basis(a_features())["security_surface"]
        self.assertEqual(surface, {"declared": True, "paths": []})

    def test_probe_hits_ride_through(self):
        surface = self._basis(a_features(security_surface_paths=[A_PROD_FILE]))[
            "security_surface"
        ]
        self.assertEqual(surface, {"declared": True, "paths": [A_PROD_FILE]})

    def test_undeclared_probe_reads_declared_false(self):
        review = replace(_REVIEW, security_surface=())
        surface = self._basis(a_features(), review)["security_surface"]
        self.assertEqual(surface, {"declared": False, "paths": []})

    def test_unreadable_diff_keeps_paths_null(self):
        # A null probe result is a hit for the planner: the field never
        # collapses None into an empty list.
        surface = self._basis(a_features(security_surface_paths=None))[
            "security_surface"
        ]
        self.assertEqual(surface, {"declared": True, "paths": None})

    def test_basis_validates_against_the_shipped_schema(self):
        record = a_review_plan_record(self._basis(a_features()))
        loaded = schema.load_schema(str(_SCHEMAS), "review-plan")
        self.assertEqual(schema.validate_record(record, loaded), [])
        bad = dict(record, basis={**record["basis"], "security_surface": {"paths": []}})
        self.assertTrue(schema.validate_record(bad, loaded))

    def test_schema_rejects_a_host_path_in_the_surface(self):
        # The ledger is published: a path is repo-relative as the change set
        # names it, never a host path, and the schema pins that at append time.
        loaded = schema.load_schema(str(_SCHEMAS), "review-plan")
        for leaked in HOST_PATHS:
            with self.subTest(path=leaked):
                basis = self._basis(a_features(security_surface_paths=[leaked]))
                self.assertTrue(
                    schema.validate_record(a_review_plan_record(basis), loaded)
                )
        relative = self._basis(a_features(security_surface_paths=[A_PROD_FILE]))
        self.assertEqual(
            schema.validate_record(a_review_plan_record(relative), loaded), []
        )


class BrokenLayoutFailsLoud(unittest.TestCase):
    """An install whose layout does not parse as the engine needs, beside a copy of the entry."""

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
        # A committed head with no base is an argument fault on its own; the
        # install fault must win over it.
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
