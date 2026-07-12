<!-- superpowers-zh:begin (do not edit between these markers) -->
# Superpowers-ZH 中文增强版

本项目已安装 superpowers-zh 技能框架（23 个 skills）。

## 核心规则

1. **收到任务时，先检查是否有匹配的 skill** — 哪怕只有 1% 的可能性也要检查
2. **设计先于编码** — 收到功能需求时，先用 brainstorming skill 做需求分析
3. **测试先于实现** — 写代码前先写测试（TDD）
4. **验证先于完成** — 声称完成前必须运行验证命令
5. **Wiki 优先** — 进入项目先读 `wiki/README.md` 路线图理解项目；完成工作后按 wiki 各文档底部的「更新指引」更新对应文档；发现新坑立即追加到 `wiki/L6-经验录.md`

## 项目手册（Wiki）

**Wiki 是项目的唯一真相源。** 新 Agent 进入项目时不从零读代码，而是按 wiki 路线图理解项目。所有 Agent 必须遵守以下规则：

### 进入规则（所有 Agent，不可跳过）

1. 进入项目后，**第一步**读 `wiki/README.md`，找到自己角色的阅读路线
2. 按路线图读 3-5 个文档，建立项目心智模型，**然后**才开始工作
3. 禁止跳过 wiki 直接读代码——除非 wiki 中不存在相关信息

### 各角色必读清单

| 角色 | 必读文档 | 时机 |
|------|---------|------|
| 方案设计 Agent | P1-产品决策日志（了解用户偏好和历史决策）→ L1-全景（了解产品现状） | 讨论前 |
| 项目搭建 Agent | L3-代码地图（定位文件）→ L6-经验录（避坑）→ 按任务选读 L4A/L4B/L5 | 开发前 |
| 框架讨论 Agent | P3-框架演进（了解历史变更）→ L2-架构（了解技术边界） | 讨论前 |

### 更新规则（开发者，不可跳过）

开发完成后，**必须**按以下对应关系更新 wiki：

| 变更类型 | 更新文档 | 更新内容 |
|---------|---------|---------|
| 新增/删除文件 | L3-代码地图 | 文件列表和功能说明 |
| 前端代码变更 | L4A-前端详解 | 函数列表、CSS 变量、交互逻辑 |
| 后端代码变更 | L4B-后端详解 | 路由、Pydantic 模型、AI 适配层 |
| API 接口变更 | L5-接口契约 | 接口契约、State 结构 |
| 发现新坑/修复 Bug | L6-经验录 | **立即追加**，不等开发完成 |
| 项目状态变化 | L1-全景 | 当前版本、功能摘要 |
| 方案设计讨论 | P1-产品决策日志 | 新想法、决策、偏好（讨论后追加） |
| 框架变更 | P3-框架演进 | 框架快照 + 变更时间线 |

### 更新原则

- **即时更新** — L6-经验录发现即记录，不等阶段结束
- **谁变更谁更新** — 项目搭建 agent 更新 L1/L3/L4/L5，方案设计 agent 更新 P1，框架讨论 agent 更新 P3
- **更新后自查** — 加载 `wiki-checkpoint` skill 确认合规

```
wiki/
├── README.md           # 总索引 + 阅读路线图
├── L1-全景.md           # 项目是什么
├── L2-架构.md           # 系统怎么搭的
├── L3-代码地图.md       # 代码在哪
├── L4A-前端详解.md       # 前端怎么改
├── L4B-后端详解.md       # 后端怎么改
├── L5-接口契约.md       # 数据怎么流
├── L6-经验录.md         # 踩过什么坑
├── P1-产品决策日志.md     # 产品往哪走（方案设计 agent 维护）
├── P2-功能扩展路线图.md   # 待实现功能规划（方案设计 agent 维护）
└── P3-框架演进.md         # 框架怎么变（框架讨论 agent 维护）
```

## 工具映射

技能中引用的 Claude Code 工具名称对应 Hermes Agent 的等价工具：
- `Read` → `read_file`
- `Write` → `write_file`
- `Edit` → `patch`
- `Bash` → `terminal`
- `Grep` / `Glob` → `search_files`
- `Skill` → `skill_view`
- `Task`（子智能体） → `delegate_task`
- `WebSearch` → `web_search`
- `WebFetch` → `web_extract`
- `TodoWrite` → `todo`

## 可用 Skills

Skills 位于 `.hermes/skills/` 目录，每个 skill 有独立的 `SKILL.md` 文件。

