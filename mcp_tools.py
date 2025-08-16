import httpx
import os
from typing import Dict, Any, Optional
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException

from instance_endpoints import get_sonarr_instance, get_radarr_instance
from sonarr import (
    get_episodes, lookup_series, add_series, get_download_queue, 
    get_download_history, delete_from_queue, get_quality_profiles, 
    find_series_with_tags, update_series_properties, delete_series, 
    delete_episode, fix_series, search_series
)
from radarr import (
    lookup_movie, add_movie, get_download_queue as get_radarr_queue, 
    get_download_history as get_radarr_history, delete_from_queue as delete_radarr_queue_item, 
    update_movie, delete_movie, get_quality_profiles as get_radarr_quality_profiles,
    get_root_folders, fix_movie
)
from mcp_server import mcp_server

def create_instance_schema(required: bool = False) -> Dict[str, Any]:
    """Create schema for instance_name parameter with default guidance"""
    return {
        "type": "string",
        "description": "Instance name (use 'default' for the primary instance unless specifically told otherwise)",
        "default": "default"
    }

async def register_sonarr_tools():
    """Register all Sonarr tools with the MCP server"""
    
    # Get series episodes
    mcp_server.register_tool(
        "get_sonarr_episodes",
        "Get all episodes for a TV series. Always use 'default' for instance_name unless user specifies otherwise.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "series_id": {"type": "integer", "description": "The series ID in Sonarr"}
            },
            "required": ["series_id"]
        },
        lambda args, auth: get_episodes(
            get_sonarr_instance(args.get("instance_name", "default")),
            args["series_id"]
        )
    )
    
    # Find series with tags (closest available function)
    mcp_server.register_tool(
        "find_series_with_tags",
        "Find TV series with specific tags in Sonarr library. Use 'default' instance unless specified.",
        {
            "type": "object", 
            "properties": {
                "instance_name": create_instance_schema(),
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tag names to search for"}
            },
            "required": ["tags"]
        },
        lambda args, auth: find_series_with_tags(
            get_sonarr_instance(args.get("instance_name", "default")),
            args["tags"]
        )
    )
    
    # Search for series
    mcp_server.register_tool(
        "search_sonarr_series",
        "Search for TV series by title. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "term": {"type": "string", "description": "Search term for series"}
            },
            "required": ["term"]
        },
        lambda args, auth: search_series(
            get_sonarr_instance(args.get("instance_name", "default")),
            args["term"]
        )
    )
    
    # Lookup series to add
    mcp_server.register_tool(
        "lookup_sonarr_series",
        "Lookup TV series to add to Sonarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "term": {"type": "string", "description": "Search term for series lookup"}
            },
            "required": ["term"]
        },
        lambda args, auth: lookup_series(
            get_sonarr_instance(args.get("instance_name", "default")),
            args["term"]
        )
    )
    
    # Add series
    mcp_server.register_tool(
        "add_sonarr_series", 
        "Add a new TV series to Sonarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "tvdbId": {"type": "integer", "description": "TVDB ID of the series"},
                "title": {"type": "string", "description": "Series title"},
                "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
                "rootFolderPath": {"type": "string", "description": "Root folder path"},
                "monitored": {"type": "boolean", "description": "Whether to monitor the series", "default": True},
                "searchForMissingEpisodes": {"type": "boolean", "description": "Search for missing episodes", "default": False}
            },
            "required": ["tvdbId", "title", "qualityProfileId", "rootFolderPath"]
        },
        lambda args, auth: add_series(
            get_sonarr_instance(args.get("instance_name", "default")),
            args
        )
    )
    
    # Get download queue
    mcp_server.register_tool(
        "get_sonarr_queue",
        "Get Sonarr download queue. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema()
            }
        },
        lambda args, auth: get_download_queue(
            get_sonarr_instance(args.get("instance_name", "default"))
        )
    )
    
    # Get download history
    mcp_server.register_tool(
        "get_sonarr_history",
        "Get Sonarr download history. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "page": {"type": "integer", "description": "Page number", "default": 1},
                "pageSize": {"type": "integer", "description": "Items per page", "default": 20}
            }
        },
        lambda args, auth: get_download_history(
            get_sonarr_instance(args.get("instance_name", "default")),
            args.get("page", 1),
            args.get("pageSize", 20)
        )
    )
    
    # Delete queue item
    mcp_server.register_tool(
        "delete_sonarr_queue_item",
        "Delete item from Sonarr download queue. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "queue_id": {"type": "integer", "description": "Queue item ID to delete"}
            },
            "required": ["queue_id"]
        },
        lambda args, auth: delete_from_queue(
            get_sonarr_instance(args.get("instance_name", "default")),
            args["queue_id"]
        )
    )
    
    # Get quality profiles
    mcp_server.register_tool(
        "get_sonarr_quality_profiles",
        "Get quality profiles for TV shows in Sonarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema()
            }
        },
        lambda args, auth: get_quality_profiles(
            get_sonarr_instance(args.get("instance_name", "default"))
        )
    )

