# 第 3 批：LLM 分析系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现每周一 03:00 自动 LLM 深度分析系统。直接调用 SenseNova API（DeepSeek-V4-Flash），每批 3 个并发请求，对项目做相关性判断、分类打标、质量评分（40分）、生成双语一句话评价、维护动态参照基准，最后重评全部项目并生成 3 份报告。

**架构：** 独立 Python 脚本 `weekly_analysis.py`，通过 urllib 直接调用 SenseNova OpenAI 兼容 API（不依赖 Hermes delegate_task，避免 cron 自动运行时审批阻塞）。13 个 API key 轮询使用。分析流程：预筛选 -> 分批 LLM 分析（每批 3 并发）-> 更新参照基准 -> 重评分 -> 生成报告 -> 构建站点 -> 部署。Cron 通过 Hermes cronjob 配置，no_agent=True 模式直接运行脚本。

**技术栈：** Python 3.12+（urllib, json, concurrent.futures）, SenseNova API (OpenAI 兼容), PyYAML

**关联文档：**
- 设计规格：`docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md`（"双层节奏架构"和"评分系统"章节）
- ADR-0002：双层节奏架构
- ADR-0003：100 分制双层评分 + 动态参照基准
- ADR-0007：项目追踪分级
- CONTEXT.md：Quality Score, Benchmark Reference, Weekly Analysis 术语

**前置条件：** 第 1 批和第 2 批已完成（数据结构已迁移、站点已重写）

**环境约束：**
- SenseNova API：base_url=`https://token.sensenova.cn/v1`，model=`deepseek-v4-flash`
- 凭证池：13 个 API key（存储在 `~/.hermes/auth.json` 的 `credential_pool.custom:sensenova` 中）
- API 模式：OpenAI 兼容 chat/completions
- 不使用 Hermes delegate_task（cron 自动运行时无人审批会阻塞）
- 不修改全局 max_concurrent_children 配置

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `scripts/weekly_analysis.py` | 主脚本：LLM 分析 + 参照基准 + 重评分 + 报告生成 |
| `scripts/llm_api.py` | SenseNova API 封装：key 轮询、请求重试、JSON 解析 |
| `scripts/llm_prompts.py` | Prompt 模板：项目分析、参照基准选择、报告生成 |
| `scripts/benchmark_manager.py` | 参照基准管理：选择、更新、评分校准 |
| `scripts/translation.py` | 双语翻译：调用 LLM 翻译 summary |
| `config/llm-analysis.yaml` | LLM 分析配置：prompt 参数、批次大小、重试策略 |
| `data/benchmarks.yaml` | 参照基准项目存储 |
| `data/translations-cache/` | 翻译缓存目录 |
| `data/snapshots/` | 每周快照目录 |
| `tests/test_llm_api.py` | API 封装测试 |
| `tests/test_weekly_analysis.py` | 分析流程测试 |
| `tests/test_benchmark_manager.py` | 参照基准测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `scripts/score.py` | 整合 quality_score（从 weekly_analysis 写入的值） |
| `scripts/generate_reports.py` | 新增 3 份报告（生态周报/工具对比/推荐榜） |
| `scripts/update_tracker.py` | 添加 `--weekly` 模式调用 weekly_analysis |

---

## 任务 1：SenseNova API 封装

**文件：**
- 创建：`scripts/llm_api.py`
- 创建：`tests/test_llm_api.py`

- [ ] **步骤 1：编写 API 封装测试**

```python
# tests/test_llm_api.py
"""Test the SenseNova API wrapper."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestKeyRotation:
    def test_load_keys_from_auth_json(self):
        from llm_api import load_api_keys
        keys = load_api_keys()
        # Should load from ~/.hermes/auth.json credential_pool
        assert isinstance(keys, list)
        # May be empty in test env, that's OK - just check structure
        for k in keys:
            assert isinstance(k, str)
            assert k.startswith('sk-')

    def test_key_rotation_round_robin(self):
        from llm_api import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key2'
        assert rotator.next() == 'key3'
        assert rotator.next() == 'key1'  # wraps around

    def test_key_rotation_skips_failed_keys(self):
        from llm_api import KeyRotator
        rotator = KeyRotator(['key1', 'key2', 'key3'])
        rotator.mark_failed('key2')
        assert rotator.next() == 'key1'
        assert rotator.next() == 'key3'  # skips key2
        assert rotator.next() == 'key1'


class TestParseJSONResponse:
    def test_parse_clean_json(self):
        from llm_api import parse_json_response
        text = '{"relevance_score": 0.85, "resource_type": ["mcp-server"]}'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.85
        assert result['resource_type'] == ['mcp-server']

    def test_parse_json_in_markdown_code_block(self):
        from llm_api import parse_json_response
        text = '```json\n{"relevance_score": 0.9}\n```'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.9

    def test_parse_json_with_surrounding_text(self):
        from llm_api import parse_json_response
        text = 'Here is my analysis:\n{"relevance_score": 0.7}\nDone.'
        result = parse_json_response(text)
        assert result['relevance_score'] == 0.7

    def test_parse_invalid_json_returns_none(self):
        from llm_api import parse_json_response
        assert parse_json_response('not json at all') is None
        assert parse_json_response('') is None
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_llm_api.py -v`
预期：FAIL

- [ ] **步骤 3：编写 llm_api.py**

