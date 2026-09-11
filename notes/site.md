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
