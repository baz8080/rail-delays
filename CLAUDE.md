# Working in this repository

Two things live here: `delay_cause`, which reads what an Irish Rail service
message says went wrong, and `delay_site`, a static site generator that turns
the collected notices into https://baz8080.github.io/rail-delays. **Both run on
the standard library alone** - `pyproject.toml` declares no runtime dependencies,
and the one build-time dependency is the shared `statusui` design layer in the
`site` group. Keep it that way.

**There is no collector here and there will not be.** `baz8080/lifts` polls the
feed every 30 minutes and writes it to `baz8080/lifts-data`; this repository
reads those logs. One endpoint returns the whole feed in one response, so a
second poller would double the request rate on a credentialed API for bytes that
are already on disk. `baz8080/lifts` `notes/delays-site.md` has the numbers.

```bash
uv run python -m delay_site --data-dir <dir>              # build out/site/
uv run python -m delay_cause --data-dir <dir> report      # every notice beside the cause it states
uv run python -m delay_cause --data-dir <dir> unread      # clauses no rule read, and notices stating none
uv run python -m delay_cause --data-dir <dir> golden      # regenerate tests/fixtures/delay-cause-golden.json
uv run --group dev ruff check
uv run python -m unittest discover -s tests -t .
```

Plain `python3` works for all of these too; uv only pins the interpreter, to the
3.14 in `.python-version`. `requires-python` says **3.11**, the same floor the
collector repository keeps for Raspberry Pi OS bookworm, so that code can move
between the two without a syntax surprise. CI runs the tests on both.

The data is `baz8080/lifts-data`, normally checked out at `../lifts-data`. Set
`LIFT_STATUS_DATA_DIR` to it or pass `--data-dir`. `tests/test_site_real.py`
skips without it; everything else runs on a bare clone.

## The UI is shared - change it upstream

