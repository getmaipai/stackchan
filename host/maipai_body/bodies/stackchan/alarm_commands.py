"""Voice alarms and timers that work with no model and no Home hub ("set an alarm for 10:30", "cancel my alarm").

The unit keeps and rings the alarms itself (firmware patches 090 to 094). This module only understands the words, then
calls ``TimerService``. Nothing here is sent anywhere. Wording that is not clearly about an alarm or a timer is left to
the chat model, so ordinary talk is never taken for a command.

Cancel rule: one match is canceled at once. With several, the alarm set by voice in the last ``RECENT_S`` seconds is the
one meant; otherwise the robot names them and asks which (say the time, or "cancel all").
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

RECENT_S = 300.0  # "cancel my alarm" right after setting one means that one

_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty five": 45,
    "forty": 40, "fifty": 50, "a quarter": 15, "half": 30,
}  # fmt: skip
_NUM = r"(\d{1,2}|" + "|".join(sorted((re.escape(w) for w in _WORDS), key=len, reverse=True)) + r")"
_CANCEL = re.compile(r"\b(cancel|delete|remove|clear|turn off|stop|get rid of|never mind)\b")
_KIND = re.compile(r"\b(alarms?|timers?)\b")
_SET = re.compile(r"\b(set|make|start|create|wake me|add|put)\b")
_AT = re.compile(
    rf"\b{_NUM}(?:\s*(?::|\s)\s*{_NUM})?\s*(a\s?m|p\s?m|in the morning|in the evening|at night)?(?=\W|$)"
)
_IN_UNITS = re.compile(rf"\b{_NUM}\s*(hours?|hrs?|minutes?|mins?|seconds?|secs?)\b")


@dataclass(frozen=True)
class AlarmCommand:
    kind: str  # "set_alarm" | "set_timer" | "cancel" | "list"
    hour: int | None = None
    minute: int | None = None
    seconds: int | None = None
    what: str = "any"  # "alarm" | "timer" | "any" (for cancel and list)
    everything: bool = False  # "cancel all"


def _n(token: str) -> int:
    return int(token) if token.isdigit() else _WORDS[token]


def _clean(text: str) -> str:
    return re.sub(r"[,.!?]+(?!\d)", " ", text.lower()).replace("’", "'").strip()


def _hour_minute(text: str) -> tuple[int, int | None, str | None] | None:
    """The first clock time in the words: (hour as said, minute or None, am/pm marker or None)."""
    for found in _AT.finditer(text):
        hour_word, minute_word, marker = found.group(1), found.group(2), found.group(3)
        hour = _n(hour_word)
        if hour > 24:
            continue
        minute = _n(minute_word) if minute_word else None
        if minute is not None and minute > 59:
            continue
        mark = None
        if marker:
            mark = "pm" if marker.startswith("p") or marker in ("in the evening", "at night") else "am"
        return hour, minute, mark
    return None


def _to_24h(hour: int, minute: int, mark: str | None, now: datetime) -> tuple[int, int]:
    """No am/pm said: the next time that clock reading comes round, morning or afternoon."""
    if mark == "am":
        return (0 if hour == 12 else hour % 12), minute
    if mark == "pm":
        return (12 if hour == 12 else hour % 12 + 12), minute
    if hour >= 13 or hour == 0:
        return hour % 24, minute
    options = [(hour % 12, minute), (hour % 12 + 12, minute)]
    here = now.hour * 60 + now.minute
    ahead = sorted(options, key=lambda hm: (hm[0] * 60 + hm[1] - here) % 1440)
    return ahead[0]


def parse_alarm_command(text: str, now: datetime | None = None) -> AlarmCommand | None:
    words = _clean(text)
    if not words:
        return None
    kind = _KIND.search(words)
    now = now or datetime.now()
    if _CANCEL.search(words) and kind:
        what = "alarm" if kind.group(1).startswith("alarm") else "timer"
        everything = bool(re.search(r"\b(all|every|everything)\b", words)) or kind.group(1).endswith("s")
        clock = _hour_minute(words)
        if clock is not None and not everything:
            hour, minute, mark = clock
            h, m = _to_24h(hour, minute or 0, mark, now)
            return AlarmCommand("cancel", hour=h, minute=m, what=what)
        return AlarmCommand("cancel", what=what, everything=everything)
    if re.search(r"\b(what|which|how many|list|any)\b.*\b(alarms?|timers?)\b", words) and not _SET.search(words):
        return AlarmCommand("list", what="alarm" if "alarm" in words else "timer")
    wake = re.search(r"\bwake me( up)? (at|by) ", words)
    if kind and kind.group(1).startswith("timer") and _SET.search(words):
        spans = _IN_UNITS.findall(words)
        total = 0
        for amount, unit in spans:
            total += _n(amount) * (3600 if unit.startswith(("h")) else 60 if unit.startswith("m") else 1)
        if total:
            return AlarmCommand("set_timer", seconds=total)
        return None
    if (kind and kind.group(1).startswith("alarm") and _SET.search(words)) or wake:
        spans = _IN_UNITS.findall(words)
        if spans and re.search(r"\bin\b", words):
            total = sum(
                _n(a) * (3600 if u.startswith("h") else 60 if u.startswith("m") else 1) for a, u in spans
            )
            if total:
                return AlarmCommand("set_timer", seconds=total)
        clock = _hour_minute(words.split(" for ", 1)[-1] if " for " in words else words.split(" at ", 1)[-1])
        if clock is None:
            return None
        hour, minute, mark = clock
        h, m = _to_24h(hour, minute or 0, mark, now)
        return AlarmCommand("set_alarm", hour=h, minute=m)
    return None


def say_time(hour: int, minute: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12}:{minute:02d} {suffix}"


def _spoken_duration(seconds: int) -> str:
    if seconds % 3600 == 0 and seconds >= 3600:
        n = seconds // 3600
        return f"{n} hour" + ("s" if n != 1 else "")
    if seconds % 60 == 0:
        n = seconds // 60
        return f"{n} minute" + ("s" if n != 1 else "")
    return f"{seconds} seconds"


class AlarmControl:
    """Runs a parsed command against the unit's timers and returns the one line to say."""

    def __init__(
        self,
        timers: Any,
        *,
        now: Callable[[], datetime] = datetime.now,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._timers = timers
        self._now = now
        self._clock = clock
        self._recent: tuple[int, float] | None = None  # id and when voice last set one

    def parse(self, text: str) -> AlarmCommand | None:
        return parse_alarm_command(text, self._now())

    def run(self, command: AlarmCommand) -> str:
        try:
            return self._run(command)
        except Exception as exc:  # the unit may be away; say what to do, never fail the turn
            return str(exc) if getattr(exc, "args", None) and isinstance(exc.args[0], str) and len(exc.args[0]) < 160 else (
                "I could not reach my clock. Check that I am on Wi-Fi, then ask again."
            )

    def _run(self, c: AlarmCommand) -> str:
        if c.kind == "set_timer":
            reply = self._timers.set_timer(c.seconds)
            self._recent = (reply.get("id"), self._clock())
            return f"OK, a {_spoken_duration(int(c.seconds or 0))} timer."
        if c.kind == "set_alarm":
            reply = self._timers.set_alarm(c.hour, c.minute)
            self._recent = (reply.get("id"), self._clock())
            return f"OK, alarm set for {say_time(int(c.hour or 0), int(c.minute or 0))}."
        rows = self._rows(c.what)
        if c.kind == "list":
            if not rows:
                return "You have nothing set."
            return "You have " + self._names(rows) + "."
        if not rows:
            return "You have no " + ("alarms" if c.what == "alarm" else "timers" if c.what == "timer" else "alarms or timers") + " set."
        if c.hour is not None:
            picked = [r for r in rows if r["at"] and (r["at"].hour, r["at"].minute) == (c.hour, c.minute)]
            if not picked:
                return f"I do not see one for {say_time(c.hour, c.minute or 0)}. You have " + self._names(rows) + "."
            return self._cancel_rows(picked)
        if c.everything:
            return self._cancel_rows(rows)
        if len(rows) == 1:
            return self._cancel_rows(rows)
        if self._recent and self._clock() - self._recent[1] <= RECENT_S:
            picked = [r for r in rows if r["id"] == self._recent[0]]
            if picked:
                return self._cancel_rows(picked)
        return (
            f"You have {len(rows)}: " + self._names(rows) + ". Say cancel, then the time, or cancel all."
        )

    def _rows(self, what: str) -> list[dict[str, Any]]:
        reply = self._timers.list_timers()
        now = self._now()
        out = []
        for row in reply.get("timers", []):
            kind = str(row.get("kind", "timer"))
            if what != "any" and kind != what:
                continue
            left = row.get("left")
            at = None
            if isinstance(left, (int, float)) and left >= 0:
                at = (now + timedelta(seconds=left + 30)).replace(second=0, microsecond=0)
            out.append({"id": row.get("id"), "kind": kind, "left": left, "at": at, "label": row.get("label", "")})
        return out

    @staticmethod
    def _names(rows: list[dict[str, Any]]) -> str:
        parts = []
        for r in rows:
            if r["kind"] == "alarm" and r["at"]:
                parts.append(f"an alarm for {say_time(r['at'].hour, r['at'].minute)}")
            elif r["left"] is not None:
                parts.append(f"a timer with {_spoken_duration(max(60, int(r['left']) // 60 * 60))} left")
            else:
                parts.append("a " + r["kind"])
        return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]

    def _cancel_rows(self, rows: list[dict[str, Any]]) -> str:
        for row in rows:
            self._timers.cancel(int(row["id"]))
        if len(rows) == 1:
            r = rows[0]
            if r["kind"] == "alarm" and r["at"]:
                return f"Canceled your {say_time(r['at'].hour, r['at'].minute)} alarm."
            return "Canceled your " + r["kind"] + "."
        return f"Canceled {len(rows)}."
