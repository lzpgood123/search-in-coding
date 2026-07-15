# 语义去重后续优化方案

> 状态：设计文档 / 后续增强项  
> 目标：在现有 URL / ID 规则去重之外，引入 embedding 模型或向量库，识别语义重复、同项目多入口、相似资料聚合，提高 Agent EcoRadar 索引质量。

## 1. 背景

当前项目已经具备：

- GitHub / Exa / fallback web 采集；
- URL / ID 级别合并；
- 自动分类、评分、curated / rejected；
- 双语字段和站点展示；
- snapshots 与 weekly diff。

但仍存在语义层面的重复或近重复：

1. 同一项目可能通过 GitHub、文章、文档、教程多个来源进入；
2. 不同 URL 指向同一生态对象；
3. 同一工具的 README、插件市场页、博客介绍可能分别成为记录；
4. 标题不同但摘要语义高度相似；
5. fallback / Exa 结果可能与 GitHub verified 记录重复。

现有规则能发现完全相同 URL，但不能可靠发现语义重复。

## 2. 优化目标

实现一个可解释、可回滚的语义去重层：

```text
normalize -> semantic_dedupe -> score -> finalize
```

目标不是直接删除记录，而是先生成候选重复关系，供 pipeline 自动合并或降权。

## 3. 非目标

首版不做：

- 人工审核后台；
- 大型向量数据库服务；
- 实时在线查询服务；
- 依赖私有账号套餐或额度的公开说明；
- 不可解释的自动删除。

## 4. 推荐技术路线

### 4.1 首选：本地轻量 embedding + 文件向量索引

适合当前仓库规模，项目记录约数百到数千条。

推荐模型：

```text
BAAI/bge-small-en-v1.5
BAAI/bge-small-zh-v1.5
sentence-transformers/all-MiniLM-L6-v2
```

优点：

- 本地运行；
- 成本低；
- 适合 GitHub Actions 或 production scheduler；
- 数据可完全留在仓库或生产运行环境；
- 不需要长期运行向量数据库。

推荐索引格式：

```text
data/semantic/embeddings.jsonl
```

或：

```text
data/semantic/vectors.npz
data/semantic/vector-meta.json
```

### 4.2 中期：FAISS 本地索引

当记录达到数万条时，可以使用：

```text
faiss-cpu
```

输出：

```text
data/semantic/faiss.index
data/semantic/vector-meta.json
```

优点：

- 查询快；
- 可离线运行；
- 不需要服务化。

缺点：

- GitHub Actions 安装依赖更重；
- 二进制索引不如 JSON 直观。

### 4.3 暂不推荐：在线向量数据库

例如 Pinecone、Qdrant Cloud、Weaviate Cloud 等。

原因：

- 当前规模不需要；
- 增加凭据和运维复杂度；
- 公开仓库不应依赖私人账号权益；
- 对 source-of-truth 可复现性不友好。

如果未来需要服务化，优先考虑自托管 Qdrant，并把它作为可选增强，不作为核心 pipeline 依赖。

## 5. 数据字段设计

新增文件：

```text
data/semantic/duplicate-candidates.yaml
```

建议结构：

```json
[
  {
    "record_id": "github-owner-repo",
    "candidate_id": "exa-some-url",
    "similarity": 0.91,
    "reason": "title+summary embedding similarity",
    "decision": "candidate",
    "preferred_id": "github-owner-repo",
    "created_at": "2026-07-06"
  }
]
```

新增到项目记录的可选字段：

```json
"semantic_group_id": "group-xxx",
"duplicate_of": "github-owner-repo",
"duplicate_confidence": 0.91,
"dedupe_state": "candidate|merged|ignored"
```

## 6. 相似度输入文本

每条记录生成一个 embedding text：

```text
name
summary
why_it_matters
category
target_tools
source_type
repo/url hostname
```

推荐函数：

```python
def embedding_text(record):
    return "\n".join([
        record.get("name", ""),
        record.get("summary", ""),
        record.get("why_it_matters", ""),
        " ".join(record.get("category", [])),
        " ".join(record.get("target_tools", [])),
        record.get("repo") or record.get("url", ""),
    ])
```

## 7. 判定策略

### 7.1 候选阈值

建议：

```text
similarity >= 0.92: strong duplicate candidate
0.85 <= similarity < 0.92: weak duplicate candidate
< 0.85: ignore
```

### 7.2 来源优先级

当两个记录重复时，preferred record 优先级：

```text
official-seed > github verified > exa verified > fallback-web
```

### 7.3 合并策略

首版不删除重复项，只做标记和降权：

- preferred record 保留；
- duplicate candidate 增加：

```json
"duplicate_of": "preferred-id",
"dedupe_state": "candidate"
```

评分阶段：

