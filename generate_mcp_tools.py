#!/usr/bin/env python3
"""
Auto-generate MCP tools from OpenAPI specification
Run this script whenever the API changes to regenerate mcp_tools_generated.py
"""

import json
import re
from typing import Dict, Any, List

def openapi_type_to_json_schema(openapi_type: Dict[str, Any]) -> Dict[str, Any]:
    """Convert OpenAPI parameter type to JSON Schema"""
    if openapi_type.get("type") == "array":
        return {
            "type": "array",
            "items": openapi_type.get("items", {"type": "string"}),
            "description": openapi_type.get("description", "")
        }
    elif openapi_type.get("type") == "integer":
        return {
            "type": "integer", 
            "description": openapi_type.get("description", "")
        }
    elif openapi_type.get("type") == "boolean":
        return {
            "type": "boolean",
            "description": openapi_type.get("description", ""),
            "default": openapi_type.get("default", False)
        }
    else:
        return {
            "type": "string",
            "description": openapi_type.get("description", "")
        }

def extract_instance_name_from_path(path: str) -> bool:
    """Check if path contains instance_name parameter"""
    return "{instance_name}" in path

def get_function_name_from_operation_id(operation_id: str, path: str) -> str:
    """Map operation ID to actual function name in sonarr.py/radarr.py"""
    
    # Direct mappings for known functions
    function_mapping = {
        # Sonarr functions
        "get_sonarr_episodes": "get_episodes",
        "find_series_in_library_sonarr__instance_name__library_get": "find_series_with_tags",
        "search_series_sonarr__instance_name__search_get": "search_series", 
        "lookup_series_sonarr__instance_name__lookup_get": "lookup_series",
        "add_series_sonarr__instance_name__series_post": "add_series",
        "get_download_queue_sonarr__instance_name__queue_get": "get_download_queue",
        "get_download_history_sonarr__instance_name__history_get": "get_download_history", 
        "delete_sonarr_queue_item": "delete_from_queue",
        "get_quality_profiles_sonarr__instance_name__qualityprofiles_get": "get_quality_profiles",
        "series_with_tags": "find_series_with_tags",
        "update_sonarr_series_properties": "update_series_properties",
        "delete_sonarr_series_or_episode": "delete_series",
        "fix_sonarr_release": "fix_series",
        
        # Radarr functions  
        "find_movie_in_library_radarr__instance_name__library_get": "lookup_movie",
        "search_movie_radarr__instance_name__search_get": "lookup_movie",
        "lookup_movie_radarr__instance_name__lookup_get": "lookup_movie", 
        "add_movie_radarr__instance_name__movie_post": "add_movie",
        "get_download_queue_radarr__instance_name__queue_get": "get_download_queue",
        "get_download_history_radarr__instance_name__history_get": "get_download_history",
        "delete_radarr_queue_item": "delete_from_queue", 
        "update_radarr_movie_properties": "update_movie",
        "delete_radarr_movie": "delete_movie",
        "get_quality_profiles_radarr__instance_name__qualityprofiles_get": "get_quality_profiles",
        "get_radarr_rootfolders": "get_root_folders",
        "fix_radarr_movie": "fix_movie",
        
        # Instance management
        "list_sonarr_instances_instances_sonarr_get": "list_sonarr_instances_handler",
        "list_radarr_instances_instances_radarr_get": "list_radarr_instances_handler"
    }
    
    return function_mapping.get(operation_id, operation_id)

