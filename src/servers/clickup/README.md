# ClickUp Server

guMCP server implementation for interacting with ClickUp task management.

### Prerequisites

- Python 3.11+
- A ClickUp App ([ClickUp API Authentication](https://clickup.com/api/developer-portal/authentication/))

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```json
local_auth/oauth_configs/clickup/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "xxxxxxxxxxxxxxxxxxxxx"
}
```

When authorizing users, the server will automatically:

1. Redirect to ClickUp's authorization URL with your configured credentials
2. Exchange the received code for an access token using ClickUp's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/clickup/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
