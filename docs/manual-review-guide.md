# Search in Coding 人工审核操作指南

> 适用对象：项目维护者 / 人工审核者。  
> 目标：把自动收集的数据从“可用线索”提升为“可信推荐”，并保证修改后能通过质量门禁、同步到正式站点。

正式站点：<https://coding.lzpgood.online/>  
项目目录：`/root/workspace/search in coding`

---

## 1. 你为什么需要人工审核

自动流程每天会从 GitHub 和 Exa 收集 AI Coding Agent 生态资料，但自动评分不能完全判断：

- 项目是否真的有用；
- 是否只是标题相关但内容无关；
- 是否已经废弃；
- 是否适合推荐给用户尝试；
- 是否应该作为“参考资料”而不是“生态项目”；
- 是否应该进入 rejected/noisy 数据集。

人工审核的核心价值是：

> 把自动抓来的项目，变成有判断力的 curated 榜单。

---

## 2. 每次人工审核先看哪些文件

建议按这个顺序看。

### 2.1 Top 20 精修报告

```text
docs/reports/curated-top-20-review.md
```

这是最适合你每周看的入口。它包含：

- Top 20 项目；
- URL；
- 当前分数；
- 当前推荐等级；
- 中文短评；
- 关联工具；
- 分类。

你的主要工作是判断这些项目：

- 是否真的值得推荐；
- 是否需要降级；
- 是否要移出 curated；
- 是否需要补充中文评价。

### 2.2 Curated 数据集

```text
data/curated-projects.yaml
```

这是正式推荐池。里面每条记录都应该是高信号项目或资料。

### 2.3 Rejected 数据集

```text
data/rejected-projects.yaml
```

这是噪声、低相关、重复、低可信记录。

### 2.4 Source Quality 审计

```text
docs/reports/source-quality-audit.md
```

用于确认 fallback-web、Exa、GitHub 的来源质量是否标注正确。

### 2.5 最终报告

```text
docs/reports/final-delivery-report.md
```

用于查看当前数据规模、来源分布、工具覆盖和 Top ecosystem projects。

---

## 3. 推荐等级怎么判断

字段：

```json
"recommendation_level": "try-now"
```

可选值建议如下。

| 等级 | 含义 | 何时使用 |
|---|---|---|
| `try-now` | 立即尝试 | 项目相关性强、可用性高、文档清楚、对 Claude Code / Codex / Cursor / OpenCode / Goose / Hermes 等目标工具有直接价值 |
| `watch` | 值得观察 | 方向有价值，但项目还新、文档不足、成熟度未知 |
| `reference` | 参考资料 | 教程、文章、榜单、生态地图、规则库、经验贴，适合学习但不是工具本身 |
| `experimental` | 实验性 | 有趣但风险高、依赖复杂、维护状态不明 |

### 快速判断法

如果一个项目满足 3 条以上，可以设为 `try-now`：

- GitHub repo 存在且近期更新；
- README 清楚；
- 有安装/使用方式；
- 与目标工具直接相关；
- 可被当前项目用户实践；
- 不只是泛 AI 或泛 prompt；
- 有 stars / forks / issue 活动；
- 来源是 GitHub 或官方文档，而不是低可信 fallback。

如果只是文章或资料，通常设为：

```json
"recommendation_level": "reference"
```

---

## 4. 分类怎么判断

字段：

```json
"category": ["skills-prompts"]
```

常用分类：

| 分类 | 含义 |
|---|---|
| `skills-prompts` | Claude Skills、agent skills、prompt packs、slash commands 等 |
| `rules-instructions` | AGENTS.md、CLAUDE.md、Cursor rules、项目规则、指令模板 |
| `mcp-acp-a2a` | MCP server、ACP、A2A、工具连接层 |
| `context-engineering` | repo map、代码索引、上下文工程、记忆、RAG |
| `agent-harness` | agent 框架、多 agent 编排、任务执行 harness |
| `testing-review-ci` | PR review、CI、测试生成、自动修复 |
| `tutorial-case-study` | 教程、经验、case study |
| `benchmark-evaluation` | benchmark、评测、对比 |
| `terminal-agent` | 终端型 agent 工具 |
| `ai-ide` | AI IDE / 编辑器 |

