// site/js/app.js
// Entry point, event delegation, debounce, skeleton screen
// Style B: report centered modal + Esc stack (report first, then detail)
// Batch B fixes: #5 favoritesOnly, #7 clearFilters + remove-filter, #8 radiogroup, #15 deep link, #14 footer
var $ = function(id) { return document.getElementById(id); };

var REPORT_TITLES = {
  'curated-top.md': 'navTop',
  'weekly-report.md': 'navWeekly',
  'tool-comparison.md': 'navCompare'
};
var activeReportFile = null;

function debounce(fn, ms) {
  var t;
  return function() {
    var args = arguments;
    var self = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(self, args); }, ms);
  };
}

function isDetailOpen() {
  var el = $('detailOverlay');
  return !!(el && el.classList.contains('open'));
}

function isReportOpen() {
  var modal = $('reportModal');
  return !!(modal && !modal.hidden);
}

function setBodyScrollLock() {
  if (isReportOpen() || isDetailOpen()) {
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
  }
}

function setReportActive(reportFile) {
  activeReportFile = reportFile || null;
  var titleKey = REPORT_TITLES[reportFile] || 'navTop';
  var titleEl = $('reportModalTitle');
  if (titleEl) titleEl.textContent = SIC_i18n.t(titleKey);

  document.querySelectorAll('[data-report]').forEach(function(el) {
    var on = !!reportFile && el.dataset.report === reportFile;
    el.classList.toggle('active', on);
    if (el.getAttribute('role') === 'tab') {
      el.setAttribute('aria-selected', on ? 'true' : 'false');
    }
  });
}

async function openReportModal(reportFile) {
  if (!reportFile) return;
  var modal = $('reportModal');
  var backdrop = $('reportBackdrop');
  var body = $('reportModalBody');
  if (!modal || !backdrop || !body) return;

  modal.hidden = false;
  backdrop.hidden = false;
  setReportActive(reportFile);
  setBodyScrollLock();
  body.innerHTML = '<p class="muted">' + SIC_render.esc(SIC_i18n.t('loading')) + '</p>';

  try {
    var r = await fetch('reports/' + reportFile);
    if (!r.ok) {
      body.innerHTML = '<p>Report not found: ' + SIC_render.esc(reportFile) + '</p>';
      return;
    }
    // Guard against race if user switched tabs quickly
    if (activeReportFile !== reportFile) return;
    var md = await r.text();
    if (activeReportFile !== reportFile) return;
    body.innerHTML = SIC_render.renderReport(md);
  } catch (err) {
    console.error('Report load error:', err);
    body.innerHTML = '<p>' + SIC_render.esc(SIC_i18n.t('loadError')) + '</p>';
  }
}

function closeReportModal() {
  var modal = $('reportModal');
  var backdrop = $('reportBackdrop');
  var body = $('reportModalBody');
  if (modal) modal.hidden = true;
  if (backdrop) backdrop.hidden = true;
  if (body) body.innerHTML = '';
  setReportActive(null);
  setBodyScrollLock();
}

// Render tag buttons (tool chips support search + collapse for 31 tools)
var TOOL_TAGS_COLLAPSE_N = 10;
var toolTagsExpanded = false;
var toolTagQuery = '';

function getToolList() {
  return (SIC_data.tools || []).filter(function(t) {
    return t.id !== 'general-ai-coding';
  });
}

function toolMatchesQuery(tool, q) {
  if (!q) return true;
  var name = String(SIC_i18n.textOf(tool, 'name') || tool.name || '').toLowerCase();
  var id = String(tool.id || '').toLowerCase();
  var aliases = (tool.aliases || []).join(' ').toLowerCase();
  return name.indexOf(q) !== -1 || id.indexOf(q) !== -1 || aliases.indexOf(q) !== -1;
}

function updateToolTagsExpandBtn(visibleCount, totalCount) {
  var btn = $('toolTagsExpand');
  if (!btn) return;
  // Only show expand when not searching and there are more than N tools
  var needToggle = !toolTagQuery && totalCount > TOOL_TAGS_COLLAPSE_N;
  btn.hidden = !needToggle;
  if (!needToggle) return;
  btn.textContent = toolTagsExpanded
    ? SIC_i18n.t('collapseTools')
    : SIC_i18n.t('expandTools') + ' (' + totalCount + ')';
}

