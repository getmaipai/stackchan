// The page: loads the two wasm modules, drives the face with requestAnimationFrame, shows measured numbers. Self-contained: no outside scripts.
(async function () {
  const t0 = performance.now();
  const face = await FaceModule();
  const cores = await CoresModule();
  const loadMs = performance.now() - t0;
  const api = (m, n, r, a) => m.cwrap(n, r, a);
  const vu = {
    init: api(face, 'vu_init', 'number', []), tick: api(face, 'vu_tick', 'number', ['number']),
    touch: api(face, 'vu_touch', null, ['number', 'number', 'number']), rgba: api(face, 'vu_rgba', 'number', []),
    emo: api(face, 'vu_set_emotion', null, ['number']), name: api(face, 'vu_emotion_name', 'string', []),
    speak: api(face, 'vu_speak', null, ['number']), taps: api(face, 'vu_taps', 'number', []),
  };
  const tInit = performance.now(); vu.init(); const initMs = performance.now() - tInit;
  const canvas = document.getElementById('face'), ctx = canvas.getContext('2d');
  const img = ctx.createImageData(320, 240);
  let frames = 0, tickMs = 0, last = performance.now(), worst = 0;
  function draw() {
    const now = performance.now(), dt = Math.min(100, now - last); last = now;
    const a = performance.now(); vu.tick(dt); const b = performance.now();
    img.data.set(face.HEAPU8.subarray(vu.rgba(), vu.rgba() + 320 * 240 * 4)); ctx.putImageData(img, 0, 0);
    const spent = b - a; tickMs += spent; worst = Math.max(worst, spent); frames++;
    requestAnimationFrame(draw);
  }
  requestAnimationFrame(draw);
  const pt = (e) => { const r = canvas.getBoundingClientRect(); return [Math.round((e.clientX - r.left) * 320 / r.width), Math.round((e.clientY - r.top) * 240 / r.height)]; };
  canvas.addEventListener('pointerdown', (e) => { canvas.setPointerCapture(e.pointerId); vu.touch(...pt(e), 0); });
  canvas.addEventListener('pointermove', (e) => { if (e.buttons) vu.touch(...pt(e), 1); });
  canvas.addEventListener('pointerup', (e) => vu.touch(...pt(e), 2));
  document.querySelectorAll('[data-emo]').forEach((b) => b.onclick = () => vu.emo(+b.dataset.emo));
  document.getElementById('speak').onchange = (e) => vu.speak(e.target.checked ? 60 : 0);
  const stats = document.getElementById('stats');
  setInterval(() => {
    stats.textContent = `wasm load+instantiate ${loadMs.toFixed(0)} ms, avatar init ${initMs.toFixed(1)} ms\n` +
      `frames ${frames}, vu_tick ${frames ? (tickMs / frames).toFixed(2) : 0} ms avg, ${worst.toFixed(1)} ms worst\n` +
      `emotion ${vu.name()}, taps ${vu.taps()}`;
  }, 500);
  window.__vu = { vu, face, cores, loadMs, initMs, stats: () => ({ frames, avgTickMs: tickMs / Math.max(1, frames), worst }) };

  // cores
  const C = (n, r, a) => api(cores, n, r, a);
  const lock = { reset: C('lock_reset', null, []), set: C('lock_set', 'number', ['string', 'string']), now: C('lock_lock_now', 'number', ['number']),
    touch: C('lock_touch', null, ['number']), key: C('lock_key', 'number', ['number', 'number']), status: C('lock_status', 'string', []),
    locked: C('lock_is_locked', 'number', []), reply: C('lock_reply', 'string', ['number']) };
  const lim = { reset: C('limit_reset', null, []), step: C('limit_step', null, ['number', 'number', 'number', 'number']), state: C('limit_state', 'string', []),
    scale: C('limit_scale', 'number', []), cap: C('limit_speed_cap', 'number', []), dance: C('limit_dance_max', 'number', []) };
  const sim = { new: C('sim_new', 'number', []), start: C('sim_start', null, ['number', 'number', 'number']), tick: C('sim_tick', 'number', ['number', 'number', 'number', 'number', 'number', 'number', 'number']),
    stage: C('sim_stage', 'number', ['number']) };
  const out = document.getElementById('cores'); const log = (s) => { out.textContent = (s + '\n' + out.textContent).slice(0, 2000); };
  let clock = 1000; // the fake clock, ms
  lock.reset(); lim.reset();
  document.getElementById('lockSet').onclick = () => { clock += 100; const r = lock.set('1234', ''); log('set code: ' + lock.reply(r)); log('lock now: ' + lock.reply(lock.now(clock)) + ' ' + lock.status()); };
  document.getElementById('lockTouch').onclick = () => { clock += 100; lock.touch(clock); log('touch: keypad shown'); };
  document.querySelectorAll('[data-k]').forEach((b) => b.onclick = () => { clock += 300; const ev = lock.key(48 + +b.dataset.k, clock); log(`key ${b.dataset.k}: event ${['none', 'UNLOCK', 'WRONG', 'CANCEL', 'IGNORED'][ev]} ${lock.status()}`); });
  const updateLimit = () => {
    clock += 2500;
    lim.step(clock, +document.getElementById('carried').checked, +document.getElementById('usb').checked, +document.getElementById('bat').value);
    lim.step(clock + 2500, +document.getElementById('carried').checked, +document.getElementById('usb').checked, +document.getElementById('bat').value);
    clock += 2500;
    log(`limit: state ${lim.state()} scale ${lim.scale()}% speed cap ${lim.cap()} dance max ${lim.dance()}`);
  };
  ['bat', 'usb', 'carried'].forEach((id) => document.getElementById(id).onchange = updateLimit);
  document.getElementById('ladder').onclick = () => {
    const s = sim.new(), avgp = cores._malloc(4); sim.start(s, 4, 1000); const stages = [];
    for (let t = 0; t < 60; t++) stages.push(sim.tick(s, 1000 + t * 1000, 500, 80, 4, 1, avgp));
    cores._free(avgp); log('ladder stage each second: ' + stages.join(''));
  };
})();
