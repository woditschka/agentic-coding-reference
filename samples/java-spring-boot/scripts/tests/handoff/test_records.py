#!/usr/bin/env python3
"""Typed-record-model suite: schema<->dataclass parity, parse_record
round-trips, lenient-lift totality, and record immutability — handoff.records
(ADR 2026-07-17 runtime-package-layout)."""

import dataclasses
import json
import keyword
import types
import typing
import unittest

from tests import test_handoff
from tests.support import (
    _REPO_SCHEMAS,
    REQ,
    TS,
    handoff,
)


def _schema_name(field_name):
    """Map a dataclass field name to its schema property name. `pass` is a
    Python keyword, so the field is `pass_`; strip the trailing underscore only
    when the stripped name is a keyword, never for an ordinary field."""
    stripped = field_name[:-1]
    if field_name.endswith("_") and keyword.iskeyword(stripped):
        return stripped
    return field_name


def _nested_dataclass(annotation):
    """The nested dataclass an annotation carries, unwrapping `X | None` and
    `tuple[X, ...]`, or None for a leaf/scalar field."""
    origin = typing.get_origin(annotation)
    if origin in (types.UnionType, typing.Union):
        for arg in typing.get_args(annotation):
            found = _nested_dataclass(arg)
            if found is not None:
                return found
        return None
    if origin is tuple:
        args = typing.get_args(annotation)
        return _nested_dataclass(args[0]) if args else None
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return annotation
    return None


def _structured_subschema(node, root):
    """If a schema node maps to a nested dataclass, return that subschema (the
    object itself, or an array's item object); else None. A structured node is
    an object carrying `properties`, or an array whose items are such an object.
    Objects without `properties` (grader-features reviewers/churn, review-plan
    basis size/history) are opaque leaves — a dict field, not a dataclass."""
    resolved = handoff.resolve_ref(node, root)
    if not isinstance(resolved, dict):
        return None
    if "properties" in resolved:
        return resolved
    items = resolved.get("items")
    if isinstance(items, dict):
        item = handoff.resolve_ref(items, root)
        if isinstance(item, dict) and "properties" in item:
            return item
    return None


class TestSchemaDataclassParity(unittest.TestCase):
    """The ADR 2026-07-17 drift gate between schemas/scratch/ and the typed model.

    For every schema file present in the tree this runs in (core carries the
    nine core types; a materialized sample adds the three stack types), walk the
    schema's properties — recursing into object subschemas and array-item
    subschemas — and assert the corresponding dataclass's field set matches
    exactly. A schema property with no field, or a field with no property, fails
    and names the path. Mirrors the real-schema sweep's subset guard: absent
    stack schemas are simply not walked here, present ones are."""

    def _assert_parity(self, schema_node, dc, root, path):
        props = schema_node.get("properties", {})
        field_names = {_schema_name(f.name) for f in dataclasses.fields(dc)}
        self.assertEqual(
            field_names,
            set(props),
            f"{path}: {dc.__name__} field set does not match schema properties",
        )
        fields_by_prop = {_schema_name(f.name): f for f in dataclasses.fields(dc)}
        for pname, subschema in props.items():
            fld = fields_by_prop[pname]
            nested = _nested_dataclass(fld.type)
            structured = _structured_subschema(subschema, root)
            here = f"{path}.{pname}"
            if structured is not None:
                self.assertIsNotNone(
                    nested,
                    f"{here}: schema is structured but the field carries no nested dataclass",
                )
                self._assert_parity(structured, nested, root, here)
            else:
                self.assertIsNone(
                    nested,
                    f"{here}: field carries a nested dataclass but the schema is a leaf",
                )

    def test_every_schema_matches_its_dataclass(self):
        paths = sorted(_REPO_SCHEMAS.glob("*.schema.json"))
        self.assertTrue(paths, f"no schemas found at {_REPO_SCHEMAS}")
        for path in paths:
            with self.subTest(schema=path.name):
                schema = json.loads(path.read_text())
                rtype = schema["properties"]["type"]["const"]
                dc = handoff._RECORD_TYPES.get(rtype)
                self.assertIsNotNone(dc, f"no dataclass registered for '{rtype}'")
                self._assert_parity(schema, dc, schema, "#")

    def test_registry_and_mappers_cover_the_same_types(self):
        self.assertEqual(set(handoff._RECORD_TYPES), set(handoff._MAPPERS))


