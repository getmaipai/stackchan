"""scripts/bench-train.py: the pure parts and a whole train run against a fake unit (no hardware)."""

from __future__ import annotations

import importlib.util
import json
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("bench_train", ROOT / "scripts" / "bench-train.py")
bt = importlib.util.module_from_spec(spec)
sys.modules["bench_train"] = bt
spec.loader.exec_module(bt)


def png(path: Path, w: int, h: int, fn) -> None:
    raw = b"".join(b"\x00" + b"".join(bytes(fn(x, y)) for x in range(w)) for y in range(h))
    def chunk(k, d):
        return struct.pack(">I", len(d)) + k + d + struct.pack(">I", zlib.crc32(k + d) & 0xFFFFFFFF)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_expect_failures():
    r = {"ok": True, "a": {"b": 5, "s": "hello"}, "l": [1, 2]}
    assert bt.expect_failures(r, {"ok": True, "a.b": {"min": 5}, "a.s": {"regex": "ell"}, "l.1": 2}) == []
    assert len(bt.expect_failures(r, {"ok": False, "a.b": {"min": 6}, "zzz": 1})) == 3


def test_memory_gate():
    good = [{"free": 87000, "min": 39800, "big": 43000}] * 5
    assert bt.memory_verdict(good, bt.GATE)[0]
    low = good + [{"free": 87000, "min": 20000, "big": 43000}]
    ok, _, bad = bt.memory_verdict(low, bt.GATE)
    assert not ok and "lowest" in bad[0]
    assert not bt.memory_verdict([], bt.GATE)[0]


def test_console_scan():
    text = "ESP-ROM:esp32s3\nboot\nassert failed: x\nESP-ROM:esp32s3\n"
    assert bt.scan_console(text) == {"boots": 2, "panics": 1}


def test_snapshot_compare(tmp_path):
    png(tmp_path / "a.png", 8, 8, lambda x, y: (10, 20, 30))
    png(tmp_path / "b.png", 8, 8, lambda x, y: (12, 20, 30))      # within a channel tolerance of 12
    png(tmp_path / "c.png", 8, 8, lambda x, y: (200, 20, 30) if x < 4 else (10, 20, 30))
    tol = bt.tolerance_for({}, "x")
    assert bt.compare_snapshot(tmp_path / "b.png", tmp_path / "a.png", tol)[0] == "PASS"
    assert bt.compare_snapshot(tmp_path / "c.png", tmp_path / "a.png", tol)[0] == "FAIL"
    assert bt.compare_snapshot(tmp_path / "c.png", tmp_path / "a.png", {**tol, "ignore": [[0, 0, 4, 8]]})[0] == "PASS"   # the changed half is ignored
    assert bt.compare_snapshot(tmp_path / "a.png", tmp_path / "none.png", tol)[0] == "NOGOLDEN"


class FakeUnit:
    def __init__(self, tmp: Path, boots_after: int | None = None):
        self.calls: list[str] = []
        self.tmp = tmp
        self.boots = 1
        self.boots_after = boots_after
        self.n = 0

    def call(self, name, args=None, wait=30):
        self.calls.append(name)
        self.n += 1
        if self.boots_after is not None and self.n == self.boots_after:
            self.boots += 1
        if name == "self.bench.heap_info":
            return {"internal_free": 87000, "internal_min": 39800, "internal_big": 43000}
        return {"ok": True, "asset_use": {"loaded": 3}}

    def snapshot(self, path: Path):
        png(path, 8, 8, lambda x, y: (10, 20, 30))

    def console(self):
        return "ESP-ROM:esp32s3\n" * self.boots


def manifest(tmp: Path, **kw) -> dict:
    png(tmp / "gold.png", 8, 8, lambda x, y: (10, 20, 30))
    return {"name": "t", "soak_s": 0.6, "heap_interval_s": 0.05, "settle_s": 0, "goldens_dir": str(tmp), "tolerance_file": str(tmp / "none.json"),
            "checks": [{"name": "asset", "tool": "self.bench.asset_use", "expect": {"asset_use.loaded": {"min": 1}}}, {"name": "shot", "snapshot": "gold"}], **kw}


def test_a_train_passes_and_puts_the_silent_state_back(tmp_path):
    man = manifest(tmp_path)
    unit = FakeUnit(tmp_path)
    res = bt.run_train(man, unit, tmp_path / "out", sleep=lambda s: __import__("time").sleep(0.01))
    assert res["pass"], (tmp_path / "out" / "result.md").read_text()
    assert unit.calls[-1] == "self.audio_speaker.set_volume"                       # restored last
    assert "PASS" in (tmp_path / "out" / "result.md").read_text()


