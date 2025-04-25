import os
import sys
from typing import Optional, Iterable
import json

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx

from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.linear.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
LINEAR_API_URL = "https://api.linear.app/graphql"
SCOPES = [
    "read",
    "write",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def execute_linear_query(query, variables=None, access_token=None):
    """Execute a GraphQL query against the Linear API"""
    if not access_token:
        raise ValueError("Linear access token is required")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {"query": query, "variables": variables or {}}

    async with httpx.AsyncClient() as client:
        response = await client.post(LINEAR_API_URL, json=payload, headers=headers)
        response_data = response.json()
        response.raise_for_status()
        return response_data


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("linear-server")

    server.user_id = user_id

    async def get_linear_client():
        """Get Linear access token for the current user"""
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return access_token

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List issues from Linear"""
        logger.info(
            f"Listing issue resources for user: {server.user_id} with cursor: {cursor}"
        )

        access_token = await get_linear_client()

        # Query to get teams first
        teams_query = """
        query($after: String) {
            teams(first: 100, after: $after) {
                nodes {
                    id
                    name
                    key
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
        """

        try:
            teams_result = await execute_linear_query(
                teams_query, access_token=access_token
            )
            teams = teams_result.get("data", {}).get("teams", {}).get("nodes", [])

            resources = []

            # Add teams as resources
            for team in teams:
                resources.append(
                    Resource(
                        uri=f"linear://team/{team['id']}",
                        mimeType="application/json",
                        name=f"Team: {team['name']} ({team['key']})",
                    )
                )

                # Query to get issues for each team
                issues_query = """
                query($teamId: ID!, $after: String) {
                    issues(
                        filter: { team: { id: { eq: $teamId } } }
                        first: 10
                        after: $after
                    ) {
                        nodes {
                            id
                            title
                            identifier
                            state {
                                name
                            }
                            project {
                                name
                            }
                            url
                        }
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                    }
                }
                """

                variables = {"teamId": team["id"]}
                if cursor:
                    variables["after"] = cursor

                issues_result = await execute_linear_query(
                    issues_query, variables, access_token=access_token
                )
                issues = (
                    issues_result.get("data", {}).get("issues", {}).get("nodes", [])
                )

                # Add issues as resources
                for issue in issues:
                    resources.append(
                        Resource(
                            uri=f"linear://issue/{issue['id']}",
                            mimeType="application/json",
                            name=f"Issue: {issue['title']} ({issue['state']['name']})",
                        )
                    )

            return resources

        except Exception as e:
            import traceback

            logger.error(f"Error fetching Linear resources: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read an issue or team from Linear by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await get_linear_client()

        uri_str = str(uri)

        if uri_str.startswith("linear://team/"):
            # Handle team resource
            team_id = uri_str.replace("linear://team/", "")

            team_query = """
            query($teamId: String!) {
                team(id: $teamId) {
                    id
                    name
                    key
                    description
                    states {
                        nodes {
                            id
                            name
                            color
                            type
                        }
                    }
                    labels {
                        nodes {
                            id
                            name
                            color
                        }
                    }
                }
            }
            """

            result = await execute_linear_query(
                team_query, {"teamId": team_id}, access_token=access_token
            )
            team_data = result.get("data", {}).get("team", {})

            if not team_data:
                raise ValueError(f"Team not found: {team_id}")

            formatted_content = json.dumps(team_data, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        elif uri_str.startswith("linear://issue/"):
            # Handle issue resource
            issue_id = uri_str.replace("linear://issue/", "")

            issue_query = """
            query($issueId: String!) {
                issue(id: $issueId) {
                    id
                    title
                    identifier
                    description
                    state {
                        id
                        name
                        color
                        type
                    }
                    team {
                        id
                        name
                        key
                    }
                    assignee {
                        id
                        name
                        email
                    }
                    labels {
                        nodes {
                            id
                            name
                            color
                        }
                    }
                    priority
                    project {
                        name
                    }
                    createdAt
                    updatedAt
                    comments {
                        nodes {
                            id
                            body
                            user {
                                name
                            }
                            createdAt
                        }
                    }
                }
            }
            """

            result = await execute_linear_query(
                issue_query, {"issueId": issue_id}, access_token=access_token
            )
            issue_data = result.get("data", {}).get("issue", {})

            if not issue_data:
                raise ValueError(f"Issue not found: {issue_id}")

            formatted_content = json.dumps(issue_data, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        raise ValueError(f"Unsupported resource URI: {uri_str}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Linear"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_issues",
                description="Search for issues in Linear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for issues",
                        }
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_issue",
                description="Create a new issue in Linear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {"type": "string", "description": "ID of the team"},
                        "title": {
                            "type": "string",
                            "description": "Title of the issue",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the issue",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority (1-4, where 1 is highest)",
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "ID of the user to assign (optional)",
                        },
                        "label_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Label IDs to apply (optional)",
                        },
                    },
                    "required": ["team_id", "title"],
                },
            ),
            Tool(
                name="update_issue",
                description="Update an existing issue in Linear",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "issue_id": {
                            "type": "string",
                            "description": "ID of the issue to update",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title (optional)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description (optional)",
                        },
                        "state_id": {
                            "type": "string",
                            "description": "New state ID (optional)",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority (1-4, where 1 is highest) (optional)",
                        },
                        "assignee_id": {
                            "type": "string",
                            "description": "New assignee ID (optional)",
                        },
                        "label_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New label IDs (optional)",
                        },
                    },
                    "required": ["issue_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Linear"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_linear_client()

        if name == "search_issues":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            issues_query = """
            query {
                issues(filter: {
                    or: [
                        { title: { containsIgnoreCase: "%s" } },
                        { description: { containsIgnoreCase: "%s" } }
                    ]
                }, first: 10) {
                    nodes {
                        id
                        title
                        identifier
                        url
                        state {
                            name
                            color
                        }
                        team {
                            key
                        }
                        priority
                        project {
                            name
                        }
                        assignee {
                            name
                        }
                    }
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                }
            }
            """ % (
                arguments["query"],
                arguments["query"],
            )

            try:
                result = await execute_linear_query(
                    issues_query, access_token=access_token
                )
                issues = result.get("data", {}).get("issues", {}).get("nodes", [])

                if not issues:
                    return [
                        TextContent(
                            type="text", text="No issues found matching your query."
                        )
                    ]

                issue_list = []
                for issue in issues:
                    priority_map = {
                        1: "Urgent",
                        2: "High",
                        3: "Medium",
                        4: "Low",
                        None: "None",
                    }
                    priority_text = priority_map.get(issue.get("priority"))
                    assignee = issue.get("assignee", {}) or {}
                    assignee = assignee.get("name", "Unassigned")

                    issue_list.append(
                        f"{issue['team']['key']}-{issue['identifier']}: {issue['title']}\n"
                        f"  State: {issue['state']['name']}\n"
                        f"  Priority: {priority_text}\n"
                        f"  Assignee: {assignee}\n"
                        f"  ID: {issue['id']}"
                    )

                formatted_result = "\n\n".join(issue_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(issues)} issues:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error searching issues: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error searching issues: {str(e)}")
                ]

        elif name == "create_issue":
            required_fields = ["team_id", "title"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            create_mutation = """
            mutation IssueCreate(
                $teamId: String!,
                $title: String!,
                $description: String,
                $priority: Int,
                $assigneeId: String,
                $labelIds: [String!],
                $stateId: String,
                $projectId: String
            ) {
                issueCreate(
                    input: {
                        teamId: $teamId,
                        title: $title,
                        description: $description,
                        priority: $priority,
                        assigneeId: $assigneeId,
                        labelIds: $labelIds,
                        stateId: $stateId,
                        projectId: $projectId
                    }
                ) {
                    issue {
                        id
                        title
                        identifier
                        url
                    }
                    success
                }
            }
            """

            variables = {
                "teamId": arguments["team_id"],
                "title": arguments["title"],
                "description": arguments.get("description"),
                "priority": arguments.get("priority"),
                "assigneeId": arguments.get("assignee_id"),
                "labelIds": arguments.get("label_ids"),
            }

            # Remove None values
            variables = {k: v for k, v in variables.items() if v is not None}

            try:
                result = await execute_linear_query(
                    create_mutation, variables, access_token=access_token
                )
                create_result = result.get("data", {}).get("issueCreate", {})

                if create_result.get("success"):
                    issue = create_result.get("issue", {})
                    return [
                        TextContent(
                            type="text",
                            text=f"Issue created successfully!\n\n"
                            f"ID: {issue.get('id')}\n"
                            f"Title: {issue.get('title')}\n"
                            f"Identifier: {issue.get('identifier')}\n"
                            f"URL: {issue.get('url')}",
                        )
                    ]
                else:
                    errors = result.get("errors", [])
                    error_messages = "\n".join(
                        [e.get("message", "Unknown error") for e in errors]
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create issue: {error_messages}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error creating issue: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating issue: {str(e)}")
                ]

        elif name == "update_issue":
            if not arguments or "issue_id" not in arguments:
                raise ValueError("Missing required parameter: issue_id")

            # Check that at least one updateable field is provided
            updateable_fields = [
                "title",
                "description",
                "state_id",
                "priority",
                "assignee_id",
                "label_ids",
            ]
            if not any(field in arguments for field in updateable_fields):
                raise ValueError("At least one field to update must be provided")

            update_mutation = """
            mutation IssueUpdate(
                $issueId: String!,
                $title: String,
                $description: String,
                $stateId: String,
                $priority: Int,
                $assigneeId: String,
                $labelIds: [String!],
                $projectId: String
            ) {
                issueUpdate(
                    id: $issueId,
                    input: {
                        title: $title,
                        description: $description,
                        stateId: $stateId,
                        priority: $priority,
                        assigneeId: $assigneeId,
                        labelIds: $labelIds,
                        projectId: $projectId
                    }
                ) {
                    issue {
                        id
                        title
                        identifier
                        url
                        state {
                            name
                        }
                    }
                    success
                }
            }
            """

            variables = {
                "issueId": arguments["issue_id"],
                "title": arguments.get("title"),
                "description": arguments.get("description"),
                "stateId": arguments.get("state_id"),
                "priority": arguments.get("priority"),
                "assigneeId": arguments.get("assignee_id"),
                "labelIds": arguments.get("label_ids"),
            }

            # Remove None values
            variables = {k: v for k, v in variables.items() if v is not None}

            try:
                result = await execute_linear_query(
                    update_mutation, variables, access_token=access_token
                )
                update_result = result.get("data", {}).get("issueUpdate", {})

                if update_result.get("success"):
                    issue = update_result.get("issue", {})
                    return [
                        TextContent(
                            type="text",
                            text=f"Issue updated successfully!\n\n"
                            f"ID: {issue.get('id')}\n"
                            f"Title: {issue.get('title')}\n"
                            f"Identifier: {issue.get('identifier')}\n"
                            f"State: {issue.get('state', {}).get('name')}\n"
                            f"URL: {issue.get('url')}",
                        )
                    ]
                else:
                    errors = result.get("errors", [])
                    error_messages = "\n".join(
                        [e.get("message", "Unknown error") for e in errors]
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to update issue: {error_messages}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error updating issue: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error updating issue: {str(e)}")
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="linear-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
