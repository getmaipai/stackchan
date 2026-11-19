#!/usr/bin/env python3
"""Intent: run the parity cases (page/py/parity_cases.py) natively: the real ctypes libraries (the core wrappers compiled here with cc), the native renderer programs, the real subprocess.
Writes the results the browser run is compared with. Needs the native renderers (bash scripts/virtual-unit/build-screens.sh) and the replayed firmware tree the wasm build used.
Usage: run_native.py OUT.json [HAL_DIR]       (HAL_DIR default .runs/wasm/fwtree/firmware/main/hal)
Placement: host-side development tool. Upstream: none."""
import ctypes
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE / "page" / "py"))
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
sys.path.insert(0, str(ROOT / "host"))


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: run_native.py OUT.json [HAL_DIR]. Give the file to write the native results to.")
        return 2
    out = Path(sys.argv[1])
    hal = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / ".runs" / "wasm" / "fwtree" / "firmware" / "main" / "hal"
    work = ROOT / ".runs" / "wasm" / "native-cores"
    work.mkdir(parents=True, exist_ok=True)
    sigs_path = ROOT / "docs-site" / "playground" / "wasm" / "cores.sigs.json"
    subprocess.run([sys.executable, "-I", str(HERE / "gen_cores.py"), str(hal), str(work / "cores_gen.c"), str(work / "sigs.json"),
                    "lock", "motion_limit", "listen_guard", "update", "updatehdr", "link_quiet", "remote", "sounds", "hourly", "touch", "reconnect"], check=True, capture_output=True)
    so = work / "cores.so"
    subprocess.run(["cc", "-O1", "-std=c99", "-shared", "-fPIC", "-w", f"-I{hal}", f"-I{HERE}", str(HERE / "cores_all.c"), str(work / "cores_gen.c"), "-o", str(so)], check=True)
    import parity_cases as P

    P.configure(ctypes.CDLL(str(so)), json.loads((work / "sigs.json").read_text()))
    results = {}
    for case in P.all_cases():
        results[case] = P.run(case)
    out.write_text(json.dumps(results, indent=0, sort_keys=True))
    errors = [c for c, r in results.items() if '"error"' in r]
    print(f"native: {len(results)} cases, {len(errors)} with an error text" + (": " + ", ".join(errors[:6]) if errors else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
