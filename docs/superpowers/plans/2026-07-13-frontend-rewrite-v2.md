# 前端重写 v2 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 全部重写前端 6 个 JS 模块 + index.html + styles.css 补丁 + generate_reports.py 重写，修复全部 10 个 bug，确保每个交互真正可用。

**架构：** 零依赖原生 JS，6 模块多 `<script>` 加载。事件委托替代 inline onclick。filters.js 纯逻辑无 DOM 依赖。

**技术栈：** 纯 HTML + CSS + 原生 JS，Python 3.12+（generate_reports.py）

**关联文档：**
- 设计规格：`docs/superpowers/specs/2026-07-13-frontend-rewrite-v2-design.md`
- ADR-0006：零依赖模块化
- 前置：第 1 批已完成（数据结构已迁移），第 2 批代码存在但质量差需重写

---

## 文件结构

### 重写文件（覆盖现有）

| 文件 | 说明 |
|------|------|
| `site/js/i18n.js` | 保持现有逻辑，微调 |
| `site/js/data.js` | 保持现有逻辑，微调 |
| `site/js/filters.js` | 实现 recentOnly，纯逻辑 |
| `site/js/render.js` | 重写：发现区逻辑、虚拟滚动修复、charts 调用、LLM summary 修复、markdown 渲染重写 |
| `site/js/charts.js` | 保持现有，确保被调用 |
| `site/js/app.js` | 重写：事件委托替代 inline onclick |
| `site/index.html` | 微调：加 recentOnly checkbox、分数分布图容器、移动端表格容器 |
| `site/styles.css` | 补丁：移动端表格 overflow-x、导出收藏输入框样式 |
| `scripts/generate_reports.py` | 完全重写：3 份新报告 |

---

## 任务 1：重写 filters.js（纯逻辑 + recentOnly）

**文件：** `site/js/filters.js`

- [ ] **步骤 1：重写 filters.js**

重写要点：
1. `apply()` 中实现 `recentOnly` 逻辑：计算最近 50 条项目的 first_seen cutoff 日期，筛选 `first_seen >= cutoff`
2. 保持 `selectedTools`/`selectedTypes`/`searchQuery`/`sortBy`/`matchMode`/`curatedOnly` 逻辑不变
3. 保持 URL state 读写不变
4. 不引用任何 DOM 对象（纯逻辑）

```javascript
// site/js/filters.js
const SIC_filters = {
  selectedTools: new Set(),
  selectedTypes: new Set(),
  searchQuery: '',
  sortBy: 'score',
  matchMode: 'or',
  curatedOnly: false,
  recentOnly: false,

  toggleTool(id) {
    if (this.selectedTools.has(id)) this.selectedTools.delete(id);
    else this.selectedTools.add(id);
  },
  toggleType(type) {
    if (this.selectedTypes.has(type)) this.selectedTypes.delete(type);
    else this.selectedTypes.add(type);
  },
  toggleMode() {
    this.matchMode = this.matchMode === 'or' ? 'and' : 'or';
  },
  clearTools() {
    this.selectedTools.clear();
  },
  setTool(id) {
    this.selectedTools.clear();
    this.selectedTools.add(id);
  },

  _recentCutoff(projects) {
    const dates = projects
      .map(p => p.first_seen || p.last_seen || '')
      .filter(Boolean)
      .sort();
    return dates[Math.max(0, dates.length - 50)] || '';
  },

  apply(projects, curatedIds) {
    const cutoff = this.recentOnly ? this._recentCutoff(projects) : '';
    let rows = projects.filter(p => {
      if (p.source_type === 'official-seed') return false;
      if (p.tracking_priority === 'reject') return false;

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        const text = JSON.stringify(p).toLowerCase();
        if (!text.includes(q)) return false;
      }

      if (this.selectedTools.size > 0) {
        const pTools = p.target_tools || [];
        if (this.matchMode === 'and') {
          if (![...this.selectedTools].every(t => pTools.includes(t))) return false;
        } else {
          if (![...this.selectedTools].some(t => pTools.includes(t))) return false;
        }
      }

      if (this.selectedTypes.size > 0) {
        const pTypes = p.resource_type || [];
        if (this.matchMode === 'and') {
          if (![...this.selectedTypes].every(t => pTypes.includes(t))) return false;
        } else {
          if (![...this.selectedTypes].some(t => pTypes.includes(t))) return false;
        }
      }

      if (this.curatedOnly && !curatedIds.has(p.id)) return false;
      if (this.recentOnly) {
        const pDate = p.first_seen || p.last_seen || '';
        if (pDate < cutoff) return false;
      }
      return true;
    });

    rows.sort((a, b) => {
      switch (this.sortBy) {
        case 'name': return SIC_i18n.textOf(a, 'name').localeCompare(SIC_i18n.textOf(b, 'name'));
        case 'stars': return (b.stars || 0) - (a.stars || 0);
        case 'updated': return String(b.last_updated || '').localeCompare(String(a.last_updated || ''));
        case 'recent': return String(b.first_seen || b.last_seen || '').localeCompare(String(a.first_seen || a.last_seen || ''));
        case 'match': {
          const aMatch = this._matchCount(a);
          const bMatch = this._matchCount(b);
          if (bMatch !== aMatch) return bMatch - aMatch;
          return (b.total_score || 0) - (a.total_score || 0);
        }
        default: return (b.total_score || 0) - (a.total_score || 0);
      }
    });
    return rows;
  },

  _matchCount(p) {
    let count = 0;
    const pTools = p.target_tools || [];
    const pTypes = p.resource_type || [];
    for (const t of this.selectedTools) if (pTools.includes(t)) count++;
    for (const t of this.selectedTypes) if (pTypes.includes(t)) count++;
    return count;
  },

  readState() {
    const qs = new URLSearchParams(location.search);
    if (qs.get('q')) this.searchQuery = qs.get('q');
    if (qs.get('tools')) qs.get('tools').split(',').forEach(t => this.selectedTools.add(t));
    if (qs.get('types')) qs.get('types').split(',').forEach(t => this.selectedTypes.add(t));
    if (qs.get('sort')) this.sortBy = qs.get('sort');
    if (qs.get('mode')) this.matchMode = qs.get('mode');
    if (qs.get('curated') === '1') this.curatedOnly = true;
    if (qs.get('recent') === '1') this.recentOnly = true;
    if (location.hash.startsWith('#favorites=')) {
      const ids = location.hash.slice(12).split(',').filter(Boolean);
      ids.forEach(id => SIC_data.favorites.add(id));
      localStorage.setItem('sic_favorites', JSON.stringify([...SIC_data.favorites]));
    }
  },

  writeState() {
    const qs = new URLSearchParams();
    if (this.searchQuery) qs.set('q', this.searchQuery);
    if (this.selectedTools.size) qs.set('tools', [...this.selectedTools].join(','));
    if (this.selectedTypes.size) qs.set('types', [...this.selectedTypes].join(','));
    if (this.sortBy !== 'score') qs.set('sort', this.sortBy);
    if (this.matchMode === 'and') qs.set('mode', 'and');
    if (this.curatedOnly) qs.set('curated', '1');
    if (this.recentOnly) qs.set('recent', '1');
    history.replaceState(null, '', `${location.pathname}${qs.toString() ? '?' + qs : ''}`);
  },
};
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/filters.js
git commit -m "fix: rewrite filters.js with recentOnly implementation and setTool/clearTools helpers"
```

