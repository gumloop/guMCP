
# Zoom GuMCP Server

GuMCP server implementation for interacting with Zoom Meetings API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Zoom OAuth App created at [Zoom App Marketplace](https://marketplace.zoom.us/develop/create)
- A local OAuth config file with your Zoom credentials

---

### 🛠️ Create a Zoom OAuth App

1. Visit the [Zoom App Marketplace](https://marketplace.zoom.us/develop/create) and log in with your Zoom account.
2. Click **"Create"** > **"OAuth"**.
3. Choose **App Type** as `OAuth` and provide basic app information (name, company, etc.).
4. Under **OAuth Information**, fill out the following:
   - **Redirect URL for OAuth**: e.g. `http://localhost:8080/callback` (for local testing)
   - **Add Whitelist URL**: Same as redirect URL
5. Save and continue to **Scopes** section. Add the following scopes at minimum:
   - `meeting:write:admin`
   - `meeting:read:admin`
   - `recording:read:admin`
   - `report:read:admin`
6. Continue through the submission process, and **Activate the App** once done.
7. Copy your **Client ID** and **Client Secret**.

---

### 🔐 OAuth Configuration

Create a file at the path `local_auth/oauth_configs/zoom/oauth.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "http://localhost:8080/callback"
}
```

**⚠️ Do not commit this file to version control. Add it to your `.gitignore`.**

---

### 🔐 Authentication

Before running the server, you need to authenticate and store your OAuth token:

```bash
python src/servers/zoom/main.py auth
```

This will:

1. Print a Zoom OAuth URL for you to open in your browser.
2. Prompt you to authenticate with your Zoom account.
3. After authorization, you'll be redirected to the callback URL with a code.
4. Copy that code from your browser and paste it into the terminal.
5. The token will be securely stored for future use.

> You only need to do this once, unless your token expires.

> ⚠️ Note: Zoom limits the URL length for scopes. Only minimal scopes are used in the authorization URL, but your app will still receive access to all scopes configured in the Zoom App Marketplace.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Zoom:

- `create_meeting` – Create a new Zoom meeting
- `update_meeting` – Update an existing Zoom meeting
- `get_meeting` – Get details of a Zoom meeting
- `list_meetings` – List all Zoom meetings
- `list_upcoming_meetings` – List all upcoming Zoom meetings
- `list_all_recordings` – List all recordings
- `get_meeting_recordings` – Get recordings for a specific meeting
- `get_meeting_participant_reports` – Get participant reports for a meeting
- `add_attendees` – Add attendees to a Zoom meeting
- `fetch_meetings_by_date` – Fetch all Zoom meetings for a given date
- `delete_meeting` – Delete a Zoom meeting

---

### ▶️ Run

#### Local Development

Start the server:

```bash
./start_sse_dev_server.sh
```

This will start the Zoom MCP server and make it available for integration and testing.

Start the local client:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/zoom/local
```

---

### 📎 Notes

- The server requires OAuth authentication for improved security.
- Ensure the following scopes are configured in your Zoom App:
  - `meeting:write:admin`
  - `meeting:read:admin`
  - `recording:read:admin`
  - `report:read:admin`
- All date inputs should be in ISO format with timezone (e.g., `2025-05-25T15:00:00Z`)
- If the timezone is not provided, it will be added automatically by the server.

---

### 📚 Resources

- [Zoom API Documentation](https://marketplace.zoom.us/docs/api-reference/zoom-api/)
- [Zoom OAuth Documentation](https://marketplace.zoom.us/docs/guides/auth/oauth/)
- [Zoom App Types](https://marketplace.zoom.us/docs/guides/build/app-types/)
