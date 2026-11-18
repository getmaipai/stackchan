"""The watchdog: a dead or silent worker is restarted alone, with back-off; a worker that keeps failing is reported."""

import threading

from maipai_body import supervisor as sv


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _thread_worker(stop):
    def start():
        t = threading.Thread(target=stop.wait, daemon=True)
        t.start()
        return t
    return start


def test_a_worker_that_dies_is_restarted_and_the_others_are_not_touched():
    clock = Clock()
    s = sv.Supervisor(clock=clock)
    stop_a, stop_b = threading.Event(), threading.Event()
    starts = {"a": 0, "b": 0}

    def make(name, stop):
        def start():
            starts[name] += 1
            return _thread_worker(stop)()
        return start

    s.add(sv.Worker("a", make("a", stop_a)))
    s.add(sv.Worker("b", make("b", stop_b)))
    stop_a.set()  # worker a dies
    import time
    time.sleep(0.05)
    stop_a.clear()
    s.check()
    assert starts == {"a": 2, "b": 1}
    assert [r["state"] for r in s.report()] == ["ok", "ok"]
    stop_a.set(); stop_b.set()


def test_a_silent_worker_is_restarted_when_its_heartbeat_is_late():
    clock = Clock()
    s = sv.Supervisor(clock=clock)
    stop = threading.Event()
    starts = []
    s.add(sv.Worker("voice", lambda: starts.append(1) or _thread_worker(stop)(), heartbeat_limit_s=10))
    clock.t = 5
    s.beat("voice")
    clock.t = 14
    s.check()
    assert len(starts) == 1  # beat at 5, limit 10: still fine at 14
    clock.t = 20
    s.check()
    assert len(starts) == 2
    stop.set()


def test_back_off_grows_and_a_worker_that_keeps_failing_is_marked_failed_and_left_alone():
    clock = Clock()
    s = sv.Supervisor(clock=clock)
    starts = []

    def start():
        starts.append(clock.t)
        raise RuntimeError("no model")
    s.add(sv.Worker("brain", start, plain="the brain"))
    for _ in range(60):
        clock.t += 10
        s._tick_pending()
        s.check()
    row = s.report()[0]
    assert row["state"] == "failed" and "no model" in row["message"] and "not being restarted" in row["message"]
    count = len(starts)
    for _ in range(10):
        clock.t += 10
        s._tick_pending(); s.check()
    assert len(starts) == count  # no more tries until a person presses restart
    assert s.restart("brain") and len(starts) == count + 1
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert gaps[0] <= gaps[2] or gaps[1] <= gaps[3]  # the waits grow


def test_the_report_says_in_plain_words_what_is_wrong_and_what_to_do():
    clock = Clock()
    s = sv.Supervisor(clock=clock)
    def broken():
        raise OSError("port busy")
    s.add(sv.Worker("settings", broken, plain="the settings page", advice="Open the settings page again in a minute."))
    row = s.report()[0]
    assert row["state"] == "restarting" and "the settings page" in row["message"] and "Open the settings page" in row["advice"]
    assert s.degraded()[0]["part"] == "settings"


def test_workers_of_different_units_are_separate():
    s = sv.Supervisor(clock=Clock())
    stop = threading.Event()
    s.add(sv.Worker("privacy", _thread_worker(stop), unit="unit-a"))
    s.add(sv.Worker("privacy", _thread_worker(stop), unit="unit-b"))
    s.remove("privacy", "unit-a")
    assert [r["unit"] for r in s.report()] == ["unit-b"]
    stop.set()


def test_the_watchdog_thread_runs_and_stops():
    s = sv.Supervisor()
    stop = threading.Event()
    s.add(sv.Worker("x", _thread_worker(stop)))
    s.start(interval=0.02)
    s.stop()
    stop.set()
    assert s._thread is None or not s._thread.is_alive()
