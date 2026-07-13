# 前端重写 v2 设计

> 日期：2026-07-13
> 状态：用户已确认
> 作者：方案设计 Agent
> 前置：第 2 批网站重写的代码质量不达标，10 个 bug 导致功能不可用，全部重写

## 背景

第 2 批网站重写产出了 6 个 JS 模块 + 新 index.html + CSS，但实现质量差：首页发现区永远空、报告链接点了没反应、虚拟滚动只能加载一页、工具卡片点击无视觉反馈、charts.js 从未被调用等 10 个 bug。用户要求全部重写。

## 问题清单

| # | 严重度 | 问题 | 根因 |
|---|--------|------|------|
| 1 | 致命 | 发现区永远空 | 所有项目 first_seen=2026-07-06，7天cutoff已过期 |
| 2 | 致命 | 报告链接失效 | 前端引用 weekly-report.md，generate_reports.py 生成的文件名不匹配 |
| 3 | 严重 | 工具卡片点击无反馈 | onclick 清空 selectedTools 但不更新 tag button active 状态 |
| 4 | 严重 | 虚拟滚动只加载一页 | IntersectionObserver 不重新 observe 新的最后一行 |
| 5 | 严重 | "最近发现"未实现 | recentOnly 变量存在但 apply() 里没用 |
| 6 | 严重 | charts.js 未调用 | SIC_charts 定义了但 render.js 从未调用 |
| 7 | 严重 | LLM Summary 空 | llm_summary 是 {zh,en} 对象，textOf() 取不到 |
| 8 | 低 | 导出收藏用 alert | 体验差 |
| 9 | 低 | markdown 渲染粗糙 | 表格破坏 HTML、不支持列表 |
| 10 | 低 | 移动端表格溢出 | 无 overflow-x |

## 设计方案

### 架构

保持零依赖原生 JS + 6 模块结构。关键改进：
- 事件绑定用事件委托（event delegation），不用 inline onclick
- filters.js 纯逻辑无 DOM 依赖
- 每个交互有视觉反馈
- charts.js 被实际调用

### 模块职责

| 模块 | 职责 |
|------|------|
| i18n.js | 双语配置、t()、textOf()、语言切换 |
| data.js | 渐进式 fetch、详情懒加载、localStorage 收藏 |
| filters.js | 多选标签筛选、OR/AND、6 种排序、URL 状态、recentOnly |
| render.js | 三区渲染、虚拟滚动（修复 observer）、详情面板、报告渲染 |
| charts.js | SVG 柱状图、直方图（被 render.js 调用） |
| app.js | 入口、事件委托绑定、debounce、骨架屏 |

### Bug 修复方案

1. **发现区**：改为"最新发现"，按 first_seen 降序 + 分数降序取 Top 12，不按 7 天 cutoff
2. **报告**：重写 generate_reports.py，生成 3 份新报告，文件名与前端匹配
3. **工具卡片**：点击时同步更新 tag button active 状态
4. **虚拟滚动**：renderMore 每次加载后对新最后一行重新 observe；clear 时 disconnect
5. **recentOnly**：filters.js apply() 中实现，取最近 50 条的 cutoff 日期
6. **charts.js**：renderToolOverview() 调用柱状图；搜索区上方加分数分布直方图
7. **LLM Summary**：detail 面板中 llm_summary 按 {zh,en} 对象直接取值
8. **导出收藏**：改为导航栏可复制的输入框
9. **markdown 渲染**：重写 renderReport，支持标题/段落/列表/表格/代码/链接
10. **移动端**：表格容器 overflow-x: auto，760px 以下最小宽度 600px

### generate_reports.py 重写

3 份报告，用新字段：

| 文件 | 内容 |
|------|------|
| weekly-report.md | 数据概况、Top 10 项目、分数分布、追踪状态 |
| tool-comparison.md | 10 工具生态规模表、资源类型分布、平均分 |
| curated-top.md | Top 50 项目表 + 按分类 Top 3 |

旧 12 份报告全部删除。

### 事件委托

所有动态生成的元素（表格行、卡片、tag button）不用 inline onclick，改为在容器上绑定事件委托：

```javascript
// app.js 中
document.getElementById('rows').addEventListener('click', handleRowClick);
document.getElementById('toolTags').addEventListener('click', handleToolTagClick);
document.getElementById('typeTags').addEventListener('click', handleTypeTagClick);
document.getElementById('toolOverview').addEventListener('click', handleToolCardClick);
document.getElementById('discovery').addEventListener('click', handleDiscoveryCardClick);
```

handleRowClick 通过 `e.target.closest('button[data-action]')` 判断点击的是详情按钮还是收藏按钮。

### 数据流

```
main()
  -> showSkeleton()
  -> data.loadAll() (progressive: metrics -> tools -> projects -> curated)
  -> filters.readState() (从 URL 恢复筛选)
  -> renderAll()
       -> renderMetrics()
       -> renderDiscovery() (最新发现 Top 12)
       -> renderToolOverview() (工具卡片 + 柱状图)
       -> renderScoreChart() (分数分布直方图)
       -> renderSearchZone() (筛选表格 + 虚拟滚动)
  -> bindEvents() (事件委托)
  -> syncUI() (同步 URL 状态到控件)
```

## 不做什么

- 不引入框架或构建工具
- 不改变 6 模块文件结构
- 不改 build_site.py 的精简/详情 JSON 逻辑（第 2 批的这部分是对的）
- 不改 CSS 自定义属性体系（第 2 批的 styles.css 基本可用，只补 bug 修复）
- 不改数据结构（第 1 批的 projects.yaml 字段不变）
