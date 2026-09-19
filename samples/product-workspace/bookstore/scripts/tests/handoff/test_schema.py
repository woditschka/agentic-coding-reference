#!/usr/bin/env python3
"""The byte contract: strict parsing, the schema subset, layout sourcing, and canonical form."""

import datetime
import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from handoff import (
    LogEntry,
    SchemaError,
    canonicalize,
    dumps_canonical,
    load_schema,
    loads_strict,
    log_schema_errors,
    only_missing_log,
    parse_log,
    parse_log_lenient,
    read_layout,
    resolve_ref,
    sanitize,
    schema as schema_module,
    ts_now,
    unsupported_keywords,
    validate_record,
    with_layout_sources,
)

from tests.support import (
    _REPO_SCHEMAS,
    BAD_SCHEMA,
    BADTYPE_SCHEMA,
    BOOLSUB_SCHEMA,
    ENUMFROM_SCHEMA,
    NUM_SCHEMA,
    PATTERNFROM_SCHEMA,
    REF_SCHEMA,
    SOME_REQ_ID,
    SOME_TS,
    STRICT_SCHEMA,
    TEST_SCHEMA,
    TUPLE_SCHEMA,
    a_record,
)

A_DECLARED_EXTRA_REVIEWER = "perf-reviewer"
SOME_LINE_POINTER = 3
RETRY_MIN = TEST_SCHEMA["properties"]["retry"]["minimum"]
RETRY_MAX = TEST_SCHEMA["properties"]["retry"]["maximum"]
NESTING_PAST_THE_INTERPRETER_LIMIT = 1_000_000
AN_OVERSIZED_NOTE = "x" * 1_000_000


class StrictParsing(unittest.TestCase):
    def test_a_top_level_duplicate_key_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            loads_strict('{"req_id": "REQ-A-001", "req_id": "REQ-A-002"}')

        self.assertIn('duplicate key: "req_id"', str(caught.exception))

    def test_a_nested_duplicate_key_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            loads_strict('{"features": {"hunks": 1, "hunks": 2}}')

        self.assertIn('duplicate key: "hunks"', str(caught.exception))

    def test_nan_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            loads_strict('{"x": NaN}')

        self.assertIn("NaN is not valid JSON", str(caught.exception))

    def test_distinct_keys_parse_as_written(self):
        line = (
            '{"type": "build-pass", "req_id": "REQ-A-001", "nested": {"x": 1, "y": 2}}'
        )

        self.assertEqual(
            loads_strict(line),
            {"type": "build-pass", "req_id": "REQ-A-001", "nested": {"x": 1, "y": 2}},
        )


