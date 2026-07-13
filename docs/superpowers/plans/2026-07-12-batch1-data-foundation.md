# 第 1 批：数据基础 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 清理旧数据、重构字段结构、实现一次性历史回溯采集、上线 100 分制中的 60 分可量化评分系统，确保站点在新数据结构下可访问。

**架构：** 移除 Exa/fallback-web 数据只保留 GitHub 264 条；重构 projects.yaml 字段（移除旧评分字段、新增 resource_type/tracking_priority/quantifiable_score 等）；编写 initial_collection.py 按月分片回溯采集 2025-01 至今的项目；重写 score.py 为 100 分制双层评分（本批只实现 60 分可量化部分，quality_score 留 0 占位）；适配 build_site.py 和旧前端使站点可访问。

**技术栈：** Python 3.12+, GitHub CLI (gh), PyYAML, pytest

**关联文档：**
- 设计规格：`docs/superpowers/specs/2026-07-12-three-layer-optimization-design.md`
- ADR-0001 ~ ADR-0007：`docs/adr/`
- 领域术语：`CONTEXT.md`

---

## 文件结构

### 新建文件

| 文件 | 职责 |
|------|------|
| `scripts/initial_collection.py` | 一次性历史回溯采集脚本，按月分片搜索 GitHub，支持断点续传 |
| `scripts/migrate_data.py` | 数据迁移脚本：清理旧数据 + 字段重构 |
| `config/scoring-v2.yaml` | 新评分配置（100 分制可量化分规则） |
| `tests/test_migrate_data.py` | 数据迁移测试 |
| `tests/test_initial_collection.py` | 回溯采集测试 |
| `tests/test_score_v2.py` | 新评分系统测试 |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `scripts/common.py` | 移除旧评分函数（total_score/score_from_stars），新增 v2 评分函数 |
| `scripts/score.py` | 重写为 100 分制可量化评分 |
| `scripts/normalize.py` | 移除 from_exa()/from_web()，重构 github_record() 字段 |
| `scripts/build_site.py` | 适配新字段结构 |
| `scripts/quality_gate.py` | 适配新字段结构 |
| `scripts/update_tracker.py` | 移除 Exa/Web 采集步骤 |
| `scripts/validate_data.py` | 更新必填字段列表 |
| `scripts/finalize_data.py` | 适配新字段结构 |
| `site/app.js` | 适配新字段名（resource_type 替代 category，total_score 0-100） |
| `site/index.html` | 适配新字段名 |

---

## 任务 1：数据迁移脚本

**文件：**
- 创建：`scripts/migrate_data.py`
- 创建：`tests/test_migrate_data.py`

- [ ] **步骤 1：编写数据迁移测试**

```python
# tests/test_migrate_data.py
"""Test data migration from old schema to new 100-point schema."""
import pytest
import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from migrate_data import migrate_project, should_remove_project


class TestShouldRemoveProject:
    def test_removes_fallback_web(self):
        p = {'source_type': 'fallback-web'}
        assert should_remove_project(p) is True

    def test_removes_exa(self):
        p = {'source_type': 'exa'}
        assert should_remove_project(p) is True

    def test_keeps_github(self):
        p = {'source_type': 'github'}
        assert should_remove_project(p) is False

    def test_keeps_official_seed(self):
        p = {'source_type': 'official-seed'}
        assert should_remove_project(p) is False


class TestMigrateProject:
    def test_removes_old_score_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'source_type': 'github',
            'score': {'ecosystem_value': 3, 'activity': 2},
            'score_reason': {'base': 18, 'source_weight': 2},
            'total_score': 20,
            'category': ['mcp-acp-a2a'],
            'record_kind': 'ecosystem-project',
            'ranking_scope': 'ecosystem',
            'source_quality': 'verified',
            'concepts': [],
            'integration_surfaces': [],
            'why_it_matters': 'test',
            'notes': '',
        }
        result = migrate_project(p)
        assert 'score' not in result  # old 6-dim score removed
        assert 'score_reason' not in result
        assert 'category' not in result  # replaced by resource_type
        assert 'record_kind' not in result
        assert 'ranking_scope' not in result
        assert 'source_quality' not in result
        assert 'concepts' not in result
        assert 'integration_surfaces' not in result
        assert 'why_it_matters' not in result
        assert 'notes' not in result

    def test_adds_new_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'source_type': 'github',
            'category': ['mcp-acp-a2a', 'skills-prompts'],
            'target_tools': ['claude-code'],
            'stars': 500,
            'forks': 10,
        }
        result = migrate_project(p)
        assert 'resource_type' in result
        assert 'quantifiable_score' in result
        assert result['quantifiable_score'] >= 0
        assert result['quantifiable_score'] <= 60
        assert 'quality_score' in result
        assert result['quality_score'] == 0  # placeholder until LLM analysis
        assert 'total_score' in result
        assert result['total_score'] == result['quantifiable_score']  # = quantifiable + 0
        assert 'tracking_priority' in result
        assert result['tracking_priority'] == 'pending'
        assert 'last_analyzed' in result
        assert result['last_analyzed'] is None
        assert 'benchmark_ref' in result
        assert result['benchmark_ref'] is None

    def test_migrates_category_to_resource_type(self):
        p = {
            'id': 'test',
            'name': 'Test MCP Server',
            'source_type': 'github',
            'category': ['mcp-acp-a2a'],
            'target_tools': ['claude-code'],
        }
        result = migrate_project(p)
        assert 'mcp-server' in result['resource_type']

    def test_migrates_multiple_categories(self):
        p = {
            'id': 'test',
            'name': 'Claude Skills Collection',
            'source_type': 'github',
            'category': ['skills-prompts', 'mcp-acp-a2a'],
            'target_tools': ['claude-code'],
        }
        result = migrate_project(p)
        assert 'skills' in result['resource_type']
        assert 'mcp-server' in result['resource_type']

    def test_official_tool_preserved(self):
        p = {
            'id': 'claude-code',
            'name': 'Claude Code',
            'source_type': 'official-seed',
            'category': ['official-tool'],
            'target_tools': ['claude-code'],
            'stars': 50000,
        }
        result = migrate_project(p)
        assert result['tracking_priority'] == 'track'
        assert result['source_type'] == 'official-seed'

    def test_preserves_retained_fields(self):
        p = {
            'id': 'test',
            'name': 'Test',
            'url': 'https://github.com/owner/repo',
            'repo': 'owner/repo',
            'source_type': 'github',
            'summary': 'A test project',
            'i18n': {'zh': {'name': 'Test', 'summary': 'A test project'}, 'en': {'name': 'Test', 'summary': 'A test project'}},
            'status': 'active',
            'stars': 1000,
            'forks': 50,
            'last_updated': '2025-06-01T00:00:00Z',
            'first_seen': '2025-06-01',
            'last_seen': '2025-07-12',
            'maturity': 'stable',
            'languages': ['Python'],
            'tags': ['ai'],
            'target_tools': ['claude-code'],
            'review_state': 'auto-indexed',
            'license': 'MIT',
        }
        result = migrate_project(p)
        for field in ['id', 'name', 'url', 'repo', 'source_type', 'summary', 'i18n',
                       'status', 'stars', 'forks', 'last_updated', 'first_seen',
                       'last_seen', 'maturity', 'languages', 'tags', 'target_tools',
                       'review_state', 'license']:
            assert field in result, f'{field} should be preserved'
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_migrate_data.py -v`
预期：FAIL，报错 `No module named 'migrate_data'`

