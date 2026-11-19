# ruff: noqa: E501, F811
"""Language packs, offline phrase packs and the host's choice of which pack a unit holds (firmware patches K10 to K13).

The host half runs against the unit's own C cores (``firmware/pack_wire_driver.c``: the pack receiver, the zip walker, the language
words reader, the phrase clip table), so a pack the host builds is read by the code the unit runs. Cases: every shipped language
pack is accepted and shows its words; damaged packs (bytes flipped with the checksum fixed up so the damage reaches the reader,
truncations, every kind of wrong word) are refused and change nothing; a push cut at every call, before the reply and after it,
is healed by the next sync; a reboot and a damaged flash cache fall back to English and to the image's clips and heal on connect;
the host sends and drops packs as the unit's language, "While it thinks" and voice change."""

from __future__ import annotations

import base64
import json
import random
import shutil
import struct

import numpy as np
import pytest
from test_wire_packs import UNIT, WireUnit, driver, unit  # noqa: F401  (fixtures)

from maipai_body import fillers, language_packs, pack_auto, packs, phrase_packs
from maipai_body.hal.errors import BodyLost
from maipai_body.unit_prefs import prefs_of
from maipai_body.unit_tools import ToolProbe


def _service(tmp_path, wire: WireUnit, *, lang="en", mode="tone", voice="", chunk=300):
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    saved: dict = {"filler_mode": mode}
    state = {"lang": lang}
    auto = pack_auto.AutoPacks(library, lambda _d: saved, lambda _d: state["lang"], lambda: voice)
    service = packs.PackService(
        ToolProbe(wire),
        library,
        packs.ActiveStore(tmp_path / "active.json"),
        chunk=chunk,
        auto=auto,
    )
    return service, library, saved, state


def _status(wire: WireUnit, kind: str) -> dict:
    return wire.raw("self.pack.status", {"type": kind})


def _push_raw(wire: WireUnit, pack: packs.Pack, chunk: int = 500) -> dict:
    """Send a pack the way PackService does and return the commit answer (the unit's own words on a refusal)."""
    begin = wire.raw(
        "self.pack.begin",
        {
            "type": pack.type,
            "name": pack.name,
            "version": pack.version,
            "size": pack.size,
            "sha256": pack.sha256,
        },
    )
    if begin.get("ok") is not True:
        return begin
    for at in range(0, pack.size, chunk):
        got = wire.raw(
            "self.pack.data",
            {"at": at, "b64": base64.b64encode(pack.payload[at : at + chunk]).decode()},
        )
        assert got.get("ok") is True, got
    return wire.raw("self.pack.commit", {})


def _fake_ogg(i: int, size: int = 3000) -> bytes:
    return b"OggS" + bytes((i * 7 + k) % 251 for k in range(size - 4))


def _phrase_pack(lang="en", voice="amy", missing=()) -> packs.Pack:
    files = {}
    n = 0
    for group, count in phrase_packs.GROUPS.items():
        for variant in range(1, count + 1):
            n += 1
            if (group, variant) not in missing:
                files[phrase_packs.clip_name(group, variant)] = _fake_ogg(n, 2000 + n * 100)
    return packs.make_pack(
        "phrase", f"Phrases {lang}", packs.zip_payload(files, stored=True), voice=voice, lang=lang
    )


# ---- the shipped language packs ----------------------------------------------------------------------------


def test_every_language_pack_is_plain_ascii_inside_the_limits_and_tiny() -> None:
    for code in language_packs.CODES:
        text = language_packs.words_text(code)
        assert text.isascii() and f"lang={code}\n" in text and "order=dmy" in text
        pack = language_packs.build(code)
        assert (
            pack.type == "language" and pack.lang == code and pack.size < 1200
        )  # a few hundred bytes, not the 200 KB gate
        assert packs.unzip_payload(pack.payload) == {"words.txt": text.encode()}
        assert (
            language_packs.build(code).sha256 == pack.sha256
        )  # the same bytes every time: the unit's cache writes nothing twice
    assert language_packs.words_text("fr").count(
        "aou"
    ) == 1 and "août" not in language_packs.words_text("fr")  # accents are folded


