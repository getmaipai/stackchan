"""Host setup and status commands."""

from __future__ import annotations

import argparse
import time

from maipai_body.bodies.stackchan.xiaozhi.pairing import PairingStore, default_pairing_path
from maipai_body.config import load_config


def main() -> int:
    parser = argparse.ArgumentParser(prog="stackchan")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("pair", help="show a one-use pairing code")
    commands.add_parser("status", help="show the brain and paired units")
    args = parser.parse_args()
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


if __name__ == "__main__":
    raise SystemExit(main())
