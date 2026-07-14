# L4A-前端详解 - 前端怎么改

> 前端开发者深入文档。读完能独立修改前端代码。
>
> **第 3 批前端重写 v3**（2026-07-13）。批次 B：Linear/Vercel 审美重做 + 15 个 dogfood 交互修复。

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
| `tool-tag` | 点击工具标签按钮 | `SIC_filters.toggleTool()` + 重新渲染表格 |
| `type-tag` | 点击类型标签按钮 | `SIC_filters.toggleType()` + 重新渲染表格 |
| `tool-filter` | 点击工具概览卡片 | `SIC_filters.setTool()` + 同步标签按钮 + 滚动到搜索区 |
| `remove-filter` | 点击筛选 chip 的 × 按钮 | 移除对应筛选条件 + 重新渲染 + syncUI |
| `reload` | 点击重试按钮 | `location.reload()` |

**关键：** 工具卡片点击后调用 `renderTagButtons()` 重新渲染标签按钮组，使 tag button 的 active 状态与 selectedTools 同步（Bug 3 修复）。

## 三区布局

| 区域 | HTML section id | 渲染函数 | 用途 |
|------|----------------|---------|------|
| 发现区 | #discoverySection | renderDiscovery() | 最新发现高质量项目（按 first_seen + 分数排序取 Top 12，无时间 cutoff） |
| 工具概览区 | #toolOverviewSection | renderToolOverview() | 10 个工具的生态规模卡片，点击跳转搜索区筛选 |
| 搜索区 | #searchZone | renderSearchZone() | 多选标签筛选 + 6 种排序 + 虚拟滚动表格 |

## 页面状态

无路由库。单页应用，所有内容在 index.html 中通过 JS 渲染。

**URL 状态持久化：** query string 保存筛选状态，通过 SIC_filters.readState() / writeState() 读写。

支持的 query 参数：
- `q` - 搜索关键词
- `tools` - 选中的工具 ID（逗号分隔）
- `types` - 选中的 resource_type（逗号分隔）
- `sort` - 排序方式（score/stars/updated/match/recent/name）
- `mode` - 匹配模式（or/and）
- `curated` - 只看推荐（1）
- `recent` - 只看最近新增（1）
- `fav` - 只看收藏（1）**[v3 新增]**
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
| loadAll(onProgress) | (fn) => Promise<bool> | 渐进式加载 4 个 JSON（metrics -> tools -> projects -> curated） |
| fetchJSON(url, onProgress, label) | (string, fn, string) => Promise | fetch 封装 |
| loadDetail(projectId) | (string) => Promise<obj> | 懒加载 projects-detail.json，缓存全部详情 |
| isFav(id) / toggleFav(id) | (string) => bool/void | 收藏管理 |
| exportFavoritesUrl() | () => string | 导出收藏 URL（hash 编码） |
| curatedIds() | () => Set | 返回 curated 项目 ID 集合 |

**数据字段（精简版 projects.json）：** id, name, url, source_type, resource_type, target_tools, summary, i18n, stars, forks, total_score, quantifiable_score, quality_score, tracking_priority, last_updated, first_seen, last_seen, license, languages, review_state

**详情版（projects-detail.json）额外字段：** score_detail, quality_detail, llm_summary, benchmark_ref, last_analyzed, repo, tags, maturity, status

### filters.js - SIC_filters

| 方法 | 签名 | 用途 |
|------|------|------|
| toggleTool(id) / toggleType(type) | (string) => void | 切换标签选中状态 |
| toggleMode() | () => void | 切换 OR/AND |
| setTool(id) | (string) => void | 清空并选中单个工具 |
| hasActiveFilters() | () => boolean | 检查是否有活跃筛选 **[v3 新增]** |
| clearAll() | () => void | 清空所有筛选 **[v3 新增]** |
| apply(projects, curatedIds) | (array, Set) => array | 筛选 + 排序，返回结果数组 |
| readState() / writeState() | () => void | URL 状态读写（writeState 保留 hash） |

