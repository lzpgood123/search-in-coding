// site/js/charts.js
// Native SVG charts for tool overview and score distribution
const SIC_charts = {
  // Simple bar chart for tool coverage
  barChart(data, maxVal) {
    const bars = data.map((d, i) => {
      const h = Math.max(2, (d.value / maxVal) * 100);
      const y = 100 - h;
      return `<rect x="${i * 40 + 5}" y="${y}" width="30" height="${h}" fill="var(--color-accent)" rx="2"/>
              <text x="${i * 40 + 20}" y="115" text-anchor="middle" font-size="9" fill="var(--color-text-muted)">${d.label.slice(0, 6)}</text>`;
    }).join('');
    return `<svg viewBox="0 0 ${data.length * 40 + 10} 130" style="width:100%;height:130px;">${bars}</svg>`;
  },

  // Score distribution histogram
  histogram(scores) {
    const buckets = [0,0,0,0,0]; // 0-20, 21-40, 41-60, 61-80, 81-100
    for (const s of scores) {
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
        {label: '0-20', value: buckets[0]},
        {label: '21-40', value: buckets[1]},
        {label: '41-60', value: buckets[2]},
        {label: '61-80', value: buckets[3]},
        {label: '81-100', value: buckets[4]},
      ],
      max
    );
  },
};
