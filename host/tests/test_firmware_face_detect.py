# ruff: noqa: E501
"""On-unit face detection with Espressif's ESP-DL (firmware patches FD01 to FD04, experiment image only).

The pure parts (the camera window to RGB conversion, the face pick, the percentile ring, the tracker's control loop) are plain C: compile each host test against the
headers as the whole of ORDER leaves them and run it, then check the C against a second implementation written here in Python (the conversion, the percentile, the
tracker's first move) so a slip in either shows. The device parts are C++ for the unit, so the tests read the patches for the rules that matter (off by default,
nothing that touches flash on the PSRAM-stack task, the camera cue before every frame, every gate, the lease wins) the way the other firmware tests do."""

from __future__ import annotations

import random
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
    "FD01-face-detect-build-switch-and-components.patch",
    "FD02-face-detect-task-and-camera-window.patch",
    "FD03-face-detect-bench-tools.patch",
    "FD04-face-track-control-loop-and-seek-hook.patch",
]
needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="no C compiler on this machine")


def _added(name: str, path: str) -> str:
    """The lines a patch adds to one file."""
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith("+"):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def _after(name: str, path: str) -> str:
    """The file as the patch leaves it where it shows it: added lines and unchanged context lines."""
    text = (PATCHES / name).read_text()
    block = text.split(f"+++ b/{path}\n", 1)[1].split("\n", 1)[1]
    out = []
    for line in block.splitlines():
        if line.startswith("diff --git"):
            break
        if line.startswith(("+", " ")):
            out.append(line[1:])
    return "\n".join(out) + "\n"


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _build(tmp_path: Path, hal: Path, source: str, *extra: str) -> Path:
    binary = tmp_path / source.replace(".c", "")
    run = subprocess.run(
        ["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{hal}", str(HERE / "firmware" / source), "-o", str(binary), *extra, "-lm"],
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    return binary


@needs_cc
@pytest.mark.parametrize("source", ["facedet_core_test.c", "face_track_core_test.c"])
def test_the_c_tests_pass(tmp_path, tmp_path_factory, source):
    binary = _build(tmp_path, cores_dir(tmp_path_factory), source)
    run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=300)
    assert run.returncode == 0 and "all passed" in run.stdout, run.stdout + run.stderr


# ---- parity: the C against a Python version of the same maths ----------------------------------------------------------------------------------------

DRIVER = r"""
#include <stdio.h>
#include <stdlib.h>
#include "maipai_facedet_core.h"
#include "maipai_face_track_core.h"
/* convert W H FMT X0 Y0 CW CH SWAP < raw frame  -> RGB bytes as hex */
static int convert(char** a)
{
    int w = atoi(a[0]), h = atoi(a[1]), fmt = atoi(a[2]), x0 = atoi(a[3]), y0 = atoi(a[4]), cw = atoi(a[5]), ch = atoi(a[6]), sw = atoi(a[7]);
    size_t n = (size_t)w * h * mw_bpp(fmt);
    uint8_t* f = malloc(n);
    if (fread(f, 1, n, stdin) != n) return 2;
    uint8_t* o = malloc((size_t)cw * ch * 3);
    int rc = fd_convert_rgb888(f, n, w, h, fmt, x0, y0, cw, ch, o, sw);
    if (rc) { printf("ERR %d\n", rc); return 0; }
    for (size_t i = 0; i < (size_t)cw * ch * 3; i++) printf("%02x", o[i]);
    printf("\n");
    return 0;
}
/* pct v1 v2 ...  */
static int pct(char** a, int n)
{
    fd_ring_t r;
    fd_ring_clear(&r);
    for (int i = 0; i < n; i++) fd_ring_add(&r, (uint32_t)atoi(a[i]));
    printf("%u %u %u\n", fd_percentile(&r, 50), fd_percentile(&r, 95), fd_percentile(&r, 99));
    return 0;
}
/* first CX PAN XSIGN : two start detections at the middle, then detections at CX (picture taken at PAN with the head still): prints the first move's pan target */
static int first(char** a)
{
    float cx = (float)atof(a[0]), pan = (float)atof(a[1]), xs = (float)atof(a[2]);
    ft_cfg_t c = {0};
    c.x_sign = xs; c.fov_h_deg = 52.0f; c.y_sign = -1.0f; c.hour_ms = 600000u;
    ft_t t; ft_init(&t, &c);
    ft_in_t in = {0};
    in.armed = 1; in.gates_ok = 1; in.mode = FT_MODE_TALK; in.conversation = 1; in.head_settled = 1; in.pan_deg = pan;
    ft_out_t o;
    uint32_t now = 1000;
    for (int k = 0; k < 2; k++) {
        in.now_ms = now; in.face_seq++; in.face_valid = 1; in.face_cx = cx; in.face_cy = 120; in.face_score = 0.9f; in.face_at_ms = now - 200;
        ft_hist_add(&t, now - 200, pan, 0);
        ft_tick(&t, &in, &o);
        now += 700;
    }
    for (int k = 0; k < 6; k++) {
        in.now_ms = now; in.face_seq++; in.face_valid = 1; in.face_cx = cx; in.face_cy = 120; in.face_score = 0.9f; in.face_at_ms = now - 200;
        ft_hist_add(&t, now - 200, pan, 0);
        ft_tick(&t, &in, &o);
        if (o.move) { printf("%.4f\n", o.pan_deg); return 0; }
        now += 700;
    }
    printf("none\n");
    return 0;
}
int main(int argc, char** argv)
{
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "convert")) return convert(argv + 2);
    if (!strcmp(argv[1], "pct")) return pct(argv + 2, argc - 2);
    if (!strcmp(argv[1], "first")) return first(argv + 2);
    return 2;
}
"""