function renderTagButtons() {
  var toolContainer = $('toolTags');
  if (toolContainer) {
    var allTools = getToolList();
    var q = (toolTagQuery || '').trim().toLowerCase();
    var matched = allTools.filter(function(t) { return toolMatchesQuery(t, q); });

    // Always keep selected tools visible even if collapsed / filtered out of search
    var selected = allTools.filter(function(t) {
      return SIC_filters.selectedTools.has(t.id);
    });

    var visible;
    if (q) {
      // Searching: show all matches (selected first)
      var seen = {};
      visible = [];
      selected.concat(matched).forEach(function(t) {
        if (seen[t.id]) return;
        seen[t.id] = true;
        if (toolMatchesQuery(t, q) || SIC_filters.selectedTools.has(t.id)) {
          visible.push(t);
        }
      });
    } else if (toolTagsExpanded || allTools.length <= TOOL_TAGS_COLLAPSE_N) {
      visible = allTools.slice();
    } else {
      // Collapsed: first N + any selected beyond N
      var seen2 = {};
      visible = [];
      allTools.slice(0, TOOL_TAGS_COLLAPSE_N).concat(selected).forEach(function(t) {
        if (seen2[t.id]) return;
        seen2[t.id] = true;
        visible.push(t);
      });
    }

    toolContainer.innerHTML = visible.map(function(t) {
      var active = SIC_filters.selectedTools.has(t.id) ? ' active' : '';
      var name = SIC_i18n.textOf(t, 'name') || t.name;
      return '<button class="tag-btn' + active + '" data-action="tool-tag" data-tool="' +
        SIC_render.esc(t.id) + '" title="' + SIC_render.esc(name) + '">' +
        SIC_render.esc(name) + '</button>';
    }).join('');

    updateToolTagsExpandBtn(visible.length, allTools.length);
  }

  var typeContainer = $('typeTags');
  if (typeContainer) {
    var allTypes = [];
    SIC_data.projects.forEach(function(p) {
      (p.resource_type || []).forEach(function(rt) {
        if (allTypes.indexOf(rt) === -1) allTypes.push(rt);
      });
    });
    allTypes.sort();
    typeContainer.innerHTML = allTypes.map(function(type) {
      var active = SIC_filters.selectedTypes.has(type) ? ' active' : '';
      var label = (SIC_i18n.t('resourceTypes')[type]) || type;
      return '<button class="tag-btn' + active + '" data-action="type-tag" data-type="' + SIC_render.esc(type) + '">' + SIC_render.esc(label) + '</button>';
    }).join('');
  }

  // Keep tool search placeholder in sync with language
  var toolSearch = $('toolTagSearch');
  if (toolSearch) {
    toolSearch.placeholder = SIC_i18n.t('toolTagSearchPlaceholder');
    if (toolSearch.value !== toolTagQuery) toolSearch.value = toolTagQuery;
  }
}

// Sync UI controls from filter state
function syncUI() {
  var qEl = $('q'); if (qEl) qEl.value = SIC_filters.searchQuery;
  var sortEl = $('sort'); if (sortEl) sortEl.value = SIC_filters.sortBy;
  var curEl = $('curatedOnly'); if (curEl) curEl.checked = SIC_filters.curatedOnly;
  var recEl = $('recentOnly'); if (recEl) recEl.checked = SIC_filters.recentOnly;
  var favEl = $('favoritesOnly'); if (favEl) favEl.checked = SIC_filters.favoritesOnly;
  var modeBtns = $('modeToggle') ? $('modeToggle').querySelectorAll('button') : null;
  if (modeBtns && modeBtns.length >= 2) {
    modeBtns[0].classList.toggle('active', SIC_filters.matchMode === 'or');
    modeBtns[1].classList.toggle('active', SIC_filters.matchMode === 'and');
    modeBtns[0].setAttribute('aria-checked', SIC_filters.matchMode === 'or');
    modeBtns[1].setAttribute('aria-checked', SIC_filters.matchMode === 'and');
  }
  renderTagButtons();
}

