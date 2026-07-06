#!/usr/bin/env python3
import argparse, json, zipfile
from pathlib import Path
from common import ROOT
INCLUDE=['README.md','pyproject.toml','.env.example','data/seed-tools.yaml','data/queries.yaml','data/sources.yaml','data/concepts.yaml','schemas','docs','scripts','site','.github']

def collect():
    files=[]
    for rel in INCLUDE:
        p=ROOT/rel
        if p.is_file(): files.append(p)
        elif p.is_dir(): files += [x for x in p.rglob('*') if x.is_file() and 'data/raw' not in str(x)]
    return sorted(set(files))

def main():
    ap=argparse.ArgumentParser(description='Export reusable tracker package')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--output', default='dist/search-in-coding-template.zip')
    args=ap.parse_args()
    files=collect()
    if args.dry_run:
        print(json.dumps({'dry_run':True,'files':len(files),'sample':[str(f.relative_to(ROOT)) for f in files[:30]]}, ensure_ascii=False, indent=2)); return
    out=ROOT/args.output; out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in files: z.write(f, f.relative_to(ROOT))
    print(json.dumps({'output':str(out),'files':len(files)}, ensure_ascii=False))
if __name__=='__main__': main()
