# Exa Status and Fallback — 2026-07-07

## mcporter list

```text
mcporter 0.9.0 — Listing 2 server(s) (per-server timeout: 30s)
- xiaohongshu (13 tools, 0.1s)
- exa (2 tools, 1.5s)
✔ Listed 2 servers (2 healthy).
```

## Exa probe

```bash
mcporter call 'exa.web_search_exa(query: "Claude Code ecosystem MCP skills", count: 3)'
```

Exit code: `1`

```text
[mcporter] exa.web_search_exa responded with HTTP 429 (Streamable HTTP error: Error POSTing to endpoint: {"jsonrpc":"2.0","error":{"code":-32000,"message":"You've hit Exa's…).
[mcporter] exa.web_search_exa responded with HTTP 429 (Streamable HTTP error: Error POSTing to endpoint: {"jsonrpc":"2.0","error":{"code":-32000,"message":"You've hit Exa's…).
[mcporter] Streamable HTTP error: Error POSTing to endpoint: {"jsonrpc":"2.0","error":{"code":-32000,"message":"You've hit Exa's free MCP rate limit. To continue using without limits, create your own Exa API key.\n\nFix: Create API key at https://dashboard.exa.ai/api-keys , then either:\n- Set the header: Authorization: Bearer YOUR_EXA_API_KEY\n- Or use the URL: https://mcp.exa.ai/mcp?exaApiKey=YOUR_EXA_API_KEY"},"id":null}
StreamableHTTPError: Streamable HTTP error: Error POSTing to endpoint: {"jsonrpc":"2.0","error":{"code":-32000,"message":"You've hit Exa's free MCP rate limit. To continue using without limits, create your own Exa API key.\n\nFix: Create API key at https://dashboard.exa.ai/api-keys , then either:\n- Set the header: Authorization: Bearer YOUR_EXA_API_KEY\n- Or use the URL: https://mcp.exa.ai/mcp?exaApiKey=YOUR_EXA_API_KEY"},"id":null}
    at StreamableHTTPClientTransport.send (file:///usr/lib/node_modules/mcporter/node_modules/@modelcontextprotocol/sdk/dist/esm/client/streamableHttp.js:364:23)
    at process.processTicksAndRejections (node:internal/process/task_queues:95:5) {
  code: 429
}
```

## Status

Exa is not configured in current mcporter environment. Existing non-GitHub web data is labeled fallback-web / fallback-not-exa and must not be treated as Exa results.
