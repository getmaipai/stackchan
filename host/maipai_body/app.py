"""MaiPai Bot's Reachy Mini app: the daemon's one running app.

Registered under the ``reachy_mini_apps`` entry point (``pyproject.toml``)
as ``MaiPaiBody``. Builds the Reachy Mini client through the HAL seam
from the ``ReachyMini`` handle the daemon hands it, holds neutral, logs
one line per state change, and honors ``stop_event`` and SIGINT within
one second while unpaired; once G4's hub link reports paired, hands off
to G9's real ``ConversationLoop`` (audio, wake word, STT/turn/TTS
against the hub, expression, and FACE-01's face recognition) for the
rest of the process's life. ``run_paired_body`` is that whole path,
RM-03's own scaffold's real destination.

One caveat to the sub-second-stop contract, found by a code review
fixed by FACE-05: once paired, ``_build_conversation_loop`` runs on its
own daemon thread while this function polls ``stop_event``. A stop or
SIGINT mid-download is honored within one poll interval, abandoning the
in-progress build; that download continues or not on its own daemon
thread, which is moot since the process is exiting.
"""

from __future__ import annotations

import asyncio
import errno
import importlib.metadata
import json
import logging
import math
import os
import random
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maipai_body import wake_look as wake_look_mod
from maipai_body import service_threads
from maipai_body.bodies.stackchan.companion import DIAGNOSTIC_KINDS
from maipai_body.bodies.stackchan.head_search import (
    AMBIENT_FACE_QUIET_S,
    AMBIENT_HOLD_S,
    AMBIENT_MOVE_QUIET_S,
    ASKED_REASONS,
    DARK_COOLDOWN_S,
    FACE_REASONS,
    GLANCE_PITCH_DEG,
    MOVE_SPEED,
    SPEAKER_PITCH_DEG,
    STEP_S,
    TURN_SPEED,
    HeadSearch,
)
from maipai_body.bodies.stackchan.head_touch_filter import HEAD_KINDS, HeadTouchFilter
from maipai_body.bodies.stackchan.idle_faces import IdleFaces
from maipai_body.bodies.stackchan.person_tracker import (
    PERSON_HINT_SCORE,
    SPEAKER_PERSON_FRESH_S,
    PersonTracker,
    choose_person,
)
from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG as CENTER_PITCH_DEG_WAKE
from maipai_body.expression.engine import ExpressionEngine
from maipai_body.expression.suppression import SuppressionContext
from maipai_body.hal.errors import BodyLost, NotPermitted
from maipai_body.hal.seam import AntennaPositions, HeadActuator, HeadPose, Indicator, NullIndicator
from maipai_body.indicator.director import EyesDirector
from maipai_body.indicator.live import LiveCaptureTap
from maipai_body.initiative.alarm import AlarmController, chime_samples
from maipai_body.link import HubLinkClient, PairingStore, discover_hub
from maipai_body.link.discovery import DiscoverHub
from maipai_body.link.lifecycle import LinkLifecycle
from maipai_body.link.offline import OfflineRungs
from maipai_body.link.prints import PrintSync
from maipai_body.link.roster import RosterPoller
from maipai_body.link.rung0 import Rung0Cues
from maipai_body.link.state import StateReporter
from maipai_body.link.state_machine import (
    DEFAULT_SLEEP_AFTER_MINUTES,
    LinkPhase,
    LinkStateMachine,
)
from maipai_body.link.supervisor import LinkSupervisor
from maipai_body.link.timesync import ClockSync, system_clock_setter
from maipai_body.presence.entries import presence_entries_from
from maipai_body.presence.motor_health import MotorHealth
from maipai_body.presence.night import NightController
from maipai_body.presence.thermal import ThermalMonitor
from maipai_body.settings_keys import power_warn_at
from maipai_body.speech.capture import AudioCapture
from maipai_body.speech.follow_up import FollowUpPolicy, PeopleDirectory
from maipai_body.speech.models import EMBEDDING, MELSPECTROGRAM, WAKE_PHRASE, ensure_wakeword_models
from maipai_body.speech.offline_clips import (
    AssetUnavailable,
    ClipsUnavailable,
    CodeAnnouncer,
    ManifestError,
    OfflineSpeaker,
    alarm_child_clip_ids,
    alarm_clip_ids,
    ensure_clip_bundle,
)
from maipai_body.speech.playback import AudioPlayback
from maipai_body.speech.stt_stream import SttStreamClient
from maipai_body.speech.tts_playback import TtsPlaybackClient
from maipai_body.speech.turn_client import TurnClient
from maipai_body.speech.wake import OpenWakeWordEngine, WakeScorer
from maipai_body.vision.embed import ensure_embedder
from maipai_body.vision.gallery import FaceGallery
from maipai_body.vision.models import SFACE

UNIT_LINK_ENCRYPTED = False  # StackChan currently connects to this service over plain ws.

try:
    if os.environ.get("MAIPAI_HUB_HOST") == "1":
        # A body hosted by Home (StackChan) never drives a Reachy daemon: the hub bundle ships no
        # Reachy SDK, and a development checkout that has it must behave the same way.
        raise ImportError("hosted body: the Reachy SDK is not used")
    import reachy_mini
    from reachy_mini import ReachyMini, ReachyMiniApp

    from maipai_body.bodies.reachy_mini.client import ReachyMiniClient
    from maipai_body.bodies.reachy_mini.eyes_client import EyesClient
    from maipai_body.bodies.reachy_mini.motors import DaemonMotorBus, MotorGate
    from maipai_body.bodies.reachy_mini.profile import REACHY_MINI_PROFILE
    from maipai_body.run_loop import ConversationLoop
    from maipai_body.vision.watch import VisionWatch

    _reachy_imported = True
except ImportError:
    reachy_mini = None
    ReachyMini = Any
    _reachy_imported = False
    VisionWatch = Any

    class ReachyMiniApp:
        """Tiny runner shim used only by the standalone StackChan host."""

        settings_app = None

        def __init__(self, *args, **kwargs) -> None:
            pass

        def wrapped_run(self) -> None:
            self.run(None, threading.Event())

        def stop(self) -> None:
            pass

    class _MissingReachyClient:
        pass

    ReachyMiniClient = _MissingReachyClient
    EyesClient = Any
    DaemonMotorBus = Any
    MotorGate = Any
    REACHY_MINI_PROFILE = None

if _reachy_imported:
    from maipai_body.run_loop import ConversationLoop
    from maipai_body.vision.detect import FiveLandmarkDetector
else:
    ConversationLoop = None
    FiveLandmarkDetector = None


logger = logging.getLogger("maipai_body.app")

# Unit events that are logged one line each: the head touch kinds and the shake.
_LOGGED_UNIT_EVENTS = HEAD_KINDS | {"shake"}


def _reaction_kind(event) -> str:
    """What the reactions hear: a head touch the unit confirmed with its motion sensor (firmware
    patch 081, ``"tap":1``) is a tap; it reacts like a pet and is logged as a tap."""
    kind = str(getattr(event, "kind", event))
    extra = getattr(event, "extra", None) or {}
    if kind == "head_touch" and extra.get("tap") in (1, True):
        return "head_tap"
    return kind


def _stackchan_selected(environ: Mapping[str, str] | None = None) -> bool:
    """Whether this Bot process is configured to serve a StackChan body."""
    from maipai_body.bodies.registry import selected

    return selected(environ).id == "stackchan"


def _no_hub_discovery(timeout_s: float = 5.0):
    """An explicit Home URL is the configured trust anchor for sidecars."""
    return None


# The face watchdog (see StackChanBehavior.face_watchdog): quiet seconds before a stuck face is
# repaired, and how often the idle face is resent while all is well.
FACE_QUIET_S = 5.0
# While drowsy or asleep the unit is asked for touch events this often; wakes repeat no sooner.
LOOK_INTERVAL_S = 0.5  # two looks a second at most
SEES_HOLD_S = 2.0  # the vision indicator keeps its glow this long after the last sighting
TURN_FACE_FRESH_S = 60.0  # turn toward a face seen this recently when a turn starts
LOST_AFTER_LOOKS = 4  # two seconds without the face it was following: it was lost
TOUCH_POLL_S = 0.5  # asleep too: at 5 s a tap or shake took up to 5 s to wake the unit
EVENT_POLL_S = 0.5  # touch, swipe and shake events are read this often while the robot is awake
IDLE_FACES_ENABLED = True
TOUCH_WAKE_COOLDOWN_S = 30.0
IN_VIEW_S = 120.0  # a face seen this recently counts as someone being there to hear a line
KEEP_AWAKE_S = 60.0  # how often the unit is told the hub is reachable (firmware patch 074)
FACE_REFRESH_S = 30.0


