# Typeform Server

guMCP server implementation for interacting with Typeform forms and responses.

### Prerequisites

- Python 3.11+
- A Typeform account (free or paid)
- Typeform API key with the following scopes:
  - forms:read
  - responses:read
  - workspaces:read

### Local Authentication

1. Follow the official [Typeform OAuth authentication guide](https://www.typeform.com/developers/get-started/applications/)
2. Select the required scopes:
   - forms:read
   - responses:read
   - workspaces:read
3. Copy the generated personal access token
4. Create a new file in the `local_auth/oauth_configs/typeform/oauth.json` directory with the following content:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "xxxxxxxxxxxxxxxxxxxxx"
}
```

To authenticate and save credentials:

```bash
python src/servers/typeform/main.py auth
```

This will launch a guided authentication flow to save your Typeform access token securely.