Tokens, base CSS, the row/bar/card components and the JS helpers come from
[`../statusui`](https://github.com/baz8080/statusui), a **uv git dependency
pinned in `uv.lock`** and inlined into every page at build by
`statusui.assemble()`. Edit it there, push, then `../statusui/rollout.sh` bumps
the pin in each site. This site's own rules are `delay_site/site.css`.

This is the fourth consumer, after uisce, esb and lifts. `rollout.sh` upstream
does not know about it yet.

## Data-shape traps

- **`start` is the train's scheduled departure**, not the start of the
  disruption. "The 09:50 Dublin Connolly to Belfast" carries `start`
  2026-08-28T09:50:00. On a lift notice in the sibling repository the same field
  means something else entirely.
- **`eventStops` describes what is affected right now and is not an identity.**
  It empties part-way through a notice's life on the same polls `locationCodes`
  does (186 of the 361 notices are seen both with a route and without one), and
  on a multi-leg notice it is the list of services still affected, so its first
  leg moves as they recover. A key that takes the field as it arrives gives 671
  disruptions where there are 392; `model.resolve` repairs both shapes.
- **The head carries the minutes**, so it changes at almost every poll. Nothing
  may key on it.
- **The apology sentence ends in the word "caused".** 300 of the 416 notices
  carry it and two carry a real "caused by", so `delay_cause.text` strips the
  template before anything reads a cause.
- **Four "Test HIM Alert Message" notices are in the corpus**, telling customers
  to ignore them. They are live tests on the real feed.
- **A run that failed is not a run that saw nothing.** The horizon is the newest
  successful run, and days past it are "no data", never a quiet day.

## Settled - don't re-litigate without reading the note

| Decision | Where |
|---|---|
| One disruption is one event, not one notice: keyed on `start` plus the resolved `eventStops` route, because Irish Rail re-words a live notice as it develops and the collector's key fractures on the head | `notes/site.md` § One disruption is one event |
| `eventStops` empties out like `locationCodes`, and on a multi-leg notice its first leg moves as services recover, so the route is resolved from the `start` rather than taken as it arrives and a multi-service start keys on the start alone. `start` alone for everything was rejected: it would have merged 6 same-minute pairs into 3 events that never happened | `notes/site.md` § `eventStops` empties out, § A multi-leg `eventStops` |
| A day's family breakdown does not partition the day, because one disruption can name a fault and its knock-on. The row carries the total separately and nothing sums the breakdown | `notes/site.md` § The day bar |
| The subject is disruption, not the word "delay": a head filter drops "Services suspended between Newry and Portadown", the worst event on the corpus. Lift outages, test alerts and reduced-capacity notices are excluded, the last of those counted and named on the page because it is a third of the feed, and judged on every wording a disruption ever had rather than its newest | `notes/site.md` § What counts as a disruption |
| Minutes are never summed, anywhere. The naive total overstates by 1.26x and mixes one observed train with a forecast over a line. Each disruption shows the worst figure it ever claimed, prefixed "at least" because a range reads at its lower bound | `notes/site.md` § The minutes are never added up |
| No percentage and no on-time performance: there is no published roll of services that ran, so there is nothing to divide by | `notes/site.md` § No denominator |
| The day bar's bands are cut from the corpus and not from round numbers, and a real-corpus test fails when the newest month stops spreading across them | `notes/site.md` § The day bar |
| A notice's cause is read from its own clause into eleven corpus-derived categories, each with a family. A cause naming another delay is a `consequence`, never a peer of a signalling fault; "an incident on the line" is never decoded; "an operational issue" is a non-answer with its own category | `notes/cause-reading.md` |
| No routes view, no feeds, no CSV, no shards, and nothing about when a disruption ended. Each one is a decision with a reason | `notes/site.md` § What the page does not have yet |
| A delays site is a repository of its own reading `lifts-data`, not a second collector and not a poll target | `baz8080/lifts` `notes/delays-site.md` |

Decisions go in `notes/`, dated, with the rejected alternatives and their
numbers. Add a row here when one closes something off - this file carries
pointers only, never the rationale, or it becomes the thing it exists to fix.

## Comments

Comments earn their place or they go. Say **why**, not what - never a paraphrase
of the line below, a heading for an obviously-named block, or an explanation of a
standard flag. What does earn a comment: a reason the obvious approach was
rejected, a dependency nothing else records, a constraint from outside the code.

One line where one will do. If the reasoning needs a paragraph it belongs in the
commit message, the PR, or `notes/` - not above the line.

## Punctuation

**No em dashes.** Not in the site's prose, the code comments, `notes/`, commit
messages, PR bodies, issue bodies or the replies in a session. The house dash is
a spaced hyphen - like this one. `scripts/no-em-dash.sh` checks the tracked
files; the prose outside the repository is on whoever is writing it.

## Before changing anything the site publishes

`tests/test_site_real.py` runs the pipeline against the real corpus: every
disruption lands in exactly one month, no lift or escalator notice leaks in,
folding never loses a sighting, two disruptions never share a key, no page
states a percentage, and the newest month is inside the budget. If it fails,
something moved in the model or in the feed - find out which before adjusting
the model to make it pass.

`tests/fixtures/delay-cause-golden.json` is every cause `delay_cause` reads,
beside the head and body it read it from, for all 416 notices on the corpus -
the ones it finds nothing in included, because a pattern that starts finding a
cause where there is none is the failure those pin against. It replays pinned
inputs, so it needs no data checkout. Corpus growth passes; a withdrawn wording
stays as a test vector. Regenerate with `golden`, read the diff, commit it with
the change.

The 500 KB initial-load budget is printed by every build and asserted by the
render tests. It holds because a reader arriving cold gets one month and never
the archive; keep it that way.

## Looking at the built site

```bash
python3 -m delay_site --data-dir ../lifts-data                   # writes out/site/
/opt/pw-browsers/chromium-1194/chrome-linux/chrome --headless --no-sandbox \
  --disable-gpu --hide-scrollbars --window-size=980,1500 --virtual-time-budget=3000 \
  --screenshot=/tmp/site.png file://$PWD/out/site/index.html
```

**Its layout viewport never goes below 500px**, whatever `--window-size` says, so
a rule under a narrower breakpoint can only be seen by raising it in a copy of
the built page, and an element hanging off the right edge of the PNG is not
proof of overflow - compare `scrollWidth` with `clientWidth` instead.
