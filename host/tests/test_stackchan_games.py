# ruff: noqa: E501
"""Games (firmware patches G01 to G03): the engine core (plain C, run on the PC with a fixed seed), the pack compiler,
the signing rule, the patch files, and the host side (names, spoken asks, tools, settings page section)."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from maipai_body.bodies.stackchan import games
from maipai_body.hal.errors import BodyLost

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PATCHES = ROOT / "firmware" / "patches"
GAMES_DIR = ROOT / "firmware" / "games"
C_TESTS = HERE / "firmware"
IDS = ("memory", "whack", "tictactoe", "bopit", "rps", "eightball", "dice")  # UI13 adds tictactoe, bopit, rps; UI15 the last two; GM04 removes Reaction Time
OLD_IDS = IDS[:2]  # what games_core_test.c (patch G01) plays: memory and whack
HAVE_CC = shutil.which("cc") is not None
HAVE_CXX = shutil.which("c++") is not None


def added_file(patch: str, path: str) -> str:
    text = (PATCHES / patch).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1]
    body = block.split("\n", 1)[1]
    lines = []
    for line in body.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            lines.append(line[1:])
    return "\n".join(lines) + "\n"


def load_compiler():
    spec = importlib.util.spec_from_file_location("game_pack", ROOT / "scripts" / "game-pack.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


COMPILER = load_compiler()


@pytest.fixture(scope="module")
def core_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from firmware_order_cores import cores_dir  # the header as the whole ORDER leaves it (patch UI03 adds the Color Memory tones)

    return cores_dir(tmp_path_factory)


# ---------------------------------------------------------------------------------------------
# the engine core, in C
# ---------------------------------------------------------------------------------------------


@pytest.mark.skipif(not HAVE_CC, reason="no C compiler on this machine")
def test_the_engine_core_passes_its_c_test_on_the_shipped_packs(
    core_dir: Path, tmp_path: Path
) -> None:
    binary = tmp_path / "games_core_test"
    flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{core_dir}"]
    source = str(C_TESTS / "games_core_test.c")
    build = subprocess.run(
        ["cc", *flags, "-fsanitize=address,undefined", source, "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:  # a toolchain without the sanitizers still runs the test
        build = subprocess.run(
            ["cc", *flags, source, "-o", str(binary)], capture_output=True, text=True
        )
    assert build.returncode == 0, build.stderr
    run = subprocess.run(
        [str(binary), *(str(GAMES_DIR / f"{i}.mpk") for i in OLD_IDS)], capture_output=True, text=True
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "all passed" in run.stdout


# ---------------------------------------------------------------------------------------------
# the pack compiler
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("game", IDS)
def test_the_committed_pack_is_what_the_compiler_makes_from_its_table(game: str) -> None:
    description = json.loads((GAMES_DIR / f"{game}.json").read_text())
    assert COMPILER.build(description) == (GAMES_DIR / f"{game}.mpk").read_bytes()


@pytest.mark.parametrize("game", IDS)
def test_a_shipped_pack_is_small_ascii_and_free_of_dashes(game: str) -> None:
    blob = (GAMES_DIR / f"{game}.mpk").read_bytes()
    assert len(blob) < 8192  # far under the 16 KB ceiling of the pack format
    info = COMPILER.info(blob)
    assert info["crc_ok"] and info["id"] == game and not info["signed"]
    assert chr(8212).encode() not in blob
    text = (GAMES_DIR / f"{game}.json").read_text()
    assert chr(8212) not in text and text.isascii()


def test_the_compiler_says_what_is_wrong_in_plain_words() -> None:
    base = json.loads((GAMES_DIR / "memory.json").read_text())

    def broken(change) -> str:
        copy = json.loads(json.dumps(base))
        change(copy)
        with pytest.raises(COMPILER.PackError) as error:
            COMPILER.build(copy)
        return str(error.value)

    assert "screen edges" in broken(lambda d: d["regions"][0].update(x=5))
    assert "plain ASCII" in broken(lambda d: d["texts"]["title"].update(es="Café"))
    assert "counter" in broken(lambda d: d["rules"][0]["do"].append(["set", "nope", 1]))
    assert "state" in broken(lambda d: d["rules"][1].update(go="nowhere"))
    assert "percent sign" in broken(lambda d: d["texts"]["title"].update(en="100% sure"))
    assert "limit" in broken(lambda d: d["texts"]["title"].update(en="x" * 60))
    assert "tone" in broken(lambda d: d["rules"][14]["do"].append(["tone", "scream"]))


# ---------------------------------------------------------------------------------------------
# signing: the pack carries the same plain Ed25519 signature a firmware update does
# ---------------------------------------------------------------------------------------------


def _openssl() -> str | None:
    try:
        return COMPILER.openssl()
    except COMPILER.PackError:
        return None


@pytest.mark.skipif(
    not HAVE_CXX or _openssl() is None, reason="needs a C++ compiler and OpenSSL with Ed25519"
)
def test_a_signed_pack_checks_with_the_update_code_and_a_changed_byte_or_key_is_refused(
    core_dir: Path, tmp_path: Path
) -> None:
    openssl = _openssl()
    assert openssl is not None

    def make_key(name: str) -> tuple[Path, bytes]:
        key = tmp_path / f"{name}.pem"
        subprocess.run(
            [openssl, "genpkey", "-algorithm", "Ed25519", "-out", str(key)],
            check=True,
            capture_output=True,
        )
        der = subprocess.run(
            [openssl, "pkey", "-in", str(key), "-pubout", "-outform", "DER"],
            check=True,
            capture_output=True,
        ).stdout
        return key, der[-32:]

    key, pub = make_key("update")
    _, other_pub = make_key("other")
    unsigned = (GAMES_DIR / "memory.mpk").read_bytes()
    signed = COMPILER.sign(unsigned, key)
    assert len(signed) == len(unsigned) + 64

    work = tmp_path / "sig"
    work.mkdir()
    verify_cc = added_file(
        "155-host-url-tools-removed-and-signed-updates.patch",
        "firmware/xiaozhi-esp32/main/update_verify.cc",
    )
    verify_h = added_file(
        "155-host-url-tools-removed-and-signed-updates.patch",
        "firmware/xiaozhi-esp32/main/update_verify.h",
    )
    (work / "update_verify.cc").write_text(verify_cc)
    (work / "update_verify.h").write_text(verify_h)
    binary = work / "sigtest"
    build = subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-I{work}",
            f"-I{core_dir}",
            str(C_TESTS / "games_sig_test.cc"),
            str(work / "update_verify.cc"),
            "-o",
            str(binary),
        ],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr

    def check(blob: bytes, public: bytes) -> str:
        (work / "pack").write_bytes(blob)
        (work / "pk").write_bytes(public)
        # what the unit's crypto library computes: SHA-512 of R, the key and the signed bytes
        digest = hashlib.sha512(blob[-64:-32] + public + blob[:-64]).digest()
        (work / "h").write_bytes(digest)
        run = subprocess.run(
            [str(binary), str(work / "pack"), str(work / "pk"), str(work / "h")],
            capture_output=True,
            text=True,
        )
        return run.stdout.strip()

    assert COMPILER.verify(signed, _write_pub(tmp_path, pub))
    assert check(signed, pub) == "verified"
    assert check(signed, other_pub) == "refused"  # a different key
    tampered = bytearray(signed)
    tampered[200] ^= 1
    # the checksum no longer matches either, so the pack is refused by the checker before the signature (patch G01),
    # and the signature does not hold for the changed bytes
    assert COMPILER.info(bytes(tampered[:-64]))["crc_ok"] is False
    assert check(bytes(tampered), pub) == "bad input"
    resigned_wrong = bytearray(signed)
    resigned_wrong[-1] ^= 1  # a damaged signature over a good pack
    assert check(bytes(resigned_wrong), pub) == "refused"


def _write_pub(tmp_path: Path, raw: bytes) -> Path:
    der = bytes.fromhex("302a300506032b6570032100") + raw
    pem = (
        "-----BEGIN PUBLIC KEY-----\n"
        + base64.encodebytes(der).decode()
        + "-----END PUBLIC KEY-----\n"
    )
    path = tmp_path / "pub.pem"
    path.write_text(pem)
    return path


# ---------------------------------------------------------------------------------------------
# the patches
# ---------------------------------------------------------------------------------------------

G_PATCHES = [
    "G01-game-engine-core.patch",
    "G02-game-player-and-tools.patch",
    "G03-game-touch-voice-and-menu.patch",
]


def test_the_game_patches_have_their_header_lines_and_are_on_order_in_order() -> None:
    order = (PATCHES / "ORDER").read_text().split()
    positions = [order.index(name) for name in G_PATCHES]
    assert positions == sorted(positions) and order.index("V04-dance-extras.patch") < positions[0]
    for name in G_PATCHES:
        text = (PATCHES / name).read_text()
        for tag in (
            "# Intent:",
            "# Placement: unit (",
            "# Upstream:",
            "# Check after a flash",
            "# Kconfig:",
        ):
            assert tag in text, (name, tag)
        assert chr(8212) not in text


def test_the_switches_and_what_is_off_by_default() -> None:
    kconfig = (PATCHES / "G01-game-engine-core.patch").read_text()
    games_block = kconfig.split("config MAIPAI_GAMES\n", 1)[1].split("help", 1)[0]
    bench_block = kconfig.split("config MAIPAI_GAMES_BENCH\n", 1)[1].split("help", 1)[0]
    assert (
        "default y" in games_block
        and "default n" in bench_block
        and "depends on MAIPAI_GAMES" in bench_block
    )
    assert "CONFIG_MAIPAI_GAMES=y" in kconfig  # the core preset turns it on


def test_the_bench_tools_and_unsigned_packs_exist_only_in_a_bench_build() -> None:
    source = added_file("G02-game-player-and-tools.patch", "firmware/main/hal/maipai_games.cc")
    bench_start = source.index(
        '#if CONFIG_MAIPAI_GAMES_BENCH\n    mcp.AddTool("self.game.bench_tap"'
    )
    for tool in (
        "self.game.bench_tap",
        "self.game.status",
        "self.game.bench_install",
        "self.game.bench_request_stop",
    ):
        assert source.index(f'"{tool}"') > bench_start
    assert (
        "bool bench_build()" in source
        and "return true;" in source.split("bool bench_build()", 1)[1][:160]
    )
    assert source.count("mg_admit(MG_SRC_EXTERNAL") == 1
    # nothing the plain tools register can load a pack: the only caller of the outside loader is a bench tool
    assert source.count("maipai_games_load_external(") == 2  # the definition and the bench call


def test_the_engine_allocates_nothing_until_a_game_starts() -> None:
    source = added_file("G02-game-player-and-tools.patch", "firmware/main/hal/maipai_games.cc")
    register = source.split("void maipai_games_register_tools()", 1)[1].split(
        "#if CONFIG_MAIPAI_GAMES_BENCH", 1
    )[0]
    for call in (
        "heap_caps_malloc",
        "heap_caps_calloc",
        "xTaskCreate",
        "lv_timer_create",
        "lv_obj_create",
        "new ",
    ):
        assert call not in register, call
    # the one timer, the objects and the record are made in the start path only
    assert source.count("lv_timer_create(") == 1 and source.count("heap_caps_calloc(") == 1
    start = source.split("const char* maipai_games_start_locked", 1)[1].split(
        "bool maipai_games_stop_locked", 1
    )[0]
    assert (
        "lv_timer_create(" in start and "heap_caps_calloc(" in start and "lv_obj_create(" in start
    )
    # no flash write on the screen task: the score is written on the main task
    assert "Application::GetInstance().Schedule(" in source and source.count("nvs_set_blob(") == 1


def test_a_game_never_moves_the_head_and_the_sounds_go_through_the_policy() -> None:
    source = added_file("G02-game-player-and-tools.patch", "firmware/main/hal/maipai_games.cc")
    for forbidden in ("GetStackChan", "motion", "setHeadAngles", "setRgbColor"):
        assert forbidden not in source, forbidden
    assert "maipai_sounds_play(MG_TONES[" in source and "PlaySound(" not in source
    assert "maipai_quiet()" in source  # full quiet ends a game and refuses a start


def test_the_touch_edges_and_the_stop_swipe_stay_the_units() -> None:
    patch = (PATCHES / "G03-game-touch-voice-and-menu.patch").read_text()
    assert "maipai_games_active() && s_trace.region0 != MTC_REGION_EDGE" in patch
    assert 'maipai_games_stop_locked("swipe")' in patch
    assert 'GetDeviceState() != kDeviceStateSpeaking && maipai_games_request_stop("stop")' in patch
    # the timer ring takes the stop word first
    assert patch.index("Stop word heard while a timer rings") < patch.index(
        'maipai_games_request_stop("stop")'
    )


def test_the_games_page_is_in_english_and_spanish() -> None:
    patch = (PATCHES / "G03-game-touch-voice-and-menu.patch").read_text()
    assert 'tx("Games", "Juegos")' in patch and 'tx("best", "mejor")' in patch


# ---------------------------------------------------------------------------------------------
# the host side
# ---------------------------------------------------------------------------------------------


def test_the_host_names_match_the_firmware_tables() -> None:
    for game in games.GAMES:
        table = json.loads((GAMES_DIR / f"{game.id}.json").read_text())
        assert table["id"] == game.id
        assert table["texts"]["title"]["en"] == game.title["en"]
        assert table["texts"]["title"]["es"] == game.title["es"]
        assert bool(table.get("lower_is_better")) is game.lower_is_better
    assert games.IDS == IDS


@pytest.mark.parametrize(
    ("said", "expect"),
    [
        ("play memory", ("start", "memory")),
        ("let's play the color memory game", ("start", "memory")),
        ("Can we play whack-a-mole?", ("start", "whack")),
        ("start tic tac toe", ("start", "tictactoe")),
        ("play reaction time", None),  # patch GM04: that game is gone, so nothing starts
        ("juega a los topos", ("start", "whack")),
        ("Juguemos al atrapa topos", ("start", "whack")),
        ("quiero jugar a memoria de colores", ("start", "memory")),
        ("quiero jugar tres en raya", ("start", "tictactoe")),
        ("quiero jugar tiempo de reacción", None),
        ("stop the game", ("stop", None)),
        ("para el juego", ("stop", None)),
        ("what games do you have", ("list", None)),
        ("¿qué juegos tienes?", ("list", None)),
        ("what is my best score in whack a mole", ("scores", "whack")),
        ("mejor puntuación", ("scores", None)),
    ],
)
def test_spoken_asks_about_games(said: str, expect: tuple[str, str | None]) -> None:
    assert games.parse_ask(said) == expect


@pytest.mark.parametrize(
    "said",
    [
        "stop",
        "stop talking",
        "list my timers",
        "play some music",
        "what is the memory of this unit",
        "tell me a story",
        "",
        None,
        5,
    ],
)
def test_words_that_are_not_about_games_are_left_alone(said: object) -> None:
    assert games.parse_ask(said) is None


class FakeGames:
    """Answers self.game.* the way the firmware does."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.link = True
        self.old = False
        self.playing = False
        self.refuse = ""

    def __call__(self, name: str, arguments: dict) -> object:
        self.calls.append((name, arguments))
        if not self.link:
            raise BodyLost("the unit is not connected")
        if self.old:
            return {"ok": False, "error": "unknown tool"}
        if name == "self.game.start":
            if self.refuse:
                return json.dumps({"ok": False, "error": self.refuse})
            self.playing = True
            return json.dumps({"ok": True})
        if name == "self.game.stop":
            was, self.playing = self.playing, False
            return {"ok": True, "was": was}
        if name == "self.game.list":
            return {
                "ok": True,
                "playing": self.playing,
                "games": [
                    {
                        "id": "memory",
                        "title": "Color Memory",
                        "lower_is_better": False,
                        "scores": [7, 5, 4],
                    },
                    {
                        "id": "tictactoe",
                        "title": "Tic-Tac-Toe",
                        "lower_is_better": False,
                        "scores": [30, 10],
                    },
                    {
                        "id": "whack",
                        "title": "Whack-a-Mole",
                        "lower_is_better": False,
                        "scores": [],
                    },
                ],
            }
        if name == "self.game.scores":
            return {"ok": True, "game": arguments["name"], "lower_is_better": False, "scores": [3]}
        raise AssertionError(name)


