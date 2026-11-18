"""Which body this process serves, chosen by `MAIPAI_BODY` from one table.

A body is a name, the environment words that select it, and whether the host process serves it on its own sockets
("hosted": the unit connects to the host, as StackChan does) or drives it through a daemon (Reachy Mini). `app.py` asks this
table instead of comparing names, so a third robot is one row here and a profile in its own package.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BODY = "reachy_mini"


@dataclass(frozen=True)
class BodyEntry:
    id: str
    words: tuple[str, ...]  # the MAIPAI_BODY values that select it (lower case)
    hosted: bool  # the host serves the robot's sockets (voice, avatar) and the robot connects in


BODIES: tuple[BodyEntry, ...] = (
    BodyEntry("reachy_mini", ("reachy_mini", "reachy-mini", "reachy"), hosted=False),
    BodyEntry("stackchan", ("stackchan", "fake"), hosted=True),
)


def selected(environ: Mapping[str, str] | None = None) -> BodyEntry:
    """The body named by MAIPAI_BODY. An unknown word selects the default body, as before."""
    environ = os.environ if environ is None else environ
    word = environ.get("MAIPAI_BODY", DEFAULT_BODY).strip().lower()
    for entry in BODIES:
        if word in entry.words:
            return entry
    return next(entry for entry in BODIES if entry.id == DEFAULT_BODY)
