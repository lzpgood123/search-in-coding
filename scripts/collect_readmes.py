#!/usr/bin/env python3
"""Batch-collect full README files for track-level projects.

Writes complete README to data/readmes/{project_id}.md and marks
has_readme_full on the project. Updates readme_preview to first 2000 chars.

Usage:
    python3 scripts/collect_readmes.py --priority track
    python3 scripts/collect_readmes.py --priority track --dry-run
    python3 scripts/collect_readmes.py --priority track --limit 50
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_jsonish, save_jsonish, run

README_PREVIEW_LIMIT = 2000
DEFAULT_SLEEP = 0.25  # per worker; 4 workers ≈ 16 req/s peak but we keep low
DEFAULT_WORKERS = 4
SAVE_EVERY = 100


def select_projects(projects, priority='track', force=False):
    """Select projects that still need full README collection."""
    selected = []
    for p in projects or []:
        if priority and p.get('tracking_priority') != priority:
            continue
        repo = p.get('repo') or ''
        if not repo or '/' not in str(repo):
            continue
        pid = p.get('id') or ''
        readme_path = ROOT / 'data' / 'readmes' / f'{pid}.md' if pid else None
        if not force:
            # checkpoint: flag true → skip (resume)
            if p.get('has_readme_full') is True:
                continue
            # already attempted (404/empty/error) → skip unless --force
            if p.get('has_readme_full') is False and p.get('readme_checked') is True:
                # only skip if we already tried in this collect pass
                # (readme_checked alone is historical enrich; require explicit collect marker)
                if p.get('readme_full_checked') is True:
                    continue
            # file already on disk → skip re-fetch
            if readme_path and readme_path.exists() and readme_path.stat().st_size > 0:
                continue
        selected.append(p)
    return selected


def fetch_readme_content(repo: str) -> tuple[str, str]:
    """Fetch README via gh api. Returns (text, note)."""
    cmd = f'gh api repos/{repo}/readme --jq .content'
    try:
        r = run(cmd, timeout=60)
    except (subprocess.TimeoutExpired, OSError, subprocess.SubprocessError):
        return '', 'timeout'
    if r.returncode != 0 or not (r.stdout or '').strip():
        err = (r.stderr or '')[:200]
        if '404' in err or 'Not Found' in err:
            return '', '404'
        return '', 'error'
    try:
        raw = base64.b64decode((r.stdout or '').strip()).decode('utf-8', errors='replace')
    except Exception:
        return '', 'decode-error'
    if not raw or len(raw.strip()) < 5:
        return '', 'empty'
    return raw, 'ok'


def fetch_and_store_readme(project: dict, sleep_s: float = 0.0) -> tuple[str, bool, str]:
    """Fetch README for one project, write file + update fields.

    Returns (project_id, changed, note).
    """
    repo = project.get('repo') or ''
    pid = project.get('id') or ''
    if not repo or not pid:
        return pid or '', False, 'no-repo-or-id'

    if sleep_s > 0:
        time.sleep(sleep_s)

    text, note = fetch_readme_content(repo)
    project['readme_full_checked'] = True
    if note != 'ok' or not text:
        project['has_readme_full'] = False
        return pid, True, note

    readme_path = ROOT / 'data' / 'readmes' / f'{pid}.md'
    readme_path.parent.mkdir(parents=True, exist_ok=True)
    readme_path.write_text(text, encoding='utf-8')
    project['has_readme_full'] = True
    project['readme_preview'] = text[:README_PREVIEW_LIMIT]
    project['readme_checked'] = True
    return pid, True, 'ok'


def main():
    ap = argparse.ArgumentParser(description='Collect full READMEs into data/readmes/')
    ap.add_argument('--priority', default='track', help='tracking_priority filter (default: track)')
    ap.add_argument('--limit', type=int, default=0, help='Max projects to process (0=all)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true', help='Re-fetch even if has_readme_full')
    ap.add_argument('--sleep', type=float, default=DEFAULT_SLEEP, help='Seconds between API calls per worker')
    ap.add_argument('--workers', type=int, default=DEFAULT_WORKERS, help='Concurrent gh api workers')
    args = ap.parse_args()

    projects = load_jsonish('data/projects.yaml')
    if not isinstance(projects, list):
        print('ERROR: projects.yaml not a list')
        sys.exit(1)

    selected = select_projects(projects, priority=args.priority, force=args.force)
    if args.limit and args.limit > 0:
        selected = selected[: args.limit]

    print(json.dumps({
        'total_projects': len(projects),
        'selected': len(selected),
        'priority': args.priority,
        'workers': args.workers,
        'dry_run': args.dry_run,
    }, ensure_ascii=False), flush=True)

    if args.dry_run or not selected:
        return

    by_id = {p.get('id'): p for p in projects if p.get('id')}
    # work on live dicts from projects list
    work = [by_id.get(p.get('id'), p) for p in selected]

    ok = fail = done = 0
    lock = Lock()
    workers = max(1, int(args.workers or 1))

    def _one(proj):
        return fetch_and_store_readme(proj, sleep_s=args.sleep)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_one, p): p for p in work}
        for fut in as_completed(futures):
            pid, changed, note = fut.result()
            with lock:
                done += 1
                if note == 'ok':
                    ok += 1
                else:
                    fail += 1
                    if note not in ('404', 'empty'):
                        print(f'  skip {pid}: {note}', flush=True)
                    elif fail <= 20 or fail % 50 == 0:
                        print(f'  skip {pid}: {note}', flush=True)

                if done % 100 == 0 or done == len(work):
                    print(f'progress {done}/{len(work)} ok={ok} fail={fail}', flush=True)

                if done % SAVE_EVERY == 0:
                    save_jsonish('data/projects.yaml', projects)
                    print(f'  checkpoint saved at {done}', flush=True)

    save_jsonish('data/projects.yaml', projects)
    print(json.dumps({
        'done': True, 'ok': ok, 'fail': fail, 'selected': len(selected),
    }, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
