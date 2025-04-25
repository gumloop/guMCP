# Mailchimp Server

guMCP server implementation for interacting with **Mailchimp** API.

---

### 📦 Prerequisites

- Python 3.11+
- A Mailchimp account
- OAuth 2.0 credentials from Mailchimp Developer Portal

---

### 🔐 OAuth Setup

1. Login to mailchimp [mailchimp.com](https://mailchimp.com)
2. Go to Account & Billing
3. Under Extras go to Registered Apps
4. Click "Register an app" if you don't have one
5. Add your redirect URI [for local host add ex. http://127.0.0.1:8080]
6. Note down:
   - Client ID
   - Client Secret


---

### 🔐 Local Authentication

Create a file named `oauth_configs/mailchimp/oauth.json` with the following structure:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri" e.g. `http://127.0.0.1:8080`
}   
```

To authenticate and save credentials for local testing, run:

```bash
python src/servers/mailchimp/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Mailchimp:

#### Audience Management Tools
- `get_audience_list` – List all available audiences
- `get_all_list` – Get all lists available in account
- `recent_activity` – Get up to the previous 180 days of recent activities in a list
- `add_update_subscriber` – Add or update a subscriber in a Mailchimp audience
- `add_subscriber_tags` – Add tags to a Mailchimp list subscriber

#### Campaign Management Tools
- `list_all_campaigns` – Get a list of all the campaigns
- `campaign_info` – Get information about a particular campaign for campaign id

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Mailchimp MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/mailchimp/local
```

---

### 📎 Notes

- The server respects Mailchimp's API rate limits:
  - 10 requests per second
  - 1000 requests per day on the free plan
  - Custom limits for higher-tier plans
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic
- All operations return standardized responses with success/error information

---

### 📚 Resources

- [Mailchimp API Documentation](https://mailchimp.com/developer/api/)
- [Mailchimp OAuth Guide](https://mailchimp.com/developer/marketing/guides/oauth-2/)
- [Mailchimp Python SDK](https://mailchimp.com/developer/marketing/api/root/)
