"""The page, on a corpus small enough to read.

The classes are the promises the page makes in its own footer: that it never
adds minutes up, that it never quotes a share of trains, and that a day the
collector had not reached is not drawn as a quiet day.
"""

from __future__ import annotations

import re
import unittest
from datetime import UTC, datetime

from delay_site import model, render
from tests.test_site_model import at, sighting


def corpus(found, horizon=None):
    grouped = model.group(found)
    return model.Corpus(
        tuple(d for d in grouped if not model.is_capacity(d)),
        tuple(d for d in grouped if model.is_capacity(d)),
        horizon or at(17),
        runs=100,
    )


def page(found, ym="2026-09", horizon=None, now=None):
    built = corpus(found, horizon)
    return render.month_page(
        ym,
        [d for d in built.disruptions if d.day.strftime("%Y-%m") == ym],
        built,
        model.months(built.disruptions, built.horizon),
        now or datetime(2026, 9, 11, 17, 0, tzinfo=UTC),
        render.SITE_HTML.read_text(encoding="utf-8"),
        render.SITE_CSS.read_text(encoding="utf-8"),
    )


SIGNALLING = sighting("+25mins delayed", "Delayed +25 minutes due to a signalling issue.")


def prose(rendered):
    """The words a reader sees, with the stylesheet and the markup taken out.

    The checks below are about what the page says, and a `width:100%` in an
    inline style is not the page saying anything.
    """
    body = re.sub(r"<style>.*?</style>", " ", rendered, flags=re.S).split("<footer>")[0]
    return re.sub(r"<[^>]+>", " ", body)


class TheDayBands(unittest.TestCase):
    def test_the_cuts_are_the_ones_the_corpus_asked_for(self):
        self.assertEqual([render.band(n) for n in (0, 1, 3, 4, 9, 10, 16, 40)],
                         ["0", "1", "1", "2", "2", "3", "3", "3"])

    def test_a_day_with_no_data_is_its_own_code(self):
        self.assertEqual(render.band(None), render.NO_DATA)

    def test_no_data_and_nothing_listed_are_different_cells(self):
        self.assertNotEqual(render.band(None), render.band(0))

    def test_a_caption_is_a_plain_count(self):
        # A family breakdown sat here once and read as a sentence competing
        # with the row below it - a reviewer called it "awful" on sight, and
        # it could overstate the day besides: one disruption naming a fault
        # and the knock-on it caused counted in both families.
        row = {"day": "2026-09-10", "counts": {"origin": 3, "consequence": 1}, "total": 4}
        self.assertEqual(render.day_caption(row), "4 disruptions")

    def test_a_single_disruption_is_not_plural(self):
        row = {"day": "2026-09-10", "counts": {"origin": 1}, "total": 1}
        self.assertEqual(render.day_caption(row), "1 disruption")


class TheMinutesAreNeverAddedUp(unittest.TestCase):
    def test_a_figure_is_shown_as_a_floor_and_not_a_measurement(self):
        self.assertIn("at least 25 minutes late", page([SIGNALLING]))

    def test_no_rendered_page_states_a_total_in_minutes(self):
        # The prototype's headline summed them and overstated by 1.26x. Nothing
        # on this page may grow one back.
        rendered = page([SIGNALLING, sighting("+40mins", "Delayed +40 minutes due to congestion.",
                                              start="2026-09-10T11:00:00")])
        self.assertNotRegex(prose(rendered), r"(?i)\b(total|sum|combined|altogether)\b.{0,40}min")

    def test_a_disruption_with_no_figure_claims_none(self):
        rendered = page([sighting("Delays expected", "Due to a signalling issue.")])
        self.assertNotIn("at least", prose(rendered))


class TheSiteNeverInventsADenominator(unittest.TestCase):
    def test_nothing_above_the_footer_states_a_percentage(self):
        self.assertNotRegex(prose(page([SIGNALLING])), r"\d\s*%")