@pytest.fixture(scope="module")
def driver(tmp_path_factory):
    if shutil.which("cc") is None:
        pytest.skip("no C compiler on this machine")
    work = tmp_path_factory.mktemp("fddriver")
    (work / "driver.c").write_text(DRIVER)
    binary = work / "driver"
    run = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", f"-I{cores_dir(tmp_path_factory)}", str(work / "driver.c"), "-o", str(binary), "-lm"], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    return binary


def _clamp8(v: int) -> int:
    return max(0, min(255, v))


def _yuv(y: int, u: int, v: int) -> tuple[int, int, int]:
    c, d, e = (y - 16) * 298, u - 128, v - 128
    return _clamp8((c + 409 * e + 128) >> 8), _clamp8((c - 100 * d - 208 * e + 128) >> 8), _clamp8((c + 516 * d + 128) >> 8)


def _convert_py(frame: bytes, w: int, fmt: int, x0: int, y0: int, cw: int, ch: int, swap: int) -> str:
    out = []
    for j in range(ch):
        for i in range(cw):
            x, y = x0 + i, y0 + j
            if fmt == 3:  # RGB565 little endian
                v = frame[(y * w + x) * 2] | (frame[(y * w + x) * 2 + 1] << 8)
                r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
                rgb = ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))
            elif fmt == 4:
                p = frame[y * w + x]
                rgb = (p, p, p)
            else:
                base = (y * w + (x & ~1)) * 2
                q = frame[base : base + 4]
                if fmt == 1:  # YUYV
                    yy, u, v = q[2 if x & 1 else 0], q[1], q[3]
                else:  # UYVY
                    yy, u, v = q[3 if x & 1 else 1], q[0], q[2]
                rgb = _yuv(yy, u, v)
            out.extend(reversed(rgb) if swap else rgb)
    return bytes(out).hex()


@needs_cc
@pytest.mark.parametrize("fmt", [1, 2, 3, 4])
def test_the_conversion_matches_a_python_version_on_random_frames(driver, fmt):
    rng = random.Random(40 + fmt)
    w, h = 32, 12
    bpp = 1 if fmt == 4 else 2
    for _ in range(4):
        frame = bytes(rng.randrange(256) for _ in range(w * h * bpp))
        x0, y0, cw, ch = rng.randrange(0, 8) * 2, rng.randrange(0, 4), rng.randrange(1, 16), rng.randrange(1, 8)
        for swap in (0, 1):
            run = subprocess.run([str(driver), "convert", str(w), str(h), str(fmt), str(x0), str(y0), str(cw), str(ch), str(swap)], input=frame, capture_output=True)
            assert run.stdout.decode().strip() == _convert_py(frame, w, fmt, x0, y0, cw, ch, swap)


