from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os
from instance_endpoints import get_radarr_instance

# Pydantic Models for Radarr
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
    statistics: dict = {}

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





async def radarr_api_call(instance: dict, endpoint: str, method: str = "GET", params: dict = None, json_data: dict = None):
    """Make an API call to a specific Radarr instance."""
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    print(f"Calling Radarr API: {method} {url} with params: {params}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data, params=params)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=json_data, params=params)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            print(f"Radarr API response: {response.status_code}")
            response.raise_for_status()
            
            # Handle successful empty responses
            if response.status_code == 204 or not response.text:
                return None
                
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Radarr API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with Radarr: {str(e)}")

@router.get(
    "/library",
    response_model=List[Movie],
    summary="Check if a movie exists in the Radarr library",
    operation_id="find_radarr_movies",
)
async def find_movie_in_library(
    term: Optional[str] = Query(default=None, description="The search term to filter by."),
    page: int = Query(default=1, description="The page number to retrieve."),
    page_size: int = Query(default=25, description="The number of items per page."),
    instance: dict = Depends(get_radarr_instance),
):
    """Search the Radarr library with optional pagination.

    Radarr sometimes returns errors when filtering server-side. To avoid this we
    fetch all movies and filter locally when a search term is provided.
    """

    async def get_all_movies():
        """Retrieve all movies from Radarr, handling pagination."""
        movies = []
        page = 1
        page_size_param = 1000
        while True:
            resp = await radarr_api_call(
                instance,
                "movie",
                params={"page": page, "pageSize": page_size_param},
            )
            page_movies = resp.get("records", resp) or []
            movies.extend(page_movies)

            total = resp.get("totalRecords")
            if total is None or len(movies) >= total:
                break
            page += 1
        return movies

    all_movies = await get_all_movies()

    # Map quality profile IDs to names
    quality_profiles = await radarr_api_call(instance, "qualityprofile")
    quality_profile_map = {qp["id"]: qp["name"] for qp in quality_profiles}

    filtered_movies = []
    term_lower = term.lower() if term else None
    for m in all_movies:
        if term_lower is None or term_lower in m.get("title", "").lower():
            if "qualityProfileId" in m:
                m["qualityProfileName"] = quality_profile_map.get(m["qualityProfileId"], "Unknown")
            filtered_movies.append(m)

    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    return filtered_movies[start_index:end_index]

@router.get("/search", summary="Search for a movie by term")
async def search_movie(term: str, instance: dict = Depends(get_radarr_instance)):
    """Searches for a movie by term and returns the TMDB ID."""
    try:
        return await radarr_api_call(instance, "movie/lookup", params={"term": term})
    except Exception as e:
        print(f"Error in search_movie: {e}")
        raise HTTPException(status_code=500, detail="Error searching for movie.")

@router.get("/lookup", summary="Search for a new movie to add to Radarr")
async def lookup_movie(term: str, instance: dict = Depends(get_radarr_instance)):
    """Searches for a new movie by a search term. This is the first step to add a new movie."""
    encoded_term = quote(term)
    return await radarr_api_call(instance, f"movie/lookup?term={encoded_term}")

@router.put("/movie/{movie_id}/move", response_model=ConfirmationMessage, summary="Move movie to new folder", tags=["internal-admin"])
async def move_movie(movie_id: int, move_request: MoveMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Moves a movie to a new root folder and triggers Radarr to move the files."""
    await radarr_api_call(instance, f"movie/{movie_id}")  # ensure movie exists
    
    # Radarr's move logic is different from Sonarr's.
    # It requires a separate "movie/editor" endpoint.
    move_payload = {
            "movieIds": [movie_id],
            "rootFolderPath": move_request.rootFolderPath,
            "moveFiles": True,
        }
    
    # We need to get the ID of the destination root folder.
    root_folders = await radarr_api_call(instance, "rootfolder")
    target_folder = next((rf for rf in root_folders if rf["path"] == move_request.rootFolderPath), None)
    
    if not target_folder:
        raise HTTPException(status_code=400, detail=f"Root folder '{move_request.rootFolderPath}' not found in Radarr.")
        
    move_payload["targetRootFolderId"] = target_folder["id"]

    # This is a command, not a simple PUT on the movie object
    await radarr_api_call(instance, "movie/editor", method="PUT", json_data=move_payload)
    
    # Return a confirmation message
    return {"message": f"Move command initiated for movie {movie_id}."}

class AddMovieRequest(BaseModel):
    title: Optional[str] = None
    tmdbId: int
    qualityProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None

@router.post("/movie", response_model=Movie, summary="Add a new movie to Radarr")
async def add_movie(request: AddMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Adds a new movie to Radarr by looking it up via its TMDB ID."""
    # First, lookup the movie by TMDB ID
    try:
        movie_to_add = await radarr_api_call(instance, f"movie/lookup/tmdb?tmdbid={request.tmdbId}")
        if not movie_to_add:
            raise HTTPException(status_code=404, detail=f"Movie with TMDB ID {request.tmdbId} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up movie: {e}")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("RADARR_DEFAULT_ROOT_FOLDER_PATH", request.rootFolderPath)
    quality_profile_name = os.environ.get("RADARR_DEFAULT_QUALITY_PROFILE_NAME", None)

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await radarr_api_call(instance, "qualityprofile")
    quality_profile_id = None
    if request.qualityProfileId:
        quality_profile_id = request.qualityProfileId
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
        "addOptions": {"searchForMovie": True}
    }

    # Add the movie to Radarr
    added_movie = await radarr_api_call(instance, "movie", method="POST", json_data=add_payload)
    return added_movie

@router.post("/radarr/add_by_title", response_model=Movie, summary="Add a new movie to Radarr by title", operation_id="add_movie_by_title_radarr", tags=["internal-admin"])
async def add_movie_by_title_radarr(title: str, instance: dict = Depends(get_radarr_instance)):
    """Adds a new movie to Radarr by looking it up by title."""
    # First, lookup the movie by title
    try:
        lookup_results = await radarr_api_call(instance, "movie/lookup", params={"term": title})
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
    quality_profiles = await radarr_api_call(instance, "qualityprofile")
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
    added_movie = await radarr_api_call(instance, "movie", method="POST", json_data=add_payload)
    return added_movie

@router.get("/queue", response_model=List[QueueItem], summary="Get Radarr download queue")
async def get_download_queue(instance: dict = Depends(get_radarr_instance)):
    """Gets the list of items currently being downloaded by Radarr."""
    queue_data = await radarr_api_call(instance, "queue")
    # The actual queue items are in the 'records' key
    return queue_data.get("records", [])

@router.get("/history", response_model=List[HistoryItem], summary="Get Radarr download history")
async def get_download_history(instance: dict = Depends(get_radarr_instance)):
    """Gets the history of recently grabbed and imported downloads from Radarr."""
    history_data = await radarr_api_call(instance, "history")
    # The actual history items are in the 'records' key
    return history_data.get("records", [])

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Radarr queue", operation_id="delete_radarr_queue_item")
async def delete_from_queue(queue_id: int, removeFromClient: bool = True, instance: dict = Depends(get_radarr_instance)):
    """Deletes an item from the Radarr download queue."""
    params = {"removeFromClient": str(removeFromClient).lower()}
    await radarr_api_call(instance, f"queue/{queue_id}", method="DELETE", params=params)
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
async def update_movie(movie_id: int, request: UpdateMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Updates properties of a specific movie, such as monitoring status or quality profile."""
    # If a new root folder is provided, handle the move operation.
    if request.newRootFolderPath:
        move_payload = {
            "movieIds": [movie_id],
            "rootFolderPath": request.newRootFolderPath,
            "moveFiles": request.moveFiles,
        }
        root_folders = await radarr_api_call(instance, "rootfolder")
        target_folder = next((rf for rf in root_folders if rf["path"] == request.newRootFolderPath), None)
        if not target_folder:
            raise HTTPException(status_code=400, detail=f"Root folder '{request.newRootFolderPath}' not found in Radarr.")
        move_payload["targetRootFolderId"] = target_folder["id"]
        return await radarr_api_call(instance, "movie/editor", method="PUT", json_data=move_payload)

    # Otherwise, perform a standard update.
    movie_data = await radarr_api_call(instance, f"movie/{movie_id}")
    update_fields = request.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if key in movie_data:
            movie_data[key] = value
            
    return await radarr_api_call(instance, "movie", method="PUT", json_data=movie_data)

@router.get("/qualityprofiles", response_model=List[QualityProfile], summary="Get quality profiles for movies in Radarr")
async def get_quality_profiles(instance: dict = Depends(get_radarr_instance)):
    """Retrieves quality profiles for MOVIES configured in Radarr."""
    return await radarr_api_call(instance, "qualityprofile")

# Tag endpoints for Radarr following API v3 spec

@router.get("/rootfolders", operation_id="get_radarr_rootfolders", summary="Get root folders from Radarr")
async def get_root_folders(instance: dict = Depends(get_radarr_instance)):
    """Get all configured root folders in Radarr."""
    return await radarr_api_call(instance, "rootfolder")

# Helper function to get tag map
async def get_tag_map(instance_config: dict) -> dict:
    """Get a mapping of tag IDs to tag names."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
    
    if response.status_code != 200:
        return {}
    
    tags = response.json()
    return {tag['id']: tag['label'] for tag in tags}

# Tag management endpoints
@router.get("/radarr/tags", summary="Get all tags from Radarr", operation_id="radarr_get_tags", tags=["internal-admin"])
async def get_tags(
    instance_config: dict = Depends(get_radarr_instance),
):
    """Get all tags configured in Radarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
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
    instance_config: dict = Depends(get_radarr_instance),
):
    """Create a new tag in Radarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    payload = {"label": label}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
    
    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to create tag: {response.text}"
        )
    
    return response.json()

@router.put("/movie/{movie_id}/tags", summary="Update tags for a movie in Radarr (NOT for TV shows)", operation_id="update_movie_tags_radarr", tags=["internal-admin"])
async def update_movie_tags(
    movie_id: int,
    request: UpdateTagsRequest,
    instance_config: dict = Depends(get_radarr_instance),
):
    """Update tags for a movie. This replaces all existing tags."""
    # First get the current movie data
    movie_url = f"{instance_config['url']}/api/v3/movie/{movie_id}"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current movie data
        movie_response = await client.get(movie_url, headers=headers)
        if movie_response.status_code != 200:
            raise HTTPException(
                status_code=movie_response.status_code,
                detail=f"Movie not found: {movie_response.text}"
            )
        
        # Update tags in movie data
        movie_data = movie_response.json()
        movie_data["tags"] = request.tags
        
        # Send updated movie data back
        update_response = await client.put(movie_url, json=movie_data, headers=headers)
        
        if update_response.status_code not in [200, 202]:
            raise HTTPException(
                status_code=update_response.status_code,
                detail=f"Failed to update movie tags: {update_response.text}"
            )
        
        return update_response.json()

@router.put("/movie/{movie_id}/monitor", status_code=200, summary="Update monitoring status for a movie", operation_id="monitor_radarr_movie", tags=["internal-admin"])
async def monitor_movie(movie_id: int, request: MonitorRequest, instance: dict = Depends(get_radarr_instance)):
    """Updates the monitoring status for a movie."""
    movie_data = await radarr_api_call(instance, f"movie/{movie_id}")
    movie_data["monitored"] = request.monitored
    updated_movie = await radarr_api_call(instance, "movie", method="PUT", json_data=movie_data)
    return updated_movie


@router.post(
    "/movie/{movie_id}/fix",
    response_model=Movie,
    summary="Replace a damaged movie file",
    operation_id="fix_radarr_movie",
)
async def fix_movie(movie_id: int, instance: dict = Depends(get_radarr_instance)):
    """Replace a corrupted or unwanted movie file.

    This endpoint deletes the existing movie, re-adds it, and triggers a search
    for a fresh copy. It should **not** be used for routine quality upgrades.
    """
    # Get movie details to get the title
    try:
        movie = await radarr_api_call(instance, f"movie/{movie_id}")
        title_to_add = movie["title"]
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Movie with ID {movie_id} not found.")
        raise e

    # Delete the movie
    await delete_movie(movie_id, deleteFiles=True, addImportExclusion=False, instance=instance)

    # Re-add the movie by title
    added_movie = await add_movie_by_title_radarr(title_to_add, instance)
    return added_movie

@router.delete("/movie/{movie_id}", status_code=200, summary="Delete a movie from Radarr", operation_id="delete_radarr_movie")
async def delete_movie(
    movie_id: int,
    deleteFiles: bool = True,
    addImportExclusion: bool = False,
    instance: dict = Depends(get_radarr_instance)
):
    """Deletes a movie from Radarr. To re-download, you must re-add the movie."""
    params = {
        "deleteFiles": str(deleteFiles).lower(),
        "addImportExclusion": str(addImportExclusion).lower()
    }
    await radarr_api_call(instance, f"movie/{movie_id}", method="DELETE", params=params)
    return {"message": f"Movie with ID {movie_id} has been deleted."}