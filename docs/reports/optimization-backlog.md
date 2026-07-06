# Search in Coding 全流程优化清单

> 生成日期：2026-07-06  
> 范围：采集、归一化、评分、报告、站点、双语、GitHub 总仓库、Actions、Hermes cron、正式部署。

正式站点：<https://coding.lzpgood.online/>  
GitHub 总仓库：<https://github.com/lzpgood123/search-in-coding>

---

## 1. 当前体检结论

项目已经具备完整闭环：

- GitHub / Exa 采集可用；
- 数据归一化、评分、auto curated/rejected 可用；
- 报告生成可用；
- 站点构建和正式 Nginx 部署可用；
- GitHub 作为 source of truth 的流程已建立；
- GitHub Actions 与 Hermes cron 均已运行；
- 中文 / English UI 切换已上线；
- 质量门禁通过。

本次验证结果：

```text
projects: 618
curated: 60
rejected: 25
github_verified: 264
non_github: 354
quality_gate: PASS
site: https://coding.lzpgood.online/ HTTP/2 200
site missing i18n: 0
```

但项目仍有一批“从可运行到高质量产品”的优化空间，主要集中在：

1. 双语内容还只是结构化 fallback，不是真正翻译；
2. 数据层 `data/projects.yaml` 尚未持久化 i18n 字段，只有 site 构建时补齐；
3. 自动评分规则偏粗，分类过度集中；
4. GitHub Actions/服务器 cron 职责仍需进一步硬化；
5. 站点功能仍偏基础，缺少详情页、趋势图、搜索体验；
6. raw 数据长期直接入 Git 可能导致仓库膨胀；
7. 报告仍是静态摘要，缺少“变化检测”和“新旧对比”；
8. 缺少自动测试覆盖，主要靠脚本运行验证。

---

## 2. 关键体检数据

### 数据规模

```text
projects: 618
curated: 60
rejected: 25
duplicate_urls: 5
missing_summary: 0
missing_i18n in data/projects.yaml: 618
missing_i18n in site/data/projects.json: 0
```

解释：

- 站点数据已有 `i18n.zh/en`；
- 但源数据 `data/projects.yaml` 还没有持久化 `i18n`；
- 当前双语字段是在 `build_site.py` 中生成的。

### 来源分布

```text
github: 264
exa: 197
fallback-web: 147
official-seed: 10
```

### 分类分布 Top 10

```text
agent-harness: 363
testing-review-ci: 357
skills-prompts: 195
mcp-acp-a2a: 162
rules-instructions: 135
context-engineering: 108
terminal-agent: 37
benchmark-evaluation: 31
tutorial-case-study: 24
official-tool: 10
```

风险：`agent-harness` 和 `testing-review-ci` 偏高，说明分类规则可能过宽。

### review_state 分布

```text
auto-reviewed: 70
unreviewed: 523
auto-rejected: 25
```

说明：当前不再人工审核，`unreviewed` 可以接受，但命名上容易误解为“待人工处理”。建议改成 `auto-indexed`。

---

## 3. P0：必须优先修复

### P0-1：把 i18n 字段持久化到 `data/projects.yaml`

**问题**  
当前站点构建时能生成 `i18n.zh/en`，但源数据 `data/projects.yaml` 仍缺少 `i18n` 字段。长期看，GitHub 总仓库作为 source of truth 时，应保存双语展示结构，而不是只在构建产物里临时补齐。

**影响**

- GitHub 数据本身不是完整双语结构；
- 后续如果要引入翻译/摘要增强，需要再回填；
- 外部用户直接读取 `data/projects.yaml` 时看不到双语结构。

**建议**

- 新增 `scripts/enrich_i18n.py`；
- 在 `update_tracker.py` 中 `normalize -> score` 之间执行；
- 对所有项目补齐：

```json
"i18n": {
  "zh": {"name": "...", "summary": "..."},
  "en": {"name": "...", "summary": "..."}
}
```

**验收**

```bash
python3 scripts/enrich_i18n.py
python3 scripts/quality_gate.py
```

并确认：

```text
missing_i18n in data/projects.yaml = 0
```

---

### P0-2：GitHub Actions 与服务器部署职责进一步隔离

**问题**  
目前已给 GitHub Actions 加了 `--skip-deploy`，这是正确的。但 `update_tracker.py` 默认部署，GitHub workflow 依赖调用者记得加参数。

**影响**

- 后续新增 workflow 时可能误触发服务器部署逻辑；
- GitHub runner 没有 `/var/www`，误运行会失败。

**建议**

- `update_tracker.py` 默认不部署；
- 服务器 cron 显式传 `--deploy`；
- 或根据环境变量 `SEARCH_IN_CODING_DEPLOY=1` 才部署。

推荐改为：

```bash
python3 scripts/update_tracker.py --deploy
```

GitHub Actions 使用默认不部署。

**验收**

- GitHub Actions 无需 `--skip-deploy` 也不部署；
- 服务器 cron 显式部署；
- 正式站点仍更新。

---

### P0-3：修正 review_state 命名，避免“待人工审核”误解

