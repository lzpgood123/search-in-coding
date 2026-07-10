# Exa Status and Fallback — 2026-07-10

## mcporter list

```text
/bin/sh: 1: mcporter: not found
```

## Exa probe

```bash
mcporter call 'exa.web_search_exa(query: "Claude Code ecosystem MCP skills", count: 3)'
```

Exit code: `127`

```text
/bin/sh: 1: mcporter: not found
```

## Status

Exa is not configured in current mcporter environment. Existing non-GitHub web data is labeled fallback-web / fallback-not-exa and must not be treated as Exa results.
