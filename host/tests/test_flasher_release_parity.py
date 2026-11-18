# ruff: noqa: E501
"""The web flasher's signature check against a release made by the real release script (scripts/release.sh, Python and openssl), not by a test helper: the page must accept
what the script signs, with the same bytes (version text with non-ASCII letters included), and refuse every change to the list after it was signed. Playground report 17."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from test_release_and_update_vectors import _fake_build

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="no node on this machine")


def _verify_in_node(tmp_path, variants: dict, pem: str) -> dict[str, str]:
    (tmp_path / "variants.json").write_text(json.dumps(variants))
    script = f"""
import {{ verifyManifestSignature, rawKeyFromPem }} from {json.dumps((ROOT / 'flasher' / 'flasher-core.js').as_uri())};
import fs from 'node:fs';
const v = JSON.parse(fs.readFileSync({json.dumps(str(tmp_path / 'variants.json'))}, 'utf8'));
const key = rawKeyFromPem({json.dumps(pem)});
const out = {{}};
for (const [name, m] of Object.entries(v)) {{ try {{ await verifyManifestSignature(m, [key]); out[name] = 'accepted'; }} catch (e) {{ out[name] = 'refused'; }} }}
console.log(JSON.stringify(out));
"""
    done = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr[-300:]
    return json.loads(done.stdout)


@pytest.mark.parametrize("version", ["1.0.0-test", "1.0.0-tést-\U0001F600"])
def test_the_page_accepts_what_the_release_script_signs_and_refuses_every_change_after(tmp_path, version):
    build, out = _fake_build(tmp_path / "build"), tmp_path / "rel"
    made = subprocess.run(["bash", str(ROOT / "scripts" / "release.sh"), "--build-dir", str(build), "--version", version, "--date", "2026-11-18", "--build-number", "7", "--test-key", "--output", str(out)], capture_output=True, text=True)
    assert made.returncode == 0, made.stderr
    manifest = json.loads((out / "flash-manifest.json").read_text())
    variants = {"as made": manifest}
    v = copy.deepcopy(manifest); v["builds"][0]["parts"][0]["sha256"] = "0" * 64; variants["part hash changed"] = v
    v = copy.deepcopy(manifest); v["version"] = "9.9.9"; variants["version changed"] = v
    v = copy.deepcopy(manifest); v["builds"].append(copy.deepcopy(v["builds"][0])); variants["second build appended"] = v
    v = copy.deepcopy(manifest); v["extra"] = {"x": 1}; variants["extra field"] = v
    v = copy.deepcopy(manifest); v["signature"]["keyid"] = "0" * 16; variants["wrong key id"] = v
    v = copy.deepcopy(manifest); v["signature"]["sig"] = manifest["signature"]["sig"][:-4] + "AAAA"; variants["signature altered"] = v
    v = copy.deepcopy(manifest); del v["signature"]; variants["no signature"] = v
    got = _verify_in_node(tmp_path, variants, (out / "release-key.pub.pem").read_text())
    assert got.pop("as made") == "accepted"
    assert set(got.values()) == {"refused"}, got
