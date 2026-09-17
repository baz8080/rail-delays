# What the site publishes - 2026-09-11

The first version. It reads `lifts-data/raw/messages-*.jsonl`, folds the notices
into disruptions, reads a cause out of each one and writes a page per month.
There is no collector here and there will not be: the sibling repository
`baz8080/lifts` polls the feed and its `notes/delays-site.md` records why a
second one would be waste.

Corpus throughout: the raw logs between the first poll on 2026-08-08 21:30:55Z
and 2026-09-11, 1620 successful runs.

## One disruption is one event, not one notice

Irish Rail re-words a live notice as things develop. The closure between Thurles
and Limerick Junction on 17 August is nine wordings over eight hours; the
Westport train on 4 September is sixteen. Counting notices counts the author's
keystrokes.

The collector's identity key cannot be reused. It is `head` + sorted
`locationCodes` + `start`, and on a delay notice the head carries the minutes:
"+15mins delayed" becomes "+21mins delayed" at the next poll, so the key
fractures on the field that changes most. 48 of the 322 identity groups on the
corpus already carry more than one head. That key is right for the lift site,
where a head is a fixed sentence, and it is not portable here.

**The key is `start` plus the `eventStops` origin and destination.** `start` on a
delay notice is the train's scheduled departure, not the start of the
disruption, and that is what makes it work: it identifies a train on a day.
362 of the 370 starts on the corpus carry exactly one route; of the 8 that carry
two, 6 are two real services leaving at the same minute and stay apart, and the
other 2 are the case below.

### `eventStops` empties out, exactly as `locationCodes` does

This is the trap, and it is the same one twice. `baz8080/lifts` found that
`locationCodes` goes empty part-way through a notice's life: 288 of the 497
non-lift notices lose it before they leave the feed and 21 never carry it, while
no lift or escalator notice has ever done it once.

`eventStops` goes with it, on the same polls. **186 of the 361 notices here are
seen both with a route and without one**, and in every one of those the `start`
holds still while the stops go. A key that takes the field as it arrives splits
one event into two, which is the bug this whole module exists to avoid: it gave
671 disruptions on a corpus that has 392.

So `resolve` fills the route back in. A sighting that lost its stops takes the
route its `start` carries, which is unambiguous for 362 of 370 starts; under a
start that carries two, it is matched on its wording instead. A wording alone is
never enough and is only ever consulted inside a single start: "Customer Notice:
This train has reduced capacity" is boilerplate on 36 different routes.

Rejected: **`start` alone as the key.** It merges only 12 more notices on this
corpus and it would have merged the 6 same-minute pairs into 3 events that never
happened. The route is cheap to resolve and the merge is not reversible.

### A multi-leg `eventStops` is not a journey, and its first leg moves

Found in review, after the above had already shipped. 324 of the sightings carry
one leg, and for those `eventStops[0]` is the service the notice is about. **The
rest carry up to ten, and there the list is the services still affected** - it
grows as an incident spreads and shrinks as they recover.

The Connolly signalling failure of 2026-08-20 is the worked example. One notice,
one `start`, and its leg list ran 1, then 4, then 10, then 7, with the first leg
changing from Donabate to Lansdowne Road into Maynooth to Dublin Connolly on the
way. Keyed on the first leg that is four disruptions, none of which happened.
The Westport disruption of 2026-09-03 does the same.

So a `start` whose notice ever named more than one service keys on the `start`
alone, and its route reads "Several services". 8 of the 370 starts are of that
shape. Decided per start and not per sighting, because the same notice is
single-leg at one poll and multi-leg at the next - that is precisely how the
Connolly one split.

The two repairs are the same fact twice: **the feed's location fields describe
what is affected right now, and are not an identity.** `locationCodes` empties,
`eventStops` empties and also re-orders. Anything keyed on either has to be
resolved from something that holds still, and `start` is the only field that
does.

## What counts as a disruption

Everything the feed carries except three things, and the exclusions are the
decision worth recording.

