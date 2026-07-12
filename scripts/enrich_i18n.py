#!/usr/bin/env python3
"""Persist bilingual display fields into source datasets.

This is schema enrichment only. It does not call translation services; it keeps
source text in both zh/en slots so the site and downstream consumers can rely on
stable i18n keys. A later translation job can replace either side safely.
"""
import argparse
import json
from common import load_jsonish, save_jsonish

DATASETS = [
    'data/projects.yaml',
    'data/curated-projects.yaml',
    'data/rejected-projects.yaml',
]

def display_text(record):
    name = record.get('name') or record.get('id') or ''
    summary = record.get('summary') or name
    return str(name), str(summary)

def ensure_i18n(record):
    name, summary = display_text(record)
    before = json.dumps(record.get('i18n', {}), ensure_ascii=False, sort_keys=True)
    i18n = record.setdefault('i18n', {})
    zh = i18n.setdefault('zh', {})
    en = i18n.setdefault('en', {})
    zh.setdefault('name', name)
    zh.setdefault('summary', summary)
    en.setdefault('name', name)
    en.setdefault('summary', summary)
    after = json.dumps(record.get('i18n', {}), ensure_ascii=False, sort_keys=True)
    return before != after

def main():
    ap = argparse.ArgumentParser(description='Persist i18n.zh/en fields into source datasets')
    ap.add_argument('--files', nargs='*', default=DATASETS)
    args = ap.parse_args()

    updated_files = 0
    records_seen = 0
    records_changed = 0
    missing_after = 0
    for rel in args.files:
        rows = load_jsonish(rel)
        if not isinstance(rows, list):
            continue
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            records_seen += 1
            if ensure_i18n(row):
                changed = True
                records_changed += 1
            i18n = row.get('i18n') or {}
            if 'zh' not in i18n or 'en' not in i18n:
                missing_after += 1
        if changed:
            save_jsonish(rel, rows)
            updated_files += 1
    print(json.dumps({
        'updated_files': updated_files,
        'records_seen': records_seen,
        'records_changed': records_changed,
        'missing_after': missing_after,
    }, ensure_ascii=False))
    if missing_after:
        raise SystemExit(1)

if __name__ == '__main__':
    main()