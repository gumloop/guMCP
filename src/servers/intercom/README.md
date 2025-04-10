# Intercom Server

guMCP server implementation for interacting with Intercom customer messaging and support platform.

### Prerequisites

- Python 3.11+
- An Intercom App ([Intercom OAuth Authentication](https://developers.intercom.com/building-apps/docs/setting-up-oauth))

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```json
local_auth/oauth_configs/intercom/oauth.json
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

1. Redirect to Intercom's authorization URL with your configured credentials
2. Exchange the received code for an access token using Intercom's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/intercom/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.