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

import { resolveManifestUrl, verifyManifestSignature, rawKeyFromPem, canonicalJson, keyId } from "../flasher-core.js";
import { generateKeyPairSync, sign, createPublicKey } from "node:crypto";

test("a release list from another site is refused, the page's own folder is read", () => {
  assert.throws(() => resolveManifestUrl("https://other.example/flash-manifest.json", "https://flasher.example/flasher/"), /own site/);
  assert.equal(resolveManifestUrl(null, "https://flasher.example/flasher/").href, "https://flasher.example/flasher/flash-manifest.json");
  assert.equal(resolveManifestUrl("../r1/flash-manifest.json", "https://flasher.example/flasher/").origin, "https://flasher.example");
});

async function signed(manifest) {
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  const pem = publicKey.export({ type: "spki", format: "pem" });
  const raw = rawKeyFromPem(pem);
  const payload = Buffer.from(canonicalJson(manifest));
  const sig = sign(null, payload, privateKey).toString("base64");
  return { manifest: { ...manifest, signature: { keyid: await keyId(raw), sig } }, raw };
}

test("a signed list passes with its key and fails with a changed byte, another key or no signature", async () => {
  const base = { version: "1.0.0", builds: [{ chipFamily: "ESP32-S3", parts: [] }], note: "ü" };
  const { manifest, raw } = await signed(base);
  assert.equal((await verifyManifestSignature(manifest, [raw])).length, 16);
  await assert.rejects(verifyManifestSignature({ ...manifest, version: "1.0.1" }, [raw]), /not valid/);
  const other = (await signed(base)).raw;
  await assert.rejects(verifyManifestSignature(manifest, [other]), /does not trust/);
  await assert.rejects(verifyManifestSignature(base, [raw]), /not signed/);
  await assert.rejects(verifyManifestSignature(manifest, []), /does not trust/);
});

test("two files at one address are refused", async () => {
  const h = "a".repeat(64);
  assert.throws(() => parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: [{ path: "a.bin", offset: 0, sha256: h }, { path: "b.bin", offset: 0, sha256: h }] }] }), /same place/);
});

// Red team, report 17: sizes are only known after the download, so the checks that need them happen in fetchAndVerify, before anything is written.
async function listFor(parts) {
  const files = {};
  const out = [];
  for (const [path, offset, bytesData] of parts) {
    files[path] = bytesData;
    out.push({ path, offset, sha256: await sha256Hex(bytesData) });
  }
  return { parts: parseManifest({ builds: [{ chipFamily: "ESP32-S3", parts: out }] }).parts, files };
}

test("a file that runs into the next one is refused before anything is written", async () => {
  const { parts, files } = await listFor([["a.bin", 0, new Uint8Array(8192).fill(1)], ["b.bin", 4096, new Uint8Array(100).fill(2)]]);
  await assert.rejects(fetchAndVerify(parts, async (p) => files[p]), /overlap|runs into/);
});

test("a file that runs past the end of the 16 MB flash is refused", async () => {
  const { parts, files } = await listFor([["a.bin", 16773120, new Uint8Array(8192).fill(1)]]);
  await assert.rejects(fetchAndVerify(parts, async (p) => files[p]), /end of the flash|too big|past/);
});

test("an empty file is refused", async () => {
  const { parts, files } = await listFor([["a.bin", 0, new Uint8Array(0)]]);
  await assert.rejects(fetchAndVerify(parts, async (p) => files[p]), /empty/);
});

test("files that touch end to end are fine", async () => {
  const { parts, files } = await listFor([["a.bin", 0, new Uint8Array(4096).fill(1)], ["b.bin", 4096, new Uint8Array(100).fill(2)]]);
  assert.equal((await fetchAndVerify(parts, async (p) => files[p])).length, 2);
});

import { assertChip, testReleaseAllowed } from "../flasher-core.js";

test("review fix: a signature that is not base64 says the release is damaged, not that the browser is old", async () => {
  const base = { version: "1.0.0", builds: [] };
  const { manifest, raw } = await signed(base);
  const bad = { ...manifest, signature: { ...manifest.signature, sig: "not base64 !!" } };
  await assert.rejects(verifyManifestSignature(bad, [raw]), (e) => e instanceof FlasherError && /not valid/.test(e.message) && !/browser/.test(e.message));
});

test("review fix: a key that is not an Ed25519 public key is refused, a real one still reads", () => {
  const { publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  assert.throws(() => rawKeyFromPem(publicKey.export({ type: "spki", format: "pem" })), /damaged/);
  const ed = generateKeyPairSync("ed25519").publicKey;
  assert.equal(rawKeyFromPem(ed.export({ type: "spki", format: "pem" })).length, 32);
  assert.throws(() => rawKeyFromPem("-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----"), /damaged/);
});

test("review fix: only an ESP32-S3 is written to", () => {
  assert.doesNotThrow(() => assertChip({ chip: { CHIP_NAME: "ESP32-S3" } }));
  for (const loader of [{ chip: { CHIP_NAME: "ESP32-C3" } }, { chip: { CHIP_NAME: "ESP32-S2" } }, { chip: { CHIP_NAME: "ESP32-S31" } }, { chip: null }, {}]) {
    assert.throws(() => assertChip(loader), (e) => e instanceof FlasherError && /ESP32-S3/.test(e.message));
  }
});

test("review fix: the test-release box is for localhost or ?test=1 only", () => {
  const at = (href) => testReleaseAllowed(new URL(href));
  assert.equal(at("https://flasher.example/flasher/"), false);
  assert.equal(at("https://flasher.example/flasher/?test=0"), false);
  assert.equal(at("https://flasher.example/flasher/?manifest=x"), false);
  assert.equal(at("https://flasher.example/flasher/?test=1"), true);
  assert.equal(at("http://localhost:8000/flasher/"), true);
  assert.equal(at("http://127.0.0.1:8000/"), true);
  assert.equal(at("https://localhost.evil.example/"), false);
});
