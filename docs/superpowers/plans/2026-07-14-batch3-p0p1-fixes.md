# 第 3 批 P0+P1 修复 实现计划

> **面向 AI 代理的工作者：** 直接按计划执行，步骤用复选框跟踪。

**目标：** 修复第 3 批评估报告中的 3 个 P0（cron 超时、score_detail 冲突、无增量落盘）和 2 个 P1（前端 /60 展示、benchmark_ref 显示 project_id）。

**前置：** 第 3 批 LLM 分析系统已完成，3 个项目已分析，114 测试通过。

---

## 任务 1：提高 cron 超时到 3600s（P0-Critical）

- [ ] **步骤 1：修改 Hermes 配置**

```bash
hermes config set cron.script_timeout_seconds 3600
```

验证：
```bash
hermes config get cron.script_timeout_seconds
```

- [ ] **步骤 2：同步修复 daily job 超时**

daily job 也受 120s 限制。确认配置全局生效后 daily job 也会使用新超时。

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git commit --allow-empty -m "fix: increase cron script timeout to 3600s for weekly LLM analysis"
```

---

## 任务 2：拆分 score_detail 和 quality_detail（P0-High）

**文件：** `scripts/weekly_analysis.py`, `scripts/score.py`, `scripts/build_site.py`, `site/js/render.js`

- [ ] **步骤 1：修改 weekly_analysis.py 的 merge_analysis_result**

把 `quality_detail` 写入独立字段，不覆盖 `score_detail`：

```python
# 在 merge_analysis_result 中，找到：
# if 'quality_detail' in analysis:
#     p['score_detail'] = analysis['quality_detail']
# 改为：
if 'quality_detail' in analysis:
    p['quality_detail'] = analysis['quality_detail']
```

- [ ] **步骤 2：修改 build_site.py 的 detail_project 和 SLIM_FIELDS**

在 `DETAIL_FIELDS` 中添加 `quality_detail`：
```python
DETAIL_FIELDS = SLIM_FIELDS + [
    'score_detail', 'quality_detail', 'llm_summary', 'benchmark_ref', 'last_analyzed',
    'repo', 'tags', 'maturity', 'status',
    'readme_preview', 'topics',
]
```

- [ ] **步骤 3：修改 render.js 详情面板展示**

在详情面板中，`score_detail` 展示可量化分项（stars/activity/adoption/maturity），`quality_detail` 展示 LLM 质量分项（relevance/practicality/novelty/ecosystem_value）：

```javascript
// 在 openDetail 中，找到 score_detail 展示部分，改为：
${sd && Object.keys(sd).length > 0 ? `
<div class="detail-section">
  <h3>${SIC_i18n.t('scoreBreakdown')}</h3>
  <div class="score-detail-grid">
    <div class="score-detail-item"><div class="label">Stars</div><div class="value">${this.safeNum(sd.stars)}/20</div></div>
    <div class="score-detail-item"><div class="label">Activity</div><div class="value">${this.safeNum(sd.activity)}/15</div></div>
    <div class="score-detail-item"><div class="label">Adoption</div><div class="value">${this.safeNum(sd.adoption)}/10</div></div>
    <div class="score-detail-item"><div class="label">Maturity</div><div class="value">${this.safeNum(sd.maturity)}/15</div></div>
  </div>
</div>` : ''}

${detail?.quality_detail && Object.keys(detail.quality_detail).length > 0 ? `
<div class="detail-section">
  <h3>${SIC_i18n.t('qualityBreakdown') || '质量分项'}</h3>
  <div class="score-detail-grid">
    <div class="score-detail-item"><div class="label">Relevance</div><div class="value">${this.safeNum(detail.quality_detail.relevance)}/10</div></div>
    <div class="score-detail-item"><div class="label">Practicality</div><div class="value">${this.safeNum(detail.quality_detail.practicality)}/10</div></div>
    <div class="score-detail-item"><div class="label">Novelty</div><div class="value">${this.safeNum(detail.quality_detail.novelty)}/10</div></div>
    <div class="score-detail-item"><div class="label">Ecosystem</div><div class="value">${this.safeNum(detail.quality_detail.ecosystem_value)}/10</div></div>
  </div>
</div>` : ''}
```

- [ ] **步骤 4：修复已分析项目的 score_detail**

3 个已分析项目的 score_detail 被覆盖了，需要恢复。重新跑 score.py 恢复可量化分项：

```bash
cd "/root/workspace/search in coding"
python3 scripts/score.py
```

- [ ] **步骤 5：重建站点并验证**

```bash
python3 scripts/build_site.py
python3 -c "
import json
details = json.load(open('site/data/projects-detail.json'))
for d in details[:3]:
    if d.get('quality_score',0) > 0:
        print(f'{d[\"name\"]}: score_detail={d.get(\"score_detail\",{})}, quality_detail={d.get(\"quality_detail\",\"MISSING\")}')
        break
"
```

- [ ] **步骤 6：Commit**

```bash
git add scripts/weekly_analysis.py scripts/score.py scripts/build_site.py site/js/render.js
git commit -m "fix: split score_detail (quantifiable) and quality_detail (LLM) to prevent field overwrite"
```

---

## 任务 3：增量落盘 checkpoint（P0-High）

**文件：** `scripts/weekly_analysis.py`

- [ ] **步骤 1：修改 run_analysis 函数，每批完成后保存**

在 `run_analysis` 函数中，每批 LLM 分析完成后立即保存 projects.yaml：

```python
# 在 run_analysis 中，每批循环结束后添加：
from common import save_jsonish
save_jsonish('data/projects.yaml', projects)
print(f'  Checkpoint saved ({len(all_results)} analyzed so far)')
```

- [ ] **步骤 2：验证断点续传**

验证 `get_projects_to_analyze` 会跳过已分析的项目（last_analyzed 已设置）：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from weekly_analysis import get_projects_to_analyze
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
to_analyze = get_projects_to_analyze(projects)
print(f'Total: {len(projects)}, to analyze: {len(to_analyze)}')
# Should be 290 (3 already analyzed)
"
```