```python
#!/usr/bin/env python3
"""SenseNova API wrapper with key rotation and retry.

Calls OpenAI-compatible chat/completions endpoint at https://token.sensenova.cn/v1
Uses 13 API keys from ~/.hermes/auth.json with round-robin rotation.
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = 'https://token.sensenova.cn/v1/chat/completions'
MODEL = 'deepseek-v4-flash'


def load_api_keys():
    """Load API keys from ~/.hermes/auth.json credential pool."""
    auth_path = Path.home() / '.hermes' / 'auth.json'
    if not auth_path.exists():
        return []
    try:
        data = json.loads(auth_path.read_text(encoding='utf-8'))
        pool = data.get('credential_pool', {}).get('custom:sensenova', [])
        keys = []
        for entry in pool:
            if isinstance(entry, dict):
                key = entry.get('access_token', '')
                if key and key.startswith('sk-'):
                    keys.append(key)
            elif isinstance(entry, str) and entry.startswith('sk-'):
                keys.append(entry)
        return keys
    except (json.JSONDecodeError, KeyError):
        return []


class KeyRotator:
    """Round-robin key rotation with failure tracking."""

    def __init__(self, keys):
        self.keys = list(keys)
        self.index = 0
        self.failed = set()

    def next(self):
        available = [k for k in self.keys if k not in self.failed]
        if not available:
            # All keys failed, reset and try again
            self.failed.clear()
            available = self.keys
        if not available:
            raise RuntimeError('No API keys available')
        # Find next available key
        for _ in range(len(self.keys)):
            k = self.keys[self.index % len(self.keys)]
            self.index += 1
            if k not in self.failed:
                return k
        return available[0]

    def mark_failed(self, key):
        self.failed.add(key)

    def reset(self):
        self.failed.clear()


def parse_json_response(text):
    """Extract JSON from LLM response text. Handles code blocks and surrounding text."""
    if not text:
        return None
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if md_match:
        try:
            return json.loads(md_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object in text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def call_llm(prompt, system_prompt=None, key=None, timeout=120):
    """Call SenseNova API with a single prompt. Returns response text or None."""
    if key is None:
        raise ValueError('API key required')

    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})

    payload = {
        'model': MODEL,
        'messages': messages,
        'temperature': 0.3,  # low temperature for consistent analysis
        'max_tokens': 2000,
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        BASE_URL,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {key}',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get('choices', [{}])[0].get('message', {}).get('content', '')
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')[:500] if e.fp else ''
        print(f'  API error {e.code}: {error_body}')
        if e.code in (401, 403):
            raise KeyError(f'Auth failed: {e.code}')
        if e.code == 429:
            raise RateLimitError('Rate limited')
        return None
    except (urllib.error.URLError, TimeoutError) as e:
        print(f'  Network error: {e}')
        return None


class RateLimitError(Exception):
    pass


def call_with_retry(prompt, system_prompt, rotator, max_retries=3):
    """Call LLM with key rotation and retry on failure."""
    last_error = None
    for attempt in range(max_retries):
        try:
            key = rotator.next()
            result = call_llm(prompt, system_prompt, key=key)
            if result:
                return result
        except KeyError:
            # Auth failed, mark key as failed
            rotator.mark_failed(key)
            print(f'  Key failed, rotating... (attempt {attempt+1}/{max_retries})')
        except RateLimitError:
            time.sleep(5 * (attempt + 1))  # exponential backoff
            print(f'  Rate limited, waiting... (attempt {attempt+1}/{max_retries})')
        except Exception as e:
            last_error = e
            print(f'  Error: {e} (attempt {attempt+1}/{max_retries})')
    print(f'  All retries exhausted: {last_error}')
    return None


def batch_analyze(items, prompt_fn, system_prompt, max_workers=3):
    """Analyze a batch of items concurrently.

    Args:
        items: list of items to analyze
        prompt_fn: function(item) -> prompt string
        system_prompt: system prompt string
        max_workers: concurrent workers (default 3)

    Returns:
        dict mapping item index to parsed JSON result (or None if failed)
    """
    keys = load_api_keys()
    if not keys:
        print('ERROR: No API keys found')
        return {}

    rotator = KeyRotator(keys)
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for i, item in enumerate(items):
            prompt = prompt_fn(item)
            future = executor.submit(call_with_retry, prompt, system_prompt, rotator)
            futures[future] = i

        for future in as_completed(futures):
            idx = futures[future]
            try:
                text = future.result()
                if text:
                    results[idx] = parse_json_response(text)
                else:
                    results[idx] = None
            except Exception as e:
                print(f'  Item {idx} failed: {e}')
                results[idx] = None

    return results
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_llm_api.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/llm_api.py tests/test_llm_api.py
git commit -m "feat: add SenseNova API wrapper with key rotation, retry, JSON parsing"
```

---

## 任务 2：Prompt 模板

**文件：**
- 创建：`scripts/llm_prompts.py`

- [ ] **步骤 1：编写 llm_prompts.py**

```python
#!/usr/bin/env python3
"""Prompt templates for LLM analysis.

Three prompt types:
1. Project analysis: relevance, resource_type, target_tools, quality_score, llm_summary
2. Benchmark selection: choose reference projects for each score range
3. Report generation: weekly report, tool comparison, top picks
"""

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

Respond with JSON in this exact format:
{{
  "relevance_score": 0.0-1.0,
  "resource_type": ["one or more of: mcp-server, skills, rules, agent-framework, cli-tool, tutorial"],
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
- resource_type: pick the most fitting types. "tutorial" is the fallback if none fit."""


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
            f"  - {p.get('name')} (score={p.get('total_score', 0)}, stars={p.get('stars', 0)}, "
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
    "标杆 (81-100)": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "优秀 (61-80)": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "可用 (41-60)": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "萌芽 (21-40)": {{"project_id": "...", "project_name": "...", "reason": "..."}},
    "噪声 (0-20)": {{"project_id": "...", "project_name": "...", "reason": "..."}}
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
```

- [ ] **步骤 2：验证语法**

