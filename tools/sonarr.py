"""Sonarr MCP tool definitions."""

from typing import Dict, Any
from backends.sonarr_client import SonarrClient


def register_sonarr_tools(server, client: SonarrClient):
    """
    Register all Sonarr tools with the MCP server.

    Args:
        server: McpServerV2 instance
        client: Initialized SonarrClient
    """

    # Series Management
    async def sonarr_list_series(args: Dict[str, Any]):
        """List all series in Sonarr."""
        try:
            series = await client.list_series()
            return {
                "success": True,
                "count": len(series),
                "series": series
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_list_series",
        description="Get all series in Sonarr library",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=sonarr_list_series
    )

    async def sonarr_lookup_series(args: Dict[str, Any]):
        """Search for series by name or TVDB ID."""
        try:
            term = args.get("term")
            if not term:
                return {"success": False, "error": "term parameter is required"}

            results = await client.lookup_series(term)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_lookup_series",
        description="Search for series by name or TVDB ID (use format 'tvdb:12345' for ID lookup)",
        parameters={
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "Search term - series name or 'tvdb:12345' for TVDB ID"
                }
            },
            "required": ["term"]
        },
        handler=sonarr_lookup_series
    )

    async def sonarr_get_series(args: Dict[str, Any]):
        """Get details of a specific series by ID."""
        try:
            series_id = args.get("series_id")
            if series_id is None:
                return {"success": False, "error": "series_id parameter is required"}

            series = await client.get_series(int(series_id))
            return {
                "success": True,
                "series": series
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_series",
        description="Get detailed information about a specific series by Sonarr ID",
        parameters={
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "integer",
                    "description": "Sonarr series ID"
                }
            },
            "required": ["series_id"]
        },
        handler=sonarr_get_series
    )

    async def sonarr_add_series(args: Dict[str, Any]):
        """Add a new series to Sonarr."""
        try:
            # Extract required fields
            tvdb_id = args.get("tvdb_id")
            title = args.get("title")
            quality_profile_id = args.get("quality_profile_id")
            root_folder_path = args.get("root_folder_path")

            if not all([tvdb_id, title, quality_profile_id, root_folder_path]):
                return {
                    "success": False,
                    "error": "Missing required fields: tvdb_id, title, quality_profile_id, root_folder_path"
                }

            # Build series data
            data = {
                "tvdbId": int(tvdb_id),
                "title": title,
                "qualityProfileId": int(quality_profile_id),
                "rootFolderPath": root_folder_path,
                "monitored": args.get("monitored", True),
                "seasonFolder": args.get("season_folder", True),
                "addOptions": {
                    "searchForMissingEpisodes": args.get("search_missing", False)
                }
            }

            # Optional fields
            if "language_profile_id" in args:
                data["languageProfileId"] = int(args["language_profile_id"])
            if "tags" in args:
                data["tags"] = args["tags"]

            series = await client.add_series(data)
            return {
                "success": True,
                "series": series
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_add_series",
        description="Add a new series to Sonarr. Use sonarr_lookup_series first to get tvdb_id and series info.",
        parameters={
            "type": "object",
            "properties": {
                "tvdb_id": {
                    "type": "integer",
                    "description": "TVDB ID of the series"
                },
                "title": {
                    "type": "string",
                    "description": "Series title"
                },
                "quality_profile_id": {
                    "type": "integer",
                    "description": "Quality profile ID (get from sonarr_get_quality_profiles)"
                },
                "root_folder_path": {
                    "type": "string",
                    "description": "Root folder path (get from sonarr_get_root_folders)"
                },
                "monitored": {
                    "type": "boolean",
                    "description": "Whether to monitor the series (default: true)"
                },
                "season_folder": {
                    "type": "boolean",
                    "description": "Use season folders (default: true)"
                },
                "search_missing": {
                    "type": "boolean",
                    "description": "Search for missing episodes after adding (default: false)"
                },
                "language_profile_id": {
                    "type": "integer",
                    "description": "Language profile ID (optional)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Tag IDs (optional)"
                }
            },
            "required": ["tvdb_id", "title", "quality_profile_id", "root_folder_path"]
        },
        handler=sonarr_add_series
    )

    # Episode Management
    async def sonarr_get_episodes(args: Dict[str, Any]):
        """Get all episodes for a series."""
        try:
            series_id = args.get("series_id")
            if series_id is None:
                return {"success": False, "error": "series_id parameter is required"}

            episodes = await client.get_episodes(int(series_id))
            return {
                "success": True,
                "count": len(episodes),
                "episodes": episodes
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_episodes",
        description="Get all episodes for a specific series",
        parameters={
            "type": "object",
            "properties": {
                "series_id": {
                    "type": "integer",
                    "description": "Sonarr series ID"
                }
            },
            "required": ["series_id"]
        },
        handler=sonarr_get_episodes
    )

    async def sonarr_get_episode(args: Dict[str, Any]):
        """Get details of a specific episode."""
        try:
            episode_id = args.get("episode_id")
            if episode_id is None:
                return {"success": False, "error": "episode_id parameter is required"}

            episode = await client.get_episode(int(episode_id))
            return {
                "success": True,
                "episode": episode
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_episode",
        description="Get detailed information about a specific episode by episode ID",
        parameters={
            "type": "object",
            "properties": {
                "episode_id": {
                    "type": "integer",
                    "description": "Sonarr episode ID"
                }
            },
            "required": ["episode_id"]
        },
        handler=sonarr_get_episode
    )

    # Release Management
    async def sonarr_get_releases(args: Dict[str, Any]):
        """Get available releases for an episode."""
        try:
            episode_id = args.get("episode_id")
            if episode_id is None:
                return {"success": False, "error": "episode_id parameter is required"}

            releases = await client.get_releases(int(episode_id))
            return {
                "success": True,
                "count": len(releases),
                "releases": releases
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_releases",
        description="Get available releases/torrents for an episode from indexers",
        parameters={
            "type": "object",
            "properties": {
                "episode_id": {
                    "type": "integer",
                    "description": "Sonarr episode ID"
                }
            },
            "required": ["episode_id"]
        },
        handler=sonarr_get_releases
    )

    async def sonarr_grab_release(args: Dict[str, Any]):
        """Grab a release and add to download queue."""
        try:
            guid = args.get("guid")
            indexer_id = args.get("indexer_id")

            if not guid or indexer_id is None:
                return {"success": False, "error": "guid and indexer_id are required"}

            result = await client.grab_release(guid, int(indexer_id))
            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_grab_release",
        description="Grab a release and add it to the download queue. Use sonarr_get_releases first to get guid and indexer_id.",
        parameters={
            "type": "object",
            "properties": {
                "guid": {
                    "type": "string",
                    "description": "Release GUID from sonarr_get_releases"
                },
                "indexer_id": {
                    "type": "integer",
                    "description": "Indexer ID from sonarr_get_releases"
                }
            },
            "required": ["guid", "indexer_id"]
        },
        handler=sonarr_grab_release
    )

    # Queue Management
    async def sonarr_get_queue(args: Dict[str, Any]):
        """Get current download queue."""
        try:
            page = args.get("page", 1)
            page_size = args.get("page_size", 20)

            queue = await client.get_queue(
                page=int(page),
                page_size=int(page_size)
            )
            return {
                "success": True,
                "queue": queue
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_queue",
        description="Get current download queue with pagination",
        parameters={
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "description": "Items per page (default: 20)"
                }
            },
            "required": []
        },
        handler=sonarr_get_queue
    )

    # History
    async def sonarr_get_history(args: Dict[str, Any]):
        """Get download/import history."""
        try:
            page = args.get("page", 1)
            page_size = args.get("page_size", 20)
            series_id = args.get("series_id")
            episode_id = args.get("episode_id")
            event_type = args.get("event_type")

            history = await client.get_history(
                page=int(page),
                page_size=int(page_size),
                series_id=int(series_id) if series_id is not None else None,
                episode_id=int(episode_id) if episode_id is not None else None,
                event_type=event_type
            )
            return {
                "success": True,
                "history": history
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_history",
        description="Get download and import history with optional filtering",
        parameters={
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "description": "Page number (default: 1)"
                },
                "page_size": {
                    "type": "integer",
                    "description": "Items per page (default: 20)"
                },
                "series_id": {
                    "type": "integer",
                    "description": "Filter by series ID (optional)"
                },
                "episode_id": {
                    "type": "integer",
                    "description": "Filter by episode ID (optional)"
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type: grabbed, downloadFolderImported, etc. (optional)"
                }
            },
            "required": []
        },
        handler=sonarr_get_history
    )

    # Configuration
    async def sonarr_get_quality_profiles(args: Dict[str, Any]):
        """Get all quality profiles."""
        try:
            profiles = await client.get_quality_profiles()
            return {
                "success": True,
                "count": len(profiles),
                "profiles": profiles
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_quality_profiles",
        description="Get all quality profiles configured in Sonarr",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=sonarr_get_quality_profiles
    )

    async def sonarr_get_root_folders(args: Dict[str, Any]):
        """Get all root folders."""
        try:
            folders = await client.get_root_folders()
            return {
                "success": True,
                "count": len(folders),
                "folders": folders
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_root_folders",
        description="Get all root folders configured in Sonarr for storing series",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=sonarr_get_root_folders
    )

    async def sonarr_get_tags(args: Dict[str, Any]):
        """Get all tags."""
        try:
            tags = await client.get_tags()
            return {
                "success": True,
                "count": len(tags),
                "tags": tags
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_get_tags",
        description="Get all tags configured in Sonarr",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=sonarr_get_tags
    )

    # System
    async def sonarr_system_status(args: Dict[str, Any]):
        """Get Sonarr system status."""
        try:
            status = await client.get_system_status()
            return {
                "success": True,
                "status": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="sonarr_system_status",
        description="Get Sonarr system status and version information",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=sonarr_system_status
    )
