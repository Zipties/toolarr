"""
This module contains the shared client logic for communicating with 
Sonarr and Radarr APIs, and a base router for common endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
import httpx

# --- Generic API Client ---

async def api_call(instance: dict, endpoint: str, method: str = "GET", params: dict = None, json_data: dict = None):
    """
    Makes a generic API call to a media service instance (Sonarr/Radarr).
    
    Args:
        instance: A dictionary containing the 'url' and 'api_key' for the instance.
        endpoint: The API endpoint to call (e.g., 'movie', 'series/lookup').
        method: The HTTP method to use ('GET', 'POST', 'PUT', 'DELETE').
        params: A dictionary of query parameters.
        json_data: A dictionary of data to send as a JSON body.

    Returns:
        The JSON response from the API.
        
    Raises:
        HTTPException: If the API call fails.
    """
    headers = {"X-Api-Key": instance["api_key"], "Content-Type": "application/json"}
    url = f"{instance['url']}/api/v3/{endpoint}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.request(method, url, headers=headers, params=params, json=json_data)
            response.raise_for_status()
            
            # Handle successful empty responses (e.g., from DELETE)
            if response.status_code == 204 or not response.text:
                return None
                
            return response.json()
        except httpx.HTTPStatusError as e:
            service_name = "Sonarr" if "sonarr" in instance['url'] else "Radarr"
            raise HTTPException(status_code=e.response.status_code, detail=f"{service_name} API error: {e.response.text}")
        except Exception as e:
            service_name = "Sonarr" if "sonarr" in instance['url'] else "Radarr"
            raise HTTPException(status_code=500, detail=f"Error communicating with {service_name}: {str(e)}")

# --- Base Router for Common Endpoints ---

class BaseMediaRouter(APIRouter):
    """
    A base router class that provides common endpoints for both Sonarr and Radarr.
    It accepts a dependency to inject the correct instance configuration.
    """
    def __init__(self, dependency, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = kwargs.get("tags")[0]

        # Define handlers within __init__ to correctly capture the dependency
        async def get_download_queue(instance: dict = Depends(dependency)):
            """Gets the list of items currently being downloaded or waiting to be downloaded."""
            queue_data = await api_call(instance, "queue")
            return queue_data.get("records", [])

        async def get_download_history(instance: dict = Depends(dependency)):
            """Gets the history of recently grabbed and imported downloads."""
            history_data = await api_call(instance, "history")
            return history_data.get("records", [])

        async def delete_from_queue(queue_id: int, removeFromClient: bool = True, instance: dict = Depends(dependency)):
            """Deletes an item from the download queue."""
            params = {"removeFromClient": str(removeFromClient).lower()}
            await api_call(instance, f"queue/{queue_id}", method="DELETE", params=params)
            return

        async def get_quality_profiles(instance: dict = Depends(dependency)):
            """Retrieves all quality profiles."""
            return await api_call(instance, "qualityprofile")

        async def get_root_folders(instance: dict = Depends(dependency)):
            """Get all configured root folders."""
            return await api_call(instance, "rootfolder")
            
        async def get_tags(instance: dict = Depends(dependency)):
            """Get all tags configured in the instance."""
            return await api_call(instance, "tag")

        async def create_tag(label: str, instance: dict = Depends(dependency)):
            """Create a new tag."""
            return await api_call(instance, "tag", method="POST", json_data={"label": label})

        async def delete_tag(tag_id: int, instance: dict = Depends(dependency)):
            """Delete a tag by its ID."""
            await api_call(instance, f"tag/{tag_id}", method="DELETE")
            return

        # Add common routes with unique operation_ids and correct dependencies
        self.add_api_route("/queue", get_download_queue, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download queue", operation_id=f"{self.service_name}_get_queue")
        self.add_api_route("/history", get_download_history, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download history", operation_id=f"{self.service_name}_get_history")
        self.add_api_route("/queue/{queue_id}", delete_from_queue, methods=["DELETE"], status_code=204, summary=f"Delete item from {self.service_name.capitalize()} queue", operation_id=f"{self.service_name}_delete_queue_item")
        self.add_api_route("/qualityprofiles", get_quality_profiles, methods=["GET"], summary=f"Get quality profiles from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_quality_profiles")
        self.add_api_route("/rootfolders", get_root_folders, methods=["GET"], summary=f"Get root folders from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_root_folders")
        self.add_api_route("/tags", get_tags, methods=["GET"], summary=f"Get all tags from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_tags")
        self.add_api_route("/tags", create_tag, methods=["POST"], summary=f"Create a new tag in {self.service_name.capitalize()}", operation_id=f"{self.service_name}_create_tag")
        self.add_api_route("/tags/{tag_id}", delete_tag, methods=["DELETE"], status_code=204, summary=f"Delete a tag from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_delete_tag")