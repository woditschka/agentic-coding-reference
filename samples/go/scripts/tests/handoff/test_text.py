#!/usr/bin/env python3
"""Display text over str: gists, plurals, and clipped locations."""

import unittest

from handoff import (
    GIST_LIMIT,
    LOCATION_LIMIT,
    full_or_gist,
    gist,
    plural,
    short_location,
)

TEXT_AT_THE_LIMIT = "x" * GIST_LIMIT
TEXT_PAST_THE_LIMIT = "x" * (GIST_LIMIT + 1)
SOME_LIMIT = 5


class Gist(unittest.TestCase):
    def test_text_at_the_limit_is_not_clipped(self):
        self.assertEqual(gist(TEXT_AT_THE_LIMIT), TEXT_AT_THE_LIMIT)

    def test_text_past_the_limit_ends_in_an_ellipsis(self):
        self.assertEqual(gist(TEXT_PAST_THE_LIMIT), "x" * (GIST_LIMIT - 1) + "…")

    def test_whitespace_runs_collapse_to_one_space(self):
        self.assertEqual(gist("  a \n\t b  "), "a b")

    def test_a_custom_limit_applies(self):
        self.assertEqual(gist("abcdefgh", SOME_LIMIT), "abcd…")

    def test_a_non_string_is_empty(self):
        self.assertEqual(gist(None), "")


class FullOrGist(unittest.TestCase):
    def test_verbose_keeps_the_whole_text_stripped(self):
        self.assertEqual(
            full_or_gist(" " + TEXT_PAST_THE_LIMIT + " ", verbose=True),
            TEXT_PAST_THE_LIMIT,
        )

    def test_non_verbose_gists(self):
        self.assertEqual(
            full_or_gist(TEXT_PAST_THE_LIMIT, verbose=False),
            gist(TEXT_PAST_THE_LIMIT),
        )

    def test_verbose_with_a_non_string_is_empty(self):
        self.assertEqual(full_or_gist(7, verbose=True), "")


class Plural(unittest.TestCase):
    def test_one_keeps_the_singular(self):
        self.assertEqual(plural(1, "finding"), "1 finding")

    def test_many_add_an_s(self):
        self.assertEqual(plural(2, "finding"), "2 findings")

    def test_a_word_ending_in_s_adds_es(self):
        self.assertEqual(plural(2, "build-pass"), "2 build-passes")


class ShortLocation(unittest.TestCase):
    def test_a_directory_is_dropped(self):
        self.assertEqual(short_location("src/ingest/limiter.py:42"), "limiter.py:42")

    def test_a_parenthetical_is_dropped(self):
        self.assertEqual(short_location("limiter.py:42 (allow)"), "limiter.py:42")

    def test_the_limit_clips(self):
        self.assertEqual(short_location("a" * 50), "a" * LOCATION_LIMIT)

    def test_a_non_string_is_empty(self):
        self.assertEqual(short_location(7), "")


if __name__ == "__main__":
    unittest.main()