- [ ] **步骤 3：Commit**

```bash
git add scripts/weekly_analysis.py
git commit -m "fix: add incremental checkpoint saving after each batch in weekly_analysis"
```

---

## 任务 4：前端分数展示修复（P1-High）

**文件：** `site/js/render.js`

- [ ] **步骤 1：修改分数展示逻辑**

已分析项目（quality_score > 0）展示 `/100`，未分析项目展示 `/60`：

```javascript
// 在 renderMore 的表格行中，找到分数展示：
// <span class="score-badge">${this.safeNum(p.total_score)}</span><span class="muted" style="font-size:11px;">/60</span>
// 改为：
const maxScore = (p.quality_score > 0) ? 100 : 60;
// <span class="score-badge">${this.safeNum(p.total_score)}</span><span class="muted" style="font-size:11px;">/${maxScore}</span>

// 在 openDetail 的详情面板中，找到：
// <span class="muted">/ 60 ${SIC_i18n.t('quantifiable')}</span>
// 改为：
const maxScore = (qualityScore > 0) ? 100 : 60;
// <span class="muted">/ ${maxScore}</span>

// 进度条也改为：
// <div class="score-bar-fill" style="width:${total/60*100}%"></div>
// 改为：
// <div class="score-bar-fill" style="width:${Math.min(100, total/maxScore*100)}%"></div>
```

- [ ] **步骤 2：Commit**

```bash
git add site/js/render.js
git commit -m "fix: display /100 for analyzed projects and /60 for unanalyzed"
```

---

## 任务 5：benchmark_ref 显示项目名（P1-Medium）

**文件：** `site/js/render.js`

- [ ] **步骤 1：修改详情面板 benchmark_ref 展示**

```javascript
// 在 openDetail 中，找到：
// ${detail?.benchmark_ref ? `<div class="detail-section"><h3>${SIC_i18n.t('benchmarkRef')}</h3><p class="muted">${this.esc(detail.benchmark_ref)}</p></div>` : ''}
// 改为：
${detail?.benchmark_ref ? (() => {
    const refProject = SIC_data.projects.find(p => p.id === detail.benchmark_ref);
    const refName = refProject ? SIC_i18n.textOf(refProject, 'name') : detail.benchmark_ref;
    return `<div class="detail-section"><h3>${SIC_i18n.t('benchmarkRef')}</h3><p class="muted">${this.esc(refName)}</p></div>`;
})() : ''}
```

- [ ] **步骤 2：Commit**

```bash
git add site/js/render.js
git commit -m "fix: display benchmark project name instead of raw id"
```

---

## 任务 6：重建、部署、验证

- [ ] **步骤 1：重新评分**

```bash
cd "/root/workspace/search in coding"
python3 scripts/score.py
```

- [ ] **步骤 2：运行 pipeline**

```bash
python3 scripts/update_tracker.py --skip-collect
```

- [ ] **步骤 3：部署**

```bash
python3 scripts/deploy_site.py
```

- [ ] **步骤 4：验证**

```bash
# 1. score_detail 和 quality_detail 分离
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
for p in projects:
    if p.get('quality_score',0) > 0:
        sd = p.get('score_detail',{})
        qd = p.get('quality_detail',{})
        print(f'{p[\"name\"]}:')
        print(f'  score_detail (quantifiable): {sd}')
        print(f'  quality_detail (LLM): {qd}')
        # Verify score_detail has stars/activity, not relevance/practicality
        if 'stars' in sd:
            print(f'  ✅ score_detail is quantifiable')
        elif 'relevance' in sd:
            print(f'  ❌ score_detail still has LLM fields')
        if 'relevance' in qd:
            print(f'  ✅ quality_detail has LLM fields')
        else:
            print(f'  ❌ quality_detail missing')
"

# 2. 前端 /100 vs /60
grep "/100\|maxScore" site/js/render.js | head -3

# 3. benchmark_ref shows name
grep "refProject\|refName" site/js/render.js | head -2

# 4. Cron timeout
hermes config get cron.script_timeout_seconds

# 5. 增量落盘
grep "Checkpoint saved\|save_jsonish" scripts/weekly_analysis.py | head -3
```

- [ ] **步骤 5：小规模分层试跑**

```bash
python3 scripts/weekly_analysis.py --max-projects 30 --skip-reports
```

验证：
- 30 个项目被分析（不只是 official-seed）
- 覆盖 skills/mcp-server/rules 等类型
- 有 reject/index 分级出现
- projects.yaml 每批保存

- [ ] **步骤 6：Commit 并 tag**

```bash
git add -A
git commit -m "fix: batch3 P0+P1 fixes - cron timeout, score_detail split, checkpoint, /100 display, benchmark name"
git tag v2025.07.14-batch3-fixes
```

---

## 验收标准

- [ ] `hermes config get cron.script_timeout_seconds` 返回 3600
- [ ] 已分析项目的 `score_detail` 包含 stars/activity/adoption/maturity（不是 relevance/practicality）
- [ ] 已分析项目有独立的 `quality_detail` 字段包含 relevance/practicality/novelty/ecosystem_value
- [ ] weekly_analysis.py 每批后保存 projects.yaml
- [ ] 前端已分析项目显示 `/100`，未分析显示 `/60`
- [ ] 前端 benchmark_ref 显示项目名而非 project_id
- [ ] --max-projects 30 试跑成功，覆盖多种 resource_type
- [ ] pipeline --skip-collect PASS
