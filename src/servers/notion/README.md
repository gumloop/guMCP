# Notion GuMCP Server

GuMCP server implementation for interacting with Notion using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Notion integration created at [Notion Developer Portal](https://www.notion.com/my-integrations)
- A local OAuth config file with your Notion `client_id`, `client_secret`, and `redirect_uri`

Create a file named `oauth.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "http://localhost:8080"
}
```

**⚠️ Do not commit this file to version control. Add it to your `.gitignore`.**

---

### 🔐 Authentication

Before running the server, you need to authenticate and store your OAuth token:

```bash
python main.py auth
```

This will:
1. Print a Notion OAuth URL for you to open in your browser.
2. Prompt you to paste the `code` after granting access.
3. Store the token securely using your `auth_client`.

You only need to do this once per user.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Notion:

- `list_all_users` – List all users
- `search_pages` – Search all pages
- `list_databases` – List all databases
- `query_database` – Query a Notion database
- `get_page` – Retrieve a page by ID
- `create_page` – Create a new page in a database
- `append_blocks` – Append content blocks to a page or block
- `get_block_children` – List content blocks of a page or block

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_remote_dev_server.sh
```

This will start the GuMCP server and make it available for integration and testing.

If you have a local client for testing, you can run it like:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/notion/local
```

Adjust the endpoint path as needed based on your deployment setup.

---

### 📎 Notes

- This implementation uses OAuth instead of a static token for improved security and multi-user support.
- Each user’s OAuth access token is securely stored via your `auth_client`.
- The `notion_oauth_client.json` file contains your app’s secret credentials and should never be committed to version control.
- This server integrates with GuMCP agents for tool-based LLM workflows.
- Make sure you’ve set the Anthropic API key in your `.env` if you're using LLM toolchains.

---

### 📚 Resources

- [Notion API Documentation](https://developers.notion.com)
- [Official Notion Python Client](https://github.com/ramnes/notion-sdk-py)
