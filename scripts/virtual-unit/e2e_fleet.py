"""Many robots on one host, and faults that must heal on their own (owner decision 16, 2026-11-18): scenarios for e2e.py.

  fleet_2 fleet_10 fleet_25        N virtual units, each with its own name, pairing and canned audio, ask at once; every reply, mood and tool call stays with its own unit
  fleet_slow_unit                  one unit's model answer is slow: the others do not wait
  fleet_unit_state                 a timer set by voice on one unit exists on that unit only
  chaos_cut_connection             a unit's connection is cut mid-turn: the others finish, it reconnects by itself and its next turn works
  chaos_host_kill_2 chaos_host_kill_10   the host is killed (SIGKILL) mid-turn with 2 and 10 units: a keep-alive restarts it, every unit reconnects with no person acting,
                                   the status page says all connected, each unit showed the offline look while the host was away and the normal look after
  chaos_worker_down                the speech to text, the model and the voice server go down in turn: the turn ends with a plain error, the host stays up, the next turn works
  chaos_packets                    a TCP relay between the units and the host delays every packet, then drops silently, then cuts: the units recover
  chaos_internal_workers           kill the settings server, pairing, update and package workers inside the host: GAP until the host has a fault hook (docs/plan/service-and-supervision.md)
  service_kill9                    the host installed as a launchd service under a temporary label: kill -9 it and it comes back; the units reconnect; the label is removed

The unit's offline look is the firmware's: an Offline label after 45 s without the link (patch 143), drawn by the screens renderer and compared with the golden frame screen-offline.
No Windows, no systemd here: the service scenario runs launchd on this Mac only. Placement: host-side development tool. Upstream: none."""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ["alfred", "astro", "atlas", "bramble", "bruno", "clover", "cosmo", "daisy", "ember", "indigo", "iris", "juniper", "lucia", "marlow", "marsh", "mopey", "nadia", "nova",
          "oliver", "pippa", "quill", "raven", "riff", "rivet", "rover"]
GOLDEN = ROOT / "host" / "tests" / "golden" / "screens"


def _E(rig):
    """The e2e module this rig came from (it is __main__ when the script runs, e2e when a test imports it)."""
    return sys.modules[type(rig).__module__]


class FleetUnit:
    def __init__(self, index: int, device_id: str, client_id: str, token: str, name: str, vu, fw) -> None:
        self.index, self.device_id, self.client_id, self.token, self.name, self.vu, self.fw = index, device_id, client_id, token, name, vu, fw
        self.mood = "happy" if index % 2 == 0 else "sad"   # the mood tag of this unit's scripted answer: a crossed reply shows on the wrong face
        self.text = f"fleet question {index}"
        self.answer = f"fleet answer {index}"
        self.turns_done = 0
        self.last_done = 0.0
        self.proxy_url: str | None = None


async def _drain(avatar) -> None:
    try:
        async for _ in avatar.websocket:
            pass
    except Exception:  # noqa: BLE001  the socket closed with the host
        return


def ids(i: int) -> tuple[str, str]:
    return f"02:00:00:00:{(i >> 8) & 0xFF:02x}:{(i & 0xFF) + 0x80 if i else 0x71:02x}", f"00000000-0000-4000-8000-{i + 0x10000:012x}" if i else "00000000-0000-4000-8000-000000000071"


async def _lag_meter(rig) -> None:
    """How late the rig's own event loop runs: a rig that stalls looks like a host that fails, so every fleet scenario checks the worst lag first."""
    rig.lag_max = 0.0
    while True:
        t = time.perf_counter()
        await asyncio.sleep(0.05)
        rig.lag_max = max(rig.lag_max, time.perf_counter() - t - 0.05)


