# PagerDuty Server

guMCP server implementation for interacting with PagerDuty incident management and on-call scheduling.

## Prerequisites

- Python 3.11+
- A PagerDuty account with API access
- PagerDuty API credentials ([PagerDuty API Documentation](https://developer.pagerduty.com))

## OAuth Configuration

1. In your PagerDuty developer portal, click on `New App`
2. Choose OAuth 2.0 in functionality and fill others as required
3. Click on register app > choose classic user oauth
4. Add required redirect URL and scope and click on register

## Local Authentication

Local authentication uses OAuth 2.0 for PagerDuty:

```json
local_auth/oauth_configs/pagerduty/oauth.json
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

1. Redirect to PagerDuty's authorization URL with your configured credentials
2. Exchange the received code for an access token using PagerDuty's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/pagerduty/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
