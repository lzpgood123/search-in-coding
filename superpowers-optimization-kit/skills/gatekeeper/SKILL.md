---
name: gatekeeper
description: Use at every fixed stage gate in the full-auto workflow. Spawns an independent gate-check via delegate_task; the executing agent must not self-approve.
---

# Gatekeeper — 阶段门禁校验

## 概述

在全自动工作流的**固定阶段边界**派出独立门禁 Agent，按检查表判定 PASS / FAIL。

**硬规则：**

1. **执行 Agent 不得自检放行** — 必须通过 `delegate_task` 派独立子 Agent 校验
2. **仅当**子 Agent 返回 `PASS` **且**门禁报告文件存在，才可进入下一阶段
3. **FAIL 则必须调用 `auto-recovery`**，不得跳过、不得自降门槛、不得改写检查表来强行通过
4. 报告写到 `docs/superpowers/gates/{YYYY-MM-DD}-{stage}.md`（格式对齐 `templates/gate-report.md`）

## 何时使用

- 全自动工作流每个固定阶段结束时（6 门）
- Goal 文档 / 完成契约推进到下一阶段前
- 用户或执行 Agent 声称「某阶段已完成」时

**不适用：**

- 阶段内部的小步自检（那是实现过程，不是阶段门）
- Goal 模式最终完成判定（那是 goal judge；本 skill 管阶段门，不替代 judge）

## MVP 说明（Phase 0）

**Phase 0：** Intake + 完成门 可详写、优先跑通；其余四门（Spec+Plan / 实现 / 验收证据 / Wiki合规）的检查表**必须存在且可用**，不得缺门。

- Phase 0 最小闭环：Intake 门禁 → … → 完成门
- Phase 1：全 6 门按检查表严格执行
- 即使当前任务只重点验收两门，结构上仍须保留完整 6 阶段检查表

## 6 阶段固定门禁

阶段顺序固定，不可重排、不可合并放行：

```
Intake / 决策编译
  → Spec + Plan
  → 实现
  → 验收证据
  → Wiki / 合规
  → 完成门
```

---

### 阶段 1：Intake / 决策编译

**stage 标识：** `intake`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | PRD 目标全部进入契约 | 完成契约「PRD 目标清单」覆盖 PRD 全部目标；无遗漏 |
| 2 | 验收场景覆盖 | 每个 PRD 目标至少对应 1 条验收场景 |
| 3 | 决策矩阵无未处理矛盾 | 无 open 矛盾；无 low/conflict 未处理项（MVP 可简化为「无 open 矛盾」） |
| 4 | 验收场景已冻结 | 契约中场景标记为已冻结；后续禁止删除/降级 |

**必读材料：** PRD、Goal 文档、完成契约、相关 P1/wiki（如有）

**PASS 条件：** 上表全部通过  
**FAIL 动作：** 调用 `auto-recovery`，不得进入 Spec+Plan

---

### 阶段 2：Spec + Plan

**stage 标识：** `spec-plan`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | spec 路径存在 | 设计/规格文档路径真实存在 |
| 2 | spec 覆盖 PRD 目标 | 文档内容覆盖契约中的 PRD 目标清单 |
| 3 | plan 路径存在 | 实现计划路径真实存在 |
| 4 | plan 步骤可执行 | 步骤可操作、可验证，非空泛描述 |
| 5 | 无不可改边界冲突 | 与 Goal 文档「不可改边界」无冲突 |

**PASS 条件：** 上表全部通过  
**FAIL 动作：** 调用 `auto-recovery`，不得进入实现

---

### 阶段 3：实现

**stage 标识：** `implement`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | plan 步骤完成 | plan 中本阶段步骤均已完成或有明确跳过理由（且不违反边界） |
| 2 | 测试命令真实输出 | 存在真实命令输出/日志；禁止「应当能过」的口头宣称 |
| 3 | 无新增 open 冲突 | 完成契约「未决项」无新增 open 冲突 |

**PASS 条件：** 上表全部通过  
**FAIL 动作：** 调用 `auto-recovery`，不得进入验收证据门

---

### 阶段 4：验收证据

**stage 标识：** `evidence`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | 每条场景有证据文件 | 完成契约每条验收场景均有可定位的证据路径 |
| 2 | 证据类型符合任务 | 前端/后端/运维等类型与场景要求匹配（截图、日志、API 响应、命令输出等） |
| 3 | 证据可复核 | 证据文件存在且内容能支撑「场景通过」结论 |

**PASS 条件：** 上表全部通过  
**FAIL 动作：** 调用 `auto-recovery`，不得进入 Wiki/合规门

---

### 阶段 5：Wiki / 合规

**stage 标识：** `wiki`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | 应更新的 wiki 已更新 | 按变更类型更新对应 L/P 文档（见 `wiki-checkpoint`） |
| 2 | wiki-checkpoint 报告通过 | 读合规 + 写合规总体通过 |

**PASS 条件：** 上表全部通过  
**FAIL 动作：** 调用 `auto-recovery`，不得进入完成门

---

