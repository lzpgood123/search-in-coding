#!/usr/bin/env python3
import argparse, json, collections, shutil, re, hashlib
from common import ROOT, load_jsonish

ZH_HINTS = re.compile(r'[\u4e00-\u9fff]')

RESOURCE_TYPE_LABELS = {
    'mcp-server': {'zh': 'MCP Server', 'en': 'MCP Server'},
    'skills': {'zh': 'Skills', 'en': 'Skills'},
    'rules': {'zh': 'Rules', 'en': 'Rules'},
    'agent-framework': {'zh': 'Agent 框架', 'en': 'Agent Framework'},
    'cli-tool': {'zh': 'CLI 工具', 'en': 'CLI Tool'},
    'tutorial': {'zh': '教程', 'en': 'Tutorial'},
}

# Fields for slim JSON (table display only)
SLIM_FIELDS = [
    'id', 'name', 'url', 'source_type', 'resource_type', 'target_tools',
    'summary', 'i18n', 'stars', 'forks', 'total_score', 'quantifiable_score',
    'quality_score', 'tracking_priority', 'last_updated', 'first_seen', 'last_seen',
    'license', 'languages', 'review_state',
]

# Fields for detail JSON (lazy-loaded)
DETAIL_FIELDS = SLIM_FIELDS + [
    'score_detail', 'llm_summary', 'benchmark_ref', 'last_analyzed',
    'repo', 'tags', 'maturity', 'status',
    'readme_preview', 'topics',
]

SITE_URL = 'https://coding.lzpgood.online/'


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
        'benchmark_ref': p.get('benchmark_ref'),
        'maturity': p.get('maturity'),
        'status': p.get('status'),
        'readme_preview': p.get('readme_preview'),
        'topics': p.get('topics', []),
    }


def enrich_tool(t):
    q = dict(t)
    q['i18n'] = q.get('i18n') or {'zh': {'name': q.get('name','')}, 'en': {'name': q.get('name','')}}
    return q


def slim_project(p):
    """Return a slim version of project for table display."""
    return {k: p.get(k) for k in SLIM_FIELDS if k in p}


def detail_project(p):
    """Return full detail version for lazy-loaded detail panel."""
    return {k: p.get(k) for k in DETAIL_FIELDS if k in p}


def hash_filename(filename, content):
    """Generate a content-hashed filename (e.g., app.a3f2b1.js)."""
    h = hashlib.md5(content.encode('utf-8')).hexdigest()[:6]
    parts = filename.rsplit('.', 1)
    if len(parts) == 2:
        return f'{parts[0]}.{h}.{parts[1]}'
    return f'{parts[0]}.{h}'


def generate_sitemap(projects):
    """Generate sitemap.xml content."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    lines.append(f'  <url><loc>{SITE_URL}</loc><changefreq>daily</changefreq><priority>1.0</priority></url>')
    lines.append('</urlset>')
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description='Build static site with slim/detail JSON, sitemap, hashed assets')
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

    # Write slim projects JSON (for table display)
    write_json('projects.json', [slim_project(p) for p in projects])
    write_json('curated-projects.json', [slim_project(p) for p in curated])
    write_json('rejected-projects.json', [slim_project(p) for p in rejected])

    # Write detail JSON (lazy-loaded by detail panel)
    write_json('projects-detail.json', [detail_project(p) for p in projects])

    # Write other data
    write_json('tools.json', tools)
    write_json('concepts.json', concepts)
    write_json('metrics.json', metrics)
    write_json('i18n.json', i18n)

    # Copy reports
    copy_reports()

    # Generate sitemap
    sitemap_path = ROOT / 'site' / 'sitemap.xml'
    sitemap_path.write_text(generate_sitemap(projects), encoding='utf-8')

    # Generate robots.txt (dogfood #27)
    robots_path = ROOT / 'site' / 'robots.txt'
    robots_path.write_text(
        'User-agent: *\nAllow: /\nSitemap: https://coding.lzpgood.online/sitemap.xml\n',
        encoding='utf-8'
    )

    # Hash JS/CSS filenames and update index.html references
    site_dir = ROOT / 'site'
    js_dir = site_dir / 'js'

    # Step 1: Restore index.html to reference original (non-hashed) filenames
    # This handles the case where build_site.py is run multiple times
    index_path = site_dir / 'index.html'
    index_html = index_path.read_text(encoding='utf-8')
    # Replace any hashed JS references back to original names (handles single or double hash)
    index_html = re.sub(r'js/([a-z0-9_-]+)(\.[a-f0-9]{6})+\.js', r'js/\1.js', index_html)
    # Replace any hashed CSS references back to original name
    index_html = re.sub(r'styles(\.[a-f0-9]{6})+\.css', r'styles.css', index_html)

    # Step 2: Clean up old hash files (pattern: name.hash.ext)
    for old_hashed in js_dir.glob('*.*.js'):
        old_hashed.unlink()
    for old_css in site_dir.glob('styles.*.css'):
        if old_css.name != 'styles.css':
            old_css.unlink()

    # Step 3: Only process original source files (not hash files)
    source_js_files = [f for f in sorted(js_dir.glob('*.js')) if not re.match(r'^[a-z]+\.[a-f0-9]{6}\.js$', f.name)]

    # Step 4: Hash and copy JS files, update index.html references
    for js_file in source_js_files:
        content = js_file.read_text(encoding='utf-8')
        hashed = hash_filename(js_file.name, content)
        hashed_path = js_dir / hashed
        hashed_path.write_text(content, encoding='utf-8')
        index_html = index_html.replace(f'js/{js_file.name}', f'js/{hashed}')

    # Step 5: Hash and copy CSS
    css_content = (site_dir / 'styles.css').read_text(encoding='utf-8')
    css_hashed = hash_filename('styles.css', css_content)
    (site_dir / css_hashed).write_text(css_content, encoding='utf-8')
    index_html = index_html.replace('styles.css', css_hashed)

    index_path.write_text(index_html, encoding='utf-8')

    print(json.dumps({
        'site_data': 'site/data',
        'reports': 'site/reports',
        'projects': len(projects),
        'slim_projects': len([slim_project(p) for p in projects]),
        'detail_projects': len([detail_project(p) for p in projects]),
        'curated': len(curated),
        'tools': len(tools),
        'sitemap': True,
        'hashed_assets': True,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
