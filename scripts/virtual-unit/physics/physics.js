// Optional physics mode of the virtual unit view. Loaded only when the person turns Physics mode on; nothing here runs otherwise.
// Three parts, so a second robot reuses the first two:
//   1. the robot description (/physics/robot.json) and its model text (/physics/model.xml, built by physics/mjcf.py from the description);
//   2. the driver: the shared tool protocol's head pose (the unit's own head target, limiter and dances, read from /state) becomes joint targets by the role names
//      in the description (head.yaw, head.pitch); the model's IMU becomes imu.accel, imu.gyro and imu.tilt_deg, which go back to the host (/imu);
//   3. the sandbox: nudge, shake, lift and push with the mouse, servo load and settling readouts.
// Placement: host-side development tool; no firmware change. Upstream: none.
const GRAV = 9.80665;

async function loadEngine() {
  const info = await (await fetch('/physics/engine.json')).json();     // the pinned address lives in the third-party record
  const mod = await import(info.module);
  const engine = await mod.default();
  return {engine, info};
}

function quatTiltDeg(q) {            // q = (w, x, y, z) of the base: the angle of the base's up axis from world up
  const [w, x, y, z] = q;
  const upz = 1 - 2 * (x * x + y * y);
  return Math.acos(Math.max(-1, Math.min(1, upz))) * 180 / Math.PI;
}

