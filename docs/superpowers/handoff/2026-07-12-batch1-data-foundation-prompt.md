# 新对话 Agent 启动提示词：第 1 批 - 数据基础

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。你的任务是实现**第 1 批：数据基础**--清理旧数据、重构字段结构、实现一次性历史回溯采集、上线 100 分制可量化评分系统，确保站点在新数据结构下可访问。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。这是你在该项目中工作的前置要求。

## 第二步：阅读项目上下文

按 `wiki/README.md` 的阅读路线图理解项目，必读：

1. `wiki/README.md` - 项目总索引和阅读路线图
2. `wiki/L1-全景.md` - 项目是什么、核心流程
3. `wiki/L3-代码地图.md` - 代码在哪、改哪个文件
4. `wiki/P1-产品决策日志.md` - 用户偏好和产品约束（重点读 2026-07-12 的 grill-with-docs 决策）
5. `wiki/L6-经验录.md` - 相关坑和注意事项

这是后端+数据任务，加读：
- `wiki/L4B-后端详解.md` - 数据管道流程、评分系统、分类系统
- `wiki/L5-接口契约.md` - 数据字段结构

## 第三步：阅读设计文档

1. `docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md` - **本次实现的设计文档（核心）**，重点读"实现分批策略"章节的第 1 批部分
2. `docs/superpowers/plans/2026-07-12-batch1-data-foundation.md` - **实现计划（8 个任务，直接按计划执行）**
3. `CONTEXT.md` - 领域术语表（理解 Resource/Tracking Priority/Quantifiable Score 等术语）
4. `docs/adr/` - 7 份 ADR，重点读 ADR-0001（仅 GitHub）、ADR-0003（100 分评分）、ADR-0005（回溯+增量）

## 第四步：执行实现

实现计划已存在于 `docs/superpowers/plans/2026-07-12-batch1-data-foundation.md`，直接按计划执行。

使用 `subagent-driven-development` 技能执行实现计划。每个子 Agent 必须遵循 TDD--先写测试再写实现。

**8 个任务的执行顺序（有依赖）：**

| 任务 | 内容 | 依赖 |
|------|------|------|
| 1 | 数据迁移脚本（migrate_data.py）| 无 |
| 2 | 新评分配置（scoring-v2.yaml）| 无 |
| 3 | 重写 score.py | 依赖 1（calc_quantifiable_score）|
| 4 | 适配 normalize.py | 依赖 1（字段结构）|
| 5 | 一次性历史回溯采集（initial_collection.py）| 依赖 4（github_record）|
| 6 | 适配 build_site.py + 前端 | 依赖 1（新字段）|
| 7 | 适配 quality_gate/validate/finalize/update_tracker | 依赖 1-6 |
| 8 | 端到端验证和部署 | 依赖 1-7 |

**任务 5（回溯采集）是最耗时的步骤**，需要数千次 GitHub API 调用。建议先完成任务 1-4 和 6-7，确保 pipeline 跑通后再执行任务 5 的实际采集（dry-run 验证可以先做）。

## 第五步：验证

调用 `verification-before-completion` 技能进行验证：

- [ ] data/projects.yaml 只含 GitHub 来源数据（264 + 10 = 274 条）
- [ ] 每条记录有 resource_type、tracking_priority、quantifiable_score、quality_score(0)、total_score(0-60)
- [ ] 旧字段（score/score_reason/category/record_kind/ranking_scope/source_quality 等）全部移除
- [ ] score.py 正确计算 60 分可量化分
- [ ] initial_collection.py 可 dry-run，生成正确的查询和月度范围
- [ ] 站点正常加载，显示新字段数据
- [ ] 所有测试通过（pytest tests/ -v）
- [ ] pipeline --skip-collect 全流程 PASS
- [ ] 站点部署到 https://coding.lzpgood.online/ 并可访问

## 第六步：更新 Wiki

开发完成后，按 wiki 各文档底部的"更新指引"更新：
- `wiki/L1-全景.md` - 更新项目状态（数据量、评分系统变更）
- `wiki/L3-代码地图.md` - 新增 migrate_data.py、initial_collection.py
- `wiki/L4B-后端详解.md` - 更新评分系统（100 分制）、数据管道流程
- `wiki/L5-接口契约.md` - 更新数据字段结构
- `wiki/L6-经验录.md` - 记录迁移过程中的坑

## 关键约束

1. **只从 GitHub 收集**，不恢复 Exa/fallback-web 采集器（ADR-0001）
2. **评分 100 分制**，本批只实现 60 分可量化部分，quality_score 留 0 占位（ADR-0003）
3. **字段名严格遵循计划**：resource_type（不是 category）、tracking_priority（不是 record_kind）、quantifiable_score + quality_score + total_score
4. **TDD**：每个任务先写测试再写实现
5. **频繁 commit**：每个任务完成后 commit，不要攒大 commit

## 不能改动的部分

- `data/seed-tools.yaml` - 工具列表不变（10 个工具保留）
- `data/concepts.yaml` - 概念定义不变
- `site/styles.css` - 前端样式第 2 批再改
- 采集器代码（collect_exa.py、collect_web.py）保留但不再调用

## 项目环境信息

- 操作系统：Ubuntu 24.04.4 LTS（内核 6.8.0-111-generic）
- Python：3.12.3（用 python3，不要用 python）
- GitHub CLI：gh 已认证（lzpgood123）
- 工作目录：`/root/workspace/search in coding`
- 站点部署：`/var/www/coding.lzpgood.online/`（Nginx）
- 测试命令：`python3 -m pytest tests/ -v`
- Pipeline 入口：`python3 scripts/update_tracker.py --skip-collect`

## 注意事项

- 数据迁移是不可逆操作，先 `--dry-run` 确认统计再实际执行
- initial_collection.py 实际运行会消耗大量 GitHub API 调用（数千次），确保断点续传可用
- 迁移后旧数据无法恢复，确保 git 中有迁移前的 commit 可回溯
- 用户偏好详细编号分步指导和精准区分状态含义
- 完成前必须验证对比确认无误
