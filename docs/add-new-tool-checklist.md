# 添加新工具 Checklist

> 用途：把一个新的 AI Coding 工具加入 Search in Coding 追踪体系。  
> 范围：从 `data/seed-tools.yaml` 定义，到采集、归一化、评分、构建、质量门禁与可选 LLM 分析。  
> 注意：`build_site.py` 只构建本地站点产物；线上发布需额外运行 `deploy_site.py`。

---

## 步骤 1：在 `data/seed-tools.yaml` 添加工具定义

参考现有工具结构（如 `claude-code`），在数组末尾追加一条完整定义。

### 必填字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `id` | 工具唯一标识（小写、连字符） | `my-new-tool` |
| `name` | 显示名称 | `My New Tool` |
| `vendor` | 厂商 | `Example Corp` |
| `repo` | GitHub 仓库 `owner/repo` | `example/my-new-tool` |
| `aliases` | 采集文本匹配用的各种叫法 | `["My New Tool", "my-new-tool"]` |
| `extension_points` | 扩展点类型 | `["skills", "hooks", "mcp"]` |
| `tracking_priority` | 追踪优先级 | `high` / `medium` / `low` |

### 可选字段

- `website`、`docs`
- `config_files`（如 `CLAUDE.md`、`AGENTS.md`）
- `related_concepts`
- `primary_type`（如 `terminal-agent`）

### 操作

```bash
# 编辑 seed-tools.yaml，在数组末尾添加新工具定义
# 推荐用编辑器，注意 YAML/JSON 结构与现有条目一致
vim data/seed-tools.yaml
```

添加后快速自检：

```bash
python3 -c "import yaml; from pathlib import Path; t=yaml.safe_load(Path('data/seed-tools.yaml').read_text()); print(len(t), [x['id'] for x in t])"
```

---

## 步骤 2：运行 `collect_github.py` 采集新工具相关项目

```bash
python3 scripts/collect_github.py
```

说明：

- 脚本会根据 `data/seed-tools.yaml` 中的 `aliases` 与 `repo` 信息搜索 GitHub
- 新工具的 `aliases` 会进入搜索/匹配逻辑
- 采集结果写入原始数据目录（`data/raw/github/YYYY-MM-DD/`）

可选调试参数：

```bash
python3 scripts/collect_github.py --help
python3 scripts/collect_github.py --dry-run
python3 scripts/collect_github.py --limit 20
```

采集后检查是否有大量误匹配；若有，先收紧 `aliases` 再重跑本步骤。

---

## 步骤 3：运行 `normalize.py` 归一化

```bash
python3 scripts/normalize.py --source github
```

说明：

- 将采集的原始数据合并/归一化为统一的 `data/projects.yaml`
- 补充缺失字段、标准化结构
- 仅 GitHub 来源时使用 `--source github`

---

## 步骤 4：运行 `score.py` 评分

```bash
python3 scripts/score.py
```

说明：

- 计算可量化分 `quantifiable_score`（0–60）
- LLM 质量分 `quality_score`（0–40）需后续 `weekly_analysis.py` 写入
- 总分 = 可量化分 + LLM 质量分

---

## 步骤 5：运行 `build_site.py` 构建站点

```bash
python3 scripts/build_site.py
```

说明：

- 生成 `site/data/projects.json`、`site/data/tools.json`、`search-index.json`、详情分片等
- 重新生成带 hash 的静态资源（如 `styles.xxxxx.css`）
- 新工具会出现在工具概览区（`tools.json` / 前端工具标签）

---

## 步骤 6：运行 `quality_gate.py` 验证

```bash
python3 scripts/quality_gate.py
```

说明：

- 检查数据完整性、必填字段、分数合理性等门禁
- 有报错时先修复数据/配置，再重跑本步骤

---

## 步骤 7：（可选）运行 `weekly_analysis.py` 分析新项目

```bash
python3 scripts/weekly_analysis.py --max-projects N
```

说明：

- 对新采集或超过重分析窗口的项目运行 LLM 分析
- 会写入 `relevance_score` 相关判定、`quality_score`、`llm_summary`、`tracking_priority` 等
- `N` 为本次分析项目数量上限（测试时可设 5–20）
- 依赖 `config/llm-analysis.yaml` 与 SenseNova API 凭证
- 分析完成后建议再跑一次：

```bash
python3 scripts/build_site.py
python3 scripts/quality_gate.py
```

常用参数：

```bash
python3 scripts/weekly_analysis.py --help
python3 scripts/weekly_analysis.py --dry-run
python3 scripts/weekly_analysis.py --max-projects 5 --skip-reports --skip-benchmarks --skip-build
```

---

## 步骤 8：注意事项

1. **aliases 要全面**：包含全称、连字符写法、常见缩写。例如 Claude Code：`["Claude Code", "claude-code", "anthropic claude code"]`。
2. **避免太通用的名字**：如单独写 `code`、`agent`，采集时会误匹配大量无关仓库。优先用完整产品名。
3. **extension_points 要准确**：按工具真实支持的扩展点填写（`skills` / `hooks` / `mcp` / `slash-commands` 等），会影响资源类型与展示。
4. **tracking_priority 影响采集与追踪侧重**：`high` 优先级工具通常覆盖更广的相关项目。
5. **采集后检查**：步骤 2 后抽查 raw 结果，确认没有大量误匹配；必要时调整 aliases 后重采。
6. **构建 ≠ 部署**：
   - `python3 scripts/build_site.py` 只生成 `site/` 产物
   - 上线需额外：`python3 scripts/deploy_site.py`（或带 `--dest` 指定 webroot）
7. **不要改评分公式/schema 来“适配”新工具**：优先改 seed 定义与 aliases；评分与 LLM schema 由既有配置维护。
8. **官方 seed 工具**：若该工具本身是被追踪的官方产品，确认 `source_type=official-seed` 相关流程与展示是否符合预期（通常由现有 official seed 管道维护）。

---

## 快速验收清单

- [ ] `data/seed-tools.yaml` 新工具 `id` 唯一，字段齐全
- [ ] `collect_github.py` 跑通，raw 结果无明显噪声洪泛
- [ ] `normalize.py --source github` 成功，新相关项目进入 `projects.yaml`
- [ ] `score.py` 成功
- [ ] `build_site.py` 成功，`site/data/tools.json` 可见新工具
- [ ] `quality_gate.py` 通过
- [ ] （可选）`weekly_analysis.py` 给新项目写入 `llm_summary` / `quality_score`
- [ ] 若需上线：`deploy_site.py` 已执行并抽查正式站

---

## 相关文件

| 路径 | 作用 |
|------|------|
| `data/seed-tools.yaml` | 目标工具清单 |
| `scripts/collect_github.py` | GitHub 采集 |
| `scripts/normalize.py` | 归一化 |
| `scripts/score.py` | 可量化评分 |
| `scripts/build_site.py` | 站点构建 |
| `scripts/quality_gate.py` | 质量门禁 |
| `scripts/weekly_analysis.py` | 每周/按需 LLM 分析 |
| `scripts/deploy_site.py` | 部署到正式站 |
| `config/llm-analysis.yaml` | LLM 分析配置 |
