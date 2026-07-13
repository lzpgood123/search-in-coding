# 三批次优化完成度评估报告

> 评估日期：2026-07-13  
> 评估站点：https://coding.lzpgood.online/  
> 评估方式：本地数据/源码核查 + 线上资源 curl 交叉验证（本环境无浏览器自动化，交互项以源码逻辑 + 线上静态资源部署一致性判定）  
> 数据快照：`data/projects.yaml` 294 条；线上 `projects.json` 294 条

## 总览

| 批次 | 计划项数 | 完成数 | 部分完成 | 未完成 | 完成率（全完成计） | 完成率（含部分） | 遗留问题数 |
|------|---------|--------|---------|--------|-------------------|------------------|-----------|
| A 数据层 | 4 | 0 | 3 | 1 | 0% | 75% | 6 |
| B 前端层 | 15 | 13 | 2 | 0 | 87% | 100% | 3 |
| C 翻译 | 1 | 0 | 1 | 0 | 0% | 100% | 1 |
| **合计** | **20** | **13** | **6** | **1** | **65%** | **95%** | **10** |

**一句话结论：**  
前端批次 B 基本落地且线上已部署；翻译批次 C 主体完成（约 90% 真双语）；数据层批次 A **未按规格闭环**——seed-tools 路径仍错、字段填充率未达预期、头部产品类 `resource_type` 仍大量误标为 `tutorial`。

---

## 批次 A 评估

### A1. seed-tools repo 路径修正

- **状态：❌ 未完成**
- **证据（`data/seed-tools.yaml` 实测）：**

| 工具 | 当前 repo | 规格正确 repo | 结果 |
|------|----------|---------------|------|
| goose | `aaif-goose/goose` | `block/goose` | ❌ 未改 |
| cursor | `cursor/cursor` | `getcursor/cursor` | ❌ 未改 |
| opencode | `anomalyco/opencode` | `sst/opencode` | ❌ 未改 |
| qoder | `QoderAI/qoder-action` | 完整 org/repo | ⚠️ 已补全格式，但是 `qoder-action` 而非计划中的 `QoderAI/qoder` |

- **遗留问题：** 3 个关键工具路径仍是旧值，后续 `gh repo view`/官方 seed 同步会继续跑偏。

### A2. 缺失项目补充

- **状态：🟡 部分完成**
- **证据：**

| 规格要求 repo | 精确匹配 | 实际存在的等价项 | 说明 |
|---------------|---------|------------------|------|
| continuedev/continue | ✅ | continuedev/continue (34846⭐) | 精确命中 |
| paul-gauthier/aider | ❌ | Aider-AI/aider (47338⭐) | org 更名后的正确仓库，非规格字面路径 |
| cline/cline | ✅ | cline/cline (64610⭐) | 精确命中 |
| rooveterinaryinc/roo | ❌ | RooCodeInc/Roo-Code (24329⭐) | org/名更名后的正确仓库 |
| block/goose | ❌ | aaif-goose/goose (51152⭐) | 未用 block/goose 规范路径 |
| getcursor/cursor | ❌ | cursor/cursor (33028⭐) | 未用 getcursor/cursor 规范路径 |

- **合计：** 精确路径 2/6；功能上“知名项目在库中”约 6/6（以更名仓库计）。
- **遗留问题：** 规格字面路径未统一；与 seed-tools 错误路径互相放大。

### A3. 字段映射修正（forks/license/languages/stars/topics/readme_preview）

- **状态：🟡 部分完成**
- **证据（`data/projects.yaml`，n=294）：**

| 字段 | 填充数 | 填充率 | 相对旧状态 | 评价 |
|------|--------|--------|------------|------|
| forks | 158/294 | 53.7% | 从 0 提升 | 有改善，未达“合理高填充”/wiki 声称 86% |
| license | 154/294 | 52.4% | 从 0 提升 | 中等 |
| languages | 215/294 | 73.1% | 改善 | 尚可 |
| stars | 222/294 | 75.5% | 72 条仍 0/缺失 | 头部有 stars，长尾仍空 |
| topics | 85/294 | 28.9% | 新增字段 | 偏低 |
| readme_preview | 6/294 | 2.0% | 仅手动补充 6 项 | 基本未铺开 |

- **站点导出缺口：**
  - 列表 JSON `projects.json` 无 `score_detail` / `topics` / `readme_preview`
  - 详情 JSON `projects-detail.json` 有 `score_detail`（294/294），但 **无** `readme_preview`、`topics`
- **遗留问题：** 字段“写进 yaml”≠“进入站点可消费数据”；readme/topics 几乎未规模化。

### A4. resource_type 误标修正