- [ ] **步骤 3：编写 migrate_data.py 实现**

```python
#!/usr/bin/env python3
"""Migrate data from old schema to new 100-point schema.

Removes Exa/fallback-web records, strips old score fields,
adds new fields (resource_type, quantifiable_score, tracking_priority, etc.).
"""
import argparse
import json
import datetime
from pathlib import Path

# Category to resource_type mapping
CATEGORY_TO_RESOURCE_TYPE = {
    'mcp-acp-a2a': 'mcp-server',
    'skills-prompts': 'skills',
    'rules-instructions': 'rules',
    'agent-harness': 'agent-framework',
    'terminal-agent': 'cli-tool',
    'tutorial-case-study': 'tutorial',
    'context-engineering': 'cli-tool',  # context tools are often CLI-based
    'testing-review-ci': 'agent-framework',  # testing/review agents are frameworks
    'benchmark-evaluation': 'tutorial',  # benchmarks are reference resources
    'ai-ide': 'cli-tool',  # IDE-related tools
    'official-tool': 'cli-tool',
    'persistent-agent': 'agent-framework',
}

# Fields to remove from old schema
OLD_FIELDS_TO_REMOVE = [
    'score', 'score_reason', 'category', 'record_kind', 'ranking_scope',
    'source_quality', 'concepts', 'integration_surfaces',
    'why_it_matters', 'notes', 'recommendation_level',
]


def should_remove_project(p):
    """Return True if project should be removed (Exa/fallback-web sources)."""
    return p.get('source_type') in ('fallback-web', 'exa')


def migrate_category_to_resource_type(p):
    """Convert old category list to new resource_type list."""
    old_cats = p.get('category', [])
    resource_types = []
    for cat in old_cats:
        rt = CATEGORY_TO_RESOURCE_TYPE.get(cat)
        if rt and rt not in resource_types:
            resource_types.append(rt)
    return resource_types if resource_types else ['tutorial']  # default fallback


def calc_quantifiable_score(p):
    """Calculate the 60-point quantifiable score.

    Stars (20) + Activity (15) + Adoption (10) + Maturity (15)
    """
    # Stars: 0-20
    stars = p.get('stars') or 0
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0
    if stars >= 50000:
        stars_score = 20
    elif stars >= 10000:
        stars_score = 16
    elif stars >= 5000:
        stars_score = 12
    elif stars >= 1000:
        stars_score = 8
    elif stars >= 100:
        stars_score = 4
    elif stars > 0:
        stars_score = 2
    else:
        stars_score = 0

    # Activity: 0-15, based on last_updated/pushed_at
    activity_score = 1  # default for unknown
    last_updated = p.get('last_updated') or p.get('last_seen') or ''
    if last_updated:
        try:
            # Parse ISO date, handle both date and datetime
            date_str = last_updated[:10]
            d = datetime.date.fromisoformat(date_str)
            now = datetime.date.today()
            days_ago = (now - d).days
            if days_ago <= 90:
                activity_score = 15
            elif days_ago <= 180:
                activity_score = 12
            elif days_ago <= 365:
                activity_score = 8
            elif days_ago <= 730:
                activity_score = 4
            else:
                activity_score = 1
        except (ValueError, TypeError):
            activity_score = 1

    # Adoption: 0-10, based on forks
    forks = p.get('forks') or 0
    try:
        forks = int(forks)
    except (TypeError, ValueError):
        forks = 0
    if forks >= 1000:
        adoption_score = 10
    elif forks >= 100:
        adoption_score = 7
    elif forks >= 10:
        adoption_score = 4
    elif forks > 0:
        adoption_score = 2
    else:
        adoption_score = 0

    # Maturity: 0-15
    maturity_score = 0
    if p.get('license'):
        maturity_score += 2
    if p.get('status') and p.get('status') not in ('unknown',):
        maturity_score += 3  # has explicit status (not just 'unknown')
    if p.get('languages'):
        maturity_score += 2
    # Check for release-like indicators
    if p.get('tags'):
        for tag in (p.get('tags') or []):
            if 'release' in tag.lower() or 'v1' in tag.lower() or 'stable' in tag.lower():
                maturity_score += 3
                break
    if p.get('maturity') and p.get('maturity') not in ('unknown',):
        maturity_score += 5
    maturity_score = min(maturity_score, 15)

    return stars_score + activity_score + adoption_score + maturity_score


def migrate_project(p):
    """Migrate a single project from old schema to new schema."""
    result = {}

    # Copy retained fields
    retained_fields = [
        'id', 'name', 'url', 'repo', 'source_type', 'summary', 'i18n',
        'status', 'stars', 'forks', 'last_updated', 'first_seen', 'last_seen',
        'maturity', 'languages', 'tags', 'target_tools', 'review_state', 'license',
    ]
    for field in retained_fields:
        if field in p:
            result[field] = p[field]

    # Migrate category -> resource_type
    result['resource_type'] = migrate_category_to_resource_type(p)

    # Calculate scores
    result['quantifiable_score'] = calc_quantifiable_score(p)
    result['quality_score'] = 0  # placeholder, filled by weekly LLM analysis
    result['total_score'] = result['quantifiable_score']  # = quantifiable + 0

    # Score detail
    result['score_detail'] = {
        'stars': min(20, result['quantifiable_score']),  # simplified for now
    }

    # New tracking fields
    result['tracking_priority'] = 'pending'
    if p.get('source_type') == 'official-seed':
        result['tracking_priority'] = 'track'
    result['last_analyzed'] = None
    result['benchmark_ref'] = None

    return result


def main():
    ap = argparse.ArgumentParser(description='Migrate data from old schema to new 100-point schema')
    ap.add_argument('--dry-run', action='store_true', help='Print stats without writing')
    ap.add_argument('--input', default='data/projects.yaml', help='Input file')
    ap.add_argument('--output', default='data/projects.yaml', help='Output file')
    args = ap.parse_args()

    root = Path(__file__).resolve().parents[1]
    in_path = root / args.input
    if not in_path.exists():
        print(f'Error: {in_path} not found')
        return

    # Load (handle both JSON and YAML)
    import yaml
    with open(in_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    projects = data if isinstance(data, list) else data.get('projects', [])

    original_count = len(projects)

    # Separate keep vs remove
    keep = []
    removed = 0
    for p in projects:
        if should_remove_project(p):
            removed += 1
        else:
            keep.append(migrate_project(p))

    stats = {
        'original': original_count,
        'removed': removed,
        'kept': len(keep),
        'by_source': {},
    }
    for p in keep:
        src = p.get('source_type', 'unknown')
        stats['by_source'][src] = stats['by_source'].get(src, 0) + 1

    print(json.dumps(stats, ensure_ascii=False, indent=2))

    if not args.dry_run:
        with open(in_path if args.output == args.input else root / args.output, 'w', encoding='utf-8') as f:
            yaml.dump(keep, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f'Written {len(keep)} projects to {args.output}')


if __name__ == '__main__':
    main()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_migrate_data.py -v`
