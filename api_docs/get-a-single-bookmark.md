# Get a Single Bookmark

**API Endpoint**
`GET https://try.karakeep.app/api/v1/bookmarks/:bookmarkId`

**Path Parameters**
*   `bookmarkId` (string, required): The ID of the bookmark to retrieve.

**Query Parameters**
*   `includeContent` (boolean): Include the bookmark's content in the response. Default is `true`.

**Responses**
A `200` response will return the bookmark object. A `404` response will be returned if the bookmark is not found.
