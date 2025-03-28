# Outlook Server

GuMCP server implementation for interacting with Microsoft Outlook.

### Prerequisites

- Python 3.11+
- A Microsoft Entra ID (formerly Azure AD) application registration
- OAuth 2.0 credentials with the following scopes:
  - https://graph.microsoft.com/Mail.ReadWrite
  - https://graph.microsoft.com/Mail.Send
  - offline_access

### Local Authentication

1. [Register a new application in Microsoft Entra ID](https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app?tabs=certificate%2Cexpose-a-web-api)
2. Add the required Microsoft Graph API permissions (Mail.ReadWrite, Mail.Send)
3. Configure a redirect URI for your application (e.g., http://localhost:8080)
4. Get your application's client ID and client secret
5. Create an `oauth.json` file:

```
local_auth/oauth_configs/outlook/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "https://xxxxxxxxxxxxx"
}
```

6. To set up and verify authentication, run:

```bash
python src/servers/outlook/main.py auth
```

### Run

#### Local Development

```bash
python src/servers/local.py --server outlook --user-id local
```