class StackChanBehavior:
    """Shared expression and bounded anonymous tracking for an attached StackChan."""

    def __init__(
        self, robot, *, vision_bridge=None, idle_interval_s: float = 8.0, baseline_path=None
    ) -> None:
        from maipai_body.bodies.stackchan.gaze import GazeState
        from maipai_body.bodies.stackchan.presence_watch import CameraStats, GreetingPolicy
        from maipai_body.bodies.stackchan.profile import STACKCHAN_PROFILE
        from maipai_body.expression.engine import ExpressionEngine

        self.robot = robot
        self._holder = "stackchan-runtime"
        self._lock = threading.RLock()
        self._active = threading.Event()
        self._phase = "idle"
        self._closed = threading.Event()
        self._presence_stop: threading.Event | None = None
        self._presence_thread: threading.Thread | None = None
        self._vision = vision_bridge
        self._idle_interval_s = idle_interval_s
        self._last_idle = 0.0
        self._expression = ExpressionEngine(robot._driver("head"), STACKCHAN_PROFILE)
        # BOT-FACE-NIGHT-01: at night no idle or tracking gestures; set by the night rule.
        self.night_active: Callable[[], bool] = lambda: False
        # Charging or on USB power: no wandering. Set by the power rule (power_idle.py).
        self.idle_still: Callable[[], bool] = lambda: False
        self.idle_still_reason: Callable[[], str] = lambda: ""
        # The unit's movement limiter (firmware ML01), set once the unit's tool channel is wired; None until then (no limit known).
        self.motion_limit: Any = None
        # robot.idle.level from the settings frame (still, calm, lively). Still until the hub says
        # otherwise: a fresh or lost-settings unit never wanders (owner request 2026-10-20).
        self.idle_level = "still"
        # Owner settings "Look toward the speaker" and "Look for faces" (both off until chosen):
        # the head turns toward a face or body at listen start, glances up after someone speaks,
        # and searches for faces on its own only when these are on (a person's spoken "find me"
        # request always works).
        self.look_toward_speaker = False
        self.look_for_faces = False
        # "Look around when I hear the wake word" (wake_look.py; default on, needs no camera). The hooks are set by the service wiring:
        # what the unit says (locked, a game), and whether the unit's own seeker owns seeking.
        self.look_on_wake = True
        self.wake_unit_busy: Callable[[], str] = lambda: ""
        self.wake_seeker_owns: Callable[[], bool] = lambda: False
        self.wake_looks = 0
        self.wake_look_scale = 1.0  # tests set 0 to run the pan at once
        self._wake_stop = threading.Event()
        self._wake_thread: threading.Thread | None = None
        self._last_wake_look = float("-inf")
        # Why the unit is occupied (a turn is running, or full quiet is on), "" when free: set once
        # the voice bridge exists. No idle look starts while it is not empty.
        self.head_busy: Callable[[], str] = lambda: ""
        # True once any move left the head off center; the post-turn settle only runs then.
        self._head_off_center = False
        self._hold_until = float("-inf")
        # Touch, swipe and shake events from the unit (patch 021) wake a drowsy or sleeping robot.
        # Set by the service wiring; None means no unit events are available.
        self.event_poll: Callable[[], list] | None = None
        # Events of every other connected unit, read once a second: handlers are called as (device_id, events). The first
        # unit's events go through wake_on_touch; touch reactions, the music dance and self-heal stay with that unit.
        self.other_unit_event_handlers: list[Callable[[str, list], None]] = []
        self.first_run_hook: Callable[[str | None, dict], object] | None = None  # the name picked on the robot's first run (first_run_name.py)
        self.primary_unit: Callable[[], str | None] = lambda: None
        self.unit_facts: Any = (
            None  # link.checkin.UnitFacts: the latest boot, memory and firmware facts
        )
        # The unit's own volume and brightness sliders: (volume, brightness), either may be None.
        self.on_levels_changed: Callable[[int | None, int | None], None] | None = None
        # Every diagnostic event (kind, extra), for the self-healing state (xiaozhi server).
        self.on_unit_event: Callable[[str, dict], object] | None = None
        # Gets the kinds of the events read ("head_touch", "shake", ...); set by the service wiring.
        self.reaction: Callable[[list[str]], object] | None = None
        self.reaction_tick: Callable[[], object] | None = None
        # Orientation: the pose logic, its timer, and whether a pose face is being held.
        self.orientation: Any = None
        self.on_firmware_version: Callable[[object], None] = lambda _version: None
        self.vision_poster: Any = None  # vision_post.VisionPoster: scene descriptions from Home
        self.lux: Callable[[], float | None] = lambda: None  # the unit's light sensor, if read
        self._vision_posting = False
        self._vision_last: tuple[str | None, Any] | None = None  # bucket and thumbnail last posted
        self.orientation_tick: Callable[[], object] | None = None
        # Tells the unit the hub is reachable, so it does not sleep or power off for being idle.
        self.keep_awake_tick: Callable[[], object] | None = None
        self.pose_held: Callable[[], bool] = lambda: False
        # The little dance (dance.py, dance_wiring.py): settings, whether one is running (the
        # ambient moves, the face watchdog and the look-around stay out of it), the unit's head
        # events (a touch ends one) and the hub's "dance" device command.
        from maipai_body.bodies.stackchan.dance import DanceSettings

        self.dance_settings = DanceSettings()
        self.dance_active: Callable[[], bool] = lambda: False
        self.dance_events: Callable[[list, float], object] | None = None
        self.dance_command: Callable[[dict], dict | None] = lambda _payload: {
            "dance": "refused",
            "why": "the dance is not ready",
        }
        # The music dance (music_dance.py, music_dance_wiring.py): the unit's per-second music
        # numbers and the hub's "music_test" device command.
        self.music_feat: Callable[[dict, float], object] | None = None
        self.idle_faces: IdleFaces | None = None
        self.music_clip: Callable[[str, dict, float], object] | None = None
        self.music_command: Callable[[dict], dict | None] = lambda _payload: {
            "music_test": "refused",
            "why": "the music dance is not ready",
        }
        self.listen_song_command: Callable[[dict], dict | None] = lambda _payload: {
            "listen_song": "refused",
            "why": "song naming is not ready",
        }
        self.wifi_add_command: Callable[[dict], dict | None] = lambda _payload: {
            "wifi": "refused",
            "why": "Wi-Fi management is not ready",
        }
        self.wifi_forget_command: Callable[[dict], dict | None] = lambda _payload: {
            "wifi": "refused",
            "why": "Wi-Fi management is not ready",
        }
        self.wifi_use_command: Callable[[dict], dict | None] = lambda _payload: {
            "wifi": "refused",
            "why": "Wi-Fi management is not ready",
        }
        self.prefer_tailnet_command: Callable[[dict], dict | None] = lambda _payload: {
            "tailnet": "refused",
            "why": "the robot is not ready",
        }
        self.song_title_command: Callable[[dict], dict | None] = lambda _payload: {
            "song_title": "unavailable",
        }
        self._last_event_poll = float("-inf")
        self._last_touch_wake = float("-inf")
        self._event_queue_drained = False
        self._head_filter = HeadTouchFilter()
        # A short look around (head_search.py): for a face when the picture moves without one,
        # and before concluding the room is dark. Quiet, gated, never in a turn or while resting.
        self._search = HeadSearch()
        # Find the person, then the face (person_tracker.py, owner design 2026-11-12): the Look
        # detector's person box aims the head, then the face is looked for above it. It replaces
        # the ambient sweep above whenever the Look model is loaded.
        self._tracker = PersonTracker()
        self._tracker_last_look_at: float | None = None
        # The false-person rate: looks and looks with a person box over a window with no face.
        self._fp_window_at: float | None = None
        self._fp_looks = 0
        self._fp_person_looks = 0
        self._fp_face_seen = False
        # The vision indicator (light_service.py `sees`): told on every change of what the camera
        # sees ("maybe", "person", "face" or None); the ring shows it only when the setting is on.
        self.on_sees: Callable[[str | None], object] | None = None
        self._sees: str | None = None
        self._sees_at = float("-inf")  # when something was last seen: the glow holds a moment
        # A spoken "turn to me" / "find me" (head_commands.py): the look for the face the person
        # asked for, started after the reply, ignoring the back-off. (reason, asked at)
        self._find_request: tuple[str, float] | None = None
        # Says one line on the robot's own initiative (the turn bridge's speak_reaction).
        self.announce: Callable[[str], object] | None = None
        # On-unit timers (bodies/stackchan/timers.py): told the unit's timer events; None when off.
        self.timers: Any = None
        # What the robot could not tell the person in time ("what did I miss"; repeat.py) and
        # whether a hard mute or full quiet is on; set where the announcements are wired.
        self.missed_log: Any = None
        self.speech_muted: Callable[[], bool] = lambda: False
        # Called with each settings frame's values (timers, announcements).
        self.settings_listeners: list[Callable[[dict], None]] = []
        # Told whenever a face is seen (a held "turn left" ends then).
        self.on_face_found: Callable[[], object] | None = None
        self._search_detail_seen = False
        self._search_after_turn = (
            False  # someone spoke and no face was in view: look after the reply
        )
        from maipai_body.bodies.stackchan.presence_watch import SceneBaseline

        # The learned empty room; a different picture is a person. Kept on disk when a path is
        # given, so a restart does not learn the room from a picture with someone in it.
        self._baseline = SceneBaseline(baseline_path)
        self._person_share = 0.0  # how much the newest picture differs from it
        self._watching_since: float | None = None  # the first look of this run
        # The unit's own head moves make the picture move: a move raises the flag, the next look
        # stamps it in the look's clock, and motion inside OWN_MOVE_BLIND_S after it is its own.
        self._own_move_flag = False
        self._own_move_at = float("-inf")
        # Looks for a face started by the picture differing from the room, nothing moving: their
        # own back-off (STILL_BACKOFF_S) and the picture the last failed one saw.
        self._search_start_thumb: Any = None  # the picture that started the running ambient look
        self._ambient_since: float | None = None  # when the current no-face trigger began to hold
        self._still_failures = 0
        self._still_failed_at = float("-inf")
        self._still_thumb: Any = None
        self._dark_confirmed_at: float | None = None
        self._camera_blocked_until = float("-inf")
        # Idle face watching: the camera level from the settings frame, the greeting style, and
        # the counters of the unit's camera stream (all set by the service wiring).
        self.watch_level: Callable[[], str] = lambda: "identify"
        self.greeting_mode = "gesture"
        self.camera_counters: Callable[[], tuple[int, int]] = lambda: (0, 0)
        self._camera_stats = CameraStats(lambda: self.camera_counters())
        self._greeting = GreetingPolicy()
        self._last_look = float("-inf")
        self._followed = False
        self._missed_looks = 0
        # The most recent face (frame x, y and when), for turning toward the speaker.
        self._last_face: tuple[float, float, float] | None = None
        self._turn_face_held = False
        self._warned: dict[str, float] = {}
        self.on_idle_level: Callable[[], None] = lambda: None
        # BOT-SC-ANIM-01: drowsy and asleep stages so an idle robot does not sit smiling for hours.
        from maipai_body.bodies.stackchan.profile import STACKCHAN_PROFILE as _profile
        from maipai_body.bodies.stackchan.routines import RestRenderer
        from maipai_body.expression.rest import RestPolicy

        self._rest = RestPolicy(
            time.monotonic(),
            drowsy_after_s=120.0,
            asleep_after_s=300.0,
            quiet_hours_active=lambda: self.night_active(),
        )
        # Why the head is where it is, for "what are you looking at?" (gaze.py).
        self.gaze = GazeState(
            asleep=lambda: self._rest.stage != "awake" or self.night_active(),
            wandering=lambda: not self.idle_still(),
        )
        from maipai_body.bodies.stackchan.head_gate import HeadMotionGate

        self.head_gate = HeadMotionGate(
            must_be_still=lambda: self.idle_still(),
            resting=lambda: self._rest.stage != "awake",
            busy=lambda: self.head_busy(),
            still_reason=lambda: self.idle_still_reason(),
            motion_hold=lambda: self._motion_hold_reason(),
        )
        from maipai_body.bodies.stackchan.sleep_z import SleepZ

        self.sleep_z = SleepZ(
            lambda tool, arguments: self.robot._driver("head").expression_device.client._call(
                tool, arguments
            ),
            self._unit_firmware_version,
        )
        self._rest_renderer = RestRenderer(
            firmware_version=self._unit_firmware_version,
            sleep_z=self.sleep_z,
            quiet_s=lambda: max(0, int(time.monotonic() - self._rest._quiet_since)),
            thresholds=lambda: (120, 300),
            night_active=self.night_active,
        )
        self._rest_profile = _profile
        self._last_person_seen = float("-inf")
        self._face_quiet_since: float | None = None
        self._face_refreshed_at = float("-inf")
        self._night_turned = False

    @property
    def presence_thread_alive(self) -> bool:
        return self._presence_thread is not None and self._presence_thread.is_alive()

    def _with_lease(self, callback):
        with self._lock:
            holder = self.robot.lease_holder
            if holder is None:
                self.robot.lease.acquire(priority="expression", holder=self._holder)
            elif holder != self._holder:
                return False
            try:
                callback()
            finally:
                if self.robot.lease_holder == self._holder:
                    self.robot.lease.release(holder=self._holder)
            return True

    def hold_pose(self, seconds: float) -> None:
        """Keep the post-turn settle from undoing a head pose the person just asked for."""
        self._hold_until = time.monotonic() + seconds

    def render_primitive(self, primitive: str) -> bool:
        if self.night_active() or self.pose_held() or self._rest.stage != "awake":
            return False
        if self.dance_active():
            return False
        # Ambient moves (the idle settle, face following) go through the one head-motion gate.
        if not self.head_gate.allow(f"ambient:{primitive}", response=self._active.is_set()):
            return False
        self._head_off_center = True
        self._note_own_move()
        return self._with_lease(
            lambda: self._expression.render_ambient(primitive, SuppressionContext())
        )

    def _unit_firmware_version(self) -> str | None:
        """The firmware version the unit reported, or None before its first report."""
        if self.unit_facts is None:
            return None
        return self.unit_facts.snapshot().get("fw_version")

    def render_turn_state(self, state: str, *, mood: str | None = None) -> None:
        self._active.set()
        was_resting = self._rest.stage != "awake"  # the turn wakes it just below; a wake from sleep does not look around
        if state != "listening":
            self.stop_wake_look()  # the reply began, the turn ended or a stop word came: the pan ends where it is
        if self._rest.stage != "awake":
            # A turn wakes the robot at once (blink, screen, ring) before its own face is shown.
            try:
                self.rest_step(time.monotonic())
            except Exception:
                self._warn_limited("rest", "StackChan rest routine failed")
        # "listening" leaves room for a pet's face; thinking and speaking own the face and voice.
        self._phase = {"listening": "listening", "settle": "idle"}.get(state, "busy")
        # Only states that really move the head ask the gate (and count toward its cap); the
        # settle back to center is essential and always passes.
        moves = state in {"listening", "thinking", "speaking"}
        may_move = (
            self.head_gate.allow(f"turn:{state}", response=True)
            if moves
            else self.head_gate.allow(f"turn:{state}", essential=True)
            if state == "settle"
            else True
        )
        if state == "thinking":
            from maipai_body.bodies.stackchan.gaze import GazeReason

            self.gaze.note(GazeReason.THINKING)
        if self.night_active():
            # One head turn to face whoever speaks, then rest; no other gestures.
            if state == "listening" and not self._night_turned:
                self._night_turned = True
                if may_move:
                    self._head_off_center = True
                    self._with_lease(
                        lambda: self._expression.render_ambient("attend", SuppressionContext())
                    )
            if state == "settle":
                self._night_turned = False
                self._active.clear()
            return
        self._night_turned = False
        primitive = {
            "listening": "perk",  # head lifts and the face brightens: it heard you
            "thinking": "attend",
            "speaking": "speak",
        }.get(state)

        def render() -> None:
            if state == "settle":
                self._turn_face_held = False
                # Only a head that actually left center is brought back: a quiet turn that moved
                # nothing must not move the head again (the unit was settling after every turn).
                if self._head_off_center and may_move and time.monotonic() >= self._hold_until:
                    self._head_off_center = False
                    self._expression.render_ambient("settle", SuppressionContext())
                return
            self._expression.render_turn_state(
                state, mood=mood, firmware_version=self._unit_firmware_version()
            )
            glanced = False
            if state == "listening":
                # "Look toward the speaker" on keeps its own wake turn as it was; the wake look is for when it is off.
                wake_look = (
                    may_move
                    and not self.look_toward_speaker
                    and self._wake_look_allowed(was_resting)
                )
                aim = may_move and (self.look_toward_speaker or wake_look)
                self._turn_face_held = aim and self._turn_toward_face()
                # The glance up replaces the listening perk; both are the one listening move.
                glanced = (
                    not self._turn_face_held
                    and aim
                    and self._glance_up_for_speaker(
                        wake_look_mod.PITCH_DEG if wake_look else SPEAKER_PITCH_DEG
                    )
                )
                if wake_look and glanced:
                    self._start_wake_look()
            if primitive is not None and may_move and not self._turn_face_held and not glanced:
                self._head_off_center = True
                self._expression.render_ambient(primitive, SuppressionContext())
            elif state == "reply_mood":
                self._expression.render_turn_state("reply_mood", mood=mood)

        try:
            self._with_lease(render)
        finally:
            if state == "settle":
                self._active.clear()

    def start_presence(self, stop_event: threading.Event) -> None:
        if self._presence_thread is not None:
            return
        self._presence_stop = threading.Event()
        try:
            # Local watching: silent, and only while robot.camera.watch_level is not "off".
            self.robot.camera.stream(enabled=True, silent=True)
        except Exception:
            logger.warning("StackChan camera stream could not start", exc_info=True)
        self._presence_thread = threading.Thread(
            target=self._presence_loop,
            args=(stop_event, self._presence_stop),
            name="stackchan-presence",
            daemon=True,
        )
        self._presence_thread.start()

    def _presence_loop(self, stop_event: threading.Event, local_stop: threading.Event) -> None:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        while not stop_event.is_set() and not local_stop.wait(0.2):
            if self._closed.is_set():
                return
            # This loop is the first unit's: with several units connected its faces and tools go to that unit only (every other unit has its own loop).
            first = self.primary_unit()
            if first is not None and ACTIVE_UNIT.get() != first:
                ACTIVE_UNIT.set(first)
            now = time.monotonic()
            if (
                not self._active.is_set()
                and not self.idle_still()
                and now - self._last_idle >= self._idle_interval_s
            ):
                self._last_idle = now
                try:
                    self.render_primitive("settle")
                except Exception:
                    self._warn_limited("idle", "StackChan idle expression failed")
            try:
                self.watch_for_faces(now)
                self.post_scene(now)
                self.search_tick(now)
            except Exception:
                self._warn_limited("tracking", "StackChan face watching failed")
            line = self._camera_stats.report(now)
            if line:
                logger.info(line)
            if self._vision is not None:
                check = self._vision.frame_check.report(now)
                if check:
                    logger.info(check)
            try:
                self.wake_on_touch(now)
            except Exception:
                self._warn_limited("touch", "StackChan touch wake check failed")
            if self.reaction_tick is not None:
                try:
                    self.reaction_tick()
                except Exception:
                    self._warn_limited("reaction", "StackChan reaction timer failed")
            if self.orientation_tick is not None:
                try:
                    self.orientation_tick()
                except Exception:
                    self._warn_limited("orientation", "StackChan orientation timer failed")
            if self.keep_awake_tick is not None:
                try:
                    self.keep_awake_tick()
                except Exception:
                    self._warn_limited("keep_awake", "StackChan keep-awake call failed")
            try:
                self.rest_step(now)
            except Exception:
                self._warn_limited("rest", "StackChan rest routine failed")
            try:
                self.face_watchdog(now)
            except Exception:
                self._warn_limited("watchdog", "StackChan face watchdog failed")

    def post_scene(self, now: float) -> None:
        """Send Home one camera picture now and then so it can describe the room (never in a turn).

        Idle only, not at night, not when watching is off, not while a post is on its way. A picture
        goes at once when the brightness bucket changed (at most every 10 s), otherwise once a
        minute if the scene differs from the last one posted and every five minutes even if not
        (each picture costs Home a model call); the frame is dropped as soon as it is posted."""
        poster = self.vision_poster
        if (
            poster is None
            or self._vision is None
            or self._vision_posting
            or self._active.is_set()
            or self.night_active()
            or self.watch_level() == "off"
        ):
            return
        from maipai_body.bodies.stackchan.vision_post import differs

        look = self._vision.latest_look(max_age_s=3.0)
        if look is None:
            return
        _jpeg, people, luma, thumb = look
        bucket = self.light_now(luma, flat=luma is None, now=now)
        last_bucket, last_thumb = self._vision_last or (None, None)
        due = poster.scene_due(
            now,
            bucket_changed=self._vision_last is not None and bucket != last_bucket,
            differs=differs(thumb, last_thumb),
        )
        if not due:
            return
        taken = self._vision.latest_look(max_age_s=3.0, take=True)
        if taken is None:
            return
        state = (bucket, thumb)
        self._vision_posting = True
        threading.Thread(
            target=self._post_scene_now,
            args=(taken[0], people, bucket, state),
            name="stackchan-vision-post",
            daemon=True,
        ).start()

    def _post_scene_now(
        self, jpeg: bytes, people: int, bucket: str | None, state: tuple[str | None, Any]
    ) -> None:
        try:
            result = self.vision_poster.post(jpeg, purpose="scene", people=people, light=bucket)
            if result.ok:
                self._vision_last = state
        except Exception:
            self._warn_limited("vision", "StackChan scene post failed")
        finally:
            self._vision_posting = False

    def vision_ask(self, kind: str) -> bool:
        """Post a picture for a question about what it sees; True when Home described it.

        Camera frames pause while a turn is on, so this uses the newest picture from just before
        the person spoke to the robot. Nothing is kept: the picture is posted and dropped."""
        poster = self.vision_poster
        if (
            poster is None
            or self._vision is None
            or self.watch_level() == "off"
            or not poster.ask_possible()
        ):
            return False
        from maipai_body.bodies.stackchan.vision_post import ASK_MAX_AGE_S

        age = self._vision.look_age()
        look = self._vision.latest_look(max_age_s=ASK_MAX_AGE_S, take=True)
        if look is None:
            logger.info(
                "StackChan vision ask (%s): no picture to send (newest is %s)",
                kind,
                "none" if age is None else f"{age:.0f} s old",
            )
            return False
        jpeg, people, luma, _thumb = look
        result = poster.post(
            jpeg,
            purpose="ask",
            people=people,
            light=self.light_now(luma, flat=luma is None),
            timeout=5.0,
        )
        logger.info(
            "StackChan vision ask (%s): picture %.0f s old, %d face(s), %s; %s",
            kind,
            age or 0.0,
            people,
            self.light_now(luma, flat=luma is None),
            result.reason,
        )
        return result.ok

    # -- looking around (owner requests 2026-11-12) -------------------------------------------

    SEARCH_MOTION_FRESH_S = 5.0  # something moved this recently: someone seems to be there
    SEARCH_FACE_GONE_S = 5.0  # and no face was seen for this long: it is out of the picture
    DARK_CONFIRMED_S = DARK_COOLDOWN_S  # a confirmed dark holds this long before it looks again
    CAMERA_BLOCKED_S = 300.0  # detail while looking around a "dark" picture: something is in front

    def search_tick(self, now: float) -> None:
        """Drive a look around, or start one when the picture calls for it (presence loop)."""
        search = self._search
        in_turn = self._active.is_set()
        if self.dance_active():
            if search.active:
                self._end_search(now, "a dance started")
            return
        if not search.active and self._tracker_tick(now, in_turn):
            return
        if search.active:
            # Never mid-reply, asleep or at night; a look for the speaker may run while listening.
            if (
                (in_turn and not (search.reason == "speaker" and self._phase == "listening"))
                or self._rest.stage != "awake"
                or self.night_active()
            ):
                self._end_search(now, "a reply, a rest or the night started")
                return
            if search.reason in FACE_REASONS:
                face = self._last_face
                if face is not None and now - face[2] <= 1.0:
                    self._end_search(
                        now,
                        f"found a face at x {face[0]:.2f}, y {face[1]:.2f} of the picture",
                        found=True,
                    )
                    return
                # The sweep has done its job once a person is in the picture: the tracker takes
                # over from there and looks for the face above the body.
                box = (
                    choose_person(self._vision.people(max_age_s=1.0))
                    if self._vision is not None and self._look_ready()
                    else None
                )
                if box is not None:
                    self._end_search(
                        now,
                        f"found a person at x {box.center_x:.2f}; looking for the face there",
                        found=True,
                    )
                    self._tracker_start(now, box, "found by the sweep")
                    return
            elif search.reason == "dark" and self._vision is not None:
                newest = self._vision.latest_look(max_age_s=1.0)
                if newest is not None and newest[2] is not None:
                    self._search_detail_seen = True
            step = search.due(now)
            if step is not None:
                # A spoken request is bounded (two passes) and never counts toward the cap.
                if not self.head_gate.allow(
                    f"search:{search.reason}",
                    response=True,
                    essential=search.reason in ASKED_REASONS,
                ):
                    self._end_search(now, "the head may not move now")
                    return
                self._search_pose(step.yaw_deg, step.pitch_deg, step.hold_s, step.speed)
                logger.info(
                    "StackChan looking around (%s): yaw %.0f, pitch %.0f up from level",
                    search.reason,
                    step.yaw_deg,
                    step.pitch_deg,
                )
            elif search.finished(now):
                self._end_search(now, "done")
            return
        if self._find_request is not None and not in_turn:
            self._start_asked_search(now)
            return
        if (
            self._vision is None
            or in_turn
            or self._rest.stage != "awake"
            or self.night_active()
            or self.watch_level() == "off"
        ):
            self._ambient_since = None
            return
        from maipai_body.bodies.stackchan.vision_post import light_bucket

        motion_age = self._real_motion_age(now)
        face_age = None if self._last_face is None else now - self._last_face[2]
        look = self._vision.latest_look(max_age_s=2.0)
        flat = look is not None and look[2] is None
        flat_verdict = light_bucket(None, self.lux(), flat=True) if flat else "n/a"
        no_face = face_age is None or face_age > self.SEARCH_FACE_GONE_S
        moved = motion_age is not None and motion_age <= self.SEARCH_MOTION_FRESH_S
        thumb = look[3] if look is not None and len(look) > 3 else None
        if not self.look_toward_speaker:
            self._search_after_turn = False
        if not self.look_for_faces and not self._search_after_turn:
            self._ambient_since = None
            return
        if no_face and self._search_after_turn:
            self._search_after_turn = False
            box = (
                self._vision.last_person(max_age_s=SPEAKER_PERSON_FRESH_S + 30.0)
                if self._look_ready()
                else None
            )
            if box is not None:
                # The body of whoever spoke is known: aim there and look for the face, no sweep.
                self._tracker_start(now, box, "spoke")
            elif search.start("speaker", now):
                logger.info("StackChan looking for the person who spoke: no face was in view")
            return
        # Person-like: something moves with no face in view, or the picture is flat while the
        # sensor says the room is lit (a body or an arm right against the lens), or the Look
        # detector hints at a person below its threshold (measured 2026-11-12: a dark hoodie
        # filling the frame scores 0.05 to 0.17). A picture that merely differs from the learned
        # empty room starts nothing (2026-11-13: it started 16 looks in 50 minutes at the desk;
        # it still lights the ring, `_note_sees`). An AMBIENT look needs all of: the same trigger
        # held AMBIENT_HOLD_S unbroken, no face for AMBIENT_FACE_QUIET_S, no head move for
        # AMBIENT_MOVE_QUIET_S, a picture unlike the one a failed look saw, and the hourly cap
        # (HeadSearch.may_start). A person box or a face hands over to the tracker at once.
        hint = self._person_hint() >= PERSON_HINT_SCORE
        close = flat and flat_verdict is None  # a body right in front of the lens, lit room
        triggered = no_face and (moved or hint or close)
        if not triggered:
            self._ambient_since = None
        elif self._ambient_since is None:
            self._ambient_since = now
        calm = (face_age is None or face_age > AMBIENT_FACE_QUIET_S) and (
            now - self._own_move_at > AMBIENT_MOVE_QUIET_S
        )
        if triggered:
            held = now - (self._ambient_since or now) >= AMBIENT_HOLD_S
            if calm and held and self._still_look_due(now, thumb):
                # Right in front of the lens the face is far above the picture: the steep climb.
                reason = "close" if close else "person"
                if search.start(reason, now):
                    self._ambient_since = None
                    self._search_start_thumb = thumb
                    logger.info(
                        "StackChan looking for a face: %s, no face in the picture",
                        "something is right against the lens in a lit room (climbing)"
                        if close
                        else f"the picture moved {motion_age:.0f} s ago"
                        if moved
                        else f"the detector hints at a person ({self._person_hint():.2f})",
                    )
            return
        self._search_after_turn = False
        # The dark check: nothing in view at all (no face, body or movement within the quiet
        # time), so a dark picture can never send the head looking while someone is there.
        if (
            flat
            and flat_verdict == "dark"
            and not hint
            and not self.dark_confirmed(now)
            and calm
            and now - self._last_person_seen > AMBIENT_FACE_QUIET_S
        ):
            if search.start("dark", now):
                self._search_detail_seen = False
                logger.info(
                    "StackChan checking the dark: no detail in the picture, sensor %s; "
                    "looking around before it concludes",
                    self.lux(),
                )

    # -- find the person, then the face (person_tracker.py) -----------------------------------

    FALSE_PERSON_WINDOW_S = 300.0  # the false-person rate is logged over windows this long

    def _look_ready(self) -> bool:
        ready = getattr(self._vision, "look_ready", None)
        return bool(ready()) if callable(ready) else False

    def _tracker_tick(self, now: float, in_turn: bool) -> bool:
        """Feed the tracker the newest look and perform what it asks. True when it has the head
        now (an attempt is running or just ended), so the older looks around stay out."""
        tracker = self._tracker
        if self._vision is None or not self._look_ready():
            return False
        asleep = self._rest.stage != "awake" or self.night_active()
        if tracker.active and asleep:
            tracker.cancel(now, "a rest or the night started")
            self._log_tracker()
            return False
        if in_turn:
            # The camera pauses while the unit listens and speaks: a follow waits for the reply
            # to end (the turn's own moves tell the tracker where the head went); an aim or a
            # face search is dropped, the person is found again after the reply.
            if tracker.active and not tracker.following:
                tracker.cancel(now, "a reply started")
                self._log_tracker()
            return False
        if asleep or self.watch_level() == "off":
            return False
        look_at = self._vision.look_at()
        if look_at is None or look_at == self._tracker_last_look_at:
            return tracker.active  # no new look since the last tick: nothing new to judge
        self._tracker_last_look_at = look_at
        face = self._last_face
        face_age = None if face is None else now - face[2]
        motion_age = self._real_motion_age(now)
        action = tracker.observe(
            now,
            self._vision.people(max_age_s=2.0),
            face_age=face_age,
            look_at=look_at,
            face_xy=None if face is None else (face[0], face[1]),
            presence_hint=self._person_hint() >= PERSON_HINT_SCORE
            or (motion_age is not None and motion_age <= 1.0),
        )
        return self._tracker_apply(now, action)

    def _tracker_start(self, now: float, box: Any, how: str) -> None:
        """Begin an attempt on a person someone else already found (the speaker turn, the sweep)."""
        if self._tracker.active or not self._look_ready():
            return
        self._tracker_apply(now, self._tracker.start(now, box, how))

    def _tracker_apply(self, now: float, action: Any) -> bool:
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG

        tracker = self._tracker
        self._log_tracker()
        if action.kind == "move":
            following = tracker.following
            source = "person-then-face:follow" if following else "person-then-face"
            if not self.head_gate.allow(source, response=True):
                if following:
                    return True  # the gate's cap: skip this step, the follow goes on
                tracker.cancel(now, "the head may not move now")
                self._log_tracker()
                return False
            move = action.move
            pose = HeadPose(
                yaw=math.radians(move.yaw_deg),
                pitch=math.radians(CENTER_PITCH_DEG + move.pitch_deg),
            )
            self._with_lease(
                lambda: self.robot.head.set(pose=pose, duration_s=move.duration_s, speed=move.speed)
            )
            self._note_own_move()
            self._head_off_center = True
            self.gaze.note(GazeReason.SEARCH)
            logger.info(
                "StackChan person-then-face: %s, yaw %.0f, pitch %.0f up from level",
                move.why,
                move.yaw_deg,
                move.pitch_deg,
            )
            return True
        if action.kind == "return":
            self.head_gate.allow("person-then-face:return", essential=True)
            self._note_own_move()
            self._move_head_slowly(HeadPose(yaw=0.0, pitch=math.radians(CENTER_PITCH_DEG)))
            tracker.note_pose(0.0, 0.0)
            return True
        return tracker.active

    def _log_tracker(self) -> None:
        for line in self._tracker.drain_events():
            logger.info("StackChan person-then-face: %s", line)
            if line.startswith("follow ->"):
                report = self._tracker.follow_report()
                if report:
                    logger.info("StackChan person-then-face: following measured: %s", report)

    def _false_person_tick(self, now: float, person: bool, face: bool) -> None:
        """Count looks with a person box while no face is seen; one line per window without a
        face says the rate (how often the detector sees a person in an empty room)."""
        if self._fp_window_at is None:
            self._fp_window_at = now
        self._fp_looks += 1
        self._fp_person_looks += 1 if person else 0
        self._fp_face_seen = self._fp_face_seen or face
        if now - self._fp_window_at < self.FALSE_PERSON_WINDOW_S:
            return
        if not self._fp_face_seen and self._fp_looks:
            logger.info(
                "StackChan person detector: no face for %.0f min, a person box in %d of %d looks "
                "(%.1f%%)",
                self.FALSE_PERSON_WINDOW_S / 60.0,
                self._fp_person_looks,
                self._fp_looks,
                100.0 * self._fp_person_looks / self._fp_looks,
            )
        self._fp_window_at = now
        self._fp_looks = self._fp_person_looks = 0
        self._fp_face_seen = False

    FIND_REQUEST_FRESH_S = 30.0  # a spoken request not started by then is dropped
    FIND_FACE_FRESH_S = 15.0  # "turn to me" turns at once to a face seen this recently

    def find_person(self, level_only: bool) -> str:
        """The person asked the robot to turn to them ("turn to me", "find me", "I'm down here").

        Answers "turned" when a face was in view a moment ago (the head is on it now), else
        "searching": a look for the face (head_search.py, reason "ask" or "ask_level") starts as
        soon as the reply is over, ignoring the back-off of earlier misses, and ends at a face.
        The head gate lets a response move even at idle level still (owner, 2026-11-12)."""
        if not level_only and self._point_at_face(self.FIND_FACE_FRESH_S):
            logger.info("StackChan turned to the person who asked: a face was in view")
            return "turned"
        self._find_request = ("ask_level" if level_only else "ask", time.monotonic())
        self._react_at_once(level_only)
        return "searching"

    def search_after_set_down(self) -> bool:
        """MOVE-SCENE-05: the unit was handled and is down. Start the 0.2.59 look for a face once
        (reason "person", under its own back-off and its never-mid-reply, asleep or at night
        rules). It only schedules the search: the presence loop drives the head moves, so the
        orientation tick that calls this never waits on them."""
        if self._vision is None or self._active.is_set() or self._rest.stage != "awake":
            return False
        if self.night_active() or self._search.active:
            return False
        started = self._search.start("person", time.monotonic())
        if started:
            logger.info("StackChan looking for a face after being set down")
        return started

    REACT_PAN_DEG = 12.0  # the first, frame-free move of a find-me: a small pan (and a glance up)

    def _react_at_once(self, level_only: bool) -> None:
        """Move now, before any frame can be seen (the camera is paused while the unit listens
        and speaks), so the person sees the head react; the look for the face confirms it."""
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG

        up = 0.0 if level_only else GLANCE_PITCH_DEG
        pose = HeadPose(
            yaw=math.radians(-self.REACT_PAN_DEG), pitch=math.radians(CENTER_PITCH_DEG + up)
        )
        try:
            self._with_lease(
                lambda: self.robot.head.set(pose=pose, duration_s=0.5, speed=TURN_SPEED)
            )
        except Exception:
            self._warn_limited("search", "StackChan first move toward the person failed")
            return
        self._head_off_center = True
        self._tracker.note_pose(-self.REACT_PAN_DEG, up)
        self.hold_pose(4.0)  # the settle after the reply must not undo it before the look starts
        self.gaze.note(GazeReason.COMMAND, "face")

    def face_yaw(self) -> float | None:
        """Yaw in degrees (left negative) toward the face seen a moment ago, or None."""
        face = self._last_face
        if face is None or time.monotonic() - face[2] > self.FIND_FACE_FRESH_S:
            return None
        from maipai_body.bodies.stackchan.vision_bridge import follow_pose
        from maipai_body.hal.seam import FaceTrackTarget

        pose = follow_pose(FaceTrackTarget(detected=True, x=face[0], y=face[1]))
        return math.degrees(pose.yaw)

    def _point_at_face(self, max_age_s: float) -> bool:
        face = self._last_face
        if face is None or time.monotonic() - face[2] > max_age_s:
            return False
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.vision_bridge import follow_pose, follow_pose_degrees
        from maipai_body.hal.seam import FaceTrackTarget

        target = FaceTrackTarget(detected=True, x=face[0], y=face[1])
        pose = follow_pose(target)
        try:
            if not self._with_lease(lambda: self.robot.head.set(pose=pose)):
                return False
        except Exception:
            self._warn_limited("search", "StackChan turn to the person failed")
            return False
        self._head_off_center = True
        self._tracker.note_pose(*follow_pose_degrees(target))
        self.gaze.note(GazeReason.COMMAND, "face")
        return True

    def _start_asked_search(self, now: float) -> None:
        request = self._find_request
        assert request is not None
        reason, asked_at = request
        self._find_request = None
        self._search_after_turn = False  # this look is the one for whoever spoke
        if now - asked_at > self.FIND_REQUEST_FRESH_S:
            return
        if self._rest.stage != "awake" or self.night_active() or self._vision is None:
            self._tell_not_found(reason)
            return
        if self._search.active:
            self._end_search(now, "a spoken request")
        if self._search.start(reason, now):
            logger.info(
                "StackChan looking for the person who asked (%s): the back-off is ignored", reason
            )

    def _tell_not_found(self, reason: str) -> None:
        from maipai_body.bodies.stackchan.head_commands import NOT_FOUND, NOT_FOUND_LEVEL

        line = NOT_FOUND_LEVEL if reason == "ask_level" else NOT_FOUND
        logger.info("StackChan did not find the person who asked (%s): %r", reason, line)
        if self.announce is not None:
            try:
                self.announce(line)
            except Exception:
                self._warn_limited("announce", "StackChan could not say it found nobody")

    def _note_room(self, now: float, newest: Any, motion_age: float | None) -> None:
        """Learn the empty room while nobody seems to be there; measure how the newest picture
        differs from it (a person at the desk differs in most of it, measured 2026-11-12)."""
        from maipai_body.bodies.stackchan.presence_watch import BASELINE_QUIET_S

        if newest is None or newest[2] is None:  # no picture, or no detail: nothing to learn
            return
        thumb = newest[3]
        self._person_share = self._baseline.differs(thumb)
        if self._watching_since is None:
            self._watching_since = now
        # Quiet: nobody seen and nothing really moved for two minutes, and this run has watched
        # that long (the first picture after a restart may well have someone in it; the room
        # kept on disk covers the start). Never while the head is away from center.
        quiet = (
            now - self._last_person_seen >= BASELINE_QUIET_S
            and now - self._watching_since >= BASELINE_QUIET_S
            and (motion_age is None or motion_age >= BASELINE_QUIET_S / 2)
            and not self._search.active
            and not self._head_off_center
        )
        if quiet:
            self._baseline.learn(thumb, now)
            self._baseline.save(now)

    def _note_own_move(self) -> None:
        """The head is being moved by the robot itself: the picture will move for a moment."""
        self._own_move_flag = True

    def head_moved_ago(self) -> float | None:
        """Seconds since the robot last moved its own head (None if it has not)."""
        if self._own_move_flag:
            return 0.0
        if self._own_move_at == float("-inf"):
            return None
        return max(0.0, time.monotonic() - self._own_move_at)

    def _real_motion_age(self, now: float) -> float | None:
        """Seconds since something other than the robot's own head move stirred the picture."""
        from maipai_body.bodies.stackchan.presence_watch import OWN_MOVE_BLIND_S

        if self._vision is None:
            return None
        age = getattr(self._vision, "motion_age", lambda: None)()
        if age is None:
            return None
        moved_at = now - age
        if self._own_move_at - 0.5 <= moved_at <= self._own_move_at + OWN_MOVE_BLIND_S:
            return None
        return age

    def _still_look_due(self, now: float, thumb: Any) -> bool:
        """May a look started only by the picture differing from the room run now? Not inside
        its back-off, and not while the picture is the one the last failed look already saw."""
        from maipai_body.bodies.stackchan.presence_watch import (
            STILL_BACKOFF_S,
            STILL_CHANGE_SHARE,
            SceneBaseline,
        )

        if self._still_failures == 0:
            return True
        wait = STILL_BACKOFF_S[min(self._still_failures, len(STILL_BACKOFF_S)) - 1]
        if now - self._still_failed_at < wait:
            return False
        return SceneBaseline.changed(thumb, self._still_thumb) >= STILL_CHANGE_SHARE

    # ---- look around on the wake word (wake_look.py) -------------------------------------------------------------------

    def _wake_look_local_block(self, was_resting: bool = False) -> str:
        """Why the head must not look around now, from what the host itself knows ("" when free). No camera frame is read."""
        if was_resting or self._rest.stage != "awake":
            return "asleep or drowsy"
        if self.night_active():
            return "night or quiet hours"
        privacy = getattr(self, "privacy", None)
        if (
            bool(getattr(privacy, "muted", False))
            or bool(getattr(privacy, "quiet", False))
            or self.speech_muted()
        ):
            return "muted or full quiet"
        orientation = self.orientation
        if self.pose_held() or (orientation is not None and orientation.sensors_untrusted()):
            return "carried, tilted or held"
        if self.dance_active():
            return "a dance is running"
        holder = self.robot.lease_holder
        if holder is not None and holder != self._holder:
            return "another source holds the head"
        return ""

    def _wake_look_allowed(self, was_resting: bool = False) -> bool:
        """Every gate for the look on the wake word, then the once-per-15-s allowance (taken here). The caller holds the listening
        state's own head-gate allowance; the pan asks the gate again for each move."""
        if not self.look_on_wake:
            return False
        reason = self._wake_look_local_block(was_resting)
        if not reason:
            try:
                reason = self.wake_unit_busy()
            except Exception:
                reason = ""
        if not reason and self.wake_seeker_owns():
            reason = "the unit's own seeker owns seeking"
        now = time.monotonic()
        if not reason and now - self._last_wake_look < wake_look_mod.COOLDOWN_S:
            reason = "one look in the last 15 s"
        if reason:
            logger.info("StackChan wake look skipped: %s", reason)
            return False
        self._last_wake_look = now
        return True

    def _start_wake_look(self) -> None:
        """After the glance up: the pan runs in its own thread so the turn is never held up."""
        self.stop_wake_look()
        stop = self._wake_stop = threading.Event()
        self.wake_looks += 1
        self._wake_thread = threading.Thread(
            target=self._wake_look_run, args=(stop,), name="stackchan-wake-look", daemon=True
        )
        self._wake_thread.start()

    def stop_wake_look(self, why: str = "") -> None:
        """End the pan at once (a touch, the reply, the turn's end); the head stays where it is and the settle brings it back."""
        thread = self._wake_thread
        if not self._wake_stop.is_set() and thread is not None and thread.is_alive():
            logger.info("StackChan wake look stopped%s", f": {why}" if why else "")
        self._wake_stop.set()

    def _wake_look_run(self, stop: threading.Event) -> None:
        scale = self.wake_look_scale
        if stop.wait((wake_look_mod.GLANCE_S + wake_look_mod.PAUSE_AFTER_GLANCE_S) * scale):
            return
        for yaw, move_s, pause_s in wake_look_mod.STEPS:
            if stop.is_set() or not self._active.is_set() or self._phase != "listening":
                return
            reason = self._wake_look_local_block()
            if reason:
                logger.info("StackChan wake look stopped: %s", reason)
                return
            if not self.head_gate.allow("turn:wake-look", response=True):
                return
            pose = HeadPose(
                yaw=math.radians(yaw),
                pitch=math.radians(CENTER_PITCH_DEG_WAKE + wake_look_mod.PITCH_DEG),
            )
            moved: list[bool] = []

            def move(pose: HeadPose = pose, move_s: float = move_s) -> None:
                if stop.is_set():
                    return
                self.robot.head.set(pose=pose, duration_s=move_s, speed=wake_look_mod.SPEED)
                moved.append(True)

            try:
                held = self._with_lease(move)
            except Exception:
                self._warn_limited("search", "StackChan wake look move failed")
                return
            if not held or not moved:
                return  # another source took the head, or the pan was stopped: nothing more
            self._note_own_move()
            self._tracker.note_pose(yaw, wake_look_mod.PITCH_DEG)
            if stop.wait((move_s + pause_s) * scale):
                return

    def _glance_up_for_speaker(self, pitch_deg: float = SPEAKER_PITCH_DEG) -> bool:
        """Someone spoke and no face is in view: a brisk, smooth glance up now (the camera is
        paused while the unit listens, so the face is looked for after the reply). The caller
        holds the listening state's own head-gate allowance; this is that one move."""
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG

        pose = HeadPose(yaw=0.0, pitch=math.radians(CENTER_PITCH_DEG + pitch_deg))
        try:
            self.robot.head.set(pose=pose, duration_s=0.5, speed=TURN_SPEED)
        except Exception:
            self._warn_limited("search", "StackChan glance toward the speaker failed")
            return False
        self._head_off_center = True
        self._note_own_move()
        self._search_after_turn = True
        self._tracker.note_pose(0.0, pitch_deg)
        self.gaze.note(GazeReason.SEARCH)
        logger.info(
            "StackChan glanced up toward the speaker: pitch %.0f up from level", pitch_deg
        )
        return True

    def _search_pose(
        self, yaw_deg: float, pitch_deg: float, hold_s: float = STEP_S, speed: int = MOVE_SPEED
    ) -> None:
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG

        pose = HeadPose(yaw=math.radians(yaw_deg), pitch=math.radians(CENTER_PITCH_DEG + pitch_deg))
        self._move_head_slowly(pose, hold_s, speed)
        self._note_own_move()
        self._head_off_center = True
        self._tracker.note_pose(yaw_deg, pitch_deg)
        self.gaze.note(GazeReason.SEARCH)

    def _move_head_slowly(
        self, pose: HeadPose, hold_s: float = STEP_S, speed: int = MOVE_SPEED
    ) -> None:
        """One eased move at the servo's slowest setting; inside a turn the turn holds the lease."""

        def move() -> None:
            self.robot.head.set(pose=pose, duration_s=hold_s * 0.6, speed=speed)

        if self._active.is_set():
            try:
                move()
            except NotPermitted:
                # The turn's own lease was already released: take one for this move, or skip it.
                try:
                    self._with_lease(move)
                except Exception:
                    self._warn_limited("search", "StackChan head move skipped: no lease")
            except Exception:
                self._warn_limited("search", "StackChan head move failed")
        else:
            self._with_lease(move)

    def _end_search(self, now: float, why: str, *, found: bool = False) -> None:
        from maipai_body.bodies.stackchan.presence_watch import STILL_BACKOFF_S

        reason = self._search.stop(now, found=found)
        if reason == "dark":
            if self._search_detail_seen:
                self._camera_blocked_until = now + self.CAMERA_BLOCKED_S
                logger.info(
                    "StackChan dark check: not dark, the camera saw detail while looking around "
                    "(something is in front of it); light unknown for %.0f s",
                    self.CAMERA_BLOCKED_S,
                )
            elif why == "done":
                self._dark_confirmed_at = now
                logger.info(
                    "StackChan dark check: dark confirmed, no detail in any direction, sensor %s",
                    self.lux(),
                )
            else:
                logger.info("StackChan dark check stopped: %s", why)
        elif reason in ASKED_REASONS:
            logger.info("StackChan stopped looking for the person who asked: %s", why)
            if found:
                self._point_at_face(2.0)  # still level or not, the head ends on the face
                return
            if why == "done":
                self._tell_not_found(reason)
        elif reason in ("person", "speaker", "close"):
            wait = self._search.wait_s("person")
            if found:
                self._still_failures = 0
                self._still_thumb = None
            elif why == "done" and reason != "speaker":
                # The picture that started the look is the one the next must differ from (the
                # picture at the end is from the swept pose, never the room at rest).
                self._still_failures += 1
                self._still_failed_at = now
                self._still_thumb = self._search_start_thumb
                wait = max(
                    wait, STILL_BACKOFF_S[min(self._still_failures, len(STILL_BACKOFF_S)) - 1]
                )
            logger.info(
                "StackChan stopped looking for a face: %s%s",
                why,
                "" if found else f"; the next look waits {wait:.0f} s at least",
            )
        if found:
            return  # following takes over from where the face is
        # Back to the resting pose: essential, so it never counts against the gate's cap.
        self.head_gate.allow("search:return", essential=True)
        self._note_own_move()
        from maipai_body.bodies.stackchan.profile import CENTER_PITCH_DEG

        self._move_head_slowly(HeadPose(yaw=0.0, pitch=math.radians(CENTER_PITCH_DEG)))
        self._tracker.note_pose(0.0, 0.0)

    def dark_confirmed(self, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        at = self._dark_confirmed_at
        return at is not None and current - at <= self.DARK_CONFIRMED_S

    def light_now(self, luma: float | None, *, flat: bool, now: float | None = None) -> str | None:
        """The light bucket the robot stands behind: a "dark" from a picture with no detail waits
        for the look around (`search_tick`) unless the head may not move; detail seen during that
        look means something is in front of the camera and the light is unknown for a while."""
        from maipai_body.bodies.stackchan.vision_post import light_bucket

        current = time.monotonic() if now is None else now
        bucket = light_bucket(luma, self.lux(), flat=flat)
        if not flat or bucket != "dark":
            return bucket
        if current < self._camera_blocked_until:
            return None
        if self.dark_confirmed(current):
            return "dark"
        cannot_look = self._rest.stage != "awake" or self.night_active() or self._active.is_set()
        return "dark" if cannot_look else None

    def light_for_sight(self, now: float | None = None) -> str | None:
        """The bucket for a spoken light question, from the newest picture (up to a minute old)."""
        if self._vision is None:
            return self.light_now(None, flat=False, now=now)
        look = self._vision.latest_look(max_age_s=60.0)
        if look is None:
            return self.light_now(None, flat=False, now=now)
        return self.light_now(look[2], flat=look[2] is None, now=now)

    def watch_for_faces(self, now: float) -> bool:
        """Look for a face in the unit's latest camera frame about twice a second.

        Local only: the frame is decoded and searched in memory and only "a face was there" is
        kept. Off while a turn is on, at night, and when the camera level is off. The head follows
        a face only when the head gate allows it; the room counts as occupied either way, which
        keeps the rest policy awake and, after a long empty spell, gives one greeting."""
        if (
            self._vision is None
            or self._active.is_set()
            or self.night_active()
            or self.watch_level() == "off"
            or now - self._last_look < LOOK_INTERVAL_S
        ):
            return False
        self._last_look = now
        if self._own_move_flag:
            self._own_move_flag = False
            self._own_move_at = now
        started = time.monotonic()
        self._followed = False
        target = self._vision.track_stream_frame(deadline_s=0.4, may_move=self._may_follow)
        if self._followed and target.detected:
            self._note_own_move()  # the head followed the face: the picture moved with it
        latest = getattr(self._vision, "latest_look", None)
        newest = latest(max_age_s=2.0) if latest is not None else None
        people = getattr(self._vision, "people", None)
        person_now = bool(people(max_age_s=1.0)) if callable(people) else False
        self._camera_stats.looked(
            time.monotonic() - started,
            target.detected,
            luma=None if newest is None else newest[2],
            flat=newest is not None and newest[2] is None,
            lux=self.lux(),
            motion=getattr(self._vision, "last_motion", None),
            person=person_now,
            detector_ms=getattr(self._vision, "last_look_ms", None),
            person_best=getattr(self._vision, "last_best_person", None),
        )
        if self._look_ready():
            self._false_person_tick(now, person_now, target.detected)
        self._note_sees(now, target.detected, person_now)
        from maipai_body.bodies.stackchan.gaze import GazeReason

        if not target.detected:
            if person_now:
                # A body with no face (an arm, a torso at the desk) is a person: it keeps the rest
                # policy awake and stops the empty room from being learned over them.
                self._last_person_seen = now
                self._still_failures = 0
                self._still_thumb = None
            self._missed_looks += 1
            if (
                self._missed_looks == LOST_AFTER_LOOKS
                and self.gaze.reason is GazeReason.TRACK
                and self.gaze.current() is GazeReason.TRACK
            ):
                self.gaze.note(GazeReason.SEARCH)  # a face it was following is gone
            # Movement without a face (an arm at the desk) is still a person: it keeps the rest
            # policy awake, so the robot can look for the face instead of dozing off (2026-11-12).
            # The robot's own head moves are not (they kept it awake all evening on 2026-11-12),
            # and a picture that merely differs from the learned room never is.
            motion_age = self._real_motion_age(now)
            if motion_age is not None and motion_age <= 1.0:
                self._last_person_seen = now
            self._note_room(now, newest, motion_age)
            return False
        self._missed_looks = 0
        self._last_person_seen = now
        self._still_failures = 0
        self._still_thumb = None
        if target.x is not None and target.y is not None:
            self._last_face = (target.x, target.y, now)
        if self.on_face_found is not None:
            self.on_face_found()
        if self._followed:
            self.gaze.note(GazeReason.TRACK)
            last_pose = getattr(self._vision, "last_pose_deg", None)
            if last_pose is not None:
                self._tracker.note_pose(*last_pose)
        if self._greeting.seen(now):
            self.greet()
        return True

    def _person_hint(self) -> float:
        """The detector's best person score on the newest look (below the box threshold)."""
        return float(getattr(self._vision, "last_best_person", 0.0) or 0.0)

    def _note_sees(self, now: float, face: bool, person: bool) -> None:
        """What the camera sees now, for the ring: a face, a person box, a possible person (a
        weak detector hint, movement, or a picture unlike the empty room), or nothing."""
        if face:
            state: str | None = "face"
        elif person:
            state = "person"
        else:
            motion_age = self._real_motion_age(now)
            from maipai_body.bodies.stackchan.presence_watch import PERSON_SHARE

            maybe = (
                self._person_hint() >= PERSON_HINT_SCORE
                or (motion_age is not None and motion_age <= 1.0)
                or self._person_share >= PERSON_SHARE
            )
            state = "maybe" if maybe else None
        if state is not None:
            self._sees_at = now
        elif now - self._sees_at < SEES_HOLD_S:
            return  # a miss between two looks: the glow holds, no flicker
        if state == self._sees:
            return
        self._sees = state
        if self.on_sees is not None:
            try:
                self.on_sees(state)
            except Exception:
                self._warn_limited("sees", "StackChan vision indicator update failed")

    def face_age(self) -> float | None:
        """Seconds since a face was last seen, or None if none has been."""
        return None if self._last_face is None else time.monotonic() - self._last_face[2]

    def _turn_toward_face(self) -> bool:
        """On listen start, turn toward the face seen a moment ago and hold the turn through the
        reply. Nothing happens when no face was seen in the last few seconds (no hunting)."""
        face = self._last_face
        if face is None or time.monotonic() - face[2] > TURN_FACE_FRESH_S:
            return self._turn_toward_person()
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.vision_bridge import follow_pose, follow_pose_degrees
        from maipai_body.hal.seam import FaceTrackTarget

        target = FaceTrackTarget(detected=True, x=face[0], y=face[1])
        pose = follow_pose(target)
        self.robot.head.set(pose=pose)  # the lease is held by the turn state that called this
        self._head_off_center = True
        self._note_own_move()
        self._tracker.note_pose(*follow_pose_degrees(target))
        self.gaze.note(GazeReason.TRACK)
        logger.info("StackChan turned toward the speaker")
        return True

    def _turn_toward_person(self) -> bool:
        """No fresh face at listen start, but the Look detector saw a body a moment ago: one brisk
        turn toward it (the box center, tilted toward its top) instead of the blind glance up; the
        tracker then looks for the face there after the reply."""
        if self._vision is None or not self._look_ready():
            return False
        box = self._vision.last_person(max_age_s=SPEAKER_PERSON_FRESH_S)
        if box is None:
            return False
        from maipai_body.bodies.stackchan.gaze import GazeReason
        from maipai_body.bodies.stackchan.vision_bridge import follow_pose, follow_pose_degrees
        from maipai_body.hal.seam import FaceTrackTarget

        target = FaceTrackTarget(detected=True, x=box.center_x, y=box.top)
        try:
            self.robot.head.set(pose=follow_pose(target), duration_s=0.5, speed=TURN_SPEED)
        except Exception:
            self._warn_limited("search", "StackChan turn toward the person failed")
            return False
        self._head_off_center = True
        self._note_own_move()
        self._tracker.note_pose(*follow_pose_degrees(target))
        self._search_after_turn = True  # look for the face there once the reply is over
        self.gaze.note(GazeReason.SEARCH)
        logger.info(
            "StackChan turned toward the person who spoke: a body at x %.2f, no face in view",
            box.center_x,
        )
        return True

    def _may_follow(self) -> bool:
        if self._look_ready():
            # The person tracker follows faces and bodies alike (relative moves, a dead zone):
            # the bridge's own absolute follow stays for a robot without the Look model.
            self._followed = False
            return False
        self._followed = (not self.idle_still()) and self.head_gate.allow("ambient:track")
        return self._followed

    def greet(self) -> None:
        """A gesture greeting: a happy face for a moment, and a nod when the head may move.

        Spoken greetings belong to Home's person and age rules; the robot only gestures."""
        if self.greeting_mode == "off" or self._rest.stage != "awake":
            return
        logger.info("StackChan greeting: someone came into view after a long while")
        from maipai_body.bodies.stackchan.meeting_faces import MeetingFaces

        MeetingFaces(lambda face: self.show_face(face, while_listening=True)).on_meeting(
            "returned_after_long"
        )
        if not self.idle_still():
            self.render_primitive("nod")

    def reaction_blocked(self) -> bool:
        """True while the robot is thinking or speaking: a touch reaction is not shown then."""
        return self._active.is_set() and self._phase != "listening"

    def _motion_hold_reason(self) -> str:
        """Why no move may be asked now (held or carried, or the battery hold), else "". The unit refuses such moves itself."""
        limit = self.motion_limit
        if limit is None:
            return ""
        try:
            state = limit.state()
        except Exception:
            return ""
        return state.why.rstrip(".") if state.hold else ""

    def show_face(self, expression: str, *, while_listening: bool = False) -> None:
        """Show a face for a moment; the face watchdog puts the idle face back.

        Not during a turn, except a reaction face while the robot is only listening."""
        if self._active.is_set() and not (while_listening and self._phase == "listening"):
            return
        if self._rest.stage != "awake":
            return
        if bool(getattr(getattr(self, "privacy", None), "muted", False)) or self.speech_muted():
            return
        device = self.robot._driver("head").expression_device
        if device is None:
            return
        from maipai_body.bodies.stackchan.avatar.server import control_avatar
        from maipai_body.bodies.stackchan.face_vocabulary import resolve_face

        device.send_avatar_frame(
            control_avatar(resolve_face(expression, self._unit_firmware_version()))
        )
        self._face_quiet_since = None  # the watchdog counts its quiet time from now

    def wake_on_touch(self, now: float) -> bool:
        """Read the unit's touch, swipe and shake events; wake a sleeper, tell the reactions.

        The unit is asked every ``EVENT_POLL_S`` while awake and every ``TOUCH_POLL_S`` while
        drowsy or asleep, during a turn too (a pat while it only listens must react; the reactions
        decide what to show). The first look after a pause only empties the unit's queue (old events
        are not a reason to react). True when it woke the robot."""
        if self.event_poll is None:
            self._event_queue_drained = False
            return False
        asleep = self._rest.stage != "awake"
        if now - self._last_event_poll < (TOUCH_POLL_S if asleep else EVENT_POLL_S):
            return False
        paused = now - self._last_event_poll > 30.0
        self._last_event_poll = now

        def tick_idle_faces() -> None:
            if asleep or self.idle_faces is None:
                return
            try:
                self.idle_faces.tick(now)
            except Exception:
                self._warn_limited("idle-faces", "StackChan idle face tick failed")

        events = self.event_poll()
        # A slider the person moved on the unit is a level to keep, never old news to drain.
        for event in events:
            if getattr(event, "kind", None) == "level_changed" and self.on_levels_changed:
                try:
                    self.on_levels_changed(
                        getattr(event, "volume", None), getattr(event, "brightness", None)
                    )
                except Exception:
                    self._warn_limited("levels", "StackChan level sync failed")
        events = [e for e in events if getattr(e, "kind", None) != "level_changed"]
        timer_rang = False
        for event in events:
            if str(getattr(event, "kind", "")).startswith("timer_"):
                timer_rang = timer_rang or event.kind == "timer_fired"
                if self.timers is not None:
                    try:
                        self.timers.on_event(event.kind, getattr(event, "extra", None))
                    except Exception:
                        self._warn_limited("timers", "StackChan timer event failed")
        for event in events:
            if getattr(event, "kind", None) in ("music_clip_ready", "music_clip_cancelled"):
                if self.music_clip is not None:
                    try:
                        self.music_clip(
                            event.kind,
                            getattr(event, "extra", None) or {},
                            now,
                        )
                    except Exception:
                        self._warn_limited("music", "StackChan music clip handling failed")
                continue
            if getattr(event, "kind", None) == "music_feat":
                # About one a second while the room is loud (firmware patch 100): the music dance
                # decides on them. The first look after a pause only drains old ones.
                if self.music_feat is not None and not (paused or not self._event_queue_drained):
                    try:
                        self.music_feat(getattr(event, "extra", None) or {}, now)
                    except Exception:
                        self._warn_limited("music", "StackChan music features handling failed")
                continue
            if getattr(event, "kind", None) in DIAGNOSTIC_KINDS:
                extra = getattr(event, "extra", None) or {}
                if self.unit_facts is not None:
                    self.unit_facts.observe(event.kind, extra)
                if event.kind in ("wifi_use_ok", "wifi_use_revert"):
                    wifi_list = getattr(self, "wifi_list", None)
                    if wifi_list is not None:
                        wifi_list.note_use_event(event.kind)
                if self.on_unit_event is not None:
                    try:
                        self.on_unit_event(event.kind, extra)
                    except Exception:
                        self._warn_limited("unit-event", "StackChan self-heal event hook failed")
                if event.kind == "stop_word" and "cmd" in extra:
                    verdict = "accepted" if extra.get("accepted") else "rejected"
                    logger.info(
                        "unit stop word: heard %r, score %s, second %s (%s)",
                        extra.get("cmd"),
                        extra.get("score"),
                        extra.get("second"),
                        verdict,
                    )
                    continue
                if event.kind == "orientation" and self.orientation is not None:
                    try:
                        self.orientation.on_event(extra)
                    except Exception:
                        self._warn_limited("orientation", "StackChan orientation reaction failed")
                if event.kind == "ws_away_notice":
                    note = getattr(self, "note_away", None)
                    if note is not None:
                        note(self.primary_unit() or "", extra)
                if event.kind == "fw":
                    try:
                        self.on_firmware_version(extra.get("version"))
                    except Exception:
                        self._warn_limited("firmware", "StackChan firmware version handling failed")
                if event.kind == "sound_played":
                    from maipai_body.bodies.stackchan.activity import log_activity

                    log_activity(
                        "unit played a sound",
                        f"name={extra.get('name')} src={extra.get('src')}",
                    )
                detail = " ".join(f"{k}={v}" for k, v in extra.items())
                label = {
                    "stop_word": "unit stop word",
                    "fw": "unit firmware",
                    "camera": "unit camera",
                    "barge_stats": "unit barge",
                    "orientation": "unit orientation",
                    "playback": "unit playback",
                    "heap_stats": "unit memory",
                    "stack_stats": "unit memory",
                    "boot": "unit boot",
                    "tap": "unit tap",
                    "wake": "unit wake",
                    "wake_stats": "unit wake",
                    "state_guard": "unit wake",
                    "wifi": "unit wifi",
                    "offline_tap": "unit offline",
                    "coredump": "unit crash",
                    "boot_core": "unit crash",
                    "firmware_update_validated": "unit update",
                    "firmware_update_rolled_back": "unit update",
                    "heal": "unit heal",
                    "wake_selftest": "unit wake",
                    "sound_played": "unit sound",
                    "power_poll": "unit power",
                    "timer_fired": "unit timer",
                    "timer_ended": "unit timer",
                    "timer_missed": "unit timer",
                    "music_stats": "unit music",
                    "privacy": "unit privacy",
                    "privacy_refused": "unit privacy",
                    "ws_away_notice": "unit away",
                }.get(event.kind, "unit touch")
                logger.info("%s: %s %s", label, event.kind, detail)
        events = [e for e in events if getattr(e, "kind", None) not in DIAGNOSTIC_KINDS]
        events = self._head_filter.accept(now, events)
        if self._search.active and any(getattr(e, "kind", None) in HEAD_KINDS for e in events):
            self._end_search(now, "a touch")
        if any(getattr(e, "kind", None) in HEAD_KINDS for e in events):
            self.stop_wake_look("a touch")
        for event in events:
            if getattr(event, "kind", None) in _LOGGED_UNIT_EVENTS:
                extra = getattr(event, "extra", None) or {}
                detail = " ".join(f"{k}={v}" for k, v in extra.items())
                logger.info(
                    "unit touch: %s %s%s",
                    event.kind,
                    detail,
                    " (first look after a pause: not acted on)"
                    if paused or not self._event_queue_drained
                    else "",
                )
        if timer_rang and asleep and now - self._last_touch_wake >= TOUCH_WAKE_COOLDOWN_S:
            # A timer or alarm ringing is not old news and not a touch: the unit shows it, and the
            # rest policy must not put the face back to sleep over it.
            self._last_touch_wake = now
            self._last_person_seen = now
            logger.info("StackChan woke up for a timer")
            return True
        if not asleep and self.idle_faces is not None:
            tick_idle_faces()
        if paused or not self._event_queue_drained:
            self._event_queue_drained = True
            return False
        if not events:
            return False
        if self.dance_events is not None:
            try:
                self.dance_events(events, now)  # a touch ends a dance
            except Exception:
                self._warn_limited("dance", "StackChan dance touch handling failed")
        kinds = [_reaction_kind(event) for event in events]
        if self.reaction is not None:
            try:
                self.reaction(kinds)
            except Exception:
                self._warn_limited("reaction", "StackChan touch reaction failed")
        if not asleep or now - self._last_touch_wake < TOUCH_WAKE_COOLDOWN_S:
            return False
        self._last_touch_wake = now
        self._last_person_seen = now  # the rest policy treats a person as activity and wakes
        logger.info("StackChan woke up on touch (%s)", ", ".join(sorted(set(kinds))))
        return True

    def extra_unit_tick(self, now: float) -> None:
        """One pass for a unit after the first (docs/plan/per-unit-behavior.md): touch, reactions, orientation, keep-awake, rest and the face
        watchdog. No camera work: face search and tracking read one camera and stay on the first unit."""
        for key, step in (
            ("touch", lambda: self.wake_on_touch(now)),
            ("reaction", lambda: self.reaction_tick and self.reaction_tick()),
            ("orientation", lambda: self.orientation_tick and self.orientation_tick()),
            ("keep_awake", lambda: self.keep_awake_tick and self.keep_awake_tick()),
            ("music", lambda: getattr(self, "music_tick", None) and self.music_tick()),
            ("rest", lambda: self.rest_step(now)),
            ("watchdog", lambda: self.face_watchdog(now)),
        ):
            try:
                step()
            except Exception:
                self._warn_limited(key, f"StackChan {key} step of an extra unit failed")

    def _warn_limited(self, key: str, message: str) -> None:
        """One warning with its traceback per minute per cause: a loop that fails five times a
        second while the unit is away logged 378 tracebacks in nine minutes."""
        now = time.monotonic()
        if now - self._warned.get(key, float("-inf")) >= 60.0:
            self._warned[key] = now
            logger.warning(message, exc_info=True)

    def face_watchdog(self, now: float) -> bool:
        """Never leave the face stuck (eyes shut, mouth open) after a lost frame or an odd exit.

        With no turn active for ``FACE_QUIET_S`` and the rest policy awake, resend the idle face
        once if the last frame was not idle (or never arrived), then every ``FACE_REFRESH_S``.
        """
        if self._active.is_set() or self.pose_held() or self.dance_active():
            self._face_quiet_since = None
            return False
        if self._face_quiet_since is None:
            self._face_quiet_since = now
            return False
        if self._rest.stage != "awake" or self.night_active():
            return False
        device = self.robot._driver("head").expression_device
        if device is None:
            return False
        stale = (
            device.last_expression != "neutral"
            or not device.last_expression_ok
            or now - self._face_refreshed_at >= FACE_REFRESH_S
        )
        if not stale or now - self._face_quiet_since < FACE_QUIET_S:
            return False
        from maipai_body.bodies.stackchan.avatar.server import control_avatar
        from maipai_body.bodies.stackchan.face_vocabulary import resolve_face

        device.send_avatar_frame(
            control_avatar(resolve_face("neutral", self._unit_firmware_version()))
        )
        self._face_refreshed_at = now
        return True

    def unit_connected(self) -> None:
        """The unit (re)connected: it boots awake, so the rest clock must not count its time off."""
        self._rest.reset(time.monotonic())

    def rest_step(self, now: float) -> str:
        """One pass of the rest policy: drop the head and sleepy face after a long quiet spell."""
        person = now - self._last_person_seen < 30.0
        before = self._rest.stage
        music_playing = False
        try:
            music_playing = bool(getattr(self, "music_heard_recently", lambda: False)())
        except Exception:
            music_playing = False
        output = self._rest.update(
            now, person_present=person, turn_active=self._active.is_set() or music_playing
        )
        if output.stage != before:
            self._note_own_move()  # the rest pose moves the head: that motion is the robot's own
        self._with_lease(
            lambda: self._rest_renderer.render(
                output,
                self.robot._driver("head"),
                self._rest_profile,
                pose_held=self.pose_held,
            )
        )
        return output.stage

    def stop_presence(self) -> None:
        if self._presence_stop is not None:
            self._presence_stop.set()
        if self._presence_thread is not None:
            self._presence_thread.join(timeout=2.0)
            self._presence_thread = None
        try:
            self.robot.camera.stream(enabled=False)
        except Exception:
            logger.debug("StackChan camera stream already stopped", exc_info=True)

    def close(self) -> None:
        self._closed.set()
        self.stop_wake_look()
        self.stop_presence()
        close = getattr(self._vision, "close", None)
        if callable(close):
            close()
        self._expression.close()
        holder = self.robot.lease_holder
        if holder is not None:
            self.robot.lease.release(holder=holder)


def _start_stackchan_night(
    voice,
    behavior: StackChanBehavior,
    link: LinkLifecycle | None,
    stop_event: threading.Event,
    hub_handlers: dict[str, Callable[[dict], Any]] | None = None,
) -> NightController:
    """BOT-FACE-NIGHT-01: the face color and night rule on a StackChan.

    The hub's `settings_changed` reaches it through the same `CommandChannel` the
    Reachy body uses, started here because this body has no conversation loop."""
    from maipai_body.bodies.stackchan.owner_levels import OwnerLevels
    from maipai_body.link.channel import CommandChannel
    from maipai_body.presence.sleep_auto import QuietHours, luma_reader

    quiet = QuietHours()
    voice.quiet_hours = quiet  # the pantry refills inside the owner's quiet hours when they are set
    watch = ["identify"]  # the default until the hub says otherwise

    class _StreamCamera:
        def get_frame(self):
            data = voice.robot.robot._driver("camera").stream_frame(0.4)
            if not data:
                return None
            from maipai_body.bodies.stackchan.vision_bridge import _decode_jpeg

            return _decode_jpeg(data)

    def leds(on: bool) -> None:
        """The night controller tells the one ring writer (the light service) the room is dark;
        it never writes a pixel itself. The service may not exist yet at the first call, so the
        state is kept on the behavior and handed over when the service starts."""
        behavior.ring_dark_room = not on
        setter = getattr(behavior, "set_ring_dark_room", None)
        if setter is not None:
            setter(not on)

    levels = OwnerLevels(_data_dir() / "owner_levels.json")
    levels.load()

    night = NightController(
        voice.robot.client,
        clock=time.monotonic,
        quiet_hours=quiet.active,
        watch_level=lambda: watch[0],
        camera_luma=luma_reader(_StreamCamera(), level=lambda: watch[0]),
        leds=leds,
        levels=levels,
        connected=lambda: bool(voice._sessions),
    )
    voice.session_listeners.append(lambda _device_id: night.on_connect())
    voice.session_listeners.append(lambda _device_id: behavior.unit_connected())
    behavior.night_active = lambda: night.night
    behavior.watch_level = lambda: watch[0]
    voice.robot.robot._driver("camera").watch_allowed = lambda: (
        watch[0] != "off"
        and not bool(getattr(getattr(behavior, "privacy", None), "vision_off", False))
    )

    def apply_settings(payload: dict) -> None:
        values = payload.get("values")
        if not isinstance(values, dict):
            return
        quiet.apply(values)
        level = values.get("robot.camera.watch_level")
        if level in ("off", "presence", "identify"):
            was_off = watch[0] == "off"
            watch[0] = level
            try:
                if level == "off":
                    behavior.robot.camera.stream(enabled=False)
                elif was_off:
                    behavior.robot.camera.stream(enabled=True, silent=True)
            except Exception:
                logger.warning("StackChan camera watch level change failed", exc_info=True)
        greeting = values.get("robot.greetings.mode")
        if greeting in ("off", "gesture", "spoken"):
            behavior.greeting_mode = greeting
        idle = values.get("robot.idle.level")
        if idle in ("still", "calm", "lively"):
            # "calm" is Home's registry default, so it cannot be told from a deliberate choice;
            # a robot that wanders on its own by default wore servos (2026-10-21), so calm counts
            # as still until the default itself changes. "lively" is always a choice.
            behavior.idle_level = _effective_idle_level(idle)
            behavior.on_idle_level()
        if "robot.vision" in values and behavior.vision_poster is not None:
            behavior.vision_poster.set_mode(values.get("robot.vision"))
        behavior.dance_settings.apply(values)
        night.apply_settings(values)
        for listener in behavior.settings_listeners:
            try:
                listener(values)
            except Exception:
                logger.warning("a settings listener failed", exc_info=True)

    if link is not None and _no_hub_configured():
        logger.info("no hub URL is set: the hub command channel is off")
    elif link is not None:
        channel = CommandChannel(
            "",
            "",
            credentials=_command_credentials(link),
            settings_handler=apply_settings,
            handlers={
                "dance": lambda payload: behavior.dance_command(payload),
                "child_present": lambda payload: _note_child(voice, payload),
                **(hub_handlers or {}),
                "music_test": lambda payload: behavior.music_command(payload),
                "listen_song": lambda payload: behavior.listen_song_command(payload),
                "wifi_add": lambda payload: behavior.wifi_add_command(payload),
                "wifi_forget": lambda payload: behavior.wifi_forget_command(payload),
                "wifi_use": lambda payload: behavior.wifi_use_command(payload),
                "prefer_tailnet": lambda payload: behavior.prefer_tailnet_command(payload),
                "song_title": lambda payload: behavior.song_title_command(payload),
            },
            on_drop=link.channel_lost,
        )
        threading.Thread(
            target=channel.run, args=(stop_event,), name="stackchan-command-channel", daemon=True
        ).start()
    threading.Thread(
        target=night.run, args=(stop_event,), name="stackchan-night", daemon=True
    ).start()
    return night


def _unit_not_upright(behavior: Any) -> bool:
    limit = getattr(behavior, "motion_limit", None)
    try:
        return bool(limit is not None and limit.state().not_upright)
    except Exception:
        return False


def _unit_muted(behavior: Any) -> bool:
    """The unit's hard mute; False before the privacy state is wired (and in tests)."""
    return bool(getattr(getattr(behavior, "privacy", None), "muted", False))


def _wire_power(voice, behavior: StackChanBehavior, night, stop_event) -> Any:
    """The host's idle-motion rule (power_idle.py): follows night and the configured level, re-asserts after a reconnect, and
    exposes `behavior.idle_still`. Moved out of `_serve_stackchan_channels` unchanged (docs/plan/seam-refactor.md, P1)."""
    from maipai_body.bodies.stackchan.power_idle import PowerIdle

    power = PowerIdle(
        voice.robot.client.set_idle_motion,
        night_active=lambda: night.night,
        configured_level=lambda: behavior.idle_level,
    )
    behavior.on_idle_level = power.refresh
    behavior.resync_idle = power.on_reconnect  # the page wrote the unit's flag: the host's own rule re-asserts it
    night.after_edge = power.refresh
    voice.session_listeners.append(lambda _device_id: power.on_reconnect())

    def _power_ticks() -> None:
        while not stop_event.wait(1.0):
            try:
                power.tick()
            except Exception:
                logger.warning("StackChan power rule failed", exc_info=True)

    threading.Thread(target=_power_ticks, name="stackchan-power-idle", daemon=True).start()
    behavior.idle_still = lambda: power.still
    behavior.idle_still_reason = lambda: power.still_reason
    return power


def _wire_light_and_health(voice, behavior: StackChanBehavior, avatar, sounds, power, offline, stop_event) -> Any:
    """The ring light service, the e-stop recovery loop, the camera cue, and the unit-event routing (self-heal, wake test, privacy,
    firmware update). Moved out of `_serve_stackchan_channels` unchanged (docs/plan/seam-refactor.md, P1). Returns the light."""
    from maipai_body.bodies.stackchan.light_wiring import start_stackchan_light

    def device_connected() -> bool:
        return bool(voice._sessions)

    light = start_stackchan_light(
        voice.robot,
        offline,
        stop_event,
        device_connected=device_connected,
        on_battery=power.on_battery_status,
    )
    behavior._rest_renderer._set_ring_sleeping = light.set_sleeping
    behavior.set_ring_dark_room = light.set_dark_room
    light.set_dark_room(bool(getattr(behavior, "ring_dark_room", False)))
    from maipai_body.bodies.stackchan.estop_recovery import EstopRecovery

    def device_answers() -> bool:
        """A real answer from the unit (a connected socket is not enough during a freeze)."""
        try:
            voice.robot.client.get_head_angles()
        except Exception:
            return False
        return True

    threading.Thread(
        target=EstopRecovery(voice.robot.robot, device_answers).run,
        args=(stop_event,),
        name="stackchan-estop-recovery",
        daemon=True,
    ).start()
    behavior.privacy_light = light
    behavior.on_firmware_version = sounds.on_firmware_version
    sounds.battery_low = lambda: light.facts.battery_low

    def camera_cue(active: bool) -> None:
        light.cue_camera(active)
        sounds.on_camera_cue(active)  # the shutter click, queued: a cue never waits on the unit

    voice.robot.robot._driver("camera").cue_sink = camera_cue
    # Self-healing (design note stackchan-self-healing-2026-11-13): what the unit says about its
    # restart guard, the wake engine test answers, and the ring's fault look while it holds.
    voice.heal.on_hold = lambda hold: light.update(fault=hold)

    from maipai_body.game_scores import ScoreBook

    behavior.score_book = ScoreBook(_data_dir() / "game-scores.json")

    def _brain_route_event(kind: str, extra: dict) -> None:
        try:
            setup = getattr(backend, "brain_setup", None)
            if setup is not None:
                from maipai_body import brain_route

                brain_route.on_event(setup.config_path, kind, extra)
        except Exception:
            logger.warning("the unit's brain route could not be filed", exc_info=True)

    def _heal_event(kind: str, extra: dict) -> None:
        if kind == "game_ended":
            try:
                behavior.score_book.on_event(getattr(behavior, "primary_unit", lambda: None)() or "", kind, extra)
            except Exception:
                logger.warning("a finished game could not be filed", exc_info=True)
        voice.heal.observe(kind, extra)
        voice.wake_tester.on_event(kind, extra)
        _brain_route_event(kind, extra)
        behavior.privacy.observe(kind, extra)
        updater = getattr(behavior, "firmware_updater", None)
        if updater is not None and kind.startswith("firmware_update_"):
            updater.on_unit_event(kind, extra, time.time())
        if kind == "first_run_done" and behavior.first_run_hook is not None:
            behavior.first_run_hook(getattr(behavior, "primary_unit", lambda: None)(), extra)

    behavior.on_unit_event = _heal_event
    avatar.unit_idle = lambda: not behavior._active.is_set()
    avatar.request_restart = voice._request_unit_restart
    return light


def _wire_hub_services(voice, behavior, avatar, faces, light, night, power, sounds, uplink, vision, units, link, offline, stop_event, device_connected, StackChanTurnBridge) -> Any:
    """The hub-facing StackChan services: head, brightness and volume commands, timers and announcements, the check-in, the command channel,
    look and orientation. Moved out of `_serve_stackchan_channels` unchanged (docs/plan/seam-refactor.md, P1). Returns the dance runner."""
    import math

    from maipai_body.bodies.stackchan.brightness import BrightnessControl
    from maipai_body.bodies.stackchan.head_commands import HeadCommander, gaze_detail
    from maipai_body.bodies.stackchan.volume import VolumeControl
    from maipai_body.hal.seam import HeadPose

    def _move_head(yaw_deg: int, pitch_deg: int, speed: int) -> None:
        pose = HeadPose(yaw=math.radians(yaw_deg), pitch=math.radians(pitch_deg))
        if not behavior._with_lease(lambda: voice.robot.robot.head.set(pose=pose, speed=speed)):
            raise RuntimeError("another part of the robot is using the head")

    def _head_blocked() -> str | None:
        if voice.robot.robot.estop_engaged:
            return "the emergency stop is latched"
        if behavior.privacy.head_blocked() is not None:
            return "it is in full quiet and holds its head still"
        # A spoken head command is the owner asking for the move, so charging no longer
        # blocks it (owner decision 2026-11-12: the 2026-10-20 charging rule is lifted).
        return None

    from maipai_body.bodies.stackchan.gaze import GazeReason
    from maipai_body.bodies.stackchan.sight import SightAnswers

    head_commander = HeadCommander(
        _move_head,
        blocked=_head_blocked,
        hold_pose=behavior.hold_pose,
        on_done=lambda command: behavior.gaze.note(GazeReason.COMMAND, gaze_detail(command)),
        find_face=behavior.find_person,
        face_yaw=behavior.face_yaw,
    )
    behavior.on_face_found = head_commander.face_found
    from maipai_body.bodies.stackchan.dance_wiring import wire_dance
    from maipai_body.bodies.stackchan.head_commands import CENTER_PITCH, CENTER_YAW, SPEED

    runner = wire_dance(
        voice=voice,
        behavior=behavior,
        light=light,
        night=night,
        head_commander=head_commander,
        level_head=lambda: _move_head(CENTER_YAW, CENTER_PITCH, SPEED),
        device_connected=device_connected,
        full_quiet_reason=behavior.privacy.muted_reason,
    )
    from maipai_body.bodies.stackchan.games import GameService as _GameService

    # "Play memory", "stop the game", "what games do you have" (and the Spanish asks) are
    # answered here, before the hub is asked: the games are the unit's own (firmware patch G01).
    from maipai_body.bodies.stackchan.game_voice import GamePicker, InstallNotices
    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT as _ACTIVE_UNIT

    behavior.game_notices = InstallNotices(_data_dir() / "install-notices.json")

    def _game_refusal() -> str | None:
        if behavior.privacy_units.muted_reason() == "full quiet":
            return "quiet"
        try:
            from maipai_body import child_gate

            if child_gate.any_present():
                return "child"
        except Exception:
            pass
        return None

    head_commander.game = _GameService(
        voice.robot.client._call,
        picker=GamePicker(),
        notices=behavior.game_notices,
        unit=lambda: _ACTIVE_UNIT.get() or "",
        refusal=_game_refusal,
        model_ready=lambda: bool(getattr(behavior, "talk_model_ready", False)),
        start_talk=lambda game_id, lang: getattr(behavior, "start_talk_game", lambda g, l: "")(game_id, lang),
    ).spoken
    from maipai_body.bodies.stackchan.music_dance_wiring import (
        MusicFeatureSwitch,
        music_status_code,
        wire_music_dance,
    )

    # The unit analyzes the room's sound only while robot.dance.auto is on and it is not muted.
    from maipai_body.bodies.stackchan.motion_limit import MotionLimit

    behavior.motion_limit = MotionLimit(voice.robot.client._call)
    music_switch = MusicFeatureSwitch(
        voice.robot.client._call,
        auto=lambda: behavior.dance_settings.auto,
        silenced=lambda: bool(behavior.speech_muted() or _unit_muted(behavior)),
    )
    # The settings page's "Dance to music" toggle flips dance_settings.auto, then asks for this sync (see _wire_idle_setting).
    behavior.music_sync = music_switch.sync
    from maipai_body.bodies.stackchan.wifi_list import WifiList

    wifi_list = WifiList(music_switch.call, on_changed=behavior.unit_facts.changed.set)
    behavior.wifi_list = wifi_list
    behavior.wifi_add_command = lambda payload: wifi_list.add(
        payload.get("ssid") if isinstance(payload, dict) else None,
        payload.get("password") if isinstance(payload, dict) else None,
    )
    behavior.wifi_forget_command = lambda payload: wifi_list.forget(
        payload.get("ssid") if isinstance(payload, dict) else None
    )
    behavior.wifi_use_command = lambda payload: wifi_list.use(
        payload.get("ssid") if isinstance(payload, dict) else None
    )
    from maipai_body.bodies.stackchan.wifi_list import prefer_tailnet as _prefer_tailnet

    behavior.prefer_tailnet_command = lambda payload: _prefer_tailnet(
        music_switch.call, payload
    )

    def identify_post(pcm: bytes, request_id: str | None = None) -> dict | None:
        try:
            import requests

            cookie, base_url = _hub_credentials_reader(link, "")()
            query = "kind=pcm16&rate=8000"
            if request_id is not None:
                from urllib.parse import quote

                query += f"&request={quote(request_id, safe='')}"
            response = requests.post(
                f"{base_url}/api/music/identify?{query}",
                data=pcm,
                headers={
                    "Cookie": f"session={cookie}",
                    "Content-Type": "application/octet-stream",
                },
                timeout=15,
            )
            if 200 <= response.status_code < 300:
                try:
                    return response.json()
                except Exception as exc:
                    logger.warning(
                        "StackChan song naming: 2xx response was not JSON: %s: %.200s",
                        type(exc).__name__,
                        str(exc),
                    )
            else:
                logger.warning(
                    "StackChan song naming: Home HTTP %s: %.120s",
                    response.status_code,
                    response.text,
                )
        except Exception as exc:
            logger.warning(
                "StackChan song naming: identify request raised %s: %.200s",
                type(exc).__name__,
                str(exc),
            )
        return None

    identify_setting_value = ["on"]

    def identify_setting() -> str:
        return identify_setting_value[0]

    def apply_identify_setting(values: dict) -> None:
        value = values.get("music.identify.online", "on")
        if value in ("on", "ask", "off"):
            identify_setting_value[0] = value

    music_dance = wire_music_dance(
        behavior=behavior,
        runner=runner,
        move_head=_move_head,
        center_pitch=CENTER_PITCH,
        speed=SPEED,
        switch=music_switch,
        identify_post=identify_post,
        identify_setting=identify_setting,
        identify_call_tool=voice.robot.client._call,
    )

    sounds.dance_active = lambda: music_dance.state in {"nod", "watch", "show", "calm", "break"}
    behavior.music_status = lambda saved: music_status_code(
        saved=saved,
        auto=behavior.dance_settings.auto,
        switch=music_switch,
        state=music_dance.state,
    )

    def idle_face_allowed() -> bool:
        if not IDLE_FACES_ENABLED or behavior._active.is_set():
            return False
        if behavior._rest.stage != "awake":
            return False
        if music_dance.state in {"nod", "watch", "show", "calm", "break"}:
            return False
        situation = runner.situation()
        if (
            situation.night
            or not situation.awake
            or situation.muted
            or situation.full_quiet
            or situation.camera_cue
            or situation.live_cue
        ):
            return False
        tracker = behavior._tracker
        if getattr(tracker, "stage", "idle") in {"aiming", "follow", "face-search"}:
            return False
        if getattr(tracker, "following", False):
            return False
        return True

    behavior.idle_faces = IdleFaces(behavior.show_face, idle_face_allowed, rng=random.Random())
    behavior.settings_listeners.append(apply_identify_setting)
    behavior.settings_listeners.append(music_switch.apply_settings)
    voice.session_listeners.append(music_switch.on_session)

    from maipai_body.bodies.stackchan.repeat import RepeatControl

    repeat_control = RepeatControl(
        missed=behavior.missed_log,
        muted=lambda: bool(behavior.speech_muted() or _unit_muted(behavior)),
    )
    behavior.settings_listeners.append(repeat_control.apply_settings)

    bridge = StackChanTurnBridge(
        voice,
        link,
        offline,
        repeat_control=repeat_control,
        units=units,
        cache_dir=_default_models_cache_dir(),
        # The current /api/stt/stream contract has no speaker field.
        # This adapter consumes that field when the hub adds it; absent
        # results remain anonymous on this turn.
        person_attribution=lambda result: getattr(result, "speaker_evidence", None),
        expression_sink=_turn_sink(behavior, light, faces, voice.connected_devices),
        live_sink=light.cue_live,
        uplink_stats=uplink,
        volume_control=VolumeControl(
            voice.robot.client._call,
            voice.robot.client.set_volume,
            on_set=lambda level, _command: night.set_owner_volume_from_voice(level),
        ),
        brightness_control=BrightnessControl(
            night.effective_brightness, night.set_brightness_from_voice
        ),
        head_control=head_commander,
        alarm_control=_alarm_control(behavior),
        gaze_control=behavior.gaze,
        sight_control=SightAnswers(
            face_age=behavior.face_age,
            camera_on=lambda: (
                behavior.watch_level() != "off" and not behavior.privacy.vision_off
            ),
            light=behavior.light_for_sight,
            camera_running_s=avatar.camera_running_s,
            watching=lambda: _detector_ready(vision),
            motion_age=lambda: None if vision is None else vision.motion_age(),
            person_age=lambda: None if vision is None else vision.person_age(),
            objects=lambda max_age_s: None if vision is None else vision.objects(max_age_s),
        ),
    )
    bridge.vision_ask = behavior.vision_ask
    from maipai_body.bodies.stackchan.talk_games import TalkGames

    # Voice games the model plays ("play twenty questions"): the start and end are answered here with no model.
    bridge.talk_games = TalkGames()
    # "Play a game" may pick a model game when a model answers (game_voice.py); the host keeps the state, the model gets no tools.
    behavior.talk_model_ready = True
    behavior.start_talk_game = lambda game_id, lang: bridge.talk_games.run(
        __import__("maipai_body.bodies.stackchan.talk_games", fromlist=["TalkCommand"]).TalkCommand("start", game_id, lang), _ACTIVE_UNIT_FOR_TALK.get() or ""
    )
    from maipai_body.bodies.stackchan.lock_voice import LockVoice

    # "Lock" / "bloquear": the unit that heard it locks, no model call. The service is read late (the settings polish is built after this).
    bridge.lock_control = LockVoice(lambda: getattr(getattr(voice, "polish", None), "lock", None))
    bridge.muted_reason = behavior.privacy.muted_reason
    bridge.on_error_line = sounds.on_error_line
    behavior.announce = bridge.speak_reaction
    voice.audio_handler = bridge.on_audio
    voice.turn_handler = bridge.listen
    from maipai_body.bodies.stackchan.reactions import Reactions

    reactions = Reactions(
        face=lambda expression: behavior.show_face(expression, while_listening=True),
        say=bridge.speak_reaction,
        quiet=lambda: night.night,
        busy=behavior.reaction_blocked,
        head_moved_ago=behavior.head_moved_ago,
        symbol=lambda name: voice.robot.client._call(
            "self.screen.show_symbol", {"name": name, "ms": 2500}
        ),
    )
    behavior.reaction = reactions.on_events
    behavior.reaction_tick = reactions.tick

    # Every unit after the first gets its own behavior object for touch and reactions (docs/plan/per-unit-behavior.md, step 2).
    from maipai_body.bodies.stackchan.adapter import create_stackchan_robot
    from maipai_body.unit_behaviors import UnitBehaviors

    def _make_unit_behavior(device_id: str) -> StackChanBehavior:
        client = voice.robot.client.for_unit(device_id)
        extra = StackChanBehavior(create_stackchan_robot(client), vision_bridge=None)
        extra.night_active = lambda: behavior.night_active()  # the household rules are shared
        extra.idle_still = lambda: behavior.idle_still()
        extra.idle_still_reason = lambda: behavior.idle_still_reason()
        extra.idle_level = behavior.idle_level
        extra.watch_level = "off"  # one camera pipeline: no face search on this unit yet

        def head_busy() -> str:
            if behavior.privacy_units.state_for(device_id).quiet:
                return "full quiet is on"
            if bridge._tasks:
                return "a turn is listening or speaking"
            return "quiet hours" if behavior.night_active() else ""

        extra.head_busy = head_busy
        unit_reactions = Reactions(
            face=lambda expression: extra.show_face(expression, while_listening=True),
            say=lambda text: bridge.speak_reaction(text, device_id),  # this unit's own line: only its own turn, speech and mute decide
            quiet=lambda: night.night,
            busy=extra.reaction_blocked,
            head_moved_ago=extra.head_moved_ago,
            symbol=lambda name: client._call("self.screen.show_symbol", {"name": name, "ms": 2500}),
        )
        extra.reaction = unit_reactions.on_events
        extra.reaction_tick = unit_reactions.tick
        from maipai_body.bodies.stackchan.orientation import SCREEN_ROTATION_ENABLED, OrientationReactions

        def rotate(degrees: int) -> None:
            if not SCREEN_ROTATION_ENABLED:
                return
            try:
                client._call("self.screen.set_rotation", {"degrees": degrees})
            except Exception:
                extra._warn_limited("rotation", "StackChan screen rotation failed")

        orientation = OrientationReactions(
            face=lambda expression: extra.show_face(expression, while_listening=False),
            say=lambda text: bridge.speak_reaction(text, device_id),
            rotate=rotate,
            hold_motion=lambda _held: None,  # the unit's own limiter (ML01) already holds a unit that is not upright
            quiet=lambda: ("night mode is on" if night.night else "") or ("asleep" if extra._rest.stage != "awake" else ""),
            busy=extra.reaction_blocked,
            resting=lambda: extra._rest.stage != "awake",
            head_pitch_deg=lambda: extra._tracker.pose[1],
            head_moved_ago=extra.head_moved_ago,
            missed=None,
            on_set_down=None,
        )
        extra.orientation = orientation
        extra.orientation_tick = orientation.tick
        import zlib

        jitter = (zlib.crc32(device_id.encode()) % 2000) / 100.0  # 0 to 20 s, the same for a unit each time: units' periodic calls are spread out
        keep_at = [time.monotonic() + jitter - KEEP_AWAKE_S]
        no_tool = [False]

        def keep_awake() -> None:
            """The hub link is up for this unit: restart its idle timers once a minute (patch 074), as for the first unit."""
            now = time.monotonic()
            if no_tool[0] or now - keep_at[0] < KEEP_AWAKE_S:
                return
            keep_at[0] = now
            try:
                client._call("self.power.keep_awake", {})
            except Exception as error:
                if type(error).__name__ == "NotSupported":
                    no_tool[0] = True

        extra.keep_awake_tick = keep_awake

        # This unit's own ring light: its own service, indicator and battery poll, so its listening cue shows on its own ring (never on another unit's).
        from types import SimpleNamespace

        from maipai_body.bodies.stackchan.light_wiring import start_stackchan_light

        extra.unit_stop = threading.Event()
        both_stop = threading.Event()

        def _watch_stops() -> None:  # the unit's own stop or the host's: either ends this unit's light threads
            while not (extra.unit_stop.is_set() or stop_event.is_set()):
                extra.unit_stop.wait(0.5)
            both_stop.set()

        threading.Thread(target=_watch_stops, name="stackchan-unit-light-stop", daemon=True).start()
        unit_light = start_stackchan_light(
            SimpleNamespace(robot=extra.robot, client=client),
            offline,
            both_stop,
            device_connected=lambda: device_id in voice._sessions,
            poll_delay_s=jitter,
        )
        extra._rest_renderer._set_ring_sleeping = unit_light.set_sleeping
        extra.privacy_light = unit_light
        extra.unit_light = unit_light
        extra.pose_held = lambda: orientation.pose != "upright" or _unit_not_upright(extra)

        # Dance to music for this unit (docs/plan/per-unit-behavior.md, step 5): its own feature switch, its own music controller and its own dance runner
        # (decision 16). The household's "Dance to music" setting is shared; the unit's own mute silences only this unit. Song naming stays with the first unit.
        from maipai_body.bodies.stackchan.motion_limit import MotionLimit

        extra.dance_settings = behavior.dance_settings
        extra.motion_limit = MotionLimit(client._call)
        unit_switch = MusicFeatureSwitch(
            client._call,
            auto=lambda: behavior.dance_settings.auto,
            silenced=lambda: bool(behavior.privacy_units.state_for(device_id).muted),
        )

        def _extra_move_head(yaw_deg: int, pitch_deg: int, speed: int) -> None:
            pose = HeadPose(yaw=math.radians(yaw_deg), pitch=math.radians(pitch_deg))
            if not extra._with_lease(lambda: extra.robot.head.set(pose=pose, speed=speed)):
                raise RuntimeError("another part of the robot is using the head")

        unit_music = wire_music_dance(
            behavior=extra,
            runner=behavior.dance_runner_for(device_id),
            move_head=_extra_move_head,
            center_pitch=CENTER_PITCH,
            speed=SPEED,
            switch=unit_switch,
            start_ticker=False,  # the unit's loop ticks it (extra_unit_tick)
        )
        extra.music_switch = unit_switch
        extra.music_sync = unit_switch.sync
        extra.music_tick = lambda: (unit_switch.sync(), unit_music.ladder_expire(time.monotonic()), unit_music.tick(time.monotonic()))
        unit_listener = unit_switch.apply_settings
        behavior.settings_listeners.append(unit_listener)
        extra.on_release = [lambda: behavior.settings_listeners.remove(unit_listener) if unit_listener in behavior.settings_listeners else None]
        return extra

    behavior.unit_behaviors = UnitBehaviors(
        primary_id=lambda: behavior.primary_unit(), connected=lambda: list(voice._sessions), make_behavior=_make_unit_behavior
    )
    behavior.other_unit_event_handlers.append(behavior.unit_behaviors.feed)
    voice.session_listeners.append(behavior.unit_behaviors.on_connect)
    behavior.unit_behaviors.start(stop_event)
    voice.primary_unit = behavior.primary_unit  # the first unit keeps voice.heal; the others get their own (server.heal_for)
    voice.unit_hold_listeners.append(
        lambda device_id, hold: (lambda light_of: light_of.update(fault=hold) if light_of is not None else None)(behavior.unit_behaviors.light_for(device_id))
    )
    # The green "your voice is being sent" cue belongs to the unit that is listening: an extra unit's turn lights its own ring, not the first unit's.
    bridge.live_sink_for = lambda active, unit: (behavior.unit_behaviors.light_for(unit) or light).cue_live(active)
    _wire_orientation(voice, behavior, bridge, night, power)
    bridge.on_user_words = reactions.on_user_words
    bridge.language = units.base.home.language
    voice.say_text = bridge.speak_reaction  # the Remote page's "Say something"

    def _head_busy() -> str:
        if getattr(getattr(behavior, "privacy", None), "quiet", False):
            return "full quiet is on"
        if bridge._tasks:
            return "a turn is listening or speaking"
        if behavior.night_active():
            return "quiet hours"
        return ""

    behavior.head_busy = _head_busy
    bridge.on_reply_mood = reactions.on_reply_mood
    from maipai_body.unit_polish import Polish

    polish = Polish(
        _unit_call(voice),
        units.store.get,
        units.store.update,
        synth=_local_synth(units.base),
        tone_on_unit=lambda device_id: _unit_plays_thinking_tone(faces, device_id),
    )
    polish.bind_faces(faces)  # the unit's screen language decides which language pack it holds
    polish.attach(bridge)
    voice.gate_bridge = bridge  # the settings page's remote activity feeds the bus gate (see _start_stackchan_settings)
    bridge.decoration_blocked = lambda: behavior._rest.stage != "awake" or behavior.night_active()
    voice.polish = polish  # the settings page reads the same state
    voice.session_listeners.append(polish.on_connect)
    _wire_look_owner(voice, units, behavior, polish, stop_event)
    from maipai_body.selftest.stackchan_wiring import build_context, build_service_hooks
    from maipai_body.speech.turn_client import TurnClient

    voice.selftest_checks, voice.selftest_runner = build_service_hooks(
        build_context(
            robot=voice.robot.robot,
            client=voice.robot.client,
            light=light,
            uplink=uplink,
            link=link,
            turn_factory=TurnClient,
        ),
        light,
    )
    return runner


def _note_away(store: dict, unit: str, extra: Any) -> None:
    """A `ws_away_notice {away_s}` event from a unit: it showed its banner after the host was out of reach for that long."""
    away = (extra or {}).get("away_s") if isinstance(extra, dict) else None
    if unit and isinstance(away, (int, float)) and not isinstance(away, bool) and away >= 0:
        store[unit] = {"away_s": int(away), "at": time.time()}


def _wire_privacy(voice, behavior: StackChanBehavior, avatar, camera_driver, stop_event) -> Any:
    """Mute, vision off and full quiet (firmware 105 to 108, docs/dev/stackchan-mute-2026-11-13.md).

    The unit is the authority; this reads its state back, keeps the host honest about it (no turn,
    no spoken line, no head move, no picture, no analysis while it is off) and checks that nothing
    leaks. Returns the controller; the state is `controller.state`."""
    from maipai_body.bodies.stackchan.privacy import PrivacyController, PrivacyState

    def leak(_what: str, _detail: str) -> None:
        light = getattr(behavior, "privacy_light", None)
        update = getattr(light, "update", None)
        if update is None:
            return
        update(fault=True)  # the existing error look, for half a minute
        threading.Timer(30.0, lambda: update(fault=bool(voice.heal.hold))).start()

    from maipai_body.bodies.stackchan.privacy import PrivacyUnits

    state = PrivacyState(on_leak=leak)
    controller = PrivacyController(voice.robot.client._call, state)
    # The first unit that connects is the primary and keeps the single-unit state above. Every other unit gets its own state,
    # read from that unit, and a turn on it is gated by its own mute (ACTIVE_UNIT), never by the primary's.
    others = PrivacyUnits(
        lambda device_id: voice.robot.client.for_unit(device_id)._call, on_leak=leak, primary=state
    )
    primary_id: list[str | None] = [None]
    behavior.primary_unit = lambda: primary_id[0]
    behavior.away_notices = {}  # unit -> {"away_s", "at"}: what the unit said when it lost the host for a while (shown on the health page)
    behavior.note_away = lambda unit, extra: _note_away(behavior.away_notices, unit, extra)
    behavior.privacy = state
    behavior.privacy_controller = controller
    behavior.privacy_units = others
    behavior.muted_reason = others.muted_reason
    behavior.settings_listeners.append(controller.apply_settings)

    def on_unit_connect(device_id: str) -> None:
        if primary_id[0] is None or primary_id[0] not in voice._sessions:
            primary_id[0] = device_id
        target = controller.on_connect if device_id == primary_id[0] else (lambda: others.on_connect(device_id))
        threading.Thread(target=target, name="stackchan-privacy-connect", daemon=True).start()

    voice.session_listeners.append(on_unit_connect)

    def poll_other_units() -> None:
        """Mute and vision changes made on a second unit reach that unit's own state (its touch events are not handled)."""
        while not stop_event.wait(1.0):
            try:
                others.poll_events(
                    list(voice._sessions),
                    primary=primary_id[0],
                    events_of=lambda device_id: voice.robot.client.for_unit(device_id).companion().poll_events(),
                    handlers=behavior.other_unit_event_handlers,
                )
            except Exception:
                logger.warning("polling the other units failed", exc_info=True)

    threading.Thread(target=poll_other_units, name="stackchan-unit-events", daemon=True).start()
    # Head moves from any part of the host stop in full quiet.
    voice.robot.robot._driver("head").move_blocked = others.head_blocked
    # No picture is asked for, kept or taken while vision is off; the local watch gate and the
    # stream ask both read this.
    camera_driver.vision_off = lambda: (
        others.vision_off()
    )  # `_start_stackchan_night` adds it to watch_allowed
    avatar.vision_blocked = others.vision_off
    avatar.on_frame_while_vision_off = others.frame_arrived

    def ticks() -> None:
        while not stop_event.wait(1.0):
            for tick in (state.tick, controller.tick, others.tick_all):
                try:
                    tick()
                except Exception:
                    logger.warning("privacy tick failed", exc_info=True)

    def stream_follows_vision(current: Any) -> None:
        """Vision went off: tell the unit's camera stream to stop. It came back on: start it again,
        quietly, if local watching is allowed (the household's watch level decides)."""
        try:
            if current.vision_off:
                behavior.robot.camera.stream(enabled=False)
            elif camera_driver.watch_allowed():
                behavior.robot.camera.stream(enabled=True, silent=True)
        except Exception:
            logger.debug("StackChan camera stream could not follow the vision state", exc_info=True)

    state.listeners.append(stream_follows_vision)

    threading.Thread(target=ticks, name="stackchan-privacy-ticks", daemon=True).start()
    return controller


def _wire_timers_and_announcements(
    voice,
    behavior: StackChanBehavior,
    stop_event: threading.Event,
    privacy: Any = None,
) -> dict[str, Callable[[dict], Any]]:
    """On-unit timers and hub announcements: the hub commands that drive them.

    Returns the extra `device-command` handlers for the StackChan command channel. The unit keeps
    and rings the timers itself (firmware patches 090 to 094); this only sets, lists and cancels
    them, says the line, and counts what is active for the check-in."""
    from maipai_body.bodies.stackchan.announce import Announcer
    from maipai_body.bodies.stackchan.games import GameService
    from maipai_body.bodies.stackchan.timers import TimerService

    def say(text: str) -> bool:
        return bool(behavior.announce is not None and behavior.announce(text))

    from maipai_body.bodies.stackchan.repeat import MissedLog

    missed_log = MissedLog()
    behavior.missed_log = missed_log

    def in_view() -> bool | None:
        # Unknown (None) when the camera is off: then nobody can be said to be absent.
        if behavior.watch_level() == "off":
            return None
        age = behavior.face_age()
        return age is not None and age <= IN_VIEW_S

    announcer = Announcer(
        missed=missed_log.note,
        in_view=in_view,
        show=lambda text: voice.robot.client.push_action(
            "create_reminder", {"duration_seconds": 1, "message": text, "repeat": False}
        ),
        say=say,
        night=lambda: bool(behavior.night_active()),
        clock=time.monotonic,
    )
    timers = TimerService(
        voice.robot.client._call,
        say=say,
        muted=lambda: announcer.muted,
        night=lambda: bool(behavior.night_active()),
        clock=time.monotonic,
        missed=missed_log.note,
    )
    behavior.speech_muted = lambda: announcer.muted or announcer.quiet
    behavior.timers = timers
    behavior.settings_listeners += [timers.apply_settings, announcer.apply_settings]

    from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

    unit_timers: dict[str, TimerService] = {}

    def timers_for(device_id: str) -> TimerService:
        """The timer service of one unit. The first unit to connect keeps `timers`; each other unit has its own, so two units'
        timer ids never meet and a ring on one is said on that unit."""
        if device_id == behavior.primary_unit() or behavior.primary_unit() is None:
            return timers
        if device_id not in unit_timers:

            def say_on(text: str, _d=device_id) -> bool:
                token = ACTIVE_UNIT.set(_d)
                try:
                    return say(text)
                finally:
                    ACTIVE_UNIT.reset(token)

            def muted_on(_d=device_id) -> bool:
                units = getattr(behavior, "privacy_units", None)
                return bool(units is not None and units.state_for(_d).muted_reason()) or announcer.quiet

            unit_timers[device_id] = TimerService(
                lambda name, args, _d=device_id: voice.robot.client.for_unit(_d)._call(name, args),
                say=say_on,
                muted=muted_on,
                night=lambda: bool(behavior.night_active()),
                clock=time.monotonic,
                missed=missed_log.note,
            )
            behavior.settings_listeners.append(unit_timers[device_id].apply_settings)
        return unit_timers[device_id]

    def on_other_unit_events(device_id: str, events: list) -> None:
        for event in events:
            if getattr(event, "kind", "") == "ws_away_notice":
                _note_away(behavior.away_notices, device_id, getattr(event, "extra", None))
        service = timers_for(device_id)
        for event in events:
            kind = str(getattr(event, "kind", ""))
            if kind.startswith("timer_"):
                try:
                    service.on_event(kind, getattr(event, "extra", None))
                except Exception:
                    logger.warning("a timer event of one unit failed", exc_info=True)

    behavior.other_unit_event_handlers.append(on_other_unit_events)

    def file_other_units_scores(device_id: str, events: list) -> None:
        book = getattr(behavior, "score_book", None)
        for event in events:
            if book is not None and getattr(event, "kind", "") == "game_ended":
                try:
                    book.on_event(device_id, "game_ended", getattr(event, "extra", None))
                except Exception:
                    logger.warning("a finished game of one unit could not be filed", exc_info=True)

    behavior.other_unit_event_handlers.append(file_other_units_scores)

    def heal_other_units(device_id: str, events: list) -> None:
        """Each extra unit's own restart guard and wake self-test hear that unit's events (never the first unit's)."""
        if device_id == behavior.primary_unit():
            return
        state, tester = voice.heal_for(device_id)
        for event in events:
            kind, extra = str(getattr(event, "kind", "")), getattr(event, "extra", None) or {}
            try:
                state.observe(kind, extra)
                tester.on_event(kind, extra)
            except Exception:
                logger.warning("a self-heal event of one unit failed", exc_info=True)

    behavior.other_unit_event_handlers.append(heal_other_units)

    behavior.timers_for = timers_for  # the voice alarm commands pick the talking unit's own service

    def refresh(device_id: str) -> None:
        service = timers_for(device_id)
        service.forget()

        def list_once() -> None:
            try:
                service.list_timers()
            except Exception:
                logger.debug("the unit's timers could not be listed", exc_info=True)

        threading.Timer(3.0, list_once).start()

    voice.session_listeners.append(refresh)

    def ticks() -> None:
        while not stop_event.wait(1.0):
            for tick in (timers.tick, announcer.tick, *[t.tick for t in list(unit_timers.values())]):
                try:
                    tick()
                except Exception:
                    logger.warning("timer or announcement tick failed", exc_info=True)

    threading.Thread(target=ticks, name="stackchan-timer-ticks", daemon=True).start()

    def set_muted(muted: bool) -> Callable[[dict], dict]:
        def handle(_payload: dict) -> dict:
            announcer.muted = muted
            return {"muted": muted}

        return handle

    mute_handlers = {"mute": set_muted(True), "unmute": set_muted(False)}
    if privacy is not None:
        # The StackChan mute is the unit's own (firmware patch 106): the hub's mute and unmute
        # drive it and answer from its read-back. Announcements and timers follow the unit's state,
        # whoever changed it (the face or Home).
        def follow_unit(state: Any) -> None:
            announcer.muted = bool(state.muted)
            announcer.quiet = bool(state.quiet)

        privacy.state.listeners.append(follow_unit)
        mute_handlers = privacy.handlers()
    return {
        **timers.handlers(),
        **GameService(voice.robot.client._call).handlers(),
        "announce": announcer.handle,
        **mute_handlers,
    }


def _wire_sounds(voice, behavior: StackChanBehavior, stop_event: threading.Event):
    """The unit's own sounds from the host side (firmware patches 115 to 118, sounds.py).

    Keeps the unit's sound policy current, plays the host-owned cues (low battery, shutter, error,
    dance start) and answers the hub's ``sound_test`` command. The light service does not exist
    yet: its low battery fact is attached later (``sounds.battery_low``)."""
    from maipai_body.bodies.stackchan.sounds import SoundService
    from maipai_body.presence.sleep_auto import QuietHours

    hours = QuietHours()

    def say(text: str) -> bool:
        return bool(behavior.announce is not None and behavior.announce(text))

    sounds = SoundService(
        voice.robot.client._call,
        say=say,
        night=lambda: bool(behavior.night_active()),
        quiet_minutes=hours.minutes,
        quiet_extras=lambda: (hours.days_mask, hours.quiet_now),
    )

    def on_settings(values: dict) -> None:
        hours.apply(values)
        sounds.apply_settings(values)

    behavior.settings_listeners.append(on_settings)
    voice.session_listeners.append(
        lambda _device_id: threading.Timer(3.0, sounds.on_connect).start()
    )

    def ticks() -> None:
        while not stop_event.wait(1.0):
            try:
                sounds.tick()
            except Exception:
                logger.warning("sound tick failed", exc_info=True)
        sounds.close()

    threading.Thread(target=ticks, name="stackchan-sound-ticks", daemon=True).start()
    return sounds


def _face_service(voice):
    """One FaceService for this host: the unit's face tools through the live voice link.

    A unit that is not connected counts as lost (the setting is saved and sent on reconnect)."""
    from maipai_body.faces import FaceService
    from maipai_body.hal.errors import BodyLost

    def call(name, arguments, *, device_id=None, timeout=5.0):
        return _device_tool_reply(voice, name, arguments, device_id, timeout)

    return FaceService(call)


def _unit_extras(voice):
    """One UnitExtras for this host: word reactions, clock and zone, network test and unit
    details, through the live voice link. A unit that is not connected counts as lost (the
    choice is saved and sent on reconnect)."""
    from maipai_body.hal.errors import BodyLost
    from maipai_body.unit_extras import UnitExtras

    def call(name, arguments, *, device_id=None, timeout=6.0):
        return _device_tool_reply(voice, name, arguments, device_id, timeout)

    return UnitExtras(call)


def _device_tool_reply(voice, name, arguments, device_id, timeout):
    """One unit tool call for the settings page. A unit that is not connected or did not answer is
    lost (BodyLost). A unit that answered with an error ("Unknown tool", a value below its minimum)
    comes back as ``{"ok": False, "error": ...}`` so the page can say what to do instead of failing."""
    import concurrent.futures

    from maipai_body.hal.errors import BodyLost

    try:
        return voice.call_device_tool(name, arguments, device_id=device_id, timeout=timeout)
    except (ConnectionError, TimeoutError, PermissionError, concurrent.futures.TimeoutError) as error:
        raise BodyLost(str(error)) from error
    except RuntimeError as error:
        return {"ok": False, "error": str(error) or "the unit answered with an error"}


def _unit_plays_thinking_tone(faces, device_id) -> bool:
    """True when the unit's own thinking tone is on and its firmware has it (so the host adds none)."""
    try:
        known = faces.features(device_id)
        return bool(faces.config(device_id).thinking_tone) and (known is None or "thinking" in known)
    except Exception:
        return False


def _local_synth(config):
    """The host's own local voice for rendering filler sounds, or None when no local speech server is set."""
    llm = config.llm
    if not llm.tts_url:
        return None
    from maipai_body.fillers import local_synth

    return local_synth(llm.tts_url, timeout_s=float(llm.timeout_seconds))


def _unit_call(voice):
    """The unit tool call every settings-page service shares: a unit that is not connected counts as lost."""
    from maipai_body.hal.errors import BodyLost

    def call(name, arguments, *, device_id=None, timeout=4.0):
        return _device_tool_reply(voice, name, arguments, device_id, timeout)

    return call


def _unit_remote(voice):
    """The Remote page's actions. The camera button works only when the unit has the camera build: a unit that
    cannot take a picture answers nothing, and the page then says it needs the camera build."""
    import asyncio

    from maipai_body.hal.errors import BodyLost
    from maipai_body.unit_remote import UnitRemote

    loop = getattr(voice, "_loop", None)

    def photo(device_id):
        if loop is None:
            return None
        try:
            return asyncio.run_coroutine_threadsafe(voice.take_photo(device_id), loop).result(timeout=15)
        except (ConnectionError, TimeoutError) as error:
            raise BodyLost(str(error)) from error
        except Exception:
            return None

    def speak(text):
        say_text = getattr(voice, "say_text", None)
        return bool(say_text(text)) if say_text is not None else False

    return UnitRemote(
        _unit_call(voice),
        photo=photo if loop is not None else None,
        speak=speak if getattr(voice, "say_text", None) is not None else None,
    )


def _picture_service(voice):
    """One PictureService for this host: the owner's picture faces, sent through the live voice link.
    A unit that is not connected counts as lost (the pictures are saved and sent on connect)."""
    from maipai_body.hal.errors import BodyLost
    from maipai_body.picture_faces import PictureService

    def call(name, arguments, *, device_id=None, timeout=8.0):
        return _device_tool_reply(voice, name, arguments, device_id, timeout)

    return PictureService(call)


def _turn_sink(behavior, light, faces=None, devices=None):
    """One turn event: move the face and set the ring's funnel state (the light standard).

    Wake word or tap opens a turn as ``listening`` (blue steady, eyes widen); the live cue (green)
    takes over while audio streams to the hub; thinking breathes magenta; speaking is white.
    """
    from concurrent.futures import ThreadPoolExecutor

    from maipai_body.faces import turn_cue
    from maipai_body.presence.funnel import FunnelState

    # One worker keeps the thinking cue's on and off in turn order and off the turn's own thread.
    cue_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="face-cue") if faces else None
    funnel = {
        "listening": FunnelState.LISTENING,
        "thinking": FunnelState.THINKING,
        "speaking": FunnelState.SPEAKING,
        "settle": FunnelState.IDLE,
    }

    talking_unit: list[str | None] = [None]  # the unit of the turn in progress, for a "settle" that arrives outside its scope

    def sink(state: str, *, mood: str | None = None) -> None:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT as _SCOPE_UNIT

        scoped = _SCOPE_UNIT.get()
        if scoped:
            talking_unit[0] = scoped
        unit_now = scoped or (talking_unit[0] if state == "settle" else None)
        if state == "settle":
            talking_unit[0] = None
        next_state = funnel.get(state)
        if next_state is not None:
            try:
                from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT as _LIGHT_UNIT

                units_light = getattr(behavior, "unit_behaviors", None)
                ((units_light.light_for(unit_now) if units_light is not None else None) or light).update(funnel=next_state)
            except Exception:  # a light never fails the turn
                logger.warning("StackChan funnel light failed", exc_info=True)
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT as _TURN_UNIT

        units_of = getattr(behavior, "unit_behaviors", None)
        owner = units_of.behavior_for(unit_now) if units_of is not None else None
        (owner or behavior).render_turn_state(state, mood=mood)  # a turn on an extra unit is that unit's own state, not the first unit's
        if cue_worker is not None:
            from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

            unit = ACTIVE_UNIT.get()  # the thinking cue belongs to the unit that is talking, never to every connected unit
            cue_devices = (lambda: [unit]) if unit else (devices or (lambda: []))
            cue_worker.submit(turn_cue, faces, cue_devices, state)

    return sink