---

## 任务 2：重写 render.js（10 个 bug 修复的核心）

**文件：** `site/js/render.js`

- [ ] **步骤 1：重写 render.js**

重写要点：
1. `renderDiscovery()`：改为"最新发现"，按 first_seen 降序 + 分数降序取 Top 12，不按 7 天 cutoff
2. `renderToolOverview()`：调用 `SIC_charts.barChart()` 画工具覆盖柱状图
3. `renderScoreChart()`：新增，调用 `SIC_charts.histogram()` 画分数分布
4. `renderMore()`：修复虚拟滚动，每次加载后对新最后一行重新 observe，clear 时 disconnect
5. `openDetail()`：llm_summary 按 `{zh, en}` 对象直接取值（`detail.llm_summary?.[SIC_i18n.lang]`）
6. `renderReport()`：重写 markdown 渲染器，支持标题/段落/无序列表/表格/代码/链接
7. 所有动态生成的元素用 `data-action` 和 `data-id` 属性，不用 inline onclick

```javascript
// site/js/render.js
const SIC_render = {
  PAGE_SIZE: 50,
  renderedCount: 0,
  currentFiltered: [],
  _observer: null,

  $: id => document.getElementById(id),
  esc: s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  safeUrl: raw => { try { const u = new URL(String(raw||''), location.href); if (['http:','https:'].includes(u.protocol)) return u.href; } catch(_){} return '#'; },
  pills: xs => (xs||[]).map(x => `<span class="pill">${this.esc(x)}</span>`).join(''),
  safeNum: v => { const n = Number(v); return Number.isFinite(n) ? String(n) : '0'; },

  renderAll() {
    SIC_i18n.applyLanguage();
    this.renderMetrics();
    this.renderDiscovery();
    this.renderToolOverview();
    this.renderScoreChart();
    this.renderSearchZone();
    SIC_filters.writeState();
  },

  renderMetrics() {
    const m = SIC_data.metrics;
    const keys = ['projects', 'curated', 'rejected', 'official_tools', 'ecosystem_projects'];
    this.$('metrics').innerHTML = keys.map(k =>
      `<div class="stat"><b>${this.safeNum(m[k] ?? 0)}</b><br><span class="muted">${SIC_i18n.t('metrics')[k]}</span></div>`
    ).join('');
  },

  // Bug 1 fix: "最新发现" instead of "本周新发现"
  renderDiscovery() {
    const recent = SIC_data.projects
      .filter(p => p.tracking_priority !== 'reject' && p.source_type !== 'official-seed')
      .sort((a, b) => {
        const dateCmp = String(b.first_seen || b.last_seen || '').localeCompare(String(a.first_seen || a.last_seen || ''));
        if (dateCmp !== 0) return dateCmp;
        return (b.total_score || 0) - (a.total_score || 0);
      })
      .slice(0, 12);

    if (recent.length === 0) {
      this.$('discovery').innerHTML = `<p class="hint">${SIC_i18n.t('discoveryHint')}</p>`;
      return;
    }

    this.$('discovery').innerHTML = recent.map(p => `
      <div class="discovery-card" data-action="detail" data-id="${this.esc(p.id)}">
        <span class="score-badge">${this.safeNum(p.total_score)}</span>
        <b>${this.esc(SIC_i18n.textOf(p, 'name'))}</b><br>
        <span class="muted">${this.esc((SIC_i18n.textOf(p, 'summary') || '').slice(0, 80))}</span><br>
        ${this.pills(p.resource_type)}
      </div>
    `).join('');
  },

  // Bug 6 fix: charts.js is called
  renderToolOverview() {
    const tools = SIC_data.tools.filter(t => t.id !== 'general-ai-coding');
    this.$('toolOverview').innerHTML = tools.map(t => {
      const count = SIC_data.projects.filter(p =>
        (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject'
      ).length;
      const curated = SIC_data.curated.filter(p => (p.target_tools || []).includes(t.id)).length;
      return `
        <div class="tool-card" data-action="tool-filter" data-tool="${this.esc(t.id)}">
          <h3>${this.esc(SIC_i18n.textOf(t, 'name') || t.name)}</h3>
          <div class="tool-stats">${count} ${SIC_i18n.lang === 'zh' ? '个项目' : ' projects'} · ${curated} ${SIC_i18n.lang === 'zh' ? '推荐' : ' curated'}</div>
        </div>
      `;
    }).join('');

    // Draw bar chart for tool coverage
    const chartData = tools.map(t => ({
      label: (SIC_i18n.textOf(t, 'name') || t.name).slice(0, 8),
      value: SIC_data.projects.filter(p => (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject').length,
    }));
    const maxVal = Math.max(...chartData.map(d => d.value), 1);
    const chartEl = this.$('toolChart');
    if (chartEl) chartEl.innerHTML = SIC_charts.barChart(chartData, maxVal);
  },

  // Bug 6 fix: score distribution histogram
  renderScoreChart() {
    const scores = SIC_data.projects
      .filter(p => p.tracking_priority !== 'reject' && p.source_type !== 'official-seed')
      .map(p => p.total_score || 0);
    const chartEl = this.$('scoreChart');
    if (chartEl && scores.length > 0) {
      chartEl.innerHTML = SIC_charts.histogram(scores);
    }
  },

  renderSearchZone() {
    const curatedIds = SIC_data.curatedIds();
    this.currentFiltered = SIC_filters.apply(SIC_data.projects, curatedIds);
    this.renderedCount = 0;

    // Bug 4 fix: disconnect old observer before clearing
    if (this._observer) {
      this._observer.disconnect();
    }
    this.$('rows').innerHTML = '';

    if (this.currentFiltered.length === 0) {
      this.$('rows').innerHTML = `<tr><td colspan="6" class="empty-box">${SIC_i18n.t('noResults')}<br><span class="muted">${SIC_i18n.t('adjustFilter')}</span></td></tr>`;
      return;
    }

    this.renderMore();
  },

  // Bug 4 fix: re-observe new last row after each load
  renderMore() {
    const start = this.renderedCount;
    const end = Math.min(start + this.PAGE_SIZE, this.currentFiltered.length);
    const curatedIds = SIC_data.curatedIds();
    const self = this;

    const html = this.currentFiltered.slice(start, end).map(p => {
      const isFav = SIC_data.isFav(p.id);
      const isCurated = curatedIds.has(p.id);
      return `<tr>
        <td>
          <b>${this.esc(SIC_i18n.textOf(p, 'name'))}</b><br>
          <span class="muted">${this.esc((SIC_i18n.textOf(p, 'summary') || '').slice(0, 100))}</span>
        </td>
        <td>${this.pills(p.resource_type)}</td>
        <td>${this.esc((p.target_tools || []).join(', '))}</td>
        <td><b>${this.safeNum(p.total_score)}</b></td>
        <td>${this.safeNum(p.stars)}</td>
        <td>
          <a href="${this.safeUrl(p.url)}" target="_blank" rel="noopener noreferrer">${SIC_i18n.t('open')}</a>
          <button class="fav-btn ${isFav ? 'active' : ''}" data-action="fav" data-id="${this.esc(p.id)}">★</button>
          ${isCurated ? `<span class="pill">${SIC_i18n.t('curated')}</span>` : ''}
          <button data-action="detail" data-id="${this.esc(p.id)}">${SIC_i18n.t('details')}</button>
        </td>
      </tr>`;
    }).join('');
    this.$('rows').insertAdjacentHTML('beforeend', html);
    this.renderedCount = end;

    // Bug 4 fix: create observer once, re-observe new last row
    if (this.renderedCount < this.currentFiltered.length) {
      if (!this._observer) {
        this._observer = new IntersectionObserver(entries => {
          if (entries[0].isIntersecting && self.renderedCount < self.currentFiltered.length) {
            self._observer.unobserve(entries[0].target);
            self.renderMore();
          }
        });
      }
      const lastRow = this.$('rows').lastElementChild;
      if (lastRow) this._observer.observe(lastRow);
    }
  },

  // Bug 7 fix: llm_summary as {zh, en} object
  async openDetail(projectId) {
    const p = SIC_data.projects.find(x => x.id === projectId);
    if (!p) return;
    const detail = await SIC_data.loadDetail(projectId);
    const overlay = this.$('detailOverlay');
    const curatedIds = SIC_data.curatedIds();
    const isFav = SIC_data.isFav(p.id);
    const qScore = p.quantifiable_score || 0;
    const qualityScore = p.quality_score || 0;
    const total = p.total_score || 0;

    // Bug 7 fix: llm_summary is {zh, en}, not i18n structure
    const llmSummary = detail?.llm_summary;
    const summaryText = llmSummary
      ? (llmSummary[SIC_i18n.lang] || llmSummary.en || llmSummary.zh || '')
      : '';

    overlay.innerHTML = `
      <button class="detail-close" data-action="close-detail">&times;</button>
      <h2>${this.esc(SIC_i18n.textOf(p, 'name'))}</h2>
      <p class="muted">${this.esc(SIC_i18n.textOf(p, 'summary') || '')}</p>

      <div class="detail-section">
        <h3>${SIC_i18n.t('scoreDetail')}</h3>
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">
          <span class="score-badge" style="font-size:20px;padding:4px 12px;">${this.safeNum(total)}</span>
          <span class="muted">/ 100</span>
        </div>
        <div style="margin-bottom:6px;">${SIC_i18n.t('quantifiable')}: ${this.safeNum(qScore)}/60
          <div class="score-bar"><div class="score-bar-fill" style="width:${qScore/60*100}%"></div></div>
        </div>
        <div>${SIC_i18n.t('quality')}: ${this.safeNum(qualityScore)}/40
          <div class="score-bar"><div class="score-bar-fill" style="width:${qualityScore/40*100}%"></div></div>
        </div>
      </div>

      <div class="detail-section">
        <h3>${SIC_i18n.t('details')}</h3>
        <p>${this.pills(p.resource_type)}</p>
        <p>${this.esc((p.target_tools || []).join(', '))}</p>
        <p class="muted">Stars: ${this.safeNum(p.stars)} · Forks: ${this.safeNum(p.forks)}</p>
        <p class="muted">License: ${this.esc(p.license || 'N/A')}</p>
        <p class="muted">Languages: ${this.esc((p.languages || []).join(', '))}</p>
        <p class="muted">First seen: ${this.esc(p.first_seen)} · Last seen: ${this.esc(p.last_seen)}</p>
        <p class="muted">Tracking: ${this.esc(p.tracking_priority)}</p>
      </div>

      ${summaryText ? `<div class="detail-section"><h3>LLM Summary</h3><p>${this.esc(summaryText)}</p></div>` : ''}

      ${detail?.benchmark_ref ? `<div class="detail-section"><h3>${SIC_i18n.t('benchmarkRef')}</h3><p class="muted">${this.esc(detail.benchmark_ref)}</p></div>` : ''}

      <div class="detail-section">
        <h3>${SIC_i18n.t('relatedProjects')}</h3>
        <div id="relatedProjects">...</div>
      </div>

      <div class="detail-section">
        <a href="${this.safeUrl(p.url)}" target="_blank" rel="noopener noreferrer">${SIC_i18n.t('open')} →</a>
        <button class="fav-btn ${isFav ? 'active' : ''}" data-action="fav" data-id="${this.esc(p.id)}">${isFav ? SIC_i18n.t('favorited') : SIC_i18n.t('favorite')}</button>
      </div>
    `;
    overlay.classList.add('open');

    // Related projects
    const related = SIC_data.projects
      .filter(x => x.id !== p.id && x.tracking_priority !== 'reject')
      .filter(x => {
        const sharedType = (x.resource_type || []).some(rt => (p.resource_type || []).includes(rt));
        const sharedTool = (x.target_tools || []).some(tt => (p.target_tools || []).includes(tt));
        return sharedType || sharedTool;
      })
      .sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
      .slice(0, 5);
    const relatedEl = document.getElementById('relatedProjects');
    if (relatedEl) {
      relatedEl.innerHTML = related.length ? related.map(r =>
        `<div style="margin-bottom:6px;"><a href="javascript:void(0)" data-action="detail" data-id="${this.esc(r.id)}">${this.esc(SIC_i18n.textOf(r, 'name'))}</a> <span class="muted">(${this.safeNum(r.total_score)})</span></div>`
      ).join('') : '<span class="muted">N/A</span>';
    }
  },

  closeDetail() {
    this.$('detailOverlay').classList.remove('open');
  },

  toggleFav(id) {
    SIC_data.toggleFav(id);
  },

  // Bug 9 fix: rewritten markdown renderer
  renderReport(md) {
    if (!md) return '<p class="muted">Report unavailable.</p>';
    // Escape HTML first
    let html = this.esc(md);
    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Code blocks
    html = html.replace(/```[\s\S]*?```/g, m => `<pre><code>${m.slice(3,-3)}</code></pre>`);
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Tables
    const lines = html.split('\n');
    let result = [];
    let inTable = false;
    let tableRows = [];
    for (let line of lines) {
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        const cells = line.split('|').filter(c => c.trim());
        if (cells.every(c => /^[\s-]+$/.test(c))) continue; // separator
        tableRows.push(`<tr>${cells.map(c => `<td>${c.trim()}</td>`).join('')}</tr>`);
        inTable = true;
      } else {
        if (inTable) {
          result.push(`<table>${tableRows.join('')}</table>`);
          tableRows = [];
          inTable = false;
        }
        result.push(line);
      }
    }
    if (inTable) result.push(`<table>${tableRows.join('')}</table>`);
    html = result.join('\n');
    // Unordered lists
    html = html.replace(/^(- .+(?:\n- .+)*)/gm, m => `<ul>${m.split('\n').map(l => `<li>${l.slice(2)}</li>`).join('')}</ul>`);
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    return `<div class="report-content"><p>${html}</p></div>`;
  },

  showSkeleton() {
    this.$('metrics').innerHTML = [1,2,3,4,5].map(() => '<div class="stat skeleton" style="width:100px;height:60px;"></div>').join('');
    this.$('discovery').innerHTML = [1,2,3].map(() => '<div class="discovery-card skeleton" style="height:100px;"></div>').join('');
    this.$('toolOverview').innerHTML = [1,2,3,4].map(() => '<div class="tool-card skeleton" style="height:80px;"></div>').join('');
    this.$('rows').innerHTML = [1,2,3,4,5].map(() => `<tr><td colspan="6"><div class="skeleton" style="height:20px;margin:8px 0;"></div></td></tr>`).join('');
  },

  showError() {
    this.$('rows').innerHTML = `<tr><td colspan="6" class="error-box">
      ${SIC_i18n.t('loadError')}<br>
      <button onclick="location.reload()">${SIC_i18n.t('retry')}</button>
    </td></tr>`;
  },
};
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/render.js
git commit -m "fix: rewrite render.js - discovery zone, virtual scroll, charts call, LLM summary, markdown renderer"
```

