// site/js/render.js
// Three-zone rendering, virtual scroll, detail panel, report rendering
// Batch B fixes: #1 score/60, #9 loading state, #10 score_detail, #11 human labels,
//   #12 hide empty fields, #20 clickable names, #7 result count + filter chips, #5 favoritesOnly
const SIC_render = {
  PAGE_SIZE: 20,
  renderedCount: 0,
  currentPage: 0,
  currentFiltered: [],
  toolOverviewExpanded: false,

  $: function(id) { return document.getElementById(id); },

  esc: function(s) {
    return String(s || '').replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  },

  safeUrl: function(raw) {
    try {
      var u = new URL(String(raw || ''), location.href);
      if (['http:', 'https:'].includes(u.protocol)) return u.href;
    } catch (_) {}
    return '#';
  },

  // Chinese mode prefers llm_summary; English / missing falls back to native summary
  summaryOf: function(item) {
    if (SIC_i18n.lang === 'zh' && item && item.llm_summary) {
      var ls = item.llm_summary;
      if (typeof ls === 'object') {
        if (ls.zh) return ls.zh;
        if (ls.en) return ls.en;
      } else if (typeof ls === 'string') {
        return ls;
      }
    }
    return SIC_i18n.textOf(item, 'summary') || '';
  },

  // #11: pills with i18n labels + color-coded classes
  pills: function(xs) {
    var self = SIC_render;
    return (xs || []).map(function(x) {
      var label = (SIC_i18n.t('resourceTypes')[x]) || x;
      var cls = 'pill-type-' + (x || 'default');
      return '<span class="pill ' + cls + '">' + self.esc(label) + '</span>';
    }).join('');
  },

  // #11: tool names as human-readable labels; empty tools show muted placeholder
  toolLabels: function(toolIds) {
    var self = SIC_render;
    var ids = toolIds || [];
    if (!ids.length) {
      return '<span class="pill muted">' + self.esc(SIC_i18n.t('noTools') || '—') + '</span>';
    }
    return ids.map(function(tid) {
      var tool = SIC_data.tools.find(function(t) { return t.id === tid; });
      var label = tool ? (SIC_i18n.textOf(tool, 'name') || tool.name) : tid;
      return '<span class="pill">' + self.esc(label) + '</span>';
    }).join('');
  },

  safeNum: function(v) {
    var n = Number(v);
    return Number.isFinite(n) ? String(n) : '0';
  },

  renderAll: function() {
    SIC_i18n.applyLanguage();
    this.renderMetrics();
    this.renderDiscovery();
    this.renderToolOverview();
    this.renderScoreChart();
    this.renderSearchZone();
    SIC_filters.writeState();
  },

  // #24: metrics now in hero area
  renderMetrics: function() {
    var m = SIC_data.metrics;
    var keys = ['projects', 'curated', 'official_tools', 'ecosystem_projects'];
    var self = this;
    this.$('metrics').innerHTML = keys.map(function(k) {
      return '<div class="hero-stat"><b>' + self.safeNum(m[k] || 0) + '</b><span class="muted">' +
        (SIC_i18n.t('metrics')[k] || k) + '</span></div>';
    }).join('');
  },

  renderDiscovery: function() {
    var self = this;
    var recent = SIC_data.projects
      .filter(function(p) {
        return p.tracking_priority !== 'reject' && p.source_type !== 'official-seed';
      })
      .sort(function(a, b) {
        var dateCmp = String(b.first_seen || b.last_seen || '').localeCompare(String(a.first_seen || a.last_seen || ''));
        if (dateCmp !== 0) return dateCmp;
        return (b.total_score || 0) - (a.total_score || 0);
      })
      .slice(0, 12);

    if (recent.length === 0) {
      this.$('discovery').innerHTML = '<p class="hint">' + SIC_i18n.t('discoveryHint') + '</p>';
      return;
    }

    this.$('discovery').innerHTML = recent.map(function(p) {
      return '<div class="discovery-card" data-action="detail" data-id="' + self.esc(p.id) + '">' +
        '<span class="score-badge">' + self.safeNum(p.total_score) + '</span> ' +
        '<b>' + self.esc(SIC_i18n.textOf(p, 'name')) + '</b><br>' +
        '<span class="muted">' + self.esc((self.summaryOf(p) || '').slice(0, 80)) + '</span><br>' +
        self.pills(p.resource_type) +
        '</div>';
    }).join('');
  },

  renderToolOverview: function() {
    var self = this;
    var TOOL_OVERVIEW_TOP_N = 8;
    var tools = SIC_data.tools.filter(function(t) { return t.id !== 'general-ai-coding'; });

    // Precompute counts once
    var withCounts = tools.map(function(t) {
      var count = SIC_data.projects.filter(function(p) {
        return (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject';
      }).length;
      var curated = SIC_data.curated.filter(function(p) {
        return (p.target_tools || []).includes(t.id);
      }).length;
      return { tool: t, count: count, curated: curated };
    }).sort(function(a, b) { return b.count - a.count; });

    var expanded = !!this.toolOverviewExpanded;
    var needToggle = withCounts.length > TOOL_OVERVIEW_TOP_N;
    var shown = (expanded || !needToggle)
      ? withCounts
      : withCounts.slice(0, TOOL_OVERVIEW_TOP_N);

    var toggleBtn = this.$('toolOverviewToggle');
    if (toggleBtn) {
      toggleBtn.hidden = !needToggle;
      if (needToggle) {
        toggleBtn.textContent = expanded
          ? SIC_i18n.t('collapseToolOverview')
          : (SIC_i18n.t('expandToolOverview') + ' (' + withCounts.length + ')');
      }
    }

    this.$('toolOverview').innerHTML = shown.map(function(item) {
      var t = item.tool;
      return '<div class="tool-card" data-action="tool-filter" data-tool="' + self.esc(t.id) + '">' +
        '<h3 title="' + self.esc(SIC_i18n.textOf(t, 'name') || t.name) + '">' +
        self.esc(SIC_i18n.textOf(t, 'name') || t.name) + '</h3>' +
        '<div class="tool-stats">' + item.count + (SIC_i18n.lang === 'zh' ? ' 个项目' : ' projects') +
        ' · ' + item.curated + (SIC_i18n.lang === 'zh' ? ' 推荐' : ' curated') + '</div>' +
        '</div>';
    }).join('');

    // Draw bar chart for tool coverage — hide zero-count tools to reduce clutter
    var chartData = withCounts
      .filter(function(item) { return item.count > 0; })
      .map(function(item) {
        return {
          label: SIC_i18n.textOf(item.tool, 'name') || item.tool.name,
          value: item.count,
        };
      });
    var maxVal = Math.max.apply(Math, chartData.map(function(d) { return d.value; }).concat([1]));
    var chartEl = this.$('toolChart');
    if (chartEl) {
      chartEl.classList.add('chart-scroll-x');
      chartEl.innerHTML = SIC_charts.barChart(chartData, maxVal, {
        ariaLabel: SIC_i18n.t('toolChartTitle'),
      });
    }
  },

  renderScoreChart: function() {
    var scores = SIC_data.projects
      .filter(function(p) {
        return p.tracking_priority !== 'reject' && p.source_type !== 'official-seed';
      })
      .map(function(p) { return p.total_score || 0; });
    var chartEl = this.$('scoreChart');
    if (chartEl && scores.length > 0) {
      chartEl.innerHTML = SIC_charts.histogram(scores);
    }
  },

  // #5 favoritesOnly + #7 result count + filter chips
  renderSearchZone: function() {
    var curatedIds = SIC_data.curatedIds();
    var pool = SIC_data.projects;

    // #5: filter by favorites
    if (SIC_filters.favoritesOnly) {
      pool = pool.filter(function(p) { return SIC_data.isFav(p.id); });
    }

    this.currentFiltered = SIC_filters.apply(pool, curatedIds);
    this.currentPage = 0;
    if (SIC_filters._pendingPage && SIC_filters._pendingPage > 0) {
      this.currentPage = SIC_filters._pendingPage - 1;
      SIC_filters._pendingPage = null;
    }
    // Clamp page into valid range after filter/sort changes
    var maxPage = Math.max(0, Math.ceil(this.currentFiltered.length / this.PAGE_SIZE) - 1);
    if (this.currentPage > maxPage) this.currentPage = maxPage;
    if (this.currentPage < 0) this.currentPage = 0;

    // #7: result count "显示 X / Y"
    var totalProjects = SIC_data.projects.filter(function(p) {
      return p.source_type !== 'official-seed' && p.tracking_priority !== 'reject';
    }).length;
    var countEl = this.$('resultCount');
    if (countEl) {
      countEl.textContent = SIC_i18n.t('showing') + ' ' + this.currentFiltered.length + ' / ' + totalProjects;
    }

    // #7: active filter chips
    this.renderActiveFilters();

    // #7: clear button visibility
    var clearBtn = this.$('clearFilters');
    if (clearBtn) clearBtn.style.display = SIC_filters.hasActiveFilters() ? '' : 'none';

    if (this.currentFiltered.length === 0) {
      this.$('rows').innerHTML = '<tr><td colspan="6" class="empty-box">' +
        SIC_i18n.t('noResults') + '<br><span class="muted">' +
        SIC_i18n.t('adjustFilter') + '</span></td></tr>';
      this.renderPagination();
      return;
    }

    this.renderPage();
    this.renderPagination();
    this.renderSortIndicators();
  },

  // #7: render active filter chips
  renderActiveFilters: function() {
    var self = this;
    var container = this.$('activeFilters');
    if (!container) return;
    var chips = [];
    if (SIC_filters.searchQuery) {
      chips.push({label: '"' + SIC_filters.searchQuery + '"', type: 'q'});
    }
    SIC_filters.selectedTools.forEach(function(t) {
      var tool = SIC_data.tools.find(function(x) { return x.id === t; });
      chips.push({label: SIC_i18n.textOf(tool, 'name') || t, type: 'tool', value: t});
    });
    SIC_filters.selectedTypes.forEach(function(t) {
      chips.push({label: (SIC_i18n.t('resourceTypes')[t]) || t, type: 'type', value: t});
    });
    container.innerHTML = chips.map(function(c) {
      return '<span class="filter-chip">' + self.esc(c.label) +
        '<button data-action="remove-filter" data-filter-type="' + c.type +
        '" data-filter-value="' + self.esc(c.value || '') + '">&times;</button></span>';
    }).join('');
  },

  // Pagination slice (replaces infinite-scroll renderMore)
  renderPage: function() {
    var self = this;
    var start = this.currentPage * this.PAGE_SIZE;
    var end = Math.min(start + this.PAGE_SIZE, this.currentFiltered.length);
    var curatedIds = SIC_data.curatedIds();

    this.$('rows').innerHTML = this.currentFiltered.slice(start, end).map(function(p) {
      var isFav = SIC_data.isFav(p.id);
      var isCurated = curatedIds.has(p.id);
      var maxScore = (p.quality_score > 0) ? 100 : 60;
      return '<tr>' +
        '<td><b class="project-name" data-action="detail" data-id="' + self.esc(p.id) + '">' + self.esc(SIC_i18n.textOf(p, 'name')) + '</b><br>' +
        '<span class="muted">' + self.esc((self.summaryOf(p) || '').slice(0, 100)) + '</span></td>' +
        '<td>' + self.pills(p.resource_type) + '</td>' +
        '<td>' + self.toolLabels(p.target_tools) + '</td>' +
        '<td><span class="score-badge">' + self.safeNum(p.total_score) + '</span><span class="muted" style="font-size:11px;">/' + maxScore + '</span></td>' +
        '<td>★ ' + self.safeNum(p.stars) + '</td>' +
        '<td>' +
          '<a href="' + self.safeUrl(p.url) + '" target="_blank" rel="noopener noreferrer">' + SIC_i18n.t('open') + '</a> ' +
          '<button class="fav-btn ' + (isFav ? 'active' : '') + '" data-action="fav" data-id="' + self.esc(p.id) + '">★</button> ' +
          (isCurated ? '<span class="pill pill-curated">' + SIC_i18n.t('curated') + '</span> ' : '') +
          '<button data-action="detail" data-id="' + self.esc(p.id) + '">' + SIC_i18n.t('details') + '</button>' +
        '</td>' +
      '</tr>';
    }).join('');
  },

  renderSortIndicators: function() {
    var ths = document.querySelectorAll('th[data-sort]');
    for (var i = 0; i < ths.length; i++) {
      var th = ths[i];
      var field = th.dataset.sort;
      var arrow = '';
      if (field === SIC_filters.sortBy) {
        arrow = SIC_filters.sortDirection === 'asc' ? ' ▲' : ' ▼';
      }
      var baseText = SIC_i18n.t(th.dataset.i18n);
      th.textContent = baseText + arrow;
    }
  },

  renderPagination: function() {
    var total = this.currentFiltered.length;
    var pages = Math.max(1, Math.ceil(total / this.PAGE_SIZE));
    var current = this.currentPage + 1; // 1-indexed for display
    var container = this.$('pagination');
    if (!container) return;

    if (total === 0 || pages <= 1) {
      container.innerHTML = '';
      return;
    }

    // Keep current inside bounds if data shrank
    if (current > pages) {
      this.currentPage = pages - 1;
      current = pages;
    }

    var html = '';
    // Previous
    if (current > 1) {
      html += '<button class="page-btn" data-action="page" data-page="' + (current - 1) + '" aria-label="Previous page">‹</button>';
    }
    // Page numbers with ellipsis
    var startPage = Math.max(1, current - 2);
    var endPage = Math.min(pages, current + 2);
    if (startPage > 1) {
      html += '<button class="page-btn" data-action="page" data-page="1">1</button>';
      if (startPage > 2) html += '<span class="page-ellipsis">…</span>';
    }
    for (var p = startPage; p <= endPage; p++) {
      html += '<button class="page-btn' + (p === current ? ' active' : '') + '" data-action="page" data-page="' + p + '"' +
        (p === current ? ' aria-current="page"' : '') + '>' + p + '</button>';
    }
    if (endPage < pages) {
      if (endPage < pages - 1) html += '<span class="page-ellipsis">…</span>';
      html += '<button class="page-btn" data-action="page" data-page="' + pages + '">' + pages + '</button>';
    }
    // Next
    if (current < pages) {
      html += '<button class="page-btn" data-action="page" data-page="' + (current + 1) + '" aria-label="Next page">›</button>';
    }
    // Page info
    html += '<span class="page-info">' + SIC_i18n.t('pageOf').replace('{cur}', current).replace('{total}', pages) + '</span>';

    container.innerHTML = html;
  },

  // #9: loading state + #10: score_detail + #12: hide empty fields + #1: score /60
  openDetail: async function(projectId) {
    var self = this;
    var overlay = this.$('detailOverlay');

    // #9: show loading immediately
    overlay.innerHTML = '<div class="detail-loading">' + SIC_i18n.t('loading') + '</div>';
    overlay.classList.add('open');

    var p = SIC_data.projects.find(function(x) { return x.id === projectId; });
    if (!p) { overlay.innerHTML = '<p>Not found</p>'; return; }

    var detail = await SIC_data.loadDetail(projectId);
    var curatedIds = SIC_data.curatedIds();
    var isFav = SIC_data.isFav(p.id);
    var qScore = p.quantifiable_score || 0;
    var qualityScore = p.quality_score || 0;
    var total = p.total_score || 0;
    var sd = (detail && detail.score_detail) || p.score_detail || {};

    // Bug 7 fix: llm_summary is {zh, en}, not i18n structure
    var llmSummary = detail ? detail.llm_summary : null;
    var summaryText = '';
    if (llmSummary && typeof llmSummary === 'object') {
      summaryText = llmSummary[SIC_i18n.lang] || llmSummary.en || llmSummary.zh || '';
    } else if (typeof llmSummary === 'string') {
      summaryText = llmSummary;
    }

    // #12: hide empty fields
    var forksLine = p.forks ? '<p class="muted">Forks: ' + this.safeNum(p.forks) + '</p>' : '';
    var licenseLine = p.license ? '<p class="muted">License: ' + this.esc(p.license) + '</p>' : '';
    var langLine = (p.languages && p.languages.filter(Boolean).length > 0)
      ? '<p class="muted">Languages: ' + this.esc(p.languages.filter(Boolean).join(', ')) + '</p>' : '';

    // #1: score display as /60 or /100
    // #10: score_detail (quantifiable) + quality_detail (LLM)
    var maxScore = (qualityScore > 0) ? 100 : 60;
    var qd = (detail && detail.quality_detail) || p.quality_detail || {};
    var scoreDetailHtml = '';
    if (sd && Object.keys(sd).length > 0 && ('stars' in sd || 'activity' in sd || 'adoption' in sd || 'maturity' in sd)) {
      scoreDetailHtml = '<div class="detail-section">' +
        '<h3>' + SIC_i18n.t('scoreBreakdown') + '</h3>' +
        '<div class="score-detail-grid">' +
          '<div class="score-detail-item"><div class="label">Stars</div><div class="value">' + this.safeNum(sd.stars) + '/20</div></div>' +
          '<div class="score-detail-item"><div class="label">Activity</div><div class="value">' + this.safeNum(sd.activity) + '/15</div></div>' +
          '<div class="score-detail-item"><div class="label">Adoption</div><div class="value">' + this.safeNum(sd.adoption) + '/10</div></div>' +
          '<div class="score-detail-item"><div class="label">Maturity</div><div class="value">' + this.safeNum(sd.maturity) + '/15</div></div>' +
        '</div>' +
      '</div>';
    }

    var qualityDetailHtml = '';
    if (qd && Object.keys(qd).length > 0) {
      qualityDetailHtml = '<div class="detail-section">' +
        '<h3>' + (SIC_i18n.t('qualityBreakdown') || '质量分项') + '</h3>' +
        '<div class="score-detail-grid">' +
          '<div class="score-detail-item"><div class="label">Relevance</div><div class="value">' + this.safeNum(qd.relevance) + '/10</div></div>' +
          '<div class="score-detail-item"><div class="label">Practicality</div><div class="value">' + this.safeNum(qd.practicality) + '/10</div></div>' +
          '<div class="score-detail-item"><div class="label">Novelty</div><div class="value">' + this.safeNum(qd.novelty) + '/10</div></div>' +
          '<div class="score-detail-item"><div class="label">Ecosystem</div><div class="value">' + this.safeNum(qd.ecosystem_value) + '/10</div></div>' +
        '</div>' +
      '</div>';
    }

    var benchmarkRefHtml = '';
    if (detail && detail.benchmark_ref) {
      var refProject = SIC_data.projects.find(function(x) { return x.id === detail.benchmark_ref; });
      var refName = refProject ? SIC_i18n.textOf(refProject, 'name') : detail.benchmark_ref;
      benchmarkRefHtml = '<div class="detail-section"><h3>' + SIC_i18n.t('benchmarkRef') + '</h3><p class="muted">' + this.esc(refName) + '</p></div>';
    }

    overlay.innerHTML =
      '<button class="detail-close" data-action="close-detail">&times;</button>' +
      '<h2>' + this.esc(SIC_i18n.textOf(p, 'name')) + '</h2>' +
      '<p class="muted">' + this.esc(SIC_i18n.textOf(p, 'summary') || '') + '</p>' +

      '<div class="detail-section">' +
        '<h3>' + SIC_i18n.t('scoreDetail') + '</h3>' +
        '<div style="display:flex;gap:12px;align-items:center;margin-bottom:8px;">' +
          '<span class="score-badge score-badge-large">' + this.safeNum(total) + '</span>' +
          '<span class="muted">/ ' + maxScore + '</span>' +
        '</div>' +
        '<div class="score-bar"><div class="score-bar-fill" style="width:' + Math.min(100, total / maxScore * 100) + '%"></div></div>' +
        (qualityScore > 0
          ? '<p class="muted" style="margin-top:8px;">' + SIC_i18n.t('quality') + ': ' + this.safeNum(qualityScore) + '/40</p>'
          : '<p class="muted" style="margin-top:8px;">' + SIC_i18n.t('qualityPending') + '</p>') +
      '</div>' +

      scoreDetailHtml +
      qualityDetailHtml +

      '<div class="detail-section">' +
        '<h3>' + SIC_i18n.t('details') + '</h3>' +
        '<p>' + this.pills(p.resource_type) + '</p>' +
        '<p>' + this.toolLabels(p.target_tools) + '</p>' +
        '<p class="muted">Stars: ★ ' + this.safeNum(p.stars) + '</p>' +
        forksLine +
        licenseLine +
        langLine +
        '<p class="muted">First seen: ' + this.esc(p.first_seen) + '</p>' +
        '<p class="muted">Tracking: ' + this.esc(p.tracking_priority) + '</p>' +
      '</div>' +

      (summaryText ? '<div class="detail-section"><h3>LLM Summary</h3><p>' + this.esc(summaryText) + '</p></div>' : '') +

      benchmarkRefHtml +

      '<div class="detail-section">' +
        '<h3>' + SIC_i18n.t('relatedProjects') + '</h3>' +
        '<div id="relatedProjects">...</div>' +
      '</div>' +

      '<div class="detail-section">' +
        '<a href="' + this.safeUrl(p.url) + '" target="_blank" rel="noopener noreferrer">' + SIC_i18n.t('open') + ' -></a> ' +
        '<button class="fav-btn ' + (isFav ? 'active' : '') + '" data-action="fav" data-id="' + this.esc(p.id) + '">' +
          (isFav ? SIC_i18n.t('favorited') : SIC_i18n.t('favorite')) + '</button>' +
      '</div>';

    // Related projects
    var related = SIC_data.projects
      .filter(function(x) { return x.id !== p.id && x.tracking_priority !== 'reject'; })
      .filter(function(x) {
        var sharedType = (x.resource_type || []).some(function(rt) { return (p.resource_type || []).includes(rt); });
        var sharedTool = (x.target_tools || []).some(function(tt) { return (p.target_tools || []).includes(tt); });
        return sharedType || sharedTool;
      })
      .sort(function(a, b) { return (b.total_score || 0) - (a.total_score || 0); })
      .slice(0, 5);
    var relatedEl = document.getElementById('relatedProjects');
    if (relatedEl) {
      relatedEl.innerHTML = related.length ? related.map(function(r) {
        return '<div style="margin-bottom:6px;"><a href="javascript:void(0)" data-action="detail" data-id="' +
          self.esc(r.id) + '">' + self.esc(SIC_i18n.textOf(r, 'name')) + '</a> <span class="muted">(' +
          self.safeNum(r.total_score) + ')</span></div>';
      }).join('') : '<span class="muted">N/A</span>';
    }
  },

  closeDetail: function() {
    this.$('detailOverlay').classList.remove('open');
  },

  toggleFav: function(id) {
    SIC_data.toggleFav(id);
  },

  renderReport: function(md) {
    if (!md) return '<p class="muted">Report unavailable.</p>';
    // Escape HTML first
    var html = this.esc(md);
    // Code blocks (before other processing to protect content)
    html = html.replace(/```[\s\S]*?```/g, function(m) {
      return '<pre><code>' + m.slice(3, -3) + '</code></pre>';
    });
    // Headers
    html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Tables
    var lines = html.split('\n');
    var result = [];
    var inTable = false;
    var tableRows = [];
    var isFirstRow = true;
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
        var cells = line.split('|').filter(function(c) { return c.trim(); });
        // Skip separator rows (e.g., |---|---|)
        if (cells.every(function(c) { return /^[\s-]+$/.test(c); })) continue;
        if (isFirstRow) {
          tableRows.push('<tr>' + cells.map(function(c) { return '<th>' + c.trim() + '</th>'; }).join('') + '</tr>');
          isFirstRow = false;
        } else {
          tableRows.push('<tr>' + cells.map(function(c) { return '<td>' + c.trim() + '</td>'; }).join('') + '</tr>');
        }
        inTable = true;
      } else {
        if (inTable) {
          result.push('<div class="table-scroll"><table>' + tableRows.join('') + '</table></div>');
          tableRows = [];
          inTable = false;
          isFirstRow = true;
        }
        result.push(line);
      }
    }
    if (inTable) result.push('<div class="table-scroll"><table>' + tableRows.join('') + '</table></div>');
    html = result.join('\n');
    // Unordered lists
    html = html.replace(/^(- .+(?:\n- .+)*)/gm, function(m) {
      return '<ul>' + m.split('\n').map(function(l) { return '<li>' + l.slice(2) + '</li>'; }).join('') + '</ul>';
    });
    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    html = html.replace(/\n/g, '<br>');
    return '<div class="report-content"><p>' + html + '</p></div>';
  },

  showSkeleton: function() {
    this.$('metrics').innerHTML = [1, 2, 3, 4].map(function() {
      return '<div class="hero-stat skeleton" style="width:120px;height:70px;"></div>';
    }).join('');
    this.$('discovery').innerHTML = [1, 2, 3].map(function() {
      return '<div class="discovery-card skeleton" style="height:100px;"></div>';
    }).join('');
    this.$('toolOverview').innerHTML = [1, 2, 3, 4].map(function() {
      return '<div class="tool-card skeleton" style="height:80px;"></div>';
    }).join('');
    this.$('rows').innerHTML = [1, 2, 3, 4, 5].map(function() {
      return '<tr><td colspan="6"><div class="skeleton" style="height:20px;margin:8px 0;"></div></td></tr>';
    }).join('');
  },

  showError: function() {
    var self = this;
    this.$('rows').innerHTML = '<tr><td colspan="6" class="error-box">' +
      SIC_i18n.t('loadError') + '<br>' +
      '<button data-action="reload">' + SIC_i18n.t('retry') + '</button>' +
      '</td></tr>';
  },
};
