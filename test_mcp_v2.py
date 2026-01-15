#!/usr/bin/env python3
"""
Test script for MCP Server v2

Tests the stdio-based MCP server by:
1. Starting the server process
2. Sending initialize request
3. Listing tools
4. Calling the ping tool
"""

import json
import asyncio
import subprocess
import sys
from typing import Dict, Any


class McpClient:
    """Simple MCP client for testing."""

    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process = None
        self.request_id = 0

    async def start(self):
        """Start the MCP server process."""
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, self.server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        print(f"✓ Started MCP server (PID: {self.process.pid})")

    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request and wait for response."""
        self.request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }

        if params:
            request["params"] = params

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        print(f"→ Sent: {method} (id={self.request_id})")

        # Read response
        response_line = await self.process.stdout.readline()
        response = json.loads(response_line.decode().strip())

        print(f"← Received: {json.dumps(response, indent=2)}")

        return response

    async def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            await self.process.wait()
            print("✓ Server stopped")


async def test_mcp_server():
    """Run MCP server tests."""
    print("=" * 60)
    print("Testing Toolarr MCP Server v2")
    print("=" * 60)
    print()

    client = McpClient("/home/cory/proj/toolarr/mcp_server_v2.py")

    try:
        # Start server
        await client.start()
        await asyncio.sleep(0.5)  # Give server time to start

        # Test 1: Initialize
        print("\n[Test 1] Initialize")
        print("-" * 60)
        init_response = await client.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        })

        assert "result" in init_response, "Initialize should return result"
        assert init_response["result"]["serverInfo"]["name"] == "toolarr-mcp-server"
        print("✓ Initialize successful")

        # Test 2: List tools
        print("\n[Test 2] List Tools")
        print("-" * 60)
        list_response = await client.send_request("tools/list")

        assert "result" in list_response, "tools/list should return result"
        assert "tools" in list_response["result"], "Result should contain tools"

        tools = list_response["result"]["tools"]
        print(f"✓ Found {len(tools)} tools")

        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # Test 3: Call ping tool
        print("\n[Test 3] Call Ping Tool")
        print("-" * 60)
        call_response = await client.send_request("tools/call", {
            "name": "ping",
            "arguments": {}
        })

        assert "result" in call_response, "tools/call should return result"
        assert "content" in call_response["result"], "Result should contain content"
        assert call_response["result"]["isError"] is False, "Should not be an error"

        print("✓ Ping tool executed successfully")

        # Test 4: Test invalid method
        print("\n[Test 4] Invalid Method")
        print("-" * 60)
        error_response = await client.send_request("invalid/method")

        assert "error" in error_response, "Invalid method should return error"
        assert error_response["error"]["code"] == -32601, "Should be method not found"
        print("✓ Error handling works correctly")

        # Test 5: Test invalid tool
        print("\n[Test 5] Invalid Tool")
        print("-" * 60)
        invalid_tool_response = await client.send_request("tools/call", {
            "name": "nonexistent_tool",
            "arguments": {}
        })

        assert "error" in invalid_tool_response, "Invalid tool should return error"
        print("✓ Invalid tool handling works correctly")

        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await client.stop()


async def interactive_test():
    """
    Interactive test - print server stderr to see logs.

    This test keeps the server running and shows its logs.
    """
    print("Starting MCP server in interactive mode...")
    print("Press Ctrl+C to stop")
    print()

    process = await asyncio.create_subprocess_exec(
        sys.executable, "/home/cory/proj/toolarr/mcp_server_v2.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def read_stderr():
        """Read and print stderr (server logs)."""
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            print(f"[SERVER] {line.decode().strip()}", file=sys.stderr)

    # Start stderr reader
    stderr_task = asyncio.create_task(read_stderr())

    try:
        # Send initialize
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "interactive-test", "version": "1.0.0"}
            }
        }) + "\n"

        process.stdin.write(init_req.encode())
        await process.stdin.drain()

        # Read response
        response = await process.stdout.readline()
        print(f"Response: {response.decode().strip()}")

        # Keep running
        await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\nStopping...")

    finally:
        process.terminate()
        await process.wait()
        stderr_task.cancel()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_test())
    else:
        asyncio.run(test_mcp_server())
