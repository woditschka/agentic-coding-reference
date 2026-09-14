#!/usr/bin/env python3
"""The typed record model: schema parity, the lenient lift, and record immutability."""

import dataclasses
import json
import keyword
import types
import typing
import unittest

from tests.support import (
    _REPO_SCHEMAS,
    GOLDEN_RECORDS,
    SOME_REQ_ID,
    SOME_TS,
    golden_record,
    handoff,
)


def _schema_name(field_name):
    """Map a field name to its schema property; a keyword field carries a trailing underscore."""
    stripped = field_name[:-1]
    if field_name.endswith("_") and keyword.iskeyword(stripped):
        return stripped
    return field_name


def _nested_dataclass(annotation):
    """Return the nested dataclass an annotation carries, or None for a scalar field."""
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
    """Return the object subschema a node maps a dataclass onto, or None for an opaque leaf."""
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


STACK_RECORDS = {
    "build-failure": {
        "type": "build-failure",
        "req_id": SOME_REQ_ID,
        "ts": SOME_TS,
        "author": "feature-implementer",
        "retry": 2,
        "failed_check": "test",
        "error_output": "assertion failed",
        "attempted": "added the guard clause",
    },
    "build-pass": {
        "type": "build-pass",
        "req_id": SOME_REQ_ID,
        "ts": SOME_TS,
        "author": "feature-implementer",
        "gate_checks_run": ["build", "test", "lint"],
    },
    "prd-entry": {
        "type": "prd-entry",
        "req_id": SOME_REQ_ID,
        "ts": SOME_TS,
        "author": "product-requirements-expert",
        "title": "Add the widget",
        "summary": "The widget does the thing.",
        "acceptance_criteria": ["it does the thing"],
        "file_targets": ["src/widget.py"],
        "test_names": ["TestWidgetDoesTheThing"],
    },
}


