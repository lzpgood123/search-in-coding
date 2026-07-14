# 新对话 Agent 启动提示词：第 3 批 P0+P1 修复

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。第 3 批 LLM 分析系统评估发现 3 个 P0（Critical/High）和 2 个 P1 问题。你的任务是修复全部 5 个问题，然后做一次 30 个项目的分层试跑验证。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。

## 第二步：阅读项目上下文

1. `wiki/README.md` - 项目总索引
2. `wiki/L3-代码地图.md` - 代码在哪
3. `wiki/L6-经验录.md` - 相关坑

## 第三步：阅读评估报告和计划

1. `docs/evaluation-batch3-llm-analysis-2026-07-14.md` - **评估报告（核心）**，详细列出了 5 个问题
2. `docs/superpowers/plans/2026-07-14-batch3-p0p1-fixes.md` - **实现计划（6 个任务，直接执行）**

## 第四步：执行修复

**6 个任务：**

| 任务 | 问题 | 优先级 |
|------|------|--------|
| 1 | cron 超时 120s -> 3600s | P0-Critical |
| 2 | score_detail 和 quality_detail 拆分 | P0-High |
| 3 | 增量落盘 checkpoint | P0-High |
| 4 | 前端 /60 vs /100 展示 | P1-High |
| 5 | benchmark_ref 显示项目名 | P1-Medium |
| 6 | 重建 + 30 项目试跑验证 | 验证 |

## 第五步：验证

- [ ] `hermes config get cron.script_timeout_seconds` 返回 3600
- [ ] 已分析项目的 score_detail 包含 stars/activity（不是 relevance/practicality）
- [ ] 已分析项目有独立的 quality_detail 字段
- [ ] weekly_analysis.py 每批后保存 projects.yaml
- [ ] 前端已分析项目显示 /100，未分析显示 /60
- [ ] 前端 benchmark_ref 显示项目名
- [ ] --max-projects 30 试跑成功，覆盖多种 resource_type
- [ ] pipeline --skip-collect PASS

## 关键约束

1. **不改 LLM prompt 模板**：prompt 已验证可用
2. **不改 benchmarks.yaml**：参照基准已正确建立
3. **不改数据结构**：只拆分字段、改展示逻辑
4. **增量落盘不能影响性能**：每批 3 个项目保存一次，不是每条
5. **30 项目试跑必须覆盖多种类型**：不能只分析 official-seed

## 项目环境信息

- 工作目录：`/root/workspace/search in coding`
- Python：3.12.3（用 python3）
- 测试：`source .venv/bin/activate && python3 -m pytest tests/ -v`
- 站点：https://coding.lzpgood.online/
- LLM API：SenseNova，13 个 key 在 `~/.hermes/auth.json`
- 当前数据：293 条项目，3 个已分析，290 个待分析
- Hermes cron：每周一 03:30，no_agent 模式

## 5 个问题的具体说明

### P0-1: cron 超时（Critical）
Hermes cron 默认脚本超时 120s，weekly_analysis 全量运行需 16-48 分钟，必被杀。
修复：`hermes config set cron.script_timeout_seconds 3600`

### P0-2: score_detail 字段冲突（High）
LLM 的 quality_detail 覆盖了 score_detail（可量化分项），导致详情页 Stars/Activity 显示 0。
修复：weekly_analysis.py 写入 `quality_detail` 独立字段，不覆盖 `score_detail`。

### P0-3: 无增量落盘（High）
当前分析完才统一保存，超时/中断后整轮白跑。
修复：每批分析完成后 save_jsonish 保存一次。

### P1-4: 前端 /60 展示错误（High）
已分析项目 total=87-92，但前端仍展示 /60，进度条溢出。
修复：quality_score > 0 时展示 /100，否则展示 /60。

### P1-5: benchmark_ref 显示 project_id（Medium）
详情面板显示 `official-hermes-agent` 而非 `Hermes Agent`。
修复：通过 project_id 查找项目名展示。
