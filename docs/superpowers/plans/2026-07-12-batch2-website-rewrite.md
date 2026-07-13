# 第 2 批：网站重写 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 27 行压缩 JS 重写为模块化零依赖前端，实现三区布局（发现/理解/搜索）、多选标签筛选、项目详情面板、站内报告渲染、收藏功能，以及完整的前端性能优化（精简 JSON、虚拟滚动、SEO、骨架屏、Nginx 缓存）。

**架构：** `site/app.js` 拆分为 `site/js/` 下 6 个模块文件（多 `<script>` 标签加载）；`styles.css` 引入 CSS 自定义属性重写；`build_site.py` 生成精简 JSON + 详情 JSON + 预渲染 HTML + sitemap.xml + 带 hash 的 JS/CSS 文件名；前端实现骨架屏、渐进式渲染、虚拟滚动、多选标签按钮组、OR/AND 切换、6 种排序、详情面板、收藏功能。

**技术栈：** 纯 HTML + CSS + 原生 JS（零依赖），Python 3.12+（build_site.py），Nginx（缓存配置）

**关联文档：**
- 设计规格：`docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md`（"网站设计"和"前端性能优化"章节）
- ADR-0006：零依赖模块化 + 三区布局
- ADR-0008：前端性能优化策略
- 领域术语：`CONTEXT.md`

**前置条件：** 第 1 批已完成（数据结构已迁移到 resource_type/total_score 0-100/tracking_priority）

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `site/js/i18n.js` | 双语配置对象 UI、t() 函数、textOf() 函数、语言切换 |
| `site/js/data.js` | 数据加载（渐进式 fetch）、全局状态管理、localStorage 收藏 |
| `site/js/filters.js` | 多选标签按钮组、OR/AND 切换、6 种排序、筛选状态读写 URL |
| `site/js/render.js` | 三区渲染（精选区、工具概览区、筛选表格）、虚拟滚动、详情面板 |
| `site/js/charts.js` | 原生 SVG 图表（分类饼图、工具柱状图、评分直方图） |
| `site/js/app.js` | 入口、事件绑定、骨架屏、错误处理、debounce |
| `site/styles.css` | 重写，CSS 自定义属性、三区布局、响应式、骨架屏、详情面板样式 |
| `site/index.html` | 重写，语义 HTML、三区结构、预渲染首屏内容、JSON-LD |
| `site/sitemap.xml` | 站点地图（build_site.py 生成） |
| `tests/test_build_site_v2.py` | build_site.py 新功能测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `scripts/build_site.py` | 精简 JSON + 详情 JSON + 预渲染 HTML + sitemap + hash 文件名 |

### 废弃文件

| 文件 | 处理 |
|------|------|
| `site/app.js`（旧 27 行版本）| 替换为 `site/js/app.js`（新模块化版本）|

---

## 任务 1：CSS 自定义属性和基础样式重写

**文件：**
- 创建：`site/styles.css`（完全重写）

- [ ] **步骤 1：编写新的 styles.css**

```css
/* === CSS Custom Properties === */
:root {
  --color-bg: #0f172a;
  --color-surface: #111827;
  --color-card: #1e293b;
  --color-input: #020617;
  --color-text: #e2e8f0;
  --color-text-secondary: #cbd5e1;
  --color-text-muted: #94a3b8;
  --color-link: #93c5fd;
  --color-border: #334155;
  --color-border-light: #475569;
  --color-accent: #2563eb;
  --color-accent-light: #60a5fa;
  --color-success: #14532d;
  --color-warning: #713f12;
  --color-danger: #4c1d95;
  --radius: 12px;
  --radius-sm: 8px;
  --spacing: 24px;
  --spacing-sm: 12px;
  --spacing-xs: 8px;
}

/* === Reset & Base === */
* { box-sizing: border-box; }
body {
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  margin: 0;
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
}
a { color: var(--color-link); }

/* === Header === */
header {
  padding: 32px var(--spacing);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}
.topbar {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing);
  align-items: flex-start;
  flex-wrap: wrap;
}
h1 { margin: 0 0 8px; font-size: 34px; }
header p { margin: 0; color: var(--color-text-secondary); }
nav { margin-top: 18px; }
nav a { margin-right: 16px; color: var(--color-link); }
.lang-switch { display: flex; gap: var(--spacing-xs); }
.lang-switch button {
  cursor: pointer;
  border: 1px solid var(--color-border-light);
  background: var(--color-input);
  color: var(--color-text);
  border-radius: 999px;
  padding: 8px 14px;
}
.lang-switch button.active {
  background: var(--color-accent);
  border-color: var(--color-accent-light);
  color: white;
}

/* === Main Layout === */
main { padding: var(--spacing); max-width: 1400px; margin: 0 auto; }

/* === Skeleton Screen === */
.skeleton {
  background: linear-gradient(90deg, var(--color-card) 25%, var(--color-surface) 50%, var(--color-card) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
.skeleton-row { height: 20px; margin-bottom: var(--spacing-xs); }

/* === Metrics Cards === */
.metrics { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); margin-bottom: var(--spacing); }
.stat {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 14px;
  min-width: 120px;
}
.stat b { font-size: 28px; }

/* === Section Headings === */
section { margin-bottom: var(--spacing); }
section h2 { font-size: 22px; margin-bottom: var(--spacing-sm); }

/* === Discovery Zone (首页精选区) === */
.discovery-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-sm);
}
.discovery-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.discovery-card:hover { border-color: var(--color-accent-light); }
.discovery-card .score-badge {
  display: inline-block;
  background: var(--color-accent);
  color: white;
  border-radius: var(--radius-sm);
  padding: 2px 8px;
  font-size: 13px;
  font-weight: bold;
}

/* === Tool Overview Zone (工具概览区) === */
.tool-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: var(--spacing-sm);
}
.tool-card {
  background: var(--color-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.tool-card:hover { border-color: var(--color-accent-light); }
.tool-card h3 { margin: 0 0 8px; font-size: 16px; }
.tool-stats { font-size: 13px; color: var(--color-text-muted); }

/* === Search Zone (筛选表格区) === */
.controls {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}
input, select {
  padding: 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  background: var(--color-input);
  color: var(--color-text);
}
input:focus, select:focus { outline: 2px solid var(--color-accent); }

/* Tag button group */
.tag-group { display: flex; flex-wrap: wrap; gap: 6px; }
.tag-btn {
  cursor: pointer;
  border: 1px solid var(--color-border-light);
  background: var(--color-input);
  color: var(--color-text-secondary);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  transition: all 0.15s;
}
.tag-btn.active {
  background: var(--color-accent);
  border-color: var(--color-accent-light);
  color: white;
}
.tag-btn:hover { border-color: var(--color-accent-light); }

/* AND/OR toggle */
.mode-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border-light);
  border-radius: 999px;
  overflow: hidden;
}
.mode-toggle button {
  border: none;
  padding: 4px 12px;
  cursor: pointer;
  background: var(--color-input);
  color: var(--color-text-muted);
  font-size: 13px;
}
.mode-toggle button.active {
  background: var(--color-accent);
  color: white;
}

/* === Table === */
table { width: 100%; border-collapse: collapse; background: var(--color-surface); }
th, td {
  padding: 10px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
  vertical-align: top;
}
th { font-size: 13px; color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

/* === Pills === */
.pill {
  display: inline-block;
  background: var(--color-border);
  border-radius: 999px;
  padding: 2px 8px;
  margin: 2px;
  font-size: 12px;
}

/* === Detail Panel === */
.detail-overlay {
  display: none;
  position: fixed;
  top: 0; right: 0; bottom: 0;
  width: min(500px, 100%);
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  box-shadow: -4px 0 24px rgba(0,0,0,0.3);
  z-index: 100;
  overflow-y: auto;
  padding: var(--spacing);
}
.detail-overlay.open { display: block; }
.detail-overlay h2 { margin-top: 0; }
.detail-close {
  position: absolute;
  top: 16px; right: 16px;
  cursor: pointer;
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 24px;
}
.detail-section { margin-bottom: var(--spacing); }
.detail-section h3 { font-size: 14px; color: var(--color-text-muted); margin-bottom: 6px; }
.score-bar {
  height: 8px;
  background: var(--color-card);
  border-radius: 4px;
  overflow: hidden;
}
.score-bar-fill { height: 100%; background: var(--color-accent); border-radius: 4px; }

/* === Favorites === */
.fav-btn {
  cursor: pointer;
  background: none;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  font-size: 13px;
  color: var(--color-text-muted);
}
.fav-btn.active { color: #fbbf24; border-color: #fbbf24; }

/* === Error & Empty States === */
.error-box, .empty-box {
  text-align: center;
  padding: 48px;
  color: var(--color-text-muted);
}
.error-box button, .empty-box button {
  margin-top: 12px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-light);
  background: var(--color-card);
  color: var(--color-text);
  cursor: pointer;
}
.error-box button:hover { border-color: var(--color-accent); }

/* === Report Rendering === */
.report-content { line-height: 1.8; }
.report-content h1 { font-size: 24px; }
.report-content h2 { font-size: 20px; }
.report-content table { margin: 12px 0; }
.report-content code { background: var(--color-card); padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }

/* === Responsive === */
@media (max-width: 760px) {
  main { padding: 14px; }
  table { font-size: 13px; }
  .topbar { display: block; }
  .lang-switch { margin-top: 16px; }
  .detail-overlay { width: 100%; }
  .discovery-grid, .tool-grid { grid-template-columns: 1fr; }
}
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/styles.css
git commit -m "feat: rewrite styles.css with CSS custom properties, three-zone layout, detail panel, skeleton"
```

