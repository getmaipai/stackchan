// The 3D StackChan of the virtual unit view: the rigged body model (model/stackchan.glb, built from the official structure files),
// orbit camera, clickable USB-C port and power button, two servo axes, live screen and lights.
// Units: 1 unit = 1 cm; the model is in meters and is scaled by 100. Every size, joint axis and limit comes from the model's own nodes
// (see model/README.md); nothing is measured here.
// The flat screen stays the truth source: this file only wraps /frame.png on the body. Placement: host-side development tool; no firmware change.

// Read a binary glTF file into three.js objects. The model has one embedded buffer, no textures and no extensions, so this small reader
// covers it and the page needs no second script from the network.
function readGlb(THREE, bytes) {
  const dv = new DataView(bytes);
  if (dv.getUint32(0, true) !== 0x46546C67) throw new Error('not a glb file');
  const jsonLen = dv.getUint32(12, true);
  const doc = JSON.parse(new TextDecoder().decode(new Uint8Array(bytes, 20, jsonLen)));
  const bin = bytes.slice(20 + jsonLen + 8);
  const srgb = v => Math.pow(Math.max(0, Math.min(1, v)), 1 / 2.2);   // the file stores linear color; this renderer draws colors as given
  const width = {SCALAR: 1, VEC2: 2, VEC3: 3};
  const arrays = {5126: Float32Array, 5123: Uint16Array, 5125: Uint32Array};
  function accessor(i) {
    const a = doc.accessors[i], v = doc.bufferViews[a.bufferView];
    return new THREE.BufferAttribute(new arrays[a.componentType](bin, v.byteOffset || 0, a.count * width[a.type]), width[a.type]);
  }
  const materials = doc.materials.map(m => {
    const c = m.pbrMetallicRoughness.baseColorFactor;
    const mat = new THREE.MeshStandardMaterial({color: new THREE.Color(srgb(c[0]), srgb(c[1]), srgb(c[2])),
      metalness: m.pbrMetallicRoughness.metallicFactor, roughness: m.pbrMetallicRoughness.roughnessFactor});
    mat.name = m.name;
    return mat;
  });
  const byName = {};
  const nodes = doc.nodes.map(n => {
    const g = new THREE.Group(); g.name = n.name; g.userData = n.extras || {};
    if (n.translation) g.position.fromArray(n.translation);
    if (n.mesh !== undefined) for (const p of doc.meshes[n.mesh].primitives) {
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', accessor(p.attributes.POSITION));
      geo.setAttribute('normal', accessor(p.attributes.NORMAL));
      if (p.attributes.TEXCOORD_0 !== undefined) geo.setAttribute('uv', accessor(p.attributes.TEXCOORD_0));
      geo.setIndex(accessor(p.indices));
      const mesh = new THREE.Mesh(geo, materials[p.material]); mesh.name = n.name; g.add(mesh);
    }
    byName[n.name] = g;
    return g;
  });
  doc.nodes.forEach((n, i) => (n.children || []).forEach(c => nodes[i].add(nodes[c])));
  const root = new THREE.Group();
  doc.scenes[doc.scene || 0].nodes.forEach(i => root.add(nodes[i]));
  return {root, byName};
}

