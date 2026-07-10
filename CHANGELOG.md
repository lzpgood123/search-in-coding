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
