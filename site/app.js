let projects = [], curated = [], tools = [], metrics = {};
let lang = localStorage.getItem('sic_lang') || ((navigator.language || '').toLowerCase().startsWith('zh') ? 'zh' : 'en');

const $ = id => document.getElementById(id);

const UI = {
  zh: {
    subtitle: 'AI Coding Agent 生态追踪器：终端 Agent、AI IDE、MCP、Skills、Rules、Context Engineering',
    navFinal: '最终报告', navCurated: '推荐榜', navAudit: '来源审计',
    officialTitle: '官方目标工具', rankingTitle: '生态项目榜',
    rankingHint: '默认排除 official seed tools；优先展示自动推荐 / verified 项目。',
    searchPlaceholder: '搜索项目、工具、分类', allTools: '全部工具', allCategories: '全部分类', allSources: '全部来源', allStates: '全部状态',
    curatedOnly: '只看自动推荐', thName: '名称', thSource: '来源', thQuality: '质量', thCategory: '分类', thTools: '工具', thScore: '分数', thLink: '链接',
    open: '打开', curated: '自动推荐', metrics: {projects:'总记录', curated:'自动推荐', rejected:'低质/噪声', official_tools:'官方工具', ecosystem_projects:'生态项目'}
  },
  en: {
    subtitle: 'AI Coding Agent ecosystem tracker: terminal agents, AI IDEs, MCP, skills, rules, and context engineering',
    navFinal: 'Final Report', navCurated: 'Curated Top', navAudit: 'Source Audit',
    officialTitle: 'Official Target Tools', rankingTitle: 'Ecosystem Ranking',
    rankingHint: 'Official seed tools are excluded by default; auto-curated and verified records are prioritized.',
    searchPlaceholder: 'Search projects, tools, categories', allTools: 'All tools', allCategories: 'All categories', allSources: 'All sources', allStates: 'All states',
    curatedOnly: 'Auto-curated only', thName: 'Name', thSource: 'Source', thQuality: 'Quality', thCategory: 'Category', thTools: 'Tools', thScore: 'Score', thLink: 'Link',
    open: 'Open', curated: 'Auto-curated', metrics: {projects:'Records', curated:'Auto-curated', rejected:'Rejected/noisy', official_tools:'Official tools', ecosystem_projects:'Ecosystem projects'}
  }
};

function t(key){ return (UI[lang] && UI[lang][key]) || UI.zh[key] || key; }
function textOf(item, field){ return item?.i18n?.[lang]?.[field] || item?.i18n?.zh?.[field] || item?.i18n?.en?.[field] || item?.[field] || ''; }
function score(p){ const n = Number(p.total_score); if (Number.isFinite(n)) return n; return Object.values(p.score || {}).reduce((a,b)=>a+(Number(b)||0),0); }
function safeNumber(v){ const n = Number(v); return Number.isFinite(n) ? String(n) : '0'; }
function escapeHtml(s){ return String(s||'').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch])); }
function safeUrl(raw){
  try {
    const u = new URL(String(raw || ''), window.location.href);
    if (['http:', 'https:'].includes(u.protocol)) return u.href;
  } catch (_) {}
  return '#';
}
function safeToken(s){ return String(s||'').replace(/[^a-zA-Z0-9_-]/g, ''); }
function pills(xs){ return (xs||[]).map(x=>`<span class="pill">${escapeHtml(x)}</span>`).join(''); }

function applyLanguage(){
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  $('langZh')?.classList.toggle('active', lang === 'zh');
  $('langEn')?.classList.toggle('active', lang === 'en');
}

function renderMetrics(){
  const keys = ['projects','curated','rejected','official_tools','ecosystem_projects'];
  $('metrics').innerHTML = keys.map(k => `<div class="stat"><b>${safeNumber(metrics[k] ?? 0)}</b><br><span class="muted">${t('metrics')[k]}</span></div>`).join('');
}

