// The Talk panel of the virtual unit view: microphone and speaker switches, level meters, the transcript, the latency of the last turn and
// a LIVE MIC sign. It only shows what the voice bridge reports: GET /talk/state and POST /talk (field names in docs/plan/view-requests.md).
// Without a bridge it says so and keeps every control off: this file never opens the microphone or plays a sound itself.
// Placement: host-side development tool; no firmware change.
function initTalk(root, opts) {
  const get = (opts && opts.fetch) || (u => fetch(u)), post = (opts && opts.post) || ((u, b) => fetch(u, {method: 'POST', body: JSON.stringify(b)}));
  root.innerHTML = '<div class="row" style="margin-top:0"><button id="tmic" disabled>Microphone: off</button><button id="tspk" disabled>Speaker: off</button>' +
    '<span id="tlive" style="display:none;background:#e64646;color:#fff;border-radius:6px;padding:3px 8px;font-size:12px;font-weight:700">LIVE MIC</span></div>' +
    '<div style="margin-top:8px;font-size:12px" class="t">Microphone level</div><div class="meter"><i id="tmicl" style="width:0"></i></div>' +
    '<div style="margin-top:6px;font-size:12px" class="t">Speaker level</div><div class="meter"><i id="tspkl" style="width:0;background:#46be6e"></i></div>' +
    '<div class="kv"><span>Last turn took</span><span id="tlat">-</span></div>' +
    '<div id="ttext" style="margin-top:6px;font-size:12px;max-height:120px;overflow:auto"></div><div id="tmsg" class="t" style="margin-top:6px;font-size:12px;min-height:2.6em"></div>';
  const $ = id => root.querySelector('#' + id);
  const state = {live: false, st: null};
  const esc = t => String(t).replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c]));
  function paint(st) {
    state.st = st; state.live = !!(st && st.live_mic);
    const up = !!st;
    $('tmic').disabled = $('tspk').disabled = !up;
    $('tmic').textContent = 'Microphone: ' + (up && st.mic_on ? 'on' : 'off'); $('tmic').className = up && st.mic_on ? 'on' : '';
    $('tspk').textContent = 'Speaker: ' + (up && st.speaker_on ? 'on' : 'off'); $('tspk').className = up && st.speaker_on ? 'on' : '';
    $('tlive').style.display = state.live ? 'inline-block' : 'none';   // shown whenever the bridge says a real microphone is open, whatever the buttons say
    $('tmicl').style.width = Math.max(0, Math.min(100, up ? st.mic_level || 0 : 0)) + '%';
    $('tspkl').style.width = Math.max(0, Math.min(100, up ? st.speaker_level || 0 : 0)) + '%';
    $('tlat').textContent = up && st.latency_ms !== undefined && st.latency_ms !== null ? (st.latency_ms / 1000).toFixed(2) + ' s' : '-';
    $('ttext').innerHTML = up ? (st.transcript || []).slice(-8).map(l => '<div><span class="t">' + esc(l.who) + ':</span> ' + esc(l.text) + '</div>').join('') : '';
  }
  async function poll() {
    try {
      const r = await get('/talk/state'), body = await r.json();
      if (!r.ok || body.isError) { paint(null); $('tmsg').textContent = body.text || 'The voice bridge is not running here.'; return; }
      paint(body); $('tmsg').textContent = body.message || '';
    } catch (err) { paint(null); $('tmsg').textContent = 'The voice bridge did not answer: ' + err.message + '. Start it and this panel comes alive.'; }
  }
  async function act(action) {
    try { const r = await post('/talk', {action}), body = await r.json(); if (body.isError || body.ok === false) $('tmsg').textContent = 'Refused: ' + (body.text || body.error || 'no reason given') + '.'; }
    catch (err) { $('tmsg').textContent = 'That did not reach the voice bridge: ' + err.message + '.'; }
    poll();
  }
  $('tmic').onclick = () => act(state.st && state.st.mic_on ? 'mic_off' : 'mic_on');
  $('tspk').onclick = () => act(state.st && state.st.speaker_on ? 'speaker_off' : 'speaker_on');
  const timer = setInterval(poll, (opts && opts.every) || 500); poll();
  return {poll, stop: () => clearInterval(timer), get live() { return state.live; }};
}
