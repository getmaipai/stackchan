"""POSIX TZ rules as the unit's clock uses them (maipai_tz_core.h zone strings such as "EST5EDT,M3.2.0,M11.1.0"):
utc_offset(rule, utc_epoch) -> seconds east of UTC, and local_to_utc(rule, naive_local_epoch).
Handles std-only rules, <+hh>name quoting, hh[:mm[:ss]] offsets (POSIX sign: EST5 is UTC-5), a DST name with an implicit
or explicit offset, and Mm.w.d[/time] transition rules in both hemispheres. Placement: host-side development tool. Upstream: none."""

from __future__ import annotations

import datetime as dt
import re

_NAME = r"(?:<[^>]+>|[A-Za-z]{3,})"
_OFF = r"[+-]?\d{1,2}(?::\d{2}(?::\d{2})?)?"
_RULE = re.compile(rf"^({_NAME})({_OFF})(?:({_NAME})({_OFF})?(?:,(M\d+\.\d+\.\d+(?:/{_OFF})?),(M\d+\.\d+\.\d+(?:/{_OFF})?))?)?$")


def _seconds(text: str) -> int:
    sign = -1 if text.startswith("-") else 1
    parts = [int(p) for p in text.lstrip("+-").split(":")]
    parts += [0] * (3 - len(parts))
    return sign * (parts[0] * 3600 + parts[1] * 60 + parts[2])


def _transition(spec: str, year: int) -> int:
    """Seconds since the epoch, in local wall time as if it were UTC, of an Mm.w.d[/time] moment in `year`."""
    body, _, at = spec[1:].partition("/")
    month, week, day = (int(x) for x in body.split("."))
    seconds_in = _seconds(at) if at else 2 * 3600
    first = dt.date(year, month, 1)
    offset = (day - first.isoweekday() % 7) % 7  # day 0 is Sunday
    d = first + dt.timedelta(days=offset + 7 * (week - 1))
    while d.month != month:  # week 5 means the last such day
        d -= dt.timedelta(days=7)
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp()) + seconds_in


def utc_offset(rule: str, utc_epoch: int) -> int:
    m = _RULE.match(rule.strip())
    if not m:
        raise ValueError(f"not a POSIX time zone rule: {rule}")
    _std_name, std_off, dst_name, dst_off, start, end = m.groups()
    std = -_seconds(std_off)
    if not dst_name or not start or not end:
        return std
    dst = -_seconds(dst_off) if dst_off else std + 3600
    year = dt.datetime.fromtimestamp(utc_epoch + std, dt.timezone.utc).year
    # transitions are given in the wall time in force before them: the start in standard time, the end in daylight time
    start_utc = _transition(start, year) - std
    end_utc = _transition(end, year) - dst
    in_dst = start_utc <= utc_epoch < end_utc if start_utc < end_utc else not (end_utc <= utc_epoch < start_utc)
    return dst if in_dst else std


def local_to_utc(rule: str, local_epoch: int) -> int:
    """The UTC moment whose local wall time is `local_epoch` (a gap or an overlap resolves to the later offset)."""
    guess = local_epoch - utc_offset(rule, local_epoch)
    return local_epoch - utc_offset(rule, guess)