class SchemaDataclassParity(unittest.TestCase):
    """Every schema property has a field and every field a property, recursively."""

    def _assert_parity(self, schema_node, record_class, root, path):
        properties = schema_node.get("properties", {})
        field_names = {_schema_name(f.name) for f in dataclasses.fields(record_class)}
        self.assertEqual(
            field_names,
            set(properties),
            f"{path}: {record_class.__name__} field set does not match schema properties",
        )
        fields_by_property = {
            _schema_name(f.name): f for f in dataclasses.fields(record_class)
        }
        for name, subschema in properties.items():
            nested = _nested_dataclass(fields_by_property[name].type)
            structured = _structured_subschema(subschema, root)
            here = f"{path}.{name}"
            if structured is not None:
                self.assertIsNotNone(
                    nested,
                    f"{here}: schema is structured but the field is not a dataclass",
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
                record_type = schema["properties"]["type"]["const"]
                registered = handoff.RECORD_TYPES.get(record_type)
                self.assertIsNotNone(
                    registered, f"no record registered for '{record_type}'"
                )
                self._assert_parity(schema, registered.cls, schema, "#")


class ParseRecordRoundTrip(unittest.TestCase):
    def test_all_core_types_carry_the_common_fields(self):
        for record_type, _, _ in GOLDEN_RECORDS:
            with self.subTest(record_type=record_type):
                raw = golden_record(record_type)
                parsed = handoff.parse_record(raw)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self.assertEqual(
                    (parsed.type, parsed.req_id, parsed.ts, parsed.author),
                    (record_type, raw["req_id"], SOME_TS, raw["author"]),
                )

    def test_all_stack_types_round_trip(self):
        for record_type, raw in STACK_RECORDS.items():
            with self.subTest(record_type=record_type):
                parsed = handoff.parse_record(raw)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self.assertEqual((parsed.type, parsed.ts), (record_type, SOME_TS))

    def test_a_consultation_response_lifts_its_memory_updates(self):
        parsed = handoff.parse_record(golden_record("consultation-response"))

        self.assertIsInstance(parsed, handoff.ConsultationResponse)
        self.assertEqual(
            parsed.memory_updates,
            (handoff.MemoryUpdate("docs/system-design.md", "Note adapter placement."),),
        )
        self.assertEqual(
            (parsed.in_response_to, parsed.notes), (1, "See the adapter ADR.")
        )

    def test_a_design_block_lifts_its_patterns(self):
        parsed = handoff.parse_record(golden_record("design-block"))

        self.assertIsInstance(parsed, handoff.DesignBlock)
        self.assertEqual(parsed.primary_paths, ("src/widget.py",))
        self.assertEqual(parsed.supporting_paths, ("tests/test_widget.py",))
        self.assertEqual(
            parsed.patterns,
            (handoff.Pattern("src/base.py:10", "Follow the base adapter."),),
        )

    def test_absent_optionals_resolve_to_their_defaults(self):
        parsed = handoff.parse_record(golden_record("design-block"))

        self.assertEqual(
            (parsed.risks, parsed.escalations, parsed.integration_points), ((), (), ())
        )
        self.assertIsNone(parsed.supersedes_record_at)
        self.assertIsNone(parsed.notes)

    def test_a_design_doc_autofix_lifts_its_source_finding(self):
        parsed = handoff.parse_record(golden_record("design-doc-autofix"))

        self.assertIsInstance(parsed, handoff.DesignDocAutofix)
        self.assertIsInstance(parsed.source_finding, handoff.SourceFinding)
        self.assertEqual(parsed.source_finding.review_feedback_author, "doc-reviewer")
        self.assertEqual(parsed.source_finding.fix, "The adapter owns serialization.")
        self.assertEqual((parsed.lines_changed, parsed.chars_changed), (1, 20))

    def test_a_prd_autofix_lifts_its_source_finding(self):
        parsed = handoff.parse_record(golden_record("prd-autofix"))

        self.assertIsInstance(parsed, handoff.PrdAutofix)
        self.assertIsInstance(parsed.source_finding, handoff.SourceFinding)
        self.assertEqual(parsed.file, "docs/prd.md")
        self.assertEqual((parsed.lines_changed, parsed.chars_changed), (1, 6))

    def test_a_grader_verdict_lifts_its_named_facets(self):
        parsed = handoff.parse_record(golden_record("grader-verdict"))

        self.assertIsInstance(parsed, handoff.GraderVerdict)
        self.assertEqual(
            parsed.facets.blast_radius, handoff.Facet("skim", "One module touched.")
        )
        self.assertEqual(parsed.facets.scope_deviation.note, "Matches the slice.")
        self.assertEqual((parsed.responding_to, parsed.verdict), ((1,), "skim"))

    def test_grader_features_lift_nested_and_nullable_fields(self):
        parsed = handoff.parse_record(golden_record("grader-features"))

        self.assertIsInstance(parsed.features, handoff.Features)
        self.assertEqual(parsed.features.test_prod_ratio, 1.5)
        self.assertIs(parsed.features.build_passed, True)
        self.assertIsNone(parsed.features.reviewers)

    def test_an_absent_nullable_array_stays_none_rather_than_empty(self):
        parsed = handoff.parse_record(golden_record("grader-features"))

        self.assertIsNone(parsed.features.files)
        self.assertIsNone(parsed.features.review_roster)

    def test_a_review_plan_bridges_the_pass_keyword(self):
        parsed = handoff.parse_record(golden_record("review-plan"))

        self.assertIsInstance(parsed.basis, handoff.PlanBasis)
        self.assertEqual(
            (parsed.basis.pass_, parsed.basis.tree_sha), ("first", "a" * 40)
        )
        self.assertIsNone(parsed.basis.prev_tree_sha)
        self.assertEqual(parsed.roster, ("code-quality-reviewer", "test-reviewer"))

    def test_a_review_plan_basis_lifts_the_security_surface(self):
        raw = golden_record("review-plan")
        raw["basis"] = {
            **raw["basis"],
            "security_surface": {"declared": True, "paths": ["src/a.txt"]},
        }

        parsed = handoff.parse_record(raw)

        self.assertEqual(
            parsed.basis.security_surface, handoff.SecuritySurface(True, ("src/a.txt",))
        )

    def test_a_plan_without_a_security_surface_carries_none(self):
        parsed = handoff.parse_record(golden_record("review-plan"))

        self.assertIsNone(parsed.basis.security_surface)

    def test_review_feedback_lifts_findings_and_defaults(self):
        parsed = handoff.parse_record(golden_record("review-feedback"))

        self.assertIsInstance(parsed, handoff.ReviewFeedback)
        (finding,) = parsed.findings
        self.assertEqual(
            (finding.severity, finding.fix, finding.clarify_target),
            ("critical", None, None),
        )
        self.assertEqual((parsed.recommendations, parsed.approved_aspects), ((), ()))

    def test_a_build_failure_lifts_its_scalars(self):
        parsed = handoff.parse_record(STACK_RECORDS["build-failure"])

        self.assertIsInstance(parsed, handoff.BuildFailure)
        self.assertEqual(parsed.retry, 2)
        self.assertIsNone(parsed.partial)
        self.assertIsNone(parsed.abort_reason)

    def test_a_build_failure_lifts_its_abort_fields(self):
        parsed = handoff.parse_record(
            {
                **STACK_RECORDS["build-failure"],
                "partial": True,
                "abort_reason": "design-mismatch",
            }
        )

        self.assertIs(parsed.partial, True)
        self.assertEqual(parsed.abort_reason, "design-mismatch")

    def test_a_build_pass_lifts_its_gate_checks(self):
        parsed = handoff.parse_record(STACK_RECORDS["build-pass"])

        self.assertEqual(parsed.gate_checks_run, ("build", "test", "lint"))
        self.assertIsNone(parsed.duration_seconds)

    def test_a_build_pass_lifts_its_duration(self):
        parsed = handoff.parse_record(
            {**STACK_RECORDS["build-pass"], "duration_seconds": 12.5}
        )

        self.assertEqual(parsed.duration_seconds, 12.5)

    def test_a_prd_entry_lifts_arrays_and_defaults(self):
        parsed = handoff.parse_record(STACK_RECORDS["prd-entry"])

        self.assertIsInstance(parsed, handoff.PrdEntry)
        self.assertEqual(parsed.acceptance_criteria, ("it does the thing",))
        self.assertEqual(parsed.test_names, ("TestWidgetDoesTheThing",))
        self.assertEqual((parsed.non_goals, parsed.dependencies), ((), ()))
        self.assertIsNone(parsed.notes)

    def test_an_intake_decision_lifts_its_fields(self):
        parsed = handoff.parse_record(
            {
                "type": "intake-decision",
                "req_id": SOME_REQ_ID,
                "author": "human",
                "request": "add editing",
                "decisions": ["NG-5 is narrowed"],
                "source": "task-prompt",
            }
        )

        self.assertIsInstance(parsed, handoff.IntakeDecision)
        self.assertEqual(
            (parsed.request, parsed.decisions, parsed.source),
            ("add editing", ("NG-5 is narrowed",), "task-prompt"),
        )


class GoldenLiftsHaveNoHoles(unittest.TestCase):
    """Every key present in a schema-valid golden record lifts to a value, so a mapper typo is loud."""

    def _field(self, name):
        return f"{name}_" if keyword.iskeyword(name) else name

    def _assert_lifted(self, obj, data, path):
        for key, value in data.items():
            if value is None:
                continue
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
        for record_type, _, _ in GOLDEN_RECORDS:
            with self.subTest(schema=record_type):
                raw = golden_record(record_type)
                parsed = handoff.parse_record(raw)
                self.assertNotIsInstance(parsed, handoff.UnknownRecord)
                self._assert_lifted(parsed, raw, record_type)


class ParseRecordTotality(unittest.TestCase):
    """A known type always lifts to its class; anything else is an UnknownRecord; nothing raises."""

    def test_an_unknown_type_is_an_unknown_record_carrying_the_raw_object(self):
        raw = {"type": "no-such-type", "x": 1}

        parsed = handoff.parse_record(raw)

        self.assertIsInstance(parsed, handoff.UnknownRecord)
        self.assertEqual(parsed.raw, raw)

    def test_a_missing_type_is_an_unknown_record(self):
        self.assertIsInstance(handoff.parse_record({}), handoff.UnknownRecord)

    def test_a_non_string_type_is_an_unknown_record(self):
        self.assertIsInstance(handoff.parse_record({"type": 5}), handoff.UnknownRecord)

    def test_an_unhashable_type_is_an_unknown_record(self):
        self.assertIsInstance(
            handoff.parse_record({"type": ["dispatch-start"]}), handoff.UnknownRecord
        )

    def test_a_bare_known_type_lifts_to_its_class(self):
        for record_type, registered in handoff.RECORD_TYPES.items():
            with self.subTest(record_type=record_type):
                parsed = handoff.parse_record({"type": record_type})
                self.assertIsInstance(parsed, registered.cls)
                self.assertEqual(parsed.type, record_type)

    def test_a_known_type_missing_required_fields_lifts_with_none_holes(self):
        raw = golden_record("consultation-request")
        del raw["question"]
        del raw["target"]

        parsed = handoff.parse_record(raw)

        self.assertIsInstance(parsed, handoff.ConsultationRequest)
        self.assertEqual((parsed.question, parsed.target), (None, None))

    def test_a_scalar_in_a_nested_object_slot_leaves_a_none_hole(self):
        parsed = handoff.parse_record(
            {**golden_record("grader-verdict"), "facets": "nope"}
        )

        self.assertIsInstance(parsed, handoff.GraderVerdict)
        self.assertIsNone(parsed.facets)

    def test_a_non_object_item_in_an_object_array_is_skipped(self):
        parsed = handoff.parse_record(
            {**golden_record("consultation-response"), "memory_updates": [5]}
        )

        self.assertIsInstance(parsed, handoff.ConsultationResponse)
        self.assertEqual(parsed.memory_updates, ())

    def test_a_scalar_in_an_array_slot_leaves_an_empty_tuple(self):
        parsed = handoff.parse_record(
            {**golden_record("dispatch-start"), "responding_to": 3}
        )

        self.assertIsInstance(parsed, handoff.DispatchStart)
        self.assertEqual(parsed.responding_to, ())

    def test_arbitrary_objects_never_raise(self):
        specimens = [
            {},
            {"type": None},
            {"type": "design-block"},
            {"type": "review-plan", "basis": []},
            {"type": "grader-features", "features": 7},
            {"type": "prd-entry", "test_names": "notalist"},
            {"type": "build-pass", "gate_checks_run": None},
        ]
        for raw in specimens:
            with self.subTest(raw=raw):
                self.assertIsInstance(handoff.parse_record(raw), handoff.HandoffRecord)


class RecordsAreFrozen(unittest.TestCase):
    def test_assigning_to_a_record_field_raises(self):
        parsed = handoff.parse_record(golden_record("dispatch-start"))

        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.author = "someone-else"

    def test_assigning_to_a_nested_field_raises(self):
        parsed = handoff.parse_record(golden_record("review-feedback"))

        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.findings[0].tag = "autofix"

    def test_an_unknown_record_is_frozen(self):
        parsed = handoff.parse_record({"type": "no-such-type"})

        with self.assertRaises(dataclasses.FrozenInstanceError):
            parsed.raw = {}


if __name__ == "__main__":
    unittest.main(verbosity=2)