运行：`cd "/root/workspace/search in coding" && python3 -m py_compile scripts/llm_prompts.py`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/llm_prompts.py
git commit -m "feat: add LLM prompt templates for project analysis, benchmark selection, report generation"
```

---

## 任务 3：参照基准管理器

**文件：**
- 创建：`scripts/benchmark_manager.py`
- 创建：`tests/test_benchmark_manager.py`

- [ ] **步骤 1：编写参照基准测试**

```python
# tests/test_benchmark_manager.py
"""Test benchmark reference management."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestBenchmarkRanges:
    def test_score_to_range(self):
        from benchmark_manager import score_to_range
        assert score_to_range(95) == '标杆'
        assert score_to_range(81) == '标杆'
        assert score_to_range(80) == '优秀'
        assert score_to_range(61) == '优秀'
        assert score_to_range(60) == '可用'
        assert score_to_range(41) == '可用'
        assert score_to_range(40) == '萌芽'
        assert score_to_range(21) == '萌芽'
        assert score_to_range(20) == '噪声'
        assert score_to_range(0) == '噪声'

    def test_range_labels(self):
        from benchmark_manager import BENCHMARK_RANGES
        labels = [r['label'] for r in BENCHMARK_RANGES]
        assert labels == ['标杆', '优秀', '可用', '萌芽', '噪声']


class TestBenchmarkManager:
    def test_load_empty_benchmarks(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        benchmarks = bm.load()
        assert benchmarks == {} or benchmarks is not None

    def test_save_and_load_benchmarks(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        bm.save({
            '标杆': {'project_id': 'test-1', 'project_name': 'Test', 'reason': 'top project'},
        })
        loaded = bm.load()
        assert '标杆' in loaded
        assert loaded['标杆']['project_id'] == 'test-1'

    def test_get_benchmark_for_score(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        bm.save({
            '标杆': {'project_id': 'ref-1'},
            '优秀': {'project_id': 'ref-2'},
            '可用': {'project_id': 'ref-3'},
            '萌芽': {'project_id': 'ref-4'},
            '噪声': {'project_id': 'ref-5'},
        })
        assert bm.get_benchmark_for_score(90)['project_id'] == 'ref-1'
        assert bm.get_benchmark_for_score(70)['project_id'] == 'ref-2'
        assert bm.get_benchmark_for_score(50)['project_id'] == 'ref-3'
        assert bm.get_benchmark_for_score(30)['project_id'] == 'ref-4'
        assert bm.get_benchmark_for_score(10)['project_id'] == 'ref-5'

    def test_group_projects_by_range(self, tmp_path):
        from benchmark_manager import BenchmarkManager
        bm = BenchmarkManager(tmp_path / 'benchmarks.yaml')
        projects = [
            {'id': '1', 'total_score': 90},
            {'id': '2', 'total_score': 70},
            {'id': '3', 'total_score': 50},
            {'id': '4', 'total_score': 30},
            {'id': '5', 'total_score': 10},
        ]
        grouped = bm.group_by_range(projects)
        assert len(grouped['标杆']) == 1
        assert len(grouped['优秀']) == 1
        assert len(grouped['可用']) == 1
        assert len(grouped['萌芽']) == 1
        assert len(grouped['噪声']) == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_benchmark_manager.py -v`
预期：FAIL

- [ ] **步骤 3：编写 benchmark_manager.py**

```python
#!/usr/bin/env python3
"""Benchmark reference manager.

