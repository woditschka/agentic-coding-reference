"""Tests for the grading application's own composition: the review-plan
basis the engine records. The ladder itself is tested under grading/."""

import importlib.util
import sys
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

from types import SimpleNamespace  # noqa: E402

from grading import config  # noqa: E402  (sys.path is set by _load)
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


_HISTORY = {"build_retries": 0, "design_revisions": 0, "consultations": 0}
_CTX = {"pass": "first", "prev_tree_sha": None}
_RESULT = {"open_findings": None, "triggers": []}
_CFG = {
    "docs": ["docs/*"],
    "config": ["*.toml"],
    "security_surface": [r"@\w+Mapping\("],
    "surface_reviewers": {},
    "size_threshold": 80,
    "mode": "risk",
}


class TestPlanBasisSecuritySurface(unittest.TestCase):
    """The basis carries the probe's result on every plan (ADR 2026-09-07,
    amendment 2026-09-09) so the planner reads the fact the high-plan rule
    reads instead of re-deriving it."""

    def setUp(self):
        # Inject a synthetic layout so the per-file classification never
        # reads a real scripts/layout.toml (the ladder tests do the same).
        self._saved = config.layout
        config.layout = SimpleNamespace(
            TEST=["**/*_test.txt", "*_test.txt"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        self.addCleanup(lambda: setattr(config, "layout", self._saved))

    def _basis(self, features, cfg=_CFG):
        return grading.plan_basis(features, _HISTORY, _CTX, _RESULT, cfg, "a" * 40)

    def test_declared_probe_with_no_hit_records_an_empty_list(self):
        surface = self._basis(_features())["security_surface"]
        self.assertEqual(surface, {"declared": True, "paths": []})

    def test_probe_hits_ride_through(self):
        surface = self._basis(_features(security_surface_paths=["src/a.txt"]))[
            "security_surface"
        ]
        self.assertEqual(surface, {"declared": True, "paths": ["src/a.txt"]})

    def test_undeclared_probe_reads_declared_false(self):
        cfg = dict(_CFG, security_surface=[])
        surface = self._basis(_features(), cfg)["security_surface"]
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


if __name__ == "__main__":
    unittest.main()
