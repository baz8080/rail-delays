"""The pipeline against the real corpus.

Skips without a `lifts-data` checkout, which is the one thing here that needs
one: everything else in this suite runs on a bare clone. If it fails, something
moved in the model or in the feed, and which one is worth knowing before the
model is adjusted to make it pass.
"""

from __future__ import annotations

import os
import re
import unittest
from datetime import UTC, datetime
from pathlib import Path

from delay_cause import CATEGORIES
from delay_site import model, render

DATA_DIR = os.environ.get("LIFT_STATUS_DATA_DIR", "../lifts-data")


def corpus_available():
    return bool(sorted(Path(DATA_DIR).glob("raw/messages-*.jsonl")))


@unittest.skipUnless(corpus_available(), f"no raw logs under {DATA_DIR}")
class TheRealCorpus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = model.load(DATA_DIR)
        cls.months = model.months(cls.corpus.disruptions, cls.corpus.horizon)
        cls.by_month = model.by_month(cls.corpus.disruptions)

    def test_the_horizon_is_the_newest_successful_run(self):
        latest = max(s.seen_at for s in model.sightings(DATA_DIR)[0])
        self.assertGreaterEqual(self.corpus.horizon, latest)

    def test_every_disruption_lands_in_exactly_one_month(self):
        placed = sum(len(v) for v in self.by_month.values())
        self.assertEqual(placed, len(self.corpus.disruptions))
        for ym in self.by_month:
            self.assertIn(ym, self.months)

    def test_no_lift_or_escalator_notice_reaches_this_site(self):
        # The sibling site publishes those, and a notice appearing on both would
        # be the same outage counted twice across two sites.
        leaked = [
            d
            for d in self.corpus.disruptions
            if re.search(r"\b(lifts?|escalators?)\b", f"{d.head} {d.text}", re.IGNORECASE)
        ]
        self.assertEqual(leaked, [], [d.head for d in leaked])

    def test_folding_never_loses_a_sighting(self):
        found, _, _ = model.sightings(DATA_DIR)
        grouped = model.group(found)
        self.assertEqual(len(grouped), len(self.corpus.disruptions) + len(self.corpus.capacity))
        first = min(s.seen_at for s in found)
        self.assertEqual(min(d.first_seen for d in grouped), first)

    def test_a_route_that_emptied_out_did_not_split_its_disruption(self):
        # The guard for the trap this model exists to avoid. Two disruptions
        # sharing a start and a route would be one event counted twice.
        keys = [(d.start, d.origin, d.destination) for d in self.corpus.disruptions]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_cause_read_is_one_the_page_can_name(self):
        for disruption in self.corpus.disruptions:
            for cause in disruption.causes:
                self.assertIn(cause.category, CATEGORIES)

    def test_the_day_bands_still_spread_the_month(self):
        # Bands cut from the corpus in September 2026. If a later month puts
        # every day in one band the bar has stopped saying anything and the cuts
        # want re-reading, which is a decision and not a silent adjustment.
        newest = self.by_month.get(self.months[-1], [])
        if len(newest) < 20:
            self.skipTest("too few disruptions in the newest month to judge the bands")
        rows = model.day_counts(self.corpus.disruptions, self.months[-1], self.corpus.horizon)
        watched = [r for r in rows if r["counts"] is not None]
        bands = {render.band(sum(r["counts"].values())) for r in watched}
        self.assertGreaterEqual(len(bands), 3, "the day bar is nearly one colour")

    def test_the_newest_month_is_inside_the_budget(self):
        page = render.month_page(
            self.months[-1],
            self.by_month.get(self.months[-1], []),
            self.corpus,
            self.months,
            datetime.now(tz=UTC),
            render.SITE_HTML.read_text(encoding="utf-8"),
            render.SITE_CSS.read_text(encoding="utf-8"),
        )
        self.assertLess(len(page.encode("utf-8")), render.BUDGET_BYTES)

    def test_no_page_states_a_share_of_trains(self):
        from tests.test_site_render import prose

        for ym in self.months:
            page = render.month_page(
                ym,
                self.by_month.get(ym, []),
                self.corpus,
                self.months,
                datetime.now(tz=UTC),
                render.SITE_HTML.read_text(encoding="utf-8"),
                render.SITE_CSS.read_text(encoding="utf-8"),
            )
            with self.subTest(month=ym):
                self.assertNotRegex(prose(page), r"\d\s*%")


if __name__ == "__main__":
    unittest.main()
