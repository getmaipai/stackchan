"""Isolation and chaos at the unit level: 2 and 10 units, one fails, the others carry on; the settings server and a worker are killed and come back."""

import threading
import time
import urllib.request
from types import SimpleNamespace

import pytest

from maipai_body.bodies.stackchan.privacy import PrivacyUnits
from maipai_body.supervisor import Supervisor, Worker


@pytest.mark.parametrize("count", [2, 10])
def test_one_units_privacy_state_never_changes_another(count):
    units = PrivacyUnits(lambda device: (lambda name, args: None))
    ids = [f"02:00:00:00:00:{n:02x}" for n in range(count)]
    for device in ids:
        units.state_for(device)
    event = SimpleNamespace(kind="privacy", extra={"muted": 1, "vision_off": 0, "quiet": 0})
    units.poll_events(ids, primary=ids[0], events_of=lambda device: [event] if device == ids[-1] else [])
    muted = [bool(units.state_for(device).muted) for device in ids]
    assert muted[-1] is True and not any(muted[:-1])


@pytest.mark.parametrize("count", [2, 10])
def test_a_dead_worker_of_one_unit_is_restarted_and_the_others_are_not_touched(count):
    sup = Supervisor()
    stops = {n: threading.Event() for n in range(count)}
    starts = {n: 0 for n in range(count)}

    def make(n):
        def start():
            starts[n] += 1
            t = threading.Thread(target=stops[n].wait, daemon=True)
            t.start()
            return t
        return start

    for n in range(count):
        sup.add(Worker("idle motion", make(n), unit=f"unit-{n}"))
    victim = count // 2
    stops[victim].set()
    time.sleep(0.05)
    stops[victim] = threading.Event()  # the restarted worker waits on a fresh event
    sup.check()
    assert starts[victim] == 2 and all(starts[n] == 1 for n in range(count) if n != victim)
    assert all(row["state"] == "ok" for row in sup.report())
    for event in stops.values():
        event.set()


def test_killing_the_settings_server_brings_it_back_without_a_person():
    from maipai_body.settings_server import SettingsServer
    from maipai_body.settings_sim import build
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as folder:
        backend, _ = build(Path(folder))
        server = SettingsServer(backend, "127.0.0.1", 0)
        port = server.port
        server.start()
        holder = {"server": server}

        def restart():
            holder["server"].stop()
            holder["server"] = SettingsServer(backend, "127.0.0.1", port)
            holder["server"].start()
            return holder["server"]._thread

        sup = Supervisor()
        sup.add(Worker("settings page", restart, plain="the settings page"), start_now=False).handle = server._thread

        def answers() -> bool:
            try:
                return urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stackchan/settings", timeout=2).status in (200, 403)
            except urllib.error.HTTPError as error:
                return error.code in (200, 403)
            except Exception:
                return False

        assert answers()
        server.shutdown()  # the fault: the serving loop ends
        server._thread.join(2)
        assert not answers()
        sup.check()
        assert answers() and sup.report()[0]["state"] == "ok"
        holder["server"].stop()


def test_a_worker_that_keeps_dying_is_reported_failed_while_the_others_run():
    sup = Supervisor()
    good = threading.Event()
    sup.add(Worker("good", lambda: _wait(good), unit="a"))
    sup.add(Worker("bad", _boom, unit="b", plain="the speech part"))
    for _ in range(40):
        sup._tick_pending()
        sup.check()
        for w in sup._workers.values():
            w.next_try = 0.0  # no waiting in a test
    states = {r["part"]: r["state"] for r in sup.report()}
    assert states == {"good": "ok", "bad": "failed"}
    good.set()


def _wait(event):
    t = threading.Thread(target=event.wait, daemon=True)
    t.start()
    return t


def _boom():
    raise RuntimeError("model missing")
