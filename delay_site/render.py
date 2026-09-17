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

from delay_cause import CONSEQUENCE, LABEL, PROXIMATE, UNSTATED
from delay_cause.text import readable

from . import model

BASE_URL = "https://baz8080.github.io/rail-delays"

TEMPLATES = Path(__file__).parent
SITE_HTML = TEMPLATES / "site.html"
SITE_CSS = TEMPLATES / "site.css"

# What a reader downloads before touching anything. One month of the archive,
# and it has to stay that way: the site is meant to run for years.
BUDGET_BYTES = 500 * 1024

# Client-side, not a server-side page: every row already ships inside the
# month's own budget, so this only changes what is on screen at once.
PAGE_SIZE = 10

# Day-cell codes, by how many disruptions were first listed that day. Bands
# rather than a count, since the caption already carries the exact number.
# Corpus-derived cuts, split roughly evenly past zero (9 days at 1-3, 14 at
# 4-9, 12 at 10+); the top band stays open-ended because nothing has reached
# 30 - a "30+" nothing has ever painted would be a legend entry that lies.
BANDS = ((1, "0"), (4, "1"), (10, "2"))
OVER_BAND = "3"
NO_DATA = "8"
FUTURE = "9"

BAND_LABEL = {
    "0": "nothing",
    "1": "1 to 3",
    "2": "4 to 9",
    OVER_BAND: "10 or more",
    NO_DATA: "no data",
}

