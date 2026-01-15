# Toolarr MCP Overhaul Plan

## Goal
Convert Toolarr from HTTP+JSON-RPC hybrid to pure stdio MCP server with complete Sonarr/Radarr API coverage.

## Architecture Changes

### Current (HTTP Gateway)
```
Claude Code → HTTP → Toolarr FastAPI → HTTP → Sonarr/Radarr
```

### Target (Pure MCP)
```
Claude Code → stdio MCP → Toolarr MCP Server → HTTP → Sonarr/Radarr
```

## Workstreams (Parallelizable)

### Stream 1: MCP Server Core (BLOCKING - do first)
- [ ] Create new `mcp_server_stdio.py` with proper MCP protocol
- [ ] Implement tool registration system
- [ ] Handle stdio transport (stdin/stdout JSON-RPC)
- [ ] Connection management for Sonarr/Radarr backends

### Stream 2: Sonarr Tools (after Stream 1 foundation)
- [ ] `sonarr_list_series` - GET /api/v3/series (NEW - was missing!)
- [ ] `sonarr_lookup_series` - Search external databases
- [ ] `sonarr_add_series` - Add series to library
- [ ] `sonarr_get_series` - Get single series by ID
- [ ] `sonarr_delete_series` - Remove series
- [ ] `sonarr_get_episodes` - List episodes for series
- [ ] `sonarr_get_episode_releases` - Browse releases (NEW!)
- [ ] `sonarr_grab_release` - Download specific release (NEW!)
- [ ] `sonarr_get_queue` - Download queue
- [ ] `sonarr_get_history` - Download history
- [ ] `sonarr_get_quality_profiles` - Quality profiles
- [ ] `sonarr_get_root_folders` - Root folders
- [ ] `sonarr_search_series` - Trigger auto-search
- [ ] `sonarr_search_episode` - Search specific episode

### Stream 3: Radarr Tools (parallel with Stream 2)
- [ ] `radarr_list_movies` - GET /api/v3/movie (NEW!)
- [ ] `radarr_lookup_movie` - Search external databases
- [ ] `radarr_add_movie` - Add movie to library
- [ ] `radarr_get_movie` - Get single movie by ID
- [ ] `radarr_delete_movie` - Remove movie
- [ ] `radarr_get_movie_releases` - Browse releases (NEW!)
- [ ] `radarr_grab_release` - Download specific release (NEW!)
- [ ] `radarr_get_queue` - Download queue
- [ ] `radarr_get_history` - Download history
- [ ] `radarr_get_quality_profiles` - Quality profiles
- [ ] `radarr_get_root_folders` - Root folders
- [ ] `radarr_search_movie` - Trigger auto-search

### Stream 4: Shared Utilities (parallel)
- [ ] Connection pool manager for backend APIs
- [ ] Response normalization (consistent output format)
- [ ] Error handling with helpful messages
- [ ] Logging/audit system

### Stream 5: Testing & Docs (after tools complete)
- [ ] Unit tests for each tool
- [ ] Integration tests against real Sonarr/Radarr
- [ ] Claude Desktop config example
- [ ] Claude Code MCP config example

## File Structure (Target)

```
toolarr/
├── mcp_server.py          # Main MCP server (stdio)
├── tools/
│   ├── __init__.py
│   ├── sonarr.py          # Sonarr tool implementations
│   ├── radarr.py          # Radarr tool implementations
│   └── shared.py          # Shared utilities
├── backends/
│   ├── __init__.py
│   ├── sonarr_client.py   # Sonarr API client
│   └── radarr_client.py   # Radarr API client
├── tests/
│   ├── test_sonarr.py
│   ├── test_radarr.py
│   └── test_integration.py
└── config.py              # Configuration management
```

## Agent Assignments

| Agent | Task | Depends On |
|-------|------|------------|
| Agent A | MCP Server Core | Nothing |
| Agent B | Sonarr Tools | Agent A (foundation) |
| Agent C | Radarr Tools | Agent A (foundation) |
| Agent D | Backend Clients | Nothing (parallel with A) |
| Agent E | Testing Suite | B, C, D complete |

## Success Criteria

1. All tools from IMPROVEMENTS.md gaps are implemented
2. Token count competitive with Skills (~5000 tokens for full schema)
3. Passes robustness tests from benchmark suite
4. Works with Claude Code MCP configuration
5. Haiku can complete the "Severance lookup" and "Dune releases" tests

## Timeline

Parallel execution should complete core work in ~2-3 agent sessions.
