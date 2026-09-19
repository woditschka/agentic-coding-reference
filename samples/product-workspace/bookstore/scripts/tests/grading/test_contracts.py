"""The deterministic design-doc sync check."""

import tempfile
import unittest
from pathlib import Path

from grading.contracts import check_contracts_sync

SOME_REQ_ID = "REQ-VET-003"
ANOTHER_REQ_ID = "REQ-VET-001"
A_LONGER_ID_WITH_THE_SAME_PREFIX = SOME_REQ_ID + "1"
A_SLUG_CONTAINING_THE_ID = SOME_REQ_ID.lower() + "-old"


class ContractsSync(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()

    def _write(self, name, text):
        (self.root / "docs" / name).write_text(text, encoding="utf-8")

    def test_id_in_both_docs_passes(self):
        self._write("prd.md", f"… `[{SOME_REQ_ID}]` …")
        self._write("system-design.md", f"| Vets | … | {SOME_REQ_ID} |")
        self.assertEqual(check_contracts_sync(SOME_REQ_ID, self.root), [])

    def test_id_missing_from_design_doc_fails(self):
        self._write("prd.md", f"`[{SOME_REQ_ID}]`")
        self._write("system-design.md", f"| Vets | … | {ANOTHER_REQ_ID} |")
        failures = check_contracts_sync(SOME_REQ_ID, self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/system-design.md", failures[0])
        self.assertIn("Contracts", failures[0])

    def test_id_missing_from_prd_fails_too(self):
        self._write("prd.md", "no requirement here")
        self._write("system-design.md", SOME_REQ_ID)
        failures = check_contracts_sync(SOME_REQ_ID, self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/prd.md", failures[0])

    def test_absent_design_brief_passes_vacuously(self):
        # An un-doctored or greenfield tree has nothing to sync against.
        self._write("prd.md", "anything")
        self.assertEqual(check_contracts_sync(SOME_REQ_ID, self.root), [])

    def test_absent_prd_checks_only_the_design_doc(self):
        self._write("system-design.md", SOME_REQ_ID)
        self.assertEqual(check_contracts_sync(SOME_REQ_ID, self.root), [])

    def test_a_malformed_req_id_fails_loud(self):
        self._write("system-design.md", "whatever")
        for bad in ("REQ-vet-3", SOME_REQ_ID + "\n"):
            with self.subTest(req_id=bad):
                failures = check_contracts_sync(bad, self.root)
                self.assertEqual(len(failures), 1)
                self.assertIn("not a req_id", failures[0])

    def test_an_id_embedded_in_a_longer_token_is_not_presence(self):
        self._write("prd.md", SOME_REQ_ID)
        self._write(
            "system-design.md",
            f"{A_LONGER_ID_WITH_THE_SAME_PREFIX} and {A_SLUG_CONTAINING_THE_ID}",
        )
        failures = check_contracts_sync(SOME_REQ_ID, self.root)
        self.assertEqual(len(failures), 1)
        self.assertIn("docs/system-design.md", failures[0])


if __name__ == "__main__":
    unittest.main()
