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

from src.utils.clickup.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
CLICKUP_API_URL = "https://api.clickup.com/api/v2"
SCOPES = []  # ClickUp doesn't use scopes in OAuth flow

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def make_clickup_request(
    endpoint, method="GET", data=None, params=None, access_token=None
):
    """Make a request to the ClickUp API"""
    if not access_token:
        raise ValueError("ClickUp access token is required")

    headers = {
        "Authorization": access_token,
        "Content-Type": "application/json",
    }

    url = f"{CLICKUP_API_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check if the response status is successful
            response.raise_for_status()

            response_data = response.json()
            return response_data

    except httpx.HTTPError as e:
        logger.error(f"HTTP error: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_body = e.response.json()
                error_message = error_body.get("err", str(e))
                raise ValueError(f"ClickUp API error: {error_message}")
            except Exception:
                pass
        raise ValueError(f"Failed to communicate with ClickUp API: {str(e)}")
    except Exception as e:
        logger.error(f"General error: {str(e)}")
        raise ValueError(f"Error in ClickUp API request: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("clickup-server")

    server.user_id = user_id

    async def get_clickup_client():
        """Get ClickUp access token for the current user"""
        return await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List workspaces and spaces from ClickUp"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        access_token = await get_clickup_client()
        resources = []

        try:
            # Get workspaces
            workspaces_result = await make_clickup_request(
                "team", access_token=access_token
            )
            workspaces = workspaces_result.get("teams", [])

            for workspace in workspaces:
                # Add workspace as resource
                workspace_id = workspace["id"]
                workspace_name = workspace["name"]

                resources.append(
                    Resource(
                        uri=f"clickup://workspace/{workspace_id}",
                        mimeType="application/json",
                        name=f"Workspace: {workspace_name}",
                    )
                )

                # Get spaces for this workspace
                spaces_result = await make_clickup_request(
                    f"team/{workspace_id}/space", access_token=access_token
                )
                spaces = spaces_result.get("spaces", [])

                for space in spaces:
                    space_id = space["id"]
                    space_name = space["name"]

                    resources.append(
                        Resource(
                            uri=f"clickup://space/{space_id}",
                            mimeType="application/json",
                            name=f"Space: {space_name} (in {workspace_name})",
                        )
                    )

                    # Get lists for this space
                    lists_result = await make_clickup_request(
                        f"space/{space_id}/list", access_token=access_token
                    )
                    lists = lists_result.get("lists", [])

                    for list_item in lists:
                        list_id = list_item["id"]
                        list_name = list_item["name"]

                        resources.append(
                            Resource(
                                uri=f"clickup://list/{list_id}",
                                mimeType="application/json",
                                name=f"List: {list_name} (in {space_name})",
                            )
                        )

            return resources

        except Exception as e:
            logger.error(f"Error fetching ClickUp resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from ClickUp by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await get_clickup_client()
        uri_str = str(uri)

        try:
            if uri_str.startswith("clickup://workspace/"):
                # Handle workspace resource
                workspace_id = uri_str.replace("clickup://workspace/", "")

                workspace_result = await make_clickup_request(
                    f"team/{workspace_id}", access_token=access_token
                )

                formatted_content = json.dumps(workspace_result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("clickup://space/"):
                # Handle space resource
                space_id = uri_str.replace("clickup://space/", "")

                space_result = await make_clickup_request(
                    f"space/{space_id}", access_token=access_token
                )

                formatted_content = json.dumps(space_result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("clickup://list/"):
                # Handle list resource
                list_id = uri_str.replace("clickup://list/", "")

                list_result = await make_clickup_request(
                    f"list/{list_id}", access_token=access_token
                )

                # Get tasks in this list
                tasks_result = await make_clickup_request(
                    f"list/{list_id}/task", access_token=access_token
                )

                # Combine list details with its tasks
                combined_result = {
                    "list": list_result,
                    "tasks": tasks_result.get("tasks", []),
                }

                formatted_content = json.dumps(combined_result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading resource: {str(e)}")
            raise ValueError(f"Error reading resource: {str(e)}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for ClickUp"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="get_authenticated_user",
                description="Get information about the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_workspaces",
                description="Get all workspaces/teams the user has access to",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="get_spaces",
                description="Get all spaces in a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "ID of the workspace",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to include archived spaces",
                        },
                    },
                    "required": ["workspace_id"],
                },
            ),
            Tool(
                name="get_folders",
                description="Get all folders in a space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_id": {
                            "type": "string",
                            "description": "ID of the space",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to include archived folders",
                        },
                    },
                    "required": ["space_id"],
                },
            ),
            Tool(
                name="get_lists",
                description="Get all lists in a folder or space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_id": {
                            "type": "string",
                            "description": "ID of the folder (required if not providing space_id)",
                        },
                        "space_id": {
                            "type": "string",
                            "description": "ID of the space (required if not providing folder_id)",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to include archived lists",
                        },
                    },
                },
            ),
            Tool(
                name="get_tasks",
                description="Get tasks from a list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "ID of the list",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to include archived tasks",
                        },
                        "include_closed": {
                            "type": "boolean",
                            "description": "Whether to include closed tasks",
                        },
                        "subtasks": {
                            "type": "boolean",
                            "description": "Whether to include subtasks",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for pagination",
                        },
                    },
                    "required": ["list_id"],
                },
            ),
            Tool(
                name="get_task_by_id",
                description="Get a specific task by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task",
                        },
                        "custom_task_ids": {
                            "type": "boolean",
                            "description": "Whether the provided ID is a custom task ID",
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Team ID (required if using custom_task_ids)",
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            Tool(
                name="create_task",
                description="Create a new task in a list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "ID of the list to create the task in",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the task",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the task",
                        },
                        "status": {
                            "type": "string",
                            "description": "Status of the task",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority (1-4, where 1 is urgent, 2 is high, 3 is normal, 4 is low)",
                        },
                        "due_date": {
                            "type": "integer",
                            "description": "Due date (unix timestamp in milliseconds)",
                        },
                        "due_date_time": {
                            "type": "boolean",
                            "description": "Whether the due date includes time",
                        },
                        "assignees": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of assignee user IDs",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of tags",
                        },
                    },
                    "required": ["list_id", "name"],
                },
            ),
            Tool(
                name="update_task",
                description="Update an existing task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name of the task",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description of the task",
                        },
                        "status": {
                            "type": "string",
                            "description": "New status of the task",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "New priority (1-4, where 1 is urgent, 2 is high, 3 is normal, 4 is low)",
                        },
                        "due_date": {
                            "type": "integer",
                            "description": "New due date (unix timestamp in milliseconds)",
                        },
                        "due_date_time": {
                            "type": "boolean",
                            "description": "Whether the due date includes time",
                        },
                        "custom_task_ids": {
                            "type": "boolean",
                            "description": "Whether the provided ID is a custom task ID",
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Team ID (required if using custom_task_ids)",
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            Tool(
                name="add_comment",
                description="Add a comment to a task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to comment on",
                        },
                        "comment_text": {
                            "type": "string",
                            "description": "Text content of the comment",
                        },
                        "assignee": {
                            "type": "integer",
                            "description": "User ID to assign the comment to",
                        },
                        "custom_task_ids": {
                            "type": "boolean",
                            "description": "Whether the provided ID is a custom task ID",
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Team ID (required if using custom_task_ids)",
                        },
                    },
                    "required": ["task_id", "comment_text"],
                },
            ),
            Tool(
                name="create_list",
                description="Create a new list in a folder or space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_id": {
                            "type": "string",
                            "description": "ID of the folder (required if not providing space_id)",
                        },
                        "space_id": {
                            "type": "string",
                            "description": "ID of the space (required if not providing folder_id)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the list",
                        },
                        "content": {
                            "type": "string",
                            "description": "Description of the list",
                        },
                        "due_date": {
                            "type": "integer",
                            "description": "Due date (unix timestamp in milliseconds)",
                        },
                        "due_date_time": {
                            "type": "boolean",
                            "description": "Whether the due date includes time",
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Priority (1-4, where 1 is urgent, 2 is high, 3 is normal, 4 is low)",
                        },
                        "assignee": {
                            "type": "integer",
                            "description": "User ID to assign the list to",
                        },
                        "status": {
                            "type": "string",
                            "description": "Status of the list",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="create_folder",
                description="Create a new folder in a space",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "space_id": {
                            "type": "string",
                            "description": "ID of the space",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the folder",
                        },
                    },
                    "required": ["space_id", "name"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for ClickUp"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_clickup_client()

        try:
            if name == "get_authenticated_user":
                # Get authorized user
                user_result = await make_clickup_request(
                    "user", access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(user_result, indent=2))
                ]

            elif name == "get_workspaces":
                # Get workspaces/teams
                workspaces_result = await make_clickup_request(
                    "team", access_token=access_token
                )

                return [
                    TextContent(
                        type="text", text=json.dumps(workspaces_result, indent=2)
                    )
                ]

            elif name == "get_spaces":
                if not arguments or "workspace_id" not in arguments:
                    raise ValueError("Missing required parameter: workspace_id")

                workspace_id = arguments["workspace_id"]
                params = {}

                if "archived" in arguments:
                    params["archived"] = str(arguments["archived"]).lower()

                spaces_result = await make_clickup_request(
                    f"team/{workspace_id}/space",
                    params=params,
                    access_token=access_token,
                )

                return [
                    TextContent(type="text", text=json.dumps(spaces_result, indent=2))
                ]

            elif name == "get_folders":
                if not arguments or "space_id" not in arguments:
                    raise ValueError("Missing required parameter: space_id")

                space_id = arguments["space_id"]
                params = {}

                if "archived" in arguments:
                    params["archived"] = str(arguments["archived"]).lower()

                folders_result = await make_clickup_request(
                    f"space/{space_id}/folder", params=params, access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(folders_result, indent=2))
                ]

            elif name == "get_lists":
                folder_id = arguments.get("folder_id") if arguments else None
                space_id = arguments.get("space_id") if arguments else None

                if not folder_id and not space_id:
                    raise ValueError(
                        "Missing required parameter: either folder_id or space_id must be provided"
                    )

                params = {}
                if "archived" in arguments:
                    params["archived"] = str(arguments["archived"]).lower()

                # Determine the endpoint based on whether folder_id or space_id is provided
                if folder_id:
                    endpoint = f"folder/{folder_id}/list"
                else:
                    endpoint = f"space/{space_id}/list"

                lists_result = await make_clickup_request(
                    endpoint, params=params, access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(lists_result, indent=2))
                ]

            elif name == "get_tasks":
                if not arguments or "list_id" not in arguments:
                    raise ValueError("Missing required parameter: list_id")

                list_id = arguments["list_id"]
                params = {}

                # Add optional parameters if provided
                if "archived" in arguments:
                    params["archived"] = str(arguments["archived"]).lower()
                if "include_closed" in arguments:
                    params["include_closed"] = str(arguments["include_closed"]).lower()
                if "subtasks" in arguments:
                    params["subtasks"] = str(arguments["subtasks"]).lower()
                if "page" in arguments:
                    params["page"] = arguments["page"]

                tasks_result = await make_clickup_request(
                    f"list/{list_id}/task", params=params, access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(tasks_result, indent=2))
                ]

            elif name == "get_task_by_id":
                if not arguments or "task_id" not in arguments:
                    raise ValueError("Missing required parameter: task_id")

                task_id = arguments["task_id"]
                params = {}

                # Add optional parameters if provided
                if "custom_task_ids" in arguments:
                    params["custom_task_ids"] = str(
                        arguments["custom_task_ids"]
                    ).lower()
                    if arguments["custom_task_ids"] and "team_id" not in arguments:
                        raise ValueError(
                            "team_id is required when using custom_task_ids"
                        )
                    params["team_id"] = arguments["team_id"]

                task_result = await make_clickup_request(
                    f"task/{task_id}", params=params, access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(task_result, indent=2))
                ]

            elif name == "create_task":
                if (
                    not arguments
                    or "list_id" not in arguments
                    or "name" not in arguments
                ):
                    raise ValueError("Missing required parameters: list_id and name")

                list_id = arguments["list_id"]

                # Prepare task data
                task_data = {"name": arguments["name"]}

                # Add optional fields if provided
                if "description" in arguments:
                    task_data["description"] = arguments["description"]
                if "status" in arguments:
                    task_data["status"] = arguments["status"]
                if "priority" in arguments:
                    task_data["priority"] = arguments["priority"]
                if "due_date" in arguments:
                    task_data["due_date"] = arguments["due_date"]
                if "due_date_time" in arguments:
                    task_data["due_date_time"] = arguments["due_date_time"]
                if "assignees" in arguments:
                    task_data["assignees"] = arguments["assignees"]
                if "tags" in arguments:
                    task_data["tags"] = arguments["tags"]

                create_result = await make_clickup_request(
                    f"list/{list_id}/task",
                    method="POST",
                    data=task_data,
                    access_token=access_token,
                )

                return [
                    TextContent(type="text", text=json.dumps(create_result, indent=2))
                ]

            elif name == "update_task":
                if not arguments or "task_id" not in arguments:
                    raise ValueError("Missing required parameter: task_id")

                task_id = arguments["task_id"]
                params = {}

                # Add params for custom task IDs if provided
                if "custom_task_ids" in arguments:
                    params["custom_task_ids"] = str(
                        arguments["custom_task_ids"]
                    ).lower()
                    if arguments["custom_task_ids"] and "team_id" not in arguments:
                        raise ValueError(
                            "team_id is required when using custom_task_ids"
                        )
                    params["team_id"] = arguments["team_id"]

                # Prepare update data (excluding task_id, custom_task_ids, and team_id)
                update_data = {
                    k: v
                    for k, v in arguments.items()
                    if k not in ["task_id", "custom_task_ids", "team_id"]
                }

                if not update_data:
                    raise ValueError("No update fields provided")

                update_result = await make_clickup_request(
                    f"task/{task_id}",
                    method="PUT",
                    data=update_data,
                    params=params,
                    access_token=access_token,
                )

                return [
                    TextContent(type="text", text=json.dumps(update_result, indent=2))
                ]

            elif name == "add_comment":
                if (
                    not arguments
                    or "task_id" not in arguments
                    or "comment_text" not in arguments
                ):
                    raise ValueError(
                        "Missing required parameters: task_id and comment_text"
                    )

                task_id = arguments["task_id"]
                params = {}

                # Add params for custom task IDs if provided
                if "custom_task_ids" in arguments:
                    params["custom_task_ids"] = str(
                        arguments["custom_task_ids"]
                    ).lower()
                    if arguments["custom_task_ids"] and "team_id" not in arguments:
                        raise ValueError(
                            "team_id is required when using custom_task_ids"
                        )
                    params["team_id"] = arguments["team_id"]

                # Prepare comment data
                comment_data = {"comment_text": arguments["comment_text"]}

                # Add assignee if provided
                if "assignee" in arguments:
                    comment_data["assignee"] = arguments["assignee"]

                comment_result = await make_clickup_request(
                    f"task/{task_id}/comment",
                    method="POST",
                    data=comment_data,
                    params=params,
                    access_token=access_token,
                )

                return [
                    TextContent(type="text", text=json.dumps(comment_result, indent=2))
                ]

            elif name == "create_list":
                if not arguments or "name" not in arguments:
                    raise ValueError("Missing required parameter: name")

                folder_id = arguments.get("folder_id")
                space_id = arguments.get("space_id")

                if not folder_id and not space_id:
                    raise ValueError("Either folder_id or space_id must be provided")

                # Determine the endpoint based on whether folder_id or space_id is provided
                if folder_id:
                    endpoint = f"folder/{folder_id}/list"
                else:
                    endpoint = f"space/{space_id}/list"

                # Prepare list data (excluding folder_id and space_id)
                list_data = {
                    k: v
                    for k, v in arguments.items()
                    if k not in ["folder_id", "space_id"]
                }

                create_result = await make_clickup_request(
                    endpoint, method="POST", data=list_data, access_token=access_token
                )

                return [
                    TextContent(type="text", text=json.dumps(create_result, indent=2))
                ]

            elif name == "create_folder":
                if (
                    not arguments
                    or "space_id" not in arguments
                    or "name" not in arguments
                ):
                    raise ValueError("Missing required parameters: space_id and name")

                space_id = arguments["space_id"]

                # Prepare folder data
                folder_data = {"name": arguments["name"]}

                create_result = await make_clickup_request(
                    f"space/{space_id}/folder",
                    method="POST",
                    data=folder_data,
                    access_token=access_token,
                )

                return [
                    TextContent(type="text", text=json.dumps(create_result, indent=2))
                ]

            raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error executing tool: {str(e)}")
            return [
                TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="clickup-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        try:
            authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
            print("Authentication successful! Credentials saved.")
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            print("Please check your OAuth configuration and try again.")
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
