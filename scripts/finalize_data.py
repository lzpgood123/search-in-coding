#!/usr/bin/env python3
"""Auto-finalize Search in Coding data from scoring config."""
import argparse
import datetime
import json
from common import load_jsonish, save_jsonish, normalize_project_fields, total_score

DEFAULT_RANKING = {
    'curated_min': 60,
    'rejected_min': 25,
    'github_min': 40,
    'non_github_min': 15,
    'try_now_min_score': 17,
    'watch_min_score': 15,
    'reject_max_score': 9,
}
HIGH_VALUE_CATEGORIES = {
    'mcp-acp-a2a', 'skills-prompts', 'rules-instructions',
    'context-engineering', 'agent-harness', 'testing-review-ci',
}

def load_ranking():
    cfg = load_jsonish('config/scoring.yaml')
    ranking = dict(DEFAULT_RANKING)
    if isinstance(cfg, dict):
        ranking.update(cfg.get('ranking', {}))
    return ranking

def ensure_official_seed(projects, tools):
    by_id = {p.get('id'): p for p in projects}
    now = datetime.date.today().isoformat()
    for t in tools:
        rid = 'official-' + t['id']
        if rid not in by_id:
            name = t['name']
            summary = f'Official seed profile for {name}'
            by_id[rid] = {
                'id': rid,
                'name': name,
                'url': t.get('website') or t.get('docs') or (f"https://github.com/{t['repo']}" if t.get('repo') else ''),
                'repo': t.get('repo'),
                'source_type': 'official-seed',
                'category': ['official-tool', t.get('primary_type', 'official-tool')],
                'target_tools': [t['id']],
                'concepts': t.get('related_concepts', []),
                'summary': summary,
                'i18n': {'zh': {'name': name, 'summary': summary}, 'en': {'name': name, 'summary': summary}},
                'why_it_matters': 'Primary target tool for the Search in Coding tracker.',
                'status': 'active',
                'license': None,
                'stars': None,
                'forks': None,
                'last_updated': now,
                'first_seen': now,
                'last_seen': now,
                'maturity': 'unknown',
                'integration_surfaces': t.get('extension_points', []),
                'languages': [],
                'tags': ['target-tool', 'official-seed'],
                'score': {'ecosystem_value': 5, 'activity': 3, 'adoption': 3, 'practicality': 5, 'novelty': 3, 'confidence': 5},
                'notes': '',
                'review_state': 'auto-curated',
                'record_kind': 'official-tool',
                'source_quality': 'verified',
                'ranking_scope': 'official',
            }
    return list(by_id.values())

def project_score(p):
    return p.get('total_score', total_score(p))

def auto_level(p, ranking):
    score = project_score(p)
    source = p.get('source_type')
    cats = set(p.get('category') or [])
    if p.get('ranking_scope') == 'learning-resource':
        return 'reference'
    if source == 'github' and score >= ranking['try_now_min_score'] and cats & HIGH_VALUE_CATEGORIES:
        return 'try-now'
    if score >= ranking['watch_min_score']:
        return 'watch'
    if source == 'exa':
        return 'reference'
    return 'watch'

def is_weak_record(p, ranking):
    return (
        project_score(p) <= ranking['reject_max_score'] or
        p.get('source_type') == 'fallback-web' or
        p.get('target_tools') == ['general-ai-coding'] or
        p.get('source_quality') in ('fallback', 'unverified')
    )

def auto_note(p):
    score = project_score(p)
    source = p.get('source_type')
    cats = ', '.join(p.get('category') or [])
    return f'Auto-selected by scoring rules: source={source}, score={score}, categories={cats}.'

def main():
    ap = argparse.ArgumentParser(description='Auto-generate curated/rejected datasets from scoring rules')
    ap.add_argument('--curated-min', type=int, default=None)
    ap.add_argument('--rejected-min', type=int, default=None)
    args = ap.parse_args()

    ranking = load_ranking()
    if args.curated_min is not None:
        ranking['curated_min'] = args.curated_min
    if args.rejected_min is not None:
        ranking['rejected_min'] = args.rejected_min

    projects = ensure_official_seed(load_jsonish('data/projects.yaml'), load_jsonish('data/seed-tools.yaml'))
    for p in projects:
        normalize_project_fields(p)
        if p.get('record_kind') == 'official-tool':
            p['review_state'] = 'auto-curated'
            p['ranking_scope'] = 'official'
        elif p.get('review_state') in ('reviewed', 'auto-reviewed', 'unreviewed'):
            p['review_state'] = 'auto-indexed'
        elif p.get('review_state') == 'rejected':
            p['review_state'] = 'auto-rejected'

    all_candidates = [p for p in projects if p.get('record_kind') != 'official-tool' and p.get('ranking_scope') in ('ecosystem', 'learning-resource')]
    candidates = sorted(all_candidates, key=lambda p: p.get('total_score', total_score(p)), reverse=True)
    non_weak = [p for p in candidates if not is_weak_record(p, ranking)]

    curated = []
    seen = set()
    def add_curated(p):
        if p.get('id') in seen:
            return
        q = dict(p)
        q['review_state'] = 'auto-curated'
        q['recommendation_level'] = auto_level(q, ranking)
        q['curation_note'] = auto_note(q)
        curated.append(q)
        seen.add(q.get('id'))

    for p in non_weak:
        if p.get('source_type') == 'github' and p.get('ranking_scope') == 'ecosystem' and len([x for x in curated if x.get('source_type') == 'github']) < ranking['github_min']:
            add_curated(p)

    for p in non_weak:
        if p.get('source_type') != 'github' and len([x for x in curated if x.get('source_type') != 'github']) < ranking['non_github_min']:
            add_curated(p)

    tools = [t['id'] for t in load_jsonish('data/seed-tools.yaml')]
    for tid in tools:
        if any(tid in (p.get('target_tools') or []) for p in curated):
            continue
        for p in candidates:
            if tid in (p.get('target_tools') or []):
                add_curated(p)
                break

    for p in candidates:
        if len(curated) >= ranking['curated_min']:
            break
        add_curated(p)

    curated_ids = {p['id'] for p in curated}
    rejected = []
    for p in sorted(projects, key=lambda p: p.get('total_score', total_score(p))):
        if len(rejected) >= ranking['rejected_min']:
            break
        if p.get('record_kind') == 'official-tool' or p.get('id') in curated_ids:
            continue
        if is_weak_record(p, ranking):
            q = dict(p)
            q['review_state'] = 'auto-rejected'
            q['ranking_scope'] = 'excluded'
            q['rejection_reason'] = 'Auto-rejected by scoring/source-quality rules: low confidence, fallback/noisy, generic, duplicate, or weak direct relevance.'
            rejected.append(q)

    rejected_ids = {p['id'] for p in rejected}
    for p in projects:
        if p['id'] in curated_ids:
            p['review_state'] = 'auto-curated'
        elif p['id'] in rejected_ids:
            p['review_state'] = 'auto-rejected'
            p['ranking_scope'] = 'excluded'
        elif p.get('record_kind') != 'official-tool':
            p['review_state'] = 'auto-indexed'

    save_jsonish('data/projects.yaml', projects)
    save_jsonish('data/curated-projects.yaml', curated)
    save_jsonish('data/rejected-projects.yaml', rejected)
    print(json.dumps({
        'mode': 'auto-scored',
        'projects': len(projects),
        'curated': len(curated),
        'rejected': len(rejected),
        'curated_github': sum(1 for p in curated if p.get('source_type') == 'github'),
        'curated_non_github': sum(1 for p in curated if p.get('source_type') != 'github'),
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()