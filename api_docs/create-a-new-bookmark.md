# Create a New Bookmark

**API Endpoint**
`POST https://try.karakeep.app/api/v1/bookmarks`

**Request Body**
The request body should be a JSON object with the following properties:

*   `type` (string, required): The type of bookmark. Must be one of `link`, `text`, or `asset`.
*   `url` (string): The URL of the bookmark. Required if `type` is `link`.
*   `title` (string): The title of the bookmark.
*   `description` (string): A description of the bookmark.
*   `tags` (array of strings): A list of tags to apply to the bookmark.

**Responses**
A `201` response will be returned if the bookmark is created successfully. The response body will contain the new bookmark object.
