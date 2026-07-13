#!/usr/bin/env python3
"""Prompt templates for LLM analysis.

Three prompt types:
1. Project analysis: relevance, resource_type, target_tools, quality_score, llm_summary
2. Benchmark selection: choose reference projects for each score range
3. Report generation: weekly report, tool comparison, top picks
"""
import json

# === System Prompts ===

ANALYSIS_SYSTEM = """You are an expert analyst for the AI Coding Agent ecosystem.
You analyze GitHub projects and determine their relevance, type, quality, and relationship to AI coding tools.

You must respond with valid JSON only, no markdown formatting, no explanation outside JSON."""

BENCHMARK_SYSTEM = """You are an expert at calibrating quality assessments.
You select reference projects that represent the standard for each quality tier.
You must respond with valid JSON only."""

REPORT_SYSTEM = """You are a technical writer creating ecosystem reports in Markdown.
Write in clear, concise language. Use tables for comparisons."""


# === Project Analysis Prompt ===

def project_analysis_prompt(project):
    """Generate the analysis prompt for a single project."""
    name = project.get('name', '')
    summary = project.get('summary', '') or ''
    url = project.get('url', '')
    stars = project.get('stars', 0)
    forks = project.get('forks', 0)
    languages = project.get('languages', [])
    license_info = project.get('license', 'N/A')
    last_updated = project.get('last_updated', 'N/A')
    existing_tools = project.get('target_tools', [])
    readme_preview = project.get('readme_preview', '') or ''
    topics = project.get('topics', []) or []

    return f"""Analyze this GitHub project for the AI Coding Agent ecosystem:

Name: {name}
URL: {url}
Summary: {summary[:300]}
Stars: {stars}
Forks: {forks}
Languages: {', '.join(languages) if languages else 'N/A'}
License: {license_info}
Last Updated: {last_updated}
Currently tagged tools: {', '.join(existing_tools) if existing_tools else 'none'}
Topics: {', '.join(topics[:10]) if topics else 'N/A'}
README excerpt (first 500 chars): {readme_preview[:500]}

Respond with JSON in this exact format:
{{
  "relevance_score": 0.0-1.0,
  "resource_type": ["one or more of: mcp-server, skills, rules, agent-framework, cli-tool, tutorial, extension"],
  "target_tools": ["zero or more of: claude-code, codex-cli, antigravity-cli, opencode, goose, qoder, trae, workbuddy-codebuddy, cursor, hermes-agent"],
  "tracking_priority": "one of: track, index, reject",
  "quality_score": 0-40,
  "quality_detail": {{
    "relevance": 0-10,
    "practicality": 0-10,
    "novelty": 0-10,
    "ecosystem_value": 0-10
  }},
  "llm_summary": {{
    "zh": "一句话中文评价",
    "en": "one sentence English summary"
  }},
  "analysis_notes": "brief explanation of your assessment"
}}

Scoring guidelines:
- relevance (0-10): How directly related to AI coding agent ecosystem? 10=core ecosystem, 5=tangentially related, 0=unrelated
- practicality (0-10): Is there working code? README quality? Usable examples? 10=production-ready with docs, 5=basic implementation, 0=empty repo
- novelty (0-10): Does this bring something new? 10=novel approach, 5=variation of existing, 0=derivative
- ecosystem_value (0-10): How valuable to the ecosystem? 10=fills critical gap, 5=nice addition, 0=redundant
- quality_score = sum of the 4 dimensions (0-40)
- tracking_priority: "track" if quality_score >= 20 and relevance >= 0.5, "index" if quality_score >= 10, "reject" otherwise
- target_tools: list tools this project is relevant to. Empty list = general ecosystem resource
- resource_type: pick the most fitting types. "tutorial" is the fallback if none fit. "extension" for browser/IDE extensions."""


# === Benchmark Selection Prompt ===

