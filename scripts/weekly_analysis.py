#!/usr/bin/env python3
"""Weekly LLM analysis pipeline.

Runs every Monday 03:00 via Hermes cron.
Analyzes new projects + re-evaluates all projects using LLM.

Flow:
1. Load projects from data/projects.yaml
2. Pre-filter: remove archived, empty repos
3. Batch LLM analysis (3 concurrent) using SenseNova DeepSeek-V4-Flash
4. Update benchmark references
5. Re-score all projects (quantifiable + quality)
6. Generate 3 reports via generate_reports.py
7. Build site
8. Save snapshot

Usage:
    python3 scripts/weekly_analysis.py                    # full run
    python3 scripts/weekly_analysis.py --max-projects 50  # limit for testing
    python3 scripts/weekly_analysis.py --dry-run          # no LLM calls, just structure
"""
import argparse
import copy
import datetime
import json
import subprocess
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT, load_jsonish, save_jsonish, today
from llm_api import batch_analyze, parse_json_response, call_with_retry, load_api_keys, KeyRotator
from llm_prompts import (
    project_analysis_prompt, ANALYSIS_SYSTEM,
    benchmark_selection_prompt, BENCHMARK_SYSTEM,
)
from benchmark_manager import BenchmarkManager, BENCHMARK_RANGES

DEFAULT_BATCH_SIZE = 10
LLM_CONFIG_PATH = ROOT / 'config' / 'llm-analysis.yaml'


def load_llm_config():
    """Load config/llm-analysis.yaml (empty dict if missing)."""
    if not LLM_CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(LLM_CONFIG_PATH.read_text(encoding='utf-8')) or {}
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f'WARNING: failed to load {LLM_CONFIG_PATH}: {e}')
        return {}


def get_batch_size(override=None):
    """Resolve concurrent batch size: CLI override > config > default 10."""
    if override is not None:
        return int(override)
    cfg = load_llm_config()
    api = cfg.get('api') or {}
    value = api.get('batch_size', DEFAULT_BATCH_SIZE)
    try:
        n = int(value)
        return n if n > 0 else DEFAULT_BATCH_SIZE
    except (TypeError, ValueError):
        return DEFAULT_BATCH_SIZE


def pre_filter(projects):
    """Pre-filter projects before LLM analysis.
    Remove archived repos. Sort by stars descending (analyze high-value first).
    """
    filtered = [p for p in projects if p.get('status') != 'archived']
    filtered.sort(key=lambda p: (p.get('stars') or 0), reverse=True)
    return filtered


def get_projects_to_analyze(projects, max_projects=None):
    """Get projects that need analysis.

    Priority:
    1. Never analyzed (last_analyzed is None)
    2. Analyzed more than 7 days ago

    Skips archived repos. Within the candidate set, sort by stars
    descending so high-value projects are analyzed first (batch4).
    """
    now = datetime.date.today()
    cutoff = (now - datetime.timedelta(days=7)).isoformat()

    to_analyze = []
    for p in projects:
        if p.get('status') == 'archived':
            continue
        last = p.get('last_analyzed')
        if last is None or last < cutoff:
            to_analyze.append(p)

    # High-star first regardless of input order
    to_analyze.sort(key=lambda p: (p.get('stars') or 0), reverse=True)

    if max_projects:
        to_analyze = to_analyze[:max_projects]

    return to_analyze


def merge_analysis_result(project, analysis):
    """Merge LLM analysis result into a project record."""
    p = copy.deepcopy(project)

    if analysis is None:
        return p  # keep original if analysis failed

    # Update fields from analysis
    if 'resource_type' in analysis:
        p['resource_type'] = analysis['resource_type']
    if 'target_tools' in analysis:
        p['target_tools'] = analysis['target_tools']
    if 'tracking_priority' in analysis:
        p['tracking_priority'] = analysis['tracking_priority']
    if 'quality_score' in analysis:
        p['quality_score'] = analysis['quality_score']
    if 'quality_detail' in analysis:
        # Keep quantifiable score_detail intact; store LLM breakdown separately.
        p['quality_detail'] = analysis['quality_detail']
    if 'llm_summary' in analysis:
        p['llm_summary'] = analysis['llm_summary']

    # Recalculate total score
    p['total_score'] = p.get('quantifiable_score', 0) + p.get('quality_score', 0)

    # Official seed tools are always tracked, regardless of LLM priority.
    if p.get('source_type') == 'official-seed':
        p['tracking_priority'] = 'track'

    # Mark as analyzed
    p['last_analyzed'] = today()

    return p