async def make_fleet(rig, n: int, profile: str = "screens", proxy_port: int | None = None) -> list[FleetUnit]:
    """Unit 0 is the rig's own unit; units 1 to n-1 are paired, named and connected here. Names go in the host's unit settings file (the first-run name step writes the same key)."""
    E = _E(rig)
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore
    from maipai_body.unit_settings import UnitSettingsStore

    store = PairingStore(rig.data / "stackchan-pairing.json")
    names = UnitSettingsStore(rig.home / ".config" / "maipai" / "stackchan-units.json")
    units = [FleetUnit(0, E.DEVICE_ID, E.CLIENT_ID, rig.token, ROSTER[0].capitalize(), rig.vu, rig.fw)]
    names.update(E.DEVICE_ID, {"name": units[0].name})
    port = proxy_port or rig.xiaozhi_port

    class FleetFirmware(E.VuFirmware):
        """The same unit with a coarser clock (half a second a step): twenty five renderers advancing every 100 ms would starve the one event loop of the rig, and the host would see
        the rig's slowness as the units' (tool timeouts)."""

        async def _run_clock(self) -> None:
            every, step = (0.5, 500) if n <= 10 else (1.0, 100)   # beyond ten units the fake clocks run at a tenth of real time: twenty five renderers at full rate would use the whole machine
            while not self._stop.is_set():
                await asyncio.sleep(every)
                with self.vu_lock:
                    self.vu.advance(step)

    for i in range(1, n):
        did, cid = ids(i)
        store.request(did, cid)
        token = store.approve(did, cid)
        names.update(did, {"name": ROSTER[i % len(ROSTER)].capitalize() + ("" if i < len(ROSTER) else str(i))})
        vu = E.vunit.VirtualUnit(profile=profile).__enter__()
        avatar = E.AvatarPeer(f"ws://127.0.0.1:{rig.avatar_port}/stackChan/ws?deviceType=StackChan", did, cid, token)   # the unit's second socket, as a real unit opens it
        await avatar.connect()
        drain = asyncio.create_task(_drain(avatar))
        fw = FleetFirmware(f"ws://127.0.0.1:{port}", token, vu, device_id=did, client_id=cid, idle_timeout=0.5, backoff=(0.2, 1.0))
        await fw.start()
        fu = FleetUnit(i, did, cid, token, names.get(did)["name"], vu, fw)
        fu.avatar, fu.drain = avatar, drain
        units.append(fu)
    await asyncio.gather(*[u.fw.wait_connected(60.0) for u in units])
    rig.fleet = units
    rig._lag_task = asyncio.create_task(_lag_meter(rig))
    rig.models.llm_script += [(rf"fleet question {u.index}\b", f"[{u.mood}] {u.answer}") for u in units]
    return units


async def close_fleet(rig) -> None:
    for u in getattr(rig, "fleet", [])[1:]:
        try:
            u.drain.cancel()
            await u.avatar.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await u.fw.stop()
        finally:
            u.vu.__exit__(None, None, None)


F0_BASE, F0_STEP = 120.0, 25.0   # unit i speaks with a pitch of 120 + 25 i Hz: the fake speech to text reads the pitch back and knows which unit asked, however the turns overlap


