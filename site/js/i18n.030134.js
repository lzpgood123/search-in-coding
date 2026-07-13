// site/js/i18n.js
// Bilingual configuration and language switching
// Batch B: added keys for favoritesOnly, showing, clearFilters, scoreBreakdown, qualityPending, footer
const SIC_i18n = {
  lang: localStorage.getItem('sic_lang') || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en'),

  UI: {
    zh: {
      subtitle: 'AI Coding Agent 生态追踪器：终端 Agent、AI IDE、MCP、Skills、Rules、Context Engineering',
      navWeekly: '生态周报', navCompare: '工具对比', navTop: '推荐榜',
      discoveryTitle: '最新发现', discoveryHint: '按发现时间排序的高质量项目 Top 12',
      toolOverviewTitle: '工具生态概览', toolOverviewHint: '点击工具卡片查看该工具的生态资源',
      searchTitle: '生态项目搜索', searchHint: '多选标签筛选，支持 OR/AND 切换',
      searchPlaceholder: '搜索项目名称或描述...',
      allTools: '全部工具', allTypes: '全部类型', allSources: '全部来源',
      sortScore: '分数', sortStars: 'Stars', sortUpdated: '最近更新', sortMatch: '标签匹配', sortRecent: '最近发现', sortName: '名称',
      modeOR: '任一匹配', modeAND: '全部匹配',
      details: '详情', copy: '复制链接', copied: '已复制', open: '打开',
      favorite: '收藏', favorited: '已收藏', exportFav: '导出收藏',
      curated: '推荐', tracking: '追踪中', indexed: '索引中',
      curatedOnly: '只看推荐', recentOnly: '只看最近新增', favoritesOnly: '只看收藏',
      thName: '名称', thType: '类型', thTools: '工具', thScore: '分数', thStars: 'Stars', thLink: '链接',
      loading: '加载中...', loadError: '数据加载失败', retry: '重试',
      noResults: '没有符合条件的项目', adjustFilter: '试试调整筛选条件',
      scoreDetail: '评分明细', quantifiable: '可量化分', quality: '质量分',
      scoreBreakdown: '评分分项', qualityPending: '质量分待 LLM 分析',
      benchmarkRef: '参照项目', relatedProjects: '关联项目', readme: 'README 预览',
      showing: '显示', clearFilters: '清空筛选',
      footerUpdated: '数据更新于', footerDesc: 'AI Coding Agent 生态追踪器',
      metrics: { projects: '总记录', curated: '推荐', rejected: '噪声', official_tools: '官方工具', ecosystem_projects: '生态项目' },
      resourceTypes: { 'mcp-server': 'MCP Server', 'skills': 'Skills', 'rules': 'Rules', 'agent-framework': 'Agent 框架', 'cli-tool': 'CLI 工具', 'tutorial': '教程' },
    },
    en: {
      subtitle: 'AI Coding Agent ecosystem tracker: terminal agents, AI IDEs, MCP, skills, rules, and context engineering',
      navWeekly: 'Weekly Report', navCompare: 'Tool Comparison', navTop: 'Top Picks',
      discoveryTitle: 'Latest Discoveries', discoveryHint: 'Top 12 high-quality projects by discovery date',
      toolOverviewTitle: 'Tool Ecosystem Overview', toolOverviewHint: 'Click a tool card to browse its ecosystem resources',
      searchTitle: 'Ecosystem Search', searchHint: 'Multi-select tag filtering with OR/AND toggle',
      searchPlaceholder: 'Search project name or description...',
      allTools: 'All tools', allTypes: 'All types', allSources: 'All sources',
      sortScore: 'Score', sortStars: 'Stars', sortUpdated: 'Recently Updated', sortMatch: 'Tag Match', sortRecent: 'Recently Discovered', sortName: 'Name',
      modeOR: 'Any match', modeAND: 'All match',
      details: 'Details', copy: 'Copy link', copied: 'Copied', open: 'Open',
      favorite: 'Favorite', favorited: 'Favorited', exportFav: 'Export Favorites',
      curated: 'Curated', tracking: 'Tracking', indexed: 'Indexed',
      curatedOnly: 'Curated only', recentOnly: 'Recent only', favoritesOnly: 'Favorites only',
      thName: 'Name', thType: 'Type', thTools: 'Tools', thScore: 'Score', thStars: 'Stars', thLink: 'Link',
      loading: 'Loading...', loadError: 'Failed to load data', retry: 'Retry',
      noResults: 'No projects match your filters', adjustFilter: 'Try adjusting your filters',
      scoreDetail: 'Score Details', quantifiable: 'Quantifiable', quality: 'Quality',
      scoreBreakdown: 'Score Breakdown', qualityPending: 'Quality score pending LLM analysis',
      benchmarkRef: 'Benchmark Reference', relatedProjects: 'Related Projects', readme: 'README Preview',
      showing: 'Showing', clearFilters: 'Clear filters',
      footerUpdated: 'Data updated', footerDesc: 'AI Coding Agent Ecosystem Tracker',
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
    var langZhBtn = document.getElementById('langZh');
    var langEnBtn = document.getElementById('langEn');
    if (langZhBtn) {
      langZhBtn.classList.toggle('active', this.lang === 'zh');
      langZhBtn.setAttribute('aria-pressed', this.lang === 'zh');
    }
    if (langEnBtn) {
      langEnBtn.classList.toggle('active', this.lang === 'en');
      langEnBtn.setAttribute('aria-pressed', this.lang === 'en');
    }
  }
};
