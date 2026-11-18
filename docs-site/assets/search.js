// Filters the page list as you type: every word must appear in the title or summary, or anywhere in the page text.
(function () {
  var q = document.getElementById('q'), list = document.getElementById('pages'), count = document.getElementById('count');
  if (!q || !list || !window.SEARCH_INDEX) return;
  var items = Array.prototype.slice.call(list.children);
  var text = {};
  window.SEARCH_INDEX.forEach(function (r) { text[r.u] = (r.t + ' ' + r.s + ' ' + r.x).toLowerCase(); });
  function run() {
    var words = q.value.toLowerCase().split(/\s+/).filter(Boolean), shown = 0;
    items.forEach(function (li) {
      var href = li.querySelector('a').getAttribute('href').replace(/^\.\.\//, '');
      var hay = text[href] || li.getAttribute('data-t');
      var ok = words.every(function (w) { return hay.indexOf(w) !== -1; });
      li.hidden = !ok;
      if (ok) shown++;
    });
    count.textContent = words.length ? shown + ' of ' + items.length + ' pages match' : items.length + ' pages';
  }
  q.addEventListener('input', run);
  run();
})();
