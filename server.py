import logging
from typing import Dict, Any

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("simple-tools-server")

# Store data as a simple dictionary to demonstrate state management
data_store = {}

# Create server instance
server = Server("simple-tools-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    logger.info("Listing tools")
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
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and return responses.
    """
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    if name == "store-data":
        if not arguments:
            raise ValueError("Missing arguments")

        key = arguments.get("key")
        value = arguments.get("value")

        if not key or not value:
            raise ValueError("Missing key or value")

        # Update server state
        data_store[key] = value

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

def get_initialization_options() -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="simple-tools-server",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
