# Zoom GuMCP Server

GuMCP server implementation for interacting with Zoom Meetings API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Zoom OAuth App created at [Zoom App Marketplace](https://marketplace.zoom.us/develop/create)
- A local OAuth config file with your Zoom credentials

Create a file at the path `local_auth/oauth_configs/zoom/oauth.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uris": ["http://localhost:8080/callback"]
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
3. After authorization, you'll be redirected to the callback URL code.
4. Copy that code from your browser and paste it back in the terminal.
5. The token will be stored securely for future use.

You only need to do this once, unless your token expires.

> **Note**: Due to Zoom's URL length limitations, the authorization URL will only include minimal scopes. However, your app will have access to all scopes configured in the Zoom App Marketplace.

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

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Zoom MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/zoom/local
```

---

### 📎 Notes

- The server requires OAuth authentication for improved security.
- Make sure your Zoom app has the following scopes configured in the Zoom App Marketplace:
  - `meeting:write:meeting`
  - `meeting:write:meeting:admin`
  - `meeting:read:meeting:admin`
  - Plus any additional scopes needed for your specific use case
- All dates should be in ISO format with timezone (e.g., `2025-05-25T15:00:00Z`)
- The server handles automatically adding timezone information if missing

---

### 📚 Resources

- [Zoom API Documentation](https://marketplace.zoom.us/docs/api-reference/zoom-api/)
- [Zoom OAuth Documentation](https://marketplace.zoom.us/docs/guides/auth/oauth/)
- [Zoom App Types](https://marketplace.zoom.us/docs/guides/build/app-types/)
