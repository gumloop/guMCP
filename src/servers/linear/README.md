# Linear Server

GuMCP server implementation for interacting with Linear.

## Prerequisites

- Python 3.11+
- A Linear OAuth2 application ([Linear Developer Settings](https://linear.app/settings/api/applications))
- Appropriate OAuth2 scopes for reading and creating issues

## Authentication

Authentication uses OAuth2 and requires a configuration file:

```
local_auth/oauth_configs/linear/oauth.json
```

```json
{
  "client_id": "YOUR_LINEAR_APP_CLIENT_ID",
  "client_secret": "YOUR_LINEAR_APP_CLIENT_SECRET",
  "redirect_uri": "http://localhost:8080/callback"
}
```

### Setting Up Your Linear Application

1. Go to [Linear Developer Settings](https://linear.app/settings/api/applications)
2. Create a new OAuth application:
   - Provide a name for your application
   - Add `http://localhost:8080/callback` as a redirect URI
   - Enable the following scopes:
     - `read` - For reading issues and workspace data
     - `write` - For updating issues
     - `issues:create` - For creating new issues
   - Save changes
3. Note your Client ID and Client Secret

### Running Authentication

To set up authentication:

```bash
python src/servers/linear/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.


## Run

### Local Development

```bash
python src/servers/local.py --server linear --user-id local
```