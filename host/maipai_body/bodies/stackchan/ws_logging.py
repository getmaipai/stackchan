"""Quiet logging for the StackChan websocket listeners.

Home's port health check opens a TCP connection and closes it without sending
a byte. websockets logs that as an ERROR with a traceback ("opening handshake
failed": InvalidMessage / EOFError), thousands of times a day. A connection
that sends no bytes is not a fault, so those records are dropped. Every other
handshake failure (a bad request, a header that is too long, a TLS error) is one INFO line
with the error's name and no traceback: anyone on the network can send one, and the log
must not fill with ERROR lines and tracebacks.
"""

from __future__ import annotations

import logging

from websockets.exceptions import InvalidMessage

_NAME = "maipai_body.stackchan.websockets"


class _DropEmptyConnections(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.getMessage() != "opening handshake failed" or not record.exc_info:
            return True
        error = record.exc_info[1]
        if isinstance(error, (EOFError, ConnectionResetError)):
            return False
        if isinstance(error, InvalidMessage):
            cause = error.__cause__ or error.__context__
            if isinstance(cause, (EOFError, ConnectionResetError)):
                return False
        record.levelno, record.levelname = logging.INFO, "INFO"
        record.msg, record.args = f"a connection did not complete the WebSocket handshake ({type(error).__name__}) and was dropped", None
        record.exc_info = record.exc_text = None
        return True


def listener_logger(name: str = _NAME) -> logging.Logger:
    """The logger to pass as ``serve(logger=...)``; created once, filter attached once."""
    logger = logging.getLogger(name)
    if not any(isinstance(item, _DropEmptyConnections) for item in logger.filters):
        logger.addFilter(_DropEmptyConnections())
    return logger
