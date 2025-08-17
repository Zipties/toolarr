#!/usr/bin/env python3
"""
MCP Bridge for Claude Desktop
Bridges stdio communication to HTTP MCP server
"""
import asyncio
import json
import sys
import httpx
from typing import Dict, Any

class MCPBridge:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.client = httpx.AsyncClient()
    
    async def send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC request to HTTP MCP server"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = await self.client.post(
                self.server_url,
                json=request,
                headers=headers,
                timeout=30.0
            )
            return response.json()
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    async def run(self):
        """Main bridge loop - read from stdin, send to HTTP server, write to stdout"""
        while True:
            try:
                # Read JSON-RPC request from stdin
                line = sys.stdin.readline().strip()
                if not line:
                    break
                
                request = json.loads(line)
                
                # Forward to HTTP MCP server
                response = await self.send_request(request)
                
                # Write response to stdout
                print(json.dumps(response), flush=True)
                
            except KeyboardInterrupt:
                break
            except json.JSONDecodeError:
                # Invalid JSON - send error response
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                # Other errors
                error_response = {
                    "jsonrpc": "2.0", 
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
        
        await self.client.aclose()

async def main():
    """Main entry point"""
    import os
    
    # Configuration from environment variables
    server_url = os.getenv("MCP_SERVER_URL", "https://toolarr.moderncaveman.us/mcp")
    api_key = os.getenv("MCP_API_KEY", "")
    
    if not api_key:
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": "MCP_API_KEY environment variable not set"
            }
        }), flush=True)
        sys.exit(1)
    
    bridge = MCPBridge(server_url, api_key)
    await bridge.run()

if __name__ == "__main__":
    asyncio.run(main())