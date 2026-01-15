# Toolarr MCP Server v2 - Architecture Summary

## What We Built

A clean, async MCP server that communicates via stdin/stdout following the Model Context Protocol specification.

## Core Files

### `mcp_server_v2.py` (Main Server)
- **McpServerV2**: Core protocol handler class
- **mcp_tool()**: Decorator for tool registration
- **main()**: Entry point that registers tools and starts server

**Key Features**:
- Line-delimited JSON-RPC 2.0 over stdio
- Tool registration system with JSON Schema
- Proper error handling with JSON-RPC error codes
- Logging to stderr (stdout reserved for protocol)

### `test_mcp_v2.py` (Test Suite)
- Automated tests for all MCP methods
- Interactive test mode for debugging
- Validates protocol compliance

### `MCP_V2_ARCHITECTURE.md` (Full Documentation)
- Complete architecture overview
- Protocol specification
- Integration guide
- Development guidelines

## How It Works

```
1. Client sends JSON-RPC request to stdin
   → {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}

2. Server parses and routes request
   → handle_request() → _handle_list_tools()

3. Server executes handler and formats response
   → {"jsonrpc": "2.0", "id": 1, "result": {"tools": [...]}}

4. Server writes response to stdout
   → Client receives result
```

## Tool Registration Pattern

```python
@mcp_tool(
    name="tool_name",
    description="What it does",
    parameters={
        "type": "object",
        "properties": {
            "param1": {"type": "string"}
        }
    }
)
async def tool_name(args: Dict[str, Any]):
    # Implementation
    return {"result": "data"}

# Register in main()
server.register_tool(
    tool_name._mcp_name,
    tool_name._mcp_description,
    tool_name._mcp_parameters,
    tool_name
)
```

## Testing

```bash
# Run automated tests
python3 test_mcp_v2.py

# Run interactive test (see logs)
python3 test_mcp_v2.py --interactive
```

**Test Results**: ✓ All tests pass
- Initialize handshake
- List tools
- Call tools
- Error handling
- Invalid method/tool detection

## Next Steps (Not Implemented Yet)

1. **Backend Clients** (Other agents building):
   - `sonarr_client.py` - Clean Sonarr API wrapper
   - `radarr_client.py` - Clean Radarr API wrapper

2. **Tool Migration**:
   - Port tools from `mcp_tools_generated.py`
   - Use new backend clients
   - Register in `main()`

3. **Instance Management**:
   - Load instances from environment variables
   - Support multiple Sonarr/Radarr instances

## Why This Architecture?

**Simple**: No HTTP server, no auth, no middleware complexity
**Fast**: Direct stdio communication, no network overhead
**Standard**: Pure MCP spec compliance
**Debuggable**: Clean separation of logs (stderr) and protocol (stdout)
**Testable**: Easy to test with subprocess pipes

## Key Design Decisions

1. **Async Throughout**: All handlers are async for consistency
2. **Decorator Pattern**: Clean tool registration with metadata
3. **Pydantic Models**: Type safety with existing `mcp_types.py`
4. **Error as Content**: Tool errors return as successful responses with `isError=true`
5. **Logging to stderr**: stdout is sacred - protocol only

## Integration with Claude

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "toolarr": {
      "command": "python3",
      "args": ["/path/to/mcp_server_v2.py"],
      "env": {
        "SONARR_INSTANCE_1_NAME": "default",
        "SONARR_INSTANCE_1_URL": "http://...",
        "SONARR_INSTANCE_1_API_KEY": "${SONARR_API_KEY}"
      }
    }
  }
}
```

## File Structure

```
toolarr/
├── mcp_server_v2.py           # New stdio-based MCP server
├── test_mcp_v2.py             # Test suite
├── MCP_V2_ARCHITECTURE.md     # Full documentation
├── ARCHITECTURE_SUMMARY.md    # This file
├── mcp_types.py               # Shared Pydantic models
├── backends/                  # Backend clients (being built)
│   ├── sonarr_client.py
│   └── radarr_client.py
└── [old files]                # Legacy HTTP implementation
```

## Status

**✓ Complete**:
- Core MCP server framework
- stdio transport layer
- JSON-RPC protocol handling
- Tool registration system
- Test suite
- Documentation

**⏳ In Progress** (Other Agents):
- Backend clients (sonarr_client, radarr_client)
- Tool implementations
- Instance management

**🔮 Future**:
- Tool migration from v1
- Deployment configuration
- Integration testing
