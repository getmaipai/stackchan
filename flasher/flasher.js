import { ESPLoader, Transport } from "./vendor/esptool-js-0.7.0.js";
import { FlasherError, assertChip, assertNotOlder, fetchAndVerify, parseManifest, rawKeyFromPem, resolveManifestUrl, testReleaseAllowed, toFileArray, verifyManifestSignature } from "./flasher-core.js";

const $ = (id) => document.getElementById(id);
const say = (text, kind = "") => { const el = $("status"); el.textContent = text; el.className = kind; };
// Only this page's own site is read: a ?manifest= that names another site is refused (resolveManifestUrl).
let MANIFEST;
try {
  MANIFEST = resolveManifestUrl(new URLSearchParams(location.search).get("manifest"), location.href).href;
} catch (error) {
  MANIFEST = null;
  setTimeout(() => { $("install").disabled = true; say(error.message, "bad"); }, 0);
}

function setProgress(done, total) {
  const bar = $("progress");
  bar.hidden = false;
  bar.max = total || 1;
  bar.value = done;
}

// The keys this page trusts: the release keys pinned in trusted-keys.json beside the page. A test release is signed with a throwaway key
// that is in no list; the box for it shows only on localhost or with ?test=1, and then the key beside the release list is used for that one run.
const testBoxAllowed = testReleaseAllowed(new URL(location.href));
let notBefore = "";
async function trustedKeys() {
  const response = await fetch("trusted-keys.json", { cache: "no-store" });
  const doc = response.ok ? await response.json() : {};
  notBefore = typeof doc.not_before === "string" ? doc.not_before : "";
  const keys = (doc.keys || []).map(rawKeyFromPem);
  if (testBoxAllowed && $("testrelease").checked) {
    const own = await fetch(new URL("release-key.pub.pem", MANIFEST), { cache: "no-store" });
    if (own.ok) keys.push(rawKeyFromPem(await own.text()));
  }
  return keys;
}

async function loadManifest() {
  const response = await fetch(MANIFEST, { cache: "no-store" });
  if (!response.ok) throw new FlasherError("The release list could not be loaded. Check that you opened this page from a release.");
  const manifest = await response.json();
  const id = await verifyManifestSignature(manifest, await trustedKeys());  // before anything is shown or offered
  assertNotOlder(manifest, notBefore);
  return { ...parseManifest(manifest), keyId: id };
}

async function install(release) {
  say("Checking the files...");
  const base = new URL(MANIFEST);
  const verified = await fetchAndVerify(release.parts, async (path) => {
    const response = await fetch(new URL(path, base), { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return new Uint8Array(await response.arrayBuffer());
  });
  say("The files are good. Choose your robot in the box your browser shows.");
  let port;
  try {
    port = await navigator.serial.requestPort({ filters: [{ usbVendorId: 0x303a }] });
  } catch {
    say("No robot was chosen. Plug the robot in with a USB cable and try again.", "bad");
    return;
  }
  const transport = new Transport(port, false);
  const loader = new ESPLoader({ transport, baudrate: 460800, romBaudrate: 115200, terminal: { clean() {}, writeLine() {}, write() {} } });
  try {
    say("Connecting to the robot...");
    await loader.main();
    assertChip(loader);
    say("Writing. Do not unplug the robot.");
    await loader.writeFlash({
      fileArray: toFileArray(verified),
      flashSize: "keep",
      flashMode: "keep",
      flashFreq: "keep",
      eraseAll: false,
      compress: true,
      reportProgress: (index, written, total) => setProgress(written, total),
    });
    await loader.after("hard_reset");
    say("Done. The robot restarts by itself. Follow the setup steps on its screen.", "good");
  } catch (error) {
    if (error instanceof FlasherError) { say(error.message, "bad"); return; }
    say("Writing stopped before it finished. Unplug the robot, plug it in again and press Install once more. The robot is not harmed.", "bad");
    console.error(error);
  } finally {
    try { await transport.disconnect(); } catch { /* the port may already be closed */ }
  }
}

let current = null;

async function showRelease() {
  current = null;
  $("install").disabled = true;
  $("version").textContent = "?";
  $("parts").replaceChildren();
  say("Loading...");
  try {
    current = await loadManifest();
  } catch (error) {
    say(error instanceof FlasherError ? error.message : "The release list could not be loaded.", "bad");
    return;
  }
  $("version").textContent = current.version;
  $("parts").replaceChildren(...current.parts.map((p) => Object.assign(document.createElement("li"), { textContent: `${p.path} at 0x${p.offset.toString(16)}` })));
  $("install").disabled = false;
  const test = testBoxAllowed && $("testrelease").checked;
  say(test ? `Ready. This is a test release signed with key ${current.keyId}. Only install it if you built it yourself. Plug the robot in with a USB cable, then press Install.`
    : "Ready. Plug the robot in with a USB cable, then press Install.");
}

async function start() {
  if (!("serial" in navigator)) {
    $("install").disabled = true;
    say("This browser cannot talk to the robot. Open this page in Chrome or Edge on a computer.", "bad");
    return;
  }
  if (MANIFEST === null) return;
  $("testrelease").checked = false;  // the browser may restore a ticked box after a reload; every visit starts unticked
  if (testBoxAllowed) {
    $("testrelease-row").hidden = false;
    $("testrelease").addEventListener("change", showRelease);
  }
  $("install").addEventListener("click", async () => {
    if (!current) return;
    $("install").disabled = true;
    try { await install(current); }
    catch (error) { say(error instanceof FlasherError ? error.message : "Something went wrong. Reload the page and try again.", "bad"); }
    finally { $("install").disabled = false; }
  });
  await showRelease();
}

start();
