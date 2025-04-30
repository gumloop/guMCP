import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Dict, Optional, Iterable

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent, Resource
from mcp.server.lowlevel.helper_types import ReadResourceContents
from pydantic import AnyUrl

from src.utils.monday.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name

# Updated scopes to exactly match monday.com's supported scopes
SCOPES = [
    "me:read",
    "boards:read",
    "workspaces:read",
    "boards:write",
    "workspaces:write",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(SERVICE_NAME)


class MondayClient:
    """Client for interacting with the Monday.com API."""

    def __init__(self, access_token: str):
        """Initialize the Monday.com client with an access token."""
        self.access_token = access_token
        self.base_url = "https://api.monday.com/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "API-Version": "2023-10",  # Using latest API version
        }

    def _make_request(self, query: str, variables: Dict = None) -> Dict:
        """Make a request to the Monday.com GraphQL API."""
        data = {"query": query}
        if variables:
            data["variables"] = variables

        response = requests.post(url=self.base_url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_me(self) -> Dict:
        """Get the current user's information."""
        query = """
        query {
            me {
                id
                name
                email
                title
                created_at
            }
        }
        """
        return self._make_request(query)

    def get_boards(self) -> Dict:
        """Get all boards accessible to the user."""
        query = """
        query {
            boards {
                id
                name
                state
                board_kind
                workspace_id
                updated_at
            }
        }
        """
        return self._make_request(query)

    def get_board(self, board_id: int) -> Dict:
        """Get a specific board by ID."""
        query = """
        query GetBoard($boardId: ID!) {
            boards(ids: [$boardId]) {
                id
                name
                state
                board_kind
                workspace_id
                updated_at
                groups {
                    id
                    title
                }
                items_page {
                    cursor
                    items {
                        id
                        name
                    }
                }
            }
        }
        """
        return self._make_request(query, {"boardId": board_id})

    def get_workspaces(self) -> Dict:
        """Get all workspaces accessible to the user."""
        query = """
        query {
            workspaces {
                id
                name
                kind
                description
            }
        }
        """
        return self._make_request(query)

    def create_item(self, board_id: int, item_name: str) -> Dict:
        """Create a new item in a board."""
        query = """
        mutation CreateItem($boardId: ID!, $itemName: String!) {
            create_item(board_id: $boardId, item_name: $itemName) {
                id
                name
               
            }
        }
        """
        variables = {"boardId": board_id, "itemName": item_name}
        return self._make_request(query, variables)

    def create_board(
        self,
        workspace_id: int,
        board_name: str,
        board_kind: str = "public",
        description: str = None,
    ) -> Dict:
        """Create a new board within a specific workspace.

        Args:
            workspace_id: The ID of the workspace where the board will be created
            board_name: The name of the new board
            board_kind: The type of board (public, private, or share)
            description: Optional description of the board
        """
        query = """
        mutation CreateBoard($workspaceId: ID!, $boardName: String!, $boardKind: BoardKind!, $description: String) {
            create_board(workspace_id: $workspaceId, board_name: $boardName, board_kind: $boardKind, description: $description) {
                id
                name
                board_kind
                description
                workspace_id
            }
        }
        """
        variables = {
            "workspaceId": workspace_id,
            "boardName": board_name,
            "boardKind": board_kind,
            "description": description,
        }
        return self._make_request(query, variables)

    def get_group(self, board_id: int, group_id: str) -> Dict:
        """Get a specific group within a board.

        Args:
            board_id: The ID of the board containing the group
            group_id: The ID of the group to fetch
        """
        query = """
        query GetGroupById($boardId: ID!, $groupId: String!) {
            boards(ids: [$boardId]) {
                groups(ids: [$groupId]) {
                    id
                    title
                    position
                    color
                }
            }
        }
        """
        variables = {"boardId": board_id, "groupId": group_id}
        return self._make_request(query, variables)

    def get_item(self, item_id: int) -> Dict:
        """Get a specific item by its ID.

        Args:
            item_id: The ID of the item to fetch
        """
        query = """
        query GetItem($itemId: ID!) {
            items(ids: [$itemId]) {
                id
                name
                board {
                    id
                    name
                }
                group {
                    id
                    title
                }
                column_values {
                    id
                    text
                    value
                }
            }
        }
        """
        variables = {"itemId": item_id}
        return self._make_request(query, variables)

    def delete_item(self, item_id: int) -> Dict:
        """Delete a specific item by its ID.

        Args:
            item_id: The ID of the item to delete
        """
        query = """
        mutation DeleteItem($itemId: ID!) {
            delete_item(item_id: $itemId) {
                id
            }
        }
        """
        variables = {"itemId": item_id}
        return self._make_request(query, variables)

    def delete_group(self, board_id: int, group_id: str) -> Dict:
        """Delete a specific group from a board.

        Args:
            board_id: The ID of the board containing the group
            group_id: The ID of the group to delete
        """
        query = """
        mutation DeleteGroup($boardId: ID!, $groupId: String!) {
            delete_group(board_id: $boardId, group_id: $groupId) {
                id
            }
        }
        """
        variables = {"boardId": board_id, "groupId": group_id}
        return self._make_request(query, variables)

    def change_column_value(
        self, board_id: int, item_id: int, column_id: str, value: str
    ) -> Dict:
        """Change the value of a column for a specific item.

        Args:
            board_id: The ID of the board containing the item
            item_id: The ID of the item to update
            column_id: The ID of the column to modify
            value: The new value for the column
        """
        query = """
        mutation ChangeColumnValue($boardId: ID!, $itemId: ID!, $columnId: String!, $value: String!) {
            change_simple_column_value(
                board_id: $boardId
                item_id: $itemId
                column_id: $columnId
                value: $value
            ) {
                id
                name
            }
        }
        """
        variables = {
            "boardId": board_id,
            "itemId": item_id,
            "columnId": column_id,
            "value": value,
        }
        return self._make_request(query, variables)

    def create_column(self, board_id: int, title: str, column_type: str) -> Dict:
        """Create a new column in a board.

        Args:
            board_id: The ID of the board where the column will be created
            title: The title/name of the new column
            column_type: The type of the column (e.g., 'status', 'text', 'number', etc.)
        """
        query = """
        mutation CreateColumn($boardId: ID!, $title: String!, $columnType: ColumnType!) {
            create_column(
                board_id: $boardId
                title: $title
                column_type: $columnType
            ) {
                id
                title
                type
            }
        }
        """
        variables = {"boardId": board_id, "title": title, "columnType": column_type}
        return self._make_request(query, variables)

    def create_group(self, board_id: int, group_name: str) -> Dict:
        """Create a new group in a board.

        Args:
            board_id: The ID of the board where the group will be created
            group_name: The name of the new group
        """
        query = """
        mutation CreateGroup($boardId: ID!, $groupName: String!) {
            create_group(board_id: $boardId, group_name: $groupName) {
                id
                title
                position
            }
        }
        """
        variables = {"boardId": board_id, "groupName": group_name}
        return self._make_request(query, variables)

    def create_subitem(self, parent_item_id: int, item_name: str) -> Dict:
        """Create a new sub-item under a parent item.

        Args:
            parent_item_id: The ID of the parent item
            item_name: The name of the new sub-item
        """
        query = """
        mutation CreateSubitem($parentItemId: ID!, $itemName: String!) {
            create_subitem(
                parent_item_id: $parentItemId
                item_name: $itemName
            ) {
                id
                name
            }
        }
        """
        variables = {"parentItemId": parent_item_id, "itemName": item_name}
        return self._make_request(query, variables)

    def delete_subitem(self, sub_item_id: int) -> Dict:
        """Delete a sub-item by its ID.

        Args:
            sub_item_id: The ID of the sub-item to delete
        """
        return self.delete_item(sub_item_id)

    def get_subitems(self, item_id: int) -> Dict:
        """Get all subitems of a specific item.

        Args:
            item_id: The ID of the parent item
        """
        query = """
        query GetSubitems($itemId: ID!) {
            items(ids: [$itemId]) {
                subitems {
                    id
                    name
                    column_values {
                        id
                        text
                        value
                    }
                }
            }
        }
        """
        variables = {"itemId": item_id}
        return self._make_request(query, variables)

    def archive_item(self, item_id: int) -> Dict:
        """Archive a specific item by its ID.

        Args:
            item_id: The ID of the item to archive
        """
        query = """
        mutation ArchiveItem($itemId: ID!) {
            archive_item(item_id: $itemId) {
                id
                name
                state
            }
        }
        """
        variables = {"itemId": item_id}
        return self._make_request(query, variables)

    def archive_group(self, board_id: int, group_id: str) -> Dict:
        """Archive a specific group in a board.

        Args:
            board_id: The ID of the board containing the group
            group_id: The ID of the group to archive
        """
        query = """
        mutation ArchiveGroup($boardId: ID!, $groupId: String!) {
            archive_group(board_id: $boardId, group_id: $groupId) {
                id
                title
                archived
            }
        }
        """
        variables = {"boardId": board_id, "groupId": group_id}
        return self._make_request(query, variables)

    def archive_board(self, board_id: int) -> Dict:
        """Archive a specific board by its ID.

        Args:
            board_id: The ID of the board to archive
        """
        query = """
        mutation ArchiveBoard($boardId: ID!) {
            archive_board(board_id: $boardId) {
                id
                name
                state
            }
        }
        """
        variables = {"boardId": board_id}
        return self._make_request(query, variables)


async def create_monday_client(user_id: str, api_key: str = None) -> MondayClient:
    """Create an authorized Monday.com API client."""
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return MondayClient(token)


def create_server(user_id: str, api_key: str = None) -> Server:
    """Initialize and configure the Monday.com MCP server."""
    server = Server("monday-server")

    server.user_id = user_id
    server.api_key = api_key
    server._monday_client = None

    async def _get_monday_client() -> MondayClient:
        """Get or create a Monday.com client."""
        if not server._monday_client:
            server._monday_client = await create_monday_client(
                server.user_id, server.api_key
            )
        return server._monday_client

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Monday.com resources (boards, workspaces, items, groups)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        monday = await _get_monday_client()
        try:
            resources = []

            # List all workspaces
            workspaces_response = monday.get_workspaces()
            for workspace in workspaces_response.get("data", {}).get("workspaces", []):
                resources.append(
                    Resource(
                        uri=f"monday://workspace/{workspace['id']}",
                        mimeType="application/json",
                        name=f"Workspace: {workspace['name']}",
                        description=f"Monday.com workspace ({workspace.get('kind', 'unknown')})",
                    )
                )

            # List all boards
            boards_response = monday.get_boards()
            for board in boards_response.get("data", {}).get("boards", []):
                resources.append(
                    Resource(
                        uri=f"monday://board/{board['id']}",
                        mimeType="application/json",
                        name=f"Board: {board['name']}",
                        description=f"Monday.com board ({board.get('board_kind', 'unknown')})",
                    )
                )

            # For each board, list its items
            for board in boards_response.get("data", {}).get("boards", []):
                board_id = board["id"]

                # Get board details to access items
                board_details = monday.get_board(board_id)
                board_data = board_details.get("data", {}).get("boards", [{}])[0]

                # List items in the board
                for item in board_data.get("items_page", {}).get("items", []):
                    resources.append(
                        Resource(
                            uri=f"monday://item/{item['id']}",
                            mimeType="application/json",
                            name=f"Item: {item['name']}",
                            description=f"Item in board {board['name']}",
                        )
                    )

                # List groups in the board
                for group in board_data.get("groups", []):
                    if group["id"] != "topics":
                        resources.append(
                            Resource(
                                uri=f"monday://board/{board_id}/group/{group['id']}",
                                mimeType="application/json",
                                name=f"Group: {group['title']}",
                                description=f"Group in board {board['name']}",
                            )
                        )

            return resources

        except Exception as e:
            logger.error(f"Error listing Monday.com resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from Monday.com by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        monday = await _get_monday_client()
        try:
            uri_str = str(uri)

            if uri_str.startswith("monday://workspace/"):
                # Handle workspace resource
                workspace_id = uri_str.replace("monday://workspace/", "")
                workspace_data = monday.get_workspaces()
                workspace = next(
                    (
                        w
                        for w in workspace_data.get("data", {}).get("workspaces", [])
                        if str(w["id"]) == workspace_id
                    ),
                    None,
                )
                if workspace:
                    return [
                        ReadResourceContents(
                            content=json.dumps(workspace, indent=2),
                            mime_type="application/json",
                        )
                    ]
            elif uri_str.startswith("monday://item/"):
                item_id = uri_str.replace("monday://item/", "")
                item_data = monday.get_item(int(item_id))
                return [
                    ReadResourceContents(
                        content=json.dumps(item_data, indent=2),
                        mime_type="application/json",
                    )
                ]

            elif uri_str.startswith("monday://board/"):
                # Handle board resource
                parts = uri_str.split("/")
                logger.info(f"Parts: {parts} {uri_str}")
                board_id = parts[3]

                if len(parts) == 4:
                    # Reading board itself
                    board_data = monday.get_board(int(board_id))
                    return [
                        ReadResourceContents(
                            content=json.dumps(board_data, indent=2),
                            mime_type="application/json",
                        )
                    ]
                elif len(parts) == 6:
                    resource_type = parts[4]
                    resource_id = parts[5]
                    if resource_type == "group":
                        # Reading group
                        group_data = monday.get_group(int(board_id), resource_id)
                        return [
                            ReadResourceContents(
                                content=json.dumps(group_data, indent=2),
                                mime_type="application/json",
                            )
                        ]

            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading Monday.com resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return a list of available Monday.com tools."""
        return [
            types.Tool(
                name="get_me",
                description="Get the current user's information",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_boards",
                description="Get all boards accessible to the user",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_board",
                description="Get a specific board by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board",
                        }
                    },
                    "required": ["board_id"],
                },
            ),
            types.Tool(
                name="get_workspaces",
                description="Get all workspaces accessible to the user",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="create_board",
                description="Create a new board within a workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "integer",
                            "description": "The ID of the workspace where the board will be created",
                        },
                        "board_name": {
                            "type": "string",
                            "description": "The name of the new board",
                        },
                        "board_kind": {
                            "type": "string",
                            "description": "The type of board (public, private, or share)",
                            "enum": ["public", "private", "share"],
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the board",
                        },
                    },
                    "required": ["workspace_id", "board_name", "board_kind"],
                },
            ),
            types.Tool(
                name="create_item",
                description="Create a new item in a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board",
                        },
                        "item_name": {
                            "type": "string",
                            "description": "The name of the new item",
                        },
                    },
                    "required": ["board_id", "item_name"],
                },
            ),
            types.Tool(
                name="get_group",
                description="Get a specific group within a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board containing the group",
                        },
                        "group_id": {
                            "type": "string",
                            "description": "The ID of the group to fetch",
                        },
                    },
                    "required": ["board_id", "group_id"],
                },
            ),
            types.Tool(
                name="get_item",
                description="Get a specific item by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "integer",
                            "description": "The ID of the item to fetch",
                        }
                    },
                    "required": ["item_id"],
                },
            ),
            types.Tool(
                name="delete_item",
                description="Delete a specific item by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "integer",
                            "description": "The ID of the item to delete",
                        }
                    },
                    "required": ["item_id"],
                },
            ),
            types.Tool(
                name="delete_group",
                description="Delete a specific group from a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board containing the group",
                        },
                        "group_id": {
                            "type": "string",
                            "description": "The ID of the group to delete",
                        },
                    },
                    "required": ["board_id", "group_id"],
                },
            ),
            types.Tool(
                name="change_column_value",
                description="Change the value of a column for a specific item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board containing the item",
                        },
                        "item_id": {
                            "type": "integer",
                            "description": "The ID of the item to update",
                        },
                        "column_id": {
                            "type": "string",
                            "description": "The ID of the column to modify",
                        },
                        "value": {
                            "type": "string",
                            "description": "The new value for the column",
                        },
                    },
                    "required": ["board_id", "item_id", "column_id", "value"],
                },
            ),
            types.Tool(
                name="create_column",
                description="Create a new column in a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board where the column will be created",
                        },
                        "title": {
                            "type": "string",
                            "description": "The title/name of the new column",
                        },
                        "column_type": {
                            "type": "string",
                            "description": "The type of the column (e.g., 'status', 'text', 'number')",
                        },
                    },
                    "required": ["board_id", "title", "column_type"],
                },
            ),
            types.Tool(
                name="create_group",
                description="Create a new group in a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board where the group will be created",
                        },
                        "group_name": {
                            "type": "string",
                            "description": "The name of the new group",
                        },
                    },
                    "required": ["board_id", "group_name"],
                },
            ),
            types.Tool(
                name="create_subitem",
                description="Create a new sub-item under a parent item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_item_id": {
                            "type": "integer",
                            "description": "The ID of the parent item",
                        },
                        "item_name": {
                            "type": "string",
                            "description": "The name of the new sub-item",
                        },
                    },
                    "required": ["parent_item_id", "item_name"],
                },
            ),
            types.Tool(
                name="delete_subitem",
                description="Delete a sub-item by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sub_item_id": {
                            "type": "integer",
                            "description": "The ID of the sub-item to delete",
                        }
                    },
                    "required": ["sub_item_id"],
                },
            ),
            types.Tool(
                name="get_subitems",
                description="Get all subitems of a specific item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "integer",
                            "description": "The ID of the parent item",
                        }
                    },
                    "required": ["item_id"],
                },
            ),
            types.Tool(
                name="archive_item",
                description="Archive a specific item by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "integer",
                            "description": "The ID of the item to archive",
                        }
                    },
                    "required": ["item_id"],
                },
            ),
            types.Tool(
                name="archive_group",
                description="Archive a specific group in a board",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board containing the group",
                        },
                        "group_id": {
                            "type": "string",
                            "description": "The ID of the group to archive",
                        },
                    },
                    "required": ["board_id", "group_id"],
                },
            ),
            types.Tool(
                name="archive_board",
                description="Archive a specific board by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "board_id": {
                            "type": "integer",
                            "description": "The ID of the board to archive",
                        }
                    },
                    "required": ["board_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        """Handle Monday.com tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        monday = await _get_monday_client()

        try:
            if name == "get_me":
                result = monday.get_me()
            elif name == "get_boards":
                result = monday.get_boards()
            elif name == "get_board":
                result = monday.get_board(arguments["board_id"])
            elif name == "get_workspaces":
                result = monday.get_workspaces()
            elif name == "create_board":
                result = monday.create_board(
                    workspace_id=arguments["workspace_id"],
                    board_name=arguments["board_name"],
                    board_kind=arguments["board_kind"],
                    description=arguments.get("description"),
                )
            elif name == "create_item":
                result = monday.create_item(
                    board_id=arguments["board_id"], item_name=arguments["item_name"]
                )
            elif name == "get_group":
                result = monday.get_group(
                    board_id=arguments["board_id"], group_id=arguments["group_id"]
                )
            elif name == "get_item":
                result = monday.get_item(item_id=arguments["item_id"])
            elif name == "delete_item":
                result = monday.delete_item(item_id=arguments["item_id"])
            elif name == "delete_subitem":
                result = monday.delete_subitem(sub_item_id=arguments["sub_item_id"])
            elif name == "delete_group":
                result = monday.delete_group(
                    board_id=arguments["board_id"], group_id=arguments["group_id"]
                )
            elif name == "change_column_value":
                result = monday.change_column_value(
                    board_id=arguments["board_id"],
                    item_id=arguments["item_id"],
                    column_id=arguments["column_id"],
                    value=arguments["value"],
                )
            elif name == "create_column":
                result = monday.create_column(
                    board_id=arguments["board_id"],
                    title=arguments["title"],
                    column_type=arguments["column_type"],
                )
            elif name == "create_group":
                result = monday.create_group(
                    board_id=arguments["board_id"], group_name=arguments["group_name"]
                )
            elif name == "create_subitem":
                result = monday.create_subitem(
                    parent_item_id=arguments["parent_item_id"],
                    item_name=arguments["item_name"],
                )
            elif name == "get_subitems":
                result = monday.get_subitems(item_id=arguments["item_id"])
            elif name == "archive_item":
                result = monday.archive_item(item_id=arguments["item_id"])
            elif name == "archive_group":
                result = monday.archive_group(
                    board_id=arguments["board_id"], group_id=arguments["group_id"]
                )
            elif name == "archive_board":
                result = monday.archive_board(board_id=arguments["board_id"])
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Define the initialization options for the Monday.com MCP server."""
    return InitializationOptions(
        server_name="monday-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