预期：PASS，全部测试通过

- [ ] **步骤 5：执行数据迁移**

运行：`cd "/root/workspace/search in coding" && python3 scripts/migrate_data.py --dry-run`
预期：输出统计信息，original=618, removed=344 (197 exa + 147 fallback-web), kept=274

然后执行实际迁移：
运行：`cd "/root/workspace/search in coding" && python3 scripts/migrate_data.py`
预期：写入 274 条迁移后的数据

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/migrate_data.py tests/test_migrate_data.py data/projects.yaml
git commit -m "feat: migrate data to new 100-point schema (remove Exa/fallback-web, add resource_type/tracking_priority)"
```

---

## 任务 2：新评分配置文件

**文件：**
- 创建：`config/scoring-v2.yaml`
- 创建：`tests/test_score_v2.py`

- [ ] **步骤 1：编写评分配置和评分测试**

```python
# tests/test_score_v2.py
"""Test the new 100-point scoring system (quantifiable part only)."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from migrate_data import calc_quantifiable_score


class TestStarsScore:
    def test_50k_stars(self):
        p = {'stars': 50000}
        score = calc_quantifiable_score(p)
        # stars component should be 20, plus default activity=1, maturity varies
        assert score >= 20

    def test_10k_stars(self):
        p = {'stars': 10000}
        score = calc_quantifiable_score(p)
        assert score >= 16

    def test_1k_stars(self):
        p = {'stars': 1000}
        score = calc_quantifiable_score(p)
        assert score >= 8

    def test_0_stars(self):
        p = {'stars': 0}
        score = calc_quantifiable_score(p)
        # stars=0, activity=1 (default), adoption=0, maturity=0
        assert score >= 1  # at least default activity

    def test_none_stars(self):
        p = {'stars': None}
        score = calc_quantifiable_score(p)
        assert score >= 1


class TestActivityScore:
    def test_recent_project(self):
        p = {'stars': 0, 'last_updated': '2025-07-01T00:00:00Z'}
        score = calc_quantifiable_score(p)
        # activity=15 for <90 days
        assert score >= 15

    def test_old_project(self):
        p = {'stars': 0, 'last_updated': '2024-01-01T00:00:00Z'}
        score = calc_quantifiable_score(p)
        # activity=1 for >2 years
        assert score <= 3  # activity=1 + minimal others


class TestAdoptionScore:
    def test_high_forks(self):
        p = {'stars': 0, 'forks': 1000}
        score = calc_quantifiable_score(p)
        assert score >= 10  # adoption=10

    def test_no_forks(self):
        p = {'stars': 0, 'forks': 0}
        score = calc_quantifiable_score(p)
        assert score >= 1  # just default activity


class TestTotalScoreRange:
    def test_max_score(self):
        p = {
            'stars': 50000,
            'forks': 1000,
            'last_updated': '2025-07-01T00:00:00Z',
            'license': 'MIT',
            'maturity': 'stable',
            'languages': ['Python'],
            'status': 'active',
        }
        score = calc_quantifiable_score(p)
        assert score <= 60
        assert score >= 40  # should be high

    def test_min_score(self):
        p = {'stars': 0, 'forks': 0}
        score = calc_quantifiable_score(p)
        assert score >= 1  # at least default activity
        assert score <= 5
```

- [ ] **步骤 2：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_score_v2.py -v`
预期：PASS（calc_quantifiable_score 已在 migrate_data.py 中实现）

- [ ] **步骤 3：创建 scoring-v2.yaml 配置**

```yaml
# config/scoring-v2.yaml
# New 100-point scoring system configuration
# Quantifiable score (60 points) - updated daily
# Quality score (40 points) - updated weekly by LLM (not in this batch)

quantifiable:
  stars:
    max: 20
    tiers:
      - {min: 50000, score: 20}
      - {min: 10000, score: 16}
      - {min: 5000, score: 12}
      - {min: 1000, score: 8}
      - {min: 100, score: 4}
      - {min: 1, score: 2}
      - {min: 0, score: 0}

  activity:
    max: 15
    tiers:
      - {days: 90, score: 15}
      - {days: 180, score: 12}
      - {days: 365, score: 8}
      - {days: 730, score: 4}
      - {days: 99999, score: 1}

  adoption:
    max: 10
    tiers:
      - {min: 1000, score: 10}
      - {min: 100, score: 7}
      - {min: 10, score: 4}
      - {min: 1, score: 2}
      - {min: 0, score: 0}

  maturity:
    max: 15
    components:
      has_license: 2
      has_explicit_status: 3
      has_languages: 2
      has_release_tag: 3
      has_maturity_label: 5

quality:
  # Placeholder - filled by weekly LLM analysis in batch 3
  max: 40
  dimensions:
    relevance: {max: 10}
    practicality: {max: 10}
    novelty: {max: 10}
    ecosystem_value: {max: 10}

benchmark_ranges:
  - {range: [81, 100], label: "标杆", description: "生态标杆项目"}
  - {range: [61, 80], label: "优秀", description: "高质量生态项目"}
  - {range: [41, 60], label: "可用", description: "可用项目"}
  - {range: [21, 40], label: "萌芽", description: "早期项目"}
  - {range: [0, 20], label: "噪声", description: "低质量或无关项目"}
```

- [ ] **步骤 4：Commit**

```bash
cd "/root/workspace/search in coding"
git add config/scoring-v2.yaml tests/test_score_v2.py
git commit -m "feat: add 100-point scoring config (quantifiable 60 + quality 40 placeholder)"
```

---

## 任务 3：重写 score.py

**文件：**
- 修改：`scripts/score.py`
- 创建：`tests/test_score_main.py`

- [ ] **步骤 1：编写 score.py 重写后的测试**

```python
# tests/test_score_main.py
"""Test the rewritten score.py main function."""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestScoreV2Main:
    def test_scores_all_projects(self, tmp_path, monkeypatch):
        """score.py should process all projects and update quantifiable_score."""
        from common import ROOT
        import score

        # Create a minimal test projects.yaml
        test_projects = [
            {
                'id': 'test-1',
                'name': 'Test Project',
                'source_type': 'github',
                'stars': 1000,
                'forks': 50,
                'last_updated': '2025-07-01T00:00:00Z',
                'target_tools': ['claude-code'],
                'resource_type': ['mcp-server'],
                'tracking_priority': 'pending',
                'license': 'MIT',
            },
        ]

        # Mock load_jsonish to return our test data
        def mock_load(rel):
            if rel == 'data/projects.yaml':
                return test_projects
            if rel == 'config/scoring-v2.yaml':
                return {}
            return []

        def mock_save(rel, data):
            pass

        monkeypatch.setattr(score, 'load_jsonish', mock_load)
        monkeypatch.setattr(score, 'save_jsonish', mock_save)

        score.main()

        p = test_projects[0]
        assert 'quantifiable_score' in p
        assert p['quantifiable_score'] > 0
        assert p['quantifiable_score'] <= 60
        assert p['total_score'] == p['quantifiable_score']  # quality_score = 0
        assert 'score_detail' in p

    def test_updates_existing_quality_score(self, tmp_path, monkeypatch):
        """If a project already has quality_score from LLM, preserve it."""
        from common import ROOT
        import score

        test_projects = [
            {
                'id': 'test-1',
                'name': 'Test',
                'source_type': 'github',
                'stars': 500,
                'forks': 10,
                'last_updated': '2025-07-01T00:00:00Z',
                'target_tools': ['claude-code'],
                'resource_type': ['skills'],
                'tracking_priority': 'track',
                'quality_score': 30,  # pre-existing from LLM
            },
        ]

        def mock_load(rel):
            if rel == 'data/projects.yaml':
                return test_projects
            return []

        def mock_save(rel, data):
            pass

        monkeypatch.setattr(score, 'load_jsonish', mock_load)
        monkeypatch.setattr(score, 'save_jsonish', mock_save)

        score.main()

        p = test_projects[0]
        assert p['quality_score'] == 30  # preserved
        assert p['total_score'] == p['quantifiable_score'] + 30
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_score_main.py -v`
预期：FAIL（score.py 还是旧版本）

- [ ] **步骤 3：重写 score.py**

```python
#!/usr/bin/env python3
"""Score projects with the new 100-point system.

