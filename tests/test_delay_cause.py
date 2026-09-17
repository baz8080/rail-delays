"""What a notice says went wrong, on notice texts the collector actually recorded.

Every string below is verbatim from `lifts-data/raw/messages-*.jsonl`, minus the
apology where it made the line unreadable. The classes are the decisions in
`notes/cause-reading.md`, one apiece: that a cause naming another delay is a
consequence and not a peer of a signalling fault, that "an incident on the line"
is not decoded, that "an operational issue" is not an answer, and that a notice
stating two causes gets two.
"""

from __future__ import annotations

import unittest

from delay_cause import model
from delay_cause.model import read


def categories(head, text=""):
    return [c.category for c in read(head, text).causes]


def one(head, text=""):
    causes = read(head, text).causes
    assert len(causes) == 1, [c.category for c in causes]
    return causes[0]


class EveryCategoryComesFromTheCorpus(unittest.TestCase):
    """One real clause per category, and the wording that decided it."""

    CLAUSES = {
        "a technical issue": model.TECHNICAL,
        "a mechanical issue on the train": model.TECHNICAL,
        "an earlier train failure": model.TECHNICAL,
        "a broken down train": model.TECHNICAL,
        "a necessary loco swap": model.TECHNICAL,
        "a signalling issue at Dromod": model.SIGNALLING,
        "a temporary speed restriction on the line": model.INFRASTRUCTURE,
        "a power supply issue": model.INFRASTRUCTURE,
        "a level crossing issue on the line ahead": model.LEVEL_CROSSING,
        "a vehicle striking a bridge at Longford": model.VEHICLE_STRIKE,
        "a passenger issue onboard": model.PASSENGER,
        "an ill passenger onboard": model.PASSENGER,
        "a medical emergency on the platform in Killiney": model.PASSENGER,
        "an incident on the line": model.INCIDENT,
        "a tragic incident on the line being attended by emergency services": model.INCIDENT,
        "congestion on the line": model.CONGESTION,
        "the late arrival of an incoming service": model.KNOCK_ON,
        "an earlier service delay on the line": model.KNOCK_ON,
        "an earlier DART cancellation": model.KNOCK_ON,
        "planned works": model.PLANNED,
        "engineering works at Waterford (Plunkett) Station": model.PLANNED,
        "an operational issue": model.UNSPECIFIED,
        "operational reasons": model.UNSPECIFIED,
    }

    def test_each_clause_reads_as_its_category(self):
        for clause, category in self.CLAUSES.items():
            with self.subTest(clause=clause):
                self.assertEqual(categories("", f"This service is delayed due to {clause}."),
                                 [category])

    def test_every_category_has_a_label_and_a_family(self):
        for category in model.CATEGORIES:
            self.assertIn(category, model.LABEL)
            self.assertIn(model.FAMILY[category], (model.ORIGIN, model.CONSEQUENCE,
                                                   model.PLANNED_FAMILY, model.UNSTATED))


class ADelayIsNotACause(unittest.TestCase):
    """The largest group on the corpus names another delay, and is filed as one.

    A chart that puts "the late arrival of an incoming service" beside "a
    signalling issue" answers the question "what does Irish Rail write in this
    field", not "what goes wrong on this railway". The family is what keeps the
    two apart.
    """

    def test_the_late_arrival_of_an_incoming_service_is_a_consequence(self):
        self.assertEqual(one("", "Departed +28 minutes delayed due to the late arrival of "
                                 "an incoming service.").family, model.CONSEQUENCE)

    def test_congestion_is_a_consequence(self):
        self.assertEqual(one("", "Delays of up to +20mins due to congestion.").family,
                         model.CONSEQUENCE)

    def test_a_signalling_fault_is_an_origin(self):
        self.assertEqual(one("", "Delayed due to a signalling issue.").family, model.ORIGIN)

    def test_a_reading_can_be_asked_for_one_family(self):
        reading = read("", "Delayed due to congestion caused by a technical issue onboard a train.")
        self.assertEqual([c.category for c in reading.of_family(model.ORIGIN)], ["technical"])
        self.assertEqual([c.category for c in reading.of_family(model.CONSEQUENCE)], ["congestion"])


