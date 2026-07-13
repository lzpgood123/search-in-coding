# Search in Coding 站点用户体验走查报告

> 项目文档位置：`docs/ux-dogfood-report-2026-07-13.md`  
> 工作副本：`dogfood-output/report.md`  
> 站点：https://coding.lzpgood.online/  
> 对应阶段：第 2 批网站重写完成后

| 字段 | 内容 |
|------|------|
| **Target** | https://coding.lzpgood.online/ |
| **Date** | 2026-07-13 |
| **Scope** | 完整站点用户体验（发现区 / 工具概览 / 搜索筛选 / 详情面板 / 报告 / 收藏 / 双语 / SEO·基础设施） |
| **Tester** | Hermes Agent（HTTP + 线上数据 + 前端源码走查；本环境无浏览器自动化工具，交互逻辑以源码与线上资源实测交叉验证） |
| **Issue count** | Critical 4 · High 10 · Medium 16 · Low 12 · **Total 42** |

---

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | 4 |
| 🟠 High | 10 |
| 🟡 Medium | 16 |
| 🔵 Low | 12 |
| **Total** | **42** |

**Overall Assessment:** 第二批三区布局与筛选骨架已经可用，页面能加载、能搜、能开详情；但作为「生态追踪器」的核心信任点（分数可信度、最新发现真实性、中文内容、数据新鲜度）目前明显失真，多个导航级功能（收藏浏览、清空筛选、结果计数、项目深链）缺失，首访信任成本偏高。

---

## Issues

### Issue #1: 100 分制评分几乎全空，排行不可信

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Category** | Content / UX |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
线上 274 条项目：`total_score` 最高仅 **37**，平均约 **19**；`quality_score` **全部为 0**。详情面板仍展示「/ 100」「质量分 x/40」进度条。用户会把「37 分」理解成「很差」，而不是「第 3 批 LLM 质量分未上线」。

**Steps to Reproduce:**
1. 打开首页，看发现区分数徽章
2. 点任意项目「详情」
3. 观察总分与质量分进度条

**Expected Behavior:**  
分数有解释（例如「当前仅可量化 60 分中的 xx」），或未启用维度隐藏/标注「待分析」。

**Actual Behavior:**  
统一按满分 100 展示，质量条永远空，排行像半成品。

**Evidence:**
- metrics / projects.json 实测：`score min/max/avg = 6/37/19.12`，`quality zero count = 274`
- 直方图桶：可见项目 `0-20: 199`，`21-40: 58`，更高桶全 0

---

### Issue #2: 「最新发现」不是最新发现

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Category** | Content / UX |
| **URL** | https://coding.lzpgood.online/#discoverySection |

**Description:**  
文案写「按发现时间排序的高质量项目 Top 12」。但全部 274 条 `first_seen` 都是 `2026-07-06`。发现区实际退化成「分数 Top 12」，和「最近发现」叙事冲突。

**Steps to Reproduce:**
1. 打开首页看「最新发现」
2. 对比项目 `first_seen` / `last_seen`

**Expected Behavior:**  
真正按新入库时间展示，或无增量时明确写「暂无新发现，展示高分项目」。

**Actual Behavior:**  
看起来像「本周新货」，实际是同一天导入的高分榜。

**Evidence:**
- `first_seen Counter({'2026-07-06': 274})`
- discovery Top12 全是同日 + 高分排序

---

### Issue #3: 中英双语几乎是假双语

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Category** | Content / UX |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
UI 文案可切换，但项目 `i18n.zh.summary` 与 `i18n.en.summary` **274/274 完全相同**。中文用户切到「中文」后，内容主体仍是英文 GitHub 描述。

**Steps to Reproduce:**
1. 点「中文」
2. 阅读发现区卡片摘要 / 表格摘要 / 详情 summary

**Expected Behavior:**  
中文 UI 下至少核心摘要有中文，或明确标注「内容原文（英）」。

**Actual Behavior:**  
壳是中文，肉是英文；双语按钮价值被稀释。

**Evidence:**
- 线上统计：`summary zh==en 274 / 274`

---

### Issue #4: 资源类型误标严重，搜索结果可信度受损

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Category** | Content / Functional |
| **URL** | https://coding.lzpgood.online/?types=tutorial |

