# ADR-0008: 前端性能优化策略

## Status: accepted

## Context

回溯后数据量从 618 条增长到数千条，`projects.json` 可能达 5-10MB。纯 SPA 全 JS 渲染导致 SEO 不可见。当前无加载状态、错误处理、缓存策略和可访问性支持。

## Decision

五项前端优化：

1. **数据加载**：精简 JSON 字段（表格数据 vs 详情数据分离）+ 虚拟滚动 + gzip + 渐进式渲染
2. **SEO**：预渲染首屏 HTML + sitemap.xml + JSON-LD 结构化数据
3. **加载状态**：骨架屏 + 渐进式渲染 + 完整错误处理（重试/空状态/错误提示）
4. **可访问性**：语义 HTML + ARIA 标签 + 键盘导航 + 焦点管理 + WCAG AA 对比度（代码重构时一并实现）
5. **Nginx 缓存**：文件名加内容 hash（JS/CSS 长缓存 immutable，JSON 5 分钟，HTML no-cache）

## Consequences

- `build_site.py` 需要生成两个 JSON（精简 + 详情）、预渲染 HTML、sitemap.xml、带 hash 的 JS/CSS
- 前端复杂度增加，但用户体验和 SEO 显著提升
- Nginx 配置需要更新缓存头
