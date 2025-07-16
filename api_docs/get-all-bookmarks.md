# Get All Bookmarks

**API Endpoint**
`GET https://try.karakeep.app/api/v1/bookmarks`

**Query Parameters**
*   `archived` (boolean): Filter by archived status.
*   `favourited` (boolean): Filter by favorited status.
*   `sortOrder` (string): Sort order, either `asc` or `desc`. Default is `desc`.
*   `limit` (number): The number of bookmarks to return.
*   `cursor` (Cursor): For pagination.
*   `includeContent` (boolean): Include the bookmark's content in the response. Default is `true`.

**Responses**
A `200` response will return an object with all bookmarks data. The response includes a `bookmarks` array and a `nextCursor` for pagination. Each bookmark object in the array contains details like `id`, `createdAt`, `title`, `tags`, and `content`.
