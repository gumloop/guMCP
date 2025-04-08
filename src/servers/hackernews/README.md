# Hacker News Server

guMCP server implementation for interacting with the **Hacker News API**.

---

### 📦 Prerequisites

- Python 3.11+
- No authentication required - Hacker News API is public and free to use

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Hacker News:

- `get_top_stories` – Get top stories from Hacker News with optional limit
- `get_latest_stories` - Get latest stories from Hacker News with optional limit
- `get_story_details` – Get detailed content about a specific Hacker News story
- `get_comments` – Get comments for a specific Hacker News story
- `get_user` – Get information about a Hacker News user
- `get_stories_by_type` – Get stories by type (top, new, best, ask, show, job)

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Hacker News MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/hackernews/local
```

---

### 📎 Notes

- The Hacker News API is public and free to use
- Rate limiting may apply for frequent requests
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services like Anthropic.

---

### 📚 Resources

- [Hacker News API Documentation](https://github.com/HackerNews/API)