async def register_radarr_tools():
    """Register all Radarr tools with the MCP server"""
    
    # Search for movie (using lookup_movie as closest available)
    mcp_server.register_tool(
        "search_radarr_movie_lookup",
        "Search for movies in external databases. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "term": {"type": "string", "description": "Movie search term"}
            },
            "required": ["term"]
        },
        lambda args, auth: lookup_movie(
            get_radarr_instance(args.get("instance_name", "default")),
            args["term"]
        )
    )
    
    # Lookup movie to add (duplicate removed as it's the same as above)
    
    # Lookup movie to add
    mcp_server.register_tool(
        "lookup_radarr_movie",
        "Lookup movies to add to Radarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "term": {"type": "string", "description": "Search term for movie lookup"}
            },
            "required": ["term"]
        },
        lambda args, auth: lookup_movie(
            get_radarr_instance(args.get("instance_name", "default")),
            args["term"]
        )
    )
    
    # Add movie
    mcp_server.register_tool(
        "add_radarr_movie",
        "Add a new movie to Radarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "tmdbId": {"type": "integer", "description": "TMDB ID of the movie"},
                "title": {"type": "string", "description": "Movie title"},
                "qualityProfileId": {"type": "integer", "description": "Quality profile ID"},
                "rootFolderPath": {"type": "string", "description": "Root folder path"},
                "monitored": {"type": "boolean", "description": "Whether to monitor the movie", "default": True},
                "searchForMovie": {"type": "boolean", "description": "Search for movie after adding", "default": False}
            },
            "required": ["tmdbId", "title", "qualityProfileId", "rootFolderPath"]
        },
        lambda args, auth: add_movie(
            get_radarr_instance(args.get("instance_name", "default")),
            args
        )
    )
    
    # Get download queue
    mcp_server.register_tool(
        "get_radarr_queue",
        "Get Radarr download queue. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema()
            }
        },
        lambda args, auth: get_radarr_queue(
            get_radarr_instance(args.get("instance_name", "default"))
        )
    )
    
    # Get download history
    mcp_server.register_tool(
        "get_radarr_history",
        "Get Radarr download history. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema(),
                "page": {"type": "integer", "description": "Page number", "default": 1},
                "pageSize": {"type": "integer", "description": "Items per page", "default": 20}
            }
        },
        lambda args, auth: get_radarr_history(
            get_radarr_instance(args.get("instance_name", "default")),
            args.get("page", 1),
            args.get("pageSize", 20)
        )
    )
    
    # Get quality profiles
    mcp_server.register_tool(
        "get_radarr_quality_profiles",
        "Get quality profiles for movies in Radarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema()
            }
        },
        lambda args, auth: get_radarr_quality_profiles(
            get_radarr_instance(args.get("instance_name", "default"))
        )
    )
    
    # Get root folders
    mcp_server.register_tool(
        "get_radarr_rootfolders",
        "Get root folders from Radarr. Use 'default' instance unless specified.",
        {
            "type": "object",
            "properties": {
                "instance_name": create_instance_schema()
            }
        },
        lambda args, auth: get_root_folders(
            get_radarr_instance(args.get("instance_name", "default"))
        )
    )

async def register_instance_tools():
    """Register instance management tools"""
    
    async def list_sonarr_instances_handler(args: Dict[str, Any], auth: HTTPAuthorizationCredentials):
        """List all configured Sonarr instances"""
        instances = []
        i = 1
        while True:
            name = os.environ.get(f"SONARR_INSTANCE_{i}_NAME")
            if not name:
                break
            url = os.environ.get(f"SONARR_INSTANCE_{i}_URL")
            if url:
                instances.append({"name": name, "url": url})
            i += 1
        return instances
    
    async def list_radarr_instances_handler(args: Dict[str, Any], auth: HTTPAuthorizationCredentials):
        """List all configured Radarr instances"""
        instances = []
        i = 1
        while True:
            name = os.environ.get(f"RADARR_INSTANCE_{i}_NAME")
            if not name:
                break
            url = os.environ.get(f"RADARR_INSTANCE_{i}_URL")
            if url:
                instances.append({"name": name, "url": url})
            i += 1
        return instances
    
    mcp_server.register_tool(
        "list_sonarr_instances",
        "List all configured Sonarr instances",
        {"type": "object", "properties": {}},
        list_sonarr_instances_handler
    )
    
    mcp_server.register_tool(
        "list_radarr_instances", 
        "List all configured Radarr instances",
        {"type": "object", "properties": {}},
        list_radarr_instances_handler
    )

async def register_all_tools():
    """Register all MCP tools"""
    await register_sonarr_tools()
    await register_radarr_tools()
    await register_instance_tools()