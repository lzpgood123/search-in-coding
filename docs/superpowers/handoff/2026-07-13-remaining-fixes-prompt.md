# 新对话 Agent 启动提示词：遗留项修复

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。三个批次的优化已基本完成，但评估报告发现若干遗留问题。你的任务是修复全部遗留问题：seed-tools 路径错误、高星项目分类误标、字段填充不全、detail JSON 缺字段、29 条未翻译 summary。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。

## 第二步：阅读项目上下文

必读：
1. `wiki/README.md` - 项目总索引
2. `wiki/L3-代码地图.md` - 代码在哪
3. `wiki/L6-经验录.md` - 相关坑

## 第三步：阅读设计文档

1. `docs/evaluation-three-batches-2026-07-13.md` - **评估报告（核心）**，详细列出了每个遗留问题
2. `docs/superpowers/plans/2026-07-13-remaining-fixes.md` - **实现计划（6 个任务，直接按计划执行）**
3. `docs/superpowers/specs/2026-07-13-site-optimization-v3-design.md` - 原始设计规格

## 第四步：执行实现

实现计划已存在于 `docs/superpowers/plans/2026-07-13-remaining-fixes.md`，直接按计划执行。

**6 个任务的执行顺序：**

| 任务 | 内容 | 预计耗时 |
|------|------|---------|
| 1 | 修正 seed-tools.yaml 三个 repo 路径 | 2 分钟 |
| 2 | 修正 7 个高星项目 resource_type 误标 | 5 分钟 |
| 3 | 批量补全字段（forks/license/topics/readme_preview） | 30-60 分钟（API 调用） |
| 4 | build_site.py 导出 readme_preview 和 topics 到 detail JSON | 5 分钟 |
| 5 | 翻译剩余英文 summary | 10 分钟 |
| 6 | 重建站点、重新评分、部署 | 5 分钟 |

**关键注意事项：**
- 任务 3 最耗时（需要对约 150 个项目调用 gh repo view），支持断点续传
- 任务 3 的 enrich_projects.py 使用 gh CLI（已认证），不需要 API key
- 任务 5 的翻译使用 SenseNova API（从 ~/.hermes/auth.json 读取 key）
- 大部分 29 条"未翻译"项目原文已是中文，实际需要翻译的只有少数英文 summary

## 第五步：验证

- [ ] seed-tools.yaml 中 goose=block/goose, cursor=getcursor/cursor, opencode=sst/opencode
- [ ] 7 个高星项目不再被标为 tutorial
- [ ] forks 填充率 > 70%
- [ ] license 填充率 > 60%
- [ ] topics 填充率 > 50%
- [ ] readme_preview 填充率 > 50%
- [ ] detail JSON 包含 readme_preview 和 topics 字段
- [ ] 翻译覆盖率 > 95%（英文残留 < 10 条）
- [ ] pipeline --skip-collect PASS
- [ ] 站点已部署到 https://coding.lzpgood.online/

## 第六步：更新 Wiki

更新 `wiki/L6-经验录.md`，记录遗留项修复过程中的坑。

## 关键约束

1. **不改前端代码**：前端已在批次 B 中完成
2. **不改数据结构**：只补全字段值
3. **gh CLI 已认证**：直接用 gh repo view 获取数据
4. **API key 从 auth.json 读取**：不硬编码
5. **频繁 commit**：每个任务完成后 commit

## 项目环境信息

- 操作系统：Ubuntu 24.04.4 LTS
- Python：3.12.3（用 python3）
- GitHub CLI：gh 已认证（lzpgood123）
- 工作目录：`/root/workspace/search in coding`
- 站点部署：`/var/www/coding.lzpgood.online/`（Nginx）
- 测试命令：`source .venv/bin/activate && python3 -m pytest tests/ -v`
- Pipeline 入口：`python3 scripts/update_tracker.py --skip-collect`
- LLM API：SenseNova，key 在 `~/.hermes/auth.json` 的 `credential_pool.custom:sensenova`

## 当前数据状态（评估报告确认的问题）

| 问题 | 当前状态 |
|------|---------|
| seed-tools repo 路径 | goose=aaif-goose/goose(错)、cursor=cursor/cursor(错)、opencode=anomalyco/opencode(错) |
| 高星项目标 tutorial | 7 个项目（goose 51k、continue 34k、cursor 33k、Roo-Code 24k 等） |
| forks 填充率 | 53.7% |
| license 填充率 | 52.4% |
| topics 填充率 | 28.9% |
| readme_preview 填充率 | 2.0%（仅 6 条） |
| detail JSON 缺字段 | 无 readme_preview、无 topics |
| 翻译覆盖率 | 90.1%（29 条未翻译，大部分原文已是中文） |