async def _start_encrypted_listeners(voice, avatar) -> None:
    """Open the encrypted ports next to the plain ones, on every interface (LAN and tailnet alike).

    A PSK link checks no hostname and no certificate, so the same listener serves any address.
    MAIPAI_LINK_BIND picks another address; MAIPAI_LINK_*_PORT override the port numbers."""
    from maipai_body.bodies.stackchan.xiaozhi import link_security as ls

    bind = os.environ.get("MAIPAI_LINK_BIND", "0.0.0.0")
    try:
        voice_port = int(os.environ.get("MAIPAI_LINK_VOICE_PORT", ls.VOICE_TLS_PORT))
        avatar_port = int(os.environ.get("MAIPAI_LINK_AVATAR_PORT", ls.AVATAR_TLS_PORT))
        http_port = int(os.environ.get("MAIPAI_LINK_HTTP_PORT", ls.HTTP_TLS_PORT))
    except ValueError as exc:
        raise ValueError(
            "The encrypted link ports must be TCP port numbers. Set MAIPAI_LINK_VOICE_PORT, "
            "MAIPAI_LINK_AVATAR_PORT and MAIPAI_LINK_HTTP_PORT to free ports."
        ) from exc
    try:
        await voice.start_encrypted(bind, voice_port, http_port)
        await avatar.start_encrypted(bind, avatar_port)
    except OSError as exc:
        logger.warning(
            "The encrypted StackChan link could not start (%s). Free ports %s, %s and %s, then "
            "restart the bot; plain links still work.",
            type(exc).__name__,
            voice_port,
            avatar_port,
            http_port,
        )
        return
    logger.info(
        "StackChan encrypted link (TLS-PSK) listening on %s: voice %s, avatar %s, http %s",
        bind,
        voice_port,
        avatar_port,
        http_port,
    )