一条记录可以有多个分类。

---

## 5. 来源质量怎么判断

字段：

```json
"source_quality": "verified"
```

建议规则：

| source_quality | 含义 |
|---|---|
| `verified` | GitHub repo、官方文档、已确认来源 |
| `fallback` | fallback-web 结果，只能作为线索 |
| `unverified` | 还没核验 |
| `blocked` | 来源不可访问或 API 失败 |

特别注意：

```json
"source_type": "fallback-web"
```

必须同时有：

```json
"source_quality": "fallback"
"tags": ["fallback-not-exa"]
```

fallback-web 不能当成 Exa 结果。

---

## 6. 一条记录应该怎么审核

对每个候选项目，按这个清单操作。

### Step 1：打开 URL

优先看：

- README；
- 最近 commit；
- release；
- issues；
- stars/forks；
- 使用示例；
- 是否和目标工具直接相关。

### Step 2：判断是否保留在 curated

保留条件：

- 与 AI Coding Agent 生态强相关；
- 对至少一个目标工具有价值；
- 不是明显噪声；
- 来源可信；
- 能解释“为什么值得关注”。

移出条件：

- 与 AI Coding 无关；
- 只是关键词碰撞；
- 重复；
- 不可访问；
- 项目过旧且无参考价值；
- 来源低可信且没有补充证据。

### Step 3：更新字段

重点字段：

```json
"review_state": "reviewed"
"recommendation_level": "try-now"
"curation_note": "中文审核理由"
"why_it_matters": "为什么重要"
"category": [...]
"target_tools": [...]
"source_quality": "verified"
"ranking_scope": "ecosystem"
```

### Step 4：必要时移动到 rejected

如果你决定移除，就把记录从：

```text
data/curated-projects.yaml
```

移动到：

```text
data/rejected-projects.yaml
```

并补充：

```json
"review_state": "rejected"
"ranking_scope": "excluded"
"rejection_reason": "中文原因"
```

---

## 7. 你可以让 Hermes 怎么帮你审

你不需要手动改 JSON。可以直接对 Hermes 说：

```text
请人工审核 curated Top 20 中的前 10 个项目。逐个打开 URL，判断是否保留、降级或移入 rejected。请修改 data/curated-projects.yaml 和 data/rejected-projects.yaml，补充中文 curation_note，然后运行质量门禁并部署正式站点。
```

或者更具体：

```text
请审核 JuliusBrussee/caveman、blader/humanizer、alirezarezvani/claude-skills 这三个项目。判断它们是否应该保留 try-now，补充中文审核理由。如果不适合，请降级为 watch 或移入 rejected。完成后运行 python3 scripts/update_tracker.py --skip-collect。
```

如果你只想给判断，不想让 Hermes 自己联网，可以说：

```text
我认为 xxx 项目不适合推荐，请把它从 curated 移到 rejected，原因是：……。然后重建报告和站点。
```

---

## 8. 修改后必须运行哪些命令

进入项目目录：

```bash
cd "/root/workspace/search in coding"
```

推荐运行：

```bash
python3 scripts/update_tracker.py --skip-collect
```

这会自动执行：

- validate；
- score；
- finalize；
- generate reports；
- build site；
- quality gate；
- deploy to `https://coding.lzpgood.online/`。

如果只想检查，不部署：

```bash
python3 scripts/update_tracker.py --skip-collect --skip-deploy
```

单独质量门禁：

```bash
python3 scripts/quality_gate.py
```

正式站点验证：

```bash
curl -I https://coding.lzpgood.online/
```

---

## 9. 人工审核后的 Git 流程

如果修改通过，应提交：

```bash
git status --short
git add data docs site
git commit -m "docs(review): curate ecosystem records"
git push origin main
```

如果是一次正式版本迭代，例如每周/月度审计后，可以更新：

```text
VERSION
CHANGELOG.md
docs/releases/YYYY.MM.DD.md
```

提交：

```bash
git commit -m "release: YYYY.MM.DD tracker update"
```

---

## 10. 每周人工审核建议流程

每周一次，约 30-60 分钟。

### 第 1 步：看 Top 20

打开：

