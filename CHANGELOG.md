## 2026.07.16 — 去掉 formerly，公开主路径旧名收口

### Changed

- 移除 README 中英与站点 footer 的 `formerly Search in Coding` 过渡标注。
- 现行公开文档与脚本门面文案统一为 **Agent EcoRadar** / `https://ecoradar.lzpgood.online/`。
- 导出包默认文件名改为 `agent-ecoradar-template.zip`；`pyproject.toml` 包名同步为 `agent-ecoradar`。

### Notes

- 历史 CHANGELOG 条目、带日期 dogfood/evaluation 报告、snapshot 数据中的旧名按档案保留。
- 采集 / 评分 / LLM 业务逻辑与数据语义未改。

## 2026.07.16 — GitHub 仓库更名为 agent-ecoradar

### Changed

- GitHub 仓库从 `lzpgood123/search-in-coding` 重命名为 `lzpgood123/agent-ecoradar`（旧 URL 由 GitHub 保留 redirect）。
- 公开 README / CONTRIBUTING / 站点 footer / badge / clone 示例同步为新仓库 URL。
- Release 站点产物包名调整为 `agent-ecoradar-site.tar.gz`。

### Notes

- 正式站仍为 `https://ecoradar.lzpgood.online/`；产品过渡标注 formerly Search in Coding 保留。
- 采集 / 评分 / LLM 业务逻辑与数据语义未改。

## 2026.07.16 — Agent EcoRadar 品牌与主站切换

### Changed

- 产品公开品牌切换为 **Agent EcoRadar**（智能体生态雷达；过渡期标注 formerly Search in Coding）。
- 正式站主入口切换为 `https://ecoradar.lzpgood.online/`；旧域 `coding.lzpgood.online` 301 到新域。
- 站点 `SITE_URL`、sitemap / robots、标题与 OG 等可见品牌字符串同步更新。
- README 中英重写；补充 MIT LICENSE、CONTRIBUTING 与 Issue/PR 模板。
- 公开仓库清理：内部协作目录（如 wiki、过程规格草稿、本地 agent 配置）移出 git 追踪，本地保留。

### Notes

- 当时 GitHub 仓库 slug 仍为 `search-in-coding`（已在后续同日条目完成改名）。
- 采集 / 评分 / LLM 业务逻辑与数据语义未改。

## 2026.07.13 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

## 2026.07.11 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

## 2026.07.10 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

## 2026.07.09 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

## 2026.07.08 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

## 2026.07.07 — 自动更新

### Changed

- 数据自动采集更新。

### Data

- `data/raw/` 新增当日采集记录。
- `data/curated/`、`data/reports/` 自动重新生成。

# Changelog

## 2026.07.06 — 正式版

Search in Coding 进入正式版，采用日期版本号迭代。

### Added

- 正式域名：`https://coding.lzpgood.online/`
- 本机 Nginx 静态站点部署路径：`/var/www/coding.lzpgood.online`
- Let's Encrypt TLS 证书：`/etc/letsencrypt/live/coding.lzpgood.online/`
- `VERSION` 日期版本文件
- `scripts/deploy_site.py` 正式站点同步脚本
- `docs/releases/2026.07.06.md` 正式版发布说明
- daily / weekly / monthly Hermes cron 任务
- Exa via mcporter 的真实语义搜索链路

### Changed

- `update_tracker.py` 支持在构建站点后自动部署到正式域名目录。
- 项目从 GitHub Pages 预览发布升级为本服务器正式 HTTPS 发布。

### Verified

- `python3 scripts/quality_gate.py` 通过。
- `https://coding.lzpgood.online/` 返回 Search in Coding 页面。
- TLS 证书签发成功，证书主体为 `coding.lzpgood.online`。
