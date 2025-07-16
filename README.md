# Toolarr: Sonarr & Radarr API Bridge for AI

Toolarr exposes a clean, tool-friendly API that allows AI assistants (like Open WebUI) to manage your Sonarr and Radarr media libraries using natural language.

##  Quick Start (2-minutes)

1.  **Download the `docker-compose.yml` file:**
    ```bash
    wget https://raw.githubusercontent.com/Zipties/toolarr/master/docker-compose.yml
    ```

2.  **Create your `.env` configuration file:**
    ```bash
    cat > .env << 'EOL'
    # Your secret API key (generate with: openssl rand -hex 32)
    TOOL_API_KEY=your_secret_api_key_here

    # Sonarr instance
    SONARR_INSTANCE_1_NAME=sonarr
    SONARR_INSTANCE_1_URL=http://sonarr:8989
    SONARR_INSTANCE_1_API_KEY=your_sonarr_api_key

    # Radarr instance
    RADARR_INSTANCE_1_NAME=radarr
    RADARR_INSTANCE_1_URL=http://radarr:7878
    RADARR_INSTANCE_1_API_KEY=your_radarr_api_key
    EOL
    ```

3.  **Deploy with Docker Swarm:**
    ```bash
    docker stack deploy -c docker-compose.yml toolarr
    ```

That's it! Toolarr is now running and ready to be connected to your AI assistant.

##  Connect to Open WebUI

1. In Open WebUI, go to **Settings > Tools** and click **Add Tool**.
2. Enter the OpenAPI schema URL: `http://<your-docker-host-ip>:8000/openapi.json`
3. Set the authentication type to **Bearer Token** and enter your `TOOL_API_KEY`.

##  Features

- **Unified API**: Manage multiple Sonarr and Radarr instances through a single, consistent interface.
- **Library Management**: Search for media, view quality profiles, move content, and update monitoring status.
- **Media Management**: Add and delete movies and TV shows, including their files.
- **Tagging**: Create, view, assign, and delete tags.
- **Queue Control**: View download queues and history, and remove items from the queue.

## 💬 Example Prompts

- "What quality profile is assigned to The Matrix?"
- "Show me the Sonarr download queue."
- "Find all movies with the '4K' quality profile."
- "Delete the stuck download for Breaking Bad."

## 🔒 Security

- All endpoints require Bearer token authentication.
- Your Sonarr/Radarr API keys are never exposed in responses.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
