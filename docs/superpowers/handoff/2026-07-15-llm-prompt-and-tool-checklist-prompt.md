# 新对话 Agent 启动提示词：LLM Prompt 扩展 + 新工具 Checklist 文档

> 将以下全部内容复制粘贴到**新对话**中作为第一条消息。  
> 本任务是**后端 prompt 优化 + 文档编写批次**，不是前端改动，不是重跑采集/评分。  
> 设计规格：`docs/superpowers/specs/2026-07-15-frontend-polish-design.md`（决策 3 + 决策 6）

---

## 你的任务

你是 "Search in Coding" 项目的开发 Agent。需要完成 2 个任务：

1. **LLM Summary 扩展到 2-3 句话**：修改 `llm_prompts.py` 的 prompt，从"一句话评价"改为"2-3 句话：是什么 + 核心功能 + 适合谁用"
2. **添加新工具 checklist 文档**：写 `docs/add-new-tool-checklist.md`，覆盖从定义到上线的完整流程

**关键约束：不改评分逻辑、不改 schema、只改 prompt 文本**

---

## 第一步：加载技能框架

1. 优先 `skill_view("hermes-agent")` 了解工作流
2. 改代码前：相关逻辑用最小回归命令验证
3. 完成前：先有命令输出证据再声称完成

---

## 第二步：阅读上下文（只读）

必读：

1. `docs/superpowers/specs/2026-07-15-frontend-polish-design.md` — **本任务设计规格（决策 3 + 决策 6）**
2. `scripts/llm_prompts.py` — **prompt 模板（重点 `project_analysis_prompt()` L28-84）**
3. `scripts/weekly_analysis.py` — LLM 分析执行脚本（了解如何调用 prompt、如何测试）
4. `data/seed-tools.yaml` — 现有工具定义结构（写 checklist 时参考字段）
5. `config/llm-analysis.yaml` — LLM 分析配置（了解 schema 约束）
6. `scripts/collect_github.py` — 采集脚本（checklist 步骤 2 参考）
7. `scripts/normalize.py` — 归一化脚本（checklist 步骤 3 参考）
8. `scripts/score.py` — 评分脚本（checklist 步骤 4 参考）
9. `scripts/build_site.py` — 构建脚本（checklist 步骤 5 参考）
10. `scripts/quality_gate.py` — 质量门禁（checklist 步骤 6 参考）

工作区：`/root/workspace/search in coding`

---

## 第三步：任务 1 — LLM Summary 扩展到 2-3 句话

### 目标

`scripts/llm_prompts.py` 的 `project_analysis_prompt()`（L28-84）中，`llm_summary` 字段当前要求"一句话中文评价" / "one sentence English summary"。改为 2-3 句话，结构为：**项目是什么 + 核心功能 + 适合谁用**。

### 当前 prompt 中的 llm_summary 字段（L69-72）

```python
  "llm_summary": {{
    "zh": "一句话中文评价",
    "en": "one sentence English summary"
  }},
```

### 改动

**`scripts/llm_prompts.py`** — `project_analysis_prompt()` 函数：

1. **修改 `llm_summary` 字段说明**（L69-72 区域）：

改为：
```python
  "llm_summary": {{
    "zh": "2-3 句话中文评价，包含：项目是什么、核心功能、适合谁用",
    "en": "2-3 sentence English summary: what it is, core features, who it's for"
  }},
```

2. **修改 prompt 末尾的 scoring guidelines 或补充说明**（L76-84 区域之后）：

在 scoring guidelines 之后、prompt 结尾之前，追加 llm_summary 的写作指引：

```python
- llm_summary: 2-3 句话评价。第一句说明项目是什么，第二句描述核心功能，第三句指出适合谁用。
  示例（中文）："AgentKit 是一个用于构建 AI Agent 的开源框架。提供工具调用、记忆管理、多步推理等核心能力，适合需要快速搭建定制化 Agent 的开发者。"
  示例（英文）："AgentKit is an open-source framework for building AI agents. It provides tool calling, memory management, and multi-step reasoning, suitable for developers who need to quickly build custom agents."
```

