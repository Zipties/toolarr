import os
import json
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials
from fastapi.openapi.utils import get_openapi
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from instance_endpoints import instances_router


# --- App Initialization ---
app = FastAPI(
    title="Toolarr: Sonarr and Radarr API Tool Server",
    version="2.0.0",
    description="OpenAPI server for Sonarr and Radarr integration with Open WebUI",
    servers=[
        {
            "url": "https://toolarr.moderncaveman.us",
            "description": "Production server"
        }
    ]
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )
    # Remove 'anyOf' from ValidationError schema
    if "ValidationError" in openapi_schema["components"]["schemas"]:
        openapi_schema["components"]["schemas"]["ValidationError"]["properties"]["loc"]["items"] = {"type": "string"}
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security ---
TOOL_API_KEY = os.environ.get("TOOL_API_KEY", "")
MCP_CLIENT_ID = os.environ.get("MCP_CLIENT_ID", "toolarr-client")
MCP_CLIENT_SECRET = os.environ.get("MCP_CLIENT_SECRET", TOOL_API_KEY)  # Fallback to API key

bearer_scheme = HTTPBearer()
basic_scheme = HTTPBasic()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Verify the Bearer token against the configured API key."""
    if not TOOL_API_KEY or credentials.credentials != TOOL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing Bearer token"
        )

async def verify_mcp_auth(request: Request):
    """Verify authentication for MCP endpoint - supports both Bearer and Basic auth"""
    # Try Bearer token first
    auth_header = request.headers.get("authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        if TOOL_API_KEY and token == TOOL_API_KEY:
            return {"type": "bearer", "token": token}
    
    # Try Basic auth (OAuth client credentials)
    elif auth_header.startswith("Basic "):
        import base64
        try:
            credentials = base64.b64decode(auth_header[6:]).decode().split(":", 1)
            if len(credentials) == 2:
                username, password = credentials
                if MCP_CLIENT_ID and MCP_CLIENT_SECRET:
                    if username == MCP_CLIENT_ID and password == MCP_CLIENT_SECRET:
                        return {"type": "basic", "username": username}
        except Exception:
            pass
    
    raise HTTPException(
        status_code=403,
        detail="Invalid authentication. Use Bearer token or OAuth client credentials."
    )


from sonarr import router as sonarr_router
from radarr import router as radarr_router

# --- Routers ---
# Include the Sonarr and Radarr routers, with security dependency
app.include_router(sonarr_router, dependencies=[Depends(verify_api_key)])
app.include_router(radarr_router, dependencies=[Depends(verify_api_key)])
app.include_router(instances_router, dependencies=[Depends(verify_api_key)])

# --- Root Endpoint ---
@app.get("/", summary="Health check", tags=["internal-admin"])
async def root():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "toolarr-server"}

@app.get("/openapi-chatgpt.json", include_in_schema=False)
async def get_pruned_openapi():
    """Serves the pruned OpenAPI spec for ChatGPT."""
    try:
        with open("openapi-chatgpt.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="OpenAPI spec not found")

# --- MCP Integration ---
from mcp_server import mcp_server
# Use auto-generated MCP tools (fallback to manual if not available)
try:
    from mcp_tools_generated import register_all_tools
    print("🔄 Using auto-generated MCP tools")
except ImportError:
    from mcp_tools import register_all_tools
    print("⚠️  Using manual MCP tools (run generate_openapi.py to auto-generate)")

# Register MCP tools on startup
@app.on_event("startup")
async def startup_event():
    """Initialize MCP tools on server startup"""
    await register_all_tools()

@app.post("/mcp", tags=["mcp"])
async def mcp_endpoint(request: Request):
    """
    Model Context Protocol (MCP) JSON-RPC endpoint.
    Supports standard MCP protocol for AI model integration.
    Supports both Bearer token and OAuth client credentials authentication.
    """
    # Verify authentication
    auth = await verify_mcp_auth(request)
    
    try:
        request_data = await request.json()
        response = await mcp_server.handle_jsonrpc_request(request_data, None)  # Auth already verified
        return response
    except json.JSONDecodeError:
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {"code": -32700, "message": "Parse error"}
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0", 
            "id": None,
            "error": {"code": -32603, "message": "Internal error", "data": str(e)}
        }

@app.get("/mcp/sse", tags=["mcp"])
async def mcp_sse_endpoint(request: Request):
    """
    Server-Sent Events endpoint for MCP real-time communication.
    Provides streaming updates for long-running operations.
    Supports both Bearer token and OAuth client credentials authentication.
    """
    # Verify authentication
    auth = await verify_mcp_auth(request)
    
    async def event_generator():
        # Keep connection alive and send periodic heartbeats
        while True:
            yield {
                "event": "heartbeat",
                "data": json.dumps({"timestamp": "heartbeat", "status": "connected"})
            }
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
    
    return EventSourceResponse(event_generator())