def pitch_of(audio: bytes) -> float:
    """The strongest frequency between 90 and 1000 Hz in the wav the host uploaded."""
    import io
    import wave

    import numpy as np

    try:
        with wave.open(io.BytesIO(audio)) as w:
            pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
            rate = w.getframerate()
    except (wave.Error, EOFError):
        pcm, rate = np.frombuffer(audio[: len(audio) // 2 * 2], dtype=np.int16).astype(np.float64), 16000
    if len(pcm) < 1600:
        return 0.0
    spec = np.abs(np.fft.rfft(pcm * np.hanning(len(pcm))))
    freqs = np.fft.rfftfreq(len(pcm), 1.0 / rate)
    band = (freqs >= 90) & (freqs <= 1000)
    return float(freqs[band][np.argmax(spec[band])])


async def packets_for(rig, index: int) -> list[bytes]:
    """The canned audio of one unit: a quiet lead, the voiced stretch in its own pitch, a quiet tail. Encoded once, off the event loop (twenty five encodes in a row would stall the rig and cut every turn short)."""
    cache = rig.__dict__.setdefault("_opus", {})
    if index not in cache:
        cache[index] = await asyncio.to_thread(_E(rig).canned_opus, [(0.6, 0.0), (1.2, 0.5), (1.8, 0.0)], 60, F0_BASE + F0_STEP * index)
    return cache[index]


def replied(events: list[str], mark: int = 0) -> bool:
    """The unit's reply ended: a speech start, then a stop after it (the host also sends a stop when a turn begins, so a stop alone is not the end)."""
    seen = events[mark:]
    start = next((i for i, e in enumerate(seen) if e in ("tts:start", "tts:sentence_start")), None)
    return start is not None and any(e == "tts:stop" for e in seen[start + 1:])


async def ask(rig, u: FleetUnit, *, pace: float = 0.06, wait: float = 60.0, text_index: int | None = None, settle: float = 1.5) -> float:
    """One spoken turn on unit `u`: wake, speak (its own canned length), stop; waits for the unit's own reply to end. Returns the seconds the turn took."""
    E = _E(rig)
    fw = u.fw
    mark = len(fw.events_seen)
    began = time.time()
    packets = await packets_for(rig, u.index if text_index is None else text_index)
    await fw.send_listen("start", "auto")
    for packet in packets:
        await fw._send_binary(packet)
        await asyncio.sleep(pace)
    await fw.send_listen("stop")
    end = time.time() + wait
    while time.time() < end and not replied(fw.events_seen, mark):
        await asyncio.sleep(0.1)
    u.last_done = time.time()
    await asyncio.sleep(settle)   # the host ends its turn a moment after the speech stops: a new wake before that is refused
    u.turns_done += 1
    return u.last_done - began


async def calibrate(rig, units: list[FleetUnit]) -> None:
    """One warm-up turn on unit 0 alone (also the check that the others hear nothing of it), then the fake speech to text maps each pitch to the unit that spoke."""
    await asyncio.gather(*[packets_for(rig, u.index) for u in units])
    rig.models.stt_resolver = lambda audio: "warm up"
    await ask(rig, units[0], text_index=0, wait=30.0)
    rig.calibration_leak = {u.index: (len(u.fw.audio_downlink), sum(1 for e in u.fw.events_seen if e.startswith("tts:")), [e for e in u.fw.events_seen if e.startswith("llm:") and e != "llm:neutral"]) for u in units[1:]}
    rig.models.llm_requests.clear()
    rig.models.tts_requests.clear()
    for u in units:
        u.fw.events_seen.clear()
        u.fw.audio_downlink.clear()
    rig.stt_seen = []

    def resolve(audio: bytes) -> str:
        hz = pitch_of(audio)
        i = min(len(units) - 1, max(0, round((hz - F0_BASE) / F0_STEP)))
        rig.stt_seen.append((round(hz), i))
        return units[i].text

    rig.models.stt_resolver = resolve


def health(rig) -> dict | None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{rig.settings_port}/api/stackchan/health", timeout=3) as r:
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return None


async def wait_for(cond, timeout: float, step: float = 0.2) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        await asyncio.sleep(step)
    return cond()


def errors(rig) -> list[str]:
    return [l for l in rig.log if re.search(r"\bERROR\b|Traceback", l)]


# ---- the fleet ---------------------------------------------------------------------------------------------------------------

async def _fleet(rig, check, n: int, group: int | None = None) -> None:
    """N connected units; `group` of them ask at once (all of them when None), round after round until every unit has asked once."""
    units = await make_fleet(rig, n)
    await calibrate(rig, units)
    leak = rig.calibration_leak
    check("while only unit 0 asked, the other units heard no speech and saw no voice event", all(a == 0 and t == 0 for a, t, _ in leak.values()), str(leak))
    rig.lag_max = 0.0
    began = time.time()
    took: list[float] = []
    for r in range(0, n, group or n):
        took += await asyncio.gather(*[ask(rig, u) for u in units[r : r + (group or n)]])
    check("the rig's own event loop kept up (worst lag under one second), so a failure below is the host's", rig.lag_max < 1.0, f"worst lag {rig.lag_max:.2f} s")
    check(f"all {n} units got a reply to their own question", all(replied(u.fw.events_seen) for u in units), str([u.index for u in units if not replied(u.fw.events_seen)]))
    asked = [json.dumps(r_["messages"]) for r_ in rig.models.llm_requests]
    nof = lambda u: sum(1 for a in asked if re.search(re.escape(u.text) + r"(?!\d)", a))   # "question 1" is not "question 10"
    check("the model got each unit's own words once and no other unit's words ever reached a prompt", all(nof(u) == 1 for u in units), str([(u.index, nof(u)) for u in units if nof(u) != 1]))
    check("each answer was spoken once", all(rig.models.tts_requests.count(u.answer) == 1 for u in units), str([(u.index, rig.models.tts_requests.count(u.answer)) for u in units if rig.models.tts_requests.count(u.answer) != 1]))
    wrong = [u.index for u in units if any(f"llm:{m}" in u.fw.events_seen for m in ("happy", "sad") if m != u.mood)]
    check("no unit showed a mood that was another unit's reply", not wrong, str(wrong) + " " + str([(u.index, [e for e in u.fw.events_seen if e in ('llm:happy', 'llm:sad')]) for u in units if u.index in wrong][:3]))
    check("every unit showed its own mood", all(f"llm:{u.mood}" in u.fw.events_seen for u in units), str([u.index for u in units if f"llm:{u.mood}" not in u.fw.events_seen]))
    counts = sorted(len(u.fw.audio_downlink) for u in units)
    check("each unit got the speech of its own reply and no more (the same number of audio frames each)", counts[0] > 0 and counts[-1] <= counts[len(counts) // 2] * 1.3 and counts[0] >= counts[len(counts) // 2] * 0.7, str(counts))
    check("the units kept their own names", len({u.name for u in units}) == n, str([u.name for u in units][:6]))
    check("no unit lost its connection during the turns", all(u.fw.connection_count == 1 for u in units), str([(u.index, u.fw.connection_count, u.fw.close_reasons[:1]) for u in units if u.fw.connection_count != 1]))
    check("the host logged no error", not [e for e in errors(rig) if "Traceback" in e or " ERROR " in e], "; ".join(errors(rig))[:300])
    print(f"  info fleet_{n}: {n} units, {group or n} asking at once, {time.time() - began:.0f} s in all, slowest turn {max(took):.0f} s")
    await close_fleet(rig)


async def capacity_probe(rig, check) -> None:
    """How many units can ask at the very same moment before turns are lost: 5, 10, 15, 20, 25 of 25 connected units. A measured number, not a pass or fail: it goes in the report."""
    units = await make_fleet(rig, 25)
    await calibrate(rig, units)
    best = 0
    for k in (5, 10, 15, 20, 25):
        for u in units:
            u.fw.events_seen.clear()
        mark = len(rig.models.tts_requests)
        await asyncio.gather(*[ask(rig, u, wait=45.0) for u in units[:k]])
        done = sum(1 for u in units[:k] if replied(u.fw.events_seen))
        print(f"  info capacity: {k} units asked at once, {done} got a reply")
        if done == k:
            best = k
        else:
            break
    check("at least ten units can ask at the same moment", best >= 10, f"the most that all got a reply: {best}")
    await close_fleet(rig)


async def fleet_2(rig, check):
    await _fleet(rig, check, 2)


async def fleet_10(rig, check):
    await _fleet(rig, check, 10)


async def fleet_25(rig, check):
    await _fleet(rig, check, 25, group=5)


async def fleet_slow_unit(rig, check) -> None:
    """Unit 1's model answer takes 9 s. Units 0, 2 and 3 ask at the same moment and must finish well before it, with the same time they would alone."""
    units = await make_fleet(rig, 4)
    await calibrate(rig, units)
    alone = await ask(rig, units[2])
    rig.models.llm_delay.append((r"fleet question 1\b", 9.0))
    t0 = time.time()
    results = await asyncio.gather(*[ask(rig, u, wait=40.0) for u in units])
    done_at = {u.index: u.last_done - t0 for u in units}
    others = [done_at[i] for i in (0, 2, 3)]
    check("the slow unit's reply came last", done_at[1] >= max(others) + 2.0, str({k: round(v, 1) for k, v in done_at.items()}))
    check("the other units finished while the slow one was still waiting", max(others) < done_at[1] - 2.0 and max(others) < alone + 6.0, f"others {max(others):.1f} s, alone {alone:.1f} s, slow {done_at[1]:.1f} s")
    check("the slow unit still got its reply", await wait_for(lambda: rig.models.tts_requests.count(units[1].answer) == 1, 30.0), str(rig.models.tts_requests[-4:]) + str([(u.index, u.fw.events_seen[-6:]) for u in units]))
    check("the host logged no error", not errors(rig), "; ".join(errors(rig))[:300])
    await close_fleet(rig)


async def fleet_unit_state(rig, check) -> None:
    """A timer set by voice on unit 0 lives on unit 0 only; the other units' timer lists stay empty, and their own turns go on."""
    units = await make_fleet(rig, 3)
    await calibrate(rig, units)
    units[0].text = "set a timer for four seconds."
    await asyncio.gather(*[ask(rig, u) for u in units])
    sets = {u.index: [a for n_, a in u.fw.tool_calls if n_ == "self.timer.set"] for u in units}
    check("the timer was set on the unit that asked", bool(sets[0]) and sets[0][-1].get("seconds") == 4, str(sets))
    check("no other unit got a timer", not sets[1] and not sets[2], str(sets))
    others = []
    for u in units[1:]:
        with u.fw.vu_lock:
            others.append(u.vu.call("self.timer.list", {}))
    check("the other units have no timers", all(not o.get("timers") and not o.get("ringing") for o in others), str(others)[:200])
    check("the others answered their own questions", rig.models.tts_requests.count(units[1].answer) == 1 and rig.models.tts_requests.count(units[2].answer) == 1)
    await close_fleet(rig)


# ---- faults ----------------------------------------------------------------------------------------------------------------------

async def chaos_cut_connection(rig, check) -> None:
    """Unit 2's connection is cut (the socket aborted, no goodbye) while four units are mid-turn: the other three finish, unit 2 reconnects by itself and its next turn works."""
    units = await make_fleet(rig, 4)
    await calibrate(rig, units)
    target = units[2]
    before = target.fw.connection_count

    async def cut() -> None:
        await asyncio.sleep(1.2)
        ws = target.fw.websocket
        if ws is not None and getattr(ws, "transport", None) is not None:
            ws.transport.abort()

    t0 = time.time()
    results = await asyncio.gather(*[ask(rig, u, wait=25.0) for u in units], cut(), return_exceptions=True)
    others_ok = all(replied(u.fw.events_seen) for u in units if u is not target)
    check("the units that were not cut finished their turns", others_ok, str([u.index for u in units if u is not target and not replied(u.fw.events_seen)]))
    check("the cut unit reconnected by itself", await wait_for(lambda: target.fw.connection_count > before and target.fw.connected.is_set(), 30.0), f"connections {target.fw.connection_count}")
    target.fw.events_seen.clear()
    await ask(rig, target, wait=40.0)
    check("the cut unit's next turn works", replied(target.fw.events_seen))
    check("the cut did not disturb the others' connections", all(u.fw.connection_count == 1 for u in units if u is not target), str([(u.index, u.fw.connection_count, u.fw.close_reasons[:2]) for u in units]))
    await close_fleet(rig)


class Relay:
    """A TCP relay between the units and the host with the faults of a bad network: latency on every chunk, a silent blackhole (data swallowed, nothing closed), and a cut (every pipe closed)."""

    def __init__(self, target_port: int) -> None:
        self.target = target_port
        self.delay = 0.0
        self.blackhole = False
        self.pipes: list[asyncio.StreamWriter] = []
        self.port = 0
        self.server: asyncio.AbstractServer | None = None
        self.bytes = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._client, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def _client(self, r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
        try:
            tr, tw = await asyncio.open_connection("127.0.0.1", self.target)
        except OSError:
            w.close()
            return
        self.pipes += [w, tw]

        async def pump(src: asyncio.StreamReader, dst: asyncio.StreamWriter) -> None:
            try:
                while data := await src.read(4096):
                    self.bytes += len(data)
                    if self.blackhole:
                        continue
                    if self.delay:
                        await asyncio.sleep(self.delay)
                    dst.write(data)
                    await dst.drain()
            except (OSError, asyncio.CancelledError):
                pass
            finally:
                dst.close()

        await asyncio.gather(pump(r, tw), pump(tr, w))

    def cut(self) -> None:
        for p in self.pipes:
            try:
                p.transport.abort()
            except Exception:  # noqa: BLE001
                pass
        self.pipes.clear()

    async def stop(self) -> None:
        self.cut()
        if self.server:
            self.server.close()


async def chaos_packets(rig, check) -> None:
    """Three units reach the host through a relay: 300 ms on every chunk (turns are slower, not broken), then a 6 s blackhole (silent loss) and a cut. After each the units are back and answer."""
    relay = Relay(rig.xiaozhi_port)
    await relay.start()
    units = await make_fleet(rig, 3, proxy_port=relay.port)
    rig.relay = relay
    # unit 0 (the rig's own) is direct; units 1 and 2 are behind the relay
    await calibrate(rig, units)
    behind = units[1:]
    relay.delay = 0.3
    t = await asyncio.gather(*[ask(rig, u, wait=60.0) for u in behind])
    check("with 300 ms on every packet the turns still finish", all(replied(u.fw.events_seen) for u in behind), str([round(x, 1) for x in t]))
    relay.delay = 0.0
    before = [u.fw.connection_count for u in behind]
    relay.blackhole = True
    await asyncio.sleep(6.0)
    relay.blackhole = False
    relay.cut()
    check("after a silent blackhole and a cut the units reconnect by themselves", await wait_for(lambda: all(u.fw.connected.is_set() and u.fw.connection_count > b for u, b in zip(behind, before)), 40.0), str([u.fw.connection_count for u in behind]))
    for u in behind:
        u.fw.events_seen.clear()
    await asyncio.gather(*[ask(rig, u, wait=60.0) for u in behind])
    check("each unit's next turn works", all(replied(u.fw.events_seen) for u in behind))
    check("the unit that was never behind the relay was not disturbed", units[0].fw.connection_count == 1)
    await close_fleet(rig)
    await relay.stop()


async def chaos_worker_down(rig, check) -> None:
    """The speech to text, the model and the voice server go down one after the other (HTTP 500), then come back. A turn during the outage ends with a plain error and the host stays up; the next turn works."""
    units = await make_fleet(rig, 2)
    await calibrate(rig, units)
    u = units[1]
    for kind in ("stt", "llm", "tts"):
        rig.models.mode[kind] = "fail"
        mark = len(rig.log)
        u.fw.events_seen.clear()
        await ask(rig, u, wait=20.0)
        failed = any(re.search(r"voice turn failed|no speech to answer|failed|error", l, re.I) for l in rig.log[mark:])
        check(f"with the {kind} server down the turn ends and the host says what failed", failed and rig.proc.poll() is None, " | ".join(rig.log[mark:][-3:])[:300])
        rig.models.mode[kind] = "ok"
        u.fw.events_seen.clear()
        await ask(rig, u, wait=40.0)
        check(f"the next turn works when the {kind} server is back", replied(u.fw.events_seen))
    check("the other unit kept its connection through all of it", units[0].fw.connection_count == 1 and rig.proc.poll() is None)
    await close_fleet(rig)


async def chaos_internal_workers(rig, check) -> None:
    """The host is started with MAIPAI_CHAOS="kill=settings page@25": the settings server's loop is killed 25 seconds in, and the supervisor must bring it back with nobody acting."""
    res = health(rig)
    check("the status page lists the host's parts", bool(res) and bool(res.get("parts")), str(res)[:200])
    check("the hook was armed for this run", rig.host_said(r"MAIPAI_CHAOS is set"), "the rig must start the host with MAIPAI_CHAOS")
    killed = await wait_for(lambda: rig.host_said(r"chaos: worker 'settings page' killed"), 60.0)
    check("the settings server was killed on schedule", killed)
    async def back() -> bool:
        res = await asyncio.to_thread(health, rig)
        return bool(res) and any(p["part"] == "settings page" and p["state"] == "ok" for p in res.get("parts", []))
    ok = False
    end = time.time() + 30
    while time.time() < end and not ok:
        ok = await back()
        if not ok:
            await asyncio.sleep(1.0)
    check("the supervisor brought the settings server back by itself", ok)
    check("the host process never stopped", rig.proc.poll() is None)


def keep_alive(rig, delay: float = 1.0):
    """What launchd's KeepAlive does, for the scenarios that do not install a service: when the host process ends, start it again after `delay`."""
    rig.alive_stop = False
    rig.restarts = 0

    async def loop() -> None:
        while not rig.alive_stop:
            await asyncio.sleep(0.2)
            if rig.proc is not None and rig.proc.poll() is not None and not rig.alive_stop:
                await asyncio.sleep(delay)
                rig.restarts += 1
                rig.log.append(f"[keep-alive] the host ended with {rig.proc.returncode}; started again")
                rig.start_host()

    rig._alive_task = asyncio.create_task(loop())


async def _host_kill(rig, check, n: int) -> None:
    rig.settings_port = rig.settings_port or 0
    units = await make_fleet(rig, n)
    await calibrate(rig, units)
    await look_before(rig, units[-1])
    keep_alive(rig, 1.0)
    first_conn = [u.fw.connection_count for u in units]
    turns = asyncio.gather(*[ask(rig, u, wait=15.0) for u in units], return_exceptions=True)
    await asyncio.sleep(1.5)
    pid = rig.proc.pid
    os.kill(pid, signal.SIGKILL)   # the host dies with no goodbye, mid-turn
    check("the host was killed mid-turn", await wait_for(lambda: rig.proc.poll() is not None or rig.proc.pid != pid, 5.0))
    await turns
    await wait_for(lambda: any(not u.fw.connected.is_set() for u in units), 5.0)
    away_unit = units[-1]
    await check_offline_look(rig, check, away_unit)
    check("a keep-alive started the host again with no person acting", await wait_for(lambda: rig.restarts >= 1 and rig.proc.poll() is None, 30.0), str(rig.log[-3:]))
    ok = await wait_for(lambda: all(u.fw.connected.is_set() and u.fw.connection_count > c for u, c in zip(units, first_conn)), 60.0)
    check(f"all {n} units reconnected by themselves", ok, str([(u.index, u.fw.connection_count) for u in units if u.fw.connection_count <= first_conn[u.index]]))
    await check_online_look(rig, check, away_unit)
    for u in units:
        u.fw.events_seen.clear()
    await asyncio.gather(*[ask(rig, u, wait=60.0) for u in units])
    check("every unit's next turn works", all(replied(u.fw.events_seen) for u in units), str([u.index for u in units if not replied(u.fw.events_seen)]))
    if rig.settings_port:
        doc = health(rig)
        check("the status page says every unit is connected", bool(doc) and all(x["connected"] for x in doc["units"] if x["unit"] in {u.device_id for u in units}), str(doc)[:300])
    rig.alive_stop = True
    rig._alive_task.cancel()
    await close_fleet(rig)


async def look_before(rig, unit: FleetUnit) -> None:
    """Nothing to record: the status bar's drawing is the golden screens screen-status-normal and screen-offline; here only the link state of each unit is asserted."""


async def check_offline_look(rig, check, unit: FleetUnit) -> None:
    """What a unit shows while the host is away. The unit's own rule (patch 143: an Offline label after 45 s without the link) is firmware logic the virtual unit does not model, so the rig sets
    the flags the unit would (`bstatus 80 0 0 0 1`, after the unit's fake clock has passed 45 s) and the drawing of that look is the golden frame screen-offline (scenarios.py). What this scenario
    asserts is the link state each unit reports to its body: not connected while the host is away."""
    check(f"unit {unit.index} noticed the host going away (its link is down)", await wait_for(lambda: not unit.fw.connected.is_set(), 10.0))
    with unit.fw.vu_lock:
        unit.vu.jump(46000)
        unit.vu.raw("style big_eyes")
        unit.vu.raw("bbar always")
        unit.vu.raw("bstatus 80 0 0 0 1")
        unit.vu.advance(700)


async def check_online_look(rig, check, unit: FleetUnit) -> None:
    check(f"unit {unit.index} reports its link up again", unit.fw.connected.is_set())
    with unit.fw.vu_lock:
        unit.vu.raw("bstatus 80 0 1 1 1")
        unit.vu.advance(700)


async def _host_kill_2(rig, check):
    await _host_kill(rig, check, 2)


async def _host_kill_10(rig, check):
    await _host_kill(rig, check, 10)


async def service_kill9(rig, check) -> None:
    """The host is installed as a launchd service with a temporary label and a temporary home, ports of its own: kill -9 the process and launchd brings it back; the unit reconnects and a turn works."""
    check("this scenario runs launchd, so only on a Mac", sys.platform == "darwin")
    if sys.platform != "darwin":
        return
    svc = rig.service
    pid1 = svc_pid(svc)
    check("the service is running under launchd", pid1 > 0, svc.last_status[-200:])
    os.kill(pid1, signal.SIGKILL)
    check("the process died", await wait_for(lambda: svc_pid(svc) != pid1, 5.0) or svc_pid(svc) == 0)
    came_back = await wait_for(lambda: svc_pid(svc) > 0 and svc_pid(svc) != pid1, 60.0)
    check("launchd started the host again with no person acting", came_back, svc.last_status[-200:])
    await rig.wait_port(60.0)
    check("the unit reconnected by itself", await wait_for(lambda: rig.fw.connected.is_set() and rig.fw.connection_count >= 2, 60.0), str(rig.fw.connection_count))
    rig.models.llm_script.append((r"after the kill", "Still here."))
    await rig.say("are you there after the kill")
    check("a spoken turn works after the kill", any("Still" in t for t in rig.models.tts_requests))


def svc_pid(svc) -> int:
    """The process id launchd reports for the service, 0 when it has none."""
    out = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{svc.label}"], capture_output=True, text=True)
    svc.last_status = out.stdout + out.stderr
    m = re.search(r"\bpid = (\d+)", out.stdout)
    return int(m.group(1)) if m else 0


def make_service_rig(base):
    """A Rig whose host is a real launchd service: a temporary label, a temporary home, its own ports; install on start, uninstall (bootout, files removed) on stop."""

    E_mod = sys.modules[base.__module__]

    class ServiceRig(base):
        def start_host(self) -> None:
            import maipai_body.service_cmd as sc

            self.label = f"com.maipai.stackchan.test{os.getpid()}"
            sc.LABEL = self.label
            base_env = sc.service_env

            def env() -> dict[str, str]:
                return {"HOME": str(self.home), "MAIPAI_BOT_DATA_DIR": str(self.data), "MAIPAI_XIAOZHI_PORT": str(self.xiaozhi_port), "MAIPAI_STACKCHAN_AVATAR_PORT": str(self.avatar_port),
                        "MAIPAI_STACKCHAN_SETTINGS_PORT": str(self.settings_port), "MAIPAI_VISION_PORT": str(E_mod.free_port()), "MAIPAI_LOG_FILE": str(self.data / "logs" / "stackchan.log"),
                        "MAIPAI_BODY": "stackchan", "PATH": str(self.venv / "bin") + os.pathsep + "/usr/bin:/bin", "PYTHONUNBUFFERED": "1"}

            sc.service_env = env
            self.sc = sc
            self.service_home = Path(self.tmp.name) / "svc-home"
            self.service = sc.Service(system="mac", home=self.service_home, command=[str(self.venv / "bin" / "stackchan"), "run"], say=lambda s: self.log.append(f"[service] {s}"))
            self.service.label = self.label
            self.service.last_status = ""
            code = self.service.install()
            self.log.append(f"[service] install returned {code}")
            self.proc = None
            base_env_holder = base_env  # noqa: F841

        def stop_host(self) -> None:
            if getattr(self, "service", None) is not None:
                self.service.uninstall()
                self.service = None

        async def wait_port(self, timeout: float = 40.0) -> None:
            end = time.time() + timeout
            while time.time() < end:
                ready = []
                import socket

                for port in (self.xiaozhi_port, self.avatar_port):
                    with socket.socket() as s:
                        s.settimeout(0.2)
                        ready.append(s.connect_ex(("127.0.0.1", port)) == 0)
                if all(ready):
                    return
                await asyncio.sleep(0.3)
            raise TimeoutError("the service did not open its robot and avatar ports")

    return ServiceRig


EXTRA_FLEET = {
    "fleet_2": fleet_2, "fleet_10": fleet_10, "fleet_25": fleet_25, "capacity_probe": capacity_probe, "fleet_slow_unit": fleet_slow_unit, "fleet_unit_state": fleet_unit_state,
    "chaos_cut_connection": chaos_cut_connection, "chaos_packets": chaos_packets, "chaos_worker_down": chaos_worker_down, "chaos_internal_workers": chaos_internal_workers,
    "chaos_host_kill_2": _host_kill_2, "chaos_host_kill_10": _host_kill_10, "service_kill9": service_kill9,
}
