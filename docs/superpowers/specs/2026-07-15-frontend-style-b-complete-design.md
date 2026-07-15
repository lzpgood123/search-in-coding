# Search in Coding — Style B 完整视觉落地设计规格

> **状态：** 方案已锁定（grilling 2026-07-15）  
> **角色：** 方案设计（本文件只定规格，不写实现代码）  
> **风格：** Warm paper dark + 琥珀强调（与 2026-07-14 锁定一致，不推翻）  
> **打包方案：** 方案 1 — 完整 Style B 呈现包（含报告居中 modal；零后端）  
> **视觉伴侣：** `docs/design-drafts/2026-07-15-frontend-visual-companion.html`  
> **历史参考：** `docs/design-drafts/2026-07-14-frontend-visual-redesign-spec.md`（气质与组件方向；实现基线以 **当前 main** 为准）

---

## 1. 背景与问题

### 1.1 当前产品现实（2026-07-15）

| 维度 | 状态 |
|------|------|
| 数据规模 | projects **5165**；curated **40**；LLM 覆盖已很高 |
| 前端性能 | `search-index.json` + detail 分片（约 52 片）+ `detail-index.json`；无单体 `projects-detail.json` |
| 交互能力 | 多选筛选、chips、清空、收藏、深链、`/60`·`/100`、score/quality 分项均已可用 |
| 字体 / CSP | 已去掉 Google Fonts，系统字体栈 |
| 正式站 | https://coding.lzpgood.online/（Nginx）；push ≠ deploy |
| 视觉 | 线上仍偏旧 Linear 蓝紫气质；工作区可能存在未提交 Style B 草稿，**不得当作唯一真相** |

### 1.2 本轮要解决的用户问题

1. 完成 **Style B** 视觉落地（暖石色深色 + 琥珀强调 + 中等偏紧密度）  
2. 图表过大/难读 → 可读并排图（轴、网格、柱顶数值）  
3. Header 报告入口形态差 → pill + **居中浮窗**阅读三报告  
4. 在 **不弄坏现网数据与接口** 的前提下可验收、可上线  

### 1.3 非目标

- 不改采集、normalize、评分、weekly LLM、cron 业务语义  
- 不新增后端接口 / JSON schema / YAML 字段  
- 不引入 React/Vue/Tailwind/Chart.js 等依赖  
- 不全面改 URL 状态协议  
- 本规格 **不强制** 在实现会话内 deploy（上线步骤另令）  

---

## 2. 已锁定决策（Grilling）

| # | 议题 | 选择 |
|---|------|------|
| 1 | 主目标 | Style B 视觉落地并上线（色板/密度/图表/报告入口） |
| 2 | 风格 | Warm paper dark + 琥珀；不推翻 07-14 |
| 3 | 改动上限 | 允许 `styles/index/charts` + `app/render/i18n`；**data.js/filters.js 默认不动**；禁止 `scripts/*` 与 `data/**` |
| 4 | 报告 | Header pill + **居中 modal** + 浮窗内 tab 切换三报告 |
| 5 | 项目详情 | **保留** `#detailOverlay` 右侧侧栏，仅 B 皮肤 |
| 6 | 图表 | 上移 metrics 下并排；轴/网格/柱顶数值；工具区只留卡 |
| 7 | 密度 | 中等偏紧完整 polish（发现/工具/搜索/表格） |
| 8 | 实现基线 | **main 为真相**；未提交草稿仅参考，按本 spec 重做/合并 |
| 9 | 打包 | 方案 1 完整呈现包；零后端 |

---

## 3. 硬边界

### 3.1 允许修改的文件

| 文件 | 用途 |
|------|------|
| `site/styles.css` | B token、组件皮肤、密度、响应式、modal、charts-row |
| `site/index.html` | Header/metrics/charts DOM、toolbar 外壳、report modal DOM、`theme-color` |
| `site/js/charts.js` | 可读 SVG（兼容 `barChart(data,maxVal)` / `histogram(scores)`） |
| `site/js/app.js` | 报告 modal 打开/关闭、tab、Esc 栈、遮罩 |
| `site/js/render.js` | 图表写入目标节点；外壳 class；**不改**筛选/评分字段语义 |
| `site/js/i18n.js` | 图表标题/副标题、报告 meta 等文案 |
| （运行）`scripts/build_site.py` | **只运行**再生 hash，不改脚本逻辑 |