class LogParsing(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log = Path(tmp.name) / "handoff.jsonl"

    def write(self, text):
        self.log.write_text(text, encoding="utf-8", newline="")

    def parse(self):
        return parse_log(str(self.log))

    def test_a_missing_log_is_one_error_and_no_entries(self):
        self.assertEqual(self.parse(), ([], [f"no handoff log at {self.log}"]))

    def test_an_empty_log_has_no_entries_and_no_errors(self):
        self.write("")

        self.assertEqual(self.parse(), ([], []))

    def test_a_single_line_yields_one_numbered_entry(self):
        record = a_record()
        self.write(json.dumps(record) + "\n")

        self.assertEqual(self.parse(), ([LogEntry(1, record)], []))

    def test_a_missing_trailing_newline_is_reported_on_the_last_line(self):
        self.write(json.dumps(a_record()))

        entries, errors = self.parse()

        self.assertEqual(errors, ["line 1: missing trailing newline"])
        self.assertEqual(len(entries), 1)

    def test_a_blank_line_is_an_error_and_later_lines_still_parse(self):
        line = json.dumps(a_record())
        self.write(line + "\n\n" + line + "\n")

        entries, errors = self.parse()

        self.assertEqual(errors, ["line 2: blank line"])
        self.assertEqual([no for no, _ in entries], [1, 3])

    def test_glued_records_are_invalid_json(self):
        line = json.dumps(a_record())
        self.write(line + line + "\n")

        _, errors = self.parse()

        self.assertTrue(errors[0].startswith("line 1: invalid JSON"))

    def test_a_non_object_line_is_an_error(self):
        self.write("[1, 2]\n")

        self.assertEqual(self.parse(), ([], ["line 1: not a JSON object"]))

    def test_a_non_utf8_log_is_one_error(self):
        self.log.write_bytes(b"\xff\n")

        _, errors = self.parse()

        self.assertTrue(errors[0].startswith("log is not valid UTF-8"))

    def test_a_directory_at_the_log_path_cannot_be_read(self):
        self.log.mkdir()

        _, errors = self.parse()

        self.assertTrue(errors[0].startswith(f"cannot read {self.log}"))

    def test_a_crlf_line_ending_still_parses(self):
        self.write(json.dumps(a_record()) + "\r\n")

        entries, errors = self.parse()

        self.assertEqual((len(entries), errors), (1, []))

    def test_unicode_line_separators_stay_inside_one_record(self):
        note = "a\u2028b\u2029c\u0085d"
        self.write(json.dumps(a_record(note=note), ensure_ascii=False) + "\n")

        entries, errors = self.parse()

        self.assertEqual(errors, [])
        self.assertEqual(entries[0].raw["note"], note)

    def test_a_deeply_nested_line_is_an_error_not_a_recursion_traceback(self):
        depth = NESTING_PAST_THE_INTERPRETER_LIMIT
        self.write("[" * depth + "]" * depth + "\n")

        self.assertEqual(
            self.parse(), ([], ["line 1: invalid JSON (nesting too deep)"])
        )


class LogParsingLenient(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.log = Path(tmp.name) / "handoff.jsonl"

    def parse(self, *lines):
        self.log.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
        return parse_log_lenient(str(self.log))

    def test_parseable_objects_keep_their_line_numbers(self):
        record = a_record()

        self.assertEqual(
            self.parse(json.dumps(record), "garbage", json.dumps(record)),
            [LogEntry(1, record), LogEntry(3, record)],
        )

    def test_a_non_object_line_is_skipped(self):
        self.assertEqual(self.parse("[1, 2]", '"text"'), [])

    def test_a_duplicate_key_line_is_skipped(self):
        self.assertEqual(self.parse('{"type": "a", "type": "b"}'), [])

    def test_a_missing_log_is_empty(self):
        self.assertEqual(parse_log_lenient(str(self.log)), [])


class OnlyMissingLog(unittest.TestCase):
    def test_no_errors_read_as_only_missing(self):
        self.assertTrue(only_missing_log([]))

    def test_the_missing_message_alone_reads_as_only_missing(self):
        self.assertTrue(only_missing_log(["no handoff log at x"]))

    def test_any_other_error_does_not_read_as_only_missing(self):
        self.assertFalse(
            only_missing_log(["no handoff log at x", "line 1: invalid JSON"])
        )


class RecordValidation(unittest.TestCase):
    def errors(self, record, schema=TEST_SCHEMA):
        return validate_record(record, schema)

    def test_a_valid_record_has_no_violations(self):
        self.assertEqual(self.errors(a_record()), [])

    def test_a_missing_required_field_is_named(self):
        record = a_record()
        del record["author"]

        self.assertEqual(self.errors(record), ["$: missing required field 'author'"])

    def test_an_enum_violation_names_the_value(self):
        (error,) = self.errors(a_record(author="impostor"))

        self.assertIn('"impostor" not in enum', error)

    def test_a_pattern_violation_names_the_pattern(self):
        (error,) = self.errors(a_record(req_id="REQ-1"))

        self.assertIn("does not match pattern", error)

    def test_a_bad_date_time_fails_the_format(self):
        (error,) = self.errors(a_record(ts="yesterday"))

        self.assertIn("is not an ISO 8601 date-time", error)

    def test_an_integer_below_the_minimum_is_a_violation(self):
        below = RETRY_MIN - 1

        self.assertEqual(
            self.errors(a_record(retry=below)),
            [f"$.retry: {below} below minimum {RETRY_MIN}"],
        )

    def test_an_integer_above_the_maximum_is_a_violation(self):
        above = RETRY_MAX + 1

        self.assertEqual(
            self.errors(a_record(retry=above)),
            [f"$.retry: {above} above maximum {RETRY_MAX}"],
        )

    def test_an_empty_array_fails_min_items(self):
        self.assertEqual(
            self.errors(a_record(tags=[])), ["$.tags: fewer than minItems 1"]
        )

    def test_a_string_shorter_than_min_length_is_a_violation(self):
        self.assertEqual(
            self.errors(a_record(note="")), ["$.note: shorter than minLength 1"]
        )

    def test_a_nested_object_is_checked_against_its_subschema(self):
        self.assertEqual(
            self.errors(a_record(nested={"aye": "a"})),
            ["$.nested: missing required field 'zee'"],
        )

    def test_an_unexpected_field_is_named_when_additional_properties_is_false(self):
        (error,) = self.errors({"type": "strict-rec", "x": 1}, STRICT_SCHEMA)

        self.assertIn("unexpected field 'x'", error)

    def test_a_reference_resolves_to_its_definition(self):
        self.assertEqual(
            self.errors({"type": "ref-rec", "facet": "skim"}, REF_SCHEMA), []
        )

    def test_a_value_outside_a_referenced_enum_is_a_violation(self):
        (error,) = self.errors({"type": "ref-rec", "facet": "nope"}, REF_SCHEMA)

        self.assertIn("not in enum", error)

    def test_a_boolean_never_satisfies_a_numeric_enum(self):
        (error,) = self.errors({"type": "num-rec", "n": True}, NUM_SCHEMA)

        self.assertIn("not in enum", error)

    def test_an_integer_never_satisfies_a_boolean_const(self):
        (error,) = self.errors({"type": "num-rec", "flag": 1}, NUM_SCHEMA)

        self.assertIn("expected const true", error)

    def test_matching_numeric_and_boolean_values_pass(self):
        self.assertEqual(
            self.errors({"type": "num-rec", "n": 1, "flag": True}, NUM_SCHEMA), []
        )

    def test_an_unsupported_keyword_stops_the_check(self):
        (error,) = self.errors({"type": "bad-rec"}, BAD_SCHEMA)

        self.assertIn("unsupported keyword at #/properties/x/anyOf", error)

    def test_an_unknown_type_name_is_a_schema_error(self):
        (error,) = self.errors({"type": "badtype-rec", "x": "y"}, BADTYPE_SCHEMA)

        self.assertIn("schema: unknown type ['strin']", error)

    def test_a_boolean_subschema_is_an_unsupported_form(self):
        (error,) = self.errors({"type": "boolsub-rec"}, BOOLSUB_SCHEMA)

        self.assertIn("unsupported schema form", error)

    def test_tuple_form_items_is_an_unsupported_form(self):
        (error,) = self.errors({"type": "tuple-rec", "x": ["a"]}, TUPLE_SCHEMA)

        self.assertIn("unsupported schema form", error)

    def test_a_non_string_pattern_is_reported_as_an_invalid_pattern(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string", "pattern": ["x"]}},
        }

        (error,) = self.errors({"a": "v"}, schema)

        self.assertIn("is not a valid regex", error)

    def test_a_broken_regex_pattern_is_reported_not_raised(self):
        schema = {
            "type": "object",
            "properties": {"a": {"type": "string", "pattern": "("}},
        }

        (error,) = self.errors({"a": "v"}, schema)

        self.assertIn("is not a valid regex", error)


class ReferenceResolution(unittest.TestCase):
    def test_a_plain_schema_resolves_to_itself(self):
        schema = {"type": "string"}

        self.assertIs(resolve_ref(schema, {}), schema)

    def test_a_reference_outside_definitions_is_a_schema_error(self):
        with self.assertRaises(SchemaError) as caught:
            resolve_ref({"$ref": "#/foo"}, {})

        self.assertIn("unsupported $ref", str(caught.exception))

    def test_a_reference_without_a_definition_is_a_schema_error(self):
        with self.assertRaises(SchemaError) as caught:
            resolve_ref({"$ref": "#/definitions/x"}, {"definitions": {}})

        self.assertIn("has no matching definition", str(caught.exception))

    def test_a_reference_cycle_past_the_hop_cap_is_a_schema_error(self):
        root = {
            "definitions": {
                "a": {"$ref": "#/definitions/b"},
                "b": {"$ref": "#/definitions/a"},
            }
        }

        with self.assertRaises(SchemaError) as caught:
            resolve_ref({"$ref": "#/definitions/a"}, root)

        self.assertIn("$ref chain too deep", str(caught.exception))


class SchemaDirectoryCase(unittest.TestCase):
    """A schema directory holding the test schema, written per test."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.schemas = Path(tmp.name)
        self.write("test-rec", json.dumps(TEST_SCHEMA))

    def write(self, record_type, text):
        (self.schemas / f"{record_type}.schema.json").write_text(text)


class SchemaLoading(SchemaDirectoryCase):
    def load(self, record_type, layout=None):
        return load_schema(str(self.schemas), record_type, layout)

    def test_a_known_type_loads_its_schema(self):
        self.assertEqual(self.load("test-rec"), TEST_SCHEMA)

    def test_a_missing_type_lists_the_known_types(self):
        with self.assertRaises(SchemaError) as caught:
            self.load("nope")

        self.assertIn("no schema for record type 'nope'", str(caught.exception))
        self.assertIn("known types: test-rec", str(caught.exception))

    def test_an_invalid_json_schema_file_is_a_schema_error(self):
        self.write("broken-rec", "{")

        with self.assertRaises(SchemaError) as caught:
            self.load("broken-rec")

        self.assertIn(
            "schema for 'broken-rec' is not valid JSON", str(caught.exception)
        )

    def test_a_non_object_schema_file_is_a_schema_error(self):
        self.write("list-rec", "[]")

        with self.assertRaises(SchemaError) as caught:
            self.load("list-rec")

        self.assertIn("is not a JSON object", str(caught.exception))

    def test_a_layout_pattern_is_applied_while_loading(self):
        self.write("pf-rec", json.dumps(PATTERNFROM_SCHEMA))

        schema = self.load("pf-rec", {"test_name_pattern": "^Test"})

        self.assertEqual(schema["properties"]["tname"]["pattern"], "^Test")


class LogSchemaErrors(SchemaDirectoryCase):
    def errors_of(self, *raws, layout=None):
        entries = [LogEntry(no, raw) for no, raw in enumerate(raws, 1)]
        return log_schema_errors(entries, str(self.schemas), layout or {})

    def test_a_valid_record_has_no_errors(self):
        self.assertEqual(self.errors_of(a_record()), [])

    def test_a_missing_type_discriminator_is_named_by_line(self):
        self.assertEqual(
            self.errors_of(a_record(), {"note": "x"}),
            ["line 2: missing 'type' discriminator"],
        )

    def test_an_unknown_type_carries_the_schema_error_by_line(self):
        errors = self.errors_of({"type": "mystery"})

        self.assertEqual(len(errors), 1)
        self.assertTrue(
            errors[0].startswith("line 1: no schema for record type 'mystery'")
        )

    def test_a_violation_carries_its_line(self):
        errors = self.errors_of(a_record(), a_record(retry=RETRY_MAX + 1))

        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("line 2: "))


class LayoutSourcing(unittest.TestCase):
    def test_pattern_from_resolves_a_dotted_layout_key(self):
        sourced = with_layout_sources({"patternFrom": "a.b"}, {"a": {"b": "^x"}})

        self.assertEqual(sourced, {"patternFrom": "a.b", "pattern": "^x"})

    def test_a_missing_layout_key_leaves_the_keyword_unset(self):
        sourced = with_layout_sources({"patternFrom": "a.b"}, {"other": "x"})

        self.assertNotIn("pattern", sourced)

    def test_an_existing_pattern_keeps_precedence_over_the_layout(self):
        sourced = with_layout_sources(
            {"pattern": "^y", "patternFrom": "k"}, {"k": "^x"}
        )

        self.assertEqual(sourced["pattern"], "^y")

    def test_enum_from_resolves_a_list_of_strings(self):
        sourced = with_layout_sources(
            ENUMFROM_SCHEMA, {"gate": {"verbs": ["build", "test"]}}
        )

        self.assertEqual(
            sourced["properties"]["verbs"]["items"]["enum"], ["build", "test"]
        )

    def test_enum_from_ignores_a_non_string_list(self):
        sourced = with_layout_sources(ENUMFROM_SCHEMA, {"gate": {"verbs": [1, 2]}})

        self.assertNotIn("enum", sourced["properties"]["verbs"]["items"])

    def test_enum_from_ignores_an_empty_list(self):
        sourced = with_layout_sources(ENUMFROM_SCHEMA, {"gate": {"verbs": []}})

        self.assertNotIn("enum", sourced["properties"]["verbs"]["items"])

    def test_sourcing_leaves_the_schema_untouched(self):
        schema = {"patternFrom": "k", "properties": {"a": {"enumFrom": "e"}}}
        before = json.dumps(schema)

        with_layout_sources(schema, {"k": "^x", "e": ["v"]})

        self.assertEqual(json.dumps(schema), before)


class LayoutReading(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.layout = Path(tmp.name) / "layout.toml"

    def test_a_missing_layout_is_empty(self):
        self.assertEqual(read_layout(str(self.layout)), {})

    def test_a_layout_parses_to_its_tables(self):
        self.layout.write_text('[gate]\nverbs = ["build"]\n')

        self.assertEqual(read_layout(str(self.layout)), {"gate": {"verbs": ["build"]}})

    def test_an_unparseable_layout_is_a_schema_error(self):
        self.layout.write_text("[gate\n")

        with self.assertRaises(SchemaError) as caught:
            read_layout(str(self.layout))

        self.assertIn("cannot be parsed", str(caught.exception))


class CanonicalForm(unittest.TestCase):
    def canonical(self, record, schema=TEST_SCHEMA):
        return canonicalize(record, schema, schema)

    def test_fields_follow_schema_declaration_order(self):
        shuffled = {
            "author": "tester",
            "note": "n",
            "type": "test-rec",
            "ts": SOME_TS,
            "req_id": SOME_REQ_ID,
        }

        self.assertEqual(
            list(self.canonical(shuffled)), ["type", "req_id", "ts", "author", "note"]
        )

    def test_unknown_fields_sort_last_alphabetically(self):
        ordered = self.canonical(a_record(zzz=1, aaa=2))

        self.assertEqual(list(ordered)[-2:], ["aaa", "zzz"])

    def test_a_nested_object_follows_its_subschema(self):
        ordered = self.canonical(a_record(nested={"aye": "a", "zee": "z"}))

        self.assertEqual(list(ordered["nested"]), ["zee", "aye"])

    def test_array_items_follow_the_items_schema(self):
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"properties": {"b": {}, "a": {}}}}
            },
        }

        ordered = canonicalize({"items": [{"a": 1, "b": 2}]}, schema, schema)

        self.assertEqual(list(ordered["items"][0]), ["b", "a"])

    def test_serialization_keeps_non_ascii_and_one_space_separators(self):
        self.assertEqual(
            dumps_canonical({"q": "Prüfung ✓", "n": 1}), '{"q": "Prüfung ✓", "n": 1}'
        )


class RealSchemas(unittest.TestCase):
    def test_every_repo_schema_stays_within_the_validator_subset(self):
        paths = sorted(_REPO_SCHEMAS.glob("*.schema.json"))
        self.assertTrue(paths, f"no schemas found at {_REPO_SCHEMAS}")
        for path in paths:
            with self.subTest(schema=path.name):
                self.assertEqual(unsupported_keywords(json.loads(path.read_text())), [])

    def test_the_dispatch_start_schema_accepts_a_declared_extra_reviewer(self):
        record = a_record(
            "dispatch-start",
            author=A_DECLARED_EXTRA_REVIEWER,
            responding_to=[SOME_LINE_POINTER],
        )

        errors = validate_record(
            record, load_schema(str(_REPO_SCHEMAS), "dispatch-start")
        )

        self.assertEqual(errors, [])

    def test_canonical_order_follows_the_dispatch_start_schema(self):
        schema = load_schema(str(_REPO_SCHEMAS), "dispatch-start")
        shuffled = {
            "responding_to": [SOME_LINE_POINTER],
            "author": "feature-implementer",
            "ts": SOME_TS,
            "req_id": SOME_REQ_ID,
            "type": "dispatch-start",
        }

        ordered = canonicalize(shuffled, schema, schema)

        self.assertEqual(
            list(ordered), ["type", "req_id", "ts", "author", "responding_to"]
        )


class Sanitizing(unittest.TestCase):
    def test_hidden_and_direction_control_characters_are_dropped(self):
        self.assertEqual(
            sanitize("a\u202eb\u200bc\u2066d\ufeffe\x1b[31mf"), "abcde[31mf"
        )

    def test_joiners_are_content_and_stay(self):
        self.assertEqual(
            sanitize("\U0001f468\u200d\U0001f4bb"), "\U0001f468\u200d\U0001f4bb"
        )

    def test_line_breaks_fold_to_one_space(self):
        self.assertEqual(sanitize("a\r\nb\tc"), "a b c")


class Clock(unittest.TestCase):
    def test_the_stamp_is_utc(self):
        parsed = datetime.datetime.fromisoformat(ts_now())

        self.assertEqual(parsed.utcoffset(), datetime.timedelta(0))

    def test_the_stamp_is_isoformat_with_offset_and_microseconds(self):
        fixed = datetime.datetime(2026, 7, 17, 12, 34, 56, 789012, tzinfo=datetime.UTC)
        with unittest.mock.patch.object(schema_module.datetime, "datetime") as clock:
            clock.now.return_value = fixed

            stamp = ts_now()

        self.assertEqual(stamp, "2026-07-17T12:34:56.789012+00:00")


if __name__ == "__main__":
    unittest.main()
