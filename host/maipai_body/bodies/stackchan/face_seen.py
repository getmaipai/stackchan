# ruff: noqa: E501
"""Tells the unit that the host's face model just found a face, so the unit can show its small face glyph (firmware patch NX05).

The unit's banner strip has a face glyph next to the microphone glyph. It shows for a few seconds after a report, and only while the
unit's "Status icons" switch is on; the unit decides that, so the host just reports. The unit's own face detector (an experiment image)
calls the same internal function, so either side may report.

Rules:

* ``note()`` is called from the look path and never waits: the call to the unit runs on a short-lived thread, at most one at a time and
  at most once a second.
* A unit that has no ``self.banner.face_seen`` tool (an older image) is asked again only after ten minutes; any other failure waits a
  minute. Neither is an error for the look path.
* Only "a face was there" is sent. No picture, box or identity ever leaves the look path.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from maipai_body.hal.errors import NotSupported

logger = logging.getLogger("maipai_body.bodies.stackchan.face_seen")

TOOL = "self.banner.face_seen"
INTERVAL_S = 1.0
SECONDS = 3
OLD_IMAGE_RETRY_S = 600.0
FAILURE_RETRY_S = 60.0


class FaceSeenSignal:
    def __init__(
        self,
        call: Callable[[str, dict[str, object]], object],
        *,
        clock: Callable[[], float] = time.monotonic,
        spawn: Callable[[Callable[[], None]], object] | None = None,
    ) -> None:
        self._call = call
        self._clock = clock
        self._spawn = spawn or _thread
        self._lock = threading.Lock()
        self._last = float("-inf")
        self._quiet_until = float("-inf")
        self._busy = False
        self.sent = 0  # reports that reached the unit (for the tests and the status page)

    def note(self) -> bool:
        """A face was found. True when a report was started, False when it was skipped (too soon, busy, or the unit lacks the tool)."""
        now = self._clock()
        with self._lock:
            if self._busy or now < self._quiet_until or now - self._last < INTERVAL_S:
                return False
            self._busy = True
            self._last = now
        try:
            self._spawn(self._send)
        except Exception:  # the look path never fails because a report could not start
            with self._lock:
                self._busy = False
                self._last = float("-inf")
            return False
        return True

    def _send(self) -> None:
        try:
            self._call(TOOL, {"seconds": SECONDS})
            self.sent += 1
        except NotSupported:
            with self._lock:
                self._quiet_until = self._clock() + OLD_IMAGE_RETRY_S
            logger.info("StackChan firmware has no %s tool; the face glyph is not reported", TOOL)
        except Exception as exc:  # a lost link or a slow unit: try again later, say nothing more
            with self._lock:
                self._quiet_until = self._clock() + FAILURE_RETRY_S
            logger.debug("face_seen report failed: %s", exc)
        finally:
            with self._lock:
                self._busy = False


def _thread(fn: Callable[[], None]) -> Any:
    t = threading.Thread(target=fn, name="face-seen", daemon=True)
    t.start()
    return t
