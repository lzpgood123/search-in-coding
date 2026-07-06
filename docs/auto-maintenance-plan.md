# Search in Coding 全自动维护方案

## 目标

取消人工审核环节，项目长期依靠 AI/规则评分维持索引库。

维护者不需要逐条审核 curated、选择、提交；自动维护流程负责：

- 每天收集 GitHub + Exa 信息；
- 每天分析、归一化、评分；
- 自动维护 auto-curated / auto-rejected；
- 自动生成报告与站点；
- 自动部署到 `https://coding.lzpgood.online/`；
- 自动把 raw 数据、归一化数据、报告、站点数据和版本记录提交到 GitHub 总仓库；
- 导入阶段即持久化 `i18n.zh/en` 展示结构，站点构建阶段防御性补齐，正式站点支持中英切换；
- 每周发布一次正式更新；
- 维护者也可以随时手动触发立即更新。

## 维护模式

### Daily：自动收集与分析

每天运行：

```bash
python3 scripts/update_tracker.py --github-limit 20 --exa-limit 3 --deploy
```

流程：

1. GitHub 搜索；
2. Exa 语义搜索；
3. raw 结果保存；
4. normalize；
5. score；
6. auto finalize curated/rejected；
7. generate reports；
8. build site；
9. quality gate；
10. deploy to production site；
11. 如有变化，提交并推送。

### Weekly：正式周更新

每周一运行一次更偏发布的更新：

```bash
python3 scripts/update_tracker.py --github-limit 50 --exa-limit 5 --deploy
```

并生成周报，提交到 GitHub。

### Manual trigger：人为要求立即更新

手动触发时可执行：

```text
立即更新 Search in Coding
```

执行：

```bash
git pull --ff-only origin main
python3 scripts/update_tracker.py --github-limit 50 --exa-limit 5 --deploy
git status --short
# 如有变化则提交推送
```

## 自动评分原则

`data/curated-projects.yaml` 不再代表人工审核结果，而是自动推荐集。

自动进入 curated 的优先级：

1. GitHub verified ecosystem records；
2. Exa verified learning/resource records；
3. 高分 MCP / skills / rules / context-engineering；
4. 每个目标工具保留一定覆盖；
5. official tools 永远单独展示，不进入 ecosystem ranking。

自动进入 rejected 的优先级：

1. 低分；
2. fallback-web 且无强相关性；
3. general-ai-coding 过泛记录；
4. 重复或低可信；
5. official tool 以外但 ranking_scope 不清晰的记录。

## 后续只做方向调整

维护者不再做逐条审核，只在需要时调整方向，例如：

- 新增追踪工具；
- 调整分类体系；
- 提升某类权重；
- 降低 fallback 权重；
- 要求发布新日期版本。

## 验收

每次自动更新必须通过：

```bash
python3 scripts/quality_gate.py
curl -I https://coding.lzpgood.online/
```
