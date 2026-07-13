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
