"""Host setup and status commands."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore, default_pairing_path
from maipai_body.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(prog="stackchan")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pair", help="show a one-use pairing code")
    commands.add_parser("status", help="show the brain and paired units")
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
    analyse = commands.add_parser("bench-analyse", help="analyse a 48 kHz recording")
    analyse.add_argument("recording")
    analyse.add_argument(
        "--question-end",
        type=float,
        default=0.0,
        help="question end offset in seconds from recording start",
    )
    frames = commands.add_parser("bench-frames", help="analyse frame timestamps")
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
    if args.command in {"flash", "update"}:
        return _flash_or_update(args)
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
    if args.command == "bench-analyse":
        from maipai_body.measure.bench import analyse_recording

        print(
            json.dumps(
                analyse_recording(args.recording, question_end_s=args.question_end), indent=2
            )
        )
        return 0
    if args.command == "bench-frames":
        from maipai_body.measure.bench import analyse_frames

        print(json.dumps(analyse_frames(args.frametimes), indent=2))
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
    config = load_config()
    store = PairingStore(default_pairing_path())
    if args.command == "pair":
        print(f"Pairing code: {store.create_pair_code()}")
        print("Enter this code on the unit setup page within 10 minutes.")
        return 0
    print(f"Brain: {config.brain}")
    devices = store.paired_devices()
    print(f"Paired units: {len(devices)}")
    for device_id, record in sorted(devices.items()):
        seen = record.get("last_seen")
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(seen))) if seen else "never"
        print(f"{device_id}: last seen {when}")
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
