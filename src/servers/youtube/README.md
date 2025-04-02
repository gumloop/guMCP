# YouTube Server

guMCP server implementation for interacting with the **YouTube Data API v3**.

---

### 📦 Prerequisites

- Python 3.11+
- A Google Cloud project with the **YouTube Data API v3 enabled**
- OAuth 2.0 credentials configured for desktop application access

---

### 🔐 Local Authentication

Local authentication uses a Google OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/youtube/oauth.json
```

This file can be downloaded when creating an OAuth client from the Google Cloud Console.

To authenticate and save credentials for local testing, run:

```bash
python src/servers/youtube/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with YouTube:

- `get_video_details` – Get title, description, and duration of a video
- `list_channel_videos` – List recent uploads from a channel
- `get_video_statistics` – Get views, likes, comments for a video
- `search_videos` – Search videos globally across YouTube
- `get_channel_details` – Retrieve channel metadata (title, description, etc.)
- `list_channel_playlists` – List playlists owned by a channel
- `get_channel_statistics` – Get subscriber count and view count
- `list_playlist_items` – List videos in a given playlist
- `get_playlist_details` – Get title and description of a playlist

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the YouTube MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/youtube/local
```

---

### 📎 Notes

- Ensure your OAuth app has **YouTube Data API v3** access enabled in the Google Cloud console.
- If you're testing with multiple users or environments, use different `user_id` values.
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic.

---

### 📚 Resources

- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [OAuth 2.0 in Google APIs](https://developers.google.com/identity/protocols/oauth2)
