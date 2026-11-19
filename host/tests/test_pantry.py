"""The content pantry (docs/design/content-pantry.md): record, shelf round trip, filter, dedupe, generator, library and the sync rule, with a fake model."""

from __future__ import annotations

import json
import time

import pytest

from maipai_packages.pantry import Pantry, shelf
from maipai_packages.pantry.dedupe import dedupe
from maipai_packages.pantry.filter import ModelDown, filter_records
from maipai_packages.pantry.generator import generate, parse
from maipai_packages.pantry.library import Library
from maipai_packages.pantry.record import Record, RecordError, check, normalize
from maipai_packages.pantry.sync import UnitState, build_shelf, plan, run_unit

JOKE = Record("joke", "en", "kid", "Why did the cat sit on the computer? | To keep an eye on the mouse.")
RIDDLE = Record("riddle", "en", "kid", "What has hands but cannot clap?", "a clock")
TRIVIA = Record("trivia", "en", "kid", "What is the largest planet in our solar system?", "Jupiter", "Mars|Venus")


def good_model(prompt: str) -> str:
    """A fake model that says yes to kid checks, knows the trivia, and has no second riddle answer."""
    if "suitable for a six year old" in prompt:
        return "Yes"
    if "largest planet" in prompt:
        return "Jupiter"
    if "different, equally good answer" in prompt:
        return "none"
    return json.dumps([{"text": "Why did the cat sit on the computer? | To keep an eye on the mouse."}, {"text": "What do you call a sleeping bull? | A bulldozer."}])


def test_a_record_has_a_stable_id_and_the_caps_are_kept():
    assert JOKE.id == Record("joke", "en", "kid", "why did the cat sit on the computer | to keep an eye on the mouse").id, "spelling and accents do not change the id"
    assert normalize("Él dijo: ¡Hola!") == "el dijo hola"
    with pytest.raises(RecordError):
        check(Record("joke", "en", "kid", "no punchline here"))
    with pytest.raises(RecordError):
        check(Record("riddle", "en", "kid", "What?", ""))
    with pytest.raises(RecordError):
        check(Record("joke", "en", "kid", "a" * 200 + "|b"))
    with pytest.raises(RecordError):
        check(Record("trivia", "en", "kid", "Q?", "A", "only one"))


def test_a_shelf_round_trips_and_stays_inside_one_item():
    records = [JOKE, Record("joke", "en", "kid", "What do you call a sleeping bull? | A bulldozer.")]
    body = shelf.pack(records)
    assert shelf.unpack(body) == [check(r) for r in records]
    trivia = shelf.unpack(shelf.pack([TRIVIA]))[0]
    assert trivia.answer == "Jupiter" and trivia.extra == "Mars|Venus"
    with pytest.raises(RecordError):
        shelf.pack([JOKE, RIDDLE])  # one kind per shelf
    with pytest.raises(RecordError):
        shelf.pack([Record("joke", "en", "adult", "a | b")], rating_ceiling="kid")
    many = [Record("story", "en", "kid", "p1|" + "x" * i) for i in range(60)]
    with pytest.raises(RecordError, match="one item holds"):
        shelf.pack(many * 20)
    with pytest.raises(RecordError):
        shelf.unpack(body[:10])
    tampered = bytearray(body)
    tampered[-3] ^= 0xFF
    with pytest.raises(RecordError):
        shelf.unpack(bytes(tampered))


def test_the_filter_drops_what_is_not_a_clear_pass_and_never_edits():
    scary = Record("joke", "en", "kid", "Why did the zombie die? | Because it was dead already.")
    wrong_fact = Record("trivia", "en", "kid", "What is the largest planet in our solar system?", "Mars", "Venus|Earth")
    fresh = Record("trivia", "en", "kid", "Who is the current president?", "someone", "a|b")
    two_answers = Record("riddle", "en", "kid", "What has hands but cannot clap?", "a clock")
    flaky = lambda prompt: "a watch" if "different, equally good answer" in prompt else good_model(prompt)  # noqa: E731
    kept, report = filter_records([JOKE, scary, wrong_fact, fresh, TRIVIA], good_model)
    assert [r.kind for r in kept] == ["joke", "trivia"]
    assert report.dropped == {"not for kids (word list)": 1, "fact not confirmed": 1, "time-bound fact": 1}
    kept, report = filter_records([two_answers], flaky)
    assert kept == [] and report.dropped == {"riddle has two answers": 1}
    kept, report = filter_records([JOKE], lambda p: "no")
    assert kept == [] and report.dropped == {"not for kids (model)": 1}
    adult = Record("joke", "en", "adult", "a | b")
    assert filter_records([adult], good_model)[0] == [] and filter_records([adult], good_model, adult_allowed=True)[0] == [check(adult)]


