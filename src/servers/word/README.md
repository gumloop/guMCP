# Word Server

guMCP server implementation for interacting with Microsoft Word documents stored in OneDrive.

### Prerequisites

- Python 3.11+
- A Microsoft account with OneDrive access
- OAuth Application in Microsoft Entra ID (formerly Azure AD)

### OAuth Setup with Microsoft Entra ID

1. Sign in to the [Microsoft Azure Portal](https://portal.azure.com)
2. Navigate to Microsoft Entra ID (Azure Active Directory) by visiting: [https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/Overview](https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/~/Overview)
3. Click on **App registrations** in the left menu, then click **+ New registration**
4. Provide a name for your application, select the appropriate account type (typically "Accounts in any organizational directory and personal Microsoft accounts"), and set the redirect URI to `http://localhost:8080` (type: Web)
5. Click **Register** to create the application
6. Copy the **Application (client) ID** displayed on the overview page - this will be your client ID
7. Under **Certificates & secrets** in the left menu, click **+ New client secret**
8. Provide a description, select an expiration period, and click **Add**
9. **Important**: Immediately copy the generated secret **Value** (it will only be shown once) - this will be your client secret
10. Navigate to **API permissions** in the left menu and click **+ Add a permission**
11. Select **Microsoft Graph** > **Delegated permissions**
12. Add the following permissions:
    - `Files.ReadWrite`
    - `Sites.ReadWrite.All`
    - `offline_access`
13. Click **Add permissions** and then **Grant admin consent** if you have admin rights

### Local Authentication

Local authentication uses an OAuth Configuration JSON file:

```json
local_auth/oauth_configs/word/oauth.json
```

Create the following file with the relevant attributes from your Entra ID app:

```json
{
  "client_id": "your_application_client_id_here",
  "client_secret": "your_client_secret_value_here",
  "redirect_uri": "http://localhost:8080"
}
```

When authorizing users, the server will automatically:

1. Redirect to Microsoft's authorization URL with your configured credentials
2. Exchange the received code for an access token using Microsoft's OAuth endpoints

For local development, you can authenticate using:

```bash
python src/servers/word/main.py auth
```

This will launch a browser-based authentication flow to obtain and save credentials.