# Representative full dicts (ts included) per record type, for parse_record
# round-trips. The nine core types reuse the golden fixtures; the three stack
# types (schemas absent in core) carry their own, so round-trips run fully here.
def _core_records():
    return {
        rtype: {**record, "ts": TS}
        for rtype, record, _ in test_handoff.TestGoldenCanonicalBytes.GOLDEN
    }


_STACK_RECORDS = {
    "build-failure": {
        "type": "build-failure",
        "req_id": REQ,
        "ts": TS,
        "author": "feature-implementer",
        "retry": 2,
        "failed_check": "test",
        "error_output": "assertion failed",
        "attempted": "added the guard clause",
    },
    "build-pass": {
        "type": "build-pass",
        "req_id": REQ,
        "ts": TS,
        "author": "feature-implementer",
        "gate_checks_run": ["build", "test", "lint"],
    },
    "prd-entry": {
        "type": "prd-entry",
        "req_id": REQ,
        "ts": TS,
        "author": "product-requirements-expert",
        "title": "Add the widget",
        "summary": "The widget does the thing.",
        "acceptance_criteria": ["it does the thing"],
        "file_targets": ["src/widget.py"],
        "test_names": ["TestWidgetDoesTheThing"],
    },
}


class TestParseRecordRoundTrip(unittest.TestCase):
    def test_all_core_types_carry_the_common_fields(self):
        for rtype, rec in _core_records().items():
            with self.subTest(rtype=rtype):
                parsed = handoff.parse_record(rec)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self.assertEqual(parsed.type, rtype)
                self.assertEqual(parsed.req_id, rec["req_id"])
                self.assertEqual(parsed.ts, TS)
                self.assertEqual(parsed.author, rec["author"])

    def test_all_stack_types_round_trip(self):
        for rtype, rec in _STACK_RECORDS.items():
            with self.subTest(rtype=rtype):
                parsed = handoff.parse_record(rec)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self.assertEqual(parsed.type, rtype)
                self.assertEqual(parsed.ts, TS)

    def test_consultation_response_lifts_memory_updates(self):
        parsed = handoff.parse_record(_core_records()["consultation-response"])
        self.assertIsInstance(parsed, handoff.ConsultationResponse)
        self.assertEqual(len(parsed.memory_updates), 1)
        mu = parsed.memory_updates[0]
        self.assertIsInstance(mu, handoff.MemoryUpdate)
        self.assertEqual(mu.path, "docs/system-design.md")
        self.assertEqual(mu.summary, "Note adapter placement.")
        self.assertEqual(parsed.in_response_to, 1)
        self.assertEqual(parsed.notes, "See the adapter ADR.")

    def test_design_block_lifts_patterns_and_defaults(self):
        parsed = handoff.parse_record(_core_records()["design-block"])
        self.assertIsInstance(parsed, handoff.DesignBlock)
        self.assertEqual(parsed.primary_paths, ("src/widget.py",))
        self.assertEqual(parsed.supporting_paths, ("tests/test_widget.py",))
        self.assertEqual(len(parsed.patterns), 1)
        self.assertIsInstance(parsed.patterns[0], handoff.Pattern)
        self.assertEqual(parsed.patterns[0].ref, "src/base.py:10")
        # Absent optionals resolve to their () / None defaults.
        self.assertEqual(parsed.risks, ())
        self.assertEqual(parsed.escalations, ())
        self.assertEqual(parsed.integration_points, ())
        self.assertIsNone(parsed.supersedes_record_at)
        self.assertIsNone(parsed.notes)

    def test_design_doc_autofix_lifts_source_finding(self):
        parsed = handoff.parse_record(_core_records()["design-doc-autofix"])
        self.assertIsInstance(parsed, handoff.DesignDocAutofix)
        self.assertIsInstance(parsed.source_finding, handoff.SourceFinding)
        self.assertEqual(parsed.source_finding.review_feedback_author, "doc-reviewer")
        self.assertEqual(parsed.source_finding.fix, "The adapter owns serialization.")
        self.assertEqual(parsed.lines_changed, 1)
        self.assertEqual(parsed.chars_changed, 20)

    def test_prd_autofix_lifts_source_finding(self):
        parsed = handoff.parse_record(_core_records()["prd-autofix"])
        self.assertIsInstance(parsed, handoff.PrdAutofix)
        self.assertIsInstance(parsed.source_finding, handoff.SourceFinding)
        self.assertEqual(parsed.source_finding.review_feedback_author, "doc-reviewer")
        self.assertEqual(parsed.file, "docs/prd.md")
        self.assertEqual(parsed.lines_changed, 1)
        self.assertEqual(parsed.chars_changed, 6)

    def test_grader_verdict_lifts_named_facets(self):
        parsed = handoff.parse_record(_core_records()["grader-verdict"])
        self.assertIsInstance(parsed, handoff.GraderVerdict)
        self.assertIsInstance(parsed.facets, handoff.Facets)
        self.assertIsInstance(parsed.facets.blast_radius, handoff.Facet)
        self.assertEqual(parsed.facets.blast_radius.verdict, "clear")
        self.assertEqual(parsed.facets.scope_deviation.note, "Matches the slice.")
        self.assertEqual(parsed.responding_to, (1,))
        self.assertEqual(parsed.verdict, "clear")

    def test_grader_features_lifts_nested_and_nullable(self):
        parsed = handoff.parse_record(_core_records()["grader-features"])
        self.assertIsInstance(parsed, handoff.GraderFeatures)
        self.assertIsInstance(parsed.features, handoff.Features)
        self.assertEqual(parsed.features.test_prod_ratio, 1.5)
        self.assertIs(parsed.features.build_passed, True)
        self.assertIsNone(parsed.features.reviewers)
        # Absent nullable arrays default to None, not ().
        self.assertIsNone(parsed.features.files)
        self.assertIsNone(parsed.features.review_roster)

    def test_review_plan_bridges_pass_keyword(self):
        parsed = handoff.parse_record(_core_records()["review-plan"])
        self.assertIsInstance(parsed, handoff.ReviewPlan)
        self.assertIsInstance(parsed.basis, handoff.PlanBasis)
        self.assertEqual(parsed.basis.pass_, "first")
        self.assertEqual(parsed.basis.tree_sha, "a" * 40)
        self.assertIsNone(parsed.basis.prev_tree_sha)
        self.assertIsNone(parsed.basis.files)
        self.assertEqual(parsed.roster, ("code-quality-reviewer", "test-reviewer"))

    def test_review_feedback_lifts_findings_and_defaults(self):
        parsed = handoff.parse_record(_core_records()["review-feedback"])
        self.assertIsInstance(parsed, handoff.ReviewFeedback)
        self.assertEqual(len(parsed.findings), 1)
        finding = parsed.findings[0]
        self.assertIsInstance(finding, handoff.Finding)
        self.assertEqual(finding.severity, "critical")
        self.assertIsNone(finding.fix)
        self.assertIsNone(finding.clarify_target)
        self.assertEqual(parsed.recommendations, ())
        self.assertEqual(parsed.approved_aspects, ())

    def test_dispatch_start_lifts_responding_to(self):
        parsed = handoff.parse_record(_core_records()["dispatch-start"])
        self.assertIsInstance(parsed, handoff.DispatchStart)
        self.assertEqual(parsed.responding_to, (0,))

    def test_consultation_request_optional_absent_is_none(self):
        rec = dict(_core_records()["consultation-request"])
        del rec["stop_state"]
        parsed = handoff.parse_record(rec)
        self.assertIsInstance(parsed, handoff.ConsultationRequest)
        self.assertIsNone(parsed.stop_state)

    def test_build_failure_optionals_present_and_absent(self):
        absent = handoff.parse_record(_STACK_RECORDS["build-failure"])
        self.assertIsInstance(absent, handoff.BuildFailure)
        self.assertEqual(absent.retry, 2)
        self.assertIsNone(absent.partial)
        self.assertIsNone(absent.abort_reason)
        present = handoff.parse_record(
            {
                **_STACK_RECORDS["build-failure"],
                "partial": True,
                "abort_reason": "design-mismatch",
            }
        )
        self.assertIs(present.partial, True)
        self.assertEqual(present.abort_reason, "design-mismatch")

    def test_build_pass_gate_checks_and_optional(self):
        parsed = handoff.parse_record(_STACK_RECORDS["build-pass"])
        self.assertEqual(parsed.gate_checks_run, ("build", "test", "lint"))
        self.assertIsNone(parsed.duration_seconds)
        with_dur = handoff.parse_record(
            {**_STACK_RECORDS["build-pass"], "duration_seconds": 12.5}
        )
        self.assertEqual(with_dur.duration_seconds, 12.5)

    def test_prd_entry_arrays_and_defaults(self):
        parsed = handoff.parse_record(_STACK_RECORDS["prd-entry"])
        self.assertIsInstance(parsed, handoff.PrdEntry)
        self.assertEqual(parsed.acceptance_criteria, ("it does the thing",))
        self.assertEqual(parsed.test_names, ("TestWidgetDoesTheThing",))
        self.assertEqual(parsed.non_goals, ())
        self.assertEqual(parsed.dependencies, ())
        self.assertIsNone(parsed.notes)


