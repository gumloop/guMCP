# JIRA Server

guMCP server implementation for interacting with Atlassian JIRA Cloud API.

---

### Prerequisites

- Python 3.11+
- A JIRA Cloud account with API access
- OAuth 2.0 credentials configured for JIRA Cloud

---

### Local Authentication

Local authentication uses a JIRA OAuth Configuration JSON file located at:

```
local_auth/oauth_configs/jira/oauth.json
```

Create the following file with the relevant attributes for your app:

```json
{
  "client_id": "xxxxxxxxxxxxxxxxxxxxx",
  "client_secret": "xxxxxxxxxxxxxxxxxxxxx",
  "redirect_uri": "http://localhost:8080"
}
```

To set this up properly, follow these steps:

1. Create an OAuth 2.0 (3LO) integration in your Atlassian developer account
2. Configure the required scopes for your application:
   - `read:jira-work`
   - `write:jira-work`
   - `read:jira-user`
   - `offline_access`
   - `manage:jira-project`
   - `manage:jira-configuration`
3. Set the callback URL to `http://localhost:8080`

For detailed instructions, refer to Atlassian's official documentation:
[OAuth 2.0 (3LO) apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)

To authenticate and save credentials for local testing, run:

```bash
python src/servers/jira/main.py auth
```

This will open a browser window for you to authorize the application. After successful authentication, your credentials will be stored securely for reuse.

---

### Supported Tools

This server exposes the following tools for interacting with JIRA:

#### Project Management Tools

- `create_project` – Set up a new JIRA project for a team, client, or initiative
- `get_project` – Retrieve metadata about a specific project
- `update_project` – Modify project details like name, lead, or description
- `delete_project` – Delete an entire project and its issues
- `list_projects` – List all accessible JIRA projects
- `get_issue_types_for_project` – Get all valid issue types for a project

#### Issue Management Tools

- `create_issue` – Create a new issue, bug, task, or story in a project
- `get_issue` – Get full details of an issue (title, description, status, comments)
- `update_issue` – Modify issue fields such as assignee, priority, or status
- `delete_issue` – Permanently remove an issue from a project
- `transition_my_issue` – Move an assigned issue to a new status
- `list_issues` – List issues by JQL query
- `comment_on_issue` – Add a comment to an issue

#### User-specific Tools

- `get_myself` – Get information about the authenticated user
- `get_my_issues` – Fetch all open issues assigned to the current user
- `get_my_recent_activity` – View recently updated issues the user interacted with
- `get_my_permissions` – Determine what actions the user is allowed to perform in a project

---

### Run

#### Local Development

You can launch the server for local development using:

```bash
./start_sse_dev_server.sh
```

This will start the MCP server and make it available for integration and testing.

You can also start the local client using the following:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/jira/local
```

---

### Notes

- Ensure your JIRA app has all the required scopes enabled in the Atlassian developer console.
- If creating a new project, you need administrative permissions in your JIRA instance.
- This server is designed to integrate with guMCP agents for tool-based LLM workflows.
- The `Cloud ID` can be obtained from your Atlassian instance URL or through the accessible resources endpoint.

---

### Resources

- [JIRA Cloud REST API documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)
- [Atlassian OAuth 2.0 (3LO) documentation](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [JIRA JQL syntax](https://support.atlassian.com/jira-software-cloud/docs/advanced-search-reference-jql-fields/)
- [Atlassian Document Format (ADF)](https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/)