class ANoticeCanStateMoreThanOneCause(unittest.TestCase):
    def test_and_joins_two_causes(self):
        self.assertEqual(
            categories("", "This service is delayed due to an earlier service delay and a "
                           "temporary speed restriction on the line."),
            ["knock_on", "infrastructure"],
        )

    def test_caused_by_chains_a_root_behind_the_proximate_one(self):
        causes = read("", "Northbound services through Balabriggan are experiencing delays of "
                          "up to +20mins due to congestion caused by a technical issue onboard "
                          "a train.").causes
        self.assertEqual([(c.category, c.role) for c in causes],
                         [("congestion", model.PROXIMATE), ("technical", model.ROOT)])

    def test_a_second_due_to_chains_the_same_way(self):
        causes = read("+20mins delays", "+20mins to services through Howth Junction due to "
                                        "07:45 Bray/Howth departing Howth Junction +25 delayed "
                                        "due to a technical issue.").causes
        self.assertEqual([(c.category, c.role) for c in causes],
                         [("knock_on", model.PROXIMATE), ("technical", model.ROOT)])

    def test_following_chains_an_incident_behind_a_late_arrival(self):
        causes = read("", "11:50 Dublin Connolly to Belfast departed +28 minutes delayed due to "
                          "the late arrival of an incoming service following an incident on "
                          "the line.").causes
        self.assertEqual([(c.category, c.role) for c in causes],
                         [("knock_on", model.PROXIMATE), ("incident", model.ROOT)])

    def test_one_fault_written_into_head_and_body_is_one_cause(self):
        self.assertEqual(
            categories("Service delayed 15 minutes - Due to a signalling issue.",
                       "This service is delayed due to a signalling issue."),
            ["signalling"],
        )

    def test_two_wordings_of_the_same_fault_are_one_cause(self):
        self.assertEqual(
            categories("", "Departed +15 minutes behind schedule. Due to a technical issue "
                           "onboard and a necessary train set replacement."),
            ["technical"],
        )


class TheClauseStopsWhereTheNoticeStopsNamingACause(unittest.TestCase):
    def test_what_the_service_will_do_instead_is_not_a_cause(self):
        # Five notices end "to aid service recovery and ease congestion on the
        # line". Reading to the full stop gives them a congestion they never claimed.
        self.assertEqual(
            categories("", "This service is delayed due to a passenger issue and will run "
                           "nonstop between Balbriggan and Drogheda (MacBride) to aid service "
                           "recovery and ease congestion on the line."),
            ["passenger"],
        )

    def test_the_service_the_notice_turns_to_is_not_a_cause(self):
        self.assertEqual(
            categories("", "Customers are advised that due to an incident on the line, the "
                           "10:00 Belfast to Dublin Connolly will have a replacement train "
                           "starting delayed from Newry."),
            ["incident"],
        )

    def test_what_a_fault_went_on_to_create_is_not_a_second_cause(self):
        self.assertEqual(
            categories("", "Delays due to a technical issue on the 14.50 Connolly/Belfast "
                           "creating congestion on the line."),
            ["technical"],
        )


class SpecificBeatsGeneral(unittest.TestCase):
    """The rule `lift_access` reads station prose by, applied to notices."""

    def test_a_vehicle_on_a_crossing_is_not_a_crossing_fault(self):
        self.assertEqual(
            categories("Services Suspended due to a vehicle striking Serpentine Level Crossing",
                       ""),
            ["vehicle_strike"],
        )

    def test_a_crossing_issue_with_no_vehicle_named_stays_a_crossing_issue(self):
        # It may be a barrier fault. The notice does not say, so neither does this.
        self.assertEqual(categories("", "Delays due to a level crossing issue at Sutton."),
                         ["level_crossing"])

    def test_an_incident_the_notice_goes_on_to_explain_is_not_unspecified(self):
        self.assertEqual(
            categories("", "Westport services will not operate following an incident at "
                           "Ballyhaunis, where a vehicle has collided with a train."),
            ["vehicle_strike"],
        )

    def test_the_typo_in_that_sentence_reads_the_same_way(self):
        # "collied" is Irish Rail's, in the other notice about the same morning.
        self.assertEqual(
            categories("", "Services to/from Westport can expect significant disruption "
                           "following an incident at Ballyhaunis, where a vehicle collied "
                           "with a train."),
            ["vehicle_strike"],
        )

    def test_an_incident_with_nothing_added_stays_unspecified(self):
        self.assertEqual(
            categories("", "Services to/from Westport can expect significant disruption "
                           "following an incident at Ballyhaunis."),
            ["incident"],
        )


