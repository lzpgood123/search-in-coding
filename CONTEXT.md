# Search in Coding

一个持续自动更新的 AI Coding Agent 生态追踪索引库。双层节奏：每日自动采集 GitHub 数据 + 每周 LLM 深度分析。GitHub 是总仓库，正式站点是展示面。

## Language

### 追踪对象

**Resource**:
被系统追踪的一条生态记录。每条 Resource 对应一个 GitHub 仓库，经过归一化和 LLM 分析后存入 `data/projects.yaml`。
_Avoid_: entry, item, record, project（project 仍用于历史兼容，但 Resource 是规范术语）

**Target Tool**:
系统追踪的 10 个 AI Coding Agent 之一（如 Claude Code、Codex CLI、Cursor）。定义在 `data/seed-tools.yaml` 中。每个工具有 `extension_points` 和 `related_concepts`。
_Avoid_: tracked tool, monitored tool

**Official Tool**:
10 个目标工具自身的记录，在站点展示中单独列出，不参与生态排名。
_Avoid_: seed tool, base tool

**泛生态资源**:
不归属任何特定 Target Tool 的 Resource。LLM 在分析时判断 target_tools 为空，表示该资源对所有 AI coding agent 都有参考价值。

### 记录生命周期

**Tracking Priority**:
Resource 的追踪级别，由 LLM 分析决定。取值：`pending`（首次发现待分析）、`track`（持续追踪，每日刷新数据）、`index`（收入索引但不追踪）、`reject`（不相关，移入噪声集）。
_Avoid_: status, level, tier

**Review State**:
Resource 的审核状态。取值：`auto-indexed`（默认入索引）、`auto-curated`（推荐集）、`auto-rejected`（噪声集）。
_Avoid_: approval state

### 采集管道

**Initial Collection**:
一次性历史回溯收集，按月分片搜索 2025 年 1 月至今的所有相关 GitHub 项目。独立脚本 `initial_collection.py`，支持断点续传，手动触发。
_Avoid_: bulk fetch, batch import

**Daily Incremental**:
每日增量更新，只做两件事：刷新 track 项目的 GitHub 数据 + 搜索当天新项目。
_Avoid_: daily collection, daily sweep

**Weekly Analysis**:
每周一 03:00 独立 cron 触发的 LLM 深度分析。派最多 10 个子代理并行调查项目，输出结构化 JSON。分析新增项目 + 重评全部项目 + 更新参照基准 + 生成报告。
_Avoid_: weekly review, LLM pass

**Pipeline**:
从采集到部署的完整数据处理流程。每日 pipeline：collect -> normalize -> score -> build -> deploy。每周 pipeline：analyze -> score -> report -> build -> deploy。
_Avoid_: workflow, process

**Snapshot**:
每次 Weekly Analysis 时的数据快照，记录当日状态，用于未来趋势分析。
_Avoid_: checkpoint, state dump

### 评分系统

**Score**:
Resource 的综合评分（0-100），由两部分组成。
_Avoid_: rating, grade, rank

**Quantifiable Score**:
可量化分（0-60），每日自动更新。由 Stars(20) + Activity(15) + Adoption(10) + Maturity(15) 组成，基于 GitHub API 实时数据。
_Avoid_: base score, auto score

**Quality Score**:
质量分（0-40），每周 LLM 更新。由 Relevance(10) + Practicality(10) + Novelty(10) + Ecosystem_value(10) 组成，由子代理深度调查给出。
_Avoid_: LLM score, subjective score

**Benchmark Reference**:
参照基准项目，各分数段的标杆。分数段：0-20（噪声）、21-40（萌芽）、41-60（可用）、61-80（优秀）、81-100（标杆）。完全由 LLM 自动选择和维护。每周分析时先更新参照基准，再基于参照重评分。
_Avoid_: reference project, anchor, baseline project

### 分类标签

**Resource Type**:
Resource 的类型标签（多值），由 LLM 打标。取值：mcp-server, skills, rules, agent-framework, cli-tool, tutorial。
_Avoid_: category（旧术语，已废弃）, tag, label

**Target Tools**:
Resource 关联的工具标签（多值），由 LLM 打标。可为空（泛生态资源）。
_Avoid_: tool association, tool mapping

### 来源

**Source Type**:
Resource 的采集来源类型。当前只有 `github`（其他来源代码保留但停用）。历史数据中的 `exa`、`fallback-web`、`official-seed` 已全部清理。
_Avoid_: origin, channel

## Concepts (参考)

以下概念定义在 `data/concepts.yaml` 中，与 Target Tool 的 `related_concepts` 关联：

**Agentic Coding**: AI agents that plan, edit files, run commands, test, and iterate.
**Context Engineering**: Preparing instructions, repo maps, memory, docs and retrieval for coding agents.
**MCP (Model Context Protocol)**: Protocol for connecting tools and data sources to AI agents.
**Skills**: Reusable packaged agent workflows, prompts, references and scripts.
**Rules / Instructions**: CLAUDE.md, AGENTS.md, Cursor rules and similar behavioral guidance.