def _wire_firmware_update(voice, behavior, link, stop_event, situation_runner: Callable[[], Any]) -> None:
    """The signed-update path from Home to the unit: ask, download, verify (key and build number), serve once, report.

    `situation_runner` returns the dance runner (set later by the hub wiring); the update waits while it says the robot is busy."""
    from maipai_body.bodies.stackchan.firmware_update import FirmwareUpdater, stream_to_file

    hub_credentials = _hub_credentials_reader(link, "")
    firmware_answer: list[dict | None] = [None]

    def ask_firmware_home() -> dict | None:
        import requests

        cookie, base_url = hub_credentials()
        try:
            # Home requires the unit's firmware version; an unknown one counts as the oldest.
            current = behavior.unit_facts.snapshot().get("fw_version") or "0.0.0"
            response = requests.get(
                f"{base_url}/api/devices/me/firmware-update",
                params={"current": current},
                headers={"Cookie": f"session={cookie}"},
                timeout=10,
            )
            payload = response.json() if 200 <= response.status_code < 300 else None
            firmware_answer[0] = payload if isinstance(payload, dict) else None
        except Exception:
            firmware_answer[0] = None
        return firmware_answer[0]

    def download_firmware(path: Path) -> None:
        import requests

        cookie, base_url = hub_credentials()
        response = requests.get(
            f"{base_url}/api/devices/me/firmware-update/app.bin",
            headers={"Cookie": f"session={cookie}"},
            timeout=120,
            stream=True,
        )
        if not 200 <= response.status_code < 300:
            raise ValueError("Home firmware download failed")
        size = (firmware_answer[0] or {}).get("size")
        stream_to_file(response, path, size)  # stops at the announced size, or 16 MiB

    def download_firmware_signature() -> bytes | None:
        """What Home serves beside the image: the signed update header (`app.bin.hdr` and `app.bin.hdr.sig`), else the older
        detached signature (`app.bin.sig`). None when Home has neither."""
        import requests

        cookie, base_url = hub_credentials()
        def fetch(suffix: str) -> bytes | None:
            response = requests.get(
                f"{base_url}/api/devices/me/firmware-update/app.bin{suffix}",
                headers={"Cookie": f"session={cookie}"},
                timeout=30,
            )
            return response.content if response.status_code == 200 and response.content else None

        header, header_signature = fetch(".hdr"), fetch(".hdr.sig")
        if header and header_signature:
            return header + header_signature  # the signed header package: 56 + 64 bytes
        return fetch(".sig")

    def verify_firmware_image() -> Callable[[bytes, bytes], bool] | None:
        """Checks an image against `[update] trusted_key`; None when no key is configured. A 120-byte package is the signed
        header: it also has to carry a build number higher than the last one this host served."""
        from maipai_body.config import load_config

        try:
            key = load_config().update.trusted_key
        except Exception:
            key = None
        if not key:
            return None
        return _update_check(key, _UpdateBuilds(_data_dir() / "update-builds.json"), lambda: behavior.unit_facts.snapshot().get("fw_build"))

    def firmware_situation() -> dict[str, Any]:
        try:
            live = situation_runner().situation()
            timer_service = behavior.timers
            if timer_service is None:
                active, rows = None, []
            else:
                with timer_service._lock:
                    active = timer_service._active
                    rows = list(active.values()) if active else []
            kinds = [row.get("kind") for row in rows]
            due = [row.get("left") for row in rows if isinstance(row.get("left"), int)]
            return {
                "link_healthy": bool(voice._sessions) and not live.offline,
                "in_turn": behavior._active.is_set(),
                "in_call": bool(voice._speaking),
                "timer_active": active is None or bool(active),
                "timers_unknown": active is None,
                "alarm_active": "alarm" in kinds,
                "timer_due_in": min(due) if due else None,
                "muted": behavior.privacy.muted if behavior.privacy.known else True,
                "full_quiet": behavior.privacy.quiet if behavior.privacy.known else True,
            }
        except Exception:
            return {"link_healthy": False, "timers_unknown": True}

    def report_update(updating: bool, progress: int | None) -> None:
        voice.firmware_update_status = (updating, progress)

    updater = FirmwareUpdater(
        ask_home=ask_firmware_home,
        download=download_firmware,
        serve_once=voice.serve_firmware_once,
        download_signature=download_firmware_signature,
        verify=(_verify := verify_firmware_image()),
        on_installed=getattr(_verify, "accepted", None),
        call_tool=voice.robot.client._call,
        situation=firmware_situation,
        battery=voice.robot.client.get_battery_status,
        unit_version=lambda: behavior.unit_facts.snapshot().get("fw_version"),
        now=time.time,
        report=report_update,
    )
    behavior.firmware_updater = updater
    behavior.settings_listeners.append(updater.apply_settings)
    voice.session_listeners.append(lambda _device_id: updater.tick(time.time()))

    def firmware_tick() -> None:
        while not stop_event.wait(600):
            updater.tick(time.time())

    threading.Thread(
        target=firmware_tick, name="stackchan-firmware-update", daemon=True
    ).start()



