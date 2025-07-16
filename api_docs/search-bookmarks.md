# Search Bookmarks

**API Endpoint**
`GET https://try.karakeep.app/api/v1/search`

**Query Parameters**
*   `query` (string, required): The search query.
*   `limit` (number): The number of results to return.
*   `cursor` (Cursor): For pagination.

**Responses**
A `200` response will return an object with the search results. The response includes a `results` array and a `nextCursor` for pagination. Each result object in the array contains details about the matched bookmark.