def test_a_model_that_goes_away_keeps_nothing_unchecked():
    def down(prompt: str) -> str:
        raise ConnectionError("no model")

    with pytest.raises(ModelDown):
        filter_records([JOKE], down)


def test_dedupe_drops_exact_and_near_copies_and_the_refused():
    near = Record("joke", "en", "kid", "Why did the cat sit on the computer? | To keep an eye on the mouse!")
    other = Record("joke", "en", "kid", "What do you call a sleeping bull? | A bulldozer.")
    twin_riddle = Record("riddle", "en", "kid", "What has two hands but can never clap?", "A clock")
    kept, report = dedupe([near, other, twin_riddle, RIDDLE], [JOKE], {other.id})
    # near joke of a known one: exact after normalizing (the "!" is dropped); the refused one; the second riddle is the same question as the first
    assert kept == [twin_riddle]
    assert report.dropped == {"exact duplicate": 1, "refused before": 1, "near duplicate": 1}
    kept, _ = dedupe([Record("joke", "en", "kid", "Totally different words about pandas | They eat bamboo all day long")], [JOKE])
    assert len(kept) == 1


def test_the_generator_filters_dedupes_stores_and_counts_its_calls(tmp_path):
    library = Library(tmp_path)
    summary = generate(library, good_model, "joke", "en", batches=1)
    assert summary["added"] == 2 and not summary["stopped"] and summary["model_calls"] >= 3
    again = generate(library, good_model, "joke", "en", batches=1)
    assert again["added"] == 0 and again["dropped"]["exact duplicate"] == 2, "the same batch twice adds nothing"
    assert library.calls_today() == summary["model_calls"] + again["model_calls"]
    assert len(library.records("joke", "en")) == 2
    assert library.last_report()["added"] == 0


def test_the_daily_cap_and_an_unreadable_reply_are_handled(tmp_path):
    library = Library(tmp_path)
    capped = generate(library, good_model, "joke", "en", daily_cap=5)
    assert capped["stopped"] == "the daily cap of model calls is reached" and capped["added"] == 0
    junk = generate(library, lambda p: "I cannot do that", "joke", "en")
    assert junk["added"] == 0 and junk["dropped"]["unreadable reply"] == 1
    assert parse('Here you go: [{"text": "a|b"}, 5, {"nope": 1}] thanks', "joke", "en", "kid") == [Record("joke", "en", "kid", "a|b")]


def test_the_library_deletes_refuses_and_keeps_the_heard_history(tmp_path):
    library = Library(tmp_path)
    library.add([JOKE, RIDDLE])
    assert library.delete(JOKE.id_hex) and not library.delete(JOKE.id_hex)
    assert [r.kind for r in library.records()] == ["riddle"]
    assert library.never_again(RIDDLE.id_hex) and library.records() == []
    kept, report = dedupe([RIDDLE], [], library.refused_ids())
    assert kept == [] and report.dropped == {"refused before": 1}
    library.add([JOKE])
    assert library.note_heard("kitchen", [{"id": JOKE.id_hex[:8], "counter": 5}, {"id": "deadbeef", "counter": 1}]) == 1
    assert library.heard("kitchen")[JOKE.id_hex]["counter"] == 5 and library.unheard("kitchen", "joke", "en") == []
    assert library.unheard("den", "joke", "en") == [JOKE], "heard is per unit"
    library.add([Record("joke", "en", "kid", "bad|line")])
    (tmp_path / "en-joke.jsonl").write_text((tmp_path / "en-joke.jsonl").read_text() + "{broken\n")
    assert len(library.records("joke", "en")) == 2, "a damaged line is skipped, never fatal"


class FakeUnit:
    def __init__(self, shelves, heard=None):
        self.shelves, self.heard_list, self.installed, self.denied = shelves, heard or [], [], []

    def status(self, unit):
        return self.shelves

    def heard_since(self, unit, seq):
        return self.heard_list[seq:], len(self.heard_list)

    def install_shelf(self, unit, kind, language, body):
        self.installed.append((kind, language, len(body)))
        return True

    def deny(self, unit, ids):
        self.denied = ids
        return True


