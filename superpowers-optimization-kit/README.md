# Superpowers Optimization Kit

> Superpowers-ZH **全自动工作流优化包**。在保留 Wiki / Handoff / Checkpoint 的基础上，增加 pre-grill、Goal 文档、阶段门禁、决策仲裁、完成契约与自动恢复，让交付可无人值守推进。

## 这是什么？

Superpowers 是一套 AI Agent 协作框架（设计先于编码、TDD、验证先于完成等纪律）。本优化包解决两层问题：

1. **协作摩擦**（经典三件套）：新 Agent 从零理解项目、设计→实现交接靠人工、Wiki 合规靠自觉  
2. **全自动交付断点**：开跑前可行性不清、阶段自批放行、失败原地踏步、口头宣称完成

| 能力 | 解决的问题 | 产出 |
|------|----------|------|
| **Wiki 体系** | 新 Agent 每次从零理解项目 | 分层项目手册 + 阅读路线图 |
| **Handoff Prompt** | 设计→实现交接依赖人工 | 模式 A：7 步启动提示词；模式 B：Goal 启动卡 |
| **Wiki 规则化** | 合规靠自觉 | 核心规则 + AGENTS.md + `wiki-checkpoint` |
| **Pre-grill** | 盲目 `/goal` | PRD 可行性循环 + 准备清单 |
| **Goal 文档** | 无人值守缺主指令 | `docs/superpowers/goals/*-goal.md` + `/goal` 声明 |
| **完成契约** | 口头宣称完成 | 活文档硬门槛 4/4 |
| **Gatekeeper** | 执行方自检放行 | 6 阶段独立 `delegate_task` 门禁 |
| **Decision Arbiter** | PRD 缺口/矛盾卡死 | 运行期仲裁（不改 PRD 目标） |
| **Auto-recovery** | 门禁 FAIL 原地踏步 | 策略旋转 + failures 报告 |

## 全自动主链路

```
用户提交 PRD
    ↓
pre-grill（人机循环：可行性 → 准备清单 → 用户确认）
    ↓
goal-document（生成 Goal 文档 + 完成契约骨架）
    ↓
用户执行 /goal <声明>（无人值守）
    ↓
┌─────────────────────────────────────┐
│  6 固定阶段门禁（gatekeeper）        │
│  1. Intake / 决策编译                │
│  2. Spec + Plan                      │
│  3. 实现                             │
│  4. 验收证据                         │
│  5. Wiki / 合规（wiki-checkpoint）   │
│  6. 完成门（完成契约硬门槛 4/4）      │
└─────────────────────────────────────┘
    ↓ 任一 FAIL
auto-recovery（策略旋转；穷尽 → failures/）
    ↓ 矛盾/缺口
decision-arbiter（不改 PRD 目标）
    ↓
硬门槛全绿 → 可宣布完成
```

**半人工回退（模式 A）：** brainstorming → writing-plans → handoff-prompt 复制到新对话 → 实现 → wiki-checkpoint。全自动优先模式 B（Goal）；模式 A 仅作半人工交接回退。

## 三层 Wiki 规则化（仍保留）

Agent 在声称完成前必须通过 wiki 合规。三层机制：

| 层级 | 机制 | 文件 | 说明 |
|------|------|------|------|
| 第一层 | 核心规则 | `superpowers-zh.md` | 「Wiki 优先」注入会话 |
| 第二层 | 强化规则 | `AGENTS.md` | 进入规则、必读清单、变更→更新表 |
| 第三层 | 合规检查 | `wiki-checkpoint` | 读/写合规报告；**完成门前必须通过**；全自动时报告路径写入完成契约证据 |

## Agent 角色

| 角色 | 职责 | 主读 | 主写 / 主产出 |
|------|------|------|--------------|
| **Pre-grill / 启动准备** | PRD 可行性、准备清单、触发 Goal | PRD、wiki README/L1/P1/L6 | 可行性结论、准备清单、触发 `goal-document` |
| **Goal 执行 Agent** | `/goal` 无人值守；过 6 门；契约与恢复 | Goal 文档、完成契约、wiki 路线图 | 代码、证据、gates/、contracts/、failures/ |
| **方案设计 Agent** | 讨论方向，产出 spec/plan（半人工） | P1-产品决策日志 | P1、spec、plan、handoff 模式 A |
| **项目搭建 Agent** | 按 handoff 模式 A 执行开发 | wiki 路线图（按需） | L1/L3/L4A/L4B/L5/L6、代码 |
| **框架讨论 Agent** | 优化框架本身 | P3-框架演进 | P3-框架演进 |
| **门禁 / 仲裁 / 恢复** | 独立校验、补洞、策略旋转 | 契约、Goal、PRD、检查表 | gate 报告、仲裁记录、失败报告 |

