"""Sonarr API client."""

from typing import Any, Dict, List, Optional
from .base import BaseArrClient


class SonarrClient(BaseArrClient):
    """Async client for Sonarr v3 API."""

    # Series Management
    async def list_series(self) -> List[Dict[str, Any]]:
        """
        Get all series in Sonarr.

        Returns:
            List of series objects
        """
        return await self.get("series")

    async def lookup_series(self, term: str) -> List[Dict[str, Any]]:
        """
        Search for series by name or TVDB ID.

        Args:
            term: Search term (series name or tvdb:12345)

        Returns:
            List of matching series from lookup
        """
        return await self.get("series/lookup", params={"term": term})

    async def get_series(self, series_id: int) -> Dict[str, Any]:
        """
        Get details of a specific series.

        Args:
            series_id: Sonarr series ID

        Returns:
            Series object
        """
        return await self.get(f"series/{series_id}")

    async def add_series(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new series to Sonarr.

        Args:
            data: Series configuration including:
                - tvdbId: TVDB ID
                - title: Series title
                - qualityProfileId: Quality profile ID
                - rootFolderPath: Root folder path
                - monitored: Whether to monitor the series
                - seasonFolder: Use season folders
                - addOptions: Add options (searchForMissingEpisodes, etc.)

        Returns:
            Created series object
        """
        return await self.post("series", json_data=data)

    async def update_series(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing series.

        Args:
            data: Updated series object (must include id)

        Returns:
            Updated series object
        """
        return await self.put("series", json_data=data)

    async def delete_series(
        self,
        series_id: int,
        delete_files: bool = False,
        add_import_exclusion: bool = False
    ) -> None:
        """
        Delete a series from Sonarr.

        Args:
            series_id: Sonarr series ID
            delete_files: Whether to delete series files from disk
            add_import_exclusion: Add series to import exclusion list
        """
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportExclusion": str(add_import_exclusion).lower()
        }
        return await self.delete(f"series/{series_id}", params=params)

    # Episode Management
    async def get_episodes(self, series_id: int) -> List[Dict[str, Any]]:
        """
        Get all episodes for a series.

        Args:
            series_id: Sonarr series ID

        Returns:
            List of episode objects
        """
        return await self.get("episode", params={"seriesId": series_id})

    async def get_episode(self, episode_id: int) -> Dict[str, Any]:
        """
        Get details of a specific episode.

        Args:
            episode_id: Sonarr episode ID

        Returns:
            Episode object
        """
        return await self.get(f"episode/{episode_id}")

    async def update_episode(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an episode (e.g., toggle monitoring).

        Args:
            data: Updated episode object (must include id)

        Returns:
            Updated episode object
        """
        return await self.put("episode", json_data=data)

    # Release Management
    async def get_releases(self, episode_id: int) -> List[Dict[str, Any]]:
        """
        Get available releases for an episode.

        Args:
            episode_id: Sonarr episode ID

        Returns:
            List of release objects
        """
        return await self.get("release", params={"episodeId": episode_id})

    async def grab_release(self, guid: str, indexer_id: int) -> Dict[str, Any]:
        """
        Grab a release and add to download queue.

        Args:
            guid: Release GUID
            indexer_id: Indexer ID

        Returns:
            Release grab result
        """
        data = {
            "guid": guid,
            "indexerId": indexer_id
        }
        return await self.post("release", json_data=data)

    # Queue Management
    async def get_queue(
        self,
        page: int = 1,
        page_size: int = 20,
        include_series: bool = True,
        include_episode: bool = True
    ) -> Dict[str, Any]:
        """
        Get current download queue.

        Args:
            page: Page number
            page_size: Number of items per page
            include_series: Include series details
            include_episode: Include episode details

        Returns:
            Queue object with records, page, pageSize, totalRecords
        """
        params = {
            "page": page,
            "pageSize": page_size,
            "includeSeries": str(include_series).lower(),
            "includeEpisode": str(include_episode).lower()
        }
        return await self.get("queue", params=params)

    async def delete_queue_item(
        self,
        queue_id: int,
        remove_from_client: bool = True,
        blocklist: bool = False
    ) -> None:
        """
        Delete an item from the queue.

        Args:
            queue_id: Queue item ID
            remove_from_client: Remove from download client
            blocklist: Add to blocklist
        """
        params = {
            "removeFromClient": str(remove_from_client).lower(),
            "blocklist": str(blocklist).lower()
        }
        return await self.delete(f"queue/{queue_id}", params=params)

    # History
    async def get_history(
        self,
        page: int = 1,
        page_size: int = 20,
        series_id: Optional[int] = None,
        episode_id: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get download/import history.

        Args:
            page: Page number
            page_size: Number of items per page
            series_id: Filter by series ID
            episode_id: Filter by episode ID
            event_type: Filter by event type (grabbed, downloadFolderImported, etc.)

        Returns:
            History object with records, page, pageSize, totalRecords
        """
        params = {
            "page": page,
            "pageSize": page_size
        }
        if series_id is not None:
            params["seriesId"] = series_id
        if episode_id is not None:
            params["episodeId"] = episode_id
        if event_type is not None:
            params["eventType"] = event_type

        return await self.get("history", params=params)

    # Configuration
    async def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """
        Get all quality profiles.

        Returns:
            List of quality profile objects
        """
        return await self.get("qualityprofile")

    async def get_quality_profile(self, profile_id: int) -> Dict[str, Any]:
        """
        Get a specific quality profile.

        Args:
            profile_id: Quality profile ID

        Returns:
            Quality profile object
        """
        return await self.get(f"qualityprofile/{profile_id}")

    async def get_root_folders(self) -> List[Dict[str, Any]]:
        """
        Get all root folders.

        Returns:
            List of root folder objects
        """
        return await self.get("rootfolder")

    async def get_language_profiles(self) -> List[Dict[str, Any]]:
        """
        Get all language profiles.

        Returns:
            List of language profile objects
        """
        return await self.get("languageprofile")

    async def get_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags.

        Returns:
            List of tag objects
        """
        return await self.get("tag")

    # Commands
    async def search_series(self, series_id: int) -> Dict[str, Any]:
        """
        Trigger a search for all episodes in a series.

        Args:
            series_id: Sonarr series ID

        Returns:
            Command object
        """
        data = {
            "name": "SeriesSearch",
            "seriesId": series_id
        }
        return await self.post("command", json_data=data)

    async def search_episode(self, episode_ids: List[int]) -> Dict[str, Any]:
        """
        Trigger a search for specific episodes.

        Args:
            episode_ids: List of episode IDs to search

        Returns:
            Command object
        """
        data = {
            "name": "EpisodeSearch",
            "episodeIds": episode_ids
        }
        return await self.post("command", json_data=data)

    async def search_season(self, series_id: int, season_number: int) -> Dict[str, Any]:
        """
        Trigger a search for all episodes in a season.

        Args:
            series_id: Sonarr series ID
            season_number: Season number

        Returns:
            Command object
        """
        data = {
            "name": "SeasonSearch",
            "seriesId": series_id,
            "seasonNumber": season_number
        }
        return await self.post("command", json_data=data)

    async def refresh_series(self, series_id: int) -> Dict[str, Any]:
        """
        Refresh series information from TVDB.

        Args:
            series_id: Sonarr series ID

        Returns:
            Command object
        """
        data = {
            "name": "RefreshSeries",
            "seriesId": series_id
        }
        return await self.post("command", json_data=data)

    async def rescan_series(self, series_id: int) -> Dict[str, Any]:
        """
        Rescan series folder for new files.

        Args:
            series_id: Sonarr series ID

        Returns:
            Command object
        """
        data = {
            "name": "RescanSeries",
            "seriesId": series_id
        }
        return await self.post("command", json_data=data)

    async def get_command(self, command_id: int) -> Dict[str, Any]:
        """
        Get status of a command.

        Args:
            command_id: Command ID

        Returns:
            Command object
        """
        return await self.get(f"command/{command_id}")

    # System
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get Sonarr system status.

        Returns:
            System status object
        """
        return await self.get("system/status")

    async def get_disk_space(self) -> List[Dict[str, Any]]:
        """
        Get disk space information.

        Returns:
            List of disk space objects
        """
        return await self.get("diskspace")