@needs_cc
def test_the_percentile_is_nearest_rank_like_numpys_inverted_cdf(driver):
    rng = random.Random(7)
    for n in (1, 2, 9, 50, 100, 255):
        vals = [rng.randrange(50, 900) for _ in range(n)]
        run = subprocess.run([str(driver), "pct", *map(str, vals)], capture_output=True, text=True)
        got = [int(x) for x in run.stdout.split()]
        s = sorted(vals)
        want = [s[max(1, -(-p * n // 100)) - 1] for p in (50, 95, 99)]
        assert got == want


@needs_cc
@pytest.mark.parametrize("xsign", [1.0, -1.0])
def test_the_trackers_first_move_matches_the_formula(driver, xsign):
    """A still box at cx and a still head at pan: the error is (cx / 320 - 0.5) * 52 * x_sign, the step is Kp 0.6 times it capped at 12 degrees, and the target
    is the angle at the picture's time plus the step (clamped to the pan limit). A box inside the 4 degree band never moves it."""
    for cx in (100.0, 140.0, 190.0, 230.0, 290.0):
        for pan in (-30.0, 0.0, 12.0, 40.0):
            run = subprocess.run([str(driver), "first", str(cx), str(pan), str(xsign)], capture_output=True, text=True)
            err = (cx / 320.0 - 0.5) * 52.0 * xsign
            if abs(err) < 4.0:
                assert run.stdout.strip() == "none"
                continue
            want = max(-80.0, min(80.0, pan + max(-12.0, min(12.0, 0.6 * err))))
            assert run.stdout.strip() != "none"
            assert float(run.stdout) == pytest.approx(want, abs=0.01)


# ---- the patches ------------------------------------------------------------------------------------------------------------------------------------


def _order() -> list[str]:
    return [n for n in (PATCHES / "ORDER").read_text().split() if not n.startswith("#")]


def test_the_patches_are_on_order_in_sequence_after_the_seek_and_ui_patches_and_carry_their_header_lines():
    order = _order()
    assert all(n in order for n in NAMES)
    idx = [order.index(n) for n in NAMES]
    assert idx == sorted(idx) and idx[-1] - idx[0] == 3  # one block, in order
    assert idx[0] > order.index("UI15-magic-8-ball-dice-and-gentle-shake.patch") and idx[0] > order.index("S14-seek-task-tools-and-setting.patch")
    for name in NAMES:
        text = (PATCHES / name).read_text()
        head = text.split("diff --git", 1)[0]
        for key in ("# Intent:", "# Placement: unit", "# Upstream:", "# Check after a flash:"):
            assert key in head, (name, key)
        assert chr(8212) not in text, name


def test_the_switch_is_off_by_default_and_the_reserved_error_is_gone():
    kconfig = _after(NAMES[0], "firmware/main/Kconfig.projbuild")
    assert re.search(r'config MAIPAI_FACE_DETECT\n\s+bool "Experiment build only[^\n]*\n\s+default n', kconfig)
    assert re.search(r"config MAIPAI_FACE_TRACK\n\s+bool .*\n\s+default n", kconfig)  # the tracker is compiled in only on a second switch
    assert re.search(r"config MAIPAI_FACE_TRACK_TILT\n\s+bool .*\n[\s\S]*?default n", kconfig)
    assert "config MAIPAI_FACE_DETECT_RATE_HZ" in kconfig and "range 2 5" in kconfig
    text = (PATCHES / NAMES[0]).read_text()
    assert "-#error" in text and "MAIPAI_FACE_DETECT is reserved" in text  # the S14 reservation is removed, not added
    assert "+#error" not in text


def test_the_components_are_pinned_exactly_and_only_in_the_experiment_build():
    manifest = _added(NAMES[0], "firmware/main/idf_component.yml")
    assert 'version: "==3.3.15"' in manifest and 'version: "==0.5.2"' in manifest
    assert manifest.count('$CONFIG{MAIPAI_FACE_DETECT} == True') >= 3  # esp-dl, the model package and the jpeg version for it
    assert '"^0.6.1"' in manifest and '$CONFIG{MAIPAI_FACE_DETECT} == False' in manifest  # the plain image keeps its old jpeg library
    cmake = _added(NAMES[0], "firmware/main/CMakeLists.txt")
    assert "if(CONFIG_MAIPAI_FACE_DETECT)" in cmake and "idf_component_optional_requires(PRIVATE espressif__esp-dl espressif__human_face_detect)" in cmake
    overlay = _added(NAMES[0], "firmware/sdkconfig.fdetect.defaults")
    for key in ("CONFIG_MAIPAI_FACE_DETECT=y", "CONFIG_FLASH_HUMAN_FACE_DETECT_MSRMNP_S8_V1=y", "CONFIG_FLASH_ESPDET_PICO_224_224_FACE=y", "CONFIG_HUMAN_FACE_DETECT_MODEL_IN_FLASH_RODATA=y"):
        assert key in overlay
    assert "FLASH_PARTITION" not in overlay  # the model is read in place from the app image, no partition


def test_the_pure_parts_have_no_hardware_call():
    for name, path in ((NAMES[1], "firmware/main/hal/maipai_facedet_core.h"), (NAMES[3], "firmware/main/hal/maipai_face_track_core.h")):
        code = _code(_added(name, path))
        assert not re.search(r"\b(esp_|heap_caps|xTask|vTask|gpio_|i2s_|xSemaphore|malloc|calloc|nvs_|Settings)\b", code), path


def test_the_detector_task_is_low_priority_with_a_psram_stack_and_touches_no_flash():
    text = _added(NAMES[1], "firmware/main/hal/maipai_facedet.cc")
    code = _code(text)
    create = re.search(r"xTaskCreatePinnedToCoreWithCaps\(fd_task, \"facedet\", kStackBytes, nullptr, (\d+), &s_task, (\d+), MALLOC_CAP_SPIRAM\)", code)
    assert create is not None and (int(create.group(1)), int(create.group(2))) == (1, 0)
    assert re.search(r"kStackBytes\s*=\s*(\d+)", code) and int(re.search(r"kStackBytes\s*=\s*(\d+)", code).group(1)) <= 16384
    assert not re.search(r"\b(nvs_|Settings\b|esp_flash_|spi_flash_|esp_partition_|esp_ota_|maipai_tb_prefs)", code)
    assert "MALLOC_CAP_SPIRAM" in code and "max_internal" not in code or "max_internal_size" in text  # weights and activations: the library default is PSRAM first
    assert "delete s_det" in code and "kUnloadMs" in code  # lazy load, freed after the idle time
    assert "CONFIG_MAIPAI_FACE_DETECT_MIN_FREE_INTERNAL" in code and "CONFIG_MAIPAI_FACE_DETECT_MIN_BLOCK_INTERNAL" in code  # admission before a load
    assert "profile_memory()" in code
    assert "HumanFaceDetect::MSRMNP_S8_V1" in code and "ESPDET_PICO_224_224_FACE" in code and "FD_CROP_FOLLOW" in code
    assert "kRgbBytes" in code and "s_rgb = static_cast<uint8_t*>(heap_caps_malloc(kRgbBytes, MALLOC_CAP_SPIRAM" in code  # the window is PSRAM


def test_the_camera_cue_is_asked_before_every_frame_and_vision_off_stops_the_read():
    code = _code(_added(NAMES[1], "firmware/main/hal/maipai_facedet.cc"))
    body = code.split("void detect_one(", 1)[1].split("\nvoid publish(", 1)[0]
    assert body.index("monitor_cue_begin") < body.index("DetectGrab")  # the cue first, every frame, test or stream
    cam = _added(NAMES[1], "firmware/main/hal/board/stackchan_camera.cc")
    assert "if (maipai_vision_off())" in cam.split("DetectGrab", 1)[1]
    assert "#if defined(CONFIG_MAIPAI_FACE_DETECT)" in cam  # no code in the plain image
    assert "heap_caps_free(frame_.data)" in cam  # the frame copy is not kept
    assert "maipai_muted() || maipai_quiet() || maipai_vision_off()" in code  # the stream and the test stop for these


def test_the_stream_runs_only_while_a_caller_keeps_asking():
    code = _code(_added(NAMES[1], "firmware/main/hal/maipai_facedet.cc"))
    assert "s_want_until" in code and "static_cast<int32_t>(s_want_until.load() - t) > 0" in code
    seek = _code(_added(NAMES[3], "firmware/main/hal/maipai_seek.cc")) if "maipai_seek.cc" in (PATCHES / NAMES[3]).read_text() else ""
    assert "maipai_fd_want(600, FD_CROP_FOLLOW)" in seek  # renewed every pass: it stops within 600 ms


def test_the_tools_and_their_numbers_are_there_and_refuse_when_they_must():
    code = _code(_added(NAMES[2], "firmware/main/hal/maipai_facedet_tools.cc"))
    for tool in ("self.look.detect_test", "self.look.detect_status"):
        assert tool in code
    for field in ('\\"ms\\":{\\"grab\\":[%u,%u],\\"conv\\":[%u,%u],\\"infer\\":[%u,%u],\\"total\\":[%u,%u]', "during_min", "int_low_water", "loaded_before", "score_best_pct", "faces", "fmt"):
        assert field in code, field
    for refusal in ("kDeviceStateIdle", "maipai_muted()", "maipai_quiet()", "maipai_vision_off()", "model must be msrmnp or pico224"):
        assert refusal in code
    assert "%f" not in code and "%.2f" not in code  # whole numbers only on a small stack
    seek = _added(NAMES[2], "firmware/main/hal/maipai_seek.cc")
    assert "maipai_fd_register_tools();" in seek and "fd_loaded" in seek and "fd_score_pct" in seek


def test_the_tracker_obeys_every_gate_and_the_lease_wins():
    core = _code(_added(NAMES[3], "firmware/main/hal/maipai_face_track_core.h"))
    gate = re.search(r"int allowed = (.*?);", core, flags=re.S).group(1)
    for term in ("in->armed", "in->gates_ok", "!in->leased", "!in->locked", "!in->carried", "!in->remote_busy", "in->mode != FT_MODE_OFF"):
        assert term in gate, term
    seek = _code(_added(NAMES[3], "firmware/main/hal/maipai_seek.cc"))
    assert "ms_lease_active(&s_w->seek.lease, now)" in seek and "in.leased" in seek
    assert "maipai_lock_locked != nullptr" in seek and "__attribute__((weak))" in seek  # does not depend on the lock patches
    assert "maipai_pickup_held()" in seek
    assert "std::atomic<bool> s_track_armed{false}" in seek  # off after every boot
    assert "op_head(nullptr, o.pan_deg" in seek  # the head moves through the remote-gated path of every seek move
    kconfig = _added(NAMES[0], "firmware/main/Kconfig.projbuild")
    assert "MAIPAI_FACE_TRACK_HOUR_MIN" in kconfig


def test_the_numbers_of_the_plan_are_the_constants_of_the_control_loop():
    core = _added(NAMES[3], "firmware/main/hal/maipai_face_track_core.h")
    for line in (
        "#define FT_DEAD_YAW_DEG 4.0f", "#define FT_DEAD_PITCH_DEG 5.0f", "#define FT_KP_YAW 0.6f", "#define FT_KP_PITCH 0.4f", "#define FT_KD 0.1f",
        "#define FT_STEP_CAP_DEG 12.0f", "#define FT_MOVE_GAP_MS 600u", "#define FT_BUDGET_MOVES 20", "#define FT_BUDGET_WINDOW_MS 60000u", "#define FT_BOX_EMA 0.6f",
        "#define FT_ERR_EMA 0.5f", "#define FT_JUMP_FRAC 0.40f", "#define FT_STALE_MS 3000u", "#define FT_NOBODY_MS 20000u", "#define FT_STILL_CAP_MS 20000u",
    ):
        assert line in core, line
    assert re.search(r"#define FT_STALL_ASK_DEG 10\.0f", core)  # the plan says 14; the 12 degree step cap makes 10 the largest ask that can occur often


def test_the_status_tail_and_the_host_keys_agree():
    sys_path = HERE.parent
    import sys

    sys.path.insert(0, str(sys_path))
    from maipai_body.look_owner import STATUS_KEYS

    tail = "".join(_added(NAMES[2], "firmware/main/hal/maipai_seek.cc").splitlines()) + _added(NAMES[3], "firmware/main/hal/maipai_face_track_core.h")
    for key in re.findall(r'\\"(fd_[a-z_]+)\\"', tail):
        assert key in STATUS_KEYS, key