def run_analysis(projects, max_projects=None, batch_size=None):
    """Run LLM analysis on projects in batches with key stats + 429 degradation.

    Args:
        projects: list of project dicts (already pre-filtered)
        max_projects: limit number of projects to analyze
        batch_size: concurrent LLM calls per batch (default from config)

    Returns:
        list of analyzed project dicts (same order as input, with results merged)
    """
    if batch_size is None:
        batch_size = get_batch_size()
    to_analyze = get_projects_to_analyze(projects, max_projects)

    if not to_analyze:
        print(f'No projects need analysis (all analyzed within 7 days)')
        return projects

    # Degradation state
    original_count = len(to_analyze)
    degraded_mode = False
    total_429_errors = 0
    total_calls = 0

    print(f'Projects to analyze: {len(to_analyze)}')

    # Map for quick lookup
    analyze_ids = {p.get('id') for p in to_analyze}

    # Process in batches of batch_size
    all_results = {}  # project_id -> analysis result
    all_key_stats = {}
    updated_projects = list(projects)

    def merge_into_projects(source_projects, results_map):
        merged = []
        for p in source_projects:
            pid = p.get('id')
            if pid in results_map:
                merged.append(merge_analysis_result(p, results_map[pid]))
            else:
                merged.append(p)
        return merged

    for i in range(0, len(to_analyze), batch_size):
        batch = to_analyze[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(to_analyze) - 1) // batch_size + 1
        print(f'\n--- Batch {batch_num}/{total_batches} ({len(batch)} projects) ---')

        # Create prompt function for each project
        def prompt_fn(p):
            return project_analysis_prompt(p)

        results, key_stats = batch_analyze(batch, prompt_fn, ANALYSIS_SYSTEM, max_workers=batch_size)

        # Merge key stats
        for kid, stat in key_stats.items():
            if kid not in all_key_stats:
                all_key_stats[kid] = {'calls': 0, 'success': 0, 'failed': 0, 'fail_reasons': []}
            all_key_stats[kid]['calls'] += stat.get('calls', 0)
            all_key_stats[kid]['success'] += stat.get('success', 0)
            all_key_stats[kid]['failed'] += stat.get('failed', 0)
            all_key_stats[kid]['fail_reasons'].extend(stat.get('fail_reasons') or [])

        # Count 429 errors for degradation (cumulative across batches)
        total_429_errors = sum(
            1
            for s in all_key_stats.values()
            for r in (s.get('fail_reasons') or [])
            if '429' in str(r) or 'rate_limit' in str(r)
        )
        total_calls = sum(s.get('calls', 0) for s in all_key_stats.values())

        for idx, result in results.items():
            project_id = batch[idx].get('id') if idx < len(batch) else None
            if project_id:
                all_results[project_id] = result
                status = 'OK' if result else 'FAILED'
                print(f'  {batch[idx].get("name", "?")}: {status}')

        # Incremental checkpoint after each batch (not per project) so timeouts
        # do not lose the whole run.
        updated_projects = merge_into_projects(projects, all_results)
        save_jsonish('data/projects.yaml', updated_projects)
        print(f'  Checkpoint saved ({len(all_results)} analyzed so far)')

        # Degradation check: if 429 rate > 30%, cut remaining work in half
        if total_calls > 10:  # only check after enough data
            rate_429 = total_429_errors / total_calls
            if rate_429 > 0.3 and not degraded_mode:
                degraded_mode = True
                remaining_batches = total_batches - batch_num
                if remaining_batches > 0:
                    # Skip half of remaining batches
                    skip_count = remaining_batches // 2
                    new_end = len(to_analyze) - (skip_count * batch_size)
                    to_analyze = to_analyze[:max(new_end, i + batch_size)]
                    print(
                        f'  ⚠️  DEGRADED MODE: 429 rate {rate_429:.0%} > 30%, '
                        f'reducing remaining projects by half'
                    )
                    total_batches = (len(to_analyze) - 1) // batch_size + 1

    success_count = sum(1 for r in all_results.values() if r is not None)
    fail_count = sum(1 for r in all_results.values() if r is None)
    print(f'\nAnalysis complete: {success_count} success, {fail_count} failed')
    if degraded_mode:
        print(f'  ⚠️  Run was in DEGRADED MODE (analyzed {len(all_results)}/{original_count})')

    # Save key stats history
    stats_path = ROOT / 'data' / 'llm-key-stats.json'
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_entry = {
        'date': today(),
        'total_calls': sum(s['calls'] for s in all_key_stats.values()),
        'total_success': sum(s['success'] for s in all_key_stats.values()),
        'total_failed': sum(s['failed'] for s in all_key_stats.values()),
        'degraded_mode': degraded_mode,
        '429_errors': total_429_errors,
        'keys': all_key_stats,
    }
    existing_stats = []
    if stats_path.exists():
        try:
            existing_stats = json.loads(stats_path.read_text(encoding='utf-8'))
            if not isinstance(existing_stats, list):
                existing_stats = [existing_stats]
        except (json.JSONDecodeError, Exception):
            existing_stats = []
    existing_stats.append(stats_entry)
    existing_stats = existing_stats[-30:]
    stats_path.write_text(json.dumps(existing_stats, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Key stats saved: {stats_path}')

    return updated_projects


def update_benchmarks(projects):
    """Update benchmark reference projects using LLM."""
    bm = BenchmarkManager()
    grouped = bm.group_by_range(projects)

    # Get top candidates for each range
    candidates = {}
    for label, ps in grouped.items():
        if ps:
            candidates[label] = sorted(ps, key=lambda p: p.get('total_score', 0), reverse=True)[:5]

    if not candidates:
        print('No candidates for benchmark selection')
        return bm.load()

    # Call LLM to select benchmarks
    existing = bm.load()
    prompt = benchmark_selection_prompt(candidates, existing)

    keys = load_api_keys()
    if not keys:
        print('ERROR: No API keys for benchmark selection')
        return existing

    rotator = KeyRotator(keys)
    text = call_with_retry(prompt, BENCHMARK_SYSTEM, rotator)
    result = parse_json_response(text)

    if result and 'benchmarks' in result:
        bm.update_from_llm(result, projects)
        print(f'Benchmarks updated: {len(result["benchmarks"])} ranges')
    else:
        print('Benchmark selection failed, keeping existing')

    return bm.load()


def rescore_all(projects):
    """Re-calculate total scores for all projects.

    total_score = quantifiable_score + quality_score
    Also assign benchmark_ref based on score range.
    """
    bm = BenchmarkManager()
    benchmarks = bm.load()

    for p in projects:
        q_score = p.get('quantifiable_score', 0)
        quality = p.get('quality_score', 0)
        p['total_score'] = q_score + quality

        # Assign benchmark reference
        total = p['total_score']
        for label, ref in benchmarks.items():
            ref_score = ref.get('score', 0)
            if abs(total - ref_score) <= 20:  # within 20 points of benchmark
                p['benchmark_ref'] = ref.get('project_id')
                break

    return projects


def generate_reports():
    """Generate 3 weekly reports by calling existing generate_reports.py."""
    print('Calling generate_reports.py...')
    r = subprocess.run(
        ['python3', 'scripts/generate_reports.py'],
        cwd=ROOT, capture_output=True, text=True, timeout=120
    )
    if r.stdout:
        print(r.stdout[-500:])
    if r.returncode != 0:
        print(f'Reports failed: {r.stderr[-500:]}')
    else:
        print('Reports generated successfully')


def save_snapshot(projects):
    """Save weekly snapshot for future trend analysis."""
    from collections import Counter
    snapshot_dir = ROOT / 'data' / 'snapshots'
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        'date': today(),
        'total_projects': len(projects),
        'by_source': dict(Counter(p.get('source_type') for p in projects)),
        'by_tracking': dict(Counter(p.get('tracking_priority') for p in projects)),
        'avg_score': round(sum(p.get('total_score', 0) for p in projects) / max(len(projects), 1), 1),
        'curated_count': sum(1 for p in projects if p.get('review_state') == 'auto-curated'),
        'rejected_count': sum(1 for p in projects if p.get('tracking_priority') == 'reject'),
        'tool_coverage': dict(Counter(t for p in projects for t in (p.get('target_tools') or []))),
        'resource_type_coverage': dict(Counter(rt for p in projects for rt in (p.get('resource_type') or []))),
        'analyzed_count': sum(1 for p in projects if p.get('quality_score', 0) > 0),
    }

    path = snapshot_dir / f'{today()}.json'
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Snapshot saved: {path}')


def main():
    ap = argparse.ArgumentParser(description='Weekly LLM analysis pipeline')
    ap.add_argument('--max-projects', type=int, default=None, help='Limit projects to analyze (for testing)')
    ap.add_argument('--batch-size', type=int, default=None, help='Concurrent LLM workers (default: config/llm-analysis.yaml)')
    ap.add_argument('--dry-run', action='store_true', help='No LLM calls, just show structure')
    ap.add_argument('--skip-reports', action='store_true', help='Skip report generation')
    ap.add_argument('--skip-benchmarks', action='store_true', help='Skip benchmark update')
    ap.add_argument('--skip-build', action='store_true', help='Skip site build')
    args = ap.parse_args()

    batch_size = get_batch_size(args.batch_size)
    print(f'=== Weekly Analysis - {today()} ===')
    print(f'batch_size={batch_size} (config-driven)')

    # Load data
    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')
    prev_projects = [copy.deepcopy(p) for p in projects]  # snapshot before changes

    print(f'Loaded: {len(projects)} projects, {len(curated)} curated, {len(tools)} tools')

    if args.dry_run:
        to_analyze = get_projects_to_analyze(projects, args.max_projects)
        print(f'\nDry run: would analyze {len(to_analyze)} projects')
        if to_analyze:
            stars_preview = [(p.get('name'), p.get('stars') or 0) for p in to_analyze[:10]]
            print(f'Top by stars: {stars_preview}')
            print(f'Sample: {to_analyze[0].get("name", "none")} stars={to_analyze[0].get("stars") or 0}')
        return

    # Step 1: Pre-filter stats only — NEVER drop archived from the full dataset
    filtered_count = sum(1 for p in projects if p.get('status') != 'archived')
    archived_count = len(projects) - filtered_count
    print(f'Pre-filter stats: active={filtered_count}, archived={archived_count} (archived kept in dataset, skipped for LLM)')

    # Step 2: Run LLM analysis on full list (selection skips archived; merge preserves all)
    print('\n--- Step 1: LLM Analysis ---')
    analyzed = run_analysis(projects, max_projects=args.max_projects, batch_size=batch_size)

    # Step 3: Update benchmarks (before rescoring!)
    if not args.skip_benchmarks:
        print('\n--- Step 2: Update Benchmarks ---')
        update_benchmarks(analyzed)

    # Step 4: Re-score all
    print('\n--- Step 3: Re-score All Projects ---')
    rescored = rescore_all(analyzed)

    # Step 5: Save snapshot
    print('\n--- Step 4: Save Snapshot ---')
    save_snapshot(rescored)

    # Step 6: Save updated projects
    save_jsonish('data/projects.yaml', rescored)
    print(f'Saved {len(rescored)} projects to data/projects.yaml')

    # Step 7: Generate reports (call existing generate_reports.py)
    if not args.skip_reports:
        print('\n--- Step 5: Generate Reports ---')
        generate_reports()

    # Step 8: Run build_site
    if not args.skip_build:
        print('\n--- Step 6: Build Site ---')
        r = subprocess.run(
            ['python3', 'scripts/build_site.py'],
            cwd=ROOT, capture_output=True, text=True, timeout=300
        )
        if r.stdout:
            print(r.stdout[-500:])
        if r.returncode != 0:
            print(f'Build site failed: {r.stderr[-500:]}')

    print('\n=== Weekly Analysis Complete ===')


if __name__ == '__main__':
    main()
