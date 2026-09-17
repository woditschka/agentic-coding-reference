#!/usr/bin/env python3
"""The autofix audit: allowlist bounds, content checks, supersession, coverage, and the audit assembly."""

import unittest

from handoff import (
    ADR_INDEX,
    AUTOFIX_CHAR_CAP,
    AUTOFIX_LINE_CAP,
    UNCOVERED_MESSAGE,
    AutofixAudit,
    Baseline,
    DesignDocAudit,
    audit_log,
    audited_autofix_lines,
    bound_errors,
    content_errors,
    covers_path,
    parse_record,
    record_covers,
    static_errors,
    uncovered_design_doc_paths,
    uncovered_paths,
)

from tests.support import A_DESIGN_DOC, SOME_TS, FakeRepository, a_record, entries

AN_ADR = "docs/adr/0001-x.md"
A_NON_GOAL_ADR = "docs/adr/2026-01-02-non-goal-x.md"
A_PRD = "docs/prd.md"
A_CODE_PATH = "src/x.py"
OTHER_SLICE = "REQ-OTHER-009"
FIX_TEXT = "new text"
BASELINE_SECONDS = 1_000.0
AT_BASELINE = "1970-01-01T00:16:40Z"
BEFORE_BASELINE = "1970-01-01T00:00:00Z"
AFTER_BASELINE = "1970-01-01T00:20:00Z"
NO_LINES: set[int] = set()
AN_OVERRIDE = {
    "non_goal_id": "NG-1",
    "owner_decision": "narrowed",
    "source": "dispatch",
}
LINES_OUTSIDE_THE_CAP = f"lines_changed outside the 1-{AUTOFIX_LINE_CAP} autofix cap"
CHARS_OUTSIDE_THE_CAP = f"chars_changed outside the 1-{AUTOFIX_CHAR_CAP} autofix cap"
A_MALFORMED_OVERRIDE = {"NG-1": "narrowed"}
FIX_MISMATCH = "new_content is not byte-identical to source_finding.fix"


def covered_note(count):
    return f"{count} dirty design-doc path(s) covered"


def an_autofix(record_type="design-doc-autofix", file=A_DESIGN_DOC, **fields):
    return a_record(
        record_type,
        **{
            "file": file,
            "category": "writing-standards",
            "source_finding": {
                "tag": "autofix",
                "location": f"{file}:1",
                "fix": FIX_TEXT,
            },
            "old_content": "old text",
            "new_content": FIX_TEXT,
            "lines_changed": 1,
            "chars_changed": len(FIX_TEXT),
            **fields,
        },
    )


def a_prd_autofix(**fields):
    return an_autofix("prd-autofix", **{"file": A_PRD, **fields})


def an_edit(old, new):
    return an_autofix(old_content=old, new_content=new, source_finding={"fix": new})


