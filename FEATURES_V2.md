# Sonarr Tool Server v2.0 - Feature Summary

## New Capabilities for Open WebUI

Your AI assistant can now:

### 1. Query Series Information
- **List all series**: Get complete library with quality profiles and root folders
- **Get specific series details**: Including statistics, seasons, and tags
- **Search for new series**: Check if already in library

### 2. Manage Series Settings
- **Change root folder**: Move series to different storage locations
- **Update quality profile**: Change from HD to 4K, etc.
- **Manage tags**: Add/remove tags for organization
- **Move files**: Physically relocate files when changing root folder

### 3. Episode Management
- **List all episodes**: See what's available and what's missing
- **Monitor/unmonitor episodes**: Individual or bulk operations
- **Check for missing episodes**: See what needs downloading
- **Search for missing episodes**: Trigger downloads

### 4. Season Management
- **Monitor/unmonitor entire seasons**: Enable or disable seasons
- **View season statistics**: Episode counts, file counts

### 5. Missing Content
- **List missing episodes**: For all series or specific ones
- **Trigger searches**: Download missing episodes automatically

### 6. Organization
- **Create and manage tags**: Organize your library
- **View quality profiles**: See available quality options
- **Check storage locations**: View available root folders

## Example AI Queries

- "What quality profile is Knight Rider using?"
- "Move Knight Rider to the private TV folder"
- "Show me all missing episodes for Knight Rider"
- "Unmonitor season 4 of Knight Rider"
- "Search for all missing episodes"
- "Add the tag 'Classic' to Knight Rider"
- "What episodes are missing from my library?"

## API Endpoints

### Series Management
- GET `/sonarr/series` - List all series
- GET `/sonarr/series/{id}` - Get series details
- PUT `/sonarr/series/{id}` - Update series (move, quality, tags)
- POST `/sonarr/series` - Add new series

### Episode Management
- GET `/sonarr/episodes?series_id={id}` - List episodes
- PUT `/sonarr/episodes/{id}` - Update single episode
- PUT `/sonarr/episodes/monitor` - Bulk update episodes

### Season Management
- PUT `/sonarr/series/{id}/season` - Update season monitoring

### Missing Content
- GET `/sonarr/wanted/missing` - List missing episodes
- POST `/sonarr/wanted/missing/search` - Search for missing

### Utilities
- GET `/sonarr/tags` - List tags
- POST `/sonarr/tags` - Create tag
- GET `/sonarr/qualityprofiles` - List quality profiles
- GET `/sonarr/rootfolders` - List root folders
- POST `/sonarr/command` - Execute Sonarr commands
