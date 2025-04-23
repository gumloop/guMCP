# SharePoint Server

guMCP server implementation for interacting with Microsoft SharePoint for list management, document libraries, user administration, file management, and site page management.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Microsoft 365 account** with access to SharePoint
- Administrative access for some features (optional)

---

### 🔐 Microsoft Azure App Setup (First-time Setup)

1. **Log in to the [Azure Portal](https://portal.azure.com/)**
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill out:
   - **Name**: e.g., `MCP SharePoint Integration`
   - **Supported account types**: Choose the appropriate option based on your needs (typically "Accounts in this organizational directory only")
   - **Redirect URI**: Select "Web" and enter your redirect URI, e.g.:
     ```
     http://localhost:8080/
     ```
   - Click **"Register"**

4. After the app is created:
   - Copy the **Application (client) ID** (this is your `client_id`)
   - Navigate to **Certificates & secrets** → **New client secret**
   - Add a description and choose an expiration period
   - Copy the **Value** of the secret (this is your `client_secret`)

5. Navigate to **API permissions** and add the following Microsoft Graph API permissions (all "Delegated" type):
   - Sites.Manage.All
   - Sites.Read.All
   - Sites.ReadWrite.All
   - User.Read.All
   - Files.Read.All
   - Files.ReadWrite.All
   - offline_access

6. Click **"Add permissions"**
7. Save all values securely.

---

### 📄 Local OAuth Credentials

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/sharepoint/) with the following content:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri"
}
```

The tenant ID can be found in Azure Active Directory under "Properties" section.

---

### 🔓 Authenticate with SharePoint

Run the following command to initiate the OAuth login:

```bash
python src/servers/sharepoint/main.py auth
```

This will open your browser and prompt you to log in to your Microsoft account. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/sharepoint/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 👥 User Management
- `get_users` – Get all users from Microsoft 365 with filtering and pagination options

#### 📊 List Management
- `list_site_lists` – List all lists in a SharePoint site
- `create_list` – Create a new list in SharePoint
- `get_list` – Get details of a SharePoint list by ID or title

#### 📝 List-Item Management
- `create_list_item` – Create a new item in a SharePoint list
- `get_list_item` – Get details of a specific item in a SharePoint list
- `get_list_items` – Get all items from a SharePoint list with filtering and sorting options
- `delete_list_item` – Delete a specific item from a SharePoint list
- `update_list_item` – Update fields of an existing item in a SharePoint list

#### 📁 File Management
- `download_file` – Download a file from the current user's OneDrive
- `create_folder` – Create a new folder in the current user's OneDrive
- `upload_file` – Upload a file to the current user's OneDrive

#### 📰 Site Page Management
- `create_site_page` – Create a new SharePoint site page
- `get_site_page` – Get details of a specific page in a SharePoint site
- `list_site_pages` – List all pages in a SharePoint site

#### 🌐 Site Information
- `get_site_info` – Get metadata and information about a SharePoint site
- `search_sites` – Search for SharePoint sites by keyword

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/sharepoint/local
```

---

### 📌 Notes on SharePoint API Usage

- When using `site_url` parameters, provide the full URL to your SharePoint site (e.g., `https://<domain>.sharepoint.com/sites/<site_name>`)
- Most tools can use either `site_id` or `site_url` for identifying the SharePoint site