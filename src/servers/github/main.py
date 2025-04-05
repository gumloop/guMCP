import os
import sys
import logging
import json
from pathlib import Path

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from github import Github

from src.auth.factory import create_auth_client
from src.utils.github.util import authenticate_and_save_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "repo",  # Full control of private repositories
    "repo:status",  # Access commit statuses
    "repo_deployment",  # Access deployment statuses
    "public_repo",  # Access public repositories
    "repo:invite",  # Manage repository invitations
    "admin:repo_hook",  # Full control of repository hooks
    "write:repo_hook",  # Create and update repository hooks
    "read:repo_hook",  # Read repository hooks
    "admin:org",  # Full control of orgs and teams
    "write:org",  # Create and update orgs and teams
    "read:org",  # Read orgs and teams
    "admin:public_key",  # Full control of user public SSH keys
    "write:public_key",  # Create and update user public SSH keys
    "read:public_key",  # Read user public SSH keys
    "admin:gpg_key",  # Full control of user GPG keys
    "write:gpg_key",  # Create and update user GPG keys
    "read:gpg_key",  # Read user GPG keys
    "notifications",  # Read notifications
    "user",  # Full access to user profile info
    "read:user",  # Read-only access to user profile info
    "user:email",  # Read user email addresses
    "user:follow",  # Follow and unfollow users
    "delete_repo",  # Delete repositories
    "gist",  # Create gists
    "read:discussion",  # Read team discussions
    "write:discussion",  # Read and write team discussions
    "admin:enterprise",  # Manage enterprise accounts
    "workflow",  # Update GitHub Action workflows
    "codespace",  # Manage codespaces
    "packages",  # Access GitHub Packages
    "delete:packages",  # Delete packages from GitHub Packages
    "read:packages",  # Read packages
    "write:packages",  # Upload packages to GitHub Packages
    "read:project",  # Read user and org projects
    "write:project",  # Manage user and org projects
    "admin:enterprise",  # Manage enterprise accounts
    "admin:ssh_signing_key",  # Manage SSH signing keys
    "write:ssh_signing_key",
    "read:ssh_signing_key",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_credentials(user_id, api_key=None):
    """
    Retrieves the OAuth access token for a specific GitHub user.

    Args:
        user_id (str): The identifier of the user.
        api_key (Optional[str]): Optional API key passed during server creation.

    Returns:
        str: The access token to authenticate with the GitHub API.

    Raises:
        ValueError: If credentials are missing or invalid.
    """
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    def handle_missing():
        err = f"GitHub credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            err += " Please run with 'auth' argument first."
        logger.error(err)
        raise ValueError(err)

    if not credentials_data:
        handle_missing()

    token = credentials_data.get("access_token") or credentials_data.get("api_key")
    if token:
        return token
    handle_missing()


async def create_github_client(user_id, api_key=None):
    """
    Creates an authorized GitHub client instance.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        Github: An authenticated GitHub client object.
    """
    token = await get_credentials(user_id, api_key)
    return Github(token)


