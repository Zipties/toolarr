# Agent Test: Skills Approach (Direct API)

You are testing direct Sonarr API access via curl/jq.

## API Details

- Sonarr URL: `http://192.168.45.15:8083`
- API Key: `7ce61d72c943483ca03864e03f013127`
- API Version: v3

## Your Task

1. Search for the TV show "Severance"
2. Check if it already exists in the Sonarr library
3. Get the list of available quality profiles
4. Report back: Does "Severance" exist? What's its TVDB ID? What quality profiles are available?

## Rules

- Use curl to hit the Sonarr API directly
- Always include `apikey=YOUR_KEY` in query params
- URL-encode search terms (spaces become %20)
- Parse JSON responses with jq
- Be efficient - don't make unnecessary API calls
- Report any errors you encounter

## API Endpoints Reference

- Search: `/api/v3/series/lookup?term=X&apikey=KEY`
- Library: `/api/v3/series?apikey=KEY`
- Profiles: `/api/v3/qualityprofile?apikey=KEY`

Go!
