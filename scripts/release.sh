#!/usr/bin/env bash
# Intent: turn one finished firmware build into a signed release folder: the images, flash-manifest.json (signed), a detached signature
# beside the app image (what the unit and the host's update path check), the public key, and a key scan. Never builds firmware.
# Usage: bash scripts/release.sh --build-dir BUILD --version 1.0.0 --date YYYY-MM-DD (--signing-key PATH | --test-key) [--output DIR] [--app-image NAME]
#   --test-key makes a throwaway key and a folder marked TEST: a test release can never be mistaken for a real one.
#   The real key is the owner's; it is never a command-line value, only a file path.
# Placement: repo release tool (host). Upstream: none.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
BUILD=""; VERSION=""; DATE=""; KEY=""; TEST=0; OUT=""; APP="xiaozhi.bin"
while (($#)); do
  case "$1" in
    --build-dir) BUILD="$2"; shift 2 ;;
    --version) VERSION="$2"; shift 2 ;;
    --date) DATE="$2"; shift 2 ;;
    --signing-key) KEY="$2"; shift 2 ;;
    --test-key) TEST=1; shift ;;
    --output) OUT="$2"; shift 2 ;;
    --app-image) APP="$2"; shift 2 ;;
    *) echo "Usage: release.sh --build-dir BUILD --version X --date YYYY-MM-DD (--signing-key PATH | --test-key) [--output DIR] [--app-image NAME]" >&2; exit 2 ;;
  esac
done
[ -n "$BUILD" ] && [ -f "$BUILD/flasher_args.json" ] || { echo "Pass --build-dir with the finished build (it holds flasher_args.json)." >&2; exit 2; }
[ -n "$VERSION" ] && [ -n "$DATE" ] || { echo "Pass --version and --date YYYY-MM-DD." >&2; exit 2; }
if [ "$TEST" = 1 ] && [ -n "$KEY" ]; then echo "Use --test-key or --signing-key, not both." >&2; exit 2; fi
if [ "$TEST" = 0 ] && [ -z "$KEY" ]; then echo "Pass --signing-key PATH (the owner's release key file), or --test-key for a dry run." >&2; exit 2; fi
[ -n "$OUT" ] || OUT="$ROOT/dist/stackchan-release-$DATE$([ "$TEST" = 1 ] && echo -TEST)"
PY=python3; [ -x "$ROOT/host/.venv/bin/python" ] && PY="$ROOT/host/.venv/bin/python"
export PYTHONPATH="$ROOT/host${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$OUT"
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
if [ "$TEST" = 1 ]; then
  KEY="$WORK/test-key.pem"
  "$PY" - "$KEY" <<'PY'
import subprocess, sys
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli
subprocess.run([openssl_cli(), "genpkey", "-algorithm", "Ed25519", "-out", sys.argv[1]], check=True, capture_output=True)
PY
  printf 'This folder was signed with a throwaway test key. It must never be published or installed on a real robot.\n' > "$OUT/TEST-KEY-NOT-FOR-RELEASE.txt"
fi
[ -f "$KEY" ] || { echo "The signing key file $KEY does not exist." >&2; exit 2; }
"$PY" -m maipai_body.bodies.stackchan.firmware.flash_manifest build --build-dir "$BUILD" --release-dir "$OUT" --version "$VERSION" --date "$DATE" --key "$KEY" --out "$OUT/flash-manifest.json"
"$PY" - "$KEY" "$OUT" "$APP" <<'PY'
import subprocess, sys
from pathlib import Path
from maipai_body.bodies.stackchan.firmware.openssl_cli import openssl_cli
key, out, app = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
image = out / app
if not image.is_file():
    raise SystemExit(f"The app image {app} is not in the release folder. Pass --app-image with its file name.")
sig = subprocess.run([openssl_cli(), "pkeyutl", "-sign", "-rawin", "-inkey", key, "-in", str(image)], check=True, capture_output=True).stdout
(out / f"{app}.sig").write_bytes(sig)
pub = subprocess.run([openssl_cli(), "pkey", "-in", key, "-pubout"], check=True, capture_output=True).stdout
(out / "release-key.pub.pem").write_bytes(pub)
PY
# Verify what was just made, as the host's update path and `stackchan flash` do.
"$PY" - "$OUT" "$APP" <<'PY'
import json, sys
from pathlib import Path
from maipai_body.bodies.stackchan.firmware.flash_manifest import verify_detached, verify_manifest
out, app = Path(sys.argv[1]), sys.argv[2]
pub = out / "release-key.pub.pem"
manifest = json.loads((out / "flash-manifest.json").read_text())
assert verify_manifest(manifest, pub), "the manifest signature does not verify"
assert verify_detached((out / app).read_bytes(), (out / f"{app}.sig").read_bytes(), pub), "the image signature does not verify"
print("release: manifest and image signatures verify")
PY
python3 "$ROOT/scripts/check-no-keys.py" "$OUT" >/dev/null || { echo "A key-shaped value is in the release folder. Nothing was released." >&2; exit 1; }
echo "release: ok -> $OUT"
