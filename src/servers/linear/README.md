# Linear Server

GuMCP server implementation for interacting with Linear issue tracking.

### Prerequisites

- Python 3.11+
- A Linear App ([Linear OAuth Authentication](https://developers.linear.app/docs/oauth/authentication))

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```json
local_auth/oauth_configs/linear/oauth.json
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

1. Redirect to Linear's authorization URL with your configured credentials
2. Exchange the received code for an access token using Linear's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/linear/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
