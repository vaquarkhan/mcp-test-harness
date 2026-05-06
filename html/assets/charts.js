/* MCP Test Harness - comparison and feature charts */

const COLORS = {
  primary: '#6366f1',
  primaryLight: 'rgba(99, 102, 241, 0.15)',
  accent: '#10b981',
  accentLight: 'rgba(16, 185, 129, 0.15)',
  purple: '#8b5cf6',
  purpleLight: 'rgba(139, 92, 246, 0.15)',
  rose: '#f43f5e',
  roseLight: 'rgba(244, 63, 94, 0.15)',
  amber: '#f59e0b',
  amberLight: 'rgba(245, 158, 11, 0.15)',
  slate: '#64748b',
  slateLight: 'rgba(100, 116, 139, 0.15)',
};

const SHARED_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        font: { family: 'Inter', size: 12, weight: '500' },
        padding: 16,
        usePointStyle: true,
        pointStyle: 'circle',
      },
    },
    tooltip: {
      backgroundColor: '#0f172a',
      titleColor: '#f8fafc',
      bodyColor: '#cbd5e1',
      borderColor: '#334155',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      titleFont: { family: 'Inter', weight: '600', size: 13 },
      bodyFont: { family: 'Inter', size: 13 },
    },
  },
  scales: {
    x: {
      grid: { color: '#e2e8f0', drawBorder: false },
      ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } },
    },
    y: {
      grid: { color: '#e2e8f0', drawBorder: false },
      ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } },
    },
  },
};

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('featureRadarChart')) renderFeatureRadar();
  if (document.getElementById('testModesChart')) renderTestModes();
  if (document.getElementById('coverageChart')) renderCoverage();
});

function renderFeatureRadar() {
  new Chart(document.getElementById('featureRadarChart'), {
    type: 'radar',
    data: {
      labels: [
        'Functional Testing',
        'Regression / Snapshots',
        'Performance / Latency',
        'CI Integration',
        'Multi-Transport',
        'Plugin System',
        'Security Testing',
      ],
      datasets: [
        {
          label: 'MCP Test Harness',
          data: [5, 5, 5, 5, 5, 5, 4],
          borderColor: COLORS.primary,
          backgroundColor: COLORS.primaryLight,
          borderWidth: 2,
          pointBackgroundColor: COLORS.primary,
          pointBorderColor: '#fff',
          pointRadius: 5,
        },
        {
          label: 'MCP Inspector',
          data: [3, 1, 1, 1, 3, 1, 1],
          borderColor: COLORS.amber,
          backgroundColor: COLORS.amberLight,
          borderWidth: 2,
          pointBackgroundColor: COLORS.amber,
          pointBorderColor: '#fff',
          pointRadius: 5,
        },
        {
          label: 'Manual Testing',
          data: [2, 1, 1, 0, 2, 0, 1],
          borderColor: COLORS.slate,
          backgroundColor: COLORS.slateLight,
          borderWidth: 2,
          pointBackgroundColor: COLORS.slate,
          pointBorderColor: '#fff',
          pointRadius: 5,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      scales: {
        r: {
          suggestedMin: 0,
          suggestedMax: 5,
          ticks: { display: false, stepSize: 1 },
          pointLabels: { font: { family: 'Inter', size: 11, weight: '600' }, color: '#334155' },
          grid: { color: '#e2e8f0' },
          angleLines: { color: '#cbd5e1' },
        },
      },
    },
  });
}

function renderTestModes() {
  new Chart(document.getElementById('testModesChart'), {
    type: 'bar',
    data: {
      labels: ['MCP Test Harness', 'MCP Inspector', 'pytest (manual)', 'Postman/Newman', 'Custom scripts'],
      datasets: [
        { label: 'Functional', data: [5, 3, 4, 3, 3], backgroundColor: COLORS.primary, borderRadius: 4 },
        { label: 'Regression', data: [5, 0, 3, 2, 1], backgroundColor: COLORS.accent, borderRadius: 4 },
        { label: 'Performance', data: [5, 0, 2, 1, 2], backgroundColor: COLORS.purple, borderRadius: 4 },
        { label: 'CI/CD', data: [5, 1, 4, 4, 2], backgroundColor: COLORS.amber, borderRadius: 4 },
      ],
    },
    options: {
      ...SHARED_OPTS,
      scales: {
        ...SHARED_OPTS.scales,
        x: { ...SHARED_OPTS.scales.x, stacked: false },
        y: { ...SHARED_OPTS.scales.y, beginAtZero: true, max: 5, title: { display: true, text: 'Capability (0-5)', color: '#475569' } },
      },
    },
  });
}

function renderCoverage() {
  new Chart(document.getElementById('coverageChart'), {
    type: 'doughnut',
    data: {
      labels: ['Assertions (12)', 'Fixtures (4)', 'Transports (3)', 'Reports (3)', 'Markers (4)'],
      datasets: [{
        data: [12, 4, 3, 3, 4],
        backgroundColor: [COLORS.primary, COLORS.accent, COLORS.purple, COLORS.amber, COLORS.rose],
        borderColor: '#fff',
        borderWidth: 3,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { font: { family: 'Inter', size: 12 }, padding: 16 } },
      },
      cutout: '55%',
    },
  });
}
