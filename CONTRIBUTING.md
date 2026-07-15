# Contributing to Agent EcoRadar

感谢关注 **Agent EcoRadar**（智能体生态雷达，formerly Search in Coding）。

## 如何参与

### 1. 报告问题

请用 [Bug report](https://github.com/lzpgood123/agent-ecoradar/issues/new?template=bug_report.md) 模板，尽量包含：

- 复现步骤
- 期望 vs 实际
- 站点路径或项目 URL（若相关）
- 浏览器 / 环境信息

### 2. 请求新增追踪工具

使用 [Tool request](https://github.com/lzpgood123/agent-ecoradar/issues/new?template=tool_request.md) 模板。  
维护者侧完整步骤见：[`docs/add-new-tool-checklist.md`](docs/add-new-tool-checklist.md)。

### 3. 修正数据

- 优先开 Issue 说明错误字段与证据链接
- 小范围修正可 PR：`data/projects.yaml` / `data/seed-tools.yaml` / `data/queries.yaml`
- 请勿提交密钥、私人路径或未脱敏快照

### 4. 改进前端

- 源码：`site/`（零依赖；模块见 `site/js/`）
- 构建：`python3 scripts/build_site.py`（会生成 hash 资源与 `site/data/`）
- 避免引入 npm 依赖或外链字体（保持严格 CSP）

### 5. 改进管道脚本

- 代码：`scripts/`
- 测试：`tests/`，运行 `python3 -m pytest`
- 不改动评分语义时请在 PR 中说明；破坏性变更请先开 Issue

## 本地环境

```bash
python3 -m venv .venv
source .venv/bin/activate
# 安装项目依赖（pyproject / requirements 以仓库为准）
python3 -m pytest
python3 scripts/build_site.py
```

可选环境变量见 `.env.example`。GitHub 元数据相关命令依赖已登录的 `gh`。

## 提交约定

- 使用清晰的英文或中文 commit message（推荐 Conventional Commits 风格，如 `fix:` / `docs:` / `feat:`）
- 一个 PR 聚焦一件事
- 公开 diff 中禁止：真实 API key、私人邮箱、本机绝对运维路径、内部协作过程记录

## 行为准则

请保持友善与建设性。恶意刷数据、滥用自动化接口或提交恶意内容的 PR 将被关闭。

## License

贡献内容默认在 [MIT](LICENSE) 下授权。
