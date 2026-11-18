#!/usr/bin/env bash
# Intent: check stackchan.glb with the Khronos glTF validator, on this Mac only (the file is read locally; nothing is uploaded).
# Usage: bash scripts/virtual-unit/model/validate.sh   Prints one line; exit 1 on any error or warning.
# Needs node and npm. The validator (pinned below, Apache-2.0) is installed into .runs/gltf-validator on first use; it is a development tool only.
# Placement: host-side development tool. Upstream: none.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/../../.." && pwd)"; DIR="$ROOT/.runs/gltf-validator"
PIN="gltf-validator@2.0.0-dev.3.10"
command -v node >/dev/null || { echo "validate: node is missing; install Node.js and run this again"; exit 2; }
[ -d "$DIR/node_modules/gltf-validator" ] || { mkdir -p "$DIR"; npm install --silent --ignore-scripts --prefix "$DIR" "$PIN" >/dev/null; }
NODE_PATH="$DIR/node_modules" node -e '
const v = require("gltf-validator"), fs = require("fs");
v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1]))).then(r => {
  const i = r.issues, bad = i.messages.filter(m => m.severity < 2);
  console.log("validate: " + i.numErrors + " errors, " + i.numWarnings + " warnings, " + i.numInfos + " infos, " + r.info.totalTriangleCount + " triangles, " + r.info.drawCallCount + " draw calls");
  for (const m of bad.slice(0, 10)) console.log("  " + m.code + " " + m.pointer + ": " + m.message);
  process.exit(bad.length ? 1 : 0);
});' "$HERE/stackchan.glb"
