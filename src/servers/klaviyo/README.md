# Klaviyo Server

guMCP server implementation for interacting with Klaviyo for email marketing, customer engagement, and audience management.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Klaviyo Account** – [Sign up here](https://www.klaviyo.com/)

---

### 🔐 Klaviyo API Setup (First-time Setup)

1. **Log in to your [Klaviyo Dashboard](https://www.klaviyo.com/dashboard)**
2. Go to **Integrations** → **[Manage Apps](https://www.klaviyo.com/manage-apps)**
3. Click on **"Create App"**
4. Fill out:
   - **App Name**: e.g., `guMCP Integration`
   - Copy the generated **Client ID** and **Client Secret**
5. Click **Continue**
6. Select the needed scopes:
   - `lists:read`
   - `lists:write`
   - `profiles:write`
   - `profiles:read`
   - `campaigns:write`
   - `campaigns:read`
   - `metrics:read`
7. Add your **Redirect URI**
8. Click **Save**

---

### 📄 Local OAuth Credentials

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/klaviyo/) with the following content:

```json
{
  "client_id": "your-client-id-from-app-creation", 
  "client_secret": "your-client-secret-from-app-creation",
  "redirect_uri": "your-redirect-uri-same-as-in-app-settings"
}
```

---

### 🔓 Authenticate with Klaviyo

Run the following command to initiate the OAuth login:

```bash
python src/servers/klaviyo/main.py auth
```

This will open your browser and prompt you to log in to Klaviyo. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/klaviyo/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 👤 Profile Management

- `create_profile` – Create a new profile with attributes
- `get_profile` – Get details of a specific profile
- `get_profiles` – Retrieve all profiles with filtering
- `update_profile` – Update an existing profile

#### 📧 Campaign Management

- `get_campaign` – Retrieve campaign details
- `list_campaigns` – List campaigns with filtering
- `update_campaign` – Modify an existing campaign
- `send_campaign` – Trigger a campaign to send
- `delete_campaign` – Remove a campaign

#### 📋 List Management

- `create_list` – Create a new list
- `get_list` – Get details of a specific list
- `get_lists` – Retrieve all lists with filtering
- `get_list_profiles` – Get profiles in a list
- `add_profiles_to_list` – Add profiles to a list
- `remove_profiles_from_list` – Remove profiles from a list

#### 📊 Analytics

- `list_metrics` – List metrics with filtering
- `get_metric` – Get details of a specific metric

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/klaviyo/local
```

---

### 📌 Notes on Klaviyo API Usage

- The API uses a Bearer token authentication
- Most requests use JSON API format
- Rate limits apply (consult Klaviyo's API documentation)
- Email templates can be created and reused
- Profiles can have custom attributes beyond standard fields