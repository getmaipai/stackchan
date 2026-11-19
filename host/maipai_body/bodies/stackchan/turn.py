"""StackChan audio turn bridge to the existing hub speech clients."""

from __future__ import annotations

import asyncio
import concurrent.futures
import inspect
import json
import logging
import os
import queue
import re
import threading
import time
import wave
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import av
import numpy as np
import numpy.typing as npt

from maipai_body import reply_tags
from maipai_body.bodies.stackchan import barge, captions
from maipai_body.bodies.stackchan.error_line import ErrorLineBreaker
from maipai_body.mouth_cues import UNIT_MAX_MS, fit_to_unit
from maipai_body.mouth_cues import mouth_cues as mouth_cues_for
from maipai_body.speaker_evidence import SpeakerEvidenceError, speaker_evidence
from maipai_body.speech.capture import BLOCK_SAMPLES
from maipai_body.speech.offline_clips import UNREACHABLE
from maipai_body.speech.playback import AudioPlayback
from maipai_body.speech.reply_stream import ReplyTagger
from maipai_body.speech.stt_stream import WAKE_PATIENCE_S, SttStreamClient, SttStreamError
from maipai_body.speech.tts_playback import TtsAuthFailed, TtsPlaybackClient
from maipai_body.speech.turn_client import TurnAuthFailed, TurnClient, TurnLinkLost

LOG = logging.getLogger(__name__)
# Frames sent ahead of playback. The firmware's decode queue holds 40 frames (2.4 s) and silently
# drops any packet that arrives when it is full, and a burst that catches up after a late frame
# lands on top of what is queued. A short lead (14 frames, 0.84 s, sent in about 0.2 s) keeps the
# queue near 10 of 40 so even a catch-up cannot overflow it. UNMEASURED on the unit.
LEAD_FRAMES = 14
# More than this many frames behind the schedule: catch up by sending the overdue frames at the
# prebuffer cadence (not back to back) so the unit's cushion is refilled, not permanently lost.
MAX_BEHIND_FRAMES = 2
# At most this many overdue frames are caught up; a longer stall has already drained the cushion,
# so the rest of the lost time is dropped from the schedule. 14 + 10 stays under the unit's 40.
CATCH_UP_MAX_FRAMES = 10
CATCH_UP_GAP_S = 0.015
# After the unit's cushion ran dry mid-reply, hold the next frames until this many exist (0.36 s)
# and send them as a burst, so playback does not restart on an empty buffer.
REFILL_FRAMES = 6
# Frames in flight (sent minus played at real time) above this are counted as over the soft cap.
IN_FLIGHT_SOFT_CAP = 30
STREAM_POLL_S = 0.01
# The listening pop-up tone plays right after a wake word or a tap and the microphone hears it;
# uplink frames this soon after a listen start are not sent on, so the tone never reaches speech
# recognition (the hub answers one short voiced burst with no_speech). UNMEASURED default.
POPUP_HOLD_S = 0.3
# A listen the device re-opens by itself right after a reply is a follow-up: the person has this
# long to speak before the turn ends quietly (default 5; a quiet room must not keep it listening).
FOLLOW_UP_S = 3.5  # a follow-up with no wake word ends fast when nothing voiced arrives
# After the unit stops speaking its own speaker echo is still in the room: without echo canceling
# the microphone is ignored this long, so it never answers itself.
ECHO_COOLDOWN_S = 0.9
FOLLOW_UP_AFTER_S = 2.0
# The unit re-opens listening by itself when any playback ends. After a line the robot said on its
# own (an orientation joke, a reaction) nobody was asked anything, so a listen that starts this
# soon after the line is not a follow-up: it is closed at once (live log 2026-11-13 09:53 and
# 09:42: "it said something and listened when I didn't say anything").
REACTION_LISTEN_S = 4.0
# The unit can end up listening without having told the host (no "listen start" arrives after a
# reply, host log 2026-10-22: audio frames flow, nothing answers, until the unit's own guard resets
# it). This many frames in a row, right after a turn, start the listen from the audio itself.
STRAY_FRAMES_TO_LISTEN = 6
# A frame whose loudest sample is above this counts as speech-level sound, to time how long the
# speech-to-text took to answer after the person stopped (a level, never audio).
LOUD_PEAK = 0.1
STRAY_GAP_S = 0.5
STRAY_WINDOW_S = 120.0
# The microphone queue holds at most this many 32 ms blocks (about 2 s); older ones are dropped.
CAPTURE_QUEUE_BLOCKS = 64
# The level line covers the first two seconds heard (16 kHz).
LEVEL_WINDOW_SAMPLES = 32000
# Opt-in debug recording of the uplink, to a folder on this Mac (up to 30 s per turn).
DEBUG_WAV_ENV = "MAIPAI_STACKCHAN_DEBUG_WAV_DIR"
DEBUG_WAV_MAX = 16000 * 30
# Voiced audio the hub must have called speech before a failure is worth an apology.
MIN_SPEECH_S = 0.5
FILLER_AFTER_S = 1.2  # no first sentence by now: show the thinking cue again, once
# Fresh speech-to-text streams opened after a dropped socket before the turn gives up.
STT_RECONNECTS = 2
FRAME_S = 0.06
MOUTH_CUE_HOLD_S = 0.25  # the most the first audio waits for its sentence to finish, so the mouth can follow host cues
# Decode and speaker delay after the last frame's play time, before the stop.
STOP_TAIL_S = 0.12


class StackChanAudioCapture:
    """AudioCapture protocol fed by decoded xiaozhi Opus frames."""

    def __init__(self) -> None:
        # Bounded: the capture keeps filling during the chat and the reply otherwise. The oldest
        # block is dropped when it is full; recognition has long since read anything that old.
        self._queue: queue.Queue[npt.NDArray[np.float32] | None] = queue.Queue(
            maxsize=CAPTURE_QUEUE_BLOCKS
        )
        self._closed = threading.Event()
        self._aborted = threading.Event()
        self._decoder = av.CodecContext.create("opus", "r")
        self._resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
        self._leftover = np.zeros(0, dtype=np.float32)
        self.peak = 0.0  # loudest sample seen (0..1); a level, never audio
        self.last_loud_at: float | None = None  # when a frame last had speech-level sound
        self._square_sum = 0.0
        self._level_samples = 0
        # Opt-in debug recording (MAIPAI_STACKCHAN_DEBUG_WAV_DIR): the decoded uplink, kept in
        # memory for one turn and written to that folder on this Mac only. Off by default.
        self._debug_samples: list[npt.NDArray[np.float32]] | None = (
            [] if os.environ.get(DEBUG_WAV_ENV) else None
        )
        self._debug_total = 0

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def feed_opus(self, data: bytes) -> None:
        if self._closed.is_set():
            return
        packet = av.Packet(data)
        for frame in self._decoder.decode(packet):
            for converted in self._resampler.resample(frame):
                samples = converted.to_ndarray().reshape(-1).astype(np.float32)
                if samples.size:
                    frame_peak = min(1.0, float(np.max(np.abs(samples))))
                    self.peak = max(self.peak, frame_peak)
                    if frame_peak > LOUD_PEAK:
                        self.last_loud_at = time.monotonic()
                    if self._level_samples < LEVEL_WINDOW_SAMPLES:
                        self._square_sum += float(np.sum(np.square(samples, dtype=np.float64)))
                        self._level_samples += samples.size
                    if self._debug_samples is not None and self._debug_total < DEBUG_WAV_MAX:
                        self._debug_samples.append(samples)
                        self._debug_total += samples.size
                self._queue_blocks(samples)

    def _queue_blocks(self, samples: npt.NDArray[np.float32]) -> None:
        data = np.concatenate((self._leftover, samples))
        while len(data) >= BLOCK_SAMPLES:
            block = data[:BLOCK_SAMPLES].copy()
            while True:
                try:
                    self._queue.put_nowait(block)
                    break
                except queue.Full:
                    try:
                        self._queue.get_nowait()  # drop the oldest
                    except queue.Empty:
                        pass
            data = data[BLOCK_SAMPLES:]
        self._leftover = data

    @property
    def rms(self) -> float:
        """Loudness of the first two seconds heard (0..1); a level, never audio."""
        if not self._level_samples:
            return 0.0
        return float(np.sqrt(self._square_sum / self._level_samples))

    def save_debug_wav(self, folder: str, name: str) -> Path | None:
        """Write the opt-in debug recording; returns the file, or None when it is off."""
        if not self._debug_samples:
            return None
        directory = Path(folder).expanduser()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.wav"
        pcm = np.clip(np.concatenate(self._debug_samples) * 32767, -32768, 32767).astype("<i2")
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(16000)
            out.writeframes(pcm.tobytes())
        return path

    def start(self) -> None:
        pass

    def stop(self) -> None:
        self.close()

    def close(self) -> None:
        self._closed.set()
        self._queue.put(None)

    def abort(self) -> None:
        self._aborted.set()
        self.close()

    def poll_blocks(self) -> list[npt.NDArray[np.float32]]:
        if self._aborted.is_set():
            raise RuntimeError("StackChan listening was aborted")
        if self._closed.is_set() and self._queue.empty():
            return [np.zeros(BLOCK_SAMPLES, dtype=np.float32)]
        try:
            first = self._queue.get(timeout=0.05)
        except queue.Empty:
            return []
        if first is None:
            self._closed.set()
            return [np.zeros(BLOCK_SAMPLES, dtype=np.float32)]
        blocks = [first]
        while len(blocks) < 8:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                self._closed.set()
                break
            blocks.append(item)
        return blocks


