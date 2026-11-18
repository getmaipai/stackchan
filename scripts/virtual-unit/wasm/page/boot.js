// Starts the virtual unit in the page (or in Node for the tests): the renderer pool, the cores, Pyodide with the unit's Python unpacked, and the API.
// start({ pyodide, bridge, zip, sigs }) -> playground: { py, api(method, path, body), tick(), newUnit(), run(code) }.
// Placement: host-side development tool (browser playground). Upstream: none.
(function (root) {
  'use strict';
  async function start(o) {
    const t0 = Date.now(), marks = {};
    const py = o.pyodide, bridge = o.bridge;
    root.vuBridge = bridge;   // Python reaches it as js.vuBridge
    await bridge.loadCores(o.sigs); marks.cores = Date.now() - t0;
    if (o.unit !== false) { await bridge.prepare('screens', 1); marks.screens = Date.now() - t0; }
    py.unpackArchive(new Uint8Array(o.zip), 'zip', { extractDir: '/' });
    py.runPython("import sys\nsys.path.insert(0, '/vu/site')\nimport js, wasm_shim\nwasm_shim.install(js.vuBridge)\nimport api\n");
    marks.python = Date.now() - t0;
    const api = py.pyimport('api');
    if (o.unit !== false) api.init(!!o.live);
    marks.unit = Date.now() - t0;
    const pg = {
      py, api, marks, bridge,
      request(method, path, body) { return JSON.parse(api.handle(method, path, body || '')); },
      tick() { return api.tick().toJs(); },
      run(code) { return py.runPython(code); },
      parityInit() {   // the cores as ctypes-shaped functions, for the parity cases
        py.FS.writeFile('/vu/site/cores.sigs.json', JSON.stringify(o.sigs));
        py.runPython("import json, parity_cases, wasm_shim\nparity_cases.configure(wasm_shim.WasmLib('cores'), json.load(open('/vu/site/cores.sigs.json')))\n");
      },
      async runCase(id) {   // a fresh renderer first when the case starts one, then the case; returns its JSON text
        const pc = py.pyimport('parity_cases');
        const kind = pc.needs(id);
        if (kind) await bridge.prepare(kind, 1);
        return pc.run(id);
      },
      async cases() { return py.pyimport('parity_cases').all_cases().toJs(); },
    };
    return pg;
  }
  const out = { start };
  if (typeof module !== 'undefined' && module.exports) module.exports = out; else root.VuBoot = out;
})(typeof self !== 'undefined' ? self : globalThis);