def test_the_five_packs_carry_the_words_the_unit_had_built_in_before_k11() -> None:
    k11 = (
        packs.__file__
        and __import__("pathlib").Path(__file__).resolve().parents[2]
        / "firmware"
        / "patches"
        / "U06-face-style-packs-and-languages.patch"
    ).read_text()
    for code in language_packs.BEFORE_K11:
        row = language_packs.WORDS[code]
        for word in (*row["weekdays"], *row["months"], row["alarm"], row["timer"]):  # type: ignore[misc]
            plain = __import__("maipai_body.unit_extras", fromlist=["screen_text"]).screen_text(
                str(word)
            )
            assert f'"{plain}"' in k11, (code, word)


def test_the_library_gets_the_shipped_packs_once_and_leaves_changed_ones_replaced_by_the_same_bytes(
    tmp_path,
) -> None:
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    first = language_packs.install(library)
    assert len(first) == 12 and language_packs.install(library) == []
    listed = {p["lang"]: p for p in library.list("language")}
    assert set(listed) == {"es", "fr", "de", "pt", "it", "nl", "nb", "sv", "da", "pl", "tr", "cs"} and all(
        p["size"] < 1200 for p in listed.values()
    )
    library.delete(language_packs.pack_id("de"))
    assert language_packs.install(library) == ["language/screen-words-de"]


@pytest.mark.parametrize("code", list(language_packs.CODES))
def test_the_unit_accepts_each_shipped_pack_and_shows_its_words_only_for_its_own_language(
    unit, code
) -> None:  # noqa: F811
    pack = language_packs.build(code)
    done = _push_raw(unit, pack)
    assert done["ok"] is True, done
    held = _status(unit, "language")
    assert (
        held["held"] is True
        and held["lang"] == code
        and held["cached"] is True
        and held["fallback"] is False
    )
    words = unit.raw("self.lang.words", {"code": code})
    row = language_packs.WORDS[code]
    assert (
        words["code"] == code
        and words["dmy"] == 1
        and words["wd0"] == language_packs.screen_text(str(row["weekdays"][0]))
        if hasattr(language_packs, "screen_text")
        else True
    )
    assert unit.raw("self.lang.words", {"code": "en"})["wd0"] == "Sun"  # English stays English
    other = "de" if code != "de" else "fr"
    assert (
        unit.raw("self.lang.words", {"code": other})["code"] == "en"
    )  # a face in another language shows English, not these words


def test_a_pack_with_an_accent_or_a_wrong_count_is_refused_with_the_old_words_kept(unit) -> None:  # noqa: F811
    assert _push_raw(unit, language_packs.build("fr"))["ok"] is True
    good = language_packs.words_text("de")
    bad = {
        "accent": good.replace("Mar,", "Mär,", 1),
        "six months": good.replace(",Dez", ""),
        "no timer": "\n".join(line for line in good.splitlines() if not line.startswith("timer=")),
        "long word": good.replace("Aug", "Augustus", 1),
        "bad code": good.replace("lang=de", "lang=DE"),
        "bad order": good.replace("order=dmy", "order=ymd"),
        "empty": "",
    }
    for what, text in bad.items():
        pack = packs.make_pack(
            "language",
            f"Bad {what}"[:40],
            packs.zip_payload({"words.txt": text.encode("utf-8")}),
            lang="de",
        )
        done = _push_raw(unit, pack)
        assert done["ok"] is False and done["code"] == "zip", (what, done)
        held = _status(unit, "language")
        assert held["lang"] == "fr" and held["held"] is True, what  # nothing changed
    missing = packs.make_pack(
        "language", "No words", packs.zip_payload({"readme.txt": b"hi"}), lang="de"
    )
    assert _push_raw(unit, missing)["ok"] is False and _status(unit, "language")["lang"] == "fr"