@dataclass
class StackChanBody:
    """What the StackChan body is made of before its services start: the two servers, the pairing and link policy, the units
    registry, the adapter-backed face and vision pieces, and the behavior. The service wiring takes these by name."""

    voice: Any
    avatar: Any
    pairing: Any
    link_security: Any
    units: Any
    tls_context: Any
    cert_path: str | None
    faces: Any
    vision: Any
    behavior: Any
    camera_driver: Any


def _build_stackchan_body(host: str, link: LinkLifecycle | None) -> StackChanBody:
    global UNIT_LINK_ENCRYPTED
    from maipai_body.bodies.stackchan.adapter import StackChanRobotAdapter
    from maipai_body.bodies.stackchan.avatar.server import AvatarServer
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore, default_pairing_path
    from maipai_body.bodies.stackchan.xiaozhi.server import XiaozhiDeviceClient, XiaozhiServer
    from maipai_body.bodies.stackchan.xiaozhi.tls import server_ssl_context

    vision_host = os.environ.get("MAIPAI_VISION_HOST", host)
    try:
        vision_port = int(os.environ.get("MAIPAI_VISION_PORT", "8767"))
    except ValueError as exc:
        raise ValueError("MAIPAI_VISION_PORT must be a TCP port number.") from exc
    pairing = PairingStore(default_pairing_path())
    voice = XiaozhiServer(
        pairing,
        robot=None,
        vision_host=vision_host,
        vision_port=vision_port,
        advertised_vision_url=os.environ.get("MAIPAI_VISION_URL"),
    )
    avatar = AvatarServer(pairing)
    # The encrypted robot link (TLS 1.2 with a pre-shared key; xiaozhi/link_security.py).
    from maipai_body.bodies.stackchan.xiaozhi.link_security import LinkSecurity

    link_security = LinkSecurity(pairing)
    voice.link = link_security
    avatar.link = link_security
    # Several robots: every unit's brain, persona, volume cap and alarms are picked by its
    # Device-Id (units.py); an unknown unit gets the top-level settings.
    from maipai_body.units import registry_from_disk

    units = registry_from_disk()
    avatar.units = units
    cert_path = os.environ.get("MAIPAI_XIAOZHI_TLS_CERT")
    key_path = os.environ.get("MAIPAI_XIAOZHI_TLS_KEY")
    tls_context = server_ssl_context(cert_path, key_path)
    UNIT_LINK_ENCRYPTED = tls_context is not None
    voice.robot = StackChanRobotAdapter(XiaozhiDeviceClient(voice))
    from maipai_body.faces import sync_on_connect

    faces = _face_service(voice)
    voice.session_listeners.append(lambda device_id: sync_on_connect(faces, device_id))
    voice._avatar_frame_sender = avatar.send_frame
    camera_driver = voice.robot.robot._driver("camera")
    avatar.start_camera_on_connect = lambda: (
        not voice.robot.robot.estop_engaged and camera_driver.watch_allowed()
    )
    vision = None
    try:
        from maipai_body.bodies.stackchan.vision_bridge import StackChanVisionBridge

        # The pinned YuNet model comes from Home like every other model; until it has been synced
        # the detector finds nothing and says so once every ten minutes.
        from maipai_body.vision.look_fast import LazyLookDetector
        from maipai_body.vision.models import YOLOX_NANO
        from maipai_body.vision.yunet import LazyFaceDetector

        vision = StackChanVisionBridge(
            voice.robot.robot,
            detector=LazyFaceDetector(lambda: _load_yunet_model(link)),
            embedder=None,
            gallery=None,
            # The Look detector (people and household things) rides the same frames; its model
            # is synced from Home like YuNet and the robot works without it until it arrives.
            look_detector=LazyLookDetector(lambda: _load_pinned_model(link, YOLOX_NANO)),
        )
    except Exception as exc:
        # One line, not a traceback: the cause is almost always a package the bundle lacks.
        logger.warning("StackChan face watching is unavailable (%s: %s)", type(exc).__name__, exc)
    if vision is not None:
        # Firmware patch NX05: a face found by the host's model lights the unit's small face glyph (rate limited, never waits).
        from maipai_body.bodies.stackchan.face_seen import FaceSeenSignal

        vision.on_face_seen = FaceSeenSignal(voice.robot.client._call).note
    behavior = StackChanBehavior(
        voice.robot.robot, vision_bridge=vision, baseline_path=_data_dir() / "scene_baseline.json"
    )
    behavior.camera_counters = lambda: (
        avatar.camera_frames_received,
        avatar.camera_bytes_received,
    )
    behavior.event_poll = voice.robot.client.companion().poll_events
    return StackChanBody(
        voice=voice,
        avatar=avatar,
        pairing=pairing,
        link_security=link_security,
        units=units,
        tls_context=tls_context,
        cert_path=cert_path,
        faces=faces,
        vision=vision,
        behavior=behavior,
        camera_driver=camera_driver,
    )


