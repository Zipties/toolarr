# Toolarr MCP v2 vs Skills - Benchmark Results

**Date**: 2026-01-15

## Executive Summary

| Metric | MCP v2 | Skills | Winner |
|--------|--------|--------|--------|
| Total Time (6 tests) | 35,808ms | 32,724ms | Skills (9% faster) |
| Success Rate | 6/6 | 6/6 | Tie |
| Est. Tokens/run | ~2,350 | ~1,350 | Skills (43% fewer) |
| API Coverage | 28 tools | Unlimited | Skills |
| Guardrails | Built-in validation | Prompt patterns | MCP |
| Setup Complexity | MCP config + restart | Just works | Skills |

**Bottom Line**: Skills wins on speed and tokens. MCP wins on guardrails and type safety. Both successfully complete identical tasks.

## Raw Benchmark Data

```
Test                 MCP Time    Skills Time   Winner
---------------------------------------------------------
series_lookup        642.8ms     374.9ms       Skills (42% faster)
movie_lookup         309.1ms     314.0ms       MCP (2% faster)
sonarr_queue         9.1ms       23.2ms        MCP (61% faster)
quality_profiles     6.1ms       22.5ms        MCP (73% faster)
episode_releases     28,772ms    26,990ms      Skills (6% faster)
movie_releases       6,068ms     4,999ms       Skills (18% faster)
```

### Observations

1. **Simple queries**: MCP is faster (connection pooling, no subprocess overhead)
2. **Complex queries**: Skills slightly faster (release searches are API-bound anyway)
3. **First request**: Skills faster (no async client init)
4. **Subsequent requests**: MCP faster (reuses connections)

## Haiku Agent Tests

Both approaches were tested with Haiku (smallest Claude model) on the same task:
> "Find releases for Severance S2E10 and identify the best quality"

### Results

| Test | MCP | Skills |
|------|-----|--------|
| Completed task? | ✅ Yes | ✅ Yes |
| Found releases? | 164 | 164 |
| Identified best? | ✅ 2160p WEBDL | ✅ 2160p WEBDL |
| Needed guidance? | No | No |

**Key Finding**: Both approaches work equally well for a "dumb" AI. The improved Skills with guardrail patterns performed just as reliably as MCP's built-in validation.

## Token Cost Analysis

### MCP Approach
- Tool schemas loaded at session start: ~250 tokens × 28 tools = **7,000 tokens upfront**
- Per tool call: ~50-100 tokens
- Response parsing: Automatic (structured JSON)

### Skills Approach
- No upfront cost (loaded on demand)
- Per skill invocation: ~150-200 tokens (prompt snippet)
- Response parsing: jq handles it

**Verdict**: Skills is more token-efficient for:
- Sessions using only a few Sonarr/Radarr operations
- One-off tasks

MCP is more efficient for:
- Sessions with many repeated operations
- Workflows that chain multiple calls

## When to Use Each

### Use MCP When:
- Building automated workflows (n8n, scripts)
- Need strict input validation
- Want IDE-like autocomplete for tools
- Running many operations per session

### Use Skills When:
- Ad-hoc requests ("check what's downloading")
- Learning/exploring the API
- Token budget is tight
- Don't want to configure MCP servers

## Architecture Comparison

```
┌─────────────────────────────────────────────────────────┐
│                      MCP v2                             │
├─────────────────────────────────────────────────────────┤
│  Claude ──► MCP Protocol ──► mcp_server_v2.py          │
│                              ├── tools/sonarr.py       │
│                              ├── tools/radarr.py       │
│                              └── backends/*.py ──► API │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      Skills                             │
├─────────────────────────────────────────────────────────┤
│  Claude ──► Skill Prompt ──► curl/jq ──► API           │
│             (patterns)       (bash)                    │
└─────────────────────────────────────────────────────────┘
```

## Conclusion

**There's no clear winner** - it depends on use case.

For **Piflix Chad** (homelab assistant), Skills remain the better choice:
- Lower token overhead
- No server to maintain
- Patterns are self-documenting
- Works without MCP configuration

For **Automation/Integrations**, MCP v2 is superior:
- Type-safe tool definitions
- Structured error handling
- Connection pooling for performance
- Standard protocol (works with any MCP client)

## Files

- Benchmark script: `benchmark/benchmark_mcp_v2.py`
- MCP server: `mcp_server_v2.py`
- Backend clients: `backends/`
- Skills: `/home/cory/proj/piflixchad/skills/sonarr/SKILL.md`