**筛选逻辑：**
- 排除 official-seed 和 reject 项目
- 搜索关键词：JSON.stringify 全文匹配
- 工具筛选：target_tools 包含关系，OR 模式 some()，AND 模式 every()
- 类型筛选：resource_type 包含关系，同上
- curatedOnly：id 在 curated 集合中

**排序模式（6 种）：**
- `score` - total_score 降序（默认）
- `stars` - stars 降序
- `updated` - last_updated 倒序
- `match` - 标签匹配数降序 + 分数降序
- `recent` - first_seen/last_seen 倒序
- `name` - 名称 localeCompare

### render.js - SIC_render

| 方法 | 签名 | 用途 |
|------|------|------|
| renderAll() | () => void | 渲染全部三区 + scoreChart + writeState() |
| renderMetrics() | () => void | 渲染 Hero 区域指标卡（v3: 移到 header） |
| renderDiscovery() | () => void | 渲染发现区（按 first_seen 降序 + 分数降序取 Top 12） |
| renderToolOverview() | () => void | 渲染工具概览卡片 + 调用 SIC_charts.barChart() |
| renderScoreChart() | () => void | 渲染分数分布直方图（v3: 移到工具概览区下方） |
| renderSearchZone() | () => void | 筛选 + 渲染表格 + 结果计数 + 活跃条件 chips + 清空按钮 |
| renderActiveFilters() | () => void | 渲染活跃筛选条件 chips **[v3 新增]** |
| renderMore() | () => void | 分页加载（PAGE_SIZE=50）+ IntersectionObserver |
| openDetail(projectId) | (string) => void | 打开详情面板（v3: 立即显示 loading → 展示 score_detail → 隐藏空字段） |
| closeDetail() | () => void | 关闭详情面板 |
| toggleFav(id) | (string) => void | 切换收藏状态 |
| pills(xs) | (array) => string | 渲染色彩标签（v3: 用 i18n 翻译 + pill-type-* 颜色类） |
| toolLabels(toolIds) | (array) => string | 渲染工具名标签（v3: 用 tools.json 的 name 而非 id） **[v3 新增]** |
| renderReport(md) | (string) => string | Markdown -> HTML 渲染（v3: 表头用 th 而非 td） |
| showSkeleton() | () => void | 骨架屏 |
| showError() | () => void | 错误状态 + 重试按钮 |

**虚拟滚动修复（Bug 4）：** IntersectionObserver 在 renderMore 每次加载后对新最后一行重新 observe；renderSearchZone 开始时 disconnect 旧 observer。Observer 只创建一次，通过 unobserve + observe 切换观察目标。

**LLM Summary 修复（Bug 7）：** detail 面板中 llm_summary 字段是 `{zh, en}` 对象（不是 i18n 结构），通过 `llmSummary[SIC_i18n.lang] || llmSummary.en || llmSummary.zh` 取值。

### charts.js - SIC_charts

| 方法 | 签名 | 用途 |
|------|------|------|
| barChart(data, maxVal) | (array, number) => string | SVG 柱状图 |
| histogram(scores) | (array) => string | 分数分布直方图（5 个区间） |

### app.js - 入口

| 函数 | 用途 |
|------|------|
| main() | 异步入口：骨架屏 -> loadAll -> readState -> renderAll -> 事件绑定 |
| debounce(fn, ms) | 搜索防抖（300ms） |
| syncUIFromFilters() | readState 后同步 UI 控件状态 |
| renderTagButtons() | 渲染工具和类型标签按钮组 |
| toggleToolTag(id, btn) / toggleTypeTag(type, btn) | 标签按钮点击处理 |

## 样式体系

全深色主题（dark mode only），Linear/Vercel 风格。使用 **CSS 自定义属性**（ADR-0006）。

**CSS 变量（:root）：**

