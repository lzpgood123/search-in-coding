# Search in Coding 三层优化设计

> 日期：2026-07-12
> 状态：用户已确认
> 作者：方案设计 Agent
> 讨论方式：grill-with-docs 逐题拷问，35 条决策全部经用户确认

## 背景

当前项目存在三层连锁问题：信息收集层有 24% 垃圾数据（含狗狗买卖、Google表格函数等完全无关内容），数据分析层评分完全由 source_type 决定而非内容质量，网站层代码不可维护且功能极度简陋。用户对技术质量和产品方向均不满意。

通过 grilling 会话（35 个问题逐个确认），重新定义了产品方向、采集策略、评分模型和网站交互。

## 产品定位

- 追踪器给自己用 + 给社区用，两者并重
- 核心用户任务：发现(A) + 搜索(B) + 理解(C)，趋势(D)暂搁置
- GitHub 是总仓库，站点是展示面

## 采集策略

### 采集源

**只从 GitHub 收集。** 其他采集器（Exa、fallback-web）代码保留但停用，为将来迭代留接口。

### 搜索方式（四结合）

| 方式 | 用途 | 示例 |
|------|------|------|
| topic 搜索 | 精确匹配仓库 topic | `topic:claude-code`, `topic:mcp-server` |
| 关键词搜索 | 工具名 + 扩展点组合 | `"claude code" skills`, `codex AGENTS.md` |
| dependents 扩展 | 从官方仓库发现依赖者 | `anthropics/claude-code` dependents |
| code 搜索 | 配置文件/引用关系发现 | `filename:CLAUDE.md`, `filename:.cursorrules` |

code 搜索结果进入 `pending` 状态，由 LLM 筛选是否为真正生态资源（区分"使用工具的项目"和"生态资源项目"）。

### 采集模式（三阶段）

**阶段 1：一次性历史回溯**
- 按月分片收集 2025 年 1 月至今所有相关 GitHub 项目
- 独立脚本 `initial_collection.py`，支持断点续传，手动触发
- 四种搜索方式全面覆盖，不限制结果页数
- 覆盖率验证：每个工具/每种 resource_type 的最低数量 + 已知重点项目校验
- 预期收集 1000-3000 个候选项目

**阶段 2：每日增量更新**
- 只做两件事：刷新追踪项目（`tracking_priority=track`）的 GitHub 数据 + 搜索当天新项目（`created:>{today-1day}`）
- 每日请求量约 50-100 次，远低于 GitHub API 限制

**阶段 3：每周 LLM 分析**
- 每周一 03:00 独立 cron 触发
- 分析本周新增项目 + 重评全部项目

## 双层节奏架构

| 节奏 | 工作 | 方法 |
|------|------|------|
| 每日 | 采集新项目 + 刷新追踪项目数据 + 更新可量化分 + 部署站点 | 纯自动化，无 LLM |
| 每周一 03:00 | LLM 深度分析新增项目 + 重评全部项目 + 生成报告 + 更新参照基准 | 独立 cron，SenseNova + DeepSeek-V4-Flash |

### LLM 分析流程

1. **收集待分析项目**：从 projects.yaml 中筛选出 last_analyzed 为空或超过 7 天的项目
2. **批量分组**：每批最多 10 个项目，派 10 个子代理并行调查
3. **子代理任务**：
   - 输入：项目 URL + title + summary（精简，不传全文）
   - 访问 GitHub 仓库页面，读取 README
   - 判断：相关性(0-1)、resource_type(多选)、target_tools(多选)、质量评估
   - 输出：固定 schema 的 JSON
4. **主 agent 收集结果**，合并回 projects.yaml
5. **更新参照基准**：LLM 评估各分数段参照项目是否需要更换（先于重评分）
6. **重评分**：基于子代理质量分 + 刷新的可量化指标，更新所有项目总分
7. **生成报告 + 构建站点 + 部署**

### 数据预筛选

一次性回溯收集后，先跑规则预筛选：
- 去掉空仓库、archived、无 README 的
- 按 stars 降序 + GitHub topic 匹配数降序排序
- 首批分析高价值项目（前 200 条），建立参照基准
- 后续每周分析 100-200 条，直到全部完成
- 每批 5% 随机抽检，准确率 < 80% 则调整 prompt

