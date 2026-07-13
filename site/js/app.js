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

  // Sync UI controls with restored state
  syncUIFromFilters();

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

// Sync UI controls with filter state after readState()
function syncUIFromFilters() {
  // Restore search input
  const qEl = $('q');
  if (qEl) qEl.value = SIC_filters.searchQuery;

  // Restore sort
  const sortEl = $('sort');
  if (sortEl) sortEl.value = SIC_filters.sortBy;

  // Restore curatedOnly
  const curEl = $('curatedOnly');
  if (curEl) curEl.checked = SIC_filters.curatedOnly;

  // Restore mode toggle buttons
  const modeBtns = $('modeToggle')?.querySelectorAll('button');
  if (modeBtns) {
    modeBtns[0].classList.toggle('active', SIC_filters.matchMode === 'or');
    modeBtns[1].classList.toggle('active', SIC_filters.matchMode === 'and');
  }

  // Render tag buttons and sync active state
  renderTagButtons();
}

// Render tool and type tag buttons
function renderTagButtons() {
  const toolContainer = $('toolTags');
  if (toolContainer) {
    toolContainer.innerHTML = SIC_data.tools
      .filter(t => t.id !== 'general-ai-coding')
      .map(t => {
        const active = SIC_filters.selectedTools.has(t.id) ? ' active' : '';
        const name = SIC_i18n.textOf(t, 'name') || t.name;
        return `<button class="tag-btn${active}" onclick="toggleToolTag('${t.id}', this)">${SIC_render.esc(name)}</button>`;
      }).join('');
  }

  const typeContainer = $('typeTags');
  if (typeContainer) {
    const allTypes = [...new Set(SIC_data.projects.flatMap(p => p.resource_type || []))].sort();
    typeContainer.innerHTML = allTypes.map(type => {
      const active = SIC_filters.selectedTypes.has(type) ? ' active' : '';
      const label = SIC_i18n.t('resourceTypes')[type] || type;
      return `<button class="tag-btn${active}" onclick="toggleTypeTag('${type}', this)">${SIC_render.esc(label)}</button>`;
    }).join('');
  }
}

// Toggle tool tag button
function toggleToolTag(id, btn) {
  SIC_filters.toggleTool(id);
  btn.classList.toggle('active');
  SIC_render.renderSearchZone();
  SIC_filters.writeState();
}

// Toggle type tag button
function toggleTypeTag(type, btn) {
  SIC_filters.toggleType(type);
  btn.classList.toggle('active');
  SIC_render.renderSearchZone();
  SIC_filters.writeState();
}

main();