class WhatThePageCallsThings(unittest.TestCase):
    def test_it_counts_disruptions_and_says_disruptions(self):
        # It folds many notices into one event, so calling the result a count of
        # notices would contradict the footer two screens further down.
        rendered = page([SIGNALLING])
        self.assertIn("1 disruption listed", rendered)
        self.assertIn("disruptions listed", rendered)

    def test_a_cause_is_printed_in_the_readers_words_and_not_decoded(self):
        rendered = page([sighting("Suspended", "Services suspended following a tragic incident.")])
        self.assertIn("Incident on the line", rendered)
        self.assertNotRegex(prose(rendered), r"(?i)\bfatalit|\bdeath\b|\bsuicide\b")

    def test_an_operational_issue_is_shown_as_no_cause_given(self):
        rendered = page([sighting("Delayed", "Delayed due to an operational issue.")])
        self.assertIn("No cause given", rendered)

    def test_the_apology_template_does_not_reach_the_page(self):
        rendered = page([sighting(
            "Delayed",
            "Delayed due to a signalling issue. Iarnród Éireann Irish Rail apologise for any "
            "inconvenience caused.",
        )])
        self.assertNotIn("inconvenience caused", rendered)

    def test_a_month_with_nothing_in_it_says_so(self):
        self.assertIn("No disruption notice was listed", page([SIGNALLING], ym="2026-08"))


class TheReducedCapacityNoticesAreNamedRatherThanDropped(unittest.TestCase):
    def test_the_count_is_printed_where_the_list_is(self):
        found = [SIGNALLING, sighting(
            "Customer Notice: This train has reduced capacity",
            "Due to operational reasons, this train will operate with reduced capacity.",
            start="2026-09-10T11:00:00",
        )]
        rendered = page(found)
        self.assertIn("1 train as having reduced capacity", rendered)
        self.assertIn("1 disruption listed", rendered)

    def test_a_month_without_any_says_nothing_about_them(self):
        self.assertNotIn("reduced capacity this month", page([SIGNALLING]))


class TheMonthTabs(unittest.TestCase):
    def test_from_the_newest_page_the_archive_is_below(self):
        self.assertEqual(
            render.tabs("2026-09", ["2026-08", "2026-09"]),
            '<a href="m/2026-08.html">August 2026</a>'
            '<a href="index.html" class="on">September 2026</a>',
        )

    def test_from_an_archive_page_the_newest_is_above(self):
        self.assertEqual(
            render.tabs("2026-08", ["2026-08", "2026-09"]),
            '<a href="2026-08.html" class="on">August 2026</a>'
            '<a href="../index.html">September 2026</a>',
        )


class TheBudget(unittest.TestCase):
    def test_a_month_of_disruptions_is_well_inside_it(self):
        found = []
        for n in range(120):
            found.append(sighting(
                f"+{n}mins delayed",
                f"Service {n} delayed +{n} minutes due to a signalling issue on the line.",
                start=f"2026-09-10T{n % 24:02d}:{n % 60:02d}:00",
                seen_at=at(9),
            ))
        rendered = page(found)
        self.assertLess(len(rendered.encode("utf-8")), render.BUDGET_BYTES)


class ADayTheMonthHasNotReachedYet(unittest.TestCase):
    """A day still to come is not a day the collector missed.

    The three sibling sites draw the two the same grey and say different things
    about them. Without the distinction two thirds of a live month reads as data
    somebody failed to collect.
    """

    def test_it_says_still_to_come_rather_than_no_data(self):
        future = {"day": "2026-09-30", "counts": None, "total": None, "future": True}
        missed = {"day": "2026-08-01", "counts": None, "total": None, "future": False}
        self.assertEqual(render.day_caption(future), "still to come")
        self.assertEqual(render.day_caption(missed), "the collector missed this day")

    def test_the_key_says_nothing_about_it(self):
        # Nobody needs a legend to be told that tomorrow has not happened.
        self.assertNotIn("still to come", render.legend())


class TheTagsOnARow(unittest.TestCase):
    def test_no_cause_given_goes_where_the_notice_also_named_one(self):
        # A notice re-worded from a mechanical issue into "an operational issue"
        # carried both answers at once, which read as the page contradicting
        # itself. Five disruptions on the corpus to 2026-09-12 are this shape.
        rendered = prose(page([
            sighting("Service CANCELLED", "Cancelled due to a mechanical issue.", seen_at=at(9)),
            sighting("Service CANCELLED", "Cancelled due to an operational issue.", seen_at=at(10)),
        ]))
        self.assertIn("Technical or mechanical fault", rendered)
        self.assertNotIn("No cause given", rendered)

    def test_a_notice_that_named_nothing_still_says_so(self):
        self.assertIn("No cause given", prose(page([sighting("Delayed", "Delayed.")])))


