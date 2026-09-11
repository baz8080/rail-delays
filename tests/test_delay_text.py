"""Getting a notice down to its words, on notices the collector actually recorded.

The first class is the point of the file. Irish Rail ends almost every banner
with an apology that ends in the word "caused", and "caused by" is one of the
phrases that introduces a cause, so a reader that matches before the template is
stripped finds the inconvenience to be the cause of the delay.
"""

from __future__ import annotations

import unittest

from delay_cause import text

APOLOGY = "Iarnród Éireann Irish Rail apologise for any inconvenience caused."


class TheApologyIsTemplate(unittest.TestCase):
    def test_the_house_apology_leaves_nothing_behind(self):
        self.assertEqual(text.readable(f"The lift is out of service. {APOLOGY}"),
                         "The lift is out of service")

    def test_every_wording_on_the_corpus_goes(self):
        # Five spellings and two typos, all of them real.
        for apology in (
            "Iarnród Éireann Irish Rail apologise for the inconvenience caused.",
            "Iarnród Éireann apologise for the inconvenience caused.",
            "Iarnród Éireann Irish Rail apologises for the inconvenience caused.",
            "Iarnród Éireann apologise or any inconvenience caused.",
            "Iarnród Éireann Irish Rail apologies for the inconvenience caused..",
            "Apologies for any inconvenience caused.",
        ):
            with self.subTest(apology=apology):
                self.assertEqual(text.readable(f"Delayed. {apology}"), "Delayed")

    def test_a_real_caused_by_survives_it(self):
        self.assertEqual(
            text.readable(f"Delays due to congestion caused by a technical issue. {APOLOGY}"),
            "Delays due to congestion caused by a technical issue",
        )


class TheEditingMarks(unittest.TestCase):
    def test_an_update_stamp_is_not_part_of_what_the_notice_says(self):
        for prefix in ("Update at 17:24 - ", "Update15:52: ", "Update 11:45hrs. ", "06:00hrs. "):
            with self.subTest(prefix=prefix):
                self.assertEqual(text.readable(prefix + "Services have resumed"),
                                 "Services have resumed")

    def test_the_writers_initials_come_off(self):
        self.assertEqual(text.readable("Bus transfers in place. -CL"), "Bus transfers in place")

    def test_entities_are_encoded_twice(self):
        self.assertEqual(text.plain("Rush &amp;#38; Lusk"), "Rush & Lusk")

    def test_a_line_break_ends_a_sentence_rather_than_joining_two(self):
        # Three of the longest notices put a separate statement on each line, and
        # a space would hand the cause reader one sentence with two clauses in it.
        self.assertEqual(
            text.sentences("Stopped at Malahide.<br><br>Staff are fault-finding."),
            ["Stopped at Malahide", "Staff are fault-finding"],
        )


class TheSentenceSplit(unittest.TestCase):
    def test_a_service_time_is_not_a_full_stop(self):
        self.assertEqual(
            text.sentences("17.43 Drogheda/GCD departed +37mins delayed"),
            ["17.43 Drogheda/GCD departed +37mins delayed"],
        )

    def test_a_spaced_hyphen_separates_two_statements(self):
        # "Level crossing struck by a vehicle - Services are suspended between
        # Mullingar and Edgeworthstown" is a cause and its consequence.
        self.assertEqual(
            text.sentences("Level crossing struck by a vehicle - Services are suspended"),
            ["Level crossing struck by a vehicle", "Services are suspended"],
        )

    def test_a_hyphenated_place_pair_is_not_a_split(self):
        self.assertEqual(text.sentences("Failed between Malahide-Donabate"),
                         ["Failed between Malahide-Donabate"])

    def test_an_empty_field_reads_as_nothing(self):
        self.assertEqual(text.sentences(None), [])
        self.assertEqual(text.readable(""), "")


if __name__ == "__main__":
    unittest.main()
