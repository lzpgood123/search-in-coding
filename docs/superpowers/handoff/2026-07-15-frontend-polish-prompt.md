# 新对话 Agent 启动提示词：前端打磨批次 1（4 个前端优化任务）

> 将以下全部内容复制粘贴到**新对话**中作为第一条消息。  
> 本任务是**前端体验优化批次**，不是后端改动，不是重跑采集/评分。  
> 设计规格：`docs/superpowers/specs/2026-07-15-frontend-polish-design.md`

---

## 你的任务

你是 "Search in Coding" 项目的开发 Agent。Style B 上线后 dogfood 发现 4 个前端体验问题，你需要逐一修复。完成后 `build_site` + `deploy` 上线。

**4 个任务：**

1. **工具/类型标签分区**：`#toolTags` 和 `#typeTags` 上方加小标题，加间距
2. **中文模式用 llm_summary 替代 summary**：中文模式优先显示中文 LLM 评价
3. **报告浮窗滚动条修复**：宽表格横向可滚动，不撑破 modal
4. **报告入口突出**：nav 下方独立报告栏，背景色区分

**关键约束：零依赖、不破坏现有功能、中文模式优先 llm_summary**

---

## 第一步：加载技能框架

1. 优先 `skill_view("hermes-agent")` 了解工作流
2. 改代码前：相关逻辑用最小回归命令验证
3. 完成前：先有命令输出证据再声称完成
4. 若改了前端/数据展示：按需更新 `wiki/L4A` 相关一句

---

## 第二步：阅读上下文（只读）

必读：

1. `docs/superpowers/specs/2026-07-15-frontend-polish-design.md` — **本任务设计规格（真相源）**
2. `site/index.html` — 当前 DOM 结构（重点 L38-44 nav、L89-90 标签区）
3. `site/js/render.js` — 渲染逻辑（重点 `renderDiscovery()` L77-103、`renderPage()` L222-247、`openDetail()` L312-448、`renderReport()` L458-513）
4. `site/js/i18n.js` — i18n 键值（重点 `textOf()` L76-78、`UI.zh` / `UI.en` 对象）
5. `site/js/app.js` — 事件绑定（重点 `renderTagButtons()` L99-125、报告 modal 事件 L354-359）
6. `site/styles.css` — 样式（重点 `.tag-group` L382、`.report-content table` L649、`.modal-body` L788、`nav` L78）
7. `scripts/build_site.py` — `SLIM_FIELDS` L17-22、`DETAIL_FIELDS` L25-29

工作区：`/root/workspace/search in coding`

---

## 第三步：任务 1 — 工具/类型标签分区

### 目标

`#toolTags` 和 `#typeTags` 当前紧挨着无标题（`index.html` L89-90），用户分不清"工具"和"类型"。加上小标题和间距。

### 改动

**`site/index.html`**（L89-90 区域）：
- `#toolTags` 上方加小标题：`<div class="filter-label" data-i18n="filterTools">工具</div>`
- `#typeTags` 上方加小标题：`<div class="filter-label" data-i18n="filterTypes">类型</div>`
- 两个区域之间加间距（通过 CSS margin 或外层 wrapper）

**`site/styles.css`**：
```css
.filter-label {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 4px;
  font-weight: 600;
}
```
- 确保 `#toolTags` 和 `#typeTags` 的 `.tag-group` 之间有 `margin-top`（当前 `.tag-group` 在 `.controls` flex 布局中是 inline 的，可能需要调整 flex-wrap 或外层结构）

**`site/js/i18n.js`**：
- `UI.zh` 新增：`filterTools: '工具', filterTypes: '类型',`
- `UI.en` 新增：`filterTools: 'Tools', filterTypes: 'Types',`

### 验收
- 工具标签上方显示"工具"/"Tools"，类型标签上方显示"类型"/"Types"
- 两区域视觉分区清晰，有间距
- 中英文切换正常

---

## 第四步：任务 2 — 中文模式用 llm_summary 替代 summary

### 目标

中文模式下，发现卡片、表格列表、详情面板优先显示中文 `llm_summary`，而非英文原生 `summary`。

### 前置：确保 slim projects.json 包含 llm_summary

**`scripts/build_site.py`**（L17-22）：
- 当前 `SLIM_FIELDS` 不含 `llm_summary`（它在 `DETAIL_FIELDS` L26）
- 将 `'llm_summary'` 加入 `SLIM_FIELDS` 列表
- **只改这一行**，不碰其他逻辑

### 改动

**`site/js/render.js`**：

核心逻辑：新增辅助函数，中文模式下优先取 `llm_summary.zh`，fallback 到 `summary`。

