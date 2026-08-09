(function () {
  var page = (document.body && document.body.getAttribute("data-docs-page")) || "";

  var MODES = [
    { id: "index", href: "index.html", label: "Home", short: "Home" },
    { id: "performance", href: "performance.html", label: "Load / performance", short: "Load" },
    { id: "chaos", href: "chaos.html", label: "Chaos", short: "Chaos" },
    { id: "resiliency", href: "resiliency.html", label: "Resiliency", short: "Resilience" },
    { id: "security", href: "security.html", label: "Security", short: "Security" },
    { id: "reports", href: "reports.html", label: "Reports", short: "Reports" },
  ];

  function injectModeTabs() {
    if (document.getElementById("docs-mode-tabs")) return;
    var header = document.querySelector(".docs-header");
    if (!header || !header.parentNode) return;
    var nav = document.createElement("nav");
    nav.id = "docs-mode-tabs";
    nav.className = "docs-mode-tabs";
    nav.setAttribute("aria-label", "Testing modes");
    var inner = document.createElement("div");
    inner.className = "docs-mode-tabs-inner";
    MODES.forEach(function (m) {
      var a = document.createElement("a");
      a.href = m.href;
      a.className = "docs-mode-tab" + (m.id === page ? " active" : "");
      a.setAttribute("data-mode", m.id);
      a.innerHTML =
        '<span class="docs-mode-tab-full">' +
        m.label +
        '</span><span class="docs-mode-tab-short">' +
        m.short +
        "</span>";
      if (m.id === page) a.setAttribute("aria-current", "page");
      inner.appendChild(a);
    });
    nav.appendChild(inner);
    header.insertAdjacentElement("afterend", nav);
  }

  function injectSidebarModes() {
    var side = document.getElementById("docs-sidebar");
    if (!side || side.querySelector("[data-docs-modes]")) return;
    var group = document.createElement("div");
    group.className = "docs-side-group";
    group.setAttribute("data-docs-modes", "1");
    group.innerHTML = '<div class="docs-side-label">Testing modes</div>';
    MODES.slice(1).forEach(function (m) {
      var a = document.createElement("a");
      a.href = m.href;
      a.textContent = m.label;
      if (m.id === page) a.className = "active";
      group.appendChild(a);
    });
    var first = side.querySelector(".docs-side-group");
    if (first && first.nextSibling) {
      side.insertBefore(group, first.nextSibling);
    } else {
      side.appendChild(group);
    }
  }

  var btn = document.getElementById("docs-menu");
  var side = document.getElementById("docs-sidebar");
  if (btn && side) {
    btn.addEventListener("click", function () {
      side.classList.toggle("open");
      btn.setAttribute(
        "aria-expanded",
        side.classList.contains("open") ? "true" : "false",
      );
    });
  }

  injectModeTabs();
  injectSidebarModes();
})();