### 子代理 JSON Schema

**输入（主 agent -> 子代理）：**
```json
{
  "id": "github-xxx",
  "name": "项目名",
  "url": "https://github.com/owner/repo",
  "repo": "owner/repo",
  "summary": "GitHub README 前 500 字",
  "stars": 1234,
  "language": "TypeScript",
  "existing_target_tools": ["claude-code"]
}
```

**输出（子代理 -> 主 agent）：**
```json
{
  "id": "github-xxx",
  "relevance_score": 0.85,
  "resource_type": ["mcp-server", "cli-tool"],
  "target_tools": ["claude-code", "cursor"],
  "tracking_priority": "track",
  "quality_score": 32,
  "quality_detail": {
    "relevance": 9,
    "practicality": 8,
    "novelty": 7,
    "ecosystem_value": 8
  },
  "llm_summary": {
    "zh": "一个高质量的 Claude Code MCP 服务器，提供代码索引和语义搜索能力。",
    "en": "A high-quality MCP server for Claude Code providing code indexing and semantic search."
  },
  "analysis_notes": "README 详尽，有示例代码，活跃维护中。"
}
```

## 评分系统

### 100 分制双层评分

| 层 | 节奏 | 负责 | 分值 |
|---|------|------|------|
| 可量化分 | 每日自动 | 规则驱动，基于 GitHub API 实时数据 | 60 分 |
| 质量分 | 每周 LLM | 子代理深度调查 | 40 分 |
| 总分 | 每日更新 | 可量化分 + 最近一次质量分 | 0-100 |

### 可量化分细则（60 分）

| 维度 | 分值 | 规则 |
|------|------|------|
| Stars | 20 | >=50k=20, >=10k=16, >=5k=12, >=1k=8, >=100=4, >0=2, 0=0 |
| Activity | 15 | pushed_at 90天内=15, 180天内=12, 365天内=8, 2年内=4, 更久=1 |
| Adoption | 10 | forks>=1000=10, >=100=7, >=10=4, >0=2, 0=0 |
| Maturity | 15 | 有release=5, 有文档=3, 有tests=3, 有CI=2, license明确=2 |

### 质量分细则（40 分）

| 维度 | 分值 | 由 LLM 评估 |
|------|------|------------|
| Relevance | 10 | 与 AI coding agent 生态的相关性 |
| Practicality | 10 | README 完整度、示例代码、文档质量 |
| Novelty | 10 | 内容独特性、创新性 |
| Ecosystem_value | 10 | 扩展面数量、生态重要性 |

### 动态参照基准

- 分数段：0-20（噪声）、21-40（萌芽）、41-60（可用）、61-80（优秀）、81-100（标杆）
- 每个分数段有 1-2 个参照项目作为标尺
- 参照项目完全由 LLM 自动选择和维护
- 每周分析时先更新参照基准，再基于参照重评分

## 分类体系

### 2 维标签

| 维度 | 标签 | 说明 |
|------|------|------|
| resource_type | mcp-server, skills, rules, agent-framework, cli-tool, tutorial | 多选，LLM 打标 |
| target_tools | 10 个目标工具 | 多选，可为空（泛生态资源），LLM 打标 |

### 筛选交互

- 标签按钮组多选（resource_type + target_tools 两个维度）
- 默认 OR 模式 + 可切换 AND 模式
- 6 种排序：分数 / Stars / 最近更新 / 标签匹配度 / 最近发现 / 名称
- OR 模式下默认按标签匹配度 + 分数组合排序

## 项目追踪

| tracking_priority | 含义 | 数据更新 | LLM 分析 |
|-------------------|------|---------|---------|
| pending | 首次发现，待 LLM 分析 | 每日刷新基础数据 | 下次每周分析时处理 |
| track | 值得持续追踪 | 每日刷新完整数据 | 每周重评 |
| index | 收入索引但不追踪 | 只在首次发现时采集 | 只在首次发现时分析 |
| reject | 不相关 | 不更新 | 不分析 |

## 网站设计

### 布局

| 区域 | 用户任务 | 内容 |
|------|---------|------|
| 首页精选区 | 发现(A) | 本周新发现的高质量项目 |
| 工具概览区 | 理解(C) | 每个工具的生态规模、资源类型分布、分数分布 |
| 多选筛选表格 | 搜索(B) | 标签按钮组多选筛选 + 6 种排序 + 分页 |