Quantifiable score (60 points): Stars + Activity + Adoption + Maturity
Quality score (40 points): Preserved from weekly LLM analysis (0 if not yet analyzed)
Total = Quantifiable + Quality
"""
import argparse
import datetime
import json

from common import load_jsonish, save_jsonish
from migrate_data import calc_quantifiable_score


def score_detail_for(p):
    """Return detailed breakdown of the quantifiable score."""
    stars = p.get('stars') or 0
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0

    if stars >= 50000:
        stars_s = 20
    elif stars >= 10000:
        stars_s = 16
    elif stars >= 5000:
        stars_s = 12
    elif stars >= 1000:
        stars_s = 8
    elif stars >= 100:
        stars_s = 4
    elif stars > 0:
        stars_s = 2
    else:
        stars_s = 0

    last_updated = p.get('last_updated') or p.get('last_seen') or ''
    activity_s = 1
    if last_updated:
        try:
            d = datetime.date.fromisoformat(last_updated[:10])
            days = (datetime.date.today() - d).days
            if days <= 90:
                activity_s = 15
            elif days <= 180:
                activity_s = 12
            elif days <= 365:
                activity_s = 8
            elif days <= 730:
                activity_s = 4
        except (ValueError, TypeError):
            pass

    forks = p.get('forks') or 0
    try:
        forks = int(forks)
    except (TypeError, ValueError):
        forks = 0
    if forks >= 1000:
        adoption_s = 10
    elif forks >= 100:
        adoption_s = 7
    elif forks >= 10:
        adoption_s = 4
    elif forks > 0:
        adoption_s = 2
    else:
        adoption_s = 0

    maturity_s = 0
    if p.get('license'):
        maturity_s += 2
    if p.get('status') and p.get('status') not in ('unknown',):
        maturity_s += 3
    if p.get('languages'):
        maturity_s += 2
    if p.get('tags'):
        for tag in (p.get('tags') or []):
            if 'release' in tag.lower() or 'v1' in tag.lower() or 'stable' in tag.lower():
                maturity_s += 3
                break
    if p.get('maturity') and p.get('maturity') not in ('unknown',):
        maturity_s += 5
    maturity_s = min(maturity_s, 15)

    return {
        'stars': stars_s,
        'activity': activity_s,
        'adoption': adoption_s,
        'maturity': maturity_s,
    }


def main():
    ap = argparse.ArgumentParser(description='Score projects with 100-point system (quantifiable only)')
    ap.parse_args()

    projects = load_jsonish('data/projects.yaml')

    for p in projects:
        # Calculate quantifiable score
        detail = score_detail_for(p)
        q_score = sum(detail.values())
        p['quantifiable_score'] = q_score
        p['score_detail'] = detail

        # Preserve existing quality_score or default to 0
        if 'quality_score' not in p:
            p['quality_score'] = 0

        # Total = quantifiable + quality
        p['total_score'] = q_score + p['quality_score']

    save_jsonish('data/projects.yaml', projects)

    stats = {
        'scored': len(projects),
        'avg_score': round(sum(p.get('total_score', 0) for p in projects) / max(len(projects), 1), 1),
        'max_score': max((p.get('total_score', 0) for p in projects), default=0),
        'min_score': min((p.get('total_score', 0) for p in projects), default=0),
    }
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == '__main__':
    main()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_score_main.py -v`
预期：PASS

- [ ] **步骤 5：运行 score.py 对迁移后的数据**

运行：`cd "/root/workspace/search in coding" && python3 scripts/score.py`
预期：输出评分统计，274 条项目全部评分

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/score.py tests/test_score_main.py data/projects.yaml
git commit -m "feat: rewrite score.py for 100-point quantifiable scoring (60/60)"
```

---

## 任务 4：适配 normalize.py

**文件：**
- 修改：`scripts/normalize.py`

- [ ] **步骤 1：移除 from_exa() 和 from_web()，重构 github_record()**

修改 `scripts/normalize.py`：

1. 删除 `from_exa()` 函数（约 46 行）
2. 删除 `from_web()` 函数（约 43 行）
3. 修改 `github_record()` 中的字段：移除 `category`/`concepts`/`integration_surfaces`/`why_it_matters`/`notes`/`score`，新增 `resource_type`/`tracking_priority`/`quantifiable_score`/`quality_score`/`total_score`/`last_analyzed`/`benchmark_ref`
4. 修改 `main()` 中 `--source` 选项只保留 `all` 和 `github`
5. 修改 `categories_for()` 重命名为 `resource_types_for()`，返回新标签

具体修改后的 `github_record()`：

```python
def resource_types_for(text):
    """Determine resource_type tags from project text."""
    low = text.lower()
    types = []
    if any(x in low for x in ['mcp server', 'model context protocol', 'mcp']):
        types.append('mcp-server')
    if any(x in low for x in ['skill', 'prompt pack', 'slash command', 'custom command']):
        types.append('skills')
    if any(x in low for x in ['cursor rules', '.cursorrules', 'agents.md', 'claude.md', 'rules']):
        types.append('rules')
    if any(x in low for x in ['agent framework', 'multi-agent', 'subagent', 'agent orchestration']):
        types.append('agent-framework')
    if any(x in low for x in ['cli', 'terminal', 'command line']):
        types.append('cli-tool')
    if any(x in low for x in ['tutorial', 'guide', 'best practice', 'case study']):
        types.append('tutorial')
    return types or ['tutorial']


def github_record(it, tools):
    fn = it.get('fullName') or it.get('nameWithOwner')
    url = it.get('url') or (f'https://github.com/{fn}' if fn else None)
    name = fn or it.get('name') or url
    if not url or not name:
        return None
    desc = it.get('description') or ''
    text = f'{name} {desc}'
    stars = it.get('stargazersCount', it.get('stargazerCount'))
    summary = desc[:240] or name
    return {
        'id': slug('github-' + name),
        'name': name,
        'url': url,
        'repo': fn,
        'source_type': 'github',
        'resource_type': resource_types_for(text),
        'target_tools': target_tools_for(text, tools),
        'summary': summary,
        'i18n': i18n_fields(name, summary),
        'status': 'archived' if it.get('isArchived') else 'unknown',
        'license': (it.get('licenseInfo') or {}).get('spdxId') if isinstance(it.get('licenseInfo'), dict) else None,
        'stars': stars,
        'forks': it.get('forkCount'),
        'last_updated': it.get('updatedAt') or it.get('pushedAt'),
        'first_seen': None,
        'last_seen': None,
        'maturity': 'unknown',
        'languages': [it.get('language') or ((it.get('primaryLanguage') or {}).get('name') if isinstance(it.get('primaryLanguage'), dict) else None)],
        'tags': [],
        'review_state': 'auto-indexed',
        'quantifiable_score': 0,  # will be calculated by score.py
        'quality_score': 0,  # will be filled by weekly LLM analysis
        'total_score': 0,
        'tracking_priority': 'pending',
        'last_analyzed': None,
        'benchmark_ref': None,
    }
```

- [ ] **步骤 2：验证语法**

运行：`cd "/root/workspace/search in coding" && python3 -m py_compile scripts/normalize.py`
预期：无错误

- [ ] **步骤 3：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/normalize.py
git commit -m "refactor: remove Exa/Web collectors from normalize.py, migrate to resource_type"
```

---

## 任务 5：一次性历史回溯采集脚本

**文件：**
- 创建：`scripts/initial_collection.py`
- 创建：`tests/test_initial_collection.py`

- [ ] **步骤 1：编写回溯采集测试**

```python
# tests/test_initial_collection.py
"""Test the initial bulk collection script."""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class TestQueryGeneration:
    def test_generates_topic_queries(self):
        from initial_collection import generate_topic_queries
        queries = generate_topic_queries()
        assert len(queries) > 0
        # Should include tool-specific topics
        assert any('claude-code' in q for q in queries)
        assert any('mcp-server' in q for q in queries)

    def test_generates_keyword_queries(self):
        from initial_collection import generate_keyword_queries
        queries = generate_keyword_queries()
        assert len(queries) > 0
        assert any('claude code' in q for q in queries)

    def test_generates_code_search_queries(self):
        from initial_collection import generate_code_search_queries
        queries = generate_code_search_queries()
        assert len(queries) > 0
        assert any('CLAUDE.md' in q for q in queries)

    def test_month_ranges(self):
        from initial_collection import generate_month_ranges
        ranges = generate_month_ranges('2025-01', '2025-07')
        assert len(ranges) == 7  # Jan to Jul
        assert ranges[0] == ('2025-01-01', '2025-01-31')
        assert ranges[-1] == ('2025-07-01', '2025-07-31')


class TestCheckpointManager:
    def test_save_and_load_checkpoint(self, tmp_path):
        from initial_collection import CheckpointManager
        ckpt = CheckpointManager(tmp_path / 'checkpoint.json')
        ckpt.save('topic:claude-code', '2025-01', 2, 50)
        assert ckpt.is_done('topic:claude-code', '2025-01')
        assert not ckpt.is_done('topic:claude-code', '2025-02')

    def test_get_progress(self, tmp_path):
        from initial_collection import CheckpointManager
        ckpt = CheckpointManager(tmp_path / 'checkpoint.json')
        ckpt.save('q1', '2025-01', 1, 30)
        ckpt.save('q2', '2025-01', 1, 20)
        progress = ckpt.get_progress()
        assert progress['total_queries'] == 2
        assert progress['total_results'] == 50
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_initial_collection.py -v`
预期：FAIL，`No module named 'initial_collection'`

- [ ] **步骤 3：编写 initial_collection.py**

```python
#!/usr/bin/env python3
"""One-time historical bulk collection of GitHub projects.

