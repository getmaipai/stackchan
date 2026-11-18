"""A hostile peer on the local network, against the real host (clean venv) with a virtual unit paired and working, for e2e.py.

Two kinds of peer: one with no credentials (it can reach the ports and the pairing exchange), and one that holds a valid token (a stolen or broken unit) and speaks
the unit's protocol badly. Each attack is followed by the same health check: the host process is alive, the real unit still gets a spoken turn, and the host's
threads, descriptors and sockets are back near where they were. An error line in the host log (a traceback) counts against the host even when it survived.
Scenarios: hostile_unauthenticated hostile_paired_peer hostile_settings. Placement: host-side development tool. Upstream: none.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import time

from e2e_extra import leak_verdict, sample

LOOSE = {"rss_mb": 80.0, "rss_pct": 40.0, "threads": 6, "fds": 12, "sockets": 8}


def errors_since(rig, mark: int, keep_handshake: bool = False) -> list[str]:
    """Error lines (and tracebacks) the host logged since `mark`. Three known log floods are counted apart by their own checks (the websocket library's "opening handshake failed"
    for a request that is not HTTP, "pairing exchange stopped" with a traceback when a unit drops mid exchange, and asyncio's "Future exception was never retrieved" for a command
    cut by a closing session), so they do not hide a fourth kind of error."""
    out = []
    for line in rig.log[mark:]:
        if not re.search(r" (ERROR|CRITICAL) ", line):
            continue
        if keep_handshake or not re.search(r"opening handshake failed|never retrieved", line):
            out.append(line[:160])
    return out


async def health(rig, check, label: str, mark: int, before: dict) -> None:
    """The host is up, the real unit still works, nothing grew, and the host did not log an error."""
    alive = rig.proc is not None and rig.proc.poll() is None
    check(f"{label}: the host is still running", alive, "exit code %s" % (rig.proc.poll() if rig.proc else "?"))
    if not alive:
        return
    rig.models.llm_script.append((r"hostile", "Still fine."))
    before_replies = len(rig.models.tts_requests)
    await rig.say("hostile check", speech_s=0.5, tail_s=0.9, pace=0.03, wait_stop=30.0)
    check(f"{label}: the real unit still gets a spoken reply", len(rig.models.tts_requests) > before_replies)
    await asyncio.sleep(3.0)
    now = sample(rig.proc.pid)
    if leak_verdict(before, now, LOOSE):   # give the host time to wind down before calling it a leak
        await asyncio.sleep(20.0)
        now = sample(rig.proc.pid)
    check(f"{label}: threads, descriptors and sockets are back near where they were", not leak_verdict(before, now, LOOSE), "; ".join(leak_verdict(before, now, LOOSE)) + f" ({before} -> {now})")
    errs = errors_since(rig, mark)
    check(f"{label}: the host logged no error line", not errs, "; ".join(errs)[:300])


def headers(device: str, client: str, token: str | None = None, **extra) -> dict:
    h = {"Device-Id": device, "Client-Id": client, "Protocol-Version": "1", **extra}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _connect(rig, hdrs: dict, **kw):
    import websockets

    return await websockets.connect(f"ws://127.0.0.1:{rig.xiaozhi_port}", additional_headers=hdrs, max_size=None, ping_interval=None, open_timeout=10, **kw)


async def quiet(coro, timeout: float = 15.0):
    """Run an attack step; whatever the host does (close, refuse, ignore) is fine here, only a crash or a hang is a finding."""
    try:
        return await asyncio.wait_for(coro, timeout)
    except Exception:  # noqa: BLE001
        return None


HELLO = {"type": "hello", "version": 1, "features": {"mcp": True}, "transport": "websocket", "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60}}

TEXT_ATTACKS = [
    "", "{", '{"type":', '{"type":"hello"', "[", "[1,2,3]", "null", "true", "123", '"just a string"', '{"type":null}', '{"type":123}', '{"type":["hello"]}',
    '{"type":"listen"}', '{"type":"listen","state":null}', '{"type":"listen","state":"start","mode":{"a":1}}', '{"type":"abort","reason":[1]}',
    '{"type":"mcp"}', '{"type":"mcp","payload":null}', '{"type":"mcp","payload":{"id":"x","result":{"content":"not a list"}}}',
    '{"type":"mcp","payload":{"id":1e400,"result":{}}}', '{"type":"tts","state":"start"}', '{"type":"stt","text":"injected"}', '{"type":"llm","emotion":"happy"}',
    "\x00\x01\x02\xff", "{" * 20000, "[" * 20000, '{"type":"' + "A" * 200000 + '"}', "{\"a\":" * 5000 + "1" + "}" * 5000, '{"type":"hello","audio_params":{"sample_rate":-1,"frame_duration":0}}',
    '{"type":"hello","audio_params":{"sample_rate":4294967296,"frame_duration":999999999999}}', '{"type":"hello","features":"x","version":"y"}',
    '{"type":"listen","state":"start","mode":"auto"}' * 3, '\ud800', json.dumps({"type": "listen", "state": "detect", "text": "A" * 100000}),
]


async def warm_up(rig) -> None:
    """One real turn first, so the baseline holds the threads and descriptors a working host keeps."""
    rig.models.llm_script.append((r"hostile", "Still fine."))
    await rig.say("hostile warm up", speech_s=0.5, tail_s=0.9, pace=0.03, wait_stop=30.0)
    await asyncio.sleep(1.0)


async def hostile_unauthenticated(rig, check) -> None:
    import websockets

    await warm_up(rig)
    mark, before = len(rig.log), sample(rig.proc.pid)
    # 1. no credentials at all, and credentials that are wrong, with frames before any hello
    for hdrs in ({}, headers("02:00:00:00:00:EE", "00000000-0000-4000-8000-0000000000ee"), headers("x" * 5000, "y" * 5000), headers("02:00:00:00:00:EE", "00000000-0000-4000-8000-0000000000ee", "not-a-token"),
                 {"Device-Id": "02:00:00:00:00:EE\u0000", "Client-Id": "a", "Protocol-Version": "99"}):
        async def one(h=hdrs):
            try:
                ws = await _connect(rig, h)
            except Exception:  # noqa: BLE001  refused at the handshake: the right answer
                return
            for payload in ("{}", b"\x00" * 3000, json.dumps(HELLO), "listen", b"\xff" * 70000):
                await quiet(ws.send(payload), 5)
            await quiet(ws.close(), 5)
        await quiet(one(), 30)
    await health(rig, check, "no credentials, frames before hello", mark, before)
    check("a request that is not valid HTTP does not log an ERROR with a traceback (anyone on the network can fill the log with it)", not errors_since(rig, mark, keep_handshake=True) or not any("handshake failed" in l for l in errors_since(rig, mark, keep_handshake=True)))

    # 2. many connections held open without a hello
    mark, before = len(rig.log), sample(rig.proc.pid)
    socks = []
    async def open_one():
        try:
            socks.append(await _connect(rig, headers("02:00:00:00:00:EE", "00000000-0000-4000-8000-0000000000ee")))
        except Exception:  # noqa: BLE001
            pass
    await asyncio.gather(*[quiet(open_one(), 20) for _ in range(300)])
    opened = len(socks)
    await health(rig, check, f"{opened} connections held open", mark, {**before, "fds": before["fds"] + opened + 20, "sockets": before["sockets"] + opened + 20, "threads": before["threads"] + 20})
    for ws in socks:
        await quiet(ws.close(), 3)
    await asyncio.sleep(3.0)
    after = sample(rig.proc.pid)
    check("the host released its descriptors and sockets once the connections closed", not leak_verdict(before, after, LOOSE), f"{before} -> {after}")

    # 3. the pairing exchange, hostile
    mark, before = len(rig.log), sample(rig.proc.pid)
    dev, cli = "02:00:00:00:00:F1", "00000000-0000-4000-8000-0000000000f1"
    pk = base64.b64encode(os.urandom(32)).decode()
    cases = [
        [{"type": "pair_nonce", "n_u": base64.b64encode(os.urandom(16)).decode()}],                                   # wrong order
        [{"type": "pair_start", "pk_u": pk}, {"type": "pair_start", "pk_u": pk}],                                      # start twice
        [{"type": "pair_start", "pk_u": "%%%not base64%%%"}],
        [{"type": "pair_start", "pk_u": base64.b64encode(b"\x00" * 31).decode()}],
        [{"type": "pair_start", "pk_u": base64.b64encode(b"\x00" * 32).decode()}],                                     # a low order point
        [{"type": "pair_start", "pk_u": base64.b64encode(b"\xff" * 33).decode()}],
        [{"type": "pair_start", "pk_u": "A" * 2_000_000}],
        [{"type": "pair_start"}], [{"type": "pair_start", "pk_u": None}], [{"type": "pair_start", "pk_u": 5}], ["[]"], ["null"], ["{"],
        [{"type": "pair_start", "pk_u": pk}, {"type": "pair_nonce", "n_u": "AAAA"}],                                    # short nonce
        [{"type": "pair_start", "pk_u": pk}, {"type": "pair_nonce", "n_u": base64.b64encode(os.urandom(16)).decode()}, {"type": "pair_nonce", "n_u": base64.b64encode(os.urandom(16)).decode()}],   # nonce twice
        [{"type": "paired"}], [{"type": "pair_failed"}],
    ]
    for msgs in cases:
        async def attack(m=msgs):
            try:
                ws = await _connect(rig, headers(dev, cli, **{"Pair-Exchange": "1"}))
            except Exception:  # noqa: BLE001
                return
            for item in m:
                await quiet(ws.send(item if isinstance(item, str) else json.dumps(item)), 10)
                await quiet(asyncio.wait_for(ws.recv(), 2), 3)
            await quiet(ws.close(), 3)
        await quiet(attack(), 30)
    await health(rig, check, "hostile pairing exchange messages", mark, before)

    # 4. a flood of pairing requests (the host limits them per address)
    mark, before = len(rig.log), sample(rig.proc.pid)
    refused = 0
    for i in range(60):
        try:
            ws = await _connect(rig, headers(f"02:00:00:00:{i:02x}:AA", f"00000000-0000-4000-8000-{i:012x}", **{"Pair-Exchange": "1"}))
            await quiet(ws.send(json.dumps({"type": "pair_start", "pk_u": pk})), 3)
            try:
                await asyncio.wait_for(ws.recv(), 3)
                await asyncio.wait_for(ws.recv(), 1)
            except websockets.ConnectionClosed as closed:
                refused += int(closed.rcvd is not None and closed.rcvd.code == 1013)
            except Exception:  # noqa: BLE001
                pass
            await quiet(ws.close(), 3)
        except Exception:  # noqa: BLE001
            refused += 1
    check("a flood of pairing requests from one address is limited (close code 1013 after 8 in 10 minutes)", refused >= 40, f"{refused} of 60 refused")
    await health(rig, check, "a flood of pairing requests", mark, before)


async def _paired_peer(rig):
    """A second paired unit with a valid token: a stolen or broken unit."""
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore

    dev, cli = "02:00:00:00:00:B7", "00000000-0000-4000-8000-0000000000b7"
    store = PairingStore(rig.data / "stackchan-pairing.json")
    store.request(dev, cli)
    return dev, cli, store.approve(dev, cli)


async def hostile_paired_peer(rig, check) -> None:
    await warm_up(rig)
    mark, before = len(rig.log), sample(rig.proc.pid)
    dev, cli, token = await _paired_peer(rig)

    async def session(frames, hello=True, pause=0.02, binary=False):
        try:
            ws = await _connect(rig, headers(dev, cli, token))
        except Exception:  # noqa: BLE001
            return
        try:
            if hello:
                await ws.send(json.dumps(HELLO))
                await quiet(asyncio.wait_for(ws.recv(), 3), 4)
            for f in frames:
                await quiet(ws.send(f), 10)
                if pause:
                    await asyncio.sleep(pause)
            await quiet(asyncio.wait_for(ws.recv(), 0.3), 1)
        finally:
            await quiet(ws.close(), 3)

    await quiet(session(TEXT_ATTACKS), 120)                       # malformed, odd and oversized text frames, after a hello
    await quiet(session(TEXT_ATTACKS, hello=False), 120)          # the same, with no hello first (wrong order)
    await health(rig, check, "malformed text frames from a paired peer", mark, before)

    mark, before = len(rig.log), sample(rig.proc.pid)
    await quiet(session([os.urandom(n) for n in (0, 1, 2, 3, 7, 100, 3000, 65535, 700_000)]), 60)   # binary frames: not opus, any length
    await quiet(session([b"\x00" * 900_000 for _ in range(6)], pause=0), 60)
    await quiet(session(["x" * 3_000_000]), 60)                                                      # over the host's 1 MiB message limit
    await health(rig, check, "binary and oversized frames from a paired peer", mark, before)

    mark, before = len(rig.log), sample(rig.proc.pid)
    await quiet(session([json.dumps(HELLO)] * 4000, pause=0), 120)                                  # a hello flood on one connection
    await quiet(session([json.dumps({"type": "listen", "state": s, "mode": "auto"}) for s in ("start", "stop") * 1500], pause=0), 120)   # listen start and stop flood
    await health(rig, check, "hello and listen floods from a paired peer", mark, before)

    mark, before = len(rig.log), sample(rig.proc.pid)
    # many sessions with one token at once (the host keeps one session per unit)
    await asyncio.gather(*[quiet(session([json.dumps(HELLO)], pause=0), 30) for _ in range(60)])
    await health(rig, check, "sixty simultaneous sessions with one token", mark, before)
    check("a session that closes while a command is in flight leaves no unretrieved future in the log", not rig.host_said(r"Future exception was never retrieved"))

    # the avatar port: frames that are not frames
    mark, before = len(rig.log), sample(rig.proc.pid)
    import websockets

    async def avatar(payloads):
        try:
            ws = await websockets.connect(f"ws://127.0.0.1:{rig.avatar_port}/stackChan/ws?deviceType=StackChan", additional_headers=headers(dev, cli, token), max_size=None, open_timeout=10)
        except Exception:  # noqa: BLE001
            return
        for p in payloads:
            await quiet(ws.send(p), 10)
            await quiet(asyncio.wait_for(ws.recv(), 0.2), 0.5)
        await quiet(ws.close(), 3)
    await quiet(avatar([b"", b"\x00", b"\x00" * 3, os.urandom(40), b"\xff" * 5000, os.urandom(900_000), "text on a binary channel", "{", b"\x01\x00\x00\x00\xff\xff\xff\xff" + b"A" * 20]), 60)
    await health(rig, check, "malformed avatar frames from a paired peer", mark, before)


async def hostile_settings(rig, check) -> None:
    """The settings page and its code entry, hit by a local peer: oversized and broken bodies, odd paths, and guessing the six digits."""
    import urllib.request

    base = f"http://127.0.0.1:{rig.settings_port}"
    await warm_up(rig)
    mark, before = len(rig.log), sample(rig.proc.pid)

    def http(method, path, body=None, headers_=None, timeout=15):
        req = urllib.request.Request(base + path, data=body, method=method, headers=headers_ or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(2000)
        except Exception as error:  # noqa: BLE001
            body_ = error.read(2000) if hasattr(error, "read") else b""
            return getattr(error, "code", 0), body_ or str(error).encode()

    posts = ["/api/stackchan/pairings/code-entry", "/api/stackchan/settings/voice", "/api/stackchan/unit", "/api/stackchan/faces/upload", "/api/stackchan/settings/update", "/api/stackchan/access"]
    bodies = [b"", b"{", b"[]", b"null", b'{"device_id": 5, "code": []}', b'{"code": "' + b"9" * 100000 + b'"}', b"{" * 50000, b"\xff\xfe\x00", b"A" * 20_000_000, json.dumps({"lang": "x" * 100000}).encode()]
    for path in posts:
        for body in bodies:
            await asyncio.to_thread(http, "POST", path, body, {"Content-Type": "application/json"})
    for path in ["/../../etc/passwd", "/settings/../../../etc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "/api/stackchan/settings?" + "a=b&" * 20000, "/" + "A" * 100000, "/api/stackchan/pairings/waiting", "//", "/settings%00.html"]:
        status, text = await asyncio.to_thread(http, "GET", path)
        check(f"GET {path[:40]!r} does not serve a file outside the page", b"root:" not in text, f"{status} {text[:80]!r}")
    await health(rig, check, "oversized and broken settings requests", mark, before)

    # replaying a code that was accepted: once for the same exchange, and once against a fresh exchange of the same unit
    from maipai_body.bodies.stackchan.xiaozhi.link_exchange import sas

    dev2, cli2 = "02:00:00:00:00:D4", "00000000-0000-4000-8000-0000000000d4"

    async def exchange() -> tuple[object, str]:
        pk_u, n_u = os.urandom(32), os.urandom(16)
        ws = await _connect(rig, headers(dev2, cli2, **{"Pair-Exchange": "1"}))
        await ws.send(json.dumps({"type": "pair_start", "pk_u": base64.b64encode(pk_u).decode()}))
        pk_h = base64.b64decode(json.loads(await asyncio.wait_for(ws.recv(), 5))["pk_h"])
        await ws.send(json.dumps({"type": "pair_nonce", "n_u": base64.b64encode(n_u).decode()}))
        n_h = base64.b64decode(json.loads(await asyncio.wait_for(ws.recv(), 5))["n_h"])
        return ws, sas(pk_u, pk_h, n_u, n_h)

    ws1, code1 = await exchange()
    status, _ = await asyncio.to_thread(http, "POST", "/api/stackchan/pairings/code-entry", json.dumps({"device_id": dev2, "code": code1}).encode(), {"Content-Type": "application/json"})
    check("the right digits pair the unit", status == 200, str(status))
    await quiet(ws1.close(), 3)
    status, text = await asyncio.to_thread(http, "POST", "/api/stackchan/pairings/code-entry", json.dumps({"device_id": dev2, "code": code1}).encode(), {"Content-Type": "application/json"})
    check("the same digits sent again are refused (the exchange is over)", status == 400, f"{status} {text[:120]!r}")
    ws2, code2 = await exchange()
    status, text = await asyncio.to_thread(http, "POST", "/api/stackchan/pairings/code-entry", json.dumps({"device_id": dev2, "code": code1}).encode(), {"Content-Type": "application/json"})
    check("digits from an earlier exchange do not pair a new one", status == 400 and code1 != code2, f"{status} {text[:120]!r}")
    await quiet(ws2.close(), 3)

    # guessing the six digits: the exchange must end on the first wrong code, and the unit be locked after a few
    import websockets
    from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore  # noqa: F401

    dev, cli = "02:00:00:00:00:C9", "00000000-0000-4000-8000-0000000000c9"
    accepted = 0
    wrong = 0
    for attempt in range(12):
        try:
            ws = await _connect(rig, headers(dev, cli, **{"Pair-Exchange": "1"}))
        except Exception:  # noqa: BLE001
            continue
        await quiet(ws.send(json.dumps({"type": "pair_start", "pk_u": base64.b64encode(os.urandom(32)).decode()})), 5)
        started = await quiet(asyncio.wait_for(ws.recv(), 3), 4)
        if started is None:
            await quiet(ws.close(), 3)
            continue
        await quiet(ws.send(json.dumps({"type": "pair_nonce", "n_u": base64.b64encode(os.urandom(16)).decode()})), 5)
        await quiet(asyncio.wait_for(ws.recv(), 3), 4)
        status, text = await asyncio.to_thread(http, "POST", "/api/stackchan/pairings/code-entry", json.dumps({"device_id": dev, "code": f"{attempt:06d}"}).encode(), {"Content-Type": "application/json"})
        wrong += 1
        accepted += int(status == 200)
        await quiet(ws.close(), 3)
    check("guessing digits never pairs a unit by luck in twelve tries", accepted == 0)
    status, text = await asyncio.to_thread(http, "POST", "/api/stackchan/pairings/code-entry", json.dumps({"device_id": dev, "code": "000000"}).encode(), {"Content-Type": "application/json"})
    check("a unit with several wrong codes is refused for a while and the refusal says so", status == 400 and (b"wait" in text.lower() or b"too many" in text.lower() or b"restart" in text.lower()), f"{status} {text[:160]!r}")
    await health(rig, check, "guessing the pairing digits", len(rig.log), sample(rig.proc.pid))

    check("a unit that drops in the middle of the pairing exchange is logged without a traceback", not rig.host_said(r"pairing exchange stopped"))


EXTRA_HOSTILE = {"hostile_unauthenticated": hostile_unauthenticated, "hostile_paired_peer": hostile_paired_peer, "hostile_settings": hostile_settings}
