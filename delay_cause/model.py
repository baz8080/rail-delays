"""What a notice says went wrong, read from the notice's own words.

Irish Rail's service messages usually name a cause, in a clause introduced by
"due to" and a handful of other phrases. The vocabulary they are written from is
small and closed: over the 416 distinct notices collected between 2026-08-08 and
2026-09-11 there are 113 distinct cause clauses, and every noun phrase in them is
one of eleven things. `notes/cause-reading.md` lists them with their counts and
records what was rejected.

Three readings this module refuses to make, all of them in the same direction as
`lift_access`'s "default to gone, never infer remains":

- **It does not decode a euphemism.** "An incident on the line" is 41 of the 367
  causes read and says nothing about what happened; "a tragic incident ... being
  attended by emergency services" is how Irish Rail writes a death on the
  railway. Both come back as `incident` with the notice's words attached, and the
  site is expected to print those words rather than a guess.
- **It does not turn a non-answer into an answer.** "An operational issue" is 27
  causes and means the railway is not saying. It is its own category so that a
  chart can show how often that happens, and it is never folded into a cause.
- **It does not promote a consequence to a cause.** "The late arrival of an
  incoming service", "congestion" and "an earlier service delay" name another
  delay, not a fault: 66 of the 367 causes, more than signalling, and 41 notices
  name one and nothing else. Those categories carry family `CONSEQUENCE`, so a
  page counting faults can leave them out and a page counting notices can say
  how much of the feed is the railway reporting that a delay propagated.

A notice can state more than one cause. "And" joins peers ("a mechanical issue
and the late arrival of the incoming service"), and "caused by", "following" and
a second "due to" chain them ("congestion caused by a technical issue onboard a
train"), which is why every cause carries a role rather than one winning.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from .text import sentences

TECHNICAL = "technical"
SIGNALLING = "signalling"
INFRASTRUCTURE = "infrastructure"
LEVEL_CROSSING = "level_crossing"
VEHICLE_STRIKE = "vehicle_strike"
PASSENGER = "passenger"
INCIDENT = "incident"
CONGESTION = "congestion"
KNOCK_ON = "knock_on"
PLANNED = "planned"
UNSPECIFIED = "unspecified"

ORIGIN = "origin"
CONSEQUENCE = "consequence"
PLANNED_FAMILY = "planned"
UNSTATED = "unstated"

# What each category is, in words a page can print. They name what the feed says,
# not what it implies: `technical` does not say "train" because 45 of its 111
# clauses are a bare "a technical issue" that names nothing, and `incident` does
# not say what kind.
LABEL = {
    TECHNICAL: "Technical or mechanical fault",
    SIGNALLING: "Signalling fault",
    INFRASTRUCTURE: "Speed restriction or power supply",
    LEVEL_CROSSING: "Level crossing issue",
    VEHICLE_STRIKE: "Road vehicle struck the railway",
    PASSENGER: "Passenger issue, including illness",
    INCIDENT: "Incident on the line, not specified",
    CONGESTION: "Congestion",
    KNOCK_ON: "Knock-on delay",
    PLANNED: "Planned works",
    UNSPECIFIED: "No cause given",
}

FAMILY = {
    TECHNICAL: ORIGIN,
    SIGNALLING: ORIGIN,
    INFRASTRUCTURE: ORIGIN,
    LEVEL_CROSSING: ORIGIN,
    VEHICLE_STRIKE: ORIGIN,
    PASSENGER: ORIGIN,
    INCIDENT: ORIGIN,
    CONGESTION: CONSEQUENCE,
    KNOCK_ON: CONSEQUENCE,
    PLANNED: PLANNED_FAMILY,
    UNSPECIFIED: UNSTATED,
}

CATEGORIES = tuple(LABEL)

# The phrases that introduce a cause. "After" is not among them: of its 5 uses on
# the corpus one is a time of day ("after 14:00hrs") and one a place in a journey
# ("after departing Castlerea"), so it is a temporal word that sometimes reads as
# causal rather than a marker. "Following" is causal on all 16 of its uses, and
# the corpus has no "the following" for it to trip over. Three of the seven below
# never fire; unlike an unused noun in PATTERNS, which would be a guess about how
# this railway talks, they are unambiguous wherever they do appear.
MARKER = re.compile(
    r"\b(due to|as a result of|caused by|because of|owing to|following|arising from)\b",
    re.IGNORECASE,
)

# Where a cause clause stops and the notice starts saying what it did about it.
# Without these, "a passenger issue and will run nonstop between Balbriggan and
# Drogheda (MacBride) to aid service recovery and ease congestion on the line"
# reads as a passenger issue *and congestion*, which is a cause the notice never
# claimed. Five notices on the corpus end that way.
TAIL = re.compile(
    r"\s+(?:and\s+)?(?:will|it will|creating|causing)\s"
    r"|,\s*(?:the\s+\d{1,2}[:.]\d{2}\b|this service|this train|services? (?:are|will)|it is)"
    r"|\s+to aid service recovery",
    re.IGNORECASE,
)

# A clause whose subject is another service's delay. Kept out of the markerless
# pass below: "delayed" on its own is what every one of these notices is about,
# and only a cause clause saying it makes it a cause.
KNOCK_ON_PATTERN = (
    r"late arrival|late running|incoming service delay"
    r"|earlier (?:service )?delays?|delays/alterations"
    r"|service (?:delays? and )?alterations|service disruptions"
    r"|earlier (?:service )?cancellation|(?:dart|service) cancellation|being cancelled"
    r"|earlier closure|earlier (?:service )?terminating|earlier stopped train"
    r"|\+\d+\s*(?:mins?|minutes?)?\s*delayed"
)

# Order is not precedence - every pattern that matches a clause contributes a
# cause - except where SUPPRESSES says one reading is the specific case of
# another.
PATTERNS = (
    (PLANNED, r"planned works|planned maintenance|engineering works"),
    (
        VEHICLE_STRIKE,
        # "collied" is Irish Rail's typo for collided, and the notice it is in is
        # the one that says what the incident at Ballyhaunis was.
        r"(?:strik\w+|struck|hitting|colli\w+)[^.]{0,40}"
        r"\b(?:vehicle|tractor|bridge|level crossing|train)\b"
        r"|\b(?:vehicle|tractor)\b[^.]{0,40}(?:strik\w+|struck|hitting|colli\w+)",
    ),
    (LEVEL_CROSSING, r"level crossing"),
    (SIGNALLING, r"signalling"),
    (
        TECHNICAL,
        r"technical issue|mechanical issue|train failure|train issue"
        r"|broken down train|loco swap|train set replacement",
    ),
    (INFRASTRUCTURE, r"speed restriction|power supply"),
    (PASSENGER, r"passenger issue|ill passenger|medical emergency|ambulance"),
    (CONGESTION, r"congestion|congestiion"),
    (KNOCK_ON, KNOCK_ON_PATTERN),
    (INCIDENT, r"incident|emergency services"),
    (UNSPECIFIED, r"operational (?:issues?|reasons)"),
)

COMPILED = tuple((name, re.compile(pattern, re.IGNORECASE)) for name, pattern in PATTERNS)

# Specific beats general, the rule `lift_access` reads station prose by. A
# vehicle on a crossing is not a crossing fault, and "an incident at Ballyhaunis,
# where a vehicle has collided with a train" is not an unspecified incident.
SUPPRESSES = {VEHICLE_STRIKE: (LEVEL_CROSSING, INCIDENT)}

# What may be read from a notice that introduces no cause clause at all. A
# deliberately short list: these noun phrases mean the same thing wherever they
# appear, and the ones left out do not. "Bus transfers" is a mitigation in nine
# notices and the stated cause of a delay in one; "knock-on delays are still
# expected" is a forecast, not an attribution. Both go unread rather than guessed.
BARE = (PLANNED, VEHICLE_STRIKE, LEVEL_CROSSING, SIGNALLING, TECHNICAL, PASSENGER, CONGESTION)

EARLIER = re.compile(r"\bearlier\b|\blate running\b", re.IGNORECASE)

PROXIMATE = "proximate"
ROOT = "root"


class Cause(NamedTuple):
    """One cause a notice states.

    `phrase` is the notice's own words for it, so a page can quote rather than
    paraphrase. `matched` is the part of them that decided the category, which is
    what makes a golden diff readable. `role` is `PROXIMATE` for the cause the
    notice gives first and `ROOT` for one it goes on to attribute that to.
    `earlier` marks a cause the notice places on another service or an earlier
    time - the reason a count of notices by category counts trains affected and
    not faults.
    """

    category: str
    phrase: str
    matched: str
    marker: str
    role: str
    earlier: bool

    @property
    def family(self):
        return FAMILY[self.category]

    @property
    def label(self):
        return LABEL[self.category]


class Reading(NamedTuple):
    causes: tuple[Cause, ...]
    unread: tuple[str, ...]

    @property
    def stated(self):
        """Whether the notice names anything at all, a non-answer included."""
        return bool(self.causes) or bool(self.unread)

    def of_family(self, family):
        return tuple(c for c in self.causes if c.family == family)


def _clause(part):
    """A cause clause, cut where the notice stops naming one."""
    cut = TAIL.search(part)
    if cut:
        part = part[: cut.start()]
    return part.strip(" ,.-")


def _causes_in(part, marker, role):
    """Every category the clause names, in the order the clause names them."""
    earlier = bool(EARLIER.search(part))
    found = []
    for name, pattern in COMPILED:
        match = pattern.search(part)
        if match:
            found.append((match.start(), Cause(name, part, match.group(0), marker, role, earlier)))
    suppressed = {name for _, cause in found for name in SUPPRESSES.get(cause.category, ())}
    return [cause for _, cause in sorted(found) if cause.category not in suppressed]


def _segments(sentence):
    """(marker, clause) for each cause clause in one sentence.

    A clause runs to the next marker rather than to the end of the sentence,
    which is what turns "congestion caused by a technical issue onboard a train"
    into two readings instead of one clause matching both.
    """
    marks = list(MARKER.finditer(sentence))
    out = []
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(sentence)
        clause = _clause(sentence[mark.end() : end])
        if clause:
            out.append((mark.group(0).lower(), clause))
    return out


def read(head, text=""):
    """Every cause the notice states, in the order it states them.

    Head and body are read together and a category is kept once: Irish Rail
    routinely writes the cause into both ("Service delayed 15 minutes - Due to a
    signalling issue." over a body that says the same), and that is one fault,
    not two.
    """
    causes, unread, seen = [], [], set()
    for value in (head, text):
        for sentence in sentences(value):
            for position, (marker, clause) in enumerate(_segments(sentence)):
                role = PROXIMATE if position == 0 else ROOT
                found = _causes_in(clause, marker, role)
                if not found:
                    unread.append(clause)
                for cause in found:
                    if cause.category not in seen:
                        seen.add(cause.category)
                        causes.append(cause)
    if not causes and not unread:
        causes = _bare(head, text)
    return Reading(tuple(_suppress(causes)), tuple(dict.fromkeys(unread)))


def _suppress(causes):
    """Specific beats general, across the whole notice and not one clause.

    A head saying "a level crossing issue" over a body saying a vehicle struck
    the crossing is one event described twice, and reading the two clauses
    independently published both. Five pinned notices did that, and each one
    counted twice in a ranking of what went wrong.
    """
    beaten = {name for cause in causes for name in SUPPRESSES.get(cause.category, ())}
    return [c for c in causes if c.category not in beaten]


def _bare(head, text):
    """A cause stated without a clause to introduce it.

    "Level crossing struck by a vehicle - Services are suspended between
    Mullingar and Edgeworthstown" is a cause and a consequence with a dash
    between them; the head "Signalling issue" is a cause and nothing else. Only
    reached when the notice introduced no clause anywhere, so a notice that did
    and was read wrongly here cannot be rescued by it.
    """
    causes, seen = [], set()
    for value in (head, text):
        for sentence in sentences(value):
            for cause in _causes_in(sentence, "", PROXIMATE):
                if cause.category in BARE and cause.category not in seen:
                    seen.add(cause.category)
                    causes.append(cause)
    return causes
