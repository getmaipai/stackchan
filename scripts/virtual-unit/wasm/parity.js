// Parity check of the browser build, in headless Chromium (Playwright): starts the page from docs-site/playground over a local server, measures load (cold and cached), runs every parity case
// (page/py/parity_cases.py) in the page, and compares with (a) the native results run_native.py wrote and (b) the committed golden frames in host/tests/golden. Also checks that the page asked
// for nothing outside its own origin, and exercises the viewer's own request path (tool call, tap, swipe, scenario). Prints one JSON report.
// Usage: [CHROME_EXE=/path/to/chrome] node scripts/virtual-unit/wasm/parity.js [native-results.json] [report.json] [screenshot.png]   (needs the build in docs-site/playground and Playwright)
// Placement: host-side development tool. Upstream: none.
const http = require('http'), fs = require('fs'), path = require('path'), zlib = require('zlib'), crypto = require('crypto');
const { chromium } = require('playwright');
const ROOT = path.resolve(__dirname, '../../..'), SITE = path.join(ROOT, 'docs-site/playground');
const nativeFile = process.argv[2] || path.join(ROOT, '.runs/wasm/native-results.json');
const reportFile = process.argv[3] || path.join(ROOT, '.runs/wasm/parity-report.json');
const shotFile = process.argv[4] || path.join(ROOT, '.runs/wasm/playground.png');
const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.wasm': 'application/wasm', '.json': 'application/json', '.zip': 'application/zip', '.glb': 'model/gltf-binary' };

