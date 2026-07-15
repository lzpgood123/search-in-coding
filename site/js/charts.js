// site/js/charts.js
// Native SVG charts for tool overview and score distribution
// Style B: readable axes, grid, value labels, compact height
// API compatible: barChart(data, maxVal), histogram(scores)
const SIC_charts = {
  _niceMax(maxVal) {
    const m = Math.max(1, Number(maxVal) || 1);
    if (m <= 5) return m;
    const exp = Math.pow(10, Math.floor(Math.log10(m)));
    const n = m / exp;
    const nice = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
    return nice * exp;
  },

  // Simple bar chart for tool coverage (optional 3rd options arg is ignored by callers)
  barChart(data, maxVal, options) {
    options = options || {};
    data = data || [];
    if (!data.length) {
      return '<svg viewBox="0 0 320 120" style="width:100%;height:120px;" aria-hidden="true"></svg>';
    }

    const padL = 36;
    const padR = 10;
    const padT = 18;
    const padB = 34;
    const chartH = 150;
    const barGap = 8;
    const minBarW = 22;
    const maxBarW = 42;
    const labelMax = 8;

    const n = data.length;
    const plotW = Math.max(n * (minBarW + barGap) + barGap, 220);
    const barW = Math.min(maxBarW, Math.max(minBarW, (plotW - barGap * (n + 1)) / n));
    const width = padL + plotW + padR;
    const height = padT + chartH + padB;
    const values = data.map((d) => Number(d.value) || 0);
    const niceMax = this._niceMax(maxVal || Math.max(...values, 1));
    const tickCount = 4;
    const ticks = [];
    for (let t = 0; t <= tickCount; t++) {
      ticks.push(Math.round((niceMax * t) / tickCount));
    }

    const grid = ticks.map((v) => {
      const y = padT + chartH - (v / niceMax) * chartH;
      return `<line x1="${padL}" y1="${y}" x2="${padL + plotW}" y2="${y}" stroke="rgba(255,248,240,0.08)" stroke-width="1"/>` +
        `<text x="${padL - 6}" y="${y + 3}" text-anchor="end" font-size="10" fill="var(--color-text-muted)">${v}</text>`;
    }).join('');

    const bars = data.map((d, i) => {
      const val = Math.max(0, Number(d.value) || 0);
      const h = Math.max(val > 0 ? 2 : 0, (val / niceMax) * chartH);
      const x = padL + barGap + i * (barW + barGap);
      const y = padT + chartH - h;
      const label = String(d.label || '').slice(0, labelMax);
      const valueY = Math.max(padT + 10, y - 4);
      return `<rect x="${x}" y="${y}" width="${barW}" height="${h}" fill="var(--color-accent)" rx="4"/>` +
        `<text x="${x + barW / 2}" y="${valueY}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--color-text-secondary)">${val}</text>` +
        `<text x="${x + barW / 2}" y="${padT + chartH + 14}" text-anchor="middle" font-size="10" fill="var(--color-text-muted)">${label}</text>`;
    }).join('');

    const axis =
      `<line x1="${padL}" y1="${padT + chartH}" x2="${padL + plotW}" y2="${padT + chartH}" stroke="rgba(255,248,240,0.16)" stroke-width="1"/>` +
      `<line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + chartH}" stroke="rgba(255,248,240,0.16)" stroke-width="1"/>`;

    return `<svg viewBox="0 0 ${width} ${height}" style="width:100%;height:auto;max-height:210px;" role="img" aria-label="${options.ariaLabel || 'chart'}">${grid}${axis}${bars}</svg>`;
  },

  // Score distribution histogram
  histogram(scores) {
    const buckets = [0, 0, 0, 0, 0]; // 0-20, 21-40, 41-60, 61-80, 81-100
    for (const s of scores || []) {
      const v = Number(s) || 0;
      if (v <= 20) buckets[0]++;
      else if (v <= 40) buckets[1]++;
      else if (v <= 60) buckets[2]++;
      else if (v <= 80) buckets[3]++;
      else buckets[4]++;
    }
    const max = Math.max(...buckets, 1);
    return this.barChart(
      [
        { label: '0-20', value: buckets[0] },
        { label: '21-40', value: buckets[1] },
        { label: '41-60', value: buckets[2] },
        { label: '61-80', value: buckets[3] },
        { label: '81-100', value: buckets[4] },
      ],
      max,
      { ariaLabel: 'score distribution' }
    );
  },
};