def test_the_service_starts_stops_lists_and_answers_spoken_asks() -> None:
    unit = FakeGames()
    service = games.GameService(unit)
    assert service.start("Whack a mole") == {"ok": True, "game": "whack"}
    assert unit.calls[-1] == ("self.game.start", {"name": "whack"})
    assert service.stop()["was"] is True
    view = service.list("es")
    assert view["ok"] and [g["title"] for g in view["games"]][1] == "Tres en raya"
    assert view["games"][1]["lower_is_better"] is False and view["games"][1]["unit"] == "puntos"
    assert service.ask("play tic tac toe")["game"] == "tictactoe"
    assert service.ask("what games do you have")["games"][0]["scores"] == [7, 5, 4]
    assert service.ask("best score in memory")["scores"] == [3]
    assert service.ask("good morning") is None


def test_the_service_speaks_plainly_when_it_cannot_do_it() -> None:
    unit = FakeGames()
    service = games.GameService(unit)
    assert "do not know that game" in service.start("chess")["error"]
    assert "No conozco" in service.start("ajedrez", "es")["error"]
    unit.refuse = (
        "The unit is in full quiet, so no game starts. Turn full quiet off, then ask again."
    )
    assert service.start("memory") == {
        "ok": False,
        "error": unit.refuse,
    }  # the unit's own sentence goes through
    unit.link = False
    lost = service.list()
    assert lost["ok"] is False and "reach my body" in lost["error"] and "ask again" in lost["error"]
    assert "No pude llegar" in service.stop("es")["error"]
    unit.link, unit.old = True, True
    old = service.list()
    assert old["ok"] is False and "firmware has no games" in old["error"]
    assert "no tiene juegos" in service.scores("memory", "es")["error"]