详见 [ROLES.md](ROLES.md)（经典三角色定义仍适用；上表为全自动扩展视图）。

## 快速开始

### 方式一：全自动（推荐）

1. 准备 PRD（可参考 `examples/mvp-backend-prd.md`）
2. 加载 `pre-grill` → 完成可行性与准备清单确认  
3. 确认 Goal 文档后执行：

```text
/goal 根据 Goal 文档 docs/superpowers/goals/YYYY-MM-DD-<topic>-goal.md 无人值守完成：{声明}
```

建议 `goals.max_turns` ≥ 100；运行期不跳门禁；失败看 `docs/superpowers/failures/`。

### 方式二：安装优化包 skills

将 `skills/` 下所需 skill 复制到项目 skill 目录（如 `.trae/skills/`），并按 `GUIDE.md` 修改框架文件：

```bash
cp -r skills/* .trae/skills/
# 或按需挑选：pre-grill goal-document completion-contract gatekeeper
#            auto-recovery decision-arbiter project-wiki handoff-prompt wiki-checkpoint
```

### 方式三：半人工 handoff（回退）

```bash
cp -r skills/project-wiki skills/handoff-prompt skills/wiki-checkpoint .trae/skills/
```

方案设计完成后用 `handoff-prompt` **模式 A** 生成 7 步启动提示词，复制到新对话。

## 目录结构

```
superpowers-optimization-kit/
├── README.md                 # 你正在读的这份
├── GUIDE.md                  # Agent 执行指南
├── ROLES.md                  # Agent 角色定义
├── LICENSE                   # MIT
├── templates/                # 全自动产物模板
│   ├── goal-document.md
│   ├── completion-contract.md
│   ├── gate-report.md
│   └── failure-report.md
├── examples/                 # MVP 样例
│   ├── mvp-backend-prd.md
│   └── mvp-goal-document.md
└── skills/
    ├── superpowers-optimizer/  # 安装入口（经典优化）
    ├── project-wiki/           # Wiki 项目手册构建器
    ├── handoff-prompt/         # 模式 A 启动提示词 + 模式 B Goal 启动卡
    ├── wiki-checkpoint/        # Wiki 合规检查点（完成门前必过）
    ├── pre-grill/              # PRD 可行性与 Goal 启动准备
    ├── goal-document/          # Goal 文档 + 契约骨架
    ├── completion-contract/    # 完成契约活文档与硬门槛
    ├── gatekeeper/             # 6 阶段独立门禁
    ├── auto-recovery/          # 门禁 FAIL 策略旋转
    └── decision-arbiter/       # PRD 缺口/矛盾仲裁
```

## 文档阅读指南

| 你想做什么 | 读什么 |
|----------|--------|
| 快速了解本包 | 本 README |
| 理解角色 | [ROLES.md](ROLES.md) |
| 安装/改框架文件 | [GUIDE.md](GUIDE.md) 或 `superpowers-optimizer` |
| 开跑前可行性 | [skills/pre-grill/SKILL.md](skills/pre-grill/SKILL.md) |
| 写 Goal / `/goal` | [skills/goal-document/SKILL.md](skills/goal-document/SKILL.md) |
| 完成契约硬门槛 | [skills/completion-contract/SKILL.md](skills/completion-contract/SKILL.md) |
| 阶段门禁 | [skills/gatekeeper/SKILL.md](skills/gatekeeper/SKILL.md) |
| 失败恢复 | [skills/auto-recovery/SKILL.md](skills/auto-recovery/SKILL.md) |
| 决策仲裁 | [skills/decision-arbiter/SKILL.md](skills/decision-arbiter/SKILL.md) |
| 半人工交接 | [skills/handoff-prompt/SKILL.md](skills/handoff-prompt/SKILL.md) |
| Wiki 合规 | [skills/wiki-checkpoint/SKILL.md](skills/wiki-checkpoint/SKILL.md) |
| 模板与样例 | `templates/`、`examples/` |

## 扩展

发现新的工作流痛点时：

1. 在 `skills/` 新增 skill（对齐现有 frontmatter 与红线风格）
2. 需要固定产物格式时，同步加 `templates/`
3. 更新本 README 的能力表、目录结构与阅读指南
4. 更新 `GUIDE.md` / `superpowers-optimizer`（若涉及安装步骤）
5. 更新 ROLES.md（若职责变化）
6. 提交 PR

## 许可证

MIT — 详见 [LICENSE](LICENSE)