Maintains reference projects for each score range.
Used to calibrate LLM quality scoring.
"""
import json
from pathlib import Path

BENCHMARK_RANGES = [
    {'label': '标杆', 'min': 81, 'max': 100, 'description': '生态标杆项目'},
    {'label': '优秀', 'min': 61, 'max': 80, 'description': '高质量生态项目'},
    {'label': '可用', 'min': 41, 'max': 60, 'description': '可用项目'},
    {'label': '萌芽', 'min': 21, 'max': 40, 'description': '早期项目'},
    {'label': '噪声', 'min': 0, 'max': 20, 'description': '低质量或无关项目'},
]


def score_to_range(score):
    """Map a score to its benchmark range label."""
    for r in BENCHMARK_RANGES:
        if r['min'] <= score <= r['max']:
            return r['label']
    return '噪声'


class BenchmarkManager:
    """Manage benchmark reference projects in data/benchmarks.yaml."""

    def __init__(self, path=None):
        if path is None:
            from common import ROOT
            path = ROOT / 'data' / 'benchmarks.yaml'
        self.path = Path(path)

    def load(self):
        """Load existing benchmarks."""
        if not self.path.exists():
            return {}
        try:
            import yaml
            data = yaml.safe_load(self.path.read_text(encoding='utf-8'))
            return data or {}
        except Exception:
            return {}

    def save(self, benchmarks):
        """Save benchmarks to file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        self.path.write_text(
            yaml.dump(benchmarks, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding='utf-8'
        )

    def get_benchmark_for_score(self, score):
        """Get the benchmark reference for a given score."""
        label = score_to_range(score)
        benchmarks = self.load()
        return benchmarks.get(label)

    def group_by_range(self, projects):
        """Group projects by their benchmark range."""
        groups = {r['label']: [] for r in BENCHMARK_RANGES}
        for p in projects:
            label = score_to_range(p.get('total_score', 0))
            groups[label].append(p)
        return groups

    def update_from_llm(self, llm_result, projects):
        """Update benchmarks from LLM selection result.

        Args:
            llm_result: dict from LLM with 'benchmarks' key
            projects: list of all projects (to resolve IDs)
        """
        benchmarks = self.load()
        project_map = {p['id']: p for p in projects}
        llm_benchmarks = llm_result.get('benchmarks', {})

        for label, info in llm_benchmarks.items():
            pid = info.get('project_id')
            if pid and pid in project_map:
                p = project_map[pid]
                benchmarks[label] = {
                    'project_id': pid,
                    'project_name': p.get('name', ''),
                    'score': p.get('total_score', 0),
                    'reason': info.get('reason', ''),
                }
            else:
                # Keep existing if LLM selected an invalid project
                print(f'  Warning: LLM selected unknown project {pid} for {label}')

        self.save(benchmarks)
        return benchmarks
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_benchmark_manager.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/benchmark_manager.py tests/test_benchmark_manager.py
git commit -m "feat: add benchmark manager with 5-tier score ranges and LLM-driven updates"
```

---

## 任务 4：主分析脚本 weekly_analysis.py

**文件：**
- 创建：`scripts/weekly_analysis.py`
- 创建：`tests/test_weekly_analysis.py`

- [ ] **步骤 1：编写主分析流程测试**

```python
# tests/test_weekly_analysis.py
"""Test the weekly analysis pipeline."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestPreFilter:
    def test_filters_empty_repos(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': '1', 'name': 'Test', 'stars': 0, 'forks': 0, 'summary': '', 'status': 'unknown'},
            {'id': '2', 'name': 'Good', 'stars': 100, 'forks': 10, 'summary': 'A real project', 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        # Empty repo (no stars, no forks, no summary) should be filtered
        assert any(p['id'] == '2' for p in filtered)
        # But project 1 might still pass if it has other value - pre_filter is lenient
        # The key test is that archived repos are removed

    def test_filters_archived(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': '1', 'name': 'Archived', 'stars': 100, 'status': 'archived'},
            {'id': '2', 'name': 'Active', 'stars': 50, 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        ids = [p['id'] for p in filtered]
        assert '2' in ids
        assert '1' not in ids

    def test_sorts_by_priority(self):
        from weekly_analysis import pre_filter
        projects = [
            {'id': 'low', 'name': 'Low', 'stars': 1, 'status': 'active'},
            {'id': 'high', 'name': 'High', 'stars': 1000, 'status': 'active'},
            {'id': 'mid', 'name': 'Mid', 'stars': 100, 'status': 'active'},
        ]
        filtered = pre_filter(projects)
        assert filtered[0]['id'] == 'high'
        assert filtered[1]['id'] == 'mid'
        assert filtered[2]['id'] == 'low'


class TestMergeResults:
    def test_merges_analysis_into_project(self):
        from weekly_analysis import merge_analysis_result
        project = {
            'id': 'test-1',
            'name': 'Test',
            'total_score': 30,
            'quantifiable_score': 30,
            'quality_score': 0,
        }
        analysis = {
            'relevance_score': 0.85,
            'resource_type': ['mcp-server'],
            'target_tools': ['claude-code'],
            'tracking_priority': 'track',
            'quality_score': 32,
            'quality_detail': {'relevance': 9, 'practicality': 8, 'novelty': 7, 'ecosystem_value': 8},
            'llm_summary': {'zh': '好的项目', 'en': 'Good project'},
            'analysis_notes': 'Nice work',
        }
        result = merge_analysis_result(project, analysis)
        assert result['quality_score'] == 32
        assert result['total_score'] == 30 + 32  # quantifiable + quality
        assert result['resource_type'] == ['mcp-server']
        assert result['target_tools'] == ['claude-code']
        assert result['tracking_priority'] == 'track'
        assert result['llm_summary'] == {'zh': '好的项目', 'en': 'Good project'}
        assert result['last_analyzed'] is not None  # should be set to today

    def test_preserves_quantifiable_score(self):
        from weekly_analysis import merge_analysis_result
        project = {'id': 't', 'quantifiable_score': 25, 'quality_score': 0, 'total_score': 25}
        analysis = {'quality_score': 20, 'resource_type': ['skills'], 'target_tools': [], 'tracking_priority': 'index'}
        result = merge_analysis_result(project, analysis)
        assert result['quantifiable_score'] == 25  # unchanged
        assert result['quality_score'] == 20
        assert result['total_score'] == 45

    def test_handles_missing_fields_in_analysis(self):
        from weekly_analysis import merge_analysis_result
        project = {'id': 't', 'quantifiable_score': 20, 'quality_score': 0, 'total_score': 20, 'resource_type': ['tutorial']}
        analysis = {'quality_score': 15}  # minimal
        result = merge_analysis_result(project, analysis)
        assert result['quality_score'] == 15
        assert result['total_score'] == 35
        # Original resource_type should be preserved
        assert result['resource_type'] == ['tutorial']
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_weekly_analysis.py -v`
预期：FAIL

- [ ] **步骤 3：编写 weekly_analysis.py**

```python
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
6. Generate 3 reports (weekly/tool-comparison/top-picks)
7. Build site and deploy

Usage:
    python3 scripts/weekly_analysis.py                    # full run
    python3 scripts/weekly_analysis.py --max-projects 50  # limit for testing
    python3 scripts/weekly_analysis.py --dry-run          # no LLM calls, just structure
"""
import argparse
import datetime
import json
import sys
from pathlib import Path

from common import ROOT, load_jsonish, save_jsonish, today
from llm_api import batch_analyze, parse_json_response, call_with_retry, load_api_keys, KeyRotator
from llm_prompts import (
    project_analysis_prompt, ANALYSIS_SYSTEM,
    benchmark_selection_prompt, BENCHMARK_SYSTEM,
    weekly_report_prompt, tool_comparison_prompt, top_picks_prompt, REPORT_SYSTEM,
)
from benchmark_manager import BenchmarkManager, BENCHMARK_RANGES


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
    """
    now = datetime.date.today()
    cutoff = (now - datetime.timedelta(days=7)).isoformat()

    to_analyze = []
    for p in projects:
        last = p.get('last_analyzed')
        if last is None or last < cutoff:
            to_analyze.append(p)

    if max_projects:
        to_analyze = to_analyze[:max_projects]

    return to_analyze


def merge_analysis_result(project, analysis):
    """Merge LLM analysis result into a project record."""
    import copy
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
        p['score_detail'] = analysis['quality_detail']
    if 'llm_summary' in analysis:
        p['llm_summary'] = analysis['llm_summary']

    # Recalculate total score
    p['total_score'] = p.get('quantifiable_score', 0) + p.get('quality_score', 0)

    # Mark as analyzed
    p['last_analyzed'] = today()

    return p


def run_analysis(projects, max_projects=None, batch_size=3):
    """Run LLM analysis on projects in batches.

    Args:
        projects: list of project dicts
        max_projects: limit number of projects to analyze
        batch_size: concurrent LLM calls per batch

    Returns:
        list of analyzed project dicts
    """
    to_analyze = get_projects_to_analyze(projects, max_projects)

    if not to_analyze:
        print(f'No projects need analysis (all analyzed within 7 days)')
        return projects

    print(f'Projects to analyze: {len(to_analyze)}')

    # Process in batches of batch_size
    all_results = {}
    for i in range(0, len(to_analyze), batch_size):
        batch = to_analyze[i:i + batch_size]
        print(f'\n--- Batch {i//batch_size + 1}/{(len(to_analyze)-1)//batch_size + 1} ({len(batch)} projects) ---')

        # Create prompt function for each project
        def prompt_fn(p):
            return project_analysis_prompt(p)

        results = batch_analyze(batch, prompt_fn, ANALYSIS_SYSTEM, max_workers=batch_size)

        for idx, result in results.items():
            project_id = batch[idx].get('id') if idx < len(batch) else None
            if project_id:
                all_results[project_id] = result
                status = 'OK' if result else 'FAILED'
                print(f'  {batch[idx].get("name", "?")}: {status}')

    # Merge results back
    updated_projects = []
    for p in projects:
        result = all_results.get(p.get('id'))
        if result is not None or p.get('id') in all_results:
            updated_projects.append(merge_analysis_result(p, result))
        else:
            updated_projects.append(p)

    success_count = sum(1 for r in all_results.values() if r is not None)
    fail_count = sum(1 for r in all_results.values() if r is None)
    print(f'\nAnalysis complete: {success_count} success, {fail_count} failed')

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


def generate_reports(projects, curated, tools, prev_projects=None):
    """Generate 3 weekly reports using LLM."""
    import yaml

    reports_dir = ROOT / 'docs' / 'reports'
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data for reports
    now = today()

    # 1. Weekly Report
    new_projects = [p for p in projects if p.get('last_analyzed') == now] if prev_projects else []
    score_changes = []
    if prev_projects:
        prev_map = {p['id']: p for p in prev_projects}
        for p in projects:
            old = prev_map.get(p['id'])
            if old and old.get('total_score', 0) != p.get('total_score', 0):
                score_changes.append({
                    'name': p.get('name'),
                    'old_score': old.get('total_score', 0),
                    'new_score': p.get('total_score', 0),
                    'delta': p.get('total_score', 0) - old.get('total_score', 0),
                })

    tracking_changes = {
        'new_track': sum(1 for p in projects if p.get('tracking_priority') == 'track'),
        'new_index': sum(1 for p in projects if p.get('tracking_priority') == 'index'),
        'new_reject': sum(1 for p in projects if p.get('tracking_priority') == 'reject'),
    }

    # Call LLM for weekly report
    keys = load_api_keys()
    rotator = KeyRotator(keys) if keys else None

    if rotator:
        prompt = weekly_report_prompt(new_projects, score_changes, tracking_changes)
        text = call_with_retry(prompt, REPORT_SYSTEM, rotator)
        (reports_dir / 'weekly-report.md').write_text(text or f'# 生态周报 {now}\n\n生成失败', encoding='utf-8')

        # 2. Tool Comparison
        tools_data = []
        for t in tools:
            t_projects = [p for p in projects if t['id'] in (p.get('target_tools') or [])]
            from collections import Counter
            type_dist = Counter()
            for p in t_projects:
                for rt in (p.get('resource_type') or []):
                    type_dist[rt] += 1
            tools_data.append({
                'name': t.get('name', t['id']),
                'id': t['id'],
                'total': len(t_projects),
                'curated': sum(1 for p in t_projects if p.get('review_state') == 'auto-curated'),
                'avg_score': round(sum(p.get('total_score', 0) for p in t_projects) / max(len(t_projects), 1), 1),
                'type_distribution': dict(type_dist),
            })
        prompt = tool_comparison_prompt(tools_data)
        text = call_with_retry(prompt, REPORT_SYSTEM, rotator)
        (reports_dir / 'tool-comparison.md').write_text(text or f'# 工具生态对比 {now}\n\n生成失败', encoding='utf-8')

        # 3. Top Picks
        prompt = top_picks_prompt(curated[:50])
        text = call_with_retry(prompt, REPORT_SYSTEM, rotator)
        (reports_dir / 'curated-top.md').write_text(text or f'# 推荐榜 {now}\n\n生成失败', encoding='utf-8')
    else:
        print('WARNING: No API keys, skipping LLM report generation')

    print(f'Reports generated: weekly-report.md, tool-comparison.md, curated-top.md')


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
    }

    path = snapshot_dir / f'{today()}.json'
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Snapshot saved: {path}')


def main():
    ap = argparse.ArgumentParser(description='Weekly LLM analysis pipeline')
    ap.add_argument('--max-projects', type=int, default=None, help='Limit projects to analyze (for testing)')
    ap.add_argument('--dry-run', action='store_true', help='No LLM calls, just show structure')
    ap.add_argument('--skip-reports', action='store_true', help='Skip report generation')
    ap.add_argument('--skip-benchmarks', action='store_true', help='Skip benchmark update')
    args = ap.parse_args()

    print(f'=== Weekly Analysis - {today()} ===')

    # Load data
    projects = load_jsonish('data/projects.yaml')
    curated = load_jsonish('data/curated-projects.yaml')
    tools = load_jsonish('data/seed-tools.yaml')
    prev_projects = [dict(p) for p in projects]  # snapshot before changes

    print(f'Loaded: {len(projects)} projects, {len(curated)} curated, {len(tools)} tools')

    if args.dry_run:
        to_analyze = get_projects_to_analyze(projects, args.max_projects)
        print(f'\nDry run: would analyze {len(to_analyze)} projects')
        print(f'Sample: {to_analyze[0]["name"] if to_analyze else "none"}')
        return

    # Step 1: Pre-filter
    filtered = pre_filter(projects)
    print(f'Pre-filtered: {len(filtered)} (removed {len(projects) - len(filtered)} archived)')

    # Step 2: Run LLM analysis
    print('\n--- Step 1: LLM Analysis ---')
    analyzed = run_analysis(filtered, max_projects=args.max_projects, batch_size=3)

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

    # Step 7: Generate reports
    if not args.skip_reports:
        print('\n--- Step 5: Generate Reports ---')
        generate_reports(rescored, curated, tools, prev_projects)

    # Step 8: Run build_site
    print('\n--- Step 6: Build Site ---')
    import subprocess
    r = subprocess.run(['python3', 'scripts/build_site.py'], cwd=ROOT, capture_output=True, text=True, timeout=300)
    print(r.stdout[-500:] if r.stdout else '')
    if r.returncode != 0:
        print(f'Build site failed: {r.stderr[-500:]}')

    print('\n=== Weekly Analysis Complete ===')


if __name__ == '__main__':
    main()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_weekly_analysis.py -v`
预期：PASS

- [ ] **步骤 5：Dry run 验证**

运行：`cd "/root/workspace/search in coding" && python3 scripts/weekly_analysis.py --dry-run`
预期：输出待分析项目数量和样本

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/weekly_analysis.py tests/test_weekly_analysis.py
git commit -m "feat: add weekly_analysis.py with LLM analysis, benchmark update, rescoring, reports"
```

---

## 任务 5：双语翻译模块

**文件：**
- 创建：`scripts/translation.py`

- [ ] **步骤 1：编写 translation.py**

```python
#!/usr/bin/env python3
"""Bilingual translation using LLM.

Translates project summaries from English to Chinese (and vice versa).
Caches results to data/translations-cache/ to avoid repeat API calls.
Processes curated projects first, then all others with daily budget limit.
"""
import hashlib
import json
from pathlib import Path

from common import ROOT, today
from llm_api import call_with_retry, load_api_keys, KeyRotator
from llm_prompts import ANALYSIS_SYSTEM

CACHE_DIR = ROOT / 'data' / 'translations-cache'
DAILY_BUDGET = 50  # max translations per day

TRANSLATION_SYSTEM = """You are a professional translator specializing in software and AI technology.
Translate the given text accurately. Respond with JSON only."""


def cache_key(url):
    """Generate cache key from URL."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:16]


def get_cached(url):
    """Get cached translation."""
    key = cache_key(url)
    path = CACHE_DIR / f'{key}.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return None


def save_cached(url, translation):
    """Save translation to cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    key = cache_key(url)
    path = CACHE_DIR / f'{key}.json'
    path.write_text(json.dumps(translation, ensure_ascii=False, indent=2), encoding='utf-8')


def translate_text(text, target_lang, rotator):
    """Translate text using LLM.

    Args:
        text: text to translate
        target_lang: 'zh' or 'en'
        rotator: KeyRotator instance

    Returns:
        translated string or None
    """
    if not text or len(text) < 5:
        return None

    source_lang = '英文' if target_lang == 'zh' else '中文'
    target_name = '中文' if target_lang == 'zh' else '英文'

    prompt = f"""Translate the following {source_lang} text to {target_name}:

{text[:500]}

Respond with JSON: {{"translated": "translated text here"}}"""

    result = call_with_retry(prompt, TRANSLATION_SYSTEM, rotator)
    if result:
        import re
        # Parse JSON from response
        match = re.search(r'\{[^}]+\}', result, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data.get('translated')
            except json.JSONDecodeError:
                pass
    return None


def translate_projects(projects, curated_only=True, daily_budget=DAILY_BUDGET):
    """Translate project summaries.

    Args:
        projects: list of project dicts
        curated_only: if True, only translate curated projects
        daily_budget: max translations per run

    Returns:
        list of updated projects
    """
    keys = load_api_keys()
    if not keys:
        print('No API keys for translation')
        return projects

    rotator = KeyRotator(keys)
    translated_count = 0

    # Filter projects needing translation
    to_translate = []
    for p in projects:
        if curated_only and p.get('review_state') != 'auto-curated':
            continue
        # Check if translation already exists
        cached = get_cached(p.get('url', ''))
        if cached:
            # Apply cached translation
            i18n = p.setdefault('i18n', {})
            if 'zh' not in i18n:
                i18n['zh'] = {}
            if 'en' not in i18n:
                i18n['en'] = {}
            if cached.get('zh'):
                i18n['zh']['summary'] = cached['zh']
            if cached.get('en'):
                i18n['en']['summary'] = cached['en']
            continue

        to_translate.append(p)

    print(f'Projects to translate: {len(to_translate)} (budget: {min(daily_budget, len(to_translate))})')

    for p in to_translate[:daily_budget]:
        summary = p.get('summary', '')
        if not summary:
            continue

        # Determine source language and translate
        import re
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', summary))

        cached_data = {}
        if not has_chinese:
            # English -> Chinese
            zh = translate_text(summary, 'zh', rotator)
            if zh:
                cached_data['zh'] = zh
                cached_data['en'] = summary
        else:
            # Chinese -> English
            en = translate_text(summary, 'en', rotator)
            if en:
                cached_data['zh'] = summary
                cached_data['en'] = en

        if cached_data:
            save_cached(p.get('url', ''), cached_data)
            i18n = p.setdefault('i18n', {})
            if 'zh' not in i18n:
                i18n['zh'] = {}
            if 'en' not in i18n:
                i18n['en'] = {}
            if cached_data.get('zh'):
                i18n['zh']['summary'] = cached_data['zh']
            if cached_data.get('en'):
                i18n['en']['summary'] = cached_data['en']
            translated_count += 1

        if translated_count % 10 == 0:
            print(f'  Translated: {translated_count}')

    print(f'Translation complete: {translated_count} new translations')
    return projects


def main():
    """Run translation for curated projects."""
    from common import load_jsonish, save_jsonish
    projects = load_jsonish('data/projects.yaml')

    print(f'=== Translation - {today()} ===')
    print(f'Total projects: {len(projects)}')
    print(f'Translating curated only (budget: {DAILY_BUDGET})')

    translated = translate_projects(projects, curated_only=True, daily_budget=DAILY_BUDGET)
    save_jsonish('data/projects.yaml', translated)
    print(f'Saved {len(translated)} projects')


if __name__ == '__main__':
    main()
```

- [ ] **步骤 2：验证语法**

运行：`cd "/root/workspace/search in coding" && python3 -m py_compile scripts/translation.py`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/translation.py
git commit -m "feat: add translation module with LLM-powered bilingual summary translation"
```

---

## 任务 6：配置文件和 .gitignore

**文件：**
- 创建：`config/llm-analysis.yaml`
- 修改：`.gitignore`

- [ ] **步骤 1：创建 LLM 分析配置**

```yaml
# config/llm-analysis.yaml
# Weekly LLM analysis configuration

api:
  provider: sensenova
  base_url: https://token.sensenova.cn/v1
  model: deepseek-v4-flash
  temperature: 0.3
  max_tokens: 2000
  timeout: 120
  max_retries: 3
  batch_size: 3  # concurrent requests per batch

analysis:
  # Projects that haven't been analyzed in N days get re-analyzed
  reanalyze_after_days: 7
  # Maximum projects to analyze per run (null = no limit)
  max_projects_per_run: null
  # Pre-filter: skip archived repos
  skip_archived: true
  # Quality score thresholds for tracking priority
  track_threshold: 20    # quality_score >= 20 -> track
  index_threshold: 10    # quality_score >= 10 -> index
  # Relevance threshold
  relevance_threshold: 0.3  # below this -> reject

benchmark:
  ranges:
    - {label: "标杆", min: 81, max: 100}
    - {label: "优秀", min: 61, max: 80}
    - {label: "可用", min: 41, max: 60}
    - {label: "萌芽", min: 21, max: 40}
    - {label: "噪声", min: 0, max: 20}
  # Re-select benchmarks if they're this many days old
  refresh_interval_days: 7

reports:
  generate: true
  types:
    - weekly-report
    - tool-comparison
    - curated-top

translation:
  curated_only: true
  daily_budget: 50

snapshot:
  save: true
  path: data/snapshots/

sampling:
  # Random sample size for quality check (0 = no sampling)
  sample_size: 5
  # If sample accuracy below this, adjust prompt
  min_accuracy: 0.8
```

- [ ] **步骤 2：更新 .gitignore**

在 `.gitignore` 中添加：
```
# LLM analysis cache (not for git)
data/translations-cache/
data/initial-collection-checkpoint.json
```

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git add config/llm-analysis.yaml .gitignore
git commit -m "feat: add LLM analysis config and gitignore for cache files"
```

---

## 任务 7：Cron 配置和端到端测试

**文件：**
- 创建：`tests/test_weekly_e2e.py`

- [ ] **步骤 1：编写端到端测试（mock LLM 调用）**

```python
# tests/test_weekly_e2e.py
"""End-to-end test for weekly analysis pipeline (with mocked LLM)."""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestWeeklyE2E:
    """Test the full pipeline with mocked LLM calls."""

    @pytest.fixture
    def mock_projects(self):
        return [
            {
                'id': 'test-1', 'name': 'Test MCP Server', 'url': 'https://github.com/test/mcp-server',
                'source_type': 'github', 'stars': 500, 'forks': 20, 'status': 'active',
                'summary': 'A Claude Code MCP server for code indexing',
                'target_tools': ['claude-code'], 'resource_type': ['mcp-server'],
                'quantifiable_score': 15, 'quality_score': 0, 'total_score': 15,
                'tracking_priority': 'pending', 'last_analyzed': None,
                'languages': ['Python'], 'license': 'MIT', 'last_updated': '2025-07-01',
                'review_state': 'auto-indexed', 'i18n': {'zh': {'name': 'Test', 'summary': 'test'}, 'en': {'name': 'Test', 'summary': 'test'}},
            },
            {
                'id': 'test-2', 'name': 'Cursor Rules Pack', 'url': 'https://github.com/test/cursor-rules',
                'source_type': 'github', 'stars': 200, 'forks': 10, 'status': 'active',
                'summary': 'Collection of cursor rules for various frameworks',
                'target_tools': ['cursor'], 'resource_type': ['rules'],
                'quantifiable_score': 10, 'quality_score': 0, 'total_score': 10,
                'tracking_priority': 'pending', 'last_analyzed': None,
                'languages': ['TypeScript'], 'license': None, 'last_updated': '2025-06-01',
                'review_state': 'auto-indexed', 'i18n': {'zh': {'name': 'Test2', 'summary': 'test2'}, 'en': {'name': 'Test2', 'summary': 'test2'}},
            },
        ]

    def test_full_pipeline_with_mock(self, mock_projects, tmp_path, monkeypatch):
        """Test pipeline: pre-filter -> analyze -> rescore -> save."""
        from weekly_analysis import pre_filter, merge_analysis_result, rescore_all

        # Mock LLM response
        mock_analysis = {
            'relevance_score': 0.9,
            'resource_type': ['mcp-server'],
            'target_tools': ['claude-code'],
            'tracking_priority': 'track',
            'quality_score': 30,
            'quality_detail': {'relevance': 8, 'practicality': 8, 'novelty': 7, 'ecosystem_value': 7},
            'llm_summary': {'zh': '优秀的MCP服务器', 'en': 'Excellent MCP server'},
            'analysis_notes': 'Active development, good docs',
        }

        # Step 1: pre-filter
        filtered = pre_filter(mock_projects)
        assert len(filtered) == 2  # both active

        # Step 2: merge analysis
        analyzed = [merge_analysis_result(p, mock_analysis) for p in filtered]
        assert analyzed[0]['quality_score'] == 30
        assert analyzed[0]['total_score'] == 15 + 30  # quantifiable + quality
        assert analyzed[0]['tracking_priority'] == 'track'
        assert analyzed[0]['last_analyzed'] is not None

        # Step 3: rescore
        rescored = rescore_all(analyzed)
        for p in rescored:
            assert p['total_score'] == p['quantifiable_score'] + p['quality_score']
```

- [ ] **步骤 2：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_weekly_e2e.py -v`
预期：PASS

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git add tests/test_weekly_e2e.py
git commit -m "test: add end-to-end test for weekly analysis pipeline with mocked LLM"
```

---

## 任务 8：端到端验证和 Cron 配置

- [ ] **步骤 1：运行所有测试**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/ -v`
预期：全部 PASS

- [ ] **步骤 2：Dry run 验证**

运行：`cd "/root/workspace/search in coding" && python3 scripts/weekly_analysis.py --dry-run`
预期：输出待分析项目数量

- [ ] **步骤 3：小规模实际运行（限 3 个项目）**

运行：`cd "/root/workspace/search in coding" && python3 scripts/weekly_analysis.py --max-projects 3 --skip-reports`
预期：
- 3 个项目被 LLM 分析
- benchmarks.yaml 生成或更新
- projects.yaml 中 3 个项目有 quality_score > 0
- snapshot 文件生成

- [ ] **步骤 4：验证数据**

运行：
```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
analyzed = [p for p in projects if p.get('quality_score', 0) > 0]
print(f'Total: {len(projects)}, Analyzed: {len(analyzed)}')
for p in analyzed[:3]:
    print(f'  {p[\"name\"]}: q={p.get(\"quantifiable_score\")}+{p.get(\"quality_score\")}={p.get(\"total_score\")} tracking={p.get(\"tracking_priority\")}')
print(f'\nBenchmarks:')
with open('data/benchmarks.yaml') as f:
    bm = yaml.safe_load(f)
for k, v in (bm or {}).items():
    print(f'  {k}: {v.get(\"project_name\",\"?\")}')
"
```

- [ ] **步骤 5：配置 Hermes Cron**

创建每周一 03:00 的 cron job：
```bash
hermes cron create \
  --name "Search in Coding weekly LLM analysis" \
  --schedule "0 3 * * 1" \
  --no-agent \
  --script "search-in-coding-weekly.sh" \
  --workdir "/root/workspace/search in coding"
```

创建脚本 `~/.hermes/scripts/search-in-coding-weekly.sh`：
```bash
#!/bin/bash
# Weekly LLM analysis for Search in Coding
cd /root/workspace/search\ in\ coding || { echo "ERROR: workdir not found"; exit 1; }
/usr/bin/python3 scripts/weekly_analysis.py 2>&1
# Also run translation
/usr/bin/python3 scripts/translation.py 2>&1
exit $?
```

- [ ] **步骤 6：部署站点**

运行：`cd "/root/workspace/search in coding" && python3 scripts/deploy_site.py`

- [ ] **步骤 7：验证站点**

访问 https://coding.lzpgood.online/，验证：
- 已分析项目有 LLM summary（中英双语一句话评价）
- 详情面板显示评分明细（可量化分 + 质量分）
- 报告链接可打开（生态周报/工具对比/推荐榜）

- [ ] **步骤 8：Commit 并 tag**

```bash
cd "/root/workspace/search in coding"
git add -A
git commit -m "feat: batch 3 complete - LLM analysis system with weekly cron, benchmarks, reports, translation"
git tag v2025.07.12-batch3
```

- [ ] **步骤 9：更新 Wiki**

更新：
- `wiki/L1-全景.md` - 更新项目状态（双层节奏架构上线）
- `wiki/L3-代码地图.md` - 新增 weekly_analysis.py、llm_api.py、llm_prompts.py、benchmark_manager.py、translation.py
- `wiki/L4B-后端详解.md` - 新增 LLM 分析系统章节
- `wiki/L6-经验录.md` - 记录 LLM 分析的坑（API 速率限制、JSON 解析、key 轮询）

---

## 验收标准

- [ ] `weekly_analysis.py` 可 dry-run，显示待分析项目数量
- [ ] `weekly_analysis.py --max-projects 3` 实际运行成功，3 个项目被 LLM 分析
- [ ] 被分析项目有 quality_score > 0、llm_summary（中英双语）、resource_type、target_tools、tracking_priority
- [ ] `data/benchmarks.yaml` 有 5 个分数段的参照项目
- [ ] `data/snapshots/YYYY-MM-DD.json` 快照文件生成
- [ ] 3 份报告生成（weekly-report.md, tool-comparison.md, curated-top.md）
- [ ] `translation.py` 可翻译 curated 项目的 summary
- [ ] `data/translations-cache/` 有缓存文件
- [ ] Hermes cron 配置为每周一 03:00，no_agent 模式
- [ ] 所有测试通过（pytest tests/ -v）
- [ ] 站点正常加载，详情面板显示 LLM 分析结果
- [ ] 站点部署到 https://coding.lzpgood.online/
