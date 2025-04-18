import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, Any, TypedDict, Union, Literal

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

from src.utils.canva.util import (
    authenticate_and_save_credentials,
    get_credentials,
)

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "app:read",
    "app:write",
    "design:content:read",
    "design:meta:read",
    "design:content:write",
    "design:permission:read",
    "design:permission:write",
    "folder:read",
    "folder:write",
    "folder:permission:read",
    "folder:permission:write",
    "asset:read",
    "asset:write",
    "comment:read",
    "comment:write",
    "brandtemplate:meta:read",
    "brandtemplate:content:read",
    "profile:read",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(SERVICE_NAME)


# Type definitions
class UserProfile(TypedDict):
    display_name: str


class ProfileResponse(TypedDict):
    profile: UserProfile


class TeamUserSummary(TypedDict):
    user_id: str
    team_id: str


class UserResponse(TypedDict):
    team_user: TeamUserSummary


class UserInfo(TypedDict):
    id: str
    display_name: str


class ThreadTypeContent(TypedDict):
    plaintext: str
    markdown: str


class ThreadTypeMentionUser(TypedDict):
    user_id: str
    team_id: str
    display_name: str


class ThreadTypeMention(TypedDict):
    tag: str
    user: ThreadTypeMentionUser


class ThreadType(TypedDict):
    type: str
    content: ThreadTypeContent
    mentions: Dict[str, ThreadTypeMention]
    assignee: Optional[UserInfo]
    resolver: Optional[UserInfo]


class Thread(TypedDict):
    id: str
    design_id: str
    thread_type: ThreadType
    author: UserInfo
    created_at: int
    updated_at: int


class ThreadResponse(TypedDict):
    thread: Thread


class ReplyContent(TypedDict):
    plaintext: str
    markdown: str


class Reply(TypedDict):
    id: str
    design_id: str
    thread_id: str
    author: UserInfo
    content: ReplyContent
    mentions: Dict[str, ThreadTypeMention]
    created_at: int
    updated_at: int


class ReplyResponse(TypedDict):
    reply: Reply


class RepliesResponse(TypedDict):
    items: List[Reply]
    continuation: Optional[str]


class DesignOwner(TypedDict):
    user_id: str
    team_id: str


class DesignThumbnail(TypedDict):
    width: int
    height: int
    url: str


class DesignUrls(TypedDict):
    edit_url: str
    view_url: str


class Design(TypedDict):
    id: str
    title: str
    owner: DesignOwner
    thumbnail: DesignThumbnail
    urls: DesignUrls
    created_at: int
    updated_at: int
    page_count: int


class DesignResponse(TypedDict):
    design: Design


class DesignsResponse(TypedDict):
    items: List[Design]
    continuation: Optional[str]


class DesignTypeInput(TypedDict):
    type: Literal["preset", "custom"]
    name: Optional[str]
    width: Optional[int]
    height: Optional[int]


class FolderThumbnail(TypedDict):
    width: int
    height: int
    url: str


class Folder(TypedDict):
    id: str
    name: str
    created_at: int
    updated_at: int
    thumbnail: FolderThumbnail


class FolderResponse(TypedDict):
    folder: Folder


