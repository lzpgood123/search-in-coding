#!/usr/bin/env python3
"""Generate 3 ecosystem reports using new schema fields.

Reports:
- weekly-report.md: data overview, top 10 projects, score distribution, tracking status
- tool-comparison.md: 10 tools ecosystem size, resource type distribution, avg score
- curated-top.md: top 50 projects table + top 3 by category
"""
import argparse, json, collections, datetime
from common import ROOT, load_jsonish


def main():
    ap = argparse.ArgumentParser(description='Generate ecosystem reports')
    ap.parse_args()
    now = datetime.date.today().isoformat()
    reports = ROOT / 'docs' / 'reports'
    reports.mkdir(parents=True, exist_ok=True)

    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')

    eco = [p for p in projects if p.get('source_type') != 'official-seed' and p.get('tracking_priority') != 'reject']
    eco_sorted = sorted(eco, key=lambda p: p.get('total_score', 0), reverse=True)

    # === 1. Weekly Report ===
    score_buckets = collections.Counter()
    for p in eco:
        s = p.get('total_score', 0)
        if s <= 20:
            score_buckets['0-20'] += 1
        elif s <= 40:
            score_buckets['21-40'] += 1
        elif s <= 60:
            score_buckets['41-60'] += 1
        elif s <= 80:
            score_buckets['61-80'] += 1
        else:
            score_buckets['81-100'] += 1

    tracking = collections.Counter(p.get('tracking_priority', 'pending') for p in projects)

    weekly = f"""# 生态周报 - {now}

## 数据概况

- 总记录数: {len(projects)}
- 生态项目: {len(eco)}
- 推荐项目: {len(curated)}
- 官方工具: {sum(1 for p in projects if p.get('source_type') == 'official-seed')}

## Top 10 项目

| # | 名称 | 类型 | 工具 | 分数 | Stars | URL |
|---|------|------|------|------|-------|-----|
"""
    for i, p in enumerate(eco_sorted[:10]):
        name = p.get('name', '').replace('|', '/')
        rtype = ', '.join(p.get('resource_type', []))
        tools_str = ', '.join(p.get('target_tools', []))
        score = p.get('total_score', 0)
        stars = p.get('stars', 0)
        url = p.get('url', '')
        weekly += f"| {i+1} | {name} | {rtype} | {tools_str} | {score} | {stars} | {url} |\n"

    weekly += f"""
## 分数分布

| 分数段 | 项目数 |
|--------|--------|
| 0-20 | {score_buckets.get('0-20', 0)} |
| 21-40 | {score_buckets.get('21-40', 0)} |
| 41-60 | {score_buckets.get('41-60', 0)} |
| 61-80 | {score_buckets.get('61-80', 0)} |
| 81-100 | {score_buckets.get('81-100', 0)} |

## 追踪状态

- 追踪中 (track): {tracking.get('track', 0)}
- 索引中 (index): {tracking.get('index', 0)}
- 待分析 (pending): {tracking.get('pending', 0)}
- 已拒绝 (reject): {tracking.get('reject', 0)}
"""
    (reports / 'weekly-report.md').write_text(weekly, encoding='utf-8')

    # === 2. Tool Comparison ===
    comparison = f"""# 工具生态对比 - {now}

## 生态规模

| 工具 | 项目数 | 推荐数 | 平均分 | Top 项目 |
|------|--------|--------|--------|---------|
"""
    for t in tools:
        tid = t['id']
        if tid == 'general-ai-coding':
            continue
        t_projects = [p for p in eco if tid in (p.get('target_tools') or [])]
        t_curated = [p for p in curated if tid in (p.get('target_tools') or [])]
        avg = round(sum(p.get('total_score', 0) for p in t_projects) / max(len(t_projects), 1), 1)
        top_name = t_projects[0]['name'] if t_projects else 'N/A'
        comparison += f"| {t.get('name', tid)} | {len(t_projects)} | {len(t_curated)} | {avg} | {top_name} |\n"

    # Resource type distribution by tool
    comparison += "\n## 资源类型分布\n\n| 工具 | MCP | Skills | Rules | Framework | CLI | Tutorial |\n|------|-----|--------|-------|-----------|-----|----------|\n"
    for t in tools:
        tid = t['id']
        if tid == 'general-ai-coding':
            continue
        t_projects = [p for p in eco if tid in (p.get('target_tools') or [])]
        type_counts = collections.Counter()
        for p in t_projects:
            for rt in (p.get('resource_type') or []):
                type_counts[rt] += 1
        comparison += f"| {t.get('name', tid)} | {type_counts.get('mcp-server', 0)} | {type_counts.get('skills', 0)} | {type_counts.get('rules', 0)} | {type_counts.get('agent-framework', 0)} | {type_counts.get('cli-tool', 0)} | {type_counts.get('tutorial', 0)} |\n"

    (reports / 'tool-comparison.md').write_text(comparison, encoding='utf-8')

    # === 3. Curated Top ===
    curated_sorted = sorted(curated, key=lambda p: p.get('total_score', 0), reverse=True)
    top_md = f"""# 推荐榜 - {now}

## Top 50 项目

| # | 名称 | 类型 | 工具 | 分数 | Stars | URL |
|---|------|------|------|------|-------|-----|
"""
    for i, p in enumerate(curated_sorted[:50]):
        name = p.get('name', '').replace('|', '/')
        rtype = ', '.join(p.get('resource_type', []))
        tools_str = ', '.join(p.get('target_tools', []))
        score = p.get('total_score', 0)
        stars = p.get('stars', 0)
        url = p.get('url', '')
        top_md += f"| {i+1} | {name} | {rtype} | {tools_str} | {score} | {stars} | {url} |\n"

    # Top 3 by resource type
    top_md += "\n## 按分类 Top 3\n\n"
    for rt in ['mcp-server', 'skills', 'rules', 'agent-framework', 'cli-tool', 'tutorial']:
        rt_projects = [p for p in eco_sorted if rt in (p.get('resource_type') or [])][:3]
        if rt_projects:
            top_md += f"\n### {rt}\n\n"
            for p in rt_projects:
                top_md += f"- [{p.get('name')}]({p.get('url')}) - {p.get('total_score', 0)} 分, {p.get('stars', 0)} stars\n"

    (reports / 'curated-top.md').write_text(top_md, encoding='utf-8')

    print(json.dumps({'reports': 3, 'projects': len(projects), 'curated': len(curated), 'tools': len(tools)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
