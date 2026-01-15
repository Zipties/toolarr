# Toolarr MCP Server v2 Architecture

## Overview

The MCP Server v2 is a complete rewrite of Toolarr's MCP implementation, moving from an HTTP gateway to a pure stdio-based MCP server following the Model Context Protocol specification.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Claude / MCP Client                   │
└─────────────────────────┬───────────────────────────────┘
                          │ stdin/stdout
                          │ JSON-RPC 2.0
                          │
┌─────────────────────────▼───────────────────────────────┐
│                  mcp_server_v2.py                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │          McpServerV2 (Core Protocol Handler)      │  │
│  │  - handle_request()    - JSON-RPC routing        │  │
│  │  - register_tool()     - Tool management         │  │
│  │  - run()               - stdio event loop         │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │              Tool Registry                        │  │
│  │  tools: Dict[str, McpTool]                       │  │
│  │  tool_handlers: Dict[str, Callable]              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────┘
                          │
                          │ Calls tool handlers
                          │
┌─────────────────────────▼───────────────────────────────┐
│                Backend Clients (Future)                  │
│  ┌────────────────┐  ┌────────────────┐                │
│  │ sonarr_client  │  │ radarr_client  │                │
│  └────────────────┘  └────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

## Core Components

### 1. McpServerV2 Class

**File**: `mcp_server_v2.py`

**Responsibilities**:
- Parse JSON-RPC 2.0 requests from stdin
- Route requests to appropriate handlers
- Manage tool registration
- Write JSON-RPC 2.0 responses to stdout
- Log to stderr (stdout reserved for protocol)

**Key Methods**:

```python
async def handle_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Main request router - parses JSON-RPC and dispatches to handlers"""

async def _handle_initialize(request: JsonRpcRequest) -> Dict[str, Any]:
    """MCP initialize handshake - returns server capabilities"""

async def _handle_list_tools(request: JsonRpcRequest) -> Dict[str, Any]:
    """Returns list of registered tools with schemas"""

async def _handle_call_tool(request: JsonRpcRequest) -> Dict[str, Any]:
    """Executes a tool and returns result"""

async def run():
    """Main stdio event loop - reads stdin, writes stdout"""
```

### 2. Tool Registration System

Tools are registered using the `@mcp_tool` decorator or via `server.register_tool()`:

```python
@mcp_tool(
    name="sonarr_list_series",
    description="List all series in Sonarr library",
    parameters={
        "type": "object",
        "properties": {
            "instance": {
                "type": "string",
                "default": "default",
                "description": "Sonarr instance name"
            }
        }
    }
)
async def list_series(args: Dict[str, Any]):
    instance = args.get("instance", "default")
    # Implementation will call sonarr_client
    return {"series": [...]}
```

### 3. Communication Protocol

**Transport**: stdio (stdin/stdout)
**Format**: Line-delimited JSON (one JSON object per line)
**Protocol**: JSON-RPC 2.0
**Logging**: stderr only (stdout reserved for protocol)

**Request Example**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "sonarr_list_series",
    "arguments": {"instance": "default"}
  }
}
```

**Response Example**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"series\": [...]}"
      }
    ],
    "isError": false
  }
}
```

## MCP Protocol Methods

### initialize
**Purpose**: Initial handshake between client and server
**Request**: Client capabilities and info
**Response**: Server capabilities and info

### tools/list
**Purpose**: Discover available tools
**Request**: Empty params
**Response**: Array of tool schemas

### tools/call
**Purpose**: Execute a tool
**Request**: Tool name and arguments
**Response**: Tool result or error (as content)

### ping
**Purpose**: Health check
**Request**: Empty params
**Response**: Status message

## Error Handling

**JSON-RPC Error Codes**:
- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid request (malformed JSON-RPC)
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

