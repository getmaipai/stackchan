"""The installed set: slots, memory meter, Automatic defaults, installing to a unit that is on, away, failing or powered off mid-install."""

import pytest

from maipai_body import installed_set as iset
from maipai_body.installed_set import InstalledSets, InstalledStore
from maipai_body.packs import PackError, PackLibrary, make_pack, zip_payload


class FakeUnit:
    """A transport over a dict of what each unit holds; faults are switches."""

    def __init__(self, library):
        self.on, self.multi, self.fail, self.held_ = {"u1": True, "u2": True}, False, {}, {}
        self.library, self.installs = library, []

    def connected(self, unit):
        return self.on.get(unit, False)

    def multi_slot(self, unit):
        return self.multi

    def held(self, unit, kind):
        return list(self.held_.get((unit, kind), []))

    def install(self, unit, kind, pack_id):
        if self.fail.get(unit):
            raise PackError(self.fail[unit])
        self.installs.append((unit, pack_id))
        self.held_.setdefault((unit, kind), [])
        sha = self.library.get(pack_id).sha256
        self.held_[(unit, kind)] = self.held_[(unit, kind)] + [sha] if self.multi else [sha]

    def remove(self, unit, kind, sha):
        self.held_[(unit, kind)] = [] if sha is None else [h for h in self.held_.get((unit, kind), []) if h != sha]


def _library(tmp_path):
    lib = PackLibrary(tmp_path / "packs", filler_root=tmp_path / "fillers")
    for kind, names in (("look", ["default", "soft"]), ("game", ["memory", "quiz", "tap", "dots", "chase"]), ("language", ["french"]), ("sound", ["chimes"])):
        for n in names:
            lang = "fr" if kind == "language" else ""
            lib.add(make_pack(kind, n, zip_payload({"a.txt": n.encode() * 10}), lang=lang))
    return lib


def _sets(tmp_path, language="fr"):
    lib = _library(tmp_path)
    unit = FakeUnit(lib)
    return InstalledSets(lib, InstalledStore(tmp_path / "sets.json"), unit, language=lambda u: language), unit, lib


def test_first_run_defaults_use_the_language_the_default_face_and_a_starter_set_of_games(tmp_path):
    sets, _, _ = _sets(tmp_path)
    chosen = sets.defaults("u1")
    assert chosen["language"][0].startswith("language/") and chosen["look"] == ["look/default"] and len(chosen["game"]) == iset.STARTER_GAMES


def test_automatic_is_the_default_mode_and_the_view_shows_slots_and_the_memory_meter(tmp_path):
    sets, _, _ = _sets(tmp_path)
    view = sets.view("u1")
    assert view["mode"] == "automatic" and view["kinds"]["game"]["slots"] == iset.SLOTS["game"] and view["kinds"]["game"]["used"] == iset.STARTER_GAMES
    assert 0 < view["meter"]["used_bytes"] < view["meter"]["budget_bytes"] and not view["warnings"]


def test_a_choice_that_does_not_fit_is_refused_in_plain_words(tmp_path):
    sets, _, _ = _sets(tmp_path)
    too_many = {"game": [f"game/{n}" for n in ("memory", "quiz", "tap", "dots", "chase")]}
    with pytest.raises(ValueError, match="room for 4"):
        sets.choose("u1", "custom", too_many)
    with pytest.raises(ValueError, match="no longer in the library"):
        sets.choose("u1", "custom", {"game": ["game/gone"]})
    with pytest.raises(ValueError):
        sets.choose("u1", "sideways")
    assert sets.choose("u1", "custom", {"game": ["game/memory"]})["mode"] == "custom"


def test_the_memory_budget_warns_when_the_choices_are_too_big(tmp_path, monkeypatch):
    sets, _, _ = _sets(tmp_path)
    monkeypatch.setattr(iset, "UNIT_PACK_BUDGET", 100)
    with pytest.raises(ValueError, match="at most 0 KB in all|in all"):
        sets.choose("u1", "custom", {"look": ["look/soft"]})


def test_reconcile_installs_the_set_removes_the_rest_and_keeps_what_is_there(tmp_path):
    sets, unit, lib = _sets(tmp_path)
    sets.choose("u1", "custom", {"look": ["look/soft"], "sound": ["sound/chimes"]})
    unit.held_[("u1", "look")] = [lib.get("look/default").sha256]  # an older face is on the robot
    states = sets.reconcile("u1")
    assert states == {"look/soft": "installed", "sound/chimes": "installed"}
    assert unit.held_[("u1", "look")] == [lib.get("look/soft").sha256]
    unit.installs.clear()
    sets.reconcile("u1")
    assert unit.installs == []  # nothing is sent twice


