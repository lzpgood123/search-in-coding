# Style B 完整视觉落地实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在当前 main 前端能力上，完整落地 Style B（Warm paper dark + 琥珀），含可读并排图表、Header 报告 pill、居中报告 modal、中等偏紧密度；零后端变更。

**架构：** 纯静态 SPA。CSS token + DOM 结构调整 + charts SVG 增强 + app.js 报告打开路径改为 modal + Esc 栈；详情侧栏保留。数据仍只读现有 search-index / detail 分片 / reports md。build_site.py 只运行再生 hash。

**技术栈：** 原生 HTML/CSS/JS；零框架；现有事件委托与全局 `SIC_*` 对象。

**规格真相源：** `docs/superpowers/specs/2026-07-15-frontend-style-b-complete-design.md`

**实现基线：**
1. `git status` 先看清工作区；未提交 Style B 草稿**仅作参考**，以 main 功能 + 本 plan 为准合并。
2. 改前确认 `site/js/data.js` 含 search-index + detail 分片；**不要**回退到 `projects-detail.json` 单体。
3. 禁止改：`scripts/*` 业务逻辑、`data/**`、默认不改 `data.js`/`filters.js`。
4. 未获用户明确确认前：**不 push、不 deploy**。

---

## 文件清单（将修改）

| 文件 | 职责 |
|------|------|
| `site/styles.css` | B token、组件皮肤、charts-row、modal、toolbar、密度、reduced-motion |
| `site/index.html` | Header/metrics/charts DOM、toolbar、report modal DOM、theme-color |
| `site/js/charts.js` | 可读 bar/histogram（兼容旧签名） |
| `site/js/i18n.js` | 图表标题/副标题、reportMeta |
| `site/js/render.js` | 图表写入 `#toolChart`/`#scoreChart`；工具区不再依赖底部大图 DOM |
| `site/js/app.js` | `openReportModal` / `closeReportModal`；Esc 栈；不再把报告塞进 detailOverlay |
| （运行）`scripts/build_site.py` | 只运行，不改代码 |
| `wiki/L4A-前端详解.md` 等 | 实现完成后按更新指引同步 |

**明确不改（除非实现证明 modal 必然损坏且写笔记）：**  
`site/js/data.js`、`site/js/filters.js`、`scripts/**`、`data/**`

---

## 任务 0：基线确认与草稿处理

**文件：** 无代码改动（只读 + 可选 stash）

- [ ] **步骤 1：记录当前 git 状态**

```bash
cd "<repo-root>"
git status --short
git log -3 --oneline
git rev-parse --abbrev-ref HEAD
```

预期：在 `main` 或用户指定分支；可能看到未提交的 `styles.css` / `index.html` / `charts.js` 草稿。

- [ ] **步骤 2：确认 main 功能契约仍在源码中**

```bash
rg -n "search-index|detail-index|detail/" site/js/data.js | head
rg -n "favoritesOnly|clearAll" site/js/filters.js | head
rg -n "quality_detail|maxScore|openDetail" site/js/render.js | head
rg -n "data-report|detailOverlay|clearFilters" site/js/app.js | head
test -f site/data/search-index.json && test -d site/data/detail && ls site/data/detail | wc -l
```

预期：search-index + detail 分片存在；data/filters/render/app 含上述能力。

- [ ] **步骤 3：处理未提交草稿（按规格：main 为真相，草稿参考）**

若工作区有半成品且与 plan 冲突：

```bash
# 可选：备份草稿后从 HEAD 恢复三文件再按 plan 重做
mkdir -p /tmp/sic-style-b-wip-ref
cp -a site/styles.css site/index.html site/js/charts.js /tmp/sic-style-b-wip-ref/ 2>/dev/null || true
# 若需干净重做：
# git checkout HEAD -- site/styles.css site/index.html site/js/charts.js
```

不要 `git checkout` 掉 `data.js`/`filters.js`/`render.js`/`app.js` 的线上能力。

