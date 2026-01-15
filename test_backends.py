#!/usr/bin/env python3
"""Test script for Toolarr backend API clients."""

import asyncio
import os
from backends import SonarrClient, RadarrClient, ArrAPIError, ArrConnectionError


# Configuration from environment
SONARR_URL = os.getenv("SONARR_INSTANCE_1_URL", "http://192.168.45.15:8083")
SONARR_API_KEY = os.getenv("SONARR_INSTANCE_1_API_KEY", "7ce61d72c943483ca03864e03f013127")
RADARR_URL = os.getenv("RADARR_INSTANCE_1_URL", "http://192.168.45.15:5051")
RADARR_API_KEY = os.getenv("RADARR_INSTANCE_1_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print('=' * 80)


def print_result(method: str, success: bool, data=None, error=None):
    """Print test result."""
    status = "✓ PASS" if success else "✗ FAIL"
    print(f"{status} | {method}")
    if data is not None:
        if isinstance(data, list):
            print(f"       → Returned {len(data)} items")
            if data and len(data) > 0:
                print(f"       → Sample: {data[0].get('title', data[0].get('name', str(data[0])[:50]))}...")
        elif isinstance(data, dict):
            keys = list(data.keys())[:5]
            print(f"       → Keys: {', '.join(keys)}...")
        else:
            print(f"       → {data}")
    if error:
        print(f"       → Error: {error}")


async def test_sonarr():
    """Test Sonarr client."""
    print_section("SONARR API TESTS")

    async with SonarrClient(SONARR_URL, SONARR_API_KEY) as client:

        # System
        try:
            status = await client.get_system_status()
            print_result("get_system_status()", True, status)
        except Exception as e:
            print_result("get_system_status()", False, error=str(e))

        # Series Management
        try:
            series = await client.list_series()
            print_result("list_series()", True, series)
        except Exception as e:
            print_result("list_series()", False, error=str(e))

        try:
            results = await client.lookup_series("Breaking Bad")
            print_result("lookup_series('Breaking Bad')", True, results)
        except Exception as e:
            print_result("lookup_series('Breaking Bad')", False, error=str(e))

        # Get first series for testing
        series_id = None
        if series and len(series) > 0:
            series_id = series[0]['id']
            try:
                series_detail = await client.get_series(series_id)
                print_result(f"get_series({series_id})", True, series_detail)
            except Exception as e:
                print_result(f"get_series({series_id})", False, error=str(e))

            # Episodes
            try:
                episodes = await client.get_episodes(series_id)
                print_result(f"get_episodes({series_id})", True, episodes)

                # Get first episode for testing
                if episodes and len(episodes) > 0:
                    episode_id = episodes[0]['id']
                    try:
                        episode_detail = await client.get_episode(episode_id)
                        print_result(f"get_episode({episode_id})", True, episode_detail)
                    except Exception as e:
                        print_result(f"get_episode({episode_id})", False, error=str(e))

                    # Releases (might be empty, that's OK)
                    try:
                        releases = await client.get_releases(episode_id)
                        print_result(f"get_releases({episode_id})", True, releases)
                    except Exception as e:
                        print_result(f"get_releases({episode_id})", False, error=str(e))
            except Exception as e:
                print_result(f"get_episodes({series_id})", False, error=str(e))

        # Queue
        try:
            queue = await client.get_queue()
            print_result("get_queue()", True, queue)
        except Exception as e:
            print_result("get_queue()", False, error=str(e))

        # History
        try:
            history = await client.get_history(page=1, page_size=10)
            print_result("get_history()", True, history)
        except Exception as e:
            print_result("get_history()", False, error=str(e))

        # Configuration
        try:
            profiles = await client.get_quality_profiles()
            print_result("get_quality_profiles()", True, profiles)
        except Exception as e:
            print_result("get_quality_profiles()", False, error=str(e))

        try:
            folders = await client.get_root_folders()
            print_result("get_root_folders()", True, folders)
        except Exception as e:
            print_result("get_root_folders()", False, error=str(e))

        try:
            lang_profiles = await client.get_language_profiles()
            print_result("get_language_profiles()", True, lang_profiles)
        except Exception as e:
            print_result("get_language_profiles()", False, error=str(e))

        try:
            tags = await client.get_tags()
            print_result("get_tags()", True, tags)
        except Exception as e:
            print_result("get_tags()", False, error=str(e))

        try:
            disk = await client.get_disk_space()
            print_result("get_disk_space()", True, disk)
        except Exception as e:
            print_result("get_disk_space()", False, error=str(e))


async def test_radarr():
    """Test Radarr client."""
    print_section("RADARR API TESTS")

    async with RadarrClient(RADARR_URL, RADARR_API_KEY) as client:

        # System
        try:
            status = await client.get_system_status()
            print_result("get_system_status()", True, status)
        except Exception as e:
            print_result("get_system_status()", False, error=str(e))

        # Movie Management
        try:
            movies = await client.list_movies()
            print_result("list_movies()", True, movies)
        except Exception as e:
            print_result("list_movies()", False, error=str(e))

        try:
            results = await client.lookup_movie("The Matrix")
            print_result("lookup_movie('The Matrix')", True, results)
        except Exception as e:
            print_result("lookup_movie('The Matrix')", False, error=str(e))

        # Get first movie for testing
        movie_id = None
        if movies and len(movies) > 0:
            movie_id = movies[0]['id']
            try:
                movie_detail = await client.get_movie(movie_id)
                print_result(f"get_movie({movie_id})", True, movie_detail)
            except Exception as e:
                print_result(f"get_movie({movie_id})", False, error=str(e))

            # Releases (might be empty, that's OK)
            try:
                releases = await client.get_releases(movie_id)
                print_result(f"get_releases({movie_id})", True, releases)
            except Exception as e:
                print_result(f"get_releases({movie_id})", False, error=str(e))

        # Queue
        try:
            queue = await client.get_queue()
            print_result("get_queue()", True, queue)
        except Exception as e:
            print_result("get_queue()", False, error=str(e))

        # History
        try:
            history = await client.get_history(page=1, page_size=10)
            print_result("get_history()", True, history)
        except Exception as e:
            print_result("get_history()", False, error=str(e))

        # Configuration
        try:
            profiles = await client.get_quality_profiles()
            print_result("get_quality_profiles()", True, profiles)
        except Exception as e:
            print_result("get_quality_profiles()", False, error=str(e))

        try:
            folders = await client.get_root_folders()
            print_result("get_root_folders()", True, folders)
        except Exception as e:
            print_result("get_root_folders()", False, error=str(e))

        try:
            tags = await client.get_tags()
            print_result("get_tags()", True, tags)
        except Exception as e:
            print_result("get_tags()", False, error=str(e))

        try:
            disk = await client.get_disk_space()
            print_result("get_disk_space()", True, disk)
        except Exception as e:
            print_result("get_disk_space()", False, error=str(e))

        try:
            exclusions = await client.get_exclusions()
            print_result("get_exclusions()", True, exclusions)
        except Exception as e:
            print_result("get_exclusions()", False, error=str(e))

        try:
            import_lists = await client.get_import_lists()
            print_result("get_import_lists()", True, import_lists)
        except Exception as e:
            print_result("get_import_lists()", False, error=str(e))


async def test_error_handling():
    """Test error handling."""
    print_section("ERROR HANDLING TESTS")

    # Test invalid URL
    try:
        async with SonarrClient("http://invalid.local:9999", "fake-key") as client:
            await client.get_system_status()
        print_result("Invalid URL handling", False, error="Should have raised ArrConnectionError")
    except ArrConnectionError as e:
        print_result("Invalid URL handling", True, error=f"Correctly raised: {type(e).__name__}")
    except Exception as e:
        print_result("Invalid URL handling", False, error=f"Wrong exception: {type(e).__name__}")

    # Test invalid API key
    try:
        async with SonarrClient(SONARR_URL, "invalid-api-key") as client:
            await client.get_system_status()
        print_result("Invalid API key handling", False, error="Should have raised ArrAPIError")
    except ArrAPIError as e:
        print_result("Invalid API key handling", True, error=f"Correctly raised: {type(e).__name__} (status {e.status_code})")
    except Exception as e:
        print_result("Invalid API key handling", False, error=f"Wrong exception: {type(e).__name__}")

    # Test 404
    try:
        async with SonarrClient(SONARR_URL, SONARR_API_KEY) as client:
            await client.get_series(999999)
        print_result("404 handling", False, error="Should have raised ArrAPIError")
    except ArrAPIError as e:
        if e.status_code == 404:
            print_result("404 handling", True, error=f"Correctly raised: {type(e).__name__} (status {e.status_code})")
        else:
            print_result("404 handling", False, error=f"Wrong status code: {e.status_code}")
    except Exception as e:
        print_result("404 handling", False, error=f"Wrong exception: {type(e).__name__}")


async def test_context_manager():
    """Test context manager cleanup."""
    print_section("CONNECTION MANAGEMENT TESTS")

    try:
        # Test async context manager
        async with SonarrClient(SONARR_URL, SONARR_API_KEY) as client:
            await client.get_system_status()
            assert client._client is not None and not client._client.is_closed

        # After exiting context, client should be closed
        assert client._client is None or client._client.is_closed
        print_result("Async context manager cleanup", True)
    except Exception as e:
        print_result("Async context manager cleanup", False, error=str(e))

    try:
        # Test manual close
        client = SonarrClient(SONARR_URL, SONARR_API_KEY)
        await client.get_system_status()
        await client.close()
        assert client._client is None or client._client.is_closed
        print_result("Manual close", True)
    except Exception as e:
        print_result("Manual close", False, error=str(e))


async def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  TOOLARR BACKEND API CLIENT TEST SUITE")
    print("=" * 80)
    print(f"\nSonarr: {SONARR_URL}")
    print(f"Radarr: {RADARR_URL}")

    await test_sonarr()
    await test_radarr()
    await test_error_handling()
    await test_context_manager()

    print("\n" + "=" * 80)
    print("  TESTS COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