def test_a_unit_that_holds_one_per_kind_gets_the_first_choice_and_a_plain_note_for_the_rest(tmp_path):
    sets, unit, _ = _sets(tmp_path)
    sets.choose("u1", "custom", {"game": ["game/memory", "game/quiz"]})
    states = sets.reconcile("u1")
    assert states == {"game/memory": "installed", "game/quiz": "waiting"}
    assert "one of these at a time" in sets.view("u1")["kinds"]["game"]["chosen"][1]["message"]
    unit.multi = True
    assert sets.reconcile("u1") == {"game/memory": "installed", "game/quiz": "installed"}


def test_a_unit_that_is_away_gets_its_set_when_it_returns(tmp_path):
    sets, unit, _ = _sets(tmp_path)
    sets.choose("u1", "custom", {"look": ["look/soft"]})
    unit.on["u1"] = False
    assert sets.reconcile("u1") == {"look/soft": "waiting"} and sets.pending() == ["u1"]
    assert "away" in sets.view("u1")["summary"]
    unit.on["u1"] = True
    assert sets.reconcile("u1") == {"look/soft": "installed"} and sets.pending() == []


def test_a_bad_signature_or_power_loss_is_reported_and_retried_without_blocking_the_rest(tmp_path):
    sets, unit, _ = _sets(tmp_path)
    sets.choose("u1", "custom", {"look": ["look/soft"], "sound": ["sound/chimes"]})
    unit.fail["u1"] = "The pack's signature is not valid."
    states = sets.reconcile("u1")
    assert states == {"look/soft": "failed", "sound/chimes": "failed"} and sets.pending() == ["u1"]
    assert sets.store.get("u1")["items"]["look/soft"]["tries"] == 1
    sets.reconcile("u1")
    assert sets.store.get("u1")["items"]["look/soft"]["tries"] == 2
    unit.fail["u1"] = None  # power is back / the key is right
    assert set(sets.reconcile("u1").values()) == {"installed"} and sets.pending() == []


def test_two_units_have_separate_sets_and_one_failing_does_not_touch_the_other(tmp_path):
    sets, unit, _ = _sets(tmp_path)
    sets.choose("u1", "custom", {"look": ["look/soft"]})
    sets.choose("u2", "custom", {"look": ["look/default"]})
    unit.fail["u1"] = "boom"
    sets.reconcile("u1")
    assert sets.reconcile("u2") == {"look/default": "installed"}
    assert sets.view("u1")["kinds"]["look"]["chosen"][0]["state"] == "failed" and sets.view("u2")["kinds"]["look"]["chosen"][0]["state"] == "installed"


def test_the_store_is_private_and_survives_a_restart(tmp_path):
    sets, _, lib = _sets(tmp_path)
    sets.choose("u1", "custom", {"look": ["look/soft"]})
    assert oct((tmp_path / "sets.json").stat().st_mode & 0o777) == "0o600"
    again = InstalledSets(lib, InstalledStore(tmp_path / "sets.json"), FakeUnit(lib))
    assert again.view("u1")["mode"] == "custom"


def test_the_dashboard_routes_choose_and_refuse(tmp_path):
    from maipai_body.settings_sim import build

    backend, _ = build(tmp_path)
    sets, _, _ = _sets(tmp_path)
    backend.installed = sets
    backend.installed_units = lambda: [{"id": "u1", "name": "", "connected": True}]
    assert backend.route_get("/on-my-robot", "en", True)[1].startswith("text/html")
    assert b"u1" in backend.route_get("/api/stackchan/installed", "en", True)[2]
    assert backend.route_post("/api/stackchan/installed/u1/choose", {"mode": "custom", "chosen": {"game": [f"game/{n}" for n in ("memory", "quiz", "tap", "dots", "chase")]}}, True)[0] == 400
    assert backend.route_post("/api/stackchan/installed/u1/choose", {"mode": "automatic"}, True)[0] == 200
    assert backend.route_post("/api/stackchan/installed/u1/choose", {"mode": "automatic"}, False)[0] == 403
