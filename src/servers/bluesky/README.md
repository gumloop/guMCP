# Bluesky Server

guMCP server implementation for interacting with the Bluesky API, supporting social media management, including posting, following, blocking, and profile management.

---

### Prerequisites

- Python 3.11+
- A Bluesky account
- Bluesky app password

---

#### How to Get Your Bluesky App Password

1. Log in to your Bluesky account at [bsky.app](https://bsky.app)
2. Click on your **Settings** icon on the bottom of left-side pane, then click on Privacy & Security [Privacy and Security](https://bsky.app/settings/privacy-and-security)
3. Navigate to the **App Passwords** section
4. Click on **Add Password**
5. Enter a name for your app (e.g., "guMCP"), and provide the access for the password
6. Copy the generated app password and keep it secure. You will be prompted to enter this during the authentication step below.

### Local Authentication

Local authentication uses your Bluesky handle and app password. The credentials will be stored securely at:

```
local_auth/credentials/bluesky/
```

To authenticate and save credentials for local testing, run:

```bash
python src/servers/bluesky/main.py auth
```

This will prompt you to enter your Bluesky handle and app password. After successful authentication, your credentials will be stored securely for reuse.

---

### Supported Tools

This server exposes the following tools for interacting with Bluesky:

#### Profile Management

- `get_my_profile` – Get the current user's profile information.

#### Post Management

- `create_post` – Create a new post with optional text and facets.
- `delete_post` – Delete an existing post by its URI.
- `get_posts` – Get recent posts from a user with pagination support.
- `get_liked_posts` – Get a list of posts liked by the user with pagination support.

#### Search

- `search_posts` – Search for posts on Bluesky with query, limit, and cursor support.
- `search_profiles` – Search for user profiles on Bluesky with query, limit, and cursor support.

#### Social Graph

- `get_follows` – Get a list of accounts the user follows with pagination support.
- `follow_user` – Follow another user by their handle or DID.
- `unfollow_user` – Unfollow a user by their handle.

#### User Management

- `mute_user` – Mute a user by their handle.
- `unmute_user` – Unmute a user by their handle.
- `block_user` – Block a user by their handle with optional reason.
- `unblock_user` – Unblock a user by their handle.

---

### Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the MCP server and make it available for integration and testing.

You can also start the local client using:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/bluesky/local
```

---

### Notes

- Ensure your Bluesky app password has the necessary permissions for the operations you want to perform.
- All API calls include proper error handling and response validation.
- This server is designed to integrate with guMCP agents for tool-based LLM workflows.

---

### Resources

- [Bluesky API Documentation](https://atproto.com/guides/overview)
- [Bluesky Developer Portal](https://atproto.com/)
- [Bluesky App](https://bsky.app)