- [ ] **步骤 4：Commit 不在此任务**（无代码则可跳过）

---

## 任务 1：i18n 文案 key（图表 / 报告）

**文件：**
- 修改：`site/js/i18n.js`

- [ ] **步骤 1：在 zh / en 的 `UI` 对象中增加 key**

在 `navTop` 附近增加（中英都要）：

```js
// zh
reportMeta: '报告',
toolChartTitle: '工具覆盖分布',
toolChartSub: '各目标工具关联项目数 · 单位：项目',
scoreChartTitle: '分数分布',
scoreChartSub: '项目 total_score 分桶 · 单位：项目数',

// en
reportMeta: 'Report',
toolChartTitle: 'Tool Coverage',
toolChartSub: 'Projects linked to each target tool · unit: projects',
scoreChartTitle: 'Score Distribution',
scoreChartSub: 'total_score buckets · unit: project count',
```

- [ ] **步骤 2：语法检查**

```bash
node --check site/js/i18n.js
```

预期：无输出，exit 0。

- [ ] **步骤 3：确认未改 data/filters**

```bash
git diff --name-only -- site/js/data.js site/js/filters.js
```

预期：空。

---

## 任务 2：charts.js 可读 SVG（兼容旧 API）

**文件：**
- 修改：`site/js/charts.js`

- [ ] **步骤 1：用 node 写失败用例（当前旧图无 Y 轴文字）**

```bash
node - <<'JS'
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync('site/js/charts.js','utf8');
const ctx = {};
vm.runInNewContext(code + '\nthis.SIC_charts = SIC_charts;', ctx);
const c = ctx.SIC_charts;
const svg = c.barChart([{label:'A',value:10},{label:'B',value:40}], 40);
const ok = svg.includes('text-anchor="end"') && (svg.includes('>40<') || svg.includes('>10<'));
console.log(ok ? 'ALREADY_READABLE' : 'NEED_UPGRADE');
if (!ok) process.exit(2);
JS
```

预期（升级前）：`NEED_UPGRADE` exit 2。

- [ ] **步骤 2：重写 `SIC_charts`，保持签名**

要求：
- `barChart(data, maxVal, options?)` — 第三参可选
- `histogram(scores)` — 仍 5 桶 0-20…81-100，内部调 barChart
- 输出含：Y 刻度（`text-anchor="end"`）、网格线、柱顶数值、X 短标签
- 高度约 180–210（viewBox + max-height）
- 使用 `var(--color-accent)` 填色

参考实现结构（可整文件替换，勿改全局名 `SIC_charts`）：

```js
const SIC_charts = {
  _niceMax(maxVal) { /* nice number scale */ },
  barChart(data, maxVal, options) { /* grid + axis + bars + value labels */ },
  histogram(scores) {
    const buckets = [0,0,0,0,0];
    // bucket scores...
    return this.barChart([
      {label:'0-20', value: buckets[0]},
      {label:'21-40', value: buckets[1]},
      {label:'41-60', value: buckets[2]},
      {label:'61-80', value: buckets[3]},
      {label:'81-100', value: buckets[4]},
    ], Math.max(...buckets, 1), { ariaLabel: 'score distribution' });
  },
};
```

- [ ] **步骤 3：再跑步骤 1 脚本**

预期：`ALREADY_READABLE` exit 0。

- [ ] **步骤 4：语法检查**

```bash
node --check site/js/charts.js
```

---

## 任务 3：index.html 结构（charts 上移 + toolbar + report modal）

**文件：**
- 修改：`site/index.html`

- [ ] **步骤 1：更新 head**

- `theme-color` → `#1c1917`
- stylesheet 在源文件阶段写 `styles.css`（build 会 hash）
- **不要**加 Google Fonts

- [ ] **步骤 2：Header 调整**