function initRobot(THREE, canvas, hooks) {
  const cv = canvas;
  const r = new THREE.WebGLRenderer({canvas: cv, antialias: true});
  r.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x15181d);
  const cam = new THREE.PerspectiveCamera(35, 1, 0.1, 200);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x334455, 0.6));
  const key = new THREE.DirectionalLight(0xffffff, 0.5); key.position.set(8, 14, 12); scene.add(key);
  const rim = new THREE.DirectionalLight(0x88aaff, 0.4); rim.position.set(-9, 6, -10); scene.add(rim);

  const robot = new THREE.Group(); scene.add(robot);
  // table
  const table = new THREE.Mesh(new THREE.CircleGeometry(16, 64), new THREE.MeshStandardMaterial({color: 0x1b2027, roughness: 1}));
  table.rotation.x = -Math.PI / 2; scene.add(table);
  const grid = new THREE.GridHelper(32, 32, 0x2a323d, 0x222932); grid.position.y = -0.01; scene.add(grid);

  // ---- the body: filled in when the model file arrives
  const tex = new THREE.Texture(); tex.minFilter = THREE.LinearFilter; tex.flipY = false;   // the model's screen UV has 0,0 at the top left
  const M = {ready: false, yaw: null, pitch: null, screen: null, headMeshes: [], leds: [], button: null, portHit: null, btnHit: null,
             yawAxis: new THREE.Vector3(0, -1, 0), pitchAxis: new THREE.Vector3(-1, 0, 0), yawLim: [-128, 128], pitchLim: [0, 90], pitchY: 4.35, topY: 7.05, baseTopY: 1.13};
  const cable = new THREE.Group(); cable.visible = false; robot.add(cable);
  const chargeLed = new THREE.Mesh(new THREE.SphereGeometry(0.1, 10, 10), new THREE.MeshBasicMaterial({color: 0x222222})); robot.add(chargeLed);
  const axes = new THREE.Group(); robot.add(axes);
  const yawGizmo = new THREE.Group(), pitchGizmo = new THREE.Group(); axes.add(yawGizmo); axes.add(pitchGizmo);

  function install(model) {
    const N = model.byName;
    for (const name of ['base', 'yaw_joint', 'pitch_joint', 'head', 'screen_plane', 'usb_c_port', 'power_button', 'ring_light_0', 'ring_light_11'])
      if (!N[name]) throw new Error('the model has no node named ' + name);
    model.root.scale.setScalar(100); robot.add(model.root); robot.updateMatrixWorld(true);
    M.yaw = N.yaw_joint; M.pitch = N.pitch_joint;
    const yj = M.yaw.userData.joint, pj = M.pitch.userData.joint;
    M.yawAxis.fromArray(yj.axis); M.pitchAxis.fromArray(pj.axis);
    M.yawLim = yj.limit_deg; M.pitchLim = pj.geometry_free_deg || [0, 90];   // the head moves freely between these; the firmware range sits inside
    const wp = o => o.getWorldPosition(new THREE.Vector3());
    M.pitchY = wp(M.pitch).y; M.topY = M.pitchY + 2.7;
    M.baseTopY = new THREE.Box3().setFromObject(N.base.children.find(c => c.isMesh)).max.y;
    // the screen: the live frame on the model's quad
    M.screen = N.screen_plane.children.find(c => c.isMesh);
    M.screen.material = new THREE.MeshBasicMaterial({map: tex});
    N.head.traverse(o => { if (o.isMesh) M.headMeshes.push(o); });
    // the 12 lights, each with its own plain material
    for (let i = 0; i < 12; i++) {
      const m = N['ring_light_' + i].children.find(c => c.isMesh);
      m.material = new THREE.MeshBasicMaterial({color: 0x222222}); M.leds.push(m);
    }
    // click targets: the port on the back of the base and the power button on the head, each with a bigger unseen target (sizes in meters)
    M.button = N.power_button.children.find(c => c.isMesh); M.button.material = M.button.material.clone();
    M.portHit = new THREE.Mesh(new THREE.BoxGeometry(0.022, 0.010, 0.010), new THREE.MeshBasicMaterial({visible: false})); N.usb_c_port.add(M.portHit);
    M.btnHit = new THREE.Mesh(new THREE.SphereGeometry(0.007, 8, 8), new THREE.MeshBasicMaterial({visible: false})); N.power_button.add(M.btnHit);
    // the cable into the port, and the charge light beside it
    const p = wp(N.usb_c_port), pz = p.z - 0.1;
    const plug = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.5, 1.4), new THREE.MeshStandardMaterial({color: 0xb7bcc4, metalness: 0.5, roughness: 0.35}));
    plug.position.set(0, p.y, pz - 0.7); cable.add(plug);
    const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(0, p.y, pz - 1.4), new THREE.Vector3(0, p.y, pz - 3), new THREE.Vector3(1.5, 0.3, pz - 5.5), new THREE.Vector3(3.5, 0.25, pz - 9), new THREE.Vector3(5, 0.25, pz - 13)]);
    cable.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.16, 10, false), new THREE.MeshStandardMaterial({color: 0x2a2f36, roughness: 0.7})));
    chargeLed.position.set(0.9, p.y + 0.35, pz + 0.1);
    // the axes gizmo sits on the model's own joints
    yawGizmo.position.set(0, M.baseTopY + 0.05, 0); pitchGizmo.position.set(0, M.pitchY, 0);
    const yawLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, M.topY + 2.4, 8), new THREE.MeshBasicMaterial({color: 0x3ddc84}));
    yawLine.position.set(0, (M.topY + 2.4) / 2, 0); axes.add(yawLine);
    const pitchLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 8.2, 8), new THREE.MeshBasicMaterial({color: 0xff6b6b}));
    pitchLine.rotation.z = Math.PI / 2; pitchLine.position.set(0, M.pitchY, 0); axes.add(pitchLine);
    target.y = M.topY / 2;
    M.ready = true;
  }
  fetch('/model/stackchan.glb').then(res => { if (!res.ok) throw new Error('HTTP ' + res.status); return res.arrayBuffer(); })
    .then(buf => install(readGlb(THREE, buf)))
    .catch(err => { if (hooks.status) hooks.status('The robot model did not load (' + err.message + '). Run python3 scripts/virtual-unit/model/make_body.py and reload; the flat screen is at /frame.png.'); });

  // axes gizmo: the yaw arc (green, flat above the base) and the pitch arc (red, in the side plane), each with its limits and a live pointer
  function arc(pts, color, width) {
    const g = new THREE.BufferGeometry().setFromPoints(pts);
    return new THREE.Line(g, new THREE.LineBasicMaterial({color, linewidth: width || 1}));
  }
  const yawArcR = 4.6, pitchArcR = 4.6;
  function yawPoint(deg, rad) { const a = -deg * Math.PI / 180; return new THREE.Vector3(Math.sin(a) * rad, 0, Math.cos(a) * rad); }
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
    // pitch: angle 0 faces forward (+z), positive looks up; the arc is drawn beside the head
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
  const target = new THREE.Vector3(0, 3.5, 0);
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
    list = list.filter(Boolean); if (!list.length) return null;
    const b = cv.getBoundingClientRect();
    v2.set(((ev.clientX - b.left) / b.width) * 2 - 1, -((ev.clientY - b.top) / b.height) * 2 + 1);
    ray.setFromCamera(v2, cam);
    return ray.intersectObjects(list, false)[0] || null;
  }
  function panelXY(ev) {   // the nearest thing under the pointer must be the screen itself, not the back of the head
    const hit = pick(ev, M.headMeshes);
    return hit && hit.object === M.screen && hit.uv ? {x: Math.round(hit.uv.x * 319), y: Math.round(hit.uv.y * 239)} : null;
  }
  const pointers = new Map(); let drag = null, pinch0 = 0;
  cv.addEventListener('pointerdown', e => {
    cv.setPointerCapture(e.pointerId); pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch0 = Math.hypot(a.x - b.x, a.y - b.y); drag = {mode: 'pinch', d0: view.dist}; return; }
    if (e.shiftKey && hooks.physicsOn() && pick(e, M.headMeshes)) { drag = {mode: 'push', sx: e.clientX, sy: e.clientY}; return; }
    const p = panelXY(e);
    if (p && hooks.on()) drag = {mode: 'touch', p, cx: e.clientX, cy: e.clientY, t: performance.now()};
    else if (pick(e, [M.portHit])) drag = {mode: 'port', cx: e.clientX, cy: e.clientY};
    else if (pick(e, [M.btnHit])) drag = {mode: 'button', cx: e.clientX, cy: e.clientY};
    else drag = {mode: 'orbit', lx: e.clientX, ly: e.clientY};
  });
  cv.addEventListener('pointermove', e => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (drag && drag.mode === 'pinch' && pointers.size === 2) { const [a, b] = [...pointers.values()]; view.dist = Math.max(6, Math.min(48, drag.d0 * pinch0 / Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)))); return; }
    if (drag && drag.mode === 'push') {   // a force on the head along the drag, in the camera's right and up directions (newtons, at most 1.2)
      const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy, k = 0.012;
      const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1);
      const f = right.multiplyScalar(dx * k).add(up.multiplyScalar(-dy * k)); if (f.length() > 1.2) f.setLength(1.2);
      hooks.push([f.z, f.x, f.y]);   // view axes to the physics frame: x forward is view z, y left is view x, z up is view y
      return;
    }
    if (drag && drag.mode === 'orbit') {
      view.az -= (e.clientX - drag.lx) * 0.008; view.el = Math.max(-0.2, Math.min(1.5, view.el + (e.clientY - drag.ly) * 0.006)); drag.lx = e.clientX; drag.ly = e.clientY; return;
    }
    if (!drag) cv.style.cursor = (pick(e, [M.portHit]) || pick(e, [M.btnHit]) || (panelXY(e) && hooks.on())) ? 'pointer' : 'grab';
  });
  function end(e) {
    pointers.delete(e.pointerId);
    const d = drag; if (pointers.size === 0) drag = null; if (!d) return;
    if (d.mode === 'push') { hooks.push(null); return; }
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

  const img = new Image();
  img.onload = () => { tex.image = img; tex.needsUpdate = true; };
  setInterval(() => { img.src = '/frame.png?' + Date.now(); }, 100);

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const BASE_MID = new THREE.Vector3(0, 0.6, 0);   // the physics model's base body origin: the middle of its base plate, 6 mm above the table
  let cy = 0, cp = 0;
  const api = {
    update(st) {
      this.st = st;
    },
    frame() {
      const st = this.st; if (!st || !M.ready) return;
      axes.visible = !!hooks.axesVisible();
      buildRanges(st.yaw_range, st.pitch_range, st.pitch_safe);
      const ph = this.phys && performance.now() - this.phys.at < 400 ? this.phys.pose : null;
      if (ph) { cy = ph.yaw; cp = ph.pitch; } else { cy += (st.head.yaw - cy) * 0.35; cp += (st.head.pitch - cp) * 0.35; }
      if (ph) {   // the model's base: where it slid, tipped or was lifted (physics frame: x forward, y left, z up; view: z forward, x right, y up)
        const q = new THREE.Quaternion(ph.quat[2], ph.quat[3], ph.quat[1], ph.quat[0]);
        robot.quaternion.copy(q);
        robot.position.set(ph.pos[1] * 100, ph.pos[2] * 100, ph.pos[0] * 100).sub(BASE_MID.clone().applyQuaternion(q));
      } else { robot.quaternion.identity(); robot.position.set(0, 0, 0); }
      // the joints turn about the axes stored in the model, held inside the range where its parts do not touch
      M.yaw.quaternion.setFromAxisAngle(M.yawAxis, clamp(cy, M.yawLim[0], M.yawLim[1]) * Math.PI / 180);   // positive yaw turns the head toward the robot's right (unverified against the unit)
      M.pitch.quaternion.setFromAxisAngle(M.pitchAxis, clamp(cp, M.pitchLim[0], M.pitchLim[1]) * Math.PI / 180);   // positive pitch looks up
      if (yawPointer) yawPointer.position.copy(yawPoint(cy, yawArcR));
      if (pitchPointer) { const p = pitchPointer.userData.pp(cp, pitchArcR); pitchPointer.position.copy(p); }
      const on = st.hw.on, leds = st.leds || [];
      M.leds.forEach((m, i) => { const c = on && leds[i] ? leds[i] : [0, 0, 0]; m.material.color.setRGB(Math.max(0.12, c[0] / 255), Math.max(0.14, c[1] / 255), Math.max(0.15, c[2] / 255)); });
      cable.visible = st.hw.usb;
      chargeLed.material.color.set(st.hw.usb ? (st.hw.charging ? 0xffb020 : 0x46be6e) : 0x222222);
      M.button.material.emissive.set(on ? 0x1f7a3c : 0x000000);
      M.screen.material.color.set(on ? 0xffffff : 0x000000);
    },
    setPhysicsPose(pose) { this.phys = {pose, at: performance.now()}; },
    render() { placeCam(); r.render(scene, cam); },
    get screen() { return M.screen; },
    model: M,
  };
  return api;
}