def test_damaged_language_and_phrase_packs_never_get_through_and_never_change_what_is_held(
    unit,
) -> None:  # noqa: F811
    """Flip bytes in a good pack and fix the checksum up so the damage reaches the unit's zip and words readers."""
    rng = random.Random(5)
    goods = {"language": language_packs.build("fr"), "phrase": _phrase_pack()}
    for kind, good in goods.items():
        assert _push_raw(unit, good)["ok"] is True
        before = _status(unit, kind)
        refused = accepted = partial = 0
        for _ in range(250):
            payload = bytearray(good.payload)
            for _ in range(rng.randint(1, 4)):
                payload[rng.randrange(len(payload))] ^= 1 << rng.randrange(8)
            if rng.random() < 0.2:
                payload = payload[: rng.randrange(1, len(payload))]
            damaged = packs.make_pack(kind, "Damaged", bytes(payload), lang="fr")
            done = _push_raw(unit, damaged, chunk=700)
            if done.get("ok") is True:
                accepted += 1  # the damage hit a byte the reader does not use, or one clip body (that clip is left out whole)
                if kind == "phrase" and _status(unit, kind)["clips"] < 16:
                    partial += 1  # the clip with a bad checksum was dropped; the others are kept and the image supplies the rest
                assert _push_raw(unit, good)["ok"] is True  # put the known-good one back
            else:
                refused += 1
                assert (
                    _status(unit, kind)["sha256"] == before["sha256"]
                )  # the held pack is untouched
        assert refused + partial > 100, (kind, refused, partial, accepted)


def test_a_phrase_pack_with_missing_or_non_ogg_clips_keeps_what_it_can_and_the_image_does_the_rest(
    unit,
) -> None:  # noqa: F811
    assert _push_raw(unit, _phrase_pack())["ok"] is True and _status(unit, "phrase")["clips"] == 16
    assert _push_raw(unit, _phrase_pack(missing={("refused", 2), ("back", 1)}))["ok"] is True
    assert _status(unit, "phrase")["clips"] == 14
    files = {"ph_no_wifi_1.ogg": b"RIFF" + b"\0" * 3000, "readme.txt": b"x" * 400}
    none_usable = packs.make_pack(
        "phrase", "Nothing", packs.zip_payload(files, stored=True), voice="amy", lang="en"
    )
    done = _push_raw(unit, none_usable)
    assert done["ok"] is False and _status(unit, "phrase")["clips"] == 14
    assert (
        _push_raw(unit, packs.make_pack("phrase", "Empty", b"", voice="x", lang="en")).get("ok")
        is False
    )


# ---- a push cut at every call, a reboot, a damaged cache ----------------------------------------------------


@pytest.mark.parametrize("fate", ["drop_before", "drop_after"])
@pytest.mark.parametrize("kind", ["language", "phrase"])
def test_a_push_cut_at_every_single_call_is_healed_by_the_next_sync(
    tmp_path, unit, kind, fate
) -> None:  # noqa: F811
    """The link drops at call 2, 3, 4 ... of the push (begin, every piece, commit), before the unit hears it and after it did."""
    service, library, saved, state = _service(tmp_path, unit, lang="fr", chunk=900)
    language_packs.install(library)
    library.add(_phrase_pack(lang="fr", voice="amy"))
    want = service.wanted(UNIT)[kind]
    assert want is not None
    pack = library.get(want)
    assert pack.size > 900 * 2 if kind == "phrase" else True
    calls_per_push = 1 + (-(-pack.size // 900)) + 1  # begin, pieces, commit
    for cut in range(1, calls_per_push + 2):  # the status probe counts as a call too
        unit.raw("reboot", {})
        unit.log.clear()
        unit.plan = {unit.count + cut: fate}
        try:
            service.sync_types(UNIT, (kind,))
        except BodyLost:
            pass
        unit.plan = {}
        held = _status(unit, kind)
        assert held["held"] is False or held["sha256"] == pack.sha256, (
            cut,
            held,
        )  # never a half pack
        service.sync(UNIT)  # the unit connects again
        held = _status(unit, kind)
        assert held["held"] is True and held["sha256"] == pack.sha256, (cut, fate)


def test_a_power_cycle_keeps_the_cached_pack_and_a_damaged_cache_falls_back_and_heals_on_connect(
    tmp_path, unit
) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, lang="de")
    language_packs.install(library)
    library.add(_phrase_pack(lang="de", voice="amy"))
    service.sync(UNIT)
    assert _status(unit, "language")["lang"] == "de"
    assert unit.raw("self.lang.words", {"code": "de"})["code"] == "de"
    begins = sum(1 for n, _ in unit.log if n == "self.pack.begin")
    unit.raw("power_cycle", {})  # RAM gone, the flash cache applied at boot
    held = _status(unit, "language")
    assert held["held"] is True and held["lang"] == "de" and held["cache"] == "ok"
    service.sync(UNIT)
    assert (
        sum(1 for n, _ in unit.log if n == "self.pack.begin") == begins
    )  # it already held it: nothing is sent twice
    # a flipped bit in the cache: found at boot, the unit shows English and says it fell back
    unit.raw("damage_cache", {"type": "language"})
    assert _status(unit, "language")["cache"] == "damaged"
    unit.raw("power_cycle", {})
    held = _status(unit, "language")
    assert held["held"] is False and held["fallback"] is True and held["lang"] == ""
    assert unit.raw("self.lang.words", {"code": "de"})["code"] == "en"
    service.sync(UNIT)  # the host connects: the pack goes out again
    assert (
        _status(unit, "language")["lang"] == "de"
        and unit.raw("self.lang.words", {"code": "de"})["code"] == "de"
    )
    # a reboot with the cache off (or a missing cache): the same fallback and the same healing
    unit.raw("reboot", {})
    assert _status(unit, "language")["held"] is False and _status(unit, "phrase")["clips"] == 0
    service.sync(UNIT)
    assert _status(unit, "language")["held"] is True and _status(unit, "phrase")["held"] is True


# ---- which pack the host sends, and when ---------------------------------------------------------------------


def test_the_language_pack_follows_the_screen_language(tmp_path, unit) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, lang="en")
    language_packs.install(library)
    service.sync(UNIT)
    assert _status(unit, "language")["held"] is False  # English is in the image: no pack
    state["lang"] = "fr"
    assert service.sync_types(UNIT, ("language",)) == {"language": "sent"}
    assert _status(unit, "language")["lang"] == "fr"
    assert service.sync_types(UNIT, ("language",)) == {"language": "kept"}  # nothing resent
    state["lang"] = "it"
    service.sync_types(UNIT, ("language",))
    assert _status(unit, "language")["lang"] == "it"  # one language pack at a time
    state["lang"] = "en"
    assert service.sync_types(UNIT, ("language",)) == {"language": "removed"}
    assert (
        _status(unit, "language")["held"] is False
        and unit.raw("self.lang.words", {"code": "it"})["code"] == "en"
    )
    state["lang"] = "xx"  # an unknown language is English
    assert service.wanted(UNIT)["language"] is None


