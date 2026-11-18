"""self.face.mouth_cues of the virtual unit follows the firmware core's rules (patch SF10)."""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "vunit", Path(__file__).resolve().parents[2] / "scripts" / "virtual-unit" / "vunit.py"
)
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)


def call(u, cues):
    return u.call(
        "self.face.mouth_cues", {"cues": cues if isinstance(cues, str) else json.dumps(cues)}
    )


def test_the_cue_rules_and_their_reasons():
    with vunit.VirtualUnit() as u:
        assert call(u, [[0, 0], [120, 3], [260, 1]]) == {"ok": True, "n": 3}
        assert call(u, "not json")["reason"] == "bad_cues"
        assert call(u, [[0, 1, 2]])["reason"] == "bad_cues"
        assert call(u, [])["reason"] == "bad_count"
        assert call(u, [[i * 100, 1] for i in range(161)])["reason"] == "bad_count"
        assert call(u, [[500, 1], [100, 1]])["reason"] == "bad_time"
        assert call(u, [[60001, 1]])["reason"] == "bad_time"
        assert call(u, [[0, 5]])["reason"] == "bad_level"
        assert (
            call(u, [[i * 50, 1] for i in range(13)])["reason"] == "too_fast"
        )  # 13 cues inside 600 ms
        assert call(u, [[i * 83, 1] for i in range(12)]) == {
            "ok": True,
            "n": 12,
        }  # 12 inside one second is allowed


def test_a_muted_or_locked_unit_refuses():
    with vunit.VirtualUnit() as u:
        u.call("self.lock.set", {"code": "1234"})
        u.call("self.lock.now")
        assert call(u, [[0, 1]])["reason"] == "locked"