保留既有 id；报告链接保留 `data-report` 与三个文件名。建议顺序：推荐榜 → 生态周报 → 工具对比。语言按钮 id 仍为 `langZh` / `langEn`。

- [ ] **步骤 3：metrics 下增加 charts-row**

在 `</header>` 前、`#metrics` 后插入（**必须保留** `#toolChart` 与 `#scoreChart`）：

```html
<section class="charts-row" id="chartsSection" aria-label="Overview charts">
  <article class="chart-card">
    <div class="chart-card-head">
      <h3 class="chart-card-title" data-i18n="toolChartTitle">工具覆盖分布</h3>
      <p class="chart-card-sub" data-i18n="toolChartSub">各目标工具关联项目数 · 单位：项目</p>
    </div>
    <div id="toolChart" class="chart-container chart-body" role="img" aria-label="Tool coverage chart"></div>
  </article>
  <article class="chart-card">
    <div class="chart-card-head">
      <h3 class="chart-card-title" data-i18n="scoreChartTitle">分数分布</h3>
      <p class="chart-card-sub" data-i18n="scoreChartSub">项目 total_score 分桶 · 单位：项目数</p>
    </div>
    <div id="scoreChart" class="chart-container chart-body" role="img" aria-label="Score distribution chart"></div>
  </article>
</section>
```

- [ ] **步骤 4：工具概览区去掉底部图表容器**

`#toolOverviewSection` 内只留标题、hint、`#toolOverview`。  
**删除**该 section 内旧的 `#toolChart` / `#scoreChart` 节点（已上移，避免重复 id）。

- [ ] **步骤 5：搜索区 controls 外包 `.toolbar`**

```html
<div class="toolbar">
  <div class="controls">
    <!-- 保持所有既有 input/select/checkbox/tag 容器 id 不变 -->
  </div>
</div>
```

- [ ] **步骤 6：在 `detailOverlay` 后增加 report modal DOM**

```html
<div id="reportBackdrop" class="modal-backdrop" hidden></div>
<div id="reportModal" class="modal" role="dialog" aria-modal="true" aria-labelledby="reportModalTitle" hidden>
  <div class="modal-head">
    <div>
      <h2 id="reportModalTitle">推荐榜</h2>
      <p class="meta" data-i18n="reportMeta">报告</p>
    </div>
    <button type="button" class="modal-close" data-action="close-report" aria-label="Close report">×</button>
  </div>
  <div class="modal-tabs" role="tablist" aria-label="Report tabs">
    <button type="button" role="tab" data-report="curated-top.md" data-i18n="navTop">推荐榜</button>
    <button type="button" role="tab" data-report="weekly-report.md" data-i18n="navWeekly">生态周报</button>
    <button type="button" role="tab" data-report="tool-comparison.md" data-i18n="navCompare">工具对比</button>
  </div>
  <div id="reportModalBody" class="modal-body report-content"></div>
</div>
```

- [ ] **步骤 7：脚本标签在源阶段用未 hash 名**

```html
<script src="js/i18n.js"></script>
<script src="js/data.js"></script>
<script src="js/filters.js"></script>
<script src="js/charts.js"></script>
<script src="js/render.js"></script>
<script src="js/app.js"></script>
```

- [ ] **步骤 8：DOM id 自检**

```bash
python3 - <<'PY'
from pathlib import Path
html=Path('site/index.html').read_text()
need=['metrics','toolChart','scoreChart','discovery','toolOverview','q','toolTags','typeTags','modeToggle','sort','curatedOnly','recentOnly','favoritesOnly','activeFilters','resultCount','clearFilters','rows','detailOverlay','reportModal','reportBackdrop','reportModalBody','exportFav','langZh','langEn','lastUpdated']
for i in need:
    assert f'id="{i}"' in html, i
# no duplicate chart ids
assert html.count('id="toolChart"')==1
assert html.count('id="scoreChart"')==1
tool=html.split('id="toolOverviewSection"')[1].split('id="searchZone"')[0]
assert 'id="toolChart"' not in tool
print('index DOM OK')
PY
```

