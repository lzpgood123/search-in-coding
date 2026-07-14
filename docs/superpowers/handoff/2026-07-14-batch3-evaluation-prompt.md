# 第 3 批 LLM 分析系统 评估提示词

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的质量评估 Agent。第 3 批 LLM 分析系统刚刚完成，你需要全面评估其完成度、LLM 输出质量、系统可靠性和遗留问题。

第 3 批与前面批次不同：它涉及 LLM 输出（质量评分、分类、一句话评价），不是简单的"有/没有"二元判断，需要评估**输出质量**和**系统可靠性**。

## 评估背景

第 3 批目标是实现每周一 03:30 自动 LLM 深度分析系统：
- 直接调用 SenseNova API（DeepSeek-V4-Flash），13 个 key 轮询
- 对项目做相关性判断、分类打标、质量评分（40分）、生成双语一句话评价
- 维护动态参照基准（5 个分数段各 1 个标杆项目）
- 重评全部项目并生成 3 份报告
- Hermes cron 每周一 03:30 no_agent 模式自动运行

## 评估项清单

### 一、基础设施（7 项）

1. **脚本是否存在**：`scripts/llm_api.py`、`scripts/llm_prompts.py`、`scripts/benchmark_manager.py`、`scripts/weekly_analysis.py`
2. **配置文件**：`config/llm-analysis.yaml`
3. **测试文件**：`tests/test_llm_api.py`、`tests/test_weekly_analysis.py`、`tests/test_benchmark_manager.py`、`tests/test_weekly_e2e.py`
4. **测试通过率**：全部测试是否通过
5. **Cron 配置**：Hermes cron 是否配置为每周一运行，no_agent 模式，工作目录正确
6. **Cron 脚本**：`~/.hermes/scripts/search-in-coding-weekly.sh` 是否存在且正确
7. **dry-run**：`python3 scripts/weekly_analysis.py --dry-run` 是否正常输出

### 二、LLM 分析功能（6 项）

8. **已分析项目数量**：有多少项目有 `quality_score > 0`（当前已知仅 3 个，因为只跑了 --max-projects 3 测试）
9. **质量分合理性**：已分析项目的 `quality_score`（0-40）是否合理？高分项目（如 Claude Code 87 分）和低分项目的分差是否合理？
10. **llm_summary 质量**：已分析项目的 `llm_summary` 是否有中英双语？内容是否准确描述了项目？
11. **resource_type 准确性**：LLM 打的 `resource_type` 标签是否准确？有没有误标？
12. **tracking_priority 合理性**：`track`/`index`/`reject` 分级是否合理？
13. **benchmark_ref 填充**：项目是否有参照基准引用？

### 三、参照基准系统（4 项）

14. **benchmarks.yaml 存在**：5 个分数段是否都有标杆项目？
15. **参照项目合理性**：标杆项目是否真的代表了该分数段？理由（reason）是否合理？
16. **参照更新流程**：weekly_analysis.py 是否先更新参照基准再重评分？
17. **benchmark_ref 关联**：项目是否正确关联到对应分数段的标杆？

### 四、评分系统集成（3 项）

18. **total_score 计算**：`total_score = quantifiable_score + quality_score` 是否正确？
19. **评分范围**：已分析项目的 total_score 是否在合理范围（如 6-92）？未分析项目是否仍为 quantifiable_score only？
20. **score.py 整合**：score.py 是否正确处理已有 quality_score（不覆盖为 0）？

### 五、报告和快照（4 项）

21. **3 份报告存在**：`docs/reports/weekly-report.md`、`tool-comparison.md`、`curated-top.md`
22. **报告内容质量**：报告是否用了新字段（resource_type/total_score/tracking_priority）？是否有旧字段残留？
23. **快照生成**：`data/snapshots/YYYY-MM-DD.json` 是否存在且包含正确统计？
24. **快照内容**：快照是否包含 total_projects、by_tracking、avg_score、tool_coverage、resource_type_coverage、analyzed_count？

### 六、前端展示（3 项）

25. **quality_score 展示**：详情面板是否展示质量分（/40）？未分析项目是否标注"待 LLM 分析"？
26. **llm_summary 展示**：详情面板是否展示 LLM 一句话评价（中英双语）？
27. **benchmark_ref 展示**：详情面板是否展示参照项目？

### 七、全量运行就绪度（3 项）

