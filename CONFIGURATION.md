# Advanced Configuration Guide

## Building from Source

If you prefer to build the image locally:

```bash
git clone https://github.com/Zipties/toolarr.git
cd toolarr
docker build -t toolarr:local .
```

Then update `docker-compose.yml`:
```yaml
image: toolarr:local
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TOOL_API_KEY` | Secret key for API authentication | `openssl rand -hex 32` |
| `SONARR_INSTANCE_1_URL` | URL to your Sonarr instance | `http://sonarr:8989` |
| `SONARR_INSTANCE_1_API_KEY` | Sonarr API key | Found in Sonarr Settings → General |
| `RADARR_INSTANCE_1_URL` | URL to your Radarr instance | `http://radarr:7878` |
| `RADARR_INSTANCE_1_API_KEY` | Radarr API key | Found in Radarr Settings → General |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SONARR_INSTANCE_1_NAME` | Display name for Sonarr instance | `sonarr` |
| `RADARR_INSTANCE_1_NAME` | Display name for Radarr instance | `radarr` |

## Multiple Instances

To add additional Sonarr or Radarr instances, increment the instance number:

```env
# Second Sonarr instance (e.g., 4K library)
SONARR_INSTANCE_2_NAME=sonarr-4k
SONARR_INSTANCE_2_URL=http://sonarr-4k:8989
SONARR_INSTANCE_2_API_KEY=your_4k_api_key

# Second Radarr instance
RADARR_INSTANCE_2_NAME=radarr-4k
RADARR_INSTANCE_2_URL=http://radarr-4k:7878
RADARR_INSTANCE_2_API_KEY=your_4k_api_key
```

## Network Configuration

### Using Different Networks

If your services use a different network than `traefik_public`:

```yaml
networks:
  your_network_name:
    external: true
```

### Creating a Dedicated Network

```bash
docker network create -d overlay media_network
```

## Development Setup

For local development:

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
docker service logs toolarr_toolarr -f
```

### Cannot Connect to Sonarr/Radarr

1. Verify service names:
   ```bash
   docker service ls
   ```

2. Test connectivity:
   ```bash
   docker run --rm --network traefik_public alpine ping sonarr
   ```

3. Check if services are on the same network:
   ```bash
   docker service inspect sonarr --format '{{json .Spec.TaskTemplate.Networks}}'
   ```

### API Key Issues

- Ensure no quotes around values in .env file
- Verify API key is correct in Sonarr/Radarr settings
- Test with curl:
  ```bash
  curl -H "Authorization: Bearer YOUR_API_KEY" http://toolarr:8000/
  ```

## API Documentation

Once deployed, full API documentation is available at:
- Swagger UI: `http://toolarr:8000/docs`
- ReDoc: `http://toolarr:8000/redoc`
- OpenAPI JSON: `http://toolarr:8000/openapi.json`
