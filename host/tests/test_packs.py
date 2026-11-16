# ruff: noqa: E501
"""The pack file, the library, the size gate, the per-unit active pack, and pushing only that pack."""

from __future__ import annotations

import base64
import json
import os
import stat

import numpy as np
import pytest

from maipai_body import fillers, packs
from maipai_body.hal.errors import BodyLost
from maipai_body.unit_tools import ToolProbe

UNIT = "aa:bb:cc:00:10:01"
OTHER = "aa:bb:cc:00:10:02"


def pack(kind="look", name="Pixel", size=1000, **kw):
    return packs.make_pack(kind, name, os.urandom(size), **kw)


class Unit:
    """A unit that records every call; ``tools`` False answers every pack tool as unknown."""

    def __init__(self, tools=True):
        self.tools, self.calls, self.held = tools, [], {}

    def __call__(self, name, args, *, device_id=None, timeout=4.0):
        if device_id is None or device_id == "gone":
            raise BodyLost("not connected")
        self.calls.append((device_id, name, dict(args)))
        if not self.tools:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        if name == "self.pack.status":
            return {"ok": True, **self.held.get(args["type"], {"held": False})}
        if name == "self.pack.commit":
            self.held[self._type] = {"held": True, "sha256": self._sha}
        if name == "self.pack.begin":
            self._type, self._sha = args["type"], args["sha256"]
        return {"ok": True}


@pytest.fixture
def lib(tmp_path):
    return packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")


def service(tmp_path, unit, lib):
    return packs.PackService(ToolProbe(unit), lib, packs.ActiveStore(tmp_path / "active.json"), chunk=400)


# ---- the file ----------------------------------------------------------------------------------------


def test_a_pack_round_trips_with_its_type_version_size_and_checksum():
    original = pack("language", "Deutsch", 300, version=4, lang="de")
    data = packs.encode(original)
    assert data.startswith(b"MAIPACK1\n")
    back = packs.decode(data)
    assert (back.type, back.name, back.version, back.size, back.lang) == ("language", "Deutsch", 4, 300, "de")
    assert back.sha256 == original.sha256 and back.payload == original.payload


@pytest.mark.parametrize("lang", ["en", "es"])
def test_bad_files_are_refused_in_plain_words(lang):
    good = packs.encode(pack())
    cases = {
        b"not a pack": "bad_file",
        good[:-5] + b"xxxxx": "bad_sum",
        packs.encode(pack("look", "x" * 80)): "bad_name",
    }
    for data, code in cases.items():
        with pytest.raises(packs.PackError) as error:
            packs.decode(data, lang)
        assert error.value.code == code
        assert str(error.value) == packs.say(lang, code) or code == "bad_name"
    header = json.dumps({"format": 1, "type": "toy", "name": "A", "version": 1, "size": 0, "sha256": ""})
    with pytest.raises(packs.PackError, match="toy" if lang == "en" else "No conozco"):
        packs.decode(packs.MAGIC + header.encode() + b"\n", lang)


def test_the_size_gate_has_one_limit_per_type_and_says_it_in_english_and_spanish():
    big = pack("look", "Huge", packs.MAX_BYTES["look"] + 1)
    with pytest.raises(packs.PackError) as en:
        packs.decode(packs.encode(big), "en")
    with pytest.raises(packs.PackError) as es:
        packs.decode(packs.encode(big), "es")
    assert en.value.code == "too_big" and "1000 KB" in str(en.value) and "robot keeps at most" in str(en.value)
    assert "máximo 1000 KB" in str(es.value)
    assert packs.MAX_BYTES["filler"] <= 400_000
    ok = pack("dance", "Small", packs.MAX_BYTES["dance"])
    assert packs.decode(packs.encode(ok)).size == packs.MAX_BYTES["dance"]


def test_a_signature_is_checked_only_when_a_verifier_is_given():
    signed = pack(signature="ab12", signer="author")
    data = packs.encode(signed)
    assert packs.decode(data).signature == "ab12"
    assert packs.decode(data, verify=lambda d, s, who: s == "ab12").signer == "author"
    with pytest.raises(packs.PackError) as error:
        packs.decode(data, "es", verify=lambda d, s, who: False)
    assert error.value.code == "bad_sig" and "firma" in str(error.value)


# ---- the library -------------------------------------------------------------------------------------


def test_the_library_imports_lists_exports_and_deletes(tmp_path, lib):
    service_ = service(tmp_path, Unit(), lib)
    data = base64.b64encode(packs.encode(pack("look", "Rubber Hose", 500))).decode()
    result = service_.import_pack(data)
    assert result["pack"]["id"] == "look/rubber-hose" and result["pack"]["size"] == 500
    assert [p["id"] for p in service_.library_view()["packs"]] == ["look/rubber-hose"]
    exported = service_.export_pack("look/rubber-hose")
    assert exported["filename"] == "look-rubber-hose.maipack"
    assert packs.decode(base64.b64decode(exported["b64"])).name == "Rubber Hose"
    service_.delete_pack("look/rubber-hose")
    assert service_.library_view()["packs"] == []
    with pytest.raises(packs.PackError, match="not in the library"):
        service_.export_pack("look/rubber-hose")
    with pytest.raises(packs.PackError):
        service_.export_pack("look/../../etc/passwd")


