// The flasher's logic with no page and no serial port in it, so it can be tested in Node: read the release manifest, fetch every
// part, check each part's SHA-256 against the manifest, and build the list the flashing library writes. Nothing is written to the
// robot unless every part checks out.

export class FlasherError extends Error {}

export function parseManifest(manifest) {
  const build = manifest && Array.isArray(manifest.builds) ? manifest.builds[0] : null;
  if (!build || build.chipFamily !== "ESP32-S3") {
    throw new FlasherError("This release is not for the StackChan (ESP32-S3). Download the release again.");
  }
  if (!Array.isArray(build.parts) || build.parts.length === 0) {
    throw new FlasherError("The release has no files to flash. Download the release again.");
  }
  const parts = build.parts.map((part) => {
    if (typeof part.path !== "string" || part.path.includes("..") || part.path.startsWith("/") || !Number.isInteger(part.offset) || part.offset < 0 || !/^[0-9a-f]{64}$/.test(String(part.sha256 || ""))) {
      throw new FlasherError("The release list is damaged. Download the release again.");
    }
    return { path: part.path, offset: part.offset, sha256: part.sha256 };
  });
  const sorted = [...parts].sort((a, b) => a.offset - b.offset);
  // Two parts at one address, or one starting inside another, would overwrite each other. The parts' sizes are not in the list, so
  // the offsets must at least differ; the files themselves are checked by hash before anything is written.
  for (let i = 1; i < sorted.length; i += 1) {
    if (sorted[i].offset === sorted[i - 1].offset) {
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

// The raw 32-byte Ed25519 key from a PEM public key (the last 32 bytes of its SubjectPublicKeyInfo).
export function rawKeyFromPem(pem) {
  const body = String(pem).replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
  const der = fromBase64(body);
  if (der.length < 32) throw new FlasherError("The release key is damaged. Download the release again.");
  return der.slice(der.length - 32);
}

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
    let ok = false;
    try {
      const key = await subtle.importKey("raw", raw, { name: "Ed25519" }, false, ["verify"]);
      ok = await subtle.verify({ name: "Ed25519" }, key, fromBase64(signature.sig), signingPayload(manifest));
    } catch {
      throw new FlasherError("This browser cannot check the release signature. Use a current Chrome or Edge.");
    }
    if (!ok) throw new FlasherError("The release list's signature is not valid, so it will not be flashed. Download the release again.");
    return signature.keyid;
  }
  throw new FlasherError("This release is signed with a key this page does not trust, so it will not be flashed.");
}
