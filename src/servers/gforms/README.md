# Google Forms Server

guMCP server implementation for interacting with the **Google Forms API** to manage Google Forms and their responses.

---

### 🚀 Prerequisites

- Python 3.11+
- A **Google Cloud project** with the following APIs enabled:
  - Google Forms API
  - Google Drive API

---

### 🔐 Google Cloud Project Setup (First-time Setup)

1. **Log in to the [Google Cloud Console](https://console.cloud.google.com/)**
2. Create a new project or select an existing one
3. Enable the required APIs:
   - Google Forms API
   - Google Drive API
4. Navigate to **APIs & Services** → **Credentials**
5. Click **Create Credentials** → **OAuth client ID**
6. Configure the OAuth consent screen if not already done
7. Select **Web application** as the application type
8. Click **Create**
9. Download the OAuth client configuration JSON file

---

### 📄 Local OAuth Credentials

Place the downloaded OAuth configuration JSON file at:

```
local_auth/oauth_configs/gforms/oauth.json
```

The file should contain your client ID and client secret.

---

### 🔓 Authenticate with Google Forms

Run the following command to initiate the OAuth login:

```bash
python src/servers/gforms/main.py auth
```

This will open your browser and prompt you to log in to your Google account. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/gforms/local_credentials.json
```

---

### 🛠 Features

This server exposes tools for the following operations:

#### 📋 Form Management
- `list_forms` – List all forms in your Google Drive
- `create_form` – Create a new form with title, description, and visibility settings
- `get_form` – Retrieve detailed information about a specific form
- `update_form` – Modify form details (title, description, visibility)
- `move_form_to_trash` – Move a form to trash
- `search_forms` – Search for forms by name

#### ❓ Question Management
- `add_question` – Add a question to an existing form (supports text, paragraph, multiple choice, and checkbox types)
- `delete_item` – Delete a question from an existing form

#### 📊 Response Management
- `list_responses` – Get all responses for a specific form
- `get_response` – Retrieve detailed information about a specific response

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/gforms/local
```

---

### 📌 Notes on Google Forms API Usage

- Ensure your OAuth app has the necessary API scopes enabled
- When creating forms, you can specify whether they should be public or private
- Question types supported include: text, paragraph, multiple choice, and checkbox
- Make sure your `.env` file contains the appropriate API keys if using external LLM services

---

### 📚 Resources

- [Google Forms API Documentation](https://developers.google.com/forms/api)
- [Google Drive API Documentation](https://developers.google.com/drive/api)
- [OAuth 2.0 in Google APIs](https://developers.google.com/identity/protocols/oauth2)