def test_the_hub_commands_are_named_and_never_raise() -> None:
    unit = FakeGames()
    handlers = games.GameService(unit).handlers()
    assert set(handlers) == {"game_start", "game_stop", "game_list", "game_scores"}
    assert handlers["game_start"]({"name": "memory"})["ok"] is True
    assert handlers["game_list"]({})["ok"] is True
    assert handlers["game_scores"]({"name": "whack"})["scores"] == [3]
    assert handlers["game_start"]({})["ok"] is False

    def boom(name: str, arguments: dict) -> object:
        raise RuntimeError("broken")

    answer = games.GameService(boom).handlers()["game_list"]({})
    assert answer["ok"] is False and "reach my body" in answer["error"]


def test_the_hub_wires_the_game_commands_next_to_the_timer_commands() -> None:
    source = (ROOT / "host" / "maipai_body" / "app.py").read_text()
    assert "**GameService(voice.robot.client._call).handlers()," in source


# ---- the settings page ----


def _settings_backend(tmp_path: Path, unit: FakeGames):
    from maipai_body import settings_page
    from maipai_body import unit_extras as extras_mod

    def call(name: str, arguments: dict, *, device_id: str, timeout: float) -> object:
        return unit(name, arguments)

    return settings_page.SettingsBackend(
        devices=lambda: {"aa:bb:cc:dd:ee:01": {}},
        store=settings_page.UnitSettingsStore(tmp_path / "units.json"),
        extras=extras_mod.UnitExtras(call),
    )


