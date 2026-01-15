# Toolarr MCP Server v2 - Quick Start

## What Is This?

A pure stdio MCP server for Toolarr that lets Claude interact with Sonarr and Radarr. No HTTP, no auth, just clean JSON-RPC over stdin/stdout.

## Files

```
mcp_server_v2.py              # The server
test_mcp_v2.py                # Test suite
MCP_V2_ARCHITECTURE.md        # Full docs
ARCHITECTURE_SUMMARY.md       # Quick reference
ADDING_TOOLS_EXAMPLE.md       # Tool development
STATUS.md                     # Current status
```

## Run Tests

```bash
cd /home/cory/proj/toolarr
python3 test_mcp_v2.py
```

**Expected Output**: ✓ All tests passed!

## How It Works

```
Claude sends JSON-RPC to stdin → Server routes to handler → Handler executes tool → Server returns JSON-RPC to stdout
```

## Architecture

```python
class McpServerV2:
    def __init__(self):
        self.tools = {}           # Tool metadata
        self.tool_handlers = {}   # Tool functions

    async def run(self):
        """Read stdin, write stdout"""

    async def handle_request(self, request):
        """Route JSON-RPC to handlers"""
```

## MCP Methods

| Method | What It Does |
|--------|--------------|
| `initialize` | Handshake between client/server |
| `tools/list` | Returns available tools |
| `tools/call` | Executes a tool |
| `ping` | Health check |

## Adding a Tool

```python
@mcp_tool(
    name="my_tool",
    description="What it does",
    parameters={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        }
    }
)
async def my_tool(args: Dict[str, Any]):
    return {"result": "data"}

# Register it
server.register_tool(
    my_tool._mcp_name,
    my_tool._mcp_description,
    my_tool._mcp_parameters,
    my_tool
)
```

## Current Status

**✓ Done**: Server framework, test suite, documentation
**⏳ In Progress**: Backend clients (other agents)
**🔮 Next**: Wire up tools once clients are ready

## Integration with Claude

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "toolarr": {
      "command": "python3",
      "args": ["/home/cory/proj/toolarr/mcp_server_v2.py"],
      "env": {
        "SONARR_INSTANCE_1_NAME": "default",
        "SONARR_INSTANCE_1_URL": "http://192.168.45.10:8989",
        "SONARR_INSTANCE_1_API_KEY": "${SONARR_API_KEY}"
      }
    }
  }
}
```

## Key Features

- **Simple**: Pure stdio, no HTTP complexity
- **Fast**: Direct process communication
- **Standard**: MCP spec compliant
- **Testable**: Easy to test with subprocess pipes
- **Debuggable**: Logs to stderr, protocol to stdout

## Error Handling

**JSON-RPC Errors**:
- `-32700`: Parse error
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

**Tool Errors**:
Returned as successful response with `isError: true`

## Logging

```python
import logging
logger = logging.getLogger(__name__)

# Always use logger, never print()
logger.debug("Debug info")
logger.info("Important events")
logger.error("Errors")
```

**Important**: stdout is ONLY for JSON-RPC. All logs go to stderr.

## Next Steps

1. **For Tool Developers**: See `ADDING_TOOLS_EXAMPLE.md`
2. **For Architecture**: See `MCP_V2_ARCHITECTURE.md`
3. **For Status**: See `STATUS.md`

## Test It Now

```bash
# Run the test suite
python3 test_mcp_v2.py

# You should see:
# ✓ Initialize successful
# ✓ Found 1 tools
# ✓ Ping tool executed successfully
# ✓ Error handling works correctly
# All tests passed! ✓
```

## Questions?

- **What's MCP?** Model Context Protocol - standard for AI tool integration
- **Why stdio?** Simpler than HTTP, standard transport, easy to test
- **Where's the HTTP server?** Gone! Pure stdio now
- **What about auth?** Not needed - local trusted process
- **When can I use it?** Framework done, waiting on backend clients

## Development

**Add a tool**:
1. Define function with `@mcp_tool` decorator
2. Register in `main()`
3. Test with `test_mcp_v2.py`

**Debug**:
```bash
# Run in interactive mode to see logs
python3 test_mcp_v2.py --interactive
```

## Summary

Built a clean, production-ready MCP server foundation. Ready for tool implementations once backend clients are complete. All tests passing, fully documented.

**Want to start coding?** See `ADDING_TOOLS_EXAMPLE.md`