3. **不改其他字段**：
   - `relevance_score`（L58）— 不变
   - `resource_type`（L59）— 不变
   - `target_tools`（L60）— 不变
   - `tracking_priority`（L61）— 不变
   - `quality_score`（L62）— 不变
   - `quality_detail`（L63-68）— 不变
   - `analysis_notes`（L73）— 不变
   - scoring guidelines（L76-84）— 不变，只追加 llm_summary 指引

4. **不改其他函数**：
   - `benchmark_selection_prompt()`（L89-125）— 不变
   - `weekly_report_prompt()`（L130-163）— 不变
   - `tool_comparison_prompt()`（L166-187）— 不变
   - `top_picks_prompt()`（L190-209）— 不变
   - `ANALYSIS_SYSTEM`（L13-16）— 不变

### 测试

改完后对 3-5 个项目测试分析效果：

```bash
cd "/root/workspace/search in coding"

# 查看 weekly_analysis.py 的用法
python3 scripts/weekly_analysis.py --help

# 对 3-5 个项目运行分析（具体命令以 weekly_analysis.py 实际参数为准）
# 可能类似：
python3 scripts/weekly_analysis.py --max-projects 5

# 或指定单个项目测试（如果有单项目分析入口）
# 检查输出 JSON 中 llm_summary 字段是否为 2-3 句话
```

验证输出：
- `llm_summary.zh` 为 2-3 句话
- 结构包含"是什么 + 核心功能 + 适合谁用"
- `llm_summary.en` 为 2-3 句话（英文对应）
- 其他字段（`relevance_score`、`quality_score`、`quality_detail` 等）格式不变

### 验收
- `project_analysis_prompt()` 的 `llm_summary` 字段说明改为 2-3 句话
- prompt 中有 llm_summary 写作指引和示例
- 3-5 个项目测试，输出的 llm_summary 符合"是什么+核心功能+适合谁用"结构
- 其他字段格式不变
- 其他 prompt 函数不变

---

## 第四步：任务 2 — 添加新工具 checklist 文档

### 目标

新建 `docs/add-new-tool-checklist.md`，包含从定义到上线的完整 8 步流程。

### 文档内容

写 `docs/add-new-tool-checklist.md`，包含以下 8 步：

#### 步骤 1：在 `data/seed-tools.yaml` 添加工具定义

参考现有工具结构（如 `claude-code` L1-34），新工具需包含：
- `id`：工具唯一标识（如 `my-new-tool`）
- `name`：工具显示名称
- `vendor`：厂商
- `repo`：GitHub 仓库（`owner/repo` 格式）
- `aliases`：工具的各种叫法（用于采集时的文本匹配）
- `extension_points`：扩展点类型（如 `skills`, `hooks`, `mcp`, `slash-commands` 等）
- `tracking_priority`：追踪优先级（`high` / `medium` / `low`）
- 可选：`website`、`docs`、`config_files`、`related_concepts`、`primary_type`

```bash
# 编辑 seed-tools.yaml，在数组末尾添加新工具定义
vim data/seed-tools.yaml
```

#### 步骤 2：运行 `collect_github.py` 采集新工具相关项目

```bash
python3 scripts/collect_github.py
```

- 脚本会根据 `seed-tools.yaml` 中的 `aliases` 和 `repo` 信息搜索 GitHub
- 新工具的 aliases 会用于搜索查询匹配
- 采集结果写入原始数据目录

#### 步骤 3：运行 `normalize.py` 归一化

```bash
python3 scripts/normalize.py --source github
```

- 将采集的原始数据归一化为统一格式
- 补充缺失字段、标准化数据结构

#### 步骤 4：运行 `score.py` 评分

```bash
python3 scripts/score.py
```

- 对归一化后的项目计算 `quantifiable_score`（0-60）
- 如果需要 LLM 质量分，后续运行 weekly_analysis.py

#### 步骤 5：运行 `build_site.py` 构建站点

```bash
python3 scripts/build_site.py
```

- 生成 `site/data/projects.json`、`site/data/tools.json` 等前端数据
- 重新生成文件 hash（`styles.css` → `styles.xxxxx.css`）
- 新工具会出现在工具概览区