---

## 任务 2：i18n.js 模块

**文件：**
- 创建：`site/js/i18n.js`

- [ ] **步骤 1：编写 i18n.js**

```javascript
// site/js/i18n.js
// Bilingual configuration and language switching
const SIC_i18n = {
  lang: localStorage.getItem('sic_lang') || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en'),

  UI: {
    zh: {
      subtitle: 'AI Coding Agent 生态追踪器：终端 Agent、AI IDE、MCP、Skills、Rules、Context Engineering',
      navWeekly: '生态周报', navCompare: '工具对比', navTop: '推荐榜',
      discoveryTitle: '本周新发现', discoveryHint: '最近 7 天新增的高质量项目',
      toolOverviewTitle: '工具生态概览', toolOverviewHint: '点击工具卡片查看该工具的生态资源',
      searchTitle: '生态项目搜索', searchHint: '多选标签筛选，支持 OR/AND 切换',
      searchPlaceholder: '搜索项目名称或描述...',
      allTools: '全部工具', allTypes: '全部类型', allSources: '全部来源',
      sortScore: '分数', sortStars: 'Stars', sortUpdated: '最近更新', sortMatch: '标签匹配', sortRecent: '最近发现', sortName: '名称',
      modeOR: '任一匹配', modeAND: '全部匹配',
      details: '详情', copy: '复制链接', copied: '已复制', open: '打开',
      favorite: '收藏', favorited: '已收藏', exportFav: '导出收藏',
      curated: '推荐', tracking: '追踪中', indexed: '索引中',
      thName: '名称', thType: '类型', thTools: '工具', thScore: '分数', thStars: 'Stars', thLink: '链接',
      loading: '加载中...', loadError: '数据加载失败', retry: '重试',
      noResults: '没有符合条件的项目', adjustFilter: '试试调整筛选条件',
      scoreDetail: '评分明细', quantifiable: '可量化分', quality: '质量分',
      benchmarkRef: '参照项目', relatedProjects: '关联项目', readme: 'README 预览',
      metrics: { projects: '总记录', curated: '推荐', rejected: '噪声', official_tools: '官方工具', ecosystem_projects: '生态项目' },
      resourceTypes: { 'mcp-server': 'MCP Server', 'skills': 'Skills', 'rules': 'Rules', 'agent-framework': 'Agent 框架', 'cli-tool': 'CLI 工具', 'tutorial': '教程' },
    },
    en: {
      subtitle: 'AI Coding Agent ecosystem tracker: terminal agents, AI IDEs, MCP, skills, rules, and context engineering',
      navWeekly: 'Weekly Report', navCompare: 'Tool Comparison', navTop: 'Top Picks',
      discoveryTitle: 'New This Week', discoveryHint: 'High-quality projects added in the last 7 days',
      toolOverviewTitle: 'Tool Ecosystem Overview', toolOverviewHint: 'Click a tool card to browse its ecosystem resources',
      searchTitle: 'Ecosystem Search', searchHint: 'Multi-select tag filtering with OR/AND toggle',
      searchPlaceholder: 'Search project name or description...',
      allTools: 'All tools', allTypes: 'All types', allSources: 'All sources',
      sortScore: 'Score', sortStars: 'Stars', sortUpdated: 'Recently Updated', sortMatch: 'Tag Match', sortRecent: 'Recently Discovered', sortName: 'Name',
      modeOR: 'Any match', modeAND: 'All match',
      details: 'Details', copy: 'Copy link', copied: 'Copied', open: 'Open',
      favorite: 'Favorite', favorited: 'Favorited', exportFav: 'Export Favorites',
      curated: 'Curated', tracking: 'Tracking', indexed: 'Indexed',
      thName: 'Name', thType: 'Type', thTools: 'Tools', thScore: 'Score', thStars: 'Stars', thLink: 'Link',
      loading: 'Loading...', loadError: 'Failed to load data', retry: 'Retry',
      noResults: 'No projects match your filters', adjustFilter: 'Try adjusting your filters',
      scoreDetail: 'Score Details', quantifiable: 'Quantifiable', quality: 'Quality',
      benchmarkRef: 'Benchmark Reference', relatedProjects: 'Related Projects', readme: 'README Preview',
      metrics: { projects: 'Records', curated: 'Curated', rejected: 'Rejected', official_tools: 'Official', ecosystem_projects: 'Ecosystem' },
      resourceTypes: { 'mcp-server': 'MCP Server', 'skills': 'Skills', 'rules': 'Rules', 'agent-framework': 'Agent Framework', 'cli-tool': 'CLI Tool', 'tutorial': 'Tutorial' },
    }
  },

  t(key) {
    return (this.UI[this.lang] && this.UI[this.lang][key]) || this.UI.zh[key] || key;
  },

  textOf(item, field) {
    return item?.i18n?.[this.lang]?.[field] || item?.i18n?.zh?.[field] || item?.i18n?.en?.[field] || item?.[field] || '';
  },

  setLang(l) {
    this.lang = l;
    localStorage.setItem('sic_lang', l);
  },

  applyLanguage() {
    document.documentElement.lang = this.lang === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = this.t(el.dataset.i18n); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = this.t(el.dataset.i18nPlaceholder); });
    document.getElementById('langZh')?.classList.toggle('active', this.lang === 'zh');
    document.getElementById('langEn')?.classList.toggle('active', this.lang === 'en');
  }
};
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/i18n.js
git commit -m "feat: add i18n.js module with bilingual config and language switching"
```

