import os
import json
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi

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
bearer_scheme = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Verify the Bearer token against the configured API key."""
    if not TOOL_API_KEY or credentials.credentials != TOOL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing Bearer token"
        )
    return credentials.credentials

# Shared HTTP client stored on application state

# --- Startup Event ---
@app.on_event("startup")
async def startup_event():
    """Initialize shared HTTP client."""
    app.state.http_client = httpx.AsyncClient(timeout=30.0)

@app.on_event("shutdown")
async def shutdown_event():
    """Close shared HTTP client on shutdown."""
    await app.state.http_client.aclose()

async def get_http_client():
    """Dependency to provide the shared HTTP client."""
    return app.state.http_client

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

