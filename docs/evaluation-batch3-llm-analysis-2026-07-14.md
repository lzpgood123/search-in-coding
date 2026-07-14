# 第 3 批 LLM 分析系统 评估报告

> 评估日期：2026-07-14  
> 评估对象：Search in Coding 第 3 批（每周 LLM 深度分析系统）  
> 站点：https://coding.lzpgood.online/  
> 数据快照：`data/projects.yaml` 293 条；已分析 3 条；待分析 290 条

## 总览

| 类别 | 项数 | 完成 | 部分完成 | 未完成 | 完成率（完成+0.5×部分） |
|------|------|------|---------|--------|------------------------|
| 基础设施 | 7 | 6 | 1 | 0 | 93% |
| LLM 分析功能 | 6 | 4 | 2 | 0 | 83% |
| 参照基准 | 4 | 2 | 2 | 0 | 75% |
| 评分集成 | 3 | 2 | 1 | 0 | 83% |
| 报告和快照 | 4 | 3 | 1 | 0 | 88% |
| 前端展示 | 3 | 1 | 2 | 0 | 67% |
| 全量运行就绪 | 3 | 1 | 1 | 1 | 50% |
| **合计** | **30** | **19** | **10** | **1** | **80%** |

**结论（一句话）**  
第 3 批的**代码骨架、测试、小规模实测、配置与 cron 注册**已基本到位，LLM 对 3 个官方工具的输出质量可信；但**全量周跑尚未就绪**——Hermes cron 默认脚本超时 120s 会直接杀死 16–48 分钟的全量任务；另有 `score_detail` 被质量分项覆盖、前端总分仍按 `/60` 展示等高优缺陷。

**状态语义说明**
- ✅ 完成：证据充分，符合验收标准
- 🟡 部分完成：主路径可用，但有明显缺口/偏差
- ❌ 未完成：当前会阻断目标能力（全量自动周跑）

---

## 逐项评估

### 一、基础设施（7 项）

#### 1. 脚本是否存在 — ✅
证据：
```
scripts/llm_api.py
scripts/llm_prompts.py
scripts/benchmark_manager.py
scripts/weekly_analysis.py
```
均存在且可导入。

#### 2. 配置文件 — ✅
`config/llm-analysis.yaml` 存在，关键项：
- `base_url: https://token.sensenova.cn/v1`
- `model: deepseek-v4-flash`
- `batch_size: 3`
- `timeout: 120`（单次 API）
- `track_threshold: 20 / index_threshold: 10 / relevance_threshold: 0.3`
- 5 段 benchmark ranges 完整

#### 3. 测试文件 — ✅
```
tests/test_llm_api.py
tests/test_weekly_analysis.py
tests/test_benchmark_manager.py
tests/test_weekly_e2e.py
```
全部存在。

#### 4. 测试通过率 — ✅
```
source .venv/bin/activate && python3 -m pytest tests/ -v --tb=short
============================= 114 passed in 1.36s ==============================
```
含 mock 的 e2e（pipeline / none analysis / benchmark rescore / snapshot）。

#### 5. Cron 配置 — 🟡
存在 job：
- id: `2aa9da554787`
- name: `Search in Coding weekly LLM analysis`
- schedule: `30 3 * * 1`（每周一 03:30）
- `no_agent: true`
- script: `search-in-coding-weekly.sh`
- workdir: `/root/workspace/search in coding`
- next_run: `2026-07-20T03:30:00+08:00`

缺口：
- 未配置 `cron.script_timeout_seconds` / `HERMES_CRON_SCRIPT_TIMEOUT`
- Hermes 默认脚本超时 **120s**
- 同项目 daily job `2a0c271a031f` 已连续出现：`Script timed out after 120s`
- 因此 weekly job“已配置”≠“能跑完”

#### 6. Cron 脚本 — ✅
`~/.hermes/scripts/search-in-coding-weekly.sh` 存在，逻辑正确：
1. `cd` 到项目目录
2. `source .venv/bin/activate`
3. `python3 scripts/weekly_analysis.py`
4. 成功后 `deploy_site.py --dest /var/www/coding.lzpgood.online`

脚本自身**没有** timeout 限制；瓶颈在 Hermes scheduler 的 120s 默认超时。