class BoundErrors(unittest.TestCase):
    def test_a_well_formed_design_doc_autofix_has_none(self):
        self.assertEqual(bound_errors(parse_record(an_autofix())), [])

    def test_a_well_formed_prd_autofix_has_none(self):
        self.assertEqual(bound_errors(parse_record(a_prd_autofix())), [])

    def test_a_design_doc_autofix_on_the_prd_is_ineligible(self):
        self.assertEqual(
            bound_errors(parse_record(an_autofix(file=A_PRD))),
            ["file is not an autofix-eligible design-doc path"],
        )

    def test_a_prd_autofix_on_a_design_doc_is_ineligible(self):
        self.assertEqual(
            bound_errors(parse_record(a_prd_autofix(file=A_DESIGN_DOC))),
            ["file is not the autofix-eligible PRD path (docs/prd.md)"],
        )

    def test_an_adr_is_an_eligible_design_doc(self):
        self.assertEqual(bound_errors(parse_record(an_autofix(file=AN_ADR))), [])

    def test_a_missing_file_is_ineligible(self):
        errors = bound_errors(parse_record(an_autofix(file=None)))

        self.assertEqual(errors, ["file is not an autofix-eligible design-doc path"])

    def test_a_non_string_file_is_ineligible(self):
        errors = bound_errors(parse_record(an_autofix(file=7)))

        self.assertEqual(errors, ["file is not an autofix-eligible design-doc path"])

    def test_a_category_outside_the_allowlist_is_reported(self):
        errors = bound_errors(parse_record(an_autofix(category="semantic")))

        self.assertEqual(errors, ["category is not autofix-eligible"])

    def test_the_line_cap_is_inclusive(self):
        self.assertEqual(
            bound_errors(parse_record(an_autofix(lines_changed=AUTOFIX_LINE_CAP))), []
        )
        self.assertEqual(
            bound_errors(parse_record(an_autofix(lines_changed=AUTOFIX_LINE_CAP + 1))),
            [LINES_OUTSIDE_THE_CAP],
        )

    def test_zero_lines_is_outside_the_cap(self):
        errors = bound_errors(parse_record(an_autofix(lines_changed=0)))

        self.assertEqual(errors, [LINES_OUTSIDE_THE_CAP])

    def test_a_string_line_count_is_outside_the_cap(self):
        errors = bound_errors(parse_record(an_autofix(lines_changed="1")))

        self.assertEqual(errors, [LINES_OUTSIDE_THE_CAP])

    def test_the_char_cap_is_inclusive(self):
        self.assertEqual(
            bound_errors(parse_record(an_autofix(chars_changed=AUTOFIX_CHAR_CAP))), []
        )
        self.assertEqual(
            bound_errors(parse_record(an_autofix(chars_changed=AUTOFIX_CHAR_CAP + 1))),
            [CHARS_OUTSIDE_THE_CAP],
        )

    def test_zero_chars_is_outside_the_cap(self):
        errors = bound_errors(parse_record(an_autofix(chars_changed=0)))

        self.assertEqual(errors, [CHARS_OUTSIDE_THE_CAP])

    def test_errors_are_listed_in_path_category_lines_chars_order(self):
        record = parse_record(
            an_autofix(file=A_PRD, category="x", lines_changed=0, chars_changed=0)
        )

        self.assertEqual(
            bound_errors(record),
            [
                "file is not an autofix-eligible design-doc path",
                "category is not autofix-eligible",
                LINES_OUTSIDE_THE_CAP,
                CHARS_OUTSIDE_THE_CAP,
            ],
        )


