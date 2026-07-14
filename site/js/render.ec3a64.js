// site/js/render.js
// Three-zone rendering, virtual scroll, detail panel, report rendering
// Batch B fixes: #1 score/60, #9 loading state, #10 score_detail, #11 human labels,
//   #12 hide empty fields, #20 clickable names, #7 result count + filter chips, #5 favoritesOnly
const SIC_render = {
  PAGE_SIZE: 50,
  renderedCount: 0,
  currentFiltered: [],
  _observer: null,

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
        '<span class="muted">' + self.esc((SIC_i18n.textOf(p, 'summary') || '').slice(0, 80)) + '</span><br>' +
        self.pills(p.resource_type) +
        '</div>';
    }).join('');
  },

  renderToolOverview: function() {
    var self = this;
    var tools = SIC_data.tools.filter(function(t) { return t.id !== 'general-ai-coding'; });
    this.$('toolOverview').innerHTML = tools.map(function(t) {
      var count = SIC_data.projects.filter(function(p) {
        return (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject';
      }).length;
      var curated = SIC_data.curated.filter(function(p) {
        return (p.target_tools || []).includes(t.id);
      }).length;
      return '<div class="tool-card" data-action="tool-filter" data-tool="' + self.esc(t.id) + '">' +
        '<h3>' + self.esc(SIC_i18n.textOf(t, 'name') || t.name) + '</h3>' +
        '<div class="tool-stats">' + count + (SIC_i18n.lang === 'zh' ? ' 个项目' : ' projects') +
        ' · ' + curated + (SIC_i18n.lang === 'zh' ? ' 推荐' : ' curated') + '</div>' +
        '</div>';
    }).join('');

    // Draw bar chart for tool coverage
    var chartData = tools.map(function(t) {
      return {
        label: (SIC_i18n.textOf(t, 'name') || t.name).slice(0, 8),
        value: SIC_data.projects.filter(function(p) {
          return (p.target_tools || []).includes(t.id) && p.tracking_priority !== 'reject';
        }).length,
      };
    });
    var maxVal = Math.max.apply(Math, chartData.map(function(d) { return d.value; }).concat([1]));
    var chartEl = this.$('toolChart');
    if (chartEl) chartEl.innerHTML = SIC_charts.barChart(chartData, maxVal);
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
    this.renderedCount = 0;

    // Bug 4 fix: disconnect old observer before clearing
    if (this._observer) {
      this._observer.disconnect();
    }
    this.$('rows').innerHTML = '';

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
      return;
    }

    this.renderMore();
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

  // Bug 4 fix: re-observe new last row after each load
  renderMore: function() {
    var self = this;
    var start = this.renderedCount;
    var end = Math.min(start + this.PAGE_SIZE, this.currentFiltered.length);
    var curatedIds = SIC_data.curatedIds();

    var html = this.currentFiltered.slice(start, end).map(function(p) {
      var isFav = SIC_data.isFav(p.id);
      var isCurated = curatedIds.has(p.id);
      var maxScore = (p.quality_score > 0) ? 100 : 60;
      // #1: score badge with /60 or /100 + #20: clickable project name + #11: human labels
      return '<tr>' +
        '<td><b class="project-name" data-action="detail" data-id="' + self.esc(p.id) + '">' + self.esc(SIC_i18n.textOf(p, 'name')) + '</b><br>' +
        '<span class="muted">' + self.esc((SIC_i18n.textOf(p, 'summary') || '').slice(0, 100)) + '</span></td>' +
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
    this.$('rows').insertAdjacentHTML('beforeend', html);
    this.renderedCount = end;

    // Bug 4 fix: create observer once, re-observe new last row
    if (this.renderedCount < this.currentFiltered.length) {
      if (!this._observer) {
        this._observer = new IntersectionObserver(function(entries) {
          if (entries[0].isIntersecting && self.renderedCount < self.currentFiltered.length) {
            self._observer.unobserve(entries[0].target);
            self.renderMore();
          }
        });
      }
      var lastRow = this.$('rows').lastElementChild;
      if (lastRow) this._observer.observe(lastRow);
    }
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
          result.push('<table>' + tableRows.join('') + '</table>');
          tableRows = [];
          inTable = false;
          isFirstRow = true;
        }
        result.push(line);
      }
    }
    if (inTable) result.push('<table>' + tableRows.join('') + '</table>');
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
