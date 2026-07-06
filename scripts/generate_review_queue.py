#!/usr/bin/env python3
"""Generate a simple human review queue from curated projects.

The goal is to let the user only read, choose an action, and submit choices
back to Hermes. Hermes then applies the decisions, validates, deploys, commits.
"""
import argparse
import json
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

def total_score(p):
    return p.get('total_score') or sum((p.get('score') or {}).values())

def main():
    ap = argparse.ArgumentParser(description='Generate simplified review queue')
    ap.add_argument('--limit', type=int, default=20)
    ap.add_argument('--output', default='docs/review/review-queue.md')
    args = ap.parse_args()

    curated = load('data/curated-projects.yaml')
    items = sorted(curated, key=total_score, reverse=True)[:args.limit]
    today = datetime.date.today().isoformat()

    lines = [
        f'# Search in Coding 简化人工审核清单 — {today}',
        '',
        '> 你只需要看项目，然后按编号选择动作。不要手改数据。把你的选择发给 Hermes，Hermes 会修改数据、验证、部署并提交。',
        '',
        '正式站点：<https://coding.lzpgood.online/>',
        '',
        '## 怎么提交你的选择',
        '',
        '直接回复类似：',
        '',
        '```text',
        '1 保留 try-now：确实值得试用。',
        '2 降级 watch：有趣但不是核心 coding agent 能力。',
        '3 移除 rejected：范围过泛，不适合本项目。',
        '4 改为 reference：更像资料，不是工具。',
        '```',
        '',
        '可选动作：',
        '',
        '| 动作 | 含义 |',
        '|---|---|',
        '| 保留 try-now | 继续作为优先推荐 |',
        '| 降级 watch | 保留，但只观察 |',
        '| 改为 reference | 作为资料/教程/参考 |',
        '| 改为 experimental | 实验性项目 |',
        '| 移除 rejected | 移出 curated，放入 rejected |',
        '| 改分类 | 你指定新分类 |',
        '| 改关联工具 | 你指定 target_tools |',
        '',
        '## 审核清单',
        '',
    ]

    for i, p in enumerate(items, 1):
        cats = ', '.join(p.get('category') or [])
        tools = ', '.join(p.get('target_tools') or [])
        level = p.get('recommendation_level', 'watch')
        source = p.get('source_type', '')
        quality = p.get('source_quality', '')
        score = total_score(p)
        summary = p.get('summary') or ''
        note = p.get('curation_note') or p.get('why_it_matters') or ''
        lines += [
            f'### {i}. {p.get("name")}',
            '',
            f'- URL: {p.get("url")}',
            f'- 当前等级: `{level}`',
            f'- 分数: `{score}`',
            f'- 来源: `{source}` / `{quality}`',
            f'- 分类: {cats}',
            f'- 关联工具: {tools}',
            f'- 摘要: {summary}',
            f'- 当前理由: {note}',
            '',
            '你的选择：`保留 try-now` / `降级 watch` / `改为 reference` / `改为 experimental` / `移除 rejected` / `改分类 ...` / `改关联工具 ...`',
            '',
        ]

    lines += [
        '## 给 Hermes 的执行要求',
        '',
        '当你提交选择后，Hermes 应执行：',
        '',
        '1. 修改 `data/curated-projects.yaml`、`data/rejected-projects.yaml`、`data/projects.yaml`。',
        '2. 运行 `python3 scripts/update_tracker.py --skip-collect`。',
        '3. 确认 `https://coding.lzpgood.online/` 正常。',
        '4. 提交并推送。',
        '',
    ]

    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'output': str(out), 'items': len(items)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
