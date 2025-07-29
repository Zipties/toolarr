from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import httpx
import os
from instance_endpoints import get_sonarr_instance
from main import get_http_client

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
    client: httpx.AsyncClient,
    method: str = "GET",
    params: dict = None,
    json_data: dict = None,
):
    """Make an API call to a specific Sonarr instance."""
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    
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
        if response.status_code == 204 or not response.text:
            return None
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Sonarr API error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Error connecting to Sonarr: {str(e)}.")
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
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Retrieves all episodes for a given series."""
    return await sonarr_api_call(instance, "episode", client, params={"seriesId": series_id})

@router.get("/library/series", response_model=List[Series], operation_id="search_sonarr_library_for_series", summary="Search Sonarr library for series.")
async def find_series_in_library(
    term: str,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Searches for a series in the library. For user output, prefer 'find_series_with_tags'."""
    all_series = await sonarr_api_call(instance, "series", client)
    
    # Get quality profiles to map IDs to names
    quality_profiles = await sonarr_api_call(instance, "qualityprofile", client)
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

@router.get("/series/id_lookup", summary="Get the series ID for a given title.", operation_id="get_sonarr_series_id_by_title")
async def get_series_id_by_title(
    title: str,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Looks up a series by title and returns its ID. Use this to get the series_id for other operations."""
    all_series = await sonarr_api_call(instance, "series", client)
    for s in all_series:
        if title.lower() == s.get("title", "").lower():
            return {"series_id": s["id"]}
    raise HTTPException(status_code=404, detail=f"Series with title '{title}' not found.")

@router.get("/lookup", summary="Search for a new series to add to Sonarr")
async def lookup_series(
    term: str,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Searches for a new series by a search term. This is the first step to add a new series."""
    return await sonarr_api_call(instance, "series/lookup", client, params={"term": term})

@router.put("/series/{sonarr_id}/move", response_model=Series, summary="Move series to new folder", tags=["internal-admin"])
async def move_series(
    sonarr_id: int,
    move_request: MoveSeriesRequest,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Moves a series to a new root folder and triggers Sonarr to move the files."""
    series = await sonarr_api_call(instance, f"series/{sonarr_id}", client)
    series_folder_name = os.path.basename(series["path"])
    new_path = os.path.join(move_request.rootFolderPath, series_folder_name)
    
    series["rootFolderPath"] = move_request.rootFolderPath
    series["path"] = new_path
    series["moveFiles"] = True
    
    updated_series = await sonarr_api_call(instance, f"series/{series['id']}", client, method="PUT", json_data=series)
    return updated_series

class AddSeriesRequest(BaseModel):
    title: Optional[str] = None
    tvdbId: int
    qualityProfileId: Optional[int] = None
    languageProfileId: Optional[int] = None
    rootFolderPath: Optional[str] = None

@router.post("/series", response_model=Series, summary="Add a new series to Sonarr")
async def add_series(
    request: AddSeriesRequest,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Adds a new series to Sonarr by looking it up via its TVDB ID."""
    # First, lookup the series by TVDB ID
    try:
        series_to_add = await sonarr_api_call(instance, f"series/lookup?term=tvdb:{request.tvdbId}", client)
        if not series_to_add:
            raise HTTPException(status_code=404, detail=f"Series with TVDB ID {request.tvdbId} not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error looking up series: {e}")

    # Get default root folder path and quality profile from environment variables
    root_folder_path = os.environ.get("SONARR_DEFAULT_ROOT_FOLDER_PATH", request.rootFolderPath)
    quality_profile_name = os.environ.get("SONARR_DEFAULT_QUALITY_PROFILE_NAME", None)
    language_profile_id = int(os.environ.get("SONARR_DEFAULT_LANGUAGE_PROFILE_ID", request.languageProfileId or 1))

    if not root_folder_path:
        raise HTTPException(status_code=400, detail="rootFolderPath must be provided either in the request or as an environment variable.")

    # Get quality profiles to find the ID for the given name
    quality_profiles = await sonarr_api_call(instance, "qualityprofile", client)
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
    added_series = await sonarr_api_call(instance, "series", client, method="POST", json_data=add_payload)
    return added_series

@router.post("/sonarr/add_by_title", response_model=Series, summary="Add a new series to Sonarr by title", operation_id="add_series_by_title_sonarr", tags=["internal-admin"])
async def add_series_by_title_sonarr(
    title: str,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Adds a new series to Sonarr by looking it up by title."""
    # First, lookup the series by title
    try:
        lookup_results = await sonarr_api_call(instance, "series/lookup", client, params={"term": title})
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
    quality_profiles = await sonarr_api_call(instance, "qualityprofile", client)
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
    added_series = await sonarr_api_call(instance, "series", client, method="POST", json_data=add_payload)
    return added_series

@router.get("/queue", response_model=List[QueueItem], summary="Get Sonarr download queue")
async def get_download_queue(
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Gets the list of items currently being downloaded by Sonarr."""
    queue_data = await sonarr_api_call(instance, "queue", client)
    # The actual queue items are in the 'records' key
    return queue_data.get("records", [])

@router.get("/history", response_model=List[HistoryItem], summary="Get Sonarr download history")
async def get_download_history(
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Gets the history of recently grabbed and imported downloads from Sonarr."""
    history_data = await sonarr_api_call(instance, "history", client)
    # The actual history items are in the 'records' key
    return history_data.get("records", [])

@router.delete("/queue/{queue_id}", status_code=204, summary="Delete item from Sonarr queue", operation_id="delete_sonarr_queue_item")
async def delete_from_queue(
    queue_id: int,
    removeFromClient: bool = True,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Deletes an item from the Sonarr download queue."""
    params = {"removeFromClient": str(removeFromClient).lower()}
    await sonarr_api_call(instance, f"queue/{queue_id}", client, method="DELETE", params=params)
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
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Retrieves quality profiles for TV SHOWS configured in Sonarr."""
    return await sonarr_api_call(instance, "qualityprofile", client)


# Helper function to get tag map
async def get_tag_map(instance_config: dict, client: httpx.AsyncClient) -> dict:
    """Get a mapping of tag IDs to tag names."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    response = await client.get(url, headers=headers)
    
    if response.status_code != 200:
        return {}
    
    tags = response.json()
    return {tag['id']: tag['label'] for tag in tags}

# Update the library search to include tag names
@router.get("/library/with-tags", summary="Find TV SHOW with tag names", operation_id="series_with_tags")
async def find_series_with_tags(
    term: str,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Searches library and includes tag names instead of just IDs. Use this for user-facing output."""
    all_series = await sonarr_api_call(instance, "series", client)
    tag_map = await get_tag_map(instance, client)
    
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
    instance_config: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Get all tags configured in Sonarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    response = await client.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to fetch tags: {response.text}"
        )
    
    return response.json()

@router.post("/sonarr/tags", summary="Create a new tag in Sonarr", operation_id="sonarr_create_tag", tags=["internal-admin"])
async def create_tag(
    label: str,
    instance_config: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Create a new tag in Sonarr."""
    url = f"{instance_config['url']}/api/v3/tag"
    headers = {"X-Api-Key": instance_config["api_key"]}
    payload = {"label": label}
    
    response = await client.post(url, json=payload, headers=headers)
    
    if response.status_code != 201:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to create tag: {response.text}"
        )
    
    return response.json()

@router.delete("/sonarr/tags/{tag_id}", status_code=204, operation_id="delete_sonarr_tag", summary="Delete a tag from Sonarr", tags=["internal-admin"])
async def delete_tag(
    tag_id: int,
    instance_config: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Delete a tag from Sonarr by its ID."""
    url = f"{instance_config['url']}/api/v3/tag/{tag_id}"
    headers = {"X-Api-Key": instance_config["api_key"]}
    
    response = await client.delete(url, headers=headers)
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"Tag with ID {tag_id} not found",
        )
    elif response.status_code != 200 and response.status_code != 204:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to delete tag: {response.text}"
        )



@router.put("/series/{series_id}", operation_id="update_sonarr_series_properties", summary="Update series properties")
async def update_series_properties(
    series_id: int,
    request: UpdateSeriesRequest,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Updates series properties. To remove a tag, get the series's current tags, then submit a new list of tags that excludes the one to be removed. This replaces the entire list of tags for the series."""
    # If a new root folder is provided, handle the move operation.
    if request.newRootFolderPath:
        series = await sonarr_api_call(instance, f"series/{series_id}", client)
        series_folder_name = os.path.basename(series["path"])
        new_path = os.path.join(request.newRootFolderPath, series_folder_name)
        
        series["rootFolderPath"] = request.newRootFolderPath
        series["path"] = new_path
        series["moveFiles"] = request.moveFiles
        
        return await sonarr_api_call(instance, f"series/{series['id']}", client, method="PUT", json_data=series)

    # Otherwise, perform a standard update.
    series_data = await sonarr_api_call(instance, f"series/{series_id}", client)
    update_fields = request.dict(exclude_unset=True)
    for key, value in update_fields.items():
        if key in series_data:
            series_data[key] = value
            
    return await sonarr_api_call(instance, f"series/{series_id}", client, method="PUT", json_data=series_data)

@router.put("/series/{series_id}/monitor", status_code=200, summary="Update monitoring status for an entire series", operation_id="monitor_sonarr_series", tags=["internal-admin"])
async def monitor_series(
    series_id: int,
    request: MonitorRequest,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Updates the monitoring status for an entire series."""
    series_data = await sonarr_api_call(instance, f"series/{series_id}", client)
    series_data["monitored"] = request.monitored
    
    # Cascade the monitoring status to all seasons
    for season in series_data.get("seasons", []):
        season["monitored"] = request.monitored
        
    updated_series = await sonarr_api_call(instance, f"series/{series_id}", client, method="PUT", json_data=series_data)
    return updated_series

@router.post(
    "/series/{series_id}/search",
    summary="Search for a series upgrade",
    operation_id="search_for_series_upgrade",
)
async def search_for_series_upgrade(
    series_id: int,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Triggers a search for a series to find a better quality version. This is a non-destructive action."""
    await sonarr_api_call(
        instance,
        "command",
        client,
        method="POST",
        json_data={"name": "SeriesSearch", "seriesId": series_id},
    )
    return {"message": f"Triggered search for series {series_id}."}

@router.put("/series/{series_id}/seasons/{season_number}/monitor", status_code=200, summary="Update monitoring status for a single season", operation_id="monitor_sonarr_season", tags=["internal-admin"])
async def monitor_season(
    series_id: int,
    season_number: int,
    request: MonitorRequest,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Updates the monitoring status for a single season of a series."""
    series_data = await sonarr_api_call(instance, f"series/{series_id}", client)
    
    # Find the season and update its monitored status
    season_found = False
    for season in series_data.get("seasons", []):
        if season.get("seasonNumber") == season_number:
            season["monitored"] = request.monitored
            season_found = True
            break
            
    if not season_found:
        raise HTTPException(status_code=404, detail=f"Season {season_number} not found in series {series_id}")

    updated_series = await sonarr_api_call(instance, f"series/{series_id}", client, method="PUT", json_data=series_data)
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
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Trigger a search for an individual episode without deleting existing files."""

    await sonarr_api_call(
        instance,
        "command",
        client,
        method="POST",
        json_data={"name": "EpisodeSearch", "episodeIds": [episode_id]},
    )

    return {"message": f"Triggered search for episode {episode_id}."}


@router.post("/series/{series_id}/fix", response_model=Series, summary="Replace a damaged series", operation_id="fix_sonarr_series")
async def fix_series(
    series_id: int,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Deletes, re-adds, and searches for a series. WARNING: This is a destructive action. For routine quality upgrades, use the '/series/{series_id}/search' endpoint instead."""
    # Get series details to get the title
    try:
        series = await sonarr_api_call(instance, f"series/{series_id}", client)
        title_to_add = series["title"]
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Series with ID {series_id} not found.")
        raise e

    # Delete the series
    await delete_series(series_id, deleteFiles=True, addImportExclusion=False, instance=instance, client=client)

    # Re-add the series by title
    added_series = await add_series_by_title_sonarr(title_to_add, instance, client)
    return added_series


@router.post("/series/{series_id}/season/{season_number}/search", status_code=200, summary="Trigger a search for an entire season", operation_id="season_search")
async def search_season(
    series_id: int,
    season_number: int,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Triggers a search for all episodes within a season."""
    await sonarr_api_call(
        instance,
        "command",
        client,
        method="POST",
        json_data={"name": "SeasonSearch", "seriesId": series_id, "seasonNumber": season_number},
    )
    return {"message": f"Triggered search for season {season_number} of series {series_id}."}


@router.post("/series/{series_id}/search", status_code=200, summary="Trigger a search for an entire series", operation_id="series_search")
async def search_series(
    series_id: int,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client),
):
    """Triggers a search for all episodes of a series."""
    await sonarr_api_call(
        instance,
        "command",
        client,
        method="POST",
        json_data={"name": "SeriesSearch", "seriesId": series_id},
    )
    return {"message": f"Triggered search for series {series_id}."}


@router.delete("/series/{series_id}", status_code=200, summary="Delete a series from Sonarr", operation_id="delete_sonarr_series")
async def delete_series(
    series_id: int,
    deleteFiles: bool = True,
    addImportExclusion: bool = False,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client)
):
    """Deletes a whole series."""
    params = {
        "deleteFiles": str(deleteFiles).lower(),
        "addImportListExclusion": str(addImportExclusion).lower()
    }
    await sonarr_api_call(instance, f"series/{series_id}", client, method="DELETE", params=params)
    return {"message": f"Series with ID {series_id} has been deleted."}

@router.delete("/series/{series_id}/episodes", status_code=200, summary="Delete a specific episode file from Sonarr", operation_id="delete_sonarr_episode")
async def delete_episode(
    series_id: int,
    season_number: int,
    episode_number: int,
    instance: dict = Depends(get_sonarr_instance),
    client: httpx.AsyncClient = Depends(get_http_client)
):
    """Deletes a specific episode file."""
    # Find the episode_id
    episodes = await sonarr_api_call(instance, "episode", client, params={"seriesId": series_id})
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
        await sonarr_api_call(instance, f"episodefile/{episode_file_id}", client, method="DELETE")
        return {"message": f"Successfully deleted file for episode S{season_number:02d}E{episode_number:02d}."}
    else:
        raise HTTPException(status_code=404, detail="Episode file ID not found.")