async function startPhysics(ui, robotView) {
  ui.status('Loading the physics engine (about 11 MB, once)...');
  const {engine, info} = await loadEngine();
  const robot = await (await fetch('/physics/robot.json')).json();
  const xml = await (await fetch('/physics/model.xml')).text();
  const model = engine.MjModel.from_xml_string(xml);
  const data = new engine.MjData(model);
  const dt = model.opt.timestep;
  const P = k => robot.params[k].v;
  const totalMass = P('mass_base') + P('mass_yaw_housing') + P('mass_tilt_servo') + P('mass_head');
  const torqueLimit = P('torque_limit');
  // addresses: the order in the model text (freejoint 7, yaw, pitch) and the sensors it declares
  const Q_YAW = 7, Q_PITCH = 8;
  const S = {accel: 0, gyro: 3, yawPos: 6, pitchPos: 7, yawF: 8, pitchF: 9, baseAccel: 10};
  const BODY = {base: 1, yaw: 2, pitch: 3};
  const rad = d => d * Math.PI / 180;
  engine.mj_forward(model, data);

  const sim = {
    running: true, ref: {yaw: 0, pitch: 0}, powered: true, push: null, lift: null, shake: null, nudge: null,
    t: 0, track: null, telemetry: {overshoot: null, settle: null}, acc: 0, last: performance.now(), imuAt: 0,
  };
  const force = (body, f) => { for (let i = 0; i < 3; i++) data.xfrc_applied[body * 6 + i] = f[i]; };
  const torque = (body, t) => { for (let i = 0; i < 3; i++) data.xfrc_applied[body * 6 + 3 + i] = t[i]; };

  function setPowered(on) {   // power off: the servos let go and the head sags, as a real one does
    if (sim.powered === on) return;
    sim.powered = on;
    for (let i = 0; i < 2; i++) {
      const k = on ? (i === 0 ? P('yaw_kp') : P('pitch_kp')) : 0, kv = on ? (i === 0 ? P('yaw_kv') : P('pitch_kv')) : 0;
      try { model.actuator_gainprm[i * 10] = k; model.actuator_biasprm[i * 10 + 1] = -k; model.actuator_biasprm[i * 10 + 2] = -kv; } catch (e) { /* the build hides the array: the head stays held */ }
    }
  }

  function controlsAndForces(tSec) {
    data.ctrl[0] = rad(sim.ref.yaw); data.ctrl[1] = rad(sim.ref.pitch);
    // clear, then apply what the sandbox asks for
    for (let b = 1; b <= 3; b++) { force(b, [0, 0, 0]); torque(b, [0, 0, 0]); }
    if (sim.nudge && tSec < sim.nudge.until) force(BODY.pitch, sim.nudge.f); else sim.nudge = null;
    if (sim.push) force(BODY.pitch, sim.push);
    if (sim.shake && tSec < sim.shake.until) {
      const a = sim.shake.amp * Math.sin(2 * Math.PI * sim.shake.hz * (tSec - sim.shake.from));
      force(BODY.base, [a, 0, 0]);
    } else sim.shake = null;
    if (sim.lift) {   // a hand: a short upward push, then a spring that holds the robot at height, then it lets go
      const z = data.qpos[2], vz = data.qvel[2], l = sim.lift;
      // the lift acceleration is shared by the three bodies in proportion to their mass, like gravity, so it makes no tipping torque by itself
      const mB = P('mass_base'), mY = P('mass_yaw_housing'), mP = P('mass_tilt_servo') + P('mass_head');
      const lift = az => { force(BODY.base, [0, 0, mB * az]); force(BODY.yaw, [0, 0, mY * az]); force(BODY.pitch, [0, 0, mP * az]); };
      if (l.phase === 'up') {
        lift(GRAV + 22);
        if (tSec - l.from > 0.12) l.phase = 'hold';
      } else if (l.phase === 'hold') {
        lift(GRAV + 214 * (l.height - z) - 12 * vz);
        force(BODY.base, [data.xfrc_applied[BODY.base * 6] + 0.05 * Math.sin(9 * tSec), 0.04 * Math.sin(7 * tSec + 1), data.xfrc_applied[BODY.base * 6 + 2]]);   // a hand is never still
      } else if (l.phase === 'drop') {
        sim.lift = null;
      }
      if (sim.lift) {     // fingers keep it level: a soft torque back toward upright and against spinning (the quaternion's vector part is half the tilt)
        const qx = data.qpos[4], qy = data.qpos[5], qz = data.qpos[6], sg = data.qpos[3] < 0 ? -1 : 1;
        torque(BODY.base, [-1.2 * 2 * sg * qx - 0.03 * data.qvel[3], -1.2 * 2 * sg * qy - 0.03 * data.qvel[4], -1.2 * 2 * sg * qz - 0.03 * data.qvel[5]]);
      }
    }
  }

  function step(nSteps, tNow) {
    for (let i = 0; i < nSteps; i++) {
      controlsAndForces(sim.t);
      engine.mj_step(model, data);
      sim.t += dt;
    }
    return tNow;
  }

  function telemetry() {
    const q = [data.qpos[3], data.qpos[4], data.qpos[5], data.qpos[6]];
    const yaw = data.qpos[Q_YAW] * 180 / Math.PI, pitch = data.qpos[Q_PITCH] * 180 / Math.PI;
    const accel = [data.sensordata[S.baseAccel], data.sensordata[S.baseAccel + 1], data.sensordata[S.baseAccel + 2]];
    const tilt = quatTiltDeg(q);
    return {yaw, pitch, accel, tilt, q, pos: [data.qpos[0], data.qpos[1], data.qpos[2]],
      yawLoad: Math.abs(data.sensordata[S.yawF]) / torqueLimit, pitchLoad: Math.abs(data.sensordata[S.pitchF]) / torqueLimit,
      gyro: [data.sensordata[S.gyro], data.sensordata[S.gyro + 1], data.sensordata[S.gyro + 2]]};
  }

  // Overshoot and settling of the pitch servo: the reference (the unit's head target, which already slews at the commanded speed) ramps, then stops.
  // From the moment it stops, track the highest excursion past it and the time until the real angle stays within half a degree for 150 ms.
  function trackSettling(tel, refPitch) {
    const tr = sim.track || (sim.track = {ref: refPitch, lastChange: sim.t, steadyRef: refPitch, steady: true, active: false, settledSince: null, max: tel.pitch, dir: 1, from: sim.t});
    if (Math.abs(refPitch - tr.ref) > 0.01) {          // the reference is moving (the host sends it about every 100 ms)
      tr.ref = refPitch; tr.lastChange = sim.t; tr.steady = false; tr.active = false; tr.settledSince = null;
      return;
    }
    if (!tr.steady && sim.t - tr.lastChange > 0.3) {    // it stopped: a move of more than 5 degrees starts a measurement
      tr.steady = true;
      if (Math.abs(tr.ref - tr.steadyRef) > 5) { tr.active = true; tr.max = tel.pitch; tr.dir = Math.sign(tr.ref - tr.steadyRef); tr.from = tr.lastChange; }
      tr.steadyRef = tr.ref;
    }
    if (!tr.active) return;
    tr.max = tr.dir > 0 ? Math.max(tr.max, tel.pitch) : Math.min(tr.max, tel.pitch);
    const rate = tr.prev === undefined ? 99 : Math.abs(tel.pitch - tr.prev) / Math.max(1e-3, sim.t - tr.prevT) ;   // degrees per second
    tr.prev = tel.pitch; tr.prevT = sim.t;
    // settled: the angle has stopped moving (gravity and the servo's finite stiffness leave it a little off the target, so it is measured against where it came to rest)
    if (rate < 3) {
      if (tr.settledSince === null) tr.settledSince = sim.t;
      if (sim.t - tr.settledSince > 0.2) {
        sim.telemetry = {overshoot: Math.max(0, tr.dir * (tr.max - tel.pitch)), settle: Math.max(0, tr.settledSince - tr.lastChange)};
        tr.active = false;
      }
    } else tr.settledSince = null;
  }

  let timer = null;   // a timer, not a draw callback: the model keeps stepping when the tab is in the background
  function frame() {
    if (!sim.running) return;
    try { frameBody(); } catch (err) { ui.status('Physics stopped: ' + err.message + '. Turn Physics mode off and on to restart.'); sim.running = false; clearInterval(timer); }
  }
  function frameBody() {
    const now = performance.now();
    sim.acc += Math.min(0.1, (now - sim.last) / 1000); sim.last = now;
    const n = Math.floor(sim.acc / dt);
    if (n > 0) { step(n); sim.acc -= n * dt; }
    const tel = telemetry();
    trackSettling(tel, sim.ref.pitch);
    robotView.setPhysicsPose({yaw: tel.yaw, pitch: tel.pitch, pos: tel.pos, quat: tel.q});
    ui.readout({tel, telemetry: sim.telemetry, lifted: !!sim.lift});
    if (now - sim.imuAt > 100) {                     // the IMU goes to the host: it decides carried and orientation with the unit's own rule
      sim.imuAt = now;
      fetch('/imu', {method: 'POST', body: JSON.stringify({accel: tel.accel, tilt_deg: tel.tilt})}).catch(() => {});
    }
  }

  const api = {
    info,
    setReference(head, on) { sim.ref = head; setPowered(on); },       // the unit's head target (limiter and dance included) from /state
    nudge() { sim.nudge = {f: [0.9, (Math.random() - 0.5) * 0.4, 0.1], until: sim.t + 0.04}; },
    shake(seconds = 0.8) { sim.shake = {from: sim.t, until: sim.t + seconds, amp: 2.6, hz: 6}; },
    lift() { if (!sim.lift) sim.lift = {phase: 'up', from: sim.t, height: 0.06}; },
    putDown() { if (sim.lift) sim.lift.phase = 'drop'; },
    push(f) { sim.push = f; },          // a force on the head in newtons (world frame), or null
    reset() {
      engine.mj_resetData(model, data); sim.lift = sim.shake = sim.nudge = sim.push = null; engine.mj_forward(model, data);
    },
    stop() {
      sim.running = false; clearInterval(timer);
      fetch('/imu/off', {method: 'POST', body: '{}'}).catch(() => {});
      try { data.delete(); model.delete(); } catch (e) { /* the engine frees on reload */ }
    },
    worldToView: q => q,
  };
  timer = setInterval(frame, 16);
  ui.status('Physics on. Shift and drag on the robot pushes the head.');
  return api;
}
window.startPhysics = startPhysics;