**Description:**  
头部高星项目大量被标成 `tutorial`，但描述明显是 skill：
- `JuliusBrussee/caveman`（85k⭐）→ tutorial
- `blader/humanizer`（27k⭐）→ tutorial
- `virgiliojr94/book-to-skill` → tutorial  

用户按类型筛选会得到错误集合；「Skills」筛选会漏掉真正 skill 项目。

**Steps to Reproduce:**
1. 打开首页 Top 项目
2. 看类型 pill / 详情 resource_type
3. 用「Skills / Tutorial」筛选对比

**Expected Behavior:**  
类型与内容一致，至少头部 curated 项目分类准确。

**Actual Behavior:**  
头部流量项目分类失真，筛选结果误导。

---

### Issue #5: 收藏只能导出，不能在站内查看/筛选

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional / UX |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
可点 ★ 收藏并「导出收藏」生成 hash URL，但：
- 无「我的收藏」列表/筛选
- `SIC_data.getFavorites()` 已实现却未被 UI 使用
- 无法只看收藏、无法取消后快速确认状态（表格需滚动找）

**Expected Behavior:**  
有收藏视图或 `只看收藏` 过滤，导出是分享能力不是唯一出口。

**Actual Behavior:**  
收藏像半成品开关。

---

### Issue #6: 导出收藏后，任意筛选会丢掉 `#favorites=` hash

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
`SIC_filters.writeState()` 使用  
`history.replaceState(null, '', pathname + '?' + qs)`，**不保留 hash**。  
用户打开导入链接 `#favorites=...` 后，只要搜索/点标签，收藏 hash 立即消失（localStorage 虽已写入，但分享链被破坏）。

**Steps to Reproduce:**
1. 打开带 `#favorites=id1,id2` 的 URL
2. 输入搜索词或点工具标签
3. 观察地址栏 hash

**Expected Behavior:**  
保留 hash，或导入后清理 hash 并给成功提示。

**Actual Behavior:**  
hash 被静默抹掉。

---

### Issue #7: 无结果计数 / 无清空筛选 / 无当前筛选摘要

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | UX |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
筛选后看不到「显示 12 / 257」。多选工具+类型+关键词后，不知道还开着哪些条件；没有「清空全部」一键复位。空结果只有文案，没有一键重置。

**Expected Behavior:**  
结果计数 + 活跃筛选 chips + 清空按钮。

**Actual Behavior:**  
筛选状态靠用户记忆。

---

### Issue #8: OR/AND 切换按钮可误触翻转

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
`modeToggle` 点击处理固定调用 `toggleMode()`，再对两个按钮统一 `classList.toggle('active')`。  
因此：**再点一次已经激活的「任一匹配」也会切到 AND**。  
`role="radiogroup"` 语义也不完整（按钮无 `role=radio` / `aria-checked`）。

**Steps to Reproduce:**
1. 默认「任一匹配」高亮
2. 再点一次「任一匹配」
3. 观察是否变成「全部匹配」

**Expected Behavior:**  
radiogroup：点已选项不变；点另一项才切换。

**Actual Behavior:**  
点同一按钮也会翻转。

---

### Issue #9: 详情面板缺少加载态，且为看一条详情拉 400KB 全量 JSON

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Performance / UX |
| **URL** | https://coding.lzpgood.online/data/projects-detail.json |

**Description:**  
`loadDetail()` 首次会 fetch 整个 `projects-detail.json`（约 **408KB**，gzip 后仍不小）。`openDetail` 在 await 期间不展示 skeleton/spinner，弱网会「点了没反应」。之后虽缓存，但首点体验差。

**Expected Behavior:**  
立即打开面板 + loading；详情按 id 分片或至少显示进度。

**Actual Behavior:**  
静默等待整包下载。

---

### Issue #10: 评分明细数据有，UI 不展示

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional / Content |
| **URL** | 详情面板 |

**Description:**  
`projects-detail.json` 含 `score_detail: {stars, activity, adoption, maturity}`，但 `render.js` **完全不渲染** `score_detail`。详情只剩两个总条（可量化/质量），用户无法理解「37 分怎么来的」。

**Expected Behavior:**  
展示分项条/表，并解释权重。

