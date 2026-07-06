# Search in Coding 收尾执行计划

## 目标

在最终交付版基础上完成发布后运行准备：修复 Hermes cron 投递问题、补齐 weekly/monthly 定时任务、生成发布前 review、生成 curated Top 20 精修报告，并确认 GitHub 仓库/Pages/Actions 可用。

## 当前状态

- GitHub 仓库已存在：`https://github.com/lzpgood123/search-in-coding`
- GitHub Pages 已启用：`http://giodio.me/search-in-coding/`
- Publish Site workflow 成功。
- Update Data workflow 成功。
- Exa 已通过 `mcporter` 真实调用成功。
- 已有 daily Hermes cron，但投递目标 `origin` 在 WebUI 下报 `unknown platform 'webui'`。

## 收尾任务

### 1. 修复 cron 投递

- 将 existing daily cron 的 `deliver` 改为 `local`，避免 WebUI origin 投递失败。
- 创建 weekly report cron。
- 创建 monthly audit cron。
- 所有 cron 使用 `/root/workspace/search in coding` 作为 `workdir`。

### 2. 发布前 review

生成：

```text
docs/reports/publish-readiness-review.md
```

检查：

- 数据规模
- 质量门禁
- Exa 状态
- GitHub Actions
- GitHub Pages
- cron 状态
- 公开发布风险

### 3. Curated Top 20 精修

生成：

```text
docs/reports/curated-top-20-review.md
```

要求：

- official tools 排除。
- 每个项目给中文短评。
- 标注优先级：立即尝试 / 值得观察 / 参考资料 / 需复核。
- 指出榜单仍需人工复核的条目。

### 4. 提交并推送

- 将新增报告和计划提交到 GitHub。
- 确认 Publish Site workflow 成功。

## 验收

```bash
python3 scripts/quality_gate.py
gh run list --limit 5
hermes cron list
```

完成后汇报 cron job id、GitHub repo、Pages URL、Actions 状态和新增报告路径。
