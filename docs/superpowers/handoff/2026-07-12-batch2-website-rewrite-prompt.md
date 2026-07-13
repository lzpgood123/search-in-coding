# 新对话 Agent 启动提示词：第 2 批 - 网站重写

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的开发 Agent。你的任务是实现**第 2 批：网站重写**--将 27 行压缩 JS 重写为模块化零依赖前端，实现三区布局（发现/理解/搜索）、多选标签筛选、项目详情面板、站内报告渲染、收藏功能，以及完整的前端性能优化。

## 第一步：加载技能框架

立即调用 Skill 工具加载 `using-superpowers` 技能。这是你在该项目中工作的前置要求。

## 第二步：阅读项目上下文

按 `wiki/README.md` 的阅读路线图理解项目，必读：

1. `wiki/README.md` - 项目总索引和阅读路线图
2. `wiki/L1-全景.md` - 项目是什么、核心流程
3. `wiki/L3-代码地图.md` - 代码在哪、改哪个文件
4. `wiki/P1-产品决策日志.md` - 用户偏好和产品约束
5. `wiki/L6-经验录.md` - 相关坑和注意事项

这是前端任务，加读：
- `wiki/L4A-前端详解.md` - 前端状态机、组件体系、样式体系（注意：第 1 批可能已更新部分字段名）

## 第三步：阅读设计文档

1. `docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md` - **设计文档**，重点读"网站设计"和"前端性能优化"章节
2. `docs/superpowers/plans/2026-07-12-batch2-website-rewrite.md` - **实现计划（8 个任务，直接按计划执行）**
3. `CONTEXT.md` - 领域术语表
4. `docs/adr/0006-zero-dependency-modular-three-zone.md` - 零依赖模块化 + 三区布局决策
5. `docs/adr/0008-frontend-performance-optimization.md` - 前端性能优化策略

## 第四步：执行实现

实现计划已存在于 `docs/superpowers/plans/2026-07-12-batch2-website-rewrite.md`，直接按计划执行。

使用 `subagent-driven-development` 技能执行实现计划。每个子 Agent 必须遵循 TDD--先写测试再写实现。

**8 个任务的执行顺序：**

| 任务 | 内容 | 依赖 |
|------|------|------|
| 1 | CSS 自定义属性和基础样式重写 | 无 |
| 2 | i18n.js 模块 | 1 |
| 3 | data.js 模块（数据加载 + 收藏）| 无 |
| 4 | filters.js 模块（多选筛选 + 排序 + URL 状态）| 3 |
| 5 | render.js 模块（三区渲染 + 虚拟滚动 + 详情面板）| 2,3,4 |
| 6 | charts.js + app.js + index.html | 1,2,3,4,5 |
| 7 | 重写 build_site.py（精简 JSON + 详情 JSON + sitemap + hash）| 无 |
| 8 | 删除旧 app.js、端到端验证和部署 | 1-7 |

**关键注意事项：**
- 任务 1-6 是纯前端文件，可以快速迭代
- 任务 7 修改后端 build 脚本，需要 TDD
- 任务 8 是集成验证，确保所有模块协同工作

## 第五步：验证

调用 `verification-before-completion` 技能进行验证：

- [ ] `site/app.js`（旧 27 行）已删除，替换为 `site/js/` 下 6 个模块文件
- [ ] `styles.css` 使用 CSS 自定义属性，包含三区布局、骨架屏、详情面板样式
- [ ] `index.html` 使用语义 HTML，包含 JSON-LD 结构化数据
- [ ] 三区布局正常：发现区 + 工具概览区 + 搜索区
- [ ] 筛选器：标签按钮组多选，OR/AND 切换，6 种排序
- [ ] 项目详情面板：侧边滑出，含评分明细、关联项目推荐
- [ ] 收藏功能：localStorage 存储，URL 导出
- [ ] 骨架屏 + 渐进式渲染 + 虚拟滚动
- [ ] 报告站内渲染
- [ ] `build_site.py` 生成精简 JSON + 详情 JSON + sitemap.xml + hash 文件名
- [ ] 移动端响应式正常
- [ ] 无 JS 控制台错误
- [ ] 所有测试通过
- [ ] 站点部署到 https://coding.lzpgood.online/ 并可访问

## 第六步：更新 Wiki

开发完成后，按 wiki 各文档底部的"更新指引"更新：
- `wiki/L3-代码地图.md` - 更新前端文件列表（site/js/ 目录）
- `wiki/L4A-前端详解.md` - **完全重写**（新的模块结构、三区布局、筛选器、详情面板）
- `wiki/L6-经验录.md` - 记录前端重构的坑

## 关键约束

1. **零依赖原则**：不引入任何前端框架或外部库（ADR-0006）
2. **多 `<script>` 标签加载**：不用 ES modules，用全局变量共享（ADR-0006）
3. **字段名遵循第 1 批**：resource_type（不是 category）、total_score（0-100）、tracking_priority
4. **CSS 自定义属性**：所有颜色值用 `var(--color-xxx)`，不硬编码（ADR-0006）
5. **TDD**：build_site.py 的修改先写测试
6. **频繁 commit**：每个任务完成后 commit

## 不能改动的部分

- `data/` 目录下的数据文件 - 由第 1 批 pipeline 生成
- `scripts/score.py` / `scripts/normalize.py` / `scripts/migrate_data.py` - 第 1 批已完成
- `data/seed-tools.yaml` / `data/concepts.yaml` - 不变
- 后端 pipeline 逻辑 - 只改 `build_site.py`

## 项目环境信息

- 操作系统：Ubuntu 24.04.4 LTS
- Python：3.12.3（用 python3）
- GitHub CLI：gh 已认证（lzpgood123）
- 工作目录：`/root/workspace/search in coding`
- 站点部署：`/var/www/coding.lzpgood.online/`（Nginx）
- 测试命令：`python3 -m pytest tests/ -v`
- Pipeline 入口：`python3 scripts/update_tracker.py --skip-collect`
- 站点构建：`python3 scripts/build_site.py`
- 站点部署：`python3 scripts/deploy_site.py`

## 注意事项

- 前端测试无法用 pytest 自动化，需在浏览器中手动验证所有交互
- hash 文件名机制要求每次 build_site.py 运行后 index.html 中的引用更新
- `projects-detail.json` 可能较大（数千条全量字段），但只在点击详情时按需 fetch
- 移动端测试：用浏览器 DevTools 模拟 375px 宽度
- 用户偏好详细编号分步指导和精准区分状态含义
- 完成前必须验证对比确认无误
