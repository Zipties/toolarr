# Toolarr Backend API Clients

Clean, async API clients for Sonarr and Radarr that handle authentication, connection pooling, error handling, and retries.

## Features

- **Async/await** - Built on httpx for high-performance async operations
- **Connection pooling** - Reuses connections for better performance
- **Automatic retries** - Exponential backoff for transient failures (429, 500, 502, 503, 504)
- **Clean error handling** - Distinct exception types for different error scenarios
- **Context manager support** - Automatic cleanup with `async with`
- **Type-safe** - Comprehensive type hints for all methods

## Installation

The clients use httpx which should already be in `requirements.txt`:

```bash
pip install httpx
```

## Quick Start

### Sonarr

```python
import asyncio
from backends import SonarrClient

async def main():
    async with SonarrClient("http://localhost:8989", "your-api-key") as client:
        # Search for a series
        results = await client.lookup_series("Breaking Bad")

        # Add series to library
        if results:
            series_data = results[0]
            series_data.update({
                "qualityProfileId": 6,
                "rootFolderPath": "/mnt/video/tv",
                "monitored": True,
                "seasonFolder": True,
                "addOptions": {
                    "searchForMissingEpisodes": True
                }
            })
            added = await client.add_series(series_data)
            print(f"Added: {added['title']}")

asyncio.run(main())
```

### Radarr

```python
import asyncio
from backends import RadarrClient

async def main():
    async with RadarrClient("http://localhost:7878", "your-api-key") as client:
        # Search for a movie
        results = await client.lookup_movie("The Matrix")

        # Add movie to library
        if results:
            movie_data = results[0]
            movie_data.update({
                "qualityProfileId": 6,
                "rootFolderPath": "/mnt/video/movies",
                "monitored": True,
                "addOptions": {
                    "searchForMovie": True
                }
            })
            added = await client.add_movie(movie_data)
            print(f"Added: {added['title']}")

asyncio.run(main())
```

## Error Handling

The clients provide three distinct exception types:

```python
from backends import SonarrClient, ArrAPIError, ArrConnectionError, ArrClientError

async with SonarrClient(url, key) as client:
    try:
        series = await client.get_series(999999)
    except ArrAPIError as e:
        # API returned an error (4xx, 5xx)
        print(f"API Error {e.status_code}: {e.message}")
        print(f"Response data: {e.response_data}")
    except ArrConnectionError as e:
        # Failed to connect to the server
        print(f"Connection failed: {e}")
    except ArrClientError as e:
        # Other unexpected errors
        print(f"Client error: {e}")
```

## Configuration

### From Environment Variables

```python
import os
from backends import SonarrClient, RadarrClient

sonarr = SonarrClient(
    base_url=os.getenv("SONARR_URL", "http://localhost:8989"),
    api_key=os.getenv("SONARR_API_KEY")
)

radarr = RadarrClient(
    base_url=os.getenv("RADARR_URL", "http://localhost:7878"),
    api_key=os.getenv("RADARR_API_KEY")
)
```

### Custom Timeouts and Retries

```python
from backends import SonarrClient

async with SonarrClient(
    base_url="http://localhost:8989",
    api_key="your-api-key",
    timeout=60.0,        # Request timeout in seconds
    max_retries=5,       # Maximum retry attempts
    retry_delay=2.0      # Base delay for exponential backoff
) as client:
    # Your code here
    pass
```

## API Reference

### Sonarr Client

#### Series Management
- `list_series()` - Get all series
- `lookup_series(term)` - Search for series
- `get_series(series_id)` - Get series details
- `add_series(data)` - Add new series
- `update_series(data)` - Update series
- `delete_series(series_id, delete_files, add_import_exclusion)` - Delete series

#### Episode Management
- `get_episodes(series_id)` - Get all episodes for series
- `get_episode(episode_id)` - Get episode details
- `update_episode(data)` - Update episode

#### Release Management
- `get_releases(episode_id)` - Get available releases
- `grab_release(guid, indexer_id)` - Download a release

#### Queue & History
- `get_queue(page, page_size, include_series, include_episode)` - Get download queue
- `delete_queue_item(queue_id, remove_from_client, blocklist)` - Remove from queue
- `get_history(page, page_size, series_id, episode_id, event_type)` - Get history

#### Configuration
- `get_quality_profiles()` - Get quality profiles
- `get_quality_profile(profile_id)` - Get specific profile
- `get_root_folders()` - Get root folders
- `get_language_profiles()` - Get language profiles
- `get_tags()` - Get tags

