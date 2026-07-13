#!/usr/bin/env python3
"""Migrate data from old schema to new 100-point schema.

Removes Exa/fallback-web records, strips old score fields,
adds new fields (resource_type, quantifiable_score, tracking_priority, etc.).
"""
import argparse
import json
import datetime
from pathlib import Path

# Category to resource_type mapping
CATEGORY_TO_RESOURCE_TYPE = {
    'mcp-acp-a2a': 'mcp-server',
    'skills-prompts': 'skills',
    'rules-instructions': 'rules',
    'agent-harness': 'agent-framework',
    'terminal-agent': 'cli-tool',
    'tutorial-case-study': 'tutorial',
    'context-engineering': 'cli-tool',  # context tools are often CLI-based
    'testing-review-ci': 'agent-framework',  # testing/review agents are frameworks
    'benchmark-evaluation': 'tutorial',  # benchmarks are reference resources
    'ai-ide': 'cli-tool',  # IDE-related tools
    'official-tool': 'cli-tool',
    'persistent-agent': 'agent-framework',
}

# Fields to remove from old schema
OLD_FIELDS_TO_REMOVE = [
    'score', 'score_reason', 'category', 'record_kind', 'ranking_scope',
    'source_quality', 'concepts', 'integration_surfaces',
    'why_it_matters', 'notes', 'recommendation_level',
]


def should_remove_project(p):
    """Return True if project should be removed (Exa/fallback-web sources)."""
    return p.get('source_type') in ('fallback-web', 'exa')


def migrate_category_to_resource_type(p):
    """Convert old category list to new resource_type list."""
    old_cats = p.get('category', [])
    resource_types = []
    for cat in old_cats:
        rt = CATEGORY_TO_RESOURCE_TYPE.get(cat)
        if rt and rt not in resource_types:
            resource_types.append(rt)
    return resource_types if resource_types else ['tutorial']  # default fallback


def calc_quantifiable_score(p):
    """Calculate the 60-point quantifiable score.

    Stars (20) + Activity (15) + Adoption (10) + Maturity (15)
    """
    # Stars: 0-20
    stars = p.get('stars') or 0
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0
    if stars >= 50000:
        stars_score = 20
    elif stars >= 10000:
        stars_score = 16
    elif stars >= 5000:
        stars_score = 12
    elif stars >= 1000:
        stars_score = 8
    elif stars >= 100:
        stars_score = 4
    elif stars > 0:
        stars_score = 2
    else:
        stars_score = 0

    # Activity: 0-15, based on last_updated/pushed_at
    activity_score = 1  # default for unknown
    last_updated = p.get('last_updated') or p.get('last_seen') or ''
    if last_updated:
        try:
            # Parse ISO date, handle both date and datetime
            date_str = last_updated[:10]
            d = datetime.date.fromisoformat(date_str)
            now = datetime.date.today()
            days_ago = (now - d).days
            if days_ago <= 90:
                activity_score = 15
            elif days_ago <= 180:
                activity_score = 12
            elif days_ago <= 365:
                activity_score = 8
            elif days_ago <= 730:
                activity_score = 4
            else:
                activity_score = 1
        except (ValueError, TypeError):
            activity_score = 1

    # Adoption: 0-10, based on forks
    forks = p.get('forks') or 0
    try:
        forks = int(forks)
    except (TypeError, ValueError):
        forks = 0
    if forks >= 1000:
        adoption_score = 10
    elif forks >= 100:
        adoption_score = 7
    elif forks >= 10:
        adoption_score = 4
    elif forks > 0:
        adoption_score = 2
    else:
        adoption_score = 0

    # Maturity: 0-15
    maturity_score = 0
    if p.get('license'):
        maturity_score += 2
    if p.get('status') and p.get('status') not in ('unknown',):
        maturity_score += 3  # has explicit status (not just 'unknown')
    if p.get('languages'):
        maturity_score += 2
    # Check for release-like indicators
    if p.get('tags'):
        for tag in (p.get('tags') or []):
            if 'release' in tag.lower() or 'v1' in tag.lower() or 'stable' in tag.lower():
                maturity_score += 3
                break
    if p.get('maturity') and p.get('maturity') not in ('unknown',):
        maturity_score += 5
    maturity_score = min(maturity_score, 15)

    return stars_score + activity_score + adoption_score + maturity_score


def migrate_project(p):
    """Migrate a single project from old schema to new schema."""
    result = {}

    # Copy retained fields
    retained_fields = [
        'id', 'name', 'url', 'repo', 'source_type', 'summary', 'i18n',
        'status', 'stars', 'forks', 'last_updated', 'first_seen', 'last_seen',
        'maturity', 'languages', 'tags', 'target_tools', 'review_state', 'license',
    ]
    for field in retained_fields:
        if field in p:
            result[field] = p[field]

    # Migrate category -> resource_type
    result['resource_type'] = migrate_category_to_resource_type(p)

    # Calculate scores
    result['quantifiable_score'] = calc_quantifiable_score(p)
    result['quality_score'] = 0  # placeholder, filled by weekly LLM analysis
    result['total_score'] = result['quantifiable_score']  # = quantifiable + 0

    # Score detail
    result['score_detail'] = {
        'stars': min(20, result['quantifiable_score']),  # simplified for now
    }

    # New tracking fields
    result['tracking_priority'] = 'pending'
    if p.get('source_type') == 'official-seed':
        result['tracking_priority'] = 'track'
    result['last_analyzed'] = None
    result['benchmark_ref'] = None

    return result


def main():
    ap = argparse.ArgumentParser(description='Migrate data from old schema to new 100-point schema')
    ap.add_argument('--dry-run', action='store_true', help='Print stats without writing')
    ap.add_argument('--input', default='data/projects.yaml', help='Input file')
    ap.add_argument('--output', default='data/projects.yaml', help='Output file')
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    in_path = root / args.input
    if not in_path.exists():
        print(f'Error: {in_path} not found')
        return

    # Load (handle both JSON and YAML)
    import yaml
    with open(in_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    projects = data if isinstance(data, list) else data.get('projects', [])

    original_count = len(projects)

    # Separate keep vs remove
    keep = []
    removed = 0
    for p in projects:
        if should_remove_project(p):
            removed += 1
        else:
            keep.append(migrate_project(p))

    stats = {
        'original': original_count,
        'removed': removed,
        'kept': len(keep),
        'by_source': {},
    }
    for p in keep:
        src = p.get('source_type', 'unknown')
        stats['by_source'][src] = stats['by_source'].get(src, 0) + 1

    print(json.dumps(stats, ensure_ascii=False, indent=2))

    if not args.dry_run:
        out_path = in_path if args.output == args.input else root / args.output
        with open(out_path, 'w', encoding='utf-8') as f:
            yaml.dump(keep, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f'Written {len(keep)} projects to {out_path}')


if __name__ == '__main__':
    main()
