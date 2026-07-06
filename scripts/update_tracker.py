#!/usr/bin/env python3
"""Run the Search in Coding tracker update pipeline.

This script is intentionally conservative: collectors may fail independently,
but validation/build quality gates must pass before the run is considered OK.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], *, required: bool = True, timeout: int = 600) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    item = {
        "cmd": " ".join(cmd),
        "returncode": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "required": required,
    }
    print(json.dumps(item, ensure_ascii=False), flush=True)
    if required and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return item


def main() -> None:
    ap = argparse.ArgumentParser(description="Collect, normalize, score, report, and build the tracker")
    ap.add_argument("--github-limit", type=int, default=20)
    ap.add_argument("--exa-limit", type=int, default=3)
    ap.add_argument("--github-queries", type=int, default=0, help="0 means all configured queries")
    ap.add_argument("--exa-queries", type=int, default=0, help="0 means all configured queries")
    ap.add_argument("--skip-collect", action="store_true", help="Only rebuild derived data/reports/site")
    ap.add_argument("--skip-deploy", action="store_true", help="Do not sync site/ to the production Nginx webroot")
    args = ap.parse_args()

    steps: list[dict] = []
    if not args.skip_collect:
        steps.append(run([
            "python3", "scripts/collect_github.py",
            "--limit", str(args.github_limit),
            "--queries", str(args.github_queries),
        ], required=False, timeout=900))
        steps.append(run([
            "python3", "scripts/collect_exa.py",
            "--limit", str(args.exa_limit),
            "--queries", str(args.exa_queries),
        ], required=False, timeout=900))
        steps.append(run(["python3", "scripts/normalize.py", "--source", "all"], timeout=600))

    for cmd in [
        ["python3", "scripts/validate_data.py"],
        ["python3", "scripts/score.py"],
        ["python3", "scripts/finalize_data.py"],
        ["python3", "scripts/generate_reports.py"],
        ["python3", "scripts/build_site.py"],
        ["python3", "scripts/quality_gate.py"],
        ["python3", "-m", "py_compile", *[str(p.relative_to(ROOT)) for p in sorted((ROOT / "scripts").glob("*.py"))]],
    ]:
        steps.append(run(cmd, timeout=900))

    if not args.skip_deploy:
        steps.append(run(["python3", "scripts/deploy_site.py"], timeout=300))

    failures = [s for s in steps if s["returncode"] != 0]
    print(json.dumps({"status": "PASS", "steps": len(steps), "non_blocking_failures": len(failures)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