#### 7. dry-run — ✅
```
=== Weekly Analysis - 2026-07-14 ===
Loaded: 293 projects, 40 curated, 10 tools
Dry run: would analyze 290 projects
Sample: Antigravity CLI / Gemini CLI
```

---

### 二、LLM 分析功能（6 项）

#### 8. 已分析项目数量 — ✅（测试规模，非全量）
- 已分析：`quality_score > 0` → **3 / 293**
- 未分析：**290 / 293**
- 与“只跑了 `--max-projects 3`”一致，**不应记为未实现**，但说明系统尚未完成业务意义上的首次全量分析。

已分析：
| 项目 | total | q + qual | tracking | resource_type |
|------|-------|----------|----------|---------------|
| Hermes Agent | 92 | 52+40 | track | agent-framework, cli-tool |
| OpenCode | 89 | 52+37 | track | agent-framework, cli-tool |
| Claude Code | 87 | 50+37 | track | cli-tool |

#### 9. 质量分合理性 — 🟡
**样本内合理：**
- 三个均为顶级官方/核心工具，quality 37–40 /40，分差小但可解释（Hermes 满分 40，OpenCode/Claude Code 37，novelty 略低）。
- `quality_detail` 维度齐全：relevance / practicality / novelty / ecosystem_value。

**样本外无法验证：**
- 尚无中低分、reject、skills/mcp 等非官方样本，无法证明分差校准与阈值阈值一致。
- 当前“高分全是官方 seed”可能造成校准偏差（见参照基准）。

#### 10. llm_summary 质量 — ✅
三项目均有中英双语，且与事实一致：

| 项目 | zh | en 评价 |
|------|----|---------|
| Hermes Agent | 自改进 AI 代理，内置学习循环，Nous Research | 准确 |
| OpenCode | 开源 AI 编码助手，高社区参与度 | 准确（定位 agent 生态核心） |
| Claude Code | Anthropic 官方终端智能编码代理，生产可用 | 准确 |

无空字段、无语言串台。

#### 11. resource_type 准确性 — ✅（当前 3 样本）
- Hermes Agent → `agent-framework` + `cli-tool`：合理
- OpenCode → `agent-framework` + `cli-tool`：合理
- Claude Code → `cli-tool`：可接受（官方终端 agent；是否补 `agent-framework` 属边界判断，不构成误标）

未发现明显误标；但样本过窄，不能外推到 skills/mcp/rules。

#### 12. tracking_priority 合理性 — ✅（当前 3 样本）
- 三者均为 `track`，与 quality≥20 且高相关一致。
- 全局：`track=15, pending=270, reject=8, index=0`
- `index=0` 正常：未分析项目大多仍为 pending，尚未经过 LLM 分级。

#### 13. benchmark_ref 填充 — 🟡
- 填充率：**293/293**
- 但关联算法不是“按分数段映射”，而是：
  ```python
  if abs(total - ref_score) <= 20:
      p['benchmark_ref'] = ref.get('project_id')
      break  # 按 benchmarks dict 顺序第一次命中
  ```
- 结果：
  - 已分析三者都指向 `official-hermes-agent`（合理）
  - 大量未分析中分项目也会被吸到最近的一个高/中位标杆，**不等于真正所属分数段**
  - 例：`JuliusBrussee/caveman` total=49 → `benchmark_ref=official-antigravity-cli`（可用段 52），若严格按 41–60 段也可接受，但算法脆弱

---

### 三、参照基准系统（4 项）

#### 14. benchmarks.yaml 存在 — ✅
5 段齐全：

| 段 | 项目 | score |
|----|------|-------|
| 标杆 | Hermes Agent | 92 |
| 优秀 | OpenCode | 89 |
| 可用 | Antigravity CLI / Gemini CLI | 52 |
| 萌芽 | op7418/Humanizer-zh | 40 |
| 噪声 | qdhenry/Claude-Code-MCP-Manager | 20 |

#### 15. 参照项目合理性 — 🟡
- 标杆/优秀：在**当前仅 3 个带 quality 的分数空间**里合理。
- 可用/萌芽/噪声：基本靠 **quantifiable_score only** 选出（quality=0），因此：
  - “可用=52 的官方 CLI”其实只是可量化高、尚未 LLM 质评
  - 分数段语义在全量分析前**不稳定**
