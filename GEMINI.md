# GEMINI Project Analysis: sonarr-tool-v2-dev

## 1. Project Overview

This project, named "Toolarr," is a Python-based API server designed to act as a unified interface for managing multiple instances of Sonarr (for TV shows) and Radarr (for movies). It exposes a RESTful API that can be used by other services, such as the Open WebUI, to interact with Sonarr and Radarr instances without needing to know their specific connection details.

The core purpose is to abstract the complexity of managing multiple media servers, providing a single, authenticated entry point for all interactions. It supports fetching library information, managing downloads, updating media properties, and handling tags.

## 2. Technical Stack

*   **Language:** Python 3.11
*   **Framework:** FastAPI
*   **Key Libraries:**
    *   `uvicorn`: ASGI server for running the FastAPI application.
    *   `pydantic`: Used for data validation and settings management (defining API request/response models).
    *   `httpx`: Asynchronous HTTP client for making API calls to the Sonarr/Radarr instances.
*   **Containerization:** Docker
*   **Orchestration:** Docker Swarm (as indicated by `docker-compose.yml` `deploy` keys and `docker stack deploy` commands).

## 3. Project Structure

The project follows a modular structure, separating concerns into different files:

```
/
├── .env.example         # Example environment variables for configuration
├── .gitignore           # Standard git ignore file
├── CONFIGURATION.md     # Detailed setup and troubleshooting guide
├── docker-compose.yml   # Docker Swarm deployment configuration
├── Dockerfile           # Defines the Docker image for the application
├── main.py              # Main application entry point (FastAPI app setup, middleware, routers)
├── radarr.py            # FastAPI router and logic for all Radarr-related endpoints
├── sonarr.py            # FastAPI router and logic for all Sonarr-related endpoints
├── instance_endpoints.py # API endpoints for listing configured instances
├── requirements.txt     # Python package dependencies
├── quick-deploy.sh      # A shell script for quick deployment (likely builds and deploys)
└── .github/workflows/   # GitHub Actions workflow for Docker image publishing
```

## 4. Code Style and Conventions

*   **Naming Convention:**
    *   Python files use `snake_case` (e.g., `instance_endpoints.py`).
    *   Functions and variables also use `snake_case` (e.g., `load_sonarr_instances`, `api_key`).
    *   Pydantic models use `PascalCase` (e.g., `UpdateTagsRequest`, `MoveSeriesRequest`).
    *   Constants are in `UPPER_CASE` (e.g., `TOOL_API_KEY`).
*   **Typing:** The code consistently uses Python type hints (e.g., `List`, `Optional`, `dict`), which is idiomatic for modern Python and FastAPI.
*   **Asynchronous Code:** The application is fully asynchronous, using `async def` for all API endpoints and `httpx.AsyncClient` for making downstream API calls. This is a best practice for I/O-bound applications like this one.
*   **Modularity:** Concerns are well-separated. `main.py` handles app setup, while `sonarr.py` and `radarr.py` contain the business logic for their respective services. This makes the codebase easy to navigate and maintain.
*   **Docstrings:** Functions generally have clear docstrings explaining their purpose, which is excellent for maintainability.

## 5. Deployment and Configuration

*   **Deployment:** The application is designed to be deployed as a Docker container within a Docker Swarm. The `docker-compose.yml` file defines a service named `toolarr` that is deployed globally on the swarm. It uses a local Docker registry (`192.168.45.15:5000`).
*   **Configuration:**
    *   Configuration is managed entirely through environment variables, loaded from a `.env` file. This is a security best practice, as it separates configuration from code.
    *   The `.env.example` file provides a clear template for all required and optional variables.
    *   The application supports configuring multiple Sonarr and Radarr instances by incrementing a number in the environment variable names (e.g., `SONARR_INSTANCE_1_NAME`, `SONARR_INSTANCE_2_NAME`).
*   **Security:** API access is protected by a Bearer token (`TOOL_API_KEY`), which is verified for all incoming requests.

## 6. Inferred Purpose and Functionality

The primary goal of this tool is to serve as a middleware or "tooling API" for a higher-level application (likely a UI).

*   **Abstraction:** It hides the network details of individual Sonarr/Radarr instances. The client only needs to know the address of the Toolarr server and which named instance it wants to talk to (e.g., "sonarr-4k").
*   **Unified API:** It provides a consistent API structure for both Sonarr and Radarr, even though their underlying APIs might have minor differences.
*   **Dynamic Instance Loading:** The application dynamically loads the configured Sonarr and Radarr instances from environment variables at startup, making it easy to add or remove instances without code changes.
*   **AI Integration Issues:** The presence of `fix_generic_endpoint.py` and the `deprecated_update_tags_redirect` in `radarr.py` strongly suggests that this tool is being used by an AI agent that sometimes confuses Sonarr and Radarr endpoints. The redirect is a workaround to handle these incorrect API calls gracefully.

## 7. Areas of Uncertainty

*   **`quick-deploy.sh`:** The exact contents of this script are unknown, but it's highly likely a convenience script that automates the build, push, and deploy steps.
## 8. Radarr Code Analysis and Corrections

*   **Initial State:** The `radarr.py` file contained several issues that were the root cause of the AI confusion and deployment failures.
*   **Key Issues Found:**
    1.  **Confusing Redirect:** A deprecated redirect from `/series/{series_id}/tags` to `/movie/{movie_id}/tags` was present. This was a symptom-fix that created ambiguity.
    2.  **Duplicate Functions:** The `get_tags` and `create_tag` functions were defined twice.
    3.  **Incorrect Update Logic:** The `update_movie` function had incorrect logic copied from `sonarr.py` related to moving files.
    4.  **Generic `operation_id`:** The `delete_from_queue` function had a generic `operation_id` that could conflict with Sonarr's.
    5.  **Pydantic Model Error:** The `MoveMovieRequest` class had a syntax error (`pass` on the wrong line) that was causing the application to crash on startup.
*   **Corrections Made:**
    1.  Removed the deprecated redirect.
    2.  Removed the duplicate functions, keeping the ones with the more specific `operation_id`s.
    3.  Corrected the logic in the `update_movie` function.
    4.  Updated the `operation_id` for `delete_from_queue` to `delete_radarr_queue_item`.
    5.  Fixed the syntax error in the `MoveMovieRequest` Pydantic model.
*   **Outcome:** The `radarr.py` module is now cleaner, more correct, and less ambiguous, which should resolve the AI's confusion and prevent future errors.

## 9. Sonarr Code Analysis and Corrections

*   **Initial State:** The `sonarr.py` file was in better condition than `radarr.py`, but still had minor issues.
*   **Key Issues Found:**
    1.  **Dead Code:** An unused `update_series` function was present, which was a remnant of earlier development.
    2.  **Generic `operation_id`:** The `delete_from_queue` function had a generic `operation_id` (`delete_queue_item`) that could conflict with Radarr's.
*   **Corrections Made:**
    1.  Removed the unused `update_series` function.
    2.  Updated the `operation_id` for `delete_from_queue` to `delete_sonarr_queue_item` for clarity and consistency.
*   **Outcome:** The `sonarr.py` module is now cleaner and more consistent with the rest of the application.
