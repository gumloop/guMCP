# Patreon GuMCP Server

GuMCP server implementation for interacting with the Patreon API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Patreon Developer account with an API application created
- OAuth credentials configured for your application

---

### 🛠️ Step 1: Create a Patreon Developer Account

1. Go to [Patreon Developer Portal](https://www.patreon.com/portal/registration/register-clients)
2. Sign up for a developer account
3. Navigate to Client & API Keys section (top right corner)
4. Create a new Client
5. Add required details:
   - App name
   - Description
   - Redirect URI (e.g., `http://localhost:8080`)
   - Client API Version as `2.0`
   - All other fields are optional
6. Create the Client

---

### 🛠️ Step 2: Configure OAuth Settings

1. Once the Client is created, expand the Client section and copy the Client ID and Client Secret

---

### 🛠️ Step 3: Set Up Local Configuration

1. Create a new folder called `local_auth` in your project directory
2. Inside that, create a folder called `oauth_configs`
3. Inside that, create a folder called `patreon`
4. Create a new file called `oauth.json` in the `patreon` folder
5. Copy and paste this into the file, replacing the placeholders with your actual values:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here",
  "redirect_uri": "your-redirect-uri-here" e.g. `http://localhost:8080`
}
```

> ⚠️ **IMPORTANT**: Never share or commit this file to version control. Add it to your `.gitignore`.

---

### 🔐 Step 4: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/patreon/main.py auth
   ```
3. Log in to your Patreon account
4. Click **"Allow"** to authorize the app
5. You're now authenticated! 🎉

> You only need to do this authentication step once, unless your token expires.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Patreon:

#### User Information
- `get_identity` – Get the current user's information with optional fields and includes

#### Campaign Management
- `get_campaigns` – Get campaigns owned by the authorized user
- `get_campaign` – Get information about a single Campaign by ID
- `get_campaign_members` – Get members of a specific campaign
- `get_campaign_posts` – Get a list of all posts on a given campaign

#### Post Management
- `get_post` – Get details of a specific post

---

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/patreon/local
   ```

---

### 📎 Important Notes

- Ensure your Patreon application is properly configured in the developer portal
- The server uses Patreon's production environment by default
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services
- The server implements rate limiting and proper error handling for API requests
- All API calls are authenticated using the stored OAuth tokens

---

### 📚 Need Help?

- [Patreon Developer Portal](https://www.patreon.com/portal/registration/register-clients)
- [Patreon API Documentation](https://docs.patreon.com/)
- [Patreon OAuth 2.0 Guide](https://docs.patreon.com/#oauth) 