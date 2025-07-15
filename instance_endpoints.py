# Add root-level instance listing endpoints before the router definitions

from fastapi import APIRouter

# Create a separate router for instance management
instances_router = APIRouter(prefix="/instances", tags=["instances"])

@instances_router.get("/sonarr", summary="List all Sonarr instances")
async def list_sonarr_instances():
    """Return a list of all configured Sonarr instances."""
    from sonarr import SONARR_INSTANCES, load_sonarr_instances
    if not SONARR_INSTANCES:
        load_sonarr_instances()
    return list(SONARR_INSTANCES.keys())

@instances_router.get("/radarr", summary="List all Radarr instances")
async def list_radarr_instances():
    """Return a list of all configured Radarr instances."""
    from radarr import RADARR_INSTANCES, load_radarr_instances
    if not RADARR_INSTANCES:
        load_radarr_instances()
    return list(RADARR_INSTANCES.keys())
