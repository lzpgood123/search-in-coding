# Search in Coding

**正式站点：<https://coding.lzpgood.online/>**

Current version: `2026.07.06`

Search in Coding is a publishable, reusable AI Coding Agent ecosystem tracker focused on terminal/agentic coding tools and adjacent AI IDE ecosystems.

## Target tools

Claude Code, OpenAI Codex CLI, Antigravity/Gemini CLI, OpenCode, Goose, Qoder/QoderWork, Trae, WorkBuddy/CodeBuddy, Cursor, Hermes Agent.

## What it tracks

- official tools and docs
- ecosystem projects
- MCP/ACP/A2A servers
- skills, prompts, rules, slash commands
- context engineering and codebase indexing
- PR review / CI automation
- tutorials, best practices, case studies
- benchmarks and evaluation resources

## Quick start

```bash
python3 scripts/validate_data.py
python3 scripts/quality_gate.py
python3 scripts/score.py
python3 scripts/generate_reports.py
python3 scripts/build_site.py
python3 scripts/export_pack.py --dry-run
```

## Data

- `data/projects.yaml`: normalized records
- `data/curated-projects.yaml`: reviewed high-signal records
- `data/rejected-projects.yaml`: noisy / low-confidence records
- `data/raw/`: source snapshots

The YAML files are JSON-compatible for stdlib parsing.

## Reports

Final reports live under `docs/reports/`.

## Manual review

Human curation guide:

```text
docs/manual-review-guide.md
```

Use it to review curated projects, move noisy records to rejected, update recommendation levels, run quality gates, and deploy the formal site.

## Site

Open `site/index.html` after running `python3 scripts/build_site.py`.

## Source policy

GitHub discovery uses `gh`. Exa semantic search should use `mcporter call 'exa.web_search_exa(query: "...", count: 3)'`; if Exa is unavailable, fallback web records are clearly labeled `fallback-web` and `fallback-not-exa`.

## Reuse

See `docs/reusable-packaging.md` and replace `data/seed-tools.yaml` + `data/queries.yaml` for another ecosystem.
