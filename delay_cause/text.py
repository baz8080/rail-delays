"""Getting a notice down to the words that say something.

These banners are typed by hand into Irish Rail's CMS and the feed hands them
back with the paste marks still in: `<br>` where the author pressed return,
HTML entities encoded twice, an "Update at 15:03 - " prefix added when somebody
came back to a live notice, an operator's initials on the end.

One piece of that is worse than noise. **The apology sentence ends in the word
"caused"**, and "caused by" is one of the phrases that introduces a cause: 305
of the 416 distinct notices on the corpus to 2026-09-11 contain the word, 300
of them in "apologise for any inconvenience caused" and two in a real "caused
by". Matching before the apology is stripped reads the inconvenience as the
cause of the delay in almost every notice Irish Rail publishes. This is the
same trap as the lift-call sentence in `lift_access` and it is handled the same
way: strip the template first, then read what is left.
"""

from __future__ import annotations

import html
import re

# Written five ways on the corpus, with two typos ("apologise or any",
# "apologies for the"), sometimes with the company name in front and sometimes
# not, sometimes with a trailing "..". The trailing full stop is taken with it
# so the sentence splitter does not leave an empty sentence behind.
APOLOGY = re.compile(
    r"(?:Iarnr[oó]d\s+[ÉE]ireann\s+)?(?:Irish\s+Rail\s+)?"
    r"apolog\w+\s+(?:for|or)\s+(?:any|the)\s+inconvenience\s+caused\s*\.*",
    re.IGNORECASE,
)

# "Update at 17:24 - ", "Update15:52: ", "Update 11:45hrs. ", "06:00hrs. ".
# Always the time the author revised the notice, never part of what it says.
UPDATE_PREFIX = re.compile(
    r"^\s*(?:Update\s*(?:at|@)?\s*)?\d{1,2}[:.]\d{2}\s*(?:hrs)?\s*[-:.]\s*",
    re.IGNORECASE,
)

# "-CL", "-AP": the person who wrote it, on 2 notices.
INITIALS = re.compile(r"\s*-\s*[A-Z]{2}\s*$")

BLOCK = re.compile(r"<\s*br\b[^>]*>|</\s*p\s*>", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")

# Not a full stop: "06.17 Connolly/Maynooth", "17.43 Drogheda/GCD" and "No. 2"
# all use one mid-token, and Irish Rail writes service times both ways.
SENTENCE = re.compile(r"(?<!\d)\.(?!\d)|;|(?<=\s)-(?=\s)|\?|!")


def plain(value):
    """A notice field as one line of readable text.

    Entities are unescaped twice because the feed double-encodes them: the
    corpus carries `&#38;` for an ampersand and `&#N;` inside an already-escaped
    body. `<br>` becomes a full stop rather than a space, because that is what
    the author meant by it - three of the longest notices put a separate
    statement on each line and a space joins two sentences into one.
    """
    if not value:
        return ""
    text = html.unescape(html.unescape(value))
    text = BLOCK.sub(". ", text)
    text = TAG.sub(" ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s*\.(\s*\.)+", ".", text)


def readable(value):
    """`plain`, with the template and the editing marks taken out."""
    text = plain(value)
    text = APOLOGY.sub(" ", text)
    text = INITIALS.sub("", text)
    text = UPDATE_PREFIX.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" .,-")


def sentences(value):
    """`readable`, split where the author ended a thought."""
    return [part.strip(" ,") for part in SENTENCE.split(readable(value)) if part.strip(" ,.")]