**Lift and escalator outages** go to the sibling site. A notice appearing on
both would be one outage counted twice across two sites, and a real-corpus test
fails if one leaks in.

**The four "Test HIM Alert Message" notices** are live tests published to the
real feed, telling customers to ignore them. Dropped by name, because their name
is the only thing that distinguishes them.

**Trains listed as having reduced capacity.** This one is large enough to argue
about: "Customer Notice: This train has reduced capacity" is **130 of the 392
disruptions, a third of the corpus, from two distinct headlines**, and almost all
of them give "operational reasons" as the cause. It is a template about the
seating and the catering, not about a train running late, and with it in the page
was mostly a list of identical entries saying nothing. It is counted separately
and the count is printed above each month's list: a third of the subject going
missing without a number beside it is the kind of thing this family does not do.

*Every* wording, not the newest one. A train can carry a capacity banner and a
delay banner at the same `start`, and reading only the latest filed three real
disruptions as seating notices - two technical faults and a bus transfer - which
took them off the site entirely. Found in review.

Rejected: **"every notice whose head says delay".** The prototype's filter, and
it drops exactly the events that matter most. "Services suspended between Newry
and Portadown", the worst disruption on the corpus, never uses the word; nor
does "All services cancelled following a vehicle collision at Ballyhaunis". The
subject is disruption, and the feed's own vocabulary for it is not one word.

## The minutes are never added up

176 of the 365 notices carry a minute figure. The prototype summed them into a
headline: "1,476 minutes of claimed delay" for August.

That figure is not defensible, for two separate reasons.

**It counts one event several times.** The figure is re-stated every time the
notice is re-worded. Reduced to one figure per disruption the corpus total falls
from 4584 to 3625, so the naive sum **overstates by 1.26x** - and that is with
the generous reduction, taking the worst figure each disruption ever claimed.

**The figures are not the same kind of number.** "This service departed +25
minutes behind schedule" is one train, observed. "+90 minute delays can be
expected" is a forecast over every train on a line. Donabate to Lansdowne Road
reads 25, then 60, then 80, then 90 as one signalling failure grows; Thurles to
Limerick Junction reads 60, then 34, then 30 as one closure eases. Adding those
together produces a number that is about nothing.

**Settled: no total anywhere, ever.** Each disruption shows the worst figure its
notice ever claimed, and the page says "at least", because a range like
"+15/20 minutes" is read at its lower bound. `tests/test_site_render.py` fails
if a total in minutes appears above the footer.

Worst rather than newest, because a disruption that eased from +60 to +30 was
still a +60 disruption, and one that grew from +25 to +90 was never a +25 one.

## No denominator, in this subject too

The lift site cannot say what share of lifts were working, because the feed
names a station only when something is wrong with it. The same hole is here and
it is wider: there is no published roll of the services that ran, so this site
can say how many disruptions were listed and can never say what share of trains
were late. "On-time performance" is not derivable from this feed at any effort.

The footer says so in the page's own words, and a real-corpus test asserts that
no month page states a percentage above the footer.

## The day bar

One cell per day, banded by how many disruptions were first listed that day,
with the family breakdown in the caption. The same component, and the same
caption listener, as the three sibling sites.

**The breakdown does not partition the day.** A disruption naming a signalling
fault and the knock-on it caused counts in two families, so the families add to
more than the total, and the row carries both rather than letting anything sum
the breakdown. Summing it overstated seven days in September 2026 and painted
one of them a band too dark. The caption says "16 listed, naming ..." for that
reason.

**The cuts come from the corpus, not from round numbers.** Over the 31 days to
11 September the daily count runs 1 to 24 with a median of 6. The first version
banded at 1-2, 3-5, 6-9 and 10+, and almost every day came out in the top band:
the bar was one colour and said nothing. The bands are 1-3, 4-8, 9-16 and 17+,
which split those 31 days roughly evenly.

That is a judgement about one month of data and it will want re-reading.
`tests/test_site_real.py` fails when the newest month puts every day in fewer
than three bands, so the re-reading is prompted rather than remembered.