def create_tool_definition(path: str, method: str, endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create MCP tool definition from OpenAPI endpoint"""
    
    operation_id = endpoint_info.get("operationId", f"{method}_{path.replace('/', '_')}")
    summary = endpoint_info.get("summary", "No description")
    description = endpoint_info.get("description", summary)
    
    # Clean description for safe string usage (escape quotes, newlines and limit length)
    description = description.replace('"', '\\"').replace("'", "\\'").replace('\n', ' ').replace('\r', ' ')
    # Remove multiple spaces
    description = ' '.join(description.split())
    if len(description) > 200:
        description = description[:200] + "..."
    
    # Determine service type
    service_type = "sonarr" if "/sonarr/" in path else "radarr" if "/radarr/" in path else "instance"
    
    # Create tool name (clean operation ID)
    tool_name = operation_id
    if "__" in tool_name:
        # Clean up auto-generated operation IDs
        parts = tool_name.split("__")
        if len(parts) > 1:
            tool_name = parts[0]
    
    # Get parameters
    parameters = endpoint_info.get("parameters", [])
    path_params = [p for p in parameters if p.get("in") == "path"]
    query_params = [p for p in parameters if p.get("in") == "query"]
    
    # Build parameter schema
    properties = {}
    required = []
    
    # Add instance_name if path contains it
    if extract_instance_name_from_path(path):
        properties["instance_name"] = {
            "type": "string",
            "description": "Instance name (use 'default' for the primary instance unless specifically told otherwise)",
            "default": "default"
        }
    
    # Add path parameters (except instance_name)
    for param in path_params:
        if param["name"] != "instance_name":
            properties[param["name"]] = openapi_type_to_json_schema(param.get("schema", {"type": "string"}))
            if param.get("required", False):
                required.append(param["name"])
    
    # Add query parameters
    for param in query_params:
        properties[param["name"]] = openapi_type_to_json_schema(param.get("schema", {"type": "string"}))
        if param.get("required", False):
            required.append(param["name"])
    
    # Add request body parameters for POST/PUT
    if method.upper() in ["POST", "PUT"] and "requestBody" in endpoint_info:
        request_body = endpoint_info["requestBody"]
        if "content" in request_body and "application/json" in request_body["content"]:
            schema = request_body["content"]["application/json"].get("schema", {})
            if "properties" in schema:
                for prop_name, prop_schema in schema["properties"].items():
                    properties[prop_name] = openapi_type_to_json_schema(prop_schema)
                    if prop_name in schema.get("required", []):
                        required.append(prop_name)
    
    # Get function name
    function_name = get_function_name_from_operation_id(operation_id, path)
    
    return {
        "tool_name": tool_name,
        "description": f"{description} Use 'default' instance unless specified.",
        "function_name": function_name, 
        "service_type": service_type,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }

def generate_mcp_tools_file(openapi_spec: Dict[str, Any]) -> str:
    """Generate the complete mcp_tools_generated.py file"""
    
    tools = []
    
    # Extract tools from OpenAPI spec
    for path, path_info in openapi_spec.get("paths", {}).items():
        for method, endpoint_info in path_info.items():
            if method.lower() in ["get", "post", "put", "delete"]:
                tool = create_tool_definition(path, method, endpoint_info)
                tools.append(tool)
    
    # Group tools by service type
    sonarr_tools = [t for t in tools if t["service_type"] == "sonarr"]
    radarr_tools = [t for t in tools if t["service_type"] == "radarr"] 
    instance_tools = [t for t in tools if t["service_type"] == "instance"]
    
    # Generate the Python file
    content = '''"""
Auto-generated MCP tools from OpenAPI specification
DO NOT EDIT MANUALLY - This file is generated by generate_mcp_tools.py
"""

import os
from typing import Dict, Any, Optional
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import HTTPException

from instance_endpoints import get_sonarr_instance, get_radarr_instance
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
    
    # Import Sonarr functions
    from sonarr import (
        get_episodes, lookup_series, add_series, get_download_queue, 
        get_download_history, delete_from_queue, get_quality_profiles, 
        find_series_with_tags, update_series_properties, delete_series, 
        delete_episode, fix_series, search_series
    )
    
'''

    # Generate Sonarr tools
    for tool in sonarr_tools:
        content += f'''    # {tool["description"][:60]}...
    mcp_server.register_tool(
        "{tool["tool_name"]}",
        "{tool["description"]}",
        {json.dumps(tool["input_schema"], indent=8)},
        lambda args, auth: {tool["function_name"]}(
            get_sonarr_instance(args.get("instance_name", "default")),
            *[args.get(param) for param in {list(tool["input_schema"]["properties"].keys())} if param != "instance_name"]
        )
    )
    
'''

    content += '''
async def register_radarr_tools():
    """Register all Radarr tools with the MCP server"""
    
    # Import Radarr functions
    from radarr import (
        lookup_movie, add_movie, get_download_queue as get_radarr_queue, 
        get_download_history as get_radarr_history, delete_from_queue as delete_radarr_queue_item, 
        update_movie, delete_movie, get_quality_profiles as get_radarr_quality_profiles,
        get_root_folders, fix_movie
    )
    
'''

    # Generate Radarr tools
    for tool in radarr_tools:
        content += f'''    # {tool["description"][:60]}...
    mcp_server.register_tool(
        "{tool["tool_name"]}",
        "{tool["description"]}",
        {json.dumps(tool["input_schema"], indent=8)},
        lambda args, auth: {tool["function_name"]}(
            get_radarr_instance(args.get("instance_name", "default")),
            *[args.get(param) for param in {list(tool["input_schema"]["properties"].keys())} if param != "instance_name"]
        )
    )
    
'''

    content += '''
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
'''

    return content

def main():
    """Generate MCP tools from OpenAPI spec"""
    print("Generating MCP tools from OpenAPI specification...")
    
    # Load OpenAPI spec
    try:
        with open("openapi-chatgpt.json", "r") as f:
            openapi_spec = json.load(f)
    except FileNotFoundError:
        print("❌ Error: openapi-chatgpt.json not found")
        print("   Run the server first to generate the OpenAPI spec")
        return
    
    # Generate MCP tools file
    content = generate_mcp_tools_file(openapi_spec)
    
    # Write generated file
    with open("mcp_tools_generated.py", "w") as f:
        f.write(content)
    
    print("✅ Generated mcp_tools_generated.py")
    print(f"   Found {len(openapi_spec.get('paths', {}))} API endpoints")
    print("   Update main.py to import from mcp_tools_generated instead of mcp_tools")

if __name__ == "__main__":
    main()