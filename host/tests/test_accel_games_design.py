"""The draft analog tilt core of docs/design/accelerometer-games.md, section 5: the C block is extracted from the page and compiled against a test program, so the spec firmware gets is checked code,
and the budget table of the page is the output of scripts/virtual-unit/tilt_games_budget.py."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "design" / "accelerometer-games.md"

TEST = r"""
#include <stdio.h>
#include <math.h>
#include "core.h"
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); return 1; } } while (0)
static void feed(mga_t* a, float x, float y, float z, const float rest[3], int n, int quiet) { for (int i = 0; i < n; i++) mga_update(a, x, y, z, rest, quiet); }
int main(void)
{
    const float rest[3] = {0.0f, 9.80665f, 0.0f};
    mga_t a = {0};
    feed(&a, 0.0f, 9.80665f, 0.0f, rest, 20, 0);
    CHECK(a.valid && a.roll_pm == 0 && a.pitch_pm == 0);                                       /* still: flat */
    feed(&a, 0.05f * 9.80665f, 9.8f, 0.0f, rest, 40, 0);
    CHECK(a.valid && a.roll_pm == 0);                                                           /* under the dead zone: flat */
    mga_t b = {0};
    feed(&b, 0.30f * 9.80665f, sqrtf(9.80665f * 9.80665f - (0.30f * 9.80665f) * (0.30f * 9.80665f)), 0.0f, rest, 60, 0);
    CHECK(b.valid && b.roll_pm > 450 && b.roll_pm < 550);                                       /* 0.30 g: (0.30-0.10)/(0.50-0.10) = half scale */
    CHECK(b.pitch_pm == 0);
    mga_t c = {0};
    feed(&c, -0.45f * 9.80665f, 8.7f, 0.0f, rest, 60, 0);
    CHECK(c.roll_pm < -800);                                                                    /* a roll to the left reads negative */
    mga_t d = {0};
    feed(&d, 0.0f, 8.8f, -0.45f * 9.80665f, rest, 60, 0);
    CHECK(d.pitch_pm > 800 && d.roll_pm == 0);                                                  /* forward is toward -z and reads positive */
    mga_t e = {0};
    feed(&e, 0.0f, 9.80665f, 0.9f * 9.80665f, rest, 60, 0);
    CHECK(e.pitch_pm == -1000 || e.pitch_pm < -900 || !e.valid);                                /* far past full scale clamps (or the length leaves the window) */
    mga_t f = {0};
    feed(&f, 0.0f, 18.0f, 0.0f, rest, 40, 0);
    CHECK(!f.valid && f.roll_pm == 0 && f.pitch_pm == 0);                                       /* the pull is far from one g: carried or shaken, no reading */
    mga_t g2 = {0};
    feed(&g2, 0.4f * 9.80665f, 8.9f, 0.0f, rest, 40, 1);
    CHECK(!g2.valid && g2.roll_pm == 0);                                                        /* the quiet time after a shake: no reading */
    mga_t h = {0};
    feed(&h, 0.0f, 9.80665f, 0.0f, rest, 20, 0);
    mga_update(&h, 0.6f * 9.80665f, 7.8f, 0.0f, rest, 0);
    CHECK(h.roll_pm < 700);                                                                     /* one sample does not jump to the end: the filter smooths it */
    puts("accel_games_design_core: all passed");
    return 0;
}
"""


def _block():
    text = PAGE.read_text()
    return re.search(r"```c\n(.*?)```", text, re.S).group(1)


@pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")
def test_the_drafted_core_compiles_and_holds_its_properties(tmp_path):
    (tmp_path / "core.h").write_text(_block())
    (tmp_path / "t.c").write_text(TEST)
    build = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", str(tmp_path / "t.c"), "-o", str(tmp_path / "t"), "-lm"], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(tmp_path / "t")], capture_output=True, text=True, timeout=30)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


def test_the_budget_table_of_the_page_is_what_the_script_prints():
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "virtual-unit" / "tilt_games_budget.py")], capture_output=True, text=True, check=True).stdout.strip()
    assert out in PAGE.read_text(), "the table in docs/design/accelerometer-games.md is out of date: run scripts/virtual-unit/tilt_games_budget.py and paste its table"
