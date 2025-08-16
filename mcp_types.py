from typing import Any, Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field
import uuid

class JsonRpcRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int, None] = None
    method: str
    params: Optional[Dict[str, Any]] = None

class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: Union[str, int, None] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class McpTool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]

class McpResource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: Optional[str] = None

class McpCapabilities(BaseModel):
    tools: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None

class McpInitializeParams(BaseModel):
    protocolVersion: str
    capabilities: McpCapabilities
    clientInfo: Dict[str, Any]

class McpInitializeResult(BaseModel):
    protocolVersion: str = "2024-11-05"
    capabilities: McpCapabilities
    serverInfo: Dict[str, Any]

class McpListToolsResult(BaseModel):
    tools: List[McpTool]

class McpCallToolParams(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None

class McpCallToolResult(BaseModel):
    content: List[Dict[str, Any]]
    isError: Optional[bool] = False

def generate_request_id() -> str:
    return str(uuid.uuid4())