#!/usr/bin/env python3
"""
Simple MCP client test script to verify the implementation
"""
import asyncio
import json
import httpx

# Test configuration
MCP_URL = "http://localhost:8000/mcp"
API_KEY = "your-api-key-here"  # Replace with actual API key
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

async def send_mcp_request(method: str, params: dict = None, request_id: str = "test-1"):
    """Send an MCP JSON-RPC request"""
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method
    }
    if params:
        request["params"] = params
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(MCP_URL, json=request, headers=HEADERS)
            return response.json()
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

async def test_mcp_server():
    """Test basic MCP server functionality"""
    print("Testing MCP Server Integration...")
    print("=" * 50)
    
    # Test 1: Initialize
    print("1. Testing MCP initialize...")
    init_params = {
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
    
    response = await send_mcp_request("initialize", init_params, "init-1")
    print(f"Initialize response: {json.dumps(response, indent=2)}")
    print()
    
    # Test 2: List Tools
    print("2. Testing tools/list...")
    response = await send_mcp_request("tools/list", {}, "list-1")
    print(f"Tools list response: {json.dumps(response, indent=2)}")
    print()
    
    # Test 3: Call a tool (list instances)
    print("3. Testing tools/call (list_sonarr_instances)...")
    call_params = {
        "name": "list_sonarr_instances",
        "arguments": {}
    }
    response = await send_mcp_request("tools/call", call_params, "call-1")
    print(f"Tool call response: {json.dumps(response, indent=2)}")
    print()
    
    # Test 4: Call another tool (search series)
    print("4. Testing tools/call (search_sonarr_series)...")
    call_params = {
        "name": "search_sonarr_series", 
        "arguments": {
            "instance_name": "default",
            "term": "Breaking Bad"
        }
    }
    response = await send_mcp_request("tools/call", call_params, "call-2")
    print(f"Search response: {json.dumps(response, indent=2)}")
    print()
    
    # Test 5: Ping
    print("5. Testing ping...")
    response = await send_mcp_request("ping", {}, "ping-1")
    print(f"Ping response: {json.dumps(response, indent=2)}")
    print()

def main():
    """Run the MCP test"""
    print("MCP Server Test Script")
    print("Make sure your server is running on http://localhost:8000")
    print("Update API_KEY variable with your actual API key")
    print()
    
    try:
        asyncio.run(test_mcp_server())
        print("✅ MCP tests completed!")
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    main()