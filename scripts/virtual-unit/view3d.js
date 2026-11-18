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
  scene.add(new THREE.HemisphereLight(0xffffff, 0x50565e, 0.5));
  const key = new THREE.DirectionalLight(0xffffff, 0.4); key.position.set(8, 14, 12); scene.add(key);
  const rim = new THREE.DirectionalLight(0xdde6ff, 0.35); rim.position.set(-9, 6, -10); scene.add(rim);
  const fill = new THREE.DirectionalLight(0xffffff, 0.25); fill.position.set(-10, 4, 9); scene.add(fill);
  const back = new THREE.DirectionalLight(0xffffff, 0.25); back.position.set(10, 5, -9); scene.add(back);
  const below = new THREE.DirectionalLight(0xffffff, 0.3); below.position.set(2, -10, 6); scene.add(below);   // so the underside reads when the view looks up at it

  const robot = new THREE.Group(); scene.add(robot);
  const BASE_MID = new THREE.Vector3(0, 0.56, 0);
  // table
  const table = new THREE.Mesh(new THREE.CircleGeometry(16, 64), new THREE.MeshStandardMaterial({color: 0x1b2027, roughness: 1}));
  table.rotation.x = -Math.PI / 2; scene.add(table);
  const grid = new THREE.GridHelper(32, 32, 0x2a323d, 0x222932); grid.position.y = 0.012; scene.add(grid);

  // ---- the body: filled in when the model file arrives
  const tex = new THREE.Texture(); tex.minFilter = THREE.LinearFilter; tex.flipY = false;   // the model's screen UV has 0,0 at the top left
  const M = {ready: false, yaw: null, pitch: null, screen: null, headMeshes: [], leds: [], button: null, portHit: null, btnHit: null,
             parts: [], hits: [], solid: [], aux: new Set(), hover: null, yawCmd: [-128, 128], pitchCmd: [3, 87], lookKey: '', labels: [], demoAt: 0,
             yawAxis: new THREE.Vector3(0, -1, 0), pitchAxis: new THREE.Vector3(-1, 0, 0), yawLim: [-128, 128], pitchLim: [0, 90], pitchY: 4.35, topY: 7.05, baseTopY: 1.13};
  const cable = new THREE.Group(); cable.visible = false; robot.add(cable);
  const axes = new THREE.Group(); robot.add(axes);
  const yawGizmo = new THREE.Group(), pitchGizmo = new THREE.Group(); axes.add(yawGizmo); axes.add(pitchGizmo);

  function install(model) {
    const N = model.byName; M.nodes = N;
    for (const name of ['base', 'yaw_joint', 'pitch_joint', 'head', 'screen_plane', 'usb_c_port', 'power_button', 'ring_light_0', 'ring_light_11'])
      if (!N[name]) throw new Error('the model has no node named ' + name);
    model.root.scale.setScalar(100); robot.add(model.root); robot.updateMatrixWorld(true);
    M.yaw = N.yaw_joint; M.pitch = N.pitch_joint;
    const yj = M.yaw.userData.joint, pj = M.pitch.userData.joint;
    M.yawAxis.fromArray(yj.axis); M.pitchAxis.fromArray(pj.axis);
    M.yawLim = yj.limit_deg; M.pitchLim = pj.geometry_free_deg || [0, 90]; M.yawCmd = yj.limit_deg; M.pitchCmd = pj.limit_deg;   // the head moves freely between these; the firmware range sits inside
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
    const unseen = new THREE.MeshBasicMaterial({visible: false});
    // each switch has a generous unseen target and a yellow glow that shows while the pointer is over it
    const glow = new THREE.MeshBasicMaterial({color: 0xffd34d, transparent: true, opacity: 0.5, depthTest: false});
    const onHead = node => { for (let o = node; o; o = o.parent) if (o === N.head) return true; return false; };
    const addSwitch = (node, geo, label, act) => {
      const mesh = new THREE.Mesh(geo, unseen), hl = new THREE.Mesh(geo, glow); hl.visible = false; hl.renderOrder = 6; hl.scale.setScalar(0.75);
      node.add(mesh); node.add(hl); M.aux.add(mesh); M.aux.add(hl); M.hits.push({mesh, hl, label, act, name: node.name, onHead: onHead(node)}); return mesh;
    };
    M.portHit = addSwitch(N.usb_c_port, new THREE.BoxGeometry(0.028, 0.016, 0.018), 'USB-C port: click to plug or unplug the cable', () => hooks.togglePort());
    M.btnHit = addSwitch(N.power_button, new THREE.SphereGeometry(0.008, 10, 10), 'Power button: click to turn the unit off or on', () => hooks.togglePower());
    if (N.reset_button) addSwitch(N.reset_button, new THREE.SphereGeometry(0.006, 10, 10), 'Reset button: a click restarts the unit (on the real one, a 3 second hold enters download mode)', () => hooks.reset && hooks.reset());
    for (let i = 0; i < 3; i++) if (N['touch_back_' + i])
      addSwitch(N['touch_back_' + i], new THREE.BoxGeometry(0.016, 0.004, 0.008), 'Head touch pad ' + i + ' of 3 (' + ['front', 'middle', 'back'][i] + '): a click is a touch on the head', () => hooks.headTouch && hooks.headTouch(i));
    // the cable into the port, and the charge light beside it
    const p = wp(N.usb_c_port), pz = p.z - 0.1;
    // a USB-C plug is small: a metal tip 8.3 x 2.5 mm that goes into the socket and a short grip barely wider, so it hides little of the base
    const tip = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.24, 0.6), new THREE.MeshStandardMaterial({color: 0xb7bcc4, metalness: 0.5, roughness: 0.35}));
    tip.position.set(0, p.y, pz + 0.05); cable.add(tip);
    const plug = new THREE.Mesh(new THREE.BoxGeometry(0.95, 0.42, 0.9), new THREE.MeshStandardMaterial({color: 0x30353d, roughness: 0.6}));
    plug.position.set(0, p.y, pz - 0.6); cable.add(plug); M.plug = plug;
    const curve = new THREE.CatmullRomCurve3([new THREE.Vector3(0, p.y, pz - 1.05), new THREE.Vector3(0, p.y, pz - 2.2), new THREE.Vector3(0.8, 0.25, pz - 4.5), new THREE.Vector3(2.5, 0.2, pz - 8), new THREE.Vector3(4, 0.2, pz - 12)]);
    cable.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.11, 10, false), new THREE.MeshStandardMaterial({color: 0x2a2f36, roughness: 0.7})));
    // the two small lights: the red one in the holder back and the one under the screen edge
    const lamp = (node, label) => { if (!node) return null; const m = node.children.find(c => c.isMesh); m.material = new THREE.MeshBasicMaterial({color: 0x000000}); addSwitch(node, new THREE.SphereGeometry(0.003, 6, 6), label, () => {}); return m; };
    M.chargeLed = lamp(N.back_charge_led, 'Charge light: red while the battery charges (behavior assumed)');
    M.bottomLed = lamp(N.screen_bottom_led, 'Light beside the reset button: green in download mode on the real unit; the firmware does not drive it, so it stays off here');
    if (N.sd_slot) addSwitch(N.sd_slot, new THREE.BoxGeometry(0.016, 0.005, 0.005), 'Card slot (microSD)', () => {});
    // the axes gizmo sits on the model's own joints
    yawGizmo.position.set(0, M.baseTopY + 0.05, 0); pitchGizmo.position.set(0, M.pitchY, 0);
    const yawLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, M.topY + 2.4, 8), new THREE.MeshBasicMaterial({color: 0x3ddc84}));
    yawLine.position.set(0, (M.topY + 2.4) / 2, 0); axes.add(yawLine);
    const pitchLine = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, 8.2, 8), new THREE.MeshBasicMaterial({color: 0xff6b6b}));
    pitchLine.rotation.z = Math.PI / 2; pitchLine.position.set(0, M.pitchY, 0); axes.add(pitchLine);
    // every drawn part remembers its own material and which link it rides on, for the Show inside and Show motion looks
    const SHELL = {shell: 1, core: 1, glass: 1, neck: 1, servo: 1, base: 1, sticker: 1, sticker_ink: 1, sticker_dark: 1, sticker_gray: 1, sticker_orange: 1, print: 1, button: 1, touch_pad: 1};
    const tag = (node, link) => node.traverse(o => { if (o.isMesh && o !== M.screen && !M.leds.includes(o) && !M.aux.has(o) && !o.userData.link) o.userData = {link, mat: o.material, shell: !!SHELL[o.material.name]}; });
    tag(N.pitch_joint, 'pitch'); tag(N.yaw_joint, 'yaw'); tag(N.base, 'base');
    model.root.traverse(o => { if (o.isMesh && o.userData.link) M.parts.push(o); });
    model.root.traverse(o => { if (o.isMesh && !M.aux.has(o)) M.solid.push(o); });
    const stage = cv.parentElement;
    for (const [text, color, node, dy] of [['turns with the pan servo (yaw)', '#3ddc84', N.neck, -0.004], ['tilts with the tilt servo (pitch)', '#ff6b6b', N.head, 0.034]]) {
      const el = document.createElement('div'); el.textContent = text;
      el.style.cssText = 'position:absolute;pointer-events:none;display:none;background:#000a;color:' + color + ';border:1px solid ' + color + ';border-radius:6px;padding:2px 7px;font-size:12px;white-space:nowrap;transform:translate(-50%,-50%)';
      stage.appendChild(el); M.labels.push({el, node, dy});
    }
    BASE_MID.y = M.baseTopY / 2;   // the physics model's base body origin: the middle of the base's height
    targetHome.y = target.y = M.topY / 2;
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

  // ---- the orbit camera: drag turns it, shift-drag or right-drag slides it, the wheel or a pinch zooms, a double click puts it back
  const target = new THREE.Vector3(0, 3.5, 0), targetHome = new THREE.Vector3(0, 3.5, 0);
  const view = {az: 0.55, el: 0.35, dist: 17};
  const HOME = {az: 0.55, el: 0.35, dist: 17};
  const EL = [-1.35, 1.5], DIST = [5, 48];   // low enough to look under the head at the reset button
  function placeCam() {
    const ce = Math.cos(view.el);
    cam.position.set(target.x + view.dist * ce * Math.sin(view.az), target.y + view.dist * Math.sin(view.el), target.z + view.dist * ce * Math.cos(view.az));
    cam.lookAt(target);
  }
  const clampView = () => { view.el = Math.max(EL[0], Math.min(EL[1], view.el)); view.dist = Math.max(DIST[0], Math.min(DIST[1], view.dist)); };
  const preset = (az, el, dist) => { Object.assign(view, {az, el, dist: dist || HOME.dist}); target.copy(targetHome); };
  const nudge = (daz, del, zoom) => { view.az += daz; view.el += del; view.dist *= zoom || 1; clampView(); };
  function pan(dx, dy) {   // slide the point the camera looks at, along the screen's right and up directions
    placeCam(); cam.updateMatrixWorld();
    const k = view.dist * 0.0016;
    target.add(new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0).multiplyScalar(-dx * k)).add(new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1).multiplyScalar(dy * k));
  }
  hooks.presets = {reset: () => preset(HOME.az, HOME.el, HOME.dist), front: () => preset(0, 0.05, 16), side: () => preset(Math.PI / 2, 0.05, 16), back: () => preset(Math.PI - 0.5, 0.25, 16), top: () => preset(0, 1.5, 19),
    under: () => preset(0.35, -0.75, 15), left: () => nudge(-0.35, 0), right: () => nudge(0.35, 0), up: () => nudge(0, 0.25), down: () => nudge(0, -0.25), zoomIn: () => nudge(0, 0, 0.8), zoomOut: () => nudge(0, 0, 1.25)};
  function size() {
    const w = cv.clientWidth || 1, h = cv.clientHeight || 1; r.setSize(w, h, false); cam.aspect = w / h;
    cam.fov = w / h < 0.9 ? 52 : 35; cam.updateProjectionMatrix();
  }
  addEventListener('resize', size); size();

  // ---- picking: the screen is touch; the port, the buttons and the head pads are switches; everything else turns the camera
  const ray = new THREE.Raycaster(), v2 = new THREE.Vector2();
  function pick(ev, list) {
    list = list.filter(Boolean); if (!list.length) return null;
    const b = cv.getBoundingClientRect();
    v2.set(((ev.clientX - b.left) / b.width) * 2 - 1, -((ev.clientY - b.top) / b.height) * 2 + 1);
    placeCam(); cam.updateMatrixWorld();
    ray.setFromCamera(v2, cam);
    return ray.intersectObjects(list, false)[0] || null;
  }
  function panelXY(ev) {   // the nearest thing under the pointer must be the screen itself, not the back of the head
    const hit = pick(ev, M.headMeshes);
    return hit && hit.object === M.screen && hit.uv ? {x: Math.round(hit.uv.x * 319), y: Math.round(hit.uv.y * 239)} : null;
  }
  function switchAt(ev) {   // a switch counts only when no part of the body is in front of it
    const hit = pick(ev, M.hits.map(h => h.mesh)); if (!hit) return null;
    const body = pick(ev, M.solid);
    return !body || hit.distance <= body.distance + 1.2 ? M.hits.find(h => h.mesh === hit.object) : null;
  }
  const tip = document.createElement('div');
  tip.style.cssText = 'position:absolute;pointer-events:none;display:none;background:#000c;color:#e8ecf1;border:1px solid #556;border-radius:6px;padding:3px 8px;font-size:12px;max-width:260px;z-index:5';
  cv.parentElement.appendChild(tip);
  const pointers = new Map(); let drag = null, pinch0 = 0, hoverAt = 0;
  cv.addEventListener('contextmenu', e => e.preventDefault());
  cv.addEventListener('pointerdown', e => {
    try { cv.setPointerCapture(e.pointerId); } catch (err) { /* a scripted pointer has nothing to capture */ }
    pointers.set(e.pointerId, {x: e.clientX, y: e.clientY}); tip.style.display = 'none';
    if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinch0 = Math.hypot(a.x - b.x, a.y - b.y); drag = {mode: 'pinch', d0: view.dist}; return; }
    if (e.shiftKey && hooks.physicsOn() && pick(e, M.headMeshes)) { drag = {mode: 'push', sx: e.clientX, sy: e.clientY}; return; }
    if (e.button === 2 || e.button === 1 || e.shiftKey) { drag = {mode: 'pan', lx: e.clientX, ly: e.clientY}; return; }
    const p = e.altKey ? null : panelXY(e), sw = p ? null : switchAt(e);   // hold Alt to turn the camera from a drag that starts on the screen
    if (p && hooks.on()) drag = {mode: 'touch', p, cx: e.clientX, cy: e.clientY, t: performance.now()};
    else if (sw) drag = {mode: 'switch', sw, cx: e.clientX, cy: e.clientY, lx: e.clientX, ly: e.clientY};
    else if (!e.altKey && headDrag() && pick(e, M.headMeshes)) drag = grabHead(e);   // a drag that starts on the head moves the head; anywhere else it turns the view
    else drag = {mode: 'orbit', lx: e.clientX, ly: e.clientY};
  });
  cv.addEventListener('pointermove', e => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, {x: e.clientX, y: e.clientY});
    if (drag && drag.mode === 'pinch' && pointers.size === 2) { const [a, b] = [...pointers.values()]; view.dist = drag.d0 * pinch0 / Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)); clampView(); return; }
    if (drag && drag.mode === 'push') {   // a force on the head along the drag, in the camera's right and up directions (newtons, at most 1.2)
      const dx = e.clientX - drag.sx, dy = e.clientY - drag.sy, k = 0.012;
      const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1);
      const f = right.multiplyScalar(dx * k).add(up.multiplyScalar(-dy * k)); if (f.length() > 1.2) f.setLength(1.2);
      hooks.push([f.z, f.x, f.y]);   // view axes to the physics frame: x forward is view z, y left is view x, z up is view y
      return;
    }
    if (drag && drag.mode === 'switch' && Math.hypot(e.clientX - drag.cx, e.clientY - drag.cy) > 8) drag = drag.sw.onHead && headDrag() ? grabHead(e) : {mode: 'orbit', lx: e.clientX, ly: e.clientY};   // a drag that starts on a switch is a drag, not a click
    if (drag && drag.mode === 'head') {   // like taking the head in your hand: across turns it (yaw), up and down nods it (pitch), inside the firmware limits
      drag.yaw = clamp(drag.yaw0 + drag.sign * (e.clientX - drag.sx) * 0.6, M.yawCmd[0], M.yawCmd[1]);
      drag.pitch = clamp(drag.pitch0 - (e.clientY - drag.sy) * 0.45, M.pitchCmd[0], M.pitchCmd[1]);
      if (performance.now() - drag.at > 500) { drag.at = performance.now(); hooks.aimHead(drag.yaw, drag.pitch, false); }   // the drawn head follows the hand at once; the unit is asked twice a second, so a long drag does not use up the limiter's move budget
      return;
    }
    if (drag && drag.mode === 'pan') { pan(e.clientX - drag.lx, e.clientY - drag.ly); drag.lx = e.clientX; drag.ly = e.clientY; return; }
    if (drag && drag.mode === 'orbit') {
      view.az -= (e.clientX - drag.lx) * 0.008; view.el += (e.clientY - drag.ly) * 0.006; clampView(); drag.lx = e.clientX; drag.ly = e.clientY; return;
    }
    if (!drag && M.ready && performance.now() - hoverAt > 50) {   // hover: a pointer over a switch names it
      hoverAt = performance.now();
      const p = panelXY(e), sw = p ? null : switchAt(e), b = cv.getBoundingClientRect();
      cv.style.cursor = (sw || (p && hooks.on())) ? 'pointer' : 'grab';
      if (M.hover !== sw) { if (M.hover) M.hover.hl.visible = false; if (sw) sw.hl.visible = true; M.hover = sw; }
      tip.style.display = sw ? 'block' : 'none';
      if (sw) { tip.textContent = sw.label; tip.style.left = (e.clientX - b.left + 14) + 'px'; tip.style.top = (e.clientY - b.top + 14) + 'px'; }
    }
  });
  function end(e) {
    pointers.delete(e.pointerId);
    const d = drag; if (pointers.size === 0) drag = null; if (!d) return;
    if (d.mode === 'push') { hooks.push(null); return; }
    if (d.mode === 'head') { cv.style.cursor = 'grab'; if (d.yaw !== undefined) hooks.aimHead(d.yaw, d.pitch, true); return; }
    const moved = d.cx === undefined ? 99 : Math.hypot(e.clientX - d.cx, e.clientY - d.cy);
    if (d.mode === 'touch') {
      const up = panelXY(e) || d.p;
      hooks.touch(moved > 12 ? {kind: 'swipe', x: d.p.x, y: d.p.y, x2: up.x, y2: up.y, ms: Math.max(120, Math.min(900, performance.now() - d.t))} : {kind: 'tap', x: d.p.x, y: d.p.y});
    } else if (d.mode === 'switch' && moved < 8) d.sw.act();
  }
  cv.addEventListener('pointerup', end); cv.addEventListener('pointercancel', end);
  cv.addEventListener('pointerleave', () => { tip.style.display = 'none'; if (M.hover) { M.hover.hl.visible = false; M.hover = null; } });
  // moving the head by hand: the same tool call the model would make, so the unit's limiter decides
  const headDrag = () => !!(hooks.dragHead && hooks.dragHead() && hooks.aimHead && hooks.on() && api.st);
  const turnSign = () => Math.cos(view.az) >= 0 ? -1 : 1;   // seen from the front, a drag to the right turns the head to the viewer's right
  function grabHead(e) { cv.style.cursor = 'grabbing'; return {mode: 'head', sx: e.clientX, sy: e.clientY, yaw0: api.st.head.yaw, pitch0: api.st.head.pitch, sign: turnSign(), at: 0}; }
  cv.tabIndex = 0;
  addEventListener('keydown', e => {   // the arrow keys nudge the head 5 degrees, unless a field or a slider has the keyboard
    const k = {ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1]}[e.key];
    if (!k || e.metaKey || e.ctrlKey || /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || '') || !headDrag()) return;
    e.preventDefault();
    hooks.aimHead(clamp(api.st.head.yaw + turnSign() * k[0] * 5, M.yawCmd[0], M.yawCmd[1]), clamp(api.st.head.pitch + k[1] * 5, M.pitchCmd[0], M.pitchCmd[1]), true);
  });
  cv.addEventListener('wheel', e => { e.preventDefault(); view.dist *= Math.exp(e.deltaY * (e.ctrlKey ? 0.01 : 0.0012)); clampView(); }, {passive: false});   // a trackpad pinch arrives as a wheel with ctrl
  cv.addEventListener('dblclick', e => { if (!panelXY(e) && !switchAt(e)) hooks.presets.reset(); });   // two quick clicks on a button are two presses, not a view reset
  cv.style.touchAction = 'none'; cv.style.cursor = 'grab';

  const img = new Image();
  img.onload = () => { tex.image = img; tex.needsUpdate = true; };
  setInterval(() => { img.src = '/frame.png?' + Date.now(); }, 100);

  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const LINK_TINT = {yaw: new THREE.Color(0x3ddc84), pitch: new THREE.Color(0xff6b6b)};
  function applyLook(inside, motion) {   // inside: the shells turn to glass so the servos, battery and boards show; motion: each moving link takes its axis color
    const key = (inside ? 'i' : '') + (motion ? 'm' : '');
    if (key === M.lookKey) return; M.lookKey = key;
    for (const o of M.parts) {
      const u = o.userData;
      if (!inside && !motion) { o.material = u.mat; o.renderOrder = 0; continue; }
      const m = u.mat.clone();
      if (motion && LINK_TINT[u.link]) m.color.lerp(LINK_TINT[u.link], 0.6);
      if (inside && u.shell) { m.transparent = true; m.opacity = u.link === 'base' ? 0.45 : 0.16; m.depthWrite = false; o.renderOrder = 2; } else o.renderOrder = 0;
      o.material = m;
    }
    M.screen.material.transparent = inside; M.screen.material.opacity = inside ? 0.35 : 1; M.screen.renderOrder = inside ? 3 : 0;
  }
  const v3 = new THREE.Vector3();
  function placeLabels(show) {
    const w = cv.clientWidth, h = cv.clientHeight;
    for (const l of M.labels) {
      if (!show) { l.el.style.display = 'none'; continue; }
      l.node.getWorldPosition(v3); v3.y += l.dy * 100; v3.project(cam);
      l.el.style.display = v3.z < 1 ? 'block' : 'none';
      l.el.style.left = ((v3.x + 1) / 2 * w) + 'px'; l.el.style.top = ((1 - v3.y) / 2 * h) + 'px';
    }
  }
  // the demo sweep: the drawn head pans left and right, then nods up and down, slowly; the unit itself is not commanded
  function demoPose(t) {
    if (t < 8) return {yaw: 90 * Math.sin(2 * Math.PI * t / 8), pitch: 10, note: 'Demo: the pan servo turns everything above the base (yaw).'};
    if (t < 16) return {yaw: 0, pitch: 10 + 75 * Math.pow(Math.sin(Math.PI * (t - 8) / 8), 2), note: 'Demo: the tilt servo nods the head about the side axis (pitch).'};
    return null;
  }
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
      const demo = !ph && M.demoAt ? demoPose((performance.now() - M.demoAt) / 1000) : null;
      if (M.demoAt && !demo) { M.demoAt = 0; if (hooks.demoDone) hooks.demoDone(); }
      if (demo && hooks.status && demo.note !== M.demoNote) { M.demoNote = demo.note; hooks.status(demo.note); }
      if (ph) { cy = ph.yaw; cp = ph.pitch; } else if (demo) { cy = demo.yaw; cp = demo.pitch; } else if (drag && drag.mode === 'head' && drag.yaw !== undefined) { cy += (drag.yaw - cy) * 0.5; cp += (drag.pitch - cp) * 0.5; } else { cy += (st.head.yaw - cy) * 0.35; cp += (st.head.pitch - cp) * 0.35; }
      const motion = !!(hooks.motionOn && hooks.motionOn()) || !!demo;
      applyLook(!!(hooks.insideOn && hooks.insideOn()), motion);
      this.labelsOn = motion;
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
      M.leds.forEach((m, i) => {   // an unlit light shows the bar's own frosted teal
        const c = on && leds[i] ? leds[i] : [0, 0, 0];
        if (c[0] + c[1] + c[2] === 0) m.material.color.setRGB(0.30, 0.46, 0.47); else m.material.color.setRGB(c[0] / 255, c[1] / 255, c[2] / 255);
      });
      cable.visible = st.hw.usb;
      if (M.chargeLed) M.chargeLed.material.color.set(st.hw.usb && st.hw.charging ? 0xff3b30 : 0x3a0806);   // red while charging, dark otherwise
      if (M.bottomLed) M.bottomLed.material.color.set(0x0b2412);   // unlit: nothing in the firmware drives it
      M.screen.material.color.set(on ? 0xffffff : 0x000000);
    },
    setPhysicsPose(pose) { this.phys = {pose, at: performance.now()}; },
    render() { placeCam(); table.visible = grid.visible = cam.position.y > 0; r.render(scene, cam); if (M.ready) placeLabels(!!this.labelsOn); },   // from below, the table would hide the underside
    demo() { M.demoNote = ''; M.demoAt = M.demoAt ? 0 : performance.now(); return !!M.demoAt; },
    get screen() { return M.screen; },
    model: M, view, target,
    pointOf(name) {   // where a switch, or any named part of the model, is on the page right now, for scripted checks
      const h = M.hits.find(x => x.name === name), o = h ? h.mesh : (M.nodes && M.nodes[name]); if (!o) return null;
      placeCam(); cam.updateMatrixWorld(); const p = o.getWorldPosition(new THREE.Vector3()).project(cam), b = cv.getBoundingClientRect();
      return {x: b.left + (p.x + 1) / 2 * b.width, y: b.top + (1 - p.y) / 2 * b.height};
    },
  };
  return api;
}
