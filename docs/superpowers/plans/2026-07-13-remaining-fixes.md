# 遗留项修复 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 修复三批次优化评估报告中发现的遗留问题：seed-tools 路径错误、高星项目分类误标、字段填充不全、detail JSON 缺字段、29 条未翻译 summary。

**架构：** 手动修正 + 脚本批量补全 + pipeline 重建。

**技术栈：** Python 3.12+, GitHub CLI (gh), PyYAML

**关联文档：**
- 评估报告：`docs/evaluation-three-batches-2026-07-13.md`
- 设计规格：`docs/superpowers/specs/2026-07-13-site-optimization-v3-design.md`

---

## 任务 1：修正 seed-tools.yaml repo 路径（A1）

**文件：** `data/seed-tools.yaml`

- [ ] **步骤 1：修正三个 repo 路径**

| 工具 | 当前 | 修正为 |
|------|------|--------|
| goose | aaif-goose/goose | block/goose |
| cursor | cursor/cursor | getcursor/cursor |
| opencode | anomalyco/opencode | sst/opencode |

- [ ] **步骤 2：验证路径正确性**

```bash
cd "/root/workspace/search in coding"
gh repo view block/goose --json nameWithOwner -q .nameWithOwner
gh repo view getcursor/cursor --json nameWithOwner -q .nameWithOwner
gh repo view sst/opencode --json nameWithOwner -q .nameWithOwner
```

- [ ] **步骤 3：Commit**

```bash
git add data/seed-tools.yaml
git commit -m "fix: correct seed-tools repo paths (goose->block/goose, cursor->getcursor/cursor, opencode->sst/opencode)"
```

---

## 任务 2：修正高星项目 resource_type 误标（A4）

**文件：** `data/projects.yaml`

- [ ] **步骤 1：修正 7 个高星项目的 resource_type**

当前误标情况：

| 项目 | Stars | 当前 resource_type | 应改为 |
|------|-------|-------------------|--------|
| aaif-goose/goose | 51152 | ['tutorial'] | ['cli-tool'] |
| continuedev/continue | 34846 | ['tutorial'] | ['cli-tool', 'agent-framework'] |
| cursor/cursor | 33028 | ['tutorial'] | ['cli-tool'] |
| RooCodeInc/Roo-Code | 24329 | ['tutorial'] | ['cli-tool', 'agent-framework'] |
| sanjeed5/awesome-cursor-rules-mdc | 3553 | ['rules', 'tutorial'] | ['rules'] |
| taishi-i/awesome-ChatGPT-repositories | 3123 | ['skills', 'tutorial'] | ['skills'] |
| flyeric0212/cursor-rules | 1872 | ['tutorial'] | ['rules'] |

用 Python 脚本批量修正：

```python
#!/usr/bin/env python3
"""Fix resource_type misclassification for high-star projects."""
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if '__file__' in dir() else Path('.')
# Actually run from project root
import os
os.chdir('/root/workspace/search in coding')

with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)

# Fix mapping: repo -> correct resource_type
fixes = {
    'aaif-goose/goose': ['cli-tool'],
    'continuedev/continue': ['cli-tool', 'agent-framework'],
    'cursor/cursor': ['cli-tool'],
    'RooCodeInc/Roo-Code': ['cli-tool', 'agent-framework'],
    'sanjeed5/awesome-cursor-rules-mdc': ['rules'],
    'taishi-i/awesome-ChatGPT-repositories': ['skills'],
    'flyeric0212/cursor-rules': ['rules'],
}

fixed = 0
for p in projects:
    repo = p.get('repo', '')
    name = p.get('name', '')
    # Match by repo or name
    key = repo if repo in fixes else (name if name in fixes else None)
    if key:
        old = p.get('resource_type', [])
        p['resource_type'] = fixes[key]
        print(f'  Fixed {name}: {old} -> {p["resource_type"]}')
        fixed += 1

print(f'\nTotal fixed: {fixed}')

with open('data/projects.yaml', 'w') as f:
    yaml.dump(projects, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
```

- [ ] **步骤 2：验证修正结果**

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
for p in sorted(projects, key=lambda x: x.get('stars',0) or 0, reverse=True)[:30]:
    rts = p.get('resource_type',[])
    stars = p.get('stars',0) or 0
    if stars > 1000 and 'tutorial' in rts:
        print(f'  ⚠️ Still tutorial: {p[\"name\"]} ({stars}⭐): {rts}')
