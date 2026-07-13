#!/usr/bin/env python3
"""Auto-finalize Search in Coding data with new 100-point schema."""
import argparse
import datetime
import json
from common import load_jsonish, save_jsonish

DEFAULT_RANKING = {
    'curated_min': 40,
    'rejected_min': 10,
    'github_min': 30,
    'try_now_min_score': 25,
    'watch_min_score': 15,
    'reject_max_score': 10,
}
HIGH_VALUE_TYPES = {
    'mcp-server', 'skills', 'rules', 'agent-framework',
}

def load_ranking():
    cfg = load_jsonish('config/scoring-v2.yaml')
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
                'resource_type': ['cli-tool'],
                'target_tools': [t['id']],
                'summary': summary,
                'i18n': {'zh': {'name': name, 'summary': summary}, 'en': {'name': name, 'summary': summary}},
                'status': 'active',
                'license': None,
                'stars': None,
                'forks': None,
                'last_updated': now,
                'first_seen': now,
                'last_seen': now,
                'maturity': 'unknown',
                'languages': [],
                'tags': ['target-tool', 'official-seed'],
                'review_state': 'auto-curated',
                'quantifiable_score': 0,
                'quality_score': 0,
                'total_score': 0,
                'score_detail': {},
                'tracking_priority': 'track',
                'last_analyzed': None,
                'benchmark_ref': None,
            }
    return list(by_id.values())

def project_score(p):
    return p.get('total_score', 0)

def auto_level(p, ranking):
    score = project_score(p)
    rtypes = set(p.get('resource_type') or [])
    if score >= ranking['try_now_min_score'] and rtypes & HIGH_VALUE_TYPES:
        return 'try-now'
    if score >= ranking['watch_min_score']:
        return 'watch'
    return 'reference'

def is_weak_record(p, ranking):
    return (
        project_score(p) <= ranking['reject_max_score'] or
        p.get('tracking_priority') == 'reject' or
        p.get('status') == 'archived'
    )

def auto_note(p):
    score = project_score(p)
    source = p.get('source_type')
    rtypes = ', '.join(p.get('resource_type') or [])
    return f'Auto-selected by scoring rules: source={source}, score={score}, resource_types={rtypes}.'

def main():
    ap = argparse.ArgumentParser(description='Auto-generate curated/rejected datasets from scoring rules')
    ap.add_argument('--curated-min', type=int, default=None)
    ap.add_argument('--rejected-min', type=int, default=None)
    ap.parse_known_args()
    args, _ = ap.parse_known_args()

    ranking = load_ranking()
    if args.curated_min is not None:
        ranking['curated_min'] = args.curated_min
    if args.rejected_min is not None:
        ranking['rejected_min'] = args.rejected_min

    projects = ensure_official_seed(load_jsonish('data/projects.yaml'), load_jsonish('data/seed-tools.yaml'))

    # Normalize review states
    for p in projects:
        if p.get('source_type') == 'official-seed':
            p['review_state'] = 'auto-curated'
            p['tracking_priority'] = p.get('tracking_priority') or 'track'
        elif p.get('review_state') in ('reviewed', 'auto-reviewed', 'unreviewed'):
            p['review_state'] = 'auto-indexed'
        elif p.get('review_state') == 'rejected':
            p['review_state'] = 'auto-rejected'

    # Candidates: non-official, non-reject
    all_candidates = [p for p in projects if p.get('source_type') != 'official-seed' and p.get('tracking_priority') != 'reject']
    candidates = sorted(all_candidates, key=lambda p: project_score(p), reverse=True)
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

    # Phase 1: GitHub high-score
    for p in non_weak:
        if p.get('source_type') == 'github' and len([x for x in curated if x.get('source_type') == 'github']) < ranking['github_min']:
            add_curated(p)

    # Phase 2: Ensure each tool has at least 1 curated
    tools = [t['id'] for t in load_jsonish('data/seed-tools.yaml')]
    for tid in tools:
        if any(tid in (p.get('target_tools') or []) for p in curated):
            continue
        for p in candidates:
            if tid in (p.get('target_tools') or []):
                add_curated(p)
                break

    # Phase 3: Fill to curated_min
    for p in candidates:
        if len(curated) >= ranking['curated_min']:
            break
        add_curated(p)

    # Rejected: lowest scoring non-official, non-curated
    curated_ids = {p['id'] for p in curated}
    rejected = []
    for p in sorted(projects, key=lambda p: project_score(p)):
        if len(rejected) >= ranking['rejected_min']:
            break
        if p.get('source_type') == 'official-seed' or p.get('id') in curated_ids:
            continue
        if is_weak_record(p, ranking):
            q = dict(p)
            q['review_state'] = 'auto-rejected'
            q['tracking_priority'] = 'reject'
            q['rejection_reason'] = f'Auto-rejected: low score ({project_score(p)}), archived, or weak relevance.'
            rejected.append(q)

    rejected_ids = {p['id'] for p in rejected}
    for p in projects:
        if p['id'] in curated_ids:
            p['review_state'] = 'auto-curated'
        elif p['id'] in rejected_ids:
            p['review_state'] = 'auto-rejected'
            p['tracking_priority'] = 'reject'
        elif p.get('source_type') != 'official-seed':
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
    }, ensure_ascii=False))

if __name__ == '__main__':
    main()
