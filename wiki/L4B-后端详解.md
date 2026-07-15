# L4B-后端详解 — 后端怎么改

> 后端开发者深入文档。读完能独立修改后端代码。

## 数据管道流程

```
update_tracker.py (入口)
  ├─ collect_github.py     -> data/raw/github/YYYY-MM-DD/
  ├─ normalize.py          -> data/projects.yaml (仅 GitHub)
  ├─ validate_data.py      -> 验证数据完整性
  ├─ score.py              -> 更新 projects.yaml (100分制可量化分)
  ├─ finalize_data.py      -> curated-projects.yaml + rejected-projects.yaml
  ├─ generate_reports.py   -> docs/reports/*.md
  ├─ build_site.py         -> site/data/*.json + site/reports/
  ├─ quality_gate.py       -> 全量检查
  ├─ py_compile *.py       -> 语法检查
  └─ deploy_site.py        -> /var/www/ (仅 --deploy 时)
```

## 分组设计

输入文件（不变的数据定义）：
| 文件 | 用途 | 关键字段 |
|------|------|---------|
| data/seed-tools.yaml | 10 个目标工具定义 | id, name, vendor, primary_type, aliases, extension_points, tracking_priority |
| data/queries.yaml | GitHub 和 Exa 搜索 query 模板 | github[], exa[] |
| data/concepts.yaml | 核心概念定义 | id, name, description |
| config/scoring.yaml | 评分权重配置 | source_weights, category_weights, penalties, ranking |