print('Check complete - no output above means all fixed')
"
```

- [ ] **步骤 3：Commit**

```bash
git add data/projects.yaml
git commit -m "fix: correct resource_type for 7 high-star projects (tutorial -> cli-tool/rules/skills)"
```

---

## 任务 3：批量补全字段（A3）

**文件：** `scripts/enrich_projects.py`（新建）, `data/projects.yaml`

- [ ] **步骤 1：编写 enrich_projects.py**

脚本功能：
- 遍历所有项目，对有 repo 的项目通过 `gh repo view --json` 获取完整数据
- 补全 forks、license、stars、languages、topics
- 获取 README 前 500 字符存为 readme_preview
- 13 个 API key 轮询（从 ~/.hermes/auth.json 读取，用 urllib 调用）
- 每批 3 并发（ThreadPoolExecutor）
- 断点续传（跳过已有数据的字段）

```python
#!/usr/bin/env python3
"""Enrich existing projects with missing GitHub data.

Fetches forks, license, stars, languages, topics, readme_preview
for all projects that have a repo field.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]

def gh_repo_view(full_name, fields):
    """Fetch repo data via gh CLI."""
    cmd = f'gh repo view {full_name} --json {fields}'
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout or '{}')
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None

def enrich_one(project):
    """Enrich a single project with GitHub data."""
    repo = project.get('repo')
    if not repo or '/' not in repo:
        return project, False

    fields = 'nameWithOwner,forkCount,licenseInfo,stargazerCount,primaryLanguage,languages,repositoryTopics,readme,description'
    data = gh_repo_view(repo, fields)
    if not data:
        return project, False

    changed = False

    # Forks
    if not project.get('forks') and data.get('forkCount') is not None:
        project['forks'] = data['forkCount']
        changed = True

    # License
    if not project.get('license'):
        lic = data.get('licenseInfo')
        if isinstance(lic, dict) and lic.get('spdxId') and lic['spdxId'] != 'NOASSERTION':
            project['license'] = lic['spdxId']
            changed = True

    # Stars
    if not project.get('stars') and data.get('stargazerCount') is not None:
        project['stars'] = data['stargazerCount']
        changed = True

    # Languages
    if not project.get('languages') or project.get('languages') == [None]:
        langs = []
        primary = data.get('primaryLanguage')
        if isinstance(primary, dict) and primary.get('name'):
            langs.append(primary['name'])
        all_langs = data.get('languages')
        if isinstance(all_langs, list):
            for l in all_langs[:5]:
                if isinstance(l, dict) and l.get('name') and l['name'] not in langs:
                    langs.append(l['name'])
        if langs:
            project['languages'] = langs
            changed = True

    # Topics
    if not project.get('topics'):
        topics_data = data.get('repositoryTopics', [])
        if isinstance(topics_data, list):
            topics = [t.get('name','') for t in topics_data if isinstance(t, dict) and t.get('name')]
            if topics:
                project['topics'] = topics
                changed = True

    # README preview
    if not project.get('readme_preview'):
        readme = data.get('readme', '')
        if readme and len(readme) > 10:
            # Clean up: remove HTML tags, take first 500 chars
            import re
            clean = re.sub(r'<[^>]+>', '', readme)
            clean = re.sub(r'\n{3,}', '\n\n', clean).strip()
            project['readme_preview'] = clean[:500]
            changed = True

    return project, changed

def main():
    ap = argparse.ArgumentParser(description='Enrich projects with GitHub data')
    ap.add_argument('--limit', type=int, default=None, help='Limit number of projects')
    ap.add_argument('--batch-size', type=int, default=3, help='Concurrent requests')
    args = ap.parse_args()

    with open(ROOT / 'data/projects.yaml') as f:
        import yaml
        projects = yaml.safe_load(f)

    print(f'Total projects: {len(projects)}')

    # Filter projects that need enrichment
    to_enrich = []
    for p in projects:
        repo = p.get('repo')
        needs = (not p.get('forks') or not p.get('license') or
                 not p.get('topics') or not p.get('readme_preview') or
                 not p.get('stars'))
        if repo and '/' in repo and needs:
            to_enrich.append(p)

    if args.limit:
        to_enrich = to_enrich[:args.limit]

    print(f'Projects to enrich: {len(to_enrich)}')

    enriched = 0
    failed = 0

    for i in range(0, len(to_enrich), args.batch_size):
        batch = to_enrich[i:i+args.batch_size]
        print(f'  Batch {i//args.batch_size + 1}/{(len(to_enrich)-1)//args.batch_size + 1} ({len(batch)} projects)')

        with ThreadPoolExecutor(max_workers=args.batch_size) as executor:
            futures = {executor.submit(enrich_one, p): p for p in batch}
            for future in as_completed(futures):
                p, changed = future.result()
                if changed:
                    enriched += 1
                    print(f'    ✅ {p.get("name","?")[:40]}')
                else:
                    failed += 1
                    print(f'    ❌ {p.get("name","?")[:40]}')

        # Save progress every 5 batches
        if (i // args.batch_size + 1) % 5 == 0:
            import yaml
            with open(ROOT / 'data/projects.yaml', 'w') as f:
                yaml.dump(projects, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f'  Progress saved: {enriched} enriched, {failed} failed')

    # Final save
    import yaml
    with open(ROOT / 'data/projects.yaml', 'w') as f:
        yaml.dump(projects, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f'\nDone: {enriched} enriched, {failed} failed out of {len(to_enrich)}')

if __name__ == '__main__':
    main()
```

- [ ] **步骤 2：运行 enrich（先小批量测试）**

```bash
cd "/root/workspace/search in coding"
python3 scripts/enrich_projects.py --limit 5
```

- [ ] **步骤 3：全量运行**

```bash
python3 scripts/enrich_projects.py
```

- [ ] **步骤 4：验证字段填充率**

```bash
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
n = len(projects)
for field in ['forks','license','stars','languages','topics','readme_preview']:
    filled = sum(1 for p in projects if p.get(field) and p.get(field) != [None] and p.get(field) != [])
    print(f'  {field}: {filled}/{n} ({100*filled/n:.1f}%)')
"
```

- [ ] **步骤 5：Commit**

```bash
git add scripts/enrich_projects.py data/projects.yaml
git commit -m "feat: enrich projects with forks/license/topics/readme_preview from GitHub API"
```

---

## 任务 4：build_site.py 导出 readme_preview 和 topics 到 detail JSON

**文件：** `scripts/build_site.py`

- [ ] **步骤 1：修改 detail_project() 函数**

在 `DETAIL_FIELDS` 列表中添加 `readme_preview` 和 `topics`：

```python
# 在 build_site.py 中找到 DETAIL_FIELDS，添加两个字段
DETAIL_FIELDS = SLIM_FIELDS + [
    'score_detail', 'llm_summary', 'benchmark_ref', 'last_analyzed',
    'repo', 'tags', 'maturity', 'status',
    'readme_preview', 'topics',  # 新增
]
```

- [ ] **步骤 2：重建站点并验证**

```bash
cd "/root/workspace/search in coding"
python3 scripts/build_site.py
python3 -c "
import json
details = json.load(open('site/data/projects-detail.json'))
d = details[0]
print('has readme_preview:', 'readme_preview' in d)
print('has topics:', 'topics' in d)
"
```

- [ ] **步骤 3：Commit**

```bash
git add scripts/build_site.py site/data/
git commit -m "feat: export readme_preview and topics to detail JSON"
```

---

## 任务 5：翻译剩余 29 条英文 summary（C 残留）

**文件：** `scripts/translate_summaries.py`（已存在，复用）

- [ ] **步骤 1：识别需要翻译的项目**

29 条未翻译项目中，大部分原文已是中文（不需要翻译），只有少量英文残留需要翻译。

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml, re
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
needs_translation = []
for p in projects:
    zh = p.get('i18n',{}).get('zh',{}).get('summary','')
    en = p.get('i18n',{}).get('en',{}).get('summary','')
    if zh == en and en:
        has_cn = bool(re.search(r'[\u4e00-\u9fff]', en))
        if not has_cn:
            needs_translation.append(p)
print(f'Needs translation: {len(needs_translation)}')
for p in needs_translation:
    print(f'  {p[\"name\"][:35]}: {p.get(\"summary\",\"\")[:60]}')
"
```

- [ ] **步骤 2：翻译剩余英文 summary**

复用 `scripts/translate_summaries.py`，它应该会自动跳过已翻译的（缓存机制）。

```bash
python3 scripts/translate_summaries.py
```

如果脚本不支持只翻译未翻译的，手动运行：

```bash
python3 -c "
import yaml, re, json, urllib.request, hashlib
from pathlib import Path

# Load API keys
auth = json.loads(Path.home().joinpath('.hermes/auth.json').read_text())
pool = auth.get('credential_pool', {}).get('custom:sensenova', [])
keys = [e['access_token'] for e in pool if isinstance(e, dict) and e.get('access_token','').startswith('sk-')]
key_idx = 0

def translate(text, target='zh'):
    global key_idx
    if not text or len(text) < 5:
        return None
    prompt = f'Translate to Chinese. Respond with only the translation:\n\n{text[:300]}'
    payload = json.dumps({'model':'deepseek-v4-flash','messages':[{'role':'user','content':prompt}],'temperature':0.3,'max_tokens':500}).encode()
    for attempt in range(3):
        key = keys[key_idx % len(keys)]
        key_idx += 1
        req = urllib.request.Request('https://token.sensenova.cn/v1/chat/completions', data=payload,
            headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result.get('choices',[{}])[0].get('message',{}).get('content','').strip()
        except Exception as e:
            print(f'  Retry {attempt+1}: {e}')
    return None

with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)

translated = 0
for p in projects:
    zh = p.get('i18n',{}).get('zh',{}).get('summary','')
    en = p.get('i18n',{}).get('en',{}).get('summary','')
    if zh == en and en:
        has_cn = bool(re.search(r'[\u4e00-\u9fff]', en))
        if not has_cn:
            result = translate(en)
            if result:
                p.setdefault('i18n',{}).setdefault('zh',{})['summary'] = result
                translated += 1
                print(f'  ✅ {p[\"name\"][:30]}: {result[:50]}')
            else:
                print(f'  ❌ {p[\"name\"][:30]}')

with open('data/projects.yaml', 'w') as f:
    yaml.dump(projects, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
print(f'\nTranslated: {translated}')
"
```

- [ ] **步骤 3：验证翻译覆盖率**

```bash
python3 -c "
import yaml, re
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
same = diff = 0
untranslated_en = 0
for p in projects:
    zh = p.get('i18n',{}).get('zh',{}).get('summary','')
    en = p.get('i18n',{}).get('en',{}).get('summary','')
    if zh == en:
        same += 1
        if en and not re.search(r'[\u4e00-\u9fff]', en):
            untranslated_en += 1
    else:
        diff += 1
print(f'zh==en: {same}/{len(projects)} (of which {untranslated_en} are English needing translation)')
print(f'zh!=en (translated): {diff}/{len(projects)} ({100*diff/len(projects):.1f}%)')
"
```

- [ ] **步骤 4：Commit**

```bash
git add data/projects.yaml
git commit -m "fix: translate remaining 29 English summaries to Chinese"
```

---

## 任务 6：重建站点、重新评分、部署

- [ ] **步骤 1：重新评分（字段更新后分数可能变化）**

```bash
cd "/root/workspace/search in coding"
python3 scripts/score.py
```

- [ ] **步骤 2：运行完整 pipeline**

```bash
python3 scripts/update_tracker.py --skip-collect
```

- [ ] **步骤 3：部署**

```bash
python3 scripts/deploy_site.py
```

- [ ] **步骤 4：验证**

```bash
python3 -c "
import yaml, json
from collections import Counter

# Data check
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
n = len(projects)
print(f'Total: {n}')
for field in ['forks','license','stars','topics','readme_preview']:
    filled = sum(1 for p in projects if p.get(field) and p.get(field) != [None] and p.get(field) != [])
    print(f'  {field}: {filled}/{n} ({100*filled/n:.1f}%)')

# No high-star tutorial
for p in sorted(projects, key=lambda x: x.get('stars',0) or 0, reverse=True)[:30]:
    if (p.get('stars',0) or 0) > 1000 and 'tutorial' in (p.get('resource_type') or []):
        print(f'  ⚠️ Still tutorial: {p[\"name\"]}')

# Translation
import re
same = sum(1 for p in projects if p.get('i18n',{}).get('zh',{}).get('summary','') == p.get('i18n',{}).get('en',{}).get('summary',''))
print(f'  zh==en: {same}/{n}')

# Detail JSON has new fields
details = json.load(open('site/data/projects-detail.json'))
d = details[0]
print(f'  detail has readme_preview: {\"readme_preview\" in d}')
print(f'  detail has topics: {\"topics\" in d}')
"
```

- [ ] **步骤 5：Commit 并 tag**

```bash
git add -A
git commit -m "fix: all remaining issues - seed-tools paths, resource_type, field enrichment, translation, detail JSON"
git tag v2025.07.13-remaining-fixes
```

---

## 验收标准

- [ ] seed-tools.yaml 中 goose=block/goose, cursor=getcursor/cursor, opencode=sst/opencode
- [ ] 7 个高星项目不再被标为 tutorial
- [ ] forks 填充率 > 70%
- [ ] license 填充率 > 60%
- [ ] topics 填充率 > 50%
- [ ] readme_preview 填充率 > 50%
- [ ] detail JSON 包含 readme_preview 和 topics 字段
- [ ] 翻译覆盖率 > 95%（英文残留 < 10 条）
- [ ] pipeline --skip-collect PASS
- [ ] 站点已部署
