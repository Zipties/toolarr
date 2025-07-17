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