def test_the_refill_rule_runs_nightly_or_on_low_stock_and_never_while_busy():
    night = time.mktime((2026, 11, 19, 3, 0, 0, 0, 0, -1))
    noon = time.mktime((2026, 11, 19, 12, 0, 0, 0, 0, -1))
    full = [{"kind": "joke", "language": "en", "count": 200, "unheard": 150}]
    low = [{"kind": "joke", "language": "en", "count": 200, "unheard": 30}]
    state = UnitState()
    assert plan(full, state, noon) == [] and plan(full, state, night) == [("joke", "en", "nightly")]
    assert plan(full, state, night, nightly_done={("joke", "en")}) == []
    assert plan(low, state, noon) == [("joke", "en", "low stock")]
    assert plan(low, UnitState(idle=False), noon) == [] and plan(low, UnitState(in_game=True), noon) == []
    assert plan(low, UnitState(on_power_or_over_half=False), noon) == []
    four = [{"kind": k, "language": "en", "count": 0, "unheard": 0} for k in ("joke", "riddle", "trivia", "story")]
    assert len(plan(four, state, noon)) == 3, "at most three swaps a window"


def test_a_shelf_is_built_unheard_first_and_a_sync_pass_takes_heard_sends_denials_and_refills(tmp_path):
    library = Library(tmp_path)
    jokes = [Record("joke", "en", "kid", f"Joke number {i} about topic {i * 7} | punchline {i * 3}") for i in range(30)]
    library.add(jokes)
    library.note_heard("kitchen", [{"id": jokes[0].id_hex[:8], "counter": 1}])
    body = build_shelf(library, "kitchen", "joke", "en", shelf.ITEM_CAP_BYTES)
    unpacked = shelf.unpack(body)
    assert unpacked[0] != jokes[0] and unpacked[-1] == check(jokes[0]), "unheard first, the heard one last"
    assert build_shelf(library, "kitchen", "joke", "en", 8000) is None, "below the floor the owner is asked to remove a pack"
    unit = FakeUnit([{"kind": "joke", "language": "en", "count": 30, "unheard": 3}], heard=[{"id": jokes[1].id_hex[:8], "counter": 2, "deny": True}])
    done = run_unit(library, unit, "kitchen", UnitState(), now=time.mktime((2026, 11, 19, 12, 0, 0, 0, 0, -1)))
    assert done["heard"] == 1 and done["swapped"] and unit.installed[0][:2] == ("joke", "en")
    assert jokes[1].id_hex in library.refused() and unit.denied == sorted(library.refused()), "a denied record is refused everywhere"
    # a second pass reads only what is new
    assert run_unit(library, unit, "kitchen", UnitState(), now=time.time())["heard"] == 0
    # an empty library has nothing to build
    empty = run_unit(Library(tmp_path / "other"), FakeUnit([{"kind": "joke", "language": "en", "count": 0, "unheard": 0}]), "kitchen", UnitState())
    assert "no records" in empty["skipped"]


def test_the_facade_lists_deletes_and_refuses_for_the_dashboard(tmp_path):
    pantry = Pantry(tmp_path, good_model, seed=False)
    assert pantry.refill("joke", "en")["added"] == 2
    view = pantry.view(kind="joke", language="en")
    assert view["total"] == 2 and view["counts"] == {"en:joke": 2} and view["report"]["added"] == 2
    row = view["rows"][0]
    assert pantry.view(query="bulldozer")["total"] == 1
    assert pantry.delete(row["id"]) and pantry.view()["total"] == 1
    other = pantry.view()["rows"][0]["id"]
    assert pantry.never_again(other) and pantry.view()["total"] == 0 and pantry.view()["refused"] == 1
    assert Pantry(tmp_path / "x").refill("joke", "en")["stopped"].startswith("No model is set")


