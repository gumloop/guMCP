import asyncio

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Store data as a simple dictionary to demonstrate state management
data_store = {}

server = Server("simple-tools-server")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
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

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="simple-tools-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
