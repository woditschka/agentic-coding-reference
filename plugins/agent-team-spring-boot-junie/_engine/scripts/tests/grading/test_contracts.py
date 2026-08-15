"""Tests for grading.contracts — the deterministic design-doc sync check.

Run (from the scripts dir): python3 -m unittest tests.grading.test_contracts
Stdlib only.
"""

import tempfile
import unittest
from pathlib import Path

from grading.contracts import check_contracts_sync


class TestContractsSync(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()

    def _write(self, name, text):
        (self.root / "docs" / name).write_text(text, encoding="utf-8")

    def test_id_in_both_docs_passes(self):
        self._write("prd.md", "… `[REQ-VET-003]` …")
        self._write("system-design.md", "| Vets | … | REQ-VET-003 |")
        self.assertEqual(check_contracts_sync("REQ-VET-003", self.root), [])

    def test_id_missing_from_design_doc_fails(self):
        self._write("prd.md", "`[REQ-VET-003]`")
        self._write("system-design.md", "| Vets | … | REQ-VET-001 |")
        failures = check_contracts_sync("REQ-VET-003", self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/system-design.md", failures[0])
        self.assertIn("Contracts", failures[0])

    def test_id_missing_from_prd_fails_too(self):
        self._write("prd.md", "no requirement here")
        self._write("system-design.md", "REQ-VET-003")
        failures = check_contracts_sync("REQ-VET-003", self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/prd.md", failures[0])

    def test_absent_design_brief_passes_vacuously(self):
        # An un-doctored or greenfield tree has nothing to sync against —
        # same convention as the gate's absent-log check.
        self._write("prd.md", "anything")
        self.assertEqual(check_contracts_sync("REQ-VET-003", self.root), [])

    def test_absent_prd_checks_only_the_design_doc(self):
        self._write("system-design.md", "REQ-VET-003")
        self.assertEqual(check_contracts_sync("REQ-VET-003", self.root), [])

    def test_malformed_req_id_fails_loud(self):
        self._write("system-design.md", "whatever")
        for bad in ("REQ-vet-3", "REQ-VET-003\n"):
            failures = check_contracts_sync(bad, self.root)
            self.assertEqual(len(failures), 1)
            self.assertIn("not a req_id", failures[0])

    def test_presence_needs_word_boundaries(self):
        # A longer id or slug containing the id as a prefix is not presence.
        self._write("prd.md", "REQ-VET-003")
        self._write("system-design.md", "REQ-VET-0031 and req-vet-003-old")
        failures = check_contracts_sync("REQ-VET-003", self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/system-design.md", failures[0])


if __name__ == "__main__":
    unittest.main()
