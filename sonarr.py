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
@router.post("/{series_id}/search", summary="Trigger manual search for all missing episodes in a series")
async def search_series(series_id: int, instance: dict = Depends(get_sonarr_instance)):
    """
    Triggers a manual search for missing episodes in the specified series.

    AI GUIDANCE:
    - Use only if the series already exists in Sonarr and is missing episodes/files.
    - To add a new series, use the /add endpoint instead.
    - Never attempt a manual search for series not in the library.
    """
    command_payload = {"name": "SeriesSearch", "seriesId": series_id}
    await api_call(instance, "command", method="POST", json_data=command_payload)
    return {"message": f"Search triggered for missing episodes in series ID {series_id}."}

@router.post("/series/{series_id}/episode/{episode_id}/search", summary="Trigger manual search for a specific episode")
async def search_episode(
    series_id: int,
    episode_id: int,
    instance: dict = Depends(get_sonarr_instance),
):
    """
    Triggers a manual search for a single episode in Sonarr by episode ID.

    AI GUIDANCE:
    - Use this endpoint if you want to download a specific missing or corrupted episode, e.g., "download S5E3 of King of Queens".
    - You must provide the series_id and episode_id (not season/episode numbers).
    - To search for all missing episodes, use the /{series_id}/search endpoint instead.
    - Never attempt a manual episode search for a series or episode not present in the library.
    """
    command_payload = {"name": "EpisodeSearch", "episodeIds": [episode_id]}
    await api_call(instance, "command", method="POST", json_data=command_payload)
    return {"message": f"Search triggered for episode ID {episode_id} in series {series_id}."}


@router.post("/series/{series_id}/fix", summary="Fix entire series: delete, blocklist, and re-add series")
async def fix_series(
    series_id: int,
    addImportExclusion: bool = True,
    instance: dict = Depends(get_sonarr_instance),
):
    """
    Fixes an entire series: deletes the series (and all files), blocklists them, then re-adds it and triggers a new download for all episodes.

    AI GUIDANCE:
    - Use ONLY if multiple episodes in the show are corrupted, missing, or cannot be fixed by per-episode/season fix.
    - When fixing a corrupted or unwanted media file, always set `addImportExclusion` to `true` in the delete call.
    - This ensures Sonarr will not attempt to re-import the same file and will fetch a new release.
    - THIS WILL REMOVE ALL EXISTING FILES AND METADATA FOR THE SERIES!
    """
    # Lookup and collect all info
    series = await api_call(instance, f"series/{series_id}")
    if not series:
        raise HTTPException(status_code=404, detail="Series not found in Sonarr")
    tvdb_id = series.get("tvdbId")
    title = series.get("title")
    quality_profile_id = series.get("qualityProfileId")
    language_profile_id = series.get("languageProfileId")
    root_folder_path = series.get("rootFolderPath")
    seasons = series.get("seasons", [])
    if not all([tvdb_id, quality_profile_id, language_profile_id, root_folder_path]):
        raise HTTPException(status_code=400, detail="Missing necessary data to re-add series")

    # Delete series (and files)
    await api_call(instance, f"series/{series_id}", method="DELETE", params={
        "deleteFiles": "true",
        "addImportExclusion": str(addImportExclusion).lower()
    })

    # Re-add
    add_payload = {
        "tvdbId": tvdb_id,
        "title": title,
        "qualityProfileId": quality_profile_id,
        "languageProfileId": language_profile_id,
        "rootFolderPath": root_folder_path,
        "monitored": True,
        "seasons": seasons,
        "addOptions": {"searchForMissingEpisodes": True}
    }
    added_series = await api_call(instance, "series", method="POST", json_data=add_payload)
    return {"message": f"Series '{title}' was deleted, blocklisted, and is being re-downloaded.", "series": added_series}


@router.post("/series/{series_id}/season/{season_number}/fix", summary="Fix an entire season: delete, blocklist, and redownload all episodes")
async def fix_season(
    series_id: int,
    season_number: int,
    addImportExclusion: bool = True,
    instance: dict = Depends(get_sonarr_instance),
):
    """
    Fixes a season: deletes all episode files in a season, blocklists them, then triggers a season-level search/download.

    AI GUIDANCE:
    - Use this if an entire season is corrupted/missing, but the rest of the show is fine.
    - When fixing a corrupted or unwanted media file, always set `addImportExclusion` to `true` in the delete call.
    - This will DELETE ALL FILES for the specified season ONLY, then trigger a re-download for that season.
    """
    # Lookup episodes in season
    series = await api_call(instance, f"series/{series_id}")
    if not series:
        raise HTTPException(status_code=404, detail="Series not found in Sonarr")
    all_episodes = await api_call(instance, f"episode?seriesId={series_id}")
    season_episodes = [ep for ep in all_episodes if ep.get("seasonNumber") == season_number]
    if not season_episodes:
        raise HTTPException(status_code=404, detail=f"No episodes found for season {season_number}.")

    # Delete all episode files in season
    for ep in season_episodes:
        if ep.get("hasFile"):
            await api_call(
                instance,
                f"episodefile/{ep['episodeFileId']}",
                method="DELETE",
                params={"addImportExclusion": str(addImportExclusion).lower()}
            )

    # Trigger season-level search (downloads missing/corrupt files)
    command_payload = {"name": "SeasonSearch", "seriesId": series_id, "seasonNumber": season_number}
    await api_call(instance, "command", method="POST", json_data=command_payload)
    return {"message": f"Season {season_number} of series '{series['title']}' is being re-downloaded."}


@router.post("/series/{series_id}/episode/{episode_id}/fix", summary="Fix a single episode: delete, blocklist, and redownload")
async def fix_episode(
    series_id: int,
    episode_id: int,
    addImportExclusion: bool = True,
    instance: dict = Depends(get_sonarr_instance),
):
    """
    Fixes an episode: deletes the file for a specific episode, blocklists it, then triggers an episode-level search/download.

    AI GUIDANCE:
    - Use this for a single corrupted/missing episode in a show.
    - When fixing a corrupted or unwanted media file, always set `addImportExclusion` to `true` in the delete call.
    - This ensures Sonarr will not attempt to re-import the same file and will fetch a new release.
    """
    # Delete episode file if present
    episode = await api_call(instance, f"episode/{episode_id}")
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found in Sonarr")
    if episode.get("hasFile"):
        await api_call(
            instance,
            f"episodefile/{episode['episodeFileId']}",
            method="DELETE",
            params={"addImportExclusion": str(addImportExclusion).lower()}
        )

    # Trigger episode-level search
    command_payload = {"name": "EpisodeSearch", "episodeIds": [episode_id]}
    await api_call(instance, "command", method="POST", json_data=command_payload)
    return {"message": f"Episode '{episode.get('title', '')}' (ID {episode_id}) is being re-downloaded."}

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
