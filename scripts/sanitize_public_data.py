#!/usr/bin/env python3
"""Sanitize public repository data and generated artifacts.

Removes local machine paths, localhost/private URLs, and internal execution
process wording from source-of-truth data before reports/site are generated.
"""
import json, re
from pathlib import Path
from urllib.parse import urlparse
from common import ROOT, load_jsonish, save_jsonish

LOCAL_PATH_RE = re.compile(r'/(root|home|Users)/[^\s,，。)\]"\']+')
PRIVATE_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}
PRIVATE_PREFIXES = tuple([f'10.', '192.168.'] + [f'172.{i}.' for i in range(16, 32)])
PRIVATE_URL_RE = re.compile(r'https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)[^\s"\']*')

def is_private_url(url):
    try:
        host = (urlparse(str(url)).hostname or '').lower()
    except Exception:
        return False
    return host in PRIVATE_HOSTS or host.startswith(PRIVATE_PREFIXES)

def clean_text(value):
    if not isinstance(value, str): return value
    value = LOCAL_PATH_RE.sub('[local-source]', value)
    value = PRIVATE_URL_RE.sub('[local-url-removed]', value)
    value = value.replace('/var/www/ecoradar.lzpgood.online', '[production-webroot]')
    value = value.replace('/var/www/coding.lzpgood.online', '[production-webroot]')
    value = value.replace('/etc/nginx/sites-available/ecoradar.lzpgood.online', '[nginx-vhost]')
    value = value.replace('/etc/nginx/sites-available/coding.lzpgood.online', '[nginx-vhost]')
    value = value.replace('/etc/letsencrypt/live/ecoradar.lzpgood.online/fullchain.pem', '[tls-certificate]')
    value = value.replace('/etc/letsencrypt/live/coding.lzpgood.online/fullchain.pem', '[tls-certificate]')
    return value

def clean_any(obj):
    if isinstance(obj, dict):
        cleaned = {}
        for k, v in obj.items():
            if k == 'source_doc':
                continue
            if k == 'notes':
                # Public site/data should not expose raw snippets that may contain
                # prompt-like text, local context-file names, or process wording.
                continue
            cleaned[k] = clean_any(v)
        return cleaned
    if isinstance(obj, list):
        return [clean_any(x) for x in obj]
    if isinstance(obj, str):
        return clean_text(obj)
    return obj

def clean_record(record):
    before = json.dumps(record, ensure_ascii=False, sort_keys=True)
    cleaned = clean_any(record)
    record.clear(); record.update(cleaned)
    return before != json.dumps(record, ensure_ascii=False, sort_keys=True)

def sanitize_rows_file(rel, drop_private=True):
    rows = load_jsonish(rel)
    if not isinstance(rows, list): return 0
    out=[]; changed=0
    for row in rows:
        if isinstance(row, dict) and drop_private and is_private_url(row.get('url')):
            changed += 1
            continue
        if isinstance(row, dict) and clean_record(row): changed += 1
        out.append(row)
    if changed or len(out) != len(rows): save_jsonish(rel, out)
    return changed

def sanitize_json_file(path):
    try:
        data=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return 0
    cleaned=clean_any(data)
    if cleaned != data:
        path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return 1
    return 0

def main():
    changed={}
    for rel in ['data/seed-tools.yaml','data/projects.yaml','data/curated-projects.yaml','data/rejected-projects.yaml']:
        changed[rel]=sanitize_rows_file(rel)
    # Sanitize machine-readable snapshots and raw evidence without dropping files.
    json_changed=0
    for root in [ROOT/'data/raw', ROOT/'data/snapshots']:
        if root.exists():
            for path in root.rglob('*.json'):
                json_changed += sanitize_json_file(path)
    changed['json_artifacts']=json_changed
    print(json.dumps({'sanitized': changed}, ensure_ascii=False))
if __name__ == '__main__': main()
