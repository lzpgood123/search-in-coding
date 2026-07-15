# L4A-前端详解 - 前端怎么改

> 前端开发者深入文档。读完能独立修改前端代码。
>
> **第 3 批前端重写 v3**（2026-07-13）。批次 B：Linear/Vercel 审美重做 + 15 个 dogfood 交互修复。
>
> **Style B 完整视觉落地**（2026-07-15）：Warm paper dark + 琥珀强调；metrics 下并排可读图表；独立报告栏 + 居中 modal；详情右侧侧栏仅换皮。
>
> **前端体验打磨**（2026-07-15）：工具/类型标签分区标题；中文模式卡片/表格优先 `llm_summary`；报告表格横向滚动；报告 pill 移出 nav。

## 架构概览

零框架、零依赖的纯原生 JS SPA。模块化拆分为 6 个 JS 文件，通过多 `<script>` 标签加载，全局变量共享（ADR-0006）。

**脚本加载顺序：** i18n.js -> data.js -> filters.js -> charts.js -> render.js -> app.js

### 事件委托架构（v2 新增）

第 3 批重写引入事件委托替代 inline onclick。所有动态生成的元素通过 `data-action` 属性标识点击类型，在 `document` 上统一监听 click 事件。

**支持的 data-action 值：**

| data-action | 触发场景 | 处理逻辑 |
|-------------|---------|---------|
| `detail` | 点击项目卡片/项目名/详情按钮 | 调用 `SIC_render.openDetail(id)` |
| `fav` | 点击收藏按钮 | 调用 `SIC_render.toggleFav(id)` + 切换 active 类 |
| `close-detail` | 点击关闭按钮 | 调用 `SIC_render.closeDetail()` |
| `close-report` | 报告 modal × | 调用 `closeReportModal()` **[Style B]** |
| `tool-tag` | 点击工具标签按钮 | `SIC_filters.toggleTool()` + 重新渲染表格 |
| `type-tag` | 点击类型标签按钮 | `SIC_filters.toggleType()` + 重新渲染表格 |
| `tool-filter` | 点击工具概览卡片 | `SIC_filters.setTool()` + 同步标签按钮 + 滚动到搜索区 |
| `remove-filter` | 点击筛选 chip 的 × 按钮 | 移除对应筛选条件 + 重新渲染 + syncUI |
| `page` | 点击页码按钮 | 切换 `SIC_render.currentPage` + renderPage/Pagination + 滚到表格顶 **[交互优化]** |
| `reload` | 点击重试按钮 | `location.reload()` |

**关键：** 工具卡片点击后调用 `renderTagButtons()` 重新渲染标签按钮组，使 tag button 的 active 状态与 selectedTools 同步（Bug 3 修复）。

## 三区布局

| 区域 | HTML section id | 渲染函数 | 用途 |
|------|----------------|---------|------|
| 发现区 | #discoverySection | renderDiscovery() | 最新发现高质量项目（按 first_seen + 分数排序取 Top 12，无时间 cutoff） |
| 工具概览区 | #toolOverviewSection | renderToolOverview() | 10 个工具的生态规模卡片，点击跳转搜索区筛选 |
| 搜索区 | #searchZone | renderSearchZone() | 多选标签筛选 + 6 种排序（表头可点） + **每页 20 条页码表格** |

## 页面状态

无路由库。单页应用，所有内容在 index.html 中通过 JS 渲染。

**URL 状态持久化：** query string 保存筛选状态，通过 SIC_filters.readState() / writeState() 读写。

支持的 query 参数：
- `q` - 搜索关键词
- `tools` - 选中的工具 ID（逗号分隔）
- `types` - 选中的 resource_type（逗号分隔）
- `sort` - 排序方式（score/stars/updated/match/recent/name）
- `dir` - 排序方向（asc/desc；默认 desc 时不写入 URL） **[交互优化 2026-07-15]**
- `mode` - 匹配模式（or/and）
- `curated` - 只看推荐（1）
- `recent` - 只看最近新增（1）
- `fav` - 只看收藏（1）**[v3 新增]**
- `page` - 当前页（1-based；第 1 页不写入 URL） **[交互优化 2026-07-15]**
- `project` - 项目深链 ID，打开时自动展开详情 **[v3 新增]**

