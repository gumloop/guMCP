# Google Meet Server

guMCP server implementation for interacting with the **Google Calendar API** to manage Google Meet meetings.

---

### 📦 Prerequisites

- Python 3.11+
- A Google Cloud project with the **Google Calendar API enabled**
- OAuth 2.0 credentials configured for desktop application access

---

### 🔐 Local Authentication

Local authentication uses a Google OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/gmeet/oauth.json
```

This file can be downloaded when creating an OAuth client from the Google Cloud Console.

To authenticate and save credentials for local testing, run:

```bash
python src/servers/gmeet/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Google Meet:

- `create_meeting` – Create a new meeting with title, description, time, and attendees
- `add_attendees` – Add attendees to an existing meeting
- `fetch_meetings_by_date` – Get all meetings scheduled for a specific date
- `get_meeting_details` – Retrieve detailed information about a specific meeting
- `update_meeting` – Modify meeting details (title, description, time)
- `delete_meeting` – Remove a meeting from the calendar

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Google Meet MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/gmeet/local
```

---

### 📎 Notes

- Ensure your OAuth app has **Google Calendar API** access enabled in the Google Cloud console
- If you're testing with multiple users or environments, use different `user_id` values
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic
- All meeting times should be provided in ISO format (YYYY-MM-DDTHH:MM:SS)

---

### 📚 Resources

- [Google Calendar API Documentation](https://developers.google.com/calendar/api)
- [OAuth 2.0 in Google APIs](https://developers.google.com/identity/protocols/oauth2)