- reason 文本可读、逻辑自洽，但校准基础偏窄。

#### 16. 参照更新流程 — ✅
`weekly_analysis.py` main 顺序：
1. LLM analysis  
2. `update_benchmarks(analyzed)`  
3. `rescore_all(analyzed)`  
4. snapshot / save / reports / build  

符合“先更新参照基准再重评分”。

#### 17. benchmark_ref 关联 — 🟡
见第 13 项：有填充，但匹配策略是 ±20 首次命中，不是按 `config/llm-analysis.yaml` 的 min/max 段严格落桶。全量后可能出现跨段错挂。

---

### 四、评分系统集成（3 项）

#### 18. total_score 计算 — ✅
全库扫描：`total_score != quantifiable_score + quality_score` → **0 条 mismatch**。

#### 19. 评分范围 — ✅
- 已分析 total：87–92（合理，因 quality 近满分）
- 未分析 total：6–52，且全部 `total == quantifiable`（quality=0）
- 符合“未分析 = 仅可量化分”

#### 20. score.py 整合 — 🟡
`score.py` 正确保留已有 `quality_score`：
```python
if 'quality_score' not in p:
    p['quality_score'] = 0
p['total_score'] = q_score + p['quality_score']
```
但存在**副作用**：
```python
p['score_detail'] = detail  # 永远写成 stars/activity/adoption/maturity
```
与 `weekly_analysis.merge_analysis_result` 的行为冲突：
```python
if 'quality_detail' in analysis:
    p['score_detail'] = analysis['quality_detail']  # 覆盖成 quality 四维
```
**高优缺陷：字段语义冲突**  
`score_detail` 同时被用作：
1. 可量化分项（前端 Stars/Activity/Adoption/Maturity）
2. LLM 质量分项（relevance/practicality/novelty/ecosystem_value）

实测：
- Hermes Agent `score_detail = {relevance:10, practicality:10, novelty:10, ecosystem_value:10}`
- 前端仍按 `sd.stars / sd.activity / ...` 渲染 → **已分析项目分项显示为 0**

---

### 五、报告和快照（4 项）

#### 21. 3 份报告存在 — ✅
```
docs/reports/weekly-report.md   (2026-07-14)
docs/reports/tool-comparison.md
docs/reports/curated-top.md
```

#### 22. 报告内容质量 — 🟡
- 无旧字段残留：`category/source_quality/ranking_scope/record_kind` 搜索结果为 0
- 使用了 `resource_type`、`total_score`、tracking 统计
- 但 `generate_reports.py` 的 Top 列表**刻意排除** `source_type == official-seed`：
  ```python
  eco = [p for p in projects if p.get('source_type') != 'official-seed' and p.get('tracking_priority') != 'reject']
  ```
  因此 Top 10 全是未分析生态项目（最高 49），**看不到刚分析出的 87–92 分官方工具**。
  这是设计过滤，不是生成失败；但在“LLM 周报”语境下，会让报告无法反映本周质量分突破。

#### 23. 快照生成 — ✅
`data/snapshots/2026-07-14.json` 存在。

#### 24. 快照内容 — ✅
含全部要求字段：
- total_projects=293
- by_tracking={track:15, pending:270, reject:8}
- avg_score=23.5
- tool_coverage / resource_type_coverage
- analyzed_count=3  
另有 by_source / curated_count / rejected_count。

---

### 六、前端展示（3 项）

#### 25. quality_score 展示 — 🟡
`site/js/render.js`：
- `qualityScore > 0` → 显示 `质量分: X/40`
- 否则 → `质量分待 LLM 分析`（i18n `qualityPending`）

问题：
- 总分 badge 使用 `total_score`，旁注仍写 **`/ 60 可量化分`**
- 进度条 `width = total / 60 * 100`
- 已分析项目 total≈90 时：
  - 文案语义错误（90 不是 /60）
  - 进度条溢出 100%
- 列表页同样有 `/60` 标注（`render.js` L228）

#### 26. llm_summary 展示 — ✅
- 正确处理 `{zh,en}` 对象，按当前语言取值
- 本地 `projects-detail.json` 与线上 `projects.json` 均含 3 个已分析项目字段
- 线上站点 HTTP 200，live list analyzed=3

