// Headless check of the 3D viewer page over a plain static server. Usage: node browser_check.js URL [screenshot.png]
// Prints one JSON line. Exits 2 when no browser or no WebGL is available (the caller then falls back to a file check).
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], shot = process.argv[3];
  let browser;
  try { browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] }); }
  catch (e) { console.log(JSON.stringify({ skipped: 'no browser: ' + e.message.split('\n')[0] })); process.exit(2); }
  const page = await browser.newPage({ viewport: { width: 1100, height: 800 } });
  const errors = [], glb = [], external = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('response', r => { if (/\.glb$/.test(r.url())) glb.push({ status: r.status(), bytes: 0, url: r.url() }); });
  page.on('request', r => { if (!r.url().startsWith(new URL(url).origin) && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) external.push(r.url()); });
  await page.goto(url, { waitUntil: 'load' });
  let ready = false;
  try { await page.waitForFunction(() => window.ROBOT && window.ROBOT.model && window.ROBOT.model.ready, null, { timeout: 20000 }); ready = true; } catch (e) { /* reported below */ }
  const out = { ready, glb, errors, external };
  if (ready) {
    await page.fill('#yaw', '40'); await page.dispatchEvent('#yaw', 'input');
    await page.click('#insideLabel, #inside').catch(() => {});
    await page.waitForTimeout(600);
    out.head = await page.evaluate(() => ({ yaw: window.VIEWER_STATE.head.yaw, label: document.getElementById('hd').textContent }));
    out.parts = await page.evaluate(() => window.ROBOT.model.parts.length);
    if (shot) await page.screenshot({ path: shot });
  } else if (errors.length && /WebGL|context/i.test(errors.join(' ') + (await page.textContent('#msg')))) { out.skipped = 'no WebGL in this browser'; }
  console.log(JSON.stringify(out));
  await browser.close();
  process.exit(ready ? 0 : (out.skipped ? 2 : 1));
})();
