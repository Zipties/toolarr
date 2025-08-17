#!/usr/bin/env python3
"""
Direct MCP Server for Claude Desktop
Implements MCP protocol directly without HTTP bridging
"""
import asyncio
import json
import sys
import httpx
import os
from typing import Dict, Any, List

class DirectMCPServer:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.tools = []
        self.initialized = False
        
    async def initialize(self):
        """Initialize by fetching tools from HTTP server"""
        async with httpx.AsyncClient() as client:
            try:
                # Get tools list
                response = await client.post(
                    self.server_url,
                    json={"jsonrpc": "2.0", "id": "init", "method": "tools/list"},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        self.tools = result["result"]["tools"]
                        self.initialized = True
                        
            except Exception as e:
                print(f"Failed to initialize: {e}", file=sys.stderr)
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request directly"""
        method = request.get("method")
        request_id = request.get("id")
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {},
                        "prompts": {}
                    },
                    "serverInfo": {
                        "name": "toolarr-mcp-server",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self.tools}
            }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"resources": []}
            }
        
        elif method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"prompts": []}
            }
        
        elif method == "tools/call":
            # Forward tool calls to HTTP server
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        self.server_url,
                        json=request,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.api_key}"
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        return response.json()
                    else:
                        return {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": f"HTTP {response.status_code}"
                            }
                        }
                        
                except Exception as e:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Tool call failed: {str(e)}"
                        }
                    }
        
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {}
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": "Method not found"
                }
            }

async def main():
    """Main server loop"""
    server_url = os.getenv("MCP_SERVER_URL", "https://toolarr.moderncaveman.us/mcp")
    api_key = os.getenv("MCP_API_KEY", "")
    
    if not api_key:
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": "MCP_API_KEY not set"}
        }))
        return
    
    server = DirectMCPServer(server_url, api_key)
    await server.initialize()
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
                
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = await server.handle_request(request)
                print(json.dumps(response))
                
            except json.JSONDecodeError:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": "Parse error"}
                }))
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Server error: {str(e)}"}
            }))

if __name__ == "__main__":
    asyncio.run(main())