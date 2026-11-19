"""Golden renders of every face style (docs/plan/face-styles-verdict.md): a digest of the thirteen mood pictures of each style in each of four face colors on each of three backgrounds, drawn by the
unit's own face code in the host renderer. A changed look shows as a changed digest; update on purpose with UPDATE_GOLDEN=1. Skipped while the renderer is not built from a tree that has patch UXF01
(the recipe styles need its `recipe` command) or at all."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GOLDEN = HERE / "golden" / "face_styles_digests.json"
sys.path.insert(0, str(ROOT / "scripts" / "virtual-unit"))
RENDER = ROOT / ".runs" / "vu-build" / "render"
if not RENDER.exists():
    pytest.skip("the face renderer is not built (bash scripts/virtual-unit/build-face.sh)", allow_module_level=True)
probe = subprocess.run([str(RENDER)], input=f"recipe {ROOT / 'firmware' / 'styles' / 'cat.rcp'}\n", capture_output=True, text=True, timeout=60)
if "unknown command" in probe.stderr:
    pytest.skip("the face renderer was built from a tree without patch UXF01", allow_module_level=True)

import face_matrix as fm  # noqa: E402
from face_styles import BACKGROUNDS, COLORS, MOODS, STYLES  # noqa: E402


def digests() -> dict[str, str]:
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        rendered = fm.render_all(STYLES, Path(tmp))
        for (style, color, background), files in rendered.items():
            h = hashlib.sha1()
            for mood in MOODS:
                h.update(files[mood].read_bytes())
            out[f"{style}/{color}/{background}"] = h.hexdigest()[:16]
    return out


def test_every_style_color_and_background_draws_as_before():
    got = digests()
    assert len(got) == len(STYLES) * len(COLORS) * len(BACKGROUNDS)
    if os.environ.get("UPDATE_GOLDEN") == "1" or not GOLDEN.exists():
        GOLDEN.write_text(json.dumps(got, indent=1, sort_keys=True) + "\n")
        return
    want = json.loads(GOLDEN.read_text())
    changed = sorted(k for k in set(got) | set(want) if got.get(k) != want.get(k))
    assert not changed, f"{len(changed)} face renders changed, first {changed[:4]}. If that is on purpose run UPDATE_GOLDEN=1 host/.venv/bin/python -m pytest host/tests/test_face_styles_golden.py"


def test_no_two_styles_look_alike():
    got = digests()
    first = {}
    for key, digest in got.items():
        style, color, background = key.split("/")
        if (color, background) == ("white", "none"):
            assert digest not in first, f"{style} draws exactly like {first[digest]}: two styles must differ"
            first[digest] = style