class ContentErrors(unittest.TestCase):
    def test_a_plain_reword_has_none(self):
        self.assertEqual(content_errors(parse_record(an_autofix())), [])

    def test_a_heading_line_is_structural(self):
        errors = content_errors(
            parse_record(an_edit("## Heading\nold", "## Heading\nnew"))
        )

        self.assertEqual(errors, ["content touches a '## ' heading line"])

    def test_a_non_goals_row_is_never_eligible_on_the_prd(self):
        raw = a_prd_autofix(
            old_content="| NG-4 | Deleting | Old |",
            new_content="| NG-4 | Deleting | New |",
            source_finding={"fix": "| NG-4 | Deleting | New |"},
        )

        errors = content_errors(parse_record(raw))

        self.assertEqual(len(errors), 1)
        self.assertIn("Non-Goals table row", errors[0])

    def test_a_non_goals_row_in_a_design_doc_is_not_the_prd_rule(self):
        errors = content_errors(
            parse_record(an_edit("| NG-4 | a | b |", "| NG-4 | a | c |"))
        )

        self.assertEqual(errors, [])

    def test_a_changed_anchor_id_is_reported(self):
        errors = content_errors(
            parse_record(an_edit('<a id="one"></a>', '<a id="two"></a>'))
        )

        self.assertEqual(
            errors, ["anchor ids differ between old_content and new_content"]
        )

    def test_a_changed_req_token_is_reported(self):
        errors = content_errors(parse_record(an_edit("see REQ-A-001", "see REQ-A-002")))

        self.assertEqual(
            errors, ["REQ-ID tokens differ between old_content and new_content"]
        )

    def test_a_code_fence_line_is_structural(self):
        errors = content_errors(parse_record(an_edit("```go\nx", "```go\ny")))

        self.assertEqual(errors, ["content touches a code-fence line"])

    def test_an_indented_code_fence_still_counts(self):
        errors = content_errors(parse_record(an_edit("  ```", "  ```")))

        self.assertEqual(errors, ["content touches a code-fence line"])

    def test_a_changed_link_target_is_reported(self):
        errors = content_errors(parse_record(an_edit("[a](x.md)", "[a](y.md)")))

        self.assertEqual(
            errors, ["markdown link targets differ between old_content and new_content"]
        )

    def test_a_reordered_reference_set_is_not_a_change(self):
        errors = content_errors(
            parse_record(an_edit("[a](x.md) [b](y.md)", "[b](y.md) [a](x.md)"))
        )

        self.assertEqual(errors, [])

    def test_new_content_must_equal_the_finding_fix(self):
        errors = content_errors(parse_record(an_autofix(new_content="paraphrased")))

        self.assertEqual(errors, [FIX_MISMATCH])

    def test_a_missing_source_finding_is_a_fix_mismatch(self):
        errors = content_errors(parse_record(an_autofix(source_finding=None)))

        self.assertEqual(errors, [FIX_MISMATCH])

    def test_non_string_contents_read_as_empty(self):
        raw = an_autofix(
            old_content=None, new_content=["x"], source_finding={"fix": ""}
        )

        self.assertEqual(content_errors(parse_record(raw)), [])

    def test_static_errors_join_bounds_and_content(self):
        record = parse_record(an_autofix(lines_changed=0, new_content="paraphrased"))

        self.assertEqual(
            static_errors(record),
            [LINES_OUTSIDE_THE_CAP, FIX_MISMATCH],
        )


class AuditedLines(unittest.TestCase):
    def test_every_open_autofix_is_audited(self):
        log = entries(an_autofix(), a_prd_autofix(), a_record("build-pass"))

        self.assertEqual(audited_autofix_lines(log), {1, 2})

    def test_a_design_block_closes_the_earlier_design_doc_autofixes_of_its_slice(self):
        log = entries(an_autofix(), a_record("design-block"), an_autofix())

        self.assertEqual(audited_autofix_lines(log), {3})

    def test_a_prd_entry_closes_the_earlier_prd_autofixes_of_its_slice(self):
        log = entries(a_prd_autofix(), a_record("prd-entry"), a_prd_autofix())

        self.assertEqual(audited_autofix_lines(log), {3})

    def test_a_prd_entry_does_not_close_design_doc_autofixes(self):
        log = entries(an_autofix(), a_record("prd-entry"))

        self.assertEqual(audited_autofix_lines(log), {1})

    def test_a_design_block_does_not_close_prd_autofixes(self):
        log = entries(a_prd_autofix(), a_record("design-block"))

        self.assertEqual(audited_autofix_lines(log), {1})

    def test_supersession_is_per_slice(self):
        log = entries(an_autofix(req_id=OTHER_SLICE), a_record("design-block"))

        self.assertEqual(audited_autofix_lines(log), {1})