28. **290 个待分析项目**：dry-run 是否显示 290 个项目待分析？（当前只分析了 3 个）
29. **全量运行预估**：290 个项目 × 每批 3 并发 = 97 批，每批约 10-30 秒，预计 16-48 分钟。cron 脚本是否设置了足够超时？
30. **错误恢复**：如果 LLM 调用失败，项目是否保持 quality_score=0 不崩溃？断点续传机制是否可用？

## 评估方法

### 第一步：读取项目文档

1. `docs/superpowers/plans/2026-07-12-batch3-llm-analysis.md` - 实现计划（已更新）
2. `docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md` - 原始设计规格
3. `docs/superpowers/specs/2026-07-13-site-optimization-v3-design.md` - v3 优化规格

### 第二步：基础设施检查

```bash
cd "/root/workspace/search in coding"

# 1. 脚本存在性
ls -la scripts/llm_api.py scripts/llm_prompts.py scripts/benchmark_manager.py scripts/weekly_analysis.py

# 2. 配置文件
cat config/llm-analysis.yaml

# 3. 测试文件
ls -la tests/test_llm_api.py tests/test_weekly_analysis.py tests/test_benchmark_manager.py tests/test_weekly_e2e.py

# 4. 测试通过率
source .venv/bin/activate && python3 -m pytest tests/ -v --tb=short

# 5. Cron 配置
hermes cron list

# 6. Cron 脚本
cat ~/.hermes/scripts/search-in-coding-weekly.sh

# 7. Dry run
python3 scripts/weekly_analysis.py --dry-run
```

### 第三步：LLM 分析质量检查

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml, json

with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
n = len(projects)

# 8. 已分析项目数量
analyzed = [p for p in projects if p.get('quality_score', 0) > 0]
print(f'已分析: {len(analyzed)}/{n}')
print(f'未分析: {n - len(analyzed)}/{n}')

# 9-12. 逐个检查已分析项目
print('\n=== 已分析项目详情 ===')
for p in analyzed:
    print(f'\n  {p[\"name\"]}:')
    print(f'    total={p.get(\"total_score\")} (q={p.get(\"quantifiable_score\")}+qual={p.get(\"quality_score\")})')
    print(f'    tracking={p.get(\"tracking_priority\")}')
    print(f'    resource_type={p.get(\"resource_type\")}')
    print(f'    target_tools={p.get(\"target_tools\")}')
    llm = p.get('llm_summary', {})
    print(f'    llm_summary zh: {llm.get(\"zh\", \"MISSING\")}')
    print(f'    llm_summary en: {llm.get(\"en\", \"MISSING\")}')
    print(f'    last_analyzed: {p.get(\"last_analyzed\")}')
    print(f'    benchmark_ref: {p.get(\"benchmark_ref\")}')

# 13. benchmark_ref 填充率
bm_filled = sum(1 for p in projects if p.get('benchmark_ref'))
print(f'\nbenchmark_ref filled: {bm_filled}/{n}')
"
```

### 第四步：参照基准检查

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml
with open('data/benchmarks.yaml') as f:
    bm = yaml.safe_load(f)
print('=== Benchmarks ===')
for label, info in (bm or {}).items():
    print(f'  {label}: {info.get(\"project_name\",\"?\")} (score={info.get(\"score\",\"?\")})')
    print(f'    reason: {info.get(\"reason\",\"?\")[:100]}')
# Check all 5 ranges exist
expected = ['标杆', '优秀', '可用', '萌芽', '噪声']
missing = [r for r in expected if r not in (bm or {})]
if missing:
    print(f'  ⚠️ Missing ranges: {missing}')
else:
    print(f'  ✅ All 5 ranges present')
"

# 16. Check weekly_analysis.py source for benchmark-before-rescore logic
grep -n "benchmark\|rescore" scripts/weekly_analysis.py | head -10
```

### 第五步：评分和报告检查

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml, json
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
n = len(projects)

# 18-19. Score check
for p in projects:
    q = p.get('quantifiable_score', 0)
    qual = p.get('quality_score', 0)
    total = p.get('total_score', 0)
    if total != q + qual:
        print(f'  ⚠️ Score mismatch: {p[\"name\"]}: total={total} != q={q}+qual={qual}')
print('Score check done')

# 20. score.py preserves quality_score
"
grep -n "quality_score" scripts/score.py | head -5

