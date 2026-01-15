# Toolarr Backend Clients - Quick Start

## Installation

No additional dependencies needed - httpx is already in `requirements.txt`.

## 30-Second Examples

### Search and Add a TV Series

```python
import asyncio
from backends import SonarrClient

async def add_series():
    async with SonarrClient(
        "http://192.168.45.15:8083",
        "7ce61d72c943483ca03864e03f013127"
    ) as client:
        # Search
        results = await client.lookup_series("Breaking Bad")

        # Add
        series = results[0]
        series.update({
            "qualityProfileId": 6,
            "rootFolderPath": "/mnt/video/tv",
            "monitored": True,
            "addOptions": {"searchForMissingEpisodes": True}
        })
        await client.add_series(series)

asyncio.run(add_series())
```

### Search and Add a Movie

```python
import asyncio
from backends import RadarrClient

async def add_movie():
    async with RadarrClient(
        "http://192.168.45.15:5051",
        "d81da54eab704db0aa2d4e1d66cd697a"
    ) as client:
        # Search
        results = await client.lookup_movie("The Matrix")

        # Add
        movie = results[0]
        movie.update({
            "qualityProfileId": 6,
            "rootFolderPath": "/mnt/video/movies",
            "monitored": True,
            "addOptions": {"searchForMovie": True}
        })
        await client.add_movie(movie)

asyncio.run(add_movie())
```

## Common Operations

### Get Your Library

```python
async with SonarrClient(url, key) as client:
    series = await client.list_series()
    print(f"You have {len(series)} TV series")

async with RadarrClient(url, key) as client:
    movies = await client.list_movies()
    print(f"You have {len(movies)} movies")
```

### Check Download Queue

```python
async with SonarrClient(url, key) as client:
    queue = await client.get_queue()
    print(f"Downloading {queue['totalRecords']} items")

    for item in queue['records']:
        print(f"  - {item['title']} ({item['status']})")
```

### Search for Missing Episodes

```python
async with SonarrClient(url, key) as client:
    # Get series
    series = await client.list_series()
    breaking_bad = next(s for s in series if "Breaking Bad" in s['title'])

    # Trigger search
    command = await client.search_series(breaking_bad['id'])
    print(f"Search started: {command['id']}")
```

### Get Available Releases

```python
async with RadarrClient(url, key) as client:
    # Get movie
    movies = await client.list_movies()
    matrix = next(m for m in movies if "Matrix" in m['title'])

    # Get releases
    releases = await client.get_releases(matrix['id'])

    for release in releases[:5]:
        print(f"{release['title']} - {release['size']} bytes")
```

## Error Handling

```python
from backends import SonarrClient, ArrAPIError, ArrConnectionError

async with SonarrClient(url, key) as client:
    try:
        series = await client.get_series(999999)
    except ArrAPIError as e:
        # API returned an error (404, 500, etc.)
        print(f"API Error {e.status_code}: {e.message}")
    except ArrConnectionError as e:
        # Couldn't connect to server
        print(f"Connection failed: {e}")
```

## Using Environment Variables

```python
import os
from backends import SonarrClient, RadarrClient

# .env file
# SONARR_URL=http://192.168.45.15:8083
# SONARR_API_KEY=your-key-here

sonarr = SonarrClient(
    os.getenv("SONARR_URL"),
    os.getenv("SONARR_API_KEY")
)
```

## Batch Operations (Parallel)

```python
import asyncio
from backends import SonarrClient

async with SonarrClient(url, key) as client:
    series = await client.list_series()

    # Fetch episodes for first 10 series in parallel
    tasks = [client.get_episodes(s['id']) for s in series[:10]]
    results = await asyncio.gather(*tasks)

    for series, episodes in zip(series[:10], results):
        print(f"{series['title']}: {len(episodes)} episodes")
```

## Configuration

```python
from backends import SonarrClient

client = SonarrClient(
    base_url="http://localhost:8989",
    api_key="your-api-key",
    timeout=60.0,       # Request timeout (seconds)
    max_retries=5,      # Max retry attempts
    retry_delay=2.0     # Base delay for backoff
)
```

## Testing Your Setup

```bash
# Run full test suite
python test_backends.py

# Run examples
python examples_backend_usage.py
```

## Complete Method List

Run this to see all available methods:

```python
from backends import SonarrClient, RadarrClient

print("Sonarr methods:")
for method in dir(SonarrClient):
    if not method.startswith('_') and callable(getattr(SonarrClient, method)):
        print(f"  - {method}")

print("\nRadarr methods:")
for method in dir(RadarrClient):
    if not method.startswith('_') and callable(getattr(RadarrClient, method)):
        print(f"  - {method}")
```

## Documentation

- **Full API Reference**: `backends/README.md`
- **Architecture Details**: `BACKEND_CLIENT_SUMMARY.md`
- **Test Suite**: `test_backends.py`
- **Examples**: `examples_backend_usage.py`

## Support

If something isn't working:

1. Check the test suite passes: `python test_backends.py`
2. Verify your URL and API key are correct
3. Check the server is accessible: `curl http://your-server:8989/api/v3/system/status?apikey=your-key`
4. Review error messages - they include status codes and response data

---

**Ready to build your MCP layer!** These clients handle all the messy API details so you can focus on building great tools.
