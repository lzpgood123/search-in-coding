#!/usr/bin/env python3
import argparse, json, collections, sys
from common import ROOT, load_jsonish, normalize_project_fields
ALLOWED_REVIEW_STATES = {'auto-indexed', 'auto-curated', 'auto-rejected'}
OBSOLETE_REVIEW_STATES = {'reviewed', 'unreviewed', 'rejected', 'auto-reviewed'}

def has_i18n(p):
    i18n = p.get('i18n') or {}
    return 'zh' in i18n and 'en' in i18n and isinstance(i18n.get('zh'), dict) and isinstance(i18n.get('en'), dict)

def main():
    ap = argparse.ArgumentParser(description='Final delivery quality gate')
    ap.add_argument('--allow-current-mvp', action='store_true')
    args = ap.parse_args()
    errors = []
    def fail(msg): errors.append(msg)

    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    rejected = load_jsonish('data/rejected-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')

    if len(projects) < 150: fail(f'normalized records <150: {len(projects)}')
    if not args.allow_current_mvp and len(curated) < 50: fail(f'curated records <50: {len(curated)}')
    if not args.allow_current_mvp and len(rejected) < 20: fail(f'rejected records <20: {len(rejected)}')

    required = ['id','name','url','source_type','category','target_tools','summary','review_state','record_kind','source_quality','ranking_scope']
    for i, p in enumerate(projects):
        normalize_project_fields(p)
        miss = [k for k in required if k not in p or p.get(k) in (None,'')]
        if miss:
            fail(f'project {i} {p.get("id")} missing {miss}'); break
        if not has_i18n(p):
            fail(f'project {i} {p.get("id")} missing i18n.zh/en'); break
        if p.get('review_state') in OBSOLETE_REVIEW_STATES:
            fail(f'project {i} {p.get("id")} has obsolete review_state {p.get("review_state")}'); break
        if p.get('review_state') not in ALLOWED_REVIEW_STATES:
            fail(f'project {i} {p.get("id")} has unknown review_state {p.get("review_state")}'); break
        if p.get('source_type') == 'fallback-web':
            if p.get('source_quality') != 'fallback': fail(f'fallback-web not fallback: {p.get("id")}'); break
            if 'fallback-not-exa' not in (p.get('tags') or []): fail(f'fallback-web missing fallback-not-exa: {p.get("id")}'); break

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
        if tc[t['id']] < 10: fail(f'tool coverage <10 for {t["id"]}: {tc[t["id"]]}')

    bad = [p for p in projects if p.get('record_kind') == 'official-tool' and p.get('ranking_scope') == 'ecosystem']
    if bad: fail('official tools appear in ecosystem ranking')

    github_verified = sum(1 for p in projects if p.get('source_type') == 'github' and p.get('source_quality') == 'verified')
    non_github = sum(1 for p in projects if p.get('source_type') != 'github')
    if github_verified < 30: fail(f'github verified records <30: {github_verified}')
    if non_github < 30: fail(f'non-github records <30: {non_github}')

    if not (ROOT/'config/scoring.yaml').exists(): fail('missing config/scoring.yaml')

    if not args.allow_current_mvp:
        for f in ['final-delivery-report.md','curated-top-projects.md','tool-ecosystem-comparison.md','trends-and-opportunities.md','source-quality-audit.md','exa-status-and-fallback.md','next-90-days-roadmap.md']:
            if not (ROOT/'docs/reports'/f).exists(): fail(f'missing report {f}')
        for f in ['projects.json','curated-projects.json','tools.json','concepts.json','metrics.json','i18n.json']:
            if not (ROOT/'site/data'/f).exists(): fail(f'missing site data {f}')
        for f in ['final-delivery-report.md','curated-top-projects.md','source-quality-audit.md']:
            if not (ROOT/'site/reports'/f).exists(): fail(f'missing published site report {f}')
        html = (ROOT/'site/index.html').read_text(encoding='utf-8')
        if '../docs/' in html: fail('site/index.html links outside Pages artifact')

    result = {'status': 'PASS' if not errors else 'FAIL', 'projects': len(projects), 'curated': len(curated), 'rejected': len(rejected), 'github_verified': github_verified, 'non_github': non_github, 'tool_coverage': dict(tc), 'errors': errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors: sys.exit(1)

if __name__ == '__main__': main()