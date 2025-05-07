# PowerPoint Server

guMCP server implementation for interacting with Microsoft PowerPoint presentations through OneDrive and SharePoint, enabling presentation creation, editing, and management capabilities.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Microsoft 365 account** with access to OneDrive/SharePoint
- The `python-pptx` library for PowerPoint manipulation

---

### 🔐 Microsoft Azure App Setup (First-time Setup)

1. **Log in to the [Azure Portal](https://portal.azure.com/)**
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill out:
   - **Name**: e.g., `MCP PowerPoint Integration`
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
   - Files.ReadWrite
   - Sites.ReadWrite.All
   - offline_access

6. Click **"Add permissions"**
7. Save all values securely.

---

### 📄 Local OAuth Credentials

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/powerpoint/) with the following content:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri"
}
```

The tenant ID can be found in Azure Active Directory under "Properties" section.

---

### 🔓 Authenticate with PowerPoint

Run the following command to initiate the OAuth login:

```bash
python src/servers/powerpoint/main.py auth
```

This will open your browser and prompt you to log in to your Microsoft account. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/powerpoint/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 📊 Presentation Management
- `list_presentations` – List PowerPoint presentations from OneDrive with optional filtering
- `create_presentation` – Create a new PowerPoint presentation in OneDrive with optional title slide
- `read_presentation` – Extract content and structure from a PowerPoint presentation
- `delete_presentation` – Delete a PowerPoint presentation from OneDrive
- `download_presentation` – Get a download URL for a PowerPoint presentation
- `search_presentations` – Search for PowerPoint presentations by content

#### 📝 Slide Management
- `add_slide` – Add a new slide to an existing presentation with specified title and content
- `update_slide` – Update content on a specific slide including title and body text
- `delete_slide` – Remove a slide from a presentation by index

---

### 📋 Common Parameters

Many tools share common parameters:

- `file_id`: The unique identifier for a PowerPoint file in OneDrive/SharePoint
- `slide_index`: 1-based index of a slide in a presentation (first slide is 1)
- `title`: Title text for a slide
- `content`: Content text for a slide body

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/powerpoint/local
```

---

### 📌 Notes on PowerPoint Integration

- The server uses the `python-pptx` library for local PowerPoint file manipulation
- Files are temporarily downloaded, modified, and then uploaded back to OneDrive
- The presentation structure that can be extracted is limited to text content; images and other media elements may not be fully represented
- Slide layouts available are dependent on the PowerPoint template being used
- Common layouts include: "Title Slide", "Title and Content", "Section Header", "Title Only", and "Blank"
