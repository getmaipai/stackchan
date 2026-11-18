// The bridge between the Python virtual unit (Pyodide) and the WebAssembly modules: renderer instances (screens, lock, cover) and the C cores. Python calls it synchronously
// (the `js` module); anything that has to wait (compiling a module) happens before, in prepare(). A renderer instance is one fresh native-program state, as one process was.
// Works in a page and in Node. Placement: host-side development tool (browser playground). Upstream: none.
(function (root) {
  'use strict';
  const E = root.VuEngine || (typeof require !== 'undefined' ? require('./engine.js') : null);

  function create(opts) {
    // opts.factories {screens, lock, cover, cores}: the Emscripten module factories; opts.binary(name) -> Promise<ArrayBuffer|Buffer> the wasm bytes (fetched once, reused by every instance)
    const bin = {}, pools = { screens: [], lock: [], cover: [] }, live = new Map();
    let nextId = 1, cores = null, sigs = null;
    async function binary(name) { if (!bin[name]) bin[name] = await opts.binary(name); return bin[name]; }
    async function instantiate(kind) {
      const wasmBinary = await binary(kind);
      const factory = opts.factories[kind];
      const eng = await E.load((o) => factory(Object.assign({ wasmBinary }, o)));
      return eng;
    }
    const api = {
      timings: {},
      async prepare(kind, n) {   // make sure n fresh instances of a renderer are ready for Python to take
        while (pools[kind].length < n) { const t0 = Date.now(); pools[kind].push(await instantiate(kind)); api.timings[kind + 'InstantiateMs'] = Date.now() - t0; }
      },
      take(kind) {   // Python: a fresh instance; returns its id
        const eng = pools[kind].shift();
        if (!eng) throw new Error('no fresh ' + kind + ' renderer is ready: call bridge.prepare("' + kind + '", 1) before starting a unit, then try again');
        const id = nextId++; live.set(id, { kind, eng }); return id;
      },
      cmd(id, line) { return live.get(id).eng.cmd(line).join('\n'); },
      file(id, path) { return live.get(id).eng.file(path); },
      drop(id, path) { live.get(id).eng.drop(path); },
      engine(id) { return live.get(id).eng; },
      release(id) { live.delete(id); },
      liveCount() { return live.size; },
      // ---- cores ----
      async loadCores(sigsJson) {
        const wasmBinary = await binary('cores');
        cores = await opts.factories.cores({ wasmBinary }); sigs = sigsJson;
        return Object.keys(sigsJson.functions).length;
      },
      coreCall(name, ret, args) {   // ret: 'i' int, 'u' unsigned, 'f' float, 's' string, 'v' void; args: numbers or strings
        if (!cores) throw new Error('the cores module is not loaded: call bridge.loadCores first');
        const types = args.map((a) => (typeof a === 'string' ? 'string' : 'number'));
        const r = cores.ccall(name, ret === 's' ? 'string' : (ret === 'v' ? null : 'number'), types, args);
        return ret === 'u' ? (r >>> 0) : r;
      },
      coreSig(name) { return sigs && sigs.functions[name] ? JSON.stringify(sigs.functions[name]) : ''; },
      coreMalloc(n) { return cores._malloc(n); },
      coreFree(p) { cores._free(p); },
      coreWrite(p, bytes) { cores.HEAPU8.set(bytes, p); },
      coreRead(p, n) { return cores.HEAPU8.slice(p, p + n); },
    };
    return api;
  }
  const out = { create };
  if (typeof module !== 'undefined' && module.exports) module.exports = out; else root.VuBridge = out;
})(typeof self !== 'undefined' ? self : globalThis);
