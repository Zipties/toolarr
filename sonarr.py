from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os
from instance_endpoints import get_sonarr_instance

# Pydantic Models for Sonarr
class Series(BaseModel):
    id: int
    title: str
    path: Optional[str] = None
    tvdbId: Optional[int] = None
    monitored: bool
    rootFolderPath: Optional[str] = None
    qualityProfileId: Optional[int] = None
    qualityProfileName: Optional[str] = None
    languageProfileId: Optional[int] = None
    year: Optional[int] = None
    seriesType: Optional[str] = None
    tags: List[int] = []
    statistics: Optional[dict] = None
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

async def sonarr_api_call(
    instance: dict,
    endpoint: str,
    request: Request,
    method: str = "GET",
    params: dict | None = None,
    json_data: dict | None = None,
) -> dict | None:
    """Make an API call to a specific Sonarr instance."""
    base_url = instance["url"].rstrip("/")
    path = endpoint.lstrip("/")
    url = f"{base_url}/api/v3/{path}"
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                params=params,
                json=json_data,
                headers=headers,
            )
        response.raise_for_status()
        if response.status_code == 204 or not response.text:
            return None
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Sonarr API error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Sonarr: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with Sonarr: {str(e)}")
class Episode(BaseModel):
    id: int
    seriesId: int
    episodeFileId: int
    seasonNumber: int
    episodeNumber: int
    title: str
    airDate: Optional[str] = None
    monitored: bool

