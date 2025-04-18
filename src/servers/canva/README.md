# Canva Server

guMCP server implementation for interacting with the **Canva API**.

---

### 📦 Prerequisites

- Python 3.11+
- A **Canva Developer Account** – [Sign up here](https://www.canva.com/developers/)
- A registered **OAuth Integration** with OAuth 2.0 credentials

---

### 🔐 Canva OAuth Integration Setup (First-time Setup)

1. **Go to the [Canva Developers Page](https://www.canva.com/developers/)** and sign in.
2. Navigate to the **Integrations** tab.
3. If you haven't already, complete the **Multi-Factor Authentication (MFA)** setup as it's required to create an integration.
4. Click on **"Create an integration"** and select relevant type from **public** or **private**
5. Fill out the basic integration details:
   - **Integration name**
   - **Scopes**
   - **Redirect URI** – e.g. `http://127.0.0.1:8080` for local development
6. Generate Client Secret:
   - Copy your **Client ID**
   - Click on **Generate Secret** and copy the secret token
   - Make sure `http://127.0.0.1:8080` is listed in the Redirect URIs
7. Go to the **Scopes** tab and enable the required scopes:
   - `app:read`, `app:write`
   - `design:content:read`, `design:meta:read`, `design:content:write`
   - `design:permission:read`, `design:permission:write`
   - `folder:read`, `folder:write`
   - `folder:permission:read`, `folder:permission:write`
   - `asset:read`, `asset:write`
   - `comment:read`, `comment:write`
   - `brandtemplate:meta:read`, `brandtemplate:content:read`
   - `profile:read`

---

### 📄 Local OAuth Credentials

Create a file at:

```
local_auth/oauth_configs/canva/oauth.json
```

With content like:

```json
{
  "client_id": "your-client-id",
  "client_secret":"your-client-secret",
  "redirect_uri": "your-redirect-uri" e.g. `http://127.0.0.1:8080`
}
```

---

### 🔓 Authenticate with Canva

Run the following command to initiate the OAuth flow:

```bash
python src/servers/canva/main.py auth
```

This will open a browser and ask you to authenticate via Canva. On success, your credentials will be saved locally for future use.

---

### 🛠️ Supported Tools

#### 👤 User Management
- `get_user_profile` – Get the current user's profile information
- `get_user_details` – Get user details including IDs

#### 💬 Comment Management
- `get_thread` – Get metadata for a comment thread
- `create_reply` – Reply to a comment
- `create_thread` – Create new comment thread
- `list_replies` – List comment replies
- `get_reply` – Get specific reply

#### 🎨 Design Management
- `get_design` – Get design metadata
- `list_designs` – List all designs with filtering
- `create_design` – Create new design

#### 📁 Folder Management
- `create_folder` – Create new folder
- `get_folder` – Get folder metadata
- `update_folder` – Update folder name
- `delete_folder` – Delete folder

---

### ▶️ Run

#### Local Development

Start the server locally using:

```bash
./start_sse_dev_server.sh
```

Start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/canva/local
```

---

### 📎 Notes

- Ensure your Canva app has the correct **OAuth scopes** enabled:
  - `app:read`, `app:write`
  - `design:content:read`, `design:meta:read`, `design:content:write`
  - `design:permission:read`, `design:permission:write`
  - `folder:read`, `folder:write`
  - `folder:permission:read`, `folder:permission:write`
  - `asset:read`, `asset:write`
  - `comment:read`, `comment:write`
  - `brandtemplate:meta:read`, `brandtemplate:content:read`
  - `profile:read`
- If testing with multiple users or environments, use distinct `user_id` values
- Add any external API keys to a `.env` file if needed

---

### 📚 Resources

- [Canva API Documentation](https://www.canva.com/developers/docs/)
- [Canva OAuth 2.0 Guide](https://www.canva.com/developers/docs/oauth-2-0/)
