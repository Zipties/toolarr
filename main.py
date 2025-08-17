import os
import json
import asyncio
import secrets
import time
from typing import Dict, Any
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

# OAuth 2.1 Dynamic Client Registration storage (use database in production)
registered_clients: Dict[str, Dict[str, Any]] = {}
active_tokens: Dict[str, Dict[str, Any]] = {}
authorization_codes: Dict[str, Dict[str, Any]] = {}

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
    import base64
    
    auth_header = request.headers.get("authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        if TOOL_API_KEY and token == TOOL_API_KEY:
            return {"type": "bearer", "token": token}
    
    # Try Basic auth (OAuth client credentials)
    elif auth_header.startswith("Basic "):
        try:
            encoded_creds = auth_header[6:]  # Remove "Basic " prefix
            decoded_creds = base64.b64decode(encoded_creds).decode()
            
            credentials = decoded_creds.split(":", 1)
            if len(credentials) == 2:
                username, password = credentials
                
                if MCP_CLIENT_ID and MCP_CLIENT_SECRET:
                    if username == MCP_CLIENT_ID and password == MCP_CLIENT_SECRET:
                        return {"type": "basic", "username": username}
        except Exception:
            pass  # Fall through to authentication failure
    
    raise HTTPException(
        status_code=401,
        detail="Invalid authentication credentials"
    )

async def verify_mcp_auth_with_dcr(request: Request):
    """Enhanced auth verification supporting DCR tokens and static credentials"""
    import base64
    
    auth_header = request.headers.get("authorization", "")
    
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        
        # Check if it's the static API key
        if TOOL_API_KEY and token == TOOL_API_KEY:
            return {"type": "bearer", "token": token}
        
        # Check if it's a DCR-generated token
        if token in active_tokens:
            token_info = active_tokens[token]
            if token_info["expires_at"] > time.time():
                return {"type": "dcr_token", "token": token}
            else:
                # Token expired, remove it
                del active_tokens[token]
    
    elif auth_header.startswith("Basic "):
        try:
            encoded_creds = auth_header[6:]
            decoded_creds = base64.b64decode(encoded_creds).decode()
            client_id, client_secret = decoded_creds.split(":", 1)
            
            # Check static credentials
            if (MCP_CLIENT_ID and MCP_CLIENT_SECRET and 
                client_id == MCP_CLIENT_ID and client_secret == MCP_CLIENT_SECRET):
                return {"type": "basic", "username": client_id}
            
            # Check DCR clients
            if client_id in registered_clients:
                stored_client = registered_clients[client_id]
                if stored_client["client_secret"] == client_secret:
                    return {"type": "dcr_basic", "username": client_id}
        except Exception:
            pass
    
    raise HTTPException(
        status_code=401,
        detail="Invalid authentication credentials"
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

@app.post("/debug-headers", tags=["debug"])
async def debug_headers(request: Request):
    """Debug endpoint to see all headers received by FastAPI"""
    return {
        "headers": dict(request.headers),
        "method": request.method,
        "url": str(request.url),
        "client": request.client.host if request.client else None
    }

@app.get("/openapi-chatgpt.json", include_in_schema=False)
async def get_pruned_openapi():
    """Serves the pruned OpenAPI spec for ChatGPT."""
    try:
        with open("openapi-chatgpt.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="OpenAPI spec not found")

# --- OAuth 2.1 Dynamic Client Registration ---

@app.get("/.well-known/oauth-authorization-server", tags=["oauth"])
async def oauth_server_metadata():
    """
    OAuth 2.0 Authorization Server Metadata (RFC 8414)
    Required for MCP clients to discover OAuth endpoints
    """
    base_url = "https://toolarr.moderncaveman.us"
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["client_credentials", "authorization_code"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
        "scopes_supported": ["mcp:tools", "mcp:resources"],
        "code_challenge_methods_supported": ["S256"],
        "registration_endpoint_auth_methods_supported": ["none"]
    }

@app.post("/oauth/register", tags=["oauth"])
async def dynamic_client_registration(request: Request):
    """
    OAuth 2.0 Dynamic Client Registration (RFC 7591)
    Allows Claude Desktop to automatically register as a client
    """
    try:
        registration_request = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Generate client credentials
    client_id = f"mcp-{secrets.token_urlsafe(16)}"
    client_secret = secrets.token_urlsafe(32)
    issued_at = int(time.time())
    
    # Store client registration
    registered_clients[client_id] = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": registration_request.get("client_name", "Unknown MCP Client"),
        "grant_types": ["client_credentials"],
        "token_endpoint_auth_method": "client_secret_basic",
        "created_at": issued_at,
        "scopes": ["mcp:tools", "mcp:resources"]
    }
    
    # Return registration response per RFC 7591
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": issued_at,
        "grant_types": ["client_credentials"],
        "token_endpoint_auth_method": "client_secret_basic",
        "scope": "mcp:tools mcp:resources"
    }

@app.post("/oauth/token", tags=["oauth"])
async def oauth_token_endpoint(request: Request):
    """
    OAuth 2.0 Token Endpoint (RFC 6749)
    Handles client_credentials grant for DCR clients
    """
    import base64
    
    # Parse form data for token request
    try:
        form_data = await request.form()
        grant_type = form_data.get("grant_type")
        code = form_data.get("code")
        redirect_uri = form_data.get("redirect_uri")
        code_verifier = form_data.get("code_verifier")
    except Exception:
        grant_type = None
    
    if grant_type not in ["client_credentials", "authorization_code"]:
        raise HTTPException(
            status_code=400, 
            detail="unsupported_grant_type"
        )
    
    # Handle Authorization Code flow
    if grant_type == "authorization_code":
        import hashlib
        import base64
        
        if not code or not redirect_uri or not code_verifier:
            raise HTTPException(
                status_code=400,
                detail="invalid_request"
            )
        
        # Verify authorization code exists and is valid
        if code not in authorization_codes:
            raise HTTPException(
                status_code=400,
                detail="invalid_grant"
            )
        
        auth_data = authorization_codes[code]
        
        # Check expiration
        if auth_data["expires_at"] < time.time():
            del authorization_codes[code]
            raise HTTPException(
                status_code=400,
                detail="invalid_grant"
            )
        
        # Verify redirect_uri matches
        if auth_data["redirect_uri"] != redirect_uri:
            raise HTTPException(
                status_code=400,
                detail="invalid_grant"
            )
        
        # Verify PKCE code_verifier
        code_challenge = auth_data["code_challenge"]
        expected_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip('=')
        
        if code_challenge != expected_challenge:
            raise HTTPException(
                status_code=400,
                detail="invalid_grant"
            )
        
        # Use client_id from authorization code
        client_id = auth_data["client_id"]
        
        # Remove used authorization code
        del authorization_codes[code]
        
    else:
        # Handle Client Credentials flow
        # Get client credentials from Authorization header
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Basic "):
            raise HTTPException(
                status_code=401, 
                detail="invalid_client"
            )
        
        try:
            encoded_creds = auth_header[6:]  # Remove "Basic " prefix
            decoded_creds = base64.b64decode(encoded_creds).decode()
            client_id, client_secret = decoded_creds.split(":", 1)
        except Exception:
            raise HTTPException(
                status_code=401, 
                detail="invalid_client"
            )
        
        # Verify client exists (check both static and DCR clients)
        client_valid = False
        
        # Check static client
        if (MCP_CLIENT_ID and MCP_CLIENT_SECRET and 
            client_id == MCP_CLIENT_ID and client_secret == MCP_CLIENT_SECRET):
            client_valid = True
        
        # Check DCR clients
        elif client_id in registered_clients:
            stored_client = registered_clients[client_id]
            if stored_client["client_secret"] == client_secret:
                client_valid = True
        
        if not client_valid:
            raise HTTPException(
                status_code=401, 
                detail="invalid_client"
            )
    
    # Generate access token
    access_token = f"mcp_token_{secrets.token_urlsafe(32)}"
    expires_in = 3600  # 1 hour
    expires_at = int(time.time()) + expires_in
    
    # Store token
    active_tokens[access_token] = {
        "client_id": client_id,
        "expires_at": expires_at,
        "scope": "mcp:tools mcp:resources"
    }
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "scope": "mcp:tools mcp:resources"
    }

