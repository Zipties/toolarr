from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException
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
            
            print(f"Radarr API response: {response.status_code} {response.text}")
            response.raise_for_status()
            
            # Handle successful empty responses
            if response.status_code == 204 or not response.text:
                return None
                
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Radarr API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with Radarr: {str(e)}")

@router.get("/library", response_model=List[Movie], summary="Check if a movie exists in the Radarr library")
async def find_movie_in_library(term: str, instance: dict = Depends(get_radarr_instance)):
    """
    Searches for a movie that is already in the Radarr library.
    This is for checking existing movies, not for discovering new ones.
    """
    all_movies = await radarr_api_call(instance, "movie")
    
    # Get quality profiles to map IDs to names
    quality_profiles = await radarr_api_call(instance, "qualityprofile")
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
    """
    Searches for a new movie by a search term.
    This is the first step to add a new movie, as it provides the necessary tmdbId.
    """
    encoded_term = quote(term)
    return await radarr_api_call(instance, f"movie/lookup?term={encoded_term}")

@router.put("/movie/{movie_id}/move", response_model=Movie, summary="Move movie to new folder")
async def move_movie(movie_id: int, move_request: MoveMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Moves a movie to a new root folder and triggers Radarr to move the files."""
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

@router.post("/radarr/add_by_title", response_model=Movie, summary="Add a new movie to Radarr by title", operation_id="add_movie_by_title_radarr")
async def add_movie_by_title_radarr(title: str, instance: dict = Depends(get_radarr_instance)):
    """
    Adds a new movie to Radarr by looking it up by title.
    This is a one-shot command that handles the lookup and add process.
    """
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
    """Gets the list of items currently being downloaded or waiting to be downloaded by Radarr."""
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
    """Deletes an item from the Radarr download queue. Optionally, it can also remove the item from the download client."""
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
class UpdateTagsRequest(BaseModel):
    tags: List[int] = Field(..., description="List of tag IDs to assign to the movie")


@router.put("/movie/{movie_id}", operation_id="update_radarr_movie_properties", summary="Update movie properties")
async def update_movie(movie_id: int, request: UpdateMovieRequest, instance: dict = Depends(get_radarr_instance)):
    """Updates properties of a specific movie, such as monitoring status or quality profile."""
    # First, get the full movie object
    movie_data = await radarr_api_call(instance, f"movie/{movie_id}")

    # Update fields if they were provided in the request
    if request.monitored is not None:
        movie_data["monitored"] = request.monitored
    if request.qualityProfileId is not None:
        movie_data["qualityProfileId"] = request.qualityProfileId
    if request.minimumAvailability is not None:
        movie_data["minimumAvailability"] = request.minimumAvailability
    if request.tags is not None:
        movie_data["tags"] = request.tags
    if request.rootFolderPath is not None:
        # This is not the correct way to move a movie in Radarr.
        # The move_movie endpoint should be used instead.
        # We are only updating the rootFolderPath property here.
        movie_data["rootFolderPath"] = request.rootFolderPath

    # Send the updated object back to Radarr
    return await radarr_api_call(instance, "movie", method="PUT", json_data=movie_data)

@router.get("/qualityprofiles", response_model=List[QualityProfile], summary="Get quality profiles for movies in Radarr")
async def get_quality_profiles(instance: dict = Depends(get_radarr_instance)):
    """Retrieves quality profiles for MOVIES configured in Radarr. Only needed when managing quality profiles directly, not for checking a movie's quality profile."""
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

# Update the library search to include tag names
@router.get("/library/with-tags", summary="Find movies with tag names", operation_id="movies_with_tags")
async def find_movies_with_tags(term: str, instance: dict = Depends(get_radarr_instance)):
    """Searches library and includes tag names instead of just IDs."""
    all_movies = await radarr_api_call(instance, "movie")
    tag_map = await get_tag_map(instance)
    
    filtered_movies = []
    for m in all_movies:
        if term.lower() in m.get("title", "").lower():
            # Add tag names
            if "tags" in m and m["tags"]:
                m["tagNames"] = [tag_map.get(tag_id, f"Unknown tag {tag_id}") for tag_id in m["tags"]]
            else:
                m["tagNames"] = []
            filtered_movies.append(m)
    
    return filtered_movies

# Tag management endpoints
@router.get("/radarr/tags", summary="Get all tags from Radarr", operation_id="radarr_get_tags")
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

@router.post("/radarr/tags", summary="Create a new tag in Radarr", operation_id="radarr_create_tag") 
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

@router.put("/movie/{movie_id}/tags", summary="Update tags for a movie in Radarr (NOT for TV shows)", operation_id="update_movie_tags_radarr")
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

@router.delete("/movie/{movie_id}", status_code=200, summary="Delete a movie from Radarr", operation_id="delete_radarr_movie")
async def delete_movie(
    movie_id: int,
    deleteFiles: bool = True,
    addImportExclusion: bool = False,
    instance: dict = Depends(get_radarr_instance)
):
    """
    Deletes a movie from Radarr.

    - **movie_id**: The ID of the movie to delete.
    - **deleteFiles**: If `True`, the movie file will be deleted from the disk.
    - **addImportExclusion**: If `True`, an import exclusion will be added for this movie.
    """
    params = {
        "deleteFiles": str(deleteFiles).lower(),
        "addImportExclusion": str(addImportExclusion).lower()
    }
    await radarr_api_call(instance, f"movie/{movie_id}", method="DELETE", params=params)
    return {"message": f"Movie with ID {movie_id} has been deleted."}