Searches GitHub for AI coding agent ecosystem projects from 2025-01 to present.
Uses four search strategies: topic search, keyword search, dependents, code search.
Supports checkpoint/resume for interrupted runs.

Usage:
    python3 scripts/initial_collection.py --start 2025-01 --end 2025-07
    python3 scripts/initial_collection.py --resume  # resume from checkpoint
"""
import argparse
import json
import datetime
from pathlib import Path

from common import ROOT, load_jsonish, save_jsonish, slug, run, today

CHECKPOINT_FILE = ROOT / 'data' / 'initial-collection-checkpoint.json'
OUTPUT_DIR = ROOT / 'data' / 'raw' / 'github-initial'


def generate_topic_queries():
    """Generate GitHub topic search queries."""
    topics = [
        'claude-code', 'cursor-rules', 'mcp-server', 'agent-skills',
        'ai-coding', 'coding-agent', 'agentic-coding',
        'claude-skills', 'cursor-mcp', 'codex-cli',
        'gemini-cli', 'opencode', 'goose-ai',
    ]
    return [f'topic:{t}' for t in topics]


def generate_keyword_queries():
    """Generate keyword search queries."""
    return [
        '"claude code" skills',
        '"claude code" mcp',
        '"claude code" hooks',
        '"cursor rules" mdc',
        '"cursor" mcp server',
        '"codex cli" AGENTS.md',
        '"codex" skills',
        '"gemini cli" extension',
        '"gemini cli" mcp',
        'opencode agent commands',
        'opencode mcp',
        'goose recipes extensions',
        'goose mcp agent',
        'qoder ai coding',
        'trae agent mcp',
        'workbuddy agent skills',
        'codebuddy agent',
        'hermes agent skills',
        'hermes agent cron',
        'AI coding agent context engineering',
        'mcp server coding agent',
        'AI PR review agent',
        'spec driven development AI coding',
        'codebase indexing AI coding agent',
    ]


def generate_code_search_queries():
    """Generate code search queries for config file discovery."""
    return [
        'filename:CLAUDE.md',
        'filename:.cursorrules',
        'filename:AGENTS.md',
        'filename:.mdc path:.cursor/rules',
        'mcpServers extension:json',
    ]


def generate_dependents_targets():
    """Official repos to fetch dependents for."""
    tools = load_jsonish('data/seed-tools.yaml')
    return [t['repo'] for t in tools if t.get('repo')]


def generate_month_ranges(start, end):
    """Generate list of (first_day, last_day) tuples for each month."""
    start_year, start_month = int(start[:4]), int(start[5:7])
    end_year, end_month = int(end[:4]), int(end[5:7])
    ranges = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        first = datetime.date(y, m, 1)
        if m == 12:
            last = datetime.date(y, 12, 31)
        else:
            last = datetime.date(y, m + 1, 1) - datetime.timedelta(days=1)
        ranges.append((first.isoformat(), last.isoformat()))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return ranges


class CheckpointManager:
    """Manage checkpoint for resume support."""

    def __init__(self, path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self):
        if self.path.exists():
            return json.loads(self.path.read_text(encoding='utf-8'))
        return {'completed': {}, 'stats': {'total_queries': 0, 'total_results': 0}}

    def save(self, query, month_range, pages, results_count):
        key = f'{query}::{month_range}'
        self.data['completed'][key] = {
            'query': query,
            'month': month_range,
            'pages': pages,
            'results': results_count,
            'timestamp': datetime.datetime.now().isoformat(),
        }
        self.data['stats']['total_queries'] = len(self.data['completed'])
        self.data['stats']['total_results'] += results_count
        self._write()

    def is_done(self, query, month_range):
        key = f'{query}::{month_range}'
        return key in self.data['completed']

    def get_progress(self):
        return {
            'total_queries': len(self.data['completed']),
            'total_results': self.data['stats']['total_results'],
        }

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')


def gh_search_repos(query, created_range, sort='stars', limit=100, page=1):
    """Search GitHub repos with date range filter."""
    start, end = created_range
    full_query = f'{query} created:{start}..{end}'
    fields = 'fullName,description,stargazersCount,url,updatedAt,language,forkCount,isArchived'
    cmd = f'gh search repos {json.dumps(full_query)} --sort {sort} --limit {limit} --page {page} --json {fields}'
    r = run(cmd, timeout=180)
    if r.returncode != 0:
        return [], r.stderr
    return json.loads(r.stdout or '[]'), None


def gh_search_code(query, limit=100, page=1):
    """Search GitHub code for config file discovery."""
    cmd = f'gh search code {json.dumps(query)} --limit {limit} --page {page} --json repository,path'
    r = run(cmd, timeout=180)
    if r.returncode != 0:
        return [], r.stderr
    return json.loads(r.stdout or '[]'), None


def collect_topic_and_keyword(queries, month_ranges, checkpoint, outdir):
    """Run topic and keyword searches across all month ranges."""
    all_repos = set()  # use fullName for dedup

    for query in queries:
        for mr in month_ranges:
            mr_key = f'{mr[0]}..{mr[1]}'
            if checkpoint.is_done(query, mr_key):
                continue

            total_results = 0
            for page in range(1, 4):  # max 3 pages
                results, err = gh_search_repos(query, mr, page=page, limit=100)
                if err:
                    print(f'  ERROR: {query} {mr_key} page {page}: {err[:200]}')
                    break
                if not results:
                    break
                total_results += len(results)
                for r in results:
                    fn = r.get('fullName')
                    if fn:
                        all_repos.add(fn)

            checkpoint.save(query, mr_key, min(3, (total_results // 100) + 1), total_results)
            print(f'  {query} [{mr_key}]: {total_results} results')

    return all_repos


def collect_code_search(checkpoint, outdir):
    """Run code searches to find repos with specific config files."""
    queries = generate_code_search_queries()
    all_repos = set()

    for query in queries:
        if checkpoint.is_done(query, 'code-search'):
            continue
        total = 0
        for page in range(1, 4):
            results, err = gh_search_code(query, page=page, limit=100)
            if err or not results:
                break
            total += len(results)
            for r in results:
                repo = r.get('repository', {})
                fn = repo.get('nameWithOwner')
                if fn:
                    all_repos.add(fn)
        checkpoint.save(query, 'code-search', 1, total)
        print(f'  code:{query}: {total} results, {len(all_repos)} unique repos')

    return all_repos


def main():
    ap = argparse.ArgumentParser(description='One-time bulk GitHub collection')
    ap.add_argument('--start', default='2025-01', help='Start month YYYY-MM')
    ap.add_argument('--end', default='2025-07', help='End month YYYY-MM')
    ap.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    ap.add_argument('--dry-run', action='store_true', help='Print queries without executing')
    args = ap.parse_args()

    if args.dry_run:
        print('Topic queries:', generate_topic_queries())
        print('Keyword queries:', generate_keyword_queries())
        print('Code search queries:', generate_code_search_queries())
        print('Dependents targets:', generate_dependents_targets())
        print('Month ranges:', generate_month_ranges(args.start, args.end))
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = CheckpointManager(CHECKPOINT_FILE)
    month_ranges = generate_month_ranges(args.start, args.end)

    print(f'=== Initial Collection: {args.start} to {args.end} ===')
    print(f'Month ranges: {len(month_ranges)}')

    # Phase 1: Topic + Keyword searches
    print('\n--- Phase 1: Topic + Keyword searches ---')
    topic_queries = generate_topic_queries()
    keyword_queries = generate_keyword_queries()
    all_queries = topic_queries + keyword_queries
    print(f'Queries: {len(all_queries)} x {len(month_ranges)} months = {len(all_queries) * len(month_ranges)} search operations')

    repo_set_1 = collect_topic_and_keyword(all_queries, month_ranges, checkpoint, OUTPUT_DIR)

    # Phase 2: Code search
    print('\n--- Phase 2: Code search ---')
    repo_set_2 = collect_code_search(checkpoint, OUTPUT_DIR)

    # Merge all unique repos
    all_repos = repo_set_1 | repo_set_2
    print(f'\n=== Summary ===')
    print(f'Topic/keyword unique repos: {len(repo_set_1)}')
    print(f'Code search unique repos: {len(repo_set_2)}')
    print(f'Total unique repos: {len(all_repos)}')

    # Save repo list for enrichment (repo_view to get full details)
    repo_list_file = OUTPUT_DIR / 'unique-repos.json'
    repo_list_file.write_text(json.dumps(sorted(all_repos), ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Repo list saved to: {repo_list_file}')

    # Phase 3: Fetch details for each repo (this is the slow part)
    print(f'\n--- Phase 3: Fetching details for {len(all_repos)} repos ---')
    details = []
    from normalize import github_record
    tools = load_jsonish('data/seed-tools.yaml')

    for i, fn in enumerate(sorted(all_repos)):
        if (i + 1) % 50 == 0:
            print(f'  Progress: {i+1}/{len(all_repos)}')
        # Use gh repo view to get full details
        fields = 'nameWithOwner,description,url,homepageUrl,stargazerCount,forkCount,licenseInfo,repositoryTopics,primaryLanguage,pushedAt,createdAt,updatedAt,isArchived,latestRelease'
        cmd = f'gh repo view {fn} --json {fields}'
        r = run(cmd, timeout=60)
        if r.returncode != 0:
            continue
        try:
            detail = json.loads(r.stdout or '{}')
            details.append(detail)
        except json.JSONDecodeError:
            continue

    # Save raw details
    details_file = OUTPUT_DIR / 'repo-details.json'
    details_file.write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Details saved: {len(details)} repos')

    # Normalize into projects format
    records = []
    for it in details:
        rec = github_record(it, tools)
        if rec:
            records.append(rec)

    # Merge with existing projects (dedup by URL)
    existing = load_jsonish('data/projects.yaml')
    by_url = {r.get('url') or r['id']: r for r in existing}
    now = today()
    for r in records:
        r['first_seen'] = r.get('first_seen') or now
        r['last_seen'] = now
        by_url[r.get('url') or r['id']] = r

    save_jsonish('data/projects.yaml', list(by_url.values()))

    progress = checkpoint.get_progress()
    print(json.dumps({
        'search_operations_completed': progress['total_queries'],
        'total_search_results': progress['total_results'],
        'unique_repos_found': len(all_repos),
        'details_fetched': len(details),
        'records_normalized': len(records),
        'total_projects': len(by_url),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/test_initial_collection.py -v`
预期：PASS

- [ ] **步骤 5：Dry run 验证查询生成**

运行：`cd "/root/workspace/search in coding" && python3 scripts/initial_collection.py --dry-run`
预期：打印所有查询和月度范围

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/initial_collection.py tests/test_initial_collection.py
git commit -m "feat: add initial_collection.py for one-time bulk GitHub collection with checkpoint/resume"
```

---

## 任务 6：适配 build_site.py 和旧前端

**文件：**
- 修改：`scripts/build_site.py`
- 修改：`site/app.js`
- 修改：`site/index.html`

- [ ] **步骤 1：修改 build_site.py 适配新字段**

在 `build_site.py` 中：

1. 将 `p.get('category')` 改为 `p.get('resource_type')`
2. 将 `p.get('total_score')` 保持不变（现在是 0-100 而非 0-30）
3. 移除对 `record_kind`/`ranking_scope`/`source_quality` 的引用
4. 新增 `tracking_priority` 到站点 JSON 输出
5. 新增 `score_detail` 到站点 JSON 输出

关键修改点（在 enrich_project 函数中）：
```python
def enrich_project(p):
    return {
        'id': p.get('id'),
        'name': p.get('name'),
        'url': p.get('url'),
        'repo': p.get('repo'),
        'source_type': p.get('source_type'),
        'resource_type': p.get('resource_type', []),
        'target_tools': p.get('target_tools', []),
        'summary': p.get('summary', ''),
        'i18n': p.get('i18n', {}),
        'stars': p.get('stars'),
        'forks': p.get('forks'),
        'last_updated': p.get('last_updated'),
        'first_seen': p.get('first_seen'),
        'last_seen': p.get('last_seen'),
        'languages': p.get('languages', []),
        'license': p.get('license'),
        'tags': p.get('tags', []),
        'review_state': p.get('review_state'),
        'tracking_priority': p.get('tracking_priority', 'pending'),
        'total_score': p.get('total_score', 0),
        'quantifiable_score': p.get('quantifiable_score', 0),
        'quality_score': p.get('quality_score', 0),
        'score_detail': p.get('score_detail', {}),
        'llm_summary': p.get('llm_summary'),
        'last_analyzed': p.get('last_analyzed'),
    }
```

同时修改 official/ecosystem 过滤逻辑：
```python
# Old: ranking_scope == 'official'
# New: source_type == 'official-seed'
official = [p for p in projects if p.get('source_type') == 'official-seed']
# Old: ranking_scope == 'ecosystem'
# New: tracking_priority != 'reject' and source_type != 'official-seed'
ecosystem = [p for p in projects if p.get('tracking_priority') != 'reject' and p.get('source_type') != 'official-seed']
```

- [ ] **步骤 2：修改 site/app.js 适配新字段**

在 `app.js` 中：

1. `p.category` -> `p.resource_type`
2. `p.source_quality` -> 移除
3. `p.ranking_scope` -> 改为 `p.source_type === 'official-seed'` 判断 official
4. 筛选下拉框 `cat` -> `resource_type`
5. `pills(p.category)` -> `pills(p.resource_type)`

- [ ] **步骤 3：修改 site/index.html**

将 `data-i18n="allCategories"` 相关文本改为"全部类型"，筛选器标签从"分类"改为"类型"。

- [ ] **步骤 4：验证站点构建**

运行：`cd "/root/workspace/search in coding" && python3 scripts/build_site.py`
预期：成功生成 site/data/*.json

- [ ] **步骤 5：验证站点数据**

运行：`cd "/root/workspace/search in coding" && python3 -c "import json; d=json.load(open('site/data/projects.json')); print(f'Projects: {len(d)}'); print(f'Sample: {json.dumps(d[0], ensure_ascii=False, indent=2)[:500]}')"`
预期：274 条项目，字段包含 resource_type/total_score(0-100)/tracking_priority

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/build_site.py site/app.js site/index.html site/data/
git commit -m "feat: adapt build_site.py and frontend to new schema (resource_type, 100-point score)"
```

---

## 任务 7：适配 quality_gate.py、validate_data.py、finalize_data.py、update_tracker.py

**文件：**
- 修改：`scripts/quality_gate.py`
- 修改：`scripts/validate_data.py`
- 修改：`scripts/finalize_data.py`
- 修改：`scripts/update_tracker.py`

- [ ] **步骤 1：修改 validate_data.py**

更新 `PROJECT_REQUIRED` 列表：
```python
PROJECT_REQUIRED = ['id', 'name', 'url', 'source_type', 'resource_type', 'target_tools', 'summary', 'review_state', 'total_score', 'tracking_priority']
```

- [ ] **步骤 2：修改 quality_gate.py**

1. 将 `category` 检查改为 `resource_type`
2. 将 `source_quality` 检查移除
3. 将 `ranking_scope` 检查改为 `source_type == 'official-seed'` / `tracking_priority`
4. 将 `record_kind` 检查移除
5. 更新最低记录数阈值（274 条数据，curated/rejected 需要调整）

- [ ] **步骤 3：修改 finalize_data.py**

1. 将 `category` 引用改为 `resource_type`
2. 将 `ranking_scope` 引用改为 `source_type`/`tracking_priority`
3. 将 `record_kind` 引用移除
4. 将 `score_reason` 引用改为 `score_detail`
5. 调整 curated/rejected 阈值（适应 100 分制）

- [ ] **步骤 4：修改 update_tracker.py**

1. 移除 `collect_exa.py` 调用
2. 移除 `collect_web.py` 调用（已在 normalize.py 中移除 from_exa/from_web）
3. 保留 `collect_github.py` 调用

修改后的步骤列表：
```python
if not args.skip_collect:
    steps.append(run([
        'python3', 'scripts/collect_github.py',
        '--limit', str(args.github_limit),
        '--queries', str(args.github_queries),
    ], required=False, timeout=900))
    steps.append(run(['python3', 'scripts/normalize.py', '--source', 'github'], timeout=600))
```

移除 `--exa-limit` 和 `--exa-queries` 参数。

- [ ] **步骤 5：验证全流程**

运行：`cd "/root/workspace/search in coding" && python3 scripts/update_tracker.py --skip-collect`
预期：全流程通过（normalize -> score -> finalize -> report -> build -> quality_gate）

- [ ] **步骤 6：Commit**

```bash
cd "/root/workspace/search in coding"
git add scripts/quality_gate.py scripts/validate_data.py scripts/finalize_data.py scripts/update_tracker.py
git commit -m "refactor: adapt quality_gate/validate/finalize/update_tracker to new schema"
```

---

## 任务 8：端到端验证和部署

- [ ] **步骤 1：运行完整 pipeline**

运行：`cd "/root/workspace/search in coding" && python3 scripts/update_tracker.py --skip-collect`
预期：全流程 PASS

- [ ] **步骤 2：运行所有测试**

运行：`cd "/root/workspace/search in coding" && python3 -m pytest tests/ -v`
预期：全部 PASS

- [ ] **步骤 3：验证数据完整性**

运行：
```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
print(f'Total: {len(projects)}')
from collections import Counter
src = Counter(p.get('source_type') for p in projects)
print(f'By source: {dict(src)}')
scores = [p.get('total_score',0) for p in projects]
print(f'Score range: {min(scores)}-{max(scores)}, avg={sum(scores)/len(scores):.1f}')
priorities = Counter(p.get('tracking_priority') for p in projects)
print(f'Tracking: {dict(priorities)}')
rt = Counter()
for p in projects:
    for r in (p.get('resource_type') or []):
        rt[r] += 1
print(f'Resource types: {dict(rt)}')
"
```
预期：
- Total: 274
- By source: github 264, official-seed 10
- Score range: 合理范围 (如 1-45)
- Tracking: pending 264, track 10
- Resource types: 各类型有分布

- [ ] **步骤 4：部署站点**

运行：`cd "/root/workspace/search in coding" && python3 scripts/deploy_site.py`
预期：部署到 /var/www/coding.lzpgood.online/

- [ ] **步骤 5：访问站点验证**

在浏览器访问 https://coding.lzpgood.online/
验证：
- 页面正常加载
- 表格显示项目数据
- 分数显示为 0-100 范围
- 筛选器使用 resource_type 而非 category
- 无 JS 错误

- [ ] **步骤 6：Commit 并 tag**

```bash
cd "/root/workspace/search in coding"
git add -A
git commit -m "feat: batch 1 complete - clean data, 100-point scoring, site accessible"
git tag v2025.07.12-batch1
```

- [ ] **步骤 7：更新 Wiki**

更新以下 wiki 文档：
- `wiki/L1-全景.md` - 更新项目状态
- `wiki/L3-代码地图.md` - 更新文件列表（新增 migrate_data.py, initial_collection.py）
- `wiki/L4B-后端详解.md` - 更新评分系统、数据管道流程
- `wiki/L5-接口契约.md` - 更新数据字段结构
- `wiki/L6-经验录.md` - 记录迁移过程中的坑

---

## 验收标准

- [ ] data/projects.yaml 只含 GitHub 来源数据（264 条 + 10 条 official-seed = 274 条）
- [ ] 每条记录有 resource_type（多值）、tracking_priority、quantifiable_score、quality_score(0)、total_score(0-60)
- [ ] 旧字段（score/score_reason/category/record_kind/ranking_scope/source_quality 等）全部移除
- [ ] score.py 正确计算 60 分可量化分
- [ ] initial_collection.py 可 dry-run，生成正确的查询和月度范围
- [ ] 站点正常加载，显示新字段数据
- [ ] 所有测试通过
- [ ] pipeline --skip-collect 全流程 PASS
