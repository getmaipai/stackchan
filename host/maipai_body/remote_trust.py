# ruff: noqa: E501
"""The trust boundary between the host and the unit for remote control (firmware patch FM03).

Two rules keep a controller from making the robot act with no cue:

1. A controller's request can never set ``source``, ``token`` or the other cue fields. The host fills them in itself, from the
   unit's own answer to ``self.remote.action`` (``RemoteCue``). A request that names one is refused (``reserved_in``).
2. The unit has a second floor that does not read ``source``: while a remote session is on, a cued kind (a head move far from
   center, find, photo, dance, game, listen) from a call that is not a controller's must carry this host's session id as its
   ``token``. The host announces the id in every ``self.remote.session`` heartbeat and stamps it, at the one place every unit
   tool call passes (``XiaozhiServer.call_device_tool``), on every such call that is not made for a controller. A call made
   while a controller's action runs is never stamped, so a controller call that reaches the unit unmarked is refused there.

The paired host is trusted by design. This closes the case of a host bug, not a hostile host. See docs/design/safety-and-privacy.md.
"""

from __future__ import annotations

import contextlib
import contextvars
import secrets
from collections.abc import Callable, Iterator, Mapping
from typing import Any

SESSION_TOOL = "self.remote.session"

# Keys only the host may put on a unit tool call. A controller's request never carries them.
CONTROLLER_RESERVED = frozenset({"source", "token", "host", "host_id", "cue", "cue_kind"})

_controller: contextvars.ContextVar[bool] = contextvars.ContextVar("maipai_controller_scope", default=False)


def new_host_id() -> int:
    """A random id for this host process, 1 to 2**31 - 2 (the unit's token field is a positive 31 bit integer)."""
    return secrets.randbelow(2**31 - 2) + 1


def gated_kind(name: str, arguments: Mapping[str, Any]) -> str | None:
    """The cue kind a unit tool call belongs to when it is a remote-facing action, else None (patch TC01)."""
    if name == "self.robot.set_head_angles":
        return "move"
    if name == "self.robot.dance":
        return "dance"
    if name == "self.game.start":
        return "game"
    if name == "self.audio.play_sound" and arguments.get("find") == 1:
        return "find"
    if name == "self.listen.test":
        return "listen"
    if name == "self.camera.take_photo":
        return "photo"
    return None


def reserved_in(values: Mapping[str, Any]) -> list[str]:
    """The reserved keys a controller's request names, sorted. Empty when the request is clean."""
    return sorted(key for key in values if key in CONTROLLER_RESERVED)


@contextlib.contextmanager
def controller_scope() -> Iterator[None]:
    """Marks the current context (task or thread) as running a controller's action: its unit calls are never stamped with the host id."""
    token = _controller.set(True)
    try:
        yield
    finally:
        _controller.reset(token)


def carry_scope(fn: Callable[..., Any]) -> Callable[..., Any]:
    """``fn`` wrapped to run in a copy of the caller's context: hand it to a thread, a timer or an executor, and a controller's scope goes with it."""
    context = contextvars.copy_context()
    return lambda *args, **kwargs: context.run(fn, *args, **kwargs)


def in_controller_scope() -> bool:
    return _controller.get()


def stamp_call(name: str, arguments: Mapping[str, Any], host_id: int) -> dict[str, Any]:
    """The arguments to send for one unit tool call: the session heartbeat gets the host id, and a cued-kind call that is not
    a controller's gets it as ``token``. Anything the caller put in ``host`` is replaced; a call marked source remote is left
    exactly as the cue marked it."""
    out = dict(arguments)
    if name == SESSION_TOOL:
        out["host"] = host_id
        return out
    if in_controller_scope() or out.get("source") == "remote":
        return out
    if gated_kind(name, out) is not None:
        out["token"] = host_id
    return out
