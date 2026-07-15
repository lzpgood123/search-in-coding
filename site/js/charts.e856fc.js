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

  // Simple bar chart for tool coverage — horizontal layout
  barChart(data, maxVal, options) {
    options = options || {};
    data = data || [];
    if (!data.length) {
      return '<svg viewBox="0 0 320 60" style="width:100%;height:60px;" aria-hidden="true"></svg>';
    }

    const padL = 120;  // 左侧标签区域
    const padR = 40;   // 右侧数值区域
    const padT = 8;
    const padB = 24;
    const rowH = 28;   // 每行高度
    const barH = 16;   // 柱子高度

    const n = data.length;
    const chartW = 400; // 柱子区域宽度
    const width = padL + chartW + padR;
    const height = padT + n * rowH + padB;

    const values = data.map((d) => Number(d.value) || 0);
    const niceMax = this._niceMax(maxVal || Math.max(...values, 1));

    // Y 轴标签 + 柱子
    const rows = data.map((d, i) => {
      const val = Math.max(0, Number(d.value) || 0);
      const barW = (val / niceMax) * chartW;
      const y = padT + i * rowH + (rowH - barH) / 2;
      let label = String(d.label || '');
      // 截断到 16 字符
      if (label.length > 16) label = label.slice(0, 15) + '…';

      return '<text x="' + (padL - 8) + '" y="' + (y + barH / 2 + 4) + '" text-anchor="end" font-size="11" fill="var(--color-text-secondary)">' + label + '</text>' +
        '<rect x="' + padL + '" y="' + y + '" width="' + barW + '" height="' + barH + '" fill="var(--color-accent)" rx="3"/>' +
        '<text x="' + (padL + barW + 6) + '" y="' + (y + barH / 2 + 4) + '" text-anchor="start" font-size="11" font-weight="600" fill="var(--color-text-secondary)">' + val + '</text>';
    }).join('');

    // X 轴刻度
    const tickCount = 4;
    let ticks = '';
    for (let t = 0; t <= tickCount; t++) {
      const v = Math.round((niceMax * t) / tickCount);
      const x = padL + (chartW * t / tickCount);
      ticks += '<line x1="' + x + '" y1="' + padT + '" x2="' + x + '" y2="' + (padT + n * rowH) + '" stroke="rgba(255,248,240,0.06)" stroke-width="1"/>' +
        '<text x="' + x + '" y="' + (height - 6) + '" text-anchor="middle" font-size="9" fill="var(--color-text-muted)">' + v + '</text>';
    }

    return '<svg viewBox="0 0 ' + width + ' ' + height + '" style="width:100%;height:auto;" role="img" aria-label="' + (options.ariaLabel || 'chart') + '">' + ticks + rows + '</svg>';
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