@app.get("/oauth/authorize", tags=["oauth"])
async def oauth_authorize_endpoint(
    response_type: str,
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str,
    code_challenge: str,
    code_challenge_method: str
):
    """
    OAuth 2.0 Authorization Endpoint (RFC 6749)
    Handles authorization code flow with PKCE
    """
    import hashlib
    import base64
    from urllib.parse import urlencode
    from fastapi.responses import RedirectResponse
    
    # Validate required parameters
    if response_type != "code":
        error_params = urlencode({
            "error": "unsupported_response_type",
            "error_description": "Only 'code' response type is supported",
            "state": state
        })
        return RedirectResponse(f"{redirect_uri}?{error_params}")
    
    if code_challenge_method != "S256":
        error_params = urlencode({
            "error": "invalid_request", 
            "error_description": "Only S256 code challenge method is supported",
            "state": state
        })
        return RedirectResponse(f"{redirect_uri}?{error_params}")
    
    # Verify client exists (check both static and DCR clients)
    client_valid = False
    if client_id == MCP_CLIENT_ID or client_id in registered_clients:
        client_valid = True
    
    if not client_valid:
        error_params = urlencode({
            "error": "invalid_client",
            "error_description": "Unknown client_id",
            "state": state
        })
        return RedirectResponse(f"{redirect_uri}?{error_params}")
    
    # Validate redirect_uri (for Claude Desktop)
    allowed_redirects = [
        "https://claude.ai/api/mcp/auth_callback",
        "http://localhost:3000/auth/callback",  # For testing
    ]
    
    if redirect_uri not in allowed_redirects:
        raise HTTPException(
            status_code=400,
            detail="invalid_redirect_uri"
        )
    
    # Generate authorization code
    auth_code = f"auth_code_{secrets.token_urlsafe(32)}"
    expires_at = int(time.time()) + 600  # 10 minutes
    
    # Store authorization code with PKCE challenge
    authorization_codes[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "expires_at": expires_at
    }
    
    # Auto-approve for MCP clients (no user interaction needed)
    # In a real app, you'd show an authorization page here
    success_params = urlencode({
        "code": auth_code,
        "state": state
    })
    
    return RedirectResponse(f"{redirect_uri}?{success_params}")

@app.post("/oauth/authorize", tags=["oauth"])
async def oauth_authorize_post_endpoint():
    """
    POST version of authorize endpoint (not used by Claude)
    """
    raise HTTPException(
        status_code=405,
        detail="Use GET for authorization endpoint"
    )

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
    Supports Bearer token, OAuth client credentials, and DCR authentication.
    """
    # Verify authentication (now supports DCR)
    auth = await verify_mcp_auth_with_dcr(request)
    
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
    Supports Bearer token, OAuth client credentials, and DCR authentication.
    """
    # Verify authentication (now supports DCR)
    auth = await verify_mcp_auth_with_dcr(request)
    
    async def event_generator():
        # Keep connection alive and send periodic heartbeats
        while True:
            yield {
                "event": "heartbeat",
                "data": json.dumps({"timestamp": "heartbeat", "status": "connected"})
            }
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
    
    return EventSourceResponse(event_generator())

