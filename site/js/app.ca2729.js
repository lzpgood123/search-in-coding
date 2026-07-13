// site/js/app.js
// Entry point, event delegation, debounce, skeleton screen
// Batch B fixes: #5 favoritesOnly, #7 clearFilters + remove-filter, #8 radiogroup, #15 deep link, #14 footer
var $ = function(id) { return document.getElementById(id); };

function debounce(fn, ms) {
  var t;
  return function() {
    var args = arguments;
    var self = this;
    clearTimeout(t);
    t = setTimeout(function() { fn.apply(self, args); }, ms);
  };
}

// Render tag buttons
function renderTagButtons() {
  var toolContainer = $('toolTags');
  if (toolContainer) {
    toolContainer.innerHTML = SIC_data.tools
      .filter(function(t) { return t.id !== 'general-ai-coding'; })
      .map(function(t) {
        var active = SIC_filters.selectedTools.has(t.id) ? ' active' : '';
        var name = SIC_i18n.textOf(t, 'name') || t.name;
        return '<button class="tag-btn' + active + '" data-action="tool-tag" data-tool="' + SIC_render.esc(t.id) + '">' + SIC_render.esc(name) + '</button>';
      }).join('');
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

  // Sort
  $('sort').addEventListener('change', function(e) {
    SIC_filters.sortBy = e.target.value;
    SIC_render.renderSearchZone();
    SIC_filters.writeState();
  });

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
  });
  $('langEn').addEventListener('click', function() {
    SIC_i18n.setLang('en');
    SIC_render.renderAll();
    syncUI();
  });

  // Detail overlay close (click on overlay background)
  $('detailOverlay').addEventListener('click', function(e) {
    if (e.target.id === 'detailOverlay') SIC_render.closeDetail();
  });

  // ESC
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') SIC_render.closeDetail();
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

  // Report links
  document.querySelectorAll('[data-report]').forEach(function(el) {
    el.addEventListener('click', async function(e) {
      e.preventDefault();
      var reportFile = el.dataset.report;
      try {
        var r = await fetch('reports/' + reportFile);
        if (!r.ok) {
          $('detailOverlay').innerHTML = '<button class="detail-close" data-action="close-detail">&times;</button>' +
            '<div class="report-content"><p>Report not found: ' + SIC_render.esc(reportFile) + '</p></div>';
          $('detailOverlay').classList.add('open');
          return;
        }
        var md = await r.text();
        $('detailOverlay').innerHTML = '<button class="detail-close" data-action="close-detail">&times;</button>' +
          SIC_render.renderReport(md);
        $('detailOverlay').classList.add('open');
      } catch (err) {
        console.error('Report load error:', err);
      }
    });
  });
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
  }
}

main();