---

## 任务 3：data.js 模块（数据加载 + 收藏）

**文件：**
- 创建：`site/js/data.js`

- [ ] **步骤 1：编写 data.js**

```javascript
// site/js/data.js
// Data loading (progressive fetch), state management, favorites
const SIC_data = {
  projects: [], curated: [], tools: [], metrics: {},
  projectDetails: {}, // lazy-loaded detail data by project id
  favorites: new Set(JSON.parse(localStorage.getItem('sic_favorites') || '[]')),
  loadError: false,

  async loadAll(onProgress) {
    this.loadError = false;
    try {
      // Progressive: metrics first (1KB), then projects, then curated/tools
      this.metrics = await this.fetchJSON('data/metrics.json', onProgress, 'metrics');
      this.tools = await this.fetchJSON('data/tools.json', onProgress, 'tools');
      this.projects = await this.fetchJSON('data/projects.json', onProgress, 'projects');
      this.curated = await this.fetchJSON('data/curated-projects.json', onProgress, 'curated');
    } catch (e) {
      console.error('Data load error:', e);
      this.loadError = true;
    }
    return !this.loadError;
  },

  async fetchJSON(url, onProgress, label) {
    if (onProgress) onProgress(label);
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
    return r.json();
  },

  async loadDetail(projectId) {
    if (this.projectDetails[projectId]) return this.projectDetails[projectId];
    try {
      // Detail data is in a separate file, loaded on demand
      const r = await fetch(`data/projects-detail.json`);
      if (!r.ok) return null;
      const all = await r.json();
      // Cache all details at once (file is small enough)
      for (const d of all) {
        this.projectDetails[d.id] = d;
      }
      return this.projectDetails[projectId];
    } catch (e) {
      console.error('Detail load error:', e);
      return null;
    }
  },

  // Favorites
  isFav(id) { return this.favorites.has(id); },
  toggleFav(id) {
    if (this.favorites.has(id)) this.favorites.delete(id);
    else this.favorites.add(id);
    localStorage.setItem('sic_favorites', JSON.stringify([...this.favorites]));
  },
  getFavorites() {
    return this.projects.filter(p => this.favorites.has(p.id));
  },
  exportFavoritesUrl() {
    const ids = [...this.favorites];
    return `${location.origin}${location.pathname}#favorites=${ids.join(',')}`;
  },

  // Curated IDs set
  curatedIds() { return new Set(this.curated.map(p => p.id)); },
};
```

- [ ] **步骤 2：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/data.js
git commit -m "feat: add data.js module with progressive fetch, detail lazy-load, favorites"
```

---

## 任务 4：filters.js 模块（多选筛选 + 排序 + URL 状态）

**文件：**
- 创建：`site/js/filters.js`

- [ ] **步骤 1：编写 filters.js**

