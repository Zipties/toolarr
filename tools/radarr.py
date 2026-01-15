"""Radarr MCP tool definitions."""

from typing import Dict, Any
from backends.radarr_client import RadarrClient


def register_radarr_tools(server, client: RadarrClient):
    """
    Register all Radarr tools with the MCP server.

    Args:
        server: McpServerV2 instance
        client: Initialized RadarrClient
    """

    # Movie Management
    async def radarr_list_movies(args: Dict[str, Any]):
        """List all movies in Radarr."""
        try:
            movies = await client.list_movies()
            return {
                "success": True,
                "count": len(movies),
                "movies": movies
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_list_movies",
        description="Get all movies in Radarr library",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_list_movies
    )

    async def radarr_lookup_movie(args: Dict[str, Any]):
        """Search for movies by title or TMDb ID."""
        try:
            term = args.get("term")
            if not term:
                return {"success": False, "error": "term parameter is required"}

            results = await client.lookup_movie(term)
            return {
                "success": True,
                "count": len(results),
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_lookup_movie",
        description="Search for movies by title or TMDb ID (use format 'tmdb:12345' for ID lookup)",
        parameters={
            "type": "object",
            "properties": {
                "term": {
                    "type": "string",
                    "description": "Search term - movie title or 'tmdb:12345' for TMDb ID"
                }
            },
            "required": ["term"]
        },
        handler=radarr_lookup_movie
    )

    async def radarr_get_movie(args: Dict[str, Any]):
        """Get details of a specific movie by ID."""
        try:
            movie_id = args.get("movie_id")
            if movie_id is None:
                return {"success": False, "error": "movie_id parameter is required"}

            movie = await client.get_movie(int(movie_id))
            return {
                "success": True,
                "movie": movie
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_get_movie",
        description="Get detailed information about a specific movie by Radarr ID",
        parameters={
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "Radarr movie ID"
                }
            },
            "required": ["movie_id"]
        },
        handler=radarr_get_movie
    )

    async def radarr_add_movie(args: Dict[str, Any]):
        """Add a new movie to Radarr."""
        try:
            # Extract required fields
            tmdb_id = args.get("tmdb_id")
            title = args.get("title")
            quality_profile_id = args.get("quality_profile_id")
            root_folder_path = args.get("root_folder_path")

            if not all([tmdb_id, title, quality_profile_id, root_folder_path]):
                return {
                    "success": False,
                    "error": "Missing required fields: tmdb_id, title, quality_profile_id, root_folder_path"
                }

            # Build movie data
            data = {
                "tmdbId": int(tmdb_id),
                "title": title,
                "qualityProfileId": int(quality_profile_id),
                "rootFolderPath": root_folder_path,
                "monitored": args.get("monitored", True),
                "addOptions": {
                    "searchForMovie": args.get("search_for_movie", False)
                }
            }

            # Optional fields
            if "year" in args:
                data["year"] = int(args["year"])
            if "tags" in args:
                data["tags"] = args["tags"]
            if "minimum_availability" in args:
                data["minimumAvailability"] = args["minimum_availability"]

            movie = await client.add_movie(data)
            return {
                "success": True,
                "movie": movie
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_add_movie",
        description="Add a new movie to Radarr. Use radarr_lookup_movie first to get tmdb_id and movie info.",
        parameters={
            "type": "object",
            "properties": {
                "tmdb_id": {
                    "type": "integer",
                    "description": "TMDb ID of the movie"
                },
                "title": {
                    "type": "string",
                    "description": "Movie title"
                },
                "quality_profile_id": {
                    "type": "integer",
                    "description": "Quality profile ID (get from radarr_get_quality_profiles)"
                },
                "root_folder_path": {
                    "type": "string",
                    "description": "Root folder path (get from radarr_get_root_folders)"
                },
                "monitored": {
                    "type": "boolean",
                    "description": "Whether to monitor the movie (default: true)"
                },
                "search_for_movie": {
                    "type": "boolean",
                    "description": "Search for movie after adding (default: false)"
                },
                "year": {
                    "type": "integer",
                    "description": "Release year (optional)"
                },
                "minimum_availability": {
                    "type": "string",
                    "description": "Minimum availability: announced, inCinemas, released (optional)"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Tag IDs (optional)"
                }
            },
            "required": ["tmdb_id", "title", "quality_profile_id", "root_folder_path"]
        },
        handler=radarr_add_movie
    )

    # Release Management
    async def radarr_get_releases(args: Dict[str, Any]):
        """Get available releases for a movie."""
        try:
            movie_id = args.get("movie_id")
            if movie_id is None:
                return {"success": False, "error": "movie_id parameter is required"}

            releases = await client.get_releases(int(movie_id))
            return {
                "success": True,
                "count": len(releases),
                "releases": releases
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_get_releases",
        description="Get available releases/torrents for a movie from indexers",
        parameters={
            "type": "object",
            "properties": {
                "movie_id": {
                    "type": "integer",
                    "description": "Radarr movie ID"
                }
            },
            "required": ["movie_id"]
        },
        handler=radarr_get_releases
    )

    async def radarr_grab_release(args: Dict[str, Any]):
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
        name="radarr_grab_release",
        description="Grab a release and add it to the download queue. Use radarr_get_releases first to get guid and indexer_id.",
        parameters={
            "type": "object",
            "properties": {
                "guid": {
                    "type": "string",
                    "description": "Release GUID from radarr_get_releases"
                },
                "indexer_id": {
                    "type": "integer",
                    "description": "Indexer ID from radarr_get_releases"
                }
            },
            "required": ["guid", "indexer_id"]
        },
        handler=radarr_grab_release
    )

    # Queue Management
    async def radarr_get_queue(args: Dict[str, Any]):
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
        name="radarr_get_queue",
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
        handler=radarr_get_queue
    )

    # History
    async def radarr_get_history(args: Dict[str, Any]):
        """Get download/import history."""
        try:
            page = args.get("page", 1)
            page_size = args.get("page_size", 20)
            movie_id = args.get("movie_id")
            event_type = args.get("event_type")

            history = await client.get_history(
                page=int(page),
                page_size=int(page_size),
                movie_id=int(movie_id) if movie_id is not None else None,
                event_type=event_type
            )
            return {
                "success": True,
                "history": history
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_get_history",
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
                "movie_id": {
                    "type": "integer",
                    "description": "Filter by movie ID (optional)"
                },
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type: grabbed, downloadFolderImported, etc. (optional)"
                }
            },
            "required": []
        },
        handler=radarr_get_history
    )

    # Configuration
    async def radarr_get_quality_profiles(args: Dict[str, Any]):
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
        name="radarr_get_quality_profiles",
        description="Get all quality profiles configured in Radarr",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_get_quality_profiles
    )

    async def radarr_get_root_folders(args: Dict[str, Any]):
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
        name="radarr_get_root_folders",
        description="Get all root folders configured in Radarr for storing movies",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_get_root_folders
    )

    async def radarr_get_tags(args: Dict[str, Any]):
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
        name="radarr_get_tags",
        description="Get all tags configured in Radarr",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_get_tags
    )

    # Exclusions
    async def radarr_get_exclusions(args: Dict[str, Any]):
        """Get all import exclusions."""
        try:
            exclusions = await client.get_exclusions()
            return {
                "success": True,
                "count": len(exclusions),
                "exclusions": exclusions
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_get_exclusions",
        description="Get all movies in the import exclusion list",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_get_exclusions
    )

    # Import Lists
    async def radarr_get_import_lists(args: Dict[str, Any]):
        """Get all import lists."""
        try:
            lists = await client.get_import_lists()
            return {
                "success": True,
                "count": len(lists),
                "lists": lists
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_get_import_lists",
        description="Get all import lists configured in Radarr",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_get_import_lists
    )

    # System
    async def radarr_system_status(args: Dict[str, Any]):
        """Get Radarr system status."""
        try:
            status = await client.get_system_status()
            return {
                "success": True,
                "status": status
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    server.register_tool(
        name="radarr_system_status",
        description="Get Radarr system status and version information",
        parameters={
            "type": "object",
            "properties": {},
            "required": []
        },
        handler=radarr_system_status
    )