- **状态：🟡 部分完成**
- **已修好（高星 skill 不再标 tutorial）：**
  - JuliusBrussee/caveman 85516⭐ → `['skills']` ✅
  - blader/humanizer 27726⭐ → `['skills']` ✅
  - 多数 `*skills*` 仓库已落在 skills
- **仍严重误标（头部产品被标 tutorial）：**

| 项目 | stars | resource_type | 问题 |
|------|-------|---------------|------|
| aaif-goose/goose | 51152 | `['tutorial']` | 开源 AI agent，不是教程 |
| continuedev/continue | 34846 | `['tutorial']` | 开源 coding agent |
| cursor/cursor | 33028 | `['tutorial']` | 产品本体 |
| RooCodeInc/Roo-Code | 24329 | `['tutorial']` | 编辑器 AI agent 产品 |

- **分布：** tutorial 97 / cli-tool 74 / mcp-server 72 / skills 62 / extension 36 / rules 18 / agent-framework 8  
- **遗留问题：** dogfood #4（Critical）只修了 skill 侧，**未修 curated 头部产品分类**。

---

## 批次 B 评估

| # | 项 | 状态 | 证据 |
|---|----|------|------|
| B1 | Linear/Vercel 风格 | ✅ | 线上 `styles.41d38f.css` 含 `--color-bg-gradient`、`--shadow-card`、半透明边框、Inter、h1=40/h2=28/h3=20 |
| B2 | 色彩区分标签 | 🟡 部分 | 6 种 pill 色已有（mcp/skills/rules/framework/cli/tutorial）；**extension 无独立 pill 色**（36 条 extension 会掉默认样式） |
| B3 | Hero 区域 | ✅ | header 内 `#metrics.hero-stats`；renderMetrics 渲染总记录/推荐/官方工具/生态项目；线上 index 已部署 |
| B4 | 分数展示 /60 + 质量分待分析 | 🟡 部分 | 表格与详情有 `/60` + `qualityPending`；**发现区卡片 score badge 未旁注 /60** |
| B5 | 工具/类型人话名称 | ✅ | `tools.json` 有 `Claude Code` 等；`i18n.resourceTypes` 有 `MCP Server`；`toolLabels()`/`pills()` 使用人话 |
| B6 | 结果计数 + 清空 + chips | ✅ | `#resultCount` / `#clearFilters` / `#activeFilters`；`showing X / Y` 逻辑在 render.js |
| B7 | 只看收藏 | ✅ | `#favoritesOnly` checkbox + filters/app 绑定 |
| B8 | OR/AND radiogroup | ✅ | `#modeToggle role=radiogroup`；点击同模式 `return` 不翻转 |
| B9 | writeState 保留 hash | ✅ | `const hash = location.hash` 后拼回 `replaceState` |
| B10 | 项目名可点 + `?project=` 深链 | ✅ | `.project-name data-action=detail`；`qs.get('project')` → `_pendingProject` → `openDetail` |
| B11 | 详情加载态 | ✅ | openDetail 先写 `.detail-loading` 再 await `loadDetail` |
| B12 | score_detail 分项 | ✅ | 详情从 `projects-detail.json` 取 `score_detail`（线上 294/294 有 stars/activity/adoption/maturity） |
| B13 | 空字段隐藏 | ✅ | forks/license/languages 空则不渲染行 |
| B14 | 页脚更新时间 + GitHub | ✅ | footer + `#lastUpdated` + GitHub 链接 |
| B15 | robots + favicon + OG | ✅ | 线上 robots 200；favicon.svg 200；index 含 og:title/description/type/url + theme-color |

**B 小结：** 15 项中 13 全完成、2 部分完成；dogfood 指定的交互修复项（#1/#5/#6/#7/#8/#9/#10/#11/#12/#14/#15/#20/#27）源码与线上静态资源一致，**可判定为已部署**。

---

## 批次 C 评估

### C1. 中文翻译

- **状态：🟡 部分完成（主体已完成）**
- **翻译覆盖率：**
  - `zh != en`：**265 / 294 = 90.1%**
  - `zh == en`：29 / 294
  - `empty zh`：0
- **真双语样本：**
  - caveman EN: “why use many token...” → ZH: “何必用那么多词...”
  - humanizer EN: “removes signs of AI-generated writing” → ZH: “移除AI生成的写作痕迹”
- **剩余 29 条说明：** 大量是**原文已是中文**（如 Humanizer-zh、RIPER-5「神级Cursor Rule」、PaiAgent 等），`zh==en` 合理；仍有少量英文未译。
- **线上一致性：** 线上 `projects.json` 统计同样 265/29，已发布。
- **遗留问题：** 未到 100%；英文残留 + 中文原文条目未做“原文语言标记”。