```javascript
// 在 SIC_render 对象中新增辅助函数
summaryOf: function(item) {
  if (SIC_i18n.lang === 'zh' && item && item.llm_summary) {
    var ls = item.llm_summary;
    if (typeof ls === 'object') {
      if (ls.zh) return ls.zh;
      if (ls.en) return ls.en;
    } else if (typeof ls === 'string') {
      return ls;
    }
  }
  return SIC_i18n.textOf(item, 'summary') || '';
},
```

调用点替换（3 处）：

1. **`renderDiscovery()`** L99：
   - 原：`SIC_i18n.textOf(p, 'summary')`
   - 改：`self.summaryOf(p)`

2. **`renderPage()`** L234：
   - 原：`SIC_i18n.textOf(p, 'summary')`
   - 改：`self.summaryOf(p)`

3. **`openDetail()`** L386：
   - 详情面板的 summary 行改为 `self.summaryOf(p)`（中文模式显示 llm_summary）
   - L415 的 LLM Summary 区块**保持不变**（已展示 `summaryText`，这是 detail JSON 的 llm_summary）
   - **详情面板同时展示两个**：原生 summary + llm_summary 中文评价。具体做法：
     - L386 的 summary 行显示 `SIC_i18n.textOf(p, 'summary')`（原生原文，保持不变）
     - L415 的 LLM Summary 区块保持不变（展示 detail 的 llm_summary）
     - 但在 slim 列表/卡片中用 `summaryOf()` 优先中文

   **修正**：详情面板 L386 保持显示原生 `summary`（原文），LLM Summary 区块（L415）已有独立展示。卡片和表格用 `summaryOf()` 优先中文。这样详情面板"同时展示两个"的需求已满足。

### 验收
- 中文模式下，发现卡片显示中文 llm_summary（有则显示，无则 fallback 英文 summary）
- 中文模式下，表格列表显示中文 llm_summary
- 英文模式不受影响（仍显示原生 summary）
- 详情面板同时有原生 summary（顶部）和 LLM Summary（独立区块）
- `build_site` 后 `projects.json` 中项目对象包含 `llm_summary` 字段

---

## 第五步：任务 3 — 报告浮窗滚动条修复

### 目标

`render.js` 的 `renderReport()`（L458-513）将 markdown 表格渲染为 `<table>`，宽表格撑破 `.modal-body`。修复为横向可滚动。

### 改动

**`site/js/render.js`** — `renderReport()` 函数：

表格闭合处（L494 和 L502）：
- 原：`result.push('<table>' + tableRows.join('') + '</table>');`
- 改：`result.push('<div class="table-scroll"><table>' + tableRows.join('') + '</table></div>');`

两处都改（L494 是循环内闭合，L502 是结尾未闭合表格的收尾）。

**`site/styles.css`**：
```css
.report-content .table-scroll {
  overflow-x: auto;
  margin: 12px 0;
}
.report-content table {
  min-width: 100%;
}
```
- `.report-content table` 已有 `width: 100%`（L651），加 `min-width: 100%` 确保窄表格也填满
- 宽表格由 `.table-scroll` 的 `overflow-x: auto` 提供横向滚动
- `.modal-body` 的 `overflow-y: auto`（L790）保持不变，竖向滚动正常

### 验收
- 打开工具对比报告（含宽表格），表格在 modal 内横向可滚动
- 竖向滚动正常（modal body 滚动）
- 表格不撑破 modal 宽度

---

## 第六步：任务 4 — 报告入口突出

### 目标

三个报告 pill 从 `<nav>` 移到独立报告栏，nav 只保留导出收藏。

### 改动

**`site/index.html`**（L38-44 区域）：

当前 nav：
```html
<nav>
  <a href="#" data-report="curated-top.md" data-i18n="navTop">推荐榜</a>
  <a href="#" data-report="weekly-report.md" data-i18n="navWeekly">生态周报</a>
  <a href="#" data-report="tool-comparison.md" data-i18n="navCompare">工具对比</a>
  <button id="exportFav" class="fav-btn" data-i18n="exportFav">导出收藏</button>
  <input id="favExportUrl" type="text" class="fav-export-input" readonly style="display:none;" placeholder="收藏链接">
</nav>
```

改为：
```html
<nav>
  <button id="exportFav" class="fav-btn" data-i18n="exportFav">导出收藏</button>
  <input id="favExportUrl" type="text" class="fav-export-input" readonly style="display:none;" placeholder="收藏链接">
</nav>
<div class="report-bar">
  <a href="#" data-report="curated-top.md" data-i18n="navTop">推荐榜</a>
  <a href="#" data-report="weekly-report.md" data-i18n="navWeekly">生态周报</a>
  <a href="#" data-report="tool-comparison.md" data-i18n="navCompare">工具对比</a>
</div>
```

