# Toolarr: Sonarr & Radarr API Tool Server

Toolarr is a powerful, self-hosted API server designed to act as a bridge between AI language models (like those in Open WebUI) and your Sonarr and Radarr instances. It exposes a clean, tool-friendly OpenAPI schema that allows you to manage your media library using natural language.

This server is built with FastAPI and is designed to be deployed as a Docker Swarm service, allowing for robust, multi-instance management of your media servers.

---

## Features

### Quality Profile Management
- **Get Quality Profiles:** List all available quality profiles for both Radarr and Sonarr instances.
- **Automatic Profile Name Resolution:** Movie and TV show searches now include the quality profile name, eliminating the need for separate lookups.

- **Multi-Instance Support:** Natively manage multiple Sonarr and Radarr instances from a single API. Perfect for separating 4K and 1080p libraries.
- **Library Management:**
    - Find movies and series in your existing library.
    - Move the file paths of movies and series between different root folders.
- **Queue Management:**
    - View the current download queue for any instance.
    - View the download history for any instance.
    - Delete items from the download queue (and optionally from the download client).
- **Intelligent by Default:** Includes a "default" instance fallback, making it easy to use with LLMs that may not specify an instance name for every call.
- **Secure:** Protected by a secret API key to prevent unauthorized access.
- **Dockerized for Swarm:** Designed to run as a global service in a Docker Swarm environment, ensuring high availability and simple deployment.

---

## Requirements

- Docker
- Docker Swarm initialized on your host(s)
- A shared Docker network that both `toolarr` and your Sonarr/Radarr services are connected to.

---

## Setup & Configuration

### 1. Clone the Repository

```bash
git clone https://github.com/Zipties/toolarr.git
cd toolarr
```

### 2. Configure Your Instances

Toolarr is configured using environment variables. A template is provided in `.env.example`.

First, copy the example file to create your own personal configuration:

```bash
cp .env.example .env
```

Now, open the `.env` file in a text editor and fill in your specific values.

```dotenv
# .env

# A secret key for your tool server. Generate one with: openssl rand -hex 32
TOOL_API_KEY=your_secret_api_key_here

# --- Sonarr Instance 1 ---
# A friendly name for this instance, used in the API URL.
SONARR_INSTANCE_1_NAME="sonarr"
# The full URL to your Sonarr instance's API.
# Use the Docker service name for reliable communication within the Swarm.
SONARR_INSTANCE_1_URL="http://piflix_sonarr:8082"
# Your Sonarr API key.
SONARR_INSTANCE_1_API_KEY="your_sonarr_api_key_here"

# --- Radarr Instance 1 ---
RADARR_INSTANCE_1_NAME="radarr"
RADARR_INSTANCE_1_URL="http://piflix_radarr:5051"
RADARR_INSTANCE_1_API_KEY="your_radarr_api_key_here"

# --- Add More Instances (Optional) ---
# To add more, just increment the number (e.g., SONARR_INSTANCE_2_...).
# SONARR_INSTANCE_2_NAME="sonarr-4k"
# SONARR_INSTANCE_2_URL="http://piflix_sonarr4k:8082"
# SONARR_INSTANCE_2_API_KEY="your_sonarr_4k_api_key_here"
```

---

## Deployment

### Using Pre-built Images

Once published, you can use pre-built images instead of building locally:

1. **From Docker Hub:**
   ```yaml
   # In docker-compose.yml, replace the build section with:
   image: USERNAME/toolarr:latest
   ```

2. **From GitHub Container Registry:**
   ```yaml
   # In docker-compose.yml, replace the build section with:
   image: ghcr.io/USERNAME/toolarr:latest
   ```


Toolarr is designed to be deployed as a Docker Swarm stack.

1.  **Edit `docker-compose.yml`:** Open the `docker-compose.yml` file and change `traefik_public` to the name of the shared Docker network that your Sonarr and Radarr containers use.

2.  **Build the Image:**
    ```bash
    docker build -t toolarr:latest .
    ```
    *(Note: For multi-node Swarms, you must make this image available on all nodes, either by pushing to a registry or using the `docker save`/`docker load` method.)*

3.  **Deploy the Stack:**
    ```bash
    docker stack deploy -c docker-compose.yml toolarr
    ```
    This will deploy the `toolarr` service globally to all nodes in your Swarm.

---

## Usage with Open WebUI

To connect Toolarr to Open WebUI (or any other compatible tool):

1.  **Go to the Tools section in Open WebUI.**
2.  **Add a new tool and provide the OpenAPI schema URL:**

    **`http://toolarr_toolarr:8000/openapi.json`**

    *(This URL uses Docker's internal DNS: `<stack_name>_<service_name>:<internal_port>`)*

3.  **Set the Authentication:**
    -   **Auth Type:** `Bearer Token`
    -   **Token:** The `TOOL_API_KEY` you set in your `.env` file.

### Example Prompts

-   **Check quality profiles:**
    > "What quality profile is assigned to Superman Returns?"
    > *(The model will get both the quality profile ID and name in a single call)*

-   **List all quality profiles:**
    > "Show me all available quality profiles for movies in Radarr."

You can now ask the model to perform actions for you.

-   **Using the default instance:**
    > "Show me the current download queue for Sonarr."
    > *(The model will likely use `instance_name: "default"`, and Toolarr will correctly use your first configured Sonarr instance.)*

-   **Specifying a named instance:**
    > "Using toolarr, find the movie 'The Matrix' on the **radarr** instance."

-   **Deleting from the queue:**
    > "Get the Sonarr queue, then delete the item with ID 12345."

---

## Recent Updates

### Enhanced Quality Profile Support
- **Automatic Quality Profile Names**: When searching for movies or TV shows, the API now automatically includes the quality profile name alongside the ID. This eliminates the need for a second API call to look up quality profile names.
- **Clearer API Descriptions**: Endpoints now clearly distinguish between Radarr (for movies) and Sonarr (for TV shows) to help AI assistants choose the correct service.

### Environment Configuration
- **No Quotes Required**: Environment variables in the `.env` file should not be wrapped in quotes. For example:
  ```
  RADARR_INSTANCE_1_URL=http://piflix_radarr:5051  # Correct
  RADARR_INSTANCE_1_URL="http://piflix_radarr:5051"  # Incorrect - will cause errors
  ```

### Example API Responses

When querying for a movie, you'll now see both the quality profile ID and name:
```json
{
  "id": 864,
  "title": "The Matrix",
  "path": "/mnt/video/movies/The Matrix (1999)",
  "qualityProfileId": 6,
  "qualityProfileName": "HD - 720p/1080p (Web)",
  ...
}
```

