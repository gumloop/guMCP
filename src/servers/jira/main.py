import os
import sys

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import json
import requests

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.jira.util import (
    authenticate_and_save_credentials,
    get_credentials,
    format_issue_description,
    format_comment_body,
    format_project_payload,
)

SERVICE_NAME = Path(__file__).parent.name
# JIRA API scopes required for operations
# Reference: https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/#supported-scopes
SCOPES = [
    "read:jira-work",
    "write:jira-work",
    "read:jira-user",
    "offline_access",
    "manage:jira-project",
    "manage:jira-configuration",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_jira_client(
    user_id,
    api_key=None,
    return_full_credentials=False,
    selected_site_index=None,
    target_cloud_id=None,
    target_site_name=None,
):
    """
    Create a new authenticated client for JIRA API calls.

    Args:
        user_id (str): The user ID for which to retrieve credentials.
        api_key (str, optional): An API key to use instead of OAuth credentials.
        return_full_credentials (bool, optional): Whether to include full credential details in the return object.
        selected_site_index (int, optional): Index of the site to use if multiple are available.
        target_cloud_id (str, optional): Specific cloud ID to use.
        target_site_name (str, optional): Specific site name to use.

    Returns:
        dict: A client configuration dictionary with headers and base URL.
    """
    try:
        # Get OAuth credentials and create authorization header
        credentials = await get_credentials(
            user_id=user_id,
            service_name=SERVICE_NAME,
            api_key=api_key,
            return_full_credentials=return_full_credentials,
        )

        if return_full_credentials:
            access_token = credentials.get("access_token")
            token_type = credentials.get("token_type", "Bearer")
        else:
            access_token = credentials
            token_type = "Bearer"

        auth_header = f"{token_type} {access_token}"

        # Create basic auth headers for fetching accessible resources
        basic_headers = {"Authorization": auth_header, "Accept": "application/json"}

        # Fetch accessible Atlassian sites for this token
        resources_response = requests.get(
            "https://api.atlassian.com/oauth/token/accessible-resources",
            headers=basic_headers,
        )

        if resources_response.status_code != 200:
            raise ValueError(
                f"Failed to fetch accessible resources: {resources_response.status_code}"
            )

        resources = resources_response.json()

        if not resources:
            raise ValueError("No accessible Atlassian sites found")

        has_multiple_sites = len(resources) > 1
        selected_site = None

        # If specific cloud_id or site_name was provided, use it
        if target_cloud_id:
            for site in resources:
                if site.get("id") == target_cloud_id:
                    selected_site = site
                    break
            if not selected_site:
                raise ValueError(
                    f"Specified cloud ID '{target_cloud_id}' not found in accessible sites"
                )

        elif target_site_name:
            for site in resources:
                site_name = site.get("name", "")
                if site_name.lower() == target_site_name.lower():
                    selected_site = site
                    break
            if not selected_site:
                available_site_names = [site.get("name", "") for site in resources]
                raise ValueError(
                    f"Specified site name '{target_site_name}' not found in accessible sites. Available: {', '.join(available_site_names)}"
                )

        # If no specific site was requested
        if selected_site is None:
            # If only one site exists, just use it
            if len(resources) == 1:
                selected_site = resources[0]
            # Otherwise use the selected index or default to first site
            else:
                selected_site_index = (
                    0
                    if selected_site_index is None
                    or selected_site_index < 0
                    or selected_site_index >= len(resources)
                    else selected_site_index
                )
                selected_site = resources[selected_site_index]

        cloud_id = selected_site.get("id")
        site_name = selected_site.get("name")

        base_url = f"https://api.atlassian.com/ex/jira/{cloud_id}"

        # Create headers for read operations (GET requests)
        read_headers = {"Authorization": auth_header, "Accept": "application/json"}

        # Create headers for write operations (POST, PUT, DELETE requests)
        write_headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Atlassian-Token": "nocheck",  # Required to bypass XSRF protection
        }

        # Return client configuration
        client = {
            "headers": read_headers,
            "write_headers": write_headers,
            "base_url": base_url,
            "site_name": site_name,
            "cloud_id": cloud_id,
            "available_sites": resources,
            "has_multiple_sites": has_multiple_sites,
            "credentials": credentials if return_full_credentials else None,
        }

        return client

    except Exception as e:
        logger.error(f"Error creating JIRA client: {str(e)}")
        raise


