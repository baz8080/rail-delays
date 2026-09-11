"""Emit the static site.

One page per month: the newest is `index.html` and every earlier one is
`m/<ym>.html`. That is what keeps the first download flat as the archive grows -
a reader arriving cold gets one month, never the corpus - and it is the same
reason the sibling lift site shards its outages per station.

Everything is rendered here, in Python. The only script on the page is
statusui's day-cell caption listener, so there is no data file to fetch and
nothing to wait for; the month tabs are ordinary links.
"""

from __future__ import annotations

import html
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import statusui

from delay_cause import CONSEQUENCE, LABEL, ORIGIN, PROXIMATE, UNSTATED
from delay_cause.model import PLANNED_FAMILY
from delay_cause.text import readable

from . import model

BASE_URL = "https://baz8080.github.io/rail-delays"

TEMPLATES = Path(__file__).parent
SITE_HTML = TEMPLATES / "site.html"
SITE_CSS = TEMPLATES / "site.css"

# What a reader downloads before touching anything. One month of the archive,
# and it has to stay that way: the site is meant to run for years.
BUDGET_BYTES = 500 * 1024

# Day-cell codes, by how many disruptions were first listed that day. Bands
# rather than a count: the bar is 31 cells wide and a reader is looking for the
# bad days, not reading numbers off it. The caption carries the number.
#
# The cuts come from the corpus and not from round numbers. Over the 31 days to
# 2026-09-11 the daily count runs 1 to 25 with a median of 6, so a bar banded at
# tens would have been one colour for almost every day and would have said
# nothing. These four bands split those 31 days roughly evenly.
BANDS = ((1, "0"), (4, "1"), (9, "2"), (17, "3"))
OVER_BAND = "4"
NO_DATA = "8"

BAND_LABEL = {
    "0": "nothing listed",
    "1": "1 to 3 listed",
    "2": "4 to 8 listed",
    "3": "9 to 16 listed",
    OVER_BAND: "17 or more listed",
    NO_DATA: "no data",
}

# What a family means in the page's own words. `origin` is deliberately not
# called "cause": the consequence families are causes too, in the sense that the
# notice names them, and the distinction this draws is whether the thing named
# is a fault or another delay.
FAMILY_LABEL = {
    ORIGIN: "something went wrong",
    CONSEQUENCE: "knock-on from another delay",
    PLANNED_FAMILY: "planned works",
    UNSTATED: "no cause given",
}

month_label = statusui.month_label


def band(count):
    """The day-cell code for a day's disruption count, or no-data for None."""
    if count is None:
        return NO_DATA
    for limit, code in BANDS:
        if count < limit:
            return code
    return OVER_BAND


def _esc(value):
    return html.escape(value or "", quote=True)


def _dublin(when):
    return when.astimezone(model.DUBLIN)


def _short(when):
    return _dublin(when).strftime("%Y-%m-%dT%H:%M")


