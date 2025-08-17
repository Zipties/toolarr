# Claude Desktop MCP Integration Setup

This guide shows how to connect Claude Desktop to your Toolarr MCP server.

## Prerequisites

- Claude Desktop installed
- Python 3.7+ with `httpx` package
- Access to your Toolarr server

## Setup Instructions

### 1. Install Required Package

```bash
pip install httpx
```

### 2. Download MCP Bridge Script

Copy the `mcp_bridge.py` file from this repository to your local machine.

### 3. Configure Claude Desktop

Add this configuration to your Claude Desktop settings file:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "toolarr": {
      "command": "python",
      "args": [
        "/absolute/path/to/mcp_bridge.py"
      ],
      "env": {
        "MCP_SERVER_URL": "https://toolarr.moderncaveman.us/mcp",
        "MCP_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

**Important**: 
- Replace `/absolute/path/to/mcp_bridge.py` with the actual path to the bridge script
- Replace `your-api-key-here` with your actual API key from the `.env` file

### 4. API Key

Your API key is: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`

### 5. Restart Claude Desktop

After saving the configuration, restart Claude Desktop completely.

## Available Tools

Once connected, Claude will have access to **31 tools** for managing your Sonarr and Radarr instances:

### Sonarr Tools
- `get_sonarr_episodes` - Get episodes for a TV series
- `lookup_series_sonarr` - Search for new series to add
- `add_series_sonarr` - Add new TV series
- `get_download_queue_sonarr` - Check download queue
- `series_with_tags` - Search library with tags
- `update_sonarr_series_properties` - Update series settings
- `delete_sonarr_series` - Remove series
- And more...

### Radarr Tools  
- `lookup_movie_radarr` - Search for new movies
- `add_movie_radarr` - Add new movies
- `get_download_queue_radarr` - Check download queue
- `update_radarr_movie_properties` - Update movie settings
- `delete_radarr_movie` - Remove movies
- `search_for_movie_upgrade` - Find better quality versions
- And more...

### Instance Management
- `list_sonarr_instances` - List configured Sonarr instances
- `list_radarr_instances` - List configured Radarr instances

## Default Instance Handling

All tools are configured to use the 'default' instance unless you specifically mention another instance name. This prevents Claude from guessing instance names.

## Troubleshooting

### Test the Bridge Manually

```bash
export MCP_SERVER_URL="https://toolarr.moderncaveman.us/mcp"
export MCP_API_KEY="your-api-key-here"
echo '{"jsonrpc": "2.0", "id": "test", "method": "ping"}' | python mcp_bridge.py
```

Expected response: `{"jsonrpc": "2.0", "id": "test", "result": {}}`

### Common Issues

1. **"Command not found"**: Ensure Python is in your PATH
2. **"Module not found"**: Install httpx with `pip install httpx`  
3. **"Authentication failed"**: Check your API key is correct
4. **"Connection refused"**: Verify the server URL is accessible

## Security Notes

- Keep your API key secure and don't share it
- The bridge script only forwards requests and doesn't store data
- All communication uses HTTPS encryption