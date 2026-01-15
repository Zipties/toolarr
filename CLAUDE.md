# Toolarr MCP Test Environment

You have access to the Toolarr MCP server which provides tools for managing Sonarr and Radarr.

## Available Tools

### Sonarr Tools (TV Shows)
- `mcp__toolarr__sonarr_list_series` - List all series in library
- `mcp__toolarr__sonarr_lookup_series` - Search for series (params: `term`)
- `mcp__toolarr__sonarr_get_series` - Get series by ID (params: `series_id`)
- `mcp__toolarr__sonarr_get_episodes` - Get episodes for series (params: `series_id`)
- `mcp__toolarr__sonarr_get_episode` - Get episode by ID (params: `episode_id`)
- `mcp__toolarr__sonarr_get_releases` - Get available releases for episode (params: `episode_id`)
- `mcp__toolarr__sonarr_grab_release` - Download a release (params: `guid`)
- `mcp__toolarr__sonarr_get_queue` - Get download queue
- `mcp__toolarr__sonarr_get_history` - Get download history
- `mcp__toolarr__sonarr_get_quality_profiles` - List quality profiles
- `mcp__toolarr__sonarr_get_root_folders` - List root folders
- `mcp__toolarr__sonarr_get_tags` - List tags
- `mcp__toolarr__sonarr_system_status` - Get system status

### Radarr Tools (Movies)
- `mcp__toolarr__radarr_list_movies` - List all movies in library
- `mcp__toolarr__radarr_lookup_movie` - Search for movies (params: `term`)
- `mcp__toolarr__radarr_get_movie` - Get movie by ID (params: `movie_id`)
- `mcp__toolarr__radarr_get_releases` - Get available releases for movie (params: `movie_id`)
- `mcp__toolarr__radarr_grab_release` - Download a release (params: `guid`)
- `mcp__toolarr__radarr_get_queue` - Get download queue
- `mcp__toolarr__radarr_get_history` - Get download history
- `mcp__toolarr__radarr_get_quality_profiles` - List quality profiles
- `mcp__toolarr__radarr_get_root_folders` - List root folders
- `mcp__toolarr__radarr_get_tags` - List tags
- `mcp__toolarr__radarr_get_exclusions` - List excluded movies
- `mcp__toolarr__radarr_get_import_lists` - List import lists
- `mcp__toolarr__radarr_system_status` - Get system status

## Test Tasks

When asked to test, try these operations:
1. Look up a series like "Severance" and find available releases for an episode
2. Check the download queue for both Sonarr and Radarr
3. List quality profiles available
4. Look up a movie and find releases for it

Report your findings clearly with counts and key details.