#### 步骤 6：运行 `quality_gate.py` 验证

```bash
python3 scripts/quality_gate.py
```

- 检查数据完整性、必填字段、分数合理性
- 如有报错需修复后重跑

#### 步骤 7：（可选）运行 `weekly_analysis.py` 分析新项目

```bash
python3 scripts/weekly_analysis.py --max-projects N
```

- 对新采集的项目运行 LLM 分析（`relevance_score`、`quality_score`、`llm_summary`）
- `N` 为分析项目数量上限
- 此步骤需要 LLM API 配置（`config/llm-analysis.yaml`）
- 分析完成后重新 `build_site.py` 更新站点

#### 步骤 8：注意事项

- **aliases 要全面**：包含工具的各种叫法、缩写、全称。例如 Claude Code 的 aliases 包含 `["Claude Code", "claude-code", "anthropic claude code"]`
- **避免太通用的名字**：如果工具名太通用（如 `code`），会导致采集时误匹配大量无关项目。在 aliases 中尽量用完整名称
- **extension_points 要准确**：根据工具实际支持的扩展点填写，影响资源类型分类
- **tracking_priority 影响采集范围**：`high` 优先级工具会采集更多相关项目
- **采集后检查**：步骤 2 后检查采集结果，确认没有大量误匹配。如有，调整 aliases 后重新采集
- **部署**：`build_site.py` 只构建，`deploy_site.py` 才部署到线上

### 验收
- `docs/add-new-tool-checklist.md` 文件存在
- 包含完整 8 步流程
- 每步有对应的脚本命令
- 引用的脚本路径与实际文件一致（`scripts/collect_github.py`、`scripts/normalize.py` 等）
- 注意事项中提到 aliases 要全面、避免太通用名字

---

## 允许修改的文件

| 文件 | 改动范围 |
|------|----------|
| `scripts/llm_prompts.py` | **仅** `project_analysis_prompt()` 的 prompt 文本（`llm_summary` 字段说明 + 写作指引） |
| `docs/add-new-tool-checklist.md` | 新建文档 |

## 不允许修改的文件

- `scripts/score.py`
- `scripts/normalize.py`
- `scripts/collect_github.py`
- `config/llm-analysis.yaml`（schema 定义）
- `data/seed-tools.yaml`（除非测试需要，但最终不改）
- 任何前端文件（`site/*`）
- `scripts/llm_prompts.py` 中的其他函数（`benchmark_selection_prompt`、`weekly_report_prompt`、`tool_comparison_prompt`、`top_picks_prompt`）

---

## 关键约束

1. **不改评分逻辑**：`score.py`、`config/scoring*.yaml` 不动
2. **不改 schema**：`config/llm-analysis.yaml` 不动，JSON 输出结构不变
3. **只改 prompt 文本**：`llm_prompts.py` 只改 `project_analysis_prompt()` 中的 `llm_summary` 字段说明和写作指引
4. **不改其他 prompt 函数**：`benchmark_selection_prompt`、`weekly_report_prompt`、`tool_comparison_prompt`、`top_picks_prompt` 不动
5. **测试验证**：改完后对 3-5 个项目实际运行分析，确认输出符合预期

---

## 验收清单

| # | 验收项 | 方法 |
|---|--------|------|
| 1 | `llm_prompts.py` 的 `llm_summary` 字段说明改为 2-3 句话 | 读取文件确认 |
| 2 | prompt 中有 llm_summary 写作指引和示例 | 读取文件确认 |
| 3 | 3-5 个项目测试，llm_summary 符合"是什么+核心功能+适合谁用" | 运行 `weekly_analysis.py` 检查输出 |
| 4 | 其他字段格式不变 | 检查测试输出 JSON 的其他字段 |
| 5 | 其他 prompt 函数不变 | diff 确认只改了 `project_analysis_prompt` |
| 6 | `docs/add-new-tool-checklist.md` 存在 | 文件存在 |
| 7 | checklist 包含完整 8 步 | 读取文件确认 |
| 8 | checklist 中脚本路径正确 | 与实际文件对比 |
| 9 | checklist 注意事项提到 aliases 和误匹配 | 读取文件确认 |
