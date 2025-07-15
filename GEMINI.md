# Sonarr Tool Server Ramp-Up Guide

This document provides a quick ramp-up for developers working on the Sonarr Tool Server.

## Project Overview

This project is a FastAPI-based server that provides a tool API for interacting with a Sonarr instance. It's designed to be used as a backend for other applications, such as an Open WebUI, to manage Sonarr's library.

## Tech Stack

*   **Backend:** Python 3 with FastAPI
*   **HTTP Client:** httpx
*   **Containerization:** Docker & Docker Compose

## Key Files

*   `main.py`: The core FastAPI application, containing all API endpoints and logic.
*   `docker-compose.yml`: Defines the Docker service for running the server.
*   `requirements.txt`: Lists the Python dependencies.
*   `.env.production`: Contains the necessary environment variables for connecting to Sonarr and securing the tool's API.
*   `openapi.json`: The OpenAPI schema for the API.

## Getting Started

### 1. Prerequisites

*   Docker and Docker Compose must be installed.

### 2. Configuration

Create a `.env` file (or use `.env.production`) and fill in the following variables:

```bash
TOOL_API_KEY=<Your secret API key for this tool>
SONARR_URL=<URL of your Sonarr instance (e.g., http://sonarr:8989)>
SONARR_API_KEY=<Your Sonarr API key>
```

### 3. Running the Server

To build and start the server, run:
```bash
docker-compose up -d --build
```

To apply changes and restart the server:
```bash
docker-compose up -d --force-recreate
```

### 4. Accessing the API Docs

Once running, the interactive API documentation (provided by Swagger UI) is available at [http://localhost:8085/docs](http://localhost:8085/docs).

## Core Functionality

The server exposes several endpoints to manage a Sonarr instance:

*   **Series Management:** Search, add, update, and move TV series.
*   **Library Information:** List existing series, root folders, and tags.
*   **Tagging:** Create and assign tags to series.