A day past the collection horizon is drawn as no data, never as a quiet day, and
so is every day before the first poll. That distinction is the sibling sites' and
it is not negotiable: the feed shows only what is up now, so an unwatched day is
not a day with nothing on it.

## What the page does not have yet

Deliberate, and each of them is a decision rather than a gap to be filled
without thinking:

- **No routes view.** Ranking routes by notice count is the prototype's headline
  and it is the one most likely to be read as performance, which it is not: a
  route with more trains gets more notices. It wants a denominator that does not
  exist, or a caveat louder than the chart.
- **No feeds and no CSV.** The lift site has both. They are cheap to add and
  they should follow the shape settling down, not lead it.
- **No shards.** The newest month is 79 KB against a 500 KB budget, and a month
  page holds one month whatever the archive grows to. When a month stops
  fitting, the per-disruption records move out the way the lift site moved its
  outages.
- **Nothing says when a disruption ended.** The feed has no resolved field, and
  a notice leaving it means the author took it down. The lift site says "no
  longer listed" and measures the listing; this site shows when a disruption was
  first listed and says nothing about the end, because a delay notice's listing
  is a few hours of an author's attention rather than a measurement of anything.

## The content pass - 2026-09-12

Everything above was written in one sitting and never read back. uisce, esb and
lifts each had a pass over their words after the numbers settled, and the shapes
they arrived at are in their own notes; this is the same pass over this page,
against those three. Nothing here changed what is counted. Corpus: the logs to
2026-09-12 05:01Z, 262 disruptions and 130 capacity notices.

**A day still to come is not a day with no data.** On 12 September the bar drew
eighteen grey cells captioned "no data" for days that had not happened. The three
sibling sites have carried two codes for this from the start - cell 8 "no data
collected for this day", cell 9 "still to come" - and paint them the same grey,
keeping the second out of the key because nobody needs a legend to be told that
tomorrow has not happened. `day_counts` takes the build clock now and marks the
row; `render.EMPTY_LABEL` carries both captions.

**The day caption answered one question twice.** A notice that named nothing
counted under no family at all, and a notice saying "an operational issue"
counted under `unstated`, so a caption could read "7 named no cause at all ... 1
no cause given" - two phrasings of the same answer, in one sentence, from the
page's own internals. They are merged into one count. The distinction is real and
the disruption's own row still carries it as a tag; a reader hovering a day cell
is not asking it. The caption also says "named" once and elides it after, because
a caption is a sentence: "17 listed, 7 named something that went wrong, 6 a
knock-on from another delay, 4 no cause at all".

**The fourth tile said again what the next section says.** It named the month's
most common fault, which is the first row of the ranked panel eight lines below
it. It counts the notices that named nothing instead - 20 of the 105 in
September - which nothing else on the page carried. It was also the one tile
whose value was text, and at 24px bold it set the height of the whole row.

**The bare timestamp moved into the phrase it measures.** The row carried
"11 Sep, 17:00" floating at its top right, explained only by a `title` a touch
screen cannot open. It reads "first listed 11 Sep, 17:00" now, on the line with
the re-wording count, which is where esb put the same thing and for the same
reason. The route moved up into `.where`, which is the heading slot the sibling
rows use, and the minutes into `.when`: "at least 25 minutes late" rather than
"at least +25 min". "Re-worded 1 time" is "re-worded once".

**"No cause given" goes where the notice also named a cause.** Five disruptions
were re-worded between a named fault and "an operational issue", and their rows
carried both tags at once, which reads as the page contradicting itself. The
reading keeps both; the row shows the answer only when it is the whole answer.

**The stale box became the stamp.** `Collected to 2026-09-12 05:01 UTC` and,
under it, a bordered box reading "The newest data here is 17 hours old". The
sibling static pages carry one thing, `Data to <stamp>`, and redden the stamp
past `STALE_AFTER`; the box was a second way of saying it and a local override of
a shared rule. The site.css `.stale` block went with it. The banner says
"September 2026 so far" while the month is the one still collecting, as the
sibling banners do, and the build clock left the footer: a reader cares where the
record stops, not when the page was assembled.