#### 27. benchmark_ref 展示 — 🟡
- 详情有 `Benchmark Reference` 区块
- 但显示的是 **project_id**（如 `official-hermes-agent`），不是项目名
- 且因第 13 项算法，未分析项目也会显示一个“最近标杆”，可能误导

---

### 七、全量运行就绪度（3 项）

#### 28. 290 个待分析项目 — ✅
dry-run：`would analyze 290 projects`  
与 `293 - 3 = 290` 一致。

#### 29. 全量运行预估 / 超时 — ❌
- 配置 `batch_size=3` → 约 97 批
- API timeout=120s/请求，预估总时长 16–48 分钟（提示词估算合理）
- **Cron 默认 script timeout = 120 秒**
- 证据链：
  1. `config.yaml` 无 `cron.script_timeout_seconds`
  2. env 无 `HERMES_CRON_SCRIPT_TIMEOUT`
  3. daily no_agent job 今日失败：`Script timed out after 120s`
  4. 官方文档：默认 120s，需显式调大

**判定：当前 weekly cron 几乎必然超时失败，全量自动运行未就绪。**

#### 30. 错误恢复 — 🟡
优点：
- `merge_analysis_result(None)` 保留原项目，不崩溃
- e2e 有 `test_pipeline_with_none_analysis`
- `get_projects_to_analyze` 以 `last_analyzed` 为 7 天窗口，成功者会跳过 → 具备**弱断点续传**
- key 轮询 + retry 存在（13 keys）

缺口：
- 失败项目不写 `last_analyzed`（好），但无独立失败队列/重试计数
- 中途进程被 120s kill 时，可能已部分写盘也可能未写盘；当前脚本是**分析完再统一 save**，超时则本周结果可能全部丢失
- 无进度 checkpoint 文件（每 N 批落盘）

---

## LLM 输出质量评估（3 个已分析项目）

### Hermes Agent（92 = 52+40）
| 字段 | 值 | 评判 |
|------|----|------|
| quality_score | 40 | ✅ 顶级代理框架，满分合理 |
| quality_detail | 10/10/10/10 | ✅ 一致性好 |
| resource_type | agent-framework, cli-tool | ✅ |
| target_tools | hermes-agent, claude-code, codex-cli | 🟡 主工具 hermes-agent 正确；附带 claude-code/codex-cli 可解释为兼容生态，但略宽 |
| tracking | track | ✅ |
| llm_summary | 中英双语，点出 self-improving + learning loop | ✅ 准确 |

### OpenCode（89 = 52+37）
| 字段 | 值 | 评判 |
|------|----|------|
| quality_score | 37 | ✅ 略低于 Hermes，合理 |
| novelty | 7 | ✅ 未给满分，有区分度 |
| resource_type | agent-framework, cli-tool | ✅ |
| target_tools | [opencode] | ✅ 精准 |
| llm_summary | 开源 AI coding agent，高社区参与 | ✅ |

### Claude Code（87 = 50+37）
| 字段 | 值 | 评判 |
|------|----|------|
| quality_score | 37 | ✅ |
| resource_type | [cli-tool] | 🟡 可接受；若加 agent-framework 也成立 |
| target_tools | [claude-code] | ✅ |
| llm_summary | Anthropic 官方终端编码代理，生产使用 | ✅ 准确 |

**样本结论：** 在“官方核心工具”子集上，LLM 输出可信、结构完整、双语合格。  
**外推限制：** 尚无 skills / mcp-server / rules / 低质噪声样本，无法验证误标率与 reject 阈值。

---

## 关键风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| Cron 脚本默认 120s 超时 | **Critical** | 全量 16–48min 必被杀；daily 已实证超时 |
| `score_detail` 字段语义冲突 | **High** | LLM 覆盖可量化分项 → 详情 Stars/Activity 等显示 0 |
| 前端总分仍按 `/60` + 进度条/60 | **High** | 已分析 total>60 时 UI 失真 |
| 无增量落盘 checkpoint | **High** | 超时/中断后整轮分析白跑 |
| benchmark_ref ±20 首次命中 | **Medium** | 跨段错挂；全量后更明显 |
| 参照基准在 quality 稀疏时失真 | **Medium** | 可用/萌芽/噪声多由 quantifiable 顶上 |
| 周报 Top 排除 official-seed | **Low/设计** | 本周 LLM 高分官方工具不进 Top 表 |
| 计划文档 checkbox 仍全是 `[ ]` | **Low** | 实现已做，计划未回填完成态 |

