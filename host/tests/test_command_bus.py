# ruff: noqa: E501
"""The command bus and the scene table (docs/design/llm-display-control-2026-11-17.md sections 4 to 6 and 8.6a)."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from maipai_body import command_bus as cb
from maipai_body import reply_tags, scenes
from maipai_body.command_bus import Command, CommandBus, Gate
from maipai_body.scenes import SceneBook, SceneError
from maipai_body.speech.reply_stream import ReplyTagger
from tests.test_reply_streaming import Tts, deltas, run_bridge
from tests.test_reply_tags import Face, sync_side

DEV = "02:00:00:00:00:15"


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def make(gate=None, saved=None):
    clock = Clock()
    store: dict = {DEV: dict(saved or {})}

    def put(device, values):
        store.setdefault(device, {}).update(values)
        return store[device]

    book = SceneBook(lambda d: store.get(d, {}), put)
    calls: list[tuple] = []

    def rec(name):
        def run(device, args):
            calls.append((name, device, dict(args)))
            return True

        return run

    bus = CommandBus(
        {n: rec(n) for n in ("fx.set", "fx.clear", "light.look", "sound.play")},
        gate=(lambda _d: gate) if gate is not None else None,
        scenes=book,
        clock=clock,
    )
    return SimpleNamespace(bus=bus, calls=calls, clock=clock, book=book, store=store)


def send(env, cmd, args=None, source="model", budget=None, **kw):
    return env.bus.send(DEV, Command(cmd, args or {}, source, **kw), budget)


# ---- the catalog and the matrix are data and say the same thing ---------------------------------------------


def test_every_command_has_a_permission_for_every_source_and_a_cost_and_limits():
    assert set(cb.CATALOG) == set(cb.MATRIX)
    for cmd, spec in cb.CATALOG.items():
        assert set(cb.MATRIX[cmd]) == set(cb.SOURCES), cmd
        assert set(cb.MATRIX[cmd].values()) <= set("YLCON"), cmd
        assert isinstance(spec["cost"], int) and isinstance(spec["limits"], dict) and spec["surface"], cmd
    assert set(cb.PRIORITY) == set(cb.SOURCES)
    assert cb.PRIORITY["owner"] < cb.PRIORITY["home"] < cb.PRIORITY["routines"] < cb.PRIORITY["model"]


def test_the_model_can_never_move_the_body_take_a_photo_or_change_privacy():
    env = make()
    for cmd in ("head.move", "dance.start", "camera.photo", "privacy.set"):
        assert cb.MATRIX[cmd]["model"] == "N"
        result = send(env, cmd, source="model", cued=True)
        assert not result.ok and result.reason == "not allowed for this source"
    assert env.calls == []


def test_a_cued_command_needs_its_cue_and_a_privacy_change_is_the_owner_s_alone():
    env = make()
    assert send(env, "head.move", source="owner").reason == "not allowed for this source"
    assert send(env, "head.move", source="owner", cued=True).reason == "not handled by the bus"  # permitted: it keeps its own path
    assert send(env, "privacy.set", source="home").reason == "not allowed for this source"
    assert send(env, "privacy.set", source="owner").reason == "not handled by the bus"


def test_table_driven_a_source_not_in_the_row_never_gets_through():
    env = make()
    args = {
        "face.mood": {"mood": "happy"}, "fx.set": {"name": "rain"}, "fx.clear": {}, "light.look": {"color": "blue"},
        "sound.play": {"name": "success"}, "scene.set": {"name": "birthday"}, "scene.clear": {},
    }  # fmt: skip
    for cmd, row in cb.MATRIX.items():
        for source, level in row.items():
            if cmd not in args:
                continue
            result = send(env, cmd, args[cmd], source=source, budget=env.bus.new_reply())
            if level == "N":
                assert not result.ok and result.reason == "not allowed for this source", (cmd, source)
            else:
                assert result.reason != "not allowed for this source", (cmd, source)
            env.clock.advance(100)


def test_a_command_cannot_name_its_own_source_or_a_made_up_one():
    env = make()
    assert send(env, "fx.set", {"name": "rain"}, source="admin").reason == "unknown source"
    assert send(env, "nope").reason == "unknown command"


def test_nothing_outside_the_bus_and_its_executors_names_a_display_tool_for_the_model_path():
    """The reply path asks the bus and never calls the overlay tool by itself once a bus is set."""
    source = (Path(__file__).parent.parent / "maipai_body" / "bodies" / "stackchan" / "turn.py").read_text()
    assert "self.overlay.set" not in source and "set_led_color" not in source and "play_sound" not in source


# ---- clamps ------------------------------------------------------------------------------------------------


def test_arguments_are_clamped_and_never_guessed():
    env = make()
    assert send(env, "fx.set", {"name": "rain", "seconds": 9999}, source="owner").args["seconds"] == reply_tags.MAX_SECONDS
    assert send(env, "fx.set", {"name": "snow", "seconds": 0}, source="owner").args["seconds"] == 1
    assert send(env, "fx.set", {"name": "rain", "seconds": 500}).args["seconds"] == 20  # the model: at most 20
    env.clock.advance(100)
    assert send(env, "light.look", {"color": "blue", "seconds": 500}, source="model").args["seconds"] == 30
    for bad in ({"name": "lluvia!"}, {"name": "rain", "intensity": "extreme"}, {"name": "rain", "seconds": "5"}, {"seconds": 5}, {"name": ["rain"]}):
        assert send(env, "fx.set", bad, source="owner").reason == "bad argument", bad
    assert send(env, "light.look", {"color": "red"}, source="owner").reason == "bad argument"  # the palette has no red
    assert send(env, "sound.play", {"name": "low_battery"}, source="owner").reason == "bad argument"
    assert send(env, "face.mood", {"mood": "joy"}, source="owner").reason == "bad argument"


# ---- gates -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gate", "refused"),
    [
        (Gate(muted=True), {"fx.set": "muted", "light.look": "muted", "sound.play": "muted"}),
        (Gate(blocked=True), {"fx.set": "asleep or blocked", "light.look": "asleep or blocked", "sound.play": "asleep or blocked"}),
        (Gate(remote=True), {"fx.set": "a remote cue holds the unit", "light.look": "a remote cue holds the unit", "sound.play": "a remote cue holds the unit"}),
        (Gate(child=True), {"sound.play": "a child is present"}),
    ],
)
def test_gates_outrank_the_model_home_and_routines_decoration(gate, refused):
    for source in ("model", "home", "routines"):
        env = make(gate)
        args = {"fx.set": {"name": "rain"}, "light.look": {"color": "blue"}, "sound.play": {"name": "exclamation"}}
        for cmd, why in refused.items():
            if cmd == "sound.play" and gate.child and source != "model":
                continue  # the child limit is the model's
            assert send(env, cmd, args[cmd], source=source).reason == why, (cmd, source)
        assert send(env, "face.mood", {"mood": "happy"}, source=source).ok  # a face is never held back by these gates
        assert env.calls == [] or all(c[0] not in refused for c in env.calls)


def test_a_child_present_still_lets_the_model_play_the_quiet_sounds_and_show_effects():
    env = make(Gate(child=True))
    assert send(env, "sound.play", {"name": "success"}).ok
    assert send(env, "fx.set", {"name": "rain"}).ok


def test_the_owner_is_not_held_by_sleep_or_a_remote_cue_but_a_hard_mute_holds_every_sound():
    env = make(Gate(blocked=True, remote=True))
    assert send(env, "fx.set", {"name": "rain"}, source="owner").ok
    muted = make(Gate(muted=True))
    assert send(muted, "sound.play", {"name": "popup"}, source="owner").reason == "muted"
    assert send(muted, "fx.set", {"name": "rain"}, source="owner").ok


# ---- priority and leases ---------------------------------------------------------------------------------


def test_a_lower_priority_source_cannot_replace_a_higher_ones_effect_until_it_ends():
    env = make()
    assert send(env, "fx.set", {"name": "snow", "seconds": 30}, source="home").ok
    assert send(env, "fx.set", {"name": "rain"}, source="model").reason == "lower priority"
    assert send(env, "fx.set", {"name": "stars"}, source="routines").reason == "lower priority"
    assert send(env, "fx.clear", source="model").reason == "lower priority"
    assert send(env, "fx.set", {"name": "sun"}, source="owner").ok  # the owner outranks Home
    assert send(env, "fx.set", {"name": "stars"}, source="home").reason == "lower priority"
    env.clock.advance(31)
    assert send(env, "fx.set", {"name": "rain"}, source="model").ok  # the lease ended


def test_clearing_gives_the_surface_back_and_the_ring_light_has_its_own_lease():
    env = make()
    assert send(env, "light.look", {"color": "blue", "seconds": 60}, source="home").ok
    assert send(env, "light.look", {"color": "green"}, source="model").reason == "lower priority"
    assert send(env, "light.look", {"color": "off"}, source="home").ok
    assert send(env, "light.look", {"color": "green"}, source="model").ok


# ---- the model's rate limits -----------------------------------------------------------------------------


def test_one_effect_one_light_and_one_sound_per_reply_and_extra_ones_are_dropped_not_spoken():
    env = make()
    budget = env.bus.new_reply()
    assert send(env, "fx.set", {"name": "rain"}, budget=budget).ok
    assert send(env, "fx.set", {"name": "snow"}, budget=budget).reason == "one per reply"
    assert send(env, "light.look", {"color": "blue"}, budget=budget).ok
    assert send(env, "light.look", {"color": "cyan"}, budget=budget).reason == "one per reply"
    assert send(env, "sound.play", {"name": "popup"}, budget=budget).ok
    assert send(env, "sound.play", {"name": "success"}, budget=budget).reason == "one per reply"
    assert send(env, "fx.set", {"name": "snow"}, budget=env.bus.new_reply()).ok  # a new reply may replace the model's own earlier effect
    assert env.bus.dropped >= 3


def test_per_minute_gap_and_same_effect_limits():
    env = make()
    for _ in range(4):
        assert send(env, "light.look", {"color": "blue", "seconds": 1}, budget=env.bus.new_reply()).ok
        env.clock.advance(2)
    assert send(env, "light.look", {"color": "blue"}, budget=env.bus.new_reply()).reason == "too many in a minute"
    env.clock.advance(60)
    assert send(env, "sound.play", {"name": "popup"}, budget=env.bus.new_reply()).ok
    env.clock.advance(5)
    assert send(env, "sound.play", {"name": "popup"}, budget=env.bus.new_reply()).reason == "too soon after the last one"
    env.clock.advance(6)
    assert send(env, "sound.play", {"name": "popup"}, budget=env.bus.new_reply()).ok
    assert send(env, "fx.set", {"name": "rain", "seconds": 1}, budget=env.bus.new_reply()).ok
    env.clock.advance(3)
    assert send(env, "fx.set", {"name": "rain", "seconds": 1}, budget=env.bus.new_reply()).reason == "the same effect just ran"


def test_other_sources_have_no_model_rate_limits():
    env = make()
    budget = env.bus.new_reply()
    for name in ("rain", "snow", "stars"):
        assert send(env, "fx.set", {"name": name, "seconds": 1}, source="owner", budget=budget).ok
        env.clock.advance(2)


# ---- scenes ------------------------------------------------------------------------------------------------


def test_the_scene_table_is_one_definition_and_has_the_ten_presets():
    assert tuple(scenes.DEFAULT_SCENES) == reply_tags.SCENE_NAMES and len(reply_tags.SCENE_NAMES) == 10
    for name, row in scenes.DEFAULT_SCENES.items():
        assert scenes.clean_row(row) == row, name
        assert set(row) == set(scenes.FIELDS)  # no field for a body move, a photo or a privacy change
        assert row["sound"] in ("", *reply_tags.QUIET_SOUNDS), name  # shipped scenes use the quiet sounds
    assert {"rainy_day", "snowy_day", "sunny_day", "bedtime", "party", "birthday", "cozy", "spooky", "focus", "celebrate"} == set(scenes.DEFAULT_SCENES)


def test_a_scene_expands_into_catalog_commands_that_can_only_decorate():
    env = make()
    parts = env.book.expand(DEV, "rainy_day")
    assert [p[0] for p in parts] == ["face.mood", "fx.set", "light.look"]
    for name in reply_tags.SCENE_NAMES:
        assert {p[0] for p in env.book.expand(DEV, name)} <= cb.SCENE_PARTS
    assert env.book.expand(DEV, "nope") == []
    assert {p[0] for p in env.book.expand_off()} <= cb.SCENE_PARTS


def test_the_model_s_scene_goes_through_the_same_checks_as_each_part_alone():
    env = make()
    budget = env.bus.new_reply()
    result = send(env, "scene.set", {"name": "rainy_day"}, budget=budget)
    assert result.ok and result.mood == "neutral"
    assert [c[0] for c in env.calls] == ["fx.set", "light.look"]
    assert env.calls[0][2] == {"name": "rain", "intensity": "normal", "seconds": 20}
    # the scene used the reply's one effect and one light: a loose effect tag after it is dropped
    assert send(env, "fx.set", {"name": "snow"}, budget=budget).reason == "one per reply"


def test_a_scene_under_a_gate_is_partly_or_wholly_dropped_and_the_face_still_comes():
    env = make(Gate(blocked=True))
    result = send(env, "scene.set", {"name": "birthday"})
    assert result.ok and result.mood == "happy" and not result.shown and env.calls == []
    assert [r.reason for n, r in result.parts if n != "face.mood"] == ["asleep or blocked"] * 3
    child = make(Gate(child=True))
    send(child, "scene.set", {"name": "celebrate"})
    assert [c[0] for c in child.calls] == ["fx.set", "light.look", "sound.play"]  # success is a quiet sound


def test_a_higher_priority_effect_keeps_its_place_against_a_scene():
    env = make()
    assert send(env, "fx.set", {"name": "snow", "seconds": 60}, source="home").ok
    result = send(env, "scene.set", {"name": "rainy_day"})
    assert result.mood == "neutral" and [n for n, r in result.parts if r.reason == "lower priority"] == ["fx.set"]
    assert all(c[1:] != (DEV, {"name": "rain", "intensity": "normal", "seconds": 20}) for c in env.calls)


def test_routines_may_not_send_scenes_and_scene_off_ends_the_effect_and_the_light():
    env = make()
    assert send(env, "scene.set", {"name": "party"}, source="routines").reason == "not allowed for this source"
    send(env, "scene.set", {"name": "party"})
    env.calls.clear()
    send(env, "scene.clear")
    assert [c[0] for c in env.calls] == ["fx.clear", "light.look"] and env.calls[1][2]["color"] == "off"


def test_an_unknown_scene_name_is_refused_and_never_guessed():
    env = make()
    assert send(env, "scene.set", {"name": "stormy_weather"}).reason == "bad argument"


# ---- saving a scene -----------------------------------------------------------------------------------------


def test_the_owner_changes_a_scene_for_one_unit_and_resets_it():
    env = make()
    row = {"mood": "love", "fx": "hearts", "level": "heavy", "light": "magenta", "sound": "popup", "hold_s": 30}
    out = env.book.save(DEV, "rainy_day", row)
    assert out["ok"] and env.book.row(DEV, "rainy_day") == row
    changed = next(x for x in out["scenes"] if x["name"] == "rainy_day")
    assert changed["changed"] is True and out["options"]["light"][1:] == list(reply_tags.LIGHT_COLORS)
    assert env.book.expand(DEV, "rainy_day")[1][1]["intensity"] == "heavy"
    assert env.book.reset(DEV, "rainy_day")["ok"] and env.book.row(DEV, "rainy_day") == scenes.DEFAULT_SCENES["rainy_day"]


@pytest.mark.parametrize(
    "row",
    [
        {"mood": "happy", "fx": "rain", "level": "normal", "light": "blue", "sound": "", "hold_s": 20, "head": "nod"},
        {"mood": "happy", "fx": "rain", "level": "normal", "light": "blue", "sound": "", "hold_s": 20, "photo": True},
        {"mood": "joy"}, {"fx": "lava"}, {"light": "red"}, {"sound": "low_battery"}, {"hold_s": 1}, {"hold_s": 500}, {"hold_s": "9"}, "rain", None,
    ],
)
def test_a_scene_row_that_could_carry_a_body_move_a_photo_or_anything_else_is_refused(row):
    env = make()
    with pytest.raises(SceneError):
        env.book.save(DEV, "party", row)
    assert env.book.row(DEV, "party") == scenes.DEFAULT_SCENES["party"]


def test_a_damaged_saved_row_falls_back_to_the_shipped_scene_and_an_unknown_name_is_refused():
    env = make(saved={"scenes": {"party": {"fx": "lava"}}})
    assert env.book.row(DEV, "party") == scenes.DEFAULT_SCENES["party"]
    with pytest.raises(SceneError):
        env.book.save(DEV, "weather", {})
    with pytest.raises(SceneError):
        env.book.reset(DEV, "weather")
    assert "Elige" in scenes.say("es", "unknown", names="x")


# ---- the turn: tags to cues to the bus -----------------------------------------------------------------------


def test_scene_sound_and_light_tags_parse_and_unknown_ones_are_dropped():
    for text, kind, name in [
        ("scene rainy_day", "scene", "rainy_day"), ("scene:birthday", "scene", "birthday"), ("SCENE Rainy Day", "scene", "rainy_day"),
        ("scene off", "scene_off", ""), ("escena fiesta", "scene", "party"), ("sound:success", "sound", "success"),
        ("light:blue", "light", "blue"), ("light blue 30", "light", "blue"), ("light:off", "light", "off"),
        ("scene", "unknown", ""), ("scene lava", "unknown", ""), ("sound", "unknown", ""), ("sound:find", "unknown", ""),
        ("sound:low_battery", "unknown", ""), ("success", "unknown", ""), ("blue", "unknown", ""), ("light:red", "unknown", ""),
        ("light:blue 0", "unknown", ""), ("light:blue x", "unknown", ""), ("light:blue 5 6", "unknown", ""), ("/scene", "unknown", ""),
    ]:  # fmt: skip
        tag = reply_tags.parse_tag(text)
        assert (tag.kind, tag.name) == (kind, name), text
    assert reply_tags.parse_tag("light:blue 30").seconds == 30


def test_the_tagger_turns_the_new_tags_into_cues_and_never_speaks_them():
    tagger = ReplyTagger()
    items = list(tagger.feed("[happy] [scene rainy_day] It is wet. [sound:popup] [light:blue 10] [scene lava] Bye. [scene off]"))
    items += tagger.flush()
    assert [i.text for i in items if i.text] == ["It is wet.", "Bye."]
    got = [(c.kind, c.name) for i in items for c in i.cues]
    assert got == [("mood", "happy"), ("scene", "rainy_day"), ("sound", "popup"), ("light", "blue"), ("scene_off", "")]
    assert tagger.tags_dropped == 1
    off = ReplyTagger(overlays=False)
    out = list(off.feed("[scene party] Hi. ")) + off.flush()
    assert [(c.kind) for i in out for c in i.cues] == [] and [i.text for i in out if i.text] == ["Hi."]


def bridge_with_bus(env, face, gate=None):
    def setup(bridge):
        sync_side(bridge)
        bridge.expression_sink = face
        bridge.command_bus = env.bus
        if gate is not None:
            env.bus.gate = lambda _d: gate

    return setup


def test_a_scene_tag_in_a_reply_sets_the_face_effect_and_light_through_the_bus_and_speaks_only_the_words(monkeypatch):
    env, face = make(), Face()
    run_bridge(monkeypatch, lambda b: deltas("[scene rainy_day] It is a wet one. Bring a coat."), setup=bridge_with_bus(env, face))
    assert Tts.spoken == ["It is a wet one.", "Bring a coat."]
    assert [c[0] for c in env.calls] == ["fx.set", "light.look"]
    assert ("reply_mood", "neutral") in face.calls


def test_an_explicit_mood_tag_wins_for_the_face_before_or_after_the_scene(monkeypatch):
    for reply in ("[sad] [scene party] Oh well.", "[scene party] [sad] Oh well."):
        env, face = make(), Face()
        run_bridge(monkeypatch, lambda b, r=reply: deltas(r), setup=bridge_with_bus(env, face))
        moods = [m for s, m in face.calls if s == "reply_mood"]
        assert moods and moods[-1] == "sadness", (reply, moods)
        assert [c[0] for c in env.calls] == ["fx.set", "light.look", "sound.play"]  # the rest of the scene still shows


def test_privacy_sleep_a_remote_cue_and_the_switch_still_win_over_a_scene_but_not_over_the_speech(monkeypatch):
    for gate in (Gate(muted=True), Gate(blocked=True), Gate(remote=True)):
        env, face = make(), Face()
        run_bridge(monkeypatch, lambda b: deltas("[scene birthday] Happy birthday!"), setup=bridge_with_bus(env, face, gate))
        assert Tts.spoken == ["Happy birthday!"] and env.calls == [], gate
    env, face = make(), Face()

    def off(bridge):
        bridge_with_bus(env, face)(bridge)
        bridge.prefs_for = lambda _d: {"overlays_enabled": False}

    run_bridge(monkeypatch, lambda b: deltas("[scene birthday] Happy birthday!"), setup=off)
    assert Tts.spoken == ["Happy birthday!"] and env.calls == []


def test_a_reply_asking_for_two_effects_gets_only_the_first(monkeypatch):
    env, face = make(), Face()
    run_bridge(monkeypatch, lambda b: deltas("[rain]Wet[/rain] and [snow]cold[/snow] today."), setup=bridge_with_bus(env, face))
    assert [c[2]["name"] for c in env.calls if c[0] == "fx.set"] == ["rain"]
    assert Tts.spoken == ["Wet and cold today."]


def test_a_reply_that_is_not_streamed_runs_its_scene_too(monkeypatch):
    env, face = make(), Face()
    run_bridge(monkeypatch, lambda b: iter([SimpleNamespace(reply_text="[scene sunny_day] Lovely out.")]), setup=bridge_with_bus(env, face))
    assert Tts.spoken == ["Lovely out."] and [c[0] for c in env.calls] == ["fx.set", "light.look"]
    assert ("reply_mood", "happiness") in face.calls or ("reply_mood", "happy") in face.calls


def test_the_persona_teaches_mood_effect_and_scene_tags_briefly_and_only_names_that_exist():
    text = reply_tags.persona_with_tags("You are kind.")
    assert all(f"[{m}]" in text for m in reply_tags.MOODS)
    assert all(f"[scene {n}]" in text for n in reply_tags.SCENE_NAMES) and "[scene off]" in text and "[rain]" in text
    suffix = reply_tags.PERSONA_SUFFIX
    assert len(suffix.split()) < 110
    for tag in re.findall(r"\[([^\]]+)\]", suffix):
        parsed = reply_tags.parse_tag(tag)
        assert parsed.kind != "unknown", tag  # the prompt can never teach a tag the host drops
    assert reply_tags.persona_with_tags(text) == text and chr(0x2014) not in suffix
