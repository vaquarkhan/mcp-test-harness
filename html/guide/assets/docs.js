(function () {
  var btn = document.getElementById("docs-menu");
  var side = document.getElementById("docs-sidebar");
  if (!btn || !side) return;
  btn.addEventListener("click", function () {
    side.classList.toggle("open");
    btn.setAttribute("aria-expanded", side.classList.contains("open") ? "true" : "false");
  });
})();
