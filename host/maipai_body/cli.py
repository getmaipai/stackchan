# ruff: noqa: E501
"""Host setup and status commands."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore, default_pairing_path
from maipai_body.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(prog="stackchan")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="start the host the robot connects to")
    commands.add_parser(
        "coding-token", help="make the coding companion token file and print where it is (never the token)"
    )
    commands.add_parser(
        "settings-token", help="print the token that logs a phone in to the settings page"
    )
    commands.add_parser("check", help="test the model and speech addresses in robot.toml")
    commands.add_parser("forget", help="unpair every robot (use before giving one away)")
    commands.add_parser("pair", help="show a one-use pairing code")
    commands.add_parser("status", help="say what is running and what is not, per robot and per part")
    service = commands.add_parser("service", help="install the host as a service that starts at boot or login and restarts itself")
    service.add_argument("action", choices=["install", "status", "start", "stop", "logs", "uninstall"])
    units = commands.add_parser("units", help="list known units with their name and online state")
    units.add_argument(
        "--host-url", default="http://127.0.0.1:8051", help="the running host's settings page"
    )
    name = commands.add_parser(
        "name", help="give a unit a name (it is shown instead of its Device-Id)"
    )
    name.add_argument("unit", help="Device-Id of the unit, or its current name")
    name.add_argument("new_name", metavar="name", help="the new name, 1 to 40 characters")
    face = commands.add_parser(
        "face", help="show or change a unit's face: style, color, captions, time-of-day"
    )
    face.add_argument("action", choices=["show", "set", "sync", "reset"])
    face.add_argument("unit", help="Device-Id of the unit, or its name")
    face.add_argument("--style", help="classic, big_eyes or minimal")
    face.add_argument("--color", "--colour", dest="color", help="none, a name, or #rrggbb")
    face.add_argument("--captions", choices=["on", "off"])
    face.add_argument("--schedule", choices=["on", "off"], help="change the face by time of day")
    face.add_argument("--hours", help="four hours that rise, for example 6,9,18,21")
    face.add_argument("--lang", help="en or es")
    face.add_argument(
        "--host-url", default="http://127.0.0.1:8051", help="the running host's settings page"
    )
    character = commands.add_parser("character", help="build or check an illustrated character pack")
    character_commands = character.add_subparsers(dest="character_action", required=True)
    character_build = character_commands.add_parser("build", help="build a character pack from image files")
    character_build.add_argument("src")
    character_build.add_argument("out_zip")
    character_build.add_argument("--name", required=True)
    character_build.add_argument("--author", required=True)
    character_build.add_argument("--license", required=True)
    character_build.add_argument("--mode", choices=["picture", "overlay", "sequence"], default="picture")
    character_build.add_argument("--fps", type=int, default=6)
    character_check = character_commands.add_parser("check", help="check a character pack")
    character_check.add_argument("pack")
    bench = commands.add_parser("bench", help="start the local unit testing console")
    bench.add_argument("--host", default="127.0.0.1")
    bench.add_argument("--port", type=int, default=9790)
    bench.add_argument("--token")
    bench.add_argument("--sim", action="store_true", help="use the in-process fake unit")
    run = commands.add_parser("bench-run", help="run the fixed 20-turn voice benchmark")
    run.add_argument("--sim", action="store_true")
    run.add_argument("--script", type=str)
    run.add_argument("--firmware-label", default="stackchan")
    run.add_argument("--play-device", help="host output device for prompt playback")
    analyze = commands.add_parser("bench-analyze", help="analyze a 48 kHz recording")
    analyze.add_argument("recording")
    analyze.add_argument(
        "--question-end",
        type=float,
        default=0.0,
        help="question end offset in seconds from recording start",
    )
    frames = commands.add_parser("bench-frames", help="analyze frame timestamps")
    frames.add_argument("frametimes")
    compare = commands.add_parser("bench-compare", help="compare two benchmark JSON files")
    compare.add_argument("a")
    compare.add_argument("b")
    for name, text in (
        ("flash", "flash a signed release to a unit over USB (esptool)"),
        ("update", "check a signed release and update a running unit over the air"),
    ):
        sub = commands.add_parser(name, help=text)
        sub.add_argument("--source", help="release folder (default: update.source in robot.toml)")
        sub.add_argument(
            "--preset", choices=["core", "home"], help="refuse a release of another preset"
        )
        sub.add_argument("--public-key", help="trusted release public key PEM")
        sub.add_argument("--dry-run", action="store_true", help="check everything, change nothing")
        sub.add_argument("--lang", help="en or es")
        if name == "flash":
            sub.add_argument(
                "--port", help="serial port of the unit, for example /dev/cu.usbmodem101"
            )
            sub.add_argument("--baud", type=int, default=460800)
        else:
            sub.add_argument("--unit", help="Device-Id of the paired unit")
            sub.add_argument("--host-url", default="http://127.0.0.1:8050")
    args = parser.parse_args()
    if args.command == "character":
        from maipai_body.character_pack import build_pack, validate_pack
        from maipai_body.picture_faces import PictureError

        if args.character_action == "check":
            problems = validate_pack(args.pack)
            if problems:
                print("\n".join(problems))
                return 1
            print("Pack is valid.")
            return 0
        try:
            build_pack(args.src, args.out_zip, args.name, args.author, args.license, args.mode, args.fps)
        except (PictureError, OSError) as error:
            print(str(error), file=sys.stderr)
            return 1
        print(f"Built {args.out_zip}")
        return 0
    if args.command in {"flash", "update"}:
        return _flash_or_update(args)
    if args.command == "face":
        return _face(args)
    if args.command == "bench":
        from maipai_body.bench import BenchServer, SimUnit
        from maipai_body.brain.fake import FakeBrain

        if not args.sim:
            print(
                "No live unit driver is attached to this command. Start the host body "
                "service with its connected unit, then use its bench endpoint.",
                file=sys.stderr,
            )
            return 2
        try:
            server = BenchServer(
                host=args.host,
                port=args.port,
                token=args.token,
                sim=True,
                unit=SimUnit(),
                brain=FakeBrain(),
            )
        except ValueError as error:
            print(str(error), file=sys.stderr)
            return 2
        print(f"StackChan bench listening at http://{args.host}:{server.address[1]}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
        return 0
    if args.command == "bench-run":
        from maipai_body.measure.bench import markdown_table, run_sim, script_path

        if not args.sim:
            print(
                "Live unit timing needs an attached voice link. Use --sim or run this "
                "from the host service.",
                file=sys.stderr,
            )
            return 2
        data = run_sim(
            Path(args.script) if args.script else script_path(), firmware=args.firmware_label
        )
        target = Path("data/bench") / f"{args.firmware_label}-{data['date']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2) + "\n")
        target.with_suffix(".md").write_text(
            f"# Benchmark {args.firmware_label} {data['date']}\n\n{markdown_table(data)}\n"
        )
        print(markdown_table(data))
        print(f"Saved {target}")
        return 0
    if args.command == "bench-analyze":
        from maipai_body.measure.bench import analyze_recording

        print(
            json.dumps(
                analyze_recording(args.recording, question_end_s=args.question_end), indent=2
            )
        )
        return 0
    if args.command == "bench-frames":
        from maipai_body.measure.bench import analyze_frames

        print(json.dumps(analyze_frames(args.frametimes), indent=2))
        return 0
    if args.command == "bench-compare":
        from maipai_body.measure.bench import compare

        table, passed = compare(
            json.loads(Path(args.a).read_text()), json.loads(Path(args.b).read_text())
        )
        print(table)
        print(
            "PASS: comparison meets the pass line."
            if passed
            else "FAIL: comparison misses the pass line."
        )
        return 0 if passed else 1
    if args.command == "run":
        os.environ.setdefault("MAIPAI_BODY", "stackchan")
        os.execv(sys.executable, [sys.executable, "-m", "maipai_body.app"])
        return 0
    if args.command == "service":
        from maipai_body.service_cmd import Service

        service = Service()
        return {"install": service.install, "status": service.status, "start": service.start, "stop": service.stop, "logs": service.logs, "uninstall": service.uninstall}[args.action]()
    config = load_config()
    store = PairingStore(default_pairing_path())
    if args.command in {"units", "name"}:
        return _units_or_name(args, config, store)
    if args.command == "coding-token":
        from maipai_packages.coding_companion.server import AgentAuth, default_token_path

        path = default_token_path()
        AgentAuth(path)
        print(f"Coding companion token file: {path}")
        print("A hook reads the token from that file and posts JSON to http://127.0.0.1:8052/status with Authorization: Bearer <token>.")
        print('Body: {"state": "working" | "waiting" | "finished", "kind": "permission" | "question", "project": "name"}')
        return 0
    if args.command == "settings-token":
        from maipai_body.local_guard import SettingsAuth

        token = SettingsAuth(default_pairing_path().parent / "settings-token").token
        print(f"Settings token: {token}")
        print("On your phone open http://<this computer's address>:8051/settings?token=<the token> once.")
        if not config.settings.lan:
            print("The page is still local only. Set lan = true under [settings] in robot.toml, restart the host, then use the address above.")
        print("Anyone on your Wi-Fi who learns the token can change the robot's settings: keep it private.")
        return 0
    if args.command == "check":
        return _check(config)
    if args.command == "forget":
        for device_id in list(store.paired_devices()):
            store.revoke(device_id)
        print("Every robot is unpaired. Run `stackchan pair` to pair one again.")
        return 0
    if args.command == "pair":
        print(f"Pairing code: {store.create_pair_code()}")
        print("Enter this code on the unit setup page within 10 minutes.")
        return 0
    from maipai_body.health import fetch_health, render_text

    health = fetch_health()
    if health is not None:
        print(render_text(health))
        return 0 if health["state"] == "ok" else 1
    print("The host is not running. Start it with `stackchan service start` (or `stackchan run`), and see `stackchan service status`.")
    print(f"Brain: {config.brain}")
    devices = store.paired_devices()
    print(f"Paired units: {len(devices)}")
    for device_id, record in sorted(devices.items()):
        seen = record.get("last_seen")
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(seen))) if seen else "never"
        print(f"{device_id}: last seen {when}")
    return 0


def _face_values(args: argparse.Namespace) -> dict[str, object]:
    values: dict[str, object] = {}
    if args.style is not None:
        values["style"] = args.style
    if args.color is not None:
        values["color"] = args.color
    if args.captions is not None:
        values["captions"] = args.captions == "on"
    if args.schedule is not None:
        values["tod"] = args.schedule == "on"
    if args.hours is not None:
        try:
            values["tod_hours"] = [int(x) for x in args.hours.replace(" ", "").split(",")]
        except ValueError:
            raise ValueError(
                "The hours must be four whole numbers from 0 to 23 with commas, for example 6,9,18,21."
            ) from None
    return values


def _face(args: argparse.Namespace) -> int:
    """`stackchan face show|set|sync|reset UNIT`: the running host owns the saved settings, so a
    change goes through its settings page and reaches the unit at once; with no host running it is
    saved to the same file and reaches the unit when the host next sees it connect."""
    import urllib.error
    import urllib.request
    from urllib.parse import quote

    from maipai_body import faces as face_settings
    from maipai_body.i18n import normalize
    from maipai_body.unit_settings import UnitSettingsStore
    from maipai_body.units import LayeredStore, known_units

    config = load_config()
    lang = normalize(args.lang or config.home.language)
    pairing = PairingStore(default_pairing_path())
    rows = known_units(
        pairing.paired_devices(), LayeredStore(UnitSettingsStore(), config.units), None
    )
    wanted = args.unit.lower().replace("-", ":")
    matches = [r for r in rows if r["device_id"].lower().replace("-", ":") == wanted]
    matches = matches or [r for r in rows if r["name"].lower() == args.unit.lower()]
    if len(matches) != 1:
        print(
            f"No single unit matches {args.unit!r}. Run `stackchan units` and copy a Device-Id from the list.",
            file=sys.stderr,
        )
        return 2
    unit_id = matches[0]["device_id"]
    try:
        values = _face_values(args)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.action in {"set"} and not values:
        print(
            "Nothing to set. Add --style, --color, --captions, --schedule or --hours.",
            file=sys.stderr,
        )
        return 2
    if args.action != "show" and values and args.action != "set":
        print(
            "Only `face set` takes settings. Use `stackchan face set UNIT --style ...`.",
            file=sys.stderr,
        )
        return 2
    base = f"{args.host_url.rstrip('/')}/api/stackchan/faces/{quote(unit_id, safe='')}"
    if args.action == "show":
        store = face_settings.FaceStore()
        service = face_settings.FaceService(face_settings.offline_call, store)
        view = face_settings.settings_view(service, unit_id, lang)
        try:
            with urllib.request.urlopen(f"{base}?lang={lang}", timeout=3) as response:  # noqa: S310
                view = json.loads(response.read())
        except (OSError, ValueError):
            pass  # the host is not running: the saved file is the answer
        print(f"{matches[0]['name']} ({unit_id})")
        for key, value in view["values"].items():
            print(f"  {key}: {value}")
        if view.get("pending"):
            print("  Not yet sent to the unit. It gets these settings when it connects.")
        for line in view.get("unavailable") or []:
            print(f"  The unit's firmware does not have: {line}")
        return 0
    if args.action == "sync":
        # `sync` re-sends what is saved: a set with no change pushes it.
        path, body = base, {"lang": lang}
    elif args.action == "reset":
        path, body = base + "/reset", {"lang": lang}
    else:
        path, body = base, {**values, "lang": lang}
    request = urllib.request.Request(
        path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
            result = json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read()).get("error", "")
        except ValueError:
            message = ""
        print(
            message or "The host refused the change. Check the values and try again.",
            file=sys.stderr,
        )
        return 2
    except OSError:
        # No host is running: save to the shared file; the host sends it on the unit's next connect.
        store = face_settings.FaceStore()
        service = face_settings.FaceService(face_settings.offline_call, store)
        try:
            if args.action == "reset":
                service.reset(unit_id, lang)
            elif args.action == "set":
                service.update(unit_id, values, lang)
        except face_settings.FaceError as error:
            print(str(error), file=sys.stderr)
            return 2
        print(
            "The host is not running, so the setting is saved only. It goes to the unit when the host "
            "next sees it connect (start the StackChan host)."
        )
        return 0
    print(result.get("message") or ("Sent to the unit." if result.get("pushed") else "Saved."))
    for line in result.get("unsupported") or []:
        print(line)
    return 0


def _online_from_host(host_url: str) -> set[str] | None:
    """Device-Ids the running host says are connected, or None when it cannot be asked."""
    import urllib.request

    try:
        with urllib.request.urlopen(  # noqa: S310
            f"{host_url.rstrip('/')}/api/stackchan/settings", timeout=3
        ) as response:
            data = json.loads(response.read())
        return {u["device_id"] for u in data["units"] if u.get("online")}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _units_or_name(args: argparse.Namespace, config, pairing: PairingStore) -> int:
    from maipai_body.unit_settings import SettingsError, UnitSettingsStore
    from maipai_body.units import LayeredStore, known_units

    store = LayeredStore(UnitSettingsStore(), config.units)
    paired = pairing.paired_devices()
    if args.command == "units":
        online = _online_from_host(args.host_url)
        rows = known_units(paired, store, online)
        if not rows:
            print("No units yet. Run `stackchan pair`, then enter the code on the unit.")
            return 0
        for row in rows:
            state = {None: "unknown", True: "online", False: "offline"}[row["online"]]
            print(
                f"{row['name']}: {row['device_id']}, {state}"
                + ("" if row["paired"] else ", not paired")
            )
        if online is None:
            print(
                f"The host did not answer at {args.host_url}, so online state is unknown. "
                "Start the StackChan host to see it."
            )
        return 0
    rows = known_units(paired, store, None)
    wanted = args.unit.lower().replace("-", ":")
    matches = [r for r in rows if r["device_id"].lower().replace("-", ":") == wanted]
    matches = matches or [r for r in rows if r["name"].lower() == args.unit.lower()]
    if not matches:
        print(
            f"No unit {args.unit!r}. Run `stackchan units` and copy a Device-Id from the list.",
            file=sys.stderr,
        )
        return 2
    if len(matches) > 1:
        print(
            f"More than one unit is called {args.unit!r}. Use its Device-Id (see `stackchan units`).",
            file=sys.stderr,
        )
        return 2
    others = [
        r
        for r in rows
        if r["name"].lower() == args.new_name.strip().lower() and r is not matches[0]
    ]
    if others:
        print(
            f"Another unit is already called {args.new_name!r}. Pick a different name.",
            file=sys.stderr,
        )
        return 2
    try:
        store.update(matches[0]["device_id"], {"name": args.new_name})
    except SettingsError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(f"{matches[0]['device_id']} is now called {args.new_name.strip()}.")
    return 0


def _flash_or_update(args: argparse.Namespace) -> int:
    from maipai_body.bodies.stackchan import updater
    from maipai_body.i18n import normalize, t

    config = load_config()
    lang = normalize(args.lang or config.home.language)
    source = args.source or config.update.source
    key = args.public_key or config.update.trusted_key
    preset = args.preset or config.update.preset
    try:
        folder = updater.read_source(source)
        if folder is None:
            raise updater.UpdateRefused(t(lang, "settings.update.none"))
        release = updater.load_release(folder, public_key=key, preset=preset, lang=lang)
        print(t(lang, "update.ok", version=release.version, preset=release.preset))
        print(release.slot.line(lang))
        if args.command == "flash":
            result = updater.flash(
                release, port=args.port, dry_run=args.dry_run, baud=args.baud, lang=lang
            )
            for note in result.notes:
                print(note)
            if args.dry_run:
                print("esptool " + " ".join(result.command))
            return 0
        return _update_via_host(args, release, lang)
    except updater.UpdateRefused as error:
        print(str(error), file=sys.stderr)
        return 2


def _update_via_host(args: argparse.Namespace, release, lang: str) -> int:
    import urllib.error
    import urllib.request

    from maipai_body.bodies.stackchan import updater
    from maipai_body.i18n import t

    if args.dry_run:
        print(t(lang, "update.dry"))
        return 0
    if not args.unit:
        raise updater.UpdateRefused(
            "Say which unit to update with --unit DEVICE_ID (stackchan status lists them). "
            "Nothing was updated."
        )
    url = f"{args.host_url.rstrip('/')}/api/stackchan/settings/{args.unit}/update"
    request = urllib.request.Request(
        url, data=json.dumps({"lang": lang}).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            print(json.loads(response.read()).get("message", ""))
            return 0
    except urllib.error.HTTPError as error:
        try:
            message = json.loads(error.read()).get("error", "")
        except ValueError:
            message = ""
        raise updater.UpdateRefused(
            message or t(lang, "update.no_host", url=args.host_url)
        ) from error
    except OSError as error:
        raise updater.UpdateRefused(t(lang, "update.no_host", url=args.host_url)) from error


if __name__ == "__main__":
    raise SystemExit(main())


def _reachable(url: str, headers: dict[str, str] | None = None) -> str | None:
    """None when the address answers, else the plain reason it does not."""
    try:
        requests.get(url, headers=headers, timeout=5)
    except requests.RequestException as exc:
        return f"cannot be reached ({type(exc).__name__}); check the address and that the program is running"
    return None


def _check(config) -> int:
    """Test each address in robot.toml and say in plain words what is wrong."""
    from maipai_body.brain.own_llm import _endpoint

    problems = 0
    print(f"Brain: {config.brain}")
    if config.brain == "home":
        print("Home is the brain: Home must be reachable and the robot paired with it.")
        return 0
    llm = config.llm
    if not llm.url:
        print("url: not set. Set url under [llm] in robot.toml to your model's address.")
        return 1
    key_name = llm.api_key_env
    headers = None
    if key_name:
        import os

        value = os.environ.get(key_name)
        if not value:
            print(f"api_key_env: the variable {key_name} is empty. Export it before you run the host.")
            problems += 1
        else:
            headers = {"Authorization": f"Bearer {value}"}
    why = _reachable(_endpoint(llm.url, "/v1/models"), headers)
    print("url: ok" if why is None else f"url: {why}")
    problems += why is not None
    for name, value, folder in (
        ("stt_url", llm.stt_url, llm.stt_model_dir),
        ("tts_url", llm.tts_url, llm.tts_model),
    ):
        if value:
            why = _reachable(value)
            print(f"{name}: ok" if why is None else f"{name}: {why}")
            problems += why is not None
        elif folder:
            print(f"{name}: not set; the built-in engine uses the model you named")
        else:
            print(
                f"{name}: not set and no built-in model named. Set {name} under [llm], or the "
                "built-in model folder, or the robot cannot "
                + ("hear you." if name == "stt_url" else "speak.")
            )
            problems += 1
    return 1 if problems else 0