def benchmark_selection_prompt(projects_by_range, existing_benchmarks=None):
    """Generate prompt for selecting benchmark reference projects.

    Args:
        projects_by_range: dict of {range_label: [top_projects]}
        existing_benchmarks: dict of current benchmarks for context
    """
    context = ""
    if existing_benchmarks:
        context = f"\nCurrent benchmarks: {json.dumps(existing_benchmarks, ensure_ascii=False)}\n"

    ranges_text = ""
    for label, projects in projects_by_range.items():
        top = sorted(projects, key=lambda p: p.get('total_score', 0), reverse=True)[:5]
        project_list = '\n'.join([
            f"  - {p.get('name')} (id={p.get('id')}, score={p.get('total_score', 0)}, stars={p.get('stars', 0)}, "
            f"type={p.get('resource_type', [])})"
            for p in top
        ])
        ranges_text += f"\n{label} (top candidates):\n{project_list}\n"

    return f"""Select one benchmark reference project for each score range.
The benchmark should be a well-known, stable project that represents the standard for that tier.
{context}
Candidate projects by score range:
{ranges_text}

Respond with JSON:
{{
  "benchmarks": {{
    "标杆": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "优秀": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "可用": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "萌芽": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "噪声": {{"project_id": "...", "project_name": "...", "reason": "..."}}
  }}
}}"""


# === Report Generation Prompts ===

def weekly_report_prompt(new_projects, score_changes, tracking_changes):
    """Generate prompt for weekly ecosystem report."""
    new_text = '\n'.join([
        f"- {p.get('name')} (score={p.get('total_score', 0)}, type={p.get('resource_type', [])})"
        for p in new_projects[:20]
    ])

    changes_text = '\n'.join([
        f"- {c.get('name')}: {c.get('old_score')} -> {c.get('new_score')} ({c.get('delta', 0):+.0f})"
        for c in score_changes[:10]
    ])

    tracking_text = f"- Added to tracking: {tracking_changes.get('new_track', 0)}\n"
    tracking_text += f"- Moved to index: {tracking_changes.get('new_index', 0)}\n"
    tracking_text += f"- Rejected: {tracking_changes.get('new_reject', 0)}"

    return f"""Write a weekly ecosystem report in Markdown for the AI Coding Agent ecosystem tracker.

## New Projects This Week
{new_text}

## Score Changes (Top Movers)
{changes_text}

## Tracking Changes
{tracking_text}

Write a report with:
1. ## 本周新发现 (highlight 3-5 most interesting new projects)
2. ## 分数变化 (notable score changes and why)
3. ## 追踪名单变动 (tracking list changes)
4. ## 生态趋势 (brief trend observation)

Keep it concise. Use Chinese for the report."""


def tool_comparison_prompt(tools_data):
    """Generate prompt for tool ecosystem comparison report."""
    tools_text = ""
    for t in tools_data:
        tools_text += f"\n{t['name']} ({t['id']}):\n"
        tools_text += f"  Total projects: {t['total']}\n"
        tools_text += f"  Curated: {t['curated']}\n"
        tools_text += f"  Avg score: {t['avg_score']}\n"
        tools_text += f"  Resource types: {t['type_distribution']}\n"

    return f"""Write a tool ecosystem comparison report in Markdown.

## Tool Data
{tools_text}

Write a report with:
1. ## 生态规模对比 (table comparing all tools)
2. ## 资源类型分布 (which tools have more MCP servers, skills, etc.)
3. ## 成熟度分析 (which ecosystems are more mature)
4. ## 机会缺口 (which tools lack ecosystem resources)

Use Chinese. Include markdown tables."""


def top_picks_prompt(curated_projects):
    """Generate prompt for curated top picks report."""
    projects_text = '\n'.join([
        f"- {p.get('name')} (score={p.get('total_score', 0)}, "
        f"type={p.get('resource_type', [])}, tools={p.get('target_tools', [])}, "
        f"stars={p.get('stars', 0)})"
        for p in curated_projects[:50]
    ])

    return f"""Write a top picks recommendation report in Markdown.

## Top 50 Projects
{projects_text}

Write a report with:
1. ## Top 10 精选 (top 10 with brief reason for each)
2. ## 分类推荐 (best MCP server, best skills collection, best rules, etc.)
3. ## 按工具推荐 (top 3 for each coding tool)

Use Chinese."""
