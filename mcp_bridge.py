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
            print(f"Sending to {self.server_url}: {json.dumps(request)}", file=sys.stderr, flush=True)
            
            response = await self.client.post(
                self.server_url,
                json=request,
                headers=headers,
                timeout=30.0
            )
            
            print(f"HTTP status: {response.status_code}", file=sys.stderr, flush=True)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Server response: {json.dumps(result)}", file=sys.stderr, flush=True)
                return result
            else:
                print(f"HTTP error: {response.text}", file=sys.stderr, flush=True)
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32603,
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
                
        except httpx.HTTPError as e:
            print(f"HTTP error: {e}", file=sys.stderr, flush=True)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32603,
                    "message": f"HTTP error: {str(e)}"
                }
            }
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr, flush=True)
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
        try:
            # Write startup debug info to stderr
            print(f"MCP Bridge starting. Server: {self.server_url}", file=sys.stderr, flush=True)
            
            while True:
                try:
                    # Read JSON-RPC request from stdin
                    line = sys.stdin.readline().strip()
                    if not line:
                        print("EOF received, exiting", file=sys.stderr, flush=True)
                        break
                    
                    print(f"Received: {line}", file=sys.stderr, flush=True)
                    request = json.loads(line)
                    
                    # Forward to HTTP MCP server
                    response = await self.send_request(request)
                    print(f"Response: {json.dumps(response)}", file=sys.stderr, flush=True)
                    
                    # Ensure response has required fields
                    if "jsonrpc" not in response:
                        response["jsonrpc"] = "2.0"
                    if "id" not in response and "id" in request:
                        response["id"] = request["id"]
                    
                    # Write response to stdout
                    print(json.dumps(response), flush=True)
                    
                except KeyboardInterrupt:
                    print("Keyboard interrupt received", file=sys.stderr, flush=True)
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}", file=sys.stderr, flush=True)
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
                    print(f"Bridge error: {e}", file=sys.stderr, flush=True)
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
        finally:
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