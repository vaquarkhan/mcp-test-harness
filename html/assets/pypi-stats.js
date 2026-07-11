/**
 * Live PyPI stats for GitHub Pages (pepy.tech total + rolling 30-day downloads).
 * The static pepy /month badge image is CDN-cached and often lags; this bar
 * fetches fresh JSON on each visit.
 */
(function () {
  const PACKAGE = document.body.dataset.pypiPackage || 'mcp-test-harness';
  const PYPI_JSON = `https://pypi.org/pypi/${PACKAGE}/json`;
  const PEPY_JSON = `https://pepy.tech/api/v2/projects/${PACKAGE}`;

  function fmt(n) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
    if (n >= 10_000) return `${Math.round(n / 1000)}k`;
    if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`;
    return String(n);
  }

  function sumLastDays(downloads, days) {
    if (!downloads || typeof downloads !== 'object') return null;
    const keys = Object.keys(downloads).sort();
    const slice = keys.slice(-days);
    let total = 0;
    for (const day of slice) {
      const perVersion = downloads[day];
      if (perVersion && typeof perVersion === 'object') {
        for (const count of Object.values(perVersion)) {
          total += Number(count) || 0;
        }
      }
    }
    return total;
  }

  function stat(label, value, href) {
    const el = document.createElement(href ? 'a' : 'span');
    el.className = 'pypi-stat';
    if (href) {
      el.href = href;
      el.target = '_blank';
      el.rel = 'noopener noreferrer';
    }
    el.innerHTML = `<span class="pypi-stat-label">${label}</span><span class="pypi-stat-value">${value}</span>`;
    return el;
  }

  async function load() {
    const inner = document.querySelector('#pypi-stats-bar .pypi-stats-inner');
    if (!inner) return;

    try {
      const [pypiRes, pepyRes] = await Promise.all([
        fetch(PYPI_JSON, { cache: 'no-store' }),
        fetch(PEPY_JSON, { cache: 'no-store' }),
      ]);
      if (!pypiRes.ok || !pepyRes.ok) throw new Error('stats fetch failed');

      const pypi = await pypiRes.json();
      const pepy = await pepyRes.json();
      const version = pypi.info?.version || '?';
      const total = Number(pepy.total_downloads) || 0;
      const month = sumLastDays(pepy.downloads, 30);

      inner.replaceChildren();
      inner.appendChild(stat('PyPI version', `v${version}`, `https://pypi.org/project/${PACKAGE}/`));
      inner.appendChild(stat('Total downloads', fmt(total), `https://pepy.tech/project/${PACKAGE}`));
      if (month != null) {
        inner.appendChild(stat('Last 30 days', fmt(month), `https://pepy.tech/project/${PACKAGE}`));
      }
      inner.appendChild(stat('Install', 'pip install mcp-test-harness', `https://pypi.org/project/${PACKAGE}/`));

      const live = document.createElement('span');
      live.className = 'pypi-stat-live';
      live.textContent = 'Live from PyPI';
      inner.appendChild(live);
    } catch {
      inner.innerHTML =
        '<span class="pypi-stat-fallback">PyPI: <a href="https://pypi.org/project/mcp-test-harness/" target="_blank" rel="noopener">mcp-test-harness</a> · stats refresh on next visit</span>';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
