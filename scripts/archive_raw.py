#!/usr/bin/env python3
"""Archive old data/raw date folders into compressed tarballs.

Default is dry-run to avoid destructive changes. Use --apply to replace old raw
folders with archives under data/raw-archive/.
"""
import argparse, datetime, json, shutil, tarfile
from pathlib import Path
from common import ROOT

def parse_date(name):
    try: return datetime.date.fromisoformat(name)
    except ValueError: return None

def archive_dir(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(dest, 'w:gz') as tar:
        tar.add(src, arcname=src.name)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--keep-days', type=int, default=30)
    ap.add_argument('--apply', action='store_true')
    args=ap.parse_args()
    today=datetime.date.today(); actions=[]
    for source in ['github','exa','web']:
        root=ROOT/'data/raw'/source
        if not root.exists(): continue
        for d in sorted(root.iterdir()):
            dt=parse_date(d.name)
            if not dt or (today-dt).days <= args.keep_days: continue
            dest=ROOT/'data/raw-archive'/source/f'{d.name}.tar.gz'
            actions.append({'source':str(d),'archive':str(dest),'age_days':(today-dt).days})
            if args.apply and not dest.exists():
                archive_dir(d,dest); shutil.rmtree(d)
    print(json.dumps({'apply':args.apply,'keep_days':args.keep_days,'actions':actions},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
