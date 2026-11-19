// The Light/dark button: switches the page and remembers the choice on this device only.
(function () {
  var b = document.getElementById('theme');
  if (!b) return;
  b.addEventListener('click', function () {
    var root = document.documentElement;
    var cur = root.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    var next = cur === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) { /* storage blocked: the choice lasts until the page closes */ }
  });
})();
// The page list on the left: open on a wide screen, folded on a phone so the page text is the first thing there. Without JavaScript it stays open.
(function () {
  var d = document.querySelector('details.tabsd');
  if (!d || !window.matchMedia) return;
  var mq = matchMedia('(max-width: 820px)');
  function sync() { d.open = !mq.matches; }
  sync();
  if (mq.addEventListener) mq.addEventListener('change', sync);
  d.addEventListener('toggle', function () { if (!mq.matches && !d.open) d.open = true; });
})();