class StackChanAudioPlayback(AudioPlayback):
    """AudioPlayback protocol encoder to authenticated XiaozhiServer.send_audio."""

    def __init__(
        self,
        server,
        device_id: str,
        *,
        clock=time.monotonic,
        sleeper=time.sleep,
        async_sleep=asyncio.sleep,
        pitch_semitones=lambda: 0.0,
        speech_speed=lambda: 1.0,
    ) -> None:
        self._server = server
        self._device_id = device_id
        # The selected voice's pitch offset in semitones (0 leaves the audio untouched).
        self._pitch_semitones = pitch_semitones
        # The unit's speaking speed (1 leaves the audio untouched).
        self._speech_speed = speech_speed
        self._pitch_buffer: list[npt.NDArray[np.float32]] = []
        # Streaming sender state (one sentence at a time).
        self._sender_future: concurrent.futures.Future | None = None
        self._finished = False
        self._sent_frames = 0
        self._lateness: list[float] = []
        self._behind_events = 0
        self._max_in_flight = 0.0
        self._over_cap = 0
        self._was_starved = False
        self._refills = 0
        self._encoder = self._new_encoder()
        self._samples = np.zeros(0, dtype=np.float32)
        self._frames: list[bytes] = []
        # Every packet of this reply as encoded (the last replies are kept in memory for
        # "say that again"; see repeat.py). Empty for a replay.
        self._recorded: list[bytes] = []
        self._lock = threading.RLock()
        self._sentence_start = True
        # Caption markers (patches N01/N04): frames ever queued and sent (not reset per sentence), the sentence being
        # spoken now as (first frame, pieces), and the (frame, text) markers waiting for the sender.
        self._added = 0
        self._popped = 0
        self._cap_open: tuple[int, list[str]] | None = None
        self._cap_marks: list[tuple[int, str]] = []
        self._clock, self._sleep, self._async_sleep = clock, sleeper, async_sleep
        self._cancel_event: threading.Event | None = None
        self._aborted = threading.Event()
        # When the robot finishes playing what was sent; the stop waits for it.
        self._play_until = 0.0
        # Called once, just before the first reply frames go to the unit (the face starts talking
        # then, not a second earlier at synthesis time).
        self.on_first_audio: Callable[[], object] | None = None
        self._announced = False
        # Host-computed mouth cues (self.face.mouth_cues, patch SF10): the unit takes one list per reply, played from the
        # first audio frame, so they are sent only for a reply that is one sentence, once that sentence is synthesized.
        self.mouth_cues_on = False
        # Sentences that say the wake phrase are marked no_barge for the unit (patch SF29); None turns it off.
        self.wake_phrases: Callable[[], list[str]] | None = barge.wake_phrases
        self._no_barge: dict[str, int] = {}  # caption piece -> milliseconds
        self._cue_samples: list[npt.NDArray[np.float32]] = []
        self._cue_collecting = True
        self._cue_decided = threading.Event()
        self._cue_single = False
        # With a unit that can append to the list it is playing (hello feature "mouth_cues_append"), every sentence sends its own
        # cues, their times continuing from the audio already queued; sentences wait here, in order, until they can be sent.
        self._cue_pending: list[npt.NDArray[np.float32]] = []
        self._cue_sent = 0
        self._cue_offset_ms = 0
        self._cue_last_ms = 0
        self._cue_first_ok = False
        self._cue_off = False
        self._cue_lock = threading.Lock()
        super().__init__(self)

    def get_output_audio_samplerate(self) -> int:
        return 24000

    @staticmethod
    def _new_encoder():
        encoder = av.CodecContext.create("opus", "w")
        encoder.sample_rate = 24000
        encoder.layout = "mono"
        encoder.format = "s16"
        # Speech-mode SILK wideband: one 60 ms frame per packet at 24 kbps. The default
        # music mode sent 64 kbps packets of three CELT frames, which the ESP32-S3
        # decoded slower than real time (choppy speech on the 2026-10-19 unit bench).
        encoder.bit_rate = 24000
        encoder.options = {"application": "voip", "frame_duration": "60", "cutoff": "8000"}
        encoder.open()
        return encoder

    def get_input_audio_samplerate(self) -> int:
        return 16000

    def get_doa(self):
        return None

    def start_recording(self):
        pass

    def stop_recording(self):
        pass

    def get_audio_sample(self):
        return None

    def start_playing(self):
        pass

    def push_audio_sample(self, data: npt.NDArray[np.float32]) -> None:
        with self._lock:
            if self._pitch_semitones() != 0.0 or self._speech_speed() != 1.0:
                # A pitch or speed change needs the whole sentence (nothing is sent before stop() anyway).
                self._pitch_buffer.append(data.astype(np.float32))
                return
            self._frame_locked(data)

    def decide_cues(self, single_sentence: bool) -> None:
        """The first sentence is fully synthesized: say whether it is the whole reply (then its cues are sent)."""
        with self._lock:
            self._cue_single = bool(single_sentence)  # takes effect at end_sentence, once the audio is all queued

    def _cue_append_ok(self) -> bool:
        check = getattr(self._server, "device_supports", None)
        try:
            return bool(check and check("mouth_cues_append", self._device_id))
        except Exception:
            return False

    def _flush_cues(self) -> None:
        """Send the sentences waiting for cues, in order: the first as a new list, the rest appended to it."""
        with self._cue_lock:
            while self._cue_pending and not self._cue_off and not self._canceled():
                if self._cue_sent == 0 and not self._cue_first_ok:
                    return
                audio = self._cue_pending.pop(0)
                span_ms = int(len(audio) * 1000 / 24000)
                if self._cue_offset_ms + span_ms > UNIT_MAX_MS:
                    self._cue_off = True  # past the unit's 60 s span: the mouth follows the loudness from here
                    return
                cues = fit_to_unit(mouth_cues_for(audio, 24000))
                shifted: list[list[int]] = []
                for t, level in cues:
                    at = max(t + self._cue_offset_ms, self._cue_last_ms)  # a closing cue may run a window past its audio
                    if shifted and shifted[-1][0] == at:
                        shifted[-1][1] = level
                    else:
                        shifted.append([at, level])
                arguments: dict[str, object] = {"cues": json.dumps(shifted)}
                if self._cue_sent:
                    arguments["append"] = True
                try:
                    self._server.call_device_tool(
                        "self.face.mouth_cues", arguments, timeout=2.0, device_id=self._device_id
                    )
                except Exception as exc:  # old firmware, muted, locked or a slow unit: the mouth follows the loudness
                    LOG.debug("StackChan mouth cues not sent: %s", type(exc).__name__)
                    if not isinstance(exc, TimeoutError):
                        self.mouth_cues_on = False
                        self._cue_off = True
                    return
                self._cue_sent += 1
                self._cue_last_ms = shifted[-1][0]
                self._cue_offset_ms += span_ms

    async def _send_mouth_cues(self) -> None:
        """The reply's first mouth list, before its first audio frame (the unit starts it with that frame)."""
        deadline = self._clock() + MOUTH_CUE_HOLD_S
        while not self._cue_decided.is_set() and self._clock() < deadline and not self._canceled():
            await self._async_sleep(0.02)
        if not self._cue_decided.is_set() or self._canceled():
            return
        if self._cue_pending:  # a unit that appends: every sentence sends its own list
            self._cue_first_ok = True
            await asyncio.to_thread(self._flush_cues)
            return
        if not self._cue_single:
            return
        with self._lock:
            samples = np.concatenate(self._cue_samples) if self._cue_samples else np.zeros(0, dtype=np.float32)
        cues = fit_to_unit(mouth_cues_for(samples, 24000))
        try:
            await asyncio.to_thread(
                self._server.call_device_tool,
                "self.face.mouth_cues",
                {"cues": json.dumps([list(c) for c in cues])},
                timeout=2.0,
                device_id=self._device_id,
            )
        except Exception as exc:  # old firmware, muted, locked or a slow unit: the mouth follows the loudness
            LOG.debug("StackChan mouth cues not sent: %s", type(exc).__name__)
            if not isinstance(exc, TimeoutError):
                self.mouth_cues_on = False

    def _frame_locked(self, data: npt.NDArray[np.float32]) -> None:
        if self.mouth_cues_on and self._cue_collecting:
            self._cue_samples.append(data.astype(np.float32))
        self._samples = np.concatenate((self._samples, data.astype(np.float32)))
        while len(self._samples) >= 1440:
            block, self._samples = self._samples[:1440], self._samples[1440:]
            frame = av.AudioFrame.from_ndarray(
                np.clip(block * 32767, -32768, 32767).astype(np.int16).reshape(1, -1),
                format="s16",
                layout="mono",
            )
            frame.sample_rate = 24000
            self._add_packets_locked(self._encoder.encode(frame))
        self._kick_locked()

    def _add_packets_locked(self, packets) -> None:
        made = [bytes(packet) for packet in packets]
        self._frames.extend(made)
        self._added += len(made)
        self._recorded.extend(made)

    def caption(self, text: str) -> None:
        """The sentence whose audio is queued next; the unit shows its exact words when that audio starts."""
        parts = captions.pieces(text)
        if self.wake_phrases is not None and text:
            try:
                if barge.says_wake_phrase(text, self.wake_phrases()):
                    for part in parts:
                        self._no_barge[part] = barge.no_barge_ms(text)
            except Exception:
                LOG.debug("StackChan wake-phrase check skipped", exc_info=True)
        with self._lock:
            self._close_caption_locked()
            if parts:
                self._cap_open = (self._added, parts)
                self._cap_marks.append((self._added, parts[0]))

    def _close_caption_locked(self) -> None:
        """The open sentence is fully queued: place its later pieces by their share of its characters."""
        if self._cap_open is None:
            return
        start, parts = self._cap_open
        self._cap_open = None
        total = self._added - start
        chars = sum(len(p) for p in parts) or 1
        spent = len(parts[0])
        for part in parts[1:]:
            self._cap_marks.append((start + int(total * spent / chars), part))
            spent += len(part)

    def _caption_args(self, caption: str | None) -> dict[str, object]:
        """The caption of a sentence_start, and no_barge with its length when the sentence says the wake phrase."""
        if not caption:
            return {}
        args: dict[str, object] = {"caption": caption}
        if caption in self._no_barge:
            args["no_barge_ms"] = self._no_barge[caption]
        return args

    def _take_caption_locked(self, frame_index: int) -> str | None:
        """The next caption due at or before this frame (one per send; a late piece goes out on the next frame)."""
        if self._cap_marks and self._cap_marks[0][0] <= frame_index:
            return self._cap_marks.pop(0)[1]
        return None

    def recorded_frames(self) -> list[bytes]:
        """The Opus packets of everything encoded for this reply, as sent to the unit."""
        with self._lock:
            return list(self._recorded)

    def _canceled(self) -> bool:
        return self._aborted.is_set() or (
            self._cancel_event is not None and self._cancel_event.is_set()
        )

    def _kick_locked(self) -> None:
        """Start sending as soon as the lead exists, while the sentence is still synthesizing."""
        if (
            self._sender_future is None
            and len(self._frames) >= LEAD_FRAMES
            and getattr(self._server, "_loop", None) is not None
            and not self._canceled()
        ):
            self._sender_future = asyncio.run_coroutine_threadsafe(
                self._sender(), self._server._loop
            )

    async def _sender(self) -> None:
        """Send the lead at once, then the rest at real time; catch up a stall in bounded steps.

        One stream carries the whole reply: sentence N+1 is synthesized while N plays, so a
        sentence boundary costs nothing unless synthesis is slower than playback. If the unit's
        cushion ran dry (the producer fell behind), the next frames are held until a small lead
        exists and sent as a burst, instead of trickling to an empty buffer."""
        with self._lock:
            lead = self._frames[:LEAD_FRAMES]
            del self._frames[:LEAD_FRAMES]
            lead_caption = self._take_caption_locked(self._popped + len(lead) - 1)
            self._popped += len(lead)
        if not lead or self._canceled():
            return
        first_sentence = self._sentence_start
        self._sentence_start = False
        if first_sentence and self.mouth_cues_on:
            await self._send_mouth_cues()
            if self._canceled():
                return
        began = self._clock()
        self._play_until = max(self._clock(), self._play_until) + len(lead) * FRAME_S
        if not self._announced:
            self._announced = True
            if self.on_first_audio is not None:
                try:
                    self.on_first_audio()
                except Exception:
                    LOG.debug("StackChan first-audio hook failed", exc_info=True)
        await self._server.send_audio(
            self._device_id,
            lead,
            sentence_start=True,
            start=first_sentence,
            stop=False,
            prebuffer=len(lead),
            **self._caption_args(lead_caption),
        )
        total = len(lead)
        sent = len(lead)  # since `began`, the last time the schedule was based
        self._note_flight(sent, began)
        deadline = self._clock()
        catching_up = False
        while not self._canceled():
            with self._lock:
                finished = self._finished
                waiting = len(self._frames)
                # Starved: nothing queued and the unit has (almost) nothing left to play. Hold the
                # next frames until REFILL_FRAMES exist (or the reply is complete).
                starved = waiting == 0 and sent - (self._clock() - began) / FRAME_S < 1.0
            if waiting == 0:
                if finished:
                    break
                self._was_starved = self._was_starved or starved
                await self._async_sleep(STREAM_POLL_S)
                deadline = max(deadline, self._clock())  # a stalled producer: no burst after it
                continue
            if self._was_starved and waiting < REFILL_FRAMES and not finished:
                await self._async_sleep(STREAM_POLL_S)
                continue
            if self._was_starved:
                with self._lock:
                    batch = self._frames[:REFILL_FRAMES]
                    del self._frames[:REFILL_FRAMES]
                    batch_caption = self._take_caption_locked(self._popped + len(batch) - 1)
                    self._popped += len(batch)
                self._was_starved = False
                self._refills += 1
                began = self._clock()
                self._play_until = max(self._clock(), self._play_until) + len(batch) * FRAME_S
                await self._server.send_audio(
                    self._device_id,
                    batch,
                    sentence_start=batch_caption is not None,
                    start=False,
                    stop=False,
                    prebuffer=len(batch),
                    **self._caption_args(batch_caption),
                )
                total += len(batch)
                sent = len(batch)
                deadline = self._clock()
                continue
            frame_caption = None
            with self._lock:
                frame = self._frames.pop(0) if self._frames else None
                if frame is not None:
                    frame_caption = self._take_caption_locked(self._popped)
                    self._popped += 1
            if frame is None:
                continue
            deadline += FRAME_S
            now = self._clock()
            behind = (now - deadline) / FRAME_S
            if behind > MAX_BEHIND_FRAMES:
                if not catching_up:
                    catching_up = True
                    self._behind_events += 1
                    LOG.warning(
                        "StackChan playback behind by %d frames (%.0f ms); catching up",
                        int(behind),
                        behind * FRAME_S * 1000,
                    )
                if behind > CATCH_UP_MAX_FRAMES:
                    deadline = now - CATCH_UP_MAX_FRAMES * FRAME_S
                await self._async_sleep(CATCH_UP_GAP_S)
            else:
                catching_up = False
                await self._async_sleep(max(0.0, deadline - now))
            if self._canceled():
                break
            self._lateness.append(max(0.0, self._clock() - deadline))
            if frame_caption:
                await self._server.send_audio(
                    self._device_id,
                    [frame],
                    sentence_start=True,
                    start=False,
                    stop=False,
                    **self._caption_args(frame_caption),
                )
            else:
                await self._server.send_audio(
                    self._device_id, [frame], sentence_start=False, start=False, stop=False
                )
            total += 1
            sent += 1
            self._play_until = max(self._play_until, self._clock()) + FRAME_S
            self._note_flight(sent, began)
        self._sent_frames += total

    def _note_flight(self, sent: int, began: float) -> None:
        in_flight = sent - (self._clock() - began) / FRAME_S
        self._max_in_flight = max(self._max_in_flight, in_flight)
        if in_flight > IN_FLIGHT_SOFT_CAP:
            self._over_cap += 1

    def _log_sentence_stats(self) -> None:
        late = sorted(self._lateness)
        p95 = late[int(0.95 * (len(late) - 1))] if late else 0.0
        LOG.info(
            "StackChan playback: %d frames, lateness p95 %.0f ms max %.0f ms, behind %d times, "
            "max in flight %.0f, over %d in flight %d times, refilled %d times",
            self._sent_frames,
            p95 * 1000,
            (late[-1] if late else 0.0) * 1000,
            self._behind_events,
            self._max_in_flight,
            IN_FLIGHT_SOFT_CAP,
            self._over_cap,
            self._refills,
        )

    def _reset_sentence(self) -> None:
        self._sender_future = None
        self._finished = False
        self._sent_frames = 0
        self._lateness = []
        self._behind_events = 0
        self._max_in_flight = 0.0
        self._over_cap = 0
        self._was_starved = False
        self._refills = 0

    def _flush_sentence_locked(self) -> None:
        if self._pitch_buffer:
            from maipai_body.speech.pitch import shape_voice

            whole = np.concatenate(self._pitch_buffer)
            self._pitch_buffer = []
            self._frame_locked(shape_voice(whole, 24000, self._pitch_semitones(), self._speech_speed()))
        if len(self._samples):
            padded = np.pad(self._samples, (0, 1440 - len(self._samples)))
            frame = av.AudioFrame.from_ndarray(
                np.clip(padded * 32767, -32768, 32767).astype(np.int16).reshape(1, -1),
                format="s16",
                layout="mono",
            )
            frame.sample_rate = 24000
            self._add_packets_locked(self._encoder.encode(frame))
        self._add_packets_locked(self._encoder.encode(None))
        self._samples = np.zeros(0, dtype=np.float32)
        self._encoder = self._new_encoder()
        self._close_caption_locked()

    def end_sentence(self) -> None:
        """One sentence is fully synthesized. The reply stays one paced stream: flush this
        sentence's encoder tail and let the sender carry on into the next sentence."""
        with self._lock:
            self._flush_sentence_locked()
            if self.mouth_cues_on and self._cue_append_ok():
                self._cue_pending.append(
                    np.concatenate(self._cue_samples) if self._cue_samples else np.zeros(0, dtype=np.float32)
                )
                self._cue_samples = []
            else:
                self._cue_collecting = False
            self._cue_decided.set()
            if self._sender_future is None and self._frames and not self._canceled():
                # A short first sentence: fewer frames than the lead, so nothing has been sent yet.
                self._sender_future = asyncio.run_coroutine_threadsafe(
                    self._sender(), self._server._loop
                )
        if self._cue_pending:
            self._flush_cues()

    def stop_playing(self) -> None:
        with self._lock:
            self._flush_sentence_locked()
        self._finish_and_wait()

    def replay_frames(self, frames) -> None:
        """Send already encoded packets again, paced like a reply (nothing is recorded again)."""
        with self._lock:
            self._frames.extend(frames)
            self._added += len(frames)
        self._finish_and_wait()

    def _finish_and_wait(self) -> None:
        with self._lock:
            self._finished = True
            if self._sender_future is None and self._frames and not self._canceled():
                # A short sentence: fewer frames than the lead, so nothing has been sent yet.
                self._sender_future = asyncio.run_coroutine_threadsafe(
                    self._sender(), self._server._loop
                )
            future = self._sender_future
            remaining = len(self._frames)
        try:
            if future is not None:
                try:
                    future.result(timeout=remaining * FRAME_S + 10.0)
                except concurrent.futures.TimeoutError:
                    future.cancel()  # the coroutine must not keep sending in the background
                    raise
            if future is not None:
                self._log_sentence_stats()
        finally:
            with self._lock:
                self._reset_sentence()

    def end(self) -> None:
        # The robot holds up to LEAD_FRAMES of audio when the last frame is sent. Stopping
        # then cut the talking mouth about 1.4 s (four words) early on the 2026-10-19 bench.
        self._sleep(max(0.0, self._play_until - self._clock()) + STOP_TAIL_S)
        asyncio.run_coroutine_threadsafe(
            self._server.stop_audio(self._device_id), self._server._loop
        ).result(timeout=5)

    def flush(self, *, send_stop: bool = True) -> None:
        self._aborted.set()
        with self._lock:
            self._samples = np.zeros(0, dtype=np.float32)
            self._frames.clear()
            self._popped = self._added
            self._cap_open, self._cap_marks = None, []
            self._pitch_buffer = []
            if self._sender_future is not None:
                self._sender_future.cancel()
            self._encoder = self._new_encoder()
        if send_stop:
            return asyncio.run_coroutine_threadsafe(
                self._server.stop_audio(self._device_id), self._server._loop
            )
        return None