```javascript
// site/js/filters.js
// Multi-select tag button filters, OR/AND toggle, 6 sort modes, URL state
const SIC_filters = {
  selectedTools: new Set(),   // selected tool IDs
  selectedTypes: new Set(),   // selected resource_type values
  searchQuery: '',
  sortBy: 'score',
  matchMode: 'or',            // 'or' or 'and'
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

  apply(projects, curatedIds) {
    let rows = projects.filter(p => {
      // Exclude rejected and official-seed from search results
      if (p.source_type === 'official-seed') return false;
      if (p.tracking_priority === 'reject') return false;

      // Search query
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase();
        const text = JSON.stringify(p).toLowerCase();
        if (!text.includes(q)) return false;
      }

      // Tool filter
      if (this.selectedTools.size > 0) {
        const pTools = p.target_tools || [];
        if (this.matchMode === 'and') {
          if (![...this.selectedTools].every(t => pTools.includes(t))) return false;
        } else {
          if (![...this.selectedTools].some(t => pTools.includes(t))) return false;
        }
      }

      // Resource type filter
      if (this.selectedTypes.size > 0) {
        const pTypes = p.resource_type || [];
        if (this.matchMode === 'and') {
          if (![...this.selectedTypes].every(t => pTypes.includes(t))) return false;
        } else {
          if (![...this.selectedTypes].some(t => pTypes.includes(t))) return false;
        }
      }

      // Curated only
      if (this.curatedOnly && !curatedIds.has(p.id)) return false;

      // Recent only (last 50)
      if (this.recentOnly) {
        // handled by caller via cutoff date
      }

      return true;
    });

    // Sort
    rows.sort((a, b) => {
      switch (this.sortBy) {
        case 'name': return SIC_i18n.textOf(a, 'name').localeCompare(SIC_i18n.textOf(b, 'name'));
        case 'stars': return (b.stars || 0) - (a.stars || 0);
        case 'updated': return String(b.last_updated || '').localeCompare(String(a.last_updated || ''));
        case 'recent': return String(b.first_seen || b.last_seen || '').localeCompare(String(a.first_seen || a.last_seen || ''));
        case 'match': {
          // Tag match count descending, then score
          const aMatch = this._matchCount(a);
          const bMatch = this._matchCount(b);
          if (bMatch !== aMatch) return bMatch - aMatch;
          return (b.total_score || 0) - (a.total_score || 0);
        }
        default: return (b.total_score || 0) - (a.total_score || 0); // 'score'
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

  // URL state
  readState() {
    const qs = new URLSearchParams(location.search);
    if (qs.get('q')) this.searchQuery = qs.get('q');
    if (qs.get('tools')) qs.get('tools').split(',').forEach(t => this.selectedTools.add(t));
    if (qs.get('types')) qs.get('types').split(',').forEach(t => this.selectedTypes.add(t));
    if (qs.get('sort')) this.sortBy = qs.get('sort');
    if (qs.get('mode')) this.matchMode = qs.get('mode');
    if (qs.get('curated') === '1') this.curatedOnly = true;
    if (qs.get('recent') === '1') this.recentOnly = true;
    // Favorites from hash
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
git commit -m "feat: add filters.js with multi-select tag buttons, OR/AND toggle, 6 sort modes, URL state"
```

---

## 任务 5：render.js 模块（三区渲染 + 虚拟滚动 + 详情面板）

**文件：**
- 创建：`site/js/render.js`

- [ ] **步骤 1：编写 render.js**