// Event delegation handler - all clicks go through here
function handleGlobalClick(e) {
  var btn = e.target.closest('[data-action]');
  if (!btn) return;
  var action = btn.dataset.action;
  var id = btn.dataset.id;

  switch (action) {
    case 'detail':
      e.preventDefault();
      SIC_render.openDetail(id);
      setBodyScrollLock();
      break;
    case 'fav':
      SIC_render.toggleFav(id);
      btn.classList.toggle('active');
      break;
    case 'close-detail':
      SIC_render.closeDetail();
      setBodyScrollLock();
      break;
    case 'close-report':
      e.preventDefault();
      closeReportModal();
      break;
    case 'tool-tag':
      SIC_filters.toggleTool(btn.dataset.tool);
      btn.classList.toggle('active');
      // Re-render chips so selected tools stay visible when collapsed/searching
      renderTagButtons();
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      break;
    case 'type-tag':
      SIC_filters.toggleType(btn.dataset.type);
      btn.classList.toggle('active');
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      break;
    case 'toggle-tool-tags':
      toolTagsExpanded = !toolTagsExpanded;
      renderTagButtons();
      break;
    case 'toggle-tool-overview':
      SIC_render.toolOverviewExpanded = !SIC_render.toolOverviewExpanded;
      SIC_render.renderToolOverview();
      break;
    case 'tool-filter':
      // Bug 3 fix: sync tag button active state
      SIC_filters.setTool(btn.dataset.tool);
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      renderTagButtons();
      var sz = $('searchZone');
      if (sz) sz.scrollIntoView({ behavior: 'smooth' });
      break;
    case 'remove-filter':
      // #7: remove individual filter chip
      var ft = btn.dataset.filterType;
      var fv = btn.dataset.filterValue;
      if (ft === 'q') SIC_filters.searchQuery = '';
      else if (ft === 'tool') SIC_filters.toggleTool(fv);
      else if (ft === 'type') SIC_filters.toggleType(fv);
      syncUI();
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
      break;
    case 'reload':
      location.reload();
      break;
    case 'page': {
      var page = parseInt(btn.dataset.page, 10);
      if (!Number.isFinite(page)) break;
      var maxPage = Math.max(1, Math.ceil(SIC_render.currentFiltered.length / SIC_render.PAGE_SIZE));
      page = Math.min(Math.max(page, 1), maxPage);
      if (page - 1 === SIC_render.currentPage) break;
      SIC_render.currentPage = page - 1; // 0-indexed
      SIC_render.renderPage();
      SIC_render.renderPagination();
      var tableWrapper = document.querySelector('.table-wrapper');
      if (tableWrapper) tableWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
      SIC_filters.writeState();
      break;
    }
  }
}

