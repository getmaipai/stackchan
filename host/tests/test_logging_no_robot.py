"""With no robot connected yet, the host log says so in one line; it does not print a traceback per failed call."""

import logging

from maipai_body.logging_setup import NoRobotYet


def _record(exc):
    try:
        raise exc
    except Exception:
        import sys

        return logging.LogRecord("x", logging.WARNING, __file__, 1, "battery read failed", None, sys.exc_info())


def test_a_no_robot_traceback_becomes_one_plain_line():
    inner = ConnectionError("No StackChan is connected. Connect and pair the robot, then retry.")
    try:
        try:
            raise inner
        except ConnectionError as e:
            raise RuntimeError("did not complete") from e
    except RuntimeError as outer:
        record = _record(outer)
    assert NoRobotYet().filter(record) is True
    assert record.exc_info is None and "no robot is connected yet" in record.getMessage()


def test_other_tracebacks_are_kept():
    record = _record(ValueError("a real bug"))
    NoRobotYet().filter(record)
    assert record.exc_info is not None
