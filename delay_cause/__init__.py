"""Reading a cause out of an Irish Rail service message.

`read(head, text)` is the whole public surface. See `model` for what it will and
will not say, and `notes/cause-reading.md` for the corpus the categories came from.
"""

from .model import (
    CATEGORIES,
    CONSEQUENCE,
    FAMILY,
    LABEL,
    ORIGIN,
    PROXIMATE,
    ROOT,
    UNSTATED,
    Cause,
    Reading,
    read,
)

__all__ = [
    "CATEGORIES",
    "CONSEQUENCE",
    "FAMILY",
    "LABEL",
    "ORIGIN",
    "PROXIMATE",
    "ROOT",
    "UNSTATED",
    "Cause",
    "Reading",
    "read",
]