function bindEvents() {
  // Global click delegation
  document.addEventListener('click', handleGlobalClick);

  // Search input with debounce
  $('q').addEventListener('input', debounce(function(e) {
    SIC_filters.searchQuery = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  }, 300));

  // Tool chip search (filter visible tool tags only; does not change project query)
  var toolSearchEl = $('toolTagSearch');
  if (toolSearchEl) {
    toolSearchEl.addEventListener('input', debounce(function(e) {
      toolTagQuery = e.target.value || '';
      // Auto-expand while searching so matches aren't hidden by collapse
      if (toolTagQuery.trim()) toolTagsExpanded = true;
      renderTagButtons();
    }, 150));
  }

  // Sort
  $('sort').addEventListener('change', function(e) {
    SIC_filters.sortBy = e.target.value;
    SIC_filters.sortDirection = 'desc';
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // Table header click sort
  var thead = document.querySelector('thead');
  if (thead) {
    thead.addEventListener('click', function(e) {
      var th = e.target.closest('th[data-sort]');
      if (!th) return;
      SIC_filters.toggleSort(th.dataset.sort);
      // Sync select
      var sortEl = $('sort');
      if (sortEl) sortEl.value = SIC_filters.sortBy;
      // Keep current page when only direction/field changes? Spec resets via renderSearchZone.
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
    });
  }

  // #8: OR/AND toggle - radiogroup behavior (clicking active button does nothing)
  $('modeToggle').addEventListener('click', function(e) {
    if (e.target.tagName !== 'BUTTON') return;
    var btns = $('modeToggle').querySelectorAll('button');
    var isOR = e.target === btns[0]; // first button is OR
    var newMode = isOR ? 'or' : 'and';
    if (newMode === SIC_filters.matchMode) return; // no change if same
    SIC_filters.matchMode = newMode;
    btns.forEach(function(b, i) {
      b.classList.toggle('active', (i === 0) === (newMode === 'or'));
      b.setAttribute('aria-checked', (i === 0) === (newMode === 'or'));
    });
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // Checkboxes
  $('curatedOnly').addEventListener('change', function(e) {
    SIC_filters.curatedOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });
  $('recentOnly').addEventListener('change', function(e) {
    SIC_filters.recentOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });
  // #5: favoritesOnly
  $('favoritesOnly').addEventListener('change', function(e) {
    SIC_filters.favoritesOnly = e.target.checked;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

  // #7: clear all filters
  var clearBtn = $('clearFilters');
  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      SIC_filters.clearAll();
      syncUI();
      SIC_render.renderSearchZone();
      SIC_filters.writeState();
    });
  }

  // Language
  $('langZh').addEventListener('click', function() {
    SIC_i18n.setLang('zh');
    SIC_render.renderAll();
    syncUI();
    if (isReportOpen() && activeReportFile) setReportActive(activeReportFile);
  });
  $('langEn').addEventListener('click', function() {
    SIC_i18n.setLang('en');
    SIC_render.renderAll();
    syncUI();
    if (isReportOpen() && activeReportFile) setReportActive(activeReportFile);
  });

  // Detail overlay close (click on overlay background)
  $('detailOverlay').addEventListener('click', function(e) {
    if (e.target.id === 'detailOverlay') {
      SIC_render.closeDetail();
      setBodyScrollLock();
    }
  });

  // Esc stack: report modal first, then detail
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Escape') return;
    if (isReportOpen()) {
      closeReportModal();
      return;
    }
    SIC_render.closeDetail();
    setBodyScrollLock();
  });

  // Export favorites - Bug 8 fix: input box instead of alert
  var exportBtn = $('exportFav');
  if (exportBtn) {
    exportBtn.addEventListener('click', function() {
      var url = SIC_data.exportFavoritesUrl();
      var input = $('favExportUrl');
      if (input) {
        input.value = url;
        input.style.display = 'block';
        input.select();
        if (navigator.clipboard) {
          navigator.clipboard.writeText(url).then(function() {
            input.dataset.copied = '1';
          }).catch(function() {});
        }
      }
    });
  }

  // Report links / modal tabs — open centered modal (never detailOverlay)
  document.querySelectorAll('[data-report]').forEach(function(el) {
    el.addEventListener('click', function(e) {
      e.preventDefault();
      openReportModal(el.dataset.report);
    });
  });

  var reportBackdrop = $('reportBackdrop');
  if (reportBackdrop) {
    reportBackdrop.addEventListener('click', function() {
      closeReportModal();
    });
  }
}

async function main() {
  SIC_render.showSkeleton();
  var ok = await SIC_data.loadAll();
  if (!ok) { SIC_render.showError(); return; }
  SIC_filters.readState();
  SIC_render.renderAll();
  syncUI();
  bindEvents();

  // #14: footer last updated time
  var lastUpdatedEl = $('lastUpdated');
  if (lastUpdatedEl) {
    lastUpdatedEl.textContent = (SIC_data.metrics && SIC_data.metrics.date)
      ? SIC_data.metrics.date
      : new Date().toISOString().slice(0, 10);
  }

  // #15: project deep link - open detail automatically
  if (SIC_filters._pendingProject) {
    SIC_render.openDetail(SIC_filters._pendingProject);
    setBodyScrollLock();
  }
}

main();
