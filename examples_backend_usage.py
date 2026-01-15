#!/usr/bin/env python3
"""Example usage of Toolarr backend API clients."""

import asyncio
import os
from backends import SonarrClient, RadarrClient, ArrAPIError, ArrConnectionError


async def sonarr_examples():
    """Example Sonarr operations."""
    print("\n=== SONARR EXAMPLES ===\n")

    # Initialize client from environment variables
    sonarr_url = os.getenv("SONARR_INSTANCE_1_URL", "http://192.168.45.15:8083")
    sonarr_key = os.getenv("SONARR_INSTANCE_1_API_KEY", "7ce61d72c943483ca03864e03f013127")

    # Use async context manager for automatic cleanup
    async with SonarrClient(sonarr_url, sonarr_key) as client:

        # Example 1: Search for a series
        print("1. Search for 'Breaking Bad':")
        results = await client.lookup_series("Breaking Bad")
        if results:
            print(f"   Found {len(results)} results")
            first = results[0]
            print(f"   - {first['title']} ({first.get('year', 'N/A')})")
            print(f"   - TVDB ID: {first.get('tvdbId')}")
            print()

        # Example 2: List all series
        print("2. Get all series:")
        series = await client.list_series()
        print(f"   Total series in library: {len(series)}")
        if series:
            monitored = [s for s in series if s.get('monitored')]
            print(f"   Monitored: {len(monitored)}")
            print()

        # Example 3: Get episodes for first series
        if series:
            first_series = series[0]
            print(f"3. Get episodes for '{first_series['title']}':")
            episodes = await client.get_episodes(first_series['id'])
            print(f"   Total episodes: {len(episodes)}")
            if episodes:
                downloaded = [e for e in episodes if e.get('hasFile')]
                print(f"   Downloaded: {len(downloaded)}")
            print()

        # Example 4: Check download queue
        print("4. Check download queue:")
        queue = await client.get_queue(page_size=5)
        print(f"   Items in queue: {queue.get('totalRecords', 0)}")
        for item in queue.get('records', []):
            print(f"   - {item.get('title')} ({item.get('status')})")
        print()

        # Example 5: Get recent history
        print("5. Get recent history:")
        history = await client.get_history(page=1, page_size=5)
        print(f"   Total history records: {history.get('totalRecords', 0)}")
        for item in history.get('records', []):
            event_type = item.get('eventType', 'unknown')
            title = item.get('sourceTitle', 'N/A')
            print(f"   - {event_type}: {title[:60]}")
        print()

        # Example 6: Get configuration
        print("6. Get quality profiles:")
        profiles = await client.get_quality_profiles()
        for profile in profiles:
            print(f"   - {profile['name']} (ID: {profile['id']})")
        print()

        print("7. Get root folders:")
        folders = await client.get_root_folders()
        for folder in folders:
            path = folder['path']
            accessible = "✓" if folder.get('accessible') else "✗"
            print(f"   {accessible} {path}")
        print()


async def radarr_examples():
    """Example Radarr operations."""
    print("\n=== RADARR EXAMPLES ===\n")

    # Initialize client from environment variables
    radarr_url = os.getenv("RADARR_INSTANCE_1_URL", "http://192.168.45.15:5051")
    radarr_key = os.getenv("RADARR_INSTANCE_1_API_KEY", "d81da54eab704db0aa2d4e1d66cd697a")

    async with RadarrClient(radarr_url, radarr_key) as client:

        # Example 1: Search for a movie
        print("1. Search for 'The Matrix':")
        results = await client.lookup_movie("The Matrix")
        if results:
            print(f"   Found {len(results)} results")
            first = results[0]
            print(f"   - {first['title']} ({first.get('year', 'N/A')})")
            print(f"   - TMDb ID: {first.get('tmdbId')}")
            print()

        # Example 2: List all movies
        print("2. Get all movies:")
        movies = await client.list_movies()
        print(f"   Total movies in library: {len(movies)}")
        if movies:
            monitored = [m for m in movies if m.get('monitored')]
            downloaded = [m for m in movies if m.get('hasFile')]
            print(f"   Monitored: {len(monitored)}")
            print(f"   Downloaded: {len(downloaded)}")
            print()

        # Example 3: Check download queue
        print("3. Check download queue:")
        queue = await client.get_queue(page_size=5)
        print(f"   Items in queue: {queue.get('totalRecords', 0)}")
        for item in queue.get('records', []):
            print(f"   - {item.get('title')} ({item.get('status')})")
        print()

        # Example 4: Get recent history
        print("4. Get recent history:")
        history = await client.get_history(page=1, page_size=5)
        print(f"   Total history records: {history.get('totalRecords', 0)}")
        for item in history.get('records', []):
            event_type = item.get('eventType', 'unknown')
            title = item.get('sourceTitle', 'N/A')
            print(f"   - {event_type}: {title[:60]}")
        print()

        # Example 5: Get configuration
        print("5. Get quality profiles:")
        profiles = await client.get_quality_profiles()
        for profile in profiles:
            print(f"   - {profile['name']} (ID: {profile['id']})")
        print()

        print("6. Get root folders:")
        folders = await client.get_root_folders()
        for folder in folders:
            path = folder['path']
            accessible = "✓" if folder.get('accessible') else "✗"
            print(f"   {accessible} {path}")
        print()


async def error_handling_example():
    """Example error handling."""
    print("\n=== ERROR HANDLING EXAMPLE ===\n")

    # Example: Graceful error handling
    async with SonarrClient("http://192.168.45.15:8083", "test-key") as client:
        try:
            # Try to get a non-existent series
            series = await client.get_series(999999)
            print(f"Series: {series}")
        except ArrAPIError as e:
            print(f"API Error: {e.status_code} - {e.message[:100]}")
        except ArrConnectionError as e:
            print(f"Connection Error: {e}")
        except Exception as e:
            print(f"Unexpected Error: {e}")


async def batch_operations_example():
    """Example of batch operations using connection pooling."""
    print("\n=== BATCH OPERATIONS EXAMPLE ===\n")

    sonarr_url = os.getenv("SONARR_INSTANCE_1_URL", "http://192.168.45.15:8083")
    sonarr_key = os.getenv("SONARR_INSTANCE_1_API_KEY", "7ce61d72c943483ca03864e03f013127")

    async with SonarrClient(sonarr_url, sonarr_key) as client:
        # Get first 5 series
        series = await client.list_series()
        series_to_check = series[:5]

        print(f"Checking episodes for {len(series_to_check)} series:")

        # Batch fetch episode counts (connection pooling handles concurrency)
        tasks = [client.get_episodes(s['id']) for s in series_to_check]
        results = await asyncio.gather(*tasks)

        for series, episodes in zip(series_to_check, results):
            print(f"   - {series['title']}: {len(episodes)} episodes")


async def main():
    """Run all examples."""
    await sonarr_examples()
    await radarr_examples()
    await error_handling_example()
    await batch_operations_example()

    print("\n✓ All examples completed!\n")


if __name__ == "__main__":
    asyncio.run(main())
