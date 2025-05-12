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
SCOPES = [
    "data.records:read",
    "data.records:write",
    "schema.bases:read",
    "schema.bases:write",
]

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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a record returned by Airtable",
                    "example": [
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Sample Record"}}'
                    ],
                },
                requiredScopes=["data.records:read"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a created record",
                    "example": [
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Sample Record"}}'
                    ],
                },
                requiredScopes=["data.records:write"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing an updated record",
                    "example": [
                        '{"id":"<RECORD_ID>","fields":{"Primary Field":"Updated Record"}}'
                    ],
                },
                requiredScopes=["data.records:write"],
            ),
            Tool(
                name="list_bases",
                description="List all accessible Airtable bases with their ID, name, and permission level",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing an accessible Airtable base",
                    "example": [
                        '{"id":"<BASE_ID>","name":"Product catalog","permissionLevel":"create"}',
                        '{"id":"<BASE_ID>","name":"Test Base","permissionLevel":"create"}',
                    ],
                },
                requiredScopes=["schema.bases:read"],
            ),
            Tool(
                name="list_tables",
                description="List all tables in a given Airtable base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                    },
                    "required": ["base_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a table in the specified base",
                    "example": [
                        '{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"type":"singleLineText","id":"<FIELD_ID>","name":"Name","description":"Primary field"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                        '{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"type":"singleLineText","id":"<FIELD_ID>","name":"Name","description":"Primary field"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                    ],
                },
                requiredScopes=["schema.bases:read"],
            ),
            Tool(
                name="base_schema",
                description="Get complete schema for all tables in a base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "include": {
                            "type": "array",
                            "description": "Additional fields to include in the response (optional)",
                            "items": {"type": "string", "enum": ["visibleFieldIds"]},
                        },
                    },
                    "required": ["base_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a table schema",
                    "example": [
                        '{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Name","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                        '{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Name","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                    ],
                },
                requiredScopes=["schema.bases:read"],
            ),
            Tool(
                name="search_records",
                description="Search for records containing specific text in a table",
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
                        "search_query": {
                            "type": "string",
                            "description": "Text to search for in records",
                        },
                    },
                    "required": ["base_id", "table_id", "search_query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a record matching the search query",
                    "example": [
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Record with search term"}}',
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Record with search term"}}',
                    ],
                },
                requiredScopes=["data.records:read"],
            ),
            Tool(
                name="get_record",
                description="Get a single record by its ID from a table",
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
                        "record_id": {
                            "type": "string",
                            "description": "Record ID to retrieve",
                        },
                    },
                    "required": ["base_id", "table_id", "record_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a record",
                    "example": [
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Record value"}}',
                        '{"id":"<RECORD_ID>","createdTime":"<TIMESTAMP>","fields":{"Primary Field":"Record value"}}',
                    ],
                },
                requiredScopes=["data.records:read"],
            ),
            Tool(
                name="delete_records",
                description="Delete one or more records from a table",
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
                        "record_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of record IDs to delete",
                        },
                    },
                    "required": ["base_id", "table_id", "record_ids"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing the result of a delete operation",
                    "example": [
                        '{"deleted":true,"id":"<RECORD_ID>"}',
                        '{"deleted":true,"id":"<RECORD_ID>"}',
                    ],
                },
                requiredScopes=["data.records:write"],
            ),
            Tool(
                name="create_table",
                description="Create a new table in a base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name for the new table",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for the new table (optional)",
                        },
                        "fields": {
                            "type": "array",
                            "description": "Fields to add to the new table",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "type": {"type": "string"},
                                    "options": {"type": "object"},
                                },
                                "required": ["name", "type"],
                            },
                        },
                    },
                    "required": ["base_id", "table_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a newly created table",
                    "example": [
                        '{"id":"<TABLE_ID>","name":"Test Table","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Primary Field","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                        '{"id":"<TABLE_ID>","name":"Test Table","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Primary Field","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
            Tool(
                name="update_table",
                description="Update an existing table's name or description",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "ID of the table to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the table (optional)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the table (optional)",
                        },
                    },
                    "required": ["base_id", "table_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing an updated table",
                    "example": [
                        '{"id":"<TABLE_ID>","name":"Updated Table","description":"Updated by automated test","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Primary Field","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                        '{"id":"<TABLE_ID>","name":"Updated Table","description":"Updated by automated test","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Primary Field","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
            Tool(
                name="create_field",
                description="Add a new field (column) to an existing table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Table ID to add the field to",
                        },
                        "field_name": {
                            "type": "string",
                            "description": "Name for the new field",
                        },
                        "field_type": {
                            "type": "string",
                            "description": "Type of field (singleLineText, multipleAttachment, etc.)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description for the field (optional)",
                        },
                        "options": {
                            "type": "object",
                            "description": "Options specific to the field type (optional)",
                        },
                    },
                    "required": ["base_id", "table_id", "field_name", "field_type"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a newly created field",
                    "example": [
                        '{"id":"<FIELD_ID>","name":"Test Field","type":"singleLineText","description":""}',
                        '{"id":"<FIELD_ID>","name":"Test Field","type":"singleLineText","description":""}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
            Tool(
                name="update_field",
                description="Update a field's metadata in a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "Airtable base ID",
                        },
                        "table_id": {
                            "type": "string",
                            "description": "Table ID containing the field",
                        },
                        "field_id": {
                            "type": "string",
                            "description": "Field ID to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the field (optional)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the field (optional)",
                        },
                        "options": {
                            "type": "object",
                            "description": "Updated options for the field (optional)",
                        },
                    },
                    "required": ["base_id", "table_id", "field_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing an updated field",
                    "example": [
                        '{"id":"<FIELD_ID>","name":"Updated Field","type":"singleLineText","description":"Updated by automated test"}',
                        '{"id":"<FIELD_ID>","name":"Updated Field","type":"singleLineText","description":"Updated by automated test"}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
            Tool(
                name="create_base",
                description="Create a new Airtable base with the provided tables",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the new base",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "Workspace ID where the base will be created",
                        },
                        "tables": {
                            "type": "array",
                            "description": "A list of JSON objects representing the tables to create with the base",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Name of the table",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "Description of the table (optional)",
                                    },
                                    "fields": {
                                        "type": "array",
                                        "description": "Array of fields to create in the table. First field becomes the primary field.",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "Name of the field",
                                                },
                                                "type": {
                                                    "type": "string",
                                                    "description": "Type of field (singleLineText, multilineText, checkbox, etc.)",
                                                },
                                                "description": {
                                                    "type": "string",
                                                    "description": "Description of the field (optional)",
                                                },
                                                "options": {
                                                    "type": "object",
                                                    "description": "Options specific to the field type (optional)",
                                                },
                                            },
                                            "required": ["name", "type"],
                                        },
                                    },
                                },
                                "required": ["name", "fields"],
                            },
                        },
                    },
                    "required": ["name", "workspace_id", "tables"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing a newly created base with its tables",
                    "example": [
                        '{"id":"<BASE_ID>","tables":[{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Name","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}]}',
                        '{"id":"<BASE_ID>","tables":[{"id":"<TABLE_ID>","name":"Test Table","description":"Test Table Description","primaryFieldId":"<FIELD_ID>","fields":[{"id":"<FIELD_ID>","name":"Name","description":"Primary field","type":"singleLineText"}],"views":[{"id":"<VIEW_ID>","name":"Grid view","type":"grid"}]}]}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
            Tool(
                name="delete_base",
                description="Delete an existing Airtable base",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "base_id": {
                            "type": "string",
                            "description": "ID of the base to delete",
                        },
                    },
                    "required": ["base_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings, each representing the result of a delete operation",
                    "example": [
                        '{"id":"<BASE_ID>","deleted":true}',
                        '{"id":"<BASE_ID>","deleted":true}',
                    ],
                },
                requiredScopes=["schema.bases:write"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        arguments = arguments or {}

        # Helper function to build URL paths
        def build_url(path_type, *args):
            if path_type == "meta":
                return f"{BASE_URL}/meta/{'/'.join(args)}"
            else:
                return f"{BASE_URL}/{'/'.join(args)}"

        # Tool configuration mapping
        tool_configs = {
            # Original tools are kept as-is
            "read_records": None,
            "create_records": None,
            "update_records": None,
            # New tools with unified configuration
            "list_bases": {
                "method": "GET",
                "url": build_url("meta", "bases"),
                "prepare_params": None,
                "prepare_data": None,
            },
            "list_tables": {
                "method": "GET",
                "url": lambda args: build_url(
                    "meta", "bases", args["base_id"], "tables"
                ),
                "prepare_params": None,
                "prepare_data": None,
            },
            "base_schema": {
                "method": "GET",
                "url": lambda args: build_url(
                    "meta", "bases", args["base_id"], "tables"
                ),
                "prepare_params": lambda args: (
                    {"include": args.get("include", [])} if "include" in args else None
                ),
                "prepare_data": None,
            },
            "search_records": {
                "method": "GET",
                "url": lambda args: build_url(
                    "data", args["base_id"], args["table_id"]
                ),
                "prepare_params": lambda args: {"search": args["search_query"]},
                "prepare_data": None,
            },
            "get_record": {
                "method": "GET",
                "url": lambda args: build_url(
                    "data", args["base_id"], args["table_id"], args["record_id"]
                ),
                "prepare_params": None,
                "prepare_data": None,
            },
            "delete_records": {
                "method": "DELETE",
                "url": lambda args: build_url(
                    "data", args["base_id"], args["table_id"]
                ),
                "prepare_params": lambda args: {"records[]": args["record_ids"]},
                "prepare_data": None,
            },
            "create_table": {
                "method": "POST",
                "url": lambda args: build_url(
                    "meta", "bases", args["base_id"], "tables"
                ),
                "prepare_params": None,
                "prepare_data": lambda args: {
                    "name": args["table_name"],
                    "description": args.get("description", ""),
                    "fields": args.get("fields", []),
                },
            },
            "update_table": {
                "method": "PATCH",
                "url": lambda args: build_url(
                    "meta", "bases", args["base_id"], "tables", args["table_id"]
                ),
                "validate": lambda args: "name" in args or "description" in args,
                "prepare_params": None,
                "prepare_data": lambda args: {
                    **({"name": args["name"]} if "name" in args else {}),
                    **(
                        {"description": args["description"]}
                        if "description" in args
                        else {}
                    ),
                },
            },
            "create_field": {
                "method": "POST",
                "url": lambda args: build_url(
                    "meta",
                    "bases",
                    args["base_id"],
                    "tables",
                    args["table_id"],
                    "fields",
                ),
                "prepare_params": None,
                "prepare_data": lambda args: {
                    "name": args["field_name"],
                    "type": args["field_type"],
                    "description": args.get("description", ""),
                    **({"options": args["options"]} if "options" in args else {}),
                },
            },
            "update_field": {
                "method": "PATCH",
                "url": lambda args: build_url(
                    "meta",
                    "bases",
                    args["base_id"],
                    "tables",
                    args["table_id"],
                    "fields",
                    args["field_id"],
                ),
                "validate": lambda args: "name" in args
                or "description" in args
                or "options" in args,
                "prepare_params": None,
                "prepare_data": lambda args: {
                    **({"name": args["name"]} if "name" in args else {}),
                    **(
                        {"description": args["description"]}
                        if "description" in args
                        else {}
                    ),
                    **({"options": args["options"]} if "options" in args else {}),
                },
            },
            "create_base": {
                "method": "POST",
                "url": build_url("meta", "bases"),
                "prepare_params": None,
                "prepare_data": lambda args: {
                    "name": args["name"],
                    "workspaceId": args["workspace_id"],
                    "tables": args["tables"],
                    **(
                        {"description": args["description"]}
                        if "description" in args
                        else {}
                    ),
                },
            },
            "delete_base": {
                "method": "DELETE",
                "url": lambda args: build_url("meta", "bases", args["base_id"]),
                "prepare_params": None,
                "prepare_data": None,
            },
        }

        async with await create_airtable_session(
            server.user_id, server.api_key
        ) as session:

            async def make_api_request(method, url, params=None, json_data=None):
                async def request_func():
                    if method.lower() == "get":
                        async with session.get(url, params=params) as response:
                            if response.status not in (200, 201):
                                error_text = await response.text()
                                raise ValueError(f"API request failed: {error_text}")
                            return await response.json()
                    elif method.lower() == "post":
                        async with session.post(url, json=json_data) as response:
                            if response.status not in (200, 201):
                                error_text = await response.text()
                                raise ValueError(f"API request failed: {error_text}")
                            return await response.json()
                    elif method.lower() == "patch":
                        async with session.patch(url, json=json_data) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                raise ValueError(f"API request failed: {error_text}")
                            return await response.json()
                    elif method.lower() == "delete":
                        query_params = []
                        if params:
                            for key, value in params.items():
                                if isinstance(value, list):
                                    for item in value:
                                        query_params.append(f"{key}={item}")
                                else:
                                    query_params.append(f"{key}={value}")

                        if query_params:
                            full_url = f"{url}?{'&'.join(query_params)}"
                        else:
                            full_url = url

                        async with session.delete(full_url) as response:
                            if response.status != 200:
                                error_text = await response.text()
                                raise ValueError(f"API request failed: {error_text}")
                            return await response.json()
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")

                return await with_exponential_backoff(request_func)

            # Keep original implementations for backward compatibility
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

                    # Return individual records as separate content items
                    if records:
                        # For backward compatibility, keep the summary text
                        result = [
                            TextContent(
                                type="text",
                                text=f"Retrieved {len(records)} records:",
                            )
                        ]

                        # Add each record as a separate content item
                        for record in records:
                            result.append(
                                TextContent(
                                    type="text",
                                    text=json.dumps(record, indent=2),
                                )
                            )
                        return result
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Retrieved 0 records:\n\n[]",
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

                    record_ids = [record.get("id") for record in updated_records]
                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully updated {len(updated_records)} records.\nRecord IDs: {', '.join(record_ids)}",
                        )
                    ]

            elif name in tool_configs:
                config = tool_configs[name]

                url = config["url"]
                if callable(url):
                    url = url(arguments)

                params = (
                    config["prepare_params"](arguments)
                    if config["prepare_params"]
                    else None
                )
                data = (
                    config["prepare_data"](arguments)
                    if config["prepare_data"]
                    else None
                )

                if "validate" in config and not config["validate"](arguments):
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "Validation failed for the request"}, indent=2
                            ),
                        )
                    ]

                try:
                    response_data = await make_api_request(
                        config["method"], url, params, data
                    )
                    logger.info(f"Response data: {response_data}")

                    # If response contains an array of items, return multiple TextContent objects
                    if isinstance(response_data, dict) and any(
                        isinstance(response_data.get(key), list)
                        and len(response_data.get(key)) > 0
                        for key in response_data.keys()
                    ):
                        result = [
                            TextContent(
                                type="text",
                                text=json.dumps(response_data, indent=2),
                            )
                        ]

                        # Find the first array in the response
                        for key, value in response_data.items():
                            if isinstance(value, list) and len(value) > 0:
                                # Add each item in the array as a separate TextContent
                                for item in value:
                                    if isinstance(item, dict):
                                        result.append(
                                            TextContent(
                                                type="text",
                                                text=json.dumps(item, indent=2),
                                            )
                                        )
                                break

                        return result
                    else:
                        return [
                            TextContent(
                                type="text", text=json.dumps(response_data, indent=2)
                            )
                        ]
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": str(e)}, indent=2)
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
