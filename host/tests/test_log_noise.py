"""Things anyone on the network can cause must not write errors or tracebacks to the log."""

import io
import logging

from maipai_body.bodies.stackchan.ws_logging import listener_logger


def _logged(exception):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    log = listener_logger()
    log.addHandler(handler)
    try:
        try:
            raise exception
        except Exception:
            log.error("opening handshake failed", exc_info=True)
    finally:
        log.removeHandler(handler)
    return stream.getvalue()


def test_a_bad_request_is_one_info_line_without_a_traceback():
    text = _logged(ValueError("bad header"))
    assert text.startswith("INFO ") and "Traceback" not in text and "ERROR" not in text and "ValueError" in text


def test_a_connection_that_sends_nothing_is_not_logged_at_all():
    assert _logged(EOFError()) == ""