class RecordCovers(unittest.TestCase):
    def test_an_autofix_covers_its_own_file(self):
        record = parse_record(an_autofix())

        self.assertTrue(record_covers(record, A_DESIGN_DOC))
        self.assertFalse(record_covers(record, AN_ADR))

    def test_a_design_block_covers_its_primary_and_supporting_paths(self):
        record = parse_record(
            a_record(
                "design-block", primary_paths=[A_CODE_PATH], supporting_paths=[AN_ADR]
            )
        )

        self.assertTrue(record_covers(record, A_CODE_PATH))
        self.assertTrue(record_covers(record, AN_ADR))
        self.assertFalse(record_covers(record, A_DESIGN_DOC))

    def test_a_design_block_with_non_list_paths_covers_nothing(self):
        record = parse_record(a_record("design-block", primary_paths=A_CODE_PATH))

        self.assertFalse(record_covers(record, A_CODE_PATH))

    def test_a_consultation_response_covers_its_memory_updates(self):
        record = parse_record(
            a_record(
                "consultation-response",
                memory_updates=[{"path": A_DESIGN_DOC, "summary": "row"}],
            )
        )

        self.assertTrue(record_covers(record, A_DESIGN_DOC))
        self.assertFalse(record_covers(record, AN_ADR))

    def test_a_scope_overriding_prd_entry_covers_only_a_non_goal_adr(self):
        record = parse_record(a_record("prd-entry", scope_overrides=[AN_OVERRIDE]))

        self.assertTrue(record_covers(record, A_NON_GOAL_ADR))
        self.assertFalse(record_covers(record, AN_ADR))

    def test_a_prd_entry_without_overrides_covers_nothing(self):
        record = parse_record(a_record("prd-entry", scope_overrides=[]))

        self.assertFalse(record_covers(record, A_NON_GOAL_ADR))

    def test_a_malformed_override_object_covers_nothing(self):
        record = parse_record(
            a_record("prd-entry", scope_overrides=A_MALFORMED_OVERRIDE)
        )

        self.assertFalse(record_covers(record, A_NON_GOAL_ADR))

    def test_other_records_cover_nothing(self):
        self.assertFalse(
            record_covers(parse_record(a_record("build-pass")), A_DESIGN_DOC)
        )


class CoversPath(unittest.TestCase):
    def entry_at(self, ts):
        return entries(an_autofix(ts=ts))[0]

    def test_without_a_baseline_any_covering_record_counts(self):
        self.assertTrue(covers_path(self.entry_at(SOME_TS), A_DESIGN_DOC, None))

    def test_a_record_newer_than_the_baseline_covers(self):
        self.assertTrue(
            covers_path(self.entry_at(AFTER_BASELINE), A_DESIGN_DOC, BASELINE_SECONDS)
        )

    def test_a_record_at_the_baseline_does_not_cover(self):
        self.assertFalse(
            covers_path(self.entry_at(AT_BASELINE), A_DESIGN_DOC, BASELINE_SECONDS)
        )

    def test_a_record_older_than_the_baseline_does_not_cover(self):
        self.assertFalse(
            covers_path(self.entry_at(BEFORE_BASELINE), A_DESIGN_DOC, BASELINE_SECONDS)
        )

    def test_an_unparseable_timestamp_does_not_cover_under_a_baseline(self):
        self.assertFalse(
            covers_path(self.entry_at("yesterday"), A_DESIGN_DOC, BASELINE_SECONDS)
        )


class UncoveredPaths(unittest.TestCase):
    def uncovered(self, paths, *raws, audited=None):
        log = entries(*raws)
        lines = audited_autofix_lines(log) if audited is None else audited
        return uncovered_paths(paths, log, lines, None)

    def test_a_dirty_path_no_record_names_is_uncovered(self):
        self.assertEqual(
            self.uncovered([A_DESIGN_DOC], a_record("build-pass")), [A_DESIGN_DOC]
        )

    def test_a_covering_record_clears_its_path(self):
        self.assertEqual(self.uncovered([A_DESIGN_DOC], an_autofix()), [])

    def test_a_superseded_autofix_does_not_cover(self):
        self.assertEqual(
            self.uncovered(
                [A_DESIGN_DOC],
                an_autofix(),
                a_record("design-block", primary_paths=["docs/other.md"]),
            ),
            [A_DESIGN_DOC],
        )

    def test_the_adr_index_follows_its_covered_files(self):
        self.assertEqual(
            self.uncovered(
                [ADR_INDEX, AN_ADR], a_record("design-block", primary_paths=[AN_ADR])
            ),
            [],
        )

    def test_the_adr_index_follows_an_uncovered_file(self):
        self.assertEqual(
            self.uncovered([ADR_INDEX, AN_ADR], a_record("build-pass")),
            [AN_ADR, ADR_INDEX],
        )

    def test_the_adr_index_alone_is_the_finding(self):
        self.assertEqual(
            self.uncovered([ADR_INDEX], a_record("build-pass")), [ADR_INDEX]
        )

    def test_the_adr_index_is_covered_by_name(self):
        self.assertEqual(
            self.uncovered(
                [ADR_INDEX], a_record("design-block", primary_paths=[ADR_INDEX])
            ),
            [],
        )

    def test_uncovered_paths_are_sorted(self):
        self.assertEqual(
            self.uncovered([A_DESIGN_DOC, AN_ADR], a_record("build-pass")),
            [AN_ADR, A_DESIGN_DOC],
        )