### 3.2 默认不修改

- `site/js/data.js`  
- `site/js/filters.js`  

例外：仅当实现中证明 **不做则 modal/URL/深链必然损坏** 时，可做最小补丁；须在实现笔记中写明原因。禁止借机改搜索算法或业务筛选语义。

### 3.3 禁止

- `scripts/*.py` 业务改动（含 `build_site.py` 的数据写出逻辑）  
- `data/**`（YAML/原始采集/评分配置）  
- 新 JSON 字段、新 API、改 `site/data/*` 生成 schema  
- 改 `site/reports/*.md` 内容（只改打开/展示方式）  
- 引入前端框架或图表库  
- 未获用户明确确认前的 `git push` / 正式站 `deploy`  

### 3.4 必须保持兼容的契约

**URL query：** `q` / `tools` / `types` / `sort` / `mode` / `curated` / `recent` / `fav` / `project`  
**Hash：** `#favorites=...` 导入收藏  
**数据消费：** 继续只读现有  

- `site/data/metrics.json`  
- `site/data/tools.json`  
- `site/data/projects.json`  
- `site/data/curated-projects.json`  
- `site/data/search-index.json`  
- `site/data/detail-index.json` + `site/data/detail/{n}.json`  
- `site/reports/curated-top.md` / `weekly-report.md` / `tool-comparison.md`  

**DOM id 契约（既有 JS 依赖，不得无故删除）：**  
`#metrics` `#toolChart` `#scoreChart` `#discovery` `#toolOverview` `#q` `#toolTags` `#typeTags` `#modeToggle` `#sort` `#curatedOnly` `#recentOnly` `#favoritesOnly` `#activeFilters` `#resultCount` `#clearFilters` `#rows` `#detailOverlay` `#exportFav` `#favExportUrl` `#langZh` `#langEn` `#lastUpdated` 以及 `data-report` 文件名。

---

## 4. 视觉系统（Style B）

### 4.1 颜色（核心 token）

```css
:root {
  --color-bg: #1c1917;
  --color-bg-elevated: #292524;
  --color-surface: #292524;
  --color-surface-2: #35302c;
  --color-card: #2c2825;
  --color-card-hover: #35302c;
  --color-input: #1a1714;
  --color-text: #faf7f2;
  --color-text-secondary: #e7e0d6;
  --color-text-muted: #b5aa9c;
  --color-accent: #f59e0b;
  --color-accent-light: #fbbf24;
  --color-accent-soft: rgba(245, 158, 11, 0.14);
  --color-accent-border: rgba(245, 158, 11, 0.35);
  --color-link: #fcd34d;
  --color-fav: #fbbf24;
  --color-danger: #f87171;
  --color-border: rgba(255, 248, 240, 0.10);
  --color-border-strong: rgba(255, 248, 240, 0.16);
}
```

**停用主用法：** 蓝紫 `--color-accent-gradient` 作为主强调；近黑 `#0f172a` 作为主背景。  
若需兼容旧变量名，可映射为琥珀 soft，但视觉结果必须是 B。

### 4.2 形状 / 阴影 / 动效

- 圆角：约 16 / 12 / 10  
- 间距：中等偏紧（正文约 14px；section h2 约 17px；站点标题约 24–26px）  
- 卡片阴影偏深、克制  
- 交互：`:active { scale(0.97) }`；hover 边框琥珀 + 微抬；modal scale+fade；focus amber ring  
- `prefers-reduced-motion: reduce` 关闭非必要 transform  
- **禁止：** 整页入场错落动画、滥用 `transition: all`  
- **字体：** 系统字体栈 only（不恢复 Google Fonts）

### 4.3 类型 pill

保留多色语义，**降饱和**，与暖底协调（mcp / skills / rules / framework / cli / tutorial）。

---

## 5. 信息架构（首屏上→下）

