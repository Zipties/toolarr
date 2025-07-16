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
    qualityProfileName: Optional[str] = None
    languageProfileId: int
    year: Optional[int] = None
    seriesType: Optional[str] = None
    tags: List[int] = []
    statistics: dict = {}
    seasons: List[dict] = []

class MoveSeriesRequest(BaseModel):
    rootFolderPath: str = Field(..., description="The new root folder path for the series.")

class QueueItem(BaseModel):
    id: int
    seriesId: int
    episodeId: int
    title: str
    status: Optional[str] = None
    protocol: str
    size: float
    timeLeft: Optional[str] = None
    estimatedCompletionTime: Optional[str] = None
    trackedDownloadStatus: Optional[str] = None
    statusMessages: Optional[List[dict]] = None
    series: Optional[dict] = None
    episode: Optional[dict] = None
    indexer: Optional[str] = None

class HistoryItem(BaseModel):
    id: int
    seriesId: int
    episodeId: int
    sourceTitle: str
    eventType: str
    status: Optional[str] = None
    date: str

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
    """Dependency to get a Sonarr instance's config. Handles 'default' keyword and case-insensitive matching."""
    if not SONARR_INSTANCES:
        load_sonarr_instances()
    
    # Handle 'default' keyword
    if instance_name.lower() == "default":
        if not SONARR_INSTANCES:
            raise HTTPException(status_code=404, detail="No Sonarr instances configured.")
        # Return the first configured instance
        return next(iter(SONARR_INSTANCES.values()))
    
    # Try exact match first
    instance = SONARR_INSTANCES.get(instance_name)
    if instance:
        return instance
    
    # Try case-insensitive match
    for name, config in SONARR_INSTANCES.items():
        if name.lower() == instance_name.lower():
            return config
    
    # Raise error for unknown instance names
    raise HTTPException(status_code=404, detail=f"Sonarr instance '{instance_name}' not found. Available instances: {list(SONARR_INSTANCES.keys())}")

async def sonarr_api_call(instance: dict, endpoint: str, method: str = "GET", params: dict = None, json_data: dict = None):
    """Make an API call to a specific Sonarr instance."""
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    
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
            
            response.raise_for_status()
            # For DELETE requests that return no content
            if response.status_code == 204:
                return None
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Sonarr API error: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error communicating with Sonarr: {str(e)}")

@router.get("/library", response_model=List[Series], summary="Find TV SHOW in Sonarr library (includes quality profile name)")
async def find_series_in_library(term: str, instance: dict = Depends(get_sonarr_instance)):
    """Searches the existing Sonarr library to find details about a specific TV series including its quality profile name. No need to separately query quality profiles."""
    all_series = await sonarr_api_call(instance, "series")
    
    # Get quality profiles to map IDs to names
    quality_profiles = await sonarr_api_call(instance, "qualityprofile")
    quality_profile_map = {qp["id"]: qp["name"] for qp in quality_profiles}
    
    # Filter series and add quality profile name
    filtered_series = []
    for s in all_series:
        if term.lower() in s.get("title", "").lower():
            # Add quality profile name to the series object
            if "qualityProfileId" in s:
                s["qualityProfileName"] = quality_profile_map.get(s["qualityProfileId"], "Unknown")
            filtered_series.append(s)
    
    return filtered_series

@router.put("/series/{sonarr_id}/move", response_model=Series, summary="Move series to new folder")
async def move_series(sonarr_id: int, move_request: MoveSeriesRequest, instance: dict = Depends(get_sonarr_instance)):
    """Moves a series to a new root folder and triggers Sonarr to move the files."""
    series = await sonarr_api_call(instance, f"series/{sonarr_id}")
    series_folder_name = os.path.basename(series["path"])
    new_path = os.path.join(move_request.rootFolderPath, series_folder_name)
    
    series["rootFolderPath"] = move_request.rootFolderPath
    series["path"] = new_path
    series["moveFiles"] = True
    
    updated_series = await sonarr_api_call(instance, f"series/{series['id']}", method="PUT", json_data=series)
    return updated_series

@router.get("/queue", response_model=List[QueueItem], summary="Get Sonarr download queue")
async def get_download_queue(instance: dict = Depends(get_sonarr_instance)):
    """Gets the list of items currently being downloaded or waiting to be downloaded by Sonarr."""
    queue_data = await sonarr_api_call(instance, "queue")
    # The actual queue items are in the 'records' key
    return queue_data.get("records", [])

@router.get("/history", response_model=List[HistoryItem], summary="Get Sonarr download history")
async def get_download_history(instance: dict = Depends(get_sonarr_instance)):
    """Gets the history of recently grabbed and imported downloads from Sonarr."""
    history_data = await sonarr_api_call(instance, "history")
    # The actual history items are in the 'records' key
    return history_data.get("records", [])

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Sonarr queue", operation_id="delete_queue_item")
async def delete_from_queue(queue_id: int, removeFromClient: bool = True, instance: dict = Depends(get_sonarr_instance)):
    """Deletes an item from the Sonarr download queue. Optionally, it can also remove the item from the download client."""
    params = {"removeFromClient": str(removeFromClient).lower()}
    await sonarr_api_call(instance, f"queue/{queue_id}", method="DELETE", params=params)
    return

class QualityProfile(BaseModel):
    id: int
    name: str

class SeasonUpdateRequest(BaseModel):
    seasonNumber: int
    monitored: bool

class UpdateSeriesRequest(BaseModel):
    monitored: Optional[bool] = None
    qualityProfileId: Optional[int] = None
    languageProfileId: Optional[int] = None
    seasonFolder: Optional[bool] = None
    path: Optional[str] = None
    tags: Optional[List[int]] = None

