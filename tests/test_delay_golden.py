"""The golden file, and what counts as a difference.

`TheGoldenFileReplaysWhatItPinned` is the guard: it reads the heads and bodies
the file pinned, runs today's patterns over them and fails on anything that
moved. Like `access-golden.json` it needs no `lifts-data` checkout, so it runs on
a bare clone rather than skipping there unnoticed.

The rest decides what a difference is. A notice one document has and the other
does not is how much corpus there was when it was written, which is the
collector's business and no code change's, and it must pass. Anything both
describe must fail the moment it moves.
"""

from __future__ import annotations

import copy
import json
import unittest

from delay_cause import golden

SIGNALLING = ("Service delay +15", "This service is delayed departing Dromod due to a "
                                   "signalling issue. Update will follow.")
CONGESTION = ("Delays", "Northbound services through Balabriggan are experiencing delays of up "
                        "to +20mins due to congestion caused by a technical issue onboard a train.")


def document():
    return golden.build([SIGNALLING, CONGESTION])


class TheDifferenceReporter(unittest.TestCase):
    def setUp(self):
        self.stored = document()
        self.current = copy.deepcopy(self.stored)

    def reading(self, head):
        return next(r for r in self.current["readings"] if r["head"] == head)

    def test_identical_documents_do_not_differ(self):
        self.assertEqual(golden.differences(self.stored, self.current), [])

    def test_a_notice_the_file_has_not_seen_is_not_a_difference(self):
        self.current["readings"].append(
            {"head": "Signalling issue", "text": "", "causes": [], "unread": []}
        )
        self.assertEqual(golden.differences(self.stored, self.current), [])
        self.assertEqual([r["head"] for r in golden.new_notices(self.stored, self.current)],
                         ["Signalling issue"])

    def test_a_notice_the_corpus_no_longer_carries_is_not_a_difference(self):
        # Irish Rail edits a live banner in place, so a pinned body going missing
        # says nothing about the code, and the wording is still a test vector.
        self.current["readings"] = [r for r in self.current["readings"]
                                    if r["head"] != SIGNALLING[0]]
        self.assertEqual(golden.differences(self.stored, self.current), [])

    def test_a_category_that_moved_names_the_notice_and_both_readings(self):
        self.reading(SIGNALLING[0])["causes"][0]["category"] = "technical"
        lines = golden.differences(self.stored, self.current)
        self.assertEqual(len(lines), 1)
        self.assertIn("'Service delay +15'", lines[0])
        self.assertIn("signalling/proximate", lines[0])
        self.assertIn("technical/proximate", lines[0])

    def test_a_cause_that_stopped_being_found_is_a_difference(self):
        self.reading(CONGESTION[0])["causes"].pop()
        self.assertEqual(len(golden.differences(self.stored, self.current)), 1)

    def test_a_clause_that_stopped_being_read_is_its_own_line(self):
        self.reading(SIGNALLING[0])["unread"] = ["a signalling issue"]
        lines = golden.differences(self.stored, self.current)
        self.assertEqual(len(lines), 1)
        self.assertIn("unread:", lines[0])

    def test_a_regeneration_adds_and_updates_but_never_drops(self):
        gained = {"head": "Signalling issue", "text": "", "causes": [], "unread": []}
        merged = golden.merge(self.stored, {"readings": [gained]})
        self.assertEqual(len(merged["readings"]), 3)
        self.assertIn(gained, merged["readings"])


class TheDocumentSurvivesTheFile(unittest.TestCase):
    """`differences` compares a fresh `build` with a parsed file, so a tuple
    anywhere in `build`'s output would read as a change on every run."""

    def test_a_round_trip_through_json_is_the_same_document(self):
        built = document()
        parsed = json.loads(golden.dumps(built))
        self.assertEqual(parsed, built)
        self.assertEqual(golden.differences(parsed, built), [])

    def test_the_document_pins_the_words_a_reading_came_from(self):
        built = document()
        congestion = next(r for r in built["readings"] if r["head"] == CONGESTION[0])
        self.assertEqual([(c["category"], c["role"]) for c in congestion["causes"]],
                         [("congestion", "proximate"), ("technical", "root")])
        self.assertEqual(congestion["text"], CONGESTION[1])


class TheGoldenFileReplaysWhatItPinned(unittest.TestCase):
    def test_the_reader_still_says_what_the_file_says_it_says(self):
        stored = json.loads(golden.PATH.read_text(encoding="utf-8"))
        current = golden.build(golden.pinned_notices(stored))
        moved = golden.differences(stored, current)
        self.assertEqual(
            moved,
            [],
            f"the reader no longer matches {golden.PATH.name}. If the change is "
            "intended, regenerate with `python -m delay_cause --data-dir <data-dir> "
            "golden`, read the diff, and commit it with the change:\n  "
            + "\n  ".join(moved),
        )

    def test_every_pinned_notice_replays_into_a_reading(self):
        # `differences` compares what both documents have, so a pinned input that
        # read back as nothing would drop out of the comparison and pass.
        stored = json.loads(golden.PATH.read_text(encoding="utf-8"))
        current = golden.build(golden.pinned_notices(stored))
        self.assertEqual(len(current["readings"]), len(stored["readings"]))

    def test_the_file_pins_the_whole_corpus_and_not_only_what_states_a_cause(self):
        # A notice the reader is silent on is a test vector too: the failure it
        # guards against is a pattern that starts finding a cause in a lift notice.
        stored = json.loads(golden.PATH.read_text(encoding="utf-8"))
        silent = [r for r in stored["readings"] if not r["causes"] and not r["unread"]]
        self.assertTrue(len(silent) > 50, len(silent))


if __name__ == "__main__":
    unittest.main()
