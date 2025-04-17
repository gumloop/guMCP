# Zoom GuMCP Server

GuMCP server implementation for interacting with Zoom Meetings API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Zoom OAuth App created at [Zoom App Marketplace](https://marketplace.zoom.us/develop/create)
- A local OAuth config file with your Zoom credentials

---

### 🛠️ Step 1: Create a Zoom OAuth App

1. Go to [Zoom App Marketplace](https://marketplace.zoom.us/develop/create) and sign in
2. Click **"Develop"** in the top menu
3. Click **"Create App"** > **"General App"**
4. Select **"User-managed app"** (this is important!)
5. You'll see your app credentials (Client ID and Client Secret) - save these for later
6. (Optional) Click the edit icon in the top left to change your app name
7. Click **"Continue"**

---

### 🛠️ Step 2: Configure OAuth Settings

1. Under **OAuth Information**, set up:
   - **Redirect URL for OAuth**: e.g. `http://localhost:8080`
   - **Add Whitelist URL**: e.g. `http://localhost:8080` (same as redirect URL)
2. Click **"Continue"**

---

### 🛠️ Step 3: Add Required Scopes

1. In the **Scopes** section, click **"Add Scopes"**
2. Search for and add the following scopes:

**Required Scopes:**
- `meeting:read:list_upcoming_meetings` - List upcoming meetings
- `meeting:read:participant` - Read meeting participants
- `meeting:read:list_meetings` - List all meetings
- `meeting:read:meeting` - Read meeting details
- `meeting:write:meeting` - Create and update meetings
- `meeting:write:registrant` - Add meeting registrants
- `meeting:update:meeting` - Update meeting settings
- `meeting:delete:meeting` - Delete meetings
- `meeting:write:invite_links` - Manage meeting invite links
- `cloud_recording:read:list_recording_files` - Access recording files
- `cloud_recording:read:list_user_recordings` - List user recordings

3. Click **"Continue"**

---

### 🛠️ Step 4: Complete App Setup

1. Review your app information
2. Click **"Submit"**
3. Once approved, click **"Activate"** to make your app live

---

### 🔐 Step 5: Set Up Local Configuration

1. Create a new folder called `local_auth` in your project directory
2. Inside that, create a folder called `oauth_configs`
3. Inside that, create a folder called `zoom`
4. Create a new file called `oauth.json` in the `zoom` folder
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

### 🔐 Step 6: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/zoom/main.py auth
   ```
3. Log in to your Zoom account
4. Click **"Allow"** to authorize the app
5. You're now authenticated! 🎉

> You only need to do this authentication step once, unless your token expires.

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

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/zoom/local
   ```

---

### 📎 Important Notes

- All dates should be in ISO format with timezone
- If you don't specify a timezone, the server will add one automatically
- If you run into any issues, check that:
  - You selected "User-managed app" during setup
  - You added all the required scopes
  - Your OAuth configuration file is in the correct location
  - You're using the correct redirect URL

---

### 📚 Need Help?

- [Zoom API Documentation](https://marketplace.zoom.us/docs/api-reference/zoom-api/)
- [Zoom OAuth Documentation](https://marketplace.zoom.us/docs/guides/auth/oauth/)
- [Zoom App Types](https://marketplace.zoom.us/docs/guides/build/app-types/)