class TheBanner(unittest.TestCase):
    def test_the_month_still_collecting_says_so_far(self):
        self.assertIn("September 2026 so far:", page([SIGNALLING]))

    def test_a_finished_month_states_a_final_figure(self):
        rendered = page([SIGNALLING], ym="2026-08")
        self.assertIn("August 2026:", rendered)
        self.assertNotIn("August 2026 so far", rendered)

    def test_data_past_the_stale_threshold_is_marked_on_the_stamp(self):
        # The default horizon is a day behind the default build clock.
        self.assertIn('Data to <span class="stale">', page([SIGNALLING]))

    def test_fresh_data_is_not(self):
        # Not a bare "stale": base.css carries the rule that paints it.
        self.assertNotIn('<span class="stale">', page([SIGNALLING], now=at(18)))


class TheDisruptionRow(unittest.TestCase):
    def test_the_time_sits_inside_the_phrase_it_measures(self):
        # It used to float at the top right on its own, saying only that
        # something happened at 10:00.
        self.assertIn("first listed 10 Sep,", page([SIGNALLING]))

    def test_a_notice_re_worded_once_is_not_re_worded_1_times(self):
        rendered = page([
            sighting("Delayed", "Delayed due to a signalling issue.", seen_at=at(9)),
            sighting("Delayed further", "Delayed further due to a signalling issue.",
                     seen_at=at(10)),
        ])
        self.assertIn("re-worded once while it was listed", rendered)


class TheTemplateIsFilled(unittest.TestCase):
    def test_no_marker_is_left_behind(self):
        rendered = page([SIGNALLING])
        self.assertEqual(re.findall(r"<!--[A-Z-]+-->", rendered), [])


def _many(n):
    return [sighting(f"+{i}mins delayed", start=f"2026-09-10T{9 + i // 60:02d}:{i % 60:02d}:00")
            for i in range(n)]


class ThePagedDisruptionList(unittest.TestCase):
    """PAGE_SIZE rows a page, client-side: every row still ships in the same
    build, `hidden` is what keeps the rest off screen until a click.
    """

    def test_a_month_at_or_under_the_page_size_has_no_pager(self):
        rendered = page(_many(render.PAGE_SIZE))
        self.assertNotIn('class="pager"', rendered)
        self.assertEqual(rendered.count('class="case"'), render.PAGE_SIZE)

    def test_a_month_over_the_page_size_pages_the_rest(self):
        rendered = page(_many(render.PAGE_SIZE + 5))
        self.assertIn('class="pager"', rendered)
        self.assertEqual(rendered.count('class="case"'), render.PAGE_SIZE + 5)
        starts_hidden = rendered.count('class="page" hidden')
        self.assertEqual(starts_hidden, 1, "only the second page starts hidden")
        self.assertIn("Page 1 of 2", rendered)

    def test_the_script_defines_and_calls_the_pager(self):
        rendered = page(_many(render.PAGE_SIZE + 1))
        self.assertIn("function pageDelays()", rendered)
        self.assertIn("pageDelays();", rendered)


class TheHoverCaptionActuallyFires(unittest.TestCase):
    """caption.js defines `bindDayCaption` and does nothing else - a page that
    inlines the script but never calls it renders a bar that looks interactive
    and is not. `closest(".row, .card")` is how the listener finds the day
    cell's own `.daycap`, so the two need a shared ancestor of one of those
    classes or the call finds no host and fills nothing.
    """

    def test_the_script_calls_what_it_defines(self):
        self.assertIn("bindDayCaption();", page([SIGNALLING]))

    def test_the_bar_and_its_caption_share_a_card_or_row(self):
        rendered = page([SIGNALLING])
        section = rendered.split('<div class="bar">')[0].rsplit("<div", 1)[1]
        self.assertIn('class="card"', section)
        # Exactly one close between them: the bar's own. A second would close
        # the card too, and the caption would be looking for a host with no
        # `.daycap` in it.
        between = rendered.split('<div class="bar">')[1].split('<div class="daycap"')[0]
        self.assertEqual(between.count("</div>"), 1)


if __name__ == "__main__":
    unittest.main()