BUSY_LINE = "I am busy with other requests. One moment."
BUSY_AT = 64  # turns in flight before a new one is told to wait


class StackChanTurnBridge:
    # Turns in flight, for the busy notice (a bridge made without __init__, as some tests do, still counts).
    _inflight = 0
    busy_at = BUSY_AT
    _inflight_lock = threading.Lock()

    def __init__(
        self,
        server,
        link,
        offline,
        *,
        cache_dir=None,
        stt_factory=SttStreamClient,
        turn_factory=TurnClient,
        tts_factory=TtsPlaybackClient,
        person_attribution=None,
        expression_sink=None,
        live_sink=None,
        uplink_stats=None,
        side_executor=None,
        volume_control=None,
        brightness_control=None,
        head_control=None,
        alarm_control=None,
        gaze_control=None,
        sight_control=None,
        repeat_control=None,
        units=None,
        on_user_words=None,
        on_reply_mood=None,
        clock=time.monotonic,
    ) -> None:
        self.server, self.link, self.offline = server, link, offline
        # The light standard's live cue: green while the voice is being sent to the hub.
        self.live_sink = live_sink
        # BOT-SELF-TEST-01: counts of uplink frames and wake detects (never audio).
        self.uplink_stats = uplink_stats
        # "Louder", "volume to 60": answered here, without asking the hub.
        self.volume_control = volume_control
        # Several robots: picks each unit's brain and volume cap by its Device-Id (units.py).
        self.units = units
        # "Brightness 50", "dimmer": answered here too, on the same terms as the volume.
        self.brightness_control = brightness_control
        # "Look left", "nod": answered here too, since the hub's model can only say "I can't".
        self.head_control = head_control
        self.alarm_control = alarm_control
        # Talk games ("play twenty questions", "tell me a riddle"; talk_games.py): started here with a fixed line, then
        # the model plays with the game's rules next to its persona. None means no talk games.
        self.talk_games = None
        self.talk_fallback = None  # PantryTalk (packages/pantry/talk_fallback.py): riddles and trivia from the library when the model cannot be reached
        # The spoken word "lock" ("bloquear"): locks the unit that heard it (lock_voice.py). None means the word goes to the model.
        self.lock_control = None
        # "What are you looking at?": answered from the head's own reason, never by the hub.
        self.gaze_control = gaze_control
        # "Can you see me?": answered from what the host knows, never "I can't see".
        self.sight_control = sight_control
        # "Say that again", "what did I miss": answered here from memory (repeat.py), no hub call.
        self.repeat_control = repeat_control
        # (kind) -> True when Home described a fresh picture for this question; set by the app.
        self.vision_ask: Callable[[str], bool] | None = None
        # Why the robot may not hear or say anything ("muted" or "full quiet"), else None.
        self.muted_reason: Callable[[], str | None] = lambda: None
        # Kind words and loving replies earn the heart (reactions.py); both may be None.
        self.on_user_words = on_user_words
        self.on_reply_mood = on_reply_mood
        self.on_turn_end = None
        self._reaction_speaking = False
        self._reaction_ended_at = float("-inf")
        self._reaction_lock = threading.Lock()
        self._reaction_units: set[str] = set()
        # The expression and light sinks make blocking device calls that wait on this very event
        # loop; run inline they froze it until each 5 s timeout (live log 2026-10-20: 5 s to start
        # a turn, 12 s to the first audio frame). One worker keeps their order.
        self._side = side_executor or concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="stackchan-side"
        )
        # The ring light has its own worker: a slow light write (5 s timeout) must not hold the
        # face behind it.
        self._light_side = side_executor or concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="stackchan-light"
        )
        self._clock = clock
        self.cache_dir = cache_dir
        from maipai_body.bodies.stackchan.speech_backend import HubBackend, LocalBackend

        self.backend = HubBackend(stt_factory, turn_factory, tts_factory)
        self._local_speech = self._local_speech_from(units)
        if self._local_speech is not None:
            self.backend = LocalBackend(stt_factory, turn_factory, tts_factory)
            from maipai_body.speech.local_speech import LocalSttClient, LocalTtsClient

            from maipai_body.speech.local_speech import builtin_stt_factory, builtin_tts_factory

            stt_url, tts_url, timeout, llm_config = self._local_speech
            stt_engine = None if stt_url else builtin_stt_factory(llm_config)
            tts_engine = None if tts_url else builtin_tts_factory(llm_config)
            self.stt_factory = lambda _base, _cookie: LocalSttClient(
                stt_url, engine=stt_engine, timeout_s=timeout, wait=lambda: self._wait_level
            )
            self.tts_factory = lambda _base, _cookie, playback: LocalTtsClient(
                tts_url, playback, engine=tts_engine, timeout_s=timeout
            )
        self.person_attribution = person_attribution or (lambda: None)
        self.expression_sink = expression_sink
        self._inflight = 0
        self._inflight_lock = threading.Lock()
        self.busy_at = BUSY_AT
        self._captures: dict[str, StackChanAudioCapture] = {}
        self._states: dict[str, str] = {}
        self._aec: dict[str, bool] = {}
        self._speech_ended: dict[str, float] = {}
        self._speaking_since: dict[str, float] = {}
        self._uplink_live = 0
        self._uplink_dropped = 0
        self._first_audio_ms: float | None = None
        self._abort_to_silence_ms: float | None = None
        self._abort_started: dict[str, float] = {}
        self._capture_started: dict[str, float] = {}
        self._modes: dict[str, str] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._playbacks: dict[str, StackChanAudioPlayback] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._settled_sessions: set[str] = set()
        # Voice diagnostics (counts only, never audio or words): frames and bytes per session.
        self._audio_stats: dict[str, list[int]] = {}
        self._popup_dropped = 0
        self._current_session = ""
        self._last_turn_end: dict[str, float] = {}
        self._followup: dict[str, bool] = {}
        self._stray: dict[str, tuple[int, float]] = {}
        self._quiet_idle: set[str] = set()  # sessions the host sent idle after a silent turn
        self.follow_up_s = FOLLOW_UP_S
        self.language = "en"
        self.dropped_utterances = 0
        # The audio half of the noise gate (steady noise, too little voiced sound). Plumbing tests
        # that feed a synthetic tone as "speech" turn it off; the words check stays on.
        self.audio_noise_gate = True
        self._wait_level = "quick"  # "Wait after you stop talking", read per turn
        # The selected voice record's pitch_semitones (-12 to 12); 0 changes nothing.
        self.pitch_semitones = lambda: 0.0
        self._breaker = ErrorLineBreaker(clock=clock)
        self._quiet_streak = 0
        # Called just before the plain apology is spoken (the error earcon, sounds.py); may be None.
        self.on_error_line = None
        # Streaming: seconds without a first sentence before the thinking cue is shown again and
        # on_slow_reply (a filler-sound hook, None until one exists) is called, once per turn.
        self.filler_after_s = FILLER_AFTER_S
        self.on_slow_reply = None
        # The unit's host-side preferences by Device-Id (unit_prefs.py): emotion faces, overlays, the
        # "While it thinks" choice and its wait. None means every default.
        self.prefs_for: Callable[[str], dict] | None = None
        # Shows overlays asked for by reply tags (overlays.py); None leaves them out.
        self.overlay_director = None
        # Plays the "While it thinks" sound when no first audio arrives in time (fillers.py); None: no sound.
        self.filler_player = None
        # True while something outranks decoration (sleep, the low-battery tired look): no overlay starts.
        self.decoration_blocked: Callable[[], bool] = lambda: False
        # The command bus (command_bus.py): when set, every decoration a reply asks for (overlay, scene, sound, light) goes through
        # its permission, gate, priority and rate checks. None leaves the older direct overlay path.
        self.command_bus = None
        # Whether a child is present and whether a remote cue holds this unit, by Device-Id; Home and the remote page fill them in.
        self._child_until: dict[str, float] = {}
        self.child_present: Callable[[str], bool] = self.child_present_for
        self.remote_active: Callable[[str], bool] = lambda _device_id: False

    def note_child_present(self, device_id: str, present: bool, seconds: float = 300.0) -> None:
        """Home (or a person on the settings page) says a child is, or is no longer, near this unit."""
        from maipai_body import child_gate

        child_gate.note(device_id, present, seconds)  # packages that must not act near a child read the same note
        if present:
            self._child_until[device_id] = self._clock() + max(1.0, float(seconds))
        else:
            self._child_until.pop(device_id, None)

    def child_present_for(self, device_id: str) -> bool:
        return self._child_until.get(device_id, 0.0) > self._clock()

    async def on_audio(self, session_id: str, data: bytes) -> None:
        stats = self._audio_stats.setdefault(session_id, [0, 0])
        stats[0] += 1
        stats[1] += len(data)
        if stats[0] == 1:
            LOG.info(
                "StackChan voice: first audio frame (%d bytes) for session %s",
                len(data),
                session_id[:8],
            )
        capture = self._captures.get(session_id)
        self._record_uplink(len(data), getattr(capture, "peak", 0.0))
        now = self._clock()
        if capture is None and self._states.get(session_id, "idle") == "idle":
            if await self._listen_from_stray_audio(session_id, now):
                return
        if self._states.get(session_id) == "speaking":
            if not self._aec.get(session_id, False):
                self._uplink_dropped += 1
                return
            self._uplink_live += 1
        elif now - self._speech_ended.get(session_id, float("-inf")) < (
            0.18 if self._aec.get(session_id, False) else ECHO_COOLDOWN_S
        ):
            self._uplink_dropped += 1
            return
        # A follow-up listen opens with no tone (the firmware plays it only for a wake word or a
        # tap), so nothing is held back there: the first word of "yes" or "again" is speech.
        if (
            capture is not None
            and not self._followup.get(session_id, False)
            and now - self._capture_started.get(session_id, -1e9) < POPUP_HOLD_S
        ):
            self._popup_dropped += 1
            return
        if capture is not None:
            started = self._capture_started.get(session_id, now)
            if self._first_audio_ms is None:
                self._first_audio_ms = max(0.0, (now - started) * 1000)
            try:
                # Decoding and resampling run off the event loop (one frame at a time, in order):
                # inline they delayed the paced send's wake-ups.
                await asyncio.to_thread(capture.feed_opus, data)
            except Exception:
                LOG.exception("StackChan Opus input could not be decoded")

    async def _listen_from_stray_audio(self, session_id: str, now: float) -> bool:
        """Audio is arriving with no listen start: after a turn, begin the listen from the audio."""
        if session_id in self._quiet_idle:
            # The host just told the unit to go idle after a silent turn; audio still in flight
            # is not a new turn. A real listen start (or a wake) clears this.
            return False
        count, last = self._stray.get(session_id, (0, float("-inf")))
        count = count + 1 if now - last <= STRAY_GAP_S else 1
        self._stray[session_id] = (count, now)
        if count < STRAY_FRAMES_TO_LISTEN:
            return False
        if now - self._last_turn_end.get(session_id, float("-inf")) > STRAY_WINDOW_S:
            return False
        device_id = next(
            (
                device
                for device, sid in getattr(self.server, "_session_ids", {}).items()
                if sid == session_id
            ),
            None,
        )
        if device_id is None:
            return False
        self._stray.pop(session_id, None)
        LOG.info(
            "StackChan voice: audio is arriving with no listen start; starting the turn from it "
            "(session %s)",
            session_id[:8],
        )
        await self.listen(session_id, device_id, "start", mode="auto")
        return True

    async def listen(
        self, session_id: str, device_id: str, state: str, *, mode="auto", aec=None
    ) -> None:
        if aec is not None:
            self._aec[session_id] = bool(aec)
        LOG.info("StackChan voice: listen %s (mode %s) for session %s", state, mode, session_id[:8])
        if state in {"start", "detect"}:
            silent = self.muted_reason()
            if silent is not None:
                LOG.info("StackChan voice: no turn, the robot is %s", silent)
                await self._go_idle(device_id)
                return
        if state == "start" and self._clock() - self._reaction_ended_at < REACTION_LISTEN_S:
            LOG.info("StackChan voice: no follow-up listen after a line it said on its own")
            self._quiet_idle.add(session_id)
            await self._go_idle(device_id)
            return
        if state == "detect":
            self._record_uplink(0, 0.0, detect=True)
        if state in {"start", "detect"}:
            self._quiet_idle.discard(session_id)
            self._audio_stats[session_id] = [0, 0]
            self._followup[session_id] = (
                state == "start"
                and self._clock() - self._last_turn_end.get(session_id, float("-inf"))
                < FOLLOW_UP_AFTER_S
            )
            self._cancel_turn(session_id, send_stop=True)
            capture = StackChanAudioCapture()
            self._captures[session_id] = capture
            self._states[session_id] = "listening"
            self._modes[session_id] = mode if mode in {"auto", "manual", "realtime"} else "auto"
            self._capture_started[session_id] = self._clock()
            task = asyncio.create_task(self._run(session_id, device_id, capture))
            self._tasks[session_id] = task
        elif state == "stop":
            capture = self._captures.get(session_id)
            if capture:
                capture.close()
        elif state == "abort":
            self.abort(session_id)

    def abort(self, session_id: str) -> None:
        self._cancel_turn(session_id, send_stop=True)

    def _cancel_turn(self, session_id: str, *, send_stop: bool) -> None:
        capture = self._captures.pop(session_id, None)
        if capture:
            capture.abort()
        cancel = self._cancel_events.get(session_id)
        if cancel:
            cancel.set()
        playback = self._playbacks.get(session_id)
        flushed = bool(playback)
        if playback:
            stopped_at = self._clock()
            try:
                stop_future = playback.flush(send_stop=send_stop)
            except TypeError:
                stop_future = playback.flush()
            if send_stop and stop_future is not None:
                stop_future.add_done_callback(
                    lambda _future: setattr(
                        self, "_abort_to_silence_ms", max(0.0, (self._clock() - stopped_at) * 1000)
                    )
                )
            elif send_stop:
                self._abort_to_silence_ms = 0.0
        task = self._tasks.pop(session_id, None)
        if task:
            task.cancel()
        self._states[session_id] = "idle"
        self._speaking_since.pop(session_id, None)
        if flushed:
            # Only a real playback leaves an echo tail to ignore; stamping on every listen start
            # dropped the first 180 ms of each utterance.
            self._speech_ended[session_id] = self._clock()
        self._settled_sessions.add(session_id)
        self._emit_expression("settle")

    @property
    def latency_counters(self) -> dict[str, float | None]:
        return {
            "abort_to_silence_ms": self._abort_to_silence_ms,
            "first_audio_ms": self._first_audio_ms,
        }

    async def _recognize(self, base, cookie, capture, started_at):
        """Speech to text, listening on while the wake patience lasts.

        The hub answers a short burst with no speech (a pop-up tone, a click) as ``no_speech``. If
        the person has had less than the wake patience to speak and the device has not stopped,
        open a fresh stream on the same capture instead of ending the turn with an apology.
        """
        followup = self._followup.get(self._current_session, False)
        window = self.follow_up_s if followup else WAKE_PATIENCE_S
        deadline = started_at + window
        first = True
        retries = 0
        while True:
            stt = self.backend.stt(base, cookie)
            self._set_live(True)
            try:
                if first and followup:
                    result = await asyncio.to_thread(stt.run, capture, patience_s=window)
                elif first:
                    result = await asyncio.to_thread(stt.run, capture)
                else:
                    remaining = max(0.5, deadline - self._clock())
                    result = await asyncio.to_thread(stt.run, capture, patience_s=remaining)
            except SttStreamError:
                # A stalled or dropped socket on this Wi-Fi is not the end of the turn: the capture
                # still holds the audio, so open a new stream while the window has time left.
                retries += 1
                if retries > STT_RECONNECTS or self._clock() >= deadline - 1.0:
                    raise
                LOG.warning(
                    "StackChan voice: the speech-to-text link dropped; reconnecting (%d of %d)",
                    retries,
                    STT_RECONNECTS,
                    exc_info=True,
                )
                first = False
                await asyncio.sleep(0.2)
                continue
            finally:
                self._set_live(False)
            first = False
            if (
                result.kind != "no_speech"
                or getattr(capture, "closed", False)
                or self._clock() >= deadline - 0.5
            ):
                return result
            LOG.info(
                "StackChan voice: no speech yet; listening on (%.1f s of patience left)",
                deadline - self._clock(),
            )

    def _log_uplink_level(self, session_id: str, capture) -> None:
        """One line per turn: how loud the microphone was, to tell "too quiet" from "not heard"."""
        try:
            LOG.info(
                "StackChan voice: uplink level peak %.2f, rms %.3f over the first 2 s",
                getattr(capture, "peak", 0.0),
                getattr(capture, "rms", 0.0),
            )
            folder = os.environ.get(DEBUG_WAV_ENV)
            saver = getattr(capture, "save_debug_wav", None)
            if folder and saver is not None:
                stamp = time.strftime("%Y%m%d-%H%M%S")
                path = saver(folder, f"uplink-{stamp}-{session_id[:8]}")
                if path is not None:
                    LOG.warning(
                        "StackChan voice: debug recording of the microphone written to %s "
                        "(%s is set; unset it to stop)",
                        path,
                        DEBUG_WAV_ENV,
                    )
        except Exception:
            LOG.warning("StackChan voice: the uplink level line failed", exc_info=True)

    def _record_uplink(self, nbytes: int, peak: float, *, detect: bool = False) -> None:
        if self.uplink_stats is None:
            return
        try:
            if detect:
                self.uplink_stats.record_detect()
            else:
                self.uplink_stats.record_frame(nbytes, peak)
        except Exception:  # a counter must never break the voice path
            LOG.warning("StackChan uplink counter failed", exc_info=True)

    live_sink_for = None  # optional: (active, unit) -> None, the live cue of the unit that is listening (set by the host for several units)

    def _set_live(self, active: bool) -> None:
        if self.live_sink is None:
            return
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        unit = ACTIVE_UNIT.get()
        if active:
            self._live_unit = unit
        elif unit is None:
            unit = getattr(self, "_live_unit", None)  # the end of a turn can run outside its unit's scope: end the cue on the unit that raised it
        self._light_side.submit(self._run_live_sink, active, unit)

    def _run_live_sink(self, active: bool, unit: str | None = None) -> None:
        try:
            if self.live_sink_for is not None:
                self.live_sink_for(active, unit)
            else:
                self.live_sink(active)
        except Exception:  # a light must never break the voice path
            LOG.warning("StackChan live cue failed", exc_info=True)

    def _emit_expression(self, state: str, *, mood: str | None = None) -> None:
        if self.expression_sink is None:
            return
        import contextvars

        # The side worker is another thread: carry the talking unit with the event, so the face goes only to the unit that asked.
        self._side.submit(contextvars.copy_context().run, self._run_expression_sink, state, mood)

    def _run_expression_sink(self, state: str, mood: str | None) -> None:
        try:
            self.expression_sink(state, mood=mood)
        except Exception:  # a failed face or head move never fails the answer
            LOG.warning("StackChan expression event failed", exc_info=True)

    def close(self) -> None:
        """Stop the side-effect worker; pending face and light updates are dropped."""
        self._side.shutdown(wait=False, cancel_futures=True)
        self._light_side.shutdown(wait=False, cancel_futures=True)

    def _speaker_evidence(self, stt_result) -> dict | None:
        try:
            # Keep compatibility with the original zero-argument injection,
            # while allowing a provider to inspect a hub STT result.
            try:
                signature = inspect.signature(self.person_attribution)
                takes_result = bool(signature.parameters)
            except (TypeError, ValueError):
                takes_result = True
            attribution = (
                self.person_attribution(stt_result) if takes_result else self.person_attribution()
            )
        except Exception:
            LOG.warning("StackChan person attribution failed", exc_info=True)
            return None
        if not attribution:
            return None
        if isinstance(attribution, dict):
            person_id = attribution.get("person_id") or attribution.get("person")
            confidence = attribution.get("confidence")
            basis = attribution.get("basis", "voice")
            level = attribution.get("level", confidence)
        else:
            person_id = getattr(attribution, "person_id", None)
            confidence = getattr(attribution, "confidence", None)
            basis = getattr(attribution, "basis", "voice")
            level = getattr(attribution, "level", confidence)
        if not person_id:
            return None
        # The household evidence contract permits only a calibrated confirmed
        # match to establish voice identity. Keep legacy numeric providers
        # behind the documented starting threshold until they return a level.
        if level == "tentative" or level == "unknown":
            return None
        if level != "confirmed" and (not isinstance(confidence, (int, float)) or confidence < 0.6):
            return None
        if basis != "voice":
            return None
        # SPEAK-02: the one strict spec-shape builder. A numeric legacy
        # confidence that cleared the bar above is a `confirmed` match.
        if level != "confirmed":
            level = "confirmed"
        try:
            return speaker_evidence(person_id, basis, level)
        except SpeakerEvidenceError:
            LOG.warning("StackChan attribution dropped: malformed person id %r", person_id)
            return None

    # The three client factories live on the backend; the older names stay (tests and callers replace them).
    @property
    def stt_factory(self):
        return self.backend.stt_factory

    @stt_factory.setter
    def stt_factory(self, value) -> None:
        self.backend.stt_factory = value

    @property
    def turn_factory(self):
        return self.backend.turn_factory

    @turn_factory.setter
    def turn_factory(self, value) -> None:
        self.backend.turn_factory = value

    @property
    def tts_factory(self):
        return self.backend.tts_factory

    @tts_factory.setter
    def tts_factory(self, value) -> None:
        self.backend.tts_factory = value

    @staticmethod
    def _local_speech_from(units):
        """(stt_url, tts_url, timeout, llm) when robot.toml sets a model and the brain is not Home:
        the host then runs with no Home. A missing speech address means the built-in engine."""
        base = getattr(units, "base", None)
        llm = getattr(base, "llm", None)
        if llm is None or getattr(base, "brain", "llm") == "home":
            return None
        if llm.url:
            return llm.stt_url or None, llm.tts_url or None, float(llm.timeout_seconds), llm
        return None

    def _noise_level(self, device_id: str) -> str:
        from maipai_body.speech.noise_gate import level_from

        store = getattr(self.units, "store", None)
        return level_from(store.get(device_id).get("ignore_noise") if store is not None else None)

    def _gate_result(self, result, device_id: str):
        """Drop what is not a person talking to the robot; every drop is logged with its reason."""
        from maipai_body.speech.noise_gate import check_audio, check_text

        if result.kind != "final":
            return result
        level = self._noise_level(device_id)
        verdict = None
        audio = getattr(result, "audio", None)
        if self.audio_noise_gate and audio is not None and len(audio):
            verdict = check_audio(audio, level)
        if verdict is None or verdict.keep:
            verdict = check_text(result.text or "", self.language)
        if verdict.keep:
            return result
        self.dropped_utterances += 1
        LOG.info(
            "StackChan voice: dropped an utterance (%s); noise level %s, %d characters",
            verdict.reason,
            level,
            len(result.text or ""),
        )
        from maipai_body.speech.stt_stream import SttStreamResult

        return SttStreamResult(kind="no_speech")

    def _log_utterance(self, result, outcome: str, device_id: str) -> None:
        """One line per utterance: engine, confidence, route and why. The words themselves are
        logged only when MAIPAI_STACKCHAN_LOG_UTTERANCES=1 (they are never kept otherwise)."""
        if result.kind != "final":
            return
        text = result.text or ""
        route, why = self._route_of(text, outcome, device_id)
        shown = repr(text) if os.environ.get("MAIPAI_STACKCHAN_LOG_UTTERANCES") == "1" else (
            f"({len(text.split())} words)"
        )
        LOG.info(
            "StackChan utterance: %s engine=%s confidence=%s route=%s (%s)",
            shown,
            getattr(result, "engine", "unknown"),
            getattr(result, "confidence", None),
            route,
            why,
        )

    def _route_of(self, text: str, outcome: str, device_id: str = "") -> tuple[str, str]:
        """Where this utterance goes: a local command (and which), or the chat model."""
        if outcome != "speech":
            return "none", f"classified {outcome}"
        from maipai_body.bodies.stackchan import brightness as bright
        from maipai_body.bodies.stackchan.head_commands import parse_head_command
        from maipai_body.bodies.stackchan.stop_phrases import is_stop_phrase
        from maipai_body.bodies.stackchan.volume import parse_volume_command

        if is_stop_phrase(text):
            return "local command", "stop phrase on the fixed list"
        lock = getattr(self, "lock_control", None)
        if lock is not None and lock.parse(text) is not None:
            return "local command", "lock word on the fixed list"
        talk = getattr(self, "talk_games", None)
        if talk is not None and talk.parse(text, device_id) is not None:
            return "local command", "talk game start or end wording found"
        if self.volume_control is not None and parse_volume_command(text) is not None:
            return "local command", "volume wording found"
        if self.brightness_control is not None and bright.parse_brightness_command(text):
            return "local command", "brightness wording found"
        if self.head_control is not None and parse_head_command(text) is not None:
            return "local command", "head movement wording found"
        if self.alarm_control is not None and self.alarm_control.parse(text) is not None:
            return "local command", "alarm or timer wording found"
        return "chat", "no local command wording; the model answers"

    def _turn_for(self, device_id: str, base, cookie):
        """This unit's turn client: its own model when it chose one, else the Home turn client."""
        if self.units is not None and self.units.has_own_llm(device_id):
            return self.units.turn_for(device_id)
        return self.backend.turn(base, cookie)

    def _unit_pitch(self, device_id: str) -> float:
        """The voice record's offset plus this unit's own pitch setting."""
        own = self.units.speech_pitch_for(device_id) if self.units is not None else 0.0
        return float(self.pitch_semitones()) + own

    def _unit_speed(self, device_id: str) -> float:
        return self.units.speech_speed_for(device_id) if self.units is not None else 1.0

    def _volume_cap(self, device_id: str) -> int | None:
        return self.units.volume_cap_for(device_id) if self.units is not None else None

    async def _run(self, session_id: str, device_id: str, capture: StackChanAudioCapture) -> None:
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        token = ACTIVE_UNIT.set(device_id)  # calls that name no unit during this turn go to the talking unit
        with self._inflight_lock:
            self._inflight += 1
            busy = self._inflight > self.busy_at
        try:
            if busy:
                self._say_busy(session_id)
            await self._run_inner(session_id, device_id, capture)
        finally:
            with self._inflight_lock:
                self._inflight -= 1
            ACTIVE_UNIT.reset(token)

    def _say_busy(self, session_id: str) -> None:
        """Many robots are asking at once: this turn waits its turn for a worker, and the unit is told so in plain words (its caption and
        error tone) instead of staying silent."""
        playback = self._playbacks.get(session_id)
        LOG.info("StackChan voice: %d turns at once; this one waits for a free worker", self._inflight)
        if self.on_error_line is not None:
            try:
                self.on_error_line()
            except Exception:
                LOG.debug("StackChan busy earcon failed", exc_info=True)
        if playback is not None:
            self._caption(playback, BUSY_LINE)

    async def _run_inner(self, session_id: str, device_id: str, capture: StackChanAudioCapture) -> None:
        try:
            playback = StackChanAudioPlayback(
                self.server,
                device_id,
                clock=self._clock,
                pitch_semitones=lambda d=device_id: self._unit_pitch(d),
                speech_speed=lambda d=device_id: self._unit_speed(d),
            )
        except TypeError:
            playback = StackChanAudioPlayback(self.server, device_id)
        playback.mouth_cues_on = True
        self._playbacks[session_id] = playback
        cancel_event = threading.Event()
        self._cancel_events[session_id] = cancel_event
        playback._cancel_event = cancel_event
        self._emit_expression("listening")
        self._settled_sessions.discard(session_id)
        started_at = self._clock()
        LOG.info("StackChan voice: turn started for session %s", session_id[:8])
        try:
            cookie = self.link.hub_client.session_cookie
            pairing = self.link.pairing_store.load()
            base = getattr(self.link.hub_client, "active_base_url", None) or (
                pairing.base_url if pairing else None
            )
            if self.backend.local:
                base, cookie = "local", "local"
                store = getattr(self.units, "store", None)
                level = store.get(device_id).get("wait_after_talking") if store else None
                self._wait_level = level if level in ("quick", "normal", "patient") else "quick"
            if not cookie or not base:
                LOG.warning(
                    "StackChan voice: no hub session (cookie %s, address %s); answering with the "
                    "offline line. Pair the Bot with the hub or check that the hub is reachable.",
                    "present" if cookie else "missing",
                    "present" if base else "missing",
                )
                self._emit_expression("thinking")
                await asyncio.to_thread(self._offline_line, playback)
                return
            self._current_session = session_id
            result = await self._recognize(base, cookie, capture, started_at)
            result = self._gate_result(result, device_id)
            self._log_uplink_level(session_id, capture)
            capture.close()  # recognition is over: stop buffering the microphone
            last_loud = getattr(capture, "last_loud_at", None)
            after = (
                f", {time.monotonic() - last_loud:.1f} s after the last loud sound"
                if last_loud is not None
                else ""
            )
            LOG.info(
                "StackChan voice: speech-to-text ended (%s, %d characters%s)",
                result.kind,
                len(result.text or ""),
                after,
            )
            outcome = self._classify(result)
            self._log_utterance(result, outcome, device_id)
            if outcome == "speech":
                from maipai_body.bodies.stackchan.stop_phrases import is_stop_phrase, normalize

                stop = is_stop_phrase(result.text)
                heard = normalize(result.text)
                # The log never holds what a person said: a matched stop phrase comes from a fixed
                # list and is named, anything else is only counted in words.
                LOG.info(
                    "StackChan voice: stop check %s -> %s",
                    repr(heard) if stop else f"({len(heard.split())} words)",
                    "yes" if stop else "no",
                )
                if stop:
                    if self.talk_games is not None:
                        self.talk_games.on_stop_phrase(device_id, result.text)  # "that's enough" also ends a talk game
                    # "Stop", "never mind", "be quiet": end the turn here, nothing is said.
                    LOG.info("StackChan voice: stop phrase heard; going idle without the hub")
                    self._quiet_streak = 0
                    await self._go_idle(device_id)
                    return
            if outcome == "speech":
                self._breaker.note_real_final()
                self._quiet_streak = 0
                self._notify(self.on_user_words, result.text)
            if outcome == "silence":
                # Nobody spoke (or it was not speech): end quietly and let the device go idle.
                await self._end_quietly(session_id, device_id)
                return
            self._emit_expression("thinking")
            if outcome == "failed":
                await asyncio.to_thread(self._speak_plain_error, playback, base, cookie)
                return
            if self.repeat_control is not None and await self._answer_repeat(
                result, session_id, playback, base, cookie
            ):
                return
            if self.lock_control is not None:
                lock_command = self.lock_control.parse(result.text or "")
                if lock_command is not None:
                    # Only the word "lock". A spoken code is never taken (lock_voice.py); the words are not logged.
                    line = await asyncio.to_thread(self.lock_control.run, lock_command, device_id)
                    LOG.info("StackChan voice: lock command")
                    if line:
                        await asyncio.to_thread(self._say, playback, base, cookie, line)
                        self._breaker.note_speech()
                    self._quiet_idle.add(session_id)
                    await self._go_idle(device_id)
                    return
            if self.alarm_control is not None:
                alarm_command = self.alarm_control.parse(result.text or "")
                if alarm_command is not None:
                    line = await asyncio.to_thread(self.alarm_control.run, alarm_command)
                    LOG.info("StackChan voice: alarm command %s (%r)", alarm_command.kind, line)
                    await asyncio.to_thread(self._say, playback, base, cookie, line)
                    self._breaker.note_speech()
                    return
            if self.brightness_control is not None:
                from maipai_body.bodies.stackchan import brightness as bright

                bright_command = bright.parse_brightness_command(result.text or "")
                if bright_command is not None:
                    before, after = await asyncio.to_thread(
                        self.brightness_control.apply, bright_command
                    )
                    LOG.info(
                        "StackChan voice: brightness command %s (%d -> %d)",
                        bright_command.kind,
                        before,
                        after,
                    )
                    line = bright.confirmation(bright_command, before, after)
                    await asyncio.to_thread(self._say, playback, base, cookie, line)
                    self._breaker.note_speech()
                    return
            if self.volume_control is not None:
                from maipai_body.bodies.stackchan.volume import confirmation, parse_volume_command

                command = parse_volume_command(result.text or "")
                if command is not None:
                    cap = self._volume_cap(device_id)
                    capped = (cap,) if cap is not None else ()
                    before, after = await asyncio.to_thread(
                        self.volume_control.apply, command, *capped
                    )
                    LOG.info(
                        "StackChan voice: volume command %s (%d -> %d)", command.kind, before, after
                    )
                    line = confirmation(command, before, after)
                    if line:
                        await asyncio.to_thread(self._say, playback, base, cookie, line)
                        self._breaker.note_speech()
                    return
            if self.talk_games is not None:
                talk_command = self.talk_games.parse(result.text or "", device_id)
                if talk_command is not None:
                    line = await asyncio.to_thread(self.talk_games.run, talk_command, device_id)
                    LOG.info("StackChan voice: talk game %s %s", talk_command.kind, talk_command.game or "")
                    if line:
                        await asyncio.to_thread(self._say, playback, base, cookie, line)
                        self._breaker.note_speech()
                    return
            if self.head_control is not None:
                from maipai_body.bodies.stackchan.head_commands import parse_head_command

                head_command = parse_head_command(result.text or "")
                if head_command is not None:
                    line = await asyncio.to_thread(self.head_control.run, head_command)
                    LOG.info("StackChan voice: head command %s (%r)", head_command.kind, line)
                    if line:
                        await asyncio.to_thread(self._say, playback, base, cookie, line)
                        self._breaker.note_speech()
                    if head_command.kind in ("face", "dance", "game"):
                        # "Dance" ends the turn the same way: the dance starts once the turn is
                        # over (never during one). "Turn to me": end the follow-up listening now.
                        # The camera sends no frames
                        # while the unit listens or speaks, so the look for the face can only start
                        # (and see) once the unit is idle; it begins on the next presence tick.
                        LOG.info("StackChan voice: face request answered; going idle for the look")
                        self._quiet_idle.add(session_id)
                        await self._go_idle(device_id)
                    return
            if self.gaze_control is not None:
                gaze_line = self.gaze_control.answer(result.text or "")
                if gaze_line:
                    LOG.info("StackChan voice: gaze question answered (%r)", gaze_line)
                    await asyncio.to_thread(self._say, playback, base, cookie, gaze_line)
                    self._breaker.note_speech()
                    return
            if self.sight_control is not None:
                sight_kind = self.sight_control.kind(result.text or "")
                described = False
                quick = None
                if sight_kind == "picture":
                    # The robot's own fast pass answers at once ("I see a person and a laptop");
                    # Home's detailed sentence follows through the normal turn. The words are
                    # never logged, only that there were some.
                    quick_look = getattr(self.sight_control, "quick_look", None)
                    quick = quick_look() if callable(quick_look) else None
                    if quick:
                        LOG.info("StackChan voice: quick look answered from the robot's own pass")
                        await asyncio.to_thread(self._say, playback, base, cookie, quick)
                        self._breaker.note_speech()
                if sight_kind in {"see_me", "picture"} and self.vision_ask is not None:
                    # Ask Home to describe one picture now; the hub then answers the question
                    # itself with that description in the turn's context (nothing here keeps it).
                    # Light questions never cost a model call: the host reads the brightness.
                    described = bool(await asyncio.to_thread(self.vision_ask, sight_kind))
                    LOG.info(
                        "StackChan voice: sight question (%s): %s",
                        sight_kind,
                        "Home described a picture" if described else "no description, host answer",
                    )
                if quick and not described:
                    return  # the quick look was the answer; nothing more to add
                sight_line = None if described else self.sight_control.answer(result.text or "")
                if sight_line:
                    LOG.info("StackChan voice: sight question answered (%r)", sight_line)
                    await asyncio.to_thread(self._say, playback, base, cookie, sight_line)
                    self._breaker.note_speech()
                    return
            turn = self._turn_for(device_id, base, cookie)
            if self.talk_games is not None:
                rules = self.talk_games.begin_turn(device_id)
                if rules:
                    from maipai_body.bodies.stackchan.talk_games import GameTurn

                    own = self.units is not None and self.units.has_own_llm(device_id)
                    turn = GameTurn(turn, rules, persona_path=own)
            await self._stream_reply(
                session_id, turn, result, playback, cancel_event, base, cookie, device_id=device_id
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOG.warning("StackChan voice turn failed: %s: %s", type(exc).__name__, str(exc)[:160])
            LOG.debug("StackChan voice turn failure detail", exc_info=True)
            if isinstance(exc, (TurnAuthFailed, TurnLinkLost)) and await self._pantry_game_turn(device_id, result, playback, base, cookie):
                pass  # a riddle or trivia game went on from the pantry library
            elif isinstance(exc, (TurnAuthFailed, TurnLinkLost, TtsAuthFailed)):
                await asyncio.to_thread(self._offline_line, playback)
            else:
                await asyncio.to_thread(self._speak_plain_error, playback, base, cookie)
        finally:
            if self._states.get(session_id) == "speaking":
                # A reply that ended abnormally must not leave the mouth open.
                try:
                    await self.server.stop_audio(device_id)
                except Exception:
                    LOG.debug(
                        "StackChan voice: tts stop after an abnormal end failed", exc_info=True
                    )
            self._last_turn_end[session_id] = self._clock()
            if session_id not in self._settled_sessions:
                self._emit_expression("settle")
            self._states[session_id] = "idle"
            self._notify(self.on_turn_end, None)
            self._settled_sessions.discard(session_id)
            # A newer listen start replaces these entries before this task's cleanup runs; only
            # remove what is still this run's own, or the new turn loses its capture.
            if self._captures.get(session_id) is capture:
                self._captures.pop(session_id, None)
            if self._tasks.get(session_id) is asyncio.current_task():
                self._tasks.pop(session_id, None)
            if self._playbacks.get(session_id) is playback:
                self._playbacks.pop(session_id, None)
            if self._cancel_events.get(session_id) is cancel_event:
                self._cancel_events.pop(session_id, None)
            frames, size = self._audio_stats.pop(session_id, [0, 0])
            LOG.info(
                "StackChan voice: turn ended after %.1f s (%d audio frames, %d bytes)",
                self._clock() - started_at,
                frames,
                size,
            )

    def _unit_prefs(self, device_id: str) -> dict:
        try:
            return dict(self.prefs_for(device_id)) if self.prefs_for is not None else {}
        except Exception:
            LOG.debug("StackChan voice: unit preferences unreadable; using defaults", exc_info=True)
            return {}

    def _overlay_cue(self, device_id: str, cue) -> None:
        """Start or end an overlay named in the reply. Privacy and sleep outrank decoration; never raises."""
        director = self.overlay_director
        if director is None or not device_id:
            return
        if cue.kind == "overlay" and (self.muted_reason() is not None or self.decoration_blocked()):
            return

        def run() -> None:
            try:
                if cue.kind == "overlay":
                    director.set(device_id, cue.name, cue.intensity, cue.seconds or reply_tags.DEFAULT_SECONDS)
                else:
                    director.clear(device_id)
            except Exception:
                LOG.debug("StackChan voice: overlay cue failed", exc_info=True)

        self._side.submit(run)

    def show_mood(self, cue_name: str) -> None:
        """Draw a mood on the face now (the settings page's scene Test); ``cue_name`` is an expression cue such as ``happiness``."""
        self._emit_expression("reply_mood", mood=cue_name)

    def _bus_cue(self, device_id: str, cue, budget) -> str | None:
        """Send one decoration cue from the reply through the command bus as the model's request. Returns the mood a scene may set
        (the caller draws it unless the reply named a mood itself). Never raises; the unit calls run off this thread."""
        bus = self.command_bus
        if bus is None or not device_id:
            return None
        from maipai_body.command_bus import Command

        if cue.kind == "overlay":
            command = Command("fx.set", {"name": cue.name, "intensity": cue.intensity, "seconds": cue.seconds or reply_tags.DEFAULT_SECONDS})
        elif cue.kind == "overlay_end":
            command = Command("fx.clear")
        elif cue.kind == "scene":
            command = Command("scene.set", {"name": cue.name})
        elif cue.kind == "scene_off":
            command = Command("scene.clear")
        elif cue.kind == "sound":
            command = Command("sound.play", {"name": cue.name})
        elif cue.kind == "light":
            command = Command("light.look", {"color": cue.name, "seconds": cue.seconds or reply_tags.DEFAULT_LIGHT_S})
        else:
            return None
        deferred: list = []
        try:
            result = bus.send(device_id, command, budget, defer=deferred)
        except Exception:
            LOG.debug("StackChan voice: decoration cue failed", exc_info=True)
            return None

        def run() -> None:
            for execute, device, args in deferred:
                try:
                    execute(device, args)
                except Exception:
                    LOG.debug("StackChan voice: decoration call failed", exc_info=True)

        if deferred:
            self._side.submit(run)
        return result.mood if command.cmd == "scene.set" else None

    async def _stream_reply(
        self,
        session_id: str,
        turn,
        result,
        playback,
        cancel_event,
        base: str,
        cookie: str,
        device_id: str = "",
    ) -> None:
        """Ask for the reply and speak it sentence by sentence while it is still being written.

        A reader thread turns the brain's events into whole, tag-free sentences on a queue; this
        coroutine speaks them in order. A brain that sends no pieces (one final reply) is spoken
        from that reply the same way, just later.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        chat_started = self._clock()
        marks: dict[str, float] = {}
        info: dict = {"turn_id": None}

        def put(item) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, item)

        def cancel_hub_turn() -> None:
            tid = info["turn_id"]
            if tid:
                try:
                    turn.cancel(tid)
                except Exception:
                    LOG.debug("StackChan voice: hub turn cancel failed", exc_info=True)

        prefs = self._unit_prefs(device_id)
        emotion_on = prefs.get("emotion_faces", True) is not False
        overlays_on = prefs.get("overlays_enabled", True) is not False
        filler_mode = prefs.get("filler_mode", "tone")
        filler_wait = float(prefs.get("filler_wait_s", 0.4))

        def put_items(items) -> None:
            for item in items:
                if item.cues:
                    put(("cues", item.cues))
                if item.text:
                    put(("sentence", item.text))

        def _drain() -> None:
            events: list = []
            tagger = ReplyTagger(moods=emotion_on, overlays=overlays_on)
            error: BaseException | None = None
            try:
                evidence = self._speaker_evidence(result)
                for event in turn.stream(result.text, speaker_evidence=evidence):
                    events.append(event)
                    tid = getattr(event, "turn_id", None)
                    if tid:
                        info["turn_id"] = tid
                    if cancel_event.is_set():
                        # A stop must end the hub's generation too, not only our playback.
                        cancel_hub_turn()
                        break
                    if emotion_on and getattr(getattr(event, "cue", None), "expressed_emotion", None):
                        put(("mood", event))
                    delta = getattr(event, "delta_text", None)
                    if not delta:
                        continue
                    marks.setdefault("first_token", self._clock())
                    put_items(tagger.feed(delta, whole=bool(getattr(event, "delta_whole", False))))
                if not cancel_event.is_set():
                    put_items(tagger.flush())
            except BaseException as exc:  # reported to the speaking side, never lost
                error = exc
            finally:
                put(("end", events, error, tagger.tags))

        reader = loop.run_in_executor(None, _drain)
        spoken: list[str] = []
        events: list = []
        error: BaseException | None = None
        tags: list[str] = []
        mood_event = None
        mood_sent = None
        filler_sent = False
        filler_played = False
        tts = None
        finished = False

        def apply_mood() -> None:
            nonlocal mood_sent
            cue = getattr(mood_event, "cue", None)
            mood = getattr(cue, "expressed_emotion", None)
            if not mood or mood == mood_sent:
                return
            mood_sent = mood
            excitement = bool(
                getattr(cue, "excitement", False) or getattr(cue, "expressed_excitement", False)
            )
            self._emit_expression(
                "reply_mood", mood="joy" if mood == "happiness" and excitement else mood
            )
            self._notify(self.on_reply_mood, mood)

        reply_budget = self.command_bus.new_reply() if self.command_bus is not None else None
        named_mood = False  # the reply named a mood itself: a scene's mood never replaces it

        def run_cues(cues) -> None:
            nonlocal mood_event, named_mood
            for cue in cues:
                scene_mood = None
                if cue.kind == "mood":
                    named_mood = True
                    mood = cue.name
                elif self.command_bus is not None:
                    scene_mood = self._bus_cue(device_id, cue, reply_budget)
                    mood = scene_mood if scene_mood and not named_mood else None
                elif cue.kind in ("overlay", "overlay_end"):
                    self._overlay_cue(device_id, cue)
                    continue
                else:
                    continue
                if mood:
                    mood_event = SimpleNamespace(
                        cue=SimpleNamespace(expressed_emotion=reply_tags.MOOD_CUE[mood])
                    )
                    if spoken:
                        apply_mood()

        async def speak(sentence: str) -> bool:
            nonlocal tts
            index = len(spoken)
            if tts is None:
                tts = self.backend.tts(base, cookie, playback)
            if index == 0:
                now = self._clock()
                marks["first_sentence"] = now
                LOG.info(
                    "StackChan voice: first sentence ready %.2f s after the request "
                    "(first token %s)",
                    now - chat_started,
                    f"{marks['first_token'] - chat_started:.2f} s"
                    if "first_token" in marks
                    else "not streamed",
                )
                apply_mood()

                def first_audio() -> None:
                    marks["first_audio"] = self._clock()
                    LOG.info(
                        "StackChan voice: first audio %.2f s after the request",
                        marks["first_audio"] - chat_started,
                    )
                    self._emit_expression("speaking")

                # The face talks as the first frames reach the unit, not at synthesis.
                playback.on_first_audio = first_audio
            self._states[session_id] = "speaking"
            self._speaking_since[session_id] = self._clock()
            spoke_at = self._clock()
            LOG.info(
                "StackChan voice: text-to-speech sentence %d started (%d characters)",
                index + 1,
                len(sentence),
            )
            self._caption(playback, sentence)
            await asyncio.to_thread(tts.speak, sentence, stop_event=cancel_event)
            synthesized_at = self._clock()
            if cancel_event.is_set():
                return False
            if index == 0 and hasattr(playback, "decide_cues"):
                # One list per reply: only a reply that ends with this sentence gets host cues.
                waiting = list(getattr(queue, "_queue", ()))
                playback.decide_cues(
                    bool(waiting) and all(item[0] == "end" for item in waiting)
                )
            spoken.append(sentence)
            # The reply is one paced stream: this sentence's tail is flushed and the sender
            # carries on while the next sentence is synthesized (no stop() per sentence).
            end_sentence = getattr(playback, "end_sentence", None)
            if end_sentence is not None:
                await asyncio.to_thread(end_sentence)
            else:
                await asyncio.to_thread(playback.stop)
            LOG.info(
                "StackChan voice: sentence %d synthesized in %.1f s",
                index + 1,
                synthesized_at - spoke_at,
            )
            return True

        try:
            while not finished:
                want_filler = (
                    self.filler_player is not None
                    and filler_mode in ("tone", "phrase")
                    and not filler_played
                    and not spoken
                )
                try:
                    item = await asyncio.wait_for(
                        queue.get(), timeout=0.05 if want_filler else 0.2
                    )
                except TimeoutError:
                    if cancel_event.is_set():
                        cancel_hub_turn()
                        return
                    if (
                        want_filler
                        and "first_audio" not in marks
                        and self._clock() - chat_started >= filler_wait
                        and self.muted_reason() is None
                    ):
                        # No first audio yet: one short non-word sound or tone, once per turn.
                        filler_played = True
                        try:
                            await asyncio.to_thread(
                                self.filler_player.play,
                                playback,
                                device_id,
                                filler_mode,
                                self.language,
                            )
                        except Exception:  # a failed filler never fails the answer
                            LOG.debug("StackChan voice: filler sound failed", exc_info=True)
                    if (
                        not filler_sent
                        and not spoken
                        and self._clock() - chat_started >= self.filler_after_s
                    ):
                        # No first sentence yet: show the thinking cue once more, and call the
                        # filler-sound hook if one is wired (none ships yet).
                        filler_sent = True
                        LOG.info(
                            "StackChan voice: no sentence after %.1f s; thinking cue",
                            self.filler_after_s,
                        )
                        self._emit_expression("thinking")
                        self._notify(self.on_slow_reply, None)
                    continue
                kind = item[0]
                if kind == "mood":
                    mood_event = item[1]
                    if spoken:
                        apply_mood()
                elif kind == "cues":
                    run_cues(item[1])
                elif kind == "sentence":
                    if asyncio.current_task().cancelling() or cancel_event.is_set():
                        return
                    if not await speak(item[1]):
                        return
                else:
                    _, events, error, tags = item
                    finished = True
            await reader
        finally:
            if not finished:
                cancel_event.set()  # this turn was canceled: let the reader thread stop too
        if cancel_event.is_set():
            return
        reply = next((e.reply_text for e in reversed(events) if e.reply_text), None)
        LOG.info(
            "StackChan voice: chat ended in %.1f s (%d events, %d sentences spoken, "
            "%d tags dropped%s)",
            self._clock() - chat_started,
            len(events),
            len(spoken),
            len(tags),
            "" if error is None else f", ended with {type(error).__name__}",
        )
        if error is not None and not spoken:
            raise error
        if not spoken and error is None:
            # Not streamed (or a built-in answer): the final reply is split and spoken here.
            if reply:
                tagger = ReplyTagger(moods=emotion_on, overlays=overlays_on)
                parsed = [*tagger.feed(reply), *tagger.flush()]
                mood_event = next(
                    (
                        e
                        for e in reversed(events)
                        if getattr(getattr(e, "cue", None), "expressed_emotion", None)
                    ),
                    mood_event,
                )
                for part in parsed:
                    run_cues(part.cues)
                    if part.text and (
                        asyncio.current_task().cancelling() or not await speak(part.text)
                    ):
                        return
        if not spoken:
            await asyncio.to_thread(self._speak_plain_error, playback, base, cookie)
            return
        apply_mood()
        if error is not None:
            LOG.warning(
                "StackChan voice: the reply stopped early (%s); spoke %d sentences, then the "
                "plain failure line",
                type(error).__name__,
                len(spoken),
            )
            await asyncio.to_thread(self._speak_plain_error, playback, base, cookie)
            self._states[session_id] = "listening"
            return
        if getattr(playback, "end_sentence", None) is not None:
            # stop() sends what is left and waits on this event loop's own coroutine, so it
            # must run off the loop: inline it deadlocked until its 30 s timeout.
            finish_started = self._clock()
            await asyncio.to_thread(playback.stop)
            LOG.info(
                "StackChan voice: reply sent to the device %.1f s after the last "
                "sentence was synthesized",
                self._clock() - finish_started,
            )
        self._keep_for_repeat(session_id, " ".join(spoken), playback, result)
        await asyncio.to_thread(playback.end)
        self._states[session_id] = "listening"
        self._speech_ended[session_id] = self._clock()
        self._breaker.note_speech()
        LOG.info("StackChan voice: reply finished playing")

    def _speaker_person(self, result) -> str | None:
        evidence = self._speaker_evidence(result)
        person = evidence.get("person") if evidence else None
        return person if isinstance(person, str) else None

    def _keep_for_repeat(self, session_id: str, reply: str, playback, result) -> None:
        """Remember this reply (text and the frames sent) for "say that again"; memory only."""
        control = self.repeat_control
        if control is not None and control.muted():
            return
        frames = getattr(playback, "recorded_frames", None)
        if control is None or not control.enabled or not callable(frames):
            return
        try:
            control.record(session_id, reply, frames(), self._speaker_person(result))
        except Exception:
            LOG.warning("StackChan voice: could not keep the reply for repeat", exc_info=True)

    async def _answer_repeat(self, result, session_id: str, playback, base, cookie) -> bool:
        """True when "say that again" or "what did I miss" was answered here, without the hub."""
        control = self.repeat_control
        command = control.parse(result.text or "")
        if command is None:
            return False
        answer = control.answer(command, session_id, self._speaker_person(result))
        if answer is None:
            return False
        LOG.info(
            "StackChan voice: repeat command %s answered on the robot (%s)",
            command.kind,
            answer.kind,
        )
        if answer.kind == "say":
            await asyncio.to_thread(self._say, playback, base, cookie, answer.line)
            if answer.clear_missed:
                control.missed.clear()
            self._breaker.note_speech()
        elif answer.kind == "replay":
            await self._replay(session_id, playback, answer)
        return True

    async def _replay(self, session_id: str, playback, answer) -> None:
        from maipai_body.bodies.stackchan.volume import VolumeCommand

        restore = None
        if answer.louder and self.volume_control is not None:
            before, after = await asyncio.to_thread(self.volume_control.apply, VolumeCommand("up"))
            restore = before if after != before else None
        playback.on_first_audio = lambda: self._emit_expression("speaking")
        self._states[session_id] = "speaking"
        self._speaking_since[session_id] = self._clock()
        try:
            await asyncio.to_thread(playback.replay_frames, list(answer.frames))
            await asyncio.to_thread(playback.end)
        finally:
            if restore is not None:
                try:
                    await asyncio.to_thread(
                        self.volume_control.apply, VolumeCommand("set", restore)
                    )
                except Exception:
                    LOG.warning("StackChan voice: could not put the volume back", exc_info=True)
        self._states[session_id] = "listening"
        self._speech_ended[session_id] = self._clock()
        self._breaker.note_speech()
        LOG.info("StackChan voice: last reply replayed (%d packets)", len(answer.frames))

    def _notify(self, hook, value) -> None:
        """Call an optional hook; a hook can never break the voice path."""
        if hook is None:
            return
        try:
            hook(value)
        except Exception:
            LOG.warning("StackChan voice hook failed", exc_info=True)

    def speak_reaction(self, text: str, device_id: str | None = None) -> bool:
        """Say one short line on the robot's own initiative (not an answer). False if it cannot.

        It speaks through the same text-to-speech path as a reply, and never while a turn is on or
        a reply is playing: the line is dropped, not queued. Never while muted or in full quiet.
        With ``device_id`` (a unit after the first, docs/plan/per-unit-behavior.md) the line goes to that unit and only that
        unit's own turn, speech and mute decide: another unit mid-turn does not silence it. Without it, one connected unit is needed."""
        sessions = getattr(self.server, "_sessions", None)
        if device_id is not None:
            from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

            if not sessions or device_id not in sessions:
                return False
            token = ACTIVE_UNIT.set(device_id)  # the unit's own mute and full quiet decide
            try:
                if self.muted_reason() is not None:
                    return False
            finally:
                ACTIVE_UNIT.reset(token)
            if device_id in self._tasks or self._states.get(device_id) == "speaking":
                return False
            unit_reaction = True
        else:
            if self.muted_reason() is not None:
                return False
            if self._tasks or any(state == "speaking" for state in self._states.values()):
                return False
            if not sessions or len(sessions) != 1:
                return False
            device_id = next(iter(sessions))
            unit_reaction = False
        try:
            cookie = self.link.hub_client.session_cookie
            pairing = self.link.pairing_store.load()
            base = getattr(self.link.hub_client, "active_base_url", None) or (
                pairing.base_url if pairing else None
            )
            if self.backend.local:
                base, cookie = "local", "local"
            if not cookie or not base:
                return False
            try:
                playback = StackChanAudioPlayback(
                    self.server,
                    device_id,
                    clock=self._clock,
                    pitch_semitones=lambda d=device_id: self._unit_pitch(d),
                speech_speed=lambda d=device_id: self._unit_speed(d),
                )
            except TypeError:
                playback = StackChanAudioPlayback(self.server, device_id)
        except Exception:
            LOG.warning("StackChan reaction line could not start", exc_info=True)
            return False
        with self._reaction_lock:
            if unit_reaction:
                if device_id in self._reaction_units:
                    return False
                self._reaction_units.add(device_id)
            else:
                if self._reaction_speaking:
                    return False
                self._reaction_speaking = True
        threading.Thread(
            target=self._say_unit_reaction if unit_reaction else self._say_reaction,
            args=(playback, base, cookie, text) + ((device_id,) if unit_reaction else ()),
            name="stackchan-reaction-speech",
            daemon=True,
        ).start()
        return True

    @staticmethod
    def _caption(playback, text: str) -> None:
        """Tell the playback which words the next audio speaks (the unit's subtitles); never fails a reply."""
        mark = getattr(playback, "caption", None)
        if mark is None or not text:
            return
        try:
            mark(text)
        except Exception:
            LOG.debug("StackChan caption skipped", exc_info=True)

    def _say_unit_reaction(self, playback, base: str, cookie: str, text: str, device_id: str) -> None:
        """A reaction line on a unit after the first: only that unit's flag is held, and no turn-end hook runs (that hook is the first unit's)."""
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        token = ACTIVE_UNIT.set(device_id)
        try:
            self._say(playback, base, cookie, text)
        finally:
            ACTIVE_UNIT.reset(token)
            with self._reaction_lock:
                self._reaction_units.discard(device_id)

    def _say_reaction(self, playback, base: str, cookie: str, text: str) -> None:
        try:
            self._say(playback, base, cookie, text)
        finally:
            self._reaction_speaking = False
            self._reaction_ended_at = self._clock()
            self._notify(self.on_turn_end, None)

    async def _pantry_game_turn(self, device_id, result, playback, base, cookie) -> bool:
        """The model is out of reach in the middle of a riddle or trivia game: play the turn from the pantry library (docs/design/model-games.md, S1). False when it cannot."""
        try:
            if self.talk_fallback is None or self.talk_games is None:
                return False
            state = self.talk_games.state(device_id)
            if state is None or not self.talk_fallback.supports(state.game):
                return False
            out = await asyncio.to_thread(self.talk_fallback.line, device_id, state.game, state.lang, getattr(result, "text", "") or "", state.started)
            if out is None:
                return False
            line, scored = out
            if scored:
                self.talk_games.add_point(device_id)
            await asyncio.to_thread(self._say, playback, base, cookie, line)
            self._breaker.note_speech()
            return True
        except Exception as exc:  # the usual offline line follows
            LOG.warning("StackChan pantry game turn failed: %s", type(exc).__name__)
            return False

    def _offline_line(self, playback) -> None:
        if not self._breaker.allow():  # a canned error line: same loop breaker as the apology
            return
        try:
            from pathlib import Path

            from maipai_body.speech.offline_clips import OfflineSpeaker, ensure_clip_bundle

            cache = self.cache_dir or (Path.home() / ".cache" / "maipai-body")
            speaker = OfflineSpeaker(ensure_clip_bundle(cache), playback)
            try:
                self._caption(playback, speaker.selected_text(UNREACHABLE) or "")
            except Exception:
                LOG.debug("StackChan offline caption skipped", exc_info=True)
            speaker.say_phrase(UNREACHABLE)
            playback.stop()
            playback.end()
        except Exception:
            LOG.warning("StackChan offline line is unavailable; install the verified clip bundle")

    def _classify(self, result) -> str:
        """``silence`` (end quietly), ``failed`` (apologize once) or ``speech`` (go on)."""
        text = (result.text or "").strip()
        if result.kind in {"no_speech", "timeout"}:
            return "silence"
        if result.kind == "final":
            return "speech" if text else "silence"
        # kind == "error": only an apology if the hub really heard someone speak.
        return "failed" if (result.speech_s or 0.0) >= MIN_SPEECH_S else "silence"

    async def _end_quietly(self, session_id: str, device_id: str) -> None:
        self._quiet_streak += 1
        LOG.info(
            "StackChan voice: no speech to answer (%d quiet turn%s in a row); going idle%s",
            self._quiet_streak,
            "" if self._quiet_streak == 1 else "s",
            " and waiting for the wake word" if self._quiet_streak >= 2 else "",
        )
        self._quiet_idle.add(session_id)
        await self._go_idle(device_id)

    async def _go_idle(self, device_id: str) -> None:
        send_idle = getattr(self.server, "send_idle", None)
        if callable(send_idle):
            try:
                await send_idle(device_id)
            except Exception:
                LOG.debug("StackChan voice: idle request failed", exc_info=True)

    def _say(self, playback, base: str, cookie: str, text: str) -> None:
        """Speak one short line through the hub's voice (a confirmation, not a chat reply)."""
        try:
            self._caption(playback, text)
            self.backend.tts(base, cookie, playback).speak(text)
            playback.stop()
            playback.end()
        except Exception:
            LOG.warning("StackChan voice: could not speak %r", text, exc_info=True)
            self._mumble(text)

    def _mumble(self, text: str) -> bool:
        """No voice answered: if the unit announced the mumble voice, send it the words as a text-only line (decision 24). False when it cannot."""
        from maipai_body.bodies.stackchan.xiaozhi.server import ACTIVE_UNIT

        loop = getattr(self.server, "_loop", None)
        device_id = ACTIVE_UNIT.get() or next(iter(getattr(self.server, "_sessions", {}) or {}), None)
        send = getattr(self.server, "send_mumble", None)
        if loop is None or send is None or device_id is None:
            return False
        try:
            return bool(asyncio.run_coroutine_threadsafe(send(device_id, text), loop).result(timeout=5))
        except Exception:
            LOG.debug("StackChan voice: the mumble line could not be sent", exc_info=True)
            return False

    def _speak_plain_error(self, playback, base: str, cookie: str) -> None:
        if not self._breaker.allow():
            return
        if self.on_error_line is not None:
            try:
                self.on_error_line()
            except Exception:  # a sound never decides whether the apology is spoken
                LOG.debug("StackChan error earcon failed", exc_info=True)
        try:
            self._caption(playback, "I couldn't understand that. Please try again.")
            self.backend.tts(base, cookie, playback).speak(
                "I couldn't understand that. Please try again."
            )
            playback.stop()
            playback.end()
        except Exception:
            self._offline_line(playback)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
