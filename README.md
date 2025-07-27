<div align="center">

  <h1>Toolarr: A Stateless API Bridge for Sonarr & Radarr</h1>
  <p>
    <strong>A high-performance, privacy-focused, and AI-native API server that connects AI assistants like Open WebUI and ChatGPT to your Sonarr and Radarr instances for seamless media management.</strong>
  </p>
  <p>
    <a href="#overview">Overview</a> •
    <a href="#key-features">Key Features</a> •
    <a href="#ai-integration">AI Integration</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#example-prompts">Example Prompts</a>
  </p>
</div>

Toolarr is engineered to be a lightweight and efficient pass-through API bridge, addressing the common performance and privacy issues found in other media management tools. It provides a clean, unified interface for all your Sonarr and Radarr instances without retaining any state or logging user data.

Its core design principle is statelessness; instance configurations are loaded from environment variables on-demand for each request, ensuring minimal overhead and maximum speed.

***

### Overview

-   **High-Performance and Stateless:** I made this because the *arr MPC servers I have tried were fun, but were slow, clunky, and tended to overrun context of an LLM quickly. I wanted something I could tie into my voice assistant, so it needed to be more focused in its API calls

-   **Optimized for AI:** Toolarr is not just compatible with AI; it's designed for it. It generates a specially pruned OpenAPI schema to work flawlessly within the constraints of custom GPTs and other AI tools.
-   **Unified Multi-Instance Support:** Manage any number of Sonarr and Radarr servers through a single, consistent API interface.
-   **Secure by Default:** All API endpoints are protected by Bearer Token authentication, and your underlying Sonarr/Radarr API keys are never exposed in responses.
-   **Simple Docker Deployment:** Deploys as a lightweight, multi-stage Docker container for a fast and simple setup.

***

### Key Features

Toolarr provides a comprehensive suite of endpoints for robust media management.

-   **Media Management:** Add new movies and TV shows via title or ID (TMDb/TVDb), and delete existing media, including the underlying files.
-   **Library Updates:** Modify monitoring status, change quality profiles, update paths, and move media files to new root folders.
-   **Intelligent Search:** Trigger searches for missing media, specific seasons, or non-destructive quality upgrades.
-   **System & Library Information:** Perform library-wide searches, retrieve detailed media information with quality profiles, and get a list of all configured root folders.
-   **Tagging:** Full support for listing, creating, assigning, and removing tags from your media.
-   **Download Queue Management:** View the current download queue and history, and remove stuck or unwanted items directly.

***

### AI Integration

A key feature of Toolarr is its built-in OpenAPI schema generator, which creates two distinct specification files during the build process.

1.  `openapi.json`: The full, comprehensive API specification for use with tools like Open WebUI.
2.  `openapi-chatgpt.json`: A pruned specification file designed explicitly for AI models with endpoint limitations. This version automatically excludes all endpoints tagged as "internal-admin," ensuring it respects the **30-endpoint limit** for tools in platforms like OpenAI's custom GPTs. This makes Toolarr an ideal backend for creating powerful, custom "Media Manager" GPTs.

***

### Getting Started

Deployment is handled via Docker and requires minimal configuration.

1.  **Configure Environment:** Copy `.env.example` to `.env` and populate it with your instance URLs and API keys.
    ```bash
    cp .env.example .env
    nano .env
    ```

2.  **Launch Service:** Use the provided `docker-compose.yml` to build and run the service.
    ```bash
    docker-compose up -d
    ```

3.  **Connect to AI Assistant:**
    -   **Open WebUI:** Navigate to **Settings > Tools** and select **Add Tool**.
    -   **Custom GPT (ChatGPT):** Create a new GPT, go to **Configure > Actions > Add an action**, and choose "Import from URL."
    -   **Schema URL:**
        -   For full functionality (e.g., Open WebUI): `http://<your-docker-host-ip>:8000/openapi.json`
        -   For ChatGPT or other limited platforms: `http://<your-docker-host-ip>:8000/openapi-chatgpt.json`
    -   **Authentication:** Set the authentication method to **Bearer Token** and provide the `TOOL_API_KEY` from your `.env` file.

### Example Prompts

-   "In Radarr, search for the movie 'Dune: Part Two'."
-   "Add the TV show 'Fallout' to Sonarr and search for missing episodes."
-   "What's currently in the Sonarr download queue?"
-   "Delete the movie 'The Emoji Movie' from the default Radarr instance, and also delete the files."
-   "Find all movies in my library with the '4K' quality profile."
-   "Trigger an upgrade search for 'Oppenheimer'."
-   "The series 'Loki' appears to be having issues. Run the fix command for it on the Sonarr instance."

***Note:*** This exposes endpoints that can delete your files, and should be respected as such. In the future I plan to add env vars to limit which endpoints can be used
### License

This project is licensed under the MIT License. See the `LICENSE` file for details.