# 21-22. Reports
echo '=== Reports ==='
ls -la docs/reports/weekly-report.md docs/reports/tool-comparison.md docs/reports/curated-top.md
echo '--- weekly-report.md (first 20 lines) ---'
head -20 docs/reports/weekly-report.md
echo '--- Check for old field names ---'
grep -c "category\|source_quality\|ranking_scope\|record_kind" docs/reports/*.md || echo 'No old fields found'

# 23-24. Snapshots
echo '=== Snapshots ==='
ls -la data/snapshots/*.json | tail -3
python3 -c "
import json, os
files = sorted([f for f in os.listdir('data/snapshots') if f.endswith('.json')])
if files:
    with open(f'data/snapshots/{files[-1]}') as f:
        snap = json.load(f)
    print(f'Latest: {files[-1]}')
    print(f'Keys: {list(snap.keys())}')
    for k in ['total_projects','by_tracking','avg_score','tool_coverage','resource_type_coverage','analyzed_count']:
        print(f'  {k}: {\"✅\" if k in snap else \"❌\"} ({snap.get(k, \"N/A\")})')
"
```

### 第六步：前端展示检查

```bash
cd "/root/workspace/search in coding"
# 25-27. Check render.js for quality_score, llm_summary, benchmark_ref display
echo "=== render.js checks ==="
grep -n "quality_score\|quality.*40\|/40" site/js/render.js
grep -n "llm_summary\|LLM Summary" site/js/render.js
grep -n "benchmark_ref\|benchmarkRef" site/js/render.js

# Check detail JSON has the fields
python3 -c "
import json
details = json.load(open('site/data/projects-detail.json'))
d = details[0]
for f in ['quality_score', 'llm_summary', 'benchmark_ref', 'score_detail', 'last_analyzed']:
    print(f'  {f}: {\"✅\" if f in d else \"❌\"}')
"
```

### 第七步：全量运行就绪度

```bash
cd "/root/workspace/search in coding"
# 28. Check dry-run output
python3 scripts/weekly_analysis.py --dry-run

# 29. Check cron script timeout handling
cat ~/.hermes/scripts/search-in-coding-weekly.sh

# 30. Check error handling in weekly_analysis.py
grep -n "except\|error\|failed\|None" scripts/weekly_analysis.py | head -10
grep -n "quality_score.*0\|default.*0" scripts/weekly_analysis.py | head -5
```

## 评估报告格式

输出一份评估报告：

```markdown
# 第 3 批 LLM 分析系统 评估报告

> 评估日期：YYYY-MM-DD

## 总览

| 类别 | 项数 | 完成 | 部分完成 | 未完成 | 完成率 |
|------|------|------|---------|--------|--------|
| 基础设施 | 7 | ? | ? | ? | ?% |
| LLM 分析功能 | 6 | ? | ? | ? | ?% |
| 参照基准 | 4 | ? | ? | ? | ?% |
| 评分集成 | 3 | ? | ? | ? | ?% |
| 报告和快照 | 4 | ? | ? | ? | ?% |
| 前端展示 | 3 | ? | ? | ? | ?% |
| 全量运行就绪 | 3 | ? | ? | ? | ?% |
| 合计 | 30 | ? | ? | ? | ?% |

## 逐项评估

（每项标注 ✅/🟡/❌ + 证据）

## LLM 输出质量评估

（对 3 个已分析项目的 llm_summary、resource_type、quality_score、tracking_priority 逐一评判准确性）

## 关键风险

| 风险 | 严重度 | 说明 |
|------|--------|------|
| ... | ... | ... |

## 建议

（下一步应该做什么：全量运行？调优 prompt？修复问题？）
```

## 项目环境信息

- 工作目录：`/root/workspace/search in coding`
- Python：3.12.3（用 python3）
- 测试：`source .venv/bin/activate && python3 -m pytest tests/ -v`
- 站点：https://coding.lzpgood.online/
- 当前数据状态：293 条项目，仅 3 个已分析（Hermes Agent/OpenCode/Claude Code），290 个待分析
- LLM API：SenseNova DeepSeek-V4-Flash，13 个 key 在 `~/.hermes/auth.json`
- Cron：每周一 03:30，no_agent 模式

## 注意事项

- 第 3 批只分析了 3 个项目（测试运行），**290 个项目尚未分析**。这不是"未完成"，而是"测试运行后等待全量运行"
- 评估重点是：系统是否就绪、LLM 输出质量是否可信、全量运行是否会出问题
- 对 LLM 输出的评估要基于事实：llm_summary 是否准确描述了项目？resource_type 是否正确？quality_score 是否合理？
- 对比 plan 中的验收标准，标注哪些已达到、哪些部分达到、哪些未达到
- 用户偏好精准区分"已完成"和"部分完成"
