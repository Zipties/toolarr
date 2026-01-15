# Toolarr vs Skills Benchmark

Compare two approaches to AI-controlled Sonarr/Radarr:
1. **Toolarr**: OpenAPI MCP gateway with structured tool calls
2. **Skills**: Direct curl/jq commands via bash (Piflix Chad approach)

## Metrics

| Metric | Description |
|--------|-------------|
| Time | Wall clock time from task start to completion |
| Accuracy | Did it return the correct result? |
| Iterations | Number of API calls / tool invocations |
| Token Est | Rough estimate based on tool schema size vs skill prompt |

## Test Scenarios

### Basic Operations
1. **Series Lookup** - Search for a TV show by name
2. **Movie Lookup** - Search for a movie by name
3. **Queue Check** - Get current download queue
4. **Quality Profiles** - List available quality profiles

### Complex Operations
5. **Add + Get Releases** - Add a series and get episode releases
6. **Add Movie + Download** - Add movie and trigger search
7. **Queue Management** - Check queue and identify stuck items

## Running Benchmarks

```bash
# Run all benchmarks
python3 benchmark.py

# Run specific test
python3 benchmark.py --test series_lookup

# Compare output
python3 benchmark.py --compare
```

## Results Format

```json
{
  "test": "series_lookup",
  "toolarr": {
    "time_ms": 245,
    "iterations": 1,
    "success": true,
    "result_hash": "abc123"
  },
  "skills": {
    "time_ms": 312,
    "iterations": 1,
    "success": true,
    "result_hash": "abc123"
  }
}
```
