# Asana Server

guMCP server implementation for interacting with Asana's project management and task tracking APIs.

## 📦 Prerequisites

- Python 3.11+
- An Asana account
- Asana OAuth App credentials (Client ID and Client Secret)

## 🔑 OAuth App Registration

To create an Asana OAuth app and get your credentials, follow these steps:

1. Log in to your Asana account
2. Go to the [Developer App Console](https://app.asana.com/0/developer-console)
3. Click "Create New App"
4. Fill in the app details:
   - App Name: Your app's name
   - Description: Brief description of your app
5. After creation, go to OAuth section and under that:
   - Note down Client ID and Client Secret
   - Add redirect url (`http://localhost:8080`) 
   - provide necessary scopes for the app 
6. Done, youe app is registered

## ⚠️ Important Note on OAuth Scopes

As of now, some OAuth scopes are in preview and will be fully rolled out by July 2025. This means some tools in this server may not work with the standard OAuth flow. There are two ways to work around this limitation (https://developers.asana.com/docs/oauth-scopes): 

### Option 1: Use Personal Access Token
1. Go to your Asana account settings
2. Navigate to "Apps" → "Manage Developer Apps"
3. Create a new Personal Access Token
4. Replace the OAuth access token with this Personal Access Token after authentication

### Option 2: Use Full Permissions
1. In the OAuth consent screen, toggle "Full Permissions" to opt out of the preview
2. Add `default` to the scopes list to get full access (support under beta, yet to be released)
3. This will grant your app full access to all features, bypassing the scope limitations

Choose the option that best fits your security requirements. Option 1 is recommended for development and testing, while Option 2 is more suitable for production use.

## 🔐 OAuth Scopes

The following scopes are required for the Asana server to function properly:

```python
SCOPES = [
    "attachments:write",
    "goals:read",
    "project_templates:read",
    "projects:read",
    "projects:write",
    "projects:delete",
    "stories:read",
    "tasks:read",
    "tasks:write",
    "tasks:delete",
    "users:read",
    "workspaces:read",
]
```

## 🔐 Local Authentication

To authenticate and save your Asana credentials for local testing, run:

```bash
python src/servers/asana/main.py auth
```

This will:
1. Open your browser to the Asana OAuth consent screen
2. After authorization, redirect you to the callback URL
3. Store your credentials securely

## 🛠️ Features

The Asana server supports a comprehensive set of operations grouped into categories:

### User Management
- `get_me`: Get current user's information including ID, name, and email
- `get_users`: Get all users in a workspace
- `get_user`: Get specific user details by ID

### Workspace Management
- `get_workspaces`: Get all workspaces accessible to the user

### Project Management
- `get_projects`: Get all projects in a workspace
- `get_project`: Get a specific project by ID
- `create_project`: Create a new project in a workspace
- `update_project`: Update details of an existing project

### Task Management
- `get_tasks`: Get all tasks in a project
- `get_task`: Get a specific task by ID
- `create_task`: Create a new task in a project
- `update_task`: Update a task's details
- `delete_task`: Delete a task
- `duplicate_task`: Duplicate an existing task

### Task Status
- `mark_task_complete`: Mark a task as complete
- `mark_task_incomplete`: Mark a task as incomplete

### Task Assignment
- `assign_task`: Assign a task to a user
- `unassign_task`: Remove the assignee from a task

### Task Followers
- `add_follower_to_task`: Add a follower to a task
- `remove_follower_from_task`: Remove a follower from a task

### Subtasks
- `add_subtask`: Add a subtask to an existing task

### Project-Task Relationships
- `add_task_to_project`: Add an existing task to a project
- `remove_task_from_project`: Remove a task from a project

### Section Management
- `create_section`: Create a new section in a project
- `add_task_to_section`: Add a task to a specific section
- `get_sections`: Get sections in a project, optionally filtered by name
- `delete_section`: Delete a specific section (must be empty and not the last section)

### Tag Management
- `create_tag`: Create a new tag in a workspace or organization
- `get_tags`: Get tags in a workspace, optionally filtered by name
- `add_tag_to_task`: Add a tag to a task
- `remove_tag_from_task`: Remove a tag from a task

### Attachment Management
- `create_attachment`: Create an attachment for a task or other object

## ▶️ Running the Server and Client

### 1. Start the Server

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

### 2. Connect with the Client

Once the server is running, connect to it using the test client:

```bash
python tests/clients/RemoteMCPTestClient.py --endpoint=http://localhost:8000/asana/local
```

## 📎 Notes

### OAuth Security:
- Store OAuth credentials securely and never commit them to source control
- Use appropriate redirect URIs for different environments
- Implement proper token refresh handling

### Rate Limiting:
- Asana API has rate limits that vary by endpoint
- The server handles rate limiting gracefully with appropriate error messages

### Data Access:
- OAuth scopes determine the level of access your app has
- Only request the scopes your app needs
- Review and update scopes as your app's requirements change

## 📚 Resources

- [Asana API Documentation](https://developers.asana.com/docs)
- [Asana Developer Console](https://app.asana.com/0/developer-console)
- [Asana OAuth Guide](https://developers.asana.com/docs/oauth)
- [Asana API Reference](https://developers.asana.com/reference)