**Actual Behavior:**  
有数据无界面。

---

### Issue #11: 表格工具名 / 类型名对用户不友好

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | UX / Content |
| **URL** | 搜索结果表 |

**Description:**  
- 工具列直接输出 `claude-code, codex-cli, antigravity-cli`
- 类型 pill 直接输出 `mcp-server` / `cli-tool`（`pills()` 未走 i18n.resourceTypes）
- 中文 UI 下仍是机器 id

**Expected Behavior:**  
显示「Claude Code」「MCP Server」等人话标签。

**Actual Behavior:**  
像内部调试表。

---

### Issue #12: 关键字段大面积空值，详情像残页

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Content |
| **URL** | 详情面板 |

**Description:**  
- `forks`: 274/274 空  
- `license`: 274/274 空  
- `languages` 含 `null`：67 条  
- `llm_summary` / `benchmark_ref` / `last_analyzed`: 全空  
- `maturity`: 全 `unknown`  

详情固定渲染 License / Languages / LLM Summary 区块结构，大量 N/A 与永不出现的 LLM 段，显得数据质量差。

**Expected Behavior:**  
空字段隐藏；未上线能力不占位。

**Actual Behavior:**  
一排 N/A。

---

### Issue #13: 报告「理解区」内容过浅，且只有中文

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Content |
| **URL** | 导航：生态周报 / 工具对比 / 推荐榜 |

**Description:**  
周报基本是计数 + Top10 表；工具对比显示 Goose **0 项目**（因 official-seed 被排除且无生态仓）；英文 UI 下报告仍是中文 markdown。对「理解生态」帮助有限。

**Expected Behavior:**  
有趋势解读、新增/掉榜、工具差异洞察；语言跟随 UI。

**Actual Behavior:**  
统计导出页。

---

### Issue #14: 页面无数据新鲜度 / 无站点页脚 / 无仓库入口

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | UX / Trust |
| **URL** | https://coding.lzpgood.online/ |

**Description:**  
用户看不到「数据更新于何时」「覆盖哪些工具」「如何贡献/反馈」。无 footer、无 GitHub 链接、无 last build 时间。作为追踪器，信任元信息缺失。

---

### Issue #15: 项目无法深链分享

| Field | Value |
|-------|-------|
| **Severity** | 🟠 High |
| **Category** | Functional / UX |
| **URL** | 详情面板 |

**Description:**  
URL 只持久化筛选参数，不支持 `?id=` / `#project=`。无法把某个项目详情分享给同事；刷新/返回后详情关闭。

---

### Issue #16: 「只看最近新增」语义失效

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Functional / UX |
| **URL** | 搜索区 checkbox |

**Description:**  
`recentOnly` 用「按 first_seen 排序后的最后 50 条 cutoff」。当前全部同日，筛选几乎恒真或无意义；文案也没解释「最近」定义（7 天？50 条？）。

---

### Issue #17: 搜索实现粗糙，结果不可预期

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Functional / UX |
| **URL** | 搜索框 |

**Description:**  
`JSON.stringify(p).toLowerCase().includes(q)` 会匹配内部 id、字段名、tracking_priority 等。搜 `pending` / `github` / 某字段名可能扫出大量无关项；也无法高亮匹配字段。

---

### Issue #18: 发现区卡片不可键盘访问

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Accessibility |
| **URL** | 发现区 / 工具卡片 |

**Description:**  
`discovery-card` / `tool-card` 是可点击 `div`，无 `tabindex`、`role="button"`、Enter/Space 处理。键盘与读屏用户难用。

---

### Issue #19: 详情 dialog 无焦点管理 / 无滚动锁定

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Accessibility / UX |
| **URL** | `#detailOverlay` |

**Description:**  
有 `role="dialog"` + ESC 关闭，但：
- 打开时不聚焦关闭按钮
- 无焦点陷阱
- 不锁 `body` 滚动
- 主内容无 `aria-hidden`
- 无遮罩层（仅右侧栏，左侧仍可点，易迷失）

---

### Issue #20: 名称列不可点，操作列拥挤

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | 结果表 |

**Description:**  
用户习惯点项目名进详情，但名字只是粗体文本；操作列挤着「打开 / ★ / 推荐 / 详情」。移动端 `min-width:600px` 横向滚动后更难点。

