# Search in Coding 网站安全加固说明

正式站点：<https://coding.lzpgood.online/>

## 已启用的安全措施

### HTTPS 与 TLS

- HTTP 自动跳转 HTTPS。
- TLS 证书由 Let's Encrypt 签发。
- 仅允许 TLSv1.2 / TLSv1.3。

### 安全响应头

Nginx vhost 已配置：

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'; frame-ancestors 'self'; upgrade-insecure-requests
X-Content-Type-Options: nosniff
X-Frame-Options: SAMEORIGIN
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), bluetooth=(), accelerometer=(), gyroscope=(), magnetometer=(), fullscreen=(self)
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

### 前端数据渲染

- 所有项目名称、摘要、分类、来源字段渲染前执行 HTML escape。
- 项目 URL 只允许 `http:` 和 `https:`。
- 外部链接使用：

```html
rel="noopener noreferrer"
```

避免 `target="_blank"` 反向控制来源页面。

## 后续建议

1. 将站点改为无 inline script/style 的严格 CSP 模式已经满足；后续避免新增 inline script。
2. 如果将来引入第三方分析、字体、CDN，必须同步更新 CSP。
3. 若将来开放用户提交数据，需要额外增加服务端清洗与审核机制。
4. 定期运行：

```bash
curl -I https://coding.lzpgood.online/
```

确认安全头仍存在。