# Two cells with no count: a day not yet reached is not one the collector
# missed. NO_DATA names the collector rather than "data" so it doesn't echo
# "nothing listed" two cells over.
EMPTY_LABEL = {
    NO_DATA: "the collector missed this day",
    FUTURE: "still to come",
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
    """What a day box says on hover: a plain count, not a family breakdown.

    A breakdown could say more than the total - a disruption naming a fault
    and its own knock-on counts in both families - and each disruption's own
    row already carries its cause.
    """
    counts = row["counts"]
    if counts is None:
        return EMPTY_LABEL[FUTURE if row.get("future") else NO_DATA]
    total = row["total"]
    if not total:
        return "nothing listed"
    return f"{total} disruption" + ("" if total == 1 else "s")


def day_bar(rows):
    """The month's day cells, with the day's count in each caption."""
    cells = []
    for row in rows:
        code = FUTURE if row.get("future") else band(row["total"])
        cap = f"{statusui.fmt_day(row['day'])}: {day_caption(row)}"
        cells.append(f'<i class="b{code}" data-cap="{_esc(cap)}"></i>')
    return "".join(cells)


def legend():
    return "".join(
        f'<span><i class="b{code}"></i>{_esc(BAND_LABEL[code])}</span>'
        for code in ("0", "1", "2", OVER_BAND, NO_DATA)
    )


def tiles(disruptions):
    """Four counts of the month's disruptions.

    The fourth is not the month's most-named fault - that is the ranked panel
    below. None of the four partition the month: a fault and its own knock-on
    count in both the second and the third.
    """
    named = sum(1 for d in disruptions if d.origins)
    knock_on = sum(1 for d in disruptions if CONSEQUENCE in d.families)
    silent = sum(1 for d in disruptions if not (set(d.families) - {UNSTATED}))
    values = [
        (len(disruptions), "disruptions listed"),
        (named, "named a cause"),
        (knock_on, "blamed congestion or an earlier service"),
        (silent, "named no cause"),
    ]
    return "".join(
        f'<div class="tile"><div class="v">{value}</div>'
        f'<div class="k">{_esc(key)}</div></div>'
        for value, key in values
    )


def routes_named(disruptions):
    return len({d.route for d in disruptions if d.route != model.UNNAMED_ROUTE})


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


def shown_causes(causes):
    """The causes a row carries as tags.

    "No cause given" is shown only when it is the whole answer - beside a
    real cause it would read as the page contradicting itself, though the
    reading itself keeps both.
    """
    named = tuple(c for c in causes if c.family != UNSTATED)
    return named or causes


def case(disruption):
    """One disruption: what it is, what is known about it, then its own words.

    The time sits inside the phrase it measures rather than floating at the
    top right: a bare timestamp does not say what happened then, and the
    `title` that used to explain it is unopenable on a touch screen.
    """
    chips = "".join(_chip(c) for c in shown_causes(disruption.causes))
    if not chips:
        chips = '<span class="chip chip-none">No cause given</span>'
    minutes = (
        f'<span class="when">at least {disruption.minutes} '
        f'{"minute" if disruption.minutes == 1 else "minutes"} late</span>'
        if disruption.minutes is not None
        else ""
    )
    bits = [f"first listed {statusui.when(_short(disruption.first_seen))}"]
    if len(disruption.updates) > 1:
        times = len(disruption.updates) - 1
        last = statusui.when(_short(disruption.updates[-1][0]))
        bits.append(
            f"re-worded once while it was listed, at {last}"
            if times == 1
            else f"re-worded {times} times while it was listed, last at {last}"
        )
    return (
        '<div class="case">'
        '<div class="top">'
        f'<span class="where">{_esc(disruption.route)}</span>{chips}{minutes}'
        "</div>"
        f'<div class="sum">{_esc(" · ".join(bits))}</div>'
        f'<div class="txt head">{_esc(readable(disruption.head))}</div>'
        f'<div class="txt">{_esc(readable(disruption.text))}</div>'
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


def paged_cases(disruptions):
    """The month's cases, chunked into `PAGE_SIZE`-row pages.

    Page 1 renders visible, so a reader with no JS still gets the newest page
    rather than nothing; `pageDelays()` moves between the rest.
    """
    ordered = sorted(disruptions, key=lambda d: d.first_seen, reverse=True)
    if not ordered:
        return '<p class="empty">No disruption notice was listed this month.</p>'
    pages = [ordered[i : i + PAGE_SIZE] for i in range(0, len(ordered), PAGE_SIZE)]
    body = "".join(
        f'<div class="page"{"" if n == 0 else " hidden"} data-page="{n + 1}">'
        + "".join(case(d) for d in page)
        + "</div>"
        for n, page in enumerate(pages)
    )
    if len(pages) < 2:
        return body
    return (
        body + '<div class="pager">'
        '<button type="button" class="prev" disabled>Newer</button>'
        f'<span class="pagenum">Page 1 of {len(pages)}</span>'
        '<button type="button" class="next">Older</button>'
        "</div>"
    )


def month_page(ym, disruptions, corpus, months, now, template, css):
    rows = model.day_counts(corpus.disruptions, ym, corpus.horizon, now)
    cases = paged_cases(disruptions)
    # Past STALE_AFTER the stamp itself goes red - an age in words would only
    # be true at build time, and this page has no clock at read time to fix it.
    observed = statusui.stamp(corpus.horizon)
    if now - corpus.horizon > model.STALE_AFTER:
        observed = f'<span class="stale">{observed}</span>'
    routes = routes_named(disruptions)
    count = len(disruptions)
    capacity = sum(1 for d in corpus.capacity if d.day.strftime("%Y-%m") == ym)
    capacity_note = (
        f"{capacity} train{'s' if capacity != 1 else ''} had reduced capacity, but "
        f"{'they are' if capacity != 1 else 'it is'} not counted as a disruption."
        if capacity
        else ""
    )
    # "so far" while the month is the one still collecting, as the sibling
    # banners say it: a headline for a finished month is a final figure.
    so_far = " so far" if ym == _dublin(corpus.horizon).strftime("%Y-%m") else ""
    headline = (
        f"<b>{_esc(month_label(ym) + so_far)}:</b> "
        f"{count} disruption{'s' if count != 1 else ''} listed"
        + (f" across {routes} route{'s' if routes != 1 else ''}" if routes else "")
    )
    return statusui.assemble(
        template,
        {
            "SITE-CSS": css,
            "CANONICAL": f"{BASE_URL}/" if ym == months[-1] else f"{BASE_URL}/m/{ym}.html",
            "MONTH": _esc(month_label(ym)),
            "HEADLINE": headline,
            "META": f"Data to {observed}",
            "TABS": tabs(ym, months),
            "TILES": tiles(disruptions),
            "BAR": day_bar(rows),
            "LEGEND": legend(),
            "ORIGINS": origins_panel(disruptions),
            "CASES": cases,
            "CAPACITY": _esc(capacity_note),
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
