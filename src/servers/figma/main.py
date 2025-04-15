import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional, List, Dict, TypedDict, Union

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
    TextContent,
    ImageContent,
    EmbeddedResource,
)

from src.utils.figma.util import (
    authenticate_and_save_credentials,
    get_credentials,
)

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "current_user:read",
    "file_content:read",
    "files:read",
    "file_comments:read",
    "file_comments:write",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(SERVICE_NAME)


# Type definitions
class FigmaUser(TypedDict):
    id: str
    handle: str
    img_url: str
    email: Optional[str]


class Vector(TypedDict):
    x: float
    y: float


class FrameOffset(TypedDict):
    node_id: str
    node_offset: Vector


class Region(TypedDict):
    x: float
    y: float
    region_height: float
    region_width: float
    comment_pin_corner: Optional[str]


class FrameOffsetRegion(TypedDict):
    node_id: str
    node_offset: Vector
    region_height: float
    region_width: float
    comment_pin_corner: Optional[str]


class Reaction(TypedDict):
    user: FigmaUser
    emoji: str
    created_at: str


class Comment(TypedDict):
    id: str
    client_meta: Union[FrameOffset, Region, FrameOffsetRegion]
    file_key: str
    parent_id: Optional[str]
    user: FigmaUser
    created_at: str
    resolved_at: Optional[str]
    order_id: Optional[int]
    reactions: List[Reaction]


class CommentsResponse(TypedDict):
    comments: List[Comment]


class Pagination(TypedDict):
    prev_page: Optional[str]
    next_page: Optional[str]


class ReactionsResponse(TypedDict):
    reactions: List[Reaction]
    pagination: Pagination


class Project(TypedDict):
    id: int
    name: str


class TeamProjectsResponse(TypedDict):
    name: str
    projects: List[Project]


class Branch(TypedDict):
    key: str
    name: str
    thumbnail_url: str
    last_modified: str


class File(TypedDict):
    key: str
    name: str
    thumbnail_url: str
    last_modified: str
    branches: Optional[List[Branch]]


class ProjectFilesResponse(TypedDict):
    name: str
    files: List[File]


class Version(TypedDict):
    id: str
    created_at: str
    label: Optional[str]
    description: Optional[str]
    user: FigmaUser


class FileVersionsResponse(TypedDict):
    versions: List[Version]
    pagination: Pagination


