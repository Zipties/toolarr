import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sonarr import router as sonarr_router
from radarr import router as radarr_router
from instance_endpoints import instances_router

# --- App Initialization ---
app = FastAPI(
    title="Toolarr: Sonarr and Radarr API Tool Server",
    version="3.0.0",
    description="A refactored, consolidated, and optimized API for managing Sonarr and Radarr, designed for AI tool integration.",
    servers=[
        {
            "url": "https://toolarr.moderncaveman.us",
            "description": "Production server"
        }
    ]
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Security ---
TOOL_API_KEY = os.environ.get("TOOL_API_KEY", "changeme") # Added default for safety
bearer_scheme = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """Verify the Bearer token against the configured API key."""
    if not TOOL_API_KEY or credentials.credentials != TOOL_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing Bearer token"
        )
    return credentials.credentials

# --- Routers ---
# Include the refactored routers with security dependency
app.include_router(sonarr_router, dependencies=[Depends(verify_api_key)])
app.include_router(radarr_router, dependencies=[Depends(verify_api_key)])
app.include_router(instances_router, dependencies=[Depends(verify_api_key)])

# --- Root Endpoint ---
@app.get("/", summary="Health check")
async def root():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "toolarr-server-v3"}
