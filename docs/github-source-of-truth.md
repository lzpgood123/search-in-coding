# GitHub 作为总仓库 / Source of Truth

## 定位

Agent EcoRadar 的长期权威数据源是 GitHub 仓库：

```text
https://github.com/lzpgood123/agent-ecoradar
```

正式站点：

```text
https://ecoradar.lzpgood.online/
```

站点是仓库数据的展示结果；GitHub 仓库才是完整索引库、历史记录、自动化、报告和版本记录的总仓库。

## GitHub 必须保存什么

以下内容必须同步到 GitHub：

- `data/raw/`：GitHub / Exa / fallback web 原始采集快照；
- `data/projects.yaml`：归一化索引库；
- `data/curated-projects.yaml`：自动评分推荐集；
- `data/rejected-projects.yaml`：自动低质/噪声/弱相关集；
- `data/scores.yaml`：评分结果；
- `docs/reports/`：自动生成报告；
- `site/data/`：站点数据；
- `site/reports/`：站点可访问报告副本；
- `scripts/`：采集、分析、评分、构建、部署脚本；
- `.github/workflows/`：GitHub 侧自动验证/采集工作流；
- `.hermes/cron-prompts/`：Hermes 长期追踪提示词；
- `VERSION`、`CHANGELOG.md`、`docs/releases/`：日期版本记录。

## 职责分工

### 服务器 Hermes cron

服务器是正式生产运行环境，负责：

1. 每日/每周自动采集 GitHub + Exa；
2. 自动评分维护 curated/rejected；
3. 生成报告和站点；
4. 部署到正式站 webroot（`ecoradar.lzpgood.online`）；
5. 将所有数据、报告、站点数据、版本记录提交并推送到 GitHub。

### GitHub Actions

GitHub Actions 是仓库侧自动化，负责：

1. 在 GitHub 环境中运行数据更新或验证；
2. 提交数据和报告到仓库；
3. 发布 GitHub Pages 预览；
4. 不部署到服务器 `/var/www`。

因此 GitHub Actions 调用 `scripts/update_tracker.py` 时不需要部署参数；部署默认关闭。服务器 Hermes cron 显式使用：

```bash
--deploy
```

## 手动立即更新

如果用户要求立即更新，应执行：

```bash
cd "/root/workspace/search in coding"
git pull --ff-only origin main
python3 scripts/update_tracker.py --github-limit 50 --exa-limit 5 --deploy
git status --short
```

如果有变化：

```bash
git add -A
git commit -m "chore(data): auto update tracker snapshot"
git push origin main
```

这样正式站点和 GitHub 总仓库都会保持一致。

## 核心原则

> GitHub 保存完整历史和完整数据；正式站点只展示当前构建结果。

任何自动更新只要产生有意义变化，都必须推送到 GitHub。