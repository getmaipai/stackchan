// The flasher's logic with no page and no serial port in it, so it can be tested in Node: read the release manifest, fetch every
// part, check each part's SHA-256 against the manifest, and build the list the flashing library writes. Nothing is written to the
// robot unless every part checks out.

export class FlasherError extends Error {}

const FLASH_BYTES = 16 * 1024 * 1024;

// A signed list stays valid for as long as it is served, so a release with a known hole would still be accepted. trusted-keys.json can carry
// "not_before" (a date): a list made before it is refused. No date means no floor.
export function assertNotOlder(manifest, notBefore) {
  if (!notBefore) return;
  const made = Date.parse(manifest && manifest.created_at);
  const floor = Date.parse(notBefore);
  if (!Number.isFinite(floor)) throw new FlasherError("The date pinned in trusted-keys.json is not a date. Fix it, for example 2026-11-19.");
  if (!Number.isFinite(made)) throw new FlasherError("The release list has no date, so it cannot be checked for age. Download the release again.");
  if (made < floor) throw new FlasherError("This release is older than the oldest release this page accepts. Download the newest release.");
}

export function parseManifest(manifest) {
  const build = manifest && Array.isArray(manifest.builds) ? manifest.builds[0] : null;
  if (!build || build.chipFamily !== "ESP32-S3") {
    throw new FlasherError("This release is not for the StackChan (ESP32-S3). Download the release again.");
  }
  if (!Array.isArray(build.parts) || build.parts.length === 0) {
    throw new FlasherError("The release has no files to flash. Download the release again.");
  }
  const parts = build.parts.map((part) => {
    // A file name inside the release folder: letters, digits, dot, dash and underscore only (no slash, no encoded dots, no address).
    const plain = typeof part.path === "string" && /^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$/.test(part.path) && !part.path.includes("..");
    // An offset the flash can erase (a multiple of 4096) and that lies inside the 16 MiB flash.
    const inside = Number.isInteger(part.offset) && part.offset >= 0 && part.offset % 4096 === 0 && part.offset < FLASH_BYTES;
    if (!plain || !inside || !/^[0-9a-f]{64}$/.test(String(part.sha256 || ""))) {
      throw new FlasherError("The release list is damaged. Download the release again.");
    }
    const size = Number.isInteger(part.size) && part.size > 0 ? part.size : 0;
    if (size && part.offset + size > FLASH_BYTES) {
      throw new FlasherError("The release list is damaged. Download the release again.");
    }
    return { path: part.path, offset: part.offset, sha256: part.sha256, size };
  });
  const sorted = [...parts].sort((a, b) => a.offset - b.offset);
  // Two parts at one address, or one starting inside another, would overwrite each other. The parts' sizes are not in the list, so
  // the offsets must at least differ; the files themselves are checked by hash before anything is written.
  for (let i = 1; i < sorted.length; i += 1) {
    const before = sorted[i - 1];
    if (sorted[i].offset === before.offset || (before.size && before.offset + before.size > sorted[i].offset)) {
      throw new FlasherError("The release list puts two files at the same place on the robot. Download the release again.");
    }
  }
  return { version: String(manifest.version || ""), flashSize: manifest.flash_size || "", parts: sorted, signed: Boolean(manifest.signature) };
}

