# ADR-0003: 100 分制双层评分 + 动态参照基准

## Status: accepted

## Context

原评分系统 0-30 分，6 维度各 0-5 分，赋值几乎完全由 source_type 决定（GitHub 一律 activity=2, practicality=3）。同来源项目分数差异极小，评分实际是在分类来源而非评估质量。

用户要求：总分提至 100，分数要分细则（stars 多的自然高分），分数不固定（会随时间变化）。

## Decision

100 分制双层评分：
- **可量化分（60分）**：Stars(20) + Activity(15) + Adoption(10) + Maturity(15)，每日自动更新
- **质量分（40分）**：Relevance(10) + Practicality(10) + Novelty(10) + Ecosystem_value(10)，每周 LLM 更新

动态参照基准：5 个分数段各有标杆项目，完全由 LLM 自动选择和维护。每周先更新参照基准，再基于参照重评分。

## Consequences

- 同来源项目间会有显著分数差异
- 分数随 stars 增长、pushed_at 变化而动态变化
- 参照基准机制确保评分尺度一致性
- 旧评分字段全部废弃，数据需要回溯重评
