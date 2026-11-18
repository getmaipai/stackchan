"""Every host service thread ends when its stop event is set (or `stop_all` runs); none of ours remain."""

import threading
import time

from maipai_body import service_threads


def test_stop_all_ends_every_registered_thread():
    stop = threading.Event()
    for index in range(3):
        service_threads.start(lambda: stop.wait(), name=f"probe-{index}", stop=stop)
    assert len([n for n in service_threads.running() if n.startswith("probe-")]) == 3
    service_threads.stop_all(timeout=2.0)
    assert [n for n in service_threads.running() if n.startswith("probe-")] == []
    assert not [t for t in threading.enumerate() if t.name.startswith("probe-")]


def test_a_thread_that_leaves_by_its_own_stop_event_is_not_listed():
    stop = threading.Event()
    service_threads.start(lambda: stop.wait(), name="probe-own", stop=stop)
    stop.set()
    deadline = time.time() + 2
    mine = lambda: [n for n in service_threads.running() if n == "probe-own"]  # noqa: E731
    while mine() and time.time() < deadline:
        time.sleep(0.01)
    assert mine() == []


def test_a_thread_that_ignores_its_stop_event_is_named():
    release = threading.Event()
    stop = threading.Event()
    service_threads.start(lambda: release.wait(5), name="probe-stuck", stop=stop)
    try:
        assert "probe-stuck" in service_threads.stop_all(timeout=0.2)
    finally:
        release.set()
        service_threads.stop_all(timeout=2.0)


def test_a_supervised_thread_that_dies_is_started_again_but_not_after_stop_all():
    from maipai_body import supervisor as sv

    sup = sv.Supervisor()
    service_threads.SUPERVISOR = sup
    try:
        stop = threading.Event()
        died = threading.Event()
        runs = []

        def work():
            runs.append(1)
            if len(runs) == 1:
                return  # the first run ends by itself: the thread dies
            died.set()
            stop.wait()

        service_threads.start(work, name="probe-supervised", stop=stop)
        deadline = time.time() + 2
        while len(runs) < 1 and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.05)
        sup.check()
        assert died.wait(2), "the supervisor did not start the dead thread again"
        service_threads.stop_all(timeout=2.0)
        assert not any(r["part"] == "probe-supervised" for r in sup.report())
    finally:
        service_threads.SUPERVISOR = None
        service_threads.stop_all(timeout=2.0)
