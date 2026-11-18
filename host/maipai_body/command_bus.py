# ruff: noqa: E501
"""The command bus: one vocabulary, who may send each command, and who wins when two sources disagree.

docs/design/llm-display-control-2026-11-17.md sections 3 to 6. The model's tags, Home, the owner's settings page and the host's own
routines are different *sources* of the same *commands*. A source gets no special power: every command passes the same checks, in
this order, before the unit hears of it:

1. the catalog (:data:`CATALOG`): is it a command, with arguments that clamp to its limits;
2. the permission matrix (:data:`MATRIX`): may this source send it (Y yes, L yes within the limits written in the entry, C only with
   a cue the unit shows, O the owner's own action, N never);
3. the gates (:class:`Gate`): privacy and sleep, a remote cue holding the unit, a child present;
4. the priority rule: the owner beats Home, Home beats the host's routines, routines beat the model; a lower source cannot replace a
   higher source's lease on a surface (face, effect, ring light) until it ends;
5. the model's own rate limits, per reply and per minute;
6. the executor (the call that reaches the unit).

The bus returns :class:`Result` (``ok``, ``shown``, ``reason``) and never raises for a refusal; a refused command is dropped and counted,
never spoken, never an error to the person. The source is set by the host from the channel a command arrived on; a command cannot
name its own source. The unit stays the final floor: it clamps again and never relaxes one of its own rules.

Not here yet (the design's later phases): cards and the ``show_card`` function (they need a unit tool that does not exist, phase 4 and
5), the unit's touch and local voice as sources, and the page, banner and head commands (they keep their own paths and appear in the
catalog only so the matrix says the model may not send them).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from maipai_body import reply_tags
from maipai_body.scenes import SceneBook

logger = logging.getLogger("maipai_body.command_bus")

# ---- sources and priority ------------------------------------------------------------------------------------

SOURCES: tuple[str, ...] = ("model", "owner", "home", "routines", "agent")
# Lower number wins (design section 6: owner controls 5, Home 6, host routines 7, the model's decoration 8).
PRIORITY: dict[str, float] = {"owner": 5, "home": 6, "routines": 7, "agent": 7.5, "model": 8}  # the coding agent: below the host's routines, above the model

# ---- the catalog: one entry per command -----------------------------------------------------------------------

# surface: what a command draws on (a lease is per surface); tool: the unit tool behind it, "" when the host decides
# cost: a rough relative weight, for the unit's governor and the tests; limits: the ceilings the bus clamps to.
CATALOG: dict[str, dict[str, Any]] = {
    "face.mood": {"surface": "face", "tool": "expression", "cost": 1, "limits": {"mood": reply_tags.MOODS}},
    "fx.set": {
        "surface": "fx",
        "tool": "self.overlay.set",
        "cost": 3,
        "limits": {"name": reply_tags.OVERLAYS, "intensity": reply_tags.INTENSITIES, "seconds": (1, reply_tags.MAX_SECONDS), "model_seconds": 20},
    },
    "fx.clear": {"surface": "fx", "tool": "self.overlay.clear", "cost": 0, "limits": {}},
    "light.look": {
        "surface": "light",
        "tool": "ring light",
        "cost": 1,
        "limits": {"color": (*reply_tags.LIGHT_COLORS, reply_tags.LIGHT_OFF), "seconds": (1, reply_tags.MAX_SECONDS), "model_seconds": reply_tags.MODEL_LIGHT_MAX_S},
    },
    "sound.play": {"surface": "sound", "tool": "self.audio.play_sound", "cost": 1, "limits": {"name": reply_tags.MODEL_SOUNDS}},
    "scene.set": {"surface": "scene", "tool": "", "cost": 5, "limits": {"name": reply_tags.SCENE_NAMES}},
    "scene.clear": {"surface": "scene", "tool": "", "cost": 0, "limits": {}},
    # Listed so the matrix says plainly that the model may not send them. They keep their own paths (head_commands, games, remote).
    "head.move": {"surface": "head", "tool": "self.robot.set_head_angles", "cost": 2, "limits": {}},
    "dance.start": {"surface": "head", "tool": "self.robot.dance", "cost": 2, "limits": {}},
    "camera.photo": {"surface": "camera", "tool": "self.camera.take_photo", "cost": 2, "limits": {}},
    "privacy.set": {"surface": "privacy", "tool": "self.privacy.set", "cost": 0, "limits": {}},
}

# The source-by-permission matrix (design section 5), as data. Y yes, L yes within the entry's limits, C only with a cue the unit
# shows, O the owner's own action only, N never.
MATRIX: dict[str, dict[str, str]] = {
    "face.mood": {"model": "L", "owner": "Y", "home": "Y", "routines": "Y", "agent": "N"},
    "fx.set": {"model": "L", "owner": "Y", "home": "Y", "routines": "Y", "agent": "N"},
    "fx.clear": {"model": "L", "owner": "Y", "home": "Y", "routines": "Y", "agent": "N"},
    "light.look": {"model": "L", "owner": "Y", "home": "Y", "routines": "Y", "agent": "L"},
    "sound.play": {"model": "L", "owner": "Y", "home": "Y", "routines": "Y", "agent": "L"},
    "scene.set": {"model": "L", "owner": "Y", "home": "Y", "routines": "N", "agent": "N"},
    "scene.clear": {"model": "L", "owner": "Y", "home": "Y", "routines": "N", "agent": "N"},
    "head.move": {"model": "N", "owner": "C", "home": "Y", "routines": "Y", "agent": "N"},
    "dance.start": {"model": "N", "owner": "C", "home": "Y", "routines": "Y", "agent": "N"},
    "camera.photo": {"model": "N", "owner": "C", "home": "Y", "routines": "Y", "agent": "N"},
    "privacy.set": {"model": "N", "owner": "O", "home": "N", "routines": "N", "agent": "N"},
}

# What a scene may expand into: the display commands and nothing that moves the body, takes a photo or changes privacy.
SCENE_PARTS: frozenset[str] = frozenset({"face.mood", "fx.set", "fx.clear", "light.look", "sound.play"})

# The model's limits (design section 8.5): per reply, per minute, and the least time between two of the same kind.
MODEL_LIMITS: dict[str, dict[str, float]] = {
    "face.mood": {"reply": 4, "minute": 20, "gap_s": 0},
    "fx.set": {"reply": 1, "minute": 6, "gap_s": 0},
    "fx.clear": {"reply": 4, "minute": 20, "gap_s": 0},
    "light.look": {"reply": 1, "minute": 4, "gap_s": 0},
    "sound.play": {"reply": 1, "minute": 4, "gap_s": 10},
}
# The coding agent's limits (package coding_companion): a tone at most once a minute, the light coalesced to a few changes a minute.
AGENT_LIMITS: dict[str, dict[str, float]] = {
    "light.look": {"reply": 99, "minute": 12, "gap_s": 0},
    "sound.play": {"reply": 99, "minute": 1, "gap_s": 60},
}
SAME_EFFECT_GAP_S = 10.0  # the model may not restart the same effect sooner than this


@dataclass(frozen=True)
class Command:
    """One thing a source asks for. ``source`` is set by the host from the channel, never by the content."""

    cmd: str
    args: dict[str, Any] = field(default_factory=dict)
    source: str = "model"
    cued: bool = False  # a cue the unit shows goes with it (the C rows)


@dataclass
class Result:
    ok: bool
    shown: bool = False
    reason: str = ""
    args: dict[str, Any] = field(default_factory=dict)  # the arguments after clamping
    parts: list[tuple[str, Result]] = field(default_factory=list)  # a scene's expanded commands, in order

    @property
    def mood(self) -> str | None:
        """The mood a scene (or a plain ``face.mood``) was allowed to set: the caller draws it."""
        for name, result in self.parts:
            if name == "face.mood" and result.ok:
                return result.args.get("mood")
        return self.args.get("mood") if self.ok and "mood" in self.args else None


@dataclass(frozen=True)
class Gate:
    """What outranks decoration right now (design sections 6 and 10). The turn bridge and Home fill it in."""

    muted: bool = False  # hard mute or full quiet: no sound, and no decoration from any source but the owner
    blocked: bool = False  # sleep, the low-battery tired look: no effect, light or sound from the model, Home or routines
    remote: bool = False  # a remote cue holds the unit: it always wins
    child: bool = False  # Home says a child is present: the model's sounds are limited to the quiet set


class ReplyBudget:
    """The model's counts for one reply. Make one per reply with :meth:`CommandBus.new_reply`."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}


