"""Disruptions, on sightings shaped like the ones the collector logs.

The first class is the point of the file. `eventStops` empties part-way through
a notice's life, exactly as `locationCodes` does, and a key that takes the field
as it arrives splits one event into two. Every fixture below is a shape the
corpus actually contains.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from delay_site import model


def at(hour, minute=0, day=10, month=9):
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def sighting(head, text="", start="2026-09-10T09:00:00", origin="Dublin Connolly",
             destination="Belfast", seen_at=None, legs=1):
    return model.Sighting(head, text, start, origin, destination, seen_at or at(9), legs)


class ARouteThatEmptiesOutIsStillTheSameDisruption(unittest.TestCase):
    def test_a_sighting_that_lost_its_stops_joins_the_one_its_start_carries(self):
        found = [
            sighting("+15mins delayed", seen_at=at(9)),
            sighting("+21mins delayed", seen_at=at(9, 30)),
            sighting("+21mins delayed", origin=None, destination=None, seen_at=at(10)),
        ]
        disruptions = model.group(found)
        self.assertEqual(len(disruptions), 1)
        self.assertEqual(disruptions[0].route, "Dublin Connolly to Belfast")
        self.assertEqual(disruptions[0].last_seen, at(10))

    def test_the_moving_head_does_not_split_it_either(self):
        # The collector's key is head + locationCodes + start, and the head
        # carries the minutes, so this is two messages to the collector and one
        # event to a reader.
        found = [
            sighting("+15mins delayed", seen_at=at(9)),
            sighting("+21mins delayed", seen_at=at(10)),
        ]
        disruptions = model.group(found)
        self.assertEqual(len(disruptions), 1)
        self.assertEqual(len(disruptions[0].updates), 2)

    def test_two_services_leaving_at_the_same_minute_stay_apart(self):
        found = [
            sighting("Delayed", origin="Westport", destination="Dublin Heuston"),
            sighting("Delayed", origin="Dublin Heuston", destination="Galway (Ceannt)"),
        ]
        self.assertEqual(len(model.group(found)), 2)

    def test_a_shrinking_leg_list_is_one_disruption_and_not_several(self):
        # On a multi-leg notice `eventStops` is the services still affected and
        # it shrinks as they recover: the Connolly failure of 2026-08-20 ran 1
        # leg, then 4, then 10, then 7, and its first leg moved from Donabate to
        # Maynooth. Keying on the first leg made that four disruptions.
        found = [
            sighting("Signalling Issue", origin="Donabate",
                     destination="Lansdowne Road", seen_at=at(12), legs=1),
            sighting("Signalling Issue", origin="Donabate",
                     destination="Lansdowne Road", seen_at=at(13), legs=10),
            sighting("Services Resuming", origin="Maynooth",
                     destination="Dublin Connolly", seen_at=at(14), legs=7),
        ]
        disruptions = model.group(found)
        self.assertEqual(len(disruptions), 1)
        self.assertEqual(disruptions[0].route, model.SEVERAL)

    def test_an_empty_sighting_under_a_contested_start_is_matched_on_its_wording(self):
        found = [
            sighting("Westport delayed", origin="Westport",
                     destination="Dublin Heuston", seen_at=at(9)),
            sighting("Galway delayed", origin="Dublin Heuston",
                     destination="Galway (Ceannt)", seen_at=at(9)),
            sighting("Westport delayed", origin=None, destination=None, seen_at=at(10)),
        ]
        disruptions = model.group(found)
        self.assertEqual(len(disruptions), 2)
        westport = next(d for d in disruptions if d.origin == "Westport")
        self.assertEqual(westport.last_seen, at(10))

    def test_a_notice_that_never_carried_a_route_says_so(self):
        found = [sighting("Delays expected", origin=None, destination=None)]
        self.assertEqual(model.group(found)[0].route, "Not stated")


class WhatTheSiteIsAbout(unittest.TestCase):
    def test_a_lift_notice_belongs_to_the_other_site(self):
        self.assertFalse(model.ours("Athy - Lift out of order", "The lifts are out of service."))
        self.assertFalse(
            model.ours("Connolly - Escalator out of order", "The Escalator is out of service.")
        )

    def test_a_live_test_alert_is_not_published(self):
        self.assertFalse(
            model.ours("Test HIM Alert Message 3 @ 10:49", "This is a Test HIM alert.")
        )

    def test_a_suspension_that_never_says_delay_is_published(self):
        # The most severe events on the corpus never use the word, so a filter
        # on it would drop exactly the ones that matter most.
        self.assertTrue(
            model.ours(
                "Services suspended between Newry and Portadown",
                "Due to an incident on the line, services are suspended.",
            )
        )

    def test_a_train_that_was_also_delayed_is_not_filed_as_a_seating_notice(self):
        # `is_capacity` read the newest wording only, and three real disruptions
        # - two technical faults and a bus transfer - vanished off the site.
        found = [
            sighting("Service delay +15", "Delayed due to a technical issue.", seen_at=at(9)),
            sighting("Customer Notice: This train has reduced capacity",
                     "Due to operational reasons, this train will operate with reduced "
                     "capacity.", seen_at=at(10)),
        ]
        self.assertFalse(model.is_capacity(model.group(found)[0]))

    def test_a_reduced_capacity_notice_is_kept_apart_rather_than_dropped(self):
        found = [
            sighting("Customer Notice: This train has reduced capacity",
                     "Due to operational reasons, this train will operate with reduced capacity."),
            sighting("+15mins delayed", "Delayed due to a signalling issue.",
                     start="2026-09-10T10:00:00"),
        ]
        capacity = [d for d in model.group(found) if model.is_capacity(d)]
        rest = [d for d in model.group(found) if not model.is_capacity(d)]
        self.assertEqual(len(capacity), 1)
        self.assertEqual(len(rest), 1)


class TheMinutesAreNotAdded(unittest.TestCase):
    def test_a_range_reads_as_its_lower_bound(self):
        self.assertEqual(model.claimed_minutes("Expected +15/20 minutes delayed", ""), 15)

    def test_every_wording_on_the_corpus_is_read(self):
        for text in (
            "17:00 Heuston/Cork has departed +15mins delayed",
            "is operating approximately 15 minutes behind schedule",
            "departed +15 minutes delayed",
            "Delays of up to +15mins can be expected",
        ):
            with self.subTest(text=text):
                self.assertEqual(model.claimed_minutes("", text), 15)

    def test_a_number_with_no_unit_is_not_a_minute_figure(self):
        # "+25 delayed" is in the corpus and says nothing this can rely on.
        self.assertIsNone(model.claimed_minutes("07:45 Bray/Howth departing +25 delayed", ""))

    def test_a_disruption_keeps_the_worst_figure_it_ever_claimed(self):
        # Donabate to Lansdowne Road read 25, then 60, then 80, then 90 as one
        # signalling failure developed. It was a +90 disruption, not a +25 one.
        found = [
            sighting("Signalling Issue", "+25 minutes delayed", seen_at=at(12)),
            sighting("Signalling Issue", "+90 minutes delayed", seen_at=at(13)),
        ]
        self.assertEqual(model.group(found)[0].minutes, 90)

    def test_and_an_easing_one_keeps_it_too(self):
        found = [
            sighting("Suspended", "+60 minutes delayed", seen_at=at(9)),
            sighting("Resuming", "+30 minutes delayed", seen_at=at(15)),
        ]
        self.assertEqual(model.group(found)[0].minutes, 60)


class TheCausesComeFromEveryWording(unittest.TestCase):
    def test_a_cause_named_only_in_a_later_wording_is_kept(self):
        found = [
            sighting("Delays expected", "Update to follow.", seen_at=at(9)),
            sighting("Delays expected", "Delayed due to a signalling issue.", seen_at=at(10)),
        ]
        self.assertEqual([c.category for c in model.group(found)[0].causes], ["signalling"])

    def test_the_same_cause_restated_is_counted_once(self):
        found = [
            sighting("+15mins", "Delayed due to a signalling issue.", seen_at=at(9)),
            sighting("+25mins", "Delayed due to a signalling issue.", seen_at=at(10)),
        ]
        self.assertEqual(len(model.group(found)[0].causes), 1)


class TheDayRows(unittest.TestCase):
    def test_a_disruption_naming_two_families_counts_once_in_the_total(self):
        found = [sighting(
            "Delays", "Delayed due to a signalling issue and an earlier service delay."
        )]
        rows = model.day_counts(model.group(found), "2026-09", at(17))
        row = next(r for r in rows if r["day"] == "2026-09-10")
        self.assertEqual(row["total"], 1)
        self.assertEqual(sum(row["counts"].values()), 2)

    def test_a_day_past_the_horizon_has_no_row_rather_than_a_zero(self):
        found = [sighting("Delayed", "Due to a signalling issue.", seen_at=at(9, 0, day=10))]
        rows = model.day_counts(model.group(found), "2026-09", at(12, 0, day=10))
        tenth = next(r for r in rows if r["day"] == "2026-09-10")
        eleventh = next(r for r in rows if r["day"] == "2026-09-11")
        self.assertEqual((tenth["counts"], tenth["total"]), ({"origin": 1}, 1))
        self.assertIsNone(
            eleventh["counts"], "a day the collector had not reached is not a quiet day"
        )

    def test_a_watched_day_with_nothing_listed_is_an_empty_row_and_not_no_data(self):
        rows = model.day_counts((), "2026-09", at(12, 0, day=10))
        self.assertEqual(next(r for r in rows if r["day"] == "2026-09-09")["counts"], {})

    def test_days_before_the_first_poll_are_no_data(self):
        rows = model.day_counts((), "2026-08", at(12, 0, day=31, month=8))
        self.assertIsNone(next(r for r in rows if r["day"] == "2026-08-01")["counts"])
        self.assertEqual(next(r for r in rows if r["day"] == "2026-08-09")["counts"], {})


if __name__ == "__main__":
    unittest.main()
