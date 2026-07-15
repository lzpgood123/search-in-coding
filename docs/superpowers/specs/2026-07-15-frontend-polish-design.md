# Search in Coding - 前端打磨设计规格

> **状态：** 方案已锁定（2026-07-15）  
> **角色：** 方案设计（本文件只定规格，不写实现代码）  
> **前置：** Style B 上线后 dogfood 发现 5 个体验问题 + 1 个文档需求  
> **历史参考：** `docs/superpowers/specs/2026-07-15-frontend-style-b-complete-design.md`（Style B 基线，不推翻）

---

## 1. 背景

### 1.1 当前状态（2026-07-15）

| 维度 | 状态 |
|------|------|
| 前端 | Style B（Warm paper dark + 琥珀）已上线运行 |
| 数据 | 5100+ 项目、40 curated、LLM 覆盖率高 |
| 报告 | 居中 modal + tab 切换三报告已可用 |
| 详情 | 右侧侧栏 `#detailOverlay`，已有 score_detail / quality_detail / llm_summary |

### 1.2 本轮要解决的问题

Style B 上线后 dogfood 发现 5 个体验问题 + 1 个文档缺失：

| # | 问题 | 当前表现 |
|---|------|----------|
| 1 | 工具/类型标签无分区 | `#toolTags` 和 `#typeTags` 连在一起，用户分不清哪个是"工具"、哪个是"类型" |
| 2 | 中文模式仍显示英文 summary | `textOf(p, 'summary')` 取的是项目原生 summary，中文用户看到大段英文 |
| 3 | LLM Summary 只有一句话 | `project_analysis_prompt()` 要求"一句话评价"，信息量不足 |
| 4 | 报告浮窗表格溢出 | 宽表格撑破 modal，竖向滚动正常但横向溢出无法滚动 |
| 5 | 报告入口不突出 | 三个报告 pill 混在 nav 里（和"导出收藏"并排），容易被忽略 |
| 6 | 缺新工具添加文档 | 新人不知道如何添加一个新工具到追踪系统 |

### 1.3 非目标

- **不改评分公式**：`scripts/score.py`、`config/scoring*.yaml` 不动
- **不改数据结构**：`data.js`、`filters.js`、`data/*` 不动
- **不改采集逻辑**：`collect_github.py`、`normalize.py` 不动
- **不引入依赖**：零前端框架、零后端

---

## 2. 决策清单

### 决策 1：工具/类型标签分区

**问题：** `#toolTags` 和 `#typeTags` 两个 `.tag-group` 在 `index.html` L89-90 紧挨着，没有标题区分，用户无法判断当前在选"工具"还是"类型"。

**方案：**
- 在 `#toolTags` 上方加小标题"工具"（i18n key: `filterTools`）
- 在 `#typeTags` 上方加小标题"类型"（i18n key: `filterTypes`）
- 两个标签区域之间加 `margin` 间距
- CSS 新增 `.filter-label` 样式：`font-size: 12px; color: var(--color-text-muted); margin-bottom: 4px;`

**改动文件：** `site/index.html`、`site/styles.css`、`site/js/i18n.js`

### 决策 2：中文模式用 llm_summary 替代 summary

**问题：** `render.js` 中 `renderDiscovery()`（L99）、`renderPage()`（L234）、`openDetail()`（L386）均调用 `SIC_i18n.textOf(p, 'summary')`，取的是项目原生 summary（多为英文）。中文用户在发现卡片、表格列表、详情面板看到大段英文，体验差。

**方案：**
- 中文模式（`lang == 'zh'`）下，如果项目有 `llm_summary.zh`，优先显示 `llm_summary` 中文评价
- 英文模式或无 `llm_summary` 时 fallback 到原生 `summary`
- 详情面板**同时展示两个**：原生 `summary` 原文 + `llm_summary` 中文评价（已有 LLM Summary 区块，L415）
- 需要 `llm_summary` 进入 slim `projects.json`：检查 `build_site.py` 的 `SLIM_FIELDS`（当前 L17-22），确认 `llm_summary` 不在其中（当前在 `DETAIL_FIELDS`，L25-26）。将 `llm_summary` 加入 `SLIM_FIELDS`。