@dataclass
class _Lease:
    source: str
    until: float


Executor = Callable[[str, dict[str, Any]], bool]


class CommandBus:
    """Validates, permits, arbitrates and rate-limits a command, then calls its executor.

    ``executors`` maps a command name to ``(device_id, clamped_args) -> bool``; ``face.mood`` has none by default (the caller draws
    the mood and the bus only says whether it was allowed). ``gate`` says what outranks decoration for a unit; ``scenes`` is the
    scene book that expands ``scene.set``.
    """

    def __init__(
        self,
        executors: dict[str, Executor] | None = None,
        *,
        gate: Callable[[str], Gate] | None = None,
        scenes: SceneBook | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.executors: dict[str, Executor] = dict(executors or {})
        self.gate = gate or (lambda _device: Gate())
        self.scenes = scenes
        self._clock = clock
        self._leases: dict[tuple[str, str], _Lease] = {}
        self._history: dict[tuple[str, str], deque[float]] = {}
        self._last_fx: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()
        self.dropped = 0  # refusals of any kind, for the bench

    def new_reply(self) -> ReplyBudget:
        return ReplyBudget()

    # ---- the one entry ---------------------------------------------------------------------------------------

    def send(self, device_id: str, command: Command, budget: ReplyBudget | None = None, *, defer: list | None = None) -> Result:
        """Check and, when allowed, run one command. With ``defer`` (a list) the checks are made and recorded but the unit calls are
        not: each is appended as ``(executor, device_id, args)`` for the caller to run off its own thread."""
        spec = CATALOG.get(command.cmd)
        if spec is None:
            return self._refuse(command, "unknown command")
        if command.source not in PRIORITY:
            return self._refuse(command, "unknown source")
        if not self._permitted(command):
            return self._refuse(command, "not allowed for this source")
        args = self._clamp(command, spec)
        if args is None:
            return self._refuse(command, "bad argument")
        if command.cmd in ("scene.set", "scene.clear"):
            return self._scene(device_id, command, args, budget, defer)
        if command.cmd not in SCENE_PARTS:
            return self._refuse(command, "not handled by the bus")  # permitted, but the command keeps its own path
        reason = self._gated(device_id, command, args)
        if reason:
            return self._refuse(command, reason, args)
        with self._lock:
            reason = self._arbitrate(device_id, command, spec, args) or self._limit(device_id, command, args, budget)
            if reason:
                return self._refuse(command, reason, args)
            self._record(device_id, command, spec, args, budget)
        executor = self.executors.get(command.cmd)
        if executor is None:
            return Result(True, shown=False, reason="", args=args)  # allowed; the caller draws (the face mood)
        if defer is not None:
            defer.append((executor, device_id, args))
            return Result(True, shown=True, args=args)  # allowed and queued
        try:
            shown = bool(executor(device_id, args))
        except Exception:
            logger.debug("command %s failed", command.cmd, exc_info=True)
            shown = False
        return Result(True, shown=shown, reason="" if shown else "the unit did not take it", args=args)

    # ---- the steps -------------------------------------------------------------------------------------------

    def _refuse(self, command: Command, reason: str, args: dict[str, Any] | None = None) -> Result:
        self.dropped += 1
        logger.debug("command %s from %s dropped: %s", command.cmd, command.source, reason)  # the reason only, never the arguments
        return Result(False, reason=reason, args=args or {})

    @staticmethod
    def permission(source: str, cmd: str) -> str:
        return MATRIX.get(cmd, {}).get(source, "N")

    def _permitted(self, command: Command) -> bool:
        level = self.permission(command.source, command.cmd)
        if level in ("Y", "L"):
            return True
        if level == "C":
            return command.cued
        if level == "O":
            return command.source == "owner"
        return False

    _REQUIRED = {"face.mood": "mood", "fx.set": "name", "light.look": "color", "sound.play": "name", "scene.set": "name"}

    def _clamp(self, command: Command, spec: dict[str, Any]) -> dict[str, Any] | None:
        """The arguments inside the catalog's limits, or None when one is not valid (an unknown name is never guessed at)."""
        limits, given, out = spec["limits"], command.args, {}
        model = command.source in ("model", "agent")
        agent = command.source == "agent"
        for key, allowed in limits.items():
            if key == "model_seconds" or key not in given:
                continue
            value = given[key]
            if key == "seconds":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    return None
                value = int(round(max(allowed[0], min(allowed[1], value))))
                if model:
                    value = min(value, limits["model_seconds"])
            elif value not in allowed or (agent and command.cmd == "sound.play" and value not in reply_tags.QUIET_SOUNDS):
                return None
            out[key] = value
        need = self._REQUIRED.get(command.cmd)
        if need and need not in out:
            return None
        if command.cmd == "fx.set":
            out.setdefault("intensity", reply_tags.DEFAULT_INTENSITY)
            out.setdefault("seconds", min(reply_tags.DEFAULT_SECONDS, limits["model_seconds"]) if model else reply_tags.DEFAULT_SECONDS)
        if command.cmd == "light.look":
            out.setdefault("seconds", reply_tags.DEFAULT_LIGHT_S if not model else min(reply_tags.DEFAULT_LIGHT_S, limits["model_seconds"]))
        return out

    def _gated(self, device_id: str, command: Command, args: dict[str, Any]) -> str:
        gate = self.gate(device_id)
        owner = command.source == "owner"
        cmd = command.cmd
        if cmd == "sound.play" and gate.muted:
            return "muted"  # a hard mute holds for every source, the owner's Test included
        if owner or cmd == "face.mood":
            return ""
        decoration = cmd in ("fx.set", "light.look", "sound.play")
        if decoration and gate.muted:
            return "muted"
        if decoration and gate.blocked:
            return "asleep or blocked"
        if decoration and gate.remote:
            return "a remote cue holds the unit"
        if cmd == "sound.play" and gate.child and command.source in ("model", "agent") and args.get("name") not in reply_tags.QUIET_SOUNDS:
            return "a child is present"
        return ""

    def _arbitrate(self, device_id: str, command: Command, spec: dict[str, Any], args: dict[str, Any]) -> str:
        surface = spec["surface"]
        if surface not in ("face", "fx", "light"):
            return ""
        lease = self._leases.get((device_id, surface))
        if lease is not None and lease.until <= self._clock():
            del self._leases[(device_id, surface)]
            lease = None
        if lease is not None and PRIORITY[command.source] > PRIORITY[lease.source]:
            return "lower priority"
        return ""

    def _limit(self, device_id: str, command: Command, args: dict[str, Any], budget: ReplyBudget | None) -> str:
        table = AGENT_LIMITS if command.source == "agent" else MODEL_LIMITS
        if command.source not in ("model", "agent") or command.cmd not in table:
            return ""
        rules = table[command.cmd]
        now = self._clock()
        if budget is not None and budget.counts.get(command.cmd, 0) >= rules["reply"]:
            return "one per reply" if rules["reply"] == 1 else "too many in one reply"
        history = self._history.setdefault((device_id, command.cmd), deque())
        while history and now - history[0] > 60.0:
            history.popleft()
        if len(history) >= rules["minute"]:
            return "too many in a minute"
        if rules["gap_s"] and history and now - history[-1] < rules["gap_s"]:
            return "too soon after the last one"
        if command.cmd == "fx.set" and now - self._last_fx.get((device_id, args["name"]), float("-inf")) < SAME_EFFECT_GAP_S:
            return "the same effect just ran"
        return ""

    def _record(self, device_id: str, command: Command, spec: dict[str, Any], args: dict[str, Any], budget: ReplyBudget | None) -> None:
        now = self._clock()
        surface = spec["surface"]
        if surface in ("fx", "light"):
            seconds = args.get("seconds", 0) if command.cmd != "fx.clear" else 0
            if command.cmd == "light.look" and args.get("color") == reply_tags.LIGHT_OFF:
                seconds = 0
            if seconds:
                self._leases[(device_id, surface)] = _Lease(command.source, now + seconds)
            else:
                self._leases.pop((device_id, surface), None)
        if (command.source == "model" and command.cmd in MODEL_LIMITS) or (command.source == "agent" and command.cmd in AGENT_LIMITS):
            self._history.setdefault((device_id, command.cmd), deque()).append(now)
            if budget is not None:
                budget.counts[command.cmd] = budget.counts.get(command.cmd, 0) + 1
            if command.cmd == "fx.set":
                self._last_fx[(device_id, args["name"])] = now

    # ---- scenes ----------------------------------------------------------------------------------------------

    def _scene(self, device_id: str, command: Command, args: dict[str, Any], budget: ReplyBudget | None, defer: list | None = None) -> Result:
        if self.scenes is None:
            return self._refuse(command, "scenes are not set up")
        if command.cmd == "scene.set":
            parts = self.scenes.expand(device_id, args["name"])
        else:
            parts = self.scenes.expand_off()
        if not parts:
            return self._refuse(command, "bad argument")
        results: list[tuple[str, Result]] = []
        for name, part_args in parts:
            if name not in SCENE_PARTS:  # a scene can never carry a body move, a photo or a privacy change
                results.append((name, self._refuse(command, "not a scene part")))
                continue
            results.append((name, self.send(device_id, Command(name, part_args, command.source, command.cued), budget, defer=defer)))
        ok = any(r.ok for _, r in results)
        return Result(ok, shown=any(r.shown for _, r in results), reason="" if ok else "nothing in the scene could be shown", args=args, parts=results)
