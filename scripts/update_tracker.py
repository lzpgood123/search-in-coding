#!/usr/bin/env python3
"""Run tracker pipeline. Deployment is opt-in via --deploy."""
import argparse, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(cmd, required=True, timeout=600):
    p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    item={'cmd':' '.join(cmd),'returncode':p.returncode,'stdout':p.stdout[-4000:],'stderr':p.stderr[-4000:],'required':required}
    print(json.dumps(item,ensure_ascii=False),flush=True)
    if required and p.returncode: raise SystemExit(p.returncode)
    return item
def main():
    ap=argparse.ArgumentParser(description='Collect, normalize, score, report, and build the tracker')
    ap.add_argument('--github-limit',type=int,default=20); ap.add_argument('--exa-limit',type=int,default=3)
    ap.add_argument('--github-queries',type=int,default=0); ap.add_argument('--exa-queries',type=int,default=0)
    ap.add_argument('--skip-collect',action='store_true'); ap.add_argument('--deploy',action='store_true')
    ap.add_argument('--skip-deploy',action='store_true',help='Deprecated no-op; deployment is opt-in via --deploy')
    a=ap.parse_args(); steps=[]
    if not a.skip_collect:
        steps.append(run(['python3','scripts/collect_github.py','--limit',str(a.github_limit),'--queries',str(a.github_queries)],required=False,timeout=900))
        steps.append(run(['python3','scripts/collect_exa.py','--limit',str(a.exa_limit),'--queries',str(a.exa_queries)],required=False,timeout=900))
        steps.append(run(['python3','scripts/normalize.py','--source','all'],timeout=600))
    for cmd in [
        ['python3','scripts/sanitize_public_data.py'], ['python3','scripts/enrich_i18n.py'], ['python3','scripts/validate_data.py'], ['python3','scripts/score.py'],
        ['python3','scripts/finalize_data.py'], ['python3','scripts/enrich_i18n.py'], ['python3','scripts/enrich_translations.py'], ['python3','scripts/generate_reports.py'],
        ['python3','scripts/snapshot_and_diff.py'], ['python3','scripts/build_site.py'], ['python3','scripts/quality_gate.py'],
        ['python3','-m','py_compile',*[str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts').glob('*.py'))]]]:
        steps.append(run(cmd,timeout=900))
    if a.deploy: steps.append(run(['python3','scripts/deploy_site.py'],timeout=300))
    print(json.dumps({'status':'PASS','steps':len(steps),'non_blocking_failures':sum(1 for s in steps if s['returncode']!=0),'deploy':bool(a.deploy)},ensure_ascii=False))
if __name__=='__main__': main()