def test_the_dashboard_routes_list_delete_refuse_and_refill_and_stay_local(tmp_path):
    from maipai_body.settings_page import PANTRY, SettingsBackend

    backend = SettingsBackend.__new__(SettingsBackend)
    backend.pantry = Pantry(tmp_path, good_model, seed=False)
    backend.language = "en"
    status, payload = backend.route_post(PANTRY + "/refill", {"kind": "joke", "language": "en"}, True)
    assert status == 200 and payload["started"] is True
    import time

    for _ in range(100):  # the refill runs in a worker; the page polls refill-state
        _, polled = backend.route_post(PANTRY + "/refill-state", {"kind": "joke", "language": "en"}, True)
        if polled["state"] != "running":
            break
        time.sleep(0.05)
    assert polled["result"]["added"] == 2
    status, raw_type, raw = backend.route_get(PANTRY, "en", True)
    view = json.loads(raw)
    assert status == 200 and view["total"] == 2
    status, listed = backend.route_post(PANTRY + "/list", {"q": "bulldozer"}, True)
    assert status == 200 and listed["total"] == 1
    rid = listed["rows"][0]["id"]
    assert backend.route_post(PANTRY + "/delete", {"id": rid}, True)[1]["removed"] is True
    assert backend.route_post(PANTRY + "/never-again", {"id": view["rows"][0]["id"]}, True)[0] == 200
    assert backend.route_post(PANTRY + "/delete", {}, True)[0] == 400
    assert backend.route_post(PANTRY + "/refill", {"kind": "joke"}, True)[0] == 400
    assert backend.route_post(PANTRY + "/delete", {"id": rid}, False)[0] == 403, "only the host computer edits the library"
    assert backend.route_get(PANTRY, "en", False)[0] == 403
    off = SettingsBackend.__new__(SettingsBackend)
    off.pantry = None
    assert json.loads(off.route_get(PANTRY, "en", True)[2]) == {"enabled": False}


def test_the_shelf_header_matches_the_firmware_reader():
    body = shelf.pack([JOKE])
    assert body[:4] == b"MPSH" and body[4] == 1 and body[5:7] == b"en" and len(shelf.HEADER.pack(b"MPSH", 1, b"en", 0, 1, 16)) == 16
    assert int.from_bytes(body[8:10], "little") == 1 and int.from_bytes(body[10:14], "little") == 16
    with pytest.raises(RecordError, match="MPSH"):
        shelf.unpack(b"XXXX" + body[4:])


def test_the_tool_link_reads_status_and_the_heard_list_in_batches_and_sends_denials():
    from maipai_packages.pantry.unit_link import ToolUnitLink

    calls = []
    batches = [{"ok": True, "counter": 5, "more": True, "entries": [{"id": "aabbccdd", "counter": 3, "heard": 1, "denied": 0}]}, {"ok": True, "counter": 9, "more": False, "entries": [{"id": "11223344", "counter": 9, "heard": 1, "denied": 1}]}]

    def call(unit, tool, args):
        calls.append((tool, args))
        if tool == "self.pantry.status":
            return {"ok": True, "shelves": [{"slot": 0, "language": "en", "bytes": 9000, "counts": {"joke": 100, "riddle": 20}, "unheard": {"joke": 90, "riddle": 2}}]}
        if tool == "self.pantry.heard":
            return batches.pop(0)
        return {"ok": True, "denied": 2}

    link = ToolUnitLink(call)
    assert link.status("u") == [
        {"kind": "joke", "language": "en", "count": 100, "unheard": 90, "bytes": 9000},
        {"kind": "riddle", "language": "en", "count": 20, "unheard": 2, "bytes": 9000},
    ]
    entries, counter = link.heard_since("u", 0)
    assert [e["id"] for e in entries] == ["aabbccdd", "11223344"] and counter == 9
    assert [a for t, a in calls if t == "self.pantry.heard"] == [{"since": 0}, {"since": 5}]
    assert link.deny("u", [JOKE.id_hex, RIDDLE.id_hex]) is True
    assert calls[-1][1]["ids"] == ",".join(sorted([JOKE.id_hex[:8], RIDDLE.id_hex[:8]]))
    assert link.install_shelf("u", "joke", "en", b"x") is False, "no asset transport yet: the old shelf stays"
    assert ToolUnitLink(call, lambda u, k, l, b: True).install_shelf("u", "joke", "en", b"x") is True


def test_refill_window_takes_fractional_hours_and_crosses_midnight():
    import time

    from maipai_packages.pantry.sync import in_window

    def at(h, m):
        return time.mktime((2026, 11, 18, h, m, 0, 0, 0, -1))

    assert in_window(at(21, 45), 21.5, 7.0) and in_window(at(3, 0), 21.5, 7.0) and not in_window(at(21, 15), 21.5, 7.0)
    assert in_window(at(2, 30), 2, 5) and not in_window(at(5, 0), 2, 5)


