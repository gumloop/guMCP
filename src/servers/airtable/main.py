import os
import sys
from typing import Optional, Iterable, Dict, Any, List
import json
import asyncio
from typing import Callable, TypeVar

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import aiohttp

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

from src.utils.airtable.util import (
    authenticate_and_save_credentials,
    get_credentials,
)


SERVICE_NAME = Path(__file__).parent.name
BASE_URL = "https://api.airtable.com/v0"
SCOPES = ["data.records:read", "data.records:write", "schema.bases:read"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

T = TypeVar("T")


async def with_exponential_backoff(
    func: Callable[[], T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
) -> T:
    """
    Execute a function with exponential backoff retry logic

    Args:
        func: Async function to execute
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        backoff_factor: Multiplier for the delay after each retry
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                raise last_exception

            logger.warning(
                f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}"
            )
            await asyncio.sleep(delay)
            delay = min(delay * backoff_factor, max_delay)


def process_airtable_token_response(token_response: Dict[str, Any]) -> Dict[str, Any]:
    """Process Airtable token response."""
    if "access_token" not in token_response:
        raise ValueError(
            f"Token exchange failed: {token_response.get('error', 'Unknown error')}"
        )

    # Store token details
    return {
        "access_token": token_response.get("access_token"),
        "refresh_token": token_response.get("refresh_token"),
        "token_type": token_response.get("token_type", "Bearer"),
        "expires_in": token_response.get("expires_in"),
        "scope": token_response.get("scope", ""),
    }


async def create_airtable_session(user_id, api_key=None):
    """Create a new aiohttp session for Airtable API requests"""
    access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    session = aiohttp.ClientSession(headers={"Authorization": f"Bearer {access_token}"})
    return session


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("airtable-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List bases and tables from Airtable"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        async with await create_airtable_session(user_id, api_key) as session:
            # First get bases (workspaces)
            async def get_bases():
                async with session.get(
                    "https://api.airtable.com/v0/meta/bases"
                ) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"Failed to list bases: {await response.text()}"
                        )
                    return await response.json()

            data = await with_exponential_backoff(get_bases)
            bases = data.get("bases", [])
            resources = []

            # For each base, list tables
            for base in bases:
                base_id = base.get("id")
                base_name = base.get("name")

                async def get_tables(base_id=base_id):
                    async with session.get(
                        f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
                    ) as response:
                        if response.status != 200:
                            raise ValueError(
                                f"Failed to list tables for base {base_id}: {await response.text()}"
                            )
                        return await response.json()

                try:
                    tables_data = await with_exponential_backoff(
                        lambda: get_tables(base_id)
                    )
                    tables = tables_data.get("tables", [])

                    for table in tables:
                        table_id = table.get("id")
                        table_name = table.get("name")

                        resource = Resource(
                            uri=f"airtable://table/{base_id}/{table_id}",
                            name=f"{base_name} - {table_name}",
                            description=f"Airtable table: {table_name} in base: {base_name}",
                        )
                        resources.append(resource)
                except Exception as e:
                    logger.error(f"Failed to get tables for base {base_id}: {str(e)}")
                    continue

            return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read records from an Airtable table by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        uri_str = str(uri)
        if not uri_str.startswith("airtable://table/"):
            raise ValueError(f"Invalid Airtable URI format: {uri}")

        # Remove the prefix and split the remaining path
        path = uri_str.replace("airtable://table/", "")
        parts = path.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid Airtable URI: {uri}, expected format: airtable://table/base_id/table_id"
            )

        base_id, table_id = parts

        async with await create_airtable_session(
            server.user_id, server.api_key
        ) as session:
            # Get table data
            async with session.get(f"{BASE_URL}/{base_id}/{table_id}") as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to read table: {error_text}")
                    raise ValueError(f"Failed to read table: {error_text}")

                data = await response.json()
                records = data.get("records", [])

                # Format records as readable text
                formatted_data = json.dumps(records, indent=2)

                return [
                    ReadResourceContents(
                        content=formatted_data, mime_type="application/json"
                    )
                ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="read_records",
                description="Read records from an Airtable table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Airtable table ID",
                        },
                        "max_records": {
                            "type": "integer",
                            "description": "Maximum number of records to return (optional)",
                        },
                        "filter_by_formula": {
                            "type": "string",
                            "description": "Airtable formula to filter records (optional)",
                        },
                    },
                    "required": ["base_id", "table_id"],
                },
            ),
            Tool(
                name="create_records",
                description="Create new records in an Airtable table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Airtable table ID",
                        },
                        "records": {
                            "type": "array",
                            "description": "Array of records to create",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "fields": {
                                        "type": "object",
                                        "description": "Record fields",
                                    }
                                },
                                "required": ["fields"],
                            },
                        },
                    },
                    "required": ["base_id", "table_id", "records"],
                },
            ),
            Tool(
                name="update_records",
                description="Update existing records in an Airtable table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Airtable table ID",
                        },
                        "records": {
                            "type": "array",
                            "description": "Array of records to update",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Record ID",
                                    },
                                    "fields": {
                                        "type": "object",
                                        "description": "Updated record fields",
                                    },
                                },
                                "required": ["id", "fields"],
                            },
                        },
                    },
                    "required": ["base_id", "table_id", "records"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if not arguments:
            raise ValueError(f"Missing arguments for tool: {name}")

        async with await create_airtable_session(
            server.user_id, server.api_key
        ) as session:
            if name == "read_records":
                base_id = arguments.get("base_id")
                table_id = arguments.get("table_id")

                if not base_id or not table_id:
                    raise ValueError("Missing base_id or table_id parameter")

                params = {}
                if "max_records" in arguments:
                    params["maxRecords"] = arguments["max_records"]
                if "filter_by_formula" in arguments:
                    params["filterByFormula"] = arguments["filter_by_formula"]

                url = f"{BASE_URL}/{base_id}/{table_id}"

                async def fetch_records():
                    async with session.get(url, params=params) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise ValueError(f"Failed to read records: {error_text}")
                        return await response.json()

                try:
                    data = await with_exponential_backoff(fetch_records)
                    records = data.get("records", [])
                    formatted_data = json.dumps(records, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Retrieved {len(records)} records:\n\n{formatted_data}",
                        )
                    ]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error: {str(e)}")]

            elif name == "create_records":
                base_id = arguments.get("base_id")
                table_id = arguments.get("table_id")
                records = arguments.get("records", [])

                if not base_id or not table_id or not records:
                    raise ValueError(
                        "Missing required parameters: base_id, table_id, or records"
                    )

                url = f"{BASE_URL}/{base_id}/{table_id}"
                async with session.post(url, json={"records": records}) as response:
                    if response.status not in (200, 201):
                        error_text = await response.text()
                        logger.error(f"Failed to create records: {error_text}")
                        return [
                            TextContent(
                                type="text",
                                text=f"Error: Failed to create records: {error_text}",
                            )
                        ]

                    data = await response.json()
                    created_records = data.get("records", [])

                    # Return confirmation with created record IDs
                    record_ids = [record.get("id") for record in created_records]
                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully created {len(created_records)} records.\nRecord IDs: {', '.join(record_ids)}",
                        )
                    ]

            elif name == "update_records":
                base_id = arguments.get("base_id")
                table_id = arguments.get("table_id")
                records = arguments.get("records", [])

                if not base_id or not table_id or not records:
                    raise ValueError(
                        "Missing required parameters: base_id, table_id, or records"
                    )

                url = f"{BASE_URL}/{base_id}/{table_id}"
                async with session.patch(url, json={"records": records}) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Failed to update records: {error_text}")
                        return [
                            TextContent(
                                type="text",
                                text=f"Error: Failed to update records: {error_text}",
                            )
                        ]

                    data = await response.json()
                    updated_records = data.get("records", [])

                    # Return confirmation with updated record IDs
                    record_ids = [record.get("id") for record in updated_records]
                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully updated {len(updated_records)} records.\nRecord IDs: {', '.join(record_ids)}",
                        )
                    ]

            raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="airtable-server",
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
        # Run OAuth flow for Airtable
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run OAuth flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
