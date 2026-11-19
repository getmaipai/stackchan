#!/usr/bin/env python3
"""Intent: pack the virtual unit's Python, unchanged, with the data files it reads and the adapter layer into one zip the page unpacks into Pyodide's file system under /vu
(the folder layout the originals expect: ROOT = /vu, scripts/virtual-unit, schema, host). Nothing is edited; one file is generated: the host's stackchan profile module is
replaced by a two-line module holding LED_CHANNEL_MAX (the real one imports numpy and pydantic, which the page does not ship), the value read from the real file.
Usage: bundle.py REPO_ROOT OUT.zip
Placement: host-side development tool. Upstream: none."""
import re
import sys
import zipfile
from pathlib import Path

VU_FILES = ["vunit.py", "hw.py", "dance_core.py", "dance_sim.py", "scenarios.py", "assets_sim.py", "ed25519_pure.py", "memory_model.py", "host_away.py", "posixtz.py", "view.py", "memory_walk.py",
            "dance/ladder_sim.c", "dance/reconnect_sim.c", "physics/mjcf.py", "physics/imu.py", "physics/robots/stackchan.robot.json", "physics/THIRD-PARTY-physics-engine.json"]
# Files the virtual unit gained later (the power model hw.py imports, the offline mumble tools/mumble_sim.py imports): packed when they exist, so this build works on a tree
# without them and on one with them. A module the unit imports that is in neither list is a missing-file error in the page: add it here.
OPTIONAL_VU_FILES = ["power_model.py", "mumble.py"]
HOST_FILES = ["maipai_body/__init__.py", "maipai_body/bodies/__init__.py", "maipai_body/bodies/stackchan/dance.py", "maipai_body/hal/errors.py", "maipai_body/unit_tools.py",
              "maipai_body/bodies/stackchan/dance_ladder.py"]


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: bundle.py REPO_ROOT OUT.zip. Give the repository folder and the zip to write.")
        return 2
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    vu = root / "scripts" / "virtual-unit"
    here = Path(__file__).resolve().parent / "page" / "py"
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        def add(src: Path, name: str) -> None:
            nonlocal count
            if not src.exists():
                raise SystemExit(f"bundle.py: {src} is missing. The virtual unit moved a file: update VU_FILES or HOST_FILES in scripts/virtual-unit/wasm/bundle.py.")
            z.write(src, "vu/" + name)
            count += 1
        for f in VU_FILES:
            add(vu / f, "scripts/virtual-unit/" + f)
        for f in OPTIONAL_VU_FILES:
            if (vu / f).exists():
                add(vu / f, "scripts/virtual-unit/" + f)
        for f in sorted((vu / "tools").glob("*.py")):
            add(f, "scripts/virtual-unit/tools/" + f.name)
        for f in sorted((root / "schema").glob("*.json")):
            add(f, "schema/" + f.name)
        add(root / "docs" / "legal" / "affiliation.json", "docs/legal/affiliation.json")
        for f in HOST_FILES:
            add(root / "host" / f, "host/" + f)
        add(vu / "model" / "stackchan.params.json", "scripts/virtual-unit/model/stackchan.params.json") if (vu / "model" / "stackchan.params.json").exists() else None
        for f in ("wasm_shim.py", "api.py", "parity_cases.py"):
            add(here / f, "site/" + f)
        prof = (root / "host" / "maipai_body" / "bodies" / "stackchan" / "profile.py").read_text()
        m = re.search(r"^LED_CHANNEL_MAX\s*=\s*(\d+)", prof, re.M)
        if not m:
            raise SystemExit("bundle.py: LED_CHANNEL_MAX is not in host/maipai_body/bodies/stackchan/profile.py. The profile changed: update scripts/virtual-unit/wasm/bundle.py.")
        z.writestr("vu/host/maipai_body/bodies/stackchan/profile.py", f'"""Browser build stand-in: only the constant the dance modules read (the real profile needs numpy and pydantic)."""\nLED_CHANNEL_MAX = {m.group(1)}\n')
        z.writestr("vu/host/maipai_body/hal/__init__.py", "")
        z.writestr("vu/host/maipai_body/bodies/stackchan/__init__.py", '"""Browser build stand-in: the real package file imports the hardware adapter (numpy, pydantic, serial); the dance modules need none of it."""\n')
    print(f"bundle: {count + 2} files, {out.stat().st_size} bytes -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