class UpdateTagsRequest(BaseModel):
    tag_ids: List[int] = Field(..., description="List of tag IDs to assign to the series")


async def update_series(series_id: int, request: UpdateSeriesRequest, instance: dict = Depends(get_sonarr_instance)):
    """Updates properties of a specific series, such as monitoring status, quality profile, and per-season monitoring."""
    # First, get the full series object
    series_data = await sonarr_api_call(instance, f"series/{series_id}")

    # Update top-level fields if they were provided
    if request.monitored is not None:
        series_data["monitored"] = request.monitored
    if request.qualityProfileId is not None:
        series_data["qualityProfileId"] = request.qualityProfileId

    # Update per-season monitoring if provided
    if request.seasons:
        for season_update in request.seasons:
            for season in series_data.get("seasons", []):
                if season.get("seasonNumber") == season_update.seasonNumber:
                    season["monitored"] = season_update.monitored
                    break

    # Send the updated object back to Sonarr
    return await sonarr_api_call(instance, "series", method="PUT", json_data=series_data)

@router.get("/qualityprofiles", response_model=List[QualityProfile], summary="Get quality profiles for TV SHOWS in Sonarr")
async def get_quality_profiles(instance: dict = Depends(get_sonarr_instance)):
    """Retrieves quality profiles for TV SHOWS configured in Sonarr. Only needed when managing quality profiles directly, not for checking a show's quality profile."""
    return await sonarr_api_call(instance, "qualityprofile")


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
@router.get("/library/with-tags", summary="Find TV SHOW with tag names", operation_id="series_with_tags")
async def find_series_with_tags(term: str, instance: dict = Depends(get_sonarr_instance)):
    """Searches library and includes tag names instead of just IDs."""
    all_series = await sonarr_api_call(instance, "series")
    tag_map = await get_tag_map(instance)
    
    filtered_series = []
    for s in all_series:
        if term.lower() in s.get("title", "").lower():
            # Add tag names
            if "tags" in s and s["tags"]:
                s["tagNames"] = [tag_map.get(tag_id, f"Unknown tag {tag_id}") for tag_id in s["tags"]]
            else:
                s["tagNames"] = []
            filtered_series.append(s)
    
    return filtered_series

# Tag management endpoints
@router.get("/tags", summary="Get all tags from Sonarr", operation_id="sonarr_get_tags")
async def get_tags(
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Get all tags configured in Sonarr."""
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

@router.get("/rootfolders", operation_id="get_sonarr_rootfolders", summary="Get root folders from Sonarr")
async def get_root_folders(instance: dict = Depends(get_sonarr_instance)):
    """Get all configured root folders in Sonarr."""
    return await sonarr_api_call(instance, "rootfolder")

@router.post("/tags", summary="Create a new tag in Sonarr", operation_id="sonarr_create_tag")
async def create_tag(
    label: str,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Create a new tag in Sonarr."""
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

@router.delete("/tags/{tag_id}", status_code=204, operation_id="delete_sonarr_tag", summary="Delete a tag from Sonarr")
async def delete_tag(
    tag_id: int,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Delete a tag from Sonarr by its ID."""
    url = f"{instance_config['url']}/api/v3/tag/{tag_id}"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(url, headers=headers)
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with ID {tag_id} not found"
            )
        elif response.status_code != 200 and response.status_code != 204:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to delete tag: {response.text}"
            )
        
        return


@router.put("/series/{series_id}", operation_id="update_sonarr_series_properties", summary="Update series properties")
async def update_series_properties(
    series_id: int,
    request: UpdateSeriesRequest,
    instance: dict = Depends(get_sonarr_instance)
):
    """Update series properties like monitoring status, quality profile, tags, etc."""
    # Get current series data
    series_data = await sonarr_api_call(instance, f"series/{series_id}")
    
    # Update only provided fields
    if request.monitored is not None:
        series_data["monitored"] = request.monitored
    if request.qualityProfileId is not None:
        series_data["qualityProfileId"] = request.qualityProfileId
    if request.languageProfileId is not None:
        series_data["languageProfileId"] = request.languageProfileId  
    if request.seasonFolder is not None:
        series_data["seasonFolder"] = request.seasonFolder
    if request.path is not None:
        series_data["path"] = request.path
    if request.tags is not None:
        series_data["tags"] = request.tags
    
    # Send update
    return await sonarr_api_call(instance, f"series/{series_id}", method="PUT", json_data=series_data)

@router.put("/series/{series_id}/tags", summary="Update tags for a TV SERIES in Sonarr", operation_id="sonarr_update_tags")
async def update_series_tags(
    series_id: int,
    request: UpdateTagsRequest,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Update tags for a series. This replaces all existing tags."""
    # First get the current series data
    series_url = f"{instance_config['url']}/api/v3/series/{series_id}"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current series data
        series_response = await client.get(series_url, headers=headers)
        if series_response.status_code != 200:
            raise HTTPException(
                status_code=series_response.status_code,
                detail=f"Series not found: {series_response.text}"
            )
        
        # Update tags in series data
        series_data = series_response.json()
        series_data["tags"] = request.tag_ids
        
        # Send updated series data back
        update_response = await client.put(series_url, json=series_data, headers=headers)
        
        if update_response.status_code not in [200, 202]:
            raise HTTPException(
                status_code=update_response.status_code,
                detail=f"Failed to update series tags: {update_response.text}"
            )
        
        return update_response.json()
