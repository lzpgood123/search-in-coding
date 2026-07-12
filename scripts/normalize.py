#!/usr/bin/env python3
import argparse, json, re
from common import ROOT, load_jsonish, save_jsonish, slug, score_from_stars

CATEGORY_RULES = {
    'mcp-acp-a2a': ['mcp server', 'model context protocol', 'a2a', 'agent communication protocol', 'acp', 'mcp'],
    'skills-prompts': ['claude skill', 'agent skill', 'skills', 'prompt pack', 'slash command', 'custom command', 'prompts'],
    'rules-instructions': ['agents.md', 'claude.md', 'cursor rules', '.cursorrules', 'instruction file', 'rules'],
    'context-engineering': ['context engineering', 'codebase index', 'repo map', 'repository map', 'semantic search', 'codebase indexing'],
    'agent-harness': ['agent harness', 'multi-agent', 'agent orchestration', 'subagent', 'agent framework', 'agentic framework'],
    'testing-review-ci': ['pull request review', 'pr review', 'code review', 'test generation', 'ci automation', 'github action', 'review agent'],
    'benchmark-evaluation': ['benchmark', 'evaluation', 'eval harness', 'leaderboard', 'spec-driven'],
    'terminal-agent': ['terminal agent', 'cli agent', 'command line coding', 'terminal ai'],
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

def categories_for(text):
    cats = []
    low = text.lower()
    for cat, phrases in CATEGORY_RULES.items():
        if has_any(low, phrases):
            cats.append(cat)
    if 'terminal' in low and 'terminal-agent' not in cats:
        cats.append('terminal-agent')
    # AI IDE should be explicit, not inferred from every AI mention.
    if has_any(low, ['ai ide', 'cursor', 'qoder', 'trae', 'workbuddy', 'codebuddy']) and 'ai-ide' not in cats:
        cats.append('ai-ide')
    return cats or ['tutorial-case-study']

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
        'category': categories_for(text),
        'target_tools': target_tools_for(text, tools),
        'concepts': [],
        'summary': summary,
        'i18n': i18n_fields(name, summary),
        'why_it_matters': 'Discovered via GitHub search for AI coding agent ecosystem queries.',
        'status': 'archived' if it.get('isArchived') else 'unknown',
        'license': (it.get('licenseInfo') or {}).get('spdxId') if isinstance(it.get('licenseInfo'), dict) else None,
        'stars': stars,
        'forks': it.get('forkCount'),
        'last_updated': it.get('updatedAt') or it.get('pushedAt'),
        'first_seen': None,
        'last_seen': None,
        'maturity': 'unknown',
        'integration_surfaces': [],
        'languages': [it.get('language') or ((it.get('primaryLanguage') or {}).get('name') if isinstance(it.get('primaryLanguage'), dict) else None)],
        'tags': [],
        'score': {'ecosystem_value': 3, 'activity': 2, 'adoption': score_from_stars(stars), 'practicality': 2, 'novelty': 2, 'confidence': 4},
        'notes': '',
        'review_state': 'auto-indexed',
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

def from_exa():
    tools = load_jsonish('data/seed-tools.yaml')
    recs = []
    for d in (ROOT / 'data/raw/exa').glob('*'):
        for p in d.glob('*.json'):
            data = json.loads(p.read_text(encoding='utf-8'))
            q = data.get('query', '')
            out = (data.get('stdout') or '')[:4000]
            urls = []
            for m in re.finditer(r'https?://[^\s\]}")]+', out):
                u = m.group(0).rstrip('.,')
                if u not in urls:
                    urls.append(u)
            if not urls and data.get('returncode') == 0 and out.strip():
                urls = [f'exa-query://{slug(q)}']
            for u in urls[:10]:
                text = q + ' ' + out[:500]
                summary = ('Exa result for: ' + q)[:240]
                recs.append({
                    'id': slug('exa-' + u),
                    'name': q[:90],
                    'url': u,
                    'repo': None,
                    'source_type': 'exa',
                    'category': categories_for(text),
                    'target_tools': target_tools_for(text, tools),
                    'concepts': [],
                    'summary': summary,
                    'i18n': i18n_fields(q[:90], summary),
                    'why_it_matters': 'Semantic web discovery result for AI coding ecosystem tracking.',
                    'status': 'unknown',
                    'license': None,
                    'stars': None,
                    'forks': None,
                    'last_updated': None,
                    'first_seen': None,
                    'last_seen': None,
                    'maturity': 'unknown',
                    'integration_surfaces': [],
                    'languages': [],
                    'tags': [],
                    'score': {'ecosystem_value': 3, 'activity': 1, 'adoption': 1, 'practicality': 2, 'novelty': 2, 'confidence': 3},
                    'notes': out[:1000],
                    'review_state': 'auto-indexed',
                })
    return recs

def from_web():
    tools = load_jsonish('data/seed-tools.yaml')
    recs = []
    for d in (ROOT / 'data/raw/web').glob('*'):
        for p in d.glob('*.json'):
            data = json.loads(p.read_text(encoding='utf-8'))
            q = data.get('query', '')
            for it in data.get('results', [])[:20]:
                u = it.get('url')
                title = it.get('title') or q
                snip = it.get('snippet') or ''
                if not u:
                    continue
                text = f'{title} {snip} {q}'
                summary = snip[:240] or ('Fallback web result for: ' + q)[:240]
                recs.append({
                    'id': slug('web-' + u),
                    'name': title[:120],
                    'url': u,
                    'repo': None,
                    'source_type': 'fallback-web',
                    'category': categories_for(text),
                    'target_tools': target_tools_for(text, tools),
                    'concepts': [],
                    'summary': summary,
                    'i18n': i18n_fields(title[:120], summary),
                    'why_it_matters': 'Fallback web discovery result because Exa/mcporter was unavailable in this environment.',
                    'status': 'unknown',
                    'license': None,
                    'stars': None,
                    'forks': None,
                    'last_updated': None,
                    'first_seen': None,
                    'last_seen': None,
                    'maturity': 'unknown',
                    'integration_surfaces': [],
                    'languages': [],
                    'tags': ['fallback-not-exa'],
                    'score': {'ecosystem_value': 2, 'activity': 1, 'adoption': 1, 'practicality': 2, 'novelty': 2, 'confidence': 2},
                    'notes': q,
                    'review_state': 'auto-indexed',
                })
    return recs

def main():
    ap = argparse.ArgumentParser(description='Normalize raw collector outputs into data/projects.yaml')
    ap.add_argument('--source', choices=['all', 'github', 'exa', 'web'], default='all')
    args = ap.parse_args()
    existing = load_jsonish('data/projects.yaml') if (ROOT / 'data/projects.yaml').exists() else []
    recs = []
    if args.source in ('all', 'github'):
        recs += from_github()
    if args.source in ('all', 'exa'):
        recs += from_exa()
    if args.source in ('all', 'web'):
        recs += from_web()
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