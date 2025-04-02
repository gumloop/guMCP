import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from notion_client import AsyncClient
from src.auth.factory import create_auth_client
from src.utils.notion.util import authenticate_and_save_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["all"]  # Notion doesn't use granular OAuth scopes like Google

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_credentials(user_id, api_key=None):
    """
    Retrieves the OAuth access token for a specific Notion user.

    Args:
        user_id (str): The identifier of the user.
        api_key (Optional[str]): Optional API key passed during server creation.

    Returns:
        str: The access token to authenticate with the Notion API.

    Raises:
        ValueError: If credentials are missing or invalid.
    """
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    def handle_missing():
        err = f"Notion credentials not found for user {user_id}."
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


async def create_notion_client(user_id, api_key=None):
    """
    Creates an authorized Notion AsyncClient instance.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        AsyncClient: An authenticated Notion client object.
    """
    token = await get_credentials(user_id, api_key)
    return AsyncClient(auth=token)


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Notion MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Notion tools registered.
    """
    server = Server("notion-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Notion API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="list_all_users",
                description="List all users",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="search_pages",
                description="Search pages by text",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="list_databases",
                description="List all databases",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="query_database",
                description="Query a Notion database",
                inputSchema={
                    "type": "object",
                    "properties": {"database_id": {"type": "string"}},
                    "required": ["database_id"],
                },
            ),
            types.Tool(
                name="get_page",
                description="Retrieve a page by ID",
                inputSchema={
                    "type": "object",
                    "properties": {"page_id": {"type": "string"}},
                    "required": ["page_id"],
                },
            ),
            types.Tool(
                name="create_page",
                description="Create a new page in a database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_id": {"type": "string"},
                        "properties": {"type": "object"},
                    },
                    "required": ["database_id", "properties"],
                },
            ),
            types.Tool(
                name="append_blocks",
                description="Append content blocks to a page or block",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "block_id": {"type": "string"},
                        "children": {"type": "array"},
                    },
                    "required": ["block_id", "children"],
                },
            ),
            types.Tool(
                name="get_block_children",
                description="List content blocks of a page or block",
                inputSchema={
                    "type": "object",
                    "properties": {"block_id": {"type": "string"}},
                    "required": ["block_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Notion API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        notion = await create_notion_client(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            if name == "list_all_users":
                result = await notion.users.list()
            elif name == "search_pages":
                result = await notion.search(query=arguments["query"])
            elif name == "list_databases":
                result = await notion.search(
                    filter={"property": "object", "value": "database"}
                )
            elif name == "query_database":
                result = await notion.databases.query(
                    database_id=arguments["database_id"]
                )
            elif name == "get_page":
                result = await notion.pages.retrieve(page_id=arguments["page_id"])
            elif name == "create_page":
                result = await notion.pages.create(
                    parent={"database_id": arguments["database_id"]},
                    properties=arguments["properties"],
                )
            elif name == "append_blocks":
                result = await notion.blocks.children.append(
                    block_id=arguments["block_id"], children=arguments["children"]
                )
            elif name == "get_block_children":
                result = await notion.blocks.children.list(
                    block_id=arguments["block_id"]
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling Notion API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options required for registering the server.

    Args:
        server_instance (Server): The guMCP server instance.

    Returns:
        InitializationOptions: The initialization configuration block.
    """
    return InitializationOptions(
        server_name="notion-server",
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
