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
    status: str
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
    status: str
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

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Sonarr queue")
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
    seasons: Optional[List[SeasonUpdateRequest]] = None

@router.put("/series/{series_id}", response_model=Series, summary="Update series properties")
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