**`site/styles.css`**：
```css
.report-bar {
  margin-top: 12px;
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  max-width: var(--max-width);
  margin-left: auto;
  margin-right: auto;
}
```
- 报告 pill 样式：复用现有 `nav a[data-report]` 样式（L89-118），或将选择器扩展为 `.report-bar a[data-report]`
- 确保现有 `nav a[data-report]` 的样式也应用到 `.report-bar a[data-report]`（可用 `.report-bar a` 或合并选择器）
- 报告 pill 的 active 状态（`setReportActive()` 在 `app.js` L48-54 用 `[data-report]` 选择器）继续生效，因为 `data-report` 属性不变

**`site/js/app.js`**：
- L354 的 `document.querySelectorAll('[data-report]')` 事件绑定**不需要改**——它选择所有带 `data-report` 的元素，报告 pill 移到 `.report-bar` 后属性不变，事件绑定自动生效
- 确认 `setReportActive()`（L42-55）的 `document.querySelectorAll('[data-report]')` 也能选到新位置的 pill——是的，`data-report` 属性不变

### 验收
- nav 中只有导出收藏按钮和收藏链接输入框
- nav 下方有独立报告栏，背景色与 nav 区分
- 三个报告 pill 在报告栏中，点击可打开 modal
- 报告 pill 的 active 状态正常切换
- 报告栏在窄屏正常 wrap

---

## 第七步：构建与部署

```bash
cd "/root/workspace/search in coding"

# 1. 重新构建站点（SLIM_FIELDS 改了，需要重新生成 projects.json + hash）
python3 scripts/build_site.py

# 2. 验证 projects.json 包含 llm_summary
python3 -c "
import json
with open('site/data/projects.json') as f:
    data = json.load(f)
has_llm = sum(1 for p in data if 'llm_summary' in p)
print(f'projects.json: {len(data)} projects, {has_llm} have llm_summary')
"

# 3. 部署
python3 scripts/deploy_site.py
```

---

## 第八步：验收清单

| # | 验收项 | 方法 |
|---|--------|------|
| 1 | 工具/类型标签有标题分区 | 打开站点，查看搜索区标签上方有"工具"/"类型"小标题 |
| 2 | 中文模式显示中文 llm_summary | 切换中文，发现卡片和表格显示中文评价（有 llm_summary 的项目） |
| 3 | 英文模式不受影响 | 切换英文，显示原生英文 summary |
| 4 | 详情面板同时有 summary 和 LLM Summary | 打开项目详情，顶部有原生 summary，下方有 LLM Summary 区块 |
| 5 | 报告浮窗宽表格可横向滚动 | 打开工具对比报告，宽表格在 modal 内可横向滚动 |
| 6 | 报告浮窗竖向滚动正常 | 报告内容超出 modal 高度时可竖向滚动 |
| 7 | nav 只有导出收藏 | nav 中无报告 pill |
| 8 | 独立报告栏存在 | nav 下方有背景色区分的报告栏，三个 pill 在此 |
| 9 | 报告 pill 点击正常 | 点击报告 pill 可打开 modal，active 状态正常 |
| 10 | 筛选/收藏/深链/分页不受影响 | 回归测试核心功能 |
| 11 | projects.json 包含 llm_summary | 构建后验证 JSON 字段 |

---

## 允许修改的文件

| 文件 | 改动范围 |
|------|----------|
| `site/index.html` | 标签分区标题 DOM、报告栏 DOM |
| `site/js/render.js` | `summaryOf()` 函数、`renderDiscovery`/`renderPage` 调用、`renderReport` 表格包裹 |
| `site/js/app.js` | 仅当事件绑定需要调整时（预计不需要） |
| `site/js/i18n.js` | 新增 `filterTools` / `filterTypes` 翻译键 |
| `site/styles.css` | `.filter-label`、`.report-bar`、`.table-scroll` 样式 |
| `scripts/build_site.py` | **仅** `SLIM_FIELDS` 列表加 `'llm_summary'` |

## 不允许修改的文件

- `site/js/data.js`
- `site/js/filters.js`
- `site/js/charts.js`
- `data/*`（YAML / JSON 原始数据）
- `scripts/normalize.py`
- `scripts/score.py`
- `scripts/llm_prompts.py`（批次 2 任务）

---

## 关键约束

1. **零依赖**：不引入任何前端框架、图表库、CSS 框架
2. **不破坏现有功能**：筛选、收藏、深链、分页、排序、报告 modal 全部正常
3. **中文模式优先 llm_summary**：`lang == 'zh'` 且项目有 `llm_summary.zh` 时优先使用，否则 fallback 英文 summary
4. **build_site.py 只改 SLIM_FIELDS**：不碰数据写出逻辑、不碰 hash 生成、不碰 detail 分片
5. **DOM id 契约不变**：`#toolTags` `#typeTags` `#reportModal` `#reportBackdrop` `#reportModalBody` `#exportFav` `#favExportUrl` 以及 `data-report` 文件名