def test_a_filler_pack_lives_in_its_own_private_folder(tmp_path, lib):
    lib.add(pack("filler", "Fillers en", 300, voice="sage", lang="en"))
    folder = tmp_path / "fillers"
    assert [p.name for p in folder.glob("*.maipack")] == ["fillers-en-sage.maipack"]
    assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    assert stat.S_IMODE(next(folder.glob("*.maipack")).stat().st_mode) == 0o600


def test_a_full_library_refuses_a_new_pack_with_the_way_out(tmp_path, lib, monkeypatch):
    monkeypatch.setattr(packs, "MAX_LIBRARY_BYTES", 1500)
    lib.add(pack("look", "One", 1000))
    with pytest.raises(packs.PackError, match="Delete a pack"):
        lib.add(pack("look", "Two", 1000))


# ---- one active pack per unit, and only that one is sent ------------------------------------------------


def test_only_the_active_pack_is_pushed_and_each_unit_has_its_own(tmp_path, lib):
    unit = Unit()
    svc = service(tmp_path, unit, lib)
    lib.add(pack("look", "Pixel", 1000))
    lib.add(pack("look", "Dots", 900))
    lib.add(pack("language", "Deutsch", 100, lang="de"))
    result = svc.activate(UNIT, "look", "look/pixel")
    assert result["pushed"] is True and svc.active.get(UNIT) == {"look": "look/pixel"} and svc.active.get(OTHER) == {}
    names = [c[1] for c in unit.calls if c[1] != "self.pack.status"]
    assert names[0] == "self.pack.begin" and names[-1] == "self.pack.commit"
    assert names.count("self.pack.data") == 3  # 1000 bytes in 400 byte pieces
    sent = unit.calls[[c[1] for c in unit.calls].index("self.pack.begin")][2]
    assert sent["name"] == "Pixel" and sent["size"] == 1000
    assert not any(c[2].get("name") in ("Dots", "Deutsch") for c in unit.calls)  # nothing but the active one


def test_choosing_the_built_in_removes_the_pack_from_the_unit(tmp_path, lib):
    unit = Unit()
    svc = service(tmp_path, unit, lib)
    lib.add(pack("look", "Pixel", 100))
    svc.activate(UNIT, "look", "look/pixel")
    unit.calls.clear()
    svc.activate(UNIT, "look", "")
    assert ("self.pack.remove", {"type": "look"}) in [(c[1], c[2]) for c in unit.calls]
    assert svc.active.get(UNIT) == {}


def test_a_unit_without_the_pack_tools_keeps_the_choice_and_is_flagged(tmp_path, lib):
    unit = Unit(tools=False)
    svc = service(tmp_path, unit, lib)
    lib.add(pack("look", "Pixel", 100))
    result = svc.activate(UNIT, "look", "look/pixel", "es")
    assert result["pushed"] is False and result["pending"] is True and "próxima actualización" in result["message"]
    assert svc.active.get(UNIT) == {"look": "look/pixel"}
    assert svc.view(UNIT)["unit_ready"] is False
    assert [c[1] for c in unit.calls] == ["self.pack.status"]  # nothing was pushed


def test_an_unreachable_unit_keeps_the_choice_and_sends_it_on_connect(tmp_path, lib):
    unit = Unit()
    svc = service(tmp_path, unit, lib)
    lib.add(pack("look", "Pixel", 100))
    assert svc.activate("gone", "look", "look/pixel")["message"].startswith("Chosen. The unit is not connected")
    svc.active.set(UNIT, "look", "look/pixel")
    svc.sync(UNIT)
    assert [c[1] for c in unit.calls].count("self.pack.begin") == 1
    unit.calls.clear()
    svc.sync(UNIT)  # the unit holds the same checksum now: nothing is sent again
    assert "self.pack.begin" not in [c[1] for c in unit.calls]


def test_a_wrong_type_or_unknown_pack_is_refused(tmp_path, lib):
    svc = service(tmp_path, Unit(), lib)
    lib.add(pack("look", "Pixel", 100))
    with pytest.raises(packs.PackError, match="look pack, not a language pack"):
        svc.activate(UNIT, "language", "look/pixel")
    with pytest.raises(packs.PackError):
        svc.activate(UNIT, "language", "language/none")
    with pytest.raises(packs.PackError, match="not known"):
        svc.activate(UNIT, "toy", "x")


# ---- fillers ------------------------------------------------------------------------------------------


