#!/usr/bin/env python3
"""Disk cleanup for old raw data, snapshots, and archives.

Cleans:
- data/raw/<source>/<date>/  — delete dirs older than --raw-days (default 30)
- data/snapshots/<date>.json — delete files older than --snapshot-days (default 90)
- data/raw-archive/<source>/<date>.tar.gz — delete archives older than --archive-days (default 90)

Does NOT clean: .venv/, cache/, site/

Usage:
    python3 scripts/cleanup_disk.py                # dry-run
    python3 scripts/cleanup_disk.py --apply        # execute deletion
    python3 scripts/cleanup_disk.py --apply --raw-days 15
"""
import argparse
import datetime
import json
import shutil
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT


def parse_date(name):
    """Parse a date string, return date object or None."""
    try:
        return datetime.date.fromisoformat(name)
    except (ValueError, TypeError):
        return None


def find_expired_dirs(parent, keep_days, today=None):
    """Find subdirectories named as dates older than keep_days."""
    if today is None:
        today = datetime.date.today()
    expired = []
    if not parent.exists():
        return expired
    for d in sorted(parent.iterdir()):
        if not d.is_dir():
            continue
        dt = parse_date(d.name)
        if dt is None:
            continue
        if (today - dt).days > keep_days:
            expired.append(d)
    return expired


def find_expired_files(parent, keep_days, today=None):
    """Find files named <date>.json older than keep_days."""
    if today is None:
        today = datetime.date.today()
    expired = []
    if not parent.exists():
        return expired
    for f in sorted(parent.iterdir()):
        if not f.is_file():
            continue
        # Extract date from filename (e.g., "2026-04-01.json" -> "2026-04-01")
        stem = f.stem
        dt = parse_date(stem)
        if dt is None:
            continue
        if (today - dt).days > keep_days:
            expired.append(f)
    return expired


def main():
    ap = argparse.ArgumentParser(description='Clean up old raw data, snapshots, and archives')
    ap.add_argument('--raw-days', type=int, default=30, help='Delete raw dirs older than N days (default 30)')
    ap.add_argument('--snapshot-days', type=int, default=90, help='Delete snapshot files older than N days (default 90)')
    ap.add_argument('--archive-days', type=int, default=90, help='Delete archived tar.gz older than N days (default 90)')
    ap.add_argument('--apply', action='store_true', help='Execute deletion (default: dry-run)')
    args = ap.parse_args()

    today = datetime.date.today()
    actions = []

    # 1. Clean data/raw/<source>/<date>/
    raw_root = ROOT / 'data' / 'raw'
    if raw_root.exists():
        for source in ['github', 'exa', 'web']:
            source_dir = raw_root / source
            expired = find_expired_dirs(source_dir, args.raw_days, today)
            for d in expired:
                actions.append({
                    'action': 'delete_dir',
                    'path': str(d),
                    'age_days': (today - parse_date(d.name)).days,
                })
                if args.apply:
                    shutil.rmtree(d)

    # 2. Clean data/snapshots/<date>.json
    snapshots_dir = ROOT / 'data' / 'snapshots'
    expired_snaps = find_expired_files(snapshots_dir, args.snapshot_days, today)
    for f in expired_snaps:
        actions.append({
            'action': 'delete_file',
            'path': str(f),
            'age_days': (today - parse_date(f.stem)).days,
        })
        if args.apply:
            f.unlink()

    # 3. Clean data/raw-archive/<source>/<date>.tar.gz
    archive_root = ROOT / 'data' / 'raw-archive'
    if archive_root.exists():
        for source in ['github', 'exa', 'web']:
            source_dir = archive_root / source
            if source_dir.exists():
                for f in sorted(source_dir.iterdir()):
                    if not f.is_file() or not f.name.endswith('.tar.gz'):
                        continue
                    # Extract date from filename (e.g., "2026-06-01.tar.gz")
                    stem = f.name.replace('.tar.gz', '')
                    dt = parse_date(stem)
                    if dt is None:
                        continue
                    if (today - dt).days > args.archive_days:
                        actions.append({
                            'action': 'delete_archive',
                            'path': str(f),
                            'age_days': (today - dt).days,
                        })
                        if args.apply:
                            f.unlink()

    # Summary
    total_size = 0
    for a in actions:
        p = Path(a['path'])
        if p.exists():
            if p.is_file():
                total_size += p.stat().st_size
            elif p.is_dir():
                for fp in p.rglob('*'):
                    if fp.is_file():
                        total_size += fp.stat().st_size

    print(json.dumps({
        'apply': args.apply,
        'today': today.isoformat(),
        'raw_days': args.raw_days,
        'snapshot_days': args.snapshot_days,
        'archive_days': args.archive_days,
        'actions_count': len(actions),
        'estimated_size_mb': round(total_size / 1024 / 1024, 1),
        'actions': actions[:50],  # show first 50
    }, ensure_ascii=False, indent=2))

    if not args.apply and actions:
        print(f'\nDry run: {len(actions)} items would be cleaned. Use --apply to execute.')


if __name__ == '__main__':
    main()