```
Header
  左：标题 + 副标题
  右：报告 pill 组 | 导出收藏 | 语言
Metrics（4 卡）
Charts 并排
  左：工具覆盖分布（可读 SVG）
  右：分数分布（可读 SVG）
最新发现（紧凑网格）
工具生态概览（紧凑网格，无底部大图）
生态项目搜索（toolbar + chips + 表格）
Footer
Detail 右侧侧栏（项目详情）
Report 居中 modal（三报告）
```

### 5.1 Header 报告 pill

- 三项：`推荐榜` / `生态周报` / `工具对比`  
- `data-report` 文件名不变：`curated-top.md` / `weekly-report.md` / `tool-comparison.md`  
- 点击：`preventDefault` → `openReportModal(file)`  
- 当前打开报告可高亮 active  

### 5.2 Metrics

- 仍渲染到 `#metrics`，数据仍 `SIC_data.metrics`  
- 数字 accent 色，标签 muted  

### 5.3 图表

- 保留 id `#toolChart` / `#scoreChart`（render.js 写入）  
- 外层 chart-card 提供标题/副标题（HTML 静态或 i18n）  
- `SIC_charts.barChart` / `histogram`：Y 轴刻度 + 网格 + 柱顶数值 + X 短标签；高度约 180–210px  
- 桌面 `1.15fr 0.85fr`；≤1100px 堆叠  
- 真实分数分布极度偏斜时，**数值标签必须可读**  
- API 向后兼容现有 `barChart(data, maxVal)`、`histogram(scores)` 调用  

### 5.4 发现 / 工具 / 搜索密度

- 发现：`minmax(240px, 1fr)` 量级，摘要一行截断  
- 工具：更紧网格；点击仍 `data-action="tool-filter"`  
- 搜索：`.toolbar` 包住 controls；表格更紧 padding、sticky thead、暖色 hover  

### 5.5 报告居中 modal

建议 DOM（仅前端）：

```html
<div id="reportBackdrop" class="modal-backdrop" hidden></div>
<div id="reportModal" class="modal" role="dialog" aria-modal="true" hidden>
  <div class="modal-head">… title + close …</div>
  <div class="modal-tabs" role="tablist">… three data-report buttons …</div>
  <div id="reportModalBody" class="modal-body report-content"></div>
</div>
```

行为：

1. `fetch('reports/' + file)`（现有路径）  
2. `SIC_render.renderReport(md)` 写入 `#reportModalBody`  
3. **不再**把报告塞进 `#detailOverlay`  
4. 关闭：× / backdrop / Esc  
5. 打开时 `body` overflow hidden；关闭时若 detail 未开则恢复  
6. 宽度 `min(720px, 100vw-32px)`，最大高度约 78vh，body 滚动  

### 5.6 项目详情侧栏

- 保留 `#detailOverlay` 与现有 `openDetail` / `loadDetail`（分片）逻辑  
- 仅 B 皮肤；宽度可 `min(560px, 100%)`  
- 不改 score_detail / quality_detail / benchmark 名展示逻辑  

---

## 6. 交互规格

### 6.1 Esc 栈

1. 若报告 modal 打开 → 只关 modal  
2. 否则若 detail 打开 → 关 detail  
3. 两者都关时 Esc 无操作  

### 6.2 与现有功能共存

以下必须回归通过：中英文、筛选/排序/chips/清空、虚拟滚动、收藏/导出、`?project=` 深链、工具卡跳转搜索区、mode radiogroup。

### 6.3 错误与加载

- 报告 fetch 失败：modal body 内错误文案，不白屏  
- 详情 loading 行为保持现有  

---

## 7. 文件改动清单（实现指引）

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `site/styles.css` | 重写 token + 组件 | B 皮肤、charts-row、modal、toolbar、密度 |
| `site/index.html` | 结构调整 | metrics 下 charts；report modal DOM；toolbar；theme-color |
| `site/js/charts.js` | 增强 SVG | 轴/网格/数值；兼容旧签名 |
| `site/js/app.js` | 报告打开路径 | modal 替代 detail 塞报告；Esc 栈 |
| `site/js/render.js` | 挂载/外壳 | 确保 chart 写入正确节点；不改业务字段 |
| `site/js/i18n.js` | 文案 key | 图表标题/副标题、report meta |
| hash 产物 | build 再生 | 不手改 `*.hash.js/css` 当源 |

