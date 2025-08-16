# MCP Integration for Toolarr

This document describes the Model Context Protocol (MCP) integration added to the Toolarr FastAPI server, enabling Claude Desktop and other AI assistants to directly manage your Sonarr and Radarr media libraries.

## Overview

The MCP integration provides 18 tools for complete media management:
- **Sonarr Tools**: TV series search, management, and monitoring
- **Radarr Tools**: Movie search, management, and monitoring  
- **Queue Management**: Download queue and history access
- **Instance Management**: Multi-instance configuration support

## Quick Start

### 1. Server Setup
Your Toolarr server now includes MCP endpoints:
- **POST** `/mcp` - Main JSON-RPC 2.0 endpoint
- **GET** `/mcp/sse` - Server-Sent Events for real-time updates

### 2. Authentication
Uses existing Bearer token authentication:
```bash
Authorization: Bearer YOUR_TOOL_API_KEY
```

### 3. Claude Desktop Configuration

Add to your Claude Desktop MCP configuration file:

**For HTTP Servers (Recommended):**
```json
{
  "mcpServers": {
    "toolarr": {
      "command": "npx",
      "args": [
        "@modelcontextprotocol/server-fetch",
        "https://your-toolarr-server.com/mcp"
      ],
      "env": {
        "AUTHORIZATION": "Bearer YOUR_TOOL_API_KEY"
      }
    }
  }
}
```

**Alternative cURL-based Configuration:**
```json
{
  "mcpServers": {
    "toolarr": {
      "command": "curl",
      "args": [
        "-X", "POST", 
        "-H", "Authorization: Bearer YOUR_TOOL_API_KEY",
        "-H", "Content-Type: application/json",
        "-d", "@-",
        "https://your-toolarr-server.com/mcp"
      ]
    }
  }
}
```

## Available Tools (18 Total)

### Sonarr Tools (10)
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `get_sonarr_episodes` | Get all episodes for a TV series | `series_id` |
| `find_series_with_tags` | Find TV series by tags | `tags[]` |
| `search_sonarr_series` | Search for TV series | `term` |
| `lookup_sonarr_series` | Lookup series to add | `term` |
| `add_sonarr_series` | Add new TV series | `tvdbId`, `title`, `qualityProfileId` |
| `get_sonarr_queue` | Get download queue | - |
| `get_sonarr_history` | Get download history | `page`, `pageSize` |
| `delete_sonarr_queue_item` | Remove queue item | `queue_id` |
| `get_sonarr_quality_profiles` | Get quality profiles | - |
| `list_sonarr_instances` | List configured instances | - |

### Radarr Tools (7)
| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_radarr_movie_lookup` | Search external movie databases | `term` |
| `lookup_radarr_movie` | Lookup movies to add | `term` |
| `add_radarr_movie` | Add new movie | `tmdbId`, `title`, `qualityProfileId` |
| `get_radarr_queue` | Get download queue | - |
| `get_radarr_history` | Get download history | `page`, `pageSize` |
| `get_radarr_quality_profiles` | Get quality profiles | - |
| `get_radarr_rootfolders` | Get root folders | - |

### Instance Management (1)
| Tool | Description |
|------|-------------|
| `list_radarr_instances` | List configured Radarr instances |

## Default Instance Strategy

**Important**: All tools use the "default" instance (your first configured instance) unless explicitly specified. This prevents AI hallucination of instance names.

```bash
# Environment variables for instances
SONARR_INSTANCE_1_NAME="default"    # First instance = "default"
SONARR_INSTANCE_1_URL="http://..."
SONARR_INSTANCE_1_API_KEY="..."

RADARR_INSTANCE_1_NAME="default"    # First instance = "default"  
RADARR_INSTANCE_1_URL="http://..."
RADARR_INSTANCE_1_API_KEY="..."
```

## Example Claude Desktop Usage

Once configured, you can ask Claude Desktop:

**TV Series Management:**
- *"Search for Breaking Bad and add it to Sonarr"*
- *"Check what's in my Sonarr download queue"*
- *"Get all episodes for series ID 123"*

**Movie Management:**
- *"Find The Matrix in external databases and add to Radarr"*
- *"Show me my Radarr download history"*
- *"What quality profiles are available for movies?"*

**Queue Management:**
- *"Remove queue item 456 from downloads"*
- *"Show me what's currently downloading"*

## Testing

Test the integration with provided scripts:

```bash
# Test without HTTP server
python3 test_mcp_direct.py

# Test with HTTP server (if running)
python3 test_mcp.py
```

## Configuration Files

Claude Desktop configuration locations:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`  
- **Linux**: `~/.config/claude/claude_desktop_config.json`

## Troubleshooting

1. **Authentication Issues**: Verify `TOOL_API_KEY` environment variable
2. **Connection Issues**: Check server URL and network accessibility
3. **Tool Not Found**: Ensure server startup completed successfully
4. **Instance Issues**: Use "default" for instance names unless specific instance needed

## Implementation Details

- **Protocol**: JSON-RPC 2.0 over HTTP
- **Transport**: HTTP POST + Server-Sent Events  
- **Authentication**: Bearer token (same as existing API)
- **Error Handling**: Standard JSON-RPC error codes
- **Real-time Updates**: SSE endpoint for progress tracking
- **Auto-Generation**: MCP tools are automatically generated from your OpenAPI spec

## Auto-Generation Workflow

Your MCP tools stay in sync with your API automatically:

1. **When you modify API endpoints** - just run `python3 regenerate_all.py`
2. **This updates** both `openapi.json` AND `mcp_tools_generated.py`
3. **Server automatically uses** the generated tools (no code changes needed)

### Regeneration Commands
```bash
# Regenerate everything (OpenAPI + MCP tools)
python3 regenerate_all.py

# Or individually
python3 generate_openapi.py      # Generates OpenAPI + MCP tools
python3 generate_mcp_tools.py    # MCP tools only
```

### Auto-Generated Files
- `mcp_tools_generated.py` - Auto-generated from OpenAPI spec
- `openapi.json` / `openapi-chatgpt.json` - Your existing OpenAPI files

### Backup Manual File
- `mcp_tools.py` - Manual backup (used if auto-generation fails)

## Security

- Uses existing Bearer token authentication
- Same security model as main API
- Tools require explicit user consent in Claude Desktop
- No automatic actions without user approval