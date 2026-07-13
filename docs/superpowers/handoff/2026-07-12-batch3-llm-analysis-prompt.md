# 新对话 Agent 启动提示词：第 3 批 - LLM 分析系统

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。你的任务是实现**第 3 批：LLM 分析系统**--每周一 03:00 自动 LLM 深度分析系统，直接调用 SenseNova API（DeepSeek-V4-Flash），对项目做相关性判断、分类打标、质量评分（40分）、生成双语一句话评价、维护动态参照基准，最后重评全部项目并生成 3 份报告。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。这是你在该项目中工作的前置要求。

## 第二步：阅读项目上下文

按 `wiki/README.md` 的阅读路线图理解项目，必读：

1. `wiki/README.md` - 项目总索引和阅读路线图
2. `wiki/L1-全景.md` - 项目是什么、核心流程
3. `wiki/L3-代码地图.md` - 代码在哪、改哪个文件
4. `wiki/P1-产品决策日志.md` - 用户偏好和产品约束（重点读 2026-07-12 的 grill-with-docs 决策）
5. `wiki/L6-经验录.md` - 相关坑和注意事项

这是后端任务，加读：
- `wiki/L4B-后端详解.md` - 数据管道流程、评分系统

## 第三步：阅读设计文档

1. `docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md` - **设计文档**，重点读"双层节奏架构"和"评分系统"章节
2. `docs/superpowers/plans/2026-07-12-batch3-llm-analysis.md` - **实现计划（8 个任务，直接按计划执行）**
3. `CONTEXT.md` - 领域术语表（重点读 Quality Score, Benchmark Reference, Weekly Analysis）
4. `docs/adr/0002-dual-layer-daily-weekly.md` - 双层节奏架构
5. `docs/adr/0003-100-point-dual-layer-scoring.md` - 100 分制评分 + 参照基准
6. `docs/adr/0007-tracking-priority-levels.md` - 项目追踪分级

## 第四步：执行实现

实现计划已存在于 `docs/superpowers/plans/2026-07-12-batch3-llm-analysis.md`，直接按计划执行。

使用 `subagent-driven-development` 技能执行实现计划。每个子 Agent 必须遵循 TDD--先写测试再写实现。

**8 个任务的执行顺序：**

| 任务 | 内容 | 依赖 |
|------|------|------|
| 1 | SenseNova API 封装（llm_api.py）| 无 |
| 2 | Prompt 模板（llm_prompts.py）| 无 |
| 3 | 参照基准管理器（benchmark_manager.py）| 无 |
| 4 | 主分析脚本（weekly_analysis.py）| 1,2,3 |
| 5 | 双语翻译模块（translation.py）| 1 |
| 6 | 配置文件和 .gitignore | 无 |
| 7 | 端到端测试（mock LLM）| 1,2,3,4 |
| 8 | 端到端验证和 Cron 配置 | 1-7 |

**关键注意事项：**
- 任务 1-3 可并行开发，无依赖
- 任务 4 是核心，依赖 1-3
- 任务 8 步骤 3 会实际调用 LLM API（限 3 个项目），确保 API key 可用
- Cron 配置需要在 Hermes 中创建，no_agent 模式直接运行脚本

## 第五步：验证

调用 `verification-before-completion` 技能进行验证：

- [ ] `weekly_analysis.py` 可 dry-run，显示待分析项目数量
- [ ] `weekly_analysis.py --max-projects 3` 实际运行成功，3 个项目被 LLM 分析
- [ ] 被分析项目有 quality_score > 0、llm_summary（中英双语）、resource_type、target_tools、tracking_priority
- [ ] `data/benchmarks.yaml` 有 5 个分数段的参照项目
- [ ] `data/snapshots/YYYY-MM-DD.json` 快照文件生成
- [ ] 3 份报告生成（weekly-report.md, tool-comparison.md, curated-top.md）
- [ ] `translation.py` 可翻译 curated 项目的 summary
- [ ] Hermes cron 配置为每周一 03:00，no_agent 模式
- [ ] 所有测试通过（pytest tests/ -v）
- [ ] 站点正常加载，详情面板显示 LLM 分析结果

## 第六步：更新 Wiki

更新：
- `wiki/L1-全景.md` - 更新项目状态（双层节奏架构上线）
- `wiki/L3-代码地图.md` - 新增 weekly_analysis.py、llm_api.py、llm_prompts.py、benchmark_manager.py、translation.py
- `wiki/L4B-后端详解.md` - 新增 LLM 分析系统章节
- `wiki/L6-经验录.md` - 记录 LLM 分析的坑（API 速率限制、JSON 解析、key 轮询）

## 关键约束

1. **直接调用 API，不用 delegate_task**：cron 自动运行时无人审批，delegate_task 会被阻塞
2. **API：SenseNova + DeepSeek-V4-Flash**：base_url=`https://token.sensenova.cn/v1`，13 个 key 轮询
3. **每批 3 并发**：不用修改全局 max_concurrent_children，直接在 Python 中用 ThreadPoolExecutor
4. **先更新参照基准再重评分**：参照基准是评分的标尺
5. **quality_score 是 0-40**：加上 quantifiable_score(0-60) = total_score(0-100)
6. **TDD**：先写测试（mock LLM 调用）再写实现
7. **频繁 commit**：每个任务完成后 commit

## 不能改动的部分

- `data/seed-tools.yaml` - 工具列表不变
- `data/concepts.yaml` - 概念定义不变
- 前端代码（site/）- 第 2 批已完成
- `scripts/score.py` 的 quantifiable_score 逻辑 - 第 1 批已完成
- `scripts/normalize.py` - 第 1 批已完成
- `scripts/build_site.py` 的精简/详情 JSON 逻辑 - 第 2 批已完成
- 全局 Hermes 配置（max_concurrent_children 等）

## 项目环境信息

- 操作系统：Ubuntu 24.04.4 LTS
- Python：3.12.3（用 python3，标准库 urllib 做 HTTP 请求，不依赖 requests/httpx）
- GitHub CLI：gh 已认证（lzpgood123）
- 工作目录：`/root/workspace/search in coding`
- 站点部署：`/var/www/coding.lzpgood.online/`（Nginx）
- 测试命令：`python3 -m pytest tests/ -v`
- Pipeline 入口：`python3 scripts/update_tracker.py --skip-collect`
- LLM API 凭证：存储在 `~/.hermes/auth.json` 的 `credential_pool.custom:sensenova` 中（13 个 key）
- LLM API base_url：`https://token.sensenova.cn/v1/chat/completions`
- LLM 模型：`deepseek-v4-flash`

## 注意事项

- **API key 安全**：不要在代码中硬编码 key，从 `~/.hermes/auth.json` 读取
- **API 速率限制**：13 个 key 轮询，遇到 429 时指数退避 + 切换 key
- **LLM 输出不稳定**：JSON 解析需要容错（code block 包裹、周围有文本等情况）
- **翻译缓存**：`data/translations-cache/` 不入 Git（已在 .gitignore 中）
- **Cron 脚本超时**：当前每日 cron 有 120s 超时问题，weekly_analysis 可能需要更长时间，考虑设置更长超时
- **抽检机制**：每批 5% 随机抽样检查分析质量，准确率 < 80% 调整 prompt
- 用户偏好详细编号分步指导和精准区分状态含义
- 完成前必须验证对比确认无误