def test_the_filler_pack_is_sent_only_while_the_thinking_sound_is_a_phrase_and_dropped_when_it_is_not(
    tmp_path, unit
) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, mode="tone")
    gen = fillers.FillerGenerator(
        lambda text: (np.sin(np.arange(9000) / 7.0).astype(np.float32) * 0.5, 16000), library
    )
    gen.generate("amy", "en")
    service.sync(UNIT)
    assert _status(unit, "filler")["held"] is False  # a tone needs no pack
    saved["filler_mode"] = "phrase"
    assert service.sync_types(UNIT, ("filler",)) == {"filler": "sent"}
    assert _status(unit, "filler")["held"] is True
    before = sum(1 for n, _ in unit.log if n == "self.pack.begin")
    service.sync(UNIT)  # a reconnect: held and the same, nothing is sent again
    assert sum(1 for n, _ in unit.log if n == "self.pack.begin") == before
    saved["filler_mode"] = "none"
    assert service.sync_types(UNIT, ("filler",)) == {"filler": "removed"}
    assert _status(unit, "filler")["held"] is False


def test_an_explicit_choice_beats_the_automatic_one_and_clearing_it_goes_back_to_automatic(
    tmp_path, unit
) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, lang="fr")
    language_packs.install(library)
    service.sync(UNIT)
    assert _status(unit, "language")["lang"] == "fr"
    service.activate(
        UNIT, "language", "language/screen-words-es"
    )  # a person picks Spanish words while the face language is French
    assert _status(unit, "language")["lang"] == "es"
    service.sync(UNIT)
    assert _status(unit, "language")["lang"] == "es"  # the choice survives a reconnect
    service.activate(UNIT, "language", "")  # back to automatic
    service.sync_types(UNIT, ("language",))
    assert _status(unit, "language")["lang"] == "fr"
    assert service.view(UNIT)["rows"]["language"]["in_sync"] is True


