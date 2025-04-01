# HubSpot Server

guMCP server implementation for interacting with HubSpot CRM.

### Prerequisites

- Python 3.11+
- A HubSpot Developer Account ([HubSpot Developer Portal](https://developers.hubspot.com/))
- A HubSpot App with OAuth 2.0 configured

### Required Scopes

The following OAuth scopes are required for the server to function:

- `crm.objects.contacts.read` - Read access to contacts
- `crm.objects.contacts.write` - Write access to contacts
- `crm.objects.companies.read` - Read access to companies
- `crm.objects.companies.write` - Write access to companies
- `crm.objects.deals.read` - Read access to deals
- `crm.objects.deals.write` - Write access to deals

### Local Authentication

Local authentication uses a OAuth Configuration JSON file:

```json
local_auth/oauth_configs/hubspot/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "xxxxxxxxxxxxxxxxxxxxx"
}
```

To authenticate and save credentials:

```bash
python src/servers/hubspot/main.py auth
```
