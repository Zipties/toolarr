# Toolarr: Sonarr & Radarr API Bridge for AI

Toolarr exposes a clean, tool-friendly API that allows AI assistants (like Open WebUI) to manage your Sonarr and Radarr media libraries using natural language.


##  Connect to Open WebUI

1. In Open WebUI, go to **Settings > Tools** and click **Add Tool**.
2. Enter the OpenAPI schema URL: `http://<your-docker-host-ip>:8000`
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
