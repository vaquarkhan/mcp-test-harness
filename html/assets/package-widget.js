/**
 * Live PyPI version + download badges from ecosystem-downloads.json
 * (Bastion-style all-time totals). Fallback: static package list + pepy badges.
 */
(function () {
  const ECOSYSTEM_JSON = 'assets/ecosystem-downloads.json';

  function formatCount(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(n);
  }

  function buildDownloadsCell(pkg) {
    const badge =
      pkg.badge_shields ||
      `https://img.shields.io/endpoint?url=${encodeURIComponent(
        `https://raw.githubusercontent.com/vaquarkhan/mcp-test-harness/main/html/assets/badges/${pkg.package}-downloads.json`
      )}`;
    const link = pkg.stats_status === 'indexed' ? pkg.pypistats : pkg.pypi;
    const statsLink =
      pkg.stats_status === 'indexed'
        ? `<a href="${pkg.pypistats}" target="_blank" rel="noopener noreferrer">pypistats</a>`
        : `<span class="text-slate-400">stats pending</span>`;
    return `<a href="${link}" target="_blank" rel="noopener noreferrer"><img src="${badge}" alt="Downloads ${pkg.package}" height="20" loading="lazy" /></a> · ${statsLink}`;
  }

  function renderPackageTable(packages) {
    const tbody = document.getElementById('pypi-widget-body');
    if (!tbody) return;
    tbody.replaceChildren();
    packages.forEach((pkg) => {
      const name = pkg.package;
      const label = pkg.protects || '';
      const tr = document.createElement('tr');
      tr.className = 'pypi-widget-row';
      tr.innerHTML = `
        <td class="pypi-widget-name"><a href="https://pypi.org/project/${name}/" target="_blank" rel="noopener noreferrer">${name}</a></td>
        <td class="pypi-widget-label">${label}</td>
        <td class="pypi-widget-version"><a href="https://pypi.org/project/${name}/" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/pypi/v/${name}?label=version&amp;color=indigo" alt="PyPI ${name}" height="20" loading="lazy" /></a></td>
        <td class="pypi-widget-dl">${buildDownloadsCell(pkg)}</td>
        <td class="pypi-widget-cmd"><code>pip install ${name}</code></td>`;
      tbody.appendChild(tr);
    });
  }

  function updateHero(data) {
    const el = document.getElementById('ecosystem-total-count');
    const meta = document.getElementById('ecosystem-total-meta');
    if (el) el.textContent = formatCount(data.total_downloads || 0);
    if (meta) {
      const updated = (data.updated_at || '').slice(0, 10);
      const pending = data.pending_count || 0;
      const pendingNote = pending
        ? ` · ${pending} new package${pending === 1 ? '' : 's'} pending pypistats index`
        : '';
      meta.textContent = `${data.indexed_count || data.package_count}/${data.package_count || 26} indexed · updated ${updated || '—'}${pendingNote}`;
    }
  }

  function load() {
    fetch(ECOSYSTEM_JSON, { cache: 'no-store' })
      .then((r) => {
        if (!r.ok) throw new Error('ecosystem json missing');
        return r.json();
      })
      .then((data) => {
        renderPackageTable(data.packages || []);
        updateHero(data);
      })
      .catch(() => {
        const meta = document.getElementById('ecosystem-total-meta');
        if (meta) {
          meta.textContent =
            'Could not load ecosystem-downloads.json — run scripts/update_ecosystem_downloads.py';
        }
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
