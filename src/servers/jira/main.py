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
from typing import Optional, Iterable

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
    AnyUrl,
    Resource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents

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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created project with its ID and key",
                    "examples": [
                        '{"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/project/10001", "id": 10001, "key": "TESTB700"}'
                    ],
                },
                requiredScopes=["manage:jira-project", "write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about a JIRA project including key, name, lead, components, issue types, etc.",
                    "examples": [
                        '{"expand": "description,lead,issueTypes,url,projectKeys,permissions,insight", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/project/10001", "id": "10001", "key": "TESTB700", "description": "Project description", "lead": {"displayName": "User Name"}, "components": [], "issueTypes": [{"name": "Task"}, {"name": "Sub-task"}], "assigneeType": "PROJECT_LEAD", "name": "Project Name", "roles": {}, "projectTypeKey": "software"}'
                    ],
                },
                requiredScopes=["read:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated project details including all fields that were changed",
                    "examples": [
                        '{"expand": "description,lead,issueTypes,url,projectKeys,permissions,insight", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/project/10001", "id": "10001", "key": "TESTB700", "description": "This is an updated test project description.", "lead": {"displayName": "User Name"}, "name": "Updated Project Name", "projectTypeKey": "software"}'
                    ],
                },
                requiredScopes=["manage:jira-project", "write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the project deletion operation",
                    "examples": [
                        '{"success": true, "message": "Project TESTB700 successfully deleted"}'
                    ],
                },
                requiredScopes=["manage:jira-project"],
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
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of JIRA projects with basic metadata for each project",
                    "examples": [
                        '{"expand": "description,lead,issueTypes,url,projectKeys,permissions,insight", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/project/10000", "id": "10000", "key": "KAN", "name": "Project Name", "avatarUrls": {}, "projectTypeKey": "software", "simplified": true, "style": "next-gen", "isPrivate": false, "properties": {}}',
                        '{"expand": "description,lead,issueTypes,url,projectKeys,permissions,insight", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/project/10001", "id": "10001", "key": "TESTB700", "name": "Test Project", "avatarUrls": {}, "projectTypeKey": "software", "simplified": false, "style": "classic", "isPrivate": false, "properties": {}}',
                    ],
                },
                requiredScopes=["read:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of issue types for a project with their available statuses",
                    "examples": [
                        '[{"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issuetype/10004", "id": "10004", "name": "Task", "subtask": false, "statuses": [{"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/status/10004", "description": "", "name": "Done", "id": "10004", "statusCategory": {"id": 3, "key": "done", "colorName": "green", "name": "Done"}}, {"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/status/3", "description": "This issue is being actively worked on", "name": "In Progress", "id": "3", "statusCategory": {"id": 4, "key": "indeterminate", "colorName": "yellow", "name": "In Progress"}}, {"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/status/10003", "description": "", "name": "To Do", "id": "10003", "statusCategory": {"id": 2, "key": "new", "colorName": "blue-gray", "name": "To Do"}}]}]'
                    ],
                },
                requiredScopes=["read:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created issue with its ID and key",
                    "examples": [
                        '{"id": "10000", "key": "TESTB700-1", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000"}'
                    ],
                },
                requiredScopes=["write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about a JIRA issue including summary, description, assignee, status, etc.",
                    "examples": [
                        '{"expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations", "id": "10000", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000", "key": "TESTB700-1", "fields": {"summary": "Issue Summary", "status": {"name": "In Progress"}, "assignee": {"displayName": "User Name"}, "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Issue description"}]}]}, "issuetype": {"name": "Task"}, "priority": {"name": "Medium"}, "creator": {"displayName": "Creator Name"}, "reporter": {"displayName": "Reporter Name"}}}'
                    ],
                },
                requiredScopes=["read:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status of the update operation",
                    "examples": [
                        '{"success": true, "message": "Issue TESTB700-1 successfully updated"}'
                    ],
                },
                requiredScopes=["write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status of the delete operation",
                    "examples": [
                        '{"success": true, "message": "Issue TESTB700-1 successfully deleted"}'
                    ],
                },
                requiredScopes=["write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status of the transition operation",
                    "examples": [
                        '{"success": true, "message": "Issue TESTB700-1 successfully transitioned to in progress"}'
                    ],
                },
                requiredScopes=["write:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of issues matching the JQL query, one issue per TextContent",
                    "examples": [
                        '{"expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations", "id": "10000", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000", "key": "TESTB700-1", "fields": {"summary": "Issue Summary", "status": {"name": "In Progress"}, "assignee": {"displayName": "User Name"}, "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Issue description"}]}]}, "issuetype": {"name": "Task"}, "priority": {"name": "Medium"}, "creator": {"displayName": "Creator Name"}, "reporter": {"displayName": "Reporter Name"}}}'
                    ],
                },
                requiredScopes=["read:jira-work"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created comment",
                    "examples": [
                        '{"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000/comment/10000", "id": "10000", "author": {"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/user?accountId=<account-id>", "accountId": "<account-id>", "displayName": "User Name", "active": true}, "body": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "This is a test comment."}]}]}, "created": "2025-05-16T16:58:43.046-0700", "updated": "2025-05-16T16:58:43.046-0700", "jsdPublic": true}'
                    ],
                },
                requiredScopes=["write:jira-work"],
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
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about your account including accountId, email, display name, and more",
                    "examples": [
                        '{"self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/user?accountId=<account-id>", "accountId": "<account-id>", "accountType": "atlassian", "emailAddress": "user@example.com", "avatarUrls": {}, "displayName": "User Name", "active": true, "timeZone": "America/Los_Angeles", "locale": "en_US", "groups": {"size": 4, "items": []}, "applicationRoles": {"size": 1, "items": []}, "expand": "groups,applicationRoles"}'
                    ],
                },
                requiredScopes=["read:jira-user"],
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
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about issues assigned to you, one issue per TextContent",
                    "examples": [
                        '{"expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations", "id": "10000", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000", "key": "TESTB700-1", "fields": {"summary": "Issue Summary", "status": {"name": "In Progress"}, "assignee": {"displayName": "User Name"}, "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Issue description"}]}]}, "issuetype": {"name": "Task"}, "priority": {"name": "Medium"}, "creator": {"displayName": "Creator Name"}, "reporter": {"displayName": "Reporter Name"}}}'
                    ],
                },
                requiredScopes=["read:jira-work", "read:jira-user"],
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
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Issues you recently created, commented on, or were assigned to",
                    "examples": [
                        '{"expand": "renderedFields,names,schema,operations,editmeta,changelog,versionedRepresentations", "id": "10000", "self": "https://api.atlassian.com/ex/jira/<cloud-id>/rest/api/3/issue/10000", "key": "TESTB700-1", "fields": {"summary": "Updated Test Issue", "status": {"name": "In Progress"}, "assignee": {"displayName": "User Name"}, "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "This is an updated test issue description."}]}]}, "issuetype": {"name": "Task"}, "priority": {"name": "Medium"}, "creator": {"displayName": "Creator Name"}, "reporter": {"displayName": "Reporter Name"}, "created": "2025-05-16T16:58:14.267-0700", "updated": "2025-05-16T16:59:51.618-0700"}}'
                    ],
                },
                requiredScopes=["read:jira-work", "read:jira-user"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of your permissions in the specified project",
                    "examples": [
                        '{"permissions": {"BROWSE_PROJECTS": {"id": "10", "key": "BROWSE_PROJECTS", "name": "Browse Projects", "type": "PROJECT", "description": "Ability to browse projects and the issues within them.", "havePermission": true}, "EDIT_ISSUES": {"id": "12", "key": "EDIT_ISSUES", "name": "Edit Issues", "type": "PROJECT", "description": "Ability to edit issues.", "havePermission": true}, "CREATE_ISSUES": {"id": "11", "key": "CREATE_ISSUES", "name": "Create Issues", "type": "PROJECT", "description": "Ability to create issues.", "havePermission": true}, "ASSIGN_ISSUES": {"id": "13", "key": "ASSIGN_ISSUES", "name": "Assign Issues", "type": "PROJECT", "description": "Ability to assign issues to other people.", "havePermission": true}}}'
                    ],
                },
                requiredScopes=["read:jira-user"],
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
            error_response = {
                "error": f"Multiple Jira sites available. You must specify either 'cloud_id' or 'site_name' for this operation.",
                "available_sites": available_site_names,
            }
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

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
                    success_response = {
                        "success": True,
                        "message": f"Project {project_key} successfully deleted",
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(success_response, indent=2)
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
                        error_response = {
                            "error": f"Project '{project_key}' not found or not accessible"
                        }
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
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
                                    text=json.dumps(error_details, indent=2),
                                )
                            ]
                        except Exception:
                            error_response = {"error": str(e)}
                            return [
                                TextContent(
                                    type="text",
                                    text=json.dumps(error_response, indent=2),
                                )
                            ]
                    error_response = {"error": str(e)}
                    return [
                        TextContent(
                            type="text", text=json.dumps(error_response, indent=2)
                        )
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
                    success_response = {
                        "success": True,
                        "message": f"Issue {issue_key} successfully updated",
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(success_response, indent=2)
                        )
                    ]

            elif name == "delete_issue":
                issue_key = api_args.get("issue_key")

                response = requests.delete(
                    f"{base_url}/rest/api/3/issue/{issue_key}", headers=headers
                )

                # DELETE returns 204 No Content when successful
                if response.status_code == 204:
                    success_response = {
                        "success": True,
                        "message": f"Issue {issue_key} successfully deleted",
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(success_response, indent=2)
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
                    available_transitions = [t["to"]["name"] for t in transitions]
                    error_response = {
                        "error": f"Could not find transition to '{transition_target}'",
                        "available_transitions": available_transitions,
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(error_response, indent=2)
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
                    success_response = {
                        "success": True,
                        "message": f"Issue {issue_key} successfully transitioned to {transition_target}",
                    }
                    return [
                        TextContent(
                            type="text", text=json.dumps(success_response, indent=2)
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
                        error_response = {
                            "error": "You must specify 'project_type_key' for project creation"
                        }
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
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
                            error_response = {
                                "error": "Error accessing Jira site. Please verify your permissions."
                            }
                            return [
                                TextContent(
                                    type="text",
                                    text=json.dumps(error_response, indent=2),
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

                    response.raise_for_status()

                except Exception as e:
                    error_message = {"error": f"Error creating project: {str(e)}"}

                    if hasattr(e, "response") and e.response is not None:
                        try:
                            error_details = e.response.json()
                            error_message["details"] = error_details
                        except Exception:
                            error_message["response_text"] = e.response.text

                    return [
                        TextContent(
                            type="text", text=json.dumps(error_message, indent=2)
                        )
                    ]

            else:
                error_response = {"error": f"Unknown tool: {name}"}
                return [
                    TextContent(type="text", text=json.dumps(error_response, indent=2))
                ]

            # Check if the response was successful
            response.raise_for_status()

            # Some endpoints return no content on success
            if response.status_code == 204:
                success_response = {
                    "success": True,
                    "message": "Operation completed successfully",
                }
                return [
                    TextContent(
                        type="text", text=json.dumps(success_response, indent=2)
                    )
                ]

            # Process the response based on its content
            result = response.json()

            # Handle array responses
            if (
                isinstance(result, dict)
                and "issues" in result
                and isinstance(result["issues"], list)
            ):
                return [
                    TextContent(type="text", text=json.dumps(issue, indent=2))
                    for issue in result["issues"]
                ]
            elif (
                isinstance(result, dict)
                and "values" in result
                and isinstance(result["values"], list)
            ):
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result["values"]
                ]
            # Return the result as a single JSON object
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except requests.exceptions.RequestException as e:
            error_message = {"error": f"JIRA API error: {str(e)}"}

            if hasattr(e, "response") and e.response is not None:
                try:
                    error_details = e.response.json()
                    error_message["details"] = error_details
                except ValueError:
                    error_message["response_text"] = e.response.text

            return [TextContent(type="text", text=json.dumps(error_message, indent=2))]
        except Exception as e:
            error_response = {"error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List JIRA organization resources (sites)"""
        logger.info(
            f"Listing organization resources for user: {server.user_id} with cursor: {cursor}"
        )

        try:
            # Get full credentials to access accessible sites
            jira_client = await create_jira_client(
                server.user_id, api_key=server.api_key, return_full_credentials=True
            )

            resources = []

            # List accessible Atlassian sites (organizations)
            available_sites = jira_client.get("available_sites", [])
            cloud_id = jira_client.get("cloud_id")

            # Add all sites as resources
            for site in available_sites:
                site_id = site.get("id")
                site_name = site.get("name")
                site_url = site.get("url", "")
                is_current = site_id == cloud_id

                resource = Resource(
                    uri=f"jira://site/{site_id}",
                    mimeType="application/json",
                    name=f"{site_name}{' (current)' if is_current else ''}",
                    description=f"Jira site: {site_name} - {site_url}",
                )
                resources.append(resource)

            return resources

        except Exception as e:
            logger.error(f"Error listing JIRA resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a JIRA organization resource"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        jira_client = await create_jira_client(server.user_id, api_key=server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("jira://"):
            raise ValueError(f"Invalid JIRA URI: {uri_str}")

        # Parse the URI to get resource type and ID
        parts = uri_str.replace("jira://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid JIRA URI format: {uri_str}")

        resource_type, resource_id = parts

        try:
            if resource_type == "site":
                # For site resources, return information about the site
                available_sites = jira_client.get("available_sites", [])
                requested_site = None

                for site in available_sites:
                    if site.get("id") == resource_id:
                        requested_site = site
                        break

                if not requested_site:
                    return [
                        ReadResourceContents(
                            content=f"Error: Site with ID {resource_id} not found",
                            mime_type="text/plain",
                        )
                    ]

                return [
                    ReadResourceContents(
                        content=json.dumps(requested_site, indent=2),
                        mime_type="application/json",
                    )
                ]
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading JIRA resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

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