**改动文件：** `site/js/render.js`、`scripts/build_site.py`（仅 `SLIM_FIELDS` 加 `llm_summary`）

### 决策 3：LLM Summary 扩展到 2-3 句话

**问题：** `llm_prompts.py` 的 `project_analysis_prompt()`（L42-84）中 `llm_summary` 字段要求"一句话中文评价" / "one sentence English summary"，信息量不足，用户看完还是不知道项目是干什么的。

**方案：**
- 修改 `project_analysis_prompt()` 中 `llm_summary` 字段说明
- 从"一句话评价"改为"2-3 句话"
- 结构：**项目是什么 + 核心功能 + 适合谁用**
- 示例：`"AgentKit 是一个用于构建 AI Agent 的开源框架。提供工具调用、记忆管理、多步推理等核心能力，适合需要快速搭建定制化 Agent 的开发者。"`
- 不改其他字段（`relevance_score`、`resource_type`、`quality_score`、`quality_detail` 等不变）
- 不改评分逻辑、不改 schema 结构（只改 prompt 文本和字段说明文字）
- 改完后对 3-5 个项目测试分析效果

**改动文件：** `scripts/llm_prompts.py`

### 决策 4：报告浮窗滚动条修复

**问题：** `render.js` 的 `renderReport()`（L458-513）将 markdown 表格渲染为 `<table>`，直接放入 `.report-content`。`styles.css` 中 `.report-content table`（L649）设 `width: 100%`，宽表格会撑破 `.modal-body`（L788-792）宽度，横向溢出无法滚动。

**方案：**
- `render.js`：报告 markdown 渲染时给每张 `<table>` 包一层 `<div class="table-scroll">`
- `styles.css`：`.report-content .table-scroll { overflow-x: auto; }` 和 `.report-content table { min-width: 100%; }`
- 竖向滚动保持不变（`.modal-body` 的 `overflow-y: auto` 不动）

**改动文件：** `site/js/render.js`、`site/styles.css`

### 决策 5：报告入口突出

**问题：** `index.html` L38-44 的 `<nav>` 中，三个报告 pill（推荐榜/生态周报/工具对比）和"导出收藏"按钮并排，报告入口不突出，用户容易忽略。

**方案：**
- `index.html`：`<nav>` 下方新增独立报告栏 `<div class="report-bar">`，三个报告 pill 移到这里
- `<nav>` 中只保留"导出收藏"按钮和收藏链接输入框
- `styles.css`：新增 `.report-bar` 样式：独立一行、背景色区分（`var(--color-surface)` 或略浅）、`padding`、`margin-top`
- 报告 pill 样式复用现有 `nav a[data-report]` 或提取为 `.report-pill`（保持视觉一致）

**改动文件：** `site/index.html`、`site/styles.css`

### 决策 6：添加新工具 checklist 文档

**问题：** 系统缺少"如何添加一个新追踪工具"的文档，新人不知道完整流程。

**方案：**
- 新建 `docs/add-new-tool-checklist.md`
- 包含从定义到上线的完整步骤（8 步）
- 参考 `data/seed-tools.yaml` 中现有工具的字段结构

**改动文件：** `docs/add-new-tool-checklist.md`（新建）

---

## 3. 批次划分

| 批次 | 包含决策 | 侧重点 | 文件 |
|------|----------|--------|------|
| **批次 1** | 决策 1 + 2 + 4 + 5 | 前端体验优化 | `docs/superpowers/handoff/2026-07-15-frontend-polish-prompt.md` |
| **批次 2** | 决策 3 + 6 | 后端 prompt + 文档 | `docs/superpowers/handoff/2026-07-15-llm-prompt-and-tool-checklist-prompt.md` |

