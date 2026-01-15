#!/usr/bin/env python3
"""
Toolarr MCP Server v2 - Pure stdio MCP implementation

This is a clean, async MCP server that communicates via stdio following
the Model Context Protocol specification. No HTTP, no FastAPI - just
JSON-RPC over stdin/stdout.
"""

import sys
import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, Awaitable
from functools import wraps

from mcp_types import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcError,
    McpCapabilities, McpInitializeParams, McpInitializeResult,
    McpListToolsResult, McpCallToolParams, McpCallToolResult,
    McpTool
)

# Configure logging to stderr (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class McpServerV2:
    """
    Pure stdio MCP server for Toolarr.

    Handles JSON-RPC 2.0 requests over stdin/stdout and manages
    tool registration and execution.
    """

    def __init__(self, server_name: str = "toolarr-mcp-server", version: str = "2.0.0"):
        self.server_name = server_name
        self.version = version
        self.tools: Dict[str, McpTool] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.initialized = False

        logger.info(f"Initializing {server_name} v{version}")

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[Any]]
    ):
        """
        Register a tool with the MCP server.

        Args:
            name: Tool name (e.g., "sonarr_list_series")
            description: Human-readable description for AI
            parameters: JSON Schema for tool parameters
            handler: Async function that executes the tool
        """
        tool = McpTool(
            name=name,
            description=description,
            inputSchema=parameters
        )

        self.tools[name] = tool
        self.tool_handlers[name] = handler

        logger.debug(f"Registered tool: {name}")

    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming JSON-RPC 2.0 request.

        Args:
            request_data: Parsed JSON-RPC request

        Returns:
            JSON-RPC response dictionary
        """
        try:
            request = JsonRpcRequest(**request_data)
        except Exception as e:
            logger.error(f"Failed to parse request: {e}")
            return self._error_response(None, -32700, "Parse error", str(e))

        logger.debug(f"Handling request: {request.method} (id={request.id})")

        try:
            # Route to appropriate handler
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_list_tools(request)
            elif request.method == "tools/call":
                return await self._handle_call_tool(request)
            elif request.method == "ping":
                return self._success_response(request.id, {"status": "pong"})
            else:
                logger.warning(f"Unknown method: {request.method}")
                return self._error_response(request.id, -32601, f"Method not found: {request.method}")

        except Exception as e:
            logger.exception(f"Internal error handling {request.method}")
            return self._error_response(request.id, -32603, "Internal error", str(e))

    async def _handle_initialize(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        try:
            # Parse client capabilities (optional validation)
            params = McpInitializeParams(**request.params) if request.params else None

            if params:
                logger.info(f"Client: {params.clientInfo.get('name', 'unknown')} v{params.clientInfo.get('version', 'unknown')}")

            # Build server capabilities
            result = McpInitializeResult(
                protocolVersion="2024-11-05",
                capabilities=McpCapabilities(
                    tools={"listChanged": True},
                    resources={},
                    prompts={}
                ),
                serverInfo={
                    "name": self.server_name,
                    "version": self.version
                }
            )

            self.initialized = True
            logger.info("Server initialized successfully")

            return self._success_response(request.id, result.model_dump())

        except Exception as e:
            logger.exception("Failed to initialize")
            return self._error_response(request.id, -32602, "Invalid params", str(e))

    async def _handle_list_tools(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP tools/list request."""
        tools_list = [tool.model_dump() for tool in self.tools.values()]

        logger.debug(f"Returning {len(tools_list)} tools")

        result = McpListToolsResult(tools=tools_list)
        return self._success_response(request.id, result.model_dump())

    async def _handle_call_tool(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP tools/call request."""
        try:
            params = McpCallToolParams(**request.params) if request.params else McpCallToolParams(name="")

            logger.info(f"Calling tool: {params.name}")
            logger.debug(f"Arguments: {params.arguments}")

            # Validate tool exists
            if params.name not in self.tool_handlers:
                logger.error(f"Tool not found: {params.name}")
                return self._error_response(request.id, -32602, f"Tool '{params.name}' not found")

            # Execute tool handler
            handler = self.tool_handlers[params.name]

            try:
                result = await handler(params.arguments or {})

                # Format successful result
                mcp_result = McpCallToolResult(
                    content=[{
                        "type": "text",
                        "text": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                    }],
                    isError=False
                )

                logger.info(f"Tool {params.name} executed successfully")
                return self._success_response(request.id, mcp_result.model_dump())

            except Exception as e:
                logger.exception(f"Tool execution failed: {params.name}")

                # Return tool error as successful response with isError=True
                mcp_result = McpCallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Tool execution error: {str(e)}"
                    }],
                    isError=True
                )

                return self._success_response(request.id, mcp_result.model_dump())

        except Exception as e:
            logger.exception("Failed to parse tool call params")
            return self._error_response(request.id, -32602, "Invalid params", str(e))

    def _success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create successful JSON-RPC response."""
        response = JsonRpcResponse(id=request_id, result=result)
        return response.model_dump(exclude_none=True)

    def _error_response(self, request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create error JSON-RPC response."""
        error = JsonRpcError(code=code, message=message, data=data)
        response = JsonRpcResponse(id=request_id, error=error.model_dump(exclude_none=True))
        return response.model_dump(exclude_none=True)

    async def run(self):
        """
        Main event loop - read from stdin, write to stdout.

        Expects line-delimited JSON-RPC requests on stdin.
        Writes line-delimited JSON-RPC responses to stdout.
        """
        logger.info("Starting stdio event loop")

        try:
            # Read from stdin line by line
            while True:
                try:
                    line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)

                    if not line:
                        logger.info("stdin closed, shutting down")
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Parse JSON-RPC request
                    try:
                        request_data = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                        error_resp = self._error_response(None, -32700, "Parse error", str(e))
                        self._write_response(error_resp)
                        continue

                    # Handle request
                    response = await self.handle_request(request_data)

                    # Write response to stdout
                    self._write_response(response)

                except Exception as e:
                    logger.exception("Error in main loop")
                    # Try to send error response
                    error_resp = self._error_response(None, -32603, "Internal error", str(e))
                    self._write_response(error_resp)

        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down")

        finally:
            logger.info("Server shutdown complete")

    def _write_response(self, response: Dict[str, Any]):
        """Write JSON-RPC response to stdout (line-delimited JSON)."""
        try:
            json_str = json.dumps(response)
            sys.stdout.write(json_str + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.exception("Failed to write response")


def mcp_tool(name: str, description: str, parameters: Dict[str, Any]):
    """
    Decorator for registering MCP tools.

    Usage:
        @mcp_tool(
            name="sonarr_list_series",
            description="List all series in Sonarr",
            parameters={
                "type": "object",
                "properties": {
                    "instance": {"type": "string", "default": "default"}
                }
            }
        )
        async def list_series(args: Dict[str, Any]):
            instance = args.get("instance", "default")
            # ... implementation
            return {"series": [...]}
    """
    def decorator(func: Callable):
        # Store metadata on function for later registration
        func._mcp_name = name
        func._mcp_description = description
        func._mcp_parameters = parameters

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        wrapper._mcp_name = name
        wrapper._mcp_description = description
        wrapper._mcp_parameters = parameters

        return wrapper

    return decorator


async def main():
    """Main entry point for the MCP server."""
    import os
    from backends.sonarr_client import SonarrClient
    from backends.radarr_client import RadarrClient
    from tools import register_sonarr_tools, register_radarr_tools

    # Load configuration from environment
    sonarr_url = os.getenv("SONARR_URL")
    sonarr_api_key = os.getenv("SONARR_API_KEY")
    radarr_url = os.getenv("RADARR_URL")
    radarr_api_key = os.getenv("RADARR_API_KEY")

    if not all([sonarr_url, sonarr_api_key, radarr_url, radarr_api_key]):
        logger.error("Missing required environment variables:")
        logger.error("  SONARR_URL, SONARR_API_KEY, RADARR_URL, RADARR_API_KEY")
        logger.error("Please set these environment variables before starting the server.")
        sys.exit(1)

    logger.info(f"Sonarr URL: {sonarr_url}")
    logger.info(f"Radarr URL: {radarr_url}")

    # Initialize clients
    sonarr_client = SonarrClient(base_url=sonarr_url, api_key=sonarr_api_key)
    radarr_client = RadarrClient(base_url=radarr_url, api_key=radarr_api_key)

    # Create server
    server = McpServerV2()

    try:
        # Register tools
        logger.info("Registering Sonarr tools...")
        register_sonarr_tools(server, sonarr_client)

        logger.info("Registering Radarr tools...")
        register_radarr_tools(server, radarr_client)

        logger.info(f"Registered {len(server.tools)} tools total")

        # Run the server
        await server.run()

    finally:
        # Cleanup
        logger.info("Shutting down and closing clients...")
        await sonarr_client.close()
        await radarr_client.close()
        logger.info("Cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