class TestGoldenLiftsHaveNoHoles(unittest.TestCase):
    """Mapper-typo tripwire. Under the lenient lift a misspelled .get key
    degrades to a silent None hole; this sweep makes it loud again: every key
    present in a schema-valid golden record lifts to a non-hole value."""

    def _field(self, name):
        return f"{name}_" if keyword.iskeyword(name) else name

    def _assert_lifted(self, obj, data, path):
        for key, value in data.items():
            if value is None:
                continue  # a raw null lifts to None by design, never a hole
            attr = getattr(obj, self._field(key))
            if isinstance(value, list) and value:
                self.assertNotEqual(len(attr), 0, f"{path}.{key} lifted empty")
                if isinstance(value[0], dict) and dataclasses.is_dataclass(attr[0]):
                    self._assert_lifted(attr[0], value[0], f"{path}.{key}[0]")
            elif isinstance(value, dict) and dataclasses.is_dataclass(attr):
                self._assert_lifted(attr, value, f"{path}.{key}")
            else:
                self.assertIsNotNone(attr, f"{path}.{key} lifted to None")

    def test_every_golden_key_lifts(self):
        for rtype, record, _ in test_handoff.TestGoldenCanonicalBytes.GOLDEN:
            with self.subTest(schema=rtype):
                full = {**record, "ts": TS}
                parsed = handoff.parse_record(full)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self._assert_lifted(parsed, full, rtype)


