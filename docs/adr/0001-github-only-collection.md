# ADR-0001: 采集源收缩到仅 GitHub

## Status: accepted

## Context

项目原有三个采集源（GitHub、Exa、fallback-web），其中 fallback-web 的 147 条数据包含完全无关内容（狗狗买卖、Google 表格函数），Exa 的 197 条数据质量不一。用户确认只需要从 GitHub 收集，其他采集器代码保留但停用，为将来迭代留接口。

## Decision

采集源收缩到仅 GitHub。现有 Exa 和 fallback-web 数据全部移除。其他采集器代码保留但不调用。

## Consequences

- 数据量从 618 降到 264 条（GitHub 来源），但质量显著提升
- 博客文章、社区讨论类内容暂时不追踪
- 未来可通过恢复 Exa 或新增 RSS 来源扩展
