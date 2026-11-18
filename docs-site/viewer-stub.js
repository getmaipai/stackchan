// View-only 3D viewer. It loads view3d.js unedited and stands in for the unit: the state object, the hooks and the two things
// view3d.js asks the unit for (the model at /model/stackchan.glb and the screen at /frame.png) are answered from this site's own files.
// Placement: documentation site only; no firmware or host change.
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var msg = $('msg');
  var base = new URL('.', document.currentScript.src).href;   // .../assets/

  // view3d.js asks for absolute paths that exist only on the dev server. Point them at the files beside this script.
  var realFetch = window.fetch.bind(window);
  window.fetch = function (url, opts) {
    if (typeof url === 'string' && url.indexOf('/model/stackchan.glb') === 0) url = base + 'stackchan.glb';
    return realFetch(url, opts);
  };
  var FACE = base + 'face.png', NativeImage = window.Image, srcSet = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src');
  window.Image = function () {
    var img = new NativeImage();
    Object.defineProperty(img, 'src', { configurable: true, get: function () { return srcSet.get.call(img); },
      set: function (v) { srcSet.set.call(img, /\/frame\.png/.test(v) ? FACE : v); } });
    return img;
  };

  // the unit's state, as view3d.js reads it
  var st = {
    yaw_range: [-128, 128], pitch_range: [3, 87], pitch_safe: [5, 85],
    head: { yaw: 0, pitch: 3 },
    hw: { on: true, booting: false, usb: false, charging: false, vbus: false, ports: { back: { plugged: false }, side: { plugged: false } } },
    leds: []
  };
  for (var i = 0; i < 12; i++) st.leds.push([0, 0, 0]);
  window.VIEWER_STATE = st;

  var clamp = function (x, a, b) { return Math.max(a, Math.min(b, x)); };
  function syncHead() {
    $('yaw').value = Math.round(st.head.yaw); $('pitch').value = Math.round(st.head.pitch);
    $('yawv').textContent = Math.round(st.head.yaw); $('pitchv').textContent = Math.round(st.head.pitch);
    $('hd').textContent = 'head: yaw ' + Math.round(st.head.yaw) + ', pitch ' + Math.round(st.head.pitch);
  }
  function aimHead(yaw, pitch) {
    st.head.yaw = clamp(yaw, st.yaw_range[0], st.yaw_range[1]);
    st.head.pitch = clamp(pitch, st.pitch_range[0], st.pitch_range[1]);
    syncHead();
  }
  function paintHw() {
    var h = st.hw, p = h.ports;
    h.usb = p.back.plugged || p.side.plugged; h.vbus = h.usb; h.charging = h.usb && h.on;
    $('bpower').textContent = 'Power: ' + (h.on ? 'on' : 'off'); $('bpower').className = h.on ? 'on' : '';
    $('bback').textContent = 'Back socket: ' + (p.back.plugged ? 'plugged in' : 'empty'); $('bback').className = p.back.plugged ? 'on' : '';
    $('bside').textContent = 'Side socket: ' + (p.side.plugged ? 'plugged in' : 'empty'); $('bside').className = p.side.plugged ? 'on' : '';
  }
  var chase = 0;
  function setLeds(f) { for (var i = 0; i < 12; i++) st.leds[i] = f(i); }
  function hex(v) { return [parseInt(v.slice(1, 3), 16), parseInt(v.slice(3, 5), 16), parseInt(v.slice(5, 7), 16)]; }
  function hsv(h) { var f = function (n) { var k = (n + h * 6) % 6; return Math.round(255 * (1 - Math.max(0, Math.min(k, 4 - k, 1)))); }; return [f(5), f(3), f(1)]; }

  if (!window.THREE) { msg.textContent = 'The 3D drawing library did not load. Reload the page.'; return; }
  var hooks = {
    status: function (t) { msg.textContent = t; },
    physicsOn: function () { return false; }, push: function () {},
    on: function () { return st.hw.on; },
    axesVisible: function () { return $('axes').checked; }, insideOn: function () { return $('inside').checked; }, motionOn: function () { return $('motion').checked; },
    demoDone: function () { $('vdemo').textContent = 'Demo sweep'; },
    dragHead: function () { return $('draghead').checked; }, aimHead: aimHead,
    richLights: function () { return $('rich').checked; }, dimRoom: function () { return $('dim').checked; },
    touch: function () { msg.textContent = 'View only: the screen does not take touch here.'; },
    headTouch: function (z) { msg.textContent = 'Head pad ' + (z + 1) + ' of 3. View only: nothing is sent.'; },
    togglePort: function (n) { var p = st.hw.ports[n || 'back']; p.plugged = !p.plugged; paintHw(); },
    togglePower: function () { st.hw.on = !st.hw.on; paintHw(); },
    reset: function () { msg.textContent = 'View only: the reset button does nothing here.'; }
  };

  var rob;
  try { rob = window.initRobot(window.THREE, $('c'), hooks); } catch (err) { msg.textContent = 'Your browser could not start 3D drawing (' + err.message + ').'; return; }
  window.ROBOT = rob;
  rob.update(st);
  msg.textContent = 'Drag the head to move it. Drag elsewhere to turn the view.';

  $('vreset').onclick = hooks.presets.reset; $('vfront').onclick = hooks.presets.front; $('vside').onclick = hooks.presets.side;
  $('vback').onclick = hooks.presets.back; $('vtop').onclick = hooks.presets.top; $('vunder').onclick = hooks.presets.under;
  $('vdemo').onclick = function () { $('vdemo').textContent = rob.demo() ? 'Stop demo' : 'Demo sweep'; };
  $('yaw').oninput = function () { aimHead(+$('yaw').value, st.head.pitch); };
  $('pitch').oninput = function () { aimHead(st.head.yaw, +$('pitch').value); };
  Array.prototype.forEach.call(document.querySelectorAll('[data-look]'), function (b) {
    b.onclick = function () { var v = b.getAttribute('data-look').split(','); aimHead(+v[0], +v[1]); };
  });
  $('bpower').onclick = hooks.togglePower; $('bback').onclick = function () { hooks.togglePort('back'); }; $('bside').onclick = function () { hooks.togglePort('side'); };
  $('ledall').onclick = function () { chase = 0; var c = hex($('ledc').value); setLeds(function () { return c; }); };
  $('ledrainbow').onclick = function () { chase = 0; setLeds(function (i) { return hsv(i / 12); }); };
  $('ledoff').onclick = function () { chase = 0; setLeds(function () { return [0, 0, 0]; }); };
  $('ledspin').onclick = function () { chase = chase ? 0 : 1; if (!chase) setLeds(function () { return [0, 0, 0]; }); };
  $('ledc').oninput = function () { if (!chase) $('ledall').onclick(); };
  setInterval(function () { if (!chase) return; var c = hex($('ledc').value), t = Math.floor(Date.now() / 90) % 12; setLeds(function (i) { var d = (t - i + 12) % 12; return d < 4 ? c.map(function (v) { return Math.round(v * (1 - d / 4)); }) : [0, 0, 0]; }); }, 90);
  paintHw(); syncHead();
  (function loop() { rob.update(st); rob.frame(); rob.render(); requestAnimationFrame(loop); })();
})();
