# GEMINI.md: Toolarr Project State

## 1. Project Purpose and Core Functionality

This project, "Toolarr," is a Python-based API server that acts as a unified interface for managing multiple instances of Sonarr and Radarr. Its primary purpose is to abstract the complexity of interacting with these media servers, providing a single, authenticated entry point for higher-level applications like the Open WebUI.

**Core Features:**
*   Manages multiple Sonarr and Radarr instances dynamically from environment variables.
*   Provides a consistent RESTful API for common actions (library search, adding/deleting media, download queue, history, etc.).
*   Handles authentication with a Bearer token.
*   Exposes the underlying Sonarr/Radarr APIs for actions like updating tags, moving files, and managing media monitoring.

## 2. Technical Stack

*   **Language:** Python 3.11
*   **Framework:** FastAPI
*   **Key Libraries:** `uvicorn`, `pydantic`, `httpx`
*   **Containerization:** Docker
*   **Orchestration:** Docker Swarm

## 3. Project Architecture and Conventions

*   **Structure:** The project is modular, with `main.py` as the entry point and separate files (`sonarr.py`, `radarr.py`) for each media server's logic.
*   **Configuration:** The application is configured entirely through environment variables, loaded from a `.env` file. This is a stateless approach that is well-suited for a containerized environment.
*   **API Design:** The API is designed to be RESTful. A key convention is to ensure all API endpoints have a unique and descriptive `operation_id`. This was implemented to resolve previous ambiguity between the Sonarr and Radarr modules and is critical for reliable AI tool routing.
*   **Code Style:** The code adheres to standard Python conventions (PEP 8), using `snake_case` for functions and variables and `PascalCase` for classes. It also makes extensive use of type hints.

## 4. Development Workflow (Docker Swarm)

This project uses a Docker Swarm for deployment. The following workflow must be followed to ensure that changes are correctly deployed to all nodes in the swarm.

1.  **Build a Tagged Image:**
    *   Build the Docker image with a unique tag for each new build.
    *   Example: `docker build -t 192.168.45.15:5000/toolarr:build-001 .`

2.  **Push to Local Registry:**
    *   Push the tagged image to the local Docker registry.
    *   Example: `docker push 192.168.45.15:5000/toolarr:build-001`

3.  **Update Compose File:**
    *   Update the `image` in `docker-compose.yml.build` to point to the new tagged image.
    *   Example: `image: 192.168.45.15:5000/toolarr:build-001`

4.  **Deploy the Stack:**
    *   Deploy the stack using the updated compose file.
    *   Example: `docker stack deploy -c docker-compose.yml.build toolarr`

## 5. Project Backlog & Future Enhancements

This section outlines identified but unimplemented features.

### 5.1. Radarr Collection Monitoring

*   **Goal:** Implement a feature to monitor an entire Radarr collection with a specific quality profile.
*   **Discovery:** The Radarr API does not support updating a collection's properties in a single atomic operation. Direct attempts to `PUT /api/v3/collection/{id}` will fail.
*   **Next Step:** The correct procedure is to:
    1.  Fetch all movies in the collection using `GET /api/v3/movie?collectionId={id}`.
    2.  Extract the `id` for each movie.
    3.  Send a single request to the `PUT /api/v3/movie/editor` endpoint with the full list of movie IDs and the desired monitoring settings.
    *   This logic needs to be implemented as a new endpoint in `radarr.py`.

### 5.2. Instance Read-Only Mode

*   **Goal:** Implement a feature to make individual Sonarr/Radarr instances read-only via an environment variable.
*   **Discovery:** A previous attempt failed due to a stateful configuration. The application was loading its configuration into a global object at startup, so changes to `.env` were not picked up by running containers.
*   **Next Step:** The configuration loading must be refactored to be stateless. The `get_..._instance` dependency functions in `instance_endpoints.py` should be responsible for reading the environment variables and constructing the configuration object on every API call.

## 6. External API Documentation

*   **Radarr API:** [https://radarr.video/docs/api/](https://radarr.video/docs/api/)
*   **Sonarr API:** [https://sonarr.tv/docs/api/](https://sonarr.tv/docs/api/)

## 7. Lessons Learned & Key Bug Fixes

This section documents important bugs and their resolutions to guide future development and prevent regressions.

### 7.1. Explicit `operation_id` for Long Routes

*   **Problem:** The AI model has a 64-character limit for tool function names. FastAPI auto-generates `operation_id`s from the function's path, which can easily exceed this limit for complex routes (e.g., `/series/{series_id}/seasons/{season_number}/monitor`).
*   **Resolution:** For any route that is long or complex, manually define a short, descriptive `operation_id` in the endpoint decorator to ensure it remains within the character limit.
    *   Example: `operation_id="monitor_sonarr_season"`

### 7.2. Cascading Monitoring Status in Sonarr

*   **Problem:** When a user unmonitors a series, they expect all seasons within that series to also be unmonitored. The Sonarr API does not do this automatically; updating the top-level `monitored` flag for a series does not affect the individual seasons.
*   **Resolution:** The `monitor_series` function was updated to explicitly iterate through the `seasons` array and set the `monitored` status for each season to match the series-level request. This ensures the application's behavior matches user expectations.

### 7.3. Guiding AI with Clear Tool Descriptions

*   **Problem:** The AI was inconsistently using the correct function to resolve tag IDs into human-readable names, sometimes returning raw IDs to the user.
*   **Resolution:** The docstrings for the library search functions were updated with explicit instructions, guiding the AI to always prefer the `_with_tags` variant for user-facing output. This provides a much stronger signal and ensures a more user-friendly experience.