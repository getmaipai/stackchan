"""The character files and their checker (scripts/character-check.py, schema/character.json, docs/design/characters.md)."""
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "character-check.py"
CHAR_DIR = ROOT / "host" / "maipai_body" / "characters"
SCHEMA = ROOT / "schema" / "character.json"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cc = _load("character_check", SCRIPT)
face_styles = _load("face_styles_for_test", ROOT / "scripts" / "virtual-unit" / "face_styles.py")

FILES = sorted(CHAR_DIR.glob("*.json"))


def shipped():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in FILES}


def atlas():
    return copy.deepcopy(shipped()["atlas"])


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_shipped_character_validates(path):
    assert cc.check_file(path) == []


def test_exactly_six_characters():
    assert sorted(shipped()) == ["atlas", "bruno", "clover", "cosmo", "daisy", "ember"]
    for stem, data in shipped().items():
        assert data["id"] == stem


def test_no_shared_style_or_color():
    chars = shipped().values()
    styles = [c["face"]["style"] for c in chars]
    colors = [c["face"]["color"] for c in chars]
    assert len(set(styles)) == len(styles)
    assert len(set(colors)) == len(colors)


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_under_1024_bytes(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")) < 1024


def test_copy_with_based_on_validates():
    data = atlas()
    data["id"] = "atlas2"
    data["based_on"] = "atlas"
    assert cc.validate(data) == []


def _mut(fn):
    data = atlas()
    fn(data)
    return data


BAD = {
    "unknown style": (lambda d: d["face"].update(style="nope"), "style"),
    "speed": (lambda d: d["voice"].update(speed=2.0), "speed"),
    "pitch": (lambda d: d["voice"].update(pitch=13), "pitch"),
    "persona": (lambda d: d.update(persona="p" * 481), "persona"),
    "extra key": (lambda d: d.update(mood="happy"), "mood"),
    "bad color": (lambda d: d["face"].update(color="#12345"), "color"),
    "missing face": (lambda d: d.pop("face"), "face"),
    "based_on is id": (lambda d: d.update(based_on="atlas"), "based_on"),
    "em dash": (lambda d: d.update(about="Calm \u2014 clear."), "em dash"),
}


@pytest.mark.parametrize("label", list(BAD))
def test_failing_cases_give_a_message(label):
    fn, word = BAD[label]
    problems = cc.validate(_mut(fn))
    assert problems, label
    assert any(word in p for p in problems), problems
    assert all(p.endswith(".") and "\u2014" not in p for p in problems)


def test_1100_byte_file(tmp_path):
    data = atlas()
    data["persona"] = "p" * 480
    data["about"] = "a" * 80
    data["wake"] = "w" * 24
    data["voice"]["ids"] = {"local": "l" * 40, "home": "h" * 40}
    data["pad"] = "x" * 400
    size = len(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    assert size > 1024
    f = tmp_path / "atlas.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    problems = cc.check_file(f)
    assert any("bytes" in p for p in problems), problems


def test_id_must_match_file_name(tmp_path):
    data = atlas()
    f = tmp_path / "other.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    problems = cc.check_file(f)
    assert len(problems) == 1 and "file name" in problems[0] and problems[0].startswith("other.json: ")


def test_bad_json_gives_a_message(tmp_path):
    f = tmp_path / "broken.json"
    f.write_text("{", encoding="utf-8")
    assert "not valid JSON" in cc.check_file(f)[0]


def test_schema_style_enum_equals_style_list():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["face"]["properties"]["style"]["enum"] == face_styles.STYLES


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def test_script_exits_0_on_shipped_files():
    r = _run()
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == "characters: ok (6 files)"


def test_script_exits_1_on_a_bad_file(tmp_path):
    data = atlas()
    data["face"]["style"] = "nope"
    f = tmp_path / "atlas.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    r = _run(str(f))
    assert r.returncode == 1
    assert r.stdout.startswith("atlas.json: ") and "style" in r.stdout
