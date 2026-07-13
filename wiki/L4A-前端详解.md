# L4A-前端详解 - 前端怎么改

> 前端开发者深入文档。读完能独立修改前端代码。
>
> **第 2 批重写后的版本**（2026-07-13）。

## 架构概览

零框架、零依赖的纯原生 JS SPA。模块化拆分为 6 个 JS 文件，通过多 `<script>` 标签加载，全局变量共享（ADR-0006）。

**脚本加载顺序：** i18n.js -> data.js -> filters.js -> charts.js -> render.js -> app.js

## 三区布局

| 区域 | HTML section id | 渲染函数 | 用途 |
|------|----------------|---------|------|
| 发现区 | #discoverySection | renderDiscovery() | 本周新发现高质量项目（7天内，top 12） |
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

**Hash 参数：** `#favorites=id1,id2` 用于导入收藏。

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

**详情版（projects-detail.json）额外字段：** score_detail, llm_summary, benchmark_ref, last_analyzed, repo, tags, maturity, status

### filters.js - SIC_filters

| 方法 | 签名 | 用途 |
|------|------|------|
| toggleTool(id) / toggleType(type) | (string) => void | 切换标签选中状态 |
| toggleMode() | () => void | 切换 OR/AND |
| apply(projects, curatedIds) | (array, Set) => array | 筛选 + 排序，返回结果数组 |
| readState() / writeState() | () => void | URL 状态读写 |

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
| renderAll() | () => void | 渲染全部三区 + writeState() |
| renderMetrics() | () => void | 渲染统计卡片 |
| renderDiscovery() | () => void | 渲染发现区（7天内 top 12） |
| renderToolOverview() | () => void | 渲染工具概览卡片 |
| renderSearchZone() | () => void | 筛选 + 渲染表格 |
| renderMore() | () => void | 分页加载（PAGE_SIZE=50）+ IntersectionObserver |
| openDetail(projectId) | (string) => void | 打开详情面板，懒加载详情数据 |
| closeDetail() | () => void | 关闭详情面板 |
| toggleFav(id, btn) | (string, Element) => void | 切换收藏状态 |
| renderReport(md) | (string) => string | 简易 Markdown -> HTML 渲染 |
| showSkeleton() | () => void | 骨架屏 |
| showError() | () => void | 错误状态 + 重试按钮 |

**虚拟滚动：** IntersectionObserver 观察最后一行，进入视口时加载下一页（50 条）。

**详情面板：** 右侧滑出（max-width 500px），含评分明细（进度条）、LLM 摘要、参照项目、关联项目推荐（同 resource_type 或 shared target_tools，top 5）。

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

全深色主题（dark mode only），使用 **CSS 自定义属性**（ADR-0006）。

**CSS 变量（:root）：**

| 变量 | 值 | 用途 |
|------|-----|------|
| --color-bg | #0f172a | 页面背景 |
| --color-surface | #111827 | header/表格背景 |
| --color-card | #1e293b | 卡片/统计背景 |
| --color-input | #020617 | 输入框/按钮背景 |
| --color-text | #e2e8f0 | 正文文本 |
| --color-text-secondary | #cbd5e1 | header 副文本 |
| --color-text-muted | #94a3b8 | 次要文本 |
| --color-link | #93c5fd | 链接 |
| --color-border | #334155 | 边框 |
| --color-border-light | #475569 | 边框（浅） |
| --color-accent | #2563eb | 强调色（按钮 active） |
| --color-accent-light | #60a5fa | 强调色（边框 hover） |
| --color-fav | #fbbf24 | 收藏星标色 |
| --radius | 12px | 圆角 |
| --spacing | 24px | 间距 |

**响应式断点：** 760px（缩小 padding、表格字体、topbar 改 block、详情面板全宽、grid 改单列）

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

**搜索：** 全文搜索（JSON.stringify），input 事件 + 300ms debounce

**筛选（标签按钮组多选）：**
1. 工具标签按钮组（#toolTags）- 多选，点击高亮
2. 类型标签按钮组（#typeTags）- 多选，点击高亮
3. OR/AND 切换（#modeToggle）- 默认 OR
4. 排序下拉框（#sort）- 6 种排序
5. 只看推荐复选框（#curatedOnly）

**工具概览区交互：** 点击工具卡片 -> 清空工具筛选 -> 选中该工具 -> 跳转到搜索区

**详情面板：** 点击项目"详情"按钮 -> 右侧滑出面板 -> 懒加载详情数据 -> 显示评分明细、LLM 摘要、关联项目

**报告渲染：** 点击导航链接 -> fetch .md 文件 -> 简易 Markdown 渲染 -> 在详情面板中展示

**收藏：** 点击 ★ 按钮 -> localStorage 存储 -> 可通过"导出收藏"按钮复制 URL

**双语切换：** 点击 中文/English 按钮 -> setLang() + localStorage -> renderAll()

**键盘导航：** ESC 关闭详情面板

## 下一步读什么

-> [L5-接口契约](L5-接口契约.md)

## 更新指引

**触发条件：** 页面增删、state 结构变更、交互流程变更、样式变量变更、模块结构变更
**更新内容：** 三区布局、模块详解、全局对象、交互模式、CSS 变量
