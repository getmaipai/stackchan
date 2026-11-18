import assert from "node:assert/strict";
import { test } from "node:test";
import { FlasherError, fetchAndVerify, parseManifest, sha256Hex, toFileArray } from "../flasher-core.js";

const bytes = (s) => new TextEncoder().encode(s);
async function manifestFor(files) {
  const parts = [];
  for (const [path, offset, data] of files) parts.push({ path, offset, sha256: await sha256Hex(bytes(data)) });
  return { version: "1.0.0", flash_size: "16MB", builds: [{ chipFamily: "ESP32-S3", parts }], signature: { keyid: "k", sig: "s" } };
}

test("parts are sorted by offset and carry their hashes", async () => {
  const m = parseManifest(await manifestFor([["app.bin", 0x20000, "app"], ["boot.bin", 0x0, "boot"]]));
  assert.deepEqual(m.parts.map((p) => p.path), ["boot.bin", "app.bin"]);
  assert.equal(m.version, "1.0.0");
});

test("a release for another chip, an empty one and a damaged one are refused in plain words", async () => {
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32", parts: [] }] }), FlasherError);
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: [] }] }), /no files/);
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: [{ path: "../x", offset: 0, sha256: "0".repeat(64) }] }] }), /damaged/);
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: [{ path: "a", offset: -1, sha256: "0".repeat(64) }] }] }), /damaged/);
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: [{ path: "a", offset: 0, sha256: "zz" }] }] }), /damaged/);
});

test("good files verify and become the list the flashing library writes", async () => {
  const files = { "boot.bin": "boot", "app.bin": "app" };
  const m = parseManifest(await manifestFor([["boot.bin", 0, "boot"], ["app.bin", 0x20000, "app"]]));
  const verified = await fetchAndVerify(m.parts, async (path) => bytes(files[path]));
  const list = toFileArray(verified);
  assert.deepEqual(list.map((f) => [f.address, f.data]), [[0, "boot"], [0x20000, "app"]]);
});

test("one changed byte stops everything before anything is written", async () => {
  const m = parseManifest(await manifestFor([["boot.bin", 0, "boot"], ["app.bin", 0x20000, "app"]]));
  await assert.rejects(fetchAndVerify(m.parts, async (path) => bytes(path === "app.bin" ? "apx" : "boot")), /app\.bin does not match/);
});

test("a download that fails says which file", async () => {
  const m = parseManifest(await manifestFor([["boot.bin", 0, "boot"]]));
  await assert.rejects(fetchAndVerify(m.parts, async () => { throw new Error("offline"); }), /Could not download boot\.bin/);
});
