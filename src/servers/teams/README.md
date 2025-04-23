# Microsoft Teams Server

guMCP server implementation for interacting with Microsoft Teams for team management, channel operations, messaging, and meetings.

---

### Prerequisites

- Python 3.11+
- A **Microsoft account** with access to Microsoft Teams
- Azure Active Directory access (for some admin features)

---

### Microsoft Teams OAuth App Setup (First-time Setup)

1. **Log in to the [Azure Portal](https://portal.azure.com/)**
2. Navigate to **Azure Active Directory** → **App registrations** → **New registration**
3. Fill out:

   - **Name**: e.g., `MCP Teams Integration`
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

5. Navigate to **API permissions** and add the following permissions:

   - Microsoft Graph API permissions (all "Delegated" type):
     - User.Read
     - offline_access
     - Team.Create
     - Team.ReadBasic.All
     - TeamSettings.ReadWrite.All
     - Channel.Create
     - ChannelSettings.ReadWrite.All
     - ChannelMember.ReadWrite.All
     - ChannelMessage.Read.All
     - ChannelMessage.Send
     - Chat.ReadWrite
     - Group.Read.All
     - TeamMember.Read.All
     - TeamMember.ReadWrite.All
     - OnlineMeetings.ReadWrite
6. Click **"Add permissions"** and then **"Grant admin consent"** for your organization
7. Save all values securely.

---

### Local OAuth Credentials

Create a file named `oauth.json` in your directory (local_auth/oauth_configs/teams/) with the following content:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "your-redirect-uri"
}
```

---

### Authenticate with Microsoft Teams

Run the following command to initiate the OAuth login:

```bash
python src/servers/teams/main.py auth
```

This will open your browser and prompt you to log in to your Microsoft account. After successful authentication, the access credentials will be saved locally to:

```
local_auth/credentials/teams/local_credentials.json
```

---

### 🛠 Features

This server exposes tools grouped into the following categories:

#### Team Management

- `get_teams` – Get the list of teams the user is a member of
- `get_team_details` – Get details of a specific Microsoft Teams team
- `get_team_members` – Get the list of members in a team
- `add_team_member` – Add a user to a team
- `remove_team_member` – Remove a user from a team

#### Channel Management

- `create_team` – Create a new Microsoft Teams team
- `get_channels` – Get the list of channels in a team
- `create_channel` – Create a new channel in a team

#### Messaging

- `get_chats` – Get the list of chats for the user
- `get_chat_messages` – Get messages from a specific chat
- `send_chat_message` – Send a message in a chat
- `get_channel_messages` – Get messages from a channel
- `send_channel_message` – Send a message to a channel
- `post_message_reply` – Post a reply to a message in a Teams channel

#### Meetings

- `create_meeting` – Create a new online meeting in Microsoft Teams

---

### ▶Running the Server and Client

#### 1. Start the Server

```bash
./start_sse_dev_server.sh
```

Make sure you've already authenticated using the `auth` command.

#### 2. Run the Client

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/teams/local
```

---

### Notes on Microsoft Teams API Usage

- Some operations require admin permissions (like viewing all teams in the organization).
- Message content supports HTML formatting for rich text messages.
- All endpoints are RESTful and return JSON.
- Team, channel, and user IDs are required for many operations - use the appropriate listing tools first to obtain these IDs.
