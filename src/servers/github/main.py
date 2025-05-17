import os
import sys
import logging
import json
from pathlib import Path
import datetime
from typing import Optional, Iterable

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.types import AnyUrl, Resource
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents

from github import Github
from github.GithubObject import GithubObject

from src.auth.factory import create_auth_client
from src.utils.github.util import authenticate_and_save_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "repo",  # Full control of private repositories
    "public_repo",  # Access public repositories
    "read:org",  # Read orgs and teams
    "user",  # Full access to user profile info
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

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None, parent_uri: Optional[str] = None
    ) -> list[Resource]:
        """List GitHub accounts and repositories"""
        logger.info(f"Listing resources for user: {user_id}, parent: {parent_uri}")

        github = await create_github_client(server.user_id, server.api_key)
        resources = []

        try:
            if parent_uri:
                if not str(parent_uri).startswith("github://organization/"):
                    raise ValueError(f"Invalid parent URI: {parent_uri}")

                org_name = str(parent_uri).replace("github://organization/", "")

                try:
                    organization = github.get_organization(org_name)
                    repos = organization.get_repos()
                    for repo in repos:
                        resources.append(
                            Resource(
                                uri=f"github://organization/{org_name}/repository/{repo.name}",
                                mimeType="application/json",
                                name=repo.name,
                                description=repo.description
                                or f"Repository: {repo.name}",
                                parentUri=parent_uri,
                            )
                        )
                except Exception as e:
                    logger.error(f"Error getting organization repos: {e}")

                return resources

            user = github.get_user()

            # Add personal account
            resources.append(
                Resource(
                    uri=f"github://organization/{user.login}",
                    mimeType="application/json",
                    name=f"{user.login}",
                    description=f"Personal GitHub account",
                    hasChildren=True,
                )
            )

            # Add organizations
            orgs = user.get_orgs()
            for org in orgs:
                resources.append(
                    Resource(
                        uri=f"github://organization/{org.login}",
                        mimeType="application/json",
                        name=org.name or org.login,
                        description=f"GitHub organization",
                        hasChildren=True,
                    )
                )

            return resources
        except Exception as e:
            logger.error(f"Error listing GitHub resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read GitHub resources"""
        logger.info(f"Reading resource: {uri} for user: {user_id}")

        github = await create_github_client(server.user_id, server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("github://"):
            raise ValueError(f"Invalid GitHub URI: {uri_str}")

        parts = uri_str.replace("github://", "").split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid GitHub URI format: {uri_str}")

        try:
            if parts[0] == "organization" and len(parts) == 2:
                org_name = parts[1]
                try:
                    # Try to get as organization first
                    org = github.get_organization(org_name)
                    result = {
                        "type": "organization",
                        "login": org.login,
                        "name": org.name,
                        "avatar_url": org.avatar_url,
                        "html_url": org.html_url,
                        "description": org.description,
                        "email": org.email,
                        "public_repos": org.public_repos,
                    }
                except Exception:
                    # Fall back to user
                    user = github.get_user(org_name)
                    result = {
                        "type": "user",
                        "login": user.login,
                        "name": user.name,
                        "avatar_url": user.avatar_url,
                        "html_url": user.html_url,
                        "bio": user.bio,
                        "location": user.location,
                        "email": user.email,
                        "public_repos": user.public_repos,
                        "followers": user.followers,
                        "following": user.following,
                    }

                return [
                    ReadResourceContents(
                        content=json.dumps(result, indent=2),
                        mime_type="application/json",
                    )
                ]

            elif (
                parts[0] == "organization"
                and len(parts) == 4
                and parts[2] == "repository"
            ):
                org_name = parts[1]
                repo_name = parts[3]

                try:
                    # Try to get as organization first
                    org = github.get_organization(org_name)
                    repo = org.get_repo(repo_name)
                except Exception:
                    # Fall back to user
                    user = github.get_user(org_name)
                    repo = user.get_repo(repo_name)

                result = github_object_to_json(repo)

                try:
                    result["readme"] = (
                        repo.get_readme().decoded_content.decode()
                        if repo.get_readme()
                        else None
                    )
                except Exception:
                    result["readme"] = None

                result["languages"] = repo.get_languages()
                result["topics"] = repo.get_topics()
                result["contributors"] = [
                    {
                        "login": c.login,
                        "contributions": c.contributions,
                        "avatar_url": c.avatar_url,
                        "html_url": c.html_url,
                    }
                    for c in repo.get_contributors()[:10]
                ]

                return [
                    ReadResourceContents(
                        content=json.dumps(result, indent=2),
                        mime_type="application/json",
                    )
                ]
            else:
                raise ValueError(f"Unsupported resource path: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading GitHub resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

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
                        "name": {
                            "type": "string",
                            "description": "Name of the repository to create",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the repository",
                        },
                        "private": {
                            "type": "boolean",
                            "description": "Whether the repository should be private (default: false)",
                        },
                        "autoInit": {
                            "type": "boolean",
                            "description": "Initialize with empty README (default: false)",
                        },
                        "gitignore_template": {
                            "type": "string",
                            "description": "Template name for .gitignore file",
                        },
                        "license_template": {
                            "type": "string",
                            "description": "Template name for license",
                        },
                        "homepage": {
                            "type": "string",
                            "description": "URL for repository homepage",
                        },
                        "has_issues": {
                            "type": "boolean",
                            "description": "Enable issues for this repository",
                        },
                        "has_projects": {
                            "type": "boolean",
                            "description": "Enable projects for this repository",
                        },
                        "has_wiki": {
                            "type": "boolean",
                            "description": "Enable wiki for this repository",
                        },
                        "has_downloads": {
                            "type": "boolean",
                            "description": "Enable downloads for this repository",
                        },
                        "topics": {
                            "type": "string",
                            "description": "Comma-separated list of topic names",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created repository",
                    "examples": [
                        '{\n  "id": 123456789,\n  "name": "example-repo",\n  "full_name": "username/example-repo",\n  "private": false,\n  "html_url": "https://github.com/username/example-repo",\n  "description": "This is an example repository",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-01T00:00:00Z",\n  "clone_url": "https://github.com/username/example-repo.git",\n  "default_branch": "main"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="search_repositories",
                description="Search for repositories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return. Default: all results.",
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["stars", "forks", "updated"],
                            "description": "Sort repositories by",
                        },
                        "order": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Order of sorting",
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Each individual repository from the search results",
                    "examples": [
                        '{\n  "id": 123456789,\n  "name": "example-repo",\n  "full_name": "username/example-repo",\n  "html_url": "https://github.com/username/example-repo",\n  "description": "This is an example repository",\n  "created_at": "2023-01-01T00:00:00Z",\n  "stargazers_count": 42,\n  "forks_count": 10,\n  "language": "Python"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_public_user_repositories",
                description="List all public repositories for the given user username",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "GitHub username to list repositories for",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return. Default: all results.",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["all", "owner", "member"],
                            "description": "Type of repositories to include",
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["created", "updated", "pushed", "full_name"],
                            "description": "Sort by field",
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Direction of sort",
                        },
                    },
                    "required": ["username"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Each individual repository for the specified user",
                    "examples": [
                        '{\n  "id": 123456789,\n  "name": "user-repo",\n  "full_name": "username/user-repo",\n  "private": false,\n  "html_url": "https://github.com/username/user-repo",\n  "description": "User repository example",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "language": "JavaScript",\n  "forks_count": 5,\n  "stargazers_count": 20\n}'
                    ],
                },
                requiredScopes=["public_repo"],
            ),
            types.Tool(
                name="list_organization_repositories",
                description="List all repositories for the given organization name",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org_name": {
                            "type": "string",
                            "description": "Name of the GitHub organization",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return. Default: all results.",
                        },
                    },
                    "required": ["org_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Each individual repository in the organization",
                    "examples": [
                        '{\n  "id": 123456789,\n  "name": "org-repo",\n  "full_name": "organization/org-repo",\n  "private": false,\n  "html_url": "https://github.com/organization/org-repo",\n  "description": "Organization repository example",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "language": "TypeScript",\n  "forks_count": 15,\n  "stargazers_count": 50\n}'
                    ],
                },
                requiredScopes=["read:org"],
            ),
            # Repository Contents & Commits
            types.Tool(
                name="get_contents",
                description="Get the contents of a file or in a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the file or directory in the repository",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name to get contents from (default: default branch)",
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "Get directory contents recursively",
                        },
                    },
                    "required": ["owner", "repo_name", "path"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File or directory contents from the repository",
                    "examples": [
                        '{\n  "name": "README.md",\n  "path": "README.md",\n  "sha": "abc123def456",\n  "size": 1234,\n  "url": "https://api.github.com/repos/username/repo/contents/README.md",\n  "html_url": "https://github.com/username/repo/blob/main/README.md",\n  "git_url": "https://api.github.com/repos/username/repo/git/blobs/abc123def456",\n  "download_url": "https://raw.githubusercontent.com/username/repo/main/README.md",\n  "type": "file",\n  "content": "IyBFeGFtcGxlIFJlcG9zaXRvcnkKClRoaXMgaXMgYW4gZXhhbXBsZSByZXBvc2l0b3J5IGZvciBkZW1vbnN0cmF0aW9uIHB1cnBvc2VzLg==",\n  "encoding": "base64"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_repository_languages",
                description="List all languages used in a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository or full name in format 'username/repository'",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository (not required if repo_name contains the full path)",
                        },
                    },
                    "required": ["repo_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Languages used in the repository with byte counts",
                    "examples": [
                        '{\n  "JavaScript": 123456,\n  "HTML": 45678,\n  "CSS": 12345,\n  "Python": 7890\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="add_file_to_repository",
                description="Add a file to a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path where to create the file, including filename",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content of the file to create",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name to create file on",
                        },
                        "commit_message": {
                            "type": "string",
                            "description": "Commit message for the file creation",
                        },
                        "sha": {
                            "type": "string",
                            "description": "The blob SHA of the file being replaced",
                        },
                        "committer_name": {
                            "type": "string",
                            "description": "Name of the committer",
                        },
                        "committer_email": {
                            "type": "string",
                            "description": "Email of the committer",
                        },
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the file creation commit operation",
                    "examples": [
                        '{\n  "content": {\n    "name": "example.txt",\n    "path": "example.txt",\n    "sha": "abc123def456",\n    "size": 25,\n    "url": "https://api.github.com/repos/username/repo/contents/example.txt",\n    "html_url": "https://github.com/username/repo/blob/main/example.txt",\n    "git_url": "https://api.github.com/repos/username/repo/git/blobs/abc123def456",\n    "type": "file"\n  },\n  "commit": {\n    "sha": "def789ghi012",\n    "html_url": "https://github.com/username/repo/commit/def789ghi012",\n    "message": "Add example.txt file",\n    "author": {\n      "name": "Example User",\n      "email": "user@example.com",\n      "date": "2023-01-01T00:00:00Z"\n    }\n  }\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_commits",
                description="List all commits for a repository by branch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "branch": {
                            "type": "string",
                            "description": "Branch name to list commits from",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of commits to return. Default: all commits.",
                        },
                        "path": {
                            "type": "string",
                            "description": "Only commits containing this file path will be returned.",
                        },
                        "author": {
                            "type": "string",
                            "description": "GitHub login or email address by which to filter by commit author.",
                        },
                    },
                    "required": ["repo_name", "branch", "owner"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of commits in the repository matching the criteria",
                    "examples": [
                        '{\n  "sha": "102ad652c462cd356aec875d340b97e7361911ae",\n  "node_id": "C_kwDOKdQ8L9oAKDEwMmFkNjUyYzQ2MmNkMzU2YWVjODc1ZDM0MGI5N2U3MzYxOTExYWU",\n  "commit": {\n    "author": {\n      "name": "example-user",\n      "email": "user@example.com",\n      "date": "2025-05-16T17:38:23Z"\n    },\n    "committer": {\n      "name": "GitHub",\n      "email": "noreply@github.com",\n      "date": "2025-05-16T17:38:23Z"\n    },\n    "message": "Create README.md",\n    "tree": {\n      "sha": "ed7a574d49ff563c6f8396db57b0bea8bda4daea",\n      "url": "https://api.github.com/repos/username/repo/git/trees/ed7a574d49ff563c6f8396db57b0bea8bda4daea"\n    },\n    "verification": {\n      "verified": true,\n      "reason": "valid",\n      "signature": "-----BEGIN PGP SIGNATURE-----\\n...\\n-----END PGP SIGNATURE-----"\n    }\n  },\n  "url": "https://api.github.com/repos/username/repo/commits/102ad652c462cd356aec875d340b97e7361911ae",\n  "html_url": "https://github.com/username/repo/commit/102ad652c462cd356aec875d340b97e7361911ae",\n  "comments_url": "https://api.github.com/repos/username/repo/commits/102ad652c462cd356aec875d340b97e7361911ae/comments",\n  "author": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "committer": {\n    "login": "web-flow",\n    "id": 19864447,\n    "avatar_url": "https://avatars.githubusercontent.com/u/19864447?v=4"\n  },\n  "parents": [\n    {\n      "sha": "4021beac283e83c64d74635cac53d4c148c0143a",\n      "url": "https://api.github.com/repos/username/repo/commits/4021beac283e83c64d74635cac53d4c148c0143a"\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="get_commit",
                description="Get detailed information about a specific commit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "commit_sha": {
                            "type": "string",
                            "description": "SHA hash of the commit to retrieve",
                        },
                    },
                    "required": ["owner", "repo_name", "commit_sha"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about the requested commit",
                    "examples": [
                        '{\n  "sha": "102ad652c462cd356aec875d340b97e7361911ae",\n  "node_id": "C_kwDOKdQ8L9oAKDEwMmFkNjUyYzQ2MmNkMzU2YWVjODc1ZDM0MGI5N2U3MzYxOTExYWU",\n  "commit": {\n    "author": {\n      "name": "example-user",\n      "email": "user@example.com",\n      "date": "2025-05-16T17:38:23Z"\n    },\n    "committer": {\n      "name": "GitHub",\n      "email": "noreply@github.com",\n      "date": "2025-05-16T17:38:23Z"\n    },\n    "message": "Create README.md",\n    "tree": {\n      "sha": "ed7a574d49ff563c6f8396db57b0bea8bda4daea",\n      "url": "https://api.github.com/repos/username/repo/git/trees/ed7a574d49ff563c6f8396db57b0bea8bda4daea"\n    },\n    "verification": {\n      "verified": true,\n      "reason": "valid",\n      "signature": "-----BEGIN PGP SIGNATURE-----\\n...\\n-----END PGP SIGNATURE-----"\n    }\n  },\n  "url": "https://api.github.com/repos/username/repo/commits/102ad652c462cd356aec875d340b97e7361911ae",\n  "html_url": "https://github.com/username/repo/commit/102ad652c462cd356aec875d340b97e7361911ae",\n  "comments_url": "https://api.github.com/repos/username/repo/commits/102ad652c462cd356aec875d340b97e7361911ae/comments",\n  "author": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "committer": {\n    "login": "web-flow",\n    "id": 19864447,\n    "avatar_url": "https://avatars.githubusercontent.com/u/19864447?v=4"\n  },\n  "parents": [\n    {\n      "sha": "4021beac283e83c64d74635cac53d4c148c0143a",\n      "url": "https://api.github.com/repos/username/repo/commits/4021beac283e83c64d74635cac53d4c148c0143a"\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            # Star & Engagement
            types.Tool(
                name="star_repository",
                description="Star a repository for the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Full name of the repository in format 'username/repository'",
                        }
                    },
                    "required": ["repo_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the star operation",
                    "examples": ['{"success": true}'],
                },
                requiredScopes=["user"],
            ),
            types.Tool(
                name="list_stargazers",
                description="List all stargazers for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of stargazers to return. Default: all stargazers.",
                        },
                    },
                    "required": ["owner", "repo_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of users who have starred the repository",
                    "examples": [
                        '{\n  "login": "example-user",\n  "id": 123456,\n  "node_id": "MDQ6VXNlcjEyMzQ1Ng==",\n  "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4",\n  "html_url": "https://github.com/example-user",\n  "type": "User"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="get_stargazers_count",
                description="Get the number of stargazers for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                    },
                    "required": ["owner", "repo_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The number of users who have starred the repository",
                    "examples": ["42"],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_starred_repos_by_user",
                description="List all repositories starred by the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of repos to return. Default: all repos.",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of repositories starred by the authenticated user",
                    "examples": [
                        '{\n  "id": 123456789,\n  "name": "example-repo",\n  "full_name": "username/example-repo",\n  "private": false,\n  "html_url": "https://github.com/username/example-repo",\n  "description": "An example repository",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "stargazers_count": 42,\n  "language": "Python"\n}'
                    ],
                },
                requiredScopes=["user"],
            ),
            # Issues & Pull Requests
            types.Tool(
                name="list_issues",
                description="List all issues for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of issues to return. Default: all issues.",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Filter issues by state. Default: open",
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of label names to filter by.",
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Filter by user assigned to issues.",
                        },
                        "creator": {
                            "type": "string",
                            "description": "Filter by user who created the issues.",
                        },
                        "mentioned": {
                            "type": "string",
                            "description": "Filter by user mentioned in issues.",
                        },
                        "milestone": {
                            "type": "string",
                            "description": 'Filter by milestone name or "*" for issues with any milestone',
                        },
                        "since": {
                            "type": "string",
                            "description": "Only issues updated at or after this time (ISO 8601 format)",
                        },
                        "sort": {
                            "type": "string",
                            "enum": ["created", "updated", "comments"],
                            "description": "Field to sort by",
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Direction of sort",
                        },
                    },
                    "required": ["repo_name", "owner"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of issues in the repository matching the criteria",
                    "examples": [
                        '{\n  "id": 12345678,\n  "number": 42,\n  "title": "Example issue title",\n  "state": "open",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "html_url": "https://github.com/username/repo/issues/42",\n  "body": "This is an example issue description",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "labels": [\n    {\n      "id": 123456789,\n      "name": "bug",\n      "color": "d73a4a"\n    }\n  ],\n  "assignees": [\n    {\n      "login": "assigned-user",\n      "id": 654321,\n      "avatar_url": "https://avatars.githubusercontent.com/u/654321?v=4"\n    }\n  ],\n  "comments": 5\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="get_issue",
                description="Get a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "issue_number": {
                            "type": "string",
                            "description": "Issue number to retrieve",
                        },
                    },
                    "required": ["repo_name", "owner", "issue_number"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about the requested issue",
                    "examples": [
                        '{\n  "url": "https://api.github.com/repos/username/repo/issues/8",\n  "repository_url": "https://api.github.com/repos/username/repo",\n  "labels_url": "https://api.github.com/repos/username/repo/issues/8/labels{/name}",\n  "comments_url": "https://api.github.com/repos/username/repo/issues/8/comments",\n  "events_url": "https://api.github.com/repos/username/repo/issues/8/events",\n  "html_url": "https://github.com/username/repo/issues/8",\n  "id": 3069613943,\n  "node_id": "I_kwDOKdQ8L8629pd3",\n  "number": 8,\n  "title": "Example issue title",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "labels": [],\n  "state": "open",\n  "locked": false,\n  "assignee": null,\n  "assignees": [],\n  "milestone": null,\n  "comments": 0,\n  "created_at": "2025-05-16T18:08:57Z",\n  "updated_at": "2025-05-16T18:08:57Z",\n  "closed_at": null,\n  "body": "This is a test issue description",\n  "reactions": {\n    "total_count": 0,\n    "+1": 0,\n    "-1": 0,\n    "laugh": 0,\n    "hooray": 0,\n    "confused": 0,\n    "heart": 0,\n    "rocket": 0,\n    "eyes": 0\n  },\n  "timeline_url": "https://api.github.com/repos/username/repo/issues/8/timeline"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="create_issue",
                description="Create a new issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the issue",
                        },
                        "body": {
                            "type": "string",
                            "description": "Body/content of the issue",
                        },
                        "labels": {
                            "type": "string",
                            "description": "Comma-separated list of labels to add",
                        },
                        "assignees": {
                            "type": "string",
                            "description": "Comma-separated list of users to assign",
                        },
                        "milestone": {
                            "type": "integer",
                            "description": "Milestone ID to assign to this issue",
                        },
                    },
                    "required": ["repo_name", "owner", "title", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created issue",
                    "examples": [
                        '{\n  "url": "https://api.github.com/repos/username/repo/issues/8",\n  "repository_url": "https://api.github.com/repos/username/repo",\n  "labels_url": "https://api.github.com/repos/username/repo/issues/8/labels{/name}",\n  "comments_url": "https://api.github.com/repos/username/repo/issues/8/comments",\n  "events_url": "https://api.github.com/repos/username/repo/issues/8/events",\n  "html_url": "https://github.com/username/repo/issues/8",\n  "id": 3069613943,\n  "node_id": "I_kwDOKdQ8L8629pd3",\n  "number": 8,\n  "title": "Example issue title",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "labels": [],\n  "state": "open",\n  "locked": false,\n  "assignee": null,\n  "assignees": [],\n  "milestone": null,\n  "comments": 0,\n  "created_at": "2025-05-16T18:08:57Z",\n  "updated_at": "2025-05-16T18:08:57Z",\n  "closed_at": null,\n  "body": "This is a test issue description",\n  "reactions": {\n    "total_count": 0,\n    "+1": 0,\n    "-1": 0,\n    "laugh": 0,\n    "hooray": 0,\n    "confused": 0,\n    "heart": 0,\n    "rocket": 0,\n    "eyes": 0\n  },\n  "timeline_url": "https://api.github.com/repos/username/repo/issues/8/timeline"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="update_issue",
                description="Update a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "issue_number": {
                            "type": "string",
                            "description": "Issue number to update",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title for the issue",
                        },
                        "body": {
                            "type": "string",
                            "description": "New body content for the issue",
                        },
                    },
                    "required": ["repo_name", "owner", "issue_number", "title", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the updated issue",
                    "examples": [
                        '{\n  "url": "https://api.github.com/repos/username/repo/issues/8",\n  "repository_url": "https://api.github.com/repos/username/repo",\n  "labels_url": "https://api.github.com/repos/username/repo/issues/8/labels{/name}",\n  "comments_url": "https://api.github.com/repos/username/repo/issues/8/comments",\n  "events_url": "https://api.github.com/repos/username/repo/issues/8/events",\n  "html_url": "https://github.com/username/repo/issues/8",\n  "id": 3069613943,\n  "node_id": "I_kwDOKdQ8L8629pd3",\n  "number": 8,\n  "title": "Updated Issue Example",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "labels": [],\n  "state": "open",\n  "locked": false,\n  "assignee": null,\n  "assignees": [],\n  "milestone": null,\n  "comments": 0,\n  "created_at": "2025-05-16T18:08:57Z",\n  "updated_at": "2025-05-16T18:09:18Z",\n  "closed_at": null,\n  "body": "This is an updated issue description",\n  "reactions": {\n    "total_count": 0,\n    "+1": 0,\n    "-1": 0,\n    "laugh": 0,\n    "hooray": 0,\n    "confused": 0,\n    "heart": 0,\n    "rocket": 0,\n    "eyes": 0\n  },\n  "timeline_url": "https://api.github.com/repos/username/repo/issues/8/timeline"\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="add_comment_to_issue",
                description="Add a comment to a specific issue for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "issue_number": {
                            "type": "string",
                            "description": "Issue number to add a comment to",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Content of the comment to add",
                        },
                    },
                    "required": ["repo_name", "owner", "issue_number", "comment"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the created comment",
                    "examples": [
                        '{\n  "url": "https://api.github.com/repos/username/repo/issues/comments/2887380907",\n  "html_url": "https://github.com/username/repo/issues/8#issuecomment-2887380907",\n  "issue_url": "https://api.github.com/repos/username/repo/issues/8",\n  "id": 2887380907,\n  "node_id": "IC_kwDOKdQ8L86sGe-r",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "created_at": "2025-05-16T18:09:31Z",\n  "updated_at": "2025-05-16T18:09:31Z",\n  "author_association": "OWNER",\n  "body": "This is a comment on the issue",\n  "reactions": {\n    "url": "https://api.github.com/repos/username/repo/issues/comments/2887380907/reactions",\n    "total_count": 0,\n    "+1": 0,\n    "-1": 0,\n    "laugh": 0,\n    "hooray": 0,\n    "confused": 0,\n    "heart": 0,\n    "rocket": 0,\n    "eyes": 0\n  }\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_branches",
                description="List all branches for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of branches to return. Default: all branches.",
                        },
                    },
                    "required": ["repo_name", "owner"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of branches in the repository",
                    "examples": [
                        '{\n  "name": "main",\n  "commit": {\n    "sha": "abc123def456",\n    "url": "https://api.github.com/repos/username/repo/commits/abc123def456"\n  },\n  "protected": true\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="create_branch",
                description="Create a new branch from existing branch for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "branch_name": {
                            "type": "string",
                            "description": "Name for the new branch",
                        },
                        "start_point": {
                            "type": "string",
                            "description": "Name of the reference branch to start from (usually 'main' or 'master')",
                        },
                    },
                    "required": ["repo_name", "owner", "branch_name", "start_point"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the created branch reference",
                    "examples": [
                        '{\n  "ref": "refs/heads/new-branch-name",\n  "node_id": "REF_kwDOHNGE1rByZWZzL2hlYWRzL25ldy1icmFuY2gtbmFtZQ",\n  "url": "https://api.github.com/repos/username/repo/git/refs/heads/new-branch-name",\n  "object": {\n    "sha": "abc123def456",\n    "type": "commit",\n    "url": "https://api.github.com/repos/username/repo/git/commits/abc123def456"\n  }\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="list_pull_requests",
                description="List all pull requests for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "max_limit": {
                            "type": "integer",
                            "description": "Maximum number of pull requests to return. Default: all PRs.",
                        },
                        "state": {
                            "type": "string",
                            "enum": ["open", "closed", "all"],
                            "description": "Filter PRs by state. Default: open",
                        },
                        "head": {
                            "type": "string",
                            "description": "Filter pulls by head branch name or user:branch format.",
                        },
                        "base": {
                            "type": "string",
                            "description": "Filter pulls by base branch name.",
                        },
                        "sort": {
                            "type": "string",
                            "enum": [
                                "created",
                                "updated",
                                "popularity",
                                "long-running",
                            ],
                            "description": "Sort PRs by. Default: created",
                        },
                        "direction": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Direction of sort. Default: desc",
                        },
                        "draft": {
                            "type": "boolean",
                            "description": "Filter for draft or non-draft PRs",
                        },
                        "since": {
                            "type": "string",
                            "description": "Only PRs updated at or after this time (ISO 8601 format)",
                        },
                    },
                    "required": ["repo_name", "owner"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of pull requests in the repository matching the criteria",
                    "examples": [
                        '{\n  "id": 12345678,\n  "number": 42,\n  "title": "Example pull request title",\n  "state": "open",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "html_url": "https://github.com/username/repo/pull/42",\n  "body": "This is an example pull request description",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "head": {\n    "ref": "feature-branch",\n    "sha": "abc123def456"\n  },\n  "base": {\n    "ref": "main",\n    "sha": "def789ghi012"\n  },\n  "draft": false,\n  "merged": false,\n  "mergeable": true,\n  "comments": 3,\n  "commits": 2,\n  "additions": 100,\n  "deletions": 50,\n  "changed_files": 5\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="get_pull_request",
                description="Get a specific pull request for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "pull_request_number": {
                            "type": "string",
                            "description": "Pull request number to retrieve",
                        },
                    },
                    "required": ["repo_name", "owner", "pull_request_number"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about the requested pull request",
                    "examples": [
                        '{\n  "id": 12345678,\n  "number": 42,\n  "title": "Example pull request title",\n  "state": "open",\n  "locked": false,\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-02T00:00:00Z",\n  "closed_at": null,\n  "merged_at": null,\n  "html_url": "https://github.com/username/repo/pull/42",\n  "body": "This is an example pull request description with more details",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "head": {\n    "ref": "feature-branch",\n    "sha": "abc123def456",\n    "label": "username:feature-branch"\n  },\n  "base": {\n    "ref": "main",\n    "sha": "def789ghi012",\n    "label": "username:main"\n  },\n  "draft": false,\n  "merged": false,\n  "mergeable": true,\n  "mergeable_state": "clean",\n  "comments": 5,\n  "review_comments": 3,\n  "commits": 2,\n  "additions": 100,\n  "deletions": 50,\n  "changed_files": 5\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="create_pull_request",
                description="Create a new pull request for a repository",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Owner username of the repository",
                        },
                        "repo_name": {
                            "type": "string",
                            "description": "Name of the repository",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the pull request",
                        },
                        "body": {
                            "type": "string",
                            "description": "Description of the pull request",
                        },
                        "base": {
                            "type": "string",
                            "description": "The name of the branch you want your changes pulled into",
                        },
                        "head": {
                            "type": "string",
                            "description": "The name of the branch where your changes are implemented",
                        },
                        "draft": {
                            "type": "boolean",
                            "description": "Create PR as draft",
                        },
                        "maintainer_can_modify": {
                            "type": "boolean",
                            "description": "Allow modifications by maintainers",
                        },
                        "issue": {
                            "type": "integer",
                            "description": "Issue number to convert to a pull request",
                        },
                    },
                    "required": ["owner", "repo_name", "title", "body", "base", "head"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the created pull request",
                    "examples": [
                        '{\n  "id": 12345678,\n  "number": 42,\n  "title": "Example pull request title",\n  "state": "open",\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-01T00:00:00Z",\n  "html_url": "https://github.com/username/repo/pull/42",\n  "body": "This is an example pull request description",\n  "user": {\n    "login": "example-user",\n    "id": 123456,\n    "avatar_url": "https://avatars.githubusercontent.com/u/123456?v=4"\n  },\n  "head": {\n    "ref": "feature-branch",\n    "sha": "abc123def456"\n  },\n  "base": {\n    "ref": "main",\n    "sha": "def789ghi012"\n  },\n  "draft": false,\n  "merged": false,\n  "mergeable": true\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
            ),
            types.Tool(
                name="fork_repository",
                description="Fork a repository to the authenticated user's account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repo_name": {
                            "type": "string",
                            "description": "Full name of the repository in format 'username/repository'",
                        }
                    },
                    "required": ["repo_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the forked repository",
                    "examples": [
                        '{\n  "id": 987654321,\n  "name": "forked-repo",\n  "full_name": "your-username/forked-repo",\n  "private": false,\n  "html_url": "https://github.com/your-username/forked-repo",\n  "description": "A fork of username/repository",\n  "fork": true,\n  "created_at": "2023-01-01T00:00:00Z",\n  "updated_at": "2023-01-01T00:00:00Z",\n  "clone_url": "https://github.com/your-username/forked-repo.git",\n  "source": {\n    "id": 123456789,\n    "name": "repository",\n    "full_name": "username/repository"\n  }\n}'
                    ],
                },
                requiredScopes=["repo", "public_repo"],
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
                # Add new parameters
                if "gitignore_template" in arguments:
                    optional_params["gitignore_template"] = arguments[
                        "gitignore_template"
                    ]
                if "license_template" in arguments:
                    optional_params["license_template"] = arguments["license_template"]
                if "homepage" in arguments:
                    optional_params["homepage"] = arguments["homepage"]
                if "has_issues" in arguments:
                    optional_params["has_issues"] = arguments["has_issues"]
                if "has_projects" in arguments:
                    optional_params["has_projects"] = arguments["has_projects"]
                if "has_wiki" in arguments:
                    optional_params["has_wiki"] = arguments["has_wiki"]
                if "has_downloads" in arguments:
                    optional_params["has_downloads"] = arguments["has_downloads"]
                if "topics" in arguments:
                    optional_params["topics"] = arguments["topics"].split(",")

                user = github.get_user()
                repo = user.create_repo(arguments["name"], **optional_params)
                result = github_object_to_json(repo)

            elif name == "search_repositories":
                # Add sorting parameters if provided
                kwargs = {"query": arguments["query"]}
                if "sort" in arguments:
                    kwargs["sort"] = arguments["sort"]
                if "order" in arguments:
                    kwargs["order"] = arguments["order"]

                repos = github.search_repositories(**kwargs)
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(repos[:max_limit]))
                else:
                    result = github_object_to_json(list(repos))

            elif name == "list_public_user_repositories":
                user = github.get_user(arguments["username"])

                # Add repository filtering parameters
                kwargs = {}
                if "type" in arguments:
                    kwargs["type"] = arguments["type"]
                if "sort" in arguments:
                    kwargs["sort"] = arguments["sort"]
                if "direction" in arguments:
                    kwargs["direction"] = arguments["direction"]

                repos = user.get_repos(**kwargs)
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(repos[:max_limit]))
                else:
                    result = github_object_to_json(list(repos))

            elif name == "list_organization_repositories":
                org = github.get_organization(arguments["org_name"])
                repos = org.get_repos()
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(repos[:max_limit]))
                else:
                    result = github_object_to_json(list(repos))

            # Repository Contents & Commits
            elif name == "get_contents":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                # Handle recursive parameter if present
                if arguments.get("recursive", False):
                    contents = repo.get_contents(
                        arguments["path"], ref=arguments["branch"], recursive=True
                    )
                else:
                    contents = repo.get_contents(
                        arguments["path"], ref=arguments["branch"]
                    )
                result = github_object_to_json(contents)

            elif name == "list_repository_languages":
                # Handle both "owner/repo" format and separate owner & repo_name parameters
                if "/" in arguments["repo_name"]:
                    repo = github.get_repo(arguments["repo_name"])
                else:
                    # Check if owner is provided separately
                    if "owner" in arguments:
                        repo = github.get_repo(
                            f"{arguments['owner']}/{arguments['repo_name']}"
                        )
                    else:
                        # If no owner provided, this will likely fail, but follow the original code behavior
                        repo = github.get_repo(arguments["repo_name"])
                result = repo.get_languages()

            elif name == "add_file_to_repository":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")

                # Set up optional parameters for file creation
                kwargs = {
                    "path": arguments["path"],
                    "message": arguments["commit_message"],
                    "content": arguments["content"],
                    "branch": arguments["branch"],
                }

                # Add optional parameters if provided
                if "sha" in arguments:
                    kwargs["sha"] = arguments["sha"]

                # Add committer info if provided
                if "committer_name" in arguments and "committer_email" in arguments:
                    committer = {
                        "name": arguments["committer_name"],
                        "email": arguments["committer_email"],
                    }
                    kwargs["committer"] = committer

                response = repo.create_file(**kwargs)
                result = github_object_to_json(response)

            elif name == "get_commit":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                commit = repo.get_commit(arguments["commit_sha"])
                result = github_object_to_json(commit)

            elif name == "list_commits":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )

                # Set up optional parameters for filtering commits
                kwargs = {"sha": arguments["branch"]}
                if "path" in arguments:
                    kwargs["path"] = arguments["path"]
                if "author" in arguments:
                    kwargs["author"] = arguments["author"]

                commits = repo.get_commits(**kwargs)

                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(commits[:max_limit]))
                else:
                    result = github_object_to_json(list(commits))

            # Star & Engagement
            elif name == "star_repository":
                user = github.get_user()
                repo = github.get_repo(arguments["repo_name"])
                response = user.add_to_starred(repo)
                result = {"success": True if response is None else response}

            elif name == "list_stargazers":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                stargazers = repo.get_stargazers()
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(stargazers[:max_limit]))
                else:
                    result = github_object_to_json(list(stargazers))

            elif name == "get_stargazers_count":
                repo = github.get_repo(
                    arguments["owner"] + "/" + arguments["repo_name"]
                )
                result = repo.stargazers_count

            elif name == "list_starred_repos_by_user":
                user = github.get_user()
                starred_repos = user.get_starred()
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(starred_repos[:max_limit]))
                else:
                    result = github_object_to_json(list(starred_repos))

            # Issues & Pull Requests
            elif name == "list_issues":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")

                # Set up optional parameters for filtering issues
                kwargs = {}
                if "state" in arguments:
                    kwargs["state"] = arguments["state"]
                if "labels" in arguments:
                    kwargs["labels"] = arguments["labels"].split(",")
                if "assignee" in arguments:
                    kwargs["assignee"] = arguments["assignee"]
                if "creator" in arguments:
                    kwargs["creator"] = arguments["creator"]
                if "mentioned" in arguments:
                    kwargs["mentioned"] = arguments["mentioned"]
                if "milestone" in arguments:
                    if arguments["milestone"] == "*":
                        kwargs["milestone"] = "*"
                    else:
                        try:
                            milestone_id = int(arguments["milestone"])
                            kwargs["milestone"] = repo.get_milestone(milestone_id)
                        except ValueError:
                            # If not an integer, assume it's a milestone title
                            milestones = repo.get_milestones()
                            for milestone in milestones:
                                if milestone.title == arguments["milestone"]:
                                    kwargs["milestone"] = milestone
                                    break
                if "since" in arguments:
                    kwargs["since"] = arguments["since"]
                if "sort" in arguments:
                    kwargs["sort"] = arguments["sort"]
                if "direction" in arguments:
                    kwargs["direction"] = arguments["direction"]

                issues = repo.get_issues(**kwargs)

                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(issues[:max_limit]))
                else:
                    result = github_object_to_json(list(issues))

            elif name == "get_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                result = github_object_to_json(issue)

            elif name == "create_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")

                # Basic parameters
                kwargs = {
                    "title": arguments["title"],
                    "body": arguments["body"],
                }

                # Optional parameters
                if "labels" in arguments:
                    kwargs["labels"] = arguments["labels"].split(",")
                if "assignees" in arguments:
                    kwargs["assignees"] = arguments["assignees"].split(",")
                if "milestone" in arguments:
                    kwargs["milestone"] = repo.get_milestone(arguments["milestone"])

                issue = repo.create_issue(**kwargs)
                result = github_object_to_json(issue)

            elif name == "update_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                issue.edit(title=arguments["title"], body=arguments["body"])
                result = github_object_to_json(issue)

            elif name == "add_comment_to_issue":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                issue = repo.get_issue(int(arguments["issue_number"]))
                comment = issue.create_comment(arguments["comment"])
                result = github_object_to_json(comment)

            elif name == "list_branches":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                branches = repo.get_branches()
                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(branches[:max_limit]))
                else:
                    result = github_object_to_json(list(branches))

            elif name == "create_branch":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                base_ref = repo.get_git_ref(f"heads/{arguments['start_point']}")
                base_sha = base_ref.object.sha
                ref = repo.create_git_ref(
                    f"refs/heads/{arguments['branch_name']}", sha=base_sha
                )
                result = github_object_to_json(ref)

            elif name == "list_pull_requests":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")

                # Set up optional parameters for filtering PRs
                kwargs = {}
                if "state" in arguments:
                    kwargs["state"] = arguments["state"]
                if "head" in arguments:
                    kwargs["head"] = arguments["head"]
                if "base" in arguments:
                    kwargs["base"] = arguments["base"]
                if "sort" in arguments:
                    kwargs["sort"] = arguments["sort"]
                if "direction" in arguments:
                    kwargs["direction"] = arguments["direction"]
                if "draft" in arguments:
                    # PyGithub 1.55+ supports 'draft' param
                    kwargs["draft"] = arguments["draft"]
                if "since" in arguments:
                    # For requests that support 'since' parameter
                    kwargs["since"] = arguments["since"]

                pull_requests = repo.get_pulls(**kwargs)

                if "max_limit" in arguments:
                    max_limit = int(arguments["max_limit"])
                    result = github_object_to_json(list(pull_requests[:max_limit]))
                else:
                    result = github_object_to_json(list(pull_requests))

            elif name == "get_pull_request":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")
                pull_request = repo.get_pull(int(arguments["pull_request_number"]))
                result = github_object_to_json(pull_request)

            elif name == "create_pull_request":
                repo = github.get_repo(f"{arguments['owner']}/{arguments['repo_name']}")

                # Basic parameters
                kwargs = {
                    "title": arguments["title"],
                    "body": arguments["body"],
                    "base": arguments["base"],
                    "head": arguments["head"],
                }

                # Optional parameters
                if "draft" in arguments:
                    kwargs["draft"] = arguments["draft"]
                if "maintainer_can_modify" in arguments:
                    kwargs["maintainer_can_modify"] = arguments["maintainer_can_modify"]

                # Issue parameter (convert issue to PR)
                if "issue" in arguments:
                    kwargs["issue"] = arguments["issue"]

                pull_request = repo.create_pull(**kwargs)
                result = github_object_to_json(pull_request)

            elif name == "fork_repository":
                user = github.get_user()
                repo_name = arguments["repo_name"]
                repo = github.get_repo(repo_name)
                forked_repo = user.create_fork(repo)
                result = github_object_to_json(forked_repo)

            else:
                raise ValueError(f"Unknown tool: {name}")

            # For array results, return each item as a separate TextContent
            if isinstance(result, list):
                return [
                    types.TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result
                ]
            else:
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

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


def github_object_to_json(obj):
    """
    Convert a GitHub object to a serializable dictionary.
    """
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return [github_object_to_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: github_object_to_json(v) for k, v in obj.items()}
    elif hasattr(obj, "_rawData") and obj._rawData:
        return obj._rawData
    elif isinstance(obj, GithubObject):
        result = {}
        for attr in dir(obj):
            if not attr.startswith("_") and attr not in (
                "get_",
                "create_",
                "update_",
                "delete_",
            ):
                try:
                    value = getattr(obj, attr)
                    if not callable(value):
                        result[attr] = github_object_to_json(value)
                except Exception:
                    pass
        return result
    else:
        try:
            return vars(obj)
        except:
            return str(obj)


if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