def test_the_settings_page_lists_every_game_and_its_best_scores(tmp_path: Path) -> None:
    unit = FakeGames()
    backend = _settings_backend(tmp_path, unit)
    path = "/api/stackchan/unit/aa:bb:cc:dd:ee:01/games"
    status, _, body = backend.route_get(path, "en", True)
    view = json.loads(body)
    assert status == 200 and view["ok"] is True
    assert view["lines"] == [
        "Color Memory: 7, 5, 4 rounds",
        "Tic-Tac-Toe: 30, 10 points",
        "Whack-a-Mole: none yet",
    ]
    status, _, body = backend.route_get(path, "es", True)
    assert json.loads(body)["lines"][0] == "Memoria de colores: 7, 5, 4 rondas"
    assert json.loads(body)["lines"][2] == "Atrapa topos: ninguna todavia"
    unit.link = False
    status, _, body = backend.route_get(path, "en", True)
    lost = json.loads(body)
    assert status == 200 and lost["ok"] is False and "ask again" in lost["error"]
    assert backend.route_get("/api/stackchan/unit/aa:bb:cc:00:00:99/games", "en", True)[0] == 400
    assert backend.route_get(path, "en", False)[0] == 403  # local administrator only


def test_the_settings_page_shows_the_games_section_in_every_language() -> None:
    from maipai_body.i18n import CATALOG
    from maipai_body.settings_page import render_page

    for code in ("en", "es", "fr", "de", "pt", "it"):
        assert CATALOG[code]["settings.games"] and CATALOG[code]["settings.games.show"]
    page = render_page("en").decode()
    assert "unitPath(id,'games')" in page and "BUILDERS.play" in page


