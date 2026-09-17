#!/usr/bin/env python3
"""Review findings: the artifact owner, the owner split, the Gate 4 shape errors, and capped dissent."""

import unittest

from handoff import (
    DESIGNER,
    IMPLEMENTER,
    PRODUCT,
    Finding,
    carries_capped_dissent,
    escalate_count,
    finding_owner,
    finding_shape_errors,
    owner_split,
    raw_findings,
)

from tests.support import a_record, entries

SOME_LOCATION = "src/widget.py:12"
A_PRD_ROW = "docs/prd.md:40"
A_DESIGN_ROW = "docs/system-design.md:7"
AN_ADR = "docs/adr/2026-01-01-thing.md:3"


def a_finding(tag="autofix", location=SOME_LOCATION, **fields):
    return {"tag": tag, "location": location, "description": "d", **fields}


def lifted(**fields):
    return Finding(**{"tag": "blocked", "location": SOME_LOCATION, **fields})


def feedback_entry(verdict="changes_requested", findings=(), raw_findings=None):
    raw = a_record("review-feedback", verdict=verdict, findings=list(findings))
    if raw_findings is not None:
        raw["findings"] = raw_findings
    return entries(raw)[0]


def verdicts_of(*raws):
    return {
        f"reviewer-{no}": entry.record for no, entry in enumerate(entries(*raws), 1)
    }


class FindingOwner(unittest.TestCase):
    def test_a_code_location_belongs_to_the_implementer(self):
        self.assertEqual(finding_owner(lifted()), IMPLEMENTER)

    def test_a_prd_row_belongs_to_the_product_expert(self):
        self.assertEqual(finding_owner(lifted(location=A_PRD_ROW)), PRODUCT)

    def test_a_design_doc_row_belongs_to_the_designer(self):
        self.assertEqual(finding_owner(lifted(location=A_DESIGN_ROW)), DESIGNER)

    def test_an_adr_belongs_to_the_designer(self):
        self.assertEqual(finding_owner(lifted(location=AN_ADR)), DESIGNER)

    def test_a_doc_autofix_has_no_agent_owner(self):
        self.assertIsNone(finding_owner(lifted(location=A_PRD_ROW, tag="autofix")))
        self.assertIsNone(finding_owner(lifted(location=A_DESIGN_ROW, tag="autofix")))

    def test_a_missing_location_falls_to_the_implementer(self):
        self.assertEqual(finding_owner(lifted(location=None)), IMPLEMENTER)

    def test_the_owner_reads_only_the_path_before_the_colon(self):
        self.assertEqual(
            finding_owner(lifted(location="docs/prd.md:docs/system-design.md")),
            PRODUCT,
        )


class OwnerSplit(unittest.TestCase):
    def test_dissenting_findings_name_their_owners_once_each_in_record_order(self):
        dissent = a_record(
            "review-feedback",
            verdict="changes_requested",
            findings=[
                a_finding(location=A_PRD_ROW, tag="blocked"),
                a_finding(),
                a_finding(location=A_PRD_ROW, tag="blocked"),
            ],
        )
        verdicts = verdicts_of(dissent)

        split = owner_split(verdicts, verdicts)

        self.assertEqual(split.owners, (PRODUCT, IMPLEMENTER))
        self.assertEqual(split.root_autofix, 0)

    def test_doc_autofixes_are_counted_for_root_instead_of_owned(self):
        doc_autofixes = [a_finding(location=A_PRD_ROW), a_finding(location=AN_ADR)]
        dissent = a_record(
            "review-feedback", verdict="changes_requested", findings=doc_autofixes
        )
        verdicts = verdicts_of(dissent)

        split = owner_split(verdicts, verdicts)

        self.assertEqual(split.owners, ())
        self.assertEqual(split.root_autofix, len(doc_autofixes))

    def test_an_escalate_finding_on_an_approved_record_joins_the_split(self):
        approved = a_record(
            "review-feedback",
            verdict="approved",
            findings=[a_finding(tag="escalate", location=A_DESIGN_ROW)],
        )
        verdicts = verdicts_of(approved)

        split = owner_split(verdicts, {})

        self.assertEqual(split.owners, (DESIGNER, IMPLEMENTER))

    def test_the_implementer_rides_a_doc_escalate_in_a_dissent(self):
        dissent = a_record(
            "review-feedback",
            verdict="changes_requested",
            findings=[a_finding(tag="escalate", location=A_PRD_ROW)],
        )
        verdicts = verdicts_of(dissent)

        self.assertEqual(owner_split(verdicts, verdicts).owners, (PRODUCT, IMPLEMENTER))

    def test_other_findings_on_an_approved_record_are_ignored(self):
        approved = a_record(
            "review-feedback", verdict="approved", findings=[a_finding(tag="clarify")]
        )
        verdicts = verdicts_of(approved)

        self.assertEqual(owner_split(verdicts, {}).owners, ())