**Hash 参数：** `#favorites=id1,id2` 用于导入收藏。writeState 现在保留 hash（dogfood #6 修复）。

## 全局对象

| 变量 | 类型 | 定义位置 | 用途 |
|------|------|---------|------|
| SIC_i18n | object | i18n.js | 双语配置、语言切换 |
| SIC_data | object | data.js | 数据加载、收藏管理 |
| SIC_filters | object | filters.js | 筛选状态、排序、URL 读写 |
| SIC_render | object | render.js | 三区渲染、详情面板、骨架屏 |
| SIC_charts | object | charts.js | SVG 图表 |

## 模块详解

### i18n.js - SIC_i18n

| 方法 | 签名 | 用途 |
|------|------|------|
| t(key) | (string) => string | 获取当前语言的翻译文本 |
| textOf(item, field) | (obj, string) => string | 从项目 i18n 结构取双语字段 |
| setLang(l) | ('zh'\|'en') => void | 切换语言，保存到 localStorage |
| applyLanguage() | () => void | 应用语言到 DOM（data-i18n 属性） |

**lang 初始值：** localStorage('sic_lang') 或 navigator.language 判断。

### data.js - SIC_data

| 方法 | 签名 | 用途 |
|------|------|------|
| loadAll(onProgress) | (fn) => Promise<bool> | 渐进式加载 metrics → tools → projects → curated → **search-index**，并构建 `searchMap` |
| fetchJSON(url, onProgress, label) | (string, fn, string) => Promise | fetch 封装 |
| loadDetail(projectId) | (string) => Promise<obj> | 读 detail-index → fetch `detail/{chunk}.json` → 缓存分片内条目；**无**单体 fallback |
| isFav(id) / toggleFav(id) | (string) => bool/void | 收藏管理 |
| exportFavoritesUrl() | () => string | 导出收藏 URL（hash 编码） |
| curatedIds() | () => Set | 返回 curated 项目 ID 集合 |

**状态字段：** `searchMap`（id→text）、`_detailIndex`（id→chunk）、`projectDetails`（详情缓存）

**数据字段（精简版 projects.json / SLIM_FIELDS）：** id, name, url, source_type, resource_type, target_tools, summary, i18n, stars, forks, total_score, quantifiable_score, quality_score, tracking_priority, last_updated, first_seen, last_seen, license, languages, review_state, **llm_summary**（2026-07-15 打磨：卡片/表格中文优先）

**搜索索引（search-index.json）：** `[{id, text}]`，text = lower(name + summary + resource_type + target_tools)

**详情分片（detail/{i}.json + detail-index.json）：** 100 条/片；额外字段 score_detail, quality_detail, llm_summary, benchmark_ref, last_analyzed, repo, tags, maturity, status, readme_preview, topics。**不再生成** projects-detail.json

### filters.js - SIC_filters

| 方法 | 签名 | 用途 |
|------|------|------|
| toggleTool(id) / toggleType(type) | (string) => void | 切换标签选中状态 |
| toggleMode() | () => void | 切换 OR/AND |
| toggleSort(field) | (string) => void | 表头排序：同列切换升降序，新列默认 desc **[交互优化]** |
| setTool(id) | (string) => void | 清空并选中单个工具 |
| hasActiveFilters() | () => boolean | 检查是否有活跃筛选 **[v3 新增]** |
| clearAll() | () => void | 清空所有筛选（含 sortDirection 重置为 desc） **[v3 新增]** |
| apply(projects, curatedIds) | (array, Set) => array | 筛选 + 排序，返回结果数组 |
| readState() / writeState() | () => void | URL 状态读写（writeState 保留 hash；含 dir/page） |

**筛选逻辑：**
- 排除 official-seed 和 reject 项目
- 搜索关键词：`SIC_data.searchMap[id].includes(q)`（批次 2）；**禁止** `JSON.stringify(project)` 全文匹配
- 工具筛选：target_tools 包含关系，OR 模式 some()，AND 模式 every()
- 类型筛选：resource_type 包含关系，同上
- curatedOnly：id 在 curated 集合中

**排序模式（6 种）：**
- `score` - total_score（默认；方向由 sortDirection 控制）
- `stars` - stars
- `updated` - last_updated
- `match` - 标签匹配数 + 分数
- `recent` - first_seen/last_seen
- `name` - 名称 localeCompare

