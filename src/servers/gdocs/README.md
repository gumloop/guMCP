# Google Docs Server

GuMCP server implementation for interacting with Google Docs.

### Prerequisites

- Python 3.11+
- A Google Cloud Project with Google Drive and Google Docs APIs enabled
- OAuth 2.0 credentials with the following scopes:
  - https://www.googleapis.com/auth/drive.file
  - https://www.googleapis.com/auth/documents

### Local Authentication

1. [Create a new Google Cloud project](https://console.cloud.google.com/projectcreate)
2. [Enable the Google Drive API and Google Docs API](https://console.cloud.google.com/workspace-api/products)
3. [Configure an OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent) ("internal" is fine for testing)
4. Add OAuth scopes:
   - https://www.googleapis.com/auth/drive.file
   - https://www.googleapis.com/auth/documents
5. [Create an OAuth Client ID](https://console.cloud.google.com/apis/credentials/oauthclient) for application type "Desktop App"
6. Download the JSON file of your client's OAuth keys
7. Rename the key file to `oauth.json` and place into the `local_auth/oauth_configs/gdocs/oauth.json`

To authenticate and save credentials:

```bash
python src/servers/gdocs/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