class EscalateCount(unittest.TestCase):
    def test_escalate_tags_are_counted_across_every_verdict(self):
        approved_findings = [a_finding(tag="escalate"), a_finding()]
        dissent_findings = [a_finding(tag="escalate")]
        verdicts = verdicts_of(
            a_record("review-feedback", verdict="approved", findings=approved_findings),
            a_record(
                "review-feedback",
                verdict="changes_requested",
                findings=dissent_findings,
            ),
        )
        escalations = [
            f for f in approved_findings + dissent_findings if f["tag"] == "escalate"
        ]

        self.assertEqual(escalate_count(verdicts), len(escalations))


class RawFindings(unittest.TestCase):
    def test_a_list_is_returned_as_recorded(self):
        entry = feedback_entry(raw_findings=[a_finding(), "not an object"])

        self.assertEqual(raw_findings(entry), [a_finding(), "not an object"])

    def test_any_other_shape_reads_as_no_findings(self):
        self.assertEqual(raw_findings(feedback_entry(raw_findings="x")), [])
        self.assertEqual(raw_findings(entries(a_record("build-pass"))[0]), [])


class FindingShapeErrors(unittest.TestCase):
    def test_a_well_formed_dissent_has_no_errors(self):
        findings = [
            a_finding(severity="minor"),
            a_finding(tag="clarify", clarify_target="x"),
        ]
        entry = feedback_entry(findings=findings)

        self.assertEqual(finding_shape_errors(entry, findings), [])

    def test_a_clarify_finding_needs_a_target(self):
        findings = [a_finding(tag="clarify")]
        entry = feedback_entry(findings=findings)

        self.assertEqual(
            finding_shape_errors(entry, findings),
            ["finding 1 has tag 'clarify' but no clarify_target"],
        )

    def test_a_fix_routable_finding_needs_a_severity(self):
        findings = [a_finding(severity="minor"), a_finding(tag="blocked")]
        entry = feedback_entry(findings=findings)

        self.assertEqual(
            finding_shape_errors(entry, findings),
            ["finding 2 has tag 'blocked' but no severity"],
        )

    def test_a_fix_routable_finding_on_an_approved_verdict_is_an_error(self):
        findings = [a_finding(severity="minor")]
        entry = feedback_entry(verdict="approved", findings=findings)

        self.assertEqual(
            finding_shape_errors(entry, findings),
            [
                "finding 1 is tag 'autofix' on an approved verdict; "
                "record changes_requested or drop the finding"
            ],
        )

    def test_channel_findings_stay_valid_on_an_approved_verdict(self):
        findings = [a_finding(tag="escalate"), a_finding(tag="truncation")]
        entry = feedback_entry(verdict="approved", findings=findings)

        self.assertEqual(finding_shape_errors(entry, findings), [])

    def test_indexes_count_every_raw_item_and_skip_non_objects(self):
        findings = ["junk", a_finding(tag="clarify")]
        entry = feedback_entry(raw_findings=findings)

        self.assertEqual(
            finding_shape_errors(entry, findings),
            ["finding 2 has tag 'clarify' but no clarify_target"],
        )

    def test_a_non_feedback_entry_is_never_read_as_approved(self):
        findings = [a_finding(severity="minor")]
        entry = entries(a_record("build-pass"))[0]

        self.assertEqual(finding_shape_errors(entry, findings), [])

    def test_errors_group_by_kind_in_target_severity_verdict_order(self):
        findings = [a_finding(tag="blocked"), a_finding(tag="clarify")]
        entry = feedback_entry(verdict="approved", findings=findings)

        self.assertEqual(
            finding_shape_errors(entry, findings),
            [
                "finding 2 has tag 'clarify' but no clarify_target",
                "finding 1 has tag 'blocked' but no severity",
                "finding 1 is tag 'blocked' on an approved verdict; "
                "record changes_requested or drop the finding",
            ],
        )


class CarriesCappedDissent(unittest.TestCase):
    def test_a_critical_fix_routable_finding_carries_dissent(self):
        self.assertTrue(carries_capped_dissent([a_finding(severity="critical")]))
        self.assertTrue(
            carries_capped_dissent([a_finding(tag="blocked", severity="critical")])
        )

    def test_a_channel_finding_carries_dissent_without_a_severity(self):
        for tag in ("truncation", "clarify", "escalate"):
            with self.subTest(tag=tag):
                self.assertTrue(carries_capped_dissent([a_finding(tag=tag)]))

    def test_a_non_critical_fix_finding_carries_no_dissent(self):
        self.assertFalse(carries_capped_dissent([a_finding(severity="minor")]))

    def test_an_empty_list_or_non_object_items_carry_no_dissent(self):
        self.assertFalse(carries_capped_dissent([]))
        self.assertFalse(carries_capped_dissent(["critical"]))


if __name__ == "__main__":
    unittest.main()
