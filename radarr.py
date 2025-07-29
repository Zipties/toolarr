from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os
from instance_endpoints import get_radarr_instance

# Pydantic Models for Radarr
class Movie(BaseModel):
    id: int
    title: str
    path: Optional[str] = None
    tmdbId: Optional[int] = None
    monitored: bool
    rootFolderPath: Optional[str] = None
    qualityProfileId: Optional[int] = None
    qualityProfileName: Optional[str] = None
    year: Optional[int] = None
    hasFile: Optional[bool] = None
    tags: List[int] = []
    statistics: Optional[dict] = None

class MoveMovieRequest(BaseModel):
    rootFolderPath: str = Field(..., description="The new root folder path for the movie.")

class QueueItem(BaseModel):
    id: int
    movieId: int
    title: str
    status: Optional[str] = None
    protocol: str
    size: float
    timeLeft: Optional[str] = None
    estimatedCompletionTime: Optional[str] = None
    trackedDownloadStatus: Optional[str] = None
    statusMessages: Optional[List[dict]] = None
    movie: Optional[dict] = None
    indexer: Optional[str] = None

class HistoryItem(BaseModel):
    id: int
    movieId: int
    sourceTitle: str
    eventType: str
    status: Optional[str] = None
    date: str

class ConfirmationMessage(BaseModel):
    message: str

# Radarr API Router
router = APIRouter(
    prefix="/radarr/{instance_name}",
    tags=["radarr"],
)

# In-memory cache for instance configurations





async def radarr_api_call(
    instance: dict,
    endpoint: str,
    request: Request,
    method: str = "GET",
    params: dict | None = None,
    json_data: dict | None = None,
) -> dict | None:
    """Make an API call to a specific Radarr instance using the shared client."""
    client: httpx.AsyncClient = request.app.state.http_client
    base_url = instance["url"].rstrip("/")
    path = endpoint.lstrip("/")
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{base_url}/api/v3/{path}"
    print(f"Calling Radarr API: {method} {url} with params: {params}")

    try:
        response = await client.request(
            method,
            url,
            params=params,
            json=json_data,
            headers=headers,
        )
        print(f"Radarr API response: {response.status_code}")
        response.raise_for_status()

        if response.status_code == 204 or not response.text:
            return None

        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Radarr API error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Radarr: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Radarr: {str(e)}")

