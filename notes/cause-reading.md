# Reading a cause out of a notice - 2026-09-11

Written in `baz8080/lifts`, where the corpus and the collector are, and moved
here with `delay_cause` when this repository was created. The decision about
where a delays site lives, and what the collector does and does not do for it,
stayed there: `notes/site.md` in that repository.

Corpus throughout: the 416 distinct (head, text) pairs in
`lifts-data/raw/messages-*.jsonl` between the first poll on 2026-08-08 21:30:55Z
and 2026-09-11, over 1620 successful runs.

## Reading a cause

### What the corpus contains

113 distinct cause clauses, introduced by four phrases: "due to", "as a result
of", "caused by" and "following". Every noun phrase in them is one of eleven
things. 335 of the 416 notices state a cause the reader takes something from,
367 causes in all; 81 state nothing, 43 of those being lift and escalator
notices, which say what is broken in the head and never say why.

| category | causes | family | the wording it comes from |
|---|---|---|---|
| `technical` | 111 | origin | "a technical issue" (45 bare), "a mechanical issue" (21 bare), and onboard/on-the-train variants; "train failure", "a broken down train", "a necessary loco swap", "a train set replacement" |
| `signalling` | 44 | origin | "a signalling issue" (29 bare), at Dromod, in Athlone, between Donabate and Lansdowne Rd |
| `incident` | 41 | origin | "an incident on the line" (27 bare), "a tragic incident", "a serious incident being attended by emergency services" |
| `knock_on` | 41 | consequence | "the late arrival of an incoming service" (10), "an earlier service delay", "an earlier DART cancellation", "late running of an earlier train", "an earlier stopped train" |
| `unspecified` | 27 | unstated | "an operational issue" (22), "operational reasons", "operational issues" |
| `passenger` | 26 | origin | "a passenger issue" (16 with its onboard variants), "an ill passenger onboard" (6), "a medical emergency on the platform in Killiney", one delay "awaiting an ambulance" |
| `congestion` | 25 | consequence | "congestion", "congestion on the line", "congestiion" |
| `vehicle_strike` | 19 | origin | "a vehicle striking a bridge", "a vehicle hitting a level crossing near Mullingar", "Level crossing struck by a vehicle", "a train has struck a tractor crossing the line", "a vehicle collision at Ballyhaunis" |
| `planned` | 11 | planned | "planned works" (7), "engineering works at Waterford (Plunkett)" (3), "planned maintenance" (1) |
| `infrastructure` | 11 | origin | "a temporary speed restriction" (9), "a power supply issue" (2) |
| `level_crossing` | 11 | origin | "a level crossing issue", four of them at Sutton |

The prototype's five were technical, signalling, incident, operational and
other. **96 of its 254 notices - 38% - were in the last two.** That is what
reading the clause properly buys, and it buys it in four separate ways.

### One: three markers were not read at all

The prototype read "due to". "As a result of", "caused by" and "following"
introduce a cause on 32 clauses, and every one of them landed in "other":

- "11:25 Cork/Heuston is expected to depart +40mins delayed as a result of an
  earlier technical issue." Filed as other; it is a technical fault, on an
  earlier train.
- "Services have resumed through Longford following a report of a vehicle
  striking a bridge." Filed as other; a road vehicle hit the railway.
- "Delays of up to +20mins can be expected to Maynooth services as a result of a
  technical issue onboard the 06.17 Connolly/Maynooth." Filed as other.

### Two: a delay whose cause is a delay is not a cause

The second-largest group in the corpus names another delay: 66 of the 367 causes,
more than signalling, and **41 notices name one and nothing else**. Irish Rail is
not reporting a fault there, it is reporting that a fault somewhere else reached
this train.

The prototype split them by accident. "Congestion" went to `operational`
alongside "an operational issue", which is a non-answer rather than a
consequence; "an earlier service delay on the line" went to `other`; "the late
arrival of an incoming service following an incident on the line" went to
`incident`, which is the root of the chain and not what the notice leads with.

Both are kept as categories - they are what the notice says - but they carry
family `CONSEQUENCE`, and that is the field that keeps a bar chart honest. A
chart of origins answers "what goes wrong on this railway". A chart including
consequences answers "what does Irish Rail write in this field", which is a
different and smaller question. Nothing forbids publishing the second; publishing
it under the first question's heading is the error.

Rejected: **one bucket per notice, winner takes all.** 32 notices state two
causes and 6 chain a root behind a proximate one, and picking one throws away the
half that is usually more informative. `read()` returns every cause with a role.

### Three: "and" is two causes, and a chain has two ends

The contrast with `lift_access` is exact and worth keeping in view. In
`platformAccess` prose, "lifts and ramps" is a *sequence* you need all of, and
reading it as a choice publishes access where there is none. In a notice's cause
clause, "and" is a genuine conjunction of two causes:

> "due to an earlier service delay and a temporary speed restriction on the line"

Two causes, both proximate. Whereas "caused by", "following" and a second "due
to" chain them, and the first one stated is the one the notice is leading with:

> "due to congestion caused by a technical issue onboard a train"
> "due to the late arrival of an incoming service following an incident on the line"
> "+20mins to services through Howth Junction due to 07:45 Bray/Howth departing
> Howth Junction +25 delayed due to a technical issue"

`congestion/proximate` then `technical/root`, and so on. The prototype read the
first of those as `technical`, on the strength of a word 40 characters into a
clause about congestion, while reading the identical notice from the previous
poll - which said only "due to congestion" - as `operational`. One event, two
buckets, half an hour apart.