def day_caption(row):
    counts = row["counts"]
    if counts is None:
        return BAND_LABEL[NO_DATA]
    total = sum(counts.values())
    if not total:
        return "nothing listed"
    parts = [
        f"{count} {FAMILY_LABEL[family]}" if family else f"{count} with no cause stated"
        for family, count in sorted(counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
    ]
    return f"{total} listed: " + ", ".join(parts)


def day_bar(rows):
    """The month's day cells, with the family breakdown in each caption."""
    cells = []
    for row in rows:
        counts = row["counts"]
        code = band(None if counts is None else sum(counts.values()))
        cap = f"{statusui.fmt_day(row['day'])}: {day_caption(row)}"
        cells.append(f'<i class="b{code}" data-cap="{_esc(cap)}"></i>')
    return "".join(cells)


def legend():
    return "".join(
        f'<span><i class="b{code}"></i>{_esc(BAND_LABEL[code])}</span>'
        for code in ("0", "1", "2", "3", OVER_BAND, NO_DATA)
    )


def tiles(disruptions):
    named = sum(1 for d in disruptions if d.origins)
    knock_on = sum(1 for d in disruptions if CONSEQUENCE in d.families)
    counted = Counter(c.category for d in disruptions for c in d.origins)
    top = counted.most_common(1)
    values = [
        (str(len(disruptions)), "disruptions listed", False),
        (str(named), "named something that went wrong", False),
        (str(knock_on), "blamed another delay", False),
        (
            LABEL[top[0][0]] if top else "Nothing",
            f"most named ({top[0][1]} of them)" if top else "no fault named this month",
            True,
        ),
    ]
    cards = "".join(
        f'<div class="tile"><div class="v{" txt" if is_text else ""}">{_esc(value)}</div>'
        f'<div class="k">{_esc(key)}</div></div>'
        for value, key, is_text in values
    )
    return cards


def routes_named(disruptions):
    return len({d.route for d in disruptions if d.route != "Not stated"})


def origins_panel(disruptions):
    """What the month's notices named, ranked, origins only.

    Consequences are left out of this one on purpose: "the late arrival of an
    incoming service" is not a thing that went wrong, and ranking it beside a
    signalling fault answers a different question. The tile above carries how
    often the feed did that instead.
    """
    counted = Counter(c.category for d in disruptions for c in d.origins)
    if not counted:
        return '<p class="quiet">No notice this month named anything that went wrong.</p>'
    most = counted.most_common(1)[0][1]
    rows = ""
    for category, count in counted.most_common():
        width = max(2, round(count / most * 100))
        rows += (
            '<div class="rank">'
            f'<div class="rname">{_esc(LABEL[category])}</div>'
            f'<div class="bar"><i style="width:{width}%"></i></div>'
            f'<div class="rn">{count}</div>'
            "</div>"
        )
    return rows


def _chip(cause):
    lead = "then " if cause.role != PROXIMATE else ""
    return f'<span class="chip chip-{cause.family}">{lead}{_esc(LABEL[cause.category])}</span>'


def case(disruption):
    chips = "".join(_chip(c) for c in disruption.causes)
    if not chips:
        chips = '<span class="chip chip-none">No cause stated</span>'
    minutes = (
        f'<span class="min">at least +{disruption.minutes} min</span>'
        if disruption.minutes is not None
        else ""
    )
    updates = ""
    if len(disruption.updates) > 1:
        times = len(disruption.updates) - 1
        updates = (
            f'<div class="tl">Re-worded {times} time{"s" if times != 1 else ""} while it was '
            f"listed, last at {_esc(statusui.when(_short(disruption.updates[-1][0])))}.</div>"
        )
    return (
        '<div class="case">'
        '<div class="top">'
        f"{chips}{minutes}"
        f'<span class="when" title="First listed, Dublin time">'
        f"{_esc(statusui.when(_short(disruption.first_seen)))}</span>"
        "</div>"
        f'<div class="sum">{_esc(disruption.route)}</div>'
        f'<div class="txt head">{_esc(readable(disruption.head))}</div>'
        f'<div class="txt">{_esc(readable(disruption.text))}</div>'
        f"{updates}"
        "</div>"
    )


def tabs(ym, months):
    """The month links, relative to the page they sit on."""
    newest = months[-1]
    here_is_newest = ym == newest
    out = ""
    for other in months:
        if other == newest:
            href = "index.html" if here_is_newest else "../index.html"
        else:
            href = f"m/{other}.html" if here_is_newest else f"{other}.html"
        on = ' class="on"' if other == ym else ""
        out += f'<a href="{_esc(href)}"{on}>{_esc(month_label(other))}</a>'
    return out


def month_page(ym, disruptions, corpus, months, now, template, css):
    rows = model.day_counts(corpus.disruptions, ym, corpus.horizon)
    cases = "".join(case(d) for d in sorted(disruptions, key=lambda d: d.first_seen, reverse=True))
    if not cases:
        cases = '<p class="empty">No disruption notice was listed this month.</p>'
    age = now - corpus.horizon
    stale = (
        '<p class="stale">The newest data here is '
        f"{statusui.hours(age.total_seconds() / 3600)} old.</p>"
        if age > model.STALE_AFTER
        else ""
    )
    routes = routes_named(disruptions)
    count = len(disruptions)
    capacity = sum(1 for d in corpus.capacity if d.day.strftime("%Y-%m") == ym)
    capacity_note = (
        f"Irish Rail also listed {capacity} train{'s' if capacity != 1 else ''} as having "
        "reduced capacity this month, which is about the seating rather than about a train "
        "running late. Those are not counted anywhere on this page."
        if capacity
        else ""
    )
    headline = (
        f"{month_label(ym)}: {count} disruption{'s' if count != 1 else ''} listed"
        + (f" across {routes} route{'s' if routes != 1 else ''}" if routes else "")
    )
    start_day = model.COLLECTION_START.astimezone(model.DUBLIN).date().isoformat()
    return statusui.assemble(
        template,
        {
            "SITE-CSS": css,
            "CANONICAL": f"{BASE_URL}/" if ym == months[-1] else f"{BASE_URL}/m/{ym}.html",
            "MONTH": _esc(month_label(ym)),
            "STALE": stale,
            "HEADLINE": _esc(headline),
            "META": f"Collected to {statusui.stamp(corpus.horizon)}",
            "TABS": tabs(ym, months),
            "TILES": tiles(disruptions),
            "BAR": day_bar(rows),
            "LEGEND": legend(),
            "ORIGINS": origins_panel(disruptions),
            "CASES": cases,
            "CAPACITY": _esc(capacity_note),
            "START": _esc(statusui.fmt_day(start_day)),
            "BUILT": statusui.stamp(now),
        },
    )


def write(site_dir, corpus, now):
    site_dir = Path(site_dir)
    (site_dir / "m").mkdir(parents=True, exist_ok=True)
    template = SITE_HTML.read_text(encoding="utf-8")
    css = SITE_CSS.read_text(encoding="utf-8")
    months = model.months(corpus.disruptions, corpus.horizon)
    grouped = model.by_month(corpus.disruptions)

    paths = []
    for ym in months:
        page = month_page(ym, grouped.get(ym, []), corpus, months, now, template, css)
        newest = ym == months[-1]
        (site_dir / "index.html" if newest else site_dir / "m" / f"{ym}.html").write_text(
            page, encoding="utf-8"
        )
        paths.append("" if newest else f"m/{ym}.html")

    (site_dir / "sitemap.xml").write_text(
        statusui.sitemap(BASE_URL, paths, now.strftime("%Y-%m-%d")), encoding="utf-8"
    )
    (site_dir / "robots.txt").write_text(statusui.robots(BASE_URL), encoding="utf-8")
    return size_report(site_dir)


def size_report(site_dir):
    """What a cold reader downloads, as (bytes, text).

    Printed on every build. The payload is the constraint these sites keep
    having to defend, so a regression belongs in the build log.
    """
    site_dir = Path(site_dir)
    initial = (site_dir / "index.html").stat().st_size
    archive = sorted((site_dir / "m").glob("*.html"))
    lines = [
        f"  {'index.html':<16}{initial / 1024:8.1f} KB   (budget {BUDGET_BYTES / 1024:.0f} KB)",
        f"  {'archive':<16}{sum(p.stat().st_size for p in archive) / 1024:8.1f} KB"
        f"   ({len(archive)} month page{'s' if len(archive) != 1 else ''})",
    ]
    if initial > BUDGET_BYTES:
        lines.append(f"  OVER BUDGET by {(initial - BUDGET_BYTES) / 1024:.1f} KB")
    return initial, "\n".join(lines)


def build(data_dir, site_dir, now=None):
    corpus = model.load(data_dir)
    return write(site_dir, corpus, now or datetime.now(tz=UTC))