@router.get("/library/movies", response_model=List[Movie], operation_id="search_radarr_library_for_movies", summary="Search Radarr library for movies.")
async def find_movie_in_library(
    term: str,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Searches the Radarr library for movies by a search term. Use this endpoint to find a movie's ID for other operations. The results include the movie ID, title, and quality profile."""
    all_movies = await radarr_api_call(instance, "movie", http_request)
    
    # Get quality profiles to map IDs to names
    quality_profiles = await radarr_api_call(instance, "qualityprofile", http_request)
    quality_profile_map = {qp["id"]: qp["name"] for qp in quality_profiles}
    
    # Filter movies and add quality profile name
    filtered_movies = []
    for m in all_movies:
        if term.lower() in m.get("title", "").lower():
            # Add quality profile name to the movie object
            if "qualityProfileId" in m:
                m["qualityProfileName"] = quality_profile_map.get(m["qualityProfileId"], "Unknown")
            filtered_movies.append(m)
    
    return filtered_movies

@router.get("/lookup", summary="Search for a new movie to add to Radarr")
async def lookup_movie(
    term: str,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Searches for a new movie by a search term. This is the first step to add a new movie."""
    encoded_term = quote(term)
    return await radarr_api_call(instance, f"movie/lookup?term={encoded_term}", http_request)

@router.put("/movie/{movie_id}/move", response_model=ConfirmationMessage, summary="Move movie to new folder", tags=["internal-admin"])
async def move_movie(
    movie_id: int,
    move_request: MoveMovieRequest,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Moves a movie to a new root folder and triggers Radarr to move the files."""
    movie = await radarr_api_call(instance, f"movie/{movie_id}", http_request)
    
    # Radarr's move logic is different from Sonarr's.
    # It requires a separate "movie/editor" endpoint.
    move_payload = {
            "movieIds": [movie_id],
            "rootFolderPath": move_request.rootFolderPath,
            "moveFiles": True,
        }
    
    # We need to get the ID of the destination root folder.
    root_folders = await radarr_api_call(instance, "rootfolder", http_request)
    target_folder = next((rf for rf in root_folders if rf["path"] == move_request.rootFolderPath), None)
    
    if not target_folder:
        raise HTTPException(status_code=400, detail=f"Root folder '{move_request.rootFolderPath}' not found in Radarr.")
        
    move_payload["targetRootFolderId"] = target_folder["id"]

    # This is a command, not a simple PUT on the movie object
    await radarr_api_call(instance, "movie/editor", http_request, method="PUT", json_data=move_payload)
    
    # Return a confirmation message
    return {"message": f"Move command initiated for movie {movie_id}."}

class AddMovieRequest(BaseModel):
    title: Optional[str] = None
    tmdbId: int
    qualityProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None
    searchForMovie: bool = True

@router.post("/movie", response_model=Movie, summary="Add a new movie to Radarr")
async def add_movie(
    movie_req: AddMovieRequest,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Adds a new movie to Radarr by looking it up via its TMDB ID."""
    # First, lookup the movie by TMDB ID
    try:
        movie_to_add = await radarr_api_call(instance, f"movie/lookup/tmdb?tmdbid={movie_req.tmdbId}", http_request)
        if not movie_to_add:
            raise HTTPException(status_code=404, detail=f"Movie with TMDB ID {movie_req.tmdbId} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up movie: {e}")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("RADARR_DEFAULT_ROOT_FOLDER_PATH", movie_req.rootFolderPath)
    quality_profile_name = os.environ.get("RADARR_DEFAULT_QUALITY_PROFILE_NAME", None)

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await radarr_api_call(instance, "qualityprofile", http_request)
    quality_profile_id = None
    if movie_req.qualityProfileId:
        quality_profile_id = movie_req.qualityProfileId
    elif quality_profile_name:
        for profile in quality_profiles:
            if profile["name"].lower() == quality_profile_name.lower():
                quality_profile_id = profile["id"]
                break
    
    if not quality_profile_id:
        raise HTTPException(status_code=400, detail=f"Quality profile '{quality_profile_name}' not found.")

    # Construct the payload for adding the movie
    add_payload = {
        "tmdbId": movie_to_add["tmdbId"],
        "title": movie_to_add["title"],
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "addOptions": {"searchForMovie": movie_req.searchForMovie}
    }

    # Add the movie to Radarr
    added_movie = await radarr_api_call(instance, "movie", http_request, method="POST", json_data=add_payload)
    return added_movie

@router.post("/radarr/add_by_title", response_model=Movie, summary="Add a new movie to Radarr by title", operation_id="add_movie_by_title_radarr", tags=["internal-admin"])
async def add_movie_by_title_radarr(
    title: str,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Adds a new movie to Radarr by looking it up by title."""
    # First, lookup the movie by title
    try:
        lookup_results = await radarr_api_call(instance, "movie/lookup", http_request, params={"term": title})
        if not lookup_results:
            raise HTTPException(status_code=404, detail=f"Movie with title '{title}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up movie: {e}")

    # Find the correct movie from the lookup results
    movie_to_add = lookup_results[0]
    
    if not movie_to_add:
        raise HTTPException(status_code=404, detail=f"Movie with title '{title}' not found in lookup results.")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("RADARR_DEFAULT_ROOT_FOLDER_PATH")
    quality_profile_name = os.environ.get("RADARR_DEFAULT_QUALITY_PROFILE_NAME")

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await radarr_api_call(instance, "qualityprofile", http_request)
    quality_profile_id = None
    if quality_profile_name:
        for profile in quality_profiles:
            if profile["name"].lower() == quality_profile_name.lower():
                quality_profile_id = profile["id"]
                break
    
    if not quality_profile_id:
        raise HTTPException(status_code=400, detail=f"Quality profile '{quality_profile_name}' not found.")

    # Construct the payload for adding the movie
    add_payload = {
        "tmdbId": movie_to_add["tmdbId"],
        "title": movie_to_add["title"],
        "qualityProfileId": quality_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "addOptions": {"searchForMovie": True}
    }

    # Add the movie to Radarr
    added_movie = await radarr_api_call(instance, "movie", http_request, method="POST", json_data=add_payload)
    return added_movie

@router.get("/queue", response_model=List[QueueItem], summary="Get Radarr download queue")
async def get_download_queue(
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Gets the list of items currently being downloaded by Radarr."""
    queue_data = await radarr_api_call(instance, "queue", http_request)
    # The actual queue items are in the 'records' key
    return queue_data.get("records", [])

@router.get("/history", response_model=List[HistoryItem], summary="Get Radarr download history")
async def get_download_history(
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Gets the history of recently grabbed and imported downloads from Radarr."""
    history_data = await radarr_api_call(instance, "history", http_request)
    # The actual history items are in the 'records' key
    return history_data.get("records", [])

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Radarr queue", operation_id="delete_radarr_queue_item")
async def delete_from_queue(
    queue_id: int,
    http_request: Request,
    removeFromClient: bool = True,
    instance: dict = Depends(get_radarr_instance),
):
    """Deletes an item from the Radarr download queue."""
    params = {"removeFromClient": str(removeFromClient).lower()}
    await radarr_api_call(instance, f"queue/{queue_id}", http_request, method="DELETE", params=params)
    return

class QualityProfile(BaseModel):
    id: int
    name: str

class UpdateMovieRequest(BaseModel):
    """Request model for updating movie properties"""
    monitored: Optional[bool] = None
    qualityProfileId: Optional[int] = None
    minimumAvailability: Optional[str] = None
    tags: Optional[List[int]] = None
    rootFolderPath: Optional[str] = None
    newRootFolderPath: Optional[str] = None
    moveFiles: Optional[bool] = False
class UpdateTagsRequest(BaseModel):
    tags: List[int] = Field(..., description="List of tag IDs to assign to the movie")

class MonitorRequest(BaseModel):
    monitored: bool

@router.put("/movie/{movie_id}", operation_id="update_radarr_movie_properties", summary="Update movie properties")
async def update_movie(
    movie_id: int,
    update_req: UpdateMovieRequest,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Updates movie properties. To remove a tag, get the movie's current tags, then submit a new list of tags that excludes the one to be removed. This replaces the entire list of tags for the movie."""
    # If a new root folder is provided, handle the move operation.
    if update_req.newRootFolderPath:
        move_payload = {
            "movieIds": [movie_id],
            "rootFolderPath": update_req.newRootFolderPath,
            "moveFiles": update_req.moveFiles,
        }
        root_folders = await radarr_api_call(instance, "rootfolder", http_request)
        target_folder = next((rf for rf in root_folders if rf["path"] == update_req.newRootFolderPath), None)
        if not target_folder:
            raise HTTPException(status_code=400, detail=f"Root folder '{update_req.newRootFolderPath}' not found in Radarr.")
        move_payload["targetRootFolderId"] = target_folder["id"]
        return await radarr_api_call(instance, "movie/editor", http_request, method="PUT", json_data=move_payload)

    # Otherwise, perform a standard update.
    movie_data = await radarr_api_call(instance, f"movie/{movie_id}", http_request)
    update_fields = update_req.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if key in movie_data:
            movie_data[key] = value
            
    return await radarr_api_call(instance, "movie", http_request, method="PUT", json_data=movie_data)

@router.get("/qualityprofiles", response_model=List[QualityProfile], summary="Get quality profiles for movies in Radarr")
async def get_quality_profiles(
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Retrieves quality profiles for MOVIES configured in Radarr."""
    return await radarr_api_call(instance, "qualityprofile", http_request)

# Tag endpoints for Radarr following API v3 spec

@router.get("/rootfolders", operation_id="get_radarr_rootfolders", summary="Get root folders from Radarr")
async def get_root_folders(
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Get all configured root folders in Radarr."""
    return await radarr_api_call(instance, "rootfolder", http_request)

# Helper function to get tag map
async def get_tag_map(instance_config: dict, http_request: Request) -> dict:
    """Get a mapping of tag IDs to tag names."""
    client: httpx.AsyncClient = http_request.app.state.http_client
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}

    response = await client.get(url, headers=headers)
    
    if response.status_code != 200:
        return {}
    
    tags = response.json()
    return {tag['id']: tag['label'] for tag in tags}

# Tag management endpoints
@router.get("/radarr/tags", summary="Get all tags from Radarr", operation_id="radarr_get_tags")
async def get_tags(
    http_request: Request,
    instance_config: dict = Depends(get_radarr_instance),
):
    """Get all tags configured in Radarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    client: httpx.AsyncClient = http_request.app.state.http_client
    response = await client.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch tags: {response.text}"
        )
    
    return response.json()

@router.post("/radarr/tags", summary="Create a new tag in Radarr", operation_id="radarr_create_tag", tags=["internal-admin"]) 
async def create_tag(
    label: str,
    http_request: Request,
    instance_config: dict = Depends(get_radarr_instance),
):
    """Create a new tag in Radarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    payload = {"label": label}
    
    client: httpx.AsyncClient = http_request.app.state.http_client
    response = await client.post(url, json=payload, headers=headers)
    
    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to create tag: {response.text}"
        )
    
    return response.json()

@router.put("/movie/{movie_id}/monitor", status_code=200, summary="Update monitoring status for a movie", operation_id="monitor_radarr_movie", tags=["internal-admin"])
async def monitor_movie(
    movie_id: int,
    monitor_req: MonitorRequest,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Updates the monitoring status for a movie."""
    movie_data = await radarr_api_call(instance, f"movie/{movie_id}", http_request)
    movie_data["monitored"] = monitor_req.monitored
    updated_movie = await radarr_api_call(instance, "movie", http_request, method="PUT", json_data=movie_data)
    return updated_movie


@router.post(
    "/movie/{movie_id}/search",
    summary="Search for a movie upgrade",
    operation_id="search_for_movie_upgrade",
)
async def search_for_movie_upgrade(
    movie_id: int,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Triggers a search for a movie to find a better quality version. This is a non-destructive action."""
    await radarr_api_call(
        instance,
        "command", http_request,
        method="POST",
        json_data={"name": "MovieSearch", "movieIds": [movie_id]},
    )
    return {"message": f"Triggered search for movie {movie_id}."}


@router.post("/movie/{movie_id}/fix", response_model=Movie, summary="Replace a damaged movie file", operation_id="fix_radarr_movie")
async def fix_movie(
    movie_id: int,
    http_request: Request,
    instance: dict = Depends(get_radarr_instance),
):
    """Deletes, re-adds, and searches for a movie. WARNING: This is a destructive action. For routine quality upgrades, use the '/movie/{movie_id}/search' endpoint instead."""
    # Get movie details to get the title
    try:
        movie = await radarr_api_call(instance, f"movie/{movie_id}", http_request)
        title_to_add = movie["title"]
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found.")
        raise e

    # Delete the movie
    await delete_movie(movie_id, deleteFiles=True, addImportExclusion=False, instance=instance, http_request=http_request)

    # Re-add the movie by title
    added_movie = await add_movie_by_title_radarr(title_to_add, instance, http_request)
    return added_movie

@router.delete("/movie/{movie_id}", status_code=200, summary="Delete a movie from Radarr", operation_id="delete_radarr_movie")
async def delete_movie(
    movie_id: int,
    http_request: Request,
    deleteFiles: bool = True,
    addImportExclusion: bool = False,
    instance: dict = Depends(get_radarr_instance),
):
    """Deletes a movie from Radarr. To re-download, you must re-add the movie."""
    params = {
        "deleteFiles": str(deleteFiles).lower(),
        "addImportExclusion": str(addImportExclusion).lower()
    }
    await radarr_api_call(instance, f"movie/{movie_id}", http_request, method="DELETE", params=params)
    return {"message": f"Movie with ID {movie_id} has been deleted."}