**升降序：** `sortDirection` 为 `asc|desc`；比较器统一按升序算 cmp，再按方向取 `cmp` 或 `-cmp`（避免 name 与数值方向语义不一致）。

### render.js - SIC_render

| 方法 | 签名 | 用途 |
|------|------|------|
| renderAll() | () => void | 渲染全部三区 + scoreChart + writeState() |
| renderMetrics() | () => void | 渲染 Hero 区域指标卡（v3: 移到 header） |
| renderDiscovery() | () => void | 渲染发现区（按 first_seen 降序 + 分数降序取 Top 12） |
| renderToolOverview() | () => void | 渲染工具概览卡片 + 调用 SIC_charts.barChart()（水平） |
| renderScoreChart() | () => void | 渲染分数分布直方图（垂直） |
| renderSearchZone() | () => void | 筛选 + 重置/恢复 page + 渲染表格 + 结果计数 + 活跃条件 chips + 清空按钮 |
| renderActiveFilters() | () => void | 渲染活跃筛选条件 chips **[v3 新增]** |
| renderPage() | () => void | 渲染当前页 20 条（替换旧 renderMore 无限滚动） **[交互优化]** |
| renderPagination() | () => void | 底部页码控件（省略号、上一页/下一页、pageOf） **[交互优化]** |
| renderSortIndicators() | () => void | 可排序表头 ▲/▼ **[交互优化]** |
| openDetail(projectId) | (string) => void | 打开详情面板（v3: 立即显示 loading → 展示 score_detail → 隐藏空字段） |
| closeDetail() | () => void | 关闭详情面板 |
| toggleFav(id) | (string) => void | 切换收藏状态 |
| pills(xs) | (array) => string | 渲染色彩标签（v3: 用 i18n 翻译 + pill-type-* 颜色类） |
| toolLabels(toolIds) | (array) => string | 渲染工具名标签（v3: 用 tools.json 的 name 而非 id） **[v3 新增]** |
| summaryOf(item) | (obj) => string | 中文模式优先 `llm_summary.zh`（无则 en），否则 `textOf(summary)` **[打磨 2026-07-15]** |
| renderReport(md) | (string) => string | Markdown -> HTML；表格外包 `.table-scroll` 横向滚动 **[打磨]** |
| showSkeleton() | () => void | 骨架屏 |
| showError() | () => void | 错误状态 + 重试按钮 |

**分页（2026-07-15）：** `PAGE_SIZE=20`，`currentPage` 0-based；筛选变化默认回第 1 页；URL `page` 深链会 clamp 到合法页。**已移除** IntersectionObserver 无限滚动。

**LLM Summary 修复（Bug 7）：** detail 面板中 llm_summary 字段是 `{zh, en}` 对象（不是 i18n 结构），通过 `llmSummary[SIC_i18n.lang] || llmSummary.en || llmSummary.zh` 取值。

**中文摘要（打磨 2026-07-15）：** 发现卡片 `renderDiscovery()` 与表格 `renderPage()` 用 `summaryOf()`：`lang==='zh'` 且存在 `llm_summary` 时优先中文评价；英文模式与无 llm_summary 时 fallback 原生 summary。详情顶部仍显示原生 summary，下方独立 LLM Summary 区块不变。

### charts.js - SIC_charts

| 方法 | 签名 | 用途 |
|------|------|------|
| barChart(data, maxVal, options?) | (array, number, object?) => string | **水平**柱状图：左侧完整工具名、柱子向右、末端数值、X 刻度；用于工具覆盖 **[交互优化]** |
| _verticalBarChart(data, maxVal, options?) | (array, number, object?) => string | **垂直**柱状图：Y 轴+网格+柱顶数值；仅 histogram 使用 |
| histogram(scores) | (array) => string | 分数分布直方图（5 桶 0-20…81-100），内部调 `_verticalBarChart`（保持垂直） |

**挂载位置：** `#toolChart` / `#scoreChart` 在 header metrics 下方 `.charts-row` 内（不再位于工具概览 section 底部）。

### app.js - 入口

