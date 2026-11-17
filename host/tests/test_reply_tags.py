# ruff: noqa: E501
"""Mood tags, overlay tags, the keyword fallback, and what the voice path does with them."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from maipai_body import reply_tags
from maipai_body.overlays import OverlayDirector, OverlayError
from maipai_body.speech.reply_stream import ReplyTagger, TagStripper
from maipai_body.unit_tools import ToolProbe
from tests.test_reply_streaming import Tts, deltas, run_bridge


def run(chunks, **kwargs):
    tagger = ReplyTagger(**kwargs)
    items = []
    for chunk in chunks:
        items += tagger.feed(chunk)
    items += tagger.flush()
    return items


def spoken(items):
    return [i.text for i in items if i.text]


def cues(items):
    return [(c.kind, c.name) for i in items for c in i.cues]


# ---- the grammar -------------------------------------------------------------------------------------


def test_the_tag_list_is_in_one_place_and_the_prompt_names_every_tag():
    assert reply_tags.MOODS == ("happy", "sad", "surprised", "angry", "doubt", "love", "sleepy", "neutral")
    assert set(reply_tags.MOOD_CUE) == set(reply_tags.MOODS)
    suffix = reply_tags.persona_with_tags("You are kind.")
    assert all(f"[{m}]" in suffix for m in reply_tags.MOODS)
    assert reply_tags.persona_with_tags(suffix) == suffix  # never added twice


@pytest.mark.parametrize(
    ("text", "kind", "name"),
    [
        ("happy", "mood", "happy"), ("feliz", "mood", "happy"), ("TRISTE", "mood", "sad"), ("mood:angry", "mood", "angry"),
        ("rain", "overlay", "rain"), ("lluvia", "overlay", "rain"), ("fuegos artificiales", "overlay", "fireworks"),
        ("/lluvia", "overlay_end", "rain"), ("/rain", "overlay_end", "rain"), ("nieve", "overlay", "snow"),
        ("wave", "unknown", ""), ("", "unknown", ""), ("/happy", "unknown", ""), ("happy now", "unknown", ""),
    ],
)  # fmt: skip
def test_parse_tag_in_english_and_spanish(text, kind, name):
    tag = reply_tags.parse_tag(text)
    assert (tag.kind, tag.name) == (kind, name)


def test_every_overlay_has_a_spanish_alias_or_its_own_name_and_intensity_words_work():
    for name in reply_tags.OVERLAYS:
        assert reply_tags.parse_tag(name).name == name
    assert reply_tags.parse_tag("rain heavy").intensity == "heavy"
    assert reply_tags.parse_tag("lluvia:fuerte").intensity == "heavy"
    assert reply_tags.parse_tag("snow soft").intensity == "light"
    assert reply_tags.parse_tag("rain lots").intensity == "normal"
    assert reply_tags.parse_tag("fuegos artificiales fuerte").intensity == "heavy"


@pytest.mark.parametrize(
    ("text", "mood"),
    [
        ("I am sorry, I cannot find it.", "sad"), ("Unfortunately it is closed today.", "sad"),
        ("Lo siento, no lo encuentro.", "sad"), ("Desafortunadamente ya cerró.", "sad"),
        ("Wow!? That is huge", "surprised"), ("¡Increíble! Ganaste.", "surprised"),
        ("Haha, that was funny.", "happy"), ("Jaja, qué gracioso.", "happy"),
        ("I love you too.", "love"), ("Te quiero mucho.", "love"),
        ("Good night, sleep well.", "sleepy"), ("Buenas noches.", "sleepy"),
        ("Hmm, I am not sure.", "doubt"), ("Quizás mañana.", "doubt"),
        ("It is three o'clock.", None), ("Son las tres.", None),
    ],
)  # fmt: skip
def test_the_fallback_guesses_a_mood_from_words_and_punctuation(text, mood):
    assert reply_tags.guess_mood(text) == mood


# ---- the stream splitter -----------------------------------------------------------------------------


def test_a_leading_mood_tag_is_stripped_and_becomes_a_cue_before_the_sentence():
    items = run(["[hap", "py] Sure, ", "I can do that. Next."])
    assert spoken(items) == ["Sure, I can do that.", "Next."]
    assert cues(items) == [("mood", "happy")]
    assert items[0].cues and not items[0].text  # the cue comes first


def test_an_overlay_span_starts_with_its_text_and_ends_after_it():
    items = run(["[rain]it is going to rain all day[/rain] so take a coat."])
    assert spoken(items) == ["it is going to rain all day so take a coat."]
    assert cues(items) == [("overlay", "rain"), ("overlay_end", "rain")]
    assert [i.text for i in items] == ["", "it is going to rain all day so take a coat.", ""]


def test_an_unclosed_tag_runs_to_the_end_of_its_sentence():
    items = run(["[snow]Snow is coming. Bring boots."])
    assert cues(items) == [("overlay", "snow"), ("overlay_end", "snow")]
    assert [i.text for i in items] == ["", "Snow is coming.", "", "Bring boots."]


def test_a_span_over_several_sentences_ends_after_the_one_with_the_closing_tag():
    items = run(["[lluvia]Llueve mucho. Sigue lloviendo. Todo el día.[/lluvia] Adiós."])
    assert spoken(items) == ["Llueve mucho.", "Sigue lloviendo.", "Todo el día. Adiós."]
    assert cues(items) == [("overlay", "rain"), ("overlay_end", "rain")]
    assert items[-1].cues and items[-1].cues[0].kind == "overlay_end"


def test_unknown_tags_are_dropped_and_never_spoken_and_nest_with_moods():
    items = run(["[sad] Oh no, [wave]it [rain]rains[/rain] [/zzzz] now. [foo]Done."])
    assert spoken(items) == ["Oh no, it rains now.", "Done."]
    assert all("[" not in t and "]" not in t for t in spoken(items))
    assert ("mood", "sad") in cues(items) and ("overlay", "rain") in cues(items)
    assert not any(c == ("overlay_end", "zzz") for c in cues(items))  # a stray close of a stopped overlay does nothing


def test_a_tag_split_across_chunks_and_a_closing_tag_alone_at_the_end():
    items = run(["[ra", "in heavy]It pours. ", "[/ra", "in]"])
    assert cues(items) == [("overlay", "rain"), ("overlay_end", "rain")]
    assert next(c for i in items for c in i.cues).intensity == "heavy"


def test_the_fallback_supplies_a_mood_only_when_the_first_sentence_has_no_tag():
    assert cues(run(["Sorry about that. Bye."])) == [("mood", "sad")]
    assert cues(run(["[happy] Sorry about that."])) == [("mood", "happy")]
    assert cues(run(["It is fine. Sorry later."])) == []  # only the first sentence is guessed
    assert cues(run(["Lo siento mucho."])) == [("mood", "sad")]


def test_switches_remove_the_tags_but_make_no_cues():
    items = run(["[happy] Hi [rain]there[/rain]. Sorry."], moods=False, overlays=False)
    assert spoken(items) == ["Hi there.", "Sorry."] and cues(items) == []


def test_the_plain_stripper_still_leaves_nothing_behind():
    assert TagStripper().feed("Hi [x] there.") == "Hi  there."


# ---- the voice path ----------------------------------------------------------------------------------


class Face:
    def __init__(self):
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, state, mood=None):
        self.calls.append((state, mood))


def sync_side(bridge):
    bridge._side = SimpleNamespace(submit=lambda fn, *a, **k: fn(*a, **k), shutdown=lambda **k: None)


def test_a_mood_tag_sets_the_face_through_the_expression_path_and_is_not_spoken(monkeypatch):
    face = Face()

    def setup(bridge):
        sync_side(bridge)
        bridge.expression_sink = face

    run_bridge(monkeypatch, lambda b: deltas("[sad] I am sorry. It broke."), setup=setup)
    assert Tts.spoken == ["I am sorry.", "It broke."]
    assert ("reply_mood", "sadness") in face.calls


def test_emotion_faces_off_still_strips_the_tag_but_keeps_the_face_alone(monkeypatch):
    face = Face()

    def setup(bridge):
        sync_side(bridge)
        bridge.expression_sink = face
        bridge.prefs_for = lambda _d: {"emotion_faces": False}

    run_bridge(monkeypatch, lambda b: deltas("[sad] I am sorry."), setup=setup)
    assert Tts.spoken == ["I am sorry."]
    assert not any(state == "reply_mood" for state, _ in face.calls)


def test_a_reply_that_is_not_streamed_gets_its_tags_handled_too(monkeypatch):
    face = Face()

    def setup(bridge):
        sync_side(bridge)
        bridge.expression_sink = face

    run_bridge(monkeypatch, lambda b: iter([SimpleNamespace(reply_text="[love] Aw. Thanks.")]), setup=setup)
    assert Tts.spoken == ["Aw.", "Thanks."]
    assert ("reply_mood", "love") in face.calls


class FakeOverlay:
    def __init__(self):
        self.calls: list[tuple] = []

    def set(self, device, name, intensity, seconds):
        self.calls.append(("set", device, name, intensity, seconds))
        return True

    def clear(self, device):
        self.calls.append(("clear", device))
        return True


def test_overlay_tags_call_the_director_with_the_unit_and_end_after_the_span(monkeypatch):
    overlay = FakeOverlay()

    def setup(bridge):
        sync_side(bridge)
        bridge.overlay_director = overlay

    run_bridge(monkeypatch, lambda b: deltas("[rain heavy]it will pour[/rain] today. Bye."), setup=setup)
    assert Tts.spoken == ["it will pour today.", "Bye."]
    assert overlay.calls[0][0:4] == ("set", "02:00:00:00:00:15", "rain", "heavy")
    assert overlay.calls[1] == ("clear", "02:00:00:00:00:15")


def test_privacy_and_the_overlay_switch_stop_decoration_but_not_the_speech(monkeypatch):
    overlay = FakeOverlay()

    def muted(bridge):
        sync_side(bridge)
        bridge.overlay_director = overlay
        bridge.muted_reason = lambda: "muted"

    run_bridge(monkeypatch, lambda b: deltas("[rain]wet[/rain] day."), setup=muted)
    assert Tts.spoken == ["wet day."] and not any(c[0] == "set" for c in overlay.calls)

    overlay2 = FakeOverlay()

    def off(bridge):
        sync_side(bridge)
        bridge.overlay_director = overlay2
        bridge.prefs_for = lambda _d: {"overlays_enabled": False}

    run_bridge(monkeypatch, lambda b: deltas("[rain]wet[/rain] day."), setup=off)
    assert Tts.spoken == ["wet day."] and overlay2.calls == []


# ---- the director: a unit without the tools is skipped quietly -----------------------------------------


def make_director(unit_has_tools: bool):
    sent: list[tuple[str, dict]] = []

    def call(name, args, *, device_id=None, timeout=4.0):
        sent.append((name, dict(args)))
        if not unit_has_tools:
            return {"ok": False, "error": f"Unknown tool: {name}"}
        return {"ok": True}

    return OverlayDirector(ToolProbe(call)), sent


def test_a_unit_without_the_overlay_tools_is_skipped_quietly_and_asked_only_once():
    director, sent = make_director(False)
    assert director.set("aa:bb", "rain", "normal", 5) is False
    assert director.set("aa:bb", "snow", "normal", 5) is False
    assert director.clear("aa:bb") is False
    assert [n for n, _ in sent] == ["self.overlay.status"]  # one probe, nothing else sent


def test_a_unit_with_the_tools_gets_set_and_clear_with_clean_values():
    director, sent = make_director(True)
    assert director.set("aa:bb", "rain", "heavy", 99999) is True
    assert director.clear("aa:bb") is True
    assert sent[1] == ("self.overlay.set", {"name": "rain", "intensity": "heavy", "seconds": reply_tags.MAX_SECONDS})
    assert sent[2][0] == "self.overlay.clear"


def test_the_remote_button_says_plainly_when_the_unit_cannot_yet_and_rejects_bad_input():
    director, _ = make_director(False)
    result = director.remote_set("aa:bb", "lluvia", "heavy", 6, "es")
    assert result["pending"] is True and "próxima actualización" in result["message"]
    with pytest.raises(OverlayError, match="not known"):
        director.remote_set("aa:bb", "tornado", None, None)
    with pytest.raises(OverlayError, match="1 to"):
        director.remote_set("aa:bb", "rain", None, 0)


# ---- the host plays a filler when the unit cannot -----------------------------------------------------


class FakeFiller:
    def __init__(self):
        self.calls: list[tuple] = []

    def play(self, playback, device_id, mode, lang):
        self.calls.append((device_id, mode, lang))
        return True


def slow(b):
    time.sleep(0.6)
    yield from deltas("Late reply.")


def test_a_slow_first_audio_plays_one_filler_after_the_wait_once_per_turn(monkeypatch):
    filler = FakeFiller()

    def setup(bridge):
        bridge.filler_player = filler
        bridge.prefs_for = lambda _d: {"filler_mode": "phrase", "filler_wait_s": 0.2}

    run_bridge(monkeypatch, slow, setup=setup)
    assert len(filler.calls) == 1 and filler.calls[0][1] == "phrase"
    assert Tts.spoken == ["Late reply."]


def test_no_filler_when_off_when_fast_or_when_muted(monkeypatch):
    for prefs, stream, muted in (
        ({"filler_mode": "none", "filler_wait_s": 0.2}, slow, False),
        ({"filler_mode": "tone", "filler_wait_s": 1.5}, slow, False),
        ({"filler_mode": "tone", "filler_wait_s": 0.2}, slow, True),
    ):
        filler = FakeFiller()

        def setup(bridge, prefs=prefs, filler=filler, muted=muted):
            bridge.filler_player = filler
            bridge.prefs_for = lambda _d: prefs
            if muted:
                bridge.muted_reason = lambda: "muted"

        run_bridge(monkeypatch, stream, setup=setup)
        assert filler.calls == [], prefs


# ---- the named combinations (patch O01) ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("stormy", "stormy"), ("storm", "stormy"), ("tormenta", "stormy"), ("tormenta eléctrica", "stormy"), ("thunderstorm", "stormy"),
        ("rainy", "rainy"), ("lluvioso", "rainy"), ("snowy", "snowy"), ("nevado", "snowy"), ("nevada", "snowy"),
        ("sunny", "sunny"), ("soleado", "sunny"), ("día soleado", "sunny"), ("windy", "windy"), ("ventoso", "windy"),
        ("night", "night"), ("noche", "night"), ("noche estrellada", "night"), ("party", "party"), ("fiesta", "party"),
        ("celebrate", "celebrate"), ("celebración", "celebrate"), ("celebracion", "celebrate"),
        ("lovely", "love"), ("romántico", "love"), ("enamorada", "love"), ("sleeping", "sleeping"), ("durmiendo", "sleeping"),
        ("thunder", "thunder"), ("trueno", "thunder"), ("rain", "rain"), ("viento", "wind"), ("sol", "sun"),
    ],
)  # fmt: skip
def test_the_combined_overlays_have_english_and_spanish_names(text, name):
    tag = reply_tags.parse_tag(text)
    assert (tag.kind, tag.name) == ("overlay", name)


def test_every_combined_overlay_has_its_own_tag_and_a_closing_tag():
    assert reply_tags.OVERLAYS == reply_tags.ELEMENT_OVERLAYS + reply_tags.COMBINED_OVERLAYS and len(reply_tags.OVERLAYS) == 26
    for name in reply_tags.COMBINED_OVERLAYS:
        assert reply_tags.parse_tag(f"overlay:{name}").name == name
        assert reply_tags.parse_tag(f"/{name}") == reply_tags.Tag("overlay_end", name)
        assert reply_tags.parse_tag(f"{name} heavy").intensity == "heavy"
    assert reply_tags.parse_tag("tormenta fuerte") == reply_tags.Tag("overlay", "stormy", "heavy")


def test_love_stays_the_mood_unless_the_tag_says_overlay():
    assert reply_tags.parse_tag("love") == reply_tags.Tag("mood", "love")
    assert reply_tags.parse_tag("amor") == reply_tags.Tag("mood", "love")
    assert reply_tags.parse_tag("overlay:love") == reply_tags.Tag("overlay", "love")
    assert reply_tags.parse_tag("love heavy") == reply_tags.Tag("overlay", "love", "heavy")
    assert reply_tags.parse_tag("/love") == reply_tags.Tag("overlay_end", "love")
    assert reply_tags.parse_tag("mood:love") == reply_tags.Tag("mood", "love")


def test_a_combined_overlay_span_runs_through_the_stream_splitter():
    items = run(["[stormy]it is a wild night outside[/stormy] stay in."])
    assert cues(items) == [("overlay", "stormy"), ("overlay_end", "stormy")]
    assert spoken(items) == ["it is a wild night outside stay in."]
    items = run(["[overlay:love]I like you[/love]. [love] Me too."])
    assert cues(items) == [("overlay", "love"), ("overlay_end", "love"), ("mood", "love")]


def test_the_settings_page_sends_a_combined_name_and_love_as_the_overlay():
    director, sent = make_director(True)
    assert director.remote_set("aa:bb", "love", "heavy", 6)["name"] == "love"
    assert director.remote_set("aa:bb", "celebrate", None, None)["name"] == "celebrate"
    sets = [args for tool, args in sent if tool == "self.overlay.set"]
    assert sets[0] == {"name": "love", "intensity": "heavy", "seconds": 6}
    assert sets[1]["name"] == "celebrate"
