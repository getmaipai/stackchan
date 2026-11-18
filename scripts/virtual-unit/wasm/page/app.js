// The playground's loader and router. It loads the WebAssembly modules and Pyodide from this site's own folders (no outside address), starts the virtual unit's Python, and answers
// the viewer's requests (the ones view.py answers over HTTP on the native playground) in the page. view.html and view3d.js run unchanged on top of it.
// Placement: host-side development tool (browser playground). Upstream: none.
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const base = new URL('.', document.currentScript.src).href;
  const T0 = performance.now();
  const marks = { start: 0 };
  let readyResolve; const ready = new Promise((r) => { readyResolve = r; });
  let pg = null, screensId = 0;
  const realFetch = window.fetch.bind(window);
  const note = (t, d) => { const a = $('pgboot-text'), b = $('pgboot-detail'); if (a && t) a.textContent = t; if (b) b.textContent = d || ''; };
  const failBoot = (err) => { note('The virtual unit did not start: ' + (err && err.message ? err.message : err), 'Reload the page. If it happens again, open the browser console (it has the full message) and report it with the browser name and version.'); console.error(err); };

  // ---- requests the viewer makes by absolute path ----
  const STATIC = { '/model/stackchan.glb': 'model/stackchan.web.glb', '/model/stackchan.web.glb': 'model/stackchan.web.glb', '/talk.js': 'talk.js', '/view3d.js': 'view3d.js' };
  const b64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
  window.fetch = async function (url, opts) {
    if (typeof url !== 'string' || url[0] !== '/') return realFetch(url, opts);
    const path = url.split('?')[0];
    if (STATIC[path]) return realFetch(base + STATIC[path], opts);
    if (path === '/physics.js' || path.indexOf('/physics/') === 0) return new Response('The physics engine is not part of the browser build.', { status: 404, headers: { 'Content-Type': 'text/plain' } });
    await ready;
    const method = (opts && opts.method) || 'GET';
    const r = pg.request(method, url.split('?')[0], (opts && opts.body) || '');
    const body = r.body_b64 ? b64(r.body_b64) : r.body;
    return new Response(body, { status: r.code, headers: { 'Content-Type': r.type || 'text/plain' } });
  };

  // ---- the screen: view3d.js asks for /frame.png about 20 times a second; it gets the unit's current frame ----
  const cv = document.createElement('canvas'); cv.width = 320; cv.height = 240;
  const cx = cv.getContext('2d'); const img = cx.createImageData(320, 240);
  let frameUrl = '', lastFrameId = -1;
  const setBlob = () => cv.toBlob((b) => { if (!b) return; const old = frameUrl; frameUrl = URL.createObjectURL(b); if (old) URL.revokeObjectURL(old); }, 'image/png');
  const srcDesc = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src'); const NativeImage = window.Image;
  window.Image = function () {
    const i = new NativeImage();
    Object.defineProperty(i, 'src', { configurable: true, get() { return srcDesc.get.call(i); }, set(v) { srcDesc.set.call(i, /\/frame\.png/.test(v) ? (frameUrl || 'data:image/gif;base64,R0lGODlhAQABAAAAACw=') : v); } });
    return i;
  };
  window.__frame = { canvas: cv };
  async function paint(r) {
    if (r.png) {
      if (r.frame_id === lastFrameId) return;
      lastFrameId = r.frame_id;
      const bytes = pg.api.frame_png().toJs();
      const bmp = await createImageBitmap(new Blob([bytes], { type: 'image/png' })); cx.drawImage(bmp, 0, 0); setBlob();
      return;
    }
    lastFrameId = -1;
    window.VuEngine.rgba(pg.bridge.engine(screensId).fb565(), img.data); cx.putImageData(img, 0, 0); setBlob();
  }

  // ---- loading ----
  const script = (src) => new Promise((ok, bad) => { const s = document.createElement('script'); s.src = base + src; s.onload = ok; s.onerror = () => bad(new Error(src + ' did not load: check that the page and its wasm, pyodide and vendor folders were published together')); document.head.appendChild(s); });
  async function boot() {
    note('Loading the virtual unit: the screens renderer, the unit\'s C cores and its Python (about 6 MB over the wire, once; the browser keeps it).', '');
    await Promise.all([script('engine.js'), script('bridge.js'), script('boot.js'), script('wasm/screens.js'), script('wasm/cores.js'), script('pyodide/pyodide.js')]);
    marks.scripts = Math.round(performance.now() - T0);
    const fetchBin = async (u) => { const r = await realFetch(base + u); if (!r.ok) throw new Error(u + ' answered ' + r.status + ': rebuild the site with scripts/virtual-unit/wasm/site-build.sh'); return r.arrayBuffer(); };
    const [zip, sigsText] = await Promise.all([fetchBin('vu-py.zip'), realFetch(base + 'wasm/cores.sigs.json').then((r) => r.text())]);
    note(null, 'Starting Python (Pyodide)...');
    const pyodide = await window.loadPyodide({ indexURL: base + 'pyodide/' });
    marks.pyodide = Math.round(performance.now() - T0);
    const factories = { screens: window.ScreensModule, cores: window.CoresModule };
    const lazy = { lock: 'wasm/lock.js', cover: 'wasm/cover.js' }, loaded = {};
    const bridge = window.VuBridge.create({ factories: new Proxy(factories, { get(t, k) { return t[k]; } }), binary: (n) => fetchBin('wasm/' + n + '.wasm') });
    bridge.ensureKind = async (k) => { if (lazy[k] && !loaded[k]) { await script(lazy[k]); factories[k] = window[k === 'lock' ? 'LockModule' : 'CoverModule']; loaded[k] = true; } };
    pg = await window.VuBoot.start({ pyodide, bridge, zip, sigs: JSON.parse(sigsText), live: true });
    screensId = pg.py.pyimport('api').screens_id();
    marks.unit = Math.round(performance.now() - T0);
    window.__playground = { pg, marks, bridge, paint, lastTick: null, ticks: 0, tickMs: 0, tickWorstMs: 0 };
    readyResolve();
    $('pgboot').classList.add('done');
    bridge.ensureKind('cover').then(() => bridge.prepare('cover', 1)).catch(() => {});   // the boot cover needs a fresh renderer at hand when the unit is switched on
    let busy = false;
    const pump = setInterval(async () => {
      if (busy) return; busy = true;
      try {
        const a = performance.now(); const r = pg.tick(); const spent = performance.now() - a;
        const P = window.__playground; P.ticks++; P.tickMs += spent; P.tickWorstMs = Math.max(P.tickWorstMs, spent); P.lastTick = r;
        await paint(r);
        if (bridge.poolSize('cover') === 0 && loaded.cover) bridge.prepare('cover', 1).catch(() => {});
      } catch (e) { console.error(e); } finally { busy = false; }
    }, 50);
    window.__playground.stop = () => clearInterval(pump);
    wireExtras(bridge);
  }

  // ---- extras next to the viewer: the language switch and the lock keypad and cover screens ----
  function wireExtras(bridge) {
    $('pglang').onchange = (e) => { pg.api.set_language(e.target.value); document.documentElement.lang = e.target.value; };
    const side = $('side'); if (!side) return;
    const sec = document.createElement('section'); sec.id = 'pggal';
    sec.innerHTML = '<h2>Lock keypad and covers</h2><div class="t" style="font-size:12px;margin-bottom:6px">The unit\'s own lock screen, keypad and link covers, drawn by the same code. Pick one.</div>'
      + '<select id="pgscr"></select><div style="margin-top:8px"><img id="pgimg" alt="the selected screen"></div>';
    side.appendChild(sec);
    const names = pg.py.pyimport('api').extra_screens().toJs(); const sel = $('pgscr');
    names.forEach((n) => { const o = document.createElement('option'); o.value = n; o.textContent = n; sel.appendChild(o); });
    sel.onchange = async () => {
      const n = sel.value, kind = /^lock/.test(n) ? 'lock' : 'cover';
      await bridge.ensureKind(kind); await bridge.prepare(kind, 1);
      const png = pg.py.pyimport('api').extra_screen(n).toJs();
      $('pgimg').src = URL.createObjectURL(new Blob([png], { type: 'image/png' }));
    };
    sel.onchange();
  }
  boot().catch(failBoot);
})();
