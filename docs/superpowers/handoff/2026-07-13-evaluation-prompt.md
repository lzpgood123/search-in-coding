# 站点评估提示词：三批次优化完成度验证

> 将以下全部内容复制粘贴到新对话中作为第一条消息。

---

## 你的任务

你是"Search in Coding"项目的质量评估 Agent。三个批次的优化刚刚完成（A 数据层修正、B 前端审美重做、C 翻译），你需要对 https://coding.lzpgood.online/ 进行全面评估，判断每个批次的完成度和遗留问题。

## 评估目标

### 批次 A：数据层修正（4 项）

1. **seed-tools repo 路径修正**：goose 应为 block/goose、cursor 应为 getcursor/cursor、opencode 应为 sst/opencode
2. **缺失项目补充**：以下项目应存在于数据库中：continuedev/continue、paul-gauthier/aider、cline/cline、rooveterinaryinc/roo、block/goose、getcursor/cursor
3. **字段映射修正**：forks、license、languages、stars 应有合理填充率（不再是全 None/0）；新增 topics 和 readme_preview 字段
4. **resource_type 误标修正**：高星 skill 项目（如 caveman、humanizer）不应被标为 tutorial；curated Top 40 分类应准确

### 批次 B：前端审美重做（15 项 dogfood 修复 + 审美升级）

5. **Linear/Vercel 风格**：渐变背景、卡片 box-shadow、半透明边框、大留白、字体层级（h1=40px/h2=28px/h3=20px）、Inter 字体加载
6. **色彩区分标签**：6 种 resource_type 各用不同颜色 pill（mcp=绿、skills=蓝、rules=紫、framework=橙、cli=青、tutorial=灰）
7. **Hero 区域**：首屏大标题 + 渐变背景 + 数据指标卡（总记录/推荐/官方工具/生态项目）
8. **分数展示 /60**（dogfood #1）：score badge 旁标注"/60"，不再展示"/ 100"，质量分标注"待 LLM 分析"
9. **工具/类型显示人话名称**（dogfood #11）：显示"Claude Code"而非"claude-code"，显示"MCP Server"而非"mcp-server"
10. **结果计数 + 清空筛选 + 活跃条件 chips**（dogfood #7）：筛选后显示"显示 X / Y"，有清空按钮，有活跃条件标签可逐个移除
11. **只看收藏**（dogfood #5）：有"只看收藏"checkbox，勾选后只显示收藏的项目
12. **OR/AND radiogroup 修复**（dogfood #8）：点已激活的按钮不翻转，点另一个才切换
13. **writeState 保留 hash**（dogfood #6）：筛选操作后 URL hash 不丢失
14. **项目名可点击 + 深链**（dogfood #15/#20）：表格中项目名可点击进详情，URL 支持 ?project=id 直接打开详情
15. **详情加载态**（dogfood #9）：点击详情后面板立即显示 loading，数据到达后替换
16. **score_detail 展示**（dogfood #10）：详情面板展示 stars/activity/adoption/maturity 分项分数
17. **空字段隐藏**（dogfood #12）：forks/license/languages 为空时详情面板不展示该行
18. **页脚**（dogfood #14）：显示数据更新时间 + GitHub 仓库链接
19. **robots.txt + favicon + OG meta**（dogfood #27）：robots.txt 可访问、favicon 显示、OG meta 标签存在

### 批次 C：翻译（1 项）

20. **中文翻译**：切换到"中文"后，项目 summary 应显示中文翻译（i18n.zh.summary != i18n.en.summary），不再是假双语

## 评估方法

### 第一步：读取项目文档

1. `docs/superpowers/specs/2026-07-13-site-optimization-v3-design.md` - 设计规格
2. `docs/ux-dogfood-report-2026-07-13.md` - 原始 dogfood 报告（42 个问题）
3. `docs/superpowers/plans/2026-07-13-batchA-data-correction.md` - 批次 A 计划
4. `docs/superpowers/plans/2026-07-13-batchB-frontend-redesign.md` - 批次 B 计划
5. `docs/superpowers/plans/2026-07-13-batchC-translation.md` - 批次 C 计划

### 第二步：数据层评估（批次 A）

通过读取 `data/projects.yaml` 和 `data/seed-tools.yaml` 评估：

```bash
cd "/root/workspace/search in coding"
# 检查 seed-tools repo 路径
python3 -c "
import yaml
with open('data/seed-tools.yaml') as f:
    tools = yaml.safe_load(f)
for t in tools:
    print(f'{t[\"id\"]}: repo={t.get(\"repo\",\"N/A\")}')
"

# 检查缺失项目是否已补充
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
repos = set(p.get('repo','') for p in projects)
for r in ['continuedev/continue','paul-gauthier/aider','cline/cline','rooveterinaryinc/roo','block/goose','getcursor/cursor']:
    print(f'{r}: {\"✅ found\" if r in repos else \"❌ missing\"}')
"

# 检查字段填充率
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
n = len(projects)
print(f'Total: {n}')
print(f'forks filled: {sum(1 for p in projects if p.get(\"forks\"))}/{n}')
print(f'license filled: {sum(1 for p in projects if p.get(\"license\"))}/{n}')
print(f'languages filled: {sum(1 for p in projects if p.get(\"languages\") and p.get(\"languages\") != [None])}/{n}')
print(f'stars filled: {sum(1 for p in projects if p.get(\"stars\"))}/{n}')
print(f'topics filled: {sum(1 for p in projects if p.get(\"topics\"))}/{n}')
print(f'readme_preview filled: {sum(1 for p in projects if p.get(\"readme_preview\"))}/{n}')
"

# 检查 resource_type 误标
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
# 检查高星 skill 项目
for p in projects:
    if p.get('stars',0) and p.get('stars',0) > 5000:
        rts = p.get('resource_type',[])
        if 'tutorial' in rts and 'skills' not in rts:
            summary = (p.get('summary','') or '').lower()
            if 'skill' in summary:
                print(f'⚠️ {p[\"name\"]} ({p.get(\"stars\")} stars): {rts} - summary mentions skill but not tagged as skills')
"
```

