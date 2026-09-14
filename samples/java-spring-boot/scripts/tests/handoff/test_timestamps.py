#!/usr/bin/env python3
"""Ledger timestamps: ISO-8601 to seconds, the clock face, and elapsed time."""

import unittest

from handoff import (
    SECONDS_PER_HOUR,
    SECONDS_PER_MINUTE,
    elapsed,
    format_duration,
    hhmm_of,
    parse_iso_seconds,
    seconds_of,
)

NOON_UTC = "2026-07-06T12:00:00+00:00"
NOON_BARE = "2026-07-06T12:00:00"
NOON_Z = "2026-07-06T12:00:00Z"
NOON_PLUS_TWO = "2026-07-06T12:00:00+02:00"


class IsoParsing(unittest.TestCase):
    def test_a_bare_timestamp_reads_as_utc(self):
        self.assertEqual(parse_iso_seconds(NOON_BARE), parse_iso_seconds(NOON_UTC))

    def test_a_z_suffix_reads_as_utc(self):
        self.assertEqual(parse_iso_seconds(NOON_Z), parse_iso_seconds(NOON_UTC))

    def test_a_lowercase_z_suffix_parses(self):
        self.assertEqual(
            parse_iso_seconds(NOON_Z.lower().replace("t", "T")),
            parse_iso_seconds(NOON_UTC),
        )

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(parse_iso_seconds(f"  {NOON_Z} "), parse_iso_seconds(NOON_UTC))

    def test_unparseable_text_is_none(self):
        self.assertIsNone(parse_iso_seconds("bogus"))


class SecondsOf(unittest.TestCase):
    def test_a_string_parses(self):
        self.assertEqual(seconds_of(NOON_Z), parse_iso_seconds(NOON_Z))

    def test_a_non_string_is_none(self):
        self.assertIsNone(seconds_of(12))


class ClockFace(unittest.TestCase):
    def test_a_full_timestamp_shows_its_hour_and_minute(self):
        self.assertEqual(hhmm_of("2026-07-06T13:32:00Z"), "13:32")

    def test_a_date_alone_has_no_clock_face(self):
        self.assertIsNone(hhmm_of("2026-07-06"))

    def test_a_value_without_the_t_separator_has_no_clock_face(self):
        self.assertIsNone(hhmm_of("2026-07-06 13:32:00"))

    def test_a_non_string_has_no_clock_face(self):
        self.assertIsNone(hhmm_of(None))


class Elapsed(unittest.TestCase):
    def test_under_a_minute_reads_in_seconds(self):
        self.assertEqual(elapsed(0, 45), "45s")

    def test_under_an_hour_reads_in_whole_minutes(self):
        self.assertEqual(elapsed(0, 15 * SECONDS_PER_MINUTE + 30), "15m")

    def test_an_hour_or_more_reads_in_hours_and_minutes(self):
        self.assertEqual(
            format_duration(SECONDS_PER_HOUR + 2 * SECONDS_PER_MINUTE), "1h 2m"
        )

    def test_an_end_before_its_start_is_untimed(self):
        self.assertIsNone(elapsed(10, 5))

    def test_a_missing_moment_is_untimed(self):
        self.assertIsNone(elapsed(None, 5))
        self.assertIsNone(elapsed(5, None))


if __name__ == "__main__":
    unittest.main()
