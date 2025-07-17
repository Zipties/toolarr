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