---

## 任务 3：重写 app.js（事件委托）

**文件：** `site/js/app.js`

- [ ] **步骤 1：重写 app.js**

重写要点：
1. 所有事件用事件委托绑定在容器上，不用 inline onclick
2. `data-action` 属性判断点击类型（detail / fav / tool-filter / close-detail）
3. 工具卡片点击后同步更新 tag button 的 active 状态（Bug 3 修复）
4. 导出收藏改为输入框（Bug 8 修复）
5. recentOnly checkbox 绑定

```javascript
// site/js/app.js
const $ = id => document.getElementById(id);

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// Render tag buttons
function renderTagButtons() {
  const toolContainer = $('toolTags');
  if (toolContainer) {
    toolContainer.innerHTML = SIC_data.tools
      .filter(t => t.id !== 'general-ai-coding')
      .map(t => {
        const active = SIC_filters.selectedTools.has(t.id) ? ' active' : '';
        const name = SIC_i18n.textOf(t, 'name') || t.name;
        return `<button class="tag-btn${active}" data-action="tool-tag" data-tool="${SIC_render.esc(t.id)}">${SIC_render.esc(name)}</button>`;
      }).join('');
  }
  const typeContainer = $('typeTags');
  if (typeContainer) {
    const allTypes = [...new Set(SIC_data.projects.flatMap(p => p.resource_type || []))].sort();
    typeContainer.innerHTML = allTypes.map(type => {
      const active = SIC_filters.selectedTypes.has(type) ? ' active' : '';
      const label = SIC_i18n.t('resourceTypes')[type] || type;
      return `<button class="tag-btn${active}" data-action="type-tag" data-type="${SIC_render.esc(type)}">${SIC_render.esc(label)}</button>`;
    }).join('');
  }
}

// Sync UI controls from filter state
function syncUI() {
  const qEl = $('q'); if (qEl) qEl.value = SIC_filters.searchQuery;
  const sortEl = $('sort'); if (sortEl) sortEl.value = SIC_filters.sortBy;
  const curEl = $('curatedOnly'); if (curEl) curEl.checked = SIC_filters.curatedOnly;
  const recEl = $('recentOnly'); if (recEl) recEl.checked = SIC_filters.recentOnly;
  const modeBtns = $('modeToggle')?.querySelectorAll('button');
  if (modeBtns) {
    modeBtns[0].classList.toggle('active', SIC_filters.matchMode === 'or');
    modeBtns[1].classList.toggle('active', SIC_filters.matchMode === 'and');
  }
  renderTagButtons();
}

// Event delegation handler
function handleGlobalClick(e) {
  const btn = e.target.closest('[data-action]');
  if (!btn) return;
  const action = btn.dataset.action;
  const id = btn.dataset.id;

  switch (action) {
    case 'detail':
      e.preventDefault();
      SIC_render.openDetail(id);
      break;
    case 'fav':
      SIC_render.toggleFav(id);
      btn.classList.toggle('active');
      break;
    case 'close-detail':
      SIC_render.closeDetail();
      break;
    case 'tool-tag':
      SIC_filters.toggleTool(btn.dataset.tool);
      btn.classList.toggle('active');
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      break;
    case 'type-tag':
      SIC_filters.toggleType(btn.dataset.type);
      btn.classList.toggle('active');
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      break;
    case 'tool-filter':
      // Bug 3 fix: sync tag button active state
      SIC_filters.setTool(btn.dataset.tool);
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      renderTagButtons();
      $('searchZone').scrollIntoView({ behavior: 'smooth' });
      break;
  }
}

function bindEvents() {
  // Global click delegation
  document.addEventListener('click', handleGlobalClick);

  // Search input with debounce
  $('q').addEventListener('input', debounce(e => {
    SIC_filters.searchQuery = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  }, 300));

  // Sort
  $('sort').addEventListener('change', e => {
    SIC_filters.sortBy = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // OR/AND toggle
  $('modeToggle').addEventListener('click', e => {
    if (e.target.tagName !== 'BUTTON') return;
    SIC_filters.toggleMode();
    $('modeToggle').querySelectorAll('button').forEach(b => b.classList.toggle('active'));
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // Checkboxes
  $('curatedOnly').addEventListener('change', e => {
    SIC_filters.curatedOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });
  $('recentOnly').addEventListener('change', e => {
    SIC_filters.recentOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // Language
  $('langZh').addEventListener('click', () => { SIC_i18n.setLang('zh'); SIC_render.renderAll(); syncUI(); });
  $('langEn').addEventListener('click', () => { SIC_i18n.setLang('en'); SIC_render.renderAll(); syncUI(); });

  // Detail overlay close
  $('detailOverlay').addEventListener('click', e => {
    if (e.target.id === 'detailOverlay') SIC_render.closeDetail();
  });

  // ESC
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') SIC_render.closeDetail();
  });

  // Export favorites - Bug 8 fix: input box instead of alert
  $('exportFav')?.addEventListener('click', () => {
    const url = SIC_data.exportFavoritesUrl();
    const input = $('favExportUrl');
    if (input) {
      input.value = url;
      input.style.display = 'block';
      input.select();
      navigator.clipboard?.writeText(url).then(() => {
        input.dataset.copied = '1';
      }).catch(() => {});
    }
  });

  // Report links
  document.querySelectorAll('[data-report]').forEach(el => {
    el.addEventListener('click', async e => {
      e.preventDefault();
      const reportFile = el.dataset.report;
      try {
        const r = await fetch(`reports/${reportFile}`);
        if (!r.ok) {
          $('detailOverlay').innerHTML = `<button class="detail-close" data-action="close-detail">&times;</button><div class="report-content"><p>Report not found: ${SIC_render.esc(reportFile)}</p></div>`;
          $('detailOverlay').classList.add('open');
          return;
        }
        const md = await r.text();
        $('detailOverlay').innerHTML = `<button class="detail-close" data-action="close-detail">&times;</button>${SIC_render.renderReport(md)}`;
        $('detailOverlay').classList.add('open');
      } catch (err) {
        console.error('Report load error:', err);
      }
    });
  });
}

async function main() {
  SIC_render.showSkeleton();
  const ok = await SIC_data.loadAll();
  if (!ok) { SIC_render.showError(); return; }
  SIC_filters.readState();
  SIC_render.renderAll();
  syncUI();
  bindEvents();
}

main();
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/app.js
git commit -m "fix: rewrite app.js with event delegation, tool card sync, favorites input box"
```