def create_server(user_id, api_key=None):
    """
    Initialize and configure the JIRA MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("jira-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """Return a list of available JIRA tools."""

        site_selection_description = "If you have access to multiple Jira sites, you must specify either cloud_id or site_name."

        # Common site selection properties to add to all tools
        site_selection_properties = {
            "cloud_id": {
                "type": "string",
                "description": "Specific Atlassian Cloud ID to use (required only if you have multiple sites)",
            },
            "site_name": {
                "type": "string",
                "description": "Atlassian site name to use (required only if you have multiple sites)",
            },
        }

        # Project Tools
        project_tools = [
            Tool(
                name="create_project",
                description=f"Set up a new JIRA project for a team, client, or initiative. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        "name": {"type": "string", "description": "Project name"},
                        "description": {
                            "type": "string",
                            "description": "Project description",
                        },
                        "project_type_key": {
                            "type": "string",
                            "description": "Type of project (required)",
                            "enum": ["software", "service_desk", "business"],
                        },
                        "lead_account_id": {
                            "type": "string",
                            "description": "Account ID of the project lead",
                        },
                        "template_key": {
                            "type": "string",
                            "description": "Template key for project creation",
                        },
                        **site_selection_properties,
                    },
                    "required": ["key", "name", "project_type_key"],
                },
            ),
            Tool(
                name="get_project",
                description=f"Retrieve metadata about a specific project. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key"],
                },
            ),
            Tool(
                name="update_project",
                description=f"Modify project details like name, lead, or description. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        "name": {"type": "string", "description": "New project name"},
                        "description": {
                            "type": "string",
                            "description": "New project description",
                        },
                        "lead_account_id": {
                            "type": "string",
                            "description": "Account ID of the new project lead",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key"],
                },
            ),
            Tool(
                name="delete_project",
                description=f"Delete an entire project and its issues. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key"],
                },
            ),
            Tool(
                name="list_projects",
                description=f"List all accessible JIRA projects. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                        },
                        **site_selection_properties,
                    },
                },
            ),
            Tool(
                name="get_issue_types_for_project",
                description=f"Get all valid issue types (e.g., Task, Bug, Story) for a project. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key"],
                },
            ),
        ]

        # Issue Tools
        issue_tools = [
            Tool(
                name="create_issue",
                description=f"Create a new issue, bug, task, or story in a project. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Issue summary/title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description",
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Issue type",
                            "enum": ["Task", "Bug", "Story", "Epic"],
                        },
                        "assignee_account_id": {
                            "type": "string",
                            "description": "Account ID of assignee",
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority",
                            "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                        },
                        "parent_key": {
                            "type": "string",
                            "description": "Parent issue key (for sub-tasks)",
                        },
                        "story_points": {
                            "type": "number",
                            "description": "Story points estimate",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Issue labels",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key", "summary", "issue_type"],
                },
            ),
            Tool(
                name="get_issue",
                description=f"Get full details of an issue (title, description, status, comments, etc.). {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., PRJ-123)",
                        },
                        "expand": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand (e.g., transitions, changelog)",
                        },
                        **site_selection_properties,
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="update_issue",
                description=f"Modify issue fields such as assignee, priority, or status. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., PRJ-123)",
                        },
                        "summary": {
                            "type": "string",
                            "description": "Issue summary/title",
                        },
                        "description": {
                            "type": "string",
                            "description": "Issue description",
                        },
                        "assignee_account_id": {
                            "type": "string",
                            "description": "Account ID of assignee",
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority",
                            "enum": ["Highest", "High", "Medium", "Low", "Lowest"],
                        },
                        "story_points": {
                            "type": "number",
                            "description": "Story points estimate",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Issue labels",
                        },
                        **site_selection_properties,
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="delete_issue",
                description=f"Permanently remove an issue from a project. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., PRJ-123)",
                        },
                        **site_selection_properties,
                    },
                    "required": ["issue_key"],
                },
            ),
            Tool(
                name="transition_my_issue",
                description=f"Move an assigned issue to a new status (e.g., 'In Progress', 'Done'). {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., PRJ-123)",
                        },
                        "transition_to": {
                            "type": "string",
                            "description": "Target status",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Comment to add during transition",
                        },
                        **site_selection_properties,
                    },
                    "required": ["issue_key", "transition_to"],
                },
            ),
            Tool(
                name="list_issues",
                description=f"List issues by JQL query. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jql": {"type": "string", "description": "JQL query string"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                        },
                        **site_selection_properties,
                    },
                    "required": ["jql"],
                },
            ),
            Tool(
                name="comment_on_issue",
                description=f"Add a comment to an issue. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_key": {
                            "type": "string",
                            "description": "Issue key (e.g., PRJ-123)",
                        },
                        "body": {"type": "string", "description": "Comment text"},
                        **site_selection_properties,
                    },
                    "required": ["issue_key", "body"],
                },
            ),
        ]

        # User-specific Tools
        user_tools = [
            Tool(
                name="get_myself",
                description=f"Get information about the authenticated user. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {**site_selection_properties},
                },
            ),
            Tool(
                name="get_my_issues",
                description=f"Fetch all open issues assigned to the current user. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status (e.g., 'In Progress')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                        },
                        **site_selection_properties,
                    },
                },
            ),
            Tool(
                name="get_my_recent_activity",
                description=f"View recently updated issues the user interacted with. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                        },
                        **site_selection_properties,
                    },
                },
            ),
            Tool(
                name="get_my_permissions",
                description=f"Determine what actions the user is allowed to perform in a project. {site_selection_description}",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_key": {
                            "type": "string",
                            "description": "Project key (e.g., PRJ)",
                        },
                        "permissions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific permissions to check",
                        },
                        **site_selection_properties,
                    },
                    "required": ["project_key"],
                },
            ),
        ]

        return project_tools + issue_tools + user_tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Handle JIRA tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called.
            arguments (dict | None): Parameters passed to the tool.

        Returns:
            list[Union[TextContent, ImageContent, EmbeddedResource]]:
                Output content from tool execution.
        """
        if arguments is None:
            arguments = {}

        # Extract site information from arguments
        target_cloud_id = arguments.get("cloud_id", None)
        target_site_name = arguments.get("site_name", None)

        # Create JIRA client with the specific site information if provided
        jira_client = await create_jira_client(
            server.user_id,
            api_key=server.api_key,
            target_cloud_id=target_cloud_id,
            target_site_name=target_site_name,
        )

        headers = jira_client["headers"]
        base_url = jira_client["base_url"]
        has_multiple_sites = jira_client["has_multiple_sites"]

        # For all tools, validate that site info is provided if needed
        if has_multiple_sites and not (target_cloud_id or target_site_name):
            available_site_names = [
                site.get("name", "") for site in jira_client.get("available_sites", [])
            ]
            site_list = ", ".join(available_site_names)
            return [
                TextContent(
                    type="text",
                    text=f"Error: Multiple Jira sites available. You must specify either 'cloud_id' or 'site_name' for this operation. Available sites: {site_list}",
                )
            ]

        # Make a clean copy of arguments without site selection parameters
        # This ensures we don't pass these to the API
        api_args = arguments.copy()
        api_args.pop("cloud_id", None)
        api_args.pop("site_name", None)

        try:
            # User-specific tools
            if name == "get_myself":
                try:
                    # Try API v3 first
                    response = requests.get(
                        f"{base_url}/rest/api/3/myself", headers=headers
                    )

                    # If it fails with 404, try API v2
                    if response.status_code == 404:
                        response = requests.get(
                            f"{base_url}/rest/api/2/myself", headers=headers
                        )

                    response.raise_for_status()

                except requests.exceptions.RequestException:
                    # Try alternative URL format as a fallback
                    alt_url = "https://api.atlassian.com/ex/jira/cloud"
                    response = requests.get(
                        f"{alt_url}/rest/api/3/myself", headers=headers
                    )

                    if response.status_code == 200:
                        base_url = alt_url

                    response.raise_for_status()

            elif name == "get_my_issues":
                max_results = api_args.get("max_results", 50)
                status_filter = (
                    f" AND status = '{api_args['status']}'"
                    if "status" in api_args
                    else ""
                )

                # Get my account ID first
                myself_response = requests.get(
                    f"{base_url}/rest/api/3/myself", headers=headers
                )
                myself_response.raise_for_status()
                myself = myself_response.json()
                account_id = myself.get("accountId")

                jql = f"assignee = '{account_id}'{status_filter} ORDER BY updated DESC"
                params = {"jql": jql, "maxResults": max_results}

                response = requests.get(
                    f"{base_url}/rest/api/3/search", headers=headers, params=params
                )

            elif name == "get_my_recent_activity":
                max_results = api_args.get("max_results", 20)

                # Get my account ID first
                myself_response = requests.get(
                    f"{base_url}/rest/api/3/myself", headers=headers
                )
                myself_response.raise_for_status()
                myself = myself_response.json()
                account_id = myself.get("accountId")

                jql = f"assignee was '{account_id}' OR reporter = '{account_id}' OR comment ~ '{account_id}' ORDER BY updated DESC"
                params = {"jql": jql, "maxResults": max_results}

                response = requests.get(
                    f"{base_url}/rest/api/3/search", headers=headers, params=params
                )

            elif name == "get_my_permissions":
                project_key = api_args.get("project_key")
                specific_permissions = api_args.get("permissions", [])

                params = {"projectKey": project_key}

                # Add permissions parameter (required by the JIRA API)
                if specific_permissions:
                    params["permissions"] = ",".join(specific_permissions)
                else:
                    params["permissions"] = (
                        "BROWSE_PROJECTS,CREATE_ISSUES,EDIT_ISSUES,ASSIGN_ISSUES"
                    )

                response = requests.get(
                    f"{base_url}/rest/api/3/mypermissions",
                    headers=headers,
                    params=params,
                )

            # Project management tools
            elif name == "list_projects":
                max_results = api_args.get("max_results", 50)

                params = {"maxResults": max_results}

                response = requests.get(
                    f"{base_url}/rest/api/3/project/search",
                    headers=headers,
                    params=params,
                )

            elif name == "get_project":
                project_key = api_args.get("project_key")

                response = requests.get(
                    f"{base_url}/rest/api/3/project/{project_key}", headers=headers
                )

            elif name == "update_project":
                project_key = api_args.get("project_key")

                # Build the update payload by excluding the project_key
                update_data = {k: v for k, v in api_args.items() if k != "project_key"}

                response = requests.put(
                    f"{base_url}/rest/api/3/project/{project_key}",
                    headers=headers,
                    json=update_data,
                )

            elif name == "delete_project":
                project_key = api_args.get("project_key")
                response = requests.delete(
                    f"{base_url}/rest/api/3/project/{project_key}", headers=headers
                )

                # Special handling for successful delete which returns no content
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=f"Project {project_key} successfully deleted",
                        )
                    ]

            elif name == "get_issue_types_for_project":
                project_key = api_args.get("project_key")

                response = requests.get(
                    f"{base_url}/rest/api/3/project/{project_key}/statuses",
                    headers=headers,
                )

            # Issue management tools
            elif name == "list_issues":
                jql = api_args.get("jql", "")
                max_results = api_args.get("max_results", 50)

                params = {"jql": jql, "maxResults": max_results}

                response = requests.get(
                    f"{base_url}/rest/api/3/search", headers=headers, params=params
                )

            elif name == "create_issue":
                project_key = api_args.get("project_key")

                try:
                    # Verify project exists
                    project_check = requests.get(
                        f"{base_url}/rest/api/3/project/{project_key}", headers=headers
                    )

                    if project_check.status_code != 200:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error: Project '{project_key}' not found or not accessible.",
                            )
                        ]

                    # Get available issue types for this project
                    issue_types_response = requests.get(
                        f"{base_url}/rest/api/3/project/{project_key}/statuses",
                        headers=headers,
                    )
                    issue_types_response.raise_for_status()

                    issue_types = []
                    for status_data in issue_types_response.json():
                        issue_type_name = status_data.get("name")
                        if issue_type_name:
                            issue_types.append(issue_type_name)

                    # Check if the requested issue type is available
                    issue_type = api_args.get("issue_type", "Task")
                    if issue_types and issue_type not in issue_types:
                        issue_type = issue_types[0]

                    issue_data = {
                        "fields": {
                            "project": {"key": project_key},
                            "summary": api_args.get("summary"),
                            "issuetype": {"name": issue_type},
                        }
                    }

                    # Add optional fields if provided
                    if "description" in api_args and api_args["description"]:
                        issue_data["fields"]["description"] = format_issue_description(
                            api_args["description"]
                        )

                    if "assignee_account_id" in api_args:
                        issue_data["fields"]["assignee"] = {
                            "accountId": api_args["assignee_account_id"]
                        }

                    if "priority" in api_args:
                        issue_data["fields"]["priority"] = {
                            "name": api_args["priority"]
                        }

                    if "parent_key" in api_args:
                        issue_data["fields"]["parent"] = {"key": api_args["parent_key"]}

                    if "story_points" in api_args:
                        issue_data["fields"]["customfield_10016"] = api_args[
                            "story_points"
                        ]

                    if "labels" in api_args:
                        issue_data["fields"]["labels"] = api_args["labels"]

                    response = requests.post(
                        f"{base_url}/rest/api/3/issue",
                        headers=jira_client["write_headers"],
                        json=issue_data,
                    )

                    response.raise_for_status()

                except Exception as e:
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            error_details = e.response.json()
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Error creating issue: {json.dumps(error_details, indent=2)}",
                                )
                            ]
                        except Exception as e:
                            logger.error(f"Error creating issue: {str(e)}")
                            return [
                                TextContent(
                                    type="text", text=f"Error creating issue: {str(e)}"
                                )
                            ]
                    return [
                        TextContent(type="text", text=f"Error creating issue: {str(e)}")
                    ]

            elif name == "get_issue":
                issue_key = api_args.get("issue_key")
                expand = ",".join(api_args.get("expand", []))

                params = {}
                if expand:
                    params["expand"] = expand

                response = requests.get(
                    f"{base_url}/rest/api/3/issue/{issue_key}",
                    headers=headers,
                    params=params,
                )

            elif name == "update_issue":
                issue_key = api_args.get("issue_key")

                update_data = {"fields": {}}

                # Add fields to update
                if "summary" in api_args:
                    update_data["fields"]["summary"] = api_args["summary"]

                if "description" in api_args:
                    update_data["fields"]["description"] = format_issue_description(
                        api_args["description"]
                    )

                if "assignee_account_id" in api_args:
                    update_data["fields"]["assignee"] = {
                        "accountId": api_args["assignee_account_id"]
                    }

                if "priority" in api_args:
                    update_data["fields"]["priority"] = {"name": api_args["priority"]}

                if "story_points" in api_args:
                    update_data["fields"]["customfield_10016"] = api_args[
                        "story_points"
                    ]

                if "labels" in api_args:
                    update_data["fields"]["labels"] = api_args["labels"]

                response = requests.put(
                    f"{base_url}/rest/api/3/issue/{issue_key}",
                    headers=headers,
                    json=update_data,
                )

                # PUT for update returns 204 No Content when successful
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text", text=f"Issue {issue_key} successfully updated"
                        )
                    ]

            elif name == "delete_issue":
                issue_key = api_args.get("issue_key")

                response = requests.delete(
                    f"{base_url}/rest/api/3/issue/{issue_key}", headers=headers
                )

                # DELETE returns 204 No Content when successful
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text", text=f"Issue {issue_key} successfully deleted"
                        )
                    ]

            elif name == "transition_my_issue":
                issue_key = api_args.get("issue_key")

                # First get available transitions
                transitions_response = requests.get(
                    f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
                    headers=headers,
                )
                transitions_response.raise_for_status()

                transitions = transitions_response.json().get("transitions", [])
                transition_target = api_args.get("transition_to", "").lower()

                # Find matching transition ID
                transition_id = None
                for transition in transitions:
                    if transition["to"]["name"].lower() == transition_target:
                        transition_id = transition["id"]
                        break

                if not transition_id:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Could not find transition to '{transition_target}'. Available transitions: {', '.join([t['to']['name'] for t in transitions])}",
                        )
                    ]

                # Build transition data
                transition_data = {"transition": {"id": transition_id}}

                # Add comment if provided
                if "comment" in api_args and api_args["comment"]:
                    transition_data["update"] = {
                        "comment": [{"add": format_comment_body(api_args["comment"])}]
                    }

                response = requests.post(
                    f"{base_url}/rest/api/3/issue/{issue_key}/transitions",
                    headers=headers,
                    json=transition_data,
                )

                # Transition returns 204 No Content when successful
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=f"Issue {issue_key} successfully transitioned to {transition_target}",
                        )
                    ]

            elif name == "comment_on_issue":
                issue_key = api_args.get("issue_key")
                comment_data = format_comment_body(api_args.get("body", ""))

                response = requests.post(
                    f"{base_url}/rest/api/3/issue/{issue_key}/comment",
                    headers=headers,
                    json=comment_data,
                )

            elif name == "create_project":
                try:
                    # Verify project_type_key is provided
                    if "project_type_key" not in api_args:
                        return [
                            TextContent(
                                type="text",
                                text="Error: You must specify 'project_type_key' for project creation.",
                            )
                        ]

                    # If lead_account_id is not provided, get the current user's account ID
                    if "lead_account_id" not in api_args:
                        try:
                            myself_response = requests.get(
                                f"{base_url}/rest/api/3/myself", headers=headers
                            )
                            myself_response.raise_for_status()
                            api_args["lead_account_id"] = myself_response.json().get(
                                "accountId"
                            )
                        except requests.exceptions.RequestException:
                            return [
                                TextContent(
                                    type="text",
                                    text="Error accessing Jira site. Please verify your permissions.",
                                )
                            ]

                    # Format the payload using the util helper
                    payload = format_project_payload(api_args)

                    # Send the POST request to create the project
                    response = requests.post(
                        f"{base_url}/rest/api/3/project",
                        headers=jira_client["write_headers"],
                        json=payload,
                        timeout=30,
                    )

                    if response.status_code in [200, 201]:
                        return [
                            TextContent(
                                type="text", text=json.dumps(response.json(), indent=2)
                            )
                        ]
                    else:
                        response.raise_for_status()
                except Exception as e:
                    error_message = f"Error creating project: {str(e)}"
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            error_details = e.response.json()
                            error_message += (
                                f"\nDetails: {json.dumps(error_details, indent=2)}"
                            )
                        except Exception as e:
                            logger.error(f"Error creating project: {str(e)}")
                            error_message += f"\nResponse text: {e.response.text}"
                    return [TextContent(type="text", text=error_message)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            # Check if the response was successful
            response.raise_for_status()

            # Some endpoints return no content on success
            if response.status_code == 204:
                return [
                    TextContent(type="text", text="Operation completed successfully")
                ]

            result = response.json()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except requests.exceptions.RequestException as e:
            error_message = f"JIRA API error: {str(e)}"
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message += f"\nDetails: {json.dumps(error_details, indent=2)}"
                except ValueError:
                    error_message += f"\nResponse text: {e.response.text}"

            return [TextContent(type="text", text=error_message)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the JIRA MCP server.

    Args:
        server_instance (Server): The server instance to describe.

    Returns:
        InitializationOptions: MCP-compatible initialization configuration.
    """
    return InitializationOptions(
        server_name="jira-server",
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