def create_server(user_id, api_key=None):
    """
    Initializes and configures a GitHub MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all GitHub tools registered.
    """
    server = Server("github-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the GitHub API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            # Repository Management
            types.Tool(
                name="create_repository",
                description="Create a new repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "private": {"type": "boolean"},
                        "autoInit": {"type": "boolean"},
                    },
                    "required": ["name"],
                },
            ),
            types.Tool(
                name="search_repositories",
                description="Search for repositories",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="list_public_user_repositories",
                description="List all public repositories for the given user username",
                inputSchema={
                    "type": "object",
                    "properties": {"username": {"type": "string"}},
                    "required": ["username"],
                },
            ),
            types.Tool(
                name="list_organization_repositories",
                description="List all repositories for the given organization name",
                inputSchema={
                    "type": "object",
                    "properties": {"org_name": {"type": "string"}},
                    "required": ["org_name"],
                },
            ),
            # Repository Contents & Commits
            types.Tool(
                name="get_contents",
                description="Get the contents of a file or in a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "branch": {"type": "string"},
                    },
                    "required": ["owner", "repo", "path"],
                },
            ),
            types.Tool(
                name="list_repository_languages",
                description="List all languages used in a repository",
                inputSchema={
                    "type": "object",
                    "properties": {"repo_name": {"type": "string"}},
                    "required": ["repo_name"],
                },
            ),
            types.Tool(
                name="add_file_to_repository",
                description="Add a file to a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "branch": {"type": "string"},
                        "commit_message": {"type": "string"},
                    },
                    "required": [
                        "owner",
                        "repo_name",
                        "path",
                        "content",
                        "branch",
                        "commit_message",
                    ],
                },
            ),
            types.Tool(
                name="list_commits",
                description="List all commits for a repository by branch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "branch": {"type": "string"},
                    },
                    "required": ["repo_name", "branch", "owner"],
                },
            ),
            types.Tool(
                name="get_commit",
                description="The api provides commit content with `read` access",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "commit_sha": {"type": "string"},
                    },
                    "required": ["owner", "repo_name", "commit_sha"],
                },
            ),
            # Star & Engagement
            types.Tool(
                name="star_repository",
                description="Star a repository for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {"repo_name": {"type": "string"}},
                    "required": ["repo_name"],
                },
            ),
            types.Tool(
                name="list_stargazers",
                description="List all stargazers for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                    },
                    "required": ["repo_name"],
                },
            ),
            types.Tool(
                name="get_stargazers_count",
                description="Get the number of stargazers for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                    },
                    "required": ["repo_name"],
                },
            ),
            types.Tool(
                name="list_starred_repos_by_user",
                description="List all repositories starred by the user",
                inputSchema={"type": "object", "properties": {}},
            ),
            # Issues & Pull Requests
            types.Tool(
                name="list_issues",
                description="List all issues for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                    },
                    "required": ["repo_name", "owner"],
                },
            ),
            types.Tool(
                name="get_issue",
                description="Get a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "issue_number": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "issue_number"],
                },
            ),
            types.Tool(
                name="create_issue",
                description="Create a new issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "title", "body"],
                },
            ),
            types.Tool(
                name="update_issue",
                description="Update a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "issue_number": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "issue_number", "title", "body"],
                },
            ),
            types.Tool(
                name="add_comment_to_issue",
                description="Add a comment to a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "issue_number": {"type": "string"},
                        "comment": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "issue_number", "comment"],
                },
            ),
            types.Tool(
                name="list_branches",
                description="List all branches for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                    },
                    "required": ["repo_name", "owner"],
                },
            ),
            types.Tool(
                name="create_branch",
                description="Create a new branch from existing branch for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "branch_name": {"type": "string"},
                        "start_point": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "branch_name", "start_point"],
                },
            ),
            types.Tool(
                name="list_pull_requests",
                description="List all pull requests for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                    },
                    "required": ["repo_name", "owner"],
                },
            ),
            types.Tool(
                name="get_pull_request",
                description="Get a specific pull request for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {"type": "string"},
                        "owner": {"type": "string"},
                        "pull_request_number": {"type": "string"},
                    },
                    "required": ["repo_name", "owner", "pull_request_number"],
                },
            ),
            types.Tool(
                name="create_pull_request",
                description="Create a new pull request for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo_name": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "base": {"type": "string"},
                        "head": {"type": "string"},
                    },
                    "required": ["owner", "repo_name", "title", "body", "base", "head"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding GitHub API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        github = await create_github_client(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            # Repository Management
            if name == "create_repository":
                optional_params = {}
                if "description" in arguments:
                    optional_params["description"] = arguments["description"]
                if "private" in arguments:
                    optional_params["private"] = arguments["private"]
                if "autoInit" in arguments:
                    optional_params["auto_init"] = arguments["autoInit"]

                user = github.get_user()
                repo = user.create_repo(arguments["name"], **optional_params)
                result = {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "url": repo.html_url,
                }

            elif name == "search_repositories":
                repos = github.search_repositories(arguments["query"])
                result = [
                    {
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "url": repo.html_url,
                    }
                    for repo in repos
                ]

            elif name == "list_public_user_repositories":
                user = github.get_user(arguments["username"])
                repos = user.get_repos()
                result = [
                    {
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "url": repo.html_url,
                    }
                    for repo in repos
                ]

            elif name == "list_organization_repositories":
                org = github.get_organization(arguments["org_name"])
                repos = org.get_repos()
                result = [
                    {
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "url": repo.html_url,
                    }
                    for repo in repos
                ]

            # Repository Contents & Commits
            elif name == "get_contents":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                contents = repo.get_contents(arguments["path"], ref=arguments["branch"])
                if isinstance(contents, list):
                    result = [
                        {"name": item.name, "path": item.path, "type": item.type}
                        for item in contents
                    ]
                else:
                    result = {
                        "name": contents.name,
                        "path": contents.path,
                        "type": contents.type,
                        "content": contents.decoded_content.decode(),
                    }

            elif name == "list_repository_languages":
                repo = github.get_repo(arguments["repo_name"])
                result = repo.get_languages()

            elif name == "add_file_to_repository":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                repo.create_file(
                    path=arguments["path"],
                    message=arguments["commit_message"],
                    content=arguments["content"],
                    branch=arguments["branch"],
                )
                result = {"success": True}

            elif name == "get_commit":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                commit = repo.get_commit(arguments["commit_sha"])
                result = {
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": {
                        "name": commit.commit.author.name,
                        "email": commit.commit.author.email,
                        "date": commit.commit.author.date.isoformat(),
                    },
                    "url": commit.html_url,
                }
            elif name == "list_commits":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                commits = repo.get_commits(sha=arguments["branch"])
                result = [
                    {
                        "sha": commit.sha,
                        "message": commit.commit.message,
                        "author": {
                            "name": commit.commit.author.name,
                            "email": commit.commit.author.email,
                            "date": commit.commit.author.date.isoformat(),
                        },
                        "url": commit.html_url,
                    }
                    for commit in commits
                ]

            # Star & Engagement
            elif name == "star_repository":
                user = github.get_user()
                repo = github.get_repo(arguments["repo_name"])
                result = user.add_to_starred(repo)

            elif name == "list_stargazers":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                stargazers = repo.get_stargazers()
                result = [
                    {"login": user.login, "id": user.id, "url": user.html_url}
                    for user in stargazers
                ]

            elif name == "get_stargazers_count":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                result = repo.stargazers_count

            elif name == "list_starred_repos_by_user":
                user = github.get_user()
                starred_repos = user.get_starred()
                result = [
                    {
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "url": repo.html_url,
                    }
                    for repo in starred_repos
                ]

            # Issues & Pull Requests
            elif name == "list_issues":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issues = repo.get_issues()
                result = [
                    {
                        "title": issue.title,
                        "number": issue.number,
                        "url": issue.html_url,
                    }
                    for issue in issues
                ]

            elif name == "get_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                result = {
                    "title": issue.title,
                    "number": issue.number,
                    "state": issue.state,
                    "body": issue.body,
                    "url": issue.html_url,
                }

            elif name == "create_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.create_issue(arguments["title"], body=arguments["body"])
                result = {
                    "title": issue.title,
                    "number": issue.number,
                    "url": issue.html_url,
                }

            elif name == "update_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                issue.edit(title=arguments["title"], body=arguments["body"])
                result = {
                    "title": issue.title,
                    "number": issue.number,
                    "url": issue.html_url,
                }

            elif name == "add_comment_to_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                issue.create_comment(arguments["comment"])
                result = {"success": True}

            elif name == "list_branches":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                branches = repo.get_branches()
                result = [{"name": branch.name} for branch in branches]

            elif name == "create_branch":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                base_ref = repo.get_git_ref(f"heads/{arguments['start_point']}")
                base_sha = base_ref.object.sha
                repo.create_git_ref(
                    f"refs/heads/{arguments['branch_name']}", sha=base_sha
                )
                result = {"success": True}

            elif name == "list_pull_requests":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                pull_requests = repo.get_pulls()
                result = [
                    {"title": pr.title, "number": pr.number, "url": pr.html_url}
                    for pr in pull_requests
                ]

            elif name == "get_pull_request":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                pull_request = repo.get_pull(int(arguments["pull_request_number"]))
                result = {
                    "title": pull_request.title,
                    "number": pull_request.number,
                    "state": pull_request.state,
                    "body": pull_request.body,
                    "url": pull_request.html_url,
                }

            elif name == "create_pull_request":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                pull_request = repo.create_pull(
                    title=arguments["title"],
                    body=arguments["body"],
                    base=arguments["base"],
                    head=arguments["head"],
                )
                result = {
                    "title": pull_request.title,
                    "number": pull_request.number,
                    "url": pull_request.html_url,
                }

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling GitHub API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options required for registering the server.

    Args:
        server_instance (Server): The GuMCP server instance.

    Returns:
        InitializationOptions: The initialization configuration block.
    """
    return InitializationOptions(
        server_name="github-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
