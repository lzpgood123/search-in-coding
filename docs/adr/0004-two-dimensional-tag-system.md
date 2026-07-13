# ADR-0004: 2 维标签分类体系替代旧分类

## Status: accepted

## Context

原分类是单维度的 `category` 字段（mcp-acp-a2a, skills-prompts, rules-instructions 等），基于关键词匹配，存在 misclassification 问题。用户质疑按 coding 工具分还是按项目类型分"真的好吗"。

讨论后确认：标签应该是多维的，但 264 条数据撑不起 4 维标签（42% 的 tool×category 组合不到 3 条记录）。

## Decision

采用 2 维标签体系：
- **resource_type**（多值）：mcp-server, skills, rules, agent-framework, cli-tool, tutorial
- **target_tools**（多值）：10 个目标工具，可为空（泛生态资源）

两个维度都由 LLM 在每周分析时自动打标。站点筛选器为标签按钮组多选，默认 OR + 可切换 AND。

旧 `category` 字段废弃，由 `resource_type` 替代。

## Consequences

- 60 种标签组合 × 264 条数据 = 平均每组 4.4 条，勉强可用
- 数据增长到 500+ 后可考虑加 scenario 或 ecosystem_role 维度
- LLM 打标比关键词匹配更准确，但不稳定（需抽检）
