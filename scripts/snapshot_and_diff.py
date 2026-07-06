#!/usr/bin/env python3
"""Create daily snapshots and weekly-style change reports."""
import argparse, json, shutil, datetime
from pathlib import Path
from common import ROOT, load_jsonish, save_jsonish

SNAP_DIR = ROOT / 'data/snapshots'
REPORT_DIR = ROOT / 'docs/reports/weekly'

def by_id(rows): return {r.get('id'): r for r in rows if r.get('id')}
def score(r): return r.get('total_score') or sum((r.get('score') or {}).values())
def latest_snapshot(before):
    if not SNAP_DIR.exists(): return None
    dates = sorted([p.name for p in SNAP_DIR.iterdir() if p.is_dir() and p.name < before])
    return SNAP_DIR / dates[-1] / 'projects.json' if dates else None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    ap.add_argument('--no-overwrite', action='store_true')
    args=ap.parse_args()
    projects=load_jsonish('data/projects.yaml'); curated=load_jsonish('data/curated-projects.yaml'); rejected=load_jsonish('data/rejected-projects.yaml')
    snap=SNAP_DIR/args.date; snap.mkdir(parents=True, exist_ok=True)
    for name, rows in [('projects.json',projects),('curated-projects.json',curated),('rejected-projects.json',rejected)]:
        out=snap/name
        if not (args.no_overwrite and out.exists()): out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    prev_path=latest_snapshot(args.date)
    prev=json.loads(prev_path.read_text()) if prev_path and prev_path.exists() else []
    cur=by_id(projects); old=by_id(prev)
    new_ids=sorted(set(cur)-set(old)); removed_ids=sorted(set(old)-set(cur))
    score_changes=[]
    for pid in sorted(set(cur)&set(old)):
        delta=score(cur[pid])-score(old[pid])
        if delta: score_changes.append((abs(delta),delta,pid,cur[pid].get('name')))
    score_changes=sorted(score_changes, reverse=True)[:20]
    cur_curated=set(p.get('id') for p in curated); old_curated=set()
    if prev_path:
        pc=prev_path.parent/'curated-projects.json'
        if pc.exists(): old_curated=set(p.get('id') for p in json.loads(pc.read_text()))
    newly_curated=sorted(cur_curated-old_curated); exited_curated=sorted(old_curated-cur_curated)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report=REPORT_DIR/f'{args.date}-weekly-update.md'
    lines=[f'# Search in Coding Weekly Change Report — {args.date}','',f'Previous snapshot: `{prev_path}`' if prev_path else 'Previous snapshot: none','', '## Summary','', f'- Projects: {len(projects)}', f'- Curated: {len(curated)}', f'- Rejected: {len(rejected)}', f'- New records: {len(new_ids)}', f'- Removed records: {len(removed_ids)}', f'- Newly curated: {len(newly_curated)}', f'- Exited curated: {len(exited_curated)}', '', '## New records', '']
    lines += [f'- `{pid}` — {cur[pid].get("name")}' for pid in new_ids[:50]] or ['- None']
    lines += ['', '## Newly curated', '']
    lines += [f'- `{pid}` — {cur.get(pid,{}).get("name", pid)}' for pid in newly_curated[:50]] or ['- None']
    lines += ['', '## Score changes', '']
    lines += [f'- `{pid}` — {name}: {delta:+}' for _,delta,pid,name in score_changes] or ['- None']
    report.write_text('\n'.join(lines).rstrip()+'\n')
    print(json.dumps({'snapshot':str(snap),'report':str(report),'new_records':len(new_ids),'newly_curated':len(newly_curated)},ensure_ascii=False))
if __name__=='__main__': main()
