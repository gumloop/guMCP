# Figma Server

guMCP server implementation for interacting with the Figma API.

### Prerequisites

- Python 3.7+
- A Figma account
- OAuth 2.0 credentials with the following scopes:
  - files:read
  - files:write
  - comments:read
  - comments:write

### Features

- Get user information
- Access and manage Figma files
- View and manage file comments
- Add and remove comment reactions
- Access team projects and files
- View file version history

### Local Authentication

1. [Create a Figma OAuth app](https://www.figma.com/developers/api#oauth2)
2. Configure your OAuth app with the required scopes
3. Set up a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Create an `oauth.json` file:

```
local_auth/oauth_configs/figma/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "redirect_uri": "your_redirect_uri"
}
```

6. To set up and verify authentication, run:

```bash
python src/servers/figma/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server figma --user-id local
```

### Available Tools

1. `get_me`

   - Gets the authenticated user's information
   - Returns user details including ID, handle, and email

2. `get_file`

   - Retrieves a Figma file by its key
   - Returns file information and content
   - Required parameter: `file_key`

3. `get_file_comments`

   - Lists comments for a specific Figma file
   - Optional parameter: `as_md` to return comments as markdown
   - Required parameter: `file_key`

4. `post_comment`

   - Adds a comment to a Figma file
   - Required parameters: `file_key`, `message`
   - Optional parameters: `client_meta`, `parent_id`

5. `delete_comment`

   - Removes a comment from a Figma file
   - Required parameters: `file_key`, `comment_id`

6. `get_comment_reactions`

   - Lists reactions for a specific comment
   - Required parameters: `file_key`, `comment_id`
   - Optional parameter: `cursor` for pagination

7. `post_comment_reaction`

   - Adds a reaction to a comment
   - Required parameters: `file_key`, `comment_id`, `emoji`

8. `delete_comment_reaction`

   - Removes a reaction from a comment
   - Required parameters: `file_key`, `comment_id`, `emoji`

9. `get_team_projects`

   - Lists all projects within a team
   - Required parameter: `team_id`

10. `get_project_files`

    - Lists files in a specific project
    - Required parameter: `project_id`
    - Optional parameter: `branch_data`

11. `get_file_versions`
    - Retrieves version history for a file
    - Required parameter: `file_key`

### Error Handling

The server provides detailed error messages for:

- Authentication failures
- Invalid tool names
- Missing required parameters
- API errors from Figma
