#!/usr/bin/env python3
"""Refresh GitHub metadata for tracked projects in batches.

Each run refreshes a batch of track-priority projects by calling
`gh repo view` to get latest stars/forks/topics/last_updated.
Designed to run daily as part of the collect pipeline.

Usage:
    python3 scripts/refresh_track_projects.py                # default batch 1000
    python3 scripts/refresh_track_projects.py --batch-size 500
    python3 scripts/refresh_track_projects.py --dry-run      # show what would be refreshed
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_jsonish, save_jsonish, today


def select_projects_to_refresh(projects, batch_size=1000):
    """Select track-priority projects to refresh, sorted by oldest last_seen first.

    Skips:
    - official-seed projects (managed separately)
    - non-track projects
    - projects without a repo field
    """
    candidates = []
    for p in projects:
        if p.get('tracking_priority') != 'track':
            continue
        if p.get('source_type') == 'official-seed':
            continue
        if not p.get('repo'):
            continue
        candidates.append(p)

    # Sort by last_seen ascending (oldest first); None sorts first
    candidates.sort(key=lambda p: p.get('last_seen') or '0000-01-01')
    return candidates[:batch_size]


def fetch_repo_data(full_name, timeout=30):
    """Fetch latest repo metadata via gh repo view."""
    fields = 'nameWithOwner,description,url,stargazerCount,forkCount,licenseInfo,repositoryTopics,primaryLanguage,pushedAt,createdAt,updatedAt,isArchived,latestRelease'
    cmd = f'gh repo view {full_name} --json {fields}'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout or '{}')
    except json.JSONDecodeError:
        return None


def merge_refreshed_data(existing, refreshed):
    """Merge refreshed GitHub data into existing project record.

    Preserves LLM fields: quality_score, quality_detail, tracking_priority,
    last_analyzed, benchmark_ref, llm_summary.
    """
    out = dict(existing)  # shallow copy

    if not refreshed:
        return out

    # Refresh quantifiable fields
    out['stars'] = refreshed.get('stargazerCount', existing.get('stars'))
    out['forks'] = refreshed.get('forkCount', existing.get('forks'))
    out['last_updated'] = refreshed.get('updatedAt') or refreshed.get('pushedAt') or existing.get('last_updated')

    if refreshed.get('isArchived'):
        out['status'] = 'archived'

    # Refresh topics
    topics_raw = refreshed.get('repositoryTopics') or []
    if isinstance(topics_raw, list):
        topics = [t.get('name') if isinstance(t, dict) else t for t in topics_raw]
        out['topics'] = [t for t in topics if t]

    # Refresh license
    license_info = refreshed.get('licenseInfo')
    if isinstance(license_info, dict):
        license_id = license_info.get('spdxId') or license_info.get('key')
        if license_id and license_id not in ('NOASSERTION', None, '', 'none'):
            out['license'] = license_id

    # Refresh languages
    primary_lang = refreshed.get('primaryLanguage')
    if isinstance(primary_lang, dict) and primary_lang.get('name'):
        out['languages'] = [primary_lang['name']]

    # Summary: only fill if existing is empty
    if not (out.get('summary') or '').strip():
        desc = refreshed.get('description') or ''
        if desc:
            out['summary'] = desc[:240]

    # Update last_seen
    out['last_seen'] = today()

    return out


def main():
    ap = argparse.ArgumentParser(description='Refresh track projects GitHub metadata in batches')
    ap.add_argument('--batch-size', type=int, default=1000, help='Number of projects to refresh per run')
    ap.add_argument('--dry-run', action='store_true', help='Show what would be refreshed without making changes')
    args = ap.parse_args()

    projects = load_jsonish('data/projects.yaml')
    to_refresh = select_projects_to_refresh(projects, batch_size=args.batch_size)

    print(f'Track projects to refresh: {len(to_refresh)} (batch_size={args.batch_size})')

    if args.dry_run:
        for p in to_refresh[:10]:
            print(f'  {p.get("repo")} (last_seen={p.get("last_seen")})')
        if len(to_refresh) > 10:
            print(f'  ... and {len(to_refresh) - 10} more')
        return

    if not to_refresh:
        print('No projects to refresh')
        return

    # Build lookup by id
    by_id = {p.get('id'): p for p in projects}

    success = 0
    failed = 0
    for p in to_refresh:
        repo = p.get('repo')
        pid = p.get('id')
        try:
            refreshed = fetch_repo_data(repo)
            if refreshed:
                by_id[pid] = merge_refreshed_data(p, refreshed)
                success += 1
            else:
                failed += 1
                print(f'  FAILED: {repo}')
        except (subprocess.TimeoutExpired, Exception) as e:
            failed += 1
            print(f'  ERROR: {repo}: {e}')

    # Save updated projects
    save_jsonish('data/projects.yaml', list(by_id.values()))

    print(json.dumps({
        'refreshed': success,
        'failed': failed,
        'total_track': sum(1 for p in projects if p.get('tracking_priority') == 'track'),
        'batch_size': args.batch_size,
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
