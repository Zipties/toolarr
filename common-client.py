"""
This module contains the shared client logic for communicating with 
Sonarr and Radarr APIs, and a base router for common endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException
import httpx

# --- Generic API Client ---

async def api_call(instance: dict, endpoint: str, method: str = "GET", params: dict = None, json_data: dict = None):
    """
    Makes a generic API call to a media service instance (Sonarr/Radarr).
    
    Args:
        instance: A dictionary containing the 'url' and 'api_key' for the instance.
        endpoint: The API endpoint to call (e.g., 'movie', 'series/lookup').
        method: The HTTP method to use ('GET', 'POST', 'PUT', 'DELETE').
        params: A dictionary of query parameters.
        json_data: A dictionary of data to send as a JSON body.

    Returns:
        The JSON response from the API.
        
    Raises:
        HTTPException: If the API call fails.
    """
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(method, url, headers=headers, params=params, json=json_data)
            response.raise_for_status()
            
            # Handle successful empty responses (e.g., from DELETE)
            if response.status_code == 204 or not response.text:
                return None
                
            return response.json()
        except httpx.HTTPStatusError as e:
            service_name = "Sonarr" if "sonarr" in instance['url'] else "Radarr"
            raise HTTPException(status_code=e.response.status_code, detail=f"{service_name} API error: {e.response.text}")
        except Exception as e:
            service_name = "Sonarr" if "sonarr" in instance['url'] else "Radarr"
            raise HTTPException(status_code=500, detail=f"Error communicating with {service_name}: {str(e)}")

# --- Base Router for Common Endpoints ---

class BaseMediaRouter(APIRouter):
    """
    A base router class that provides common endpoints for both Sonarr and Radarr.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = kwargs.get("tags")[0] # e.g., "sonarr" or "radarr"
        
        # Add common routes
        self.add_api_route("/queue", self.get_download_queue, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download queue")
        self.add_api_route("/history", self.get_download_history, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download history")
        self.add_api_route("/queue/{queue_id}", self.delete_from_queue, methods=["DELETE"], status_code=204, summary=f"Delete item from {self.service_name.capitalize()} queue")
        self.add_api_route("/qualityprofiles", self.get_quality_profiles, methods=["GET"], summary=f"Get quality profiles from {self.service_name.capitalize()}")
        self.add_api_route("/rootfolders", self.get_root_folders, methods=["GET"], summary=f"Get root folders from {self.service_name.capitalize()}")
        self.add_api_route("/tags", self.get_tags, methods=["GET"], summary=f"Get all tags from {self.service_name.capitalize()}")
        self.add_api_route("/tags", self.create_tag, methods=["POST"], summary=f"Create a new tag in {self.service_name.capitalize()}")
        self.add_api_route("/tags/{tag_id}", self.delete_tag, methods=["DELETE"], status_code=204, summary=f"Delete a tag from {self.service_name.capitalize()}")

    async def get_download_queue(self, instance: dict):
        """Gets the list of items currently being downloaded or waiting to be downloaded."""
        queue_data = await api_call(instance, "queue")
        return queue_data.get("records", [])

    async def get_download_history(self, instance: dict):
        """Gets the history of recently grabbed and imported downloads."""
        history_data = await api_call(instance, "history")
        return history_data.get("records", [])

    async def delete_from_queue(self, queue_id: int, removeFromClient: bool = True, instance: dict = None):
        """Deletes an item from the download queue."""
        params = {"removeFromClient": str(removeFromClient).lower()}
        await api_call(instance, f"queue/{queue_id}", method="DELETE", params=params)
        return

    async def get_quality_profiles(self, instance: dict):
        """Retrieves all quality profiles."""
        return await api_call(instance, "qualityprofile")

    async def get_root_folders(self, instance: dict):
        """Get all configured root folders."""
        return await api_call(instance, "rootfolder")
        
    async def get_tags(self, instance: dict):
        """Get all tags configured in the instance."""
        return await api_call(instance, "tag")

    async def create_tag(self, label: str, instance: dict):
        """Create a new tag."""
        return await api_call(instance, "tag", method="POST", json_data={"label": label})

    async def delete_tag(self, tag_id: int, instance: dict):
        """Delete a tag by its ID."""
        await api_call(instance, f"tag/{tag_id}", method="DELETE")
        return
```python:radarr.py
"""
This module contains all Radarr-specific endpoints, models, and logic.
"""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Union

from common_client import BaseMediaRouter, api_call
from instance_endpoints import get_radarr_instance

# --- Pydantic Models for Radarr ---

class Movie(BaseModel):
    id: int
    title: str
    path: str
    tmdbId: int
    monitored: bool
    rootFolderPath: str
    qualityProfileId: int
    qualityProfileName: Optional[str] = None
    year: Optional[int] = None
    hasFile: Optional[bool] = None
    tags: List[int] = []
    tagNames: Optional[List[str]] = []
    statistics: dict = {}

class AddMovieRequest(BaseModel):
    lookup_id: Union[str, int] = Field(..., description="The movie title (string) or TMDB ID (integer) to add.")
    qualityProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None

class CommandRequest(BaseModel):
    command: str = Field(..., description="The command to execute.")
    movie_id: Optional[int] = Field(None, description="The ID of the movie to target.")
    # Add other potential command parameters here

# --- Radarr Router ---

# This router inherits all common endpoints from BaseMediaRouter
router = BaseMediaRouter(
    prefix="/radarr/{instance_name}",
    tags=["radarr"],
)

# --- Helper Functions ---

async def get_tag_map(instance: dict) -> dict:
    """Gets a mapping of tag IDs to tag names for Radarr."""
    tags = await api_call(instance, "tag")
    return {tag['id']: tag['label'] for tag in tags}

# --- Radarr Specific Endpoints ---

@router.get("/library", response_model=List[Movie], summary="Search the Radarr library")
async def find_movie_in_library(term: str, include_tags: bool = False, instance: dict = Depends(get_radarr_instance)):
    """
    Searches for a movie that is already in the Radarr library.
    """
    all_movies = await api_call(instance, "movie")
    
    # Pre-fetch maps for efficiency
    quality_profiles = await api_call(instance, "qualityprofile")
    quality_profile_map = {qp["id"]: qp["name"] for qp in quality_profiles}
    tag_map = await get_tag_map(instance) if include_tags else {}
    
    filtered_movies = []
    for m in all_movies:
        if term.lower() in m.get("title", "").lower():
            m["qualityProfileName"] = quality_profile_map.get(m["qualityProfileId"], "Unknown")
            if include_tags:
                m["tagNames"] = [tag_map.get(tag_id, f"Unknown tag {tag_id}") for tag_id in m.get("tags", [])]
            filtered_movies.append(m)
    
    return filtered_movies

@router.post("/add", response_model=Movie, summary="Add a new movie to Radarr")
async def add_movie(request: AddMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """
    Adds a new movie to Radarr by either its title or TMDB ID.
    """
    # Step 1: Lookup the movie
    if isinstance(request.lookup_id, int): # It's a TMDB ID
        lookup_results = await api_call(instance, f"movie/lookup/tmdb?tmdbId={request.lookup_id}")
        movie_to_add = lookup_results # The result is a single movie object
    else: # It's a title string
        lookup_results = await api_call(instance, "movie/lookup", params={"term": request.lookup_id})
        if not lookup_results:
            raise HTTPException(status_code=404, detail=f"Movie with title '{request.lookup_id}' not found.")
        movie_to_add = lookup_results[0] # Take the first result

    # Step 2: Determine Quality Profile and Root Folder
    quality_profiles = await api_call(instance, "qualityprofile")
    quality_profile_id = request.qualityProfileId or next((p['id'] for p in quality_profiles if p['name'] == "HD-1080p"), quality_profiles[0]['id'])

    root_folders = await api_call(instance, "rootfolder")
    root_folder_path = request.rootFolderPath or root_folders[0]['path']

    # Step 3: Construct and send the add payload
    add_payload = {
        "tmdbId": movie_to_add["tmdbId"],
        "title": movie_to_add["title"],
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }
    return await api_call(instance, "movie", method="POST", json_data=add_payload)

@router.post("/command", summary="Execute a command on Radarr")
async def execute_radarr_command(request: CommandRequest, instance: dict = Depends(get_radarr_instance)):
    """
    Executes various commands on Radarr, such as searching for movies.
    """
    command = request.command.lower()
    
    if command == "search_specific":
        if not request.movie_id:
            raise HTTPException(status_code=400, detail="movie_id is required for 'search_specific' command.")
        command_payload = {"name": "MoviesSearch", "movieIds": [request.movie_id]}
        await api_call(instance, "command", method="POST", json_data=command_payload)
        return {"message": f"Search triggered for movie ID {request.movie_id}."}

    elif command == "search_all_missing":
        all_movies = await api_call(instance, "movie")
        missing_movie_ids = [m['id'] for m in all_movies if not m.get('hasFile', False) and m.get('monitored', False)]
        if not missing_movie_ids:
            return {"message": "No missing monitored movies found to search for."}
        command_payload = {"name": "MoviesSearch", "movieIds": missing_movie_ids}
        await api_call(instance, "command", method="POST", json_data=command_payload)
        return {"message": f"Search triggered for {len(missing_movie_ids)} missing movies."}
        
    elif command == "fix_media":
        if not request.movie_id:
            raise HTTPException(status_code=400, detail="movie_id is required for 'fix_media' command.")
        
        # Step 1: Delete the movie (with file deletion and blocklisting)
        await api_call(instance, f"movie/{request.movie_id}", method="DELETE", params={"deleteFiles": "true", "addImportExclusion": "true"})
        
        # Step 2: Re-add the movie (this part would need more logic to get the original details)
        # For now, this is a placeholder for a more complex workflow.
        return {"message": f"Fix command initiated for movie ID {request.movie_id}. Movie deleted and blocklisted."}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {request.command}")
```python:sonarr.py
"""
This module contains all Sonarr-specific endpoints, models, and logic.
"""
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Union

from common_client import BaseMediaRouter, api_call
from instance_endpoints import get_sonarr_instance

# --- Pydantic Models for Sonarr ---

class Series(BaseModel):
    id: int
    title: str
    path: str
    tvdbId: int
    monitored: bool
    rootFolderPath: str
    qualityProfileId: int
    qualityProfileName: Optional[str] = None
    languageProfileId: int
    year: Optional[int] = None
    seriesType: Optional[str] = None
    tags: List[int] = []
    tagNames: Optional[List[str]] = []
    seasons: List[dict] = []
    statistics: dict = {}

class AddSeriesRequest(BaseModel):
    lookup_id: Union[str, int] = Field(..., description="The series title (string) or TVDB ID (integer) to add.")
    qualityProfileId: Optional[int] = None
    languageProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None

class MonitorRequest(BaseModel):
    monitored: bool
    season_number: Optional[int] = Field(None, description="If provided, only this season's status will be updated.")

class CommandRequest(BaseModel):
    command: str = Field(..., description="The command to execute.")
    series_id: Optional[int] = Field(None, description="The ID of the series to target.")

# --- Sonarr Router ---

router = BaseMediaRouter(
    prefix="/sonarr/{instance_name}",
    tags=["sonarr"],
)

# --- Helper Functions ---

async def get_tag_map(instance: dict) -> dict:
    """Gets a mapping of tag IDs to tag names for Sonarr."""
    tags = await api_call(instance, "tag")
    return {tag['id']: tag['label'] for tag in tags}

# --- Sonarr Specific Endpoints ---

@router.get("/library", response_model=List[Series], summary="Search the Sonarr library")
async def find_series_in_library(term: str, include_tags: bool = False, instance: dict = Depends(get_sonarr_instance)):
    """
    Searches for a series that is already in the Sonarr library.
    """
    all_series = await api_call(instance, "series")
    
    quality_profiles = await api_call(instance, "qualityprofile")
    quality_profile_map = {qp["id"]: qp["name"] for qp in quality_profiles}
    tag_map = await get_tag_map(instance) if include_tags else {}
    
    filtered_series = []
    for s in all_series:
        if term.lower() in s.get("title", "").lower():
            s["qualityProfileName"] = quality_profile_map.get(s["qualityProfileId"], "Unknown")
            if include_tags:
                s["tagNames"] = [tag_map.get(tag_id, f"Unknown tag {tag_id}") for tag_id in s.get("tags", [])]
            filtered_series.append(s)
            
    return filtered_series

@router.post("/add", response_model=Series, summary="Add a new series to Sonarr")
async def add_series(request: AddSeriesRequest, instance: dict = Depends(get_sonarr_instance)):
    """
    Adds a new series to Sonarr by either its title or TVDB ID.
    """
    # Step 1: Lookup the series
    if isinstance(request.lookup_id, int): # It's a TVDB ID
        lookup_results = await api_call(instance, "series/lookup", params={"term": f"tvdb:{request.lookup_id}"})
    else: # It's a title string
        lookup_results = await api_call(instance, "series/lookup", params={"term": request.lookup_id})
    
    if not lookup_results:
        raise HTTPException(status_code=404, detail=f"Series '{request.lookup_id}' not found.")
    series_to_add = lookup_results[0]

    # Step 2: Determine Profiles and Root Folder
    quality_profiles = await api_call(instance, "qualityprofile")
    quality_profile_id = request.qualityProfileId or next((p['id'] for p in quality_profiles if p['name'] == "HD-1080p"), quality_profiles[0]['id'])
    
    language_profiles = await api_call(instance, "languageprofile")
    language_profile_id = request.languageProfileId or language_profiles[0]['id']

    root_folders = await api_call(instance, "rootfolder")
    root_folder_path = request.rootFolderPath or root_folders[0]['path']

    # Step 3: Construct and send the add payload
    add_payload = {
        "tvdbId": series_to_add["tvdbId"],
        "title": series_to_add["title"],
        "qualityProfileId": quality_profile_id,
        "languageProfileId": language_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "seasons": series_to_add["seasons"],
        "addOptions": {"searchForMissingEpisodes": True}
    }
    return await api_call(instance, "series", method="POST", json_data=add_payload)

@router.put("/monitor", summary="Update monitoring status for a series or season")
async def update_monitoring_status(request: MonitorRequest, series_id: int, instance: dict = Depends(get_sonarr_instance)):
    """
    Updates the monitoring status for an entire series or a single season.
    """
    series_data = await api_call(instance, f"series/{series_id}")
    
    if request.season_number is not None:
        # Update a single season
        season_found = False
        for season in series_data.get("seasons", []):
            if season.get("seasonNumber") == request.season_number:
                season["monitored"] = request.monitored
                season_found = True
                break
        if not season_found:
            raise HTTPException(status_code=404, detail=f"Season {request.season_number} not found.")
    else:
        # Update the entire series and all its seasons
        series_data["monitored"] = request.monitored
        for season in series_data.get("seasons", []):
            season["monitored"] = request.monitored
            
    return await api_call(instance, f"series/{series_id}", method="PUT", json_data=series_data)

@router.post("/command", summary="Execute a command on Sonarr")
async def execute_sonarr_command(request: CommandRequest, instance: dict = Depends(get_sonarr_instance)):
    """
    Executes various commands on Sonarr, such as searching for series.
    """
    command = request.command.lower()
    
    if command == "search_specific":
        if not request.series_id:
            raise HTTPException(status_code=400, detail="series_id is required for 'search_specific' command.")
        command_payload = {"name": "SeriesSearch", "seriesId": request.series_id}
        await api_call(instance, "command", method="POST", json_data=command_payload)
        return {"message": f"Search triggered for series ID {request.series_id}."}

    elif command == "search_all_missing":
        # Sonarr's API for this is more complex, often requiring a per-series check.
        # A full implementation would iterate all series. For now, we note the feature parity goal.
        return {"message": "Feature 'search_all_missing' for Sonarr is planned."}

    elif command == "fix_media":
        if not request.series_id:
            raise HTTPException(status_code=400, detail="series_id is required for 'fix_media' command.")
        await api_call(instance, f"series/{request.series_id}", method="DELETE", params={"deleteFiles": "true", "addImportExclusion": "true"})
        return {"message": f"Fix command initiated for series ID {request.series_id}. Series deleted and blocklisted."}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown command: {request.command}")
```python:main.py
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
            "url": "[https://toolarr.moderncaveman.us](https://toolarr.moderncaveman.us)",
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
```text:requirements.txt
fastapi
uvicorn[standard]
pydantic
httpx