class WhatTheReaderRefusesToSay(unittest.TestCase):
    def test_a_tragic_incident_is_reported_in_the_feeds_own_words(self):
        cause = one("", "Services are suspended following a tragic incident on the line being "
                        "attended by emergency services.")
        self.assertEqual(cause.category, model.INCIDENT)
        self.assertEqual(model.LABEL[cause.category], "Incident on the line")
        self.assertIn("tragic incident", cause.phrase)

    def test_an_operational_issue_is_a_non_answer_and_is_filed_as_one(self):
        cause = one("", "The 09:50 Dublin Connolly to Belfast is operating approximately 14 "
                        "minutes behind schedule due to an operational issue.")
        self.assertEqual((cause.category, cause.family), (model.UNSPECIFIED, model.UNSTATED))

    def test_a_notice_that_names_nothing_names_nothing(self):
        reading = read("Terminating at Connolly",
                       "This service will terminate at Connolly this evening.")
        self.assertEqual(reading.causes, ())
        self.assertFalse(reading.stated)

    def test_a_lift_notice_states_no_cause_unless_it_says_planned_works(self):
        self.assertEqual(categories("Athy - Lift out of order",
                                    "Lifts at platforms 1 and 2 are currently out of service."), [])
        self.assertEqual(categories("Dublin Pearse - Lift out of order",
                                    "The lift at platform 2 is temporarily unavailable due to "
                                    "planned works."), ["planned"])

    def test_a_cancelled_service_is_not_a_cause_of_itself(self):
        self.assertEqual(categories("Service cancelled", "This service has been cancelled."), [])
        self.assertEqual(categories("", "Delayed due to an earlier DART cancellation."),
                         ["knock_on"])

    def test_a_clause_no_rule_reads_is_reported_rather_than_bucketed(self):
        reading = read("", "This service is delayed due to a badger on the line.")
        self.assertEqual(reading.causes, ())
        self.assertEqual(reading.unread, ("a badger on the line",))
        self.assertTrue(reading.stated)


class ACauseWithNoClauseToIntroduceIt(unittest.TestCase):
    def test_a_cause_and_its_consequence_with_a_dash_between_them(self):
        self.assertEqual(
            categories("Services suspended between Mullingar and Edgeworthstown.",
                       "Level crossing struck by a vehicle - Services are suspended between "
                       "Mullingar and Edgeworthstown."),
            ["vehicle_strike"],
        )

    def test_a_head_that_is_only_a_cause(self):
        self.assertEqual(categories("Signalling issue", "Staff are working to rectify this."),
                         ["signalling"])

    def test_a_train_that_struck_a_tractor(self):
        self.assertEqual(
            categories("Services suspended between Portarlington and Tullamore.",
                       "A train has struck a tractor crossing the line. Emergency services "
                       "are en route."),
            ["vehicle_strike"],
        )

    def test_a_delay_awaiting_an_ambulance(self):
        self.assertEqual(
            categories("Departed Thurles +36 minutes delayed.",
                       "09:00 Dublin Heuston to Cork (Kent) was delayed in Thurles awaiting "
                       "an ambulance."),
            ["passenger"],
        )

    def test_a_knock_on_with_no_clause_is_left_unread_rather_than_guessed(self):
        # "Bus transfers" is a mitigation in nine notices and a stated cause in
        # one. Nothing here is confident enough to tell them apart.
        self.assertEqual(
            categories("+74min delayed", "17:20 Galway/Heuston departed Athlone +74mins "
                                         "delayed, as it was awaiting bus transfers from Mayo."),
            [],
        )

    def test_it_only_runs_where_the_notice_introduced_no_clause_at_all(self):
        # A notice that named a cause properly is read from that clause, so a
        # stray noun elsewhere in the body cannot add a second one.
        self.assertEqual(
            categories("Delays Expected", "The failed 18.50 Connolly/Belfast between Malahide "
                                          "and Donabate is being moved. Delays are due to "
                                          "congestion."),
            ["congestion"],
        )


class WhenACauseIsNotThisTrains(unittest.TestCase):
    """One signalling fault at Dromod produced seven notices in a day.

    Counting notices by category counts trains affected, not faults, and
    `earlier` is what lets a page say so.
    """

    def test_an_earlier_fault_is_marked(self):
        self.assertTrue(one("", "This service departed Connolly +34 minutes behind schedule. "
                                "Due to an earlier signalling issue at Connolly.").earlier)

    def test_this_trains_own_fault_is_not(self):
        self.assertFalse(one("", "This service is delayed departing Dromod due to a "
                                 "signalling issue.").earlier)


if __name__ == "__main__":
    unittest.main()
