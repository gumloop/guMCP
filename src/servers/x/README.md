# X Server

GuMCP server implementation for interacting with X (formerly Twitter).

### Prerequisites

- Python 3.11+
- An X Developer Account with a Project ([Create X Project](https://developer.x.com/en/portal/dashboard)) with the following scopes:
  - tweet.read
  - tweet.write
  - users.read
  - offline.access

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```
local_auth/oauth_configs/x/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "http://localhost:8080"
}
```

To set up and verify authentication, run:

```bash
python src/servers/x/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server x --user-id local
```
