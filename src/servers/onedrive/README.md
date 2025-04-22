# OneDrive Server

guMCP server implementation for interacting with Microsoft OneDrive.

### Prerequisites

- Python 3.11+
- A Microsoft Entra ID (formerly Azure AD) application registration
- OAuth 2.0 credentials with the following scopes:
  - https://graph.microsoft.com/.default
  - offline_access

### Features

- List files and folders in OneDrive
- Upload files to OneDrive
- Download files from OneDrive
- Create new folders
- Delete files and folders
- Search for files
- Generate sharing links (view-only or edit access)

### Local Authentication

1. [Register a new application in Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate%2Cexpose-a-web-api)
2. Add the required Microsoft Graph API permissions. Add it as a "Delegated" permission. (Files.ReadWrite.All)
3. Configure a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Create an `oauth.json` file:

```
local_auth/oauth_configs/onedrive/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri" e.g. `http://localhost:8080`
}
```

6. To set up and verify authentication, run:

```bash
python src/servers/onedrive/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server onedrive --user-id local
```

### Available Tools

1. `list_files`

   - Lists files and folders in a specified OneDrive directory
   - Default path is root "/"

2. `upload_file`

   - Uploads a local file to OneDrive
   - Requires local file path and destination path

3. `download_file`

   - Downloads a file from OneDrive to local storage
   - Requires OneDrive file path and local destination path

4. `create_folder`

   - Creates a new folder in OneDrive
   - Requires parent folder path and new folder name

5. `delete_item`

   - Deletes a file or folder from OneDrive
   - Requires path to the item to delete

6. `search_files`

   - Searches for files in OneDrive
   - Requires search term

7. `get_file_sharing_link`
   - Generates a sharing link for a file
   - Can create view-only or edit links
   - Requires file path

### 📎 Notes

- Ensure your Microsoft Entra ID application has the correct API permissions (Files.ReadWrite.All) configured.
- The OAuth configuration file should be kept secure and not committed to version control.
- Make sure your redirect URI matches exactly what's configured in your Microsoft Entra ID application.

### 📚 Resources

- [Microsoft Graph API Documentation](https://learn.microsoft.com/en-us/graph/overview)
- [OneDrive API Reference](https://learn.microsoft.com/en-us/onedrive/developer/rest-api/)
