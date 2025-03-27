# Google Drive Server
MCP server implementation for interacting with Google Drive.

### Prerequisites

- Python 3.11+
- Google OAuth 2.0 credentials
- Google Drive API enabled in Google Cloud Console

### Authentication

Three authentication methods are supported:

1. **OAuth configuration file**:
   ```
   local_auth/oauth_configs/gdrive/oauth.json
   ```
   This file should contain your OAuth client configuration from Google Cloud Console.

2. **Environment variables**:
   ```bash
   export GOOGLE_OAUTH_CLIENT_ID=your_client_id
   export GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
   ```

3. **Interactive prompt** (local development only):
   ```bash
   python src/servers/gdrive/main.py auth
   ```
   This will launch a browser-based authentication flow to obtain and save credentials.

### Run

#### Local Development

```bash
python src/servers/local.py --server gdrive --user-id local
```