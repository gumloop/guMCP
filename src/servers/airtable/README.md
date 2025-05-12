# Airtable Server

guMCP server implementation for interacting with Airtable.

### Prerequisites

- Python 3.11+
- An Airtable account and API access
- An Airtable OAuth application with the following scopes (see [Airtable OAuth documentation](https://airtable.com/developers/web/guides/oauth-integrations)):
  - data.records:read
  - data.records:write
  - schema.bases:read
  - schema.bases:write

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```
local_auth/oauth_configs/airtable/oauth.json
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
python src/servers/airtable/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server airtable --user-id local
```
