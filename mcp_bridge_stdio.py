#!/usr/bin/env python3
"""
Simplified MCP Bridge for Claude Desktop
Uses line-by-line stdio communication as expected by Claude Desktop
"""
import asyncio
import json
import sys
import httpx
import os
from typing import Dict, Any

async def main():
    """Main stdio bridge loop"""
    server_url = os.getenv("MCP_SERVER_URL", "https://toolarr.moderncaveman.us/mcp")
    api_key = os.getenv("MCP_API_KEY", "")
    
    if not api_key:
        print(json.dumps({
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32603, "message": "MCP_API_KEY not set"}
        }))
        return
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                # Read request from stdin
                line = sys.stdin.readline()
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Parse request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"}
                    }))
                    continue
                
                # Forward to HTTP server
                try:
                    response = await client.post(
                        server_url,
                        json=request,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}"
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(json.dumps(result))
                    else:
                        print(json.dumps({
                            "jsonrpc": "2.0",
                            "id": request.get("id"),
                            "error": {
                                "code": -32603,
                                "message": f"HTTP {response.status_code}"
                            }
                        }))
                        
                except Exception as e:
                    print(json.dumps({
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "error": {
                            "code": -32603,
                            "message": f"Request failed: {str(e)}"
                        }
                    }))
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Bridge error: {str(e)}"
                    }
                }))

if __name__ == "__main__":
    asyncio.run(main())