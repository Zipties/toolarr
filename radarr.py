from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os

# Pydantic Models for Radarr
class Movie(BaseModel):
    id: int
    title: str
    path: str
    tmdbId: int
    monitored: bool
    rootFolderPath: str
    qualityProfileId: int
    tags: List[int] = []
    statistics: dict = {}

class MoveMovieRequest(BaseModel):
    rootFolderPath: str = Field(..., description="The new root folder path for the movie.")

# Radarr API Router
router = APIRouter(
    prefix="/radarr/{instance_name}",
    tags=["radarr"],
)

# In-memory cache for instance configurations
RADARR_INSTANCES = {}

def load_radarr_instances():
    """Load Radarr instance configurations from environment variables."""
    i = 1
    while True:
        name = os.environ.get(f"RADARR_INSTANCE_{i}_NAME")
        url = os.environ.get(f"RADARR_INSTANCE_{i}_URL")
        api_key = os.environ.get(f"RADARR_INSTANCE_{i}_API_KEY")
        if not all([name, url, api_key]):
            break
        RADARR_INSTANCES[name] = {"url": url, "api_key": api_key}
        i += 1

def get_radarr_instance(instance_name: str):
    """Dependency to get a Radarr instance's config. Handles 'default' keyword."""
    if not RADARR_INSTANCES:
        load_radarr_instances()

    if instance_name == "default":
        if not RADARR_INSTANCES:
            raise HTTPException(status_code=404, detail="No Radarr instances configured.")
        # Return the first configured instance
        return next(iter(RADARR_INSTANCES.values()))

    instance = RADARR_INSTANCES.get(instance_name)
    if not instance:
        raise HTTPException(status_code=404, detail=f"Radarr instance '{instance_name}' not found.")
    return instance

async def radarr_api_call(instance: dict, endpoint: str, method: str = "GET", json_data: dict = None):
    """Make an API call to a specific Radarr instance."""
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
            raise HTTPException(status_code=e.response.status_code, detail=f"Radarr API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with Radarr: {str(e)}")

@router.get("/library", response_model=List[Movie])
async def search_library(term: str, instance: dict = Depends(get_radarr_instance)):
    """Search for a movie in the Radarr library by title."""
    all_movies = await radarr_api_call(instance, "movie")
    return [m for m in all_movies if term.lower() in m.get("title", "").lower()]

@router.put("/movie/{movie_id}/move", response_model=Movie)
async def move_movie(movie_id: int, move_request: MoveMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Move a movie to a new root folder."""
    movie = await radarr_api_call(instance, f"movie/{movie_id}")
    
    # Radarr's move logic is different from Sonarr's.
    # It requires a separate "movie/editor" endpoint.
    move_payload = {
        "movieIds": [movie_id],
        "targetRootFolderId": 0, # Placeholder, needs to be looked up
        "moveFiles": True
    }
    
    # We need to get the ID of the destination root folder.
    root_folders = await radarr_api_call(instance, "rootfolder")
    target_folder = next((rf for rf in root_folders if rf["path"] == move_request.rootFolderPath), None)
    
    if not target_folder:
        raise HTTPException(status_code=400, detail=f"Root folder '{move_request.rootFolderPath}' not found in Radarr.")
        
    move_payload["targetRootFolderId"] = target_folder["id"]

    # This is a command, not a simple PUT on the movie object
    await radarr_api_call(instance, "movie/editor", method="PUT", json_data=move_payload)
    
    # Return the updated movie details
    updated_movie = await radarr_api_call(instance, f"movie/{movie_id}")
    return updated_movie
