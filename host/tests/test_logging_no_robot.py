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


def test_the_terminal_stays_quiet_before_the_first_robot_but_the_log_file_keeps_it_as_info():
    import logging

    record = logging.LogRecord("x", logging.WARNING, __file__, 1, "StackChan tool self.music.set failed: ConnectionError: No StackChan is connected. Connect and pair the robot.", None, None)
    assert NoRobotYet(drop=True).filter(record) is False
    again = logging.LogRecord("x", logging.WARNING, __file__, 1, "battery read failed (no robot is connected yet)", None, None)
    assert NoRobotYet().filter(again) is True and again.levelno == logging.INFO
    other = logging.LogRecord("x", logging.WARNING, __file__, 1, "a real problem", None, None)
    assert NoRobotYet(drop=True).filter(other) is True and other.levelno == logging.WARNING