---

## dogfood 42 问题对照（本三批次相关）

| dogfood # | 主题 | 本三批次是否覆盖 | 当前状态 |
|-----------|------|------------------|----------|
| #1 | 分数 /100 误导 | B | ✅ 改为 /60 + 待 LLM |
| #3 | 假双语 | C | 🟡 90.1% 真双语 |
| #4 | resource_type 误标 | A | 🟡 skill 修好，产品 tutorial 仍错 |
| #5 | 只看收藏 | B | ✅ |
| #6 | hash 被清掉 | B | ✅ |
| #7 | 计数/清空/chips | B | ✅ |
| #8 | OR/AND 翻转 | B | ✅ |
| #9 | 详情 loading | B | ✅ |
| #10 | score_detail | B | ✅ |
| #11 | 人话标签 | B | ✅ |
| #12 | 空字段隐藏 | B | ✅ |
| #14 | 页脚 | B | ✅ |
| #15/#20 | 深链/可点项目名 | B | ✅ |
| #27 | robots/favicon/OG | B | ✅ |
| #2 | 最新发现叙事失真 | 不在本三批 | 仍可能存在（first_seen 高度集中：2026-07-13×282，2026-07-06×12） |
| 其余 #16–#42 | 多种 UX/内容 | 多数未纳入本三批 | 需另表跟踪 |

---

## 遗留问题清单

| # | 严重度 | 问题 | 所属批次 | 建议修复方式 |
|---|--------|------|---------|------------|
| 1 | 🔴 High | seed-tools 中 goose/cursor/opencode 路径仍错误 | A1 | 按规格改 `block/goose`、`getcursor/cursor`、`sst/opencode` 并验证 `gh repo view` |
| 2 | 🔴 High | 头部产品 continue/goose/cursor/Roo-Code 仍标 `tutorial` | A4 | 对 curated Top/高星产品手工或规则重标为 `cli-tool`/`extension`/`agent-framework` |
| 3 | 🟠 High | forks/license/stars 填充率仍中等；stars 72 条空 | A3 | 回补 `gh repo view` 全量 enrich，或重跑 normalize 映射 |
| 4 | 🟠 High | `readme_preview` 仅 6/294，且未进入站点 detail JSON | A3 | 批量拉取 README + 改 `build_site.py` 导出 detail 字段 |
| 5 | 🟡 Medium | topics 28.9% 且未导出到站点 | A3 | 映射 + 导出 |
| 6 | 🟡 Medium | 规格要求的 6 个 repo 字面路径仅 2 精确命中 | A2 | 统一 canonical repo（或文档改为接受更名后路径） |
| 7 | 🟡 Medium | extension 类型无彩色 pill / i18n 人话映射 | B2 | 补 `.pill-type-extension` 与 `resourceTypes.extension` |
| 8 | 🔵 Low | 发现区 score badge 未显示 `/60` | B4 | discovery 卡片与表格一致加 `/60` |
| 9 | 🔵 Low | 翻译 29 条 zh==en（含中文原文与少量未译英文） | C1 | 识别源语言；仅对英文残留补译 |
| 10 | 🟡 Medium（范围外） | 「最新发现」first_seen 高度同日，叙事仍弱 | 非本批 | 增量采集或改文案 |

---

## 总体评价

三批次里，**批次 B（前端审美 + dogfood 交互）完成度最高**，源码与 https://coding.lzpgood.online/ 线上资源一致，用户可感知的筛选/收藏/深链/详情/SEO 基础设施已基本达标。  
**批次 C 翻译主体成功**，假双语问题从 100% 同文降到约 10% 同文，中文切换已有实质内容。  

真正拖后腿的是 **批次 A**：计划写了 seed-tools 纠错与字段/分类修正，但验收数据表明 **A1 基本未做、A3/A4 只做了一半**。这会继续伤害信任信号——用户看到 5 万星的 Goose/Continue 被标成「教程」，比前端美不美观更伤产品可信度。

**建议优先级：**  
1. 立刻修 A1 seed-tools + A4 头部产品 resource_type（低成本、高收益）  
2. 回补 A3 字段 enrich 并打通站点导出（readme/topics/score 列表策略）  
3. 补 B 的 extension pill 与发现区 `/60` 小缺口  
4. 清扫 C 的英文残留  

**完成度口径说明：**  
- “完成数 13/20 = 65%”按**严格全完成**计；  
- 若“部分完成也算推进”，则 **19/20 = 95% 有进展**，但 **不可宣称三批次全部完成**。