### 项目详情面板

全量信息：名称+URL、LLM 一句话评价（中英）、总分+评分明细、resource_type 标签、target_tools 标签、tracking_priority、GitHub stars/forks/pushed_at、语言、License、README 预览、最近 release、评分参照项目对比、关联项目推荐、收藏按钮。

### 报告系统

| 报告 | 内容 | 频率 |
|------|------|------|
| 生态周报 | 本周新增精选、分数变化最大项目、新趋势、追踪名单变化 | 每周 |
| 工具生态对比 | 10 个工具的生态规模、资源类型分布、成熟度对比 | 每周 |
| 推荐榜 | Top 50 项目 + 分类推荐 | 每周 |

报告在站内用 markdown 渲染器展示，不跳转裸 .md 文件。

### 收藏功能

- localStorage 存储 + URL 导出（编码到 URL hash）
- 不需要后端，不违反零依赖原则

### 代码重构

- 保持零依赖原则，拆分为模块化文件（js/i18n.js, data.js, filters.js, render.js, charts.js, app.js）
- CSS 自定义属性替代硬编码颜色
- 分页（每页 50 条）+ 搜索 debounce（300ms）
- 移动端：表格转卡片布局，筛选控件折叠为抽屉

## 数据结构变更

### 移除字段

score(6维0-5), score_reason, total_score(0-30), source_quality, category(旧分类), record_kind, ranking_scope, concepts, integration_surfaces, recommendation_level, why_it_matters, notes

### 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| resource_type | string[] | 多选标签 |
| quantifiable_score | int | 0-60，每日更新 |
| quality_score | int | 0-40，每周 LLM 更新 |
| total_score | int | 0-100 |
| score_detail | object | 分数明细 |
| llm_summary | object | {zh, en} LLM 一句话评价 |
| tracking_priority | string | pending/track/index/reject |
| last_analyzed | date | 最后 LLM 分析日期 |
| benchmark_ref | string | 参照项目 ID |

### 保留字段

id, name, url, repo, source_type, summary, i18n, status, stars, forks, last_updated, first_seen, last_seen, maturity, languages, tags, target_tools, review_state

## 数据清理

- 现有 618 条全部清理
- 只保留 GitHub 来源 264 条（official-seed 10 条保留）
- Exa 197 条 + fallback-web 147 条全部移除
- 保留的 264 条由 LLM 重新分析打标

## 双语翻译

- 先翻译 curated 60 条（最高质量、最有展示价值）
- 后逐步翻译全部有效记录，每日预算 50 条
- 翻译结果缓存到 data/translations-cache/
- 翻译 API 不可用时回退到原英文

## 部署

- 每日部署：每日采集后更新站点数据（stars/分数变化）
- 每周部署：LLM 分析后更新报告和页面内容
- 生产环境：Nginx（腾讯云上海）
- GitHub Pages：预览发布面

## 前端性能优化

### 数据加载

- **精简 JSON 字段**：`projects.json` 只含表格展示字段（id, name, summary, resource_type, target_tools, total_score, stars, url），详情数据单独放 `projects-detail.json` 按需 fetch
- **虚拟滚动**：`IntersectionObserver` 实现无限滚动，只渲染可视区域 DOM 节点
- **gzip 压缩**：Nginx 启用 gzip，JSON 压缩率约 70-80%
- **渐进式渲染**：先加载 metrics.json（1KB）渲染统计，再加载 projects.json 渲染表格，最后补充 curated/tools

### SEO

- **预渲染首屏 HTML**：首页精选区和工具概览区内容直接写死在 HTML 中，爬虫可见
- **sitemap.xml**：生成站点地图
- **JSON-LD 结构化数据**：嵌入 SoftwareApplication schema

### 加载状态与错误处理

- **骨架屏**：数据加载前展示灰色占位框模拟页面结构
- **渐进式渲染**：每个 JSON 到达后立即渲染对应区域
- **错误处理**：fetch 失败显示重试按钮，筛选结果为空显示提示，详情加载失败显示错误信息

### 可访问性（代码重构时一并实现）