**实现基线：** 以 clean/main 行为为准；若工作区有未提交草稿，对照本 spec 合并，冲突时 **以本 spec + main 功能** 为准。

---

## 8. 验收标准

### 8.1 必须通过

- [ ] 无新后端接口、无新 JSON schema、无改 `data/**` / 采集评分 LLM 脚本逻辑  
- [ ] `data.js` / `filters.js` 默认与 main 一致（无理由不改）  
- [ ] 两张图：标题/副标题或单位、轴或等价刻度、柱上数值；桌面并排；窄屏可堆叠  
- [ ] Header 报告为 pill；点击打开**居中浮窗**；可 tab 切换三报告；内容来自现有 md  
- [ ] 报告**不**再写入 `#detailOverlay`  
- [ ] 项目详情仍右侧侧栏；`?project=` 深链可用  
- [ ] Esc / 遮罩 / × 关闭浮层，且与 detail 不互踩  
- [ ] 筛选 / 排序 / chips / 清空 / 收藏 / 导出 / 中英文 / 虚拟滚动仍可用  
- [ ] search-index + detail 分片加载路径未被破坏  
- [ ] `python3 scripts/build_site.py` 成功；`index.html` 引用的 hash CSS/JS 存在  
- [ ] 整体视觉为 Warm paper dark + amber；无 Google Fonts  
- [ ] 未擅自 push / deploy（除非用户另令）  

### 8.2 加分

- [ ] reduced-motion 下关闭非必要 transform  
- [ ] modal 焦点管理（Tab 循环）  
- [ ] 图表 aria-label 完整  

---

## 9. 上线路径（实现完成后，需用户确认）

1. 本地 build + 手工/静态验收  
2. commit 仅视觉相关文件（含 hash 新旧替换）  
3. （可选）`git push origin main`  
4. **正式站：** `python3 scripts/deploy_site.py --dest /var/www/coding.lzpgood.online`（先 dry-run）  
5. curl + 浏览器强刷验收  

说明：push ≠ deploy；GitHub Pages Actions ≠ 腾讯云 Nginx 正式站。

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 改 render 误伤筛选 | 只改 class/外壳/图表挂载，不改 `SIC_filters.apply` |
| 报告 modal 与 detail Esc 冲突 | 统一 Esc 栈：先 report 后 detail |
| 图表在 5k 项目上聚合卡顿 | 继续现有一次 map；勿在 hover 重算 |
| 未提交草稿与 main 混杂 | 以 main 功能 + 本 spec 合并；验收前 diff 禁改文件 |
| 误动 data 管道 | 硬禁止 scripts/data；PR/提交前 `git diff` 自检 |
| 偏斜直方图难读 | 强制柱顶数值与 Y 刻度 |

---

## 11. 建议实现批次

1. CSS token + B 皮肤（Header/metrics/cards/table/pills/detail）  
2. index 结构调整 + charts 可读化 + 并排上移  
3. 报告 modal + app Esc 栈 + i18n  
4. 密度 polish + reduced-motion  
5. `build_site.py` + 功能回归 +（可选）wiki L4A/L3/L6 更新  

---

## 12. 决策摘要（一句话）

> 在 **零后端、默认不动 data/filters** 前提下，以 **当前 main** 为基线，把站点完整升级为 **Style B Warm paper dark**：可读并排图表、中等偏紧密度、Header 报告 pill + **居中 modal**，项目详情保留右侧侧栏，build 再生 hash 后按用户确认再 push/deploy。

---

## 13. 规格自检

| 检查项 | 结果 |
|--------|------|
| 无 TBD/TODO 占位实现步骤 | 通过（上线需用户令，已写明） |
| 与 grilling 决策一致 | 通过 |
| 与 main 数据契约不冲突 | 通过（只读现有静态资源） |
| 文件边界清晰 | 通过 |
| 验收可测 | 通过 |
| 未要求实现 Agent 改后端 | 通过 |
