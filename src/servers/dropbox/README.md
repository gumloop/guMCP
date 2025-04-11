# Dropbox Server

guMCP server implementation for interacting with **Dropbox**.

---

### 📦 Prerequisites

- Python 3.11+
- Dropbox account
- OAuth 2.0 credentials from Dropbox App Console

---

### 🔐 OAuth Setup

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click "Create app"
3. Choose "Scoped access"
4. Choose the type of access you need
5. Name your app
6. Under "OAuth 2", note down:
   - App key (client_id)
   - App secret (client_secret)
7. Add your redirect URI
8. Under "Permissions" tab, enable these scopes:
   ```
   account_info.write
   account_info.read
   files.metadata.read
   files.metadata.write
   files.content.read
   files.content.write
   file_requests.read
   file_requests.write

   ```

---

### 🔐 Local Authentication

Create a file named `oauth_configs/dropbox/oauth.json` with the following structure:

```json
{
  "client_id": "your-app-key",
  "client_secret": "your-app-secret",
  "redirect_uri": "your-redirect-uri"
}   
```

To authenticate and save credentials for local testing, run:

```bash
python -m src/servers/dropbox/main auth
```

After successful authentication, your credentials will be stored securely for reuse.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Dropbox:

- `list_files` – List files or folders in a specific directory in Dropbox
- `upload_file` – Upload a file to a specific directory in Dropbox
- `create_folder` – Create a folder in a specific directory in Dropbox
- `delete` – Delete a file or folder from a specific directory in Dropbox
- `download` – Download a file from a specific directory in Dropbox
- `search` – Search for a file or a folder in Dropbox
- `move` – Move a file or a folder to a specific directory in Dropbox
- `get_user_info` – Get information about the current user
- `get_file_metadata` – Get metadata/information about a file in Dropbox

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the Dropbox MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/dropbox/local
```

---

### 📎 Notes

- All paths in Dropbox should start with "/" (root directory)
- File operations are asynchronous and use thread pooling for better performance
- Upload operations support both "add" and "overwrite" modes
- The server handles pagination automatically for large directories
- All operations return standardized responses with success/error information

---

### 📚 Resources

- [Dropbox API Documentation](https://www.dropbox.com/developers/documentation)
- [Dropbox OAuth Guide](https://www.dropbox.com/developers/reference/oauth-guide)
- [Dropbox Python SDK](https://github.com/dropbox/dropbox-sdk-python)
