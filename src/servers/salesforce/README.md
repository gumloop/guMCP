
# Salesforce Server

guMCP server implementation for interacting with Salesforce.

---

## 🚀 Prerequisites

- Python 3.11+
- A Salesforce Developer Account ([Sign up for Developer Edition](https://developer.salesforce.com/signup))
- A Connected App in Salesforce with OAuth enabled

---

## 🔧 Creating a Salesforce Connected App

Follow these steps to create a Connected App in Salesforce and obtain the credentials:

1. **Login to Salesforce Developer Account**
   - Visit: https://developer.salesforce.com/signup

2. **Navigate to App Manager**
   - Click on the gear icon ⚙️ → **Setup**
   - Search for **App Manager** in the Quick Find box
   - Click **New Connected App**

3. **Basic Information**
   - Fill in the **Connected App Name** (e.g., `guMCP App`)
   - Fill in **API Name** (auto-filled)
   - Provide a valid **Contact Email**

4. **Enable OAuth Settings**
   - Scroll to **API (Enable OAuth Settings)** and check ✅ `Enable OAuth Settings`
   - **Callback URL (redirect URI)**:
     - (e.g., `http://localhost:8080`)
   - **Selected OAuth Scopes**:
     Add the required scopes

5. **Save and Continue**
   - Click **Save**. It may take 2-10 minutes to activate.

6. **Get Client ID and Secret**
   - Once saved, open your Connected App from the App Manager
   - Go to **View** → You’ll find your:
     - **Consumer Key** (Client ID)
     - **Consumer Secret** (Client Secret)

---

## 🔐 Local Authentication Setup

Create the following file:

```
local_auth/oauth_configs/salesforce/oauth.json
```

Example content:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri",
  "login_domain":"your-company.my.salesforce.com" # This is optional, add this only if you have custom login subdomain (ex.)

}
```

---

## 🧪 Verify Authentication

To initiate the auth flow:

```bash
python src/servers/salesforce/main.py auth
```

---

## 🛠️ Available Tools

1. **SOQL Query** (`soql_query`)
   - Retrieve records using Salesforce Object Query Language

2. **SOSL Search** (`sosl_search`)
   - Full-text search across multiple objects

3. **Object Description** (`describe_object`)
   - Retrieves metadata like field types, required fields, picklists

4. **Record Operations**
   - `get_record`: Retrieve by ID
   - `create_record`: Add new record
   - `update_record`: Modify existing
   - `delete_record`: Delete record

5. **Organization Limits** (`get_org_limits`)
   - API usage stats and limits overview

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Salesforce MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/salesforce/local
```

---

## 🔐 Security Notes

- Keep OAuth credentials private
- Use only necessary scopes
- Rotate `client_secret` periodically
- Monitor usage to avoid quota issues
