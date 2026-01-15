"""Radarr API client."""

from typing import Any, Dict, List, Optional
from .base import BaseArrClient


class RadarrClient(BaseArrClient):
    """Async client for Radarr v3 API."""

    # Movie Management
    async def list_movies(self) -> List[Dict[str, Any]]:
        """
        Get all movies in Radarr.

        Returns:
            List of movie objects
        """
        return await self.get("movie")

    async def lookup_movie(self, term: str) -> List[Dict[str, Any]]:
        """
        Search for movies by title or TMDb ID.

        Args:
            term: Search term (movie title or tmdb:12345)

        Returns:
            List of matching movies from lookup
        """
        return await self.get("movie/lookup", params={"term": term})

    async def get_movie(self, movie_id: int) -> Dict[str, Any]:
        """
        Get details of a specific movie.

        Args:
            movie_id: Radarr movie ID

        Returns:
            Movie object
        """
        return await self.get(f"movie/{movie_id}")

    async def add_movie(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new movie to Radarr.

        Args:
            data: Movie configuration including:
                - tmdbId: TMDb ID
                - title: Movie title
                - qualityProfileId: Quality profile ID
                - rootFolderPath: Root folder path
                - monitored: Whether to monitor the movie
                - addOptions: Add options (searchForMovie, etc.)

        Returns:
            Created movie object
        """
        return await self.post("movie", json_data=data)

    async def update_movie(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing movie.

        Args:
            data: Updated movie object (must include id)

        Returns:
            Updated movie object
        """
        return await self.put("movie", json_data=data)

    async def delete_movie(
        self,
        movie_id: int,
        delete_files: bool = False,
        add_import_exclusion: bool = False
    ) -> None:
        """
        Delete a movie from Radarr.

        Args:
            movie_id: Radarr movie ID
            delete_files: Whether to delete movie files from disk
            add_import_exclusion: Add movie to import exclusion list
        """
        params = {
            "deleteFiles": str(delete_files).lower(),
            "addImportExclusion": str(add_import_exclusion).lower()
        }
        return await self.delete(f"movie/{movie_id}", params=params)

    # Release Management
    async def get_releases(self, movie_id: int) -> List[Dict[str, Any]]:
        """
        Get available releases for a movie.

        Args:
            movie_id: Radarr movie ID

        Returns:
            List of release objects
        """
        return await self.get("release", params={"movieId": movie_id})

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
        include_movie: bool = True
    ) -> Dict[str, Any]:
        """
        Get current download queue.

        Args:
            page: Page number
            page_size: Number of items per page
            include_movie: Include movie details

        Returns:
            Queue object with records, page, pageSize, totalRecords
        """
        params = {
            "page": page,
            "pageSize": page_size,
            "includeMovie": str(include_movie).lower()
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
        movie_id: Optional[int] = None,
        event_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get download/import history.

        Args:
            page: Page number
            page_size: Number of items per page
            movie_id: Filter by movie ID
            event_type: Filter by event type (grabbed, downloadFolderImported, etc.)

        Returns:
            History object with records, page, pageSize, totalRecords
        """
        params = {
            "page": page,
            "pageSize": page_size
        }
        if movie_id is not None:
            params["movieId"] = movie_id
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

    async def get_tags(self) -> List[Dict[str, Any]]:
        """
        Get all tags.

        Returns:
            List of tag objects
        """
        return await self.get("tag")

    # Commands
    async def search_movie(self, movie_id: int) -> Dict[str, Any]:
        """
        Trigger a search for a movie.

        Args:
            movie_id: Radarr movie ID

        Returns:
            Command object
        """
        data = {
            "name": "MoviesSearch",
            "movieIds": [movie_id]
        }
        return await self.post("command", json_data=data)

    async def search_movies(self, movie_ids: List[int]) -> Dict[str, Any]:
        """
        Trigger a search for multiple movies.

        Args:
            movie_ids: List of Radarr movie IDs

        Returns:
            Command object
        """
        data = {
            "name": "MoviesSearch",
            "movieIds": movie_ids
        }
        return await self.post("command", json_data=data)

    async def refresh_movie(self, movie_id: int) -> Dict[str, Any]:
        """
        Refresh movie information from TMDb.

        Args:
            movie_id: Radarr movie ID

        Returns:
            Command object
        """
        data = {
            "name": "RefreshMovie",
            "movieId": movie_id
        }
        return await self.post("command", json_data=data)

    async def rescan_movie(self, movie_id: int) -> Dict[str, Any]:
        """
        Rescan movie folder for new files.

        Args:
            movie_id: Radarr movie ID

        Returns:
            Command object
        """
        data = {
            "name": "RescanMovie",
            "movieId": movie_id
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
        Get Radarr system status.

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

    # Import Lists
    async def get_import_lists(self) -> List[Dict[str, Any]]:
        """
        Get all import lists.

        Returns:
            List of import list objects
        """
        return await self.get("importlist")

    # Exclusions
    async def get_exclusions(self) -> List[Dict[str, Any]]:
        """
        Get all import exclusions.

        Returns:
            List of exclusion objects
        """
        return await self.get("exclusions")

    async def add_exclusion(self, tmdb_id: int, title: str, year: int) -> Dict[str, Any]:
        """
        Add a movie to the exclusion list.

        Args:
            tmdb_id: TMDb ID
            title: Movie title
            year: Release year

        Returns:
            Created exclusion object
        """
        data = {
            "tmdbId": tmdb_id,
            "movieTitle": title,
            "movieYear": year
        }
        return await self.post("exclusions", json_data=data)

    async def delete_exclusion(self, exclusion_id: int) -> None:
        """
        Delete an exclusion.

        Args:
            exclusion_id: Exclusion ID
        """
        return await self.delete(f"exclusions/{exclusion_id}")
