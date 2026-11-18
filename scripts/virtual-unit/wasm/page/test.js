// The test harness page (test.html): the same modules and the same Python as the playground, without the viewer and its 3D drawing, so the parity cases run at the speed of the code, not of
// the software WebGL of a headless browser. Placement: host-side development tool (browser playground). Upstream: none.
(async function () {
  'use strict';
  const base = new URL('.', document.currentScript.src).href, T0 = performance.now(), marks = {};
  const script = (src) => new Promise((ok, bad) => { const s = document.createElement('script'); s.src = base + src; s.onload = ok; s.onerror = () => bad(new Error(src + ' did not load')); document.head.appendChild(s); });
  const out = document.getElementById('out');
  try {
    await Promise.all([script('engine.js'), script('bridge.js'), script('boot.js'), script('wasm/screens.js'), script('wasm/cores.js'), script('wasm/lock.js'), script('wasm/cover.js'), script('pyodide/pyodide.js')]);
    const fetchBin = async (u) => (await fetch(base + u)).arrayBuffer();
    const [zip, sigs] = await Promise.all([fetchBin('vu-py.zip'), fetch(base + 'wasm/cores.sigs.json').then((r) => r.json())]);
    const pyodide = await window.loadPyodide({ indexURL: base + 'pyodide/' }); marks.pyodide = Math.round(performance.now() - T0);
    const bridge = window.VuBridge.create({ factories: { screens: window.ScreensModule, lock: window.LockModule, cover: window.CoverModule, cores: window.CoresModule }, binary: (n) => fetchBin('wasm/' + n + '.wasm') });
    const pg = await window.VuBoot.start({ pyodide, bridge, zip, sigs, unit: false }); marks.ready = Math.round(performance.now() - T0);
    window.__playground = { pg, marks }; out.textContent = 'ready ' + JSON.stringify(marks);
  } catch (e) { out.textContent = 'failed: ' + e.message; console.error(e); }
})();