---

## 任务 4：styles.css — Style B 皮肤 + modal + charts-row + 密度

**文件：**
- 修改：`site/styles.css`（可整文件按 B token 重写，但须覆盖现有组件选择器）

- [ ] **步骤 1：替换 `:root` 为 Warm paper dark tokens**

必须包含：`--color-bg: #1c1917`、`--color-accent: #f59e0b`、elevated/card/muted/link/border/soft/focus 等（见 spec §4.1）。

- [ ] **步骤 2：body 使用系统字体，字号约 14px**

禁止 `fonts.googleapis.com`。

- [ ] **步骤 3：Header / nav a[data-report] pill / metrics / cards / pills / table / detail**

- 报告链接：圆角 pill、琥珀 active/hover  
- metrics 数字：accent 实色（不要蓝紫渐变 clip text）  
- score-badge：琥珀 soft fill  
- type pills：降饱和  
- detail-overlay：暖 elevated 底，宽 `min(560px,100%)`  

- [ ] **步骤 4：新增 `.charts-row` / `.chart-card` / `.toolbar` / `.modal*`**

```css
.charts-row { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 12px; }
@media (max-width: 1100px) { .charts-row { grid-template-columns: 1fr; } }
.modal-backdrop { position: fixed; inset: 0; z-index: 200; /* dim */ }
.modal { position: fixed; z-index: 210; width: min(720px, calc(100vw - 32px)); max-height: 78vh; /* center */ }
.modal-backdrop[hidden], .modal[hidden] { display: none !important; }
```

- [ ] **步骤 5：密度**

- discovery `minmax(240px, 1fr)`  
- tool `minmax(180px, 1fr)` 量级  
- section h2 ~17px；h1 ~25px  
- active scale 0.97；reduced-motion 关闭非必要 transform  

- [ ] **步骤 6：静态断言**

```bash
python3 - <<'PY'
from pathlib import Path
c=Path('site/styles.css').read_text()
assert '#1c1917' in c and '#f59e0b' in c
assert '#0f172a' not in c
assert 'fonts.googleapis' not in c
assert '.charts-row' in c and '.modal' in c and '.toolbar' in c
print('css B OK')
PY
```

---

## 任务 5：render.js — 图表挂载兼容（不改业务字段）

**文件：**
- 修改：`site/js/render.js`（仅图表相关函数）

- [ ] **步骤 1：确认 `renderToolOverview` / `renderScoreChart` 仍写入 `#toolChart` / `#scoreChart`**

当前逻辑已是 `this.$('toolChart')` / `this.$('scoreChart')`。图表节点上移后 **通常无需改逻辑**。

- [ ] **步骤 2：若 `barChart` 调用可传 ariaLabel，可选增强**

```js
// 仅当 charts 支持第 3 参时
chartEl.innerHTML = SIC_charts.barChart(chartData, maxVal);
// 保持两参调用也合法；可选：
// SIC_charts.barChart(chartData, maxVal, { ariaLabel: SIC_i18n.t('toolChartTitle') });
```

- [ ] **步骤 3：禁止改动**

不要改：`SIC_filters.apply` 调用、score_detail/quality_detail 拼装、favorites 逻辑、虚拟滚动。

- [ ] **步骤 4：语法检查**

```bash
node --check site/js/render.js
git diff --stat -- site/js/render.js
```

预期：diff 极小或仅图表调用行。

---

## 任务 6：app.js — 报告居中 modal + Esc 栈

**文件：**
- 修改：`site/js/app.js`

- [ ] **步骤 1：增加报告状态与 API**

