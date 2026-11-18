#!/usr/bin/env node
// Make docs/images/hero-playground.gif: a scripted screen recording of the playground (view.py: 3D model, the unit's screen, the tool panel).
// Usage: node scripts/make-hero-playground-gif.mjs [--keep-frames DIR]
// Starts the viewer on a free port, drives headless Chrome over its debugging port (Node 22+ has fetch and WebSocket built in, no package needed),
// presses the page's own buttons (an emotion, a dance, a tool call, the head sliders), takes screenshots for about 10 s and builds the GIF with ffmpeg.
// Placement: host-side development tool; no firmware change. Upstream: none.
import { spawn, execFileSync } from "node:child_process";
import { mkdtempSync, writeFileSync, mkdirSync, cpSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(ROOT, "docs", "images", "hero-playground.gif");
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
import { createServer } from "node:net";
const freePort = () => new Promise((res) => { const s = createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); }); });
const VIEW_PORT = await freePort(), DEBUG_PORT = await freePort(), W = 1000, H = 600, FRAMES = 60, FPS = 6;
const keep = process.argv.includes("--keep-frames") ? process.argv[process.argv.indexOf("--keep-frames") + 1] : null;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const view = spawn("python3", [join(ROOT, "scripts/virtual-unit/view.py"), String(VIEW_PORT)], { stdio: "ignore" });
const profile = mkdtempSync(join(tmpdir(), "hero-chrome-"));
const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${DEBUG_PORT}`, `--user-data-dir=${profile}`, `--window-size=${W},${H}`, "--hide-scrollbars",
  "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "about:blank"], { stdio: "ignore" });
const frames = mkdtempSync(join(tmpdir(), "hero-frames-"));
function cleanup() { try { view.kill(); chrome.kill(); } catch {} try { rmSync(profile, { recursive: true, force: true, maxRetries: 5 }); } catch {} }
process.on("exit", cleanup);

async function targets() {
  for (let i = 0; i < 100; i++) {
    try { return await (await fetch(`http://127.0.0.1:${DEBUG_PORT}/json`)).json(); } catch { await sleep(200); }
  }
  throw new Error("Chrome did not start: set CHROME to a Chrome or Chromium binary and run again.");
}
const page = (await targets()).find((t) => t.type === "page");
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const waiting = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && waiting.has(d.id)) { waiting.get(d.id)(d); waiting.delete(d.id); } };
const send = (method, params = {}) => new Promise((res) => { const i = ++id; waiting.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const js = (expr) => send("Runtime.evaluate", { expression: expr, awaitPromise: true });
const click = (sel) => js(`document.querySelector(${JSON.stringify(sel)})?.click()`);

await send("Page.enable");
await send("Emulation.setDeviceMetricsOverride", { width: W, height: H, deviceScaleFactor: 1, mobile: false });
for (let i = 0; i < 50; i++) { try { if ((await fetch(`http://127.0.0.1:${VIEW_PORT}/state`)).ok) break; } catch {} await sleep(200); }
await send("Page.navigate", { url: `http://127.0.0.1:${VIEW_PORT}/` });
await sleep(4000);

// the script: frame number -> what to press
const actions = {
  4: () => click('#emos button:nth-child(2)'),
  14: () => click('[data-dance="happy"]'),
  22: () => js(`document.getElementById('dom').scrollIntoView({block:'start'})`),
  26: () => click('#go'),
  30: () => js(`(()=>{const y=document.getElementById('yaw');y.value=-60;y.dispatchEvent(new Event('input',{bubbles:true}));y.dispatchEvent(new Event('change',{bubbles:true}))})()`),
  40: () => js(`(()=>{const y=document.getElementById('yaw');y.value=60;y.dispatchEvent(new Event('input',{bubbles:true}));y.dispatchEvent(new Event('change',{bubbles:true}))})()`),
  48: () => click("#dstop"),
  50: () => click('#emos button:nth-child(5)'),
};
const t0 = Date.now();
for (let n = 0; n < FRAMES; n++) {
  if (actions[n]) await actions[n]();
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(frames, `f${String(n).padStart(4, "0")}.png`), Buffer.from(shot.result.data, "base64"));
  const due = t0 + ((n + 1) * 1000) / FPS; const wait = due - Date.now(); if (wait > 0) await sleep(wait);
}
if (keep) { mkdirSync(keep, { recursive: true }); cpSync(frames, keep, { recursive: true }); }
const vf = "scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle";
execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", join(frames, "f%04d.png"), "-vf", vf, "-loop", "0", OUT]);
rmSync(frames, { recursive: true, force: true });
console.log(`wrote ${OUT} (${FRAMES} frames, ${(statSync(OUT).size / 1e6).toFixed(2)} MB)`);
cleanup(); process.exit(0);
