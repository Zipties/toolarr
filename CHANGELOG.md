# Changelog

## [1.6.0] - 2025-07-16

### Features
- Added an endpoint to monitor and unmonitor movies in Radarr.
- Added endpoints to monitor and unmonitor series and individual seasons in Sonarr.

### Bug Fixes
- Fixed a bug where unmonitoring a series in Sonarr would not cascade the change to all seasons.
- Added explicit `operationId`s to new endpoints to prevent issues with auto-generated names being too long.

### [1.5.0] - 2025-07-16

### Features
- Added an endpoint to delete movies from Radarr.
- Added an endpoint to delete series from Sonarr.

### Bug Fixes
- The application now correctly handles empty responses from the Radarr and Sonarr APIs, preventing crashes on successful deletions.
- Corrected an issue where the AI would not provide human-readable tag names for Radarr, making the output inconsistent with Sonarr.

### Documentation
- Improved the docstrings for the library search functions to ensure the AI consistently uses the correct tool for resolving tag IDs.