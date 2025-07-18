"""
This module contains the shared client logic for communicating with 
Sonarr and Radarr APIs, and a base router for common endpoints.
"""
from typing import List
from fastapi import APIRouter, HTTPException
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
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_name = kwargs.get("tags")[0] # e.g., "sonarr" or "radarr"
        
        # Add common routes with unique operation_ids
        self.add_api_route("/queue", self.get_download_queue, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download queue", operation_id=f"{self.service_name}_get_queue")
        self.add_api_route("/history", self.get_download_history, methods=["GET"], summary=f"Get {self.service_name.capitalize()} download history", operation_id=f"{self.service_name}_get_history")
        self.add_api_route("/queue/{queue_id}", self.delete_from_queue, methods=["DELETE"], status_code=204, summary=f"Delete item from {self.service_name.capitalize()} queue", operation_id=f"{self.service_name}_delete_queue_item")
        self.add_api_route("/qualityprofiles", self.get_quality_profiles, methods=["GET"], summary=f"Get quality profiles from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_quality_profiles")
        self.add_api_route("/rootfolders", self.get_root_folders, methods=["GET"], summary=f"Get root folders from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_root_folders")
        self.add_api_route("/tags", self.get_tags, methods=["GET"], summary=f"Get all tags from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_get_tags")
        self.add_api_route("/tags", self.create_tag, methods=["POST"], summary=f"Create a new tag in {self.service_name.capitalize()}", operation_id=f"{self.service_name}_create_tag")
        self.add_api_route("/tags/{tag_id}", self.delete_tag, methods=["DELETE"], status_code=204, summary=f"Delete a tag from {self.service_name.capitalize()}", operation_id=f"{self.service_name}_delete_tag")

    async def get_download_queue(self, instance: dict):
        """Gets the list of items currently being downloaded or waiting to be downloaded."""
        queue_data = await api_call(instance, "queue")
        return queue_data.get("records", [])

    async def get_download_history(self, instance: dict):
        """Gets the history of recently grabbed and imported downloads."""
        history_data = await api_call(instance, "history")
        return history_data.get("records", [])

    async def delete_from_queue(self, queue_id: int, removeFromClient: bool = True, instance: dict = None):
        """Deletes an item from the download queue."""
        params = {"removeFromClient": str(removeFromClient).lower()}
        await api_call(instance, f"queue/{queue_id}", method="DELETE", params=params)
        return

    async def get_quality_profiles(self, instance: dict):
        """Retrieves all quality profiles."""
        return await api_call(instance, "qualityprofile")

    async def get_root_folders(self, instance: dict):
        """Get all configured root folders."""
        return await api_call(instance, "rootfolder")
        
    async def get_tags(self, instance: dict):
        """Get all tags configured in the instance."""
        return await api_call(instance, "tag")

    async def create_tag(self, label: str, instance: dict):
        """Create a new tag."""
        return await api_call(instance, "tag", method="POST", json_data={"label": label})

    async def delete_tag(self, tag_id: int, instance: dict):
        """Delete a tag by its ID."""
        await api_call(instance, f"tag/{tag_id}", method="DELETE")
        return