class DesignDocCoverage(unittest.TestCase):
    def coverage(self, repository, *raws):
        log = entries(*raws)
        return uncovered_design_doc_paths(log, repository)

    def test_an_unborn_repository_notes_the_first_commit(self):
        self.assertEqual(
            self.coverage(FakeRepository(repo_state="unborn")),
            DesignDocAudit(
                (), "no commit yet — direct-edit detection starts at the first commit"
            ),
        )

    def test_no_repository_cannot_be_audited(self):
        self.assertIsNone(self.coverage(FakeRepository(repo_state="no-repo")))

    def test_an_unreadable_dirty_list_cannot_be_audited(self):
        self.assertIsNone(self.coverage(FakeRepository(dirty=None)))

    def test_an_unreadable_baseline_cannot_be_audited(self):
        repository = FakeRepository(dirty=(A_DESIGN_DOC,), baseline=Baseline(False))

        self.assertIsNone(self.coverage(repository))

    def test_a_clean_tree_needs_no_baseline(self):
        repository = FakeRepository(dirty=(), baseline=Baseline(False))

        self.assertEqual(self.coverage(repository), DesignDocAudit((), covered_note(0)))

    def test_a_covered_dirty_path_reports_the_count(self):
        dirty = (A_DESIGN_DOC,)

        audit = self.coverage(FakeRepository(dirty=dirty), an_autofix())

        self.assertEqual(audit, DesignDocAudit((), covered_note(len(dirty))))

    def test_an_uncovered_dirty_path_is_named(self):
        audit = self.coverage(
            FakeRepository(dirty=(A_DESIGN_DOC,)), a_record("build-pass")
        )

        self.assertEqual(audit.uncovered, (A_DESIGN_DOC,))

    def test_the_baseline_seconds_expire_older_records(self):
        repository = FakeRepository(
            dirty=(A_DESIGN_DOC,), baseline=Baseline(True, BASELINE_SECONDS)
        )

        audit = self.coverage(repository, an_autofix(ts=BEFORE_BASELINE))

        self.assertEqual(audit.uncovered, (A_DESIGN_DOC,))


class AuditLog(unittest.TestCase):
    def test_a_clean_log_and_tree_audit_clean(self):
        audit = audit_log(entries(an_autofix()), FakeRepository())

        self.assertEqual(audit, AutofixAudit((), 1, covered_note(0)))

    def test_static_failures_precede_coverage_failures_and_carry_their_line(self):
        log = entries(a_record("build-pass"), an_autofix(lines_changed=0))

        audit = audit_log(log, FakeRepository(dirty=(AN_ADR,)))

        self.assertEqual(
            audit.failures,
            (f"line 2: {LINES_OUTSIDE_THE_CAP}", f"{AN_ADR}: {UNCOVERED_MESSAGE}"),
        )

    def test_superseded_records_are_neither_validated_nor_counted(self):
        log = entries(an_autofix(lines_changed=0), a_record("design-block"))

        audit = audit_log(log, FakeRepository())

        self.assertEqual(audit, AutofixAudit((), 0, covered_note(0)))

    def test_an_unreadable_repository_keeps_the_static_failures_and_drops_the_note(
        self,
    ):
        audit = audit_log(
            entries(an_autofix(lines_changed=0)), FakeRepository(repo_state=None)
        )

        self.assertEqual(len(audit.failures), 1)
        self.assertIsNone(audit.note)


if __name__ == "__main__":
    unittest.main()
