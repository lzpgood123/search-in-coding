# 新对话 Agent 启动提示词：前端重写 v2

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。你的任务是实现**前端重写 v2**--第 2 批网站重写的代码质量不达标，10 个 bug 导致功能不可用。全部重写前端 6 个 JS 模块 + index.html + styles.css 补丁 + generate_reports.py 重写，确保每个交互真正可用。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。这是你在该项目中工作的前置要求。

## 第二步：阅读项目上下文

按 `wiki/README.md` 的阅读路线图理解项目，必读：

1. `wiki/README.md` - 项目总索引和阅读路线图
2. `wiki/L3-代码地图.md` - 代码在哪、改哪个文件
3. `wiki/L4A-前端详解.md` - 前端结构（注意：当前版本有 bug，本任务就是修复）
4. `wiki/L6-经验录.md` - 相关坑和注意事项

## 第三步：阅读设计文档

1. `docs/superpowers/specs/2026-07-13-frontend-rewrite-v2-design.md` - **本次设计文档（核心）**，包含 10 个 bug 的详细诊断和修复方案
2. `docs/superpowers/plans/2026-07-13-frontend-rewrite-v2.md` - **实现计划（6 个任务，直接按计划执行）**
3. `CONTEXT.md` - 领域术语表

## 第四步：执行实现

实现计划已存在于 `docs/superpowers/plans/2026-07-13-frontend-rewrite-v2.md`，直接按计划执行。

使用 `subagent-driven-development` 技能执行实现计划。

**6 个任务的执行顺序：**

| 任务 | 内容 | 依赖 |
|------|------|------|
| 1 | 重写 filters.js（纯逻辑 + recentOnly）| 无 |
| 2 | 重写 render.js（10 个 bug 修复核心）| 1 |
| 3 | 重写 app.js（事件委托）| 1,2 |
| 4 | 更新 index.html 和 styles.css | 1,2,3 |
| 5 | 重写 generate_reports.py | 无 |
| 6 | 重建站点、部署、验证 | 1-5 |

**关键注意事项：**
- 任务 2 是核心，render.js 的重写包含 10 个 bug 中 7 个的修复
- 任务 3 的事件委托是架构性改进，所有动态元素不用 inline onclick
- 任务 6 的浏览器验证清单有 24 项，每项必须确认

## 第五步：验证

调用 `verification-before-completion` 技能进行验证：

- [ ] "最新发现"区有 12 个项目卡片
- [ ] 3 份报告链接点击后在面板内正常渲染
- [ ] 工具卡片点击后 tag button 同步高亮
- [ ] 虚拟滚动可连续加载多页
- [ ] "只看最近新增" checkbox 功能正常
- [ ] 工具覆盖柱状图和分数分布直方图显示
- [ ] 详情面板 LLM Summary 正确显示（如有）
- [ ] 导出收藏显示输入框（不是 alert）
- [ ] 报告 markdown 渲染支持表格/列表/标题
- [ ] 移动端表格可横向滚动
- [ ] 无 inline onclick（全部事件委托）
- [ ] 无 JS 控制台错误
- [ ] pipeline --skip-collect PASS

## 第六步：更新 Wiki

更新：
- `wiki/L4A-前端详解.md` - 更新事件委托机制、最新发现逻辑、虚拟滚动修复
- `wiki/L6-经验录.md` - 记录第 2 批的 10 个 bug 和教训

## 关键约束

1. **零依赖原生 JS**：不引入任何框架或外部库
2. **事件委托**：所有动态元素用 `data-action` + 事件委托，不用 inline onclick
3. **字段名遵循第 1 批**：resource_type / total_score(0-100) / tracking_priority / quantifiable_score / quality_score
4. **generate_reports.py 文件名**：weekly-report.md / tool-comparison.md / curated-top.md（与前端 data-report 匹配）
5. **不改 build_site.py**：精简/详情 JSON 逻辑是对的
6. **不改数据结构**：projects.yaml 字段不变
7. **频繁 commit**：每个任务完成后 commit

## 不能改动的部分

- `scripts/build_site.py` - 第 2 批的构建逻辑正确
- `scripts/score.py` / `scripts/normalize.py` / `scripts/migrate_data.py` - 第 1 批已完成
- `data/seed-tools.yaml` / `data/concepts.yaml` - 不变
- `data/projects.yaml` - 数据不变
- 全局 Hermes 配置

## 项目环境信息

- 操作系统：Ubuntu 24.04.4 LTS
- Python：3.12.3（用 python3）
- 工作目录：`/root/workspace/search in coding`
- 站点部署：`/var/www/coding.lzpgood.online/`（Nginx）
- 测试命令：`source .venv/bin/activate && python3 -m pytest tests/ -v`（需要 venv，pytest 未全局安装）
- Pipeline 入口：`python3 scripts/update_tracker.py --skip-collect`
- 站点构建：`python3 scripts/build_site.py`
- 站点部署：`python3 scripts/deploy_site.py`

## 10 个 Bug 清单（必须全部修复）

| # | 问题 | 修复要点 |
|---|------|---------|
| 1 | 发现区永远空 | 改为"最新发现"，按 first_seen + 分数排序取 Top 12 |
| 2 | 报告链接失效 | 重写 generate_reports.py，文件名匹配前端 |
| 3 | 工具卡片点击无反馈 | 点击后同步更新 tag button active 状态 |
| 4 | 虚拟滚动只加载一页 | renderMore 后重新 observe 新最后一行 |
| 5 | "最近发现"未实现 | filters.js apply() 中实现 recentOnly |
| 6 | charts.js 未调用 | renderToolOverview 调用柱状图，新增分数直方图 |
| 7 | LLM Summary 空 | llm_summary 按 {zh,en} 对象取值 |
| 8 | 导出收藏用 alert | 改为输入框 |
| 9 | markdown 渲染粗糙 | 重写 renderReport |
| 10 | 移动端表格溢出 | overflow-x: auto |

## 注意事项

- 前端测试无法用 pytest 自动化，需在浏览器中逐项验证 24 项交互
- `site/js/` 下同时有原始文件和 hash 文件（如 app.js 和 app.517e5a.js），修改原始文件后需要重新运行 build_site.py 生成新 hash
- generate_reports.py 删除了旧字段引用（category/source_quality/ranking_scope），全部用新字段
- 用户偏好详细编号分步指导和精准区分状态含义
- 完成前必须验证对比确认无误