#### Commands
- `search_series(series_id)` - Search all episodes in series
- `search_episode(episode_ids)` - Search specific episodes
- `search_season(series_id, season_number)` - Search season
- `refresh_series(series_id)` - Refresh series metadata
- `rescan_series(series_id)` - Rescan series folder
- `get_command(command_id)` - Get command status

#### System
- `get_system_status()` - Get system status
- `get_disk_space()` - Get disk space info

### Radarr Client

#### Movie Management
- `list_movies()` - Get all movies
- `lookup_movie(term)` - Search for movies
- `get_movie(movie_id)` - Get movie details
- `add_movie(data)` - Add new movie
- `update_movie(data)` - Update movie
- `delete_movie(movie_id, delete_files, add_import_exclusion)` - Delete movie

#### Release Management
- `get_releases(movie_id)` - Get available releases
- `grab_release(guid, indexer_id)` - Download a release

#### Queue & History
- `get_queue(page, page_size, include_movie)` - Get download queue
- `delete_queue_item(queue_id, remove_from_client, blocklist)` - Remove from queue
- `get_history(page, page_size, movie_id, event_type)` - Get history

#### Configuration
- `get_quality_profiles()` - Get quality profiles
- `get_quality_profile(profile_id)` - Get specific profile
- `get_root_folders()` - Get root folders
- `get_tags()` - Get tags

#### Commands
- `search_movie(movie_id)` - Search for movie
- `search_movies(movie_ids)` - Search multiple movies
- `refresh_movie(movie_id)` - Refresh movie metadata
- `rescan_movie(movie_id)` - Rescan movie folder
- `get_command(command_id)` - Get command status

#### System
- `get_system_status()` - Get system status
- `get_disk_space()` - Get disk space info

#### Exclusions & Lists
- `get_import_lists()` - Get import lists
- `get_exclusions()` - Get import exclusions
- `add_exclusion(tmdb_id, title, year)` - Add exclusion
- `delete_exclusion(exclusion_id)` - Remove exclusion

## Performance Tips

### Connection Pooling

The clients automatically maintain a connection pool. Reuse the same client instance for multiple requests:

```python
async with SonarrClient(url, key) as client:
    # Multiple requests reuse the same connection pool
    series = await client.list_series()
    for s in series[:10]:
        episodes = await client.get_episodes(s['id'])
```

### Batch Operations

Use `asyncio.gather()` for parallel requests:

```python
async with SonarrClient(url, key) as client:
    series = await client.list_series()

    # Fetch episodes for multiple series in parallel
    tasks = [client.get_episodes(s['id']) for s in series[:5]]
    results = await asyncio.gather(*tasks)
```

### Manual Cleanup

If not using context manager, remember to close:

```python
client = SonarrClient(url, key)
try:
    series = await client.list_series()
finally:
    await client.close()  # Important!
```

## Testing

Run the test suite:

```bash
# Set environment variables
export SONARR_INSTANCE_1_URL=http://192.168.45.15:8083
export SONARR_INSTANCE_1_API_KEY=your-key-here
export RADARR_INSTANCE_1_URL=http://192.168.45.15:5051
export RADARR_INSTANCE_1_API_KEY=your-key-here

# Run tests
python test_backends.py
```

See examples:

```bash
python examples_backend_usage.py
```

## Architecture

```
backends/
├── __init__.py           # Package exports
├── base.py               # BaseArrClient with common functionality
├── sonarr_client.py      # SonarrClient implementation
├── radarr_client.py      # RadarrClient implementation
└── README.md             # This file
```

### Base Client Features

The `BaseArrClient` provides:

- **Connection management** - httpx.AsyncClient with connection pooling
- **Request building** - Automatic URL construction and header injection
- **Error normalization** - Converts httpx exceptions to semantic exceptions
- **Retry logic** - Exponential backoff for transient failures
- **Response parsing** - JSON parsing and 204 handling

### Client Hierarchy

```
BaseArrClient
├── SonarrClient (Sonarr v3 API)
└── RadarrClient (Radarr v3 API)
```

## Future Enhancements

Potential improvements:

- [ ] Response caching for repeated queries
- [ ] Request rate limiting
- [ ] WebSocket support for real-time updates
- [ ] Bulk operations helpers
- [ ] Pydantic models for request/response validation
- [ ] Support for Lidarr, Readarr, etc.
