// The 3D StackChan of the virtual unit view: the real body proportions, orbit camera, clickable USB-C port and power button, two servo axes.
// Units: 1 unit = 1 cm. Sizes come from the maker's data sheet (M5Stack K151: 54.0 x 70.5 x 61.5 mm overall, the CoreS3 head 54 x 54 x 15.5 mm,
// a 2 inch screen with a 40.8 x 30.6 mm picture); the shape of the neck and base is an approximation from the product photos, kept in DIMS so it can be corrected in one place.
// The flat screen stays the truth source: this file only wraps /frame.png on a body. Placement: host-side development tool; no firmware change.
const DIMS = {
  head: {w: 5.4, h: 5.4, d: 1.55, r: 0.55},        // CoreS3 enclosure (width, height, depth, corner radius)
  screen: {w: 4.08, h: 3.06},                       // the 2 inch picture, 4:3 like the 320 by 240 panel
  bezel: {w: 4.7, h: 3.7},
  base: {w: 5.4, h: 0.8, d: 6.15, r: 0.35, y: 0.2}, // the whole robot is 54.0 wide and 61.5 to 62.0 deep
  feet: {r: 0.34, h: 0.2},
  yawHousing: {r: 1.35, h: 0.9},                    // the pan servo under the neck
  pitchAxisY: 2.0,                                  // height of the nod axis above the table
  tiltServo: {w: 2.6, h: 2.1, d: 2.0, z: -1.5},     // the nod servo behind the head
  total: {w: 5.4, h: 7.05, d: 6.15},                // 70.5 mm tall with the head upright
  port: {w: 0.9, h: 0.32, y: 0.6},                  // USB-C on the back of the base
  button: {r: 0.28, y: 0.62, z: -1.1},              // power button on the right side of the base
};
function initRobot(THREE, canvas, hooks) {
  const cv = canvas;
  const r = new THREE.WebGLRenderer({canvas: cv, antialias: true});
  r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15181d);
  const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 1.0));
  const key = new THREE.DirectionalLight(0xffffff, 0.9); key.position.set(8, 14, 12); scene.add(key);
  const rim = new THREE.DirectionalLight(0x88aaff, 0.4); rim.position.set(-9, 6, -10); scene.add(rim);

  const white = new THREE.MeshStandardMaterial({color: 0xeceff3, roughness: 0.45});
  const gray = new THREE.MeshStandardMaterial({color: 0x39424e, roughness: 0.6});
  const dark = new THREE.MeshStandardMaterial({color: 0x15181c, roughness: 0.8});
  const rubber = new THREE.MeshStandardMaterial({color: 0x20242a, roughness: 0.95});

  function roundedBox(w, h, d, rad, mat) {
    const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
    s.moveTo(x + rad, y); s.lineTo(x + w - rad, y); s.absarc(x + w - rad, y + rad, rad, -Math.PI / 2, 0);
    s.lineTo(x + w, y + h - rad); s.absarc(x + w - rad, y + h - rad, rad, 0, Math.PI / 2);
    s.lineTo(x + rad, y + h); s.absarc(x + rad, y + h - rad, rad, Math.PI / 2, Math.PI);
    s.lineTo(x, y + rad); s.absarc(x + rad, y + rad, rad, Math.PI, 1.5 * Math.PI);
    const g = new THREE.ExtrudeGeometry(s, {depth: d, bevelEnabled: false, curveSegments: 10});
    g.translate(0, 0, -d / 2);
    return new THREE.Mesh(g, mat);
  }

  const robot = new THREE.Group(); scene.add(robot);
  // table
  const table = new THREE.Mesh(new THREE.CircleGeometry(16, 64), new THREE.MeshStandardMaterial({color: 0x1b2027, roughness: 1}));
  table.rotation.x = -Math.PI / 2; scene.add(table);
  const grid = new THREE.GridHelper(32, 32, 0x2a323d, 0x222932); grid.position.y = 0.01; scene.add(grid);

  // base with feet
  const B = DIMS.base;
  const baseShape = new THREE.Mesh(new THREE.BoxGeometry(B.w, B.h, B.d), white);
  baseShape.position.set(0, B.y + B.h / 2, 0); robot.add(baseShape);
  for (const [fx, fz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    const f = new THREE.Mesh(new THREE.CylinderGeometry(DIMS.feet.r, DIMS.feet.r, DIMS.feet.h, 20), rubber);
    f.position.set(fx * (B.w / 2 - 0.55), DIMS.feet.h / 2, fz * (B.d / 2 - 0.55)); robot.add(f);
  }
  // USB-C port on the back face, and a bigger invisible target to click
  const port = new THREE.Mesh(new THREE.BoxGeometry(DIMS.port.w, DIMS.port.h, 0.12), dark);
  port.position.set(0, DIMS.port.y, -B.d / 2 - 0.005); robot.add(port);
  const portHit = new THREE.Mesh(new THREE.BoxGeometry(2.2, 1.0, 0.8), new THREE.MeshBasicMaterial({visible: false}));
  portHit.position.set(0, DIMS.port.y, -B.d / 2 - 0.2); robot.add(portHit);
  // power button on the right side
  const btn = new THREE.Mesh(new THREE.CylinderGeometry(DIMS.button.r, DIMS.button.r, 0.14, 24), new THREE.MeshStandardMaterial({color: 0x888e96, emissive: 0x000000}));
  btn.rotation.z = Math.PI / 2; btn.position.set(B.w / 2 + 0.05, DIMS.button.y, DIMS.button.z); robot.add(btn);
  const btnHit = new THREE.Mesh(new THREE.SphereGeometry(0.8, 8, 8), new THREE.MeshBasicMaterial({visible: false}));
  btnHit.position.copy(btn.position); robot.add(btnHit);
  // the cable
  const cable = new THREE.Group(); cable.visible = false; robot.add(cable);
  const pz = -B.d / 2;
  const plug = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.55, 1.4), new THREE.MeshStandardMaterial({color: 0xb7bcc4, metalness: 0.5, roughness: 0.35}));
  plug.position.set(0, DIMS.port.y, pz - 0.7); cable.add(plug);
  const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(0, DIMS.port.y, pz - 1.4), new THREE.Vector3(0, DIMS.port.y, pz - 3), new THREE.Vector3(1.5, 0.3, pz - 5.5), new THREE.Vector3(3.5, 0.25, pz - 9), new THREE.Vector3(5, 0.25, pz - 13)]);
  cable.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.16, 10, false), new THREE.MeshStandardMaterial({color: 0x2a2f36, roughness: 0.7})));
  // power LED in the cable plug while charging
  const chargeLed = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 10), new THREE.MeshBasicMaterial({color: 0x222222}));
  chargeLed.position.set(0.9, DIMS.port.y + 0.35, pz - 0.2); robot.add(chargeLed);

  // the yaw group turns about the vertical axis through the neck; the pitch group nods about the horizontal axis
  const yawG = new THREE.Group(); yawG.position.set(0, B.y + B.h, 0); robot.add(yawG);
  const housing = new THREE.Mesh(new THREE.CylinderGeometry(DIMS.yawHousing.r, DIMS.yawHousing.r * 1.08, DIMS.yawHousing.h, 40), gray);
  housing.position.y = DIMS.yawHousing.h / 2; yawG.add(housing);
  const ringLeds = [];
  for (let i = 0; i < 12; i++) {  // the ring of 12 lights around the neck (position is a stand-in: the unit's lights are 12 RGB LEDs)
    const a = (i / 12) * Math.PI * 2;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 10), new THREE.MeshBasicMaterial({color: 0x222222}));
    m.position.set(Math.sin(a) * (DIMS.yawHousing.r * 1.05), DIMS.yawHousing.h * 0.55, Math.cos(a) * (DIMS.yawHousing.r * 1.05)); yawG.add(m); ringLeds.push(m);
  }
  const pitchBase = DIMS.pitchAxisY - (B.y + B.h);  // the pitch axis height above the yaw group origin
  const T = DIMS.tiltServo;
  const servo = new THREE.Mesh(new THREE.BoxGeometry(T.w, T.h, T.d), gray); servo.position.set(0, pitchBase + 0.2, T.z); yawG.add(servo);
  const pitchG = new THREE.Group(); pitchG.position.set(0, pitchBase, 0); yawG.add(pitchG);
  const horn = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 0.5, 28), new THREE.MeshStandardMaterial({color: 0xaab0b8, metalness: 0.4, roughness: 0.4}));
  horn.rotation.x = Math.PI / 2; horn.position.set(0, 0, -0.55); pitchG.add(horn);
  const H = DIMS.head;
  const headCenterY = DIMS.total.h - H.h / 2 - DIMS.pitchAxisY;  // 70.5 mm overall with the head upright
  const head = new THREE.Group(); head.position.set(0, headCenterY, 0); pitchG.add(head);
  head.add(roundedBox(H.w, H.h, H.d, H.r, white));
  const tex = new THREE.Texture(); tex.minFilter = THREE.LinearFilter; tex.colorSpace = THREE.SRGBColorSpace || undefined;
  const bezel = new THREE.Mesh(new THREE.PlaneGeometry(DIMS.bezel.w, DIMS.bezel.h), new THREE.MeshBasicMaterial({color: 0x07090c}));
  bezel.position.set(0, 0.2, H.d / 2 + 0.004); head.add(bezel);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(DIMS.screen.w, DIMS.screen.h), new THREE.MeshBasicMaterial({map: tex}));
  screen.position.set(0, 0.2, H.d / 2 + 0.008); head.add(screen);
  const cam1 = new THREE.Mesh(new THREE.CircleGeometry(0.1, 16), new THREE.MeshBasicMaterial({color: 0x0a0c10}));
  cam1.position.set(0, 0.2 + DIMS.bezel.h / 2 + 0.35, H.d / 2 + 0.008); head.add(cam1);   // the camera above the screen
  for (const sx of [-1, 1]) for (let k = 0; k < 3; k++) {  // microphone holes
    const hole = new THREE.Mesh(new THREE.CircleGeometry(0.04, 8), new THREE.MeshBasicMaterial({color: 0x9aa1ab}));
    hole.position.set(sx * (1.1 + k * 0.18), 0.2 - DIMS.bezel.h / 2 - 0.4, H.d / 2 + 0.008); head.add(hole);
  }

  // axes gizmo: the yaw arc (green, flat above the base) and the pitch arc (red, in the side plane), each with its limits and a live pointer
  const axes = new THREE.Group(); robot.add(axes);
  function arc(pts, color, width) {
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    return new THREE.Line(g, new THREE.LineBasicMaterial({color, linewidth: width || 1}));
  }
  const yawArcR = 4.3, pitchArcR = 3.9;
  function yawPoint(deg, rad) { const a = -deg * Math.PI / 180; return new THREE.Vector3(Math.sin(a) * rad, 0, Math.cos(a) * rad); }
  const yawGizmo = new THREE.Group(); yawGizmo.position.set(0, B.y + B.h + 0.05, 0); axes.add(yawGizmo);
  const pitchGizmo = new THREE.Group(); pitchGizmo.position.set(0, DIMS.pitchAxisY, 0); axes.add(pitchGizmo);
  const yawLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 9.5, 8), new THREE.MeshBasicMaterial({color: 0x3ddc84}));
  yawLine.position.set(0, DIMS.total.h / 2 + 0.4, 0); axes.add(yawLine);
  const pitchLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 8.2, 8), new THREE.MeshBasicMaterial({color: 0xff6b6b}));
  pitchLine.rotation.z = Math.PI / 2; pitchLine.position.set(0, DIMS.pitchAxisY, 0); axes.add(pitchLine);
  let yawPointer = null, pitchPointer = null, rangeKey = '';
  function buildRanges(yr, pr, ps) {
    const k = [yr, pr, ps].join();
    if (k === rangeKey) return; rangeKey = k;
    yawGizmo.clear(); pitchGizmo.clear();
    const yp = []; for (let d = yr[0]; d <= yr[1]; d += 4) yp.push(yawPoint(d, yawArcR));
    yawGizmo.add(arc(yp, 0x3ddc84));
    for (const d of yr) yawGizmo.add(arc([new THREE.Vector3(), yawPoint(d, yawArcR + 0.4)], 0x3ddc84));
    yawGizmo.add(arc([new THREE.Vector3(), yawPoint(0, yawArcR + 0.3)], 0x2a6d4a));
    yawPointer = new THREE.Mesh(new THREE.SphereGeometry(0.22, 14, 14), new THREE.MeshBasicMaterial({color: 0x3ddc84})); yawGizmo.add(yawPointer);
    // pitch: angle 0 faces forward (+z), positive looks up; the arc is drawn at the right of the head
    const pp = (deg, rad) => new THREE.Vector3(3.2, Math.sin(deg * Math.PI / 180) * rad, Math.cos(deg * Math.PI / 180) * rad);
    const full = []; for (let d = pr[0]; d <= pr[1]; d += 3) full.push(pp(d, pitchArcR));
    pitchGizmo.add(arc(full, 0x7a3a3a));
    const safe = []; for (let d = ps[0]; d <= ps[1]; d += 3) safe.push(pp(d, pitchArcR));
    pitchGizmo.add(arc(safe, 0xff6b6b));
    for (const d of pr) pitchGizmo.add(arc([new THREE.Vector3(3.2, 0, 0), pp(d, pitchArcR + 0.4)], 0xff6b6b));
    pitchPointer = new THREE.Mesh(new THREE.SphereGeometry(0.2, 14, 14), new THREE.MeshBasicMaterial({color: 0xff6b6b})); pitchGizmo.add(pitchPointer);
    pitchPointer.userData.pp = pp;
  }

  // ---- the orbit camera
  const target = new THREE.Vector3(0, 3.3, 0);
  const view = {az: 0.55, el: 0.35, dist: 22};
  const HOME = {az: 0.55, el: 0.35, dist: 22};
  function placeCam() {
    const ce = Math.cos(view.el);
    cam.position.set(target.x + view.dist * ce * Math.sin(view.az), target.y + view.dist * Math.sin(view.el), target.z + view.dist * ce * Math.cos(view.az));
    cam.lookAt(target);
  }
  const preset = (az, el, dist) => { Object.assign(view, {az, el, dist: dist || HOME.dist}); };
  hooks.presets = {reset: () => preset(HOME.az, HOME.el, HOME.dist), front: () => preset(0, 0.05, 20), side: () => preset(Math.PI / 2, 0.05, 20), back: () => preset(Math.PI - 0.5, 0.25, 20), top: () => preset(0, 1.5, 24)};
  function size() {
    const w = cv.clientWidth || 1, h = cv.clientHeight || 1; r.setSize(w, h, false); cam.aspect = w / h;
    cam.fov = w / h < 0.9 ? 52 : 35; cam.updateProjectionMatrix();
  }
  addEventListener('resize', size); size();

  // ---- picking: the screen is touch, the port and the button are switches, everything else orbits
  const ray = new THREE.Raycaster(), v2 = new THREE.Vector2();
  function pick(ev, list) {
    const b = cv.getBoundingClientRect();
    v2.set(((ev.clientX - b.left) / b.width) * 2 - 1, -((ev.clientY - b.top) / b.height) * 2 + 1);
    ray.setFromCamera(v2, cam);
    return ray.intersectObjects(list, false)[0] || null;
  }
  function panelXY(ev) {
    const hit = pick(ev, [screen]);
    return hit && hit.uv ? {x: Math.round(hit.uv.x * 319), y: Math.round((1 - hit.uv.y) * 239)} : null;
  }
  const pointers = new Map(); let drag = null, pinch0 = 0;
  cv.addEventListener('pointerdown', e => {
    cv.setPointerCapture(e.pointerId); pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch0 = Math.hypot(a.x - b.x, a.y - b.y); drag = {mode: 'pinch', d0: view.dist}; return; }
    const p = panelXY(e);
    if (p && hooks.on()) drag = {mode: 'touch', p, cx: e.clientX, cy: e.clientY, t: performance.now()};
    else if (pick(e, [portHit])) drag = {mode: 'port', cx: e.clientX, cy: e.clientY};
    else if (pick(e, [btnHit])) drag = {mode: 'button', cx: e.clientX, cy: e.clientY};
    else drag = {mode: 'orbit', lx: e.clientX, ly: e.clientY};
  });
  cv.addEventListener('pointermove', e => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (drag && drag.mode === 'pinch' && pointers.size === 2) { const [a, b] = [...pointers.values()]; view.dist = Math.max(6, Math.min(48, drag.d0 * pinch0 / Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)))); return; }
    if (drag && drag.mode === 'orbit') {
      view.az -= (e.clientX - drag.lx) * 0.008; view.el = Math.max(-0.2, Math.min(1.5, view.el + (e.clientY - drag.ly) * 0.006)); drag.lx = e.clientX; drag.ly = e.clientY; return;
    }
    if (!drag) cv.style.cursor = (pick(e, [portHit]) || pick(e, [btnHit]) || (panelXY(e) && hooks.on())) ? 'pointer' : 'grab';
  });
  function end(e) {
    pointers.delete(e.pointerId);
    const d = drag; if (pointers.size === 0) drag = null; if (!d) return;
    const moved = d.cx === undefined ? 99 : Math.hypot(e.clientX - d.cx, e.clientY - d.cy);
    if (d.mode === 'touch') {
      const up = panelXY(e) || d.p;
      hooks.touch(moved > 12 ? {kind: 'swipe', x: d.p.x, y: d.p.y, x2: up.x, y2: up.y, ms: Math.max(120, Math.min(900, performance.now() - d.t))} : {kind: 'tap', x: d.p.x, y: d.p.y});
    } else if (d.mode === 'port' && moved < 8) hooks.togglePort();
    else if (d.mode === 'button' && moved < 8) hooks.togglePower();
  }
  cv.addEventListener('pointerup', end); cv.addEventListener('pointercancel', end);
  cv.addEventListener('wheel', e => { e.preventDefault(); view.dist = Math.max(6, Math.min(48, view.dist * Math.exp(e.deltaY * 0.0012))); }, {passive: false});
  cv.style.touchAction = 'none'; cv.style.cursor = 'grab';

  const img = new Image(); let off = true;
  img.onload = () => { tex.image = img; tex.needsUpdate = true; };
  setInterval(() => { img.src = '/frame.png?' + Date.now(); }, 100);

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  let cy = 0, cp = 0;
  const api = {
    update(st) {
      this.st = st;
    },
    frame() {
      const st = this.st; if (!st) return;
      hooks.axesVisible() ? axes.visible = true : axes.visible = false;
      buildRanges(st.yaw_range, st.pitch_range, st.pitch_safe);
      cy += (st.head.yaw - cy) * 0.35; cp += (st.head.pitch - cp) * 0.35;
      yawG.rotation.y = -cy * Math.PI / 180;      // sign convention: positive yaw turns the head to the viewer's left (unverified against the unit)
      pitchG.rotation.x = -cp * Math.PI / 180;    // positive pitch looks up
      if (yawPointer) yawPointer.position.copy(yawPoint(cy, yawArcR));
      if (pitchPointer) { const p = pitchPointer.userData.pp(cp, pitchArcR); pitchPointer.position.copy(p); }
      const on = st.hw.on, leds = st.leds || [];
      ringLeds.forEach((m, i) => { const c = on && leds[i] ? leds[i] : [0, 0, 0]; m.material.color.setRGB(Math.max(0.1, c[0] / 255), Math.max(0.1, c[1] / 255), Math.max(0.1, c[2] / 255)); });
      cable.visible = st.hw.usb;
      chargeLed.material.color.set(st.hw.usb ? (st.hw.charging ? 0xffb020 : 0x46be6e) : 0x222222);
      btn.material.emissive.set(on ? 0x1f7a3c : 0x000000);
      screen.material.color.set(on ? 0xffffff : 0x000000);
    },
    render() { placeCam(); r.render(scene, cam); },
    screen,
  };
  return api;
}
