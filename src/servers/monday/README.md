GuMCP server implementation for interacting with the Monday.com API using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A Monday.com account
- OAuth credentials configured for your application

---

### 🛠️ Step 1: Create a Monday.com Developer Account and Get API Credentials

1. Go to [Monday.com](https://monday.com)
2. Click on "Get Started"
3. Create an account by:
   - Continuing with Google or
   - Entering your email
4. Complete the account setup:
   - Enter your full name
   - Create a password
   - Set your account name
   - Answer profession-related questions
5. After logging in:
   - You can add team members or click "Remind me later"
   - Create your first project
6. Once in the main dashboard:
   - Click on your profile icon in the top right corner
   - Select "Developers" from the menu
   - Go to "My Apps" on the left sidebar
   - Scroll down on the right side
   - Click "Build App"
7. Configure your app:
   - Enter an app name
   - Choose a color
   - Add a short description
8. Copy your Client ID and Client Secret
9. Configure OAuth permissions:
   - Click on "Build" in the left sidebar
   - Select "OAuth Permissions"
   - Add your redirect URI (e.g., `http://localhost:8080`)
   - Enable the following scopes:
     - `me:read` - Read current user information
     - `boards:read` - Read boards and their content
     - `workspaces:read` - Read workspaces
     - `boards:write` - Create and modify boards and their content
     - `workspaces:write` - Create and modify workspaces
   - Save the changes

---

### 🛠️ Step 2: Configure OAuth Settings

1. Create a new folder called `local_auth` in your project directory
2. Inside that, create a folder called `oauth_configs`
3. Inside that, create a folder called `monday`
4. Create a new file called `oauth.json` in the `monday` folder
5. Copy and paste this into the file, replacing the placeholders with your actual values:

```json
{
  "client_id": "your-client-id-here",
  "client_secret": "your-client-secret-here",
  "redirect_uri": "your-redirect-uri-here" e.g. `http://localhost:8080`
}
```

> ⚠️ **IMPORTANT**: Never share or commit this file to version control. Add it to your `.gitignore`.
---

### 🔐 Step 3: Authenticate Your App

1. Open your terminal
2. Run this command:
   ```bash
   python src/servers/monday/main.py auth
   ```
3. Log in to your Monday.com account
4. Click **"Allow"** to authorize the app
5. You're now authenticated! 🎉

> You only need to do this authentication step once, unless your token expires.
---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with Monday.com:

#### User Information
- `get_me` – Get the current user's information including name and email

#### Board Management
- `get_boards` – Get all boards accessible to the user
- `get_board` – Get a specific board by ID
- `create_board` – Create a new board within a workspace
- `archive_board` – Archive a specific board by its ID

#### Item Management
- `get_item` – Get a specific item by its ID
- `create_item` – Create a new item in a board
- `delete_item` – Delete a specific item by its ID
- `archive_item` – Archive a specific item by its ID
- `get_subitems` – Get all subitems of a specific item
- `create_subitem` – Create a new sub-item under a parent item
- `delete_subitem` – Delete a sub-item by its ID

#### Group Management
- `get_group` – Get a specific group within a board
- `create_group` – Create a new group in a board
- `delete_group` – Delete a specific group from a board
- `archive_group` – Archive a specific group in a board

#### Column Management
- `create_column` – Create a new column in a board
- `change_column_value` – Change the value of a column for a specific item

#### Workspace Management
- `get_workspaces` – Get all workspaces accessible to the user

---

### ▶️ Running the Server

#### Local Development

1. Start the server:
   ```bash
   ./start_sse_dev_server.sh
   ```

2. In a new terminal, start the test client:
   ```bash
   python RemoteMCPTestClient.py --endpoint http://localhost:8000/monday/local
   ```

---

### 📎 Important Notes

- Ensure your Monday.com application is properly configured in the developer portal
- The server uses Monday.com's production environment by default
- Make sure your `.env` file contains the appropriate API keys if you're using external LLM services
- The server implements rate limiting and proper error handling for API requests
- All API calls are authenticated using the stored OAuth tokens

---

### 📚 Need Help?

- [Monday.com Developer Portal](https://developer.monday.com/)
- [Monday.com API Documentation](https://developer.monday.com/api-reference/docs)
- [Monday.com OAuth Guide](https://developer.monday.com/api-reference/docs/authentication)
