# Agent Test: Toolarr Approach

You are testing the Toolarr API gateway for Sonarr control.

## Your Tools

You have access to a REST API at `http://localhost:8010` with Bearer token `toolarr-benchmark-key-2026`.

Available endpoints:
- GET `/sonarr/sonarr/lookup?term=X` - Search for a series
- GET `/sonarr/sonarr/series` - List all series in library
- GET `/sonarr/sonarr/qualityprofiles` - List quality profiles
- GET `/sonarr/sonarr/queue` - Get download queue

## Your Task

1. Search for the TV show "Severance"
2. Check if it already exists in the Sonarr library
3. Get the list of available quality profiles
4. Report back: Does "Severance" exist? What's its TVDB ID? What quality profiles are available?

## Rules

- Use curl with the Bearer token header
- Parse JSON responses with jq
- Be efficient - don't make unnecessary API calls
- Report any errors you encounter

Go!
