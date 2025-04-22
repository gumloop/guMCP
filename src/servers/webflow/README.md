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