class FigmaClient:
    """Client for interacting with the Figma API."""

    def __init__(self, access_token: str):
        """Initialize the Figma client with an access token."""
        self.access_token = access_token
        self.base_url = "https://api.figma.com/v1"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(
        self, method: str, endpoint: str, params: Dict = None, data: Dict = None
    ) -> Dict:
        """Make a request to the Figma API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, params=params, json=data
        )
        response.raise_for_status()
        return response.json()

    def get_me(self) -> FigmaUser:
        """Get the authenticated user's information."""
        return self._make_request("GET", "me")

    def get_file(self, file_key: str) -> Dict:
        """Get a Figma file by key."""
        return self._make_request("GET", f"files/{file_key}")

    def get_file_images(
        self, file_key: str, node_ids: List[str], format: str = "png"
    ) -> Dict:
        """Get images for specific nodes in a Figma file."""
        return self._make_request(
            "GET",
            f"images/{file_key}",
            params={"ids": ",".join(node_ids), "format": format},
        )

    def get_file_comments(self, file_key: str, as_md: bool = False) -> CommentsResponse:
        """
        Get comments for a Figma file.

        Args:
            file_key: The file key to get comments from
            as_md: If True, returns comments as markdown equivalents when applicable

        Returns:
            A response containing a list of comments
        """
        params = {}
        if as_md:
            params["as_md"] = "true"

        return self._make_request("GET", f"files/{file_key}/comments", params=params)

    def post_comment(
        self,
        file_key: str,
        message: str,
        client_meta: Optional[Dict] = None,
        parent_id: Optional[str] = None,
    ) -> Dict:
        """
        Post a comment on a Figma file.

        Args:
            file_key: The file key to post the comment to
            message: The comment message
            client_meta: Optional positioning information for the comment
            parent_id: Optional ID of the parent comment if this is a reply

        Returns:
            The created comment
        """
        data = {"message": message}
        if client_meta:
            data["client_meta"] = client_meta
        if parent_id:
            data["parent_id"] = parent_id

        return self._make_request("POST", f"files/{file_key}/comments", data=data)

    def delete_comment(self, file_key: str, comment_id: str) -> None:
        """
        Delete a comment from a Figma file.

        Args:
            file_key: The file key containing the comment
            comment_id: The ID of the comment to delete

        Returns:
            None
        """
        url = f"{self.base_url}/files/{file_key}/comments/{comment_id}"
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()

    def get_comment_reactions(
        self, file_key: str, comment_id: str, cursor: Optional[str] = None
    ) -> ReactionsResponse:
        """
        Get reactions for a specific comment.

        Args:
            file_key: The file key containing the comment
            comment_id: The ID of the comment to get reactions for
            cursor: Optional cursor for pagination

        Returns:
            A response containing a list of reactions and pagination information
        """
        params = {}
        if cursor:
            params["cursor"] = cursor

        return self._make_request(
            "GET", f"files/{file_key}/comments/{comment_id}/reactions", params=params
        )

    def post_comment_reaction(self, file_key: str, comment_id: str, emoji: str) -> None:
        """
        Post a reaction to a comment.

        Args:
            file_key: The file key containing the comment
            comment_id: The ID of the comment to react to
            emoji: The emoji shortcode for the reaction

        Returns:
            None
        """
        data = {"emoji": emoji}
        url = f"{self.base_url}/files/{file_key}/comments/{comment_id}/reactions"
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()

    def delete_comment_reaction(
        self, file_key: str, comment_id: str, emoji: str
    ) -> None:
        """
        Delete a reaction from a comment.

        Args:
            file_key: The file key containing the comment
            comment_id: The ID of the comment containing the reaction
            emoji: The emoji shortcode of the reaction to delete

        Returns:
            None
        """
        url = f"{self.base_url}/files/{file_key}/comments/{comment_id}/reactions"
        params = {"emoji": emoji}
        response = requests.delete(url, headers=self.headers, params=params)
        response.raise_for_status()

    def get_team_projects(self, team_id: str) -> TeamProjectsResponse:
        """
        Get all projects within a team.

        Args:
            team_id: The ID of the team to list projects from

        Returns:
            A response containing the team name and a list of projects
        """
        return self._make_request("GET", f"teams/{team_id}/projects")

    def get_project_files(
        self, project_id: str, branch_data: bool = False
    ) -> ProjectFilesResponse:
        """
        List the files in a given project.

        Args:
            project_id: The ID of the project to list files from
            branch_data: Whether to return branch metadata in the response

        Returns:
            A response containing the project name and a list of files
        """
        params = {}
        if branch_data:
            params["branch_data"] = "true"

        return self._make_request("GET", f"projects/{project_id}/files", params=params)

    def get_file_versions(self, file_key: str) -> FileVersionsResponse:
        """
        Get the version history of a file.

        Args:
            file_key: The file key to get version history from

        Returns:
            A response containing a list of versions and pagination information
        """
        return self._make_request("GET", f"files/{file_key}/versions")


