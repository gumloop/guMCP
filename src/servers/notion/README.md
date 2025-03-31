
# Notion GuMCP Server

GuMCP server implementation for interacting with Notion.

---

### 📦 Prerequisites

- Python 3.11+
- A Notion integration token (see [Creating integrations](https://developers.notion.com/docs/create-a-notion-integration))
- A `.env` file with your `NOTION_TOKEN` set

Example `.env` content:
```
NOTION_TOKEN=secret_abc123...
```

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Notion:

- `list-all-users` – List all users
- `search-pages` – Search all pages
- `list-databases` – List all databases
- `query-database` – Query a Notion database
- `get-page` – Retrieve a page by ID
- `create-page` – Create a new page in a database
- `append-blocks` – Append content blocks to a page or block
- `get-block-children` – List content blocks of a page or block

---

### ▶️ Run

#### Local Development

You can launch the server for local development using (example script):

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

- Ensure you have created a Notion integration and saved its secret token in your `.env` file under `NOTION_TOKEN`.
- If you're testing with multiple users or environments, you may need different token values or `user_id` values.
- This server integrates with GuMCP agents for tool-based LLM workflows.
- Make sure you have mentioned the Anthropic API key in the `.env` file if you're using it for additional LLM features.

---

### 📚 Resources

- [Notion API Documentation](https://developers.notion.com)
- [Official Notion Python Client](https://github.com/ramnes/notion-sdk-py)
