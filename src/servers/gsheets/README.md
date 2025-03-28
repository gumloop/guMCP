# Google Sheets Server

GuMCP server implementation for interacting with Google Sheets.

---

### 📦 Prerequisites

- Python 3.11+
- A Google Cloud project with the **Google Sheets API enabled**
- OAuth 2.0 credentials configured for desktop application access

---

### 🔐 Local Authentication

Local authentication uses a Google OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/gsheets/oauth.json
```
This file can be obtained when you are creating an oauth client from google cloud applciation in the GCP console. 

To authenticate and save credentials for local testing, run:

```bash
python src/servers/gsheets/main.py auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Google Sheets:

- `create-sheet` – Create a new spreadsheet
- `get-spreadsheet-info` – Retrieve spreadsheet metadata
- `get-sheet-names` – List sheet/tab names
- `batch-get` – Read values from multiple ranges
- `batch-update` – Write values to multiple ranges
- `append-values` – Append new rows to a sheet
- `lookup-row` – Search for a row by value
- `clear-values` – Clear a given sheet range
- `copy-sheet` – Copy a sheet from one spreadsheet to another

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_remote_dev_server.sh
```

This will start the MCP server and make it available for integration and testing.

You can also start the local client using the following -

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/gsheets/local
```
---

### 📎 Notes

- Ensure your OAuth app has **Sheets API access** enabled in the Google Cloud console.
- If you're testing with multiple users or environments, use different `user_id` values.
- This server is designed to integrate with GuMCP agents for tool-based LLM workflows.
- Make sure you have mentioned the anthropic API key in the .env file.

---

### 📚 Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [OAuth 2.0 in Google APIs](https://developers.google.com/identity/protocols/oauth2)