**问题**  
项目已取消人工审核，但 523 条记录仍是：

```text
unreviewed
```

这容易让读者误以为需要人工审核。

**建议**

改为自动维护语义：

```text
auto-indexed
auto-curated
auto-rejected
```

或者：

```text
indexed
recommended
excluded
```

**验收**

- 数据与站点筛选器不再使用 `unreviewed`；
- README/报告里解释自动状态；
- quality gate 支持新状态。

---

## 4. P1：强烈建议优化

### P1-1：分类规则过宽，需要升级为多阶段分类

**问题**  
`agent-harness` 和 `testing-review-ci` 记录过多，说明 keyword matching 太粗。

当前 `normalize.py` 里类似：

```python
('agent', 'agent-harness')
('review', 'testing-review-ci')
```

这会把大量只出现 agent/review 字样的记录误分类。

**建议**

改成多阶段：

1. keyword 初筛；
2. source type 加权；
3. URL / repo name 加权；
4. summary 规则；
5. 冲突分类修正。

例如：

- `agent-harness` 需要出现 `agent framework`、`multi-agent`、`orchestration`、`harness` 等组合；
- `testing-review-ci` 需要出现 `pull request`、`code review`、`CI`、`test generation` 等更明确词组。

**验收**

- `agent-harness` 占比下降；
- Top curated 项目分类更准确；
- `tool-ecosystem-comparison.md` 更可信。

---

### P1-2：评分模型需要拆分为可解释配置

**问题**  
评分逻辑分散在 `score.py` 和 `finalize_data.py`，权重写死，难以调整方向。

**建议**

新增：

```text
config/scoring.yaml
```

包含：

- source weights；
- category weights；
- freshness weights；
- stars/forks 权重；
- fallback 惩罚；
- target tool priority。

**验收**

- 不改代码也能调整权重；
- 报告输出评分解释；
- README 说明评分机制。

---

### P1-3：报告缺少“变化检测”

**问题**  
当前报告展示当前状态，但缺少：

- 本次新增了什么；
- 哪些项目分数上升/下降；
- 哪些项目进入/退出 curated；
- 哪些工具生态变化明显。

**建议**

保存快照：

```text
data/snapshots/YYYY-MM-DD/projects.json
```

生成 diff 报告：

```text
docs/reports/weekly/YYYY-MM-DD-weekly-update.md
```

包含：

- new records；
- removed records；
- newly curated；
- newly rejected；
- score changes；
- tool coverage changes。

**验收**

每周报告不只是总览，而能回答：

> 这周生态发生了什么变化？

---

### P1-4：站点需要详情页或展开面板

**问题**  
当前站点只有表格：名称、摘要、来源、质量、分类、工具、分数、链接。对于 600+ 记录，信息密度不够。

**建议**

增加点击展开：

- why_it_matters；
- score breakdown；
- first_seen / last_seen；
- record_kind；
- recommendation_level；
- notes / Exa highlights；
- raw source link。

**验收**

用户不用打开 JSON，也能理解为什么这个项目被推荐。

---

### P1-5：双语需要从“结构双语”升级到“内容双语”

**问题**  
目前 UI 双语已完成，数据有 `i18n.zh/en` 结构，但项目摘要本身多数仍是来源语言复制。

**建议**

增加可选 enrichment：

```text
scripts/enrich_translations.py
```

策略：

- 英文来源生成中文摘要；
- 中文来源生成英文摘要；
- 保留原文；
- 标记 `translation_state: auto-generated`。

**验收**

- Top 60 curated 至少有真实中英摘要；
- 站点切换 English 时不是中文说明；
- 切换中文时英文项目有中文摘要。

---

## 5. P2：中期增强

### P2-1：仓库体积治理

**问题**  
`data/raw/` 每天写入 Git，长期可能膨胀。

**建议**

- 保留最近 N 天 raw；
- 月度归档压缩到 release asset；
- 或用 Git LFS / GitHub Releases 存大快照。

**验收**

- 仓库 clone 保持轻量；
- raw 仍可追溯。

---

### P2-2：GitHub topics 为空

**问题**  
仓库 topics 当前为空，不利于 GitHub 搜索发现。

**建议 topics**

```text
ai-coding
coding-agent
agentic-coding
mcp
claude-code
codex
cursor
opencode
hermes-agent
ecosystem-tracker
```

**验收**

```bash
gh repo view --json repositoryTopics
```

显示 topics。

---

### P2-3：GitHub Pages 有一次历史失败记录

**问题**  
最近成功，但 run list 仍显示一次历史 failure。不是 blocker，但会影响观感。

**建议**

- 可忽略；
- 或在 README 中只显示当前 badge；
- 后续如果失败频繁，改为 Pages 预览可选，不作为主链路。

---

### P2-4：增加 tests 目录

**问题**  
目前靠脚本运行验证，没有正式测试集。

**建议**

新增：

```text
tests/test_data_integrity.py
tests/test_scoring.py
tests/test_i18n.py
tests/test_site_build.py
```