# ---- the spoken path (answered on the host, before the hub is asked) ----


def test_a_spoken_game_ask_becomes_a_game_command_and_is_answered_in_the_language_used() -> None:
    from maipai_body.bodies.stackchan.head_commands import HeadCommander, parse_head_command

    command = parse_head_command("can you play whack a mole please")
    assert command is not None and command.kind == "game" and command.game_ask == ("start", "whack")
    unit = FakeGames()
    service = games.GameService(unit)
    commander = HeadCommander(lambda yaw, pitch, speed: None, game=service.spoken)
    assert commander.run(command) == "Okay, let's play Whack-a-Mole."
    assert unit.calls[-1] == ("self.game.start", {"name": "whack"})
    spanish = parse_head_command("juega a los topos")
    assert spanish is not None and commander.run(spanish) == "Vale, a jugar a Atrapa topos."
    stop = parse_head_command("stop the game")
    assert stop is not None and commander.run(stop) == "Okay, I stopped the game."
    assert commander.run(stop) == "No game is playing right now."
    listing = parse_head_command("what games do you have")
    assert listing is not None
    assert commander.run(listing) == "I have Color Memory, Tic-Tac-Toe and Whack-a-Mole."
    best = parse_head_command("what is my best score in tic tac toe")
    assert best is not None and commander.run(best) == "Your best in Tic-Tac-Toe is 3 points."
    # the plain words around the games do not become game commands, and the head commands still work
    assert parse_head_command("stop") is None
    left = parse_head_command("look left")
    assert left is not None and left.kind == "look"


def test_a_refused_spoken_start_says_why_and_a_lost_unit_says_what_to_do() -> None:
    from maipai_body.bodies.stackchan.head_commands import CAN_DO, HeadCommander, parse_head_command

    unit = FakeGames()
    service = games.GameService(unit)
    commander = HeadCommander(lambda yaw, pitch, speed: None, game=service.spoken)
    command = parse_head_command("play memory")
    assert command is not None
    unit.refuse = (
        "The unit is in full quiet, so no game starts. Turn full quiet off, then ask again."
    )
    assert commander.run(command) == unit.refuse
    unit.refuse, unit.link = "", False
    assert "reach my body" in commander.run(command)
    assert (
        HeadCommander(lambda yaw, pitch, speed: None).run(command) == CAN_DO
    )  # no games wired: it says what it can do