### 阶段 6：完成门

**stage 标识：** `completion`

| # | 检查项 | 判定标准 |
|---|--------|----------|
| 1 | 硬门槛 1 | PRD 目标全部覆盖 |
| 2 | 硬门槛 2 | 验收场景全部有实测证据 |
| 3 | 硬门槛 3 | 无未决冲突 |
| 4 | 硬门槛 4 | Wiki/检查点合规 |
| 5 | 宣布完成标记 | 完成契约 `可否宣布完成=是`（且仅当 1–4 全绿） |

**PASS 条件：** 硬门槛 4/4 且 `可否宣布完成=是`  
**FAIL 动作：** 调用 `auto-recovery`；**禁止**在未全绿时宣布任务完成

---

## 强制：`delegate_task` 调用模板

执行 Agent **必须**按下列模板派出独立门禁 Agent，**禁止**自己对照检查表勾选后放行。

```text
delegate_task(
  goal="作为独立门禁校验 Agent，检查阶段 {STAGE} 是否通过",
  context="""
  项目根：{ROOT}
  完成契约：{CONTRACT_PATH}
  Goal 文档：{GOAL_PATH}
  PRD：{PRD_PATH}
  本阶段：{STAGE}
  必读：gatekeeper skill 中该阶段检查表
  输出：按 templates/gate-report.md 写到 docs/superpowers/gates/{date}-{stage}.md
  返回：PASS 或 FAIL + 原因列表
  """
)
```

### 占位符

| 占位符 | 含义 | 示例 |
|--------|------|------|
| `{STAGE}` | 阶段标识 | `intake` / `spec-plan` / `implement` / `evidence` / `wiki` / `completion` |
| `{ROOT}` | 项目根绝对路径 | `/root/workspace/agent-ecoradar` |
| `{CONTRACT_PATH}` | 完成契约路径 | `docs/superpowers/contracts/...` |
| `{GOAL_PATH}` | Goal 文档路径 | `docs/superpowers/goals/...` |
| `{PRD_PATH}` | PRD 路径 | 用户提供或 examples 中的 PRD |
| `{date}` | 报告日期 | `2026-07-19` |
| `{stage}` | 报告文件名中的阶段段 | 与 `{STAGE}` 相同 |

### 放行规则（不可协商）

1. 调用 `delegate_task` 派出**独立**子 Agent（门禁 Agent ≠ 执行 Agent）
2. 子 Agent 按本 skill 对应阶段检查表逐项判定，并写入门禁报告
3. **仅当**同时满足：
   - 子 Agent 返回结果为 **PASS**
   - 报告文件存在于 `docs/superpowers/gates/`
   - 报告内检查项与结论一致  
   → 才允许进入下一阶段
4. 若返回 **FAIL**：
   - **必须**加载并执行 `auto-recovery`
   - **不得**跳过本门禁
   - **不得**由执行 Agent 改判为 PASS
   - **不得**删除/降级已冻结验收场景来制造假绿
5. 重试后再次过门：仍须重新 `delegate_task`，上一轮 FAIL 报告保留作审计

## 门禁报告要求

路径：`docs/superpowers/gates/{YYYY-MM-DD}-{stage}.md`

结构对齐 `templates/gate-report.md`：

```markdown
# 门禁报告：{阶段名}

- 任务：
- 时间：
- 校验 Agent：delegate_task 子 Agent
- 结果：PASS / FAIL

## 检查项
| # | 检查 | 结果 | 证据 |
|---|------|------|------|

## 失败原因（如有）
## 建议修复策略（如有）
```

目录不存在则先创建 `docs/superpowers/gates/`。

## 与相关 skill 的关系

| Skill | 关系 |
|-------|------|
| `completion-contract` | 契约是门禁的主要数据源；完成门读硬门槛 |
| `auto-recovery` | 任一阶段 FAIL 后的唯一合法去向 |
| `decision-arbiter` | 矛盾/缺口类失败由 recovery 路由到仲裁（Phase 1） |
| `wiki-checkpoint` | Wiki/合规门的具体读/写检查实现 |
| `goal-document` | 提供阶段流程与不可改边界 |
| `pre-grill` | Intake 前准备；不替代 Intake 门禁 |

## 反模式（禁止）

- 执行 Agent 自写「自检通过」然后进入下一阶段
- 无报告文件却宣称 PASS
- FAIL 后不调用 `auto-recovery` 直接改 plan/降场景
- 把 6 门合成 1 次模糊检查
- Phase 0 以「MVP」为由删除 Spec+Plan / 实现 / 证据 / Wiki 检查表（可简跑，表必须在）

## 快速检查清单（执行 Agent）

- [ ] 当前阶段名称与 stage 标识已确定
- [ ] 已按模板 `delegate_task`（未自检）
- [ ] 子 Agent 返回 PASS 或 FAIL
- [ ] `docs/superpowers/gates/` 下报告已落盘
- [ ] PASS → 更新完成契约阶段 → 进入下一阶段
- [ ] FAIL → 立即 `auto-recovery`，不跳过