```js
var REPORT_TITLES = {
  'curated-top.md': 'navTop',
  'weekly-report.md': 'navWeekly',
  'tool-comparison.md': 'navCompare',
};
var activeReportFile = null;

function isReportOpen() {
  var modal = $('reportModal');
  return !!(modal && !modal.hidden);
}

function setReportActive(reportFile) { /* toggle .active on pills/tabs; set #reportModalTitle */ }

async function openReportModal(reportFile) {
  // show modal+backdrop; body overflow hidden
  // fetch reports/<file>; SIC_render.renderReport(md) -> #reportModalBody
  // on 404: error text in body; NEVER write report into detailOverlay
}

function closeReportModal() {
  // hide modal+backdrop; clear active; restore overflow if detail closed
}
```

- [ ] **步骤 2：替换现有 `document.querySelectorAll('[data-report]')` 处理器**

删除把报告写入 `$('detailOverlay')` 的分支，改为：

```js
document.querySelectorAll('[data-report]').forEach(function(el) {
  el.addEventListener('click', function(e) {
    e.preventDefault();
    openReportModal(el.dataset.report);
  });
});
```

注意：Header 与 modal tabs 都有 `data-report`，会绑两次监听 — 可接受；或在 `bindEvents` 用事件委托统一处理。

- [ ] **步骤 3：全局 click 增加 `close-report`**

在 `handleGlobalClick` 的 switch 中：

```js
case 'close-report':
  e.preventDefault();
  closeReportModal();
  break;
```

- [ ] **步骤 4：backdrop 点击关闭**

```js
var reportBackdrop = $('reportBackdrop');
if (reportBackdrop) {
  reportBackdrop.addEventListener('click', function() { closeReportModal(); });
}
```

- [ ] **步骤 5：Esc 栈**

替换仅 `closeDetail` 的 Esc 处理：

```js
document.addEventListener('keydown', function(e) {
  if (e.key !== 'Escape') return;
  if (isReportOpen()) { closeReportModal(); return; }
  SIC_render.closeDetail();
});
```

- [ ] **步骤 6：语言切换后若 modal 开着，刷新标题 active 文案**

在 `langZh` / `langEn` handler 末尾：若 `isReportOpen() && activeReportFile` 则 `setReportActive(activeReportFile)`。

