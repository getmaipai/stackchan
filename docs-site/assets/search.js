// The search box under the header, on every page. It reads the index file that ships with the site (assets/search-index.js), so it works with no network.
// The index loads the first time you use the box, so a page that nobody searches from does not pay for it.
// On the Search page the same box filters the full page list there; on every other page it shows the best matches in a list under the box.
// Keys: type to search, Down and Up to move, Enter to open the marked page (or all matches on the Search page), Escape to close, / to jump to the box.
(function () {
  var form = document.getElementById('sitesearch');
  var q = document.getElementById('sitesearch-q');
  var box = document.getElementById('sitesearch-results');
  if (!form || !q || !box) return;
  // Tell the style sheet how tall the header is, so the page list and the page text fill the rest of the window.
  var head = document.querySelector('header.top');
  function sizeHeader() { if (head) document.documentElement.style.setProperty('--hh', head.offsetHeight + 'px'); }
  sizeHeader();
  window.addEventListener('resize', sizeHeader);
  window.addEventListener('load', sizeHeader);
  var base = form.getAttribute('data-base') || '';
  var pages = document.getElementById('pages'), count = document.getElementById('count');
  var MAX = 8, items = [], active = -1, haystack = null, loading = false, waiting = null;

  function words() { return q.value.toLowerCase().split(/\s+/).filter(Boolean); }

  function build() {
    haystack = {};
    (window.SEARCH_INDEX || []).forEach(function (r) { haystack[r.u] = { r: r, title: r.t.toLowerCase(), sum: r.s.toLowerCase(), all: (r.t + ' ' + r.s + ' ' + r.x).toLowerCase() }; });
  }

  function ensureIndex(then) {
    if (window.SEARCH_INDEX) { if (!haystack) build(); then(); return; }
    waiting = then;   // the newest request wins: the box may have changed while the file loaded
    if (loading) return;
    loading = true;
    var s = document.createElement('script');
    s.src = form.getAttribute('data-index');
    s.onload = function () { loading = false; build(); if (waiting) waiting(); };
    s.onerror = function () {
      loading = false;
      show([], 'The search index did not load. Reload the page, or open the Search page from the menu.');
    };
    document.head.appendChild(s);
  }

  function score(h, ws) {
    var n = 0;
    for (var i = 0; i < ws.length; i++) {
      var w = ws[i];
      if (h.all.indexOf(w) === -1) return -1;
      if (h.title.indexOf(w) !== -1) n += 10;
      if (h.sum.indexOf(w) !== -1) n += 3;
    }
    return n;
  }

  function mark(i) {
    var links = box.querySelectorAll('a');
    for (var k = 0; k < links.length; k++) links[k].setAttribute('aria-selected', k === i ? 'true' : 'false');
    active = i;
    if (i >= 0 && links[i]) { q.setAttribute('aria-activedescendant', links[i].id); links[i].scrollIntoView({ block: 'nearest' }); }
    else q.removeAttribute('aria-activedescendant');
  }

  function show(list, note) {
    box.textContent = '';
    active = -1;
    q.removeAttribute('aria-activedescendant');
    if (!list.length && !note) { box.hidden = true; q.setAttribute('aria-expanded', 'false'); return; }
    if (note) {
      var li0 = document.createElement('li');
      li0.className = 'none';
      li0.setAttribute('role', 'presentation');
      li0.textContent = note;
      box.appendChild(li0);
    }
    list.forEach(function (h, i) {
      var li = document.createElement('li'), a = document.createElement('a'), t = document.createElement('span'), s = document.createElement('span');
      li.setAttribute('role', 'presentation');
      a.href = base + h.r.u;
      a.id = 'sitesearch-r' + i;
      a.setAttribute('role', 'option');
      a.setAttribute('aria-selected', 'false');
      t.className = 't'; t.textContent = h.r.t;
      s.className = 's'; s.textContent = h.r.s.length > 110 ? h.r.s.slice(0, 107) + '...' : h.r.s;
      a.appendChild(t); a.appendChild(s); li.appendChild(a); box.appendChild(li);
    });
    box.hidden = false;
    q.setAttribute('aria-expanded', 'true');
  }

  function filterList(ws) {
    var shown = 0, total = pages.children.length;
    Array.prototype.forEach.call(pages.children, function (li) {
      var href = li.querySelector('a').getAttribute('href');
      var h = haystack && haystack[href];
      var hay = h ? h.all : li.getAttribute('data-t');
      var ok = ws.every(function (w) { return hay.indexOf(w) !== -1; });
      li.hidden = !ok;
      if (ok) shown++;
    });
    if (count) count.textContent = ws.length ? shown + ' of ' + total + ' pages match' : total + ' pages';
  }

  function run() {
    var ws = words();
    if (pages) { ensureIndex(function () { filterList(ws); }); filterList(ws); return; }
    if (!ws.length) { show([]); return; }
    ensureIndex(function () {
      var ws2 = words();
      if (!ws2.length) { show([]); return; }
      var hits = [];
      Object.keys(haystack).forEach(function (u) { var n = score(haystack[u], ws2); if (n >= 0) hits.push({ n: n, r: haystack[u].r }); });
      hits.sort(function (a, b) { return b.n - a.n || a.r.t.localeCompare(b.r.t); });
      items = hits.slice(0, MAX).map(function (h) { return { r: h.r }; });
      show(items, hits.length ? (hits.length > MAX ? 'Showing ' + MAX + ' of ' + hits.length + ' pages. Press Enter to see them all.' : '') : 'No page matches "' + q.value.trim() + '". Try fewer or shorter words.');
    });
  }

  q.addEventListener('input', run);
  q.addEventListener('focus', function () { ensureIndex(function () {}); });
  q.addEventListener('keydown', function (e) {
    var n = box.querySelectorAll('a').length;
    if (e.key === 'ArrowDown' && n) { e.preventDefault(); mark(active + 1 >= n ? 0 : active + 1); }
    else if (e.key === 'ArrowUp' && n) { e.preventDefault(); mark(active <= 0 ? n - 1 : active - 1); }
    else if (e.key === 'Escape') { if (!box.hidden) { e.preventDefault(); show([]); } else q.value = ''; if (pages) run(); }
  });
  form.addEventListener('submit', function (e) {
    var links = box.querySelectorAll('a');
    if (active >= 0 && links[active]) { e.preventDefault(); location.href = links[active].href; }
    else if (pages) e.preventDefault();
  });
  document.addEventListener('click', function (e) { if (!form.contains(e.target)) show([]); });
  document.addEventListener('keydown', function (e) {
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test(tag) && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); q.focus(); q.select(); }
  });

  // The Search page gets ?q=words from the box on other pages (Enter with no page marked) and shows the matches there.
  var m = /[?&]q=([^&]*)/.exec(location.search);
  if (m) { try { q.value = decodeURIComponent(m[1].replace(/\+/g, ' ')); } catch (e) { q.value = ''; } }
  if (pages) { run(); if (!m) q.focus(); }
})();