### 第三步：前端评估（批次 B）

通过读取前端源码和线上资源评估：

```bash
# 检查 styles.css 是否有 Linear/Vercel 风格元素
cd "/root/workspace/search in coding"
grep -c "box-shadow\|gradient\|rgba(255,255,255" site/styles.css
grep "pill-type-" site/styles.css | head -10
grep "Inter" site/styles.css | head -3

# 检查 index.html 是否有 Hero/页脚/OG meta
grep -c "hero-stat\|footer\|og:\|favicon\|theme-color" site/index.html

# 检查 render.js 是否有 /60、score_detail、loading 等
grep -c "/ 60\|score_detail\|detail-loading\|favoritesOnly\|resultCount\|activeFilters" site/js/render.js

# 检查 filters.js 是否有 favoritesOnly、clearAll、hash 保留
grep -c "favoritesOnly\|clearAll\|location.hash" site/js/filters.js

# 检查 robots.txt 和 favicon
curl -s https://coding.lzpgood.online/robots.txt | head -5
curl -sI https://coding.lzpgood.online/favicon.svg | head -3
```

### 第四步：翻译评估（批次 C）

```bash
cd "/root/workspace/search in coding"
python3 -c "
import yaml
with open('data/projects.yaml') as f:
    projects = yaml.safe_load(f)
same = 0
diff = 0
for p in projects:
    zh = p.get('i18n',{}).get('zh',{}).get('summary','')
    en = p.get('i18n',{}).get('en',{}).get('summary','')
    if zh == en:
        same += 1
    else:
        diff += 1
print(f'zh == en (untranslated): {same}/{len(projects)}')
print(f'zh != en (translated): {diff}/{len(projects)}')
print(f'Translation coverage: {diff/len(projects)*100:.1f}%')
"
```

### 第五步：线上站点验证

访问 https://coding.lzpgood.online/ 并验证：

1. 首屏是否有 Hero 区域（大标题 + 渐变背景 + 指标卡）
2. 卡片是否有 box-shadow 和半透明边框
3. resource_type pill 是否有不同颜色
4. 分数 badge 是否标注"/60"
5. 工具/类型标签是否显示人话名称
6. 筛选后是否有结果计数和清空按钮
7. "只看收藏"checkbox 是否存在且功能正常
8. OR/AND 切换是否正确（点已选项不翻转）
9. 点击项目名是否能打开详情
10. 详情面板是否有加载态
11. 详情面板是否展示 score_detail 分项
12. 空字段是否隐藏
13. 页脚是否有更新时间和 GitHub 链接
14. favicon 是否显示
15. 切换到中文后项目 summary 是否显示中文

## 评估报告格式

输出一份评估报告，格式如下：

```markdown
# 三批次优化完成度评估报告

> 评估日期：YYYY-MM-DD
> 评估站点：https://coding.lzpgood.online/

## 总览

| 批次 | 计划项数 | 完成数 | 完成率 | 遗留问题数 |
|------|---------|--------|--------|-----------|
| A 数据层 | 4 | ? | ?% | ? |
| B 前端层 | 15 | ? | ?% | ? |
| C 翻译 | 1 | ? | ?% | ? |
| 合计 | 20 | ? | ?% | ? |

## 批次 A 评估

### A1. seed-tools repo 路径修正
- 状态：✅/❌
- 证据：...
- 遗留问题：...

### A2. 缺失项目补充
- 状态：✅/❌
- 证据：...

（依次列出每项）

## 批次 B 评估

（依次列出 15 项，每项标注状态和证据）

## 批次 C 评估

### C1. 中文翻译
- 状态：✅/❌
- 翻译覆盖率：?%
- 证据：...

## 遗留问题清单

| # | 严重度 | 问题 | 所属批次 | 建议修复方式 |
|---|--------|------|---------|------------|
| 1 | ... | ... | ... | ... |

## 总体评价

（一段话总结整体完成度和建议）
```

## 项目环境信息

- 工作目录：`/root/workspace/search in coding`
- Python：3.12.3（用 python3）
- 站点：https://coding.lzpgood.online/
- GitHub 仓库：https://github.com/lzpgood123/search-in-coding
- pytest 需要在 .venv 中运行：`source .venv/bin/activate && python3 -m pytest tests/ -v`
- 前端源码在 `site/` 目录，JS 模块在 `site/js/`
- 数据文件在 `data/projects.yaml`
- dogfood 报告：`docs/ux-dogfood-report-2026-07-13.md`（原始 42 个问题，可对比检查修复情况）

## 注意事项

- 如果无法用浏览器访问站点，通过 curl/fetch 线上资源和读取源码交叉验证
- 评估应基于事实和证据，每个判断都要有数据支撑
- 对于"部分完成"的项，标注具体缺失内容
- 对比 dogfood 报告中的 42 个问题，标注哪些已修复、哪些仍存在
- 用户偏好精准区分"已完成"和"部分完成"，不要含糊
