# X Server

guMCP server implementation for interacting with X (formerly Twitter).

### Prerequisites

- Python 3.11+
- An X Developer Account with API access ([X Developer Portal](https://developer.twitter.com/en))
- A Project and App with OAuth 2.0 authentication

### Local Authentication

Local authentication uses an OAuth Configuration JSON file:

```
local_auth/oauth_configs/x/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://xxxxxxxxxxxxx"
}
```

To set up and verify authentication, run:

```bash
python src/servers/x/main.py auth
```