### Four: a clause stops before the notice stops talking

Five notices end like this:

> "... due to a passenger issue and will run nonstop between Balbriggan and
> Drogheda (MacBride) to aid service recovery and ease congestion on the line."

Read to the full stop, that notice claims congestion it never claimed. A clause
ends at "and will", "it will", "creating", "causing", "to aid service recovery",
or a comma followed by the notice turning to name the affected service
("..., the 10:00 Belfast to Dublin Connolly will have a replacement train"). All
five shapes are in the corpus; none is speculative.

The one that reads oddly and is right: "a technical issue on the 14.50
Connolly/Belfast **creating** congestion on the line" is one cause, not two. What
a fault went on to create is its effect.

## What the reader refuses to say

Every rule here leans the same way as `notes/station-access.md` § *The safe
direction*: say less than the notice, never more.

**It does not decode a euphemism.** "An incident on the line" is 41 causes and
says nothing about what happened. "A tragic incident on the line being attended
by emergency services" is how Irish Rail writes a death on the railway, and the
reader's label for it is "Incident on the line, not specified". Turning that into
a word the notice does not use would be an inference on the most sensitive thing
this feed carries, published on an archive page with no way to correct it. The
category quotes and the site is expected to print the quote.

**It does not turn a non-answer into an answer.** "An operational issue" is 27
causes and means the railway is not saying. It is its own category, family
`unstated`, so a page can show how often that happens; it is never folded into a
fault, and it is kept apart from the 81 notices that state nothing at all, which
is a different silence.

**It does not merge things the feed distinguishes.** "A level crossing issue" and
"a vehicle striking Serpentine Level Crossing" are one bucket in the prototype
and two here: the first may be a barrier fault and the notice does not say, and
publishing a collision that was never reported is the same error as decoding
"incident". Where a notice does say - "an incident at Ballyhaunis, where a
vehicle has collided with a train" - the specific reading wins over the general
one, which is `lift_access`'s specific-beats-general rule in another domain.

**It does not invent a cause where there is no clause.** A markerless pass runs
only when the notice introduced no clause anywhere, and only for seven
categories whose noun phrase means the same thing wherever it appears. It reads
"Level crossing struck by a vehicle - Services are suspended between Mullingar
and Edgeworthstown", the head "Signalling issue", and a service "delayed in
Thurles awaiting an ambulance". It deliberately does not read "as it was
awaiting bus transfers from Mayo" or "Knock-on delays are still expected": bus
transfers are a mitigation in nine notices and a stated cause in one, and a
forecast of knock-on delays is not an attribution. Six notices are left unread on
purpose, which is the honest number to leave.

## The apology ends in the word "caused"

> "Iarnród Éireann Irish Rail apologise for any inconvenience caused."

**305 of the 416 notices contain the word "caused". 300 of them are that
sentence and two are a real "caused by".** A reader that matches before the
template is stripped finds the inconvenience to be the cause of the delay in
almost every notice Irish Rail publishes.

This is the lift-call sentence again - the boilerplate at dozens of station
pages that invents lifts at Greystones, Killiney and Donabate if you match the
word "lift" before stripping it - and it is handled the same way, in
`delay_cause.text`, before anything else runs. Five spellings and two typos
("apologise **or** any", "apologies for the") are in the corpus.

Three more paste marks come off with it, all of them capable of changing a
reading: an "Update at 17:24 - " stamp, the writer's initials ("-CL"), and HTML
entities the feed encodes twice. `<br>` becomes a full stop and not a space,
because three of the longest notices put a separate statement on each line and a
space hands the reader one sentence with two clauses in it.

And the sentence splitter must not split on the full stop in "17.43
Drogheda/GCD" or "06.17 Connolly/Maynooth", which is the same shape as Athlone's
"No." defeating `lift_access`'s splitter.

## How a pattern earns its place

A word stays in `PATTERNS` only if the corpus uses it, or if it is a spelling of
something the corpus uses. Speculative vocabulary came out on the first pass:
`failed`, `overhead`, `power failure`, `passenger taken ill`, `lorry`, `truck`,
`car`, a bare `hit` and the American `signaling` all matched nothing, and each
was a guess about how this railway talks. This is the rule
`notes/station-access.md` applied when it dropped "level crossing" from the
step-free guard list for guarding nothing.

Two exceptions, both recorded rather than quietly taken. Three of the seven cause
markers never fire; they stay because "because of" and "owing to" are
unambiguous wherever they appear in English, which an invented noun is not. And
observed typos stay: "congestiion" is in two notices, and "collied" for collided
is in the one notice that says what happened at Ballyhaunis - without it, that
notice reads as an unspecified incident.

## What this counts, and what it can never count

**Counting notices by category counts trains affected, not faults.** Nine
distinct notices state a signalling issue on 12 August and six of them name the
same one, at Dromod, mostly one per affected service. 53 notices place their
cause on an earlier train or an earlier time
("an earlier signalling issue at Connolly"), and `Cause.earlier` is the flag that
lets a page say so. A site that prints "44 signalling faults" from this will be
wrong by roughly the number of trains per fault.

**And there is no denominator.** This is the lift grade's ceiling in another
subject: the feed names a service only when something is wrong with it, there is
no roll of scheduled services, so counts and minutes are publishable and "% of
trains delayed" and "on-time performance" are not. The prototype said this in its
footer and it should survive into the site's own words, the way
`notes/site.md` § *The grade is availability* did.
