#!/usr/bin/env python3
"""LLM re-judge target_tools only (does not touch scores / types / priority).

Usage:
    python3 scripts/retarget_tools.py --priority track --dry-run
    python3 scripts/retarget_tools.py --priority track --limit 20
    python3 scripts/retarget_tools.py --priority track
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_jsonish, save_jsonish
from llm_api import call_with_retry, load_api_keys, KeyRotator, parse_json_response
from llm_prompts import load_project_readme, format_active_tools
from seed_tools_schema import load_seed_tools, iter_active_tools

SYSTEM_PROMPT = (
    'You are an expert analyst for the AI Coding Agent ecosystem. '
    'Respond with valid JSON only, no markdown.'
)

CHECKPOINT_PATH = ROOT / 'data' / 'retarget-checkpoint.json'
SAVE_EVERY = 50


def filter_valid_tool_ids(ids, valid_ids):
    """Keep only known tool ids, preserve order, drop dups."""
    out = []
    for tid in ids or []:
        if not isinstance(tid, str):
            continue
        tid = tid.strip()
        if tid in valid_ids and tid not in out:
            out.append(tid)
    return out


def apply_retarget_result(project, result, valid_ids):
    """Apply LLM result: only overwrite target_tools when non-empty valid list.

    Empty / invalid / None → keep original (per design risk mitigation).
    """
    if not project:
        return project
    if not result or not isinstance(result, dict):
        return project
    tools = result.get('target_tools')
    if not isinstance(tools, list) or len(tools) == 0:
        return project
    filtered = filter_valid_tool_ids(tools, valid_ids)
    if not filtered:
        return project
    project['target_tools'] = filtered
    if result.get('reason'):
        project['retarget_reason'] = str(result.get('reason'))[:300]
    project['retargeted_at'] = time.strftime('%Y-%m-%d')
    return project


def build_retarget_prompt(project, active_tools):
    """Build a slim prompt that only asks for target_tools."""
    name = project.get('name') or ''
    topics = project.get('topics') or []
    existing = project.get('target_tools') or []
    summary = (project.get('summary') or '')[:300]
    readme = load_project_readme(project)
    tool_list = format_active_tools(active_tools)
    n = len(active_tools) if active_tools else 10
    return f"""你是 AI 编码工具生态分析专家。

以下是当前追踪的 {n} 个 AI 编码工具：
{tool_list}

请根据项目信息判断这个项目与哪些工具相关。

项目名：{name}
Summary：{summary}
Topics：{', '.join(topics) if topics else 'N/A'}
当前标签：{', '.join(existing) if existing else 'none'}
README（完整）：{readme}

只返回 JSON：
{{"target_tools": ["tool_id_1", ...], "reason": "一句话理由"}}

注意：
- 只返回上述 JSON，不要其他内容
- target_tools 可以为空数组（表示无具体工具归属）
- 如果项目与 AI 相关但不针对任何具体工具，返回 ["general-ai-coding"]
- 判断依据：README 内容、项目描述、topics
- tool_id 必须是上面列表中的 id（或 general-ai-coding）
"""


def load_checkpoint():
    if not CHECKPOINT_PATH.exists():
        return set()
    try:
        data = json.loads(CHECKPOINT_PATH.read_text(encoding='utf-8'))
        return set(data.get('done_ids') or [])
    except (json.JSONDecodeError, OSError):
        return set()


def save_checkpoint(done_ids):
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(
        json.dumps({
            'done_ids': sorted(done_ids),
            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


def select_projects(projects, priority='track', done_ids=None, force=False):
    done_ids = done_ids or set()
    selected = []
    for p in projects or []:
        if priority and p.get('tracking_priority') != priority:
            continue
        pid = p.get('id')
        if not pid:
            continue
        if not force and pid in done_ids:
            continue
        selected.append(p)
    return selected


def _analyze_one(project, active_tools, rotator):
    prompt = build_retarget_prompt(project, active_tools)
    text = call_with_retry(prompt, SYSTEM_PROMPT, rotator, max_retries=3)
    result = parse_json_response(text) if text else None
    return project.get('id'), result


def main():
    ap = argparse.ArgumentParser(description='LLM retarget target_tools only')
    ap.add_argument('--priority', default='track')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--max-projects', type=int, default=0, help='alias of --limit')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--force', action='store_true', help='Ignore checkpoint')
    ap.add_argument('--sleep', type=float, default=0.05)
    ap.add_argument('--workers', type=int, default=4, help='Concurrent LLM workers')
    args = ap.parse_args()
    limit = args.limit or args.max_projects or 0

    projects = load_jsonish('data/projects.yaml')
    if not isinstance(projects, list):
        print('ERROR: projects.yaml not a list')
        sys.exit(1)

    tools = load_seed_tools(normalize=True)
    active_tools = list(iter_active_tools(tools))
    valid_ids = {t.get('id') for t in active_tools if t.get('id')}
    valid_ids.add('general-ai-coding')

    done_ids = set() if args.force else load_checkpoint()
    selected = select_projects(projects, priority=args.priority, done_ids=done_ids, force=args.force)
    if limit > 0:
        selected = selected[:limit]

    print(json.dumps({
        'total_projects': len(projects),
        'active_tools': len(active_tools),
        'selected': len(selected),
        'checkpoint_done': len(done_ids),
        'workers': args.workers,
        'dry_run': args.dry_run,
    }, ensure_ascii=False), flush=True)

    if args.dry_run or not selected:
        return

    keys = load_api_keys()
    if not keys:
        print('ERROR: No SenseNova API keys')
        sys.exit(1)
    rotator = KeyRotator(keys)

    by_id = {p.get('id'): p for p in projects if p.get('id')}
    work = [by_id.get(p.get('id'), p) for p in selected]
    changed = errors = done = 0
    lock = Lock()
    workers = max(1, int(args.workers or 1))

    def _one(proj):
        if args.sleep > 0:
            time.sleep(args.sleep)
        return _analyze_one(proj, active_tools, rotator)

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_one, p): p for p in work}
        for fut in as_completed(futures):
            pid, result = fut.result()
            live = by_id.get(pid)
            with lock:
                done += 1
                if live is None:
                    errors += 1
                else:
                    before = list(live.get('target_tools') or [])
                    apply_retarget_result(live, result, valid_ids)
                    after = list(live.get('target_tools') or [])
                    if result is None:
                        errors += 1
                        if errors <= 20 or errors % 50 == 0:
                            print(f'  error {live.get("name") or pid}: no/invalid LLM response', flush=True)
                    elif before != after:
                        changed += 1
                        if changed <= 30 or changed % 50 == 0:
                            print(f'  {pid}: {before} -> {after}', flush=True)
                if pid:
                    done_ids.add(pid)

                if done % 50 == 0 or done == len(work):
                    print(f'progress {done}/{len(work)} changed={changed} errors={errors}', flush=True)

                if done % SAVE_EVERY == 0:
                    save_jsonish('data/projects.yaml', projects)
                    save_checkpoint(done_ids)
                    print(f'  checkpoint saved at {done}', flush=True)

    save_jsonish('data/projects.yaml', projects)
    save_checkpoint(done_ids)
    print(json.dumps({
        'done': True,
        'processed': len(selected),
        'changed': changed,
        'errors': errors,
        'checkpoint_total': len(done_ids),
    }, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
