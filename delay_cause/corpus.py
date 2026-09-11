"""Every distinct notice the collector has logged, read straight from the logs.

Not from `lift_status.db`. The database drops an item whose `locationCodes` is
empty into `unidentifiable_items`, and Irish Rail empties that field on a notice
part-way through its life: 288 of the 497 non-lift notices on the corpus to
2026-09-11 carry codes for some of their polls and `[]` for the rest, and 21
never carry them at all. None of the 55 lift and escalator notices does it once,
which is why nothing in the lift site ever noticed. `notes/site.md`.

The raw logs are the source of truth and `rebuild` already replays them, so this
reads them the same way rather than asking the derived tables for rows they do
not have.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple


class Notice(NamedTuple):
    head: str
    text: str
    start: str
    codes: tuple[str, ...]
    first_seen: str
    sightings: int


def distinct(data_dir):
    """Every distinct (head, text) in the raw logs, oldest first sighting first.

    Identity here is the words, not the collector's key: a delay notice's head
    carries the minutes ("+15mins delayed" becomes "+21mins delayed" at the next
    poll) so `head + locationCodes + start` fractures on the thing that changes
    most. What this module reads is the text, so the text is the key.
    """
    seen = {}
    for path in sorted(Path(data_dir).glob("raw/messages-*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    run = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if run.get("http_status") != 200 or run.get("network_error"):
                    continue
                try:
                    items = json.loads(run.get("body") or "")
                except (json.JSONDecodeError, TypeError):
                    continue
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    head = (item.get("head") or "").strip()
                    text = (item.get("text") or "").strip()
                    key = (head, text)
                    if key in seen:
                        seen[key] = seen[key]._replace(sightings=seen[key].sightings + 1)
                        continue
                    codes = item.get("locationCodes")
                    seen[key] = Notice(
                        head=head,
                        text=text,
                        start=(item.get("start") or "").strip(),
                        codes=tuple(codes) if isinstance(codes, list) else (),
                        first_seen=run.get("fetched_at_utc") or "",
                        sightings=1,
                    )
    return sorted(seen.values(), key=lambda n: (n.first_seen, n.head, n.text))
