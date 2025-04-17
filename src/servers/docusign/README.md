# DocuSign Server

guMCP server implementation for interacting with DocuSign for electronic signatures, document management, and user administration.

---

### 🚀 Prerequisites

- Python 3.11+
- A **DocuSign Developer Account** – [Sign up for free here](https://www.docusign.com/)

---

### 🔐 DocuSign OAuth App Setup (First-time Setup)

1. **Log in to the [DocuSign Developer Portal](https://admindemo.docusign.com/)**
2. Go to **Settings** → **Apps and Keys** (in the left sidebar)
3. Click on **"Add App & Integration Key"**
4. Fill out:
   - **App Name**: e.g., `guMCP Integration`
   - Click **"Create App"**
5. After the app is created:
   - Copy the **Integration Key** (this is your `client_id`)
   - Under **Authentication**, click **"Add Secret Key"** and copy it (this is your `client_secret`)
   - Under **Redirect URIs**, click **"Add URI"** and add your redirect uri, e.g.:
     ```
     http://localhost:8080/
     ```

- **Note: Make sure to use a _trailing slash_ in the redirect URI**

6. Save all values securely.

---

### 📄 Local OAuth Credentials

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/docusign/) with the following content:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri"
}
```

---

### 🔓 Authenticate with DocuSign

Run the following command to initiate the OAuth login:

```bash
python src/servers/docusign/main.py auth
```

This will open your browser and prompt you to log in to DocuSign. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/docusign/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### 📑 Template Management

- `list_templates` – List templates in your account
- `get_template` – Get details of a specific template
- `create_template` – Create a new reusable template

#### ✉️ Envelope Management

- `create_envelope` – Create envelope from templates or files
- `get_envelope` – Retrieve envelope details
- `send_envelope` – Send envelope to recipients
- `get_envelope_status_bulk` – Get statuses for multiple envelopes

#### 👤 User Management

- `create_user` – Add users to your account
- `list_users` – List users with filtering
- `get_user` – Get information on a specific user

---

### ▶️ Running the Server and Client

#### 1. Start the Server

```bash
python src/servers/main.py
```

Make sure you’ve already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/docusign/local
```

---

### 📌 Notes on DocuSign API Usage

- Most operations require your **account ID**, which is fetched automatically after auth.
- Documents should be base64 encoded.
- Signature fields ("tabs") must be configured in envelopes/templates before sending.
- All endpoints are RESTful and return JSON.