def test_first_run_loads_the_built_in_set_once_and_deleted_records_stay_deleted(tmp_path):
    from maipai_packages.pantry import Pantry

    pantry = Pantry(tmp_path, None, languages=("en", "es"))
    from maipai_packages.pantry.seed_loader import seed_files, seed_records

    total = sum(len(seed_records(f)) for f in seed_files(("en", "es")))
    assert pantry.seeded == total > 400  # English and Spanish only; the other languages were not chosen
    view = pantry.view()
    assert view["built_in"]["state"] == "Built-in set" and view["built_in"]["records"] == total and view["rows"][0]["built_in"] is True
    first = pantry.library.records("joke", "en")[0]
    pantry.delete(first.id_hex)
    again = Pantry(tmp_path, None, languages=("en", "es"))
    assert again.seeded == 0 and first.id_hex not in {r.id_hex for r in again.library.records()}
    pantry.never_again(pantry.library.records("riddle", "en")[0].id_hex)


def test_never_again_records_are_not_loaded_from_the_seed(tmp_path):
    from maipai_packages.pantry import Pantry
    from maipai_packages.pantry.library import Library
    from maipai_packages.pantry.seed_loader import load_seed, seed_files, seed_records

    library = Library(tmp_path)
    target = seed_records(seed_files(("en",))[0])[0]
    library.add([target])
    library.never_again(target.id_hex)
    load_seed(library, ("en",))
    assert target.id_hex not in {r.id_hex for r in library.records()}


def test_line_records_need_a_known_situation_and_no_answer():
    import pytest
    from maipai_packages.pantry.record import SITUATIONS, Record, RecordError, check

    assert len(SITUATIONS) == 20
    ok = check(Record("line", "en", "kid", "Good morning. I am glad you are here.", "", "greeting_morning"))
    assert ok.kind == "line"
    for bad in (
        Record("line", "en", "kid", "Hello", "", "nonsense"),
        Record("line", "en", "kid", "Hello", "x", "greeting_day"),
        Record("line", "en", "adult", "Hello", "", "greeting_day"),
        Record("line", "en", "kid", "x" * 101, "", "greeting_day"),
    ):
        with pytest.raises(RecordError):
            check(bad)


def test_lines_survive_the_shelf_and_dedupe_only_within_a_situation():
    from maipai_packages.pantry.dedupe import dedupe
    from maipai_packages.pantry.record import Record
    from maipai_packages.pantry.shelf import pack, unpack

    lines = [Record("line", "en", "kid", "Good morning, friend.", "", "greeting_morning"), Record("line", "en", "kid", "Good evening, friend.", "", "greeting_evening")]
    back = unpack(pack(lines))
    assert [(r.text, r.extra) for r in back] == [(r.text, r.extra) for r in lines]
    kept, _report = dedupe([Record("line", "en", "kid", "Hello there my friend", "", "greeting_day"), Record("line", "en", "kid", "Hello there my friend now", "", "touch_head")], [])
    assert len(kept) == 2  # similar words under two situations are both kept
    kept, _report = dedupe([Record("line", "en", "kid", "Hello there my friend", "", "greeting_day"), Record("line", "en", "kid", "Hello there my friend now", "", "greeting_day")], [])
    assert len(kept) == 1


def test_the_dashboard_view_counts_offline_lines_by_situation_and_shows_the_tag(tmp_path):
    from maipai_packages.pantry import Pantry
    from maipai_packages.pantry.record import Record

    pantry = Pantry(tmp_path, None, languages=("en",), seed=False)
    pantry.library.add([Record("line", "en", "kid", "Good morning, friend.", "", "greeting_morning"), Record("line", "en", "kid", "Morning light is nice.", "", "greeting_morning"), Record("line", "en", "kid", "Good night.", "", "goodnight")])
    view = pantry.view(kind="line", language="en")
    assert view["situations"] == {"greeting_morning": 2, "goodnight": 1}
    assert {r["situation"] for r in view["rows"]} == {"greeting_morning", "goodnight"}
    assert pantry.view(kind="line", language="en", query="goodnight")["total"] == 1  # the situation is searchable


