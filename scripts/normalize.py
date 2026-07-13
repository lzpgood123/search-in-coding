#!/usr/bin/env python3
import argparse, json, re
from common import ROOT, load_jsonish, save_jsonish, slug

# Old CATEGORY_RULES kept for reference but replaced by resource_types_for()
RESOURCE_TYPE_RULES = {
    'mcp-server': ['mcp server', 'model context protocol', 'mcp'],
    'skills': ['skill', 'prompt pack', 'slash command', 'custom command', 'agent skill', 'claude skill'],
    'rules': ['agents.md', 'claude.md', 'cursor rules', '.cursorrules', 'rules', 'instruction file'],
    'agent-framework': ['agent framework', 'multi-agent', 'subagent', 'agent orchestration', 'agentic framework'],
    'cli-tool': ['cli', 'terminal', 'command line', 'codebase index', 'repo map', 'repository map', 'semantic search', 'codebase indexing'],
    'tutorial': ['tutorial', 'guide', 'best practice', 'case study', 'benchmark', 'evaluation', 'eval harness', 'leaderboard'],
}

ZH_RE = re.compile(r'[\u4e00-\u9fff]')

def i18n_fields(name, summary):
    name = name or ''
    summary = summary or ''
    return {'zh': {'name': name, 'summary': summary}, 'en': {'name': name, 'summary': summary}}

def has_any(text, phrases):
    low = text.lower()
    return any(p.lower() in low for p in phrases)

def target_tools_for(text, tools):
    low = text.lower()
    ids = []
    for t in tools:
        aliases = t.get('aliases', []) + [t.get('name', ''), t.get('id', '')]
        if any(a and a.lower() in low for a in aliases):
            ids.append(t['id'])
    return ids or ['general-ai-coding']

def resource_types_for(text):
    """Determine resource_type tags from project text."""
    low = text.lower()
    types = []
    for rt, phrases in RESOURCE_TYPE_RULES.items():
        if has_any(low, phrases):
            types.append(rt)
    return types or ['tutorial']

def github_record(it, tools):
    fn = it.get('fullName') or it.get('nameWithOwner')
    url = it.get('url') or (f'https://github.com/{fn}' if fn else None)
    name = fn or it.get('name') or url
    if not url or not name:
        return None
    desc = it.get('description') or ''
    text = f'{name} {desc}'
    stars = it.get('stargazersCount', it.get('stargazerCount'))
    summary = desc[:240] or name
    return {
        'id': slug('github-' + name),
        'name': name,
        'url': url,
        'repo': fn,
        'source_type': 'github',
        'resource_type': resource_types_for(text),
        'target_tools': target_tools_for(text, tools),
        'summary': summary,
        'i18n': i18n_fields(name, summary),
        'status': 'archived' if it.get('isArchived') else 'unknown',
        'license': (it.get('licenseInfo') or {}).get('spdxId') if isinstance(it.get('licenseInfo'), dict) else None,
        'stars': stars,
        'forks': it.get('forkCount'),
        'last_updated': it.get('updatedAt') or it.get('pushedAt'),
        'first_seen': None,
        'last_seen': None,
        'maturity': 'unknown',
        'languages': [it.get('language') or ((it.get('primaryLanguage') or {}).get('name') if isinstance(it.get('primaryLanguage'), dict) else None)],
        'tags': [],
        'review_state': 'auto-indexed',
        'quantifiable_score': 0,  # will be calculated by score.py
        'quality_score': 0,  # will be filled by weekly LLM analysis
        'total_score': 0,
        'score_detail': {},
        'tracking_priority': 'pending',
        'last_analyzed': None,
        'benchmark_ref': None,
    }

def from_github():
    tools = load_jsonish('data/seed-tools.yaml')
    recs = []
    for d in (ROOT / 'data/raw/github').glob('*'):
        for p in d.glob('*.json'):
            if p.name.endswith('-error.json'):
                continue
            data = json.loads(p.read_text(encoding='utf-8'))
            items = data if isinstance(data, list) else data.get('results', data if isinstance(data, list) else [])
            if p.name == 'repo-details.json':
                items = data
            for it in items:
                rec = github_record(it, tools)
                if rec:
                    recs.append(rec)
    return recs

def main():
    ap = argparse.ArgumentParser(description='Normalize raw collector outputs into data/projects.yaml')
    ap.add_argument('--source', choices=['all', 'github'], default='all')
    ap.parse_known_args()
    existing = load_jsonish('data/projects.yaml') if (ROOT / 'data/projects.yaml').exists() else []
    recs = from_github()
    by = {r.get('url') or r['id']: r for r in existing}
    import datetime
    now = datetime.date.today().isoformat()
    for r in recs:
        r['first_seen'] = r.get('first_seen') or now
        r['last_seen'] = now
        by[r.get('url') or r['id']] = r
    save_jsonish('data/projects.yaml', list(by.values()))
    print(json.dumps({'normalized_new': len(recs), 'total': len(by)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
