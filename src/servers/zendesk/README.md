# Zendesk Server

guMCP server implementation for interacting with Zendesk.

### Prerequisites

- Python 3.11+
- A Zendesk account with API access
- A Zendesk OAuth application with the following scopes:
  - read
  - write

### Local Authentication

Local authentication uses an OAuth Configuration JSON file:

```
local_auth/oauth_configs/zendesk/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://xxxxxxxxxxxxx",
  "custom_subdomain": "your-subdomain"
}
```

Notes:
- The `custom_subdomain` is your Zendesk subdomain (e.g., if your Zendesk URL is `example.zendesk.com`, use `example`)


To set up and verify authentication, run:

```bash
python src/servers/zendesk/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
