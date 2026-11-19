// The renderer bridge: one native renderer program built as WebAssembly (screens, lock or cover), driven by command lines exactly as the native program is on stdin.
// cmd(line) runs one command and returns the lines the program printed; fb565() is the live frame buffer; file(path) reads a file the program wrote (a snap PNG).
// Works in a page and in Node. Placement: host-side development tool (browser playground). Upstream: none.
(function (root) {
  'use strict';
  async function load(factory) {
    const lines = [];
    const mod = await factory({ print: (t) => lines.push(t), printErr: (t) => { if (!/^unknown overlay/.test(t)) lines.push('stderr: ' + t); } });
    mod._vu_init();
    const cmd = mod.cwrap('vu_cmd', null, ['string']);
    return {
      mod,
      cmd(line) {
        lines.length = 0;
        const m = /^(snap|snapnow|sheet|lock|pad)\s.*?(\/\S+)\s*$/.exec(line);   // a command that writes a PNG: the folder has to exist in the module's memory file system
        if (m) { const d = m[2].replace(/\/[^/]*$/, ''); if (d) mod.FS.mkdirTree(d); }
        cmd(line); return lines.slice();
      },
      fbPtr() { return mod._vu_fb(); },
      fb565() { return mod.HEAPU8.subarray(mod._vu_fb(), mod._vu_fb() + 320 * 240 * 2); },
      file(path) { return mod.FS.readFile(path); },
      drop(path) { try { mod.FS.unlink(path); } catch (e) { /* not there */ } },
    };
  }
  // RGB565 (little endian) to RGBA, the way the renderers' own PNG writers expand it (v * 255 / 31 and v * 255 / 63)
  function rgba(fb, out) {
    out = out || new Uint8ClampedArray(320 * 240 * 4);
    for (let i = 0, j = 0; i < 320 * 240; i++, j += 4) {
      const v = fb[i * 2] | (fb[i * 2 + 1] << 8);
      out[j] = (((v >> 11) & 31) * 255 / 31) | 0; out[j + 1] = (((v >> 5) & 63) * 255 / 63) | 0; out[j + 2] = ((v & 31) * 255 / 31) | 0; out[j + 3] = 255;
    }
    return out;
  }
  const api = { load, rgba };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.VuEngine = api;
})(typeof self !== 'undefined' ? self : globalThis);