# -- review fixes (api45) -------------------------------------------------------------------------------------------------------------
def test_a_bad_never_again_id_is_refused_and_a_damaged_list_does_not_stop_generation(tmp_path):
    from maipai_body.settings_page import PANTRY, SettingsBackend

    backend = SettingsBackend.__new__(SettingsBackend)
    backend.pantry = Pantry(tmp_path, good_model, seed=False)
    backend.language = "en"
    for action in ("never-again", "delete"):
        for bad in ("not-hex", "ABCDEF0123456789", "abcd", "0123456789abcdef00"):
            assert backend.route_post(PANTRY + "/" + action, {"id": bad}, True)[0] == 400, f"{action} {bad}"
    assert backend.pantry.library.refused() == set()
    with pytest.raises(ValueError, match="16"):
        backend.pantry.library.never_again("not-hex")
    # a rejected.json already damaged by an older build still lets the library work and keeps garbage away from the units
    good_id = "0123456789abcdef"
    (tmp_path / "rejected.json").write_text(json.dumps(["not-hex", good_id, 5]))
    assert backend.pantry.library.refused() == {good_id} and backend.pantry.library.refused_ids() == {bytes.fromhex(good_id)}
    assert generate(backend.pantry.library, good_model, "joke", "en")["added"] == 2
    unit = FakeUnit([])
    run_unit(backend.pantry.library, unit, "kitchen", UnitState())
    assert unit.denied == [good_id]
    # garbage in a heard list is skipped, not fatal
    assert backend.pantry.library.note_heard("kitchen", [{"id": "zz"}, {"id": 5}, "x", {"id": backend.pantry.library.records()[0].id_hex[:8], "counter": "bad"}]) == 0


def test_an_empty_model_reply_stops_the_fact_and_riddle_checks_and_a_loose_match_is_not_a_pass(tmp_path):
    wrong = Record("trivia", "en", "kid", "What is the capital of France?", "Berlin", "Rome|Madrid")
    for record in (wrong, RIDDLE):
        for silent in ("", "   \n", None):
            with pytest.raises(ModelDown, match="empty"):
                filter_records([record], lambda p, _s=silent: _s if "suitable" not in p else "Yes")
    two = Record("riddle", "en", "kid", "What has hands but cannot clap?", "a clock")
    kept, report = filter_records([two], lambda p: "none" if "different" in p else "Yes")
    assert kept == [two] and report.kept == 1
    kept, report = filter_records([two], lambda p: "!!!" if "different" in p else "Yes")
    assert kept == [] and report.dropped == {"riddle has two answers": 1}, "a reply with no words is not 'none'"
    ant = Record("trivia", "en", "kid", "Which small insect lives in a colony?", "ant", "bee|fly")
    for got in ("a", "elephant", "an"):
        kept, report = filter_records([ant], lambda p, _g=got: "Yes" if "suitable" in p else _g)
        assert kept == [] and report.dropped == {"fact not confirmed": 1}, got
    assert filter_records([ant], lambda p: "Yes" if "suitable" in p else "An ant.")[0] == [check(ant)]
    # the generator stops the run and keeps nothing on a silent model
    library = Library(tmp_path)
    silent = generate(library, lambda p: json.dumps([{"text": "What is 2 plus 2? ", "answer": "4", "extra": "5|6"}]) if "Write" in p else "", "trivia", "en", rating="adult", adult_allowed=True)
    assert silent["added"] == 0 and "empty" in silent["stopped"] and library.records() == []


def test_the_unit_is_told_each_never_again_id_once_in_small_batches_and_a_refusal_is_tried_again(tmp_path):
    from maipai_packages.pantry.unit_link import ToolUnitLink

    library = Library(tmp_path)
    ids = [f"{i:08x}{i:08x}" for i in range(1, 41)]
    for rid in ids:
        library.never_again(rid)
    sent, flash = [], {"writes": 0, "denied": set(), "reject": False}

    def call(unit, tool, args):
        if tool == "self.pantry.heard":
            return {"ok": True, "counter": 0, "more": False, "entries": []}
        if tool == "self.pantry.status":
            return {"ok": True, "shelves": []}
        if tool == "self.pantry.deny":
            wanted = args["ids"].split(",")
            sent.append(wanted)
            if flash["reject"]:
                return {"ok": True, "denied": 0, "new": 0}
            fresh = [w for w in wanted if w not in flash["denied"]]
            flash["denied"] |= set(fresh)
            flash["writes"] += 1 if fresh else 0  # the unit writes flash only for a new deny
            return {"ok": True, "denied": len(wanted), "new": len(fresh)}
        return {"ok": False}

    link = ToolUnitLink(call)
    run_unit(library, link, "kitchen", UnitState(idle=False))
    assert sum(len(b) for b in sent) == 40 and max(len(b) for b in sent) <= 16 and flash["writes"] == len(sent)
    sent.clear()
    before = flash["writes"]
    run_unit(library, link, "kitchen", UnitState(idle=False))
    run_unit(library, link, "kitchen", UnitState(idle=False))
    assert sent == [] and flash["writes"] == before, "nothing is sent twice"
    library.never_again("000000ff000000ff")
    run_unit(library, link, "kitchen", UnitState(idle=False))
    assert sent == [["000000ff"]]
    # a unit that does not take the id gets it again on the next pass, and a second unit has its own list
    sent.clear()
    flash["reject"] = True
    library.never_again("000000ee000000ee")
    run_unit(library, link, "kitchen", UnitState(idle=False))
    flash["reject"] = False
    run_unit(library, link, "kitchen", UnitState(idle=False))
    assert [b for b in sent] == [["000000ee"], ["000000ee"]]
    sent.clear()
    run_unit(library, link, "bedroom", UnitState(idle=False))
    assert sum(len(b) for b in sent) == 42


