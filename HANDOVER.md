## Handover Documentation for Sonarr Tool Server Project

### Project Overview
Building an OpenAPI tool server that allows Open WebUI (an AI chat interface) to interact with Sonarr (TV show management system) through natural language queries.

### Current Status
- **V1 Working**: Basic search/add functionality deployed globally on port 8085
- **V2 Development**: Enhanced features but facing OpenAPI schema validation issues with Open WebUI
- **Issue**: Open WebUI reports "400: Invalid schema for function 'get_missing_episodes_sonarr_wanted_missing_get': None is not valid under any of the given schemas"

### File Locations
```
/root/sonarr-tool-dev/           # Original v1 development
/root/sonarr-tool-v2-dev/        # Current v2 development
  ├── main.py                    # Current minimal version (2 endpoints only)
  ├── main_full.py               # Full v2 with all features (has schema issues)
  ├── Dockerfile
  ├── requirements.txt
  └── .env.production            # Contains API keys

/docker/sonarr-tool-server/      # Production deployment directory
```

### Docker Images
- `sonarr-tool-server:v1-bearer-auth` - Original working version (backup)
- `sonarr-tool-server:latest` - Currently v2 on global deployment
- `sonarr-tool-server:v2-minimal` - Minimal version with 2 endpoints only

### Deployments
- **Port 8085**: Global swarm service (3 nodes: dock-servarr, docker-homestead, docker-lappy)
- **Port 8086**: Local test container (currently running v2-minimal)

### API Keys
- **Tool API Key**: `b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0`
- **Sonarr API Key**: `7ce61d72c943483ca03864e03f013127`
- **Sonarr URL**: `http://piflix_sonarr:8082`

### The Problem
Open WebUI cannot handle FastAPI's OpenAPI schemas that contain `anyOf` with `null` type, which are generated when using `Optional[type] = None` in Pydantic models or function parameters.

### What Was Tried
1. Changed `Optional[int] = None` to `int = Query(0)` for function parameters
2. Attempted to remove Optional from Pydantic models
3. Created minimal version with no Optional fields

### Current Test
The minimal version (main.py) only has 2 endpoints without any Optional fields. Test if Open WebUI can use this on port 8086.

### Next Steps for New AI
1. **If minimal version works**: Gradually add back features one by one, avoiding Optional types
2. **If minimal still fails**: Check Open WebUI logs/console for more details about what it's parsing
3. **Alternative approach**: Consider using Union types or separate endpoints instead of Optional parameters

### Key Commands
```bash
# Check what's running
docker ps | grep sonarr-tool

# View logs
docker logs sonarr-tool-v2-test

# Test API directly
curl -H "Authorization: Bearer b3975f71af18e822d1a019f53999c92f13109ec39b38f50839cb408c0a90dfa0" \
     "http://localhost:8086/sonarr/series"

# Check schema
curl "http://localhost:8086/openapi.json" | jq '.'

# Rebuild and deploy test version
docker stop sonarr-tool-v2-test && docker rm sonarr-tool-v2-test && \
docker build -t sonarr-tool-server:v2-test . && \
docker run -d --name sonarr-tool-v2-test \
    --network traefik_public \
    --env-file .env.production \
    -p 8086:8000 \
    sonarr-tool-server:v2-test
```

### Knight Rider Test Case
- Series ID: 2312
- Located at: `/mnt/video/tv/Knight Rider (1982) [tvdb-77216]`
- Has all episodes, no tags currently assigned

Good luck!
