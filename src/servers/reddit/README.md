# Reddit Server

guMCP server implementation for interacting with the **Reddit API**.

---

### 📦 Prerequisites

- Python 3.11+
- OAuth 2.0 credentials configured for desktop application access

---

### 🔐 Local Authentication

Local authentication uses a Reddit OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/reddit/oauth.json
```

This file can be downloaded when creating an OAuth client from the Reddit Developer Portal.

To authenticate and save credentials for local testing, run:

```bash
python src/servers/reddit/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Reddit:

- `retrieve_reddit_post` – Fetch top posts in a subreddit with optional size limit
- `get_reddit_post_details` – Get detailed content about a specific Reddit post
- `create_reddit_post` – Create a new Reddit post
- `create_reddit_comment` - Create a new Reddit comment on a specific post
- `fetch_post_comments` – Fetch comments for a specific Reddit post
- `edit_reddit_post` – Edit a specific Reddit post
- `edit_reddit_comment` – Edit a specific Reddit comment
- `delete_reddit_post` – Delete a specific Reddit post
- `delete_reddit_comment` – Delete a specific Reddit comment

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Reddit MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/reddit/local
```

---

### 📎 Notes

- Ensure your OAuth app has the required scopes enabled: `identity`, `read`, `submit`, `edit`, `history`, `flair`
- If you're testing with multiple users or environments, use different `user_id` values.
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic.

---

### 📚 Resources

- [Reddit API Documentation](https://www.reddit.com/dev/api)
- [Reddit OAuth2 Documentation](https://github.com/reddit-archive/reddit/wiki/OAuth2)
