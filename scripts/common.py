import json, re, subprocess, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def load_jsonish(rel):
    p=ROOT/rel
    if not p.exists(): return []
    txt=p.read_text(encoding='utf-8').strip()
    if not txt: return []
    return json.loads(txt)

def save_jsonish(rel, data):
    p=ROOT/rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding='utf-8')

def today(): return datetime.date.today().isoformat()

def slug(s):
    s = re.sub(r'[^a-zA-Z0-9]+','-', str(s).lower()).strip('-')
    return s[:100] or 'item'

def run(cmd, timeout=120):
    return subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=True, timeout=timeout)

def score_from_stars(stars):
    try: stars=int(stars or 0)
    except Exception: stars=0
    if stars>=50000: return 5
    if stars>=10000: return 4
    if stars>=1000: return 3
    if stars>=100: return 2
    if stars>0: return 1
    return 0

def total_score(p):
    s=p.get('score') or {}
    return sum(s.get(k,0) for k in ['ecosystem_value','activity','adoption','practicality','novelty','confidence'])

def infer_record_kind(p):
    st=p.get('source_type')
    cats=p.get('category') or []
    text=(p.get('name','')+' '+p.get('summary','')+' '+p.get('url','')).lower()
    if st=='official-seed' or 'official-tool' in cats:
        return 'official-tool'
    if st=='fallback-web':
        if any(x in text for x in ['tutorial','guide','best practice','docs','blog','case study','changelog','使用','教程','经验']):
            return 'tutorial'
        return 'fallback-result'
    if st=='github': return 'ecosystem-project'
    if st=='exa': return 'article'
    return 'ecosystem-project'

def infer_source_quality(p):
    st=p.get('source_type')
    if st in ('official-seed','github'): return 'verified'
    if st=='fallback-web': return 'fallback'
    if st=='exa': return 'verified'
    return 'unverified'

def infer_ranking_scope(p):
    kind=p.get('record_kind') or infer_record_kind(p)
    if kind=='official-tool': return 'official'
    if kind in ('tutorial','article','fallback-result'): return 'learning-resource'
    if p.get('review_state') in ('rejected', 'auto-rejected'): return 'excluded'
    return 'ecosystem'

def normalize_project_fields(p):
    p.setdefault('category', [])
    p.setdefault('target_tools', [])
    p.setdefault('concepts', [])
    p.setdefault('summary', p.get('name',''))
    p.setdefault('why_it_matters', '')
    p.setdefault('review_state', 'auto-indexed')
    p['record_kind']=p.get('record_kind') or infer_record_kind(p)
    p['source_quality']=p.get('source_quality') or infer_source_quality(p)
    p['ranking_scope']=p.get('ranking_scope') or infer_ranking_scope(p)
    if p.get('source_type')=='fallback-web':
        tags=p.setdefault('tags', [])
        if 'fallback-not-exa' not in tags: tags.append('fallback-not-exa')
        p['source_quality']='fallback'
    if p.get('review_state') == 'unreviewed':
        p['review_state'] = 'auto-indexed'
    if p.get('review_state') == 'reviewed':
        p['review_state'] = 'auto-curated'
    if p.get('review_state') == 'rejected':
        p['review_state'] = 'auto-rejected'
    if p['record_kind']=='official-tool':
        p['ranking_scope']='official'
        p['source_quality']='verified'
        p['review_state']='auto-curated'
    return p