---

### Issue #21: 图表信息密度低且难读

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Visual / UX |
| **URL** | `#toolChart` `#scoreChart` |

**Description:**  
- 工具柱状图 label 截断到 6 字符（`Claude`/`OpenAI` 难辨）
- 无数值标注、无图例标题
- 当前分数分布几乎只剩两根柱，视觉价值低
- 图表无文字替代说明（a11y）

---

### Issue #22: Markdown 报告渲染粗糙

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Visual / Functional |
| **URL** | 报告面板 |

**Description:**  
自定义渲染器：
- 表头行也用 `<td>` 而非 `<th>`
- 链接替换未再校验协议（相对安全因先 escape，但 `javascript:` 等需警惕）
- 复杂表格/长 URL 在 500px 侧栏难读
- 报告应用独立阅读页而不是详情侧栏更合适

---

### Issue #23: 导出收藏缺少空态与复制反馈

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | 导出收藏按钮 |

**Description:**  
无收藏时仍导出空 hash；clipboard 成功后无「已复制」文案（i18n 有 `copied` 未用）；输入框突然出现，移动端易被挤乱。

---

### Issue #24: 指标卡放在搜索区中部，信息架构跳跃

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | `#metrics` |

**Description:**  
路径是：最新发现 → 工具概览 →（搜索标题）→ 分数图 → **总记录/推荐/噪声** → 筛选控件 → 表。  
统计更像全局概览，却埋在搜索区；「噪声/rejected」无解释，普通用户不解。

---

### Issue #25: tracking 状态叙事混乱

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Content / UX |
| **URL** | 详情 Tracking 字段 / 周报 |

**Description:**  
- 257 条 `pending`
- 10 条 `track` 全是 official-seed
- 0 条 `index`
- 搜索默认排除 official-seed  

用户在周报看到「追踪中 10」会以为有 10 个重点生态项目，实际是 10 个官方工具种子，且搜索里不可见。

---

### Issue #26: Goose / 部分工具生态空洞却同权展示

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Content / UX |
| **URL** | 工具概览 / 工具对比报告 |

**Description:**  
Goose 生态仓 0（仅 official-seed）；Trae 极少。工具卡片仍同级展示，点击后搜索结果空或极少，无引导文案「覆盖不足，欢迎提交」。

---

### Issue #27: robots.txt / favicon / 社交 meta 缺失

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | SEO / Content |
| **URL** | `/robots.txt` `/favicon.ico` |

**Description:**  
- `/robots.txt` 因 SPA `try_files ... /index.html` **返回 200 HTML 首页**
- `/favicon.ico` 404
- 无 `og:` / `twitter:` / `theme-color` / canonical  
分享到社交媒体时无预览图与描述增强。

---

### Issue #28: Inter 字体声明了但未加载

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Visual |
| **URL** | 全局样式 |

**Description:**  
`font-family: Inter, system-ui, ...` 但 HTML 无字体加载。多数设备直接 fallback，首屏字体不可控。

---

### Issue #29: 带 hash 的静态资源只缓存 1 小时

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Performance |
| **URL** | `styles.0d5272.css` / `js/*.js` |

**Description:**  
构建已做 content hash，但 nginx `expires 1h`。失去「immutable 长缓存」收益；JSON 数据与 hashed JS 同一策略也不理想（数据应短缓存/协商缓存，hash 资产应长缓存）。

---

### Issue #30: 未知路径一律回落首页（软 404）

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | Functional / SEO |
| **URL** | https://coding.lzpgood.online/foo |

**Description:**  
`/foo`、`/weekly-report.md` 根路径都 200 回首页 HTML。对错误链接无 404 页；爬虫可能索引重复内容。

---

### Issue #31: 官方工具本身不能在搜索中被找到

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | 搜索区 |

**Description:**  
`source_type === 'official-seed'` 被硬过滤。用户搜 “Claude Code” / “Cursor” 可能找不到官方入口卡；工具概览卡片也不是外链到官网/文档，只做筛选器。

---

### Issue #32: 关联项目过宽，相关度低

| Field | Value |
|-------|-------|
| **Severity** | 🟡 Medium |
| **Category** | UX |
| **URL** | 详情「关联项目」 |

