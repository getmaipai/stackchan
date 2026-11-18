"""Logging for the hosted Bot (MAIPAI_HUB_HOST=1).

Python shows only WARNING and above on stderr when nothing configures logging, so the
StackChan voice-session lines (listen, first audio frame, speech-to-text, chat) at INFO never
reached the hub's log. A hosted Bot logs ``maipai_body`` at INFO with a timestamp.
"""

from __future__ import annotations

import logging
import os

class NoRobotYet(logging.Filter):
    """A failed call that was only because no robot is connected yet is logged as one plain line, not a traceback."""

    def filter(self, record: logging.LogRecord) -> bool:
        error = record.exc_info[1] if record.exc_info else None
        while error is not None:
            if "No StackChan is connected" in str(error):
                record.exc_info = None
                record.msg = f"{record.getMessage()} (no robot is connected yet)"
                record.args = None
                break
            error = error.__cause__ or error.__context__
        return True


_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(hosted: bool | None = None, *, root: logging.Logger | None = None) -> None:
    """Idempotent: add a stderr handler once and raise ``maipai_body`` to INFO when hosted."""
    if hosted is None:
        hosted = os.environ.get("MAIPAI_HUB_HOST") == "1"
    root = root if root is not None else logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_FORMAT))
        handler.addFilter(NoRobotYet())
        root.addHandler(handler)
        root.setLevel(logging.WARNING)
    if hosted:
        logging.getLogger("maipai_body").setLevel(logging.INFO)