- **brainstorming**: 在任何创造性工作之前必须使用此技能——创建功能、构建组件、添加功能或修改行为。在实现之前先探索用户意图、需求和设计。
- **chinese-code-review**: 中文 review 沟通参考——话术模板、分级标注（必须修复/建议修改/仅供参考）、国内团队常见反模式应对。仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。
- **chinese-commit-conventions**: 中文 commit 与 changelog 配置参考——Conventional Commits 中文适配、commitlint/husky/commitizen 中文模板、conventional-changelog 中文配置。仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。
- **chinese-documentation**: 中文文档排版参考——中英文空格、全半角标点、术语保留、链接格式、中文文案排版指北约定。仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。
- **chinese-git-workflow**: 国内 Git 平台配置参考——Gitee、Coding.net、极狐 GitLab、CNB 的 SSH/HTTPS/凭据/CI 接入差异与镜像同步配置。仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。
- **dispatching-parallel-agents**: 当面对 2 个以上可以独立进行、无共享状态或顺序依赖的任务时使用
- **executing-plans**: 当你有一份书面实现计划需要在单独的会话中执行，并设有审查检查点时使用
- **finishing-a-development-branch**: 当实现完成、所有测试通过、需要决定如何集成工作时使用——通过提供合并、PR 或清理等结构化选项来引导开发工作的收尾
- **handoff-prompt**: 当设计文档和实现计划完成后，需要生成一份可在新对话中执行的启动提示词时使用。方案设计 agent 自动加载，生成 7 步路由指南，输出在对话中供用户复制
- **mcp-builder**: MCP 服务器构建方法论 — 系统化构建生产级 MCP 工具，让 AI 助手连接外部能力
- **project-wiki**: 当初始化新项目文档体系、构建跨 Agent 项目全息手册、或用户要求"构建wiki"、"初始化项目手册"、"生成项目文档"时使用。一次性构建 wiki/ 目录 + 写入 HERMES.md 维护规则
- **receiving-code-review**: 收到代码审查反馈后、实施建议之前使用，尤其当反馈不明确或技术上有疑问时——需要技术严谨性和验证，而非敷衍附和或盲目执行
- **requesting-code-review**: 完成任务、实现重要功能或合并前使用，用于验证工作成果是否符合要求
- **subagent-driven-development**: 当在当前会话中执行包含独立任务的实现计划时使用
- **systematic-debugging**: 遇到任何 bug、测试失败或异常行为时使用，在提出修复方案之前执行
- **test-driven-development**: 在实现任何功能或修复 bug 时使用，在编写实现代码之前
- **using-git-worktrees**: 当需要开始与当前工作区隔离的功能开发，或在执行实现计划之前使用——通过原生工具或 git worktree 回退机制确保隔离工作区存在
- **using-superpowers**: 在开始任何对话时使用——确立如何查找和使用技能，要求在任何响应（包括澄清性问题）之前调用 Skill 工具
- **verification-before-completion**: 在宣称工作完成、已修复或测试通过之前使用，在提交或创建 PR 之前——必须运行验证命令并确认输出后才能声称成功；始终用证据支撑断言
- **wiki-checkpoint**: 在声称工作完成前使用，检查 wiki 读/写合规——确认已读必读文档、已更新应更新的文档，输出合规报告
- **workflow-runner**: 在 Claude Code / OpenClaw / Cursor 中直接运行 agency-orchestrator YAML 工作流——无需 API key，使用当前会话的 LLM 作为执行引擎。当用户提供 .yaml 工作流文件或要求多角色协作完成任务时触发。
- **writing-plans**: 当你有规格说明或需求用于多步骤任务时使用，在动手写代码之前
- **writing-skills**: 当创建新技能、编辑现有技能或在部署前验证技能是否有效时使用

## 如何使用

当任务匹配某个 skill 时，使用 `skill_view("skill-name")` 加载对应 skill 并严格遵循其流程。

### 项目级 Skills（非全局）

本项目的 23 个 skills 位于 `.hermes/skills/` 目录，**未注册到全局 external_dirs**（避免污染所有对话的 skills_list）。它们只在本工作区生效，通过以下方式加载：

1. **首选：** `skill_view("skill-name")` — Hermes 会自动发现 `.hermes/skills/` 中的 skill，正常加载
2. **回退：** 如果 skills_list 中看不到（证明 Hermes 未自动发现），用 `read_file(".hermes/skills/<name>/SKILL.md")` 直接读取 skill 内容

任务匹配 skill 时，按以下顺序检查：
- 先在 skills_list 中找全局 skill（如 plan、systematic-debugging）
- 如果找不到匹配的全局 skill，再检查 `.hermes/skills/` 中的项目级 skill
- 使用 read_file 直接读取路径 `.hermes/skills/<name>/SKILL.md` 获取完整内容
<!-- superpowers-zh:end -->