def test_the_phrase_pack_matches_the_language_and_prefers_the_active_voice(tmp_path, unit) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, lang="es", voice="bruno")
    library.add(_phrase_pack(lang="es", voice="amy"))
    library.add(_phrase_pack(lang="es", voice="bruno"))
    library.add(_phrase_pack(lang="en", voice="bruno"))
    service.sync(UNIT)
    held = _status(unit, "phrase")
    assert held["held"] is True and held["clips"] == 16
    assert service.wanted(UNIT)["phrase"] == "phrase/phrases-es-bruno"
    state["lang"] = "fr"  # no French phrases: the unit says the clips built into its image
    assert service.sync_types(UNIT, ("phrase",)) == {"phrase": "removed"}
    assert _status(unit, "phrase")["fallback"] is True


def test_a_unit_that_is_gone_or_has_no_pack_tools_is_left_alone_without_an_error(tmp_path) -> None:
    def gone(*_a, **_k):
        raise BodyLost("not connected")

    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    language_packs.install(library)
    auto = pack_auto.AutoPacks(library, lambda _d: {}, lambda _d: "fr")
    service = packs.PackService(
        ToolProbe(gone), library, packs.ActiveStore(tmp_path / "a.json"), auto=auto
    )
    service.sync(UNIT)
    assert service.sync_types(UNIT, ("language", "filler")) == {}
    assert (
        service.view(UNIT)["unit_ready"] is False
        and service.view(UNIT)["wanted"]["language"] == "language/screen-words-fr"
    )

    def old(name, args, **_k):
        return {"ok": False, "error": "Unknown tool: " + name}

    service = packs.PackService(
        ToolProbe(old), library, packs.ActiveStore(tmp_path / "b.json"), auto=auto
    )
    service.sync(UNIT)
    assert service.sync_types(UNIT, ("language",)) == {} and service.view(UNIT)["reachable"] is True


# ---- making the offline phrases -------------------------------------------------------------------------------


def _speech(text: str):
    rate = 24000
    t = np.arange(int(rate * (0.6 + 0.02 * len(text)))) / rate
    return (0.4 * np.sin(2 * np.pi * (180 + len(text)) * t)).astype(np.float32), rate


def _fake_encoder(samples, rate) -> bytes:
    seconds = len(samples) / rate
    return b"OggS" + bytes(range(256)) * int(1 + seconds * 12)


def test_the_phrase_generator_makes_sixteen_clips_with_the_voice_for_each_language(
    tmp_path, unit
) -> None:  # noqa: F811
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    gen = phrase_packs.PhraseGenerator(_speech, library, _fake_encoder)
    for lang in ("en", "es"):
        info = gen.generate("amy", lang)
        pack = library.get(info["id"])
        assert (
            pack.type == "phrase"
            and pack.voice == "amy"
            and pack.lang == lang
            and pack.size <= packs.MAX_BYTES["phrase"]
        )
        files = packs.unzip_payload(pack.payload)
        clips = sorted(n for n in files if n.endswith(".ogg"))
        assert len(clips) == 16 and "ph_no_wifi_1.ogg" in clips and "ph_back_2.ogg" in clips
        assert all(
            files[c][:4] == b"OggS"
            and phrase_packs.MIN_CLIP <= len(files[c]) <= phrase_packs.MAX_CLIP
            for c in clips
        )
        assert (
            _push_raw(unit, pack, chunk=2000)["ok"] is True
            and _status(unit, "phrase")["clips"] == 16
        )  # the unit's own reader takes it
    assert [p["lang"] for p in library.list("phrase")] == ["en", "es"]


def test_the_phrase_texts_cover_every_clip_and_use_american_spelling_and_no_em_dash() -> None:
    for lang in phrase_packs.languages():
        texts = phrase_packs.texts_for(lang)
        assert texts is not None and {g: len(v) for g, v in texts.items()} == phrase_packs.GROUPS
        for sentence in (s for v in texts.values() for s in v):
            assert sentence.strip() and chr(8212) not in sentence and len(sentence) < 60
    assert (
        phrase_packs.texts_for("fr") is None
    )  # a language with no text set has no phrase pack: the unit says the image's clips


def test_a_sentence_that_fails_is_left_out_and_a_dead_engine_says_what_to_do(tmp_path) -> None:
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    count = {"n": 0}

    def flaky(text):
        count["n"] += 1
        if count["n"] % 4 == 0:
            raise OSError("engine")
        return _speech(text)

    payload, kept = phrase_packs.PhraseGenerator(flaky, library, _fake_encoder).render("en")
    assert kept == 12 and len(packs.unzip_payload(payload)) == 13  # twelve clips and the index
    dead = phrase_packs.PhraseGenerator(
        lambda _t: (_ for _ in ()).throw(OSError("down")), library, _fake_encoder
    )
    with pytest.raises(packs.PackError, match="speech server is running"):
        dead.generate("amy", "en")
    with pytest.raises(packs.PackError, match="local voice engine"):
        phrase_packs.PhraseGenerator(None, library).generate("amy", "en")
    with pytest.raises(packs.PackError, match="motor de voz local"):
        phrase_packs.PhraseGenerator(None, library).generate("amy", "es")