async def _serve_stackchan_channels(
    stop_event: threading.Event,
    host: str,
    xiaozhi_port: int,
    avatar_host: str,
    avatar_port: int,
    link: LinkLifecycle | None = None,
    offline: OfflineRungs | None = None,
) -> None:
    from maipai_body.supervisor import Supervisor

    supervisor = Supervisor()
    _RUNTIME.update(supervisor=supervisor, started=time.time(), stop=stop_event)
    service_threads.SUPERVISOR = supervisor  # every service thread is now watched and restarted when it dies
    supervisor.start()
    from maipai_body.chaos import start_from_environment

    start_from_environment(supervisor)  # a no-op unless MAIPAI_CHAOS is set (tests only)
    body = _build_stackchan_body(host, link)
    from maipai_body.bodies.stackchan.turn import StackChanTurnBridge

    voice, avatar, pairing, link_security = body.voice, body.avatar, body.pairing, body.link_security
    units, tls_context, cert_path = body.units, body.tls_context, body.cert_path
    faces, vision, behavior, camera_driver = body.faces, body.vision, body.behavior, body.camera_driver
    privacy = _wire_privacy(voice, behavior, avatar, camera_driver, stop_event)
    if link is not None:
        from maipai_body.bodies.stackchan.vision_post import VisionPoster

        # Pictures reach Home only through this poster; `robot.vision` (settings_changed below) and
        # Home's own refusals decide whether any is sent.
        behavior.vision_poster = VisionPoster(_hub_credentials_reader(link, ""))
        behavior.lux = lambda: getattr(voice.robot.client, "last_lux", None)
        _start_robot_checkin(voice, behavior, link, stop_event)
    timers = _wire_timers_and_announcements(voice, behavior, stop_event, privacy)
    sounds = _wire_sounds(voice, behavior, stop_event)
    night = _start_stackchan_night(
        voice, behavior, link, stop_event, {**timers, **sounds.handlers()}
    )
    if link is not None:
        _wire_firmware_update(voice, behavior, link, stop_event, lambda: runner)
    behavior._rest_renderer._set_brightness = night._device.set_brightness
    behavior._rest_renderer._restore_brightness = night.effective_brightness
    behavior.on_levels_changed = night.set_levels_from_unit
    power = _wire_power(voice, behavior, night, stop_event)
    light = _wire_light_and_health(voice, behavior, avatar, sounds, power, offline, stop_event)

    def device_connected() -> bool:
        return bool(voice._sessions)

    from maipai_body.bodies.stackchan.uplink_stats import UplinkStats

    uplink = UplinkStats()
    runner = None  # the dance runner (set by the hub wiring; `firmware_situation` reads it when asked)
    if link is not None and offline is not None:
        runner = _wire_hub_services(
            voice, behavior, avatar, faces, light, night, power, sounds, uplink, vision, units, link, offline, stop_event,
            device_connected, StackChanTurnBridge,
        )
    await voice.start(host, xiaozhi_port, ssl=tls_context)
    # The voice and avatar servers share this loop. A task beats once a second; a loop that stops beating shows on the health page as "not responding"
    # (reported, not restarted: the servers cannot be swapped inside a running host, so the advice is to restart the host).
    from maipai_body.supervisor import Worker as _Worker

    main_loop = asyncio.get_running_loop()

    async def _beat_servers() -> None:
        while not stop_event.is_set():
            supervisor.beat("voice server")
            await asyncio.sleep(1.0)

    beat_task = asyncio.create_task(_beat_servers(), name="voice-server-heartbeat")

    class _LoopHandle:
        @staticmethod
        def is_alive() -> bool:
            return main_loop.is_running() and not beat_task.done()

    supervisor.add(
        _Worker(
            "voice server",
            lambda: _LoopHandle(),
            heartbeat_limit_s=15.0,
            plain="the voice and avatar servers",
            advice="Restart the host with `stackchan service stop` and `stackchan service start`. If it happens again, run `stackchan service logs`.",
        )
    )
    settings_server = _start_settings_page(voice, pairing, units, behavior, faces, link_security)
    try:
        await avatar.start(avatar_host, avatar_port, ssl=tls_context)
        await _start_encrypted_listeners(voice, avatar)
        scheme = "wss" if cert_path else "ws"
        logger.info(
            "StackChan xiaozhi and avatar services listening on %s://%s:%s and %s://%s:%s",
            scheme,
            host,
            xiaozhi_port,
            scheme,
            avatar_host,
            avatar_port,
        )
        while not stop_event.is_set() and not voice._session_ready.is_set():
            await asyncio.sleep(0.1)
        if voice._session_ready.is_set() and not stop_event.is_set():
            # start_presence makes device calls that wait on this loop: run it off the loop.
            await asyncio.to_thread(behavior.start_presence, stop_event)
        await asyncio.to_thread(stop_event.wait)
    finally:
        beat_task.cancel()
        supervisor.stop()  # stopping the host on purpose is not a failure: nothing is restarted from here on
        service_threads.SUPERVISOR = None
        _RUNTIME.clear()
        if settings_server is not None:
            settings_server.stop()
        behavior.close()
        await avatar.close()
        await voice.close()


_IDLE_LEVELS = {"off": "still", "calm": "calm", "lively": "lively"}


def _wire_look_owner(voice, units, behavior, polish, stop_event) -> None:
    """Who turns toward faces (look_owner.py): the heartbeat that holds the unit's owner lease while the Home hub's tracking runs."""
    from maipai_body.first_run_name import FirstRunNames
    from maipai_body.look_owner import LookLeaseRunner, LookOwner

    names = FirstRunNames(units.store)   # the name picked on the robot's first run becomes the unit's name on the page
    behavior.first_run_hook = names.on_event

    def other_units_first_run(device_id: str, events: list) -> None:
        for event in events:
            if getattr(event, "kind", "") == "first_run_done":
                names.on_event(device_id, getattr(event, "extra", None))

    behavior.other_unit_event_handlers.append(other_units_first_run)

    def hub_configured() -> bool:
        return getattr(units.base, "brain", "llm") == "home" or bool(os.environ.get("MAIPAI_HUB_URL", "").strip())

    def tracking() -> bool:
        vision = getattr(behavior, "_vision", None)
        ready = getattr(behavior, "_look_ready", None)
        return bool(
            vision is not None
            and callable(ready)
            and ready()
            and (behavior.look_toward_speaker or behavior.look_for_faces)
            and behavior.watch_level() != "off"
        )

    owner = LookOwner(polish.probe, units.store.get, hub_configured=hub_configured, tracking=tracking)
    voice.look_owner = owner
    polish.prefs.look_status = owner.cached_status  # the page shows who turns toward faces and when someone was last seen
    voice.session_listeners.append(owner.forget)
    runner = LookLeaseRunner(
        owner,
        lambda: list(getattr(voice, "_sessions", ())),
        stop_event,
        apply=lambda device_id: getattr(voice, "look_sync", lambda _id: None)(device_id),
    )
    threading.Thread(target=runner.run, name="look-lease", daemon=True).start()


def _wire_brain_page(backend) -> None:
    """The Brain page and the first-run page (brain_setup): three ways to get a brain; starts the local model server when it is the brain."""
    from maipai_body.brain_setup.controller import BrainSetup
    from maipai_body.config import example_config_path

    setup = BrainSetup(example_config_path(), _data_dir() / "local-stack")
    backend.brain_setup = setup
    setup.on_leave_hosted = lambda: _leave_hosted_units(voice)
    if setup.start_if_enabled():
        logger.info("The local model server is running on this computer.")
        from maipai_body import service_threads

        supervisor = service_threads.SUPERVISOR
        if supervisor is not None:  # watched like every other part: it is restarted if it dies, and reported if it keeps failing
            from maipai_body.supervisor import Worker as _ModelWorker

            class _ModelHandle:
                @staticmethod
                def is_alive() -> bool:
                    return setup.llama.running()

            def restart_model():
                if not setup.start_if_enabled():
                    raise RuntimeError("the local model server did not start")
                return _ModelHandle()

            worker = supervisor.add(
                _ModelWorker(
                    "local model",
                    restart_model,
                    plain="the local model",
                    advice="Open the Brain page and press Install again, or pick the small model. Then run `stackchan service logs`.",
                ),
                start_now=False,
            )
            worker.handle = _ModelHandle()
            worker.state, worker.last_start, worker.last_beat = "ok", time.monotonic(), time.monotonic()
            worker.kill = setup.llama.stop  # the chaos hook: the model server stops; the watchdog starts it again
    elif setup.needs_choice():
        logger.info("No brain is set yet. Open the settings page on this computer at /brain to choose one of three ways.")


def _quiet_registry_values(values: dict) -> dict:
    """A unit's saved quiet schedule and "Quiet now" as the registry keys the sound service and the night rules read."""
    from maipai_body.settings_keys import QUIET_DAYS_KEY, QUIET_ENABLED_KEY, QUIET_FROM_KEY, QUIET_NOW_KEY, QUIET_TO_KEY

    out: dict = {}
    schedule = values.get("quiet_schedule")
    if isinstance(schedule, dict):
        for key, registry in (("from", QUIET_FROM_KEY), ("to", QUIET_TO_KEY), ("days", QUIET_DAYS_KEY), ("enabled", QUIET_ENABLED_KEY)):
            if key in schedule:
                out[registry] = schedule[key]
        if "enabled" in schedule and schedule["enabled"]:
            out[QUIET_ENABLED_KEY] = True  # applied after from and to, so a window that is on stays on
    if isinstance(values.get("quiet_now"), bool):
        out[QUIET_NOW_KEY] = values["quiet_now"]
    return out


def _wire_idle_setting(backend, units, behavior, voice) -> None:
    """The page's "Idle movement" (off, calm, lively; default off) sets the one idle level every
    ambient head move is gated on. It is applied at start, when a unit connects, and on each save."""

    def apply(device_id: str, values: dict) -> None:
        registry = _quiet_registry_values(values)
        if registry:
            for listener in behavior.settings_listeners:  # the household quiet schedule (sounds, night): the same keys Home sends
                try:
                    listener(registry)
                except Exception:
                    logger.warning("a quiet hours listener failed", exc_info=True)
        level = values.get("idle_movement")
        if level in _IDLE_LEVELS:
            behavior.idle_level = _IDLE_LEVELS[level]
            behavior.on_idle_level()
        if "idle_motion" in values and getattr(behavior, "resync_idle", None) is not None:
            behavior.resync_idle()
        if isinstance(values.get("dance_to_music"), bool):
            # "Dance to music" (off until chosen): the same switch Home's robot.dance.auto flips. The music dance controller
            # runs only while it is on, and the unit analyzes the room's sound only then (MusicFeatureSwitch).
            behavior.dance_settings.apply({"robot.dance.auto": values["dance_to_music"]})
            sync = getattr(behavior, "music_sync", None)
            if sync is not None:
                sync()
        for key in ("look_speaker", "look_faces"):
            if isinstance(values.get(key), bool):
                choice[key] = values[key]
        if isinstance(values.get("look_on_wake"), bool):
            behavior.look_on_wake = values["look_on_wake"]  # "Look around when I hear the wake word" (wake_look.py)
            if not behavior.look_on_wake:
                behavior.stop_wake_look("the setting was turned off")
        unit_id[0] = device_id
        sync_look(device_id)

    def sync_look(device_id: str) -> None:
        """The host's own face search (this person's two choices) runs only when it owns face seeking, or when the robot owns it
        but this unit cannot seek yet (look_owner.py); with no owner service every choice applies as before."""
        owner = getattr(voice, "look_owner", None)
        may = True
        if owner is not None:
            try:
                may = owner.host_may_search(device_id)
            except Exception:
                may = True
        behavior.look_toward_speaker = bool(choice["look_speaker"]) and may
        behavior.look_for_faces = bool(choice["look_faces"]) and may

    choice = {"look_speaker": False, "look_faces": False}
    unit_id: list[str | None] = [None]  # the unit the last save or connect named (one unit per host in practice)
    from maipai_body.wake_look import UnitCheck

    behavior.wake_unit_busy = UnitCheck(
        lambda: getattr(getattr(voice, "polish", None), "probe", None), lambda: unit_id[0]
    ).reason

    def seeker_owns() -> bool:
        """The owner chose that nobody turns toward faces (the wake look then stays still)."""
        owner = getattr(voice, "look_owner", None)
        device_id = unit_id[0]
        if owner is None or not device_id:
            return False
        try:
            # Only "nobody turns toward faces" blocks the wake look. The unit's own seeker moves on motion and the wake look is
            # a short pan after the wake word, so a robot-owned unit still looks around when called (owner request 2026-11-17).
            return owner.setting(device_id) == "off"
        except Exception:
            return False

    behavior.wake_seeker_owns = seeker_owns
    voice.look_sync = sync_look
    backend.on_saved = apply
    backend.score_book = getattr(behavior, "score_book", None)  # best scores per person for the Games page

    def on_connect(device_id: str) -> None:
        own = units.store.get(device_id)
        apply(
            device_id,
            {
                "idle_movement": own.get("idle_movement", "off"),
                "look_speaker": own.get("look_speaker", False),
                "look_faces": own.get("look_faces", False),
                "look_on_wake": own.get("look_on_wake", True),
                "dance_to_music": own.get("dance_to_music", False),
                **{k: own[k] for k in ("quiet_schedule", "quiet_now") if k in own},
            },
        )

    backend.music_status = lambda saved: getattr(behavior, "music_status", lambda s: "waiting" if s else "off")(saved)
    voice.session_listeners.append(on_connect)


def _wire_installed_sets(voice, backend, pairing, stop_event) -> None:
    """The 'On my robot' page: per-robot installed sets, the first-run defaults, and a retry loop for a robot that was away (installed_set.py)."""
    from maipai_body.installed_set import InstalledSets, InstalledStore
    from maipai_body.installed_set_legacy import LegacyTransport

    packs = getattr(getattr(backend, "polish", None), "packs", None)
    if packs is None:
        return
    try:
        from maipai_body.config import load_config

        language = load_config().home.language or "en"
    except Exception:
        language = "en"
    transport = LegacyTransport(packs, lambda unit: unit in voice._sessions, lambda unit: voice.device_supports("assets", unit))  # the unit says so in its hello; there is no read-only asset tool to probe
    sets = InstalledSets(packs.library, InstalledStore(_data_dir() / "installed-sets.json"), transport, language=lambda unit: language)
    backend.installed = sets
    backend.installed_units = lambda: [{"id": d, "name": "", "connected": d in voice._sessions} for d in sorted(set(pairing.paired_devices()) | set(voice._sessions))]

    def on_connect(device_id: str) -> None:
        threading.Timer(4.0, sets.reconcile, args=(device_id,)).start()  # a moment after the unit's own start-up, like the other syncs

    voice.session_listeners.append(on_connect)

    def retry() -> None:
        while not stop_event.wait(30.0):
            for unit in sets.pending():
                if unit in voice._sessions:
                    try:
                        sets.reconcile(unit)
                    except Exception:
                        logger.warning("installed set retry failed", exc_info=True)

    service_threads.start(retry, name="installed-set-retry", stop=stop_event)


from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT as _ACTIVE_UNIT_FOR_TALK  # noqa: E402


def _wire_assets(voice, backend) -> None:
    """Signed, ranged, cacheable delivery of the packs a unit is meant to hold (assets.py): a unit gets only what the host chose for it."""
    from maipai_body.assets import Asset, AssetService, SigningKey

    packs = getattr(getattr(backend, "polish", None), "packs", None)
    if packs is None:
        return

    def provider(device_id: str, asset_id: str):
        for pack_id in {p for p in packs.wanted(device_id).values() if p}:
            try:
                pack = packs.library.get(pack_id)
            except Exception:
                continue
            if pack.sha256 == asset_id:
                return Asset(pack.sha256, pack.kind, pack.name, pack.version, pack.payload)
        return None

    voice.assets = AssetService(SigningKey(_data_dir() / "asset-signing.pem"), provider)


_RUNTIME: dict[str, Any] = {}  # what the running host shares with its pages: the supervisor and the start time


def _start_settings_page(voice, pairing, units, behavior, faces=None, link_security=None):
    """Serve the core settings page from the live host (loopback, port 8051; 0 turns it off).

    Also pushes each unit's own alarms to it, by Device-Id, whenever that unit connects."""
    from maipai_body.live_units import LiveUnits
    from maipai_body.settings_page import SettingsBackend
    from maipai_body.unit_device import UnitDevice

    def push_alarms(device_id: str) -> None:
        try:
            units.push_alarms(
                device_id,
                lambda d, name, args: voice.call_device_tool(name, args, device_id=d),
            )
        except Exception:
            logger.warning(
                "could not push alarms to unit %s; they are pushed again when it reconnects",
                device_id[-5:],
                exc_info=True,
            )

    voice.session_listeners.append(push_alarms)
    from maipai_body.unit_extras import sync_on_connect as extras_sync

    extras = _unit_extras(voice)
    # When a unit connects: set its clock and zone (the host is its only time source) and send the
    # owner's word reactions if there are any.
    voice.session_listeners.append(lambda device_id: extras_sync(extras, device_id))
    # The owner's own picture faces (firmware patch H04): the unit keeps them in memory, so they go out again
    # when it connects.
    from maipai_body.picture_faces import sync_on_connect as pictures_sync

    pictures = _picture_service(voice)
    voice.session_listeners.append(lambda device_id: pictures_sync(pictures, device_id))
    try:
        port = int(os.environ.get("MAIPAI_STACKCHAN_SETTINGS_PORT", "8051"))
    except ValueError:
        logger.warning("MAIPAI_STACKCHAN_SETTINGS_PORT is not a port number; settings page is off")
        return None
    if port == 0:
        return None
    live = LiveUnits(
        voice, sole_unit_version=lambda: behavior.unit_facts.snapshot().get("fw_version")
    )
    config = units.base
    gate_bridge = getattr(voice, "gate_bridge", None)
    backend = SettingsBackend(
        devices=pairing.paired_devices,
        store=units.store,
        live=live.live,
        host_address=f"127.0.0.1:{port}",
        update_source=config.update.source,
        public_key=config.update.trusted_key,
        push=live.push,
        preset=config.update.preset,
        language=config.home.language,
        faces=faces,
        extras=extras,
        pictures=pictures,
        device=UnitDevice(_unit_call(voice)),
        remote=_unit_remote(voice),
        polish=getattr(voice, "polish", None),
        link=link_security,
    )
    _wire_idle_setting(backend, units, behavior, voice)
    _wire_brain_page(backend)
    if gate_bridge is not None:
        gate_bridge.remote_active = lambda device_id: backend.activity.session_active(device_id)
    from maipai_body.settings_server import SettingsServer

    try:
        lan = False
        try:
            from maipai_body.config import load_config

            lan = load_config().settings.lan
        except Exception:
            lan = False
        auth = None
        if lan:
            from maipai_body.local_guard import SettingsAuth

            auth = SettingsAuth(_default_pairing_path().parent / "settings-token")
        server = SettingsServer(backend, "0.0.0.0" if lan else "127.0.0.1", port, auth=auth)
        _start_coding_companion(backend, voice)
        _start_wake_word_maker(backend)
        _start_pantry(backend, voice)
        from maipai_body import service_handover
        from maipai_body.service_cmd import Service

        def _service_state() -> dict:
            probe = Service(say=lambda _text: None)
            return {"can_install": probe.system in ("mac", "linux") and not probe.file().exists()}

        backend.service_state = _service_state
        backend.service_handover = service_handover.start_handover
        backend.pair_code = pairing.create_pair_code
        backend.pair_exchange = voice
        backend.phone_link = lambda: {
            "lan": lan,
            "base": f"http://{_lan_address()}:{port}",
            "token": auth.token if auth else "",
        }
    except OSError:
        logger.warning(
            "settings page port %d is in use; set MAIPAI_STACKCHAN_SETTINGS_PORT to a free port",
            port,
        )
        return None
    _wire_assets(voice, backend)
    _wire_installed_sets(voice, backend, pairing, _RUNTIME.get("stop") or threading.Event())
    server.start()
    logger.info("StackChan settings page on http://127.0.0.1:%d/settings", server.port)
    if os.environ.get("MAIPAI_HUB_HOST") != "1":   # run by hand in a terminal: say once what is running and what to do next (a service logs to its file instead)
        print(
            f"MaiPai host is running.\n  Choose a brain: open http://127.0.0.1:{server.port}/brain in a browser on this computer.\n"
            "  Pair a robot: run `stackchan pair` in another terminal.\n  Stop the host with Ctrl+C.",
            file=sys.stderr,
            flush=True,
        )
    supervisor = _RUNTIME.get("supervisor")
    if supervisor is not None:
        from maipai_body.health import build_health
        from maipai_body.supervisor import Worker

        started = _RUNTIME.get("started") or time.time()
        backend.health = lambda: build_health(supervisor, connected=list(voice._sessions), paired=pairing.paired_devices(), started=started, away=getattr(behavior, "away_notices", None))
        # A part that needs you is also said on each robot's own screen (degraded_banner.py); a unit without the tool is never sent anything.
        from maipai_body.degraded_banner import DegradedBanner

        banner = DegradedBanner(
            health=backend.health,
            units=lambda: list(voice._sessions),
            has_tool=lambda unit: getattr(getattr(voice, "polish", None), "probe", None) is not None and voice.polish.probe.has(unit, "banner") is True,
            send=lambda unit, args: voice.robot.client.for_unit(unit)._call("self.banner.set", args),
        )

        banner_stop = threading.Event()

        def _banner_loop() -> None:
            while not banner_stop.wait(10.0):
                banner.tick()

        service_threads.start(_banner_loop, name="degraded-banner", stop=banner_stop)
        holder = {"server": server}
        bind = "0.0.0.0" if lan else "127.0.0.1"

        def restart_settings_page():
            try:
                holder["server"].stop()
            except Exception:
                pass
            holder["server"] = SettingsServer(backend, bind, port, auth=auth)
            holder["server"].start()
            return holder["server"]._thread

        worker = supervisor.add(Worker("settings page", restart_settings_page, plain="the settings page", advice="Open the settings page again in a minute. If it does not come back, run `stackchan service logs`."), start_now=False)
        worker.handle = server._thread
        worker.kill = lambda: holder["server"].shutdown()  # the chaos hook: the serving loop ends; the watchdog starts the server again
    return server


def _react_hook(tap, folder):
    """The recorded-moves reaction hook of the Reachy body (MOVES-01); the StackChan host never loads the moves package."""
    from maipai_body.moves.react import build_react_hook

    return build_react_hook(tap, folder, os.environ)


def _run_stackchan_service(
    stop_event: threading.Event,
    link: LinkLifecycle | None = None,
    offline: OfflineRungs | None = None,
) -> None:
    host = os.environ.get("MAIPAI_XIAOZHI_HOST", "127.0.0.1")
    try:
        xiaozhi_port = int(os.environ.get("MAIPAI_XIAOZHI_PORT", "8765"))
        avatar_host = os.environ.get("MAIPAI_STACKCHAN_AVATAR_HOST", "127.0.0.1")
        if "MAIPAI_XIAOZHI_HOST" in os.environ and "MAIPAI_STACKCHAN_AVATAR_HOST" not in os.environ:
            avatar_host = host
        avatar_port = int(os.environ.get("MAIPAI_STACKCHAN_AVATAR_PORT", "8766"))
    except ValueError as exc:
        raise ValueError(
            "StackChan listener ports must be TCP port numbers. "
            "Set MAIPAI_XIAOZHI_PORT and MAIPAI_STACKCHAN_AVATAR_PORT to free ports."
        ) from exc
    if link is None or offline is None:
        asyncio.run(
            _serve_stackchan_channels(stop_event, host, xiaozhi_port, avatar_host, avatar_port)
        )
    else:
        asyncio.run(
            _serve_stackchan_channels(
                stop_event, host, xiaozhi_port, avatar_host, avatar_port, link, offline
            )
        )


# FACE-01's own model_id convention (home's lib/biometricPrints.ts's
# KNOWN_MODELS uses the identical string, matching on purpose - a
# print synced from the hub is refused by FaceGallery.add() unless
# this body's own model_id matches what the hub stamped it with).
_FACE_MODEL_ID = "sface-2021dec"

