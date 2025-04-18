# GitHub GuMCP Server

GuMCP server implementation for interacting with GitHub using OAuth authentication.

---

### 📦 Prerequisites

- Python 3.11+
- A GitHub OAuth App created at [GitHub Developer Settings](https://github.com/settings/developers)
- A local OAuth config file with your GitHub `client_id`, `client_secret`, and `redirect_uri`

Create a file named `oauth.json`:

```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret",
  "redirect_uri": "http://localhost:8080"
}
```

**⚠️ Do not commit this file to version control. Add it to your `.gitignore`.**

---

### 🔐 Authentication

Before running the server, you need to authenticate and store your OAuth token:

```bash
python main.py auth
```

This will:
1. Print a GitHub OAuth URL for you to open in your browser.
2. Prompt you to paste the `code` after granting access.
3. Store the token securely using your `auth_client`.

You only need to do this once per user.

---

### 🛠️ Supported Tools

This server exposes the following tools for interacting with GitHub:

- `create_repository` – Create a new repository
- `search_repositories` – Search for repositories
- `list_public_user_repositories` – List all public repositories for the given user username
- `list_organization_repositories` – List all repositories for the given organization name
- `get_contents` – Get the contents of a file or in a repository
- `list_repository_languages` – List all languages used in a repository
- `add_file_to_repository` - Add a file to a repository with a commit message
- `list_commits` – List all commits for a repository by branch
- `get_commit` – The api provides commit content with read access
- `star_repository` – Star a repository for the authenticated user
- `list_stargazers` – List all stargazers for a repository
- `get_stargazers_count` – Get the number of stargazers for a repository
- `list_starred_repos_by_user` – List all repositories starred by the user
- `list_issues` – List all issues for a repository
- `get_issue` – Get a specific issue for a repository
- `create_issue` – Create a new issue for a repository
- `update_issue` – Update a specific issue for a repository
- `add_comment_to_issue` – Add a comment to a specific issue for a repository
- `list_branches` – List all branches for a repository
- `list_pull_requests` – List all pull requests for a repository
- `get_pull_request` – Get a specific pull request for a repository
- `create_pull_request` – Create a new pull request for a repository

---

### ▶️ Run

#### Local Development

You can launch the server for local development using:

```bash
./start_remote_dev_server.sh
```

This will start the GuMCP server and make it available for integration and testing.

If you have a local client for testing, you can run it like:

```bash
python RemoteMCPTestClient.py --endpoint http://localhost:8000/github/local
```

Adjust the endpoint path as needed based on your deployment setup.

---

### 📎 Notes

- This implementation uses OAuth instead of a static token for improved security and multi-user support.
- Each user's OAuth access token is securely stored via your `auth_client`.
- The `github_oauth_client.json` file contains your app's secret credentials and should never be committed to version control.
- This server integrates with GuMCP agents for tool-based LLM workflows.
- Make sure you've set the Anthropic API key in your `.env` if you're using LLM toolchains.

---

### 📚 Resources

- [GitHub API Documentation](https://docs.github.com/en/rest)
- [Official GitHub Python Client](https://pygithub.readthedocs.io/)