export async function sha256Hex(bytes, subtle = globalThis.crypto.subtle) {
  const digest = await subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

// fetchBytes(path) -> Uint8Array. Returns [{path, offset, data}] in offset order, or throws a plain message naming the bad file.
export async function fetchAndVerify(parts, fetchBytes, subtle = globalThis.crypto.subtle) {
  const out = [];
  for (const part of parts) {
    let data;
    try {
      data = await fetchBytes(part.path);
    } catch (error) {
      throw new FlasherError(`Could not download ${part.path}. Check your connection and try again.`);
    }
    if ((await sha256Hex(data, subtle)) !== part.sha256) {
      throw new FlasherError(`${part.path} does not match the release list, so nothing was written to the robot. Download the release again.`);
    }
    // The size is only known now: an empty file, one that runs past the end of the flash, or one that runs into the next file would be written over something else.
    if (data.length === 0) {
      throw new FlasherError(`${part.path} is empty, so nothing was written to the robot. Download the release again.`);
    }
    if (part.offset + data.length > FLASH_BYTES) {
      throw new FlasherError(`${part.path} would run past the end of the robot's flash, so nothing was written. Download the release again.`);
    }
    const before = out[out.length - 1];
    if (before && before.offset + before.data.length > part.offset) {
      throw new FlasherError(`${before.path} runs into ${part.path} on the robot, so nothing was written. Download the release again.`);
    }
    out.push({ path: part.path, offset: part.offset, data });
  }
  return out;
}

export function toBinaryString(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return s;
}

// The list the flashing library takes: data as a binary string, address as the byte offset.
export function toFileArray(verified) {
  return verified.map((part) => ({ data: toBinaryString(part.data), address: part.offset }));
}

// The release list is read only from this page's own site: a link that names another site's list is refused.
export function resolveManifestUrl(requested, pageUrl) {
  const page = new URL(pageUrl);
  let url;
  try {
    url = new URL(requested || "flash-manifest.json", page);
  } catch {
    throw new FlasherError("The release list address is not valid. Open this page from a release.");
  }
  if (url.origin !== page.origin) {
    throw new FlasherError("This page only flashes a release from its own site. Open the flasher from the release you downloaded.");
  }
  return url;
}

// Sorted-key compact JSON without the signature: the bytes the release script signed (the same rule as the spec's signing payload).
export function canonicalJson(value) {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((k) => `${JSON.stringify(k)}:${canonicalJson(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

export function signingPayload(manifest) {
  const { signature, ...rest } = manifest;
  return new TextEncoder().encode(canonicalJson(rest));
}

const fromBase64 = (text) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

// The fixed start of an Ed25519 SubjectPublicKeyInfo; the 32 key bytes follow it (44 bytes in all).
const ED25519_SPKI_PREFIX = [0x30, 0x2a, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x03, 0x21, 0x00];

// The raw 32-byte Ed25519 key from a PEM public key. Any other kind of key is refused.
export function rawKeyFromPem(pem) {
  const body = String(pem).replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  let der;
  try { der = fromBase64(body); } catch { throw new FlasherError("The release key is damaged. Download the release again."); }
  if (der.length !== ED25519_SPKI_PREFIX.length + 32 || !ED25519_SPKI_PREFIX.every((byte, i) => der[i] === byte)) {
    throw new FlasherError("The release key is damaged. Download the release again.");
  }
  return der.slice(ED25519_SPKI_PREFIX.length);
}

// The test-release box is for people who built a release themselves: it shows on localhost or with ?test=1, never on a published page.
export function testReleaseAllowed(url) {
  return ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname) || url.searchParams.get("test") === "1";
}

// The robot must be an ESP32-S3: the images are built for it and do not boot on another chip. Call after the loader has connected.
export function assertChip(loader) {
  const name = loader && loader.chip && loader.chip.CHIP_NAME;
  if (name !== "ESP32-S3") {
    throw new FlasherError(`This board is ${name || "not a chip this page knows"}, not an ESP32-S3, so nothing was written. Connect a StackChan (ESP32-S3) and try again.`);
  }
}

const NOT_VALID = "The release list's signature is not valid, so it will not be flashed. Download the release again.";

export async function keyId(raw, subtle = globalThis.crypto.subtle) {
  return (await sha256Hex(raw, subtle)).slice(0, 16);
}

// Checks the release list's Ed25519 signature against keys the page trusts (a list of raw 32-byte keys). Returns the key id.
// Nothing is offered to the person unless this passes.
export async function verifyManifestSignature(manifest, trustedRawKeys, subtle = globalThis.crypto.subtle) {
  const signature = manifest && manifest.signature;
  if (!signature || typeof signature.keyid !== "string" || typeof signature.sig !== "string") {
    throw new FlasherError("This release list is not signed, so it will not be flashed. Download the release again.");
  }
  for (const raw of trustedRawKeys) {
    if ((await keyId(raw, subtle)) !== signature.keyid) continue;
    let sig;
    try { sig = fromBase64(signature.sig); } catch { throw new FlasherError(NOT_VALID); }
    let ok = false;
    try {
      const key = await subtle.importKey("raw", raw, { name: "Ed25519" }, false, ["verify"]);
      ok = await subtle.verify({ name: "Ed25519" }, key, sig, signingPayload(manifest));
    } catch {
      throw new FlasherError("This browser cannot check the release signature. Use a current Chrome or Edge.");
    }
    if (!ok) throw new FlasherError(NOT_VALID);
    return signature.keyid;
  }
  throw new FlasherError("This release is signed with a key this page does not trust, so it will not be flashed.");
}
