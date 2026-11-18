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