- 语义 HTML（`<main>`, `<section>`, `<nav>`, `<table>`）
- ARIA 标签（`aria-label`, `role="table"`）
- 键盘导航（Tab + Enter 展开详情）
- 焦点管理（详情面板打开焦点跳转）
- 颜色对比度 >= 4.5:1（WCAG AA）

### Nginx 缓存策略

| 资源 | 缓存策略 |
|------|---------|
| `index.html` | `no-cache`（每次检查更新） |
| `js/*.js`, `styles.css` | `max-age=31536000, immutable` + 文件名加内容 hash |
| `data/*.json` | `max-age=300`（5 分钟） |
| `reports/*.md` | `max-age=3600`（1 小时） |

`build_site.py` 生成 JS/CSS 时在文件名中加入内容 hash（如 `app.a3f2b1.js`），`index.html` 引用带 hash 的文件名。

## 不做什么（YAGNI）

- 不引入前端框架（React/Vue），保持零依赖
- 不引入数据库，继续用 YAML/JSON + Git
- 不做用户账号/登录系统
- 不做实时数据更新（保持每日批量 + 每周分析模式）
- 不做趋势页面（等数据积累 3-6 个月后再加）
- 趋势功能暂时搁置

## 实现分批策略

分 3 批实现，每批有独立可交付物，不会陷入"什么都做了一半"的状态。

### 第 1 批：数据基础

| 工作项 | 内容 |
|--------|------|
| 数据清理 | 移除 Exa/fallback-web 数据，只保留 GitHub 264 条 |
| 字段重构 | 移除旧字段，新增 resource_type/quantifiable_score/quality_score/tracking_priority/last_analyzed/benchmark_ref/llm_summary |
| 一次性历史回溯 | `initial_collection.py` 按月分片搜索 2025-01 至今，断点续传 |
| 评分系统（可量化分部分） | 100 分制中的 60 分可量化分，每日自动更新 |
| 临时站点 | 旧前端适配新数据结构，确保站点能跑通 |

**交付物**：干净的数据集 + 新评分 + 站点可访问
**依赖**：无
**风险**：低（确定性工作）

### 第 2 批：网站重写

| 工作项 | 内容 |
|--------|------|
| 三区布局 | 首页精选区 + 工具概览区 + 多选筛选表格 |
| 多选筛选器 | 标签按钮组 + OR/AND 切换 + 6 种排序 |
| 项目详情面板 | 全量信息 + 关联项目推荐 + 参照对比 |
| 报告系统 | 3 类报告 + 站内 markdown 渲染 |
| 收藏功能 | localStorage + URL 导出 |
| 代码重构 | 模块化拆分 + CSS 自定义属性 |
| 前端性能 | 精简 JSON + 虚拟滚动 + gzip + 渐进式渲染 |
| SEO | 预渲染首屏 HTML + sitemap.xml + JSON-LD |
| 加载状态 | 骨架屏 + 错误处理 |
| 可访问性 | 语义 HTML + ARIA + 键盘导航 |
| Nginx 缓存 | 文件名 hash + 分级缓存策略 |

**交付物**：完整的新站点，用户体验到位
**依赖**：第 1 批完成
**风险**：中（纯前端工作量大但确定）

### 第 3 批：LLM 分析系统

| 工作项 | 内容 |
|--------|------|
| 子代理 prompt 设计 | 输入/输出 schema + few-shot 示例 + 调试 |
| 每周 cron 配置 | 独立 cron，SenseNova + DeepSeek-V4-Flash，每周一 03:00 |
| 参照基准机制 | LLM 自动选择各分数段标杆项目 |
| 质量分 40 分 | 子代理深度调查 + 结构化 JSON 输出 |
| 每周重评全部项目 | 不只新增，全部重评 |
| 数据预筛选 | 空仓库/archived/无README 过滤 + 按优先级排序 |
| 抽检机制 | 5% 随机抽样，准确率 < 80% 调整 prompt |
| 双语翻译 | 先 curated 后全量 |
| 报告生成 | 生态周报/工具对比/推荐榜，每周 LLM 生成 |

**交付物**：完整的双层节奏架构上线
**依赖**：第 1、2 批完成
**风险**：高（LLM 输出稳定性、prompt 调试、参照基准合理性需要反复迭代）