def fake_synth(text):
    rate = 22050
    t = np.arange(int(0.5 * rate)) / rate
    tone = 0.3 * np.sin(2 * np.pi * (200 + len(text) * 20) * t)
    quiet = np.zeros(int(0.3 * rate))
    return np.concatenate((quiet, tone, quiet)).astype(np.float32), rate


def test_clips_are_trimmed_and_normalised_and_mulaw_round_trips():
    samples, rate = fake_synth("Hmm.")
    clip = fillers.render_clip(samples, rate)
    assert clip is not None and 0.45 < len(clip) / fillers.RATE < 0.6  # the 0.6 s of silence is gone
    assert abs(float(np.max(np.abs(clip))) - fillers.TARGET_PEAK) < 0.01
    back = fillers.mulaw_decode(fillers.mulaw_encode(clip))
    assert float(np.max(np.abs(back - clip))) < 0.05
    assert fillers.render_clip(np.zeros(8000, dtype=np.float32), 16000) is None  # silence is not a clip


@pytest.mark.parametrize("lang", ["en", "es"])
def test_the_generator_makes_every_sound_with_several_takes_inside_the_size_gate(lib, lang):
    gen = fillers.FillerGenerator(fake_synth, lib)
    info = gen.generate("sage", lang)
    assert info["type"] == "filler" and info["voice"] == "sage" and info["size"] <= packs.MAX_BYTES["filler"]
    files = packs.unzip_payload(lib.get(info["id"]).payload)
    index = json.loads(files["index.json"])
    sounds = {c["name"] for c in index["clips"]}
    assert sounds == set(fillers.RECIPES[lang])
    assert all(sum(1 for c in index["clips"] if c["name"] == s) == 3 for s in sounds)
    assert {"hmm", "uh", "um", "ah", "oh", "aha", "mm_hm", "sigh", "breath", "laugh", "throat"} <= sounds


def test_a_long_set_is_cut_down_to_fit_the_pack_limit(lib, monkeypatch):
    def long_synth(text):
        t = np.arange(int(1.1 * 22050)) / 22050
        return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), 22050

    monkeypatch.setitem(packs.MAX_BYTES, "filler", 120_000)
    gen = fillers.FillerGenerator(long_synth, lib)
    info = gen.generate("sage", "en")
    assert info["size"] <= 120_000
    index = json.loads(packs.unzip_payload(lib.get(info["id"]).payload)["index.json"])
    assert {c["name"] for c in index["clips"]}  # something is left, takes were dropped


def test_no_engine_and_a_dead_engine_say_what_to_do(lib):
    with pytest.raises(packs.PackError, match="local speech server"):
        fillers.FillerGenerator(None, lib).generate("sage", "en")

    def dead(text):
        raise ConnectionError("down")

    with pytest.raises(packs.PackError, match="did not answer"):
        fillers.FillerGenerator(dead, lib).generate("sage", "en")


class Sink:
    def __init__(self):
        self.pushed, self.ended = [], 0

    def push_audio_sample(self, data):
        self.pushed.append(data)

    def end_sentence(self):
        self.ended += 1


def test_the_player_never_repeats_a_sound_and_plays_through_the_voice_link_when_the_unit_cannot(lib):
    fillers.FillerGenerator(fake_synth, lib).generate("sage", "en")
    unit = Unit(tools=False)
    player = fillers.FillerPlayer(lib, None, ToolProbe(unit))
    sink = Sink()
    names = []
    for _ in range(12):
        assert player.play(sink, UNIT, "phrase", "en") is True
        names.append(player.played[-1][1])
    assert all(a != b for a, b in zip(names, names[1:], strict=False))
    assert len(sink.pushed) == 12 and sink.ended == 12
    assert all(d.dtype == np.float32 and 0.1 < len(d) / fillers.OUT_RATE < 1.3 for d in sink.pushed)
    assert not any(c[1] == "self.filler.play" for c in unit.calls)


def test_the_tone_option_plays_a_short_tone_and_phrase_without_a_pack_falls_back_to_it(lib):
    player = fillers.FillerPlayer(lib, None, ToolProbe(Unit(tools=False)))
    sink = Sink()
    assert player.play(sink, UNIT, "tone", "en") and player.play(sink, UNIT, "phrase", "en")
    assert [n for _, n in player.played] == ["tone", "tone"]
    assert 0.15 < len(sink.pushed[0]) / fillers.OUT_RATE < 0.4
    assert player.play(sink, UNIT, "none", "en") is False and len(sink.pushed) == 2


def test_a_unit_with_the_filler_tool_plays_its_own_and_the_host_stays_quiet(lib):
    unit = Unit(tools=True)
    player = fillers.FillerPlayer(lib, None, ToolProbe(unit))
    sink = Sink()
    assert player.play(sink, UNIT, "phrase", "en") is True
    assert sink.pushed == []
    assert ("self.filler.play", {"mode": "phrase"}) in [(c[1], c[2]) for c in unit.calls]