class CanvaClient:
    """Client for interacting with the Canva API."""

    def __init__(self, access_token: str):
        """Initialize the Canva client with an access token."""
        self.access_token = access_token
        self.base_url = "https://api.canva.com/rest/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Make a request to the Canva API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, params=params, json=data
        )
        response.raise_for_status()
        return response.json()

    def get_user_profile(self) -> ProfileResponse:
        """Get the authenticated user's profile information."""
        return self._make_request("GET", "users/me/profile")

    def get_user_details(self) -> UserResponse:
        """Get the authenticated user's details including user ID and team ID."""
        return self._make_request("GET", "users/me")

    def get_thread(self, design_id: str, thread_id: str) -> ThreadResponse:
        """Get metadata for a comment thread."""
        return self._make_request("GET", f"designs/{design_id}/comments/{thread_id}")

    def create_reply(
        self, design_id: str, thread_id: str, message_plaintext: str
    ) -> ReplyResponse:
        """Reply to a comment on a design."""
        data = {"message_plaintext": message_plaintext}
        return self._make_request(
            "POST", f"designs/{design_id}/comments/{thread_id}/replies", data=data
        )

    def create_thread(
        self, design_id: str, message_plaintext: str, assignee_id: Optional[str] = None
    ) -> ThreadResponse:
        """Create a new comment thread on a design."""
        data = {"message_plaintext": message_plaintext}
        if assignee_id:
            data["assignee_id"] = assignee_id
        return self._make_request("POST", f"designs/{design_id}/comments", data=data)

    def list_replies(
        self,
        design_id: str,
        thread_id: str,
        limit: Optional[int] = None,
        continuation: Optional[str] = None,
    ) -> RepliesResponse:
        """List the replies to a comment on a design."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if continuation is not None:
            params["continuation"] = continuation
        return self._make_request(
            "GET", f"designs/{design_id}/comments/{thread_id}/replies", params=params
        )

    def get_reply(self, design_id: str, thread_id: str, reply_id: str) -> ReplyResponse:
        """Get a comment reply."""
        return self._make_request(
            "GET", f"designs/{design_id}/comments/{thread_id}/replies/{reply_id}"
        )

    def get_design(self, design_id: str) -> DesignResponse:
        """Get the metadata for one of the user's designs."""
        return self._make_request("GET", f"designs/{design_id}")

    def list_designs(
        self,
        query: Optional[str] = None,
        continuation: Optional[str] = None,
        ownership: Optional[Literal["any", "owned", "shared"]] = None,
        sort_by: Optional[
            Literal[
                "relevance",
                "modified_descending",
                "modified_ascending",
                "title_descending",
                "title_ascending",
            ]
        ] = None,
    ) -> DesignsResponse:
        """List all the user's designs."""
        params = {}
        if query is not None:
            params["query"] = query
        if continuation is not None:
            params["continuation"] = continuation
        if ownership is not None:
            params["ownership"] = ownership
        if sort_by is not None:
            params["sort_by"] = sort_by
        return self._make_request("GET", "designs", params=params)

    def create_design(
        self,
        design_type: Optional[DesignTypeInput] = None,
        asset_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> DesignResponse:
        """Create a new Canva design."""
        data = {}
        if design_type is not None:
            data["design_type"] = design_type
        if asset_id is not None:
            data["asset_id"] = asset_id
        if title is not None:
            data["title"] = title
        return self._make_request("POST", "designs", data=data)

    def create_folder(self, name: str, parent_folder_id: str) -> FolderResponse:
        """Create a new folder in the user's Projects."""
        data = {"name": name, "parent_folder_id": parent_folder_id}
        return self._make_request("POST", "folders", data=data)

    def get_folder(self, folder_id: str) -> FolderResponse:
        """Get the metadata for a folder."""
        return self._make_request("GET", f"folders/{folder_id}")

    def update_folder(self, folder_id: str, name: str) -> FolderResponse:
        """Update a folder's metadata."""
        data = {"name": name}
        return self._make_request("PATCH", f"folders/{folder_id}", data=data)

    def delete_folder(self, folder_id: str) -> None:
        """Delete a folder."""
        url = f"{self.base_url}/folders/{folder_id}"
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()


async def create_canva_client(user_id: str, api_key: str = None) -> CanvaClient:
    """
    Create an authorized Canva API client.

    Args:
        user_id (str): The user ID associated with the credentials.
        api_key (str, optional): Optional override for authentication.

    Returns:
        CanvaClient: Canva API client with credentials initialized.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return CanvaClient(token)


def create_server(user_id: str, api_key: str = None) -> Server:
    """
    Initialize and configure the Canva MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("canva-server")

    server.user_id = user_id
    server.api_key = api_key
    server._canva_client = None

    async def _get_canva_client() -> CanvaClient:
        """Get or create a Canva client."""
        if not server._canva_client:
            server._canva_client = await create_canva_client(
                server.user_id, server.api_key
            )
        return server._canva_client

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available Canva tools.

        Returns:
            list[types.Tool]: List of tool definitions supported by this server.
        """
        return [
            types.Tool(
                name="get_user_profile",
                description="Get the current user's profile information including display name",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_user_details",
                description="Get the current user's details including user ID and team ID",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_thread",
                description="Get metadata for a comment thread",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                    },
                    "required": ["design_id", "thread_id"],
                },
            ),
            types.Tool(
                name="create_reply",
                description="Reply to a comment on a design",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "message_plaintext": {"type": "string"},
                    },
                    "required": ["design_id", "thread_id", "message_plaintext"],
                },
            ),
            types.Tool(
                name="create_thread",
                description="Create a new comment thread on a design",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string"},
                        "message_plaintext": {"type": "string"},
                        "assignee_id": {"type": "string"},
                    },
                    "required": ["design_id", "message_plaintext"],
                },
            ),
            types.Tool(
                name="list_replies",
                description="List the replies to a comment on a design",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        "continuation": {"type": "string"},
                    },
                    "required": ["design_id", "thread_id"],
                },
            ),
            types.Tool(
                name="get_reply",
                description="Get a comment reply",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "reply_id": {"type": "string"},
                    },
                    "required": ["design_id", "thread_id", "reply_id"],
                },
            ),
            types.Tool(
                name="get_design",
                description="Get the metadata for one of the user's designs",
                inputSchema={
                    "type": "object",
                    "properties": {"design_id": {"type": "string"}},
                    "required": ["design_id"],
                },
            ),
            types.Tool(
                name="list_designs",
                description="List all the user's designs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "maxLength": 255},
                        "continuation": {"type": "string"},
                        "ownership": {
                            "type": "string",
                            "enum": ["any", "owned", "shared"],
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": [
                                "relevance",
                                "modified_descending",
                                "modified_ascending",
                                "title_descending",
                                "title_ascending",
                            ],
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="create_design",
                description="Create a new Canva design",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "design_type": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": ["preset", "custom"],
                                },
                                "name": {"type": "string"},
                                "width": {"type": "integer"},
                                "height": {"type": "integer"},
                            },
                            "required": ["type"],
                        },
                        "asset_id": {"type": "string"},
                        "title": {"type": "string", "minLength": 1, "maxLength": 255},
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="create_folder",
                description="Create a new folder in the user's Projects",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1, "maxLength": 255},
                        "parent_folder_id": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 50,
                        },
                    },
                    "required": ["name", "parent_folder_id"],
                },
            ),
            types.Tool(
                name="get_folder",
                description="Get the metadata for a folder",
                inputSchema={
                    "type": "object",
                    "properties": {"folder_id": {"type": "string"}},
                    "required": ["folder_id"],
                },
            ),
            types.Tool(
                name="update_folder",
                description="Update a folder's metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_id": {"type": "string"},
                        "name": {"type": "string", "minLength": 1, "maxLength": 255},
                    },
                    "required": ["folder_id", "name"],
                },
            ),
            types.Tool(
                name="delete_folder",
                description="Delete a folder",
                inputSchema={
                    "type": "object",
                    "properties": {"folder_id": {"type": "string"}},
                    "required": ["folder_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Handle Canva tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called.
            arguments (dict | None): Parameters passed to the tool.

        Returns:
            list[Union[TextContent, ImageContent, EmbeddedResource]]:
                Output content from tool execution.
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        canva = await _get_canva_client()

        try:
            if name == "get_user_profile":
                result = canva.get_user_profile()
            elif name == "get_user_details":
                result = canva.get_user_details()
            elif name == "get_thread":
                result = canva.get_thread(
                    arguments["design_id"], arguments["thread_id"]
                )
            elif name == "create_reply":
                result = canva.create_reply(
                    arguments["design_id"],
                    arguments["thread_id"],
                    arguments["message_plaintext"],
                )
            elif name == "create_thread":
                result = canva.create_thread(
                    arguments["design_id"],
                    arguments["message_plaintext"],
                    arguments.get("assignee_id"),
                )
            elif name == "list_replies":
                result = canva.list_replies(
                    arguments["design_id"],
                    arguments["thread_id"],
                    arguments.get("limit"),
                    arguments.get("continuation"),
                )
            elif name == "get_reply":
                result = canva.get_reply(
                    arguments["design_id"],
                    arguments["thread_id"],
                    arguments["reply_id"],
                )
            elif name == "get_design":
                result = canva.get_design(arguments["design_id"])
            elif name == "list_designs":
                result = canva.list_designs(
                    arguments.get("query"),
                    arguments.get("continuation"),
                    arguments.get("ownership"),
                    arguments.get("sort_by"),
                )
            elif name == "create_design":
                result = canva.create_design(
                    arguments.get("design_type"),
                    arguments.get("asset_id"),
                    arguments.get("title"),
                )
            elif name == "create_folder":
                result = canva.create_folder(
                    arguments["name"], arguments["parent_folder_id"]
                )
            elif name == "get_folder":
                result = canva.get_folder(arguments["folder_id"])
            elif name == "update_folder":
                result = canva.update_folder(arguments["folder_id"], arguments["name"])
            elif name == "delete_folder":
                canva.delete_folder(arguments["folder_id"])
                result = {"success": True, "message": "Folder deleted successfully"}
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the Canva MCP server.

    Args:
        server_instance (Server): The server instance to describe.

    Returns:
        InitializationOptions: MCP-compatible initialization configuration.
    """
    return InitializationOptions(
        server_name="canva-server",
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
        import asyncio

        asyncio.run(authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES))
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