```text
docs/reports/curated-top-20-review.md
```

挑出：

- 5 个最值得试用的；
- 5 个可能是噪声的；
- 3 个需要加深追踪的方向。

### 第 2 步：实际打开 URL 核验

重点看 GitHub repo 的 README 和活跃度。

### 第 3 步：做判断

每个项目只需要做一个动作：

- 保留；
- 升级；
- 降级；
- 移入 rejected；
- 改分类；
- 改关联工具；
- 补中文说明。

### 第 4 步：让 Hermes 改数据

可以直接把你的判断发给 Hermes。

示例：

```text
请按以下审核意见修改 Search in Coding：
1. JuliusBrussee/caveman 保留，但从 try-now 降为 watch，原因是 token 压缩有趣但不是核心 coding agent 能力。
2. alirezarezvani/claude-skills 保留 try-now，补充说明：这是 Claude Skills 生态观察样本。
3. taishi-i/awesome-ChatGPT-repositories 移入 rejected，原因是范围过泛，不是 AI Coding Agent 专项。
修改后运行 update_tracker.py --skip-collect 并提交。
```

### 第 5 步：检查正式站点

打开：

```text
https://coding.lzpgood.online/
```

确认榜单和数据已更新。

---

## 11. 每月人工审核建议流程

每月一次，约 1-2 小时。

重点问题：

1. 目标工具是否要扩展？例如 Windsurf、Aider、Cline、Roo Code、Devin。
2. 分类体系是否要调整？
3. 评分规则是否偏向 stars 过多？
4. Exa 搜索 query 是否需要新增？
5. curated 是否仍然有 50 条以上高质量记录？
6. rejected 里是否有误杀？
7. 是否应该发布新的日期版本？

建议让 Hermes 生成月度审核材料：

```text
请基于 data/curated-projects.yaml、data/rejected-projects.yaml 和 docs/reports/source-quality-audit.md，生成本月人工审核建议，列出应该升级、降级、移除、重新核验的项目各 10 个。
```

---

## 12. 审核判断的优先级

人工审核时，请按这个优先级判断：

1. 与目标工具直接相关性；
2. 是否可实际使用；
3. 来源可信度；
4. 是否代表一个生态趋势；
5. 是否有中文用户价值；
6. stars/forks/活跃度；
7. 是否可复用到 Hermes 自动化。

不要只看 stars。

---

## 13. 常见错误

### 错误 1：把泛 AI 项目放进 curated

如果项目只是“AI 工具大全”，但没有 AI Coding Agent 专项价值，应该降级为 `reference` 或移入 rejected。

### 错误 2：fallback-web 当成已验证事实

fallback-web 只能是线索。要进入 `try-now`，最好有 GitHub、官方文档或实际试用证据。

### 错误 3：官方工具混入 ecosystem 榜

Claude Code、Codex、Cursor 等官方目标工具应该在 official 区域，不应该进入 ecosystem ranking。

### 错误 4：只改 curated，不跑质量门禁

任何人工修改后都必须跑：

```bash
python3 scripts/update_tracker.py --skip-collect
```

---

## 14. 最小人工审核模板

你可以每次只填这个模板，然后交给 Hermes 执行：

```text
请按以下人工审核意见修改 Search in Coding：

保留：
- 项目：
  原因：
  推荐等级：

降级：
- 项目：
  从：
  到：
  原因：

移入 rejected：
- 项目：
  原因：

改分类：
- 项目：
  新分类：
  原因：

改关联工具：
- 项目：
  新 target_tools：
  原因：

执行要求：
1. 修改 data/curated-projects.yaml / data/rejected-projects.yaml / data/projects.yaml。
2. 运行 python3 scripts/update_tracker.py --skip-collect。
3. 确认 https://coding.lzpgood.online/ 正常。
4. 提交并推送。
```

---

## 15. 人工审核完成的定义

一次人工审核完成，必须满足：

- 你的审核意见已反映到数据；
- `quality_gate.py` 通过；
- 正式站点已部署；
- Git 已提交推送；
- 如果是重要审核，已更新报告或版本说明。

最终检查：

```bash
git status --short
python3 scripts/quality_gate.py
curl -I https://coding.lzpgood.online/
```
