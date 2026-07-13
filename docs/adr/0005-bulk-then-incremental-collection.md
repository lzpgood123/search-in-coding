# ADR-0005: 一次性历史回溯 + 增量更新采集模式

## Status: accepted

## Context

原采集模式是每日用固定 query 搜索 GitHub + Exa + fallback-web，广撒网式采集。当采集源收缩到仅 GitHub 后，GitHub 是结构化可穷举的数据源，不需要每天大量搜索。

用户提出：先一次性收集完 2025 年 1 月至今的项目，之后每日只做增量。

## Decision

三阶段采集模式：
1. **一次性历史回溯**：按月分片搜索 2025-01 至今，独立脚本 `initial_collection.py`，断点续传，手动触发。四种搜索方式（topic/关键词/dependents/code）全面覆盖。
2. **每日增量**：刷新 track 项目数据 + 搜索当天新项目（`created:>{today-1day}`）。
3. **每周 LLM 分析**：分析新增 + 重评全部。

覆盖率验证：每工具/每 resource_type 最低数量 + 已知重点项目校验。

## Consequences

- 一次性回溯可能收集 1000-3000 个候选项目，需要预筛选后分批 LLM 分析
- 每日请求量从数百降到 50-100 次
- 断点续传机制增加脚本复杂度但保证可靠性