GitHub Actions 中运行：

```bash
python3 -m pytest
```

**验收**

- 数据字段变更有测试保护；
- 双语字段缺失会失败；
- scoring 规则更安全。

---

### P2-5：站点搜索体验增强

建议：

- 支持 URL 参数保存筛选状态；
- 支持按 score/source/tool/category 排序；
- 支持一键复制项目链接；
- 支持只看最近新增；
- 支持移动端卡片视图。

---

## 6. P3：高级方向

### P3-1：引入 Embedding / 相似项目去重

当前有 5 个 duplicate URL，但更大的问题是语义重复。可用 embedding 或简单相似度进行去重。

### P3-2：发布数据包 / API

可以从 GitHub Pages 或正式站点暴露：

```text
/data/projects.json
/data/curated-projects.json
/data/metrics.json
```

进一步可以发布 npm/pip 包或 Docker 镜像，但现在不是必须。

### P3-3：多生态复用模板

把当前项目抽象成模板：

```text
ecosystem-tracker-template
```

用于其他领域：MCP 生态、AI IDE 生态、Agent framework 生态、国内 AI 工具生态等。

---

## 7. 推荐执行顺序

### 第一批：稳定性和数据源可信度

1. P0-1：持久化 i18n 到 `data/projects.yaml`。
2. P0-2：改成默认不部署，服务器显式 `--deploy`。
3. P0-3：review_state 改名为自动维护语义。
4. P1-1：分类规则收紧。
5. P1-2：评分配置外置。

### 第二批：产品体验

6. P1-3：周报变化检测。
7. P1-4：站点详情展开。
8. P1-5：Top curated 真双语摘要。
9. P2-5：搜索/筛选体验增强。

### 第三批：长期运营

10. P2-1：仓库体积治理。
11. P2-2：补 GitHub topics。
12. P2-4：正式测试集。
13. P3-1：语义去重。
14. P3-3：模板化复用。

---

## 8. 可以立即执行的下一步提示词

如果要开始优化，建议直接执行第一批：

```text
请按 docs/reports/optimization-backlog.md 的第一批优化执行：
1. 持久化 i18n 到 data/projects.yaml；
2. update_tracker 默认不部署，服务器 cron 显式 --deploy；
3. 将 review_state 改成 auto-indexed / auto-curated / auto-rejected；
4. 收紧分类规则；
5. 将评分权重外置到 config/scoring.yaml。
完成后运行完整验证、部署正式站点、提交并推送。
```
---

## 9. 第一批优化执行结果 — 2026-07-06

本轮 Goal 执行已完成第一批优化：

- `data/projects.yaml`、`data/curated-projects.yaml`、`data/rejected-projects.yaml` 已持久化 `i18n.zh/en`。
- `scripts/update_tracker.py` 已改为默认不部署，只有显式 `--deploy` 才同步到 `/var/www/coding.lzpgood.online`。
- Hermes daily / weekly cron 已更新为显式 `--deploy`。
- `review_state` 已改为自动维护语义：`auto-indexed` / `auto-curated` / `auto-rejected`。
- `scripts/normalize.py` 已收紧分类规则，避免仅凭 `agent` / `review` 过度归类。
- 新增 `config/scoring.yaml`，`scripts/score.py` 与 `scripts/finalize_data.py` 已读取配置。
- `scripts/quality_gate.py` 已增加 i18n、review_state、scoring config 等检查。

执行后关键指标：

```text
missing_i18n in data/projects.yaml: 0
review_state: auto-curated=70, auto-indexed=523, auto-rejected=25
agent-harness: 62
testing-review-ci: 56
quality_gate: PASS
production deploy: PASS
```

剩余下一批建议：

1. 增加 weekly diff / change detection。
2. 增加站点详情展开面板。
3. 对 Top curated 做真实中英摘要增强。
4. 增加 pytest 测试集。
5. 设计 raw 数据归档策略。
---

## 10. 剩余优化完成结果 — 2026-07-06

本轮已继续完成优化清单剩余主要项目：

- P1-3：新增 `scripts/snapshot_and_diff.py`，生成 `data/snapshots/` 与 `docs/reports/weekly/` 变化报告。
- P1-4 / P2-5：站点增加详情展开、排序、URL 筛选状态、复制链接、最近新增筛选。
- P1-5：新增 `scripts/enrich_translations.py`，对 Top curated 生成规则化中英摘要并标记 `translation_state=rule-generated`。
- P2-1：新增 `scripts/archive_raw.py` 与 `docs/raw-data-retention.md`，提供 raw 归档策略。
- P2-2：GitHub topics 已设置。
- P2-4：新增 pytest 测试集并接入 GitHub Actions。
- P3-2：新增 `docs/data-api.md`，说明静态 JSON 数据 API。
- P3-3：新增 `docs/ecosystem-tracker-template.md`，说明模板化复用方式。

仍属未来增强的方向：

- 使用真实 LLM/人工校订翻译替代规则化摘要。
- 使用 embedding 做更强语义去重。
- 将大型 raw archive 移到 GitHub Release assets。