**Description:**  
只要共享任意 resource_type **或** target_tool 即相关，再按分数取 Top5。头部 Claude 项目几乎总是推荐同一批高分 Claude 资源，信息增益低。

---

### Issue #33: 无深色以外主题 / 无对比度检查辅助

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Visual / Accessibility |
| **URL** | 全局 |

**Description:**  
强制 dark only；部分 muted 文本 `#94a3b8` on `#0f172a` 大致可过，但 pill 灰底灰字偏弱；无 `prefers-color-scheme` / 高对比选项。

---

### Issue #34: 语言切换按钮状态可访问性一般

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Accessibility |
| **URL** | 语言切换 |

**Description:**  
有 active class，但无 `aria-pressed`。

---

### Issue #35: 表格无排序列头点击，排序控件远离结果

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | UX |
| **URL** | 结果表 |

**Description:**  
只能通过上方 select 排序，不能点「Stars/分数」表头；表头 uppercase 样式像可点却不可点。

---

### Issue #36: 无批量操作 / 无对比模式

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | UX |
| **URL** | 搜索区 |

**Description:**  
生态研究常见需求：并排对比 2–3 个 MCP/skills。当前只能来回开详情。

---

### Issue #37: 无 README 预览（i18n 有文案未实现）

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Functional |
| **URL** | 详情 |

**Description:**  
i18n 含 `readme: 'README 预览'`，界面未实现。用户仍需跳 GitHub 才能判断质量。

---

### Issue #38: 无复制项目链接按钮（i18n 有 copy/copied 未用）

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | UX |
| **URL** | 详情 / 表格 |

**Description:**  
文案键存在，功能未接线。

---

### Issue #39: sitemap 只有首页一条

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | SEO |
| **URL** | `/sitemap.xml` |

**Description:**  
单页应用可理解，但若未来有报告独立 URL/项目页，当前 sitemap 无扩展性；也无 `lastmod`。

---

### Issue #40: 首屏信息噪音：分数图 + 工具图 + 指标卡叠加

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | UX |
| **URL** | 首页中部 |

**Description:**  
在数据量 200+ 且分数分布极偏时，图表先于表格出现，延后「找到一个能用的资源」主任务。对目标用户（开发者找 MCP/skill）主路径偏长。

---

### Issue #41: 移动端控件折行后扫描成本高

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | Visual / UX |
| **URL** | ≤760px |

**Description:**  
工具标签 10 个 + 类型 6 个 + 模式 + 排序 + 两 checkbox 全部 flex wrap，小屏形成大块按钮墙，搜索框不 sticky，回改筛选要滚很远。

---

### Issue #42: 错误态只替换表格，上方骨架/旧区状态不一致

| Field | Value |
|-------|-------|
| **Severity** | 🔵 Low |
| **Category** | UX |
| **URL** | 加载失败路径 |

**Description:**  
`showError()` 只写 `#rows`。若未来部分请求失败，发现区/工具区可能停在 skeleton 或空白，缺少整页错误态。

---

## Issues Summary Table

| # | Title | Severity | Category |
|---|-------|----------|----------|
| 1 | 100 分制几乎全空，排行不可信 | Critical | Content/UX |
| 2 | 「最新发现」实为高分榜 | Critical | Content/UX |
| 3 | 中英内容 100% 相同 | Critical | Content |
| 4 | 资源类型误标（skill→tutorial） | Critical | Content |
| 5 | 收藏无法站内浏览 | High | Functional |
| 6 | writeState 丢掉 favorites hash | High | Functional |
| 7 | 无结果计数/清空筛选 | High | UX |
| 8 | OR/AND 误触翻转 | High | Functional |
| 9 | 详情首载 400KB 且无 loading | High | Performance |
| 10 | score_detail 有数据不展示 | High | Functional |
| 11 | 工具/类型显示机器 id | High | UX |
| 12 | forks/license/LLM 等大面积空 | High | Content |
| 13 | 报告过浅且仅中文 | High | Content |
| 14 | 无更新时间/页脚/仓库入口 | High | Trust |
| 15 | 项目详情不能深链 | High | Functional |
| 16 | 「最近新增」语义失效 | Medium | Functional |
| 17 | JSON.stringify 搜索过宽 | Medium | Functional |
| 18 | 卡片不可键盘访问 | Medium | A11y |
| 19 | dialog 无焦点/滚动管理 | Medium | A11y |
| 20 | 名称不可点，操作列拥挤 | Medium | UX |
| 21 | 图表难读 | Medium | Visual |
| 22 | 报告 Markdown 渲染粗糙 | Medium | Visual |
| 23 | 导出收藏反馈弱 | Medium | UX |
| 24 | 指标卡信息架构跳跃 | Medium | UX |
| 25 | tracking 状态叙事混乱 | Medium | Content |
| 26 | 空生态工具同权展示 | Medium | Content |
| 27 | robots/favicon/OG 缺失 | Medium | SEO |
| 28 | Inter 未加载 | Medium | Visual |
| 29 | hash 资源仅缓存 1h | Medium | Perf |
| 30 | 软 404 | Medium | SEO |
| 31 | 官方工具搜不到 | Medium | UX |
| 32 | 关联项目过宽 | Medium | UX |
| 33-42 | 主题/表头排序/README/复制/sitemap/首屏噪音/移动筛选墙/错误态等 | Low | 多项 |

