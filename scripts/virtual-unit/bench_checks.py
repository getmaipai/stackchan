#!/usr/bin/env python3
"""Virtual dry runs of the three bench checks (plan section 9), so the bench agent knows the steps and the expected readings before a window.
Usage: bench_checks.py [--report]   runs the three scenarios; --report prints a markdown report. Exit 1 when a scenario does not give its expected reading.
Each scenario is labeled by what it proves: "rule" (the unit's own C rule, compiled here), "model" (a small copy of the patch text's logic),
"screen" (the unit's own drawing code). None of them proves what the unit does: the last line of each says what only the unit can show.
Placement: host-side development tool. Upstream: none."""
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("vunit", HERE / "vunit.py")
vunit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vunit)
sys.path.insert(0, str(HERE))


def patch_file(patch: str, path: str) -> str:
    """The text of a file a patch adds, read from the patch itself."""
    t = (ROOT / "firmware" / "patches" / patch).read_text()
    a = t.index(f"+++ b/{path}")
    out = []
    for line in t[a:].splitlines()[2:]:
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def update_trial():
    """Check 2: a wirelessly installed image is kept after 20 s with the host, 60 s without it, and rolled back at 120 s when the loop is dead."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "maipai_update_core.h").write_text(patch_file("FM01-first-boot-trial.patch", "firmware/main/hal/maipai_update_core.h"))
        exe = Path(tmp) / "trial"
        subprocess.run(["cc", "-std=c99", "-Wall", "-Werror", f"-I{tmp}", str(HERE / "update_trial.c"), "-o", str(exe)], check=True, capture_output=True)
        def run(host, cam, alive):
            return subprocess.run([str(exe), str(host), str(cam), str(alive), "200"], capture_output=True, text=True).stdout.strip()
        rows = [("host answers", run(1, 2, 1), "KEEP_HOST at 20"), ("host off", run(0, 2, 1), "KEEP_QUIET at 60"),
                ("main loop dead", run(1, 2, 0), "ROLLBACK at 120"), ("camera never settles", run(1, -1, 1), "ROLLBACK at 120")]
    return {"title": "A wireless update is confirmed (FM01)", "kind": "rule", "rows": rows,
            "unit_only": "that the unit's own timer calls the rule once a second, saves the record, and that the base boot loader does not roll back first: read the log for 'on trial' then 'keeping it'."}


def listen_cut():
    """Check 3: the listening guard (patches L03 and SF03) ends Listening after 8 s with no voice, and never later than 60 s after the entry."""
    pats = ROOT / "firmware" / "patches"
    follow = int(re.search(r"kFollowUpListenSeconds = (\d+);", (pats / "L03-followup-window-8s.patch").read_text()).group(1))
    cap = int(re.search(r"kListenCapSeconds = (\d+);", (pats / "SF03-listening-guard-follows-voice.patch").read_text()).group(1))
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "maipai_listen_guard_core.h").write_text(patch_file("SF03-listening-guard-follows-voice.patch", "firmware/main/hal/maipai_listen_guard_core.h"))
        exe = Path(tmp) / "guard"
        subprocess.run(["cc", "-std=c99", "-Wall", "-Werror", f"-I{tmp}", str(HERE / "listen_guard.c"), "-o", str(exe)], check=True, capture_output=True)
        def run(frm, until):
            return subprocess.run([str(exe), str(follow), str(cap), str(frm), str(until)], capture_output=True, text=True).stdout.strip()
        rows = [("no one speaks after wake", run(0, 0), "ends at 8"), ("a 12 s sentence from 1 s to 13 s", run(1, 13), "ends at 21"),
                ("speech that never stops", run(1, 200), f"ends at {cap}")]
    return {"title": "A long sentence after wake (SF03)", "kind": "rule", "rows": rows,
            "unit_only": "that the unit feeds the rule real voice detection every second and the host still gets the whole sentence: say a 12 s sentence after the wake word, read the log for no 'State guard returning listening to idle' until 8 s after the last word, and that the reply starts (fw-voice-bench.py ROUNDS --gate)."}


def wifi_setup():
    """Check 1: no saved network: the unit shows the Wi-Fi setup screen with the hotspot name and address."""
    with vunit.VirtualUnit() as u:
        u.state.setdefault("network", {})["wifi"] = [{"ssid": "Home", "password": "x"}]
        before = len(u.call("self.wifi.list_saved")["result"])
        wiped = u.call("self.wifi.forget", {"index": 0})  # a user-only tool: hidden from the model, answers a call by name
        saved = u.call("self.wifi.list_saved")["result"]
        listed = [t["name"] for t in u.tools_list(for_model=True)]
    rows = [("a saved network exists before the wipe", f"{before}", "1"), ("self.wifi.forget answers", str(wiped.get("ok")), "True"),
            ("saved networks after the wipe", f"{len(saved)}", "0"), ("the model's tool list hides self.wifi.forget", str("self.wifi.forget" not in listed), "True")]
    golden = ROOT / "host" / "tests" / "golden" / "screens" / "cover-wifi-setup.png"
    rows.append(("setup screen frame exists (drawn by the unit's own cover code)", str(golden.exists()), "True"))
    return {"title": "Wi-Fi setup with no saved network", "kind": "screen", "rows": rows,
            "unit_only": "whether the unit really reaches the setup branch with no saved network and shows the hotspot name and address (the review says the branch may never be reached): wipe Wi-Fi with self.wifi.forget, reboot, snapshot the screen, compare with cover-wifi-setup.png."}


def main():
    checks = [wifi_setup(), update_trial(), listen_cut()]
    bad = 0
    out = ["# Bench checks: virtual dry run", ""]
    for c in checks:
        out.append(f"## {c['title']} ({c['kind']})")
        for what, got, want in c["rows"]:
            ok = str(got) == want
            bad += not ok
            out.append(f"- {'ok' if ok else 'WRONG'}: {what}: got {got}, expected {want}")
        out += [f"- only the unit can show: {c['unit_only']}", ""]
    text = "\n".join(out)
    print(text if "--report" in sys.argv else f"{len(checks)} bench checks dry-run, {bad} readings off")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
