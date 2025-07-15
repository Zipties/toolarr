from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os

# Pydantic Models for Sonarr
class Series(BaseModel):
    id: int
    title: str
    path: str
    tvdbId: int
    monitored: bool
    rootFolderPath: str
    qualityProfileId: int
    languageProfileId: int
    tags: List[int] = []
    statistics: dict = {}
    seasons: List[dict] = []

class MoveSeriesRequest(BaseModel):
    rootFolderPath: str = Field(..., description="The new root folder path for the series.")

# Sonarr API Router
router = APIRouter(
    prefix="/sonarr/{instance_name}",
    tags=["sonarr"],
)

# In-memory cache for instance configurations
SONARR_INSTANCES = {}

def load_sonarr_instances():
    """Load Sonarr instance configurations from environment variables."""
    i = 1
    while True:
        name = os.environ.get(f"SONARR_INSTANCE_{i}_NAME")
        url = os.environ.get(f"SONARR_INSTANCE_{i}_URL")
        api_key = os.environ.get(f"SONARR_INSTANCE_{i}_API_KEY")
        if not all([name, url, api_key]):
            break
        SONARR_INSTANCES[name] = {"url": url, "api_key": api_key}
        i += 1

def get_sonarr_instance(instance_name: str):
    """Dependency to get a Sonarr instance's config. Handles 'default' keyword."""
    if not SONARR_INSTANCES:
        load_sonarr_instances()
    
    if instance_name == "default":
        if not SONARR_INSTANCES:
            raise HTTPException(status_code=404, detail="No Sonarr instances configured.")
        # Return the first configured instance
        return next(iter(SONARR_INSTANCES.values()))

    instance = SONARR_INSTANCES.get(instance_name)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Sonarr instance '{instance_name}' not found.")
    return instance

async def sonarr_api_call(instance: dict, endpoint: str, method: str = "GET", json_data: dict = None):
    """Make an API call to a specific Sonarr instance."""
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=json_data)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Sonarr API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with Sonarr: {str(e)}")

@router.get("/library", response_model=List[Series])
async def search_library(term: str, instance: dict = Depends(get_sonarr_instance)):
    """Search for a series in the Sonarr library by title."""
    all_series = await sonarr_api_call(instance, "series")
    return [s for s in all_series if term.lower() in s.get("title", "").lower()]

@router.put("/series/{sonarr_id}/move", response_model=Series)
async def move_series(sonarr_id: int, move_request: MoveSeriesRequest, instance: dict = Depends(get_sonarr_instance)):
    """Move a series to a new root folder."""
    series = await sonarr_api_call(instance, f"series/{sonarr_id}")
    series_folder_name = os.path.basename(series["path"])
    new_path = os.path.join(move_request.rootFolderPath, series_folder_name)
    
    series["rootFolderPath"] = move_request.rootFolderPath
    series["path"] = new_path
    series["moveFiles"] = True
    
    updated_series = await sonarr_api_call(instance, f"series/{series['id']}", method="PUT", json_data=series)
    return updated_series
