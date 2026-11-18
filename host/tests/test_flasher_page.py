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
