# Slack Server

guMCP server implementation for interacting with Slack.

### Prerequisites

- Python 3.11+
- A Slack App ([Create Slack App](https://api.slack.com/quickstart#creating)) with the following scopes:
  - channels:history
  - channels:read
  - chat:write
  - chat:write.customize
  - groups:read
  - groups:write
  - groups:history
  - pins:read
  - pins:write
  - reactions:write
  - files:read
  - files:write
  - im:read
  - channels:manage
  - users:read

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```
local_auth/oauth_configs/slack/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://xxxxxxxxxxxxx"
}
```

- Note: Slack requires https for the redirect uri, so if running locally, setup an [ngrok redirect](https://ngrok.com/docs/universal-gateway/http/) to port 8080

To set up and verify authentication, run:

```bash
python src/servers/slack/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server slack --user-id local
```
