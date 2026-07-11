/**
 * Enhance the PyPI stats bar with live JSON (PyPI version + pepy totals).
 * Badge images in the HTML render immediately; JS updates the detail line when
 * fetch succeeds (pepy API may block CORS - badges still show ~10k total).
 */
(function () {
  const PACKAGE = document.body.dataset.pypiPackage || 'mcp-test-harness';
  const PYPI_JSON = `https://pypi.org/pypi/${PACKAGE}/json`;
  const PEPY_JSON = `https://pepy.tech/api/v2/projects/${PACKAGE}`;

  function fmt(n) {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, '')}M`;
    if (n >= 10_000) return `${Math.round(n / 1000)}k`;
    if (n >= 1000) return `${(n / 1000).toFixed(1).replace(/\.0$/, '')}k`;
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
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

  function bustBadgeImages() {
    document.querySelectorAll('#pypi-stats-bar img[data-pepy-total]').forEach((img) => {
      const base = img.getAttribute('src')?.split('?')[0];
      if (base) img.src = `${base}?ts=${Date.now()}`;
    });
  }

  async function load() {
    const detail = document.getElementById('pypi-stats-live-detail');
    if (!detail) return;

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
      const parts = [`Live: v${version}`, `${fmt(total)} total downloads`];
      if (month != null) parts.push(`${fmt(month)} last 30 days`);
      detail.textContent = parts.join(' · ');
      bustBadgeImages();
    } catch {
      detail.textContent = 'Badge totals from pepy/PyPI · live JSON blocked in browser (badges still update on CDN)';
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