async def create_figma_client(user_id: str, api_key: str = None) -> FigmaClient:
    """
    Create an authorized Figma API client.

    Args:
        user_id (str): The user ID associated with the credentials.
        api_key (str, optional): Optional override for authentication.

    Returns:
        FigmaClient: Figma API client with credentials initialized.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return FigmaClient(token)


def create_server(user_id: str, api_key: str = None) -> Server:
    """
    Initialize and configure the Figma MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("figma-server")

    server.user_id = user_id
    server.api_key = api_key
    server._figma_client = None

    async def _get_figma_client() -> FigmaClient:
        """Get or create a Figma client."""
        if not server._figma_client:
            server._figma_client = await create_figma_client(
                server.user_id, server.api_key
            )
        return server._figma_client

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available Figma tools.

        Returns:
            list[types.Tool]: List of tool definitions supported by this server.
        """
        return [
            types.Tool(
                name="get_me",
                description="Get the authenticated user's information",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="get_file",
                description="Get a Figma file by key",
                inputSchema={
                    "type": "object",
                    "properties": {"file_key": {"type": "string"}},
                    "required": ["file_key"],
                },
            ),
            types.Tool(
                name="get_file_comments",
                description="Get comments for a Figma file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "as_md": {"type": "boolean"},
                    },
                    "required": ["file_key"],
                },
            ),
            types.Tool(
                name="post_comment",
                description="Post a comment on a Figma file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "message": {"type": "string"},
                        "client_meta": {"type": "object"},
                        "parent_id": {"type": "string"},
                    },
                    "required": ["file_key", "message"],
                },
            ),
            types.Tool(
                name="delete_comment",
                description="Delete a comment from a Figma file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "comment_id": {"type": "string"},
                    },
                    "required": ["file_key", "comment_id"],
                },
            ),
            types.Tool(
                name="get_comment_reactions",
                description="Get reactions for a specific comment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "comment_id": {"type": "string"},
                        "cursor": {"type": "string"},
                    },
                    "required": ["file_key", "comment_id"],
                },
            ),
            types.Tool(
                name="post_comment_reaction",
                description="Post a reaction to a comment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "comment_id": {"type": "string"},
                        "emoji": {"type": "string"},
                    },
                    "required": ["file_key", "comment_id", "emoji"],
                },
            ),
            types.Tool(
                name="delete_comment_reaction",
                description="Delete a reaction from a comment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_key": {"type": "string"},
                        "comment_id": {"type": "string"},
                        "emoji": {"type": "string"},
                    },
                    "required": ["file_key", "comment_id", "emoji"],
                },
            ),
            types.Tool(
                name="get_team_projects",
                description="Get all projects within a team",
                inputSchema={
                    "type": "object",
                    "properties": {"team_id": {"type": "string"}},
                    "required": ["team_id"],
                },
            ),
            types.Tool(
                name="get_project_files",
                description="List the files in a given project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "branch_data": {"type": "boolean"},
                    },
                    "required": ["project_id"],
                },
            ),
            types.Tool(
                name="get_file_versions",
                description="Get the version history of a file",
                inputSchema={
                    "type": "object",
                    "properties": {"file_key": {"type": "string"}},
                    "required": ["file_key"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Handle Figma tool invocation from the MCP system.

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

        figma = await _get_figma_client()

        try:
            if name == "get_me":
                result = figma.get_me()
            elif name == "get_file":
                result = figma.get_file(arguments["file_key"])

            elif name == "get_file_comments":
                result = figma.get_file_comments(
                    arguments["file_key"], arguments.get("as_md", False)
                )
            elif name == "post_comment":
                result = figma.post_comment(
                    arguments["file_key"],
                    arguments["message"],
                    arguments.get("client_meta"),
                    arguments.get("parent_id"),
                )
            elif name == "delete_comment":
                figma.delete_comment(arguments["file_key"], arguments["comment_id"])
                result = {"success": True, "message": "Comment deleted successfully"}
            elif name == "get_comment_reactions":
                result = figma.get_comment_reactions(
                    arguments["file_key"],
                    arguments["comment_id"],
                    arguments.get("cursor"),
                )
            elif name == "post_comment_reaction":
                figma.post_comment_reaction(
                    arguments["file_key"], arguments["comment_id"], arguments["emoji"]
                )
                result = {"success": True, "message": "Reaction added successfully"}
            elif name == "delete_comment_reaction":
                figma.delete_comment_reaction(
                    arguments["file_key"], arguments["comment_id"], arguments["emoji"]
                )
                result = {"success": True, "message": "Reaction deleted successfully"}
            elif name == "get_team_projects":
                result = figma.get_team_projects(arguments["team_id"])
            elif name == "get_project_files":
                result = figma.get_project_files(
                    arguments["project_id"], arguments.get("branch_data", False)
                )
            elif name == "get_file_versions":
                result = figma.get_file_versions(arguments["file_key"])
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
    Define the initialization options for the Figma MCP server.

    Args:
        server_instance (Server): The server instance to describe.

    Returns:
        InitializationOptions: MCP-compatible initialization configuration.
    """
    return InitializationOptions(
        server_name="figma-server",
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