**批次间无强依赖**，可并行执行。批次 1 的决策 2 需要 `build_site.py` 改 `SLIM_FIELDS` 后重新 `build_site` + `deploy`。

---

## 4. 硬边界

### 4.1 批次 1 允许修改的文件

| 文件 | 改动范围 |
|------|----------|
| `site/index.html` | 标签分区标题 DOM、报告栏 DOM |
| `site/js/render.js` | `textOf()` 调用中文优先 llm_summary、报告表格包裹 |
| `site/js/app.js` | 报告 pill 事件绑定迁移（如需） |
| `site/js/i18n.js` | 新增 `filterTools` / `filterTypes` 翻译键 |
| `site/styles.css` | `.filter-label`、`.report-bar`、`.table-scroll` 样式 |
| `scripts/build_site.py` | **仅** `SLIM_FIELDS` 列表加 `llm_summary` |

### 4.2 批次 1 不允许修改

- `site/js/data.js`
- `site/js/filters.js`
- `site/js/charts.js`
- `data/*`（YAML / JSON 原始数据）
- `scripts/normalize.py`
- `scripts/score.py`

### 4.3 批次 2 允许修改的文件

| 文件 | 改动范围 |
|------|----------|
| `scripts/llm_prompts.py` | **仅** `project_analysis_prompt()` 的 prompt 文本（`llm_summary` 字段说明） |
| `docs/add-new-tool-checklist.md` | 新建文档 |

### 4.4 批次 2 不允许修改

- `scripts/score.py`
- `scripts/normalize.py`
- `config/llm-analysis.yaml`（schema 定义）
- 任何前端文件

### 4.5 必须保持兼容的契约

**URL query：** `q` / `tools` / `types` / `sort` / `mode` / `curated` / `recent` / `fav` / `project`  
**DOM id 契约：** `#toolTags` `#typeTags` `#reportModal` `#reportBackdrop` `#reportModalBody` `#detailOverlay` `#exportFav` 以及 `data-report` 文件名  
**数据消费：** `site/data/projects.json`、`site/data/detail/*.json` 结构不变（仅 `projects.json` 多一个 `llm_summary` 字段）

---

## 5. 验收标准

### 批次 1

1. ✅ 中文模式下，发现卡片和表格列表显示中文 llm_summary（有则显示，无则 fallback 英文 summary）
2. ✅ 详情面板同时展示原生 summary 和 LLM Summary
3. ✅ 工具/类型标签上方各有小标题，视觉分区清晰
4. ✅ 报告浮窗宽表格可横向滚动，不撑破 modal
5. ✅ nav 下方有独立报告栏，背景色区分，三个报告 pill 在此
6. ✅ nav 中只保留导出收藏
7. ✅ `build_site` 后 `projects.json` 包含 `llm_summary` 字段
8. ✅ 现有功能（筛选、收藏、深链、分页、排序）不受影响

### 批次 2

1. ✅ `llm_prompts.py` 的 `llm_summary` 字段说明改为 2-3 句话
2. ✅ 3-5 个项目测试分析，输出的 llm_summary 符合"是什么+核心功能+适合谁用"结构
3. ✅ 其他字段（relevance_score、quality_score 等）格式不变
4. ✅ `docs/add-new-tool-checklist.md` 存在，包含完整 8 步流程
5. ✅ checklist 中引用的脚本路径与实际文件一致

---

## 6. 关键约束

1. **零依赖**：不引入任何前端框架、图表库、CSS 框架
2. **不破坏现有功能**：筛选、收藏、深链、分页、排序、报告 modal 全部正常
3. **中文模式优先 llm_summary**：`lang == 'zh'` 且项目有 `llm_summary.zh` 时优先使用，否则 fallback 英文 summary
4. **build_site.py 只改 SLIM_FIELDS**：不碰数据写出逻辑、不碰 hash 生成、不碰 detail 分片
5. **llm_prompts.py 只改 prompt 文本**：不碰评分逻辑、不碰 schema、不碰其他 prompt 函数
