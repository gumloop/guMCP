# Attio Server

GuMCP server implementation for interacting with Attio.

### Prerequisites

- Python 3.11+
- An Attio account and API access
- An Attio OAuth App key with appropriate permissions for (see [Attio API documentation](https://developers.attio.com/docs/integrations)):
  - Reading companies and contacts
  - Writing companies and contacts
  - Managing lists

### Local Authentication

Local authentication uses an API key configuration JSON file:

```
local_auth/oauth_configs/attio/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "http://xxxxxxxxxxxxx"
}
```

To set up and verify authentication, run:

```bash
python src/servers/attio/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server attio --user-id local
```
