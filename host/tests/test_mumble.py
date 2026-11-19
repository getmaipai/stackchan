"""Patch UX16, the offline mumble: the pure C core and the Python reference give the same notes for the same text in all six languages; the notes follow the caption's timing;
the mouth follows the notes; the core calls nothing of the hardware and the patch is on ORDER with its header lines."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAME = "UX16-offline-mumble-core.patch"
if not (PATCHES / NAME).exists():   # the patch waits on the branch ux/unproven-games for its bench proof (plain boot first); its tests join ORDER with it
    pytest.skip(NAME + " is not in firmware/patches yet", allow_module_level=True)
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
import mumble  # noqa: E402

SENTENCES = {
    "en": "Hello! I am your robot. How can I help you today?",
    "es": "¡Hola! Soy tu robot. ¿En qué puedo ayudarte hoy?",
    "fr": "Bonjour ! Je suis ton robot. Comment puis-je t'aider aujourd'hui ?",
    "de": "Hallo! Ich bin dein Roboter. Wie kann ich dir heute helfen?",
    "pt": "Olá! Eu sou o teu robô. Como posso ajudar-te hoje?",
    "it": "Ciao! Sono il tuo robot. Come posso aiutarti oggi?",
    "edge": "Straße œuvre ÀÉÎÕÜ ñ ç \u2014 42… ok (yes), no; maybe: 日本語 😀 Привет",
    "empty-ish": "   ",
}


def _added(path: str) -> str:
    text = (PATCHES / NAME).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


@pytest.fixture(scope="module")
def dump(tmp_path_factory):
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    d = tmp_path_factory.mktemp("mumble")
    (d / "maipai_mumble_core.h").write_text(_added("firmware/main/hal/maipai_mumble_core.h"))
    exe = d / "dump"
    r = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{d}", str(HERE / "firmware" / "mumble_core_dump.c"), "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return exe


@pytest.mark.parametrize("lang", sorted(SENTENCES))
def test_the_c_core_and_the_reference_agree(dump, lang):
    text = SENTENCES[lang]
    out = subprocess.run([str(dump), text, "3000"], capture_output=True, text=True, check=True).stdout.split("\n")
    c = [tuple(int(x) for x in line.split()) for line in out if line.strip()]
    py = [b.as_tuple() for b in mumble.blips(text, 100, 3100)]
    assert c == py, f"{lang}: the C core and the Python reference differ at the first mismatch: {next((i for i, (a, b) in enumerate(zip(c, py)) if a != b), min(len(c), len(py)))}"


def test_the_notes_follow_the_caption_timing():
    text = SENTENCES["en"]
    for ms in (800, 2500, 7000):
        b = mumble.blips(text, 1000, 1000 + ms)
        assert b[0].t_ms == 1000 and b[-1].t_ms + b[-1].dur_ms <= 1000 + ms
        assert all(b[i].t_ms <= b[i + 1].t_ms for i in range(len(b) - 1))
        assert len(b) == len(text)           # one note slot for every character
    fast, slow = mumble.blips(text, 0, 1000), mumble.blips(text, 0, 4000)
    assert slow[5].t_ms == 4 * fast[5].t_ms or abs(slow[5].t_ms - 4 * fast[5].t_ms) <= 3   # the same text spread over four times as long


def test_every_language_has_notes_and_rests_and_a_moving_mouth():
    for lang, text in SENTENCES.items():
        if lang == "empty-ish":
            continue
        b = mumble.blips(text, 0, 3000)
        assert sum(1 for x in b if x.dur_ms) >= len(text) // 2, lang
        assert any(x.dur_ms == 0 for x in b), f"{lang}: spaces and marks must rest"
        mouth = mumble.mouth_schedule(b)
        assert max(mouth) >= 85 and 0 in mouth and len(set(mouth)) >= 4, f"{lang}: the mouth must open and close in several widths"


def test_a_question_rises_and_a_statement_falls():
    q = mumble.blips("Are you there?", 0, 1400)
    s = mumble.blips("You are there.", 0, 1400)
    last_q = [b for b in q if b.dur_ms][-1]
    last_s = [b for b in s if b.dur_ms][-1]
    assert last_q.f0 > mumble.freq(4), "the last letter of a question is raised"
    assert last_s.f0 <= mumble.freq(4), "the last letter of a statement is lowered"


def test_the_same_text_always_gives_the_same_notes():
    assert mumble.blips(SENTENCES["fr"], 0, 2000) == mumble.blips(SENTENCES["fr"], 0, 2000)


def test_the_patch_is_on_order_with_its_header_lines_and_the_core_is_free_of_hardware():
    assert NAME in (PATCHES / "ORDER").read_text().split()
    head = (PATCHES / NAME).read_text().split("diff --git", 1)[0]
    for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:", "# Kconfig:"):
        assert key in head
    assert not re.search(r"esp_|nvs_|hal_bridge|Application|Board::|malloc|calloc", _added("firmware/main/hal/maipai_mumble_core.h"))


def test_the_virtual_unit_mumbles_a_caption_with_its_mouth():
    import importlib.util
    if not (ROOT / ".runs" / "vu-screens" / "render").exists():
        pytest.skip("screens renderer not built")
    spec = importlib.util.spec_from_file_location("vunit", ROOT / "scripts" / "virtual-unit" / "vunit.py")
    vunit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vunit)
    with vunit.VirtualUnit(profile="screens") as u:
        out = u.call("sim.mumble", {"text": SENTENCES["es"], "ms": 3000})
        assert out["ok"] and out["notes"] > 20 and out["rests"] > 5
        u.advance(3400)
        st = u.state["mumble"]
        assert not st["active"] and len(st["played"]) == out["notes"], "every note was played and the mumble ended by itself"
        assert u.call("sim.mumble", {"text": ""})["ok"] is False