function serve() {
  const hits = [];
  const srv = http.createServer((q, r) => {
    const rel = decodeURIComponent(q.url.split('?')[0]); const f = path.join(SITE, rel === '/' ? 'index.html' : rel);
    if (!f.startsWith(SITE) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { r.writeHead(404, { 'content-type': 'text/plain' }); return r.end('not found'); }
    const body = fs.readFileSync(f); hits.push({ url: rel === '/' ? '/index.html' : rel, bytes: body.length });
    // as a static host would send it: compressed, and told to keep the big files
    const gz = zlib.gzipSync(body, { level: 6 });
    r.writeHead(200, { 'content-type': MIME[path.extname(f)] || 'application/octet-stream', 'content-encoding': 'gzip', 'content-length': gz.length, 'cache-control': 'public, max-age=3600' });
    r.end(gz);
  });
  return new Promise((ok) => srv.listen(0, '127.0.0.1', () => ok({ srv, hits, url: `http://127.0.0.1:${srv.address().port}/` })));
}
const pixelsSha = (png) => { const i = png.indexOf('IDAT') + 4, e = png.lastIndexOf('IEND') - 8; return crypto.createHash('sha256').update(zlib.inflateSync(png.subarray(i, e))).digest('hex'); };

(async () => {
  const { srv, hits, url } = await serve();
  const browser = await chromium.launch(process.env.CHROME_EXE ? { executablePath: process.env.CHROME_EXE, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] } : {});
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 } });
  const report = { browser: browser.version(), cases: {}, load: {}, errors: [], external: [] };
  const attach = (page) => {
    page.on('pageerror', (e) => report.errors.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error') report.errors.push(m.text()); });
    page.on('request', (q) => { const u = q.url(); if (!u.startsWith(url) && !u.startsWith('data:') && !u.startsWith('blob:')) report.external.push(u); });
  };
  // ---- cold and cached load ----
  let page = await ctx.newPage(); attach(page);
  const t0 = Date.now(); await page.goto(url); await page.waitForFunction('window.__playground', null, { timeout: 120000 });
  report.load.cold_ms = Date.now() - t0; report.load.marks = await page.evaluate('window.__playground.marks');
  const wire = {}; let total = 0;
  for (const h of hits) { const g = zlib.gzipSync(fs.readFileSync(path.join(SITE, h.url)), { level: 6 }).length; wire[h.url] = { raw: h.bytes, gzip: g }; total += g; }
  report.load.transfer_gzip_bytes = total; report.load.files = wire;
  report.load.raw_bytes = hits.reduce((a, h) => a + h.bytes, 0);
  await page.close();   // the cached load is measured alone: one viewer page at a time (the 3D drawing is software-rendered in a headless browser)
  const page2 = await ctx.newPage(); attach(page2); hits.length = 0;
  const t1 = Date.now(); await page2.goto(url); await page2.waitForFunction('window.__playground', null, { timeout: 120000 });
  report.load.cached_ms = Date.now() - t1; report.load.cached_marks = await page2.evaluate('window.__playground.marks'); report.load.cached_requests_to_server = hits.length;
  page = page2;
  // ---- viewer path: tool call, tap, scenario, power, language, frame time ----
  await page.waitForTimeout(2500);
  const viewer = await page.evaluate(async () => {
    const j = async (m, p, b) => (await (await fetch(p, { method: m, body: b ? JSON.stringify(b) : undefined })).json());
    const out = {};
    out.call = await j('POST', '/call', { name: 'self.face.bench_emotion', arguments: { emotion: 'happy' } });
    out.tools = (await j('GET', '/tools')).tools.length;
    out.scenarios = (await j('GET', '/scenarios')).scenarios.length;
    out.tap = await j('POST', '/touch', { kind: 'tap', x: 185, y: 212 });
    out.swipe = await j('POST', '/touch', { kind: 'swipe', x: 250, y: 120, x2: 60, y2: 120, ms: 250 });
    out.battery = await j('POST', '/hw', { key: 'battery', value: 30 });
    out.state = await j('GET', '/state'); out.state = { now_ms: out.state.now_ms, emotion: out.state.emotion, battery: out.state.battery, motion: out.state.motion.state };
    out.scenario = await j('POST', '/scenario', { name: 'face-happy' });
    return out;
  });
  const wifi0 = await page.evaluate(async () => (await (await fetch('/state')).json()).hw.wifi);
  await page.click('#bwifi'); await page.waitForTimeout(400);
  viewer.wifi_button = { before: wifi0, after: await page.evaluate(async () => (await (await fetch('/state')).json()).hw.wifi) };
  report.viewer = viewer;
  await page.waitForTimeout(3000);
  report.frame = await page.evaluate(() => { const P = window.__playground; return { ticks: P.ticks, avg_tick_ms: P.tickMs / Math.max(1, P.ticks), worst_tick_ms: P.tickWorstMs }; });
  await page.selectOption('#pglang', 'es'); await page.waitForTimeout(600); await page.selectOption('#pglang', 'en');
  await page.screenshot({ path: shotFile });
  // ---- parity cases, on the harness page (no viewer, no 3D drawing) ----
  await page.close();
  const tp = await ctx.newPage(); attach(tp);
  await tp.goto(url + 'test.html'); await tp.waitForFunction('window.__playground', null, { timeout: 120000 });
  const native = JSON.parse(fs.readFileSync(nativeFile));
  report.load.harness_marks = await tp.evaluate('window.__playground.marks');
  const ids = await tp.evaluate(async () => { const pg = window.__playground.pg; pg.parityInit(); return await pg.cases(); });
  const t2 = Date.now(); const got = {};
  for (let i = 0; i < ids.length; i += 40) Object.assign(got, await tp.evaluate(async (chunk) => { const o = {}; for (const id of chunk) o[id] = await window.__playground.pg.runCase(id); return o; }, ids.slice(i, i + 40)));
  report.cases_ms = Date.now() - t2;
  const groups = {};
  const G = (id) => id.split(':')[0] + (id.startsWith('core:') ? '' : '');
  for (const id of ids) {
    const g = G(id); groups[g] = groups[g] || { total: 0, equal_to_native: 0, golden_total: 0, golden_equal: 0, differ: [] };
    groups[g].total++;
    if (got[id] === native[id]) groups[g].equal_to_native++; else groups[g].differ.push(id);
    if (id.startsWith('frame:')) {
      const n = id.slice(6), a = path.join(ROOT, 'host/tests/golden/screens', n + '.png'), b = path.join(ROOT, 'host/tests/golden/face', n + '.png');
      const gold = fs.existsSync(a) ? a : (fs.existsSync(b) ? b : null);
      if (gold) { groups[g].golden_total++; const gs = pixelsSha(fs.readFileSync(gold)), ns = JSON.parse(native[id]).sha;
        if (JSON.parse(got[id]).sha === gs) groups[g].golden_equal++;
        else if (ns !== gs) (groups[g].golden_stale = groups[g].golden_stale || []).push(n);   // the native renderer differs from this golden too: the golden is out of date, not the browser build
        else (groups[g].golden_differ = groups[g].golden_differ || []).push(n); }
    }
  }
  report.groups = groups; report.case_count = ids.length;
  report.sample = { 'quiet:schedule': JSON.parse(got['quiet:schedule']).agree, 'dance:loud_peak-home': JSON.parse(got['dance:loud_peak-home']).stages.join('').slice(0, 80) };
  fs.writeFileSync(reportFile, JSON.stringify(report, null, 1));
  const line = Object.entries(groups).map(([g, v]) => `${g} ${v.equal_to_native}/${v.total}` + (v.golden_total ? ` golden ${v.golden_equal}/${v.golden_total}` : '')).join(', ');
  console.log(`cold ${report.load.cold_ms} ms, cached ${report.load.cached_ms} ms, transfer ${(total / 1048576).toFixed(2)} MB gzip; parity: ${line}; external requests ${report.external.length}; page errors ${report.errors.length}`);
  await browser.close(); srv.close();
  const bad = Object.values(groups).some((v) => v.differ.length || (v.golden_differ || []).length) || report.external.length;
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
