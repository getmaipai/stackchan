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