| 变量 | 值 | 用途 |
|------|-----|------|
| --color-bg | #0f172a | 页面背景 |
| --color-bg-gradient | linear-gradient(180deg, #0f172a 0%, #1e293b 100%) | header 渐变背景 **[v3]** |
| --color-surface | #111827 | 表格背景 |
| --color-card | #1e293b | 卡片背景 |
| --color-card-hover | #243244 | 表格行 hover 背景 **[v3]** |
| --color-input | #020617 | 输入框背景 |
| --color-text | #e2e8f0 | 正文文本 |
| --color-text-secondary | #cbd5e1 | header 副文本 |
| --color-text-muted | #94a3b8 | 次要文本 |
| --color-link | #93c5fd | 链接 |
| --color-border | #334155 | 边框 |
| --color-border-subtle | rgba(255,255,255,0.08) | 半透明边框 **[v3]** |
| --color-accent | #2563eb | 强调色 |
| --color-accent-gradient | linear-gradient(135deg, #2563eb, #7c3aed) | 渐变强调色 **[v3]** |
| --color-accent-light | #60a5fa | 强调色（边框 hover） |
| --color-fav | #fbbf24 | 收藏星标色 |
| --radius | 12px | 圆角 |
| --spacing | 32px | 间距（v3: 从 24px 增大） |
| --shadow-card | 0 2px 8px rgba(0,0,0,0.3), 0 0 1px rgba(255,255,255,0.05) | 卡片阴影 **[v3]** |
| --shadow-card-hover | 0 4px 16px rgba(0,0,0,0.4), 0 0 1px rgba(255,255,255,0.1) | 卡片 hover 阴影 **[v3]** |

**色彩标签 pill 类（v3 新增）：**

| 类名 | 颜色 | 对应 resource_type |
|------|------|-------------------|
| .pill-type-mcp-server | 绿底绿字 | MCP Server |
| .pill-type-skills | 蓝底蓝字 | Skills |
| .pill-type-rules | 紫底紫字 | Rules |
| .pill-type-agent-framework | 橙底橙字 | Agent Framework |
| .pill-type-cli-tool | 青底青字 | CLI Tool |
| .pill-type-tutorial | 灰底灰字 | Tutorial |

**字体层级（v3）：** h1=40px(800), h2=28px(700), h3=20px(600), 正文=16px。Inter 字体通过 Google Fonts 加载。

**响应式断点：** 760px（缩小 padding、表格 min-width:600px、topbar 改 column、详情面板全宽、grid 改单列、hero-stat 缩小）

**骨架屏：** shimmer 动画（linear-gradient + background-position 动画）

## build_site.py 与前端的关联

build_site.py 生成：
1. **精简 JSON**（projects.json 等）- 只含表格展示字段
2. **详情 JSON**（projects-detail.json）- 全量字段，懒加载
3. **带 hash 的 JS/CSS 文件名**（如 app.517e5a.js）- Nginx 长缓存 immutable
4. **sitemap.xml** - 站点地图
5. **更新 index.html 中的引用** - 指向带 hash 的文件名

**重要：** build_site.py 多次运行时会先清理旧 hash 文件、恢复 index.html 原始引用，再重新生成 hash。这是幂等操作。

## 交互模式

**筛选（标签按钮组多选）：**
1. 工具标签按钮组（#toolTags）- 多选，点击高亮
2. 类型标签按钮组（#typeTags）- 多选，点击高亮
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
- 懒加载详情数据，llm_summary 按 {zh,en} 对象取值

**报告渲染：** 点击导航链接 -> fetch .md 文件 -> Markdown 渲染器（v3: 表头用 th）-> 在详情面板中展示

**收藏：** 点击 ★ 按钮 -> localStorage 存储 -> 可通过"导出收藏"按钮显示 URL 输入框 -> "只看收藏"筛选 **[v3]**

**双语切换：** 点击 中文/English 按钮 -> setLang() + localStorage -> renderAll()，按钮有 aria-pressed **[v3]**

**页脚（v3 新增，dogfood #14）：** 显示数据更新时间 + GitHub 仓库链接 + 数据说明

**键盘导航：** ESC 关闭详情面板

## 下一步读什么

-> [L5-接口契约](L5-接口契约.md)

## 更新指引

**触发条件：** 页面增删、state 结构变更、交互流程变更、样式变量变更、模块结构变更
**更新内容：** 三区布局、模块详解、全局对象、交互模式、CSS 变量
