"""Turning the raw message logs into disruptions.

Read straight from `lifts-data/raw/messages-*.jsonl`, not from `lift_status.db`.
The collector's identity key is `head` + `locationCodes` + `start`, and both of
those fields move underneath a delay notice: the head carries the minutes, so
"+15mins delayed" becomes "+21mins delayed" at the next poll, and Irish Rail
empties `locationCodes` part-way through a notice's life. 288 of the 497
non-lift notices on the corpus lose the field before they leave the feed.
`notes/site.md` has the numbers.

What this module builds instead is a **disruption**: every notice sharing a
`start` and a route, which is one event being re-worded as it develops. Nine
notices over eight hours on 17 August are one Thurles to Limerick Junction
closure, not nine of anything. The route is resolved rather than read off each
sighting, because `eventStops` empties out on the same polls `locationCodes`
does; `resolve` below has that, and `notes/site.md` has the numbers.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import NamedTuple
from zoneinfo import ZoneInfo

from delay_cause import FAMILY, ORIGIN, read

# Irish Rail's timestamps carry no UTC offset, the same as every other Irish
# transport API of this vintage. Treated as Dublin wall-clock, as the collector
# treats them.
DUBLIN = ZoneInfo("Europe/Dublin")

# The first poll. The feed shows only what is up now, so nothing before this
# instant exists anywhere and days before it are "no data", never "quiet".
COLLECTION_START = datetime(2026, 8, 8, 21, 30, 55, tzinfo=UTC)

# This site's subject is every notice that is not one of those. The lift repo
# publishes the lift outages; a notice about both machines is theirs, not this
# site's, and `classify` there is the pattern this mirrors.
NOT_OURS = re.compile(
    r"\b(lifts?|escalators?)\b.*\bout of (order|service)\b", re.IGNORECASE
)

# Live tests, published to the real feed, telling customers to ignore them.
# Four distinct ones on the corpus. Dropped by name because that is the only
# thing that distinguishes them.
TEST_NOTICE = re.compile(r"\btest HIM alert\b", re.IGNORECASE)

# "Customer Notice: This train has reduced capacity" is a template about the
# seats, not about the train running late, and it is a third of the feed: 133 of
# the 394 disruptions on the corpus, from two distinct heads, 130 of them giving
# "operational reasons" as the cause. Counted separately and named on the page
# rather than dropped silently - a third of the subject going missing without a
# number beside it is the kind of thing this family does not do. `notes/site.md`.
CAPACITY_NOTICE = re.compile(r"\breduced capacity\b", re.IGNORECASE)

# A minute figure, as the feed writes one: "+15mins", "+15/20 minutes delayed",
# "approximately 14 minutes behind schedule", "+40 minutes delayed". The unit is
# required - the corpus also carries a bare "+25 delayed", and a number with no
# unit beside it is not one this reads. A range takes its lower bound: "+15/20"
# is at least fifteen and the page says "at least".
MINUTES = re.compile(r"\+?\s*(\d{1,3})\s*(?:/\s*\d{1,3}\s*)?(?:mins?|minutes?)\b", re.IGNORECASE)

# How far the data may lag the build before the page says so. The collector
# pushes every six hours, so the newest data can legitimately be about seven
# hours old; a single missed push shows thirteen or more. Same number and the
# same reasoning as the lift site's.
STALE_AFTER = timedelta(hours=10)


class Sighting(NamedTuple):
    head: str
    text: str
    start: str
    origin: str | None
    destination: str | None
    seen_at: datetime
    # How many legs `eventStops` carried. On a multi-leg notice the list is the
    # services still affected and it shrinks as they recover, so the first leg
    # is not an identity; `resolve` reads this rather than the route.
    legs: int = 1


class Disruption(NamedTuple):
    """One event, and every wording the feed gave it."""

    start: str
    origin: str | None
    destination: str | None
    head: str
    text: str
    first_seen: datetime
    last_seen: datetime
    updates: tuple[tuple[datetime, str, str], ...]
    minutes: int | None
    causes: tuple

    @property
    def route(self):
        if self.origin and self.destination and self.origin != self.destination:
            return f"{self.origin} to {self.destination}"
        return self.origin or self.destination or UNNAMED_ROUTE

    @property
    def day(self):
        """The date it was first listed, in Dublin, which is what the bars count."""
        return self.first_seen.astimezone(DUBLIN).date()

    @property
    def families(self):
        return tuple(dict.fromkeys(FAMILY[c.category] for c in self.causes))

    @property
    def origins(self):
        return tuple(c for c in self.causes if FAMILY[c.category] == ORIGIN)


class Corpus(NamedTuple):
    disruptions: tuple[Disruption, ...]
    capacity: tuple[Disruption, ...]
    horizon: datetime
    runs: int


def _parse_run(line):
    try:
        run = json.loads(line)
    except json.JSONDecodeError:
        return None, None
    if run.get("http_status") != 200 or run.get("network_error"):
        return None, None
    try:
        items = json.loads(run.get("body") or "")
    except (json.JSONDecodeError, TypeError):
        return None, None
    if not isinstance(items, list):
        return None, None
    try:
        seen_at = datetime.strptime(run.get("fetched_at_utc") or "", "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        # Every other field here is guarded, and one odd line in a log that is
        # append-only and years long must not take the whole build down.
        return None, None
    return seen_at.replace(tzinfo=UTC), items


def ours(head, text):
    """Whether a notice is this site's subject.

    Everything the feed carries except the lift and escalator outages, which
    belong to the sibling site, and the test alerts. Deliberately not "every
    notice whose head says delay": the most severe events on the corpus are
    headed "Services suspended between Newry and Portadown" and never use the
    word, so a delay filter would drop exactly the ones that matter most.
    `notes/site.md`.
    """
    if TEST_NOTICE.search(head) or TEST_NOTICE.search(text):
        return False
    # Each field on its own: the pattern spans words, and run together a head
    # naming a lift would pair with an "out of service" halfway down the body.
    return not (NOT_OURS.search(head) or NOT_OURS.search(text))


def sightings(data_dir):
    """Every sighting of every notice this site publishes, and the last good run."""
    found, horizon, runs = [], None, 0
    for path in sorted(Path(data_dir).glob("raw/messages-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                seen_at, items = _parse_run(line)
                if seen_at is None:
                    continue
                runs += 1
                horizon = seen_at if horizon is None else max(horizon, seen_at)
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    head = (item.get("head") or "").strip()
                    text = (item.get("text") or "").strip()
                    if not ours(head, text):
                        continue
                    stops = item.get("eventStops") or []
                    first = stops[0] if stops and isinstance(stops[0], dict) else {}
                    found.append(
                        Sighting(
                            head=head,
                            text=text,
                            start=(item.get("start") or "").strip(),
                            origin=(first.get("sStop") or "").strip() or None,
                            destination=(first.get("eStop") or "").strip() or None,
                            seen_at=seen_at,
                            legs=len(stops),
                        )
                    )
    return found, horizon, runs


def claimed_minutes(head, text):
    """The minute figure the notice claims, or None.

    The lower bound of a range, so "+15/20 minutes delayed" reads as fifteen and
    the page can say "at least". Head before body: the head is where the feed
    puts the current figure when it updates one.
    """
    for value in (head, text):
        match = MINUTES.search(value or "")
        if match:
            return int(match.group(1))
    return None


# What the route reads as when a notice names more than one service.
SEVERAL = "Several services"

# And when it never named one at all. It heads the disruption's row, where
# "Not stated" read like an empty database column rather than a sentence.
UNNAMED_ROUTE = "Route not stated"


def routes_by_start(found):
    """The routes each `start` was ever seen with, ignoring the empty ones."""
    routes = defaultdict(set)
    for sighting in found:
        if sighting.origin or sighting.destination:
            routes[sighting.start].add((sighting.origin, sighting.destination))
    return routes


def network_starts(found):
    """The starts whose notice ever named more than one service.

    `eventStops` on such a notice is the list of services still affected, and it
    shrinks as they recover: the Connolly signalling failure of 2026-08-20 ran
    1 leg, then 4, then 10, then 7, and its first leg changed from Donabate to
    Maynooth on the way. So the first leg is not an identity for it, and nothing
    keys on the route under these starts at all.

    Decided per start rather than per sighting, because the same notice is
    single-leg at one poll and multi-leg at the next.
    """
    return {s.start for s in found if s.legs > 1}


def resolve(found):
    """[(sighting, route)], with the route each sighting belongs to.

    Two separate repairs, both for the same underlying behaviour: the feed's
    location fields are a description of what is affected right now, not an
    identity, and they move underneath a live notice.

    **An emptied `eventStops`.** It goes empty part-way through a notice's life
    exactly as `locationCodes` does, and on the same polls: 186 of the 361
    notices on the corpus are seen both with a route and without one, and in
    every one of those the `start` holds still while the stops go. Such a
    sighting takes the route its `start` carries, which is unambiguous for 362
    of the 370 starts. Under a start that carries two it is matched on its
    wording instead - a wording alone is never enough, "Customer Notice: This
    train has reduced capacity" being boilerplate on 36 routes, so it is only
    ever consulted inside a single start.

    **A shrinking leg list.** See `network_starts`. Those starts key on the
    start alone and their route reads `SEVERAL`.
    """
    routes = routes_by_start(found)
    network = network_starts(found)
    wordings = {}
    for sighting in sorted(found, key=lambda s: s.seen_at):
        if sighting.origin or sighting.destination:
            wordings[(sighting.start, sighting.head, sighting.text)] = (
                sighting.origin,
                sighting.destination,
            )
    out = []
    for sighting in found:
        if sighting.start in network:
            route = (SEVERAL, None)
        elif sighting.origin or sighting.destination:
            route = (sighting.origin, sighting.destination)
        else:
            known = routes.get(sighting.start, set())
            if len(known) == 1:
                route = next(iter(known))
            else:
                route = wordings.get((sighting.start, sighting.head, sighting.text), (None, None))
        out.append((sighting, route))
    return out


def group(found):
    """Sightings folded into disruptions, oldest first.

    Keyed on `start` with the route `resolve` worked out, which is the service
    or the stretch of line the notice is about. A notice whose wording changes
    stays one disruption and gains an update; the collector's key would have
    made it two, because the head carries the minutes.
    """
    by_key = defaultdict(list)
    for sighting, (origin, destination) in resolve(found):
        by_key[(sighting.start, origin, destination)].append(sighting)

    out = []
    for (start, origin, destination), group_sightings in by_key.items():
        group_sightings.sort(key=lambda s: s.seen_at)
        wordings = []
        for sighting in group_sightings:
            if not wordings or (wordings[-1][1], wordings[-1][2]) != (sighting.head, sighting.text):
                wordings.append((sighting.seen_at, sighting.head, sighting.text))
        latest = wordings[-1]
        figures = [
            m
            for m in (claimed_minutes(head, text) for _, head, text in wordings)
            if m is not None
        ]
        causes = []
        for _, head, text in wordings:
            for cause in read(head, text).causes:
                if cause.category not in {c.category for c in causes}:
                    causes.append(cause)
        out.append(
            Disruption(
                start=start,
                origin=origin,
                destination=destination,
                head=latest[1],
                text=latest[2],
                first_seen=group_sightings[0].seen_at,
                last_seen=group_sightings[-1].seen_at,
                updates=tuple(wordings),
                # The worst figure the notice ever claimed, not the newest: a
                # disruption that eased from +60 to +30 was still a +60 one, and
                # one that grew from +25 to +90 is not a +25 one either.
                minutes=max(figures) if figures else None,
                causes=tuple(causes),
            )
        )
    out.sort(key=lambda d: (d.first_seen, d.route))
    return tuple(out)


def is_capacity(disruption):
    """Whether every wording this disruption ever had was a capacity notice.

    Every, not the latest. A train can carry a capacity banner and a delay
    banner at the same `start`, and reading only the newest filed three real
    disruptions - two technical faults and a bus transfer - as seating notices,
    which took them off the site entirely.
    """
    return all(
        CAPACITY_NOTICE.search(f"{head} {text}") for _, head, text in disruption.updates
    )


def load(data_dir):
    found, horizon, runs = sightings(data_dir)
    if horizon is None:
        raise ValueError(f"no successful runs in {data_dir}/raw")
    grouped = group(found)
    return Corpus(
        tuple(d for d in grouped if not is_capacity(d)),
        tuple(d for d in grouped if is_capacity(d)),
        horizon,
        runs,
    )


def months(disruptions, until):
    """Every month from the first poll to the horizon, oldest first."""
    first = COLLECTION_START.astimezone(DUBLIN).date().replace(day=1)
    last = until.astimezone(DUBLIN).date().replace(day=1)
    out, cursor = [], first
    while cursor <= last:
        out.append(cursor.strftime("%Y-%m"))
        cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)
    for disruption in disruptions:
        ym = disruption.day.strftime("%Y-%m")
        if ym not in out:
            out.append(ym)
    return sorted(set(out))


def by_month(disruptions):
    grouped = defaultdict(list)
    for disruption in disruptions:
        grouped[disruption.day.strftime("%Y-%m")].append(disruption)
    return grouped


def days_in(ym):
    year, month = int(ym[:4]), int(ym[5:7])
    nxt = date(year + month // 12, month % 12 + 1, 1)
    return (nxt - date(year, month, 1)).days


def day_counts(disruptions, ym, until, now=None):
    """One row per day of the month: how many were listed, and of what families.

    `total` and `counts` are separate because a disruption can name two families
    - a signalling fault and the knock-on it caused - and would then be counted
    twice by anything summing the breakdown. Seven days in September 2026 read
    one too high that way, and one of them was painted a band too dark.

    A day past the horizon has no row at all rather than a zero: the collector
    had not reached it, and a chart that draws nothing and a chart that draws
    zero say different things.

    A day that has not started yet is marked `future` and says so instead. Given
    `now` it is the same distinction the three sibling sites draw, and without it
    two thirds of a live month reads as data somebody failed to collect.
    """
    horizon_day = until.astimezone(DUBLIN).date()
    today = now.astimezone(DUBLIN).date() if now else None
    rows = []
    listed = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for disruption in disruptions:
        if disruption.day.strftime("%Y-%m") != ym:
            continue
        total[disruption.day] += 1
        for family in disruption.families or (None,):
            listed[disruption.day][family] += 1
    for number in range(1, days_in(ym) + 1):
        day = date(int(ym[:4]), int(ym[5:7]), number)
        if day > horizon_day or day < COLLECTION_START.astimezone(DUBLIN).date():
            rows.append({
                "day": day.isoformat(),
                "counts": None,
                "total": None,
                "future": bool(today and day > today),
            })
            continue
        rows.append({
            "day": day.isoformat(),
            "counts": dict(listed.get(day, {})),
            "total": total.get(day, 0),
            "future": False,
        })
    return rows