def test_a_restart_during_the_train_is_counted_and_the_silent_state_reapplied(tmp_path):
    man = manifest(tmp_path)
    unit = FakeUnit(tmp_path, boots_after=6)
    res = bt.run_train(man, unit, tmp_path / "out", sleep=lambda s: __import__("time").sleep(0.01))
    assert res["restarts"] >= 1 and not res["pass"]
    assert unit.calls.count("self.audio_speaker.set_volume") >= 3                  # at start, after the restart, at the end


def test_a_failing_check_does_not_stop_the_train(tmp_path):
    man = manifest(tmp_path)
    man["checks"].insert(0, {"name": "bad", "tool": "self.bench.asset_use", "expect": {"asset_use.loaded": {"min": 99}}})
    res = bt.run_train(man, FakeUnit(tmp_path), tmp_path / "out", sleep=lambda s: __import__("time").sleep(0.01))
    assert [c["status"] for c in res["checks"]] == ["FAIL", "PASS", "PASS"] and not res["pass"]
    assert json.loads((tmp_path / "out" / "result.json").read_text())["train"] == "t"


def test_console_memory_lines_are_read():
    text = "I (1) SystemInfo: mem internal_free=66707 internal_min=39828 int_big=31744 x\nSystemInfo: mem internal_free=66000 internal_min=39000 int_big=30000\n"
    assert bt.console_samples(text) == [{"free": 66707, "min": 39828, "big": 31744}, {"free": 66000, "min": 39000, "big": 30000}]


def test_an_optional_pre_step_may_fail(tmp_path):
    class U(FakeUnit):
        def call(self, name, args=None, wait=30):
            if name == "self.screen.set_brightness":
                raise RuntimeError("refused")
            return super().call(name, args, wait)

    png(tmp_path / "gold.png", 8, 8, lambda x, y: (10, 20, 30))
    check = {"name": "shot", "snapshot": "gold", "pre": [{"tool": "self.screen.set_brightness", "args": {"brightness": 100}, "optional": True}]}
    res = bt.run_check(U(tmp_path), check, tmp_path, {}, tmp_path, 0, sleep=lambda s: None)
    assert res["status"] == "PASS"
    check["pre"][0]["optional"] = False
    assert bt.run_check(U(tmp_path), check, tmp_path, {}, tmp_path, 0, sleep=lambda s: None)["status"] == "FAIL"


def test_a_mismatch_writes_a_side_by_side(tmp_path):
    png(tmp_path / "gold.png", 8, 8, lambda x, y: (200, 20, 30))
    res = bt.run_check(FakeUnit(tmp_path), {"name": "shot", "snapshot": "gold"}, tmp_path, {}, tmp_path, 0, sleep=lambda s: None)
    assert res["status"] == "FAIL" and (tmp_path / "shot-vs-golden.png").exists()


def test_final_and_after_restart_checks_run(tmp_path):
    man = manifest(tmp_path)
    man["final_checks"] = [{"name": "last", "tool": "self.brain.status", "expect": {"ok": True}}]
    man["after_restart_checks"] = [{"name": "again", "tool": "self.brain.status", "expect": {"ok": True}}]
    unit = FakeUnit(tmp_path, boots_after=6)
    res = bt.run_train(man, unit, tmp_path / "out", sleep=lambda s: __import__("time").sleep(0.01))
    names = [c["name"] for c in res["checks"]]
    assert "last (after soak)" in names and "again (after restart)" in names


def test_a_screen_check_clears_quiet_for_the_picture_and_restores_the_silent_state(tmp_path):
    png(tmp_path / "gold.png", 8, 8, lambda x, y: (10, 20, 30))
    unit = FakeUnit(tmp_path)
    res = bt.run_check(unit, {"name": "shot", "snapshot": "gold"}, tmp_path, {}, tmp_path, 0, sleep=lambda s: None)
    assert res["status"] == "PASS"
    assert unit.calls[0] == "self.privacy.set" and unit.calls[-1] == "self.audio_speaker.set_volume"   # quiet off first, the silent state last
    unit2 = FakeUnit(tmp_path)
    bt.run_check(unit2, {"name": "tool", "tool": "self.privacy.get"}, tmp_path, {}, tmp_path, 0, sleep=lambda s: None)
    assert unit2.calls == ["self.privacy.get"]                                                          # a tool check keeps the unit in full quiet