```javascript
// site/js/render.js
// Three-zone rendering: discovery, tool overview, search table
// Virtual scroll for table, detail panel, report rendering
const SIC_render = {
  PAGE_SIZE: 50,
  currentPage: 0,
  renderedCount: 0,
  currentFiltered: [],

  $: id => document.getElementById(id),
  esc: s => String(s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  safeUrl: raw => { try { const u = new URL(String(raw||''), location.href); if (['http:','https:'].includes(u.protocol)) return u.href; } catch(_){} return '#'; },
  pills: xs => (xs||[]).map(x => `<span class="pill">${SIC_render.esc(x)}</span>`).join(''),
  safeNum: v => { const n = Number(v); return Number.isFinite(n) ? String(n) : '0'; },

  renderAll() {
    SIC_i18n.applyLanguage();
    this.renderMetrics();
    this.renderDiscovery();
    this.renderToolOverview();
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

  renderDiscovery() {
    // Show projects added in last 7 days, sorted by score, top 12
    const now = new Date();
    const cutoff = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const recent = SIC_data.projects
      .filter(p => (p.first_seen || p.last_seen || '') >= cutoff && p.tracking_priority !== 'reject')
      .sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
      .slice(0, 12);

    if (recent.length === 0) {
      this.$('discovery').innerHTML = `<p class="hint">${SIC_i18n.t('discoveryHint')}</p>`;
      return;
    }

    this.$('discovery').innerHTML = recent.map(p => `
      <div class="discovery-card" onclick="SIC_render.openDetail('${this.esc(p.id)}')">
        <span class="score-badge">${this.safeNum(p.total_score)}</span>
        <b>${this.esc(SIC_i18n.textOf(p, 'name'))}</b><br>
        <span class="muted">${this.esc((SIC_i18n.textOf(p, 'summary') || '').slice(0, 80))}</span><br>
        ${this.pills(p.resource_type)}
      </div>
    `).join('');
  },

  renderToolOverview() {
    const tools = SIC_data.tools.filter(t => t.id !== 'general-ai-coding');
    this.$('toolOverview').innerHTML = tools.map(t => {
      const count = SIC_data.projects.filter(p =>
        (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject'
      ).length;
      const curated = SIC_data.curated.filter(p => (p.target_tools || []).includes(t.id)).length;
      return `
        <div class="tool-card" onclick="SIC_filters.selectedTools.clear(); SIC_filters.selectedTools.add('${this.esc(t.id)}'); SIC_render.renderSearchZone(); document.getElementById('searchZone').scrollIntoView();">
          <h3>${this.esc(SIC_i18n.textOf(t, 'name') || t.name)}</h3>
          <div class="tool-stats">${count} ${SIC_i18n.lang === 'zh' ? '个项目' : ' projects'} · ${curated} ${SIC_i18n.lang === 'zh' ? '推荐' : ' curated'}</div>
        </div>
      `;
    }).join('');
  },

  renderSearchZone() {
    const curatedIds = SIC_data.curatedIds();
    this.currentFiltered = SIC_filters.apply(SIC_data.projects, curatedIds);
    this.currentPage = 0;
    this.renderedCount = 0;
    this.$('rows').innerHTML = '';

    if (this.currentFiltered.length === 0) {
      this.$('rows').innerHTML = `<tr><td colspan="6" class="empty-box">${SIC_i18n.t('noResults')}<br><span class="muted">${SIC_i18n.t('adjustFilter')}</span></td></tr>`;
      return;
    }

    this.renderMore();
  },

  renderMore() {
    const start = this.renderedCount;
    const end = Math.min(start + this.PAGE_SIZE, this.currentFiltered.length);
    const curatedIds = SIC_data.curatedIds();
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
          <button class="fav-btn ${isFav ? 'active' : ''}" onclick="SIC_render.toggleFav('${this.esc(p.id)}', this)">★</button>
          ${isCurated ? `<span class="pill">${SIC_i18n.t('curated')}</span>` : ''}
          <button onclick="SIC_render.openDetail('${this.esc(p.id)}')">${SIC_i18n.t('details')}</button>
        </td>
      </tr>`;
    }).join('');
    this.$('rows').insertAdjacentHTML('beforeend', html);
    this.renderedCount = end;

    // Show "load more" or use IntersectionObserver
    if (this.renderedCount < this.currentFiltered.length) {
      if (!this._observer) {
        this._observer = new IntersectionObserver(entries => {
          if (entries[0].isIntersecting && this.renderedCount < this.currentFiltered.length) {
            this.renderMore();
          }
        });
      }
      // Observe the last row
      const lastRow = this.$('rows').lastElementChild;
      if (lastRow) this._observer.observe(lastRow);
    }
  },

  // Detail panel
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

    overlay.innerHTML = `
      <button class="detail-close" onclick="SIC_render.closeDetail()">&times;</button>
      <h2>${this.esc(SIC_i18n.textOf(p, 'name'))}</h2>
      <p class="muted">${this.esc(SIC_i18n.textOf(p, 'summary') || '')}</p>

      <div class="detail-section">
        <h3>${SIC_i18n.t('scoreDetail')}</h3>
        <div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">
          <span class="score-badge" style="font-size:20px;padding:4px 12px;background:var(--color-accent);color:white;border-radius:8px;">${this.safeNum(total)}</span>
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

      ${detail?.llm_summary ? `<div class="detail-section"><h3>LLM Summary</h3><p>${this.esc(SIC_i18n.textOf(detail, 'llm_summary') || '')}</p></div>` : ''}

      ${detail?.benchmark_ref ? `<div class="detail-section"><h3>${SIC_i18n.t('benchmarkRef')}</h3><p class="muted">${this.esc(detail.benchmark_ref)}</p></div>` : ''}

      <div class="detail-section">
        <h3>${SIC_i18n.t('relatedProjects')}</h3>
        <div id="relatedProjects">...</div>
      </div>

      <div class="detail-section">
        <a href="${this.safeUrl(p.url)}" target="_blank" rel="noopener noreferrer">${SIC_i18n.t('open')} →</a>
        <button class="fav-btn ${isFav ? 'active' : ''}" onclick="SIC_render.toggleFav('${this.esc(p.id)}', this)">${isFav ? SIC_i18n.t('favorited') : SIC_i18n.t('favorite')}</button>
      </div>
    `;
    overlay.classList.add('open');

    // Load related projects (same resource_type or shared tools)
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
        `<div style="margin-bottom:6px;"><a href="javascript:void(0)" onclick="SIC_render.openDetail('${this.esc(r.id)}')">${this.esc(SIC_i18n.textOf(r, 'name'))}</a> <span class="muted">(${this.safeNum(r.total_score)})</span></div>`
      ).join('') : '<span class="muted">N/A</span>';
    }
  },

  closeDetail() {
    this.$('detailOverlay').classList.remove('open');
  },

  toggleFav(id, btn) {
    SIC_data.toggleFav(id);
    if (btn) btn.classList.toggle('active');
  },

  // Report rendering (simple markdown to HTML)
  renderReport(md) {
    let html = this.esc(md);
    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Tables
    html = html.replace(/^\|(.+)\|$/gm, (match) => {
      const cells = match.split('|').filter(c => c.trim());
      if (cells.every(c => /^[\s-]+$/.test(c))) return ''; // separator row
      return '<tr>' + cells.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
    });
    html = html.replace(/(<tr>[\s\S]*?<\/tr>)/g, '<table>$1</table>');
    // Code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    // Line breaks
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<div class="report-content"><p>' + html + '</p></div>';
    return html;
  },

  // Skeleton screen
  showSkeleton() {
    this.$('metrics').innerHTML = [1,2,3,4,5].map(() => '<div class="stat skeleton skeleton-row" style="width:100px;height:60px;"></div>').join('');
    this.$('discovery').innerHTML = [1,2,3].map(() => '<div class="discovery-card skeleton" style="height:100px;"></div>').join('');
    this.$('toolOverview').innerHTML = [1,2,3,4].map(() => '<div class="tool-card skeleton" style="height:80px;"></div>').join('');
    this.$('rows').innerHTML = [1,2,3,4,5].map(() => `<tr><td colspan="6"><div class="skeleton skeleton-row"></div></td></tr>`).join('');
  },

  // Error state
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
git commit -m "feat: add render.js with three-zone layout, virtual scroll, detail panel, report rendering"
```

---

## 任务 6：charts.js + app.js + index.html

**文件：**
- 创建：`site/js/charts.js`
- 创建：`site/js/app.js`
- 创建：`site/index.html`

- [ ] **步骤 1：编写 charts.js**

```javascript
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
```

- [ ] **步骤 2：编写 app.js（入口）**

```javascript
// site/js/app.js
// Entry point: event binding, debounce, init
const $ = id => document.getElementById(id);

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

