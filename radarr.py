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

    AI GUIDANCE:
    - Before adding media, always check if it already exists in the library using the /library endpoint.
    - If the media is not found, use this /add endpoint to add it (which also triggers an auto-download).
    - If the media is found but missing files, use the manual /search endpoint for that specific item (by ID).
    - Never attempt to add media that already exists—this will result in an error.
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

@router.post("/{movie_id}/search", summary="Trigger manual search for an existing movie in Radarr")
async def search_movie(movie_id: int, instance: dict = Depends(get_radarr_instance)):
    """
    Triggers a manual search for the specified movie in Radarr.

    AI GUIDANCE:
    - Before using this endpoint, confirm the media exists in the library using the /library endpoint.
    - Use this endpoint ONLY if the movie already exists in Radarr but is missing a file or needs a new download.
    - To add a new movie, use the /add endpoint instead.
    - Never attempt a manual search for media that is not already present—this will result in an error.
    """
    command_payload = {"name": "MoviesSearch", "movieIds": [movie_id]}
    await api_call(instance, "command", method="POST", json_data=command_payload)
    return {"message": f"Search triggered for movie ID {movie_id}."}
@router.post("/movie/{movie_id}/fix", summary="Delete, blocklist, and re-add a movie to force a fresh download", operation_id="fix_radarr_movie")
async def fix_movie(
    movie_id: int,
    addImportExclusion: bool = True,
    instance: dict = Depends(get_radarr_instance),
):
    """
    Fix a corrupted or missing movie by deleting it, blocklisting the old release, re-adding it, and triggering a new download.

    AI GUIDANCE:
    - Use this only if the movie already exists and has a corrupted/missing file.
    - When fixing a corrupted or unwanted media file, always set `addImportExclusion` to `true` in the delete call.
    - This ensures Radarr will not attempt to re-import the same file and will fetch a new release.
    - Do not use if you want to just search for a missing file—use /{movie_id}/search for that.
    """
    # 1. Lookup the movie
    movie = await api_call(instance, f"movie/{movie_id}")
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found in Radarr")
    tmdb_id = movie.get("tmdbId")
    title = movie.get("title")
    quality_profile_id = movie.get("qualityProfileId")
    root_folder_path = movie.get("rootFolderPath")
    if not all([tmdb_id, quality_profile_id, root_folder_path]):
        raise HTTPException(status_code=400, detail="Missing necessary data to re-add movie")

    # 2. Delete the movie (including files and blocklisting)
    await api_call(instance, f"movie/{movie_id}", method="DELETE", params={
        "deleteFiles": "true",
        "addImportExclusion": str(addImportExclusion).lower()
    })

    # 3. Re-add the movie
    add_payload = {
        "tmdbId": tmdb_id,
        "title": title,
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }
    added_movie = await api_call(instance, "movie", method="POST", json_data=add_payload)
    return {"message": f"Movie '{title}' was deleted, blocklisted, and is being re-downloaded.", "movie": added_movie}

@router.post("/command", summary="Execute a command on Radarr", deprecated=True)
async def execute_radarr_command(request: CommandRequest, instance: dict = Depends(get_radarr_instance)):
    """
    Executes Radarr commands via the /command endpoint.
    Note: It is now preferred to use specific, dedicated endpoints like `/{movie_id}/search` or `/movie/{movie_id}/fix`.

    USAGE:
    - Supply a JSON body with the following structure:
      {
        "command": "COMMAND_NAME",
        ... other parameters as needed ...
      }
    - Supported commands include:
        - "MoviesSearch": { "movieIds": [int, ...] }
        - "RenameFiles": { "movieIds": [int, ...] }
        - "RescanMovie": { "movieId": int }
        - "Backup": {}

    HOW TO GET IDs:
    - To obtain a valid `movieId`, use the `/library` endpoint to search for the movie by name.

    EXAMPLES:
    - Trigger a search for specific movies:
      { "command": "MoviesSearch", "movieIds": [123, 456] }
    - Trigger a file rename for a movie:
      { "command": "RenameFiles", "movieIds": [123] }

    See full list and details: https://github.com/Radarr/Radarr/wiki/API-Commands
    """
    # The command name in the payload must match one of the commands supported by the Radarr API.
    command = request.command
    payload = {"name": command}

    # Validate required parameters for commands that need them.
    if command in ["MoviesSearch", "RenameFiles"]:
        if not request.movie_id:
            raise HTTPException(status_code=400, detail="`movie_id` is required for this command.")
        payload["movieIds"] = [request.movie_id]
    elif command == "RescanMovie":
        if not request.movie_id:
            raise HTTPException(status_code=400, detail="`movie_id` is required for this command.")
        payload["movieId"] = request.movie_id
    
    # Send the command to the Radarr API.
    await api_call(instance, "command", method="POST", json_data=payload)
    return {"message": f"Command '{command}' initiated successfully."}
