# Publish Readiness Review — 2026-07-06

## 结论

Search in Coding 已达到公开发布与长期运行的正式版条件：GitHub 仓库公开，正式 HTTPS 域名 `https://coding.lzpgood.online/` 已上线，Nginx 静态部署可用，Publish Site 与 Update Data workflow 均成功，Hermes daily/weekly/monthly cron 已配置为 local 投递，Exa 通过 mcporter 实测可用。

## 仓库

- GitHub: https://github.com/lzpgood123/search-in-coding
- 正式站点: https://coding.lzpgood.online/
- GitHub Pages 预览: http://giodio.me/search-in-coding/
- Visibility: public

## 数据规模

- Normalized records: 586
- Curated records: 60
- Rejected/noisy records: 25
- Official tools: 10
- Ecosystem projects: 264

## 来源分布

- exa: 165
- fallback-web: 147
- github: 264
- official-seed: 10

## Pages 状态

```json
{"build_type":"workflow","cname":null,"html_url":"http://giodio.me/search-in-coding/","https_enforced":false,"public":true,"status":null}
```

## 最近 GitHub Actions

```text
completed	success	Update Data	Update Data	main	workflow_dispatch	28780457105	1m53s	2026-07-06T09:08:18Z
completed	success	chore(data): refresh tracker with working Exa results	Publish Site	main	push	28780414252	14s	2026-07-06T09:07:35Z
completed	success	chore(data): update tracker snapshot	Publish Site	main	push	28768439497	14s	2026-07-06T04:46:14Z
completed	failure	feat: add continuous tracker update pipeline	Publish Site	main	push	28768144024	17s	2026-07-06T04:37:18Z
completed	success	chore: initial search in coding tracker release	Publish Site	main	push	28766451256	15s	2026-07-06T03:49:51Z
```

## 发布风险

1. 当前 Pages API 返回 `https_enforced: false`，公开访问地址为 `http://giodio.me/search-in-coding/`；后续如需正式公开传播，建议处理 HTTPS。
2. Curated Top 20 仍是规则+初步语义筛选，应逐步进行人工体验验证。
3. 部分 fallback-web 记录仍保留作发现线索，但已通过 source_quality 与 tags 明确标注。

## 建议下一步

- 处理 Pages HTTPS / 自定义域名。
- 人工试用 Top 20 中最相关的 5-10 个项目。
- 观察 daily cron 明天 03:00 的本地输出。