@router.get("/series/{series_id}/episodes", response_model=List[Episode], summary="Get all episodes for a series", operation_id="get_sonarr_episodes")
async def get_episodes(
    series_id: int,
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Retrieves all episodes for a given series."""
    return await sonarr_api_call(instance, "episode", request, params={"seriesId": series_id})


@router.get("/lookup", summary="Search for a new series to add to Sonarr")
async def lookup_series(
    term: str,
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Searches for a new series by a search term. This is the first step to add a new series."""
    return await sonarr_api_call(instance, "series/lookup", request, params={"term": term})

@router.put("/series/{sonarr_id}/move", response_model=Series, summary="Move series to new folder", tags=["internal-admin"])
async def move_series(
    sonarr_id: int,
    move_request: MoveSeriesRequest,
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Moves a series to a new root folder and triggers Sonarr to move the files."""
    series = await sonarr_api_call(instance, f"series/{sonarr_id}", request)
    series_folder_name = os.path.basename(series["path"])
    new_path = os.path.join(move_request.rootFolderPath, series_folder_name)
    
    series["rootFolderPath"] = move_request.rootFolderPath
    series["path"] = new_path
    series["moveFiles"] = True
    
    updated_series = await sonarr_api_call(instance, f"series/{series['id']}", request, method="PUT", json_data=series)
    return updated_series

class AddSeriesRequest(BaseModel):
    title: Optional[str] = None
    tvdbId: int
    qualityProfileId: Optional[int] = None
    languageProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None

@router.post("/series", response_model=Series, summary="Add a new series to Sonarr")
async def add_series(
    series_req: AddSeriesRequest,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Adds a new series to Sonarr by looking it up via its TVDB ID."""
    # First, lookup the series by TVDB ID
    try:
        series_to_add = await sonarr_api_call(instance, f"series/lookup?term=tvdb:{series_req.tvdbId}", http_request)
        if not series_to_add:
            raise HTTPException(status_code=404, detail=f"Series with TVDB ID {series_req.tvdbId} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up series: {e}")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("SONARR_DEFAULT_ROOT_FOLDER_PATH", series_req.rootFolderPath)
    quality_profile_name = os.environ.get("SONARR_DEFAULT_QUALITY_PROFILE_NAME", None)
    language_profile_id = int(os.environ.get("SONARR_DEFAULT_LANGUAGE_PROFILE_ID", series_req.languageProfileId or 1))

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await sonarr_api_call(instance, "qualityprofile", http_request)
    quality_profile_id = None
    if series_req.qualityProfileId:
        quality_profile_id = series_req.qualityProfileId
    elif quality_profile_name:
        for profile in quality_profiles:
            if profile["name"].lower() == quality_profile_name.lower():
                quality_profile_id = profile["id"]
                break
    
    if not quality_profile_id:
        raise HTTPException(status_code=400, detail=f"Quality profile '{quality_profile_name}' not found.")

    # Construct the payload for adding the series
    add_payload = {
        "tvdbId": series_to_add[0]["tvdbId"],
        "title": series_to_add[0]["title"],
        "qualityProfileId": quality_profile_id,
        "languageProfileId": language_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "seasons": series_to_add[0]["seasons"],
        "addOptions": {"searchForMissingEpisodes": True}
    }

    # Add the series to Sonarr
    added_series = await sonarr_api_call(instance, "series", http_request, method="POST", json_data=add_payload)
    return added_series

@router.post("/sonarr/add_by_title", response_model=Series, summary="Add a new series to Sonarr by title", operation_id="add_series_by_title_sonarr", tags=["internal-admin"])
async def add_series_by_title_sonarr(
    title: str,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Adds a new series to Sonarr by looking it up by title."""
    # First, lookup the series by title
    try:
        lookup_results = await sonarr_api_call(instance, "series/lookup", http_request, params={"term": title})
        if not lookup_results:
            raise HTTPException(status_code=404, detail=f"Series with title '{title}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up series: {e}")

    # Find the correct series from the lookup results
    series_to_add = lookup_results[0]
    
    if not series_to_add:
        raise HTTPException(status_code=404, detail=f"Series with title '{title}' not found in lookup results.")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("SONARR_DEFAULT_ROOT_FOLDER_PATH")
    quality_profile_name = os.environ.get("SONARR_DEFAULT_QUALITY_PROFILE_NAME")
    language_profile_id = int(os.environ.get("SONARR_DEFAULT_LANGUAGE_PROFILE_ID", 1))

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await sonarr_api_call(instance, "qualityprofile", http_request)
    quality_profile_id = None
    if quality_profile_name:
        for profile in quality_profiles:
            if profile["name"].lower() == quality_profile_name.lower():
                quality_profile_id = profile["id"]
                break
    
    if not quality_profile_id:
        raise HTTPException(status_code=400, detail=f"Quality profile '{quality_profile_name}' not found.")

    # Construct the payload for adding the series
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

    # Add the series to Sonarr
    added_series = await sonarr_api_call(instance, "series", http_request, method="POST", json_data=add_payload)
    return added_series

@router.get("/queue", response_model=List[QueueItem], summary="Get Sonarr download queue")
async def get_download_queue(
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Gets the list of items currently being downloaded by Sonarr."""
    queue_data = await sonarr_api_call(instance, "queue", request)
    # The actual queue items are in the 'records' key
    return queue_data.get("records", [])

@router.get("/history", response_model=List[HistoryItem], summary="Get Sonarr download history")
async def get_download_history(
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Gets the history of recently grabbed and imported downloads from Sonarr."""
    history_data = await sonarr_api_call(instance, "history", request)
    # The actual history items are in the 'records' key
    return history_data.get("records", [])

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Sonarr queue", operation_id="delete_sonarr_queue_item")
async def delete_from_queue(
    queue_id: int,
    request: Request,
    removeFromClient: bool = True,
    instance: dict = Depends(get_sonarr_instance),
):
    """Deletes an item from the Sonarr download queue."""
    params = {"removeFromClient": str(removeFromClient).lower()}
    await sonarr_api_call(instance, f"queue/{queue_id}", request, method="DELETE", params=params)
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
    newRootFolderPath: Optional[str] = None
    moveFiles: Optional[bool] = False

class UpdateTagsRequest(BaseModel):
    tags: List[int] = Field(..., description="List of tag IDs to assign to the series")

class MonitorRequest(BaseModel):
    monitored: bool

@router.get("/qualityprofiles", response_model=List[QualityProfile], summary="Get quality profiles for TV SHOWS in Sonarr")
async def get_quality_profiles(
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Retrieves quality profiles for TV SHOWS configured in Sonarr."""
    return await sonarr_api_call(instance, "qualityprofile", request)


# Helper function to get tag map
async def get_tag_map(instance_config: dict, request: Request) -> dict:
    """Get a mapping of tag IDs to tag names."""
    tags = await sonarr_api_call(instance_config, "tag", request)
    if not tags:
        return {}
    return {tag["id"]: tag["label"] for tag in tags}

# Update the library search to include tag names
@router.get("/library/with-tags", summary="Find TV SHOW with tag names", operation_id="series_with_tags")
async def find_series_with_tags(
    term: str,
    request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Searches the Sonarr library for TV shows and returns detailed results including tag names. Use this endpoint to find a series' ID for other operations."""
    all_series = await sonarr_api_call(instance, "series", request)
    tag_map = await get_tag_map(instance, request)
    
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
@router.get("/sonarr/tags", summary="Get all tags from Sonarr", operation_id="sonarr_get_tags")
async def get_tags(
    http_request: Request,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Get all tags configured in Sonarr."""
    return await sonarr_api_call(instance_config, "tag", http_request)

@router.post("/sonarr/tags", summary="Create a new tag in Sonarr", operation_id="sonarr_create_tag", tags=["internal-admin"])
async def create_tag(
    label: str,
    request: Request,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Create a new tag in Sonarr."""
    payload = {"label": label}
    created = await sonarr_api_call(
        instance_config,
        "tag",
        request,
        method="POST",
        json_data=payload,
    )
    return created

@router.delete("/sonarr/tags/{tag_id}", status_code=204, operation_id="delete_sonarr_tag", summary="Delete a tag from Sonarr", tags=["internal-admin"])
async def delete_tag(
    tag_id: int,
    request: Request,
    instance_config: dict = Depends(get_sonarr_instance),
):
    """Delete a tag from Sonarr by its ID."""
    try:
        await sonarr_api_call(
            instance_config,
            f"tag/{tag_id}",
            request,
            method="DELETE",
        )
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with ID {tag_id} not found",
            ) from e
        raise



@router.put("/series/{series_id}", operation_id="update_sonarr_series_properties", summary="Update series properties")
async def update_series_properties(
    series_id: int,
    update_req: UpdateSeriesRequest,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Updates series properties. To remove a tag, get the series's current tags, then submit a new list of tags that excludes the one to be removed. This replaces the entire list of tags for the series."""
    # If a new root folder is provided, handle the move operation.
    if update_req.newRootFolderPath:
        series = await sonarr_api_call(instance, f"series/{series_id}", http_request)
        series_folder_name = os.path.basename(series["path"])
        new_path = os.path.join(update_req.newRootFolderPath, series_folder_name)
        
        series["rootFolderPath"] = update_req.newRootFolderPath
        series["path"] = new_path
        series["moveFiles"] = update_req.moveFiles

        return await sonarr_api_call(instance, f"series/{series['id']}", http_request, method="PUT", json_data=series)

    # Otherwise, perform a standard update.
    series_data = await sonarr_api_call(instance, f"series/{series_id}", http_request)
    update_fields = update_req.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if key in series_data:
            series_data[key] = value
            
    return await sonarr_api_call(instance, f"series/{series_id}", http_request, method="PUT", json_data=series_data)

@router.put("/series/{series_id}/monitor", status_code=200, summary="Update monitoring status for an entire series", operation_id="monitor_sonarr_series", tags=["internal-admin"])
async def monitor_series(
    series_id: int,
    monitor_req: MonitorRequest,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Updates the monitoring status for an entire series."""
    series_data = await sonarr_api_call(instance, f"series/{series_id}", http_request)
    series_data["monitored"] = monitor_req.monitored
    
    # Cascade the monitoring status to all seasons
    for season in series_data.get("seasons", []):
        season["monitored"] = monitor_req.monitored
        
    updated_series = await sonarr_api_call(instance, f"series/{series_id}", http_request, method="PUT", json_data=series_data)
    return updated_series

@router.post(
    "/series/{series_id}/search",
    summary="Search for a series upgrade",
    operation_id="search_for_series_upgrade",
)
async def search_for_series_upgrade(
    series_id: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Triggers a search for a series to find a better quality version. This is a non-destructive action."""
    await sonarr_api_call(
        instance,
        "command", http_request,
        method="POST",
        json_data={"name": "SeriesSearch", "seriesId": series_id},
    )
    return {"message": f"Triggered search for series {series_id}."}

@router.put("/series/{series_id}/seasons/{season_number}/monitor", status_code=200, summary="Update monitoring status for a single season", operation_id="monitor_sonarr_season", tags=["internal-admin"])
async def monitor_season(
    series_id: int,
    season_number: int,
    monitor_req: MonitorRequest,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Updates the monitoring status for a single season of a series."""
    series_data = await sonarr_api_call(instance, f"series/{series_id}", http_request)
    
    # Find the season and update its monitored status
    season_found = False
    for season in series_data.get("seasons", []):
        if season.get("seasonNumber") == season_number:
            season["monitored"] = monitor_req.monitored
            season_found = True
            break
            
    if not season_found:
        raise HTTPException(status_code=404, detail=f"Season {season_number} not found in series {series_id}")

    updated_series = await sonarr_api_call(instance, f"series/{series_id}", http_request, method="PUT", json_data=series_data)
    return updated_series


@router.post(
    "/series/{series_id}/episodes/{episode_id}/search",
    status_code=200,
    summary="Search for a single episode",
    operation_id="search_sonarr_episode",
)
async def search_episode(
    series_id: int,
    episode_id: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Trigger a search for an individual episode without deleting existing files."""

    await sonarr_api_call(
        instance,
        "command", http_request,
        method="POST",
        json_data={"name": "EpisodeSearch", "episodeIds": [episode_id]},
    )

    return {"message": f"Triggered search for episode {episode_id}."}


@router.post("/series/{series_id}/fix", response_model=Series, summary="Replace a damaged series", operation_id="fix_sonarr_series")
async def fix_series(
    series_id: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Deletes, re-adds, and searches for a series. WARNING: This is a destructive action. For routine quality upgrades, use the '/series/{series_id}/search' endpoint instead."""
    # Get series details to get the title
    try:
        series = await sonarr_api_call(instance, f"series/{series_id}", http_request)
        title_to_add = series["title"]
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Series with ID {series_id} not found.")
        raise e

    # Delete the series
    await delete_series(series_id, deleteFiles=True, addImportExclusion=False, instance=instance, http_request=http_request)

    # Re-add the series by title
    added_series = await add_series_by_title_sonarr(title_to_add, instance, http_request)
    return added_series


@router.post("/series/{series_id}/season/{season_number}/search", status_code=200, summary="Trigger a search for an entire season", operation_id="season_search")
async def search_season(
    series_id: int,
    season_number: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Triggers a search for all episodes within a season."""
    await sonarr_api_call(
        instance,
        "command", http_request,
        method="POST",
        json_data={"name": "SeasonSearch", "seriesId": series_id, "seasonNumber": season_number},
    )
    return {"message": f"Triggered search for season {season_number} of series {series_id}."}


@router.post("/series/{series_id}/search", status_code=200, summary="Trigger a search for an entire series", operation_id="series_search")
async def search_series(
    series_id: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance),
):
    """Triggers a search for all episodes of a series."""
    await sonarr_api_call(
        instance,
        "command", http_request,
        method="POST",
        json_data={"name": "SeriesSearch", "seriesId": series_id},
    )
    return {"message": f"Triggered search for series {series_id}."}


@router.delete("/series/{series_id}", status_code=200, summary="Delete a series from Sonarr", operation_id="delete_sonarr_series")
async def delete_series(
    series_id: int,
    http_request: Request,
    deleteFiles: bool = True,
    addImportExclusion: bool = False,
    instance: dict = Depends(get_sonarr_instance)
):
    """Deletes a whole series."""
    params = {
        "deleteFiles": str(deleteFiles).lower(),
        "addImportListExclusion": str(addImportExclusion).lower()
    }
    await sonarr_api_call(instance, f"series/{series_id}", http_request, method="DELETE", params=params)
    return {"message": f"Series with ID {series_id} has been deleted."}

@router.delete("/series/{series_id}/episodes", status_code=200, summary="Delete a specific episode file from Sonarr", operation_id="delete_sonarr_episode")
async def delete_episode(
    series_id: int,
    season_number: int,
    episode_number: int,
    http_request: Request,
    instance: dict = Depends(get_sonarr_instance)
):
    """Deletes a specific episode file."""
    # Find the episode_id
    episodes = await sonarr_api_call(instance, "episode", http_request, params={"seriesId": series_id})
    episode_to_delete = None
    for episode in episodes:
        if episode.get("seasonNumber") == season_number and episode.get("episodeNumber") == episode_number:
            episode_to_delete = episode
            break
    
    if not episode_to_delete or not episode_to_delete.get("hasFile"):
        raise HTTPException(status_code=404, detail=f"Episode S{season_number:02d}E{episode_number:02d} not found or has no file.")

    # Delete the episode file
    episode_file_id = episode_to_delete.get("episodeFileId")
    if episode_file_id:
        await sonarr_api_call(instance, f"episodefile/{episode_file_id}", http_request, method="DELETE")
        return {"message": f"Successfully deleted file for episode S{season_number:02d}E{episode_number:02d}."}
    else:
        raise HTTPException(status_code=404, detail="Episode file ID not found.")
