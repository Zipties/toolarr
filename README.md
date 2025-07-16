# Toolarr: Sonarr & Radarr API Bridge for AI

Toolarr exposes a clean, tool-friendly API that allows AI assistants (like Open WebUI) to manage your Sonarr and Radarr media libraries using natural language.

##  Quick Start (2 minutes)

```bash
# Download the docker-compose file
wget https://raw.githubusercontent.com/Zipties/toolarr/master/docker-compose.yml

# Create your configuration
cat > .env << 'EOL'
TOOL_API_KEY=your_secret_api_key_here
SONARR_INSTANCE_1_NAME=sonarr
SONARR_INSTANCE_1_URL=http://sonarr:8989
SONARR_INSTANCE_1_API_KEY=your_sonarr_api_key
RADARR_INSTANCE_1_NAME=radarr
RADARR_INSTANCE_1_URL=http://radarr:7878
RADARR_INSTANCE_1_API_KEY=your_radarr_api_key
EOL

# Deploy to Docker Swarm
docker stack deploy -c docker-compose.yml toolarr
```

That's it! Toolarr is now running.

##  Configuration

### Minimal Configuration
You only need to provide:
- `TOOL_API_KEY`: A secret key to protect your API (generate with `openssl rand -hex 32`)
- Your Sonarr/Radarr URLs and API keys

### Service Names
Use the Docker service names for reliable communication within your stack:
- If Sonarr is deployed as `media_sonarr`, use `http://media_sonarr:8989`
- If Radarr is deployed as `media_radarr`, use `http://media_radarr:7878`

### Multiple Instances
Add more instances by incrementing the number:
```env
SONARR_INSTANCE_2_NAME=sonarr-4k
SONARR_INSTANCE_2_URL=http://sonarr-4k:8989
SONARR_INSTANCE_2_API_KEY=your_4k_api_key
```

##  Connect to Open WebUI

1. In Open WebUI, go to **Tools** → **Add Tool**
2. Enter the OpenAPI URL: `http://toolarr:8000/openapi.json`
3. Set authentication:
   - Type: **Bearer Token**
   - Token: Your `TOOL_API_KEY`

##  Features

### Quality Profile Management
- **Automatic Profile Names**: When searching for content, quality profile names are included automatically
- **Clear Service Distinction**: API clearly separates movie (Radarr) and TV show (Sonarr) operations

### Library Management
- Search for movies and TV shows
- View quality profiles
- Move content between folders
- Update series monitoring

### Media Management
- Add new movies and TV shows to your library
- Delete movies and TV shows, including their files

### Tag Management
- Create, view, and delete tags
- Assign tags to media

### Queue Management
- View download queues
- Check download history
- Delete items from queue

## 💬 Example Prompts

Once connected to your AI assistant:

- "What quality profile is assigned to The Matrix?"
- "Show me the Sonarr download queue"
- "Find all movies with the '4K' quality profile"
- "Delete the stuck download for Breaking Bad"

##  Docker Image

Pre-built images are available:
```yaml
# In docker-compose.yml
image: ghcr.io/zipties/toolarr:master
```

## 🔒 Security

- All endpoints require Bearer token authentication
- API keys are never exposed in responses
- Supports multiple isolated instances

## 📦 Requirements

- Docker with Swarm mode initialized
- Network connectivity to your Sonarr/Radarr instances
- Shared Docker network (e.g., `traefik_public`)

## 🛠 Advanced Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for:
- Building from source
- Custom network setups
- Development setup
- Troubleshooting

## 📄 License

MIT License - see [LICENSE](LICENSE) for details
