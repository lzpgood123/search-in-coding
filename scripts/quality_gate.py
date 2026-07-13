#!/usr/bin/env python3
import argparse, json, collections, sys
from common import ROOT, load_jsonish
ALLOWED_REVIEW_STATES = {'auto-indexed', 'auto-curated', 'auto-rejected'}
ALLOWED_TRACKING_PRIORITIES = {'pending', 'track', 'index', 'reject'}

def has_i18n(p):
    i18n = p.get('i18n') or {}
    return 'zh' in i18n and 'en' in i18n and isinstance(i18n.get('zh'), dict) and isinstance(i18n.get('en'), dict)

def main():
    ap = argparse.ArgumentParser(description='Final delivery quality gate')
    ap.add_argument('--allow-current-mvp', action='store_true')
    ap.parse_known_args()
    args, _ = ap.parse_known_args()
    errors = []
    def fail(msg): errors.append(msg)

    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    rejected = load_jsonish('data/rejected-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')

    if len(projects) < 100: fail(f'normalized records <100: {len(projects)}')
    if not args.allow_current_mvp and len(curated) < 20: fail(f'curated records <20: {len(curated)}')
    if not args.allow_current_mvp and len(rejected) < 5: fail(f'rejected records <5: {len(rejected)}')

    required = ['id','name','url','source_type','resource_type','target_tools','summary','review_state','total_score','tracking_priority','quantifiable_score','quality_score']
    for i, p in enumerate(projects):
        miss = [k for k in required if k not in p or p.get(k) in (None,'')]
        if miss:
            fail(f'project {i} {p.get("id")} missing {miss}'); break
        if not has_i18n(p):
            fail(f'project {i} {p.get("id")} missing i18n.zh/en'); break
        if p.get('review_state') not in ALLOWED_REVIEW_STATES:
            fail(f'project {i} {p.get("id")} has unknown review_state {p.get("review_state")}'); break
        if p.get('tracking_priority') not in ALLOWED_TRACKING_PRIORITIES:
            fail(f'project {i} {p.get("id")} has unknown tracking_priority {p.get("tracking_priority")}'); break

    for dataset_name, rows, expected_state in [
        ('curated', curated, 'auto-curated'),
        ('rejected', rejected, 'auto-rejected'),
    ]:
        for i, p in enumerate(rows):
            if not has_i18n(p):
                fail(f'{dataset_name} {i} {p.get("id")} missing i18n.zh/en'); break
            if p.get('review_state') != expected_state:
                fail(f'{dataset_name} {i} {p.get("id")} review_state != {expected_state}: {p.get("review_state")}'); break

    tc = collections.Counter(t for p in projects for t in p.get('target_tools', []))
    for t in tools:
        if tc[t['id']] < 1: fail(f'tool coverage <1 for {t["id"]}: {tc[t["id"]]}')

    # Official tools should have tracking_priority=track and source_type=official-seed
    official_in_ecosystem = [p for p in projects if p.get('source_type') == 'official-seed' and p.get('tracking_priority') != 'track']
    if official_in_ecosystem: fail('official tools with wrong tracking_priority')

    github_count = sum(1 for p in projects if p.get('source_type') == 'github')
    if github_count < 50: fail(f'github records <50: {github_count}')

    if not (ROOT/'config/scoring-v2.yaml').exists(): fail('missing config/scoring-v2.yaml')

    if not args.allow_current_mvp:
        for f in ['projects.json','curated-projects.json','tools.json','concepts.json','metrics.json','i18n.json']:
            if not (ROOT/'site/data'/f).exists(): fail(f'missing site data {f}')

    result = {'status': 'PASS' if not errors else 'FAIL', 'projects': len(projects), 'curated': len(curated), 'rejected': len(rejected), 'github_count': github_count, 'tool_coverage': dict(tc), 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors: sys.exit(1)

if __name__ == '__main__': main()