def test_two_refills_of_one_kind_and_language_run_one_after_the_other_and_share_the_daily_cap(tmp_path):
    import threading

    library = Library(tmp_path)
    started = threading.Event()

    def slow(prompt: str) -> str:
        started.set()
        time.sleep(0.15)
        return good_model(prompt)

    results = []
    first = threading.Thread(target=lambda: results.append(generate(library, slow, "joke", "en", daily_cap=22)))
    first.start()
    started.wait(2)
    second = generate(library, slow, "joke", "en", daily_cap=22)
    first.join()
    assert results[0]["added"] == 2 and second["added"] == 0
    assert second["stopped"] == "the daily cap of model calls is reached", "the second run checks the cap after the first one counted its calls"
    assert len(library.records("joke", "en")) == 2, "no record is added twice"
    # the dashboard facade does not hold a second request open behind a running refill
    pantry = Pantry(tmp_path / "p", slow, seed=False)
    started.clear()
    runner = threading.Thread(target=lambda: results.append(pantry.refill("joke", "en")))
    runner.start()
    started.wait(2)
    busy = pantry.refill("joke", "en")
    runner.join()
    assert busy["added"] == 0 and "already running" in busy["stopped"]
    assert results[-1]["added"] == 2


def test_letters_without_an_ascii_fold_keep_their_own_ids_and_kid_generation_needs_a_word_list(tmp_path):
    assert normalize("Straße Łódź") == "strasse lodz"
    assert normalize("Ærø ı Øl") == "aero i ol"
    one = Record("joke", "en", "kid", "Привет мир | Ха")
    two = Record("joke", "en", "kid", "Совсем другая шутка | Ха-ха")
    assert one.id != two.id and one.id == Record("joke", "en", "kid", "привет, мир! | ха").id
    assert Record("joke", "pl", "kid", "Łódź | a").id != Record("joke", "pl", "kid", "Odz | a").id, "two different words no longer merge"
    assert Record("joke", "en", "kid", "Straße | x").id == Record("joke", "en", "kid", "strasse | x").id
    library = Library(tmp_path)
    called = []
    stopped = generate(library, lambda p: called.append(p) or "[]", "joke", "nl", rating="kid")
    assert called == [] and "word list" in stopped["stopped"] and stopped["added"] == 0
    generate(library, lambda p: called.append(p) or "[]", "joke", "es", rating="kid")
    assert called, "a language with a word list still asks the model"


def test_refill_in_the_background_answers_at_once_and_the_poll_gives_the_result(tmp_path):
    """Review fix R2-29: the dashboard request does not stay open for the model calls; it starts the refill and polls its state."""
    import threading
    import time

    release = threading.Event()

    def slow(prompt: str) -> str:
        release.wait(5)
        return ""

    pantry = Pantry(tmp_path / "p", slow, seed=False)
    first = pantry.start_refill("joke", "en")
    assert first["started"] is True
    assert pantry.refill_state("joke", "en")["state"] == "running"
    again = pantry.start_refill("joke", "en")
    assert again["started"] is False and again["state"] == "running"
    release.set()
    for _ in range(100):
        state = pantry.refill_state("joke", "en")
        if state["state"] != "running":
            break
        time.sleep(0.05)
    assert state["state"] == "done" and "added" in state["result"]
    assert pantry.refill_state("riddle", "en")["state"] == "idle"
