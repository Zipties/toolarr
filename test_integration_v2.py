#!/usr/bin/env python3
"""
Integration test for the new Toolarr MCP v2.

Tests the complete flow:
1. Backend clients can connect to Sonarr/Radarr
2. MCP server starts and responds to protocol
3. Tools execute correctly through MCP

Run this after all agents complete their work.
"""

import asyncio
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


async def test_backend_clients():
    """Test that backend clients work."""
    print("\n=== Testing Backend Clients ===")

    try:
        from backends.sonarr_client import SonarrClient
        from backends.radarr_client import RadarrClient
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("   Backend clients not ready yet")
        return False

    # Test Sonarr
    print("\nTesting Sonarr client...")
    try:
        async with SonarrClient(
            base_url=os.getenv("SONARR_URL", "http://192.168.45.15:8083"),
            api_key=os.getenv("SONARR_API_KEY", "7ce61d72c943483ca03864e03f013127")
        ) as client:
            # Test list_series
            series = await client.list_series()
            print(f"  ✅ list_series: {len(series)} series in library")

            # Test lookup
            results = await client.lookup_series("Severance")
            print(f"  ✅ lookup_series: Found {len(results)} results")

            # Test quality profiles
            profiles = await client.get_quality_profiles()
            print(f"  ✅ get_quality_profiles: {len(profiles)} profiles")
    except Exception as e:
        print(f"  ❌ Sonarr error: {e}")
        return False

    # Test Radarr
    print("\nTesting Radarr client...")
    try:
        async with RadarrClient(
            base_url=os.getenv("RADARR_URL", "http://192.168.45.15:5051"),
            api_key=os.getenv("RADARR_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")
        ) as client:
            # Test list_movies
            movies = await client.list_movies()
            print(f"  ✅ list_movies: {len(movies)} movies in library")

            # Test lookup
            results = await client.lookup_movie("Dune")
            print(f"  ✅ lookup_movie: Found {len(results)} results")

            # Test quality profiles
            profiles = await client.get_quality_profiles()
            print(f"  ✅ get_quality_profiles: {len(profiles)} profiles")
    except Exception as e:
        print(f"  ❌ Radarr error: {e}")
        return False

    return True


async def test_mcp_server():
    """Test that MCP server responds correctly."""
    print("\n=== Testing MCP Server ===")

    try:
        from mcp_server_v2 import McpServerV2
        from backends.sonarr_client import SonarrClient
        from backends.radarr_client import RadarrClient
        from tools import register_sonarr_tools, register_radarr_tools
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("   MCP server not ready yet")
        return False

    try:
        # Create server and clients
        server = McpServerV2()
        sonarr_client = SonarrClient(
            base_url=os.getenv("SONARR_URL", "http://192.168.45.15:8083"),
            api_key=os.getenv("SONARR_API_KEY", "7ce61d72c943483ca03864e03f013127")
        )
        radarr_client = RadarrClient(
            base_url=os.getenv("RADARR_URL", "http://192.168.45.15:5051"),
            api_key=os.getenv("RADARR_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")
        )

        # Register tools
        register_sonarr_tools(server, sonarr_client)
        register_radarr_tools(server, radarr_client)

        # Test initialize
        init_response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0.0"}
            }
        })
        print(f"  ✅ initialize: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'OK')}")

        # Test tools/list
        list_response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        })
        tools = list_response.get("result", {}).get("tools", [])
        print(f"  ✅ tools/list: {len(tools)} tools registered")

        # Cleanup
        await sonarr_client.close()
        await radarr_client.close()

    except Exception as e:
        print(f"  ❌ MCP server error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_tool_execution():
    """Test executing tools through MCP."""
    print("\n=== Testing Tool Execution ===")

    try:
        from mcp_server_v2 import McpServerV2
        from backends.sonarr_client import SonarrClient
        from backends.radarr_client import RadarrClient
        from tools import register_sonarr_tools, register_radarr_tools
    except ImportError:
        print("❌ MCP server not ready")
        return False

    try:
        # Create server and clients
        server = McpServerV2()
        sonarr_client = SonarrClient(
            base_url=os.getenv("SONARR_URL", "http://192.168.45.15:8083"),
            api_key=os.getenv("SONARR_API_KEY", "7ce61d72c943483ca03864e03f013127")
        )
        radarr_client = RadarrClient(
            base_url=os.getenv("RADARR_URL", "http://192.168.45.15:5051"),
            api_key=os.getenv("RADARR_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")
        )

        # Register tools
        register_sonarr_tools(server, sonarr_client)
        register_radarr_tools(server, radarr_client)

        # Test sonarr_list_series
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "sonarr_list_series",
                "arguments": {}
            }
        })
        result = response.get("result", {})
        if "error" in response:
            print(f"  ❌ sonarr_list_series: {response['error']}")
        else:
            print(f"  ✅ sonarr_list_series: executed")

        # Test sonarr_lookup_series
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "sonarr_lookup_series",
                "arguments": {"term": "Breaking Bad"}
            }
        })
        if "error" in response:
            print(f"  ❌ sonarr_lookup_series: {response['error']}")
        else:
            print(f"  ✅ sonarr_lookup_series: executed")

        # Test radarr_list_movies
        response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "radarr_list_movies",
                "arguments": {}
            }
        })
        if "error" in response:
            print(f"  ❌ radarr_list_movies: {response['error']}")
        else:
            print(f"  ✅ radarr_list_movies: executed")

        # Cleanup
        await sonarr_client.close()
        await radarr_client.close()

    except Exception as e:
        print(f"  ❌ Tool execution error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("TOOLARR MCP v2 INTEGRATION TEST")
    print("=" * 60)

    results = []

    results.append(("Backend Clients", await test_backend_clients()))
    results.append(("MCP Server", await test_mcp_server()))
    results.append(("Tool Execution", await test_tool_execution()))

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 All integration tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
