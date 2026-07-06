#!/usr/bin/env python3
"""Deploy generated static site to the production Nginx webroot."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = Path('/var/www/coding.lzpgood.online')

def copytree(src: Path, dst: Path, dry_run: bool = False) -> dict:
    files = [p for p in src.rglob('*') if p.is_file()]
    if dry_run:
        return {'dry_run': True, 'source': str(src), 'dest': str(dst), 'files': len(files)}
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.rglob('*'):
        if old.is_file():
            old.unlink()
    for p in files:
        rel = p.relative_to(src)
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, out)
    return {'dry_run': False, 'source': str(src), 'dest': str(dst), 'files': len(files)}

def main():
    ap = argparse.ArgumentParser(description='Deploy site/ to production webroot')
    ap.add_argument('--dest', default=str(DEFAULT_DEST))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-chown', action='store_true')
    args = ap.parse_args()
    src = ROOT / 'site'
    if not (src / 'index.html').exists():
        raise SystemExit('site/index.html missing; run scripts/build_site.py first')
    result = copytree(src, Path(args.dest), args.dry_run)
    if not args.dry_run and not args.no_chown and os.geteuid() == 0:
        subprocess.run(['chown', '-R', 'www-data:www-data', args.dest], check=False)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    main()