**Tool Errors**:
Tool execution errors are returned as successful responses with `isError: true`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{"type": "text", "text": "Error: Series not found"}],
    "isError": true
  }
}
```

## Testing

**Test Suite**: `test_mcp_v2.py`

**Tests**:
1. Initialize handshake
2. List tools
3. Call ping tool
4. Invalid method handling
5. Invalid tool handling

**Run Tests**:
```bash
python3 test_mcp_v2.py
```

**Interactive Test** (shows server logs):
```bash
python3 test_mcp_v2.py --interactive
```

## Future Work

### Phase 1: Backend Clients (In Progress)
- `sonarr_client.py` - Clean Sonarr API wrapper
- `radarr_client.py` - Clean Radarr API wrapper

### Phase 2: Tool Implementation
- Migrate existing tools from `mcp_tools_generated.py`
- Use new backend clients instead of old code
- Register tools in `main()` function

### Phase 3: Instance Management
- Load instances from environment variables
- Support multiple Sonarr/Radarr instances
- Instance selection in tool calls

### Phase 4: Deployment
- Update Docker setup for stdio mode
- Create MCP server configuration
- Integration testing

## Differences from v1

| Feature | v1 (HTTP) | v2 (stdio) |
|---------|-----------|------------|
| Transport | HTTP/FastAPI | stdin/stdout |
| Protocol | JSON-RPC over HTTP | JSON-RPC over stdio |
| Auth | OAuth 2.1, API keys | None (trusted local) |
| Deployment | Docker container with port | Spawned process |
| Tool Handlers | Lambda with auth params | Pure async functions |
| Logging | stdout/stderr mixed | stderr only |

## Benefits of v2

1. **Simpler**: No HTTP server, no auth middleware, no FastAPI
2. **Faster**: Direct process communication, no network overhead
3. **Reliable**: stdio is a stable, well-understood transport
4. **Standard**: Pure MCP spec compliance
5. **Debuggable**: Logs go to stderr, protocol to stdout

## Integration with Claude

**`.mcp.json` Configuration**:
```json
{
  "mcpServers": {
    "toolarr": {
      "command": "python3",
      "args": ["/home/cory/proj/toolarr/mcp_server_v2.py"],
      "env": {
        "SONARR_INSTANCE_1_NAME": "default",
        "SONARR_INSTANCE_1_URL": "http://192.168.45.10:8989",
        "SONARR_INSTANCE_1_API_KEY": "${SONARR_API_KEY}",
        "RADARR_INSTANCE_1_NAME": "default",
        "RADARR_INSTANCE_1_URL": "http://192.168.45.10:7878",
        "RADARR_INSTANCE_1_API_KEY": "${RADARR_API_KEY}"
      }
    }
  }
}
```

## Development Guidelines

### Adding a New Tool

1. **Define the tool function**:
```python
@mcp_tool(
    name="my_tool",
    description="What it does",
    parameters={...}
)
async def my_tool(args: Dict[str, Any]):
    # Implementation
    return result
```

2. **Register in main()**:
```python
server.register_tool(
    my_tool._mcp_name,
    my_tool._mcp_description,
    my_tool._mcp_parameters,
    my_tool
)
```

3. **Test it**:
```python
# In test_mcp_v2.py
test_response = await client.send_request("tools/call", {
    "name": "my_tool",
    "arguments": {...}
})
```

### Logging Best Practices

```python
import logging
logger = logging.getLogger(__name__)

# Always use logger, never print()
logger.debug("Detailed info for debugging")
logger.info("Important events")
logger.warning("Warning conditions")
logger.error("Error conditions")
logger.exception("Errors with stack trace")
```

**Remember**: stdout is ONLY for JSON-RPC protocol messages. All human-readable logs go to stderr.

## Resources

- MCP Specification: https://modelcontextprotocol.io
- JSON-RPC 2.0: https://www.jsonrpc.org/specification
- Existing Implementation: `mcp_server.py` (HTTP-based)
- Tool Definitions: `mcp_tools_generated.py`
