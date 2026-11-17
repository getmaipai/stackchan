# ruff: noqa: E501
"""The roaming, private-network and setup-page patches of 2026-11-17 (RM01 to RM07): they are on ORDER in sequence with their
header lines, the plain-C rules compile and pass against the headers as the whole ORDER leaves them, the setup hotspot is
named stackchan-XXXX, the setup page stays open for several networks within its size budget, and no patch carries a key."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from firmware_order_cores import cores_dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATCHES = ROOT / "firmware" / "patches"
NAMES = [
    "RM01-wifi-roam-weak-signal-scan.patch",
    "RM02-wifi-roam-move-to-stronger-ap.patch",
    "RM03-travel-guard-no-saved-off.patch",
    "RM04-travel-follow-hub-relay-region.patch",
    "RM05-travel-prefer-private-route-hook.patch",
    "RM06-setup-hotspot-named-stackchan.patch",
    "RM07-setup-page-stays-open-for-several-networks.patch",
]


def _text(name: str) -> str:
    return (PATCHES / name).read_text()


def _order() -> list[str]:
    return [n.strip() for n in (PATCHES / "ORDER").read_text().splitlines() if n.strip() and not n.startswith("#")]


def test_listed_in_order_in_sequence_and_documented():
    order = _order()
    assert [n for n in order if n.startswith("RM")] == NAMES
    positions = [order.index(n) for n in NAMES]
    assert positions == sorted(positions)
    assert order.index("TN07-travel-review-fixes.patch") < positions[0]
    for name in NAMES:
        head = _text(name).split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement:", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)


def test_no_patch_carries_a_key_an_em_dash_or_a_real_address():
    for name in NAMES + ["../tailnet/microlink-region.patch"]:
        text = _text(name)
        assert re.search(r"tskey-[A-Za-z0-9_]{8,}", text) is None, name
        ours = [line for line in text.splitlines() if line.startswith(("+", "#"))]  # context lines are the vendor's own text
        assert not any(chr(0x2014) in line for line in ours), name


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
@pytest.mark.parametrize("test", ["roam_core_test.c", "tailnet_region_test.c", "tailnet_travel_test.c"])
def test_the_core_tests_pass_against_the_cores_the_whole_order_leaves(tmp_path, tmp_path_factory, test):
    hal = cores_dir(tmp_path_factory)
    binary = tmp_path / "t"
    build = subprocess.run(
        ["cc", "-std=c99", "-D_DEFAULT_SOURCE", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / test), "-o", str(binary)],
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0 and "passed" in run.stdout, run.stdout + run.stderr


def _portal(tmp_path_factory) -> Path:
    """The portal headers as the whole ORDER leaves them."""
    work = tmp_path_factory.mktemp("portal_order")
    for name in _order():
        text = (PATCHES / name).read_text()
        diff = work / "p.diff"
        diff.write_text(text[text.index("diff --git") :])
        run = subprocess.run(
            ["git", "apply", "--include=firmware/portal/*.h", str(diff)], cwd=work, capture_output=True, text=True
        )
        assert run.returncode == 0, f"{name}: {run.stderr}"
    return work / "firmware" / "portal"


@pytest.mark.skipif(shutil.which("c++") is None or shutil.which("git") is None, reason="no C++ compiler or git")
def test_the_hotspot_is_named_stackchan_and_the_page_fits_in_both_languages(tmp_path, tmp_path_factory):
    portal = _portal(tmp_path_factory)
    src = tmp_path / "t.cc"  # the page is a C++ raw string
    src.write_text(
        r'''
#include <stdio.h>
#include <string.h>
#include "maipai_portal_core.h"
#include "maipai_portal_page.h"
int main(void) {
    char s[40];
    mp_ssid(s, sizeof(s), 0x0a, 0xB3);
    if (strcmp(s, "stackchan-0AB3") != 0) { printf("FAIL name %s\n", s); return 1; }
    mp_ssid(s, sizeof(s), 0xff, 0x01);
    if (strcmp(s, "stackchan-FF01") != 0 || strlen(s) > 32) { printf("FAIL name2 %s\n", s); return 1; }
    for (int lang = 0; lang < 2; lang++) {
        size_t total = strlen(mp_page);
        for (int i = 0; i < MP_S_COUNT; i++) {
            const char* t = mp_str(lang, i);
            if (t == NULL || t[0] == 0) { printf("FAIL empty string %d lang %d\n", i, lang); return 1; }
            total += strlen(t) + 4;
        }
        if (total > 6 * 1024) { printf("FAIL page too big %zu lang %d\n", total, lang); return 1; }
        if (strstr(mp_str(lang, MP_S_OK), "Finish") == NULL && strstr(mp_str(lang, MP_S_OK), "Terminar") == NULL) {
            printf("FAIL the saved line does not point to Finish in lang %d\n", lang); return 1;
        }
    }
    if (strstr(mp_page, "id=d") == NULL || strstr(mp_page, "finish:true") == NULL) { printf("FAIL no finish button\n"); return 1; }
    printf("all passed\n");
    return 0;
}
'''
    )
    binary = tmp_path / "t"
    build = subprocess.run(
        ["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", f"-I{portal}", str(src), "-o", str(binary)], capture_output=True, text=True
    )
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_roam_wiring_keeps_its_rules():
    runtime = _text(NAMES[0])
    assert "esp_nvs" not in runtime and "nvs_" not in runtime  # no flash and no NVS on the timer task
    assert "kDeviceStateIdle" in runtime  # no scan while a turn is going on
    block = _text(NAMES[1])
    assert "mr_pick(" in block and "esp_wifi_disconnect();" in block
    assert "remember_bssid_ = 0;" in block  # a pin saved by the old firmware is ignored
    assert "FATAL_ERROR" in block  # a changed vendor file stops the configure
    assert "microlink_set_home_derp_region" in _text(NAMES[3])
    removed = [line for line in _text(NAMES[2]).splitlines() if line.startswith("-") and not line.startswith("---")]
    assert any("save_u8(kKeyOn, 0);" in line for line in removed)  # the guard no longer saves "off"
