"""The web flasher's logic (flasher/flasher-core.js) runs under Node: manifest checks, hash checks, nothing written on a bad file."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_flasher_core_tests_pass_under_node():
    result = subprocess.run(["node", "--test", str(ROOT / "flasher" / "test" / "core.test.mjs")], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_page_has_no_outside_scripts_and_names_what_it_does():
    html = (ROOT / "flasher" / "index.html").read_text()
    assert "http://" not in html and "https://" not in html  # everything loads from this folder
    assert 'type="module" src="flasher.js"' in html and 'id="install"' in html and 'role="status"' in html
    js = (ROOT / "flasher" / "flasher.js").read_text()
    assert "./vendor/esptool-js-0.7.0.js" in js and "fetchAndVerify" in js


def test_review_fix_the_page_hides_the_test_box_and_checks_the_chip_before_writing():
    html = (ROOT / "flasher" / "index.html").read_text()
    assert 'id="testrelease-row" hidden' in html  # shown only by the script, on localhost or ?test=1
    js = (ROOT / "flasher" / "flasher.js").read_text()
    assert "testBoxAllowed && $(\"testrelease\").checked" in js and "current.keyId" in js
    assert js.index("assertChip(loader)") < js.index("loader.writeFlash")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node is not installed")
def test_the_page_verifies_the_signature_the_release_script_makes(tmp_path):
    """A real release folder (test key): the JavaScript check accepts its list with its own key and refuses it with a changed version."""
    from test_release_and_update_vectors import _fake_build

    build = _fake_build(tmp_path / "build")
    out = tmp_path / "rel"
    done = subprocess.run(["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", "2.0.0", "--date", "2026-11-18",
                           "--build-number", "1", "--test-key", "--output", str(out)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr[-300:]
    script = f"""
import * as core from './flasher-core.js';
import {{ readFileSync }} from 'node:fs';
const m = JSON.parse(readFileSync({json_str(out / 'flash-manifest.json')}, 'utf8'));
const raw = core.rawKeyFromPem(readFileSync({json_str(out / 'release-key.pub.pem')}, 'utf8'));
await core.verifyManifestSignature(m, [raw]);
let refused = false;
try {{ await core.verifyManifestSignature({{ ...m, version: '9.9.9' }}, [raw]); }} catch (e) {{ refused = true; }}
console.log(refused ? 'ok' : 'accepted-changed');
"""
    result = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, cwd=ROOT / "flasher")
    assert result.stdout.strip() == "ok", result.stderr[-400:] + result.stdout


def json_str(path) -> str:
    import json

    return json.dumps(str(path))


def test_review_fix_the_test_release_box_starts_unticked_and_the_pinned_date_floor_is_wired():
    root = Path(__file__).resolve().parents[2] / "flasher"
    html = (root / "index.html").read_text()
    js = (root / "flasher.js").read_text()
    assert 'id="testrelease" autocomplete="off"' in html
    assert '$("testrelease").checked = false;' in js
    assert "assertNotOlder(manifest, notBefore)" in js and "not_before" in js