| 函数 | 用途 |
|------|------|
| main() | 异步入口：骨架屏 -> loadAll -> readState -> renderAll -> 事件绑定 |
| debounce(fn, ms) | 搜索防抖（300ms） |
| syncUI() | readState 后同步 UI 控件状态 |
| renderTagButtons() | 渲染工具和类型标签按钮组 |
| openReportModal(file) | fetch `reports/<file>` → `SIC_render.renderReport` 写入 `#reportModalBody`；**不**写入 detailOverlay **[Style B]** |
| closeReportModal() | 关 modal/backdrop，清 active，恢复 overflow（若 detail 未开） **[Style B]** |
| isReportOpen() / setReportActive(file) | modal 状态与 pill/tab 高亮 **[Style B]** |
| handleGlobalClick() | 含 `close-report`、`page` 等 data-action |

## 样式体系

全深色主题（dark mode only），**Style B Warm paper dark + 琥珀强调**（2026-07-15）。使用 **CSS 自定义属性**（ADR-0006）。

**CSS 变量（:root，Style B）：**

| 变量 | 值 | 用途 |
|------|-----|------|
| --color-bg | #1c1917 | 页面背景（暖石色） |
| --color-bg-gradient | linear-gradient(180deg, #24201c 0%, #1c1917 100%) | header 渐变 |
| --color-bg-elevated | #292524 | 浮层/详情底 |
| --color-surface | #292524 | 表格背景 |
| --color-surface-2 | #35302c | 次级面 |
| --color-card | #2c2825 | 卡片背景 |
| --color-card-hover | #35302c | 行/卡 hover |
| --color-input | #1a1714 | 输入框背景 |
| --color-text | #faf7f2 | 正文 |
| --color-text-secondary | #e7e0d6 | 副文本 |
| --color-text-muted | #b5aa9c | 次要文本 |
| --color-link | #fcd34d | 链接（琥珀浅） |
| --color-border | rgba(255,248,240,0.10) | 边框 |
| --color-border-strong | rgba(255,248,240,0.16) | 强边框 |
| --color-border-subtle | rgba(255,248,240,0.08) | 细边框 |
| --color-accent | #f59e0b | 主强调（琥珀） |
| --color-accent-light | #fbbf24 | 强调浅色 |
| --color-accent-soft | rgba(245,158,11,0.14) | 软填充 |
| --color-accent-border | rgba(245,158,11,0.35) | 强调边框 |
| --color-accent-gradient | linear-gradient(135deg, #f59e0b, #fbbf24) | 兼容旧名，不再作蓝紫主强调 |
| --color-fav | #fbbf24 | 收藏星标 |
| --radius / --radius-sm / --radius-xs | 16 / 12 / 10 | 圆角 |
| --spacing | 22px | 中等偏紧间距 |
| --shadow-card / --shadow-card-hover | 深色克制阴影 | 卡片 |

**已停用主用法：** 近黑 `#0f172a` 主背景、蓝紫主强调。

**色彩标签 pill 类：** 保留多色语义，**降饱和**与暖底协调（mcp / skills / rules / framework / cli / tutorial）。

**字体层级（Style B）：** h1≈25px、section h2≈17px、正文 14px。**系统字体栈 only**；禁止 Google Fonts。

**布局组件（Style B）：**
- `.charts-row`：桌面 `1.15fr 0.85fr`，≤1100px 堆叠；`.chart-card` 含标题/副标题
- `.toolbar`：搜索 controls 外壳
- `.modal-backdrop` / `.modal` / `.modal-tabs` / `.modal-body`：居中报告浮窗（宽 `min(720px,100vw-32px)`，max-height≈78vh）
- `.detail-overlay`：右侧侧栏宽 `min(560px,100%)`，仅 B 皮肤

**响应式断点：** 1100px（图表堆叠、metrics 2 列）；760px（单列、详情全宽、表格 min-width）

**动效：** `:active { scale(0.97) }`；`prefers-reduced-motion: reduce` 关闭非必要 transform/动画

**骨架屏：** shimmer 动画

## build_site.py 与前端的关联

build_site.py 生成：
1. **精简 JSON**（projects.json 等）- 只含表格展示字段（SLIM_FIELDS）
2. **搜索索引**（search-index.json）- 轻量 id+text
3. **详情分片**（detail/{i}.json，chunk=100）+ **detail-index.json**（id→chunk）
4. **带 hash 的 JS/CSS 文件名**（如 app.517e5a.js）- Nginx 长缓存 immutable
5. **sitemap.xml** / **robots.txt**
6. **更新 index.html 中的引用** - 指向带 hash 的文件名
7. **删除** 单体 `projects-detail.json`（若存在）

**重要：** build_site.py 多次运行时会先清理旧 hash 文件与旧 detail 分片、恢复 index.html 原始引用，再重新生成。这是幂等操作。

## 交互模式

**筛选（标签按钮组多选）：**
1. 工具标签按钮组（#toolTags）- 多选，点击高亮；上方 `.filter-label`（i18n `filterTools`）**[打磨]**
2. 类型标签按钮组（#typeTags）- 多选，点击高亮；上方 `.filter-label`（i18n `filterTypes`）**[打磨]**
3. OR/AND 切换（#modeToggle）- 默认 OR，radiogroup 行为（点已选项不翻转）**[v3: dogfood #8]**
4. 排序下拉框（#sort）- 6 种排序
5. 只看推荐复选框（#curatedOnly）
6. 只看最近新增复选框（#recentOnly）
7. 只看收藏复选框（#favoritesOnly）**[v3: dogfood #5]**

**结果反馈（v3 新增，dogfood #7）：**
- 结果计数：显示"显示 X / Y"
- 活跃条件 chips：当前筛选条件以可移除的 chip 形式展示
- 清空筛选按钮：一键复位所有筛选

**工具概览区交互：** 点击工具卡片 -> setTool()（清空工具筛选 + 选中该工具）-> renderTagButtons() 同步标签按钮 active 状态 -> 跳转到搜索区

**详情面板（v3 重大更新）：**
- 点击项目名/卡片/详情按钮 -> 右侧滑出面板
- **立即显示 loading 状态**（dogfood #9），数据到达后替换
- 展示评分分项 score_detail（stars/20, activity/15, adoption/10, maturity/15）**[dogfood #10]**
- 展示质量分项 quality_detail（relevance/practicality/novelty/ecosystem_value）**[batch3 fix]**
- 已分析项目总分展示 `/100`，未分析展示 `/60`；进度条按 maxScore 计算 **[batch3 fix]**
- benchmark_ref 通过 project id 查找项目名展示，而非裸 id **[batch3 fix]**
- 未分析时质量分标注"待 LLM 分析"
- 空字段隐藏（forks/license/languages 为空时不展示）**[dogfood #12]**
- 项目深链：`?project=id` 打开时自动展开详情 **[dogfood #15]**
- 懒加载详情数据，llm_summary 按 {zh,en} 对象取值；列表中文摘要见 `summaryOf()`

**报告渲染（Style B + 打磨）：** `<nav>` 仅保留导出收藏；其下独立 `.report-bar` 放三个报告 pill（`data-report` 文件名不变）→ 居中 `#reportModal` → 浮窗内 tab 切换三报告（`curated-top.md` / `weekly-report.md` / `tool-comparison.md`）→ `SIC_render.renderReport(md)` 写入 `#reportModalBody`（宽表格包在 `.table-scroll` 内横向滚动）。**不再**把报告塞进 `#detailOverlay`。关闭：× / backdrop / Esc。

**收藏：** 点击 ★ 按钮 -> localStorage 存储 -> 可通过"导出收藏"按钮显示 URL 输入框 -> "只看收藏"筛选 **[v3]**

**双语切换：** 点击 中文/English 按钮 -> setLang() + localStorage -> renderAll()，按钮有 aria-pressed；若报告 modal 开着则刷新标题文案 **[Style B]**

**页脚（v3 新增，dogfood #14）：** 显示数据更新时间 + GitHub 仓库链接 + 数据说明

**键盘导航 / Esc 栈（Style B）：**
1. 若报告 modal 打开 → 只关 modal
2. 否则若 detail 打开 → 关 detail
3. 两者都关时 Esc 无操作

## 下一步读什么

-> [L5-接口契约](L5-接口契约.md)

## 更新指引

**触发条件：** 页面增删、state 结构变更、交互流程变更、样式变量变更、模块结构变更
**更新内容：** 三区布局、模块详解、全局对象、交互模式、CSS 变量
