# Adding Tools to MCP Server v2 - Quick Guide

## Simple Example: Placeholder Tools

Here's how to add placeholder tools that will later be filled in with real implementations:

```python
# In mcp_server_v2.py, add to main() function:

# Example 1: Simple tool with no parameters
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
async def sonarr_list_series(args: Dict[str, Any]):
    instance = args.get("instance", "default")
    # TODO: Replace with actual sonarr_client call
    return {
        "status": "not_implemented",
        "message": "Will call sonarr_client.list_series()",
        "instance": instance
    }

# Example 2: Tool with required parameters
@mcp_tool(
    name="sonarr_search_series",
    description="Search for a series by name",
    parameters={
        "type": "object",
        "properties": {
            "term": {
                "type": "string",
                "description": "Search term"
            },
            "instance": {
                "type": "string",
                "default": "default",
                "description": "Sonarr instance name"
            }
        },
        "required": ["term"]
    }
)
async def sonarr_search_series(args: Dict[str, Any]):
    term = args.get("term")
    instance = args.get("instance", "default")

    # TODO: Replace with actual sonarr_client call
    return {
        "status": "not_implemented",
        "message": f"Will search for '{term}' on instance '{instance}'",
        "term": term,
        "instance": instance
    }

# Register tools
server.register_tool(
    sonarr_list_series._mcp_name,
    sonarr_list_series._mcp_description,
    sonarr_list_series._mcp_parameters,
    sonarr_list_series
)

server.register_tool(
    sonarr_search_series._mcp_name,
    sonarr_search_series._mcp_description,
    sonarr_search_series._mcp_parameters,
    sonarr_search_series
)
```

## With Backend Client (Once Available)

```python
# Import the backend client
from backends.sonarr_client import SonarrClient

# Initialize clients (load from env)
sonarr_instances = {}
i = 1
while True:
    name = os.environ.get(f"SONARR_INSTANCE_{i}_NAME")
    if not name:
        break
    url = os.environ.get(f"SONARR_INSTANCE_{i}_URL")
    api_key = os.environ.get(f"SONARR_INSTANCE_{i}_API_KEY")
    if url and api_key:
        sonarr_instances[name] = SonarrClient(url, api_key)
    i += 1

# Real implementation
@mcp_tool(
    name="sonarr_list_series",
    description="List all series in Sonarr library",
    parameters={
        "type": "object",
        "properties": {
            "instance": {"type": "string", "default": "default"}
        }
    }
)
async def sonarr_list_series(args: Dict[str, Any]):
    instance_name = args.get("instance", "default")

    if instance_name not in sonarr_instances:
        raise ValueError(f"Unknown instance: {instance_name}")

    client = sonarr_instances[instance_name]
    series = await client.list_series()

    return {
        "instance": instance_name,
        "series": series,
        "total": len(series)
    }
```

## Complex Tool Example

```python
@mcp_tool(
    name="sonarr_add_series",
    description="Add a new series to Sonarr",
    parameters={
        "type": "object",
        "properties": {
            "tvdb_id": {
                "type": "integer",
                "description": "TVDB ID of the series"
            },
            "quality_profile_id": {
                "type": "integer",
                "description": "Quality profile ID"
            },
            "root_folder": {
                "type": "string",
                "description": "Root folder path"
            },
            "monitored": {
                "type": "boolean",
                "default": True,
                "description": "Monitor the series"
            },
            "search_now": {
                "type": "boolean",
                "default": True,
                "description": "Search for episodes immediately"
            },
            "instance": {
                "type": "string",
                "default": "default",
                "description": "Sonarr instance name"
            }
        },
        "required": ["tvdb_id", "quality_profile_id", "root_folder"]
    }
)
async def sonarr_add_series(args: Dict[str, Any]):
    instance_name = args.get("instance", "default")

    if instance_name not in sonarr_instances:
        raise ValueError(f"Unknown instance: {instance_name}")

    client = sonarr_instances[instance_name]

    result = await client.add_series(
        tvdb_id=args["tvdb_id"],
        quality_profile_id=args["quality_profile_id"],
        root_folder=args["root_folder"],
        monitored=args.get("monitored", True),
        search_now=args.get("search_now", True)
    )

    return {
        "success": True,
        "series": result,
        "instance": instance_name
    }
```

## Testing Your Tool

Add to `test_mcp_v2.py`:

```python
# Test new tool
print("\n[Test] Sonarr List Series")
print("-" * 60)
response = await client.send_request("tools/call", {
    "name": "sonarr_list_series",
    "arguments": {"instance": "default"}
})

assert "result" in response
assert response["result"]["isError"] is False
print("✓ Tool executed successfully")
```

## Common Patterns

### Instance Selection
```python
instance_name = args.get("instance", "default")
if instance_name not in instances:
    raise ValueError(f"Unknown instance: {instance_name}")
client = instances[instance_name]
```

### Error Handling
```python
try:
    result = await client.some_operation()
    return {"success": True, "data": result}
except ValueError as e:
    raise  # Let MCP server handle it
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Return Format
```python
# Simple success
return {"success": True, "data": [...]}

# With metadata
return {
    "success": True,
    "instance": instance_name,
    "total": len(items),
    "items": items
}

# Error (raise exception, MCP server formats it)
raise ValueError("Series not found")
```

## Migration from Old Tools

Look at `mcp_tools_generated.py` to see existing tool definitions, then:

1. Copy the parameter schema
2. Rewrite the handler to use new backend client
3. Test with `test_mcp_v2.py`

Example old tool:
```python
# OLD (from mcp_tools_generated.py)
mcp_server.register_tool(
    "get_sonarr_episodes",
    "Retrieves all episodes for a given series",
    {
        "type": "object",
        "properties": {
            "instance_name": {...},
            "series_id": {"type": "integer"}
        },
        "required": ["series_id"]
    },
    lambda args, auth: get_episodes(
        get_sonarr_instance(args.get("instance_name", "default")),
        args.get("series_id")
    )
)
```

New version:
```python
# NEW (in mcp_server_v2.py)
@mcp_tool(
    name="get_sonarr_episodes",
    description="Retrieves all episodes for a given series",
    parameters={
        "type": "object",
        "properties": {
            "series_id": {"type": "integer", "description": "Series ID"},
            "instance": {"type": "string", "default": "default"}
        },
        "required": ["series_id"]
    }
)
async def get_sonarr_episodes(args: Dict[str, Any]):
    instance = args.get("instance", "default")
    series_id = args["series_id"]

    client = sonarr_instances[instance]
    episodes = await client.get_episodes(series_id)

    return {"series_id": series_id, "episodes": episodes}
```

## Next Steps

1. Create placeholder tools (copy schemas from `mcp_tools_generated.py`)
2. Test that they're discoverable and callable
3. Wait for backend clients to be ready
4. Replace placeholder implementations with real client calls
5. Test end-to-end