- [ ] **步骤 7：静态断言 app 不再往 detail 塞 reports/**

```bash
rg -n "reports/" site/js/app.js
rg -n "detailOverlay.*report|report.*detailOverlay" site/js/app.js || true
rg -n "openReportModal|closeReportModal|isReportOpen" site/js/app.js
node --check site/js/app.js
```

预期：存在 open/close/isReport；fetch reports 写入 reportModalBody 路径清晰。

---

## 任务 7：build + 回归验证

**文件：** hash 产物（由 build 生成）

- [ ] **步骤 1：build**

```bash
cd "<repo-root>"
python3 scripts/build_site.py
```

预期：JSON 含 `projects: 5165`、`hashed_assets: true`、`detail_chunks` 存在（或等价分片字段）；exit 0。

- [ ] **步骤 2：禁改文件未变**

```bash
git diff --name-only HEAD -- site/js/data.js site/js/filters.js scripts/ data/
```

预期：空（或仅你在笔记中声明的最小例外）。

- [ ] **步骤 3：hash 引用存在**

```bash
python3 - <<'PY'
from pathlib import Path
import re
html=Path('site/index.html').read_text()
refs=re.findall(r'(?:href|src)="((?:styles\.[a-f0-9]{6}\.css|js/[a-z0-9_-]+\.[a-f0-9]{6}\.js))"', html)
assert refs, 'no hashed refs'
for r in refs:
    assert (Path('site')/r).exists(), r
print('hash OK', refs)
PY
```

- [ ] **步骤 4：charts 运行时再测**

```bash
node - <<'JS'
const fs=require('fs'); const vm=require('vm');
const code=fs.readFileSync('site/js/charts.js','utf8');
const ctx={}; vm.runInNewContext(code+'\nthis.SIC_charts=SIC_charts;', ctx);
const c=ctx.SIC_charts;
const svg=c.barChart([{label:'A',value:10},{label:'B',value:40}],40);
const h=c.histogram([10,25,25,70,90]);
if(!svg.includes('text-anchor="end"')) throw new Error('no axis');
if(!h.includes('21-40')) throw new Error('no hist label');
console.log('charts OK');
JS
```

- [ ] **步骤 5：本地预览清单（手工）**

```bash
cd site && python3 -m http.server 8765
```

勾选：
- [ ] 暖石色 + 琥珀，非蓝紫近黑  
- [ ] 图表在 metrics 下并排，有轴/数值  
- [ ] 报告 pill → 居中 modal → tab 切换三报告  
- [ ] 详情侧栏仍可用；`?project=` 深链  
- [ ] Esc：先关 report 再关 detail  
- [ ] 筛选/chips/清空/收藏/中英文  
- [ ] 搜索与详情加载（search-index + 分片）正常  

- [ ] **步骤 6：可选 pytest**

```bash
if [ -d .venv ]; then . .venv/bin/activate; fi
python3 -m pytest tests/test_build_site_v2.py -q --tb=line
```

有则应 PASS；与视觉无关的失败需区分是否本任务引起。

---

## 任务 8：Wiki 更新（实现 Agent 完成时）

**文件：**
- 修改：`wiki/L4A-前端详解.md`（CSS 变量、报告 modal、charts 布局、Esc）
- 修改：`wiki/L3-代码地图.md`（前端文件职责若有变）
- 修改：`wiki/L6-经验录.md`（坑：modal vs detail Esc；只改源再 build）
- 可选：`wiki/L1-全景.md` 状态一句 Style B 落地

- [ ] **步骤 1：按各文档更新指引补丁**  
- [ ] **步骤 2：wiki-checkpoint 自检**  
- [ ] **步骤 3：不 push / 不 deploy**（除非用户本会话明确下令）

---

## 任务 9：提交（仅用户要求时）

- [ ] **步骤 1：diff 审查**

```bash
git status --short
git diff --stat
```

只应出现 site 视觉相关 + 可选 wiki + 本 plan/spec。

- [ ] **步骤 2：commit 示例**

```bash
git add site/index.html site/styles.css site/js/charts.js site/js/app.js site/js/render.js site/js/i18n.js
git add -u site/
# 若更新 wiki：
# git add wiki/L4A-前端详解.md wiki/L3-代码地图.md wiki/L6-经验录.md wiki/L1-全景.md
git commit -m "feat(site): complete Style B Warm paper dark visual landing"
```

- [ ] **步骤 3：上线另令**

```bash
# push（仅确认后）
# git push origin main

# deploy（仅确认后）
# python3 scripts/deploy_site.py --dest /var/www/coding.lzpgood.online --dry-run
# python3 scripts/deploy_site.py --dest /var/www/coding.lzpgood.online
```

---

## 规格覆盖度自检

| 规格章节 | 对应任务 |
|----------|----------|
| Style B token / 密度 | 任务 4 |
| 图表上移 + 可读 | 任务 2、3、5 |
| 报告 pill + 居中 modal | 任务 3、6 |
| 详情侧栏 B 皮 | 任务 4 |
| i18n 文案 | 任务 1 |
| 零后端 / data·filters 默不动 | 任务 0、7 |
| build + 验收 | 任务 7 |
| wiki | 任务 8 |
| push/deploy 另令 | 任务 9 |

无 TBD 占位实现步骤。

---

## 执行交接

计划已保存到：

`docs/superpowers/plans/2026-07-15-frontend-style-b-complete.md`

**两种执行方式：**

1. **子代理驱动（推荐）** — 每个任务新子代理 + 任务间审查（`subagent-driven-development`）  
2. **内联执行** — 本会话 `executing-plans`，分批检查点  

**选哪种方式？** 确认后实现 Agent 再动代码。
