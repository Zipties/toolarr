# Claude Desktop Direct MCP Connection Setup

**NEW**: Your Toolarr server now supports direct HTTP MCP connections from Claude Desktop, eliminating the need for bridge scripts!

## Prerequisites

- Claude Desktop with MCP support
- Your deployed Toolarr server with OAuth support

## Setup Instructions

### Option 1: Use Claude Desktop UI - OAuth Client Credentials (Recommended)

1. **Open Claude Desktop Settings**
2. **Navigate to MCP Servers section**
3. **Add New Server** with these details:
   - **Server URL**: `https://toolarr.moderncaveman.us/mcp`
   - **Authentication Type**: OAuth Client Credentials
   - **Client ID**: `toolarr-client`
   - **Client Secret**: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`

### Option 2: Use Claude Desktop UI - Bearer Token (Alternative)

1. **Open Claude Desktop Settings**
2. **Navigate to MCP Servers section**
3. **Add New Server** with these details:
   - **Server URL**: `https://toolarr.moderncaveman.us/mcp`
   - **Authentication Type**: Bearer Token
   - **Token**: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`

### Option 3: Configuration File Method

If Claude Desktop doesn't have UI support yet, add this to your config file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

**OAuth Client Credentials (Recommended):**
```json
{
  "mcpServers": {
    "toolarr": {
      "url": "https://toolarr.moderncaveman.us/mcp",
      "auth": {
        "type": "oauth_client_credentials",
        "client_id": "toolarr-client",
        "client_secret": "b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0"
      }
    }
  }
}
```

**Bearer Token (Alternative):**
```json
{
  "mcpServers": {
    "toolarr": {
      "url": "https://toolarr.moderncaveman.us/mcp",
      "auth": {
        "type": "bearer",
        "token": "b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0"
      }
    }
  }
}
```

## Authentication

Your server supports **both** authentication methods:

### 1. OAuth Client Credentials (Recommended)
- **Client ID**: `toolarr-client`
- **Client Secret**: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`
- **Authorization Header**: `Basic dG9vbGFyci1jbGllbnQ6YjM5NzVmNzFhZjE4ZTgyMmQxYTAxOWY1Mzk5OWM5MmYxMzEwOWVjMzliMzhmNTA4MzljYjQwOGMwYTkwZGZhMA==`

### 2. Bearer Token (Alternative)
- **Token**: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`
- **Authorization Header**: `Bearer b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`

**Both methods are fully functional through Traefik and direct connection!**

## Available Tools

Once connected, Claude will have access to **31 tools**:

### Sonarr Tools (15)
- `get_sonarr_episodes` - Get episodes for TV series
- `lookup_series_sonarr` - Search for new series to add
- `add_series_sonarr` - Add new TV series
- `get_download_queue_sonarr` - Check download queue
- `series_with_tags` - Search library with tags
- `update_sonarr_series_properties` - Update series settings
- `delete_sonarr_series` - Remove series
- And 8 more tools...

### Radarr Tools (12)
- `lookup_movie_radarr` - Search for new movies
- `add_movie_radarr` - Add new movies
- `get_download_queue_radarr` - Check download queue
- `update_radarr_movie_properties` - Update movie settings
- `delete_radarr_movie` - Remove movies
- `search_for_movie_upgrade` - Find better quality versions
- And 6 more tools...

### Instance Management Tools (4)
- `list_sonarr_instances` - List Sonarr instances
- `list_radarr_instances` - List Radarr instances
- `season_search` - Search for season episodes
- `series_search` - Search for series episodes

## Testing Your Connection

### Manual Test (Optional)
```bash
# Test OAuth Client Credentials authentication
curl -X POST https://toolarr.moderncaveman.us/mcp \
  -H "Content-Type: application/json" \
  -u "toolarr-client:b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "ping"}'

# Test Bearer token authentication (alternative)
curl -X POST https://toolarr.moderncaveman.us/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "ping"}'

# Expected response: {"jsonrpc":"2.0","id":1,"result":{}}
```

### In Claude Desktop
Once configured, try asking:
- **"Can you check my Sonarr download queue?"**
- **"Search for the TV series Breaking Bad"**
- **"List my Radarr instances"**
- **"Show me what's in my download history"**

## Troubleshooting

### Connection Issues
1. **Verify server is running**: Check https://toolarr.moderncaveman.us/docs
2. **Check credentials**: Ensure Client ID and Secret are correct
3. **Network access**: Verify Claude Desktop can reach your server

### Authentication Failures
- **Double-check Client Secret**: Must match exactly
- **Try Bearer token method**: As fallback for testing
- **Check server logs**: For detailed error information

## Security Notes

- **Client credentials are equivalent to API keys** - keep them secure
- **HTTPS encryption** protects credentials in transit
- **No bridge scripts needed** - direct connection is more secure
- **Environment variables** store secrets securely on server

## Advantages of Direct Connection

✅ **No bridge scripts** - eliminates complexity and failure points
✅ **Better security** - direct HTTPS connection
✅ **Faster response** - no proxy overhead  
✅ **Easier setup** - just enter credentials in UI
✅ **Auto-reconnection** - Claude Desktop handles connection management
✅ **Real-time updates** - server can push notifications

Your Toolarr MCP integration is now enterprise-ready! 🚀