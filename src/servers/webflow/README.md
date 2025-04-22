# Webflow Server

guMCP server implementation for interacting with Webflow sites and content management.

### Prerequisites

- Python 3.11+
- A Webflow account and application ([Webflow OAuth Authentication](https://webflow.com/dashboard/workspace))


### OAuth Setup

1. Log into your Webflow dashboard and click on **Integrations**
2. Click **Create an App** and fill in the necessary information
3. Navigate to **Building Blocks** > **Data Client** and enable the following scopes:
   - `authorized_user:read`
   - `sites:read`
   - `forms:read`
   - `forms:write`
   - `pages:read`
   - `cms:read`
   - `cms:write`
   - `users:read`
   - `users:write`
4. Add your redirect URI (e.g., `http://localhost:8000/callback`) and create your app
5. Save your Client ID and Client Secret for local authentication

### Local Authentication

Local authentication uses an OAuth Configuration JSON file:

```json
local_auth/oauth_configs/webflow/oauth.json
```

Create the following file with the relevant attributes from your Webflow app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "xxxxxxxxxxxxxxxxxxxxx"
}
```

When authorizing users, the server will automatically:

1. Redirect to Webflow's authorization URL with your configured credentials
2. Exchange the received code for an access token using Webflow's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/webflow/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.

### Available Tools

The Webflow server provides tools to interact with the Webflow API:

#### User Management
- `get_authorized_user` - Get information about the authorized Webflow user
- `list_users` - Get a list of users for a site
- `get_user` - Get a User by ID
- `delete_user` - Delete a User by ID
- `invite_user` - Create and invite a user with an email address

#### Site Management
- `list_sites` - List all sites the access token can access
- `get_site` - Get details of a specific site by ID
- `get_custom_domains` - Get a list of all custom domains for a site

#### Forms and Submissions
- `list_forms` - List forms for a given site
- `list_form_submissions` - List form submissions for a given form
- `get_form_submission` - Get information about a specific form submission
- `list_form_submissions_by_site` - List form submissions for a given site
- `delete_form_submission` - Delete a form submission

#### Pages
- `list_pages` - List all pages for a site
- `get_page_metadata` - Get metadata information for a single page
- `get_page_content` - Get content from a static page

#### Collections
- `list_collections` - List all Collections within a Site
- `get_collection` - Get the full details of a collection from its ID
- `delete_collection` - Delete a collection using its ID
- `create_collection` - Create a Collection for a site

### Response Handling

All API responses contain a `_status_code` field that indicates the HTTP status of the request:
- 200: Success with data
- 204: Success with no content (common for delete operations)
- 4xx/5xx: Error conditions

For collection operations:
- `get_collection` returns collection details including `name`, `slug`, `fields`, etc.
- `delete_collection` returns a 204 status code on success with no content body
- When creating or updating collections, verify field validations (e.g., `maxLength`, `pattern`) to avoid errors

### Example Usage

To list all your Webflow sites:

```
Call the list_sites tool without any parameters.
```

To get details about a specific site:

```
Call the get_site tool with the site_id parameter.
```

To list form submissions:

```
Call list_form_submissions with the form_id parameter.
```