**The footer took the sibling shape.** "Why there are no totals in minutes" and
"Why there is no percentage" were two disclosures defending the page against
questions nobody had asked yet; they are three paragraphs of one
"What this cannot tell you", which is what esb calls its own. "How to read a
disruption" is new and both esb and lifts carry one. The last line ends "not
affiliated with Iarnród Éireann." like all three.

### Rejected

**Showing only the notice's body, as the lift site does.** The rows print Irish
Rail's headline and then the sentence under it, which looked like the same thing
twice. It is not: 232 of the 262 heads are not verbatim inside their own body,
and reading the widest gaps, the head is where "Train held at Clongriffin",
"Platform 1 Connolly", "All services cancelled" and "a bus transfer will operate
between Belfast and Newry" are stated. The lift site can drop the head because a
lift notice's head is "Lift(s) out of order" and nothing else. Both stay.

**An age in words on the banner, as the app pages show.** `freshness()` runs in
the browser against the reader's clock. These pages have no JS but the caption
listener, so the only age they could print is the one true at build time, which
is wrong the moment the page is cached. The stamp is a fact that stays true.

## How this gets published - 2026-09-12

The site had not moved since the manual build of 2026-09-11 20:29Z, with the
data a poll behind it from 05:01Z the next morning. Nothing was broken: the
first two deploys failed before Pages was pointed at Actions and have been fine
since, and the build takes under a second.

**Nothing asks for the build.** `lifts-data/.github/workflows/build-site.yml`
posts one dispatch, to `baz8080/lifts/actions/workflows/pages.yml`, and that is
what keeps the lift site within a minute of the data landing. This repository
reads the same logs and is not on that list, so its only cadence is the two
crons in `pages.yml`, which GitHub runs hours late when it runs them: the
07:20Z one did not fire at all on 2026-09-12.

The fix is a second step in `lifts-data`, the same three lines pointed here:

```yaml
      - env:
          GH_TOKEN: ${{ secrets.SITE_BUILD_TOKEN }}
        run: |
          gh api -X POST \
            repos/baz8080/rail-delays/actions/workflows/pages.yml/dispatches \
            -f ref=main
```

`SITE_BUILD_TOKEN` is a fine-grained token with Actions: write on
`baz8080/lifts`; it needs the same on `baz8080/rail-delays` before that step can
work. Both are owner actions in another repository, so they are not done here.
Until they are, the crons stand and a stale page says so in its own stamp.

## The day bar's colours and words, reviewed - 2026-09-17

A reviewer looking at a build against live data (September 2026, 41 collected
days at review time) found three real problems, none of them the counting.

**"Nothing" and "1 to 3" read as one colour.** `--good` and `--fair` are both
dark, moderately saturated greens at the width a day box actually renders, and
the eye cannot split them apart in a 22px bar. Dropped `--fair` from the run
entirely rather than picking a lighter shade for it: esb's own day cells solve
the same problem the same way, skipping straight from `--good` to `--warning`.

**One band fewer, cut where the corpus splits evenly.** Over the 41 days to
2026-09-17 the daily count is 0 on 6 days and otherwise runs 1 to 25; split
three ways rather than four it is 9 days at 1-3, 14 at 4-9, 12 at 10 or more,
which is as even a three-way split as the corpus offers. The top band stays
open-ended ("10 or more") rather than "10-29" plus a "30+" that has never
fired: nothing in the corpus has reached 30, and a legend entry nothing has
ever painted is a legend entry that lies about what the bar can show.

**"Nothing listed" and "no data" read as the same claim.** Both are "no-word"
sentences about a day, and a reader hovering two adjacent boxes and getting
"nothing listed" then "no data collected for this day" reasonably asked what
the difference was. The no-data caption now names the actual mechanism instead
of repeating "data": "the collector missed this day."

**The hover hint took uisce's exact wording.** "Hover a day for what it held"
became "Hover a day in a bar for its detail," matching uisce's own hint
character for character - there was no reason for a third phrasing of the same
instruction.

