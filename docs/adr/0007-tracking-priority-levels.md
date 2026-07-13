# ADR-0007: 项目追踪分级机制

## Status: accepted

## Context

一次性回溯收集数千项目后，不是所有项目都值得每日刷新数据。1 star 的空仓库和 50000 star 的活跃项目不应该消耗同样的追踪资源。

## Decision

`tracking_priority` 字段，由 LLM 分析决定：
- `pending`：首次发现，待 LLM 分析
- `track`：值得持续追踪，每日刷新完整数据，每周重评
- `index`：收入索引但不追踪，只在首次发现时采集和分析
- `reject`：不相关，移入噪声集

首次发现的项目默认 pending，每日只刷新基础数据，等下次每周 LLM 分析时确定追踪级别。

## Consequences

- 每日 API 请求量可控（只刷新 track 项目）
- index 项目数据可能过时，但不影响整体质量
- LLM 需要明确的追踪判断标准（分数、增长趋势、生态重要性）
