#!/usr/bin/env python3
"""
MCP Bridge for Claude Desktop - Fixed Version
Strict JSON-RPC 2.0 compliance for Claude Desktop integration
"""
import asyncio
import json
import sys
import httpx
from typing import Dict, Any, Optional

class MCPBridge:
    def __init__(self, server_url: str, api_key: str):
        self.server_url = server_url
        self.api_key = api_key
        self.client = httpx.AsyncClient()
    
    def validate_jsonrpc_request(self, data: Dict[str, Any]) -> bool:
        """Validate JSON-RPC 2.0 request format"""
        if data.get("jsonrpc") != "2.0":
            return False
        if "method" not in data:
            return False
        # id is optional for notifications
        return True
    
    def create_error_response(self, request_id: Optional[Any], code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create a properly formatted JSON-RPC 2.0 error response"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        if data is not None:
            response["error"]["data"] = data
        return response
    
    def create_success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create a properly formatted JSON-RPC 2.0 success response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result if result is not None else {}
        }
    
    async def send_to_server(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send request to HTTP MCP server and return validated response"""
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
            
            if response.status_code == 200:
                server_response = response.json()
                
                # Validate server response format
                if not isinstance(server_response, dict):
                    return self.create_error_response(
                        request.get("id"), 
                        -32603, 
                        "Server returned non-object response"
                    )
                
                # Ensure response has proper JSON-RPC format
                if server_response.get("jsonrpc") != "2.0":
                    server_response["jsonrpc"] = "2.0"
                
                # Ensure id matches request
                if "id" in request:
                    server_response["id"] = request["id"]
                
                # Ensure response has either result or error
                if "result" not in server_response and "error" not in server_response:
                    server_response["result"] = {}
                
                return server_response
                
            elif response.status_code == 403:
                return self.create_error_response(
                    request.get("id"),
                    -32602,
                    "Authentication failed - check API key"
                )
            else:
                return self.create_error_response(
                    request.get("id"),
                    -32603,
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )
                
        except httpx.TimeoutException:
            return self.create_error_response(
                request.get("id"),
                -32603,
                "Request timeout"
            )
        except httpx.HTTPError as e:
            return self.create_error_response(
                request.get("id"),
                -32603,
                f"HTTP error: {str(e)}"
            )
        except json.JSONDecodeError:
            return self.create_error_response(
                request.get("id"),
                -32603,
                "Server returned invalid JSON"
            )
        except Exception as e:
            return self.create_error_response(
                request.get("id"),
                -32603,
                f"Unexpected error: {str(e)}"
            )
    
    async def run(self):
        """Main bridge loop with strict JSON-RPC 2.0 compliance"""
        try:
            while True:
                try:
                    # Read line from stdin
                    line = sys.stdin.readline()
                    if not line:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse JSON-RPC request
                    try:
                        request = json.loads(line)
                    except json.JSONDecodeError:
                        error_response = self.create_error_response(None, -32700, "Parse error")
                        print(json.dumps(error_response), flush=True)
                        continue
                    
                    # Validate request format
                    if not self.validate_jsonrpc_request(request):
                        error_response = self.create_error_response(
                            request.get("id"), 
                            -32600, 
                            "Invalid Request"
                        )
                        print(json.dumps(error_response), flush=True)
                        continue
                    
                    # Handle notification (no response expected)
                    if "id" not in request:
                        # For notifications, just forward to server but don't respond
                        await self.send_to_server(request)
                        continue
                    
                    # Forward request and get response
                    response = await self.send_to_server(request)
                    
                    # Send response
                    print(json.dumps(response), flush=True)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    # Last resort error handling
                    error_response = self.create_error_response(None, -32603, f"Bridge error: {str(e)}")
                    print(json.dumps(error_response), flush=True)
                    
        finally:
            await self.client.aclose()

async def main():
    """Main entry point"""
    import os
    
    # Get configuration from environment
    server_url = os.getenv("MCP_SERVER_URL", "https://toolarr.moderncaveman.us/mcp")
    api_key = os.getenv("MCP_API_KEY", "")
    
    if not api_key:
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": "MCP_API_KEY environment variable not set"
            }
        }
        print(json.dumps(error_response), flush=True)
        sys.exit(1)
    
    # Start bridge
    bridge = MCPBridge(server_url, api_key)
    await bridge.run()

if __name__ == "__main__":
    asyncio.run(main())