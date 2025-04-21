# LinkedIn Server

guMCP server implementation for interacting with **LinkedIn**.

---

### 📦 Prerequisites

- Python 3.7+
- LinkedIn Developer Account
- LinkedIn App credentials (Client ID and Client Secret)
- OAuth2 configuration

---

### 🔑 App Setup and Authentication

To set up your LinkedIn application and get the required credentials, follow these steps:

1. Go to the [LinkedIn Developers Solutions](https://developer.linkedin.com/) page
2. Click "Create app" if you don't have one already, or go to "My apps" if you have an existing app
3. Fill in the required data and create an app
4. Go to the "Products" tab and enable:
   - "Share on LinkedIn"
   - "Sign In with LinkedIn using OpenID Connect"
5. Go to the "Auth" tab and configure a redirect URI for your application (e.g., http://localhost:8080) in OAuth 2.0 settings
6. Get your application's client ID and client secret

---

### 🔐 Local Authentication

Create a file named `local_auth/oauth_configs/linkedin/oauth.json` with the following structure:

```json
{
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "redirect_uri": "your-redirect-uri"
}
```

### 🛠️ Supported Tools

This server exposes the following tools for interacting with LinkedIn using direct API calls:

#### Core API Tools
- `get_user_info` – Get information about the authenticated user including profile and email

#### Post Creation Tools
- `create_text_post` – Create a text-only post on LinkedIn
- `create_article_post` – Create a post on LinkedIn with an article
- `create_image_post` – Create a post on LinkedIn with an image

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the LinkedIn MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/linkedin/local
```

---

### 📎 Notes

- The server uses LinkedIn's v2 API with direct HTTP requests
- All posts are created with public visibility by default
- Image uploads are limited to 20MB
- Rate limits apply based on your LinkedIn application tier
- Make sure to provide valid OAuth credentials before making requests
- The server uses the standard `requests` library for all API calls

---

### 📚 Resources

- [LinkedIn API Documentation](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps)
- [LinkedIn REST API Reference](https://docs.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rest-api)