# G4's settings page: the SDK starts a FastAPI server bound to this URL
# only when custom_app_url is set. Port picked from the design-resolver's
# own worked example (2026-09-28) of what a parent would type - no
# stronger convention exists yet across the Reachy Mini app ecosystem.
SETTINGS_APP_URL = "http://127.0.0.1:8042"


def _app_version() -> str | None:
    """The installed `maipai-bot` version, or None when the package is not
    installed (a bare source checkout), which the spec's nullable
    `app_version` says the hub reads as "no version known"."""
    try:
        return importlib.metadata.version("maipai-bot")
    except importlib.metadata.PackageNotFoundError:
        return None


def _data_dir() -> Path:
    default = str(Path.home() / ".local/share/maipai-bot")
    return Path(os.environ.get("MAIPAI_BOT_DATA_DIR") or default)


def _default_pairing_path() -> Path:
    return _data_dir() / "hub-pairing.json"


def _default_models_cache_dir() -> Path:
    return _data_dir() / "models"


_NEUTRAL_POSE = HeadPose()
_NEUTRAL_ANTENNAS = AntennaPositions(left=0.0, right=0.0)
_NEUTRAL_DURATION_S = 1.0
_STOP_POLL_INTERVAL_S = 0.1

_STATE_STARTING = "starting"
_STATE_HOLDING_NEUTRAL = "holding_neutral"
_STATE_BODY_LOST = "body_lost"
_STATE_STOPPED = "stopped"
_STATE_WAITING_FOR_PAIRING = "waiting_for_pairing"
_STATE_CONVERSATION_LOOP = "conversation_loop"


def _sigint_handler(stop_event: threading.Event) -> Callable[[int, object], None]:
    """Return a handler that turns SIGINT into a normal stop_event.set()."""

    def handler(signum: int, frame: object) -> None:
        logger.info("SIGINT received")
        stop_event.set()

    return handler


def _log_state(state: str) -> None:
    logger.info("state: %s", state)


_SLEEP_AFTER_ENV = "MAIPAI_LINK_SLEEP_AFTER_MIN"


def _sleep_after_s(environ: Mapping[str, str] | None = None) -> float:
    """LINK-STATE-01's "after N minutes" setting, from the environment (no
    settings store exists yet). An unreadable or non-positive value falls
    back to the unmeasured default rather than disabling sleep."""
    environ = os.environ if environ is None else environ
    raw = environ.get(_SLEEP_AFTER_ENV)
    if raw is not None:
        try:
            minutes = float(raw)
        except ValueError:
            minutes = math.nan
        if math.isfinite(minutes) and minutes > 0:
            return minutes * 60.0
        logger.warning("ignoring %s=%r; using the default", _SLEEP_AFTER_ENV, raw)
    return DEFAULT_SLEEP_AFTER_MINUTES * 60.0


@dataclass
class LinkStack:
    """The hub link and the offline ladder over it, built together."""

    machine: LinkStateMachine
    link: LinkLifecycle
    offline: OfflineRungs
    supervisor: LinkSupervisor
    announcer: CodeAnnouncer


def _build_link_stack(
    store: PairingStore,
    client: HubLinkClient,
    *,
    discover: DiscoverHub,
    sleep_after_s: float,
    clock: Callable[[], float] = time.monotonic,
    wall_clock: Callable[[], float] = time.time,
    label: str = "Reachy Mini",
    pairing_secret_path: Path | None = None,
    extra_capabilities: list[str] | None = None,
    hub_url: str | None = None,
) -> LinkStack:
    """LINK-STATE-01's wiring. Rung 1's recognizer and router are left
    unwired: the keyword spotter's cost on the Compute Module is UNVERIFIED
    (docs/dev/offline-ladder-unit-checks.md), so a wake during an outage
    gets the acknowledgement animation and the status line until that row is
    recorded and a recognizer is passed in."""
    machine = LinkStateMachine(clock=clock, wall_clock=wall_clock, sleep_after_s=sleep_after_s)
    # G4b: the pairing code is spoken from the offline clips; the speaker is
    # attached once the body is up (`run_paired_body`).
    announcer = CodeAnnouncer()
    link = LinkLifecycle(
        store,
        client,
        discover=discover,
        observer=machine,
        address_walk=True,
        on_code=announcer,
        label=label,
        pairing_secret_path=pairing_secret_path,
        extra_capabilities=extra_capabilities,
        hub_url=hub_url,
    )
    announcer.current_code = lambda: link.state.code
    rung0 = Rung0Cues(machine=machine, clock=clock)
    offline = OfflineRungs(machine=machine, rung0=rung0, retry_link=link.reconnect_once)
    supervisor = LinkSupervisor(
        machine=machine,
        reconnect=link.reconnect_once,
        clock=clock,
        rung0=rung0,
    )
    return LinkStack(
        machine=machine,
        link=link,
        offline=offline,
        supervisor=supervisor,
        announcer=announcer,
    )


def _knock_hooks(
    offline: OfflineRungs | None,
) -> tuple[Callable[[], bool] | None, Callable[[], None] | None]:
    """KNOCK-01's two hooks: the robot sleeps in the ladder's `sleeping` phase,
    and a double knock is an immediate try at the hub (the supervisor's own
    sleeping cadence is minutes). None while there is no ladder."""
    if offline is None:
        return None, None

    def is_asleep() -> bool:
        return offline.machine.phase is LinkPhase.SLEEPING

    def wake() -> None:
        if offline.retry_link is not None:
            offline.retry_link()

    return is_asleep, wake


def _link_state_payload(link: LinkLifecycle, offline: OfflineRungs) -> dict:
    """The settings page's frame: pairing as before, plus the ladder's phase
    and its rung 2 status text (always visible, whatever can be spoken)."""
    state = link.state
    return {
        "paired": state.paired,
        "code": state.code,
        "hub_instance_id": state.hub_instance_id,
        "link": {
            "phase": offline.machine.phase.value,
            "status": offline.status_text(),
            "reply": offline.last_reply.text if offline.last_reply is not None else None,
        },
    }


def _clip_speaker(cache_dir: Path, playback: AudioPlayback) -> OfflineSpeaker | None:
    """The offline clip speaker, or None while the bundle is not released
    or not rendered (G4b): the ladder then cues the body and shows text."""
    try:
        return OfflineSpeaker(ensure_clip_bundle(cache_dir), playback)
    except (AssetUnavailable, ClipsUnavailable, ManifestError) as exc:
        logger.info("offline clips unavailable, the ladder stays silent: %s", exc)
        return None


def _hold_neutral(client: HeadActuator) -> None:
    """goto neutral, then hold - the floor `run_paired_body` starts
    from every time, whether it ends up waiting for pairing or (once
    paired) running the real conversation loop."""
    client.goto(
        pose=_NEUTRAL_POSE,
        antennas=_NEUTRAL_ANTENNAS,
        body_yaw=0.0,
        duration_s=_NEUTRAL_DURATION_S,
    )
    client.hold()


def _start_eyes() -> Indicator:
    """The Reachy Eyes, or a null indicator when they cannot be started. An
    absent board is not an error: the client reports ``connected=False`` and
    keeps looking; the body runs the same without it."""
    try:
        eyes = EyesClient()
        eyes.start()
        return eyes
    except Exception:
        logger.warning("the Reachy Eyes could not be started; running without them", exc_info=True)
        return NullIndicator()


def _attach_motor_safety(client: ReachyMiniClient, stop_event: threading.Event):
    """SETTLE-GATE and MOTOR-RECOVER-01: every head command goes through the gate,
    the watchdog compares what was asked with where the body is, and the process
    leaves the head at a safe rest when it stops (never asleep)."""
    bus = DaemonMotorBus.for_client(client)
    gate = MotorGate(client, bus)

    def offer(names: list[str]) -> None:
        logger.warning("motors %s are stuck; a reboot is offered and needs a yes", names)

    def repaired(record: dict) -> None:
        logger.warning("motor repair record: %s", record)

    health = MotorHealth(
        bus,
        commanded=lambda: gate.commanded,
        present=client.present_state,
        on_offer=offer,
        on_repair=repaired,
        after_step=gate.invalidate_checks,
    )

    def safe_exit_when_stopped() -> None:
        stop_event.wait()
        try:
            why = gate.safe_exit()
            if why:
                logger.info("safe exit skipped motion: %s", why)
        except Exception:
            logger.warning("safe exit failed", exc_info=True)

    service_threads.start(safe_exit_when_stopped, name="motor-safe-exit", stop=stop_event)
    return gate, health


def _attach_eyes(
    client: ReachyMiniClient, stop_event: threading.Event
) -> tuple[LiveCaptureTap, EyesDirector]:
    """EYES-02: the one tap every mic open and frame read goes through, and the
    director that turns its facts and the funnel's shown state into looks.
    Settings and age-band presence have no bot-side transport yet, so the
    tested providers deliberately return defaults and unknown presence."""
    indicator = _start_eyes()
    tap = LiveCaptureTap(client)
    director = EyesDirector(indicator, settings=_eyes_settings, presence=_eyes_presence)
    tap.subscribe(director.on_capture)

    def close_when_stopped() -> None:
        stop_event.wait()
        director.close()
        close = getattr(indicator, "close", None)
        if close is not None:
            close()

    service_threads.start(close_when_stopped, name="eyes-close", stop=stop_event)
    return tap, director


# The latest settings frame values the eyes read (their own keys plus the household
# quiet hours); empty until the hub sends any, which parses to the declared defaults.
_EYES_VALUES: dict[str, object] = {}


def _eyes_settings():
    """The eyes' settings from the hub's settings frame; declared defaults before it."""
    from maipai_body.indicator.settings import parse_settings

    return parse_settings(_EYES_VALUES)


def _eyes_presence():
    """Age-band presence is supplied by Home; unknown is the safe interim value."""
    return None


def _build_conversation_loop(
    client: ReachyMiniClient,
    session_cookie: str,
    base_url: str,
    cache_dir: Path,
    link: LinkLifecycle,
    stop_event: threading.Event,
    *,
    offline: OfflineRungs | None = None,
) -> ConversationLoop:
    """Real construction, once paired: everything G9's `ConversationLoop`
    needs, pointed at the paired hub and the local model cache.

    FACE-01's own gap (`docs/BACKLOG.md`): "real `FiveLandmarkDetector`/
    `SFaceEmbedder`/`FaceGallery` construction wherever the daemon
    actually boots the loop (nothing does yet)" - this is that
    wherever. Print sync starts here because this function creates the
    gallery it updates and already owns the live credentials reader.
    Model downloads (the wake-word front end, the
    wake phrase, SFace) happen here, synchronously, the first time a
    fresh install ever reaches a paired state.
    """
    from maipai_body.link.assets import AssetSync

    asset_sync = [AssetSync(base_url, session_cookie)]
    asset_sync[0].sync(cache_dir)
    hub_credentials = _hub_credentials_reader(link, base_url)
    # From here every consumer gets the tap, never the bare client: it is how
    # the green live cue knows when the voice is leaving for the hub.
    gate, motor_health = _attach_motor_safety(client, stop_event)
    tap, director = _attach_eyes(gate, stop_event)
    wakeword_paths = ensure_wakeword_models(cache_dir)
    wake_engine = OpenWakeWordEngine(
        wake_phrase_model=wakeword_paths[WAKE_PHRASE.file],
        melspec_model=wakeword_paths[MELSPECTROGRAM.file],
        embedding_model=wakeword_paths[EMBEDDING.file],
    )
    audio_playback = AudioPlayback(tap)
    if offline is not None:
        offline.speaker = _clip_speaker(cache_dir, audio_playback)
        if offline.rung0 is not None:
            offline.rung0.attach(speaker=offline.speaker)
    gallery = FaceGallery(model_id=_FACE_MODEL_ID, model_sha256=SFACE.sha256)
    print_sync = PrintSync(gallery, hub_credentials, stop_event)
    # FACE-WATCH-01: the always-on watch, at the default `identify` until the
    # hub's settings_changed says otherwise (enrolled faces only: the gallery
    # holds no print for a guest, and each person's own level still applies).
    thermal_monitor = ThermalMonitor()
    vision_watch = VisionWatch(
        tap,
        FiveLandmarkDetector(),
        ensure_embedder(cache_dir),
        gallery,
        # THERMAL-01: the one governor sets the rate (2 Hz from 70 C), not a second thermometer.
        rate_hz=lambda: thermal_monitor.state.vision_hz,
    )
    is_asleep, wake_from_sleep = _knock_hooks(offline)
    offer_engine = _build_offer_engine(cache_dir, os.environ)
    # FOLLOWUP-01: the directory is the seam the hub's roster fills (age band and
    # `person.robot.follow_up` per person; `RosterPoller` below). Until a fetch
    # fills it, and again when it goes stale, every speaker is the child default
    # and the window stays closed, which is the safe direction.
    people = PeopleDirectory()
    follow_up = FollowUpPolicy(people)
    sleep = _build_sleep_auto(tap, vision_watch, os.environ)
    expression_engine = ExpressionEngine(
        tap,
        REACHY_MINI_PROFILE,
        threaded=True,
        speech_rms_provider=audio_playback.recent_rms,
        state_feed_factory=lambda: tap.state_feed(frequency=50.0),
    )
    loop = ConversationLoop(
        client=tap,
        expression_engine=expression_engine,
        attention=_build_attention(expression_engine, os.environ),
        touch_detector=_build_touch_detector(os.environ),
        sleep_auto=sleep.policy if sleep else None,
        luma_source=sleep.luma if sleep else None,
        quiet_hours=sleep.quiet.active if sleep else None,
        audio_capture=AudioCapture(tap),
        audio_playback=audio_playback,
        wake_scorer=WakeScorer(wake_engine, tap),
        stt_client=SttStreamClient(base_url, session_cookie),
        turn_client=TurnClient(base_url, session_cookie),
        tts_client=TtsPlaybackClient(base_url, session_cookie, audio_playback),
        hub_credentials=hub_credentials,
        vision_watch=vision_watch,
        follow_up=follow_up,
        offline=offline,
        # MOVES-01: None unless MAIPAI_BOT_REACT_MOVES is set.
        react_hook=_react_hook(tap, cache_dir / "moves"),
        carry_gravity_compensation=REACHY_MINI_PROFILE.carry_gravity_compensation,
        capture_scope=tap.sending_to_hub,
        motor_health=motor_health,
        thermal=thermal_monitor,
        is_asleep=is_asleep,
        wake_from_sleep=wake_from_sleep,
        offer_engine=offer_engine,
        unmute_listener=_build_unmute_listener(cache_dir, os.environ),
        band_of=people.band_of,
        presence_entries=lambda: presence_entries_from(vision_watch.current(), people.band_of),
        # MOVE-SCENE-05: after a set down the loop runs this once on its own worker: one fresh
        # detection cycle of the watch (the tracks were just dropped). Reachy has no battery
        # and no screen, so the SELF-SCENE-02 ladder stays off (`battery_status` is omitted).
        face_search=vision_watch.step,
        power_warn_at=lambda: power_warn_at(_EYES_VALUES),
    )
    loop.subscribe_view(director.on_view)
    alarm = _build_alarm_controller(loop, audio_playback, offline, people, lambda m: _send(m))
    loop.set_alarm_word_handler(alarm.on_spoken)
    service_threads.start(_alarm_backstop, args=(alarm, stop_event), name="alarm-backstop", stop=stop_event)
    threading.Thread(target=print_sync.run, name="face-print-sync", daemon=True).start()
    # FOLLOWUP-01: the hub's roster fills `people` (refresh now, every 30 s, and
    # right after a command-channel drop); a stale roster clears to unknown.
    roster_poller = RosterPoller(people, hub_credentials, stop_event)
    service_threads.start(roster_poller.run, name="roster-poller", stop=stop_event)

    from maipai_body.link.channel import CommandChannel

    def set_muted(payload: dict) -> dict:
        muted = payload.get("muted")
        if not isinstance(muted, bool):
            raise ValueError("mute command requires a boolean muted field")
        loop.set_muted(muted)
        return {"muted": muted}

    def refresh_assets(_payload: dict) -> None:
        cookie, current_url = hub_credentials()
        refreshed = AssetSync(current_url, cookie)
        refreshed.on_asset_changed(cache_dir)
        asset_sync[0] = refreshed

    def command_credentials() -> tuple[str, str]:
        cookie, current_url = hub_credentials()
        return current_url, cookie

    def apply_settings(payload: dict) -> None:
        values = payload.get("values")
        level = values.get("robot.camera.watch_level") if isinstance(values, dict) else None
        if level in ("off", "presence", "identify"):
            loop.set_watch_level(level)
        if isinstance(values, dict):
            _EYES_VALUES.update(values)
            alarm.apply_settings(values)
        if sleep is not None and isinstance(values, dict):
            sleep.apply_settings(values)
        seconds = values.get("robot.follow_up.seconds") if isinstance(values, dict) else None
        if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
            follow_up.set_seconds(seconds)

    command_channel = CommandChannel(
        base_url,
        session_cookie,
        credentials=command_credentials,
        settings_handler=apply_settings,
        time_handler=getattr(getattr(link.hub_client, "clock_sync", None), "observe_iso", None),
        on_drop=link.channel_lost,
        handlers={
            "mute": lambda _payload: set_muted({"muted": True}),
            "unmute": lambda _payload: set_muted({"muted": False}),
            "asset_changed": refresh_assets,
            "motor_reboot": motor_reboot_handler(loop),
            "offer": loop.offer.receive,
            "alarm": alarm.handle_command,
        },
    )
    loop.bind_offer_frames(command_channel.send_frame)

    def _send(message: dict) -> bool:
        return command_channel.send_frame(message)

    from maipai_body.vision.live_view import LiveViewStreamer

    def post_live_frame(view_id: str, jpeg: bytes) -> int:
        import requests

        cookie, current_url = hub_credentials()
        response = requests.post(
            f"{current_url.rstrip('/')}/api/devices/me/stream/{view_id}",
            data=jpeg,
            headers={"Cookie": f"session={cookie}", "Content-Type": "image/jpeg"},
            timeout=(3, 5),
        )
        return response.status_code

    live_view = LiveViewStreamer(
        camera=tap,
        post_frame=post_live_frame,
        refusal=loop.live_view_refusal,
        connected=lambda: command_channel.connected,
    )
    command_channel.handlers["live_view_start"] = live_view.start
    command_channel.handlers["live_view_stop"] = live_view.stop
    command_channel.add_drop_listener(live_view.on_channel_drop)
    command_channel.add_drop_listener(roster_poller.poke)
    threading.Thread(
        target=command_channel.run,
        args=(stop_event,),
        name="robot-command-channel",
        daemon=True,
    ).start()
    return loop


def motor_reboot_handler(loop: Any) -> Callable[[dict], dict]:
    """The hub's `motor_reboot` (spec-v0.1.151): sent only after an adult said yes on the
    Devices card, and it reboots only the motors named. The ack carries the outcome and
    the next state frame shows what is still latched."""

    def handle(payload: dict) -> dict:
        motors = payload.get("motors")
        if (
            not isinstance(motors, list)
            or not motors
            or not all(isinstance(name, str) and name for name in motors)
        ):
            raise ValueError("motor_reboot requires a non-empty motors list of names")
        return loop.reboot_motors(motors)

    return handle


def _build_attention(engine: ExpressionEngine, env: Mapping[str, str]) -> object | None:
    """S-EXPR-04: our own gaze and idle layers instead of the daemon's tracker.
    Off unless MAIPAI_BOT_ATTENTION=1: every number in it is an UNMEASURED design
    default until the unit rows (M-R2) confirm them, so the daemon tracker stays
    the default."""
    if env.get("MAIPAI_BOT_ATTENTION") != "1":
        return None
    from maipai_body.presence.attention import Attention

    return Attention(engine, clock=time.monotonic)


@dataclass
class _SleepAuto:
    """SLEEP-AUTO-01's pieces, so `apply_settings` can reach the live policy."""

    policy: object
    luma: Callable[[], float | None]
    quiet: object

    def apply_settings(self, values: Mapping[str, object]) -> None:
        self.quiet.apply(values)  # type: ignore[attr-defined]
        auto = values.get("robot.sleep.auto")
        if isinstance(auto, bool):
            self.policy.auto_enabled = auto  # type: ignore[attr-defined]


def _build_sleep_auto(camera: object, vision_watch: VisionWatch, env: Mapping[str, str]):
    """SLEEP-AUTO-01: dark-and-quiet and quiet-hours sleep. Off unless
    MAIPAI_BOT_SLEEP_AUTO=1 (its thresholds are UNMEASURED). `robot.sleep.auto` and
    `household.quiet_hours.from`/`.to` are registry keys since spec-v0.1.151; the
    registry default for the first is on, so the policy starts enabled and a
    `settings_changed` only ever turns it off or back on."""
    if env.get("MAIPAI_BOT_SLEEP_AUTO") != "1":
        return None
    from maipai_body.presence.sleep_auto import QuietHours, SleepAutoPolicy, luma_reader

    return _SleepAuto(
        policy=SleepAutoPolicy(auto_enabled=True),
        luma=luma_reader(camera, level=lambda: vision_watch.device_level),
        quiet=QuietHours(),
    )


def _build_touch_detector(env: Mapping[str, str]) -> object | None:
    """TOUCH-01: an antenna push acknowledges, or wakes a sleeping robot. Off unless
    MAIPAI_BOT_TOUCH=1: the thresholds are UNMEASURED until runbook rows T0 to T4."""
    if env.get("MAIPAI_BOT_TOUCH") != "1":
        return None
    from maipai_body.presence.touch import AntennaTouchDetector

    return AntennaTouchDetector()


def _build_offer_engine(cache_dir: Path, env) -> object | None:
    """OFFER-01: the local spotter for the offer window, or None (offers are then
    refused with `no_spotter`). Off unless MAIPAI_BOT_OFFER_SPOTTER=1: the offer
    phrases' token file is not yet checked against the pinned model."""
    if env.get("MAIPAI_BOT_OFFER_SPOTTER") != "1":
        return None
    try:
        from maipai_body.speech.kws import (
            OFFER_KEYWORDS_FILE,
            SherpaKeywordEngine,
            ensure_kws_model,
        )

        return SherpaKeywordEngine(ensure_kws_model(cache_dir), keywords_file=OFFER_KEYWORDS_FILE)
    except Exception:
        logger.warning("offer spotter unavailable; offers will be refused", exc_info=True)
        return None


def _build_unmute_listener(cache_dir: Path, env) -> object | None:
    """MUTE-LOCAL-01: the on-robot "listen again" spotter, or None (a hub mute can then
    only be lifted by the hub). Off unless MAIPAI_BOT_UNMUTE_SPOTTER=1: the phrase's
    token file is hand-tokenised and its CPU row is not measured."""
    if env.get("MAIPAI_BOT_UNMUTE_SPOTTER") != "1":
        return None
    try:
        from maipai_body.speech.kws import (
            UNMUTE_KEYWORDS_FILE,
            SherpaKeywordEngine,
            UnmuteListener,
            ensure_kws_model,
        )

        engine = SherpaKeywordEngine(
            ensure_kws_model(cache_dir), keywords_file=UNMUTE_KEYWORDS_FILE
        )
        return UnmuteListener(engine)
    except Exception:
        logger.warning("unmute spotter unavailable; only the hub can unmute", exc_info=True)
        return None


class _AlarmSpeaker:
    """The alarm's `AlarmPlayer`: a fixed chime and bundle clips through the
    robot's own playback. It never synthesises; no bundle means chime only."""

    def __init__(self, playback: AudioPlayback, offline: OfflineRungs | None) -> None:
        self._playback = playback
        self._offline = offline

    def _speaker(self):
        return None if self._offline is None else self._offline.speaker

    def chime(self) -> None:
        rate = self._playback.output_samplerate()
        if rate:
            self._playback.push(chime_samples(rate))

    def clips(self, clip_ids) -> bool:
        speaker = self._speaker()
        if speaker is None or not speaker.can_say(list(clip_ids)):
            return False
        return bool(speaker.say(list(clip_ids)))

    def stop(self) -> None:
        self._playback.flush()


def _build_alarm_controller(
    loop: ConversationLoop,
    playback: AudioPlayback,
    offline: OfflineRungs | None,
    people: PeopleDirectory,
    send: Callable[[dict], bool],
) -> AlarmController:
    """ALARM-PLAY-01. No daemon volume seam exists on this body yet, so the
    floor is applied only where a `Volume` is injected (BACKLOG, open)."""
    from maipai_body.speaker_evidence import effective_band

    def bundle():
        speaker = None if offline is None else offline.speaker
        return getattr(speaker, "bundle", None)

    def has(clip_id: str) -> bool:
        b = bundle()
        return b is not None and b.has(clip_id)

    def resolve(kind, area):
        b = bundle()
        return [] if b is None else alarm_clip_ids(b.manifest, has, kind, area)

    return AlarmController(
        player=_AlarmSpeaker(playback, offline),
        present=loop.set_safety_alarm,
        resolve_clips=resolve,
        child_clips=lambda: alarm_child_clip_ids(has),
        send_action=send,
        audience=lambda: loop.speaker_snapshot()[1],
        is_child=lambda entry: effective_band(entry, people.band_of)[0] == "child",
        evidence=lambda: loop.speaker_snapshot()[0],
    )


def _alarm_backstop(alarm: AlarmController, stop_event: threading.Event) -> None:
    while not stop_event.wait(1.0):
        try:
            alarm.tick()
        except Exception:
            logger.warning("alarm backstop failed", exc_info=True)


def _detector_ready(vision: Any) -> bool:
    """True once the face model is loaded, so "I see nobody" is a real answer."""
    ready = getattr(getattr(vision, "detector", None), "ready", False)
    return bool(ready() if callable(ready) else ready)


def _wire_orientation(voice: Any, behavior: Any, bridge: Any, night: Any, power: Any) -> None:
    """Pose faces, lines, screen rotation and the motion hold for the unit's orientation events."""
    from maipai_body.bodies.stackchan.orientation import (
        SCREEN_ROTATION_ENABLED,
        OrientationReactions,
    )
    from maipai_body.hal.errors import NotSupported

    def rotate(degrees: int) -> None:
        if not SCREEN_ROTATION_ENABLED:
            return
        try:
            voice.robot.client._call("self.screen.set_rotation", {"degrees": degrees})
        except Exception:
            behavior._warn_limited("rotation", "StackChan screen rotation failed")

    def asleep() -> bool:
        return behavior._rest.stage != "awake"

    orientation = OrientationReactions(
        face=lambda expression: behavior.show_face(expression, while_listening=False),
        say=bridge.speak_reaction,
        rotate=rotate,
        hold_motion=power.set_orientation_hold,
        quiet=lambda: ("night mode is on" if night.night else "") or ("asleep" if asleep() else ""),
        busy=behavior.reaction_blocked,
        resting=lambda: behavior._rest.stage != "awake",
        head_pitch_deg=lambda: behavior._tracker.pose[1],
        head_moved_ago=behavior.head_moved_ago,
        missed=getattr(getattr(behavior, "missed_log", None), "note", None),
        on_set_down=getattr(behavior, "search_after_set_down", None),
    )
    behavior.orientation = orientation
    night.sensors_blocked = orientation.sensors_untrusted
    # The unit's own reading of its orientation (firmware ML01) counts as "not upright" too, so host and unit agree.
    behavior.pose_held = lambda: orientation.pose != "upright" or _unit_not_upright(behavior)

    def tick() -> None:
        orientation.tick()

    behavior.orientation_tick = tick

    keep_awake_at = [float("-inf")]
    unsupported = [False]

    def keep_awake() -> None:
        """While the hub link is up, restart the unit's idle timers once a minute (patch 074)."""
        now = time.monotonic()
        if unsupported[0] or not voice._sessions or now - keep_awake_at[0] < KEEP_AWAKE_S:
            return
        keep_awake_at[0] = now
        try:
            voice.robot.client._call("self.power.keep_awake", {})
        except NotSupported:
            unsupported[0] = True  # firmware before patch 074: nothing to keep awake
            logger.info("StackChan firmware has no keep_awake tool; idle shutdown stays as flashed")

    behavior.keep_awake_tick = keep_awake
    voice.session_listeners.append(lambda _device_id: orientation.reassert())
    bridge.on_turn_end = orientation.on_turn_end


