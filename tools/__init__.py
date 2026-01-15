"""
Toolarr MCP Tools

This package contains MCP tool definitions that wrap the Sonarr and Radarr
backend clients, providing a clean interface for the MCP server.
"""

from .sonarr import register_sonarr_tools
from .radarr import register_radarr_tools

__all__ = ["register_sonarr_tools", "register_radarr_tools"]