---

## 与计划验收标准对照

| 计划验收项 | 状态 |
|-----------|------|
| dry-run 显示待分析数量 | ✅ 290 |
| `--max-projects 3` 实测成功 | ✅ 3 项目有 quality/summary/tags/tracking |
| benchmarks 5 段 | ✅ |
| snapshot 生成 | ✅ |
| 3 份报告 | ✅ |
| Hermes cron 周一 + no_agent | 🟡 已注册，但超时未配置 |
| 全部测试通过 | ✅ 114 passed |
| 站点展示 LLM 结果 | 🟡 字段在数据层有；UI 展示有缺陷 |
| 全量业务就绪 | ❌ 未就绪 |

---

## 建议（按优先级）

### P0 — 全量运行前必须修
1. **提高 weekly cron 超时**  
   - `hermes` 配置：`cron.script_timeout_seconds: 3600`（或至少 2700）  
   - 或 `HERMES_CRON_SCRIPT_TIMEOUT=3600`  
   - 同步检查 daily job（已在 120s 失败）
2. **分析过程增量落盘**  
   - 每批或每 N 个成功项目 `save_jsonish`  
   - 保证 120s/网络中断后仍可续跑
3. **拆分 `score_detail` 与 `quality_detail`**  
   - 建议：`score_detail` 只保留 quantifiable 四维  
   - 新增 `quality_detail` 存 LLM 四维  
   - `merge_analysis_result` 停止覆盖 `score_detail`

### P1 — 体验与校准
4. 前端详情/列表：  
   - 已分析：`total /100`，进度条按 100  
   - 未分析：可继续显示 quantifiable `/60` + “质量分待 LLM 分析”
5. `benchmark_ref` 按 config ranges 严格落桶，展示项目名而非 id
6. 小批量分层试跑再全量：  
   - 例如 `--max-projects 30`，覆盖 skills/mcp/低星项目，检查 reject/index 分布

### P2 — 报告与文档
7. 周报增加“本周 LLM 新分析 / 分数跃迁”小节（含 official-seed）
8. 回填 plan checkbox 与 wiki（L1/L3/L4B/L6）状态
9. 全量成功后更新 snapshot 与站点，再做第二次质量抽检（建议 20 条分层抽样）

---

## 测试与证据附录

| 检查 | 命令/位置 | 结果 |
|------|-----------|------|
| 测试 | `pytest tests/ -v` | 114 passed |
| dry-run | `python3 scripts/weekly_analysis.py --dry-run` | 290 to analyze |
| 数据 | `data/projects.yaml` | 3 analyzed, 0 score mismatch |
| 基准 | `data/benchmarks.yaml` | 5 ranges |
| 快照 | `data/snapshots/2026-07-14.json` | 字段齐全 |
| 报告 | `docs/reports/*.md` | 3 份，无旧字段 |
| 前端代码 | `site/js/render.js` | quality/llm/benchmark 有；/60 问题在 |
| 线上 | `https://coding.lzpgood.online/` | 200；analyzed=3 |
| Cron | `hermes cron list` / `jobs.json` | weekly 03:30 Mon, no_agent；timeout 默认 120 |
| Daily 失败证据 | `~/.hermes/cron/output/2a0c271a031f/2026-07-14_03-02-05.md` | timed out after 120s |
| API keys | `~/.hermes/auth.json` `custom:sensenova` | 13 keys |

---

## 最终判定

| 维度 | 判定 |
|------|------|
| 实现完成度（代码+测试+小跑通） | **高（约 80%）** |
| LLM 输出质量（当前 3 样本） | **可信** |
| 系统可靠性（全量自动周跑） | **未就绪（Critical: timeout）** |
| 是否建议立刻全量 cron 放行 | **否** |
| 建议下一步 | 先修 P0（超时 + 落盘 + score_detail），再 `--max-projects 30` 试跑，通过后再放开周一全量 |

**一句话交付结论：**  
第 3 批“能跑通小样本”已完成；“能每周自动、可靠地分析全部约 290 个项目并正确展示”尚未完成。优先堵住 cron 120s 超时与 `score_detail` 覆盖，再谈全量上线。