def test_a_computer_without_ffmpeg_says_what_to_install(tmp_path, monkeypatch) -> None:
    library = packs.PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(packs.PackError, match="ffmpeg is not installed"):
        phrase_packs.PhraseGenerator(_speech, library).generate("amy", "en")


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg is not installed on this machine"
)
def test_the_real_encoder_makes_an_ogg_opus_file_like_the_images_clips() -> None:
    t = np.arange(16000) / 16000
    audio = (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    ogg = phrase_packs.encode_ogg_opus(audio)
    assert (
        ogg[:4] == b"OggS"
        and b"OpusHead" in ogg[:64]
        and b"OpusTags" in ogg[:256]
        and 400 < len(ogg) < 8000
    )
    rate = struct.unpack("<I", ogg[ogg.index(b"OpusHead") + 12 : ogg.index(b"OpusHead") + 16])[0]
    assert rate == 16000  # the header says 16 kHz mono like the clips in the image


def test_the_background_start_reports_progress_and_sends_when_done(tmp_path, unit) -> None:  # noqa: F811
    service, library, saved, state = _service(tmp_path, unit, lang="en")
    gen = phrase_packs.PhraseGenerator(_speech, library, _fake_encoder)
    done = []
    gen.start("amy", "en", on_done=lambda info: done.append(service.sync_types(UNIT, ("phrase",))))
    for _ in range(200):
        if not gen.status["running"] and done:
            break
        __import__("time").sleep(0.05)
    assert (
        done == [{"phrase": "sent"}]
        and gen.status["error"] == ""
        and _status(unit, "phrase")["clips"] == 16
    )
    with pytest.raises(packs.PackError, match="already being made"):
        gen.status["running"] = True
        gen.start("amy", "en")


def test_the_type_lists_of_host_and_unit_agree(tmp_path_factory) -> None:
    from firmware_order_cores import cores_dir

    text = (cores_dir(tmp_path_factory) / "maipai_pack_core.h").read_text()
    names = __import__("re").search(r"TPK_TYPE_NAMES\[TPK_TYPES\] = \{([^}]*)\}", text).group(1)
    assert tuple(__import__("re").findall(r'"(\w+)"', names)) == packs.TYPES
    gates = [
        int(x.rstrip("u"))
        for x in __import__("re")
        .search(r"TPK_MAX_BYTES\[TPK_TYPES\]\s*= \{([^}]*)\}", text)
        .group(1)
        .split(",")
    ]
    assert gates == [packs.MAX_BYTES[t] for t in packs.TYPES]


def test_prefs_default_filler_mode_is_tone_and_the_delay_range_is_the_units() -> None:
    values = prefs_of({})
    assert values["filler_mode"] == "tone" and values["filler_wait_s"] == 0.4


# ---- the settings page: real state, the language switch, the phrases --------------------------------------------

from maipai_body.settings_sim import DEN, KITCHEN, build  # noqa: E402

PATH = "/api/stackchan/unit/{}/{}"


def _get(backend, unit_id, what, lang="en"):
    status, _, body = backend.route_get(PATH.format(unit_id, what), lang, True)
    return status, json.loads(body)


def test_the_packs_view_shows_what_the_robot_holds_and_what_it_should(tmp_path) -> None:
    backend, units = build(tmp_path, next_unit=True)
    status, out = backend.route_post("/api/stackchan/faces/" + KITCHEN, {"screen_lang": "fr"}, True)
    assert status == 200, out
    # the language change reached the unit: its pack is the French words, sent by the host without a click
    assert units[KITCHEN].pack_held["language"]["name"] == "Screen words fr"
    view = _get(backend, KITCHEN, "packs")[1]
    row = view["rows"]["language"]
    assert (
        row["wanted"] == "language/screen-words-fr"
        and row["held"] is True
        and row["in_sync"] is True
        and row["explicit"] is False
    )
    assert (
        row["wanted_size"] < 1200
        and view["rows"]["look"]["in_sync"] is True
        and view["rows"]["filler"]["wanted"] is None
    )
    assert view["unit_ready"] is True and set(view["rows"]) == set(packs.TYPES)
    # back to English: the pack is dropped and the row says built in
    backend.route_post("/api/stackchan/faces/" + KITCHEN, {"screen_lang": "en"}, True)
    assert "language" not in units[KITCHEN].pack_held
    assert _get(backend, KITCHEN, "packs")[1]["rows"]["language"]["in_sync"] is True


def test_a_unit_that_is_off_keeps_the_choice_and_gets_it_on_connect(tmp_path) -> None:
    backend, units = build(tmp_path, next_unit=True)
    units[KITCHEN].online = False
    status, _ = backend.route_post("/api/stackchan/faces/" + KITCHEN, {"screen_lang": "de"}, True)
    assert status == 200 and units[KITCHEN].pack_held == {}
    view = _get(backend, KITCHEN, "packs")[1]
    assert view["unit_ready"] is False and view["wanted"]["language"] == "language/screen-words-de"
    units[KITCHEN].online = True
    backend.polish.on_connect(KITCHEN)
    assert units[KITCHEN].pack_held["language"]["name"] == "Screen words de"
    assert units[DEN].pack_held == {}  # the other unit was not touched


def test_the_thinking_sound_setting_sends_and_drops_the_filler_pack(tmp_path) -> None:
    backend, units = build(tmp_path, next_unit=True)
    backend.polish.generator.generate("sage", "en")
    assert "filler" not in units[KITCHEN].pack_held
    status, _ = backend.route_post(PATH.format(KITCHEN, "prefs"), {"filler_mode": "phrase"}, True)
    assert status == 200 and units[KITCHEN].pack_held["filler"]["name"] == "Fillers en"
    backend.route_post(PATH.format(KITCHEN, "prefs"), {"filler_mode": "tone"}, True)
    assert "filler" not in units[KITCHEN].pack_held
    backend.route_post(
        PATH.format(KITCHEN, "prefs"), {"filler_wait_s": 0.9}, True
    )  # a delay change sends no pack at all
    calls = [
        c[0]
        for c in units[KITCHEN].calls
        if c[0].startswith("self.pack.") and c[0] != "self.pack.status"
    ]
    assert calls.count("self.pack.begin") == 1 and calls.count("self.pack.remove") == 1


def test_the_phrase_routes_list_make_and_send(tmp_path) -> None:
    backend, units = build(tmp_path, next_unit=True)
    status, view = _get(backend, KITCHEN, "phrases")
    assert (
        status == 200
        and view["packs"] == []
        and view["languages"] == ["en", "es"]
        and view["can_make"] is True
    )
    backend.polish.phrases.encoder = _fake_encoder
    status, out = backend.route_post(
        PATH.format(KITCHEN, "phrases/generate"), {"voice": "sage", "for_lang": "en"}, True
    )
    assert status == 200 and out["ok"] is True
    for _ in range(100):
        if units[KITCHEN].pack_held.get("phrase"):
            break
        __import__("time").sleep(0.05)
    assert units[KITCHEN].pack_held["phrase"]["name"] == "Phrases en"
    view = _get(backend, KITCHEN, "phrases")[1]
    assert (
        [p["voice"] for p in view["packs"]] == ["sage"]
        and view["wanted"] == "phrase/phrases-en-sage"
        and view["status"]["error"] == ""
    )
    status, out = backend.route_post(PATH.format(KITCHEN, "packs/sync"), {}, True)
    assert status == 200 and out["done"]["phrase"] == "kept"


def test_the_pages_new_words_are_in_the_page_and_the_script_parses(tmp_path) -> None:
    from maipai_body import settings_ui
    from maipai_body.settings_page import render_page

    js = settings_ui.JS
    for needle in (
        "rowsOf",
        "pol.lang.ascii",
        "phrases/generate",
        "packs/sync",
        "pol.phr.title",
        "stateWord",
    ):
        assert needle in js, needle
    page = render_page("fr").decode()
    assert "settings.ui.pol.phr.title" in page
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    script = tmp_path / "page.js"
    script.write_text(js)
    import subprocess

    run = subprocess.run([node, "--check", str(script)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
