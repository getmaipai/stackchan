// Headless check: serves this folder, opens index.html in Chromium (Playwright), taps the face, runs the cores, prints measurements as JSON.
// Usage: node scripts/virtual-unit/wasm/check.js [out.png]   (needs the build output from build.sh and Playwright)
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('playwright');
const root = __dirname, mime = { '.html': 'text/html', '.js': 'text/javascript', '.wasm': 'application/wasm' };
const srv = http.createServer((q, r) => {
  const f = path.join(root, q.url === '/' ? 'index.html' : decodeURIComponent(q.url.split('?')[0]));
  if (!f.startsWith(root) || !fs.existsSync(f)) { r.writeHead(404); return r.end('not found'); }
  r.writeHead(200, { 'content-type': mime[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r);
});
(async () => {
  await new Promise((ok) => srv.listen(0, ok));
  const url = `http://127.0.0.1:${srv.address().port}/`;
  const browser = await chromium.launch(); const page = await browser.newPage({ viewport: { width: 800, height: 1100 } });
  const errors = []; page.on('pageerror', (e) => errors.push(String(e))); page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const external = []; page.on('request', (q) => { if (!q.url().startsWith(url) && !q.url().startsWith('data:')) external.push(q.url()); });
  const t0 = Date.now(); await page.goto(url); await page.waitForFunction('window.__vu', null, { timeout: 30000 }); const readyMs = Date.now() - t0;
  const taps0 = await page.evaluate('window.__vu.vu.taps()');
  const box = await page.locator('#face').boundingBox();
  const shot = async (n) => page.locator('#face').screenshot({ path: process.argv[2] ? process.argv[2].replace('.png', `-${n}.png`) : undefined });
  await page.waitForTimeout(500); await shot('before');
  await page.mouse.click(box.x + box.width * 0.8, box.y + box.height * 0.3); await page.waitForTimeout(600); await shot('after');
  const taps1 = await page.evaluate('window.__vu.vu.taps()');
  const emo = await page.evaluate('window.__vu.vu.name()');
  await page.waitForTimeout(1500);
  const frame = await page.evaluate('window.__vu.stats()');
  // pixels differ between before and after the tap
  const lit = await page.evaluate(() => { const c = document.getElementById('face').getContext('2d').getImageData(0, 0, 320, 240).data; let n = 0; for (let i = 0; i < c.length; i += 4) if (c[i] + c[i + 1] + c[i + 2] > 384) n++; return n; });
  await page.click('#lockSet'); await page.click('#lockTouch'); for (const k of [1, 2, 3, 4]) await page.click(`[data-k="${k}"]`);
  await page.click('#ladder'); await page.fill('#bat', '10'); await page.dispatchEvent('#bat', 'change');
  const cores = await page.locator('#cores').textContent();
  console.log(JSON.stringify({ readyMs, loadMs: await page.evaluate('window.__vu.loadMs'), tapsBefore: taps0, tapsAfter: taps1, emotionAfterTap: emo, litPixels: lit, frame, externalRequests: external, errors, cores: cores.split('\n').filter(Boolean) }, null, 1));
  await browser.close(); srv.close();
})();
