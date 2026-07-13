#!/usr/bin/env python3
import argparse, json, collections, shutil, re
from common import ROOT, load_jsonish

ZH_HINTS = re.compile(r'[\u4e00-\u9fff]')

RESOURCE_TYPE_LABELS = {
    'mcp-server': {'zh': 'MCP 服务器', 'en': 'MCP Server'},
    'skills': {'zh': 'Skills / Prompts', 'en': 'Skills / Prompts'},
    'rules': {'zh': '规则 / 指令', 'en': 'Rules / Instructions'},
    'agent-framework': {'zh': 'Agent 框架', 'en': 'Agent Framework'},
    'cli-tool': {'zh': 'CLI 工具', 'en': 'CLI Tool'},
    'tutorial': {'zh': '教程 / 案例', 'en': 'Tutorial / Case Study'},
}

def write_json(name, data):
    p = ROOT / 'site/data' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def copy_reports():
    src = ROOT / 'docs/reports'
    dst = ROOT / 'site/reports'
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob('*.md'):
        old.unlink()
    for report in sorted(src.glob('*.md')):
        shutil.copy2(report, dst / report.name)

def bilingual_text(name, summary=''):
    name = name or ''
    summary = summary or ''
    has_zh = bool(ZH_HINTS.search(name + summary))
    return {
        'zh': {'name': name, 'summary': summary},
        'en': {'name': name, 'summary': summary if not has_zh else summary},
    }

def enrich_project(p):
    return {
        'id': p.get('id'),
        'name': p.get('name'),
        'url': p.get('url'),
        'repo': p.get('repo'),
        'source_type': p.get('source_type'),
        'resource_type': p.get('resource_type', []),
        'target_tools': p.get('target_tools', []),
        'summary': p.get('summary', ''),
        'i18n': p.get('i18n') or bilingual_text(p.get('name'), p.get('summary')),
        'stars': p.get('stars'),
        'forks': p.get('forks'),
        'last_updated': p.get('last_updated'),
        'first_seen': p.get('first_seen'),
        'last_seen': p.get('last_seen'),
        'languages': p.get('languages', []),
        'license': p.get('license'),
        'tags': p.get('tags', []),
        'review_state': p.get('review_state'),
        'tracking_priority': p.get('tracking_priority', 'pending'),
        'total_score': p.get('total_score', 0),
        'quantifiable_score': p.get('quantifiable_score', 0),
        'quality_score': p.get('quality_score', 0),
        'score_detail': p.get('score_detail', {}),
        'llm_summary': p.get('llm_summary'),
        'last_analyzed': p.get('last_analyzed'),
    }

def enrich_tool(t):
    q = dict(t)
    q['i18n'] = q.get('i18n') or {'zh': {'name': q.get('name','')}, 'en': {'name': q.get('name','')}}
    return q

def main():
    ap = argparse.ArgumentParser(description='Build bilingual static site data from project datasets')
    ap.parse_known_args()
    projects = [enrich_project(p) for p in load_jsonish('data/projects.yaml')]
    curated = [enrich_project(p) for p in load_jsonish('data/curated-projects.yaml')]
    rejected = [enrich_project(p) for p in load_jsonish('data/rejected-projects.yaml')]
    tools = [enrich_tool(t) for t in load_jsonish('data/seed-tools.yaml')]
    concepts = load_jsonish('data/concepts.yaml')
    official = [p for p in projects if p.get('source_type') == 'official-seed']
    ecosystem = [p for p in projects if p.get('tracking_priority') != 'reject' and p.get('source_type') != 'official-seed']
    metrics = {
        'projects': len(projects),
        'curated': len(curated),
        'rejected': len(rejected),
        'official_tools': len(official),
        'ecosystem_projects': len(ecosystem),
        'sources': dict(collections.Counter(p.get('source_type') for p in projects)),
        'tracking_priorities': dict(collections.Counter(p.get('tracking_priority') for p in projects)),
        'tool_coverage': dict(collections.Counter(t for p in projects for t in p.get('target_tools', []))),
        'resource_type_coverage': dict(collections.Counter(c for p in projects for c in p.get('resource_type', []))),
        'languages': ['zh', 'en'],
    }
    i18n = {'languages': ['zh', 'en'], 'default': 'zh', 'resource_types': RESOURCE_TYPE_LABELS}
    write_json('projects.json', projects)
    write_json('curated-projects.json', curated)
    write_json('rejected-projects.json', rejected)
    write_json('tools.json', tools)
    write_json('concepts.json', concepts)
    write_json('metrics.json', metrics)
    write_json('i18n.json', i18n)
    copy_reports()
    print(json.dumps({'site_data':'site/data','reports':'site/reports','projects':len(projects),'curated':len(curated),'tools':len(tools),'concepts':len(concepts),'languages':['zh','en']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