缓存文件（可重新生成）：
| 文件 | 生成来源 | 用途 |
|------|---------|------|
| data/projects.yaml | normalize.py | 全量归一化索引库 |
| data/scores.yaml | score.py | 评分结果 |
| data/curated-projects.yaml | finalize_data.py | 自动推荐集 |
| data/rejected-projects.yaml | finalize_data.py | 噪声集 |
| docs/reports/*.md | generate_reports.py | 自动报告 |
| site/data/*.json | build_site.py | 站点数据 |
| data/raw/* | collectors | 原始快照 |
| data/snapshots/* | snapshot_and_diff.py | 数据快照 |

## 分类系统 (resource_type)

在 `normalize.py` 中定义的基于 **name+summary 关键词 + topics 映射** 的规则引擎（2 维标签）。**不读** `readme_preview`（README 只服务 LLM）。

### resource_type（多选，关键词规则引擎 + topics；LLM 可再打标）

按 `CONCRETE_RESOURCE_ORDER` 优先级匹配：

| 标签 | 关键词/topics 示例 | 优先级 |
|---------|-----------|--------|
| mcp-server | mcp server/gateway/hub；topics: mcp, mcp-server, model-context-protocol | 1（最高） |
| skills | skill library / claude code skill；topics: skills, claude-skills, agent-skills | 2 |
| extension | extension, plugin, vscode/chrome extension | 3 |
| rules | cursor rules, coding rules, system prompt；topics: cursor-rules, cursorrules | 4 |
| agent-framework | agent runtime/platform/sdk, coding agent；topics: multi-agent, agent-framework, langchain | 5 |
| cli-tool | developer tool, code assistant, terminal；topics: cli, cli-tool, command-line | 6 |
| tutorial | tutorial, awesome list, benchmark（仅无具体类型时） | 7（最低） |

**匹配规则：**
1. Phase 1：关键词匹配具体类型（mcp-server ~ cli-tool）
2. Phase 1.5：`TOPIC_RESOURCE_MAP` 精确 topics 映射（tutorial topics 仅在无具体类型时生效）
3. 兜底：`['tutorial']`
4. **禁止**「仅有 AI topics → cli-tool」兜底（AI/llm/claude 等信号本身不构成具体类型）
5. 具体类型命中时**不**再追加 tutorial 标签
6. CLI：`python3 scripts/normalize.py --skip-raw` 仅重分类现有 `projects.yaml`

### target_tools（多选，**可为空**）

1. seed-tools aliases 在 text 或 topics 中匹配 → 具体工具 id
2. 无匹配但 topics/文本含 AI 信号 → `['general-ai-coding']`
3. 无匹配且无 AI 信号 → **`[]`**（前端 `toolLabels` 显示 muted 占位；quality_gate/metrics 兼容）

### 安全 merge

`safe_merge_record()` 刷新 GitHub 字段时**保留** LLM 字段：`quality_score` / `quality_detail` / `tracking_priority` / `last_analyzed` / `benchmark_ref` / `llm_summary`；`official-seed` 强制 `tracking_priority=track` 且不改 display name。

## 评分系统

### 100 分制双层评分（ADR-0003）

| 层 | 节奏 | 负责 | 分值 |
|---|------|------|------|
| 可量化分 | 每日自动 | 规则驱动，基于 GitHub API 实时数据 | 60 分 |
| 质量分 | 每周 LLM | 子代理深度调查 | 40 分 |
| 总分 | 每日更新 | 可量化分 + 最近一次质量分 | 0-100 |

### 可量化分细则（60 分，每日自动）

| 维度 | 分值 | 规则 |
|------|------|------|
| Stars | 20 | >=50k=20, >=10k=16, >=5k=12, >=1k=8, >=100=4, >0=2, 0=0 |
| Activity | 15 | pushed_at 90天内=15, 180天内=12, 365天内=8, 2年内=4, 更久=1 |
| Adoption | 10 | forks>=1000=10, >=100=7, >=10=4, >0=2, 0=0 |
| Maturity | 15 | 有release=5, 有文档=3, 有tests=3, 有CI=2, license明确=2 |

### 质量分细则（40 分，每周 LLM，第 3 批实现）

| 维度 | 分值 | 由 LLM 评估 |
|------|------|------------|
| Relevance | 10 | 与 AI coding agent 生态的相关性 |
| Practicality | 10 | README 完整度、示例代码、文档质量 |
| Novelty | 10 | 内容独特性、创新性 |
| Ecosystem_value | 10 | 扩展面数量、生态重要性 |

### 配置文件

- `config/scoring-v2.yaml` - 100 分制评分配置（量化分规则 + 质量分占位 + 参照基准段）
- `config/scoring.yaml` - 旧评分配置（保留但不再使用）

### Curated 选择规则（新）

1. GitHub 高分项目优先入选（至少 30 条）
2. 确保每个工具至少 1 条 curated
3. 补满到 40 条（按分数排序）
4. Rejected：分数 <=10 或 archived 或 tracking_priority=reject

## 数据校验

validate_data.py 检查：
- seed-tools.yaml 必须含 id, name, vendor, primary_type, aliases, tracking_priority
- concepts.yaml 必须含 id, name, description
- projects.yaml 必须含 id, name, url, source_type, resource_type, target_tools, summary, review_state, total_score, tracking_priority

## 质量门禁 (quality_gate.py)

检查项：
- 归一化记录 >= 100
- curated >= 20, rejected >= 5
- 所有项目含 required 字段（resource_type, tracking_priority, total_score, quantifiable_score, quality_score）
- 所有项目含 i18n.zh/en
- review_state 为 auto-indexed / auto-curated / auto-rejected
- tracking_priority 为 pending / track / index / reject
- 每个工具覆盖 >= 1
- 官方工具 source_type=official-seed 且 tracking_priority=track
- GitHub 记录 >= 50
- config/scoring-v2.yaml 存在
- 所有必需的站点数据文件存在

## LLM 分析系统（第 3 批）

### 每周 LLM 分析流程

```
weekly_analysis.py (入口；周一全量 / 工作日增量 via Hermes cron)
  ├─ pre_filter()           -> 移除 archived，按 stars 降序
  ├─ run_analysis()         -> LLM 批量分析（batch_size=10 并发，ThreadPoolExecutor；候选 stars 降序）
  │    ├─ llm_api.py        -> SenseNova API 调用（13 key 轮询，429 指数退避）
  │    ├─ llm_prompts.py    -> 项目分析 prompt（输入: readme_preview + 元数据）
  │    └─ merge_analysis_result() -> 合并 LLM 结果到项目记录
  ├─ update_benchmarks()    -> LLM 选择 5 分数段参照项目
  │    └─ benchmark_manager.py -> 加载/保存/更新 benchmarks.yaml
  ├─ rescore_all()          -> total_score = quantifiable + quality
  ├─ save_snapshot()        -> data/snapshots/YYYY-MM-DD.json
  ├─ save_jsonish()         -> 更新 projects.yaml
  ├─ generate_reports.py    -> 3 份报告（周报/工具对比/推荐榜）
  └─ build_site.py          -> 重建站点 JSON
```

### SenseNova API 封装（llm_api.py）

| 组件 | 说明 |
|------|------|
| load_api_keys() | 从 ~/.hermes/auth.json 读取 13 个 key（custom:sensenova 凭证池） |
| KeyRotator | 轮询 key + 线程锁；失败跳过；`mark_success`/`get_stats`；stats 用 key 后 8 位 |
| parse_json_response() | 容错 JSON 解析：直接解析 -> markdown 代码块 -> 正则提取 -> 首尾花括号 |
| call_llm() | 单次 API 调用（urllib，OpenAI 兼容格式） |
| call_with_retry() | 重试：成功 mark_success；401/403/429/空响应 mark_failed(reason)；最多 3 次 |
| batch_analyze() | 并发分析；返回 `(results_dict, key_stats)`；默认 workers 由 config `batch_size=10` |

### 参照基准管理（benchmark_manager.py）

5 个分数段，每段 1 个参照项目：

| 标签 | 分数范围 | 说明 |
|------|---------|------|
| 标杆 | 81-100 | 生态标杆项目 |
| 优秀 | 61-80 | 高质量生态项目 |
| 可用 | 41-60 | 可用项目 |
| 萃芽 | 21-40 | 早期项目 |
| 噪声 | 0-20 | 低质量或无关项目 |

- LLM 从每个分数段 top 5 候选中选择 1 个参照项目
- 参照项目写入 `data/benchmarks.yaml`
- 每周分析时先更新参照基准，再基于参照重评分

### 质量分 4 维度（40 分，LLM 评估）

| 维度 | 分值 | 评估标准 |
|------|------|---------|
| Relevance | 0-10 | 与 AI coding agent 生态的相关性 |
| Practicality | 0-10 | README 完整度、示例代码、文档质量 |
| Novelty | 0-10 | 内容独特性、创新性 |
| Ecosystem_value | 0-10 | 扩展面数量、生态重要性 |

### LLM 输出 Schema

```json
{
  "relevance_score": 0.0-1.0,
  "resource_type": ["mcp-server", ...],
  "target_tools": ["claude-code", ...],
  "tracking_priority": "track|index|reject",
  "quality_score": 0-40,
  "quality_detail": {"relevance": 0-10, "practicality": 0-10, "novelty": 0-10, "ecosystem_value": 0-10},
  "llm_summary": {"zh": "2-3 句话中文评价：是什么 + 核心功能 + 适合谁用", "en": "2-3 sentence English summary: what it is, core features, who it's for"},
  "analysis_notes": "brief explanation"
}
```

### Hermes Cron 配置

- **Job ID:** 2aa9da554787
- **名称:** Search in Coding weekly LLM analysis
- **计划:** 每周一 05:00（`0 5 * * 1`）— 与 03:00 采集错开 2 小时
- **模式:** no_agent=True（直接运行脚本，不经过 LLM 编排）
- **脚本:** `~/.hermes/scripts/search-in-coding-weekly.sh`
- **超时:** `cron.script_timeout_seconds=3600`（全量 LLM 分析约 16–48 分钟，默认 120s 会杀进程）
- **部署:** 脚本内自动调用 deploy_site.py
- **增量落盘:** `run_analysis()` 每批后 `save_jsonish('data/projects.yaml')`
- **字段拆分:** LLM `quality_detail` 写独立字段，不覆盖可量化 `score_detail`
- **官方 seed 保护:** `source_type=official-seed` 强制 `tracking_priority=track`
- **Key 监控:** 每次分析后写入 `data/llm-key-stats.json`（最近 30 条）
- **429 降级:** 累计 429 比例 >30% 时 halved 剩余批次，标记 `degraded_mode: true`

### 配置文件

- `config/llm-analysis.yaml` - LLM 分析配置（API 参数、批次大小、重试策略、基准分数段）

## 一次性历史回溯采集（initial_collection.py）

- **时间下界:** `created:>2024-01-01`
- **分层:** L1≥100k → L2 50k–99k → L3 10k–49k（全时段+极薄负向）；L4 1k–9k（按月+弱正向/coding signal）；L5a/L5b（topic+keyword，adaptive，严格过滤）；<100 本轮不做
- **安全 merge:** 同 URL/repo 只刷新 GitHub 可量化字段，保留 `quality_score`/`quality_detail`/`tracking_priority`/`last_analyzed`/`benchmark_ref`；新项目默认 `pending` + `quality_score=0`；official-seed 不降级
- **code search:** CLAUDE.md / .cursorrules / AGENTS.md 等 → `pending`；详情阶段 strict 过滤噪声
- **checkpoint:** `data/initial-collection-checkpoint.json`（gitignore）+ `data/raw/github-initial/candidates.json` + search-cache
- **CLI:** `--dry-run` / `--search-only` / `--details-only` / `--skip-existing` / `--no-readme` / `--skip-seed-topics` / `--max-details`
- **本轮不做:** dependents API、README 内链抽生态、stars<100（见 ADR-0005）
- **2026-07-14 执行结果:** 候选 **6016**，详情 **6016**，`projects` **293→5165**，`last_analyzed` **33** 完好；`filtered≈1085`，`detail_errors=1`；本地 `update_tracker.py --skip-collect` **PASS**；commit `8571786`（未 push/deploy）

## 错误处理

- 采集器独立运行，失败只记录不阻塞管道（required=False）
- normalize/score/finalize/report/build 失败则直接 exit（required=True）
- Exa 不可用时自动 fallback 到 web 搜索，但标记 fallback-not-exa

## 配置管理

环境变量（可选）：
- SEARCH_IN_CODING_WEBROOT — 部署目标目录
- EXA_API_KEY — 仅在直接 HTTP fallback 时需要

配置文件：
- config/scoring.yaml — 评分权重 + 排名阈值

## 测试覆盖

12 个测试文件（pytest），190 个测试用例（2026-07-15 自运行加固后）：
- test_pipeline_features.py - 管道功能测试（resource_types 误匹配、finalize 弱记录）
- test_data_integrity.py - 数据完整性测试（i18n、review_state 一致性）
- test_normalize_fields.py - normalize.py 字段映射和 resource_type 分类测试（25 个，批次 A 新增）
- test_build_site_v2.py - 站点构建测试（精简/详情字段、hash 文件名、sitemap）
- test_score_v2.py - 100 分制评分测试（stars/activity/adoption 维度）
- test_score_main.py - score.py 主流程测试
- test_migrate_data.py - 数据迁移测试
- test_initial_collection.py - 历史回溯采集测试（分层查询、过滤、安全 merge、checkpoint）
- test_translate_summaries.py - 翻译模块测试（JSON 解析、缓存、key 轮询）
- test_llm_api.py - LLM API 封装测试（key 轮询、JSON 解析容错、重试逻辑）
- test_benchmark_manager.py - 参照基准管理测试（5 分数段、加载/保存、LLM 更新）
- test_weekly_analysis.py - 每周分析流程测试（预筛选、结果合并、项目选择）
- test_weekly_e2e.py - 端到端测试（mock LLM 全流程、None 处理、基准+快照）
- test_refresh_track_projects.py - track 项目分批刷新（选择/排序/merge 保留 LLM 字段）
- test_archive_low_score.py - 低分/reject 归档选择逻辑
- test_cleanup_disk.py - raw/snapshots 过期清理逻辑

运行命令：`source .venv/bin/activate && python3 -m pytest tests/ -v`

## 下一步读什么

→ [L5-接口契约](L5-接口契约.md)

## 更新指引

**触发条件：** API 端点增删、核心模块变更、错误处理逻辑变更、评分规则变更
**更新内容：** 管道流程、分类系统、评分系统、配置管理


## Batch4 LLM 策略（2026-07-15，已收口 COMPLETE）

- `config/llm-analysis.yaml`：`api.batch_size: 10`（`DEFAULT_BATCH_SIZE=10`）
- `get_projects_to_analyze()`：跳过 archived；候选 **stars 降序**；优先 `last_analyzed is None` / 超过 7 天
- `KeyRotator`：`threading.Lock` 保护 next/mark_failed/reset
- cron：`script_timeout_seconds=3600`
  - 采集 daily：`search-in-coding-daily.sh` → `update_tracker.py` + `refresh_track_projects.py`（job `2a0c271a031f`，03:00，source venv，不 deploy）
  - 周 LLM：`search-in-coding-weekly.sh` → `weekly_analysis.py`（job `2aa9da554787`，Mon 05:00）
  - 日增量 LLM：`search-in-coding-llm-daily.sh` → `weekly_analysis.py --max-projects 200 --skip-benchmarks` + deploy（job `f110f12e4d96`，Tue–Sat 05:00）
  - weekly release Hermes cron `7388b6c788e8` 已 pause（GitHub Actions release.yml）
- 运维脚本：`archive_low_score.py`、`cleanup_disk.py`；LLM key stats → `data/llm-key-stats.json`；429 降级
- 收口基线→终态（2026-07-15）：active no_last_analyzed **100→0**；total no_la 含 archived **205→105**；candidates_to_analyze **0**
