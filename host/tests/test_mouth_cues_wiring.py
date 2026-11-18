"""The reply's mouth cues go to the unit (self.face.mouth_cues) before the first audio frame, within the unit's limits."""

import asyncio
import json
import threading

import numpy as np

from maipai_body.bodies.stackchan.turn import StackChanAudioPlayback
from maipai_body.mouth_cues import UNIT_MAX_CUES, UNIT_MAX_MS, fit_to_unit, mouth_cues


class _Server:
    def __init__(self, loop, fail=None):
        self._loop = loop
        self.events = []
        self.fail = fail

    async def send_audio(self, device_id, frames, **kwargs):
        self.events.append(("audio", len(frames)))

    async def stop_audio(self, device_id):
        self.events.append(("stop",))

    def call_device_tool(self, name, arguments, *, timeout, device_id):
        self.events.append(("tool", name, arguments, device_id))
        if self.fail:
            raise self.fail


def _speech(seconds=1.2):
    t = np.arange(int(24000 * seconds)) / 24000
    return (0.3 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 3 * t) > 0)).astype(np.float32)


def _play(single, fail=None, on=True):
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    server = _Server(loop, fail)
    playback = StackChanAudioPlayback(server, "02:00:00:00:00:01")
    playback.mouth_cues_on = on
    audio = _speech()
    for start in range(0, len(audio), 2400):
        playback.push_audio_sample(audio[start : start + 2400])
    playback.decide_cues(single)
    playback.end_sentence()
    playback.end()
    loop.call_soon_threadsafe(loop.stop)
    return server.events


def test_a_one_sentence_reply_sends_its_cues_before_the_first_audio():
    events = _play(True)
    names = [e[0] for e in events]
    assert names.index("tool") < names.index("audio")
    tool = next(e for e in events if e[0] == "tool")
    assert tool[1] == "self.face.mouth_cues" and tool[3] == "02:00:00:00:00:01"
    cues = json.loads(tool[2]["cues"])
    assert cues[-1][1] == 0, "the list ends with the mouth closed"
    assert [c[0] for c in cues] == sorted(c[0] for c in cues)
    assert all(0 <= c[1] <= 4 for c in cues)


def test_a_reply_with_more_sentences_sends_no_list():
    assert "tool" not in [e[0] for e in _play(False)]


def test_cues_off_sends_nothing():
    assert "tool" not in [e[0] for e in _play(True, on=False)]


def test_a_refusal_from_the_unit_does_not_stop_the_speech():
    events = _play(True, fail=RuntimeError("muted"))
    assert "audio" in [e[0] for e in events]


def test_a_long_reply_is_cut_to_the_units_list_limits():
    long = mouth_cues(_speech(30.0), 24000)
    fitted = fit_to_unit(long)
    assert len(fitted) <= UNIT_MAX_CUES and fitted[-1][1] == 0 and fitted[-1][0] <= UNIT_MAX_MS
    times = [c[0] for c in fitted]
    assert times == sorted(times)
    assert all(sum(1 for u in times if t <= u < t + 1000) <= 12 for t in times)


class _AppendServer(_Server):
    def device_supports(self, feature, device_id=None):
        return feature == "mouth_cues_append"


def _play_sentences(count):
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()
    server = _AppendServer(loop)
    playback = StackChanAudioPlayback(server, "02:00:00:00:00:01")
    playback.mouth_cues_on = True
    audio = _speech(1.0)
    for _ in range(count):
        for start in range(0, len(audio), 2400):
            playback.push_audio_sample(audio[start : start + 2400])
        playback.decide_cues(False)
        playback.end_sentence()
    playback.end()
    loop.call_soon_threadsafe(loop.stop)
    return server.events


def test_a_unit_that_can_append_gets_one_list_per_sentence_with_continuing_times():
    events = _play_sentences(3)
    tools = [e for e in events if e[0] == "tool"]
    assert len(tools) == 3
    assert [e[0] for e in events].index("tool") < [e[0] for e in events].index("audio")
    assert "append" not in tools[0][2] and tools[1][2]["append"] and tools[2][2]["append"]
    last = -1
    for tool in tools:
        cues = json.loads(tool[2]["cues"])
        assert cues[0][0] >= last and [c[0] for c in cues] == sorted(c[0] for c in cues)
        assert all(0 <= c[1] <= 4 for c in cues) and len(cues) <= UNIT_MAX_CUES
        last = cues[-1][0]
    assert json.loads(tools[1][2]["cues"])[0][0] >= 900, "the second sentence's times continue from the first sentence's audio"
