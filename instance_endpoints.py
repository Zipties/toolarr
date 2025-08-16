from fastapi import APIRouter, HTTPException
import os

# Create a separate router for instance management
# Add "internal-admin" to the tags list
instances_router = APIRouter(tags=["instances", "internal-admin"])

def get_radarr_instance(instance_name: str):
    """
    Dependency to get a Radarr instance's config.
    Loads from environment variables on each request to be stateless.
    """
    i = 1
    while True:
        name = os.environ.get(f"RADARR_INSTANCE_{i}_NAME")
        if not name:
            # No more instances to check
            break

        if name.lower() == instance_name.lower() or (instance_name.lower() == "default" and i == 1):
            url = os.environ.get(f"RADARR_INSTANCE_{i}_URL")
            api_key = os.environ.get(f"RADARR_INSTANCE_{i}_API_KEY")
            if url and api_key:
                return {"url": url, "api_key": api_key}
        i += 1
    
    # If no instance was found, raise an error
    raise HTTPException(status_code=404, detail=f"Radarr instance '{instance_name}' not found or is missing URL/API key.")

def get_sonarr_instance(instance_name: str):
    """
    Dependency to get a Sonarr instance's config.
    Loads from environment variables on each request to be stateless.
    """
    i = 1
    while True:
        name = os.environ.get(f"SONARR_INSTANCE_{i}_NAME")
        if not name:
            # No more instances to check
            break

        if name.lower() == instance_name.lower() or (instance_name.lower() == "default" and i == 1):
            url = os.environ.get(f"SONARR_INSTANCE_{i}_URL")
            api_key = os.environ.get(f"SONARR_INSTANCE_{i}_API_KEY")
            if url and api_key:
                return {"url": url, "api_key": api_key}
        i += 1
    
    # If no instance was found, raise an error
    raise HTTPException(status_code=404, detail=f"Sonarr instance '{instance_name}' not found or is missing URL/API key.")

@instances_router.get("/instances/sonarr", summary="List all Sonarr instances")
async def list_sonarr_instances():
    """Return a list of all configured Sonarr instances."""
    instances = []
    i = 1
    while True:
        name = os.environ.get(f"SONARR_INSTANCE_{i}_NAME")
        if not name:
            break
        instances.append(name)
        i += 1
    return instances

@instances_router.get("/instances/radarr", summary="List all Radarr instances")
async def list_radarr_instances():
    """Return a list of all configured Radarr instances."""
    instances = []
    i = 1
    while True:
        name = os.environ.get(f"RADARR_INSTANCE_{i}_NAME")
        if not name:
            break
        instances.append(name)
        i += 1
    return instances
