"""The name picked on the robot's first run reaches the host (firmware patches SF09 and UX11, host/maipai_body/first_run_name.py): index 6 is StackChan, the default; the six older indexes keep their
names; the name is saved once for a unit that has none and never replaces a name typed on the settings page; the settings page and the unit list show it; a bad index saves nothing."""

from __future__ import annotations

import pytest

from maipai_body.bodies.stackchan.companion import DIAGNOSTIC_KINDS, StackChanCompanion
from maipai_body.first_run_name import DEFAULT_NAME, NAMES, FirstRunNames, disambiguate, name_for_index
from maipai_body.units import LayeredStore, known_units
from maipai_body.unit_settings import UnitSettingsStore

UNIT = "02:00:00:00:00:71"


@pytest.fixture()
def store(tmp_path):
    return LayeredStore(UnitSettingsStore(tmp_path / "units.json"))


def test_the_seven_names_keep_the_indexes_the_robot_saves():
    assert NAMES[:6] == ("Astro", "Clover", "Ember", "Nova", "Pippa", "Rover")
    assert NAMES[6] == "StackChan" == DEFAULT_NAME
    assert [name_for_index(i) for i in range(7)] == list(NAMES)


@pytest.mark.parametrize("bad", [-1, 7, 99, None, "6", 6.0, True, [6]])
def test_an_index_that_is_not_one_of_the_seven_means_no_name(bad):
    assert name_for_index(bad) is None


def test_the_picked_name_is_saved_once_and_shown_on_the_settings_page_list(store):
    names = FirstRunNames(store)
    assert names.on_event(UNIT, {"lang": 0, "name": 6, "mode": 1}) == "StackChan"
    assert store.get(UNIT)["name"] == "StackChan"
    rows = known_units({UNIT: object()}, store)
    assert rows[0]["name"] == "StackChan"


def test_every_index_is_saved_exactly_as_picked(store, tmp_path):
    for index, expected in enumerate(NAMES):
        fresh = LayeredStore(UnitSettingsStore(tmp_path / f"u{index}.json"))
        assert FirstRunNames(fresh).on_event(UNIT, {"name": index}) == expected
        assert fresh.get(UNIT)["name"] == expected


def test_a_name_typed_on_the_page_is_never_replaced(store):
    store.update(UNIT, {"name": "Kitchen robot"})
    assert FirstRunNames(store).on_event(UNIT, {"name": 3}) is None
    assert store.get(UNIT)["name"] == "Kitchen robot"


def test_a_bad_event_saves_nothing(store):
    names = FirstRunNames(store)
    assert names.on_event(UNIT, {"name": 12}) is None
    assert names.on_event(UNIT, {}) is None
    assert names.on_event(None, {"name": 1}) is None
    assert "name" not in store.get(UNIT)


def test_a_unit_with_no_name_shows_stackchan_and_two_of_them_are_told_apart(store):
    other = "02:00:00:00:00:99"
    rows = known_units({UNIT: object(), other: object()}, store)
    assert {r["name"] for r in rows} == {f"StackChan {other[-5:]}", f"StackChan {UNIT[-5:]}"}
    assert known_units({UNIT: object()}, store)[0]["name"] == "StackChan"
    assert disambiguate([{"name": "Nova", "device_id": UNIT}])[0]["name"] == "Nova"


def test_the_first_run_event_keeps_its_fields_when_the_host_reads_the_unit_events():
    assert "first_run_done" in DIAGNOSTIC_KINDS
    comp = StackChanCompanion(lambda name, args: [{"kind": "first_run_done", "at_ms": 5, "lang": 0, "name": 6, "mode": 1}])
    event = comp.poll_events()[0]
    assert event.kind == "first_run_done" and event.extra == {"lang": 0, "name": 6, "mode": 1}
