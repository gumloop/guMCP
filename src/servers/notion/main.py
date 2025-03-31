import os
import sys

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
from dotenv import load_dotenv

# mcp is a custom package containing types, server definitions, and related models
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# notion_client is the official Notion SDK for Python (async version)
from notion_client import AsyncClient
import json

# create_auth_client is a custom function for handling user authentication
from src.auth.factory import create_auth_client

# Configure logging to capture info-level logs and above
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("notion-server")

# Load environment variables, such as the Notion API token
load_dotenv()
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
notion = AsyncClient(auth=NOTION_TOKEN)

# SERVICE_NAME is derived from the parent directory's name
SERVICE_NAME = Path(__file__).parent.name

def create_server(user_id, api_key=None):
    """
    Creates and configures a Notion server instance.

    This function sets up a GuMCP server with tooling for interacting with
    the Notion API. It includes endpoints for listing, searching, creating,
    and retrieving data from Notion.

    Args:
        user_id (str): The user identifier (for authentication or context).
        api_key (str, optional): An optional API key. Defaults to None.

    Returns:
        Server: A configured GuMCP server instance ready to handle requests.
    """
    server = Server("notion-server")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists available tools.

        Each tool is described with a corresponding JSON Schema definition
        for input validation. This function can be extended to register
        additional tools in the future.

        Returns:
            list[types.Tool]: A list of tool definitions with name, description, and schema.
        """
        # Retrieve user ID from the server instance context
        current_user = getattr(server, "user_id", None)
        logger.info(f"Listing tools for user: {current_user}")

        return [
            types.Tool(name="list-all-users", description="List all users", inputSchema={"type": "object", "properties": {}}),
            types.Tool(name="search-pages", description="Search all pages", inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }),
            types.Tool(name="list-databases", description="List all databases", inputSchema={"type": "object", "properties": {}}),
            types.Tool(name="query-database", description="Query a Notion database", inputSchema={
                "type": "object",
                "properties": {"database_id": {"type": "string"}},
                "required": ["database_id"]
            }),
            types.Tool(name="get-page", description="Retrieve a page by ID", inputSchema={
                "type": "object",
                "properties": {"page_id": {"type": "string"}},
                "required": ["page_id"]
            }),
            types.Tool(name="create-page", description="Create a new page in a database", inputSchema={
                "type": "object",
                "properties": {
                    "database_id": {"type": "string"},
                    "properties": {"type": "object"},
                },
                "required": ["database_id", "properties"]
            }),
            types.Tool(name="append-blocks", description="Append content blocks to a page or block", inputSchema={
                "type": "object",
                "properties": {
                    "block_id": {"type": "string"},
                    "children": {"type": "array"},
                },
                "required": ["block_id", "children"]
            }),
            types.Tool(name="get-block-children", description="List content blocks of a page or block", inputSchema={
                "type": "object",
                "properties": {"block_id": {"type": "string"}},
                "required": ["block_id"]
            }),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handles the invocation of a tool by name, passing the necessary arguments.

        This function dispatches calls to various Notion API methods depending on
        the tool name. It returns text content in JSON format for consistency.

        Args:
            name (str): The name of the tool to call (e.g., 'list-all-users').
            arguments (dict|None): A dictionary of arguments as required by the chosen tool.

        Returns:
            list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            A list of content objects containing the tool's response data.
        """
        # Retrieve user ID from the server instance context
        current_user = getattr(server, "user_id", None)
        logger.info(
            f"User {current_user} calling tool: {name} with arguments: {arguments}"
        )

        if name == "list-all-users":
            # List all Notion users
            result = await notion.users.list()
            return [types.TextContent(type="text", text=json.dumps(result.get("results", []), indent=2))]

        elif name == "search-pages":
            # Search all pages containing the query string
            result = await notion.search(query=arguments["query"])
            return [types.TextContent(type="text", text=json.dumps(result.get("results", []), indent=2))]

        elif name == "list-databases":
            # Search objects that are specifically databases
            result = await notion.search(filter={"property": "object", "value": "database"})
            return [types.TextContent(type="text", text=json.dumps(result.get("results", []), indent=2))]

        elif name == "query-database":
            # Query a specific database by ID
            result = await notion.databases.query(database_id=arguments["database_id"])
            return [types.TextContent(type="text", text=json.dumps(result.get("results", []), indent=2))]

        elif name == "get-page":
            # Retrieve a single page by ID
            result = await notion.pages.retrieve(page_id=arguments["page_id"])
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "create-page":
            # Create a page in a specified Notion database
            result = await notion.pages.create(parent={"database_id": arguments["database_id"]}, properties=arguments["properties"])
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "append-blocks":
            # Append content blocks (text, images, etc.) to a page or an existing block
            result = await notion.blocks.children.append(block_id=arguments["block_id"], children=arguments["children"])
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "get-block-children":
            # Retrieve all child blocks for a page or block
            result = await notion.blocks.children.list(block_id=arguments["block_id"])
            return [types.TextContent(type="text", text=json.dumps(result.get("results", []), indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    return server

# Assigning the create_server function to a variable for use by external modules
server = create_server

def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Retrieves the initialization options for the server.

    This constructs and returns InitializationOptions by leveraging the
    server's built-in capability methods, along with notification options
    and experimental capabilities.

    Args:
        server_instance (Server): A configured GuMCP server instance.

    Returns:
        InitializationOptions: The initialization options for this server,
        including capabilities and version information.
    """
    return InitializationOptions(
        server_name="notion-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

# Main handler to allow local authentication
if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        # In a local development flow, the user_id defaults to "local"
        user_id = "local"
    else:
        # Usage instructions if the user did not provide the correct argument
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