function renderOfficial(){
  const off = projects.filter(p => p.ranking_scope === 'official');
  $('official').innerHTML = off.map(p => `<div class="card"><b>${escapeHtml(textOf(p,'name'))}</b><br>${pills(p.category)}<br><a href="${safeUrl(p.url)}" target="_blank" rel="noopener noreferrer">${t('open')}</a></div>`).join('');
}

function renderFiltersOnce(){
  const currentTool = $('tool').value, currentCat = $('cat').value, currentSource = $('source').value;
  $('tool').innerHTML = `<option value="">${t('allTools')}</option>`;
  tools.forEach(tool => $('tool').insertAdjacentHTML('beforeend', `<option value="${escapeHtml(tool.id)}">${escapeHtml(textOf(tool,'name') || tool.name)}</option>`));
  $('cat').innerHTML = `<option value="">${t('allCategories')}</option>`;
  [...new Set(projects.flatMap(p=>p.category||[]))].sort().forEach(c => $('cat').insertAdjacentHTML('beforeend', `<option>${escapeHtml(c)}</option>`));
  $('source').innerHTML = `<option value="">${t('allSources')}</option>`;
  [...new Set(projects.map(p=>p.source_type).filter(Boolean))].sort().forEach(s => $('source').insertAdjacentHTML('beforeend', `<option>${escapeHtml(s)}</option>`));
  $('tool').value = currentTool; $('cat').value = currentCat; $('source').value = currentSource;
}

function render(){
  applyLanguage(); renderMetrics(); renderOfficial(); renderFiltersOnce();
  const q = $('q').value.toLowerCase();
  const tool = $('tool').value, cat = $('cat').value, source = $('source').value, review = $('review').value, curatedOnly = $('curatedOnly').checked;
  const cids = new Set(curated.map(p=>p.id));
  const rows = projects
    .filter(p => p.ranking_scope === 'ecosystem' || p.ranking_scope === 'learning-resource')
    .filter(p => (!q || JSON.stringify(p).toLowerCase().includes(q)) && (!tool || (p.target_tools||[]).includes(tool)) && (!cat || (p.category||[]).includes(cat)) && (!source || p.source_type === source) && (!review || p.review_state === review) && (!curatedOnly || cids.has(p.id)))
    .sort((a,b)=>(cids.has(b.id)-cids.has(a.id)) || score(b)-score(a));
  $('rows').innerHTML = rows.map(p => `<tr><td><b>${escapeHtml(textOf(p,'name'))}</b><br><span class="muted">${escapeHtml(textOf(p,'summary'))}</span></td><td>${escapeHtml(p.source_type)}</td><td><span class="pill quality-${safeToken(p.source_quality||'unverified')}">${escapeHtml(p.source_quality||'unverified')}</span>${cids.has(p.id)?`<span class="pill">${t('curated')}</span>`:''}</td><td>${pills(p.category)}</td><td>${escapeHtml((p.target_tools||[]).join(', '))}</td><td>${safeNumber(score(p))}</td><td><a href="${safeUrl(p.url)}" target="_blank" rel="noopener noreferrer">${t('open')}</a></td></tr>`).join('');
}

async function main(){
  projects = await fetch('data/projects.json').then(r=>r.json()).catch(()=>[]);
  curated = await fetch('data/curated-projects.json').then(r=>r.json()).catch(()=>[]);
  tools = await fetch('data/tools.json').then(r=>r.json()).catch(()=>[]);
  metrics = await fetch('data/metrics.json').then(r=>r.json()).catch(()=>({}));
  ['q','tool','cat','source','review','curatedOnly'].forEach(id => $(id).addEventListener('input', render));
  $('langZh').addEventListener('click', () => { lang='zh'; localStorage.setItem('sic_lang', lang); render(); });
  $('langEn').addEventListener('click', () => { lang='en'; localStorage.setItem('sic_lang', lang); render(); });
  render();
}
main();