- `dedupe_state=candidate` 降低 confidence 或 total_score；
- curated 阶段默认跳过 duplicate candidate；
- rejected 阶段可将低质量 duplicate 放入 auto-rejected。

### 7.4 人类可解释

所有候选写入报告：

```text
docs/reports/semantic-dedupe-candidates.md
```

报告应包含：

- record A / B；
- similarity；
- source_type；
- preferred_id；
- reason；
- link。

## 8. 推荐脚本设计

新增：

```text
scripts/semantic_dedupe.py
```

命令：

```bash
python3 scripts/semantic_dedupe.py --backend local-json --threshold 0.85
```

可选：

```bash
python3 scripts/semantic_dedupe.py --backend faiss --threshold 0.85
python3 scripts/semantic_dedupe.py --apply
```

默认 dry-run：只生成候选，不改 `data/projects.yaml`。

`--apply`：写入 `duplicate_of` / `dedupe_state` 字段。

## 9. Pipeline 接入点

建议接入：

```text
normalize -> enrich_i18n -> semantic_dedupe -> score -> finalize
```

原因：

- normalize 后字段齐全；
- score 前可以对 duplicate 降权；
- finalize 前可避免 duplicate 进入 curated。

`update_tracker.py` 中可增加：

```text
python3 scripts/semantic_dedupe.py --apply
```

但首版建议先只在 weekly job 使用 `--apply`，daily 只生成候选。

## 10. 依赖管理

如果使用 sentence-transformers，需要新增：

```text
requirements-ml.txt
```

内容示例：

```text
sentence-transformers
numpy
scikit-learn
```

如果担心依赖过重，首版可以使用 sklearn 的 TF-IDF cosine similarity 作为 baseline：

```text
scripts/semantic_dedupe.py --backend tfidf
```

这样无需模型下载，适合先验证流程。

## 11. 分阶段实施计划

### Phase 1：TF-IDF baseline

- 新增 `scripts/semantic_dedupe.py --backend tfidf`；
- 生成 `data/semantic/duplicate-candidates.yaml`；
- 生成 `docs/reports/semantic-dedupe-candidates.md`；
- 不修改主数据。

验收：

```bash
python3 scripts/semantic_dedupe.py --backend tfidf
python3 scripts/quality_gate.py
```

### Phase 2：安全 apply

- 增加 `--apply`；
- 对 high confidence duplicate 写入：

```text
duplicate_of
dedupe_state
semantic_group_id
```

- score 阶段对 duplicate 降权；
- finalize 阶段跳过 duplicate candidate。

验收：

```bash
python3 scripts/update_tracker.py --skip-collect --deploy
python3 -m pytest
```

### Phase 3：Embedding backend

- 增加 sentence-transformers backend；
- 缓存 vectors；
- 支持增量更新；
- 对比 TF-IDF 与 embedding 候选质量。

验收：

- Top duplicate candidates 中误报率可接受；
- curated 中重复项目减少；
- 报告能解释为什么合并/降权。

### Phase 4：FAISS / Qdrant 可选增强

当记录规模明显增长后再考虑。

## 12. 测试计划

新增测试：

```text
tests/test_semantic_dedupe.py
```

覆盖：

1. 相同项目不同 URL 能成为 candidate；
2. 完全不同类别不会误判；
3. official/github 优先于 fallback；
4. `--apply` 不会删除记录；
5. duplicate candidate 不进入 curated。

## 13. 风险与防护

| 风险 | 防护 |
|---|---|
| 相似主题但不同项目被误判重复 | 默认 candidate，不自动删除 |
| embedding 模型下载慢 | 首版 TF-IDF baseline，无模型依赖 |
| GitHub Actions 依赖过重 | ML backend 可选，不作为默认 CI |
| 二进制索引污染 Git | 首版 JSON/NPZ；FAISS 文件可按需忽略或归档 |
| 影响 curated 质量 | 先报告候选，再 apply |

## 14. 推荐默认实现

建议下一轮先做：

```text
Phase 1 + Phase 2 的 TF-IDF baseline
```

理由：

- 不引入大模型依赖；
- 可快速验证语义去重价值；
- 可解释；
- 不影响现有稳定 pipeline；
- 后续可无缝替换为 embedding backend。

## 15. Definition of Done

语义去重优化完成标准：

- `scripts/semantic_dedupe.py` 存在；
- `data/semantic/duplicate-candidates.yaml` 自动生成；
- `docs/reports/semantic-dedupe-candidates.md` 自动生成；
- `tests/test_semantic_dedupe.py` 通过；
- `quality_gate.py` 通过；
- curated 中不会出现 high-confidence duplicate；
- pipeline 仍可默认无模型依赖运行；
- 文档说明 TF-IDF / embedding / FAISS 三种后端取舍。
