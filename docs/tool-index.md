# AI 工具搜集分类索引

> 本页是 **Agent EcoRadar**（智能体生态雷达）的工具维度索引，用于从目标 AI Coding 工具进入对应生态数据。数据来源为 `data/seed-tools.yaml` 与 `data/projects.yaml`，由自动采集和评分流程持续更新。

正式站点：<https://ecoradar.lzpgood.online/>  
总仓库：<https://github.com/lzpgood123/agent-ecoradar>

## 总览

- 目标工具数：10
- 当前总记录数：5165
- Curated 自动推荐集：40
- Rejected 自动低质/噪声集：10

## 按工具索引

### Claude Code (`claude-code`)

- 厂商：Anthropic
- 类型：`terminal-agent`
- 官网：https://code.claude.com
- 文档：https://code.claude.com
- 代表仓库：anthropics/claude-code
- 当前记录数：108
- 扩展点：skills, hooks, slash-commands, mcp, subagents
- 相关概念：agentic-coding, context-engineering, mcp, skills, subagents
- 主要分类：testing-review-ci(62), skills-prompts(54), agent-harness(36), mcp-acp-a2a(34), rules-instructions(17), context-engineering(11), terminal-agent(4), benchmark-evaluation(3)

### OpenAI Codex CLI (`codex-cli`)

- 厂商：OpenAI
- 类型：`terminal-agent`
- 官网：https://chatgpt.com/codex
- 文档：https://developers.openai.com/codex
- 代表仓库：openai/codex
- 当前记录数：61
- 扩展点：skills, slash-commands, execution-policy, hooks, github-pr
- 相关概念：agentic-coding, AGENTS.md, sandbox, policy-engine
- 主要分类：skills-prompts(34), testing-review-ci(26), agent-harness(26), rules-instructions(17), mcp-acp-a2a(14), context-engineering(12), terminal-agent(3), benchmark-evaluation(2)

### Antigravity CLI / Gemini CLI (`antigravity-cli`)

- 厂商：Google
- 类型：`terminal-agent`
- 官网：https://antigravity.google/
- 文档：https://antigravity.google/docs/cli-install
- 代表仓库：google-gemini/gemini-cli
- 当前记录数：68
- 扩展点：plugins, skills, mcp, a2a, hooks, subagents
- 相关概念：multi-agent, a2a, mcp, plugins
- 主要分类：agent-harness(41), testing-review-ci(37), rules-instructions(16), context-engineering(15), mcp-acp-a2a(13), terminal-agent(13), skills-prompts(12), tutorial-case-study(10)

### OpenCode (`opencode`)

- 厂商：Anomaly
- 类型：`terminal-agent`
- 官网：https://opencode.ai
- 文档：https://opencode.ai/docs
- 代表仓库：anomalyco/opencode
- 当前记录数：59
- 扩展点：commands, agents, mcp, lsp, sourcegraph
- 相关概念：multi-provider, lsp, mcp, subagents
- 主要分类：agent-harness(33), testing-review-ci(25), mcp-acp-a2a(23), skills-prompts(11), rules-instructions(7), context-engineering(5), benchmark-evaluation(4), terminal-agent(2)

### Goose (`goose`)

- 厂商：AAIF / Block
- 类型：`terminal-agent`
- 官网：https://goose-docs.ai/
- 文档：https://goose-docs.ai/
- 代表仓库：aaif-goose/goose
- 当前记录数：45
- 扩展点：mcp extensions, recipes, subagents, acp, local models
- 相关概念：mcp, acp, recipes, sandbox, local-inference
- 主要分类：testing-review-ci(35), agent-harness(31), rules-instructions(15), context-engineering(14), mcp-acp-a2a(7), skills-prompts(7), official-tool(1), terminal-agent(1)

### Qoder / QoderWork (`qoder`)

- 厂商：Alibaba
- 类型：`ai-ide`
- 官网：https://qoder.com
- 文档：https://qoder.com
- 代表仓库：qoderAI
- 当前记录数：57
- 扩展点：skills, plugins, mcp, repo-wiki
- 相关概念：spec-driven-development, repo-wiki, skills, mcp
- 主要分类：agent-harness(38), testing-review-ci(32), skills-prompts(24), mcp-acp-a2a(14), benchmark-evaluation(7), tutorial-case-study(7), context-engineering(7), rules-instructions(5)

### Trae / Trae Work (`trae`)

- 厂商：ByteDance
- 类型：`ai-ide`
- 官网：https://www.trae.ai
- 文档：https://www.trae.ai/docs
- 代表仓库：bytedance/trae-agent
- 当前记录数：25
- 扩展点：mcp, skills, agent-system, online-search
- 相关概念：ai-ide, builder-mode, solo-agent, mcp
- 主要分类：testing-review-ci(18), mcp-acp-a2a(11), skills-prompts(11), rules-instructions(8), agent-harness(6), context-engineering(3), official-tool(1), ai-ide(1)

### WorkBuddy / CodeBuddy (`workbuddy-codebuddy`)

- 厂商：Tencent
- 类型：`ai-ide`
- 官网：https://www.workbuddy.ai
- 文档：https://www.workbuddy.ai/docs/zh/workbuddy/Overview
- 代表仓库：N/A
- 当前记录数：55
- 扩展点：mcp, skills, connectors, craft-agent
- 相关概念：office-agent, code-completion, mcp, skills
- 主要分类：testing-review-ci(34), agent-harness(33), skills-prompts(25), mcp-acp-a2a(10), rules-instructions(10), terminal-agent(10), context-engineering(5), tutorial-case-study(2)

### Cursor (`cursor`)

- 厂商：Anysphere
- 类型：`ai-ide`
- 官网：https://cursor.com
- 文档：https://docs.cursor.com
- 代表仓库：cursor/cursor
- 当前记录数：72
- 扩展点：rules, skills, mcp, hooks, cloud-agents, bugbot
- 相关概念：ai-ide, rules, mcp, cloud-agents, bugbot
- 主要分类：rules-instructions(37), testing-review-ci(36), mcp-acp-a2a(31), agent-harness(27), skills-prompts(15), context-engineering(13), tutorial-case-study(2), benchmark-evaluation(2)

### Hermes Agent (`hermes-agent`)

- 厂商：Nous Research
- 类型：`persistent-agent`
- 官网：https://hermes-agent.nousresearch.com/docs/
- 文档：https://hermes-agent.nousresearch.com/docs/
- 代表仓库：NousResearch/hermes-agent
- 当前记录数：53
- 扩展点：skills, cron, memory, delegation, tools, mcp
- 相关概念：persistent-memory, skills, cron, delegation, self-improvement
- 主要分类：agent-harness(52), testing-review-ci(34), skills-prompts(31), rules-instructions(11), context-engineering(9), mcp-acp-a2a(4), terminal-agent(1), official-tool(1)


## 按生态分类索引

- `agent-harness`：363 条
- `testing-review-ci`：357 条
- `skills-prompts`：195 条
- `mcp-acp-a2a`：162 条
- `rules-instructions`：135 条
- `context-engineering`：108 条
- `terminal-agent`：37 条
- `benchmark-evaluation`：31 条
- `tutorial-case-study`：24 条
- `official-tool`：10 条
- `ai-ide`：4 条
- `persistent-agent`：1 条

## 相关数据文件

- `data/seed-tools.yaml`：目标工具定义。
- `data/projects.yaml`：全量归一化记录。
- `data/curated-projects.yaml`：自动评分推荐集。
- `data/rejected-projects.yaml`：自动低质/噪声记录。
- `site/data/projects.json`：站点使用的数据。