---

## 任务 4：更新 index.html 和 styles.css

**文件：** `site/index.html`, `site/styles.css`

- [ ] **步骤 1：更新 index.html**

添加：
1. `recentOnly` checkbox
2. `toolChart` 和 `scoreChart` 容器
3. `favExportUrl` 输入框
4. 表格容器 `overflow-x: auto`

```html
<!-- 在 curatedOnly 旁边加 recentOnly -->
<label><input id="curatedOnly" type="checkbox"> <span data-i18n="curatedOnly">只看推荐</span></label>
<label><input id="recentOnly" type="checkbox"> <span data-i18n="recentOnly">只看最近新增</span></label>
```

```html
<!-- 工具概览区下方加图表容器 -->
<div id="toolChart" class="chart-container"></div>
```

```html
<!-- 搜索区表格上方加分数分布图 -->
<div id="scoreChart" class="chart-container"></div>
```

```html
<!-- 导航栏收藏导出改为输入框 -->
<button id="exportFav" class="fav-btn" data-i18n="exportFav">导出收藏</button>
<input id="favExportUrl" type="text" class="fav-export-input" readonly style="display:none;" placeholder="收藏链接">
```

```html
<!-- 表格用容器包裹 -->
<div class="table-wrapper">
  <table role="table">...</table>
</div>
```

