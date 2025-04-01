import os
import sys
import logging
import json
from pathlib import Path

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

# mcp is a custom package containing types, server definitions, and related models
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# notion_client is the official Notion SDK for Python (async version)
from notion_client import AsyncClient

# create_auth_client is a custom function for handling user authentication
from src.auth.factory import create_auth_client

# Configure logging to capture info-level logs and above
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("notion-server")

# SERVICE_NAME is derived from the parent directory's name
SERVICE_NAME = Path(__file__).parent.name

def authenticate_and_save_notion_key(user_id):
    """
    Authenticate with Notion and save API key for the specified user ID.
    Prompts for an API key locally (if ENVIRONMENT=local) and saves
    it via the auth client.
    """
    logger = logging.getLogger("notion")
    logger.info(f"Starting Notion authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Notion API key: ").strip()
    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("notion", user_id, {"api_key": api_key})
    logger.info(f"Notion API key saved for user {user_id}. You can now run the server.")
    return api_key


def get_notion_credentials(user_id, api_key=None):
    """
    Get the Notion API key for the specified user.

    If api_key is provided, it will be used to instantiate the
    auth client. Then we retrieve and validate the user's
    stored Notion API key. Raises ValueError if not found.
    """
    logger = logging.getLogger("notion")
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("notion", user_id)

    def handle_missing_credentials():
        error_str = f"Notion API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    # For some auth clients, credentials_data might already be the API key string
    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


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
    server.user_id = user_id
    server.api_key = api_key

    # Retrieve an API key from stored credentials (or from the passed argument)
    api_key = get_notion_credentials(server.user_id, api_key=server.api_key)
    # Create an AsyncClient and store it on the server instance
    server.notion = AsyncClient(auth=api_key)

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
        current_user = getattr(server, "user_id", None)
        logger.info(f"Listing tools for user: {current_user}")

        return [
            types.Tool(
                name="list_all_users",
                description="List all users",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="search_pages",
                description="Search all pages",
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
        current_user = getattr(server, "user_id", None)
        logger.info(f"User {current_user} calling tool: {name} with arguments: {arguments}")

        notion = getattr(server, "notion", None)
        if not notion:
            return [
                types.TextContent(
                    type="text",
                    text="Error: Notion client not initialized.",
                )
            ]

        # If the closure's 'api_key' ended up not being set, fail early
        if not api_key:
            return [
                types.TextContent(
                    type="text",
                    text="Error: Notion API key not provided. Please configure your API key.",
                )
            ]

        if not arguments:
            return [
                types.TextContent(
                    type="text",
                    text="Error: No arguments provided."
                )
            ]

        if name == "list_all_users":
            result = await notion.users.list()
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result.get("results", []), indent=2)
                )
            ]

        elif name == "search_pages":
            result = await notion.search(query=arguments["query"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result.get("results", []), indent=2)
                )
            ]

        elif name == "list_databases":
            result = await notion.search(filter={"property": "object", "value": "database"})
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result.get("results", []), indent=2)
                )
            ]

        elif name == "query_database":
            result = await notion.databases.query(database_id=arguments["database_id"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result.get("results", []), indent=2)
                )
            ]

        elif name == "get_page":
            result = await notion.pages.retrieve(page_id=arguments["page_id"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]

        elif name == "create_page":
            result = await notion.pages.create(
                parent={"database_id": arguments["database_id"]},
                properties=arguments["properties"],
            )
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]

        elif name == "append_blocks":
            result = await notion.blocks.children.append(
                block_id=arguments["block_id"],
                children=arguments["children"]
            )
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )
            ]

        elif name == "get_block_children":
            result = await notion.blocks.children.list(block_id=arguments["block_id"])
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(result.get("results", []), indent=2)
                )
            ]

        # If the tool name is unrecognized
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


if __name__ == "__main__":
    # Safeguard in case user didn't provide any command-line args
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        # In a local development flow, the user_id defaults to "local"
        user_id = "local"
        authenticate_and_save_notion_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
