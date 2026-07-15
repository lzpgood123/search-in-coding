// site/js/filters.js
// Multi-select tag filtering, OR/AND toggle, 6 sort modes, URL state, recentOnly
// Batch B fixes: #5 favoritesOnly, #6 hash preservation, #7 hasActiveFilters/clearAll, #8 radiogroup, #15 deep link
// Pure logic - no DOM references
const SIC_filters = {
  selectedTools: new Set(),
  selectedTypes: new Set(),
  searchQuery: '',
  sortBy: 'score',
  sortDirection: 'desc',
  matchMode: 'or',
  curatedOnly: false,
  recentOnly: false,
  favoritesOnly: false,
  _pendingProject: null,
  _pendingPage: null,

  toggleSort(field) {
    if (this.sortBy === field) {
      this.sortDirection = this.sortDirection === 'desc' ? 'asc' : 'desc';
    } else {
      this.sortBy = field;
      this.sortDirection = 'desc';
    }
  },

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

  // #7: check if any filters are active
  hasActiveFilters() {
    return this.searchQuery || this.selectedTools.size > 0 || this.selectedTypes.size > 0 ||
      this.curatedOnly || this.recentOnly || this.favoritesOnly;
  },

  // #7: clear all filters
  clearAll() {
    this.searchQuery = '';
    this.selectedTools.clear();
    this.selectedTypes.clear();
    this.curatedOnly = false;
    this.recentOnly = false;
    this.favoritesOnly = false;
    this.sortBy = 'score';
    this.matchMode = 'or';
  },

  // Bug 5 fix: recentOnly - compute cutoff date from last 50 projects by first_seen
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
        // Batch 2: use prebuilt search-index Map (name/summary/resource_type/target_tools)
        // Do NOT JSON.stringify the whole project (matches internal fields & is slow).
        const q = this.searchQuery.toLowerCase();
        const text = (SIC_data.searchMap && SIC_data.searchMap[p.id]) || '';
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
      let cmp;
      switch (this.sortBy) {
        case 'name': cmp = SIC_i18n.textOf(a, 'name').localeCompare(SIC_i18n.textOf(b, 'name')); break;
        case 'stars': cmp = (b.stars || 0) - (a.stars || 0); break;
        case 'updated': cmp = String(b.last_updated || '').localeCompare(String(a.last_updated || '')); break;
        case 'recent': cmp = String(b.first_seen || b.last_seen || '').localeCompare(String(a.first_seen || a.last_seen || '')); break;
        case 'match': {
          const aMatch = this._matchCount(a);
          const bMatch = this._matchCount(b);
          if (bMatch !== aMatch) { cmp = bMatch - aMatch; break; }
          cmp = (b.total_score || 0) - (a.total_score || 0);
          break;
        }
        default: cmp = (b.total_score || 0) - (a.total_score || 0);
      }
      return this.sortDirection === 'asc' ? -cmp : cmp;
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
    if (qs.get('dir')) this.sortDirection = qs.get('dir');
    if (qs.get('mode')) this.matchMode = qs.get('mode');
    if (qs.get('curated') === '1') this.curatedOnly = true;
    if (qs.get('recent') === '1') this.recentOnly = true;
    if (qs.get('fav') === '1') this.favoritesOnly = true;
    // #15: project deep link
    if (qs.get('project')) this._pendingProject = qs.get('project');
    if (qs.get('page')) this._pendingPage = parseInt(qs.get('page'), 10);
    if (location.hash.startsWith('#favorites=')) {
      const ids = location.hash.slice(12).split(',').filter(Boolean);
      ids.forEach(id => SIC_data.favorites.add(id));
      localStorage.setItem('sic_favorites', JSON.stringify([...SIC_data.favorites]));
    }
  },

  // #6: preserve hash in writeState
  writeState() {
    const qs = new URLSearchParams();
    if (this.searchQuery) qs.set('q', this.searchQuery);
    if (this.selectedTools.size) qs.set('tools', [...this.selectedTools].join(','));
    if (this.selectedTypes.size) qs.set('types', [...this.selectedTypes].join(','));
    if (this.sortBy !== 'score') qs.set('sort', this.sortBy);
    if (this.sortDirection !== 'desc') qs.set('dir', this.sortDirection);
    if (this.matchMode === 'and') qs.set('mode', 'and');
    if (this.curatedOnly) qs.set('curated', '1');
    if (this.recentOnly) qs.set('recent', '1');
    if (this.favoritesOnly) qs.set('fav', '1');
    if (SIC_render.currentPage > 0) qs.set('page', String(SIC_render.currentPage + 1));
    const hash = location.hash; // #6: preserve hash
    history.replaceState(null, '', `${location.pathname}${qs.toString() ? '?' + qs : ''}${hash}`);
  },
};
