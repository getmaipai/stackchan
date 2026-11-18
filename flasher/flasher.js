import { ESPLoader, Transport } from "./vendor/esptool-js-0.7.0.js";
import { FlasherError, fetchAndVerify, parseManifest, toFileArray } from "./flasher-core.js";

const $ = (id) => document.getElementById(id);
const say = (text, kind = "") => { const el = $("status"); el.textContent = text; el.className = kind; };
const MANIFEST = new URLSearchParams(location.search).get("manifest") || "flash-manifest.json";

function setProgress(done, total) {
  const bar = $("progress");
  bar.hidden = false;
  bar.max = total || 1;
  bar.value = done;
}

async function loadManifest() {
  const response = await fetch(MANIFEST, { cache: "no-store" });
  if (!response.ok) throw new FlasherError("The release list could not be loaded. Check that you opened this page from a release.");
  return parseManifest(await response.json());
}

async function install(release) {
  say("Checking the files...");
  const base = new URL(MANIFEST, location.href);
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
    say("Writing stopped before it finished. Unplug the robot, plug it in again and press Install once more. The robot is not harmed.", "bad");
    console.error(error);
  } finally {
    try { await transport.disconnect(); } catch { /* the port may already be closed */ }
  }
}

async function start() {
  if (!("serial" in navigator)) {
    $("install").disabled = true;
    say("This browser cannot talk to the robot. Open this page in Chrome or Edge on a computer.", "bad");
    return;
  }
  let release;
  try {
    release = await loadManifest();
  } catch (error) {
    $("install").disabled = true;
    say(error instanceof FlasherError ? error.message : "The release list could not be loaded.", "bad");
    return;
  }
  $("version").textContent = release.version;
  $("parts").replaceChildren(...release.parts.map((p) => Object.assign(document.createElement("li"), { textContent: `${p.path} at 0x${p.offset.toString(16)}` })));
  $("install").addEventListener("click", async () => {
    $("install").disabled = true;
    try { await install(release); }
    catch (error) { say(error instanceof FlasherError ? error.message : "Something went wrong. Reload the page and try again.", "bad"); }
    finally { $("install").disabled = false; }
  });
  say("Ready. Plug the robot in with a USB cable, then press Install.");
}

start();