class TestParseRecordTotality(unittest.TestCase):
    """parse_record is total and lenient: a known "type" always lifts to its
    dataclass (absent fields become None / () holes); UnknownRecord is only for
    an unknown, missing, or non-string "type"; no dict ever raises."""

    def test_unknown_type_is_unknown_record(self):
        rec = {"type": "no-such-type", "x": 1}
        parsed = handoff.parse_record(rec)
        self.assertIsInstance(parsed, handoff.UnknownRecord)
        self.assertEqual(parsed.raw, rec)

    def test_missing_type_is_unknown_record(self):
        self.assertIsInstance(handoff.parse_record({}), handoff.UnknownRecord)

    def test_intake_decision_lifts_its_fields(self):
        parsed = handoff.parse_record(
            {
                "type": "intake-decision",
                "req_id": "REQ-A-001",
                "author": "human",
                "request": "add editing",
                "decisions": ["NG-5 is narrowed"],
                "source": "task-prompt",
            }
        )
        self.assertIsInstance(parsed, handoff.IntakeDecision)
        self.assertEqual(parsed.request, "add editing")
        self.assertEqual(parsed.decisions, ("NG-5 is narrowed",))
        self.assertEqual(parsed.source, "task-prompt")

    def test_non_string_type_is_unknown_record(self):
        # An int type, and an unhashable (list) type — neither may raise.
        self.assertIsInstance(handoff.parse_record({"type": 5}), handoff.UnknownRecord)
        self.assertIsInstance(
            handoff.parse_record({"type": ["dispatch-start"]}), handoff.UnknownRecord
        )

    def test_bare_known_type_lifts_to_its_class(self):
        # The total-per-type pin: {"type": t} alone returns t's dataclass for
        # every registered type — requiredness is the schema validator's job.
        for rtype, cls in handoff._RECORD_TYPES.items():
            with self.subTest(rtype=rtype):
                parsed = handoff.parse_record({"type": rtype})
                self.assertIsInstance(parsed, cls)
                self.assertEqual(parsed.type, rtype)

    def test_known_type_missing_required_fields_lifts_with_none_holes(self):
        # Was: missing required field -> UnknownRecord. Now inverted: a known
        # type always lifts to its dataclass, absent fields resolved to None.
        rec = dict(_core_records()["consultation-request"])
        del rec["question"]
        del rec["target"]
        parsed = handoff.parse_record(rec)
        self.assertIsInstance(parsed, handoff.ConsultationRequest)
        self.assertIsNone(parsed.question)
        self.assertIsNone(parsed.target)
        self.assertEqual(parsed.type, "consultation-request")

    def test_non_dict_where_object_expected_leaves_a_default_hole(self):
        # Was: a non-dict/non-list in a structured slot -> UnknownRecord. Now
        # inverted: the field takes its default (None for a nested object, ()
        # for an array), and the record still lifts to its dataclass.
        bad_facets = {**_core_records()["grader-verdict"], "facets": "nope"}
        gv = handoff.parse_record(bad_facets)
        self.assertIsInstance(gv, handoff.GraderVerdict)
        self.assertIsNone(gv.facets)
        # memory_updates carrying a non-dict item: the item is skipped.
        bad_mu = {**_core_records()["consultation-response"], "memory_updates": [5]}
        cr = handoff.parse_record(bad_mu)
        self.assertIsInstance(cr, handoff.ConsultationResponse)
        self.assertEqual(cr.memory_updates, ())
        # responding_to a scalar instead of a list: the array defaults to ().
        bad_rt = {**_core_records()["dispatch-start"], "responding_to": 3}
        ds = handoff.parse_record(bad_rt)
        self.assertIsInstance(ds, handoff.DispatchStart)
        self.assertEqual(ds.responding_to, ())

    def test_never_raises_on_arbitrary_dicts(self):
        specimens = [
            {},
            {"type": None},
            {"type": "design-block"},
            {"type": "review-plan", "basis": []},
            {"type": "grader-features", "features": 7},
            {"type": "prd-entry", "test_names": "notalist"},
            {"type": "build-pass", "gate_checks_run": None},
        ]
        for rec in specimens:
            with self.subTest(rec=rec):
                self.assertIsInstance(handoff.parse_record(rec), handoff.HandoffRecord)


class TestRecordFrozen(unittest.TestCase):
    def test_assigning_to_a_record_field_raises(self):
        parsed = handoff.parse_record(_core_records()["dispatch-start"])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.author = "someone-else"

    def test_assigning_to_a_nested_field_raises(self):
        parsed = handoff.parse_record(_core_records()["review-feedback"])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.findings[0].tag = "autofix"

    def test_unknown_record_is_frozen(self):
        parsed = handoff.parse_record({"type": "no-such-type"})
        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.raw = {}


if __name__ == "__main__":
    unittest.main(verbosity=2)