async function main() {
  // Show skeleton immediately
  SIC_render.showSkeleton();

  // Load data progressively
  const ok = await SIC_data.loadAll(label => {
    // Could update skeleton with progress indicator
  });

  if (!ok) {
    SIC_render.showError();
    return;
  }

  // Read URL state
  SIC_filters.readState();

  // Initial render
  SIC_render.renderAll();

  // Event bindings
  // Search input with debounce
  $('q').addEventListener('input', debounce(e => {
    SIC_filters.searchQuery = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  }, 300));

  // Sort selector
  $('sort').addEventListener('change', e => {
    SIC_filters.sortBy = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // OR/AND toggle
  $('modeToggle').addEventListener('click', () => {
    SIC_filters.toggleMode();
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
    $('modeToggle').querySelectorAll('button').forEach(b => b.classList.toggle('active'));
  });

  // Curated only checkbox
  $('curatedOnly').addEventListener('change', e => {
    SIC_filters.curatedOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // Language toggle
  $('langZh').addEventListener('click', () => { SIC_i18n.setLang('zh'); SIC_render.renderAll(); });
  $('langEn').addEventListener('click', () => { SIC_i18n.setLang('en'); SIC_render.renderAll(); });

  // Detail panel close on overlay click
  $('detailOverlay').addEventListener('click', e => {
    if (e.target.id === 'detailOverlay') SIC_render.closeDetail();
  });

  // Keyboard: ESC to close detail
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') SIC_render.closeDetail();
  });

  // Export favorites button
  $('exportFav')?.addEventListener('click', () => {
    const url = SIC_data.exportFavoritesUrl();
    navigator.clipboard?.writeText(url).catch(() => {});
    alert(url);
  });

  // Nav links: load reports in-site
  document.querySelectorAll('[data-report]').forEach(el => {
    el.addEventListener('click', async e => {
      e.preventDefault();
      const reportFile = el.dataset.report;
      try {
        const r = await fetch(`reports/${reportFile}`);
        const md = await r.text();
        $('detailOverlay').innerHTML = `<button class="detail-close" onclick="SIC_render.closeDetail()">&times;</button>${SIC_render.renderReport(md)}`;
        $('detailOverlay').classList.add('open');
      } catch (err) {
        console.error('Report load error:', err);
      }
    });
  });
}

main();
```

- [ ] **步骤 3：编写 index.html**

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Search in Coding - AI Coding Agent 生态追踪器</title>
  <meta name="description" content="持续自动更新的 AI Coding Agent 生态追踪索引库，追踪 10 个主流 AI 编码工具的插件、MCP、Skills、Rules、Context Engineering 资源。">
  <link rel="stylesheet" href="styles.css">
  <!-- JSON-LD structured data -->
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Search in Coding",
    "description": "AI Coding Agent ecosystem tracker",
    "url": "https://coding.lzpgood.online/"
  }
  </script>
</head>
<body>
  <header>
    <div class="topbar">
      <div>
        <h1>Search in Coding</h1>
        <p data-i18n="subtitle">AI Coding Agent 生态追踪器</p>
      </div>
      <div class="lang-switch" aria-label="Language switcher">
        <button id="langZh" type="button">中文</button>
        <button id="langEn" type="button">English</button>
      </div>
    </div>
    <nav>
      <a href="#" data-report="weekly-report.md" data-i18n="navWeekly">生态周报</a>
      <a href="#" data-report="tool-comparison.md" data-i18n="navCompare">工具对比</a>
      <a href="#" data-report="curated-top.md" data-i18n="navTop">推荐榜</a>
      <button id="exportFav" class="fav-btn" data-i18n="exportFav">导出收藏</button>
    </nav>
  </header>

  <main>
    <!-- Zone 1: Discovery -->
    <section id="discoverySection">
      <h2 data-i18n="discoveryTitle">本周新发现</h2>
      <p class="hint" data-i18n="discoveryHint">最近 7 天新增的高质量项目</p>
      <div id="discovery" class="discovery-grid"></div>
    </section>

    <!-- Zone 2: Tool Overview -->
    <section id="toolOverviewSection">
      <h2 data-i18n="toolOverviewTitle">工具生态概览</h2>
      <p class="hint" data-i18n="toolOverviewHint">点击工具卡片查看该工具的生态资源</p>
      <div id="toolOverview" class="tool-grid"></div>
    </section>

    <!-- Zone 3: Search -->
    <section id="searchZone">
      <h2 data-i18n="searchTitle">生态项目搜索</h2>
      <p class="hint" data-i18n="searchHint">多选标签筛选</p>

      <!-- Metrics -->
      <section id="metrics" class="metrics" aria-label="Statistics"></section>

      <!-- Controls -->
      <div class="controls">
        <input id="q" data-i18n-placeholder="searchPlaceholder" placeholder="搜索..." aria-label="Search">

        <!-- Tool tag buttons -->
        <div id="toolTags" class="tag-group" role="group" aria-label="Tool filter"></div>

        <!-- Resource type tag buttons -->
        <div id="typeTags" class="tag-group" role="group" aria-label="Type filter"></div>

        <!-- OR/AND toggle -->
        <div id="modeToggle" class="mode-toggle" role="radiogroup" aria-label="Match mode">
          <button class="active" data-i18n="modeOR">任一匹配</button>
          <button data-i18n="modeAND">全部匹配</button>
        </div>

        <!-- Sort -->
        <select id="sort" aria-label="Sort">
          <option value="score" data-i18n="sortScore">分数</option>
          <option value="stars" data-i18n="sortStars">Stars</option>
          <option value="updated" data-i18n="sortUpdated">最近更新</option>
          <option value="match" data-i18n="sortMatch">标签匹配</option>
          <option value="recent" data-i18n="sortRecent">最近发现</option>
          <option value="name" data-i18n="sortName">名称</option>
        </select>

        <label><input id="curatedOnly" type="checkbox"> <span data-i18n="curatedOnly">只看推荐</span></label>
      </div>

      <!-- Results table -->
      <table role="table">
        <thead>
          <tr>
            <th data-i18n="thName">名称</th>
            <th data-i18n="thType">类型</th>
            <th data-i18n="thTools">工具</th>
            <th data-i18n="thScore">分数</th>
            <th data-i18n="thStars">Stars</th>
            <th data-i18n="thLink">链接</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </section>
  </main>

  <!-- Detail panel overlay -->
  <aside id="detailOverlay" class="detail-overlay" role="dialog" aria-modal="true" aria-label="Project details"></aside>

  <!-- Scripts: load order matters -->
  <script src="js/i18n.js"></script>
  <script src="js/data.js"></script>
  <script src="js/filters.js"></script>
  <script src="js/charts.js"></script>
  <script src="js/render.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

- [ ] **步骤 4：Commit**

```bash
cd "/root/workspace/search in coding"
git add site/js/charts.js site/js/app.js site/index.html
git commit -m "feat: add charts.js, app.js entry point, and new index.html with three-zone semantic layout"
```

---

## 任务 7：重写 build_site.py（精简 JSON + 详情 JSON + sitemap + hash 文件名）

**文件：**
- 修改：`scripts/build_site.py`
- 创建：`tests/test_build_site_v2.py`

- [ ] **步骤 1：编写 build_site.py 测试**

```python
# tests/test_build_site_v2.py
"""Test build_site.py v2 features: slim JSON, detail JSON, sitemap, hash filenames."""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestBuildSiteV2:
    def test_slim_project_fields(self):
        """Slim projects.json should only contain table display fields."""
        from build_site import slim_project
        p = {
            'id': 'test', 'name': 'Test', 'url': 'https://github.com/o/r',
            'repo': 'o/r', 'source_type': 'github',
            'resource_type': ['mcp-server'], 'target_tools': ['claude-code'],
            'summary': 'A test', 'i18n': {'zh': {'name': 'Test', 'summary': 'A test'}, 'en': {}},
            'stars': 100, 'forks': 10, 'total_score': 35,
            'quantifiable_score': 35, 'quality_score': 0,
            'tracking_priority': 'pending',
            'last_updated': '2025-07-01', 'first_seen': '2025-07-01', 'last_seen': '2025-07-12',
            'license': 'MIT', 'languages': ['Python'],
            # These should NOT be in slim version:
            'score_detail': {'stars': 4, 'activity': 15},
            'llm_summary': {'zh': '...', 'en': '...'},
            'benchmark_ref': 'some-ref',
            'last_analyzed': '2025-07-10',
            'tags': ['ai'],
            'review_state': 'auto-indexed',
            'maturity': 'stable',
            'status': 'active',
        }
        slim = slim_project(p)
        assert 'id' in slim
        assert 'name' in slim
        assert 'total_score' in slim
        assert 'resource_type' in slim
        assert 'target_tools' in slim
        assert 'stars' in slim
        # Detail fields should NOT be in slim
        assert 'score_detail' not in slim
        assert 'llm_summary' not in slim
        assert 'benchmark_ref' not in slim
        assert 'last_analyzed' not in slim

    def test_detail_project_fields(self):
        """Detail JSON should contain all fields including LLM analysis."""
        from build_site import detail_project
        p = {
            'id': 'test', 'name': 'Test',
            'score_detail': {'stars': 4},
            'llm_summary': {'zh': '好的', 'en': 'Good'},
            'benchmark_ref': 'ref-1',
            'last_analyzed': '2025-07-10',
            'tracking_priority': 'track',
            'quantifiable_score': 35,
            'quality_score': 0,
            'total_score': 35,
        }
        detail = detail_project(p)
        assert detail['id'] == 'test'
        assert 'score_detail' in detail
        assert 'llm_summary' in detail
        assert 'benchmark_ref' in detail

    def test_hash_filename(self):
        from build_site import hash_filename
        h1 = hash_filename('app.js', 'content1')
        h2 = hash_filename('app.js', 'content2')
        assert h1 != h2
        assert h1.startswith('app.') and h1.endswith('.js')
        assert h2.startswith('app.') and h2.endswith('.js')
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_build_site_v2.py -v`
预期：FAIL

- [ ] **步骤 3：重写 build_site.py**

在 `build_site.py` 中新增以下函数和逻辑：

```python
import hashlib

# Fields for slim JSON (table display only)
SLIM_FIELDS = [
    'id', 'name', 'url', 'source_type', 'resource_type', 'target_tools',
    'summary', 'i18n', 'stars', 'forks', 'total_score', 'quantifiable_score',
    'quality_score', 'tracking_priority', 'last_updated', 'first_seen', 'last_seen',
    'license', 'languages', 'review_state',
]

# Fields for detail JSON (lazy-loaded)
DETAIL_FIELDS = SLIM_FIELDS + [
    'score_detail', 'llm_summary', 'benchmark_ref', 'last_analyzed',
    'repo', 'tags', 'maturity', 'status', 'why_it_matters',
]

RESOURCE_TYPE_LABELS = {
    'mcp-server': {'zh': 'MCP Server', 'en': 'MCP Server'},
    'skills': {'zh': 'Skills', 'en': 'Skills'},
    'rules': {'zh': 'Rules', 'en': 'Rules'},
    'agent-framework': {'zh': 'Agent 框架', 'en': 'Agent Framework'},
    'cli-tool': {'zh': 'CLI 工具', 'en': 'CLI Tool'},
    'tutorial': {'zh': '教程', 'en': 'Tutorial'},
}


def slim_project(p):
    """Return a slim version of project for table display."""
    return {k: p.get(k) for k in SLIM_FIELDS if k in p}


def detail_project(p):
    """Return full detail version for lazy-loaded detail panel."""
    return {k: p.get(k) for k in DETAIL_FIELDS if k in p}


def hash_filename(filename, content):
    """Generate a content-hashed filename (e.g., app.a3f2b1.js)."""
    h = hashlib.md5(content.encode('utf-8')).hexdigest()[:6]
    parts = filename.rsplit('.', 1)
    if len(parts) == 2:
        return f'{parts[0]}.{h}.{parts[1]}'
    return f'{parts[0]}.{h}'


def generate_sitemap(projects):
    """Generate sitemap.xml content."""
    urls = ['https://coding.lzpgood.online/']
    for p in projects:
        if p.get('url') and 'github.com' in p.get('url', ''):
            # Don't add GitHub URLs to sitemap, only our site pages
            pass
    # For now just the main page (detail pages are client-side rendered)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    lines.append('  <url><loc>https://coding.lzpgood.online/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
    lines.append('</urlset>')
    return '\n'.join(lines)


def prerender_html(projects, tools, metrics):
    """Generate pre-rendered HTML for SEO (first screen content)."""
    # This is a simplified version - inject key data into index.html
    # For full implementation, generate server-side rendered HTML
    pass  # Will be implemented in the main() function


def main():
    ap = argparse.ArgumentParser(description='Build static site with slim/detail JSON, sitemap, hashed assets')
    ap.parse_args()

    projects = [enrich_project(p) for p in load_jsonish('data/projects.yaml')]
    curated = [enrich_project(p) for p in load_jsonish('data/curated-projects.yaml')]
    rejected = [enrich_project(p) for p in load_jsonish('data/rejected-projects.yaml')]
    tools = [enrich_tool(t) for t in load_jsonish('data/seed-tools.yaml')]
    concepts = load_jsonish('data/concepts.yaml')

    official = [p for p in projects if p.get('source_type') == 'official-seed']
    ecosystem = [p for p in projects if p.get('tracking_priority') != 'reject' and p.get('source_type') != 'official-seed']

    metrics = {
        'projects': len(projects),
        'curated': len(curated),
        'rejected': len(rejected),
        'official_tools': len(official),
        'ecosystem_projects': len(ecosystem),
        'sources': dict(collections.Counter(p.get('source_type') for p in projects)),
        'tool_coverage': dict(collections.Counter(t for p in projects for t in p.get('target_tools', []))),
        'resource_type_coverage': dict(collections.Counter(c for p in projects for c in (p.get('resource_type') or []))),
        'languages': ['zh', 'en'],
    }

    i18n = {'languages': ['zh', 'en'], 'default': 'zh', 'resource_types': RESOURCE_TYPE_LABELS}

    # Write slim projects JSON (for table display)
    write_json('projects.json', [slim_project(p) for p in projects])
    write_json('curated-projects.json', [slim_project(p) for p in curated])
    write_json('rejected-projects.json', [slim_project(p) for p in rejected])

    # Write detail JSON (lazy-loaded by detail panel)
    write_json('projects-detail.json', [detail_project(p) for p in projects])

    # Write other data
    write_json('tools.json', tools)
    write_json('concepts.json', concepts)
    write_json('metrics.json', metrics)
    write_json('i18n.json', i18n)

    # Copy reports
    copy_reports()

    # Generate sitemap
    sitemap_path = ROOT / 'site' / 'sitemap.xml'
    sitemap_path.write_text(generate_sitemap(projects), encoding='utf-8')

    # Hash JS/CSS filenames and update index.html references
    site_dir = ROOT / 'site'
    for js_file in sorted((site_dir / 'js').glob('*.js')):
        content = js_file.read_text(encoding='utf-8')
        hashed = hash_filename(js_file.name, content)
        hashed_path = site_dir / 'js' / hashed
        hashed_path.write_text(content, encoding='utf-8')

    css_content = (site_dir / 'styles.css').read_text(encoding='utf-8')
    css_hashed = hash_filename('styles.css', css_content)
    (site_dir / css_hashed).write_text(css_content, encoding='utf-8')

    # Update index.html to reference hashed filenames
    index_path = site_dir / 'index.html'
    index_html = index_path.read_text(encoding='utf-8')
    for js_file in sorted((site_dir / 'js').glob('*.js')):
        orig_name = js_file.name
        content = js_file.read_text(encoding='utf-8')
        hashed = hash_filename(orig_name, content)
        index_html = index_html.replace(f'js/{orig_name}', f'js/{hashed}')
    index_html = index_html.replace('styles.css', css_hashed)
    index_path.write_text(index_html, encoding='utf-8')

    print(json.dumps({
        'site_data': 'site/data',
        'reports': 'site/reports',
        'projects': len(projects),
        'slim_projects': len([slim_project(p) for p in projects]),
        'detail_projects': len([detail_project(p) for p in projects]),
        'curated': len(curated),
        'tools': len(tools),
        'sitemap': True,
        'hashed_assets': True,
    }, ensure_ascii=False))
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_build_site_v2.py -v`
预期：PASS

- [ ] **步骤 5：运行 build_site.py**

运行：`cd "/root/workspace/search in coding" && python3 scripts/build_site.py`
预期：生成 slim JSON + detail JSON + sitemap.xml + hashed JS/CSS

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/build_site.py tests/test_build_site_v2.py site/
git commit -m "feat: build_site.py v2 with slim/detail JSON, sitemap, hashed assets, SEO"
```

---

## 任务 8：删除旧 app.js、端到端验证和部署

- [ ] **步骤 1：删除旧 app.js**

```bash
cd "/root/workspace/search in coding"
rm site/app.js  # old 27-line version, replaced by site/js/app.js
```

- [ ] **步骤 2：运行完整 pipeline**

运行：`cd "/root/workspace/search in coding" && python3 scripts/update_tracker.py --skip-collect`
预期：全流程 PASS

- [ ] **步骤 3：运行所有测试**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/ -v`
预期：全部 PASS

- [ ] **步骤 4：验证站点文件**

运行：
```bash
cd "/root/workspace/search in coding"
echo "=== JS modules ==="
ls -la site/js/
echo "=== Data files ==="
ls -la site/data/
echo "=== Sitemap ==="
head -5 site/sitemap.xml
echo "=== Hashed assets ==="
ls site/js/app.*.js site/styles.*.css 2>/dev/null
echo "=== Index references ==="
grep -o 'js/[a-z]*\.[a-z0-9]*\.js' site/index.html
grep -o 'styles\.[a-z0-9]*\.css' site/index.html
```

- [ ] **步骤 5：部署站点**

运行：`cd "/root/workspace/search in coding" && python3 scripts/deploy_site.py`

- [ ] **步骤 6：浏览器验证**

访问 https://coding.lzpgood.online/，验证：
- 骨架屏在加载期间显示
- 三区布局正常（发现区、工具概览区、搜索区）
- 标签按钮组多选筛选工作正常
- OR/AND 切换工作正常
- 6 种排序切换正常
- 项目详情面板打开/关闭正常
- 收藏功能正常（刷新后保留）
- 报告链接打开站内渲染
- 移动端响应式布局正常
- 无 JS 控制台错误

- [ ] **步骤 7：Commit 并 tag**

```bash
cd "/root/workspace/search in coding"
git add -A
git commit -m "feat: batch 2 complete - website rewrite with three-zone layout, multi-select filters, detail panel, SEO, performance"
git tag v2025.07.12-batch2
```

- [ ] **步骤 8：更新 Wiki**

更新：
- `wiki/L3-代码地图.md` - 更新前端文件列表（site/js/ 目录）
- `wiki/L4A-前端详解.md` - 完全重写（新的模块结构、三区布局、筛选器、详情面板）
- `wiki/L6-经验录.md` - 记录前端重构的坑

---

## 验收标准

- [ ] `site/app.js`（旧 27 行）已删除，替换为 `site/js/` 下 6 个模块文件
- [ ] `styles.css` 使用 CSS 自定义属性，包含三区布局、骨架屏、详情面板样式
- [ ] `index.html` 使用语义 HTML，包含 JSON-LD 结构化数据
- [ ] 三区布局正常：发现区（本周新增）+ 工具概览区（10 个工具卡片）+ 搜索区（筛选表格）
- [ ] 筛选器：标签按钮组多选，OR/AND 切换，6 种排序
- [ ] 项目详情面板：侧边滑出，含评分明细、关联项目推荐
- [ ] 收藏功能：localStorage 存储，URL 导出
- [ ] 骨架屏：数据加载期间显示
- [ ] 渐进式渲染：metrics 先到先渲染
- [ ] 虚拟滚动：IntersectionObserver 实现分页加载
- [ ] 报告站内渲染：点击导航链接在详情面板中展示
- [ ] `build_site.py` 生成精简 JSON + 详情 JSON + sitemap.xml + hash 文件名
- [ ] 移动端响应式正常
- [ ] 无 JS 控制台错误
- [ ] 所有测试通过
