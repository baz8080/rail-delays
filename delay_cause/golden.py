"""Every cause the reader finds, beside the notice it found it in.

`tests/fixtures/delay-cause-golden.json` pins the inputs next to the outputs, so
the test replays a head and a body through today's patterns and compares. It
needs no `lifts-data` checkout and runs on a bare clone, which is the shape
`access-golden.json` arrived at after the version that re-derived from live rows
reddened `main` three times in five days. `notes/station-access.md` § The golden
file pins its inputs has that history; the same two rules apply here.

A notice the file has not seen is corpus growth and passes. A notice the corpus
no longer carries stays pinned and keeps being a test vector: these banners are
edited in place, and a wording Irish Rail has withdrawn is still a wording the
reader has to handle if it comes back.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import model

PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "delay-cause-golden.json"


def _reading(head, text):
    reading = model.read(head, text)
    return {
        "head": head,
        "text": text,
        "causes": [
            {
                "category": cause.category,
                "family": cause.family,
                "phrase": cause.phrase,
                "matched": cause.matched,
                "marker": cause.marker,
                "role": cause.role,
                "earlier": cause.earlier,
            }
            for cause in reading.causes
        ],
        "unread": list(reading.unread),
    }


def build(notices):
    """The reader's output for every distinct (head, text) it is given."""
    pairs = sorted({(head, text) for head, text in notices})
    return {"readings": [_reading(head, text) for head, text in pairs]}


def pinned_notices(document):
    return [(r["head"], r["text"]) for r in document.get("readings", [])]


def _key(reading):
    return reading["head"], reading["text"]


def _moved(label, before, after):
    return [
        f"{label}: {field}: {before.get(field)!r} -> {after.get(field)!r}"
        for field in sorted(set(before) | set(after))
        if before.get(field) != after.get(field)
    ]


def differences(stored, current):
    """Where two documents disagree about a notice both pinned.

    Moves only, the rule `lift_access.golden` settled: what one document holds
    and the other does not is how much corpus there was when it was written, and
    no code change decides that.
    """
    out = []
    old = {_key(r): r for r in stored.get("readings", [])}
    new = {_key(r): r for r in current.get("readings", [])}
    for key in sorted(set(old) & set(new)):
        label = f"notice {key[0]!r}" if key[0] else f"notice {key[1][:40]!r}"
        before, after = old[key], new[key]
        if before.get("causes") != after.get("causes"):
            out.append(f"{label}: causes: {_causes(before)} -> {_causes(after)}")
        out.extend(_moved(label, {"unread": before.get("unread")}, {"unread": after.get("unread")}))
    return out


def _causes(reading):
    return "[" + ", ".join(
        f"{c['category']}/{c['role']}({c['matched']!r})" for c in reading.get("causes", [])
    ) + "]"


def new_notices(stored, current):
    seen = {_key(r) for r in stored.get("readings", [])}
    return [r for r in current.get("readings", []) if _key(r) not in seen]


def merge(stored, current):
    """`current` over `stored`, so a regeneration adds and updates but never drops."""
    readings = {_key(r): r for r in stored.get("readings", [])}
    readings.update({_key(r): r for r in current.get("readings", [])})
    return {"readings": [readings[key] for key in sorted(readings)]}


def load():
    if not PATH.exists():
        return {"readings": []}
    return json.loads(PATH.read_text(encoding="utf-8"))


def dumps(document):
    return json.dumps(document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