---

## Testing Coverage

### Pages / Surfaces Tested
- 首页三区（发现 / 工具概览 / 搜索）
- 详情侧栏逻辑与数据字段
- 报告三入口与 `/reports/*.md`
- 公共 JSON：`metrics/tools/projects/projects-detail/curated`
- SEO 相关：`sitemap.xml` / `robots.txt` / `favicon`
- nginx 行为：SPA fallback、缓存头、gzip

### Features Exercised (static + logic)
- 双语切换代码路径
- 多选工具/类型 + OR/AND
- 6 种排序字段
- curatedOnly / recentOnly
- 收藏 localStorage + 导出 URL
- URL query 状态读写
- 虚拟滚动 IntersectionObserver 实现审查
- 图表与 metrics 渲染

### Not Tested / Out of Scope
- 真实浏览器像素级截图与视觉回归（本会话无 browser toolset）
- 真实触屏手势 / 读屏软件实测
- 跨浏览器（Safari/Firefox）兼容
- 第 3 批 LLM 分析上线后的质量分体验

### Blockers
- 无浏览器自动化工具，交互类问题以源码路径 + 线上资源响应交叉确认；标为 Functional 的条目建议在实机再点验一遍。

---

## Prioritized Recommendations（作为真实用户的排序）

### P0 — 先修信任（否则站「能用」但不值得信）
1. **分数解释**：未上线质量分时改文案为「可量化分 /60」或显示「完整分待 LLM 分析」；不要假装 100 分制已生效。  
2. **发现区诚实**：无新增量时改标题/空态；有增量才叫「最新发现」。  
3. **类型纠错**：至少 curated Top / 高星项目重打 `resource_type`。  
4. **中文内容策略**：真翻译，或 UI 标明「摘要为英文原文」。

### P1 — 让「找资源」主路径顺手
5. 结果计数 + 清空筛选 + 活跃条件 chips  
6. 收藏夹视图  
7. 项目名可点 + 详情深链 `?project=`  
8. 工具/类型显示人话名称  
9. 详情展示 `score_detail`，隐藏空字段  
10. 修 OR/AND radiogroup；writeState 保留/规范化 hash

### P2 — 理解与信任包装
11. 页脚：更新时间、GitHub、数据说明  
12. 报告加趋势/洞察，英文 UI 出英文报告  
13. robots.txt / favicon / OG  
14. 详情 loading + 分片详情  
15. hash 静态资源长缓存，JSON 短缓存

---

## Notes

- 第二批前端工程化（模块拆分、事件委托、URL state、骨架屏、CSP/HSTS）基础是好的，问题更多在 **产品诚实度与完成度**，不是「页面打不开」。  
- 当前最伤体验的不是缺炫技交互，而是：**分数、新鲜度、分类、语言** 四个信任信号同时失真。  
- 第 3 批 LLM 分析若上线质量分与中文摘要，可直接消化 Critical #1/#3 的大部分；但 #2/#4/#7 等仍需产品/前端单独修。  
- 完整报告路径：`/root/workspace/search in coding/dogfood-output/report.md`
