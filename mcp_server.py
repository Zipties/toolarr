import json
import asyncio
from typing import Dict, Any, Optional, Callable
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from mcp_types import (
    JsonRpcRequest, JsonRpcResponse, JsonRpcError,
    McpCapabilities, McpInitializeParams, McpInitializeResult,
    McpListToolsResult, McpCallToolParams, McpCallToolResult,
    generate_request_id
)

class McpServer:
    def __init__(self):
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
        """Register a tool with the MCP server"""
        self.tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema
        }
        self.tool_handlers[name] = handler
    
    async def handle_jsonrpc_request(self, request_data: Dict[str, Any], 
                                   auth_credentials: Optional[HTTPAuthorizationCredentials] = None) -> Dict[str, Any]:
        """Handle incoming JSON-RPC 2.0 requests"""
        try:
            request = JsonRpcRequest(**request_data)
        except Exception as e:
            return self._create_error_response(None, -32700, "Parse error", str(e))
        
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_list_tools(request)
            elif request.method == "tools/call":
                return await self._handle_call_tool(request, auth_credentials)
            elif request.method == "resources/list":
                return await self._handle_list_resources(request)
            elif request.method == "prompts/list":
                return await self._handle_list_prompts(request)
            elif request.method == "ping":
                return self._create_success_response(request.id, {})
            else:
                return self._create_error_response(request.id, -32601, "Method not found")
                
        except Exception as e:
            return self._create_error_response(request.id, -32603, "Internal error", str(e))
    
    async def _handle_initialize(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        try:
            params = McpInitializeParams(**request.params) if request.params else None
            
            result = McpInitializeResult(
                capabilities=McpCapabilities(
                    tools={"listChanged": True},
                    resources={},
                    prompts={}
                ),
                serverInfo={
                    "name": "toolarr-mcp-server",
                    "version": "1.0.0"
                }
            )
            
            return self._create_success_response(request.id, result.model_dump())
            
        except Exception as e:
            return self._create_error_response(request.id, -32602, "Invalid params", str(e))
    
    async def _handle_list_tools(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP tools/list request"""
        tools_list = list(self.tools.values())
        result = McpListToolsResult(tools=tools_list)
        return self._create_success_response(request.id, result.model_dump())
    
    async def _handle_list_resources(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP resources/list request"""
        # Return empty list since we don't have resources
        return self._create_success_response(request.id, {"resources": []})
    
    async def _handle_list_prompts(self, request: JsonRpcRequest) -> Dict[str, Any]:
        """Handle MCP prompts/list request"""
        # Return empty list since we don't have prompts
        return self._create_success_response(request.id, {"prompts": []})
    
    async def _handle_call_tool(self, request: JsonRpcRequest, 
                              auth_credentials: Optional[HTTPAuthorizationCredentials] = None) -> Dict[str, Any]:
        """Handle MCP tools/call request"""
        try:
            params = McpCallToolParams(**request.params) if request.params else McpCallToolParams(name="")
            
            if params.name not in self.tool_handlers:
                return self._create_error_response(request.id, -32602, f"Tool '{params.name}' not found")
            
            handler = self.tool_handlers[params.name]
            
            # Call the tool handler with arguments and auth
            try:
                result = await handler(params.arguments or {}, auth_credentials)
                
                # Format result according to MCP specification
                if isinstance(result, dict) and "error" in result:
                    # Handle error from tool
                    mcp_result = McpCallToolResult(
                        content=[{
                            "type": "text",
                            "text": f"Error: {result.get('error', 'Unknown error')}"
                        }],
                        isError=True
                    )
                else:
                    # Format successful result
                    mcp_result = McpCallToolResult(
                        content=[{
                            "type": "text", 
                            "text": json.dumps(result, indent=2) if isinstance(result, (dict, list)) else str(result)
                        }],
                        isError=False
                    )
                
                return self._create_success_response(request.id, mcp_result.model_dump())
                
            except HTTPException as e:
                mcp_result = McpCallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"HTTP Error {e.status_code}: {e.detail}"
                    }],
                    isError=True
                )
                return self._create_success_response(request.id, mcp_result.model_dump())
                
            except Exception as e:
                mcp_result = McpCallToolResult(
                    content=[{
                        "type": "text",
                        "text": f"Tool execution error: {str(e)}"
                    }],
                    isError=True
                )
                return self._create_success_response(request.id, mcp_result.model_dump())
                
        except Exception as e:
            return self._create_error_response(request.id, -32602, "Invalid params", str(e))
    
    def _create_success_response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        """Create a successful JSON-RPC response"""
        response = JsonRpcResponse(id=request_id, result=result)
        return response.model_dump(exclude_none=True)
    
    def _create_error_response(self, request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create an error JSON-RPC response"""
        error = JsonRpcError(code=code, message=message, data=data)
        response = JsonRpcResponse(id=request_id, error=error.model_dump(exclude_none=True))
        return response.model_dump(exclude_none=True)

# Global MCP server instance
mcp_server = McpServer()