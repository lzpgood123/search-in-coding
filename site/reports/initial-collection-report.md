# Initial Collection Report — 2026-07-06

## 摘要

Search in Coding 初始采集与归一化已完成。由于当前 `mcporter list` 显示没有 MCP servers configured，Exa 调用 `mcporter call 'exa.web_search_exa(...)'` 全部失败；项目已保存 Exa 失败 raw 记录，并使用 Bing RSS fallback 补充非 GitHub 互联网来源，所有 fallback 记录均标记为 `fallback-web`，不会伪装成 Exa 结果。

## 统计

- 总记录数：292
- GitHub 记录数：136
- 非 GitHub 记录数：156
- fallback web 记录数：147
- 官方 seed 记录数：9

## 按来源统计

- github: 136
- fallback-web: 147
- official-seed: 9

## 按工具统计

- antigravity-cli: 33
- claude-code: 46
- codex-cli: 30
- cursor: 26
- general-ai-coding: 32
- goose: 21
- hermes-agent: 17
- opencode: 24
- qoder: 41
- trae: 10
- workbuddy-codebuddy: 37

## 按分类统计

- agent-harness: 153
- ai-ide: 4
- benchmark-evaluation: 10
- context-engineering: 33
- mcp-acp-a2a: 79
- official-tool: 9
- persistent-agent: 1
- rules-instructions: 62
- skills-prompts: 95
- terminal-agent: 12
- testing-review-ci: 125
- tutorial-case-study: 19

## Top 20 候选

1. [Claude Code](https://code.claude.com) — score 24 — official-tool, terminal-agent
2. [OpenAI Codex CLI](https://chatgpt.com/codex) — score 24 — official-tool, terminal-agent
3. [OpenCode](https://opencode.ai) — score 24 — official-tool, terminal-agent
4. [Goose](https://goose-docs.ai/) — score 24 — official-tool, terminal-agent
5. [Qoder / QoderWork](https://qoder.com) — score 24 — official-tool, ai-ide
6. [Trae / Trae Work](https://www.trae.ai) — score 24 — official-tool, ai-ide
7. [WorkBuddy / CodeBuddy](https://www.workbuddy.ai) — score 24 — official-tool, ai-ide
8. [Cursor](https://cursor.com) — score 24 — official-tool, ai-ide
9. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/) — score 24 — official-tool, persistent-agent
10. [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) — score 19 — skills-prompts
11. [blader/humanizer](https://github.com/blader/humanizer) — score 18 — skills-prompts
12. [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) — score 18 — skills-prompts, testing-review-ci, agent-harness
13. [op7418/Humanizer-zh](https://github.com/op7418/Humanizer-zh) — score 18 — skills-prompts
14. [virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill) — score 17 — skills-prompts
15. [SimoneAvogadro/android-reverse-engineering-skill](https://github.com/SimoneAvogadro/android-reverse-engineering-skill) — score 17 — skills-prompts
16. [trailofbits/skills](https://github.com/trailofbits/skills) — score 17 — skills-prompts
17. [zarazhangrui/codebase-to-course](https://github.com/zarazhangrui/codebase-to-course) — score 17 — skills-prompts
18. [OpenCoworkAI/open-cowork](https://github.com/OpenCoworkAI/open-cowork) — score 17 — mcp-acp-a2a, skills-prompts, agent-harness
19. [steipete/claude-code-mcp](https://github.com/steipete/claude-code-mcp) — score 17 — mcp-acp-a2a, agent-harness
20. [sanjeed5/awesome-cursor-rules-mdc](https://github.com/sanjeed5/awesome-cursor-rules-mdc) — score 17 — rules-instructions

## 重要说明

- GitHub 搜索通过 `gh` 执行，raw 保存在 `data/raw/github/2026-07-06/`。
- Exa 查询失败证据保存在 `data/raw/exa/2026-07-06/`。
- fallback web 查询 raw 保存在 `data/raw/web/2026-07-06/`。
- 初始分类和评分是规则化 MVP，后续需要人工复核 Top 项目。