def _remote_forced_off() -> bool:
    from maipai_body.settings_page import _remote_forced_off as forced

    return forced()


def _configured_hub_url() -> str:
    """The hub address: MAIPAI_HUB_URL, else `[home] url` in robot.toml (StackChan only)."""
    url = os.environ.get("MAIPAI_HUB_URL", "").strip()
    if url or not _stackchan_selected():
        return url
    try:
        from maipai_body.config import load_config

        return load_config().home.url.strip()
    except Exception:
        return ""


def _start_wake_word_maker(backend) -> None:
    """The wake word maker's routes, only when it is switched on (nothing is imported otherwise)."""
    try:
        from maipai_body.config import load_config

        cfg = load_config().packages.wake_word_maker
    except Exception:
        return
    if not cfg.enabled:
        return
    from pathlib import Path

    from maipai_body.bodies.stackchan.xiaozhi.pairing import default_pairing_path
    from maipai_packages.wake_word_maker import WakeStore, WakeWordMaker

    folder = Path(cfg.folder) if cfg.folder else default_pairing_path().parent / "wakeword"
    backend.wakeword = WakeWordMaker(WakeStore(folder))


def _pantry_window(voice) -> tuple[float, float]:
    """The refill window: the owner's quiet hours when they are set, else 02:00 to 05:00 (decision 35)."""
    try:
        start, end = voice.quiet_hours.minutes()
    except Exception:
        start = end = -1
    return (start / 60, end / 60) if start >= 0 else (2, 5)


def _leave_hosted_units(voice) -> int:
    """The person left the hosted route on the Brain page: each connected unit that has the tool erases its vendor link."""
    from maipai_body import brain_route

    probe = getattr(getattr(voice, "polish", None), "probe", None)
    return brain_route.leave_hosted(
        list(voice._sessions),
        lambda unit: probe is not None and probe.has(unit, "brain_route") is True,
        lambda unit, args: voice.robot.client.for_unit(unit)._call(brain_route.TOOL, args),
    )


def _start_pantry(backend, voice=None) -> None:
    """The content pantry's routes and its model, only when it is switched on (nothing is imported otherwise)."""
    try:
        from maipai_body.config import load_config

        config = load_config()
        cfg = config.packages.pantry
    except Exception:
        return
    if not cfg.enabled:
        return
    from pathlib import Path

    from maipai_body.bodies.stackchan.xiaozhi.pairing import default_pairing_path
    from maipai_packages.pantry import Pantry
    from maipai_packages.pantry.model import chat_function

    folder = Path(cfg.folder) if cfg.folder else default_pairing_path().parent / "pantry"
    try:
        ask = chat_function(config.llm.url, getattr(config.llm, "model", "") or "", getattr(config.llm, "api_key_env", "") or "")
    except ValueError:
        ask = None  # no model yet: the page shows the library, and Refill says to choose a brain
    backend.pantry = Pantry(folder, ask, daily_cap=cfg.daily_cap, languages=tuple(cfg.languages), adult_humor=cfg.adult_humor)
    if voice is None:
        return
    # Riddles and trivia go on from the library when the model cannot be reached in the middle of a game (talk_fallback.py).
    from maipai_packages.pantry.talk_fallback import PantryTalk

    game_bridge = getattr(voice, "gate_bridge", None)
    if game_bridge is not None:
        game_bridge.talk_fallback = PantryTalk(backend.pantry.library, adult_humor=lambda: bool(cfg.adult_humor))
    # Every five minutes, for each connected unit: take its heard list, send denials, and refill what the rule says (docs/design/content-pantry.md section 5).
    from maipai_packages.pantry.sync import UnitState, run_unit
    from maipai_packages.pantry.unit_link import ToolUnitLink

    from maipai_body.asset_transport import AssetTransport

    call_unit = lambda unit, tool, args: voice.robot.client.for_unit(unit)._call(tool, args)  # noqa: E731
    transport = AssetTransport(call_unit)

    def install_shelf(unit: str, kind: str, language: str, body: bytes) -> bool:
        result = transport.install_pantry_shelf(unit, kind, language, body, record_count=int.from_bytes(body[8:10], "little"))
        if not result.ok:
            logger.info("pantry: the %s %s shelf was not installed: %s", language, kind, result.message)
        return result.ok

    link = ToolUnitLink(call_unit, install_shelf)
    done_tonight: set[tuple[str, str]] = set()
    pantry_stop = threading.Event()

    def _pantry_loop() -> None:
        while not pantry_stop.wait(300.0):
            for unit in list(voice._sessions):
                try:
                    idle = voice._turns_running == 0 and unit not in voice._speaking
                    run_unit(backend.pantry.library, link, unit, UnitState(idle=idle), window=_pantry_window(voice), nightly_done=done_tonight)
                except Exception:
                    logger.debug("pantry sync of one unit failed", exc_info=True)

    service_threads.start(_pantry_loop, name="pantry-sync", stop=pantry_stop)


def _start_coding_companion(backend, voice) -> None:
    """The coding companion's endpoint, only when it is switched on (nothing is imported or opened otherwise)."""
    try:
        from maipai_body.config import load_config

        cfg = load_config().packages.coding_companion
    except Exception:
        return
    if not cfg.enabled:
        return
    from maipai_packages.coding_companion import shared_status
    from maipai_packages.coding_companion.server import (
        AgentAuth,
        AgentServer,
        default_token_path,
        make_presenter,
    )

    shared_status().show_request_text = cfg.show_request_text
    try:
        server = AgentServer(
            shared_status(),
            AgentAuth(default_token_path()),
            make_presenter(backend.polish.bus, lambda: list(voice.connected_devices())),
            cfg.port,
        )
    except OSError:
        logger.warning("coding companion port %d is in use; set another port under [packages.coding_companion]", cfg.port)
        return
    server.start()
    logger.info("coding companion endpoint on 127.0.0.1:%d", server.port)


def _lan_address() -> str:
    """This computer's address on the local network (the one a phone on the same Wi-Fi can reach)."""
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("192.0.2.1", 9))  # no packet is sent: this only picks the outgoing interface
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def _update_check(key, builds, installed_build):
    """The image check of the host's update path. A 120-byte package carries a build number that has to be above the installed build and the
    highest build this host has seen installed. The number is only noted as pending here; ``accepted`` (called when the unit reports the
    install done) records it, so an install that failed can be tried again with the same build (review fix R2-23)."""
    from maipai_body.bodies.stackchan.firmware.flash_manifest import verify_detached
    from maipai_body.bodies.stackchan.firmware.update_header import PACKAGE_LEN, verify_package

    pending: list[int | None] = [None]

    def check(image: bytes, signature: bytes) -> bool:
        if len(signature) != PACKAGE_LEN:
            return verify_detached(image, signature, key)
        installed = installed_build()
        known = builds.highest()
        floor = max([n for n in (installed if isinstance(installed, int) else None, known) if n is not None], default=None)
        verdict = verify_package(signature, image, key, installed_build=floor)
        if verdict.ok:
            pending[0] = verdict.header["build_number"]
        return verdict.ok

    def accepted() -> None:
        if pending[0] is not None:
            builds.record(pending[0])
            pending[0] = None

    check.accepted = accepted  # type: ignore[attr-defined]
    return check


class _UpdateBuilds:
    """The highest update build number this host has accepted, kept in a small file (anti-rollback on the host's side)."""

    def __init__(self, path) -> None:
        self._path = path

    def highest(self) -> int | None:
        try:
            value = json.loads(self._path.read_text()).get("highest")
        except (OSError, ValueError):
            return None
        return value if isinstance(value, int) and value > 0 else None

    def record(self, build_number: int) -> None:
        if (self.highest() or 0) < build_number:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"highest": build_number}) + "\n")


def _note_child(voice, payload: dict) -> dict:
    """Home says a child is (or is no longer) near a unit: the command bus limits the model's sounds."""
    bridge = getattr(voice, "gate_bridge", None)
    if bridge is None:
        return {"ok": False}
    device_id = str(payload.get("device_id") or "")
    targets = [device_id] if device_id else list(getattr(voice, "connected_devices", lambda: [])())
    for target in targets:
        bridge.note_child_present(target, bool(payload.get("present")), float(payload.get("seconds") or 300))
    return {"ok": True}


def _no_hub_configured() -> bool:
    """No Home to talk to: no hub URL is set and the owner did not choose brain "home".

    A host that is not told about a hub never browses the network for one and never
    pairs with whichever hub answers."""
    if _configured_hub_url():
        return False
    if os.environ.get("MAIPAI_HUB_HOST") == "1":
        return True
    if not _stackchan_selected():
        return False
    try:
        from maipai_body.config import load_config

        return load_config().brain != "home"
    except Exception:
        return True


def _start_robot_checkin(voice: Any, behavior: Any, link: LinkLifecycle, stop_event: Any) -> None:
    """Report the connected StackChan to the hub: address, firmware, memory, boot reason."""
    from maipai_body.link.checkin import (
        RobotCheckin,
        UnitFacts,
        build_payload,
        link_class_line,
    )

    facts = UnitFacts()
    behavior.unit_facts = facts
    connected = threading.Event()
    voice.session_listeners.append(lambda _device_id: connected.set())
    wifi_cache: list[Any] = [float("-inf"), None]
    wifi_cache_seq: list[int] = [-1]
    wifi_lock = threading.Lock()

    def collect() -> dict[str, Any]:
        sessions = list(voice._sessions)
        device_id = sessions[0] if sessions else None
        address, since = voice._session_info.get(device_id, (None, None))
        status: dict[str, Any] = {}
        if device_id is not None:
            try:
                status = {
                    "network": (voice.robot.client.get_device_status() or {}).get("network"),
                    "battery": voice.robot.client.get_battery_status(),
                }
                battery = status["battery"]
                status["battery"] = {
                    "level": battery.get("percent"),
                    "charging": battery.get("charging"),
                }
            except Exception:
                logger.debug("robot check-in could not read the unit's status", exc_info=True)
        wifi_saved = None
        wifi_saved_at = None
        wifi_last = None
        wifi_list = getattr(behavior, "wifi_list", None)
        if wifi_list is not None:
            with wifi_lock:
                now_mono = time.monotonic()
                # Read the unit's list again every check-in (about a minute) and at once after any
                # add, forget or switch: Jesse could not see whether an add had worked (2026-11-14).
                if now_mono - wifi_cache[0] >= 55 or wifi_cache_seq[0] != wifi_list.change_seq:
                    # saved() retains its last readable list on failure; an initial failure is
                    # represented as absent so Home can distinguish unknown from an empty list.
                    try:
                        queried = wifi_list.saved()
                        wifi_cache[:] = [now_mono, queried if wifi_list.has_saved else None]
                    except Exception:
                        wifi_cache[:] = [now_mono, None]
                    wifi_cache_seq[0] = wifi_list.change_seq
                wifi_saved = wifi_cache[1]
                wifi_saved_at = wifi_list.saved_at
                wifi_last = wifi_list.last
        payload = build_payload(
            device_id=device_id,
            address=address,
            connected_since=since,
            facts=facts.snapshot(),
            orientation=getattr(behavior.orientation, "pose", None),
            status=status,
            bot_version=_app_version(),
            now=time.time(),
            timers_active=behavior.timers.active_count() if behavior.timers is not None else None,
            updating=getattr(voice, "firmware_update_status", (None, None))[0],
            update_progress=getattr(voice, "firmware_update_status", (None, None))[1],
            wifi_saved=wifi_saved,
            link_encrypted=UNIT_LINK_ENCRYPTED,
            wifi_saved_at=wifi_saved_at,
            wifi_last=wifi_last,
        )
        # Log how the link looks to Home when it changes (a class, never an address).
        line = link_class_line(payload, facts.snapshot())
        if link_logged[0] != line:
            link_logged[0] = line
            from maipai_body.bodies.stackchan.activity import log_activity

            log_activity(line)
        return payload

    link_logged: list[str | None] = [None]
    if _no_hub_configured():
        logger.info("no hub URL is set: the hub check-in is off (the unit's facts stay local)")
        return
    reporter = RobotCheckin(
        _hub_credentials_reader(link, ""), stop_event, collect, facts, connected
    )
    service_threads.start(reporter.run, name="robot-checkin", stop=stop_event)


def _hub_credentials_reader(link: LinkLifecycle, base_url: str) -> Callable[[], tuple[str, str]]:
    """Build a live credentials reader that retains the last good URL."""
    last_known_good_url = [base_url]

    def read() -> tuple[str, str]:
        try:
            pairing = link.pairing_store.load()
        except Exception:
            logger.warning("failed to read hub pairing during credential refresh", exc_info=True)
        else:
            if pairing is not None:
                last_known_good_url[0] = pairing.base_url
        # The address that last answered wins over the stored one: a tailnet
        # answer is not persisted (the LAN address stays the pairing) but the
        # turn clients must still reach the hub where it answered.
        answered = getattr(link.hub_client, "active_base_url", None)
        return link.hub_client.session_cookie or "", answered or last_known_good_url[0]

    return read


def _load_yunet_model(link: LinkLifecycle | None) -> Path:
    """The verified YuNet file: from the local model cache, else synced from the paired hub."""
    from maipai_body.vision.models import YUNET

    return _load_pinned_model(link, YUNET)


def _load_pinned_model(link: LinkLifecycle | None, asset: Any) -> Path:
    """A verified pinned model file: from the local cache, else synced from the paired hub."""
    from maipai_body.link.assets import AssetSync
    from maipai_body.model_assets import AssetUnavailable, ensure_asset

    cache = _default_models_cache_dir()
    try:
        return ensure_asset(asset, cache)  # already synced (or the fetcher is configured)
    except AssetUnavailable:
        pass
    if link is None:
        raise AssetUnavailable(f"{asset.file} is not synced and the robot is not paired with Home")
    url, cookie = _command_credentials(link)()
    if not url or not cookie:
        raise AssetUnavailable(f"{asset.file} is not synced and Home has not answered yet")
    sync = AssetSync(url, cookie, refresh_credentials=_command_credentials(link))
    return sync.ensure(asset, cache)


def _effective_idle_level(level: str) -> str:
    """The idle level acted on: Home's default "calm" counts as "still"."""
    return "still" if level == "calm" else level


def _command_credentials(link: LinkLifecycle) -> Callable[[], tuple[str, str]]:
    """The command channel's reader: ``(base_url, session_cookie)``, in that order.

    ``_hub_credentials_reader`` answers ``(cookie, url)``; the channel unpacks the other way, so
    the cookie was used as the URL and the channel failed with a ValueError every 30 s.
    """
    read = _hub_credentials_reader(link, "")

    def credentials() -> tuple[str, str]:
        cookie, url = read()
        return url, cookie

    return credentials


def _has_stored_pairing(link: LinkLifecycle) -> bool:
    try:
        return link.pairing_store.load() is not None
    except Exception:
        logger.warning("could not read the stored pairing at boot", exc_info=True)
        return False


def _clock_synced(link: object) -> bool:
    """ROBOT-TIME-01: false until the first contact with the hub since boot."""
    sync = getattr(getattr(link, "hub_client", None), "clock_sync", None)
    return bool(getattr(sync, "synced", False)) if isinstance(sync, ClockSync) else False


def run_paired_body(
    client: ReachyMiniClient,
    link: LinkLifecycle,
    stop_event: threading.Event,
    *,
    cache_dir: Path,
    offline: OfflineRungs | None = None,
    supervisor: LinkSupervisor | None = None,
    announcer: CodeAnnouncer | None = None,
) -> None:
    """The real boot path: hold neutral until G4's link reports paired,
    then hand off to `ConversationLoop` for the rest of the process's
    life. Still holds neutral and honors `stop_event`/SIGINT within one
    second if pairing never happens - RM-03's own original scaffold
    contract, unchanged.

    Hub-facing speech clients are refreshed at turn boundaries from
    the link's live session cookie and pairing URL, so an in-flight
    turn keeps its original clients while the next turn picks up a
    rotated session.
    """
    _log_state(_STATE_STARTING)
    try:
        _hold_neutral(client)
        _log_state(_STATE_HOLDING_NEUTRAL)
        _log_state(_STATE_WAITING_FOR_PAIRING)
        if announcer is not None:
            # An unpaired robot has no hub to synthesize the code with: it
            # says it from the clips, so the speaker exists before pairing.
            threading.Thread(
                target=lambda: announcer.attach(_clip_speaker(cache_dir, AudioPlayback(client))),
                name="pairing-code-speaker",
                daemon=True,
            ).start()
        # A body that was paired before does not wait for the hub: the ladder
        # and the wake behavior run from boot, whether or not the first
        # redeem has succeeded (LINK-STATE-01). A body never paired still
        # waits for pairing, as before.
        boot_offline = offline is not None and _has_stored_pairing(link)
        paired = False
        while not stop_event.is_set():
            if link.state.paired or boot_offline:
                paired = True
                break
            stop_event.wait(_STOP_POLL_INTERVAL_S)
        if not paired:
            return

        if boot_offline:
            # The machine starts connected; with a stored pairing and no
            # redeem yet that is not true, so the outage state, the supervisor's
            # retries and the wake's offline path start now, not when the first
            # redeem finally fails (its walk can take many seconds).
            offline.machine.booted_without_contact("the hub has not answered since power-on")

        if supervisor is not None:
            threading.Thread(
                target=supervisor.run, args=(stop_event,), name="link-supervisor", daemon=True
            ).start()

        pairing = link.pairing_store.load()
        if pairing is None:
            # Paired per LinkLifecycle's in-memory state but the file
            # it just wrote is unreadable - report as body_lost's own
            # sibling rather than crash the process on a torn write.
            logger.error("link reports paired but the pairing record could not be read")
            return
        session_cookie = link.hub_client.session_cookie
        if not session_cookie and boot_offline:
            # The hub has not answered yet. The loop re-reads the live cookie
            # at its first turn boundary, so an empty one here is never used.
            session_cookie = ""
        elif not session_cookie:
            # Same shape as the unreadable-pairing-record case above: a
            # code review (2026-09-28) caught this silently falling
            # back to "" and building every hub client anyway, which
            # would only surface as an opaque 401 deep inside the first
            # real turn instead of a clear error right here.
            logger.error("link reports paired but has no session cookie")
            return

        hub_credentials = _hub_credentials_reader(link, pairing.base_url)
        loop_ready = threading.Event()
        loop_result: list[ConversationLoop] = []

        def state_snapshot() -> dict[str, object]:
            # `daemon_version` is the vendor SDK's version; `app_version`
            # is this app's own (`maipai-bot`), the one the hub compares
            # to a getmaipai/bot release (ROBOT-STATE-SPEC-02, G10-VERSION).
            versions = {
                "daemon_version": getattr(reachy_mini, "__version__", None),
                "app_version": _app_version(),
            }
            if not loop_ready.is_set() or not loop_result:
                return {
                    "activity": "starting",
                    "muted": False,
                    "tracking": False,
                    "clock_synced": _clock_synced(link),
                    "on_battery": None,
                    "battery_level": None,
                    **versions,
                }
            # SELF-SCENE-02: the loop's own battery fields (battery_level, charging,
            # low_power, on_battery) win over the unknown defaults when it reports them.
            return {
                "on_battery": None,
                "battery_level": None,
                **loop_result[0].snapshot(),
                "clock_synced": _clock_synced(link),
                **versions,
            }

        state_change_event = threading.Event()
        state_change_event.set()
        reporter = StateReporter(
            hub_credentials,
            stop_event,
            state_snapshot,
            state_change_event,
        )
        service_threads.start(reporter.run, name="robot-state-reporter", stop=stop_event)

        build_result: list[ConversationLoop | Exception] = []

        def build_loop() -> None:
            try:
                # Only passed when there is a ladder, so a body without one
                # builds the loop exactly as before.
                extra = {"offline": offline} if offline is not None else {}
                loop = _build_conversation_loop(
                    client, session_cookie, pairing.base_url, cache_dir, link, stop_event, **extra
                )
                loop_result.append(loop)
                loop_ready.set()
                state_change_event.set()
                build_result.append(loop)
            except Exception as exc:
                build_result.append(exc)

        try:
            build_thread = threading.Thread(
                target=build_loop, name="conversation-loop-build", daemon=True
            )
            build_thread.start()
            while build_thread.is_alive():
                if stop_event.wait(_STOP_POLL_INTERVAL_S):
                    logger.info(
                        "stop requested during model download; abandoning conversation loop build"
                    )
                    return
            build_thread.join()
            if isinstance(build_result[0], Exception):
                raise build_result[0]
            loop = build_result[0]
        except Exception:
            # A code review (2026-09-28) caught this uncaught: a
            # model-download failure (no network, GitHub briefly
            # unreachable, a corrupted partial download tripping
            # model_assets.py's checksum check) is a plain RuntimeError
            # subclass, not BodyLost, so it used to propagate out of
            # this function and crash the whole daemon process - on
            # every restart, for a fresh install with a flaky network,
            # until someone noticed and intervened by hand. Logged and
            # treated as "couldn't reach conversational state," the
            # same as the two branches above, not a crash.
            logger.exception("failed to build the conversation loop")
            return
        _log_state(_STATE_CONVERSATION_LOOP)
        loop.run(stop_event)
    except BodyLost:
        _log_state(_STATE_BODY_LOST)
    finally:
        _log_state(_STATE_STOPPED)
        service_threads.stop_all(timeout=1.0)


def _alarm_control(behavior):
    """Voice alarms and timers, run through the unit's own timers (None when the timer service is off)."""
    from maipai_body.bodies.stackchan.alarm_commands import AlarmControl

    if getattr(behavior, "timers", None) is None:
        return None
    return _UnitAlarms(behavior, AlarmControl)


class _UnitAlarms:
    """Voice alarms and timers for several units: each unit's own AlarmControl over that unit's own timer service, so "cancel my alarm" on one unit
    never sees another unit's alarm and an alarm set on a unit rings on that unit (docs/plan/per-unit-behavior.md, step 5)."""

    def __init__(self, behavior, control_class) -> None:
        self._behavior, self._class = behavior, control_class
        self._by_unit: dict[str, Any] = {}

    def _for(self):
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        unit = ACTIVE_UNIT.get() or ""
        control = self._by_unit.get(unit)
        if control is None:
            timers_for = getattr(self._behavior, "timers_for", None)
            timers = timers_for(unit) if (timers_for is not None and unit) else getattr(self._behavior, "timers", None)
            if timers is None:
                return None
            control = self._by_unit[unit] = self._class(timers)
        return control

    def parse(self, text: str):
        control = self._for()
        return control.parse(text) if control is not None else None

    def run(self, command) -> str:
        control = self._for()
        if control is None:
            return "I could not reach my clock. Check that I am on Wi-Fi, then ask again."
        return control.run(command)


def _clock_setter(hosted: bool):
    """A hosted body (StackChan) never sets its host computer's clock and never runs sudo."""
    return None if hosted else system_clock_setter()


class MaiPaiBody(ReachyMiniApp):
    """The MaiPai body, run by the daemon as its one app."""

    custom_app_url: str | None = SETTINGS_APP_URL

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        store = PairingStore(_default_pairing_path())
        hosted = os.environ.get("MAIPAI_HUB_HOST") == "1"
        from maipai_body.logging_setup import configure_logging

        configure_logging(hosted)
        discover = _no_hub_discovery if hosted else discover_hub
        self._stack = _build_link_stack(
            store,
            HubLinkClient(
                store,
                clock_sync=ClockSync(_clock_setter(hosted)),
                discover=discover,
            ),
            discover=discover,
            sleep_after_s=_sleep_after_s(),
            label=os.environ.get("MAIPAI_BOT_LABEL", "StackChan" if hosted else "Reachy Mini"),
            pairing_secret_path=(Path(os.environ["MAIPAI_BOT_DATA_DIR"]) / "pairing-secret")
            if hosted
            else None,
            extra_capabilities=["no_vendor_login"] if hosted else [],
            hub_url=(_configured_hub_url() or None) if (hosted or _stackchan_selected()) else None,
        )
        self.link = self._stack.link
        # The base class only wires static files + index.html; the
        # settings page's own JS polls this for live pairing state.
        if self.settings_app is not None:

            @self.settings_app.get("/api/state")
            async def link_state() -> dict:
                return _link_state_payload(self.link, self._stack.offline)

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """Run the body: install the SIGINT handler, start the hub link
        on its own thread, then hold neutral until paired and run the
        real conversation loop for the rest of the process's life."""
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, _sigint_handler(stop_event))
        if _stackchan_selected():
            link_thread = None
            if _no_hub_configured():
                logger.info(
                    "no hub URL is set: the hub link, command channel and check-in are off"
                )
            else:
                link_thread = threading.Thread(
                    target=self.link.run, args=(stop_event,), name="hub-link", daemon=True
                )
                link_thread.start()
                supervisor_thread = threading.Thread(
                    target=self._stack.supervisor.run,
                    args=(stop_event,),
                    name="link-supervisor",
                    daemon=True,
                )
                supervisor_thread.start()
            try:
                _run_stackchan_service(stop_event, self.link, self._stack.offline)
            finally:
                if link_thread is not None:
                    link_thread.join(timeout=5.0)
                signal.signal(signal.SIGINT, previous_handler)
            return
        link_thread = threading.Thread(
            target=self.link.run, args=(stop_event,), name="hub-link", daemon=True
        )
        link_thread.start()
        try:
            client = ReachyMiniClient(REACHY_MINI_PROFILE, reachy=reachy_mini)
            run_paired_body(
                client,
                self.link,
                stop_event,
                cache_dir=_default_models_cache_dir(),
                offline=self._stack.offline,
                supervisor=self._stack.supervisor,
                announcer=self._stack.announcer,
            )
        finally:
            signal.signal(signal.SIGINT, previous_handler)
            link_thread.join(timeout=5.0)


if __name__ == "__main__":
    # The daemon starts an installed app by running its entry point's
    # module as `python -m <module>` in its own subprocess (never by
    # importing the class directly), so this block is the actual thing
    # that runs: found live, RM-03's first daemon-driven start finished
    # in under a second with no error because this block was missing
    # and `python -m maipai_body.app` had nothing to do.
    app = MaiPaiBody()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
    except OSError as error:
        if error.errno != errno.EADDRINUSE:
            raise
        # A port the host needs is taken: say so in plain words instead of a traceback (most often a second copy of the host is already running).
        print(
            f"The host could not start: {error.strerror or 'a port is already in use'}.\n"
            "  Another copy of the host may already be running (check with `stackchan status`), or another program uses that port.\n"
            "  Stop the other one, or set a free port with MAIPAI_XIAOZHI_PORT, MAIPAI_STACKCHAN_AVATAR_PORT or MAIPAI_STACKCHAN_SETTINGS_PORT, then run `stackchan run` again.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
