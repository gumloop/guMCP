import logging

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("simple-tools-server")

user_data_stores = {}


def create_server(user_id=None, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("simple-tools-server")

    if user_id:
        server.user_id = user_id
        # Initialize user data store if needed
        if user_id not in user_data_stores:
            user_data_stores[user_id] = {}

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        List available tools.
        Each tool specifies its arguments using JSON Schema validation.
        """
        current_user = getattr(server, "user_id", None)
        logger.info(f"Listing tools for user: {current_user}")

        return [
            types.Tool(
                name="store-data",
                description="Store a key-value pair in the server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["key", "value"],
                },
            ),
            types.Tool(
                name="retrieve-data",
                description="Retrieve a value by its key",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                    },
                    "required": ["key"],
                },
            ),
            types.Tool(
                name="list-data",
                description="List all stored key-value pairs",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Handle tool execution requests.
        Tools can modify server state and return responses.
        """
        current_user = getattr(server, "user_id", None)
        logger.info(
            f"User {current_user} calling tool: {name} with arguments: {arguments}"
        )

        # Get user-specific data store
        data_store = user_data_stores.get(current_user, {})

        if name == "store-data":
            if not arguments:
                raise ValueError("Missing arguments")

            key = arguments.get("key")
            value = arguments.get("value")

            if not key or not value:
                raise ValueError("Missing key or value")

            # Update user-specific server state
            data_store[key] = value
            # Ensure it's saved back to the global store
            if current_user:
                user_data_stores[current_user] = data_store

            return [
                types.TextContent(
                    type="text",
                    text=f"Stored '{key}' with value: {value}",
                )
            ]

        elif name == "retrieve-data":
            if not arguments:
                raise ValueError("Missing arguments")

            key = arguments.get("key")

            if not key:
                raise ValueError("Missing key")

            if key not in data_store:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Key '{key}' not found",
                    )
                ]

            return [
                types.TextContent(
                    type="text",
                    text=f"Value for '{key}': {data_store[key]}",
                )
            ]

        elif name == "list-data":
            if not data_store:
                return [
                    types.TextContent(
                        type="text",
                        text="No data stored",
                    )
                ]

            data_list = "\n".join([f"- {k}: {v}" for k, v in data_store.items()])
            return [
                types.TextContent(
                    type="text",
                    text=f"Stored data:\n{data_list}",
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="simple-tools-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