**Rejected: printing the count inside each box.** A day box is a few pixels
wide at 31 to a bar; a two-digit count would either be unreadable or force the
bar wider than the card, and no sibling site prints digits in its day cells for
the same reason. The count already reaches the reader through the hover
caption, which was the point of adding the caption listener in the first
place.

## More words read back, from a live review - 2026-09-17

The same review pass caught four more with a specific fix each.

**The header repeated the footer.** "and what each one said went wrong" on the
header's sub line said the same thing the row cards already say, in the first
sentence a reader hits. Dropped; the sub line now names only what the notices
are.

**The disclosure's shape didn't match its sibling.** "A notice going up is the
only signal there is" stood alone; lifts pairs it with what a notice's absence
means, in one sentence: "A notice going up is the only signal, and a notice
coming down is the only other one." Taking the pairing without also taking
lifts' claim that a disruption "ends" when its notice does: this site does not
track an end at all (see "Nothing says when a disruption ended" above), so the
second sentence stays "a notice leaving it just means the author took it down,"
not "an outage ends here."

**Two footer links pointed at a feed nobody asked to read from here.**
"Collected data" and "Lift outages" left the footer; "Source code" is what a
reader of an independent site wants next to "not affiliated," and the other
two repeated what "How this measures" already says in prose.

**"Cell" only ever appears in this family's code and notes, never to a
reader.** None of uisce, esb or lifts names the day square for a reader either
- they only say "Hover a day...". "One cell a day" became "One box a day."

## Hovering did nothing - 2026-09-17

A reviewer hovered a day box on the live preview and got nothing. Two separate
bugs, not one:

**`bindDayCaption()` was never called.** `caption.js` only defines the
function; something has to invoke it. esb, lifts and uisce all call it at the
bottom of their own script tag. This page inlined the script and stopped
there, so the listener was never attached - not since the caption feature was
added, on any build this site has ever shipped.

**The bar and its caption had no shared host.** `bindDayCaption`'s handler
does `cell.closest(".row, .card")` to find the day box's own `.daycap`, the
same way lifts wraps a month's bar and its caption in one `<div class="card">`.
Here the bar, the caption line and the legend sat as bare siblings of `<main>`,
so `closest` found nothing and the assignment silently did nothing even once
the call was added.

Fixed both: `bindDayCaption();` runs after the inlined script, and the bar,
`.daycap` and legend are wrapped in one `<div class="card">`. Verified by
dispatching a synthetic `pointerover` at a built page in headless Chromium and
reading the `.daycap` text back, not by re-reading the markup - which is how
the second bug was missed the first time a reply here claimed hovering worked.
`TheHoverCaptionActuallyFires` pins both: the script calls what it defines, and
exactly one `</div>` sits between the bar opening and the caption div, so a
future edit that pulls them apart again fails a test instead of a reader.

## The day caption stopped naming families - 2026-09-17

A reviewer called the caption "awful" on sight: "16 listed, 5 named planned
works, 5 no cause at all, 4 something that went wrong, 3 a knock-on from
another delay" is a sentence built for someone auditing the model, not a
reader hovering a box. It also invited the exact question it got: the parts
summed to 17 against a total of 16, which is documented and correct (a
disruption naming a fault and its own knock-on counts in both families, "The
day bar" above) but reads as a mistake to anyone who has not read that note.

The caption is now the count alone: "16 disruptions". The breakdown was never
the only place that information lived - each disruption's own row already
carries its cause - so nothing is lost, only a sentence that was answering a
question a box hover does not need to answer. `FAMILY_LABEL` left `render.py`
with it: nothing else read it.

Two more words changed on the same pass. "Every day of September 2026" became
"September 2026" - the tabs above it and the banner both already say the
month, and the heading did not need a fourth restatement in three words.
"Hover a day in a bar for its detail," which had matched uisce's own hint
character for character since the last review, was pointed back to plainer
words: "Hover over a day for details."