- [ ] **步骤 2：更新 styles.css**

添加：
```css
/* Bug 10 fix: mobile table scroll */
.table-wrapper { overflow-x: auto; }
@media (max-width: 760px) {
  .table-wrapper table { min-width: 600px; }
}

/* Bug 8 fix: favorites export input */
.fav-export-input {
  margin-left: 8px;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  background: var(--color-input);
  color: var(--color-text);
  font-size: 12px;
  max-width: 300px;
}

/* Chart container */
.chart-container { margin-bottom: var(--spacing); overflow-x: auto; }
```

- [ ] **步骤 3：更新 i18n.js 添加 recentOnly 翻译**

在 UI.zh 和 UI.en 中各添加：
```javascript
// zh
recentOnly: '只看最近新增',
// en
recentOnly: 'Recent only',
```

- [ ] **步骤 4：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/index.html site/styles.css site/js/i18n.js
git commit -m "fix: update index.html and styles.css for recentOnly, charts, table scroll, favorites input"
```

---

## 任务 5：重写 generate_reports.py

**文件：** `scripts/generate_reports.py`

- [ ] **步骤 1：删除旧报告**

```bash
cd "/root/workspace/search in coding"
rm -f docs/reports/*.md
```

- [ ] **步骤 2：重写 generate_reports.py**

```python
#!/usr/bin/env python3
"""Generate 3 ecosystem reports using new schema fields.

Reports:
- weekly-report.md: data overview, top 10 projects, score distribution, tracking status
- tool-comparison.md: 10 tools ecosystem size, resource type distribution, avg score
- curated-top.md: top 50 projects table + top 3 by category
"""
import argparse, json, collections, datetime
from common import ROOT, load_jsonish

def main():
    ap = argparse.ArgumentParser(description='Generate ecosystem reports')
    ap.parse_args()
    now = datetime.date.today().isoformat()
    reports = ROOT / 'docs' / 'reports'
    reports.mkdir(parents=True, exist_ok=True)

    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')

    eco = [p for p in projects if p.get('source_type') != 'official-seed' and p.get('tracking_priority') != 'reject']
    eco_sorted = sorted(eco, key=lambda p: p.get('total_score', 0), reverse=True)

    # === 1. Weekly Report ===
    score_buckets = collections.Counter()
    for p in eco:
        s = p.get('total_score', 0)
        if s <= 20: score_buckets['0-20'] += 1
        elif s <= 40: score_buckets['21-40'] += 1
        elif s <= 60: score_buckets['41-60'] += 1
        elif s <= 80: score_buckets['61-80'] += 1
        else: score_buckets['81-100'] += 1

    tracking = collections.Counter(p.get('tracking_priority', 'pending') for p in projects)

    weekly = f"""# 生态周报 - {now}

## 数据概况

- 总记录数: {len(projects)}
- 生态项目: {len(eco)}
- 推荐项目: {len(curated)}
- 官方工具: {sum(1 for p in projects if p.get('source_type') == 'official-seed')}

## Top 10 项目

| # | 名称 | 类型 | 工具 | 分数 | Stars | URL |
|---|------|------|------|------|-------|-----|
"""
    for i, p in enumerate(eco_sorted[:10]):
        name = p.get('name', '').replace('|', '/')
        rtype = ', '.join(p.get('resource_type', []))
        tools_str = ', '.join(p.get('target_tools', []))
        score = p.get('total_score', 0)
        stars = p.get('stars', 0)
        url = p.get('url', '')
        weekly += f"| {i+1} | {name} | {rtype} | {tools_str} | {score} | {stars} | {url} |\n"

    weekly += f"""
## 分数分布

| 分数段 | 项目数 |
|--------|--------|
| 0-20 | {score_buckets.get('0-20', 0)} |
| 21-40 | {score_buckets.get('21-40', 0)} |
| 41-60 | {score_buckets.get('41-60', 0)} |
| 61-80 | {score_buckets.get('61-80', 0)} |
| 81-100 | {score_buckets.get('81-100', 0)} |

## 追踪状态

- 追踪中 (track): {tracking.get('track', 0)}
- 索引中 (index): {tracking.get('index', 0)}
- 待分析 (pending): {tracking.get('pending', 0)}
- 已拒绝 (reject): {tracking.get('reject', 0)}
"""
    (reports / 'weekly-report.md').write_text(weekly, encoding='utf-8')

    # === 2. Tool Comparison ===
    comparison = f"""# 工具生态对比 - {now}

## 生态规模

| 工具 | 项目数 | 推荐数 | 平均分 | Top 项目 |
|------|--------|--------|--------|---------|
"""
    for t in tools:
        tid = t['id']
        if tid == 'general-ai-coding': continue
        t_projects = [p for p in eco if tid in (p.get('target_tools') or [])]
        t_curated = [p for p in curated if tid in (p.get('target_tools') or [])]
        avg = round(sum(p.get('total_score', 0) for p in t_projects) / max(len(t_projects), 1), 1)
        top_name = t_projects[0]['name'] if t_projects else 'N/A'
        comparison += f"| {t.get('name', tid)} | {len(t_projects)} | {len(t_curated)} | {avg} | {top_name} |\n"

    # Resource type distribution by tool
    comparison += "\n## 资源类型分布\n\n| 工具 | MCP | Skills | Rules | Framework | CLI | Tutorial |\n|------|-----|--------|-------|-----------|-----|----------|\n"
    for t in tools:
        tid = t['id']
        if tid == 'general-ai-coding': continue
        t_projects = [p for p in eco if tid in (p.get('target_tools') or [])]
        type_counts = collections.Counter()
        for p in t_projects:
            for rt in (p.get('resource_type') or []):
                type_counts[rt] += 1
        comparison += f"| {t.get('name', tid)} | {type_counts.get('mcp-server', 0)} | {type_counts.get('skills', 0)} | {type_counts.get('rules', 0)} | {type_counts.get('agent-framework', 0)} | {type_counts.get('cli-tool', 0)} | {type_counts.get('tutorial', 0)} |\n"

    (reports / 'tool-comparison.md').write_text(comparison, encoding='utf-8')

    # === 3. Curated Top ===
    curated_sorted = sorted(curated, key=lambda p: p.get('total_score', 0), reverse=True)
    top_md = f"""# 推荐榜 - {now}

## Top 50 项目

| # | 名称 | 类型 | 工具 | 分数 | Stars | URL |
|---|------|------|------|------|-------|-----|
"""
    for i, p in enumerate(curated_sorted[:50]):
        name = p.get('name', '').replace('|', '/')
        rtype = ', '.join(p.get('resource_type', []))
        tools_str = ', '.join(p.get('target_tools', []))
        score = p.get('total_score', 0)
        stars = p.get('stars', 0)
        url = p.get('url', '')
        top_md += f"| {i+1} | {name} | {rtype} | {tools_str} | {score} | {stars} | {url} |\n"

    # Top 3 by resource type
    top_md += "\n## 按分类 Top 3\n\n"
    for rt in ['mcp-server', 'skills', 'rules', 'agent-framework', 'cli-tool', 'tutorial']:
        rt_projects = [p for p in eco_sorted if rt in (p.get('resource_type') or [])][:3]
        if rt_projects:
            top_md += f"\n### {rt}\n\n"
            for p in rt_projects:
                top_md += f"- [{p.get('name')}]({p.get('url')}) - {p.get('total_score', 0)} 分, {p.get('stars', 0)} stars\n"

    (reports / 'curated-top.md').write_text(top_md, encoding='utf-8')

    print(json.dumps({'reports': 3, 'projects': len(projects), 'curated': len(curated), 'tools': len(tools)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
```

- [ ] **步骤 3：运行 generate_reports.py**

运行：`cd "/root/workspace/search in coding" && python3 scripts/generate_reports.py`
预期：生成 3 份报告

- [ ] **步骤 4：验证报告文件**

运行：`ls -la docs/reports/`
预期：只有 weekly-report.md, tool-comparison.md, curated-top.md 三个文件

- [ ] **步骤 5：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/generate_reports.py docs/reports/
git commit -m "fix: rewrite generate_reports.py for 3 new reports with new schema fields"
```

---

## 任务 6：重建站点、部署、验证

- [ ] **步骤 1：运行完整 pipeline**

运行：`cd "/root/workspace/search in coding" && python3 scripts/update_tracker.py --skip-collect`
预期：全流程 PASS

- [ ] **步骤 2：验证站点数据**

运行：
```bash
cd "/root/workspace/search in coding"
echo "=== Reports ===" && ls site/reports/
echo "=== JS files ===" && ls site/js/*.js
echo "=== Data ===" && ls site/data/
```

- [ ] **步骤 3：部署站点**

运行：`cd "/root/workspace/search in coding" && python3 scripts/deploy_site.py`

- [ ] **步骤 4：浏览器验证清单**

访问 https://coding.lzpgood.online/，逐项验证：

- [ ] 骨架屏显示后数据正常加载
- [ ] "最新发现"区有 12 个项目卡片（不是空的）
- [ ] 工具概览区有 10 个工具卡片 + 柱状图
- [ ] 分数分布直方图显示在搜索区上方
- [ ] 点击工具卡片 -> tag button 高亮 + 搜索区筛选 + 滚动
- [ ] 点击 tag button -> 切换选中 + 表格更新
- [ ] OR/AND 切换 -> 表格重新筛选
- [ ] 6 种排序切换正常
- [ ] "只看推荐" checkbox 正常
- [ ] "只看最近新增" checkbox 正常
- [ ] 搜索框输入 -> debounce 后筛选
- [ ] 滚动到底部 -> 加载更多行（虚拟滚动）
- [ ] 点击"详情" -> 侧边面板打开，显示评分明细
- [ ] 详情面板中 LLM Summary（如果有）正确显示
- [ ] 详情面板中关联项目可点击跳转
- [ ] 收藏按钮点击 -> 星标切换
- [ ] 导出收藏 -> 输入框显示 URL（不是 alert）
- [ ] 点击"生态周报" -> 面板内渲染 markdown 报告
- [ ] 点击"工具对比" -> 面板内渲染 markdown 报告
- [ ] 点击"推荐榜" -> 面板内渲染 markdown 报告
- [ ] 中英文切换 -> 全部 UI 文本切换
- [ ] ESC 键 -> 关闭详情面板
- [ ] 移动端（375px）-> 表格可横向滚动
- [ ] 无 JS 控制台错误

- [ ] **步骤 5：Commit 并 tag**

```bash
cd "/root/workspace/search in coding"
git add -A
git commit -m "fix: frontend rewrite v2 - all 10 bugs fixed, event delegation, reports rewritten"
git tag v2025.07.13-frontend-v2
```

- [ ] **步骤 6：更新 Wiki**

更新：
- `wiki/L4A-前端详解.md` - 更新事件委托机制、最新发现逻辑、虚拟滚动修复
- `wiki/L6-经验录.md` - 记录第 2 批的 10 个 bug 和教训

---

## 验收标准

- [ ] "最新发现"区有 12 个项目卡片
- [ ] 3 份报告链接点击后在面板内正常渲染
- [ ] 工具卡片点击后 tag button 同步高亮
- [ ] 虚拟滚动可连续加载多页
- [ ] "只看最近新增" checkbox 功能正常
- [ ] 工具覆盖柱状图和分数分布直方图显示
- [ ] 详情面板 LLM Summary 正确显示（如有）
- [ ] 导出收藏显示输入框（不是 alert）
- [ ] 报告 markdown 渲染支持表格/列表/标题
- [ ] 移动端表格可横向滚动
- [ ] 无 inline onclick（全部事件委托）
- [ ] 无 JS 控制台错误
- [ ] pipeline --skip-collect PASS
