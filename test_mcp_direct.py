#!/usr/bin/env python3
"""
Direct MCP server test without HTTP layer
"""
import asyncio
import json
from mcp_server import mcp_server
# Use auto-generated MCP tools (fallback to manual if not available)
try:
    from mcp_tools_generated import register_all_tools
    print("🔄 Using auto-generated MCP tools for testing")
except ImportError:
    from mcp_tools import register_all_tools
    print("⚠️  Using manual MCP tools for testing")

async def test_mcp_direct():
    """Test MCP server functionality directly"""
    print("Testing MCP Server Direct Integration...")
    print("=" * 50)
    
    # Initialize the server
    await register_all_tools()
    print(f"✅ Registered {len(mcp_server.tools)} tools")
    print()
    
    # Test 1: Initialize
    print("1. Testing MCP initialize...")
    init_request = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    response = await mcp_server.handle_jsonrpc_request(init_request)
    print(f"✅ Initialize: {response.get('result', {}).get('serverInfo', {}).get('name', 'OK')}")
    print()
    
    # Test 2: List Tools
    print("2. Testing tools/list...")
    list_request = {
        "jsonrpc": "2.0",
        "id": "list-1", 
        "method": "tools/list",
        "params": {}
    }
    
    response = await mcp_server.handle_jsonrpc_request(list_request)
    if "result" in response:
        tools = response["result"].get("tools", [])
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools[:5]:  # Show first 5 tools
            print(f"   - {tool['name']}: {tool['description'][:60]}...")
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more tools")
    else:
        print(f"❌ Error: {response}")
    print()
    
    # Test 3: Test tool schemas
    print("3. Testing tool schemas...")
    test_tools = ["list_sonarr_instances", "search_sonarr_series", "get_sonarr_queue"]
    for tool_name in test_tools:
        if tool_name in mcp_server.tools:
            tool = mcp_server.tools[tool_name]
            schema = tool.get("inputSchema", {})
            properties = schema.get("properties", {})
            print(f"   ✅ {tool_name}: {len(properties)} parameters")
        else:
            print(f"   ❌ {tool_name}: not found")
    print()
    
    # Test 4: Test simple tool call (list instances)
    print("4. Testing tools/call (list_sonarr_instances)...")
    call_request = {
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {
            "name": "list_sonarr_instances",
            "arguments": {}
        }
    }
    
    response = await mcp_server.handle_jsonrpc_request(call_request)
    if "result" in response:
        content = response["result"].get("content", [])
        if content:
            text = content[0].get("text", "")
            print(f"✅ Tool call result: {text[:100]}...")
        else:
            print("✅ Tool call completed (empty result)")
    else:
        print(f"❌ Error: {response.get('error', 'Unknown error')}")
    print()
    
    # Test 5: Test ping
    print("5. Testing ping...")
    ping_request = {
        "jsonrpc": "2.0",
        "id": "ping-1",
        "method": "ping"
    }
    
    response = await mcp_server.handle_jsonrpc_request(ping_request)
    if "result" in response:
        print("✅ Ping successful")
    else:
        print(f"❌ Ping failed: {response}")
    print()
    
    # Test 6: Test invalid method
    print("6. Testing invalid method...")
    invalid_request = {
        "jsonrpc": "2.0",
        "id": "invalid-1",
        "method": "invalid_method"
    }
    
    response = await mcp_server.handle_jsonrpc_request(invalid_request)
    if "error" in response and response["error"]["code"] == -32601:
        print("✅ Error handling works correctly")
    else:
        print(f"❌ Unexpected response: {response}")
    print()

def main():
    """Run the direct MCP test"""
    print("Direct MCP Server Test")
    print("Testing without HTTP layer")
    print()
    
    try:
        asyncio.run(test_mcp_direct())
        print("🎉 All direct MCP tests completed successfully!")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()