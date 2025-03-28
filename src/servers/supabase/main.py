import os
import sys
import httpx
from typing import Optional, Iterable, List, Dict, Any

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
import json
from pathlib import Path
import supabase
from src.utils.supabase.util import authenticate_and_save_credentials, get_credentials

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

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_projects(access_token):
    """Get list of available Supabase projects"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    projects_url = "https://api.supabase.com/v1/projects"

    async with httpx.AsyncClient() as client:
        response = await client.get(projects_url, headers=headers)
        response.raise_for_status()
        return response.json()


async def create_supabase_client(access_token, project_id):
    """Create a Supabase client for a specific project"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    api_key_url = f"https://api.supabase.com/v1/projects/{project_id}/api-keys"

    async with httpx.AsyncClient() as client:
        response = await client.get(api_key_url, headers=headers)
        response.raise_for_status()
        api_keys = response.json()
        service_role_key = next(
            (
                key_dict["api_key"]
                for key_dict in api_keys
                if key_dict["name"] == "service_role"
            ),
            None,
        )

    if service_role_key is None:
        return

    project_url = f"https://{project_id}.supabase.co"
    return supabase.create_client(project_url, service_role_key)


async def get_tables_list(client):
    """Fetch the list of tables from Supabase"""
    response = await client.get("/rest/v1/?select=tablename")
    response.raise_for_status()
    return response.json()


async def get_table_schema(client, table_name):
    """Fetch the schema for a specific table"""
    # Use Postgres information_schema to get column definitions
    response = await client.post(
        "/rest/v1/rpc/execute",
        json={
            "query": f"""
            SELECT 
                column_name, 
                data_type, 
                is_nullable, 
                column_default
            FROM 
                information_schema.columns
            WHERE 
                table_name = '{table_name}'
            ORDER BY 
                ordinal_position
            """
        },
    )
    response.raise_for_status()
    return response.json()


async def execute_query(client, query, params=None):
    """Execute a SQL query and return the results"""
    data = {"query": query}
    if params:
        data["params"] = params

    response = await client.post("/rest/v1/rpc/execute", json=data)
    response.raise_for_status()
    return response.json()


async def get_table_data(client, table_name, limit=100, offset=0, filter_str=None):
    """Get data from a Supabase table with optional filtering"""
    url = f"/rest/v1/{table_name}"
    params = {
        "limit": limit,
        "offset": offset,
    }

    if filter_str:
        # Parse the filter string and add appropriate query parameters
        # This is a simplified implementation
        for filter_part in filter_str.split(","):
            if "=" in filter_part:
                key, value = filter_part.split("=", 1)
                params[key] = value

    response = await client.get(url, params=params)
    response.raise_for_status()
    return response.json()


async def insert_data(client, table_name, data):
    """Insert data into a Supabase table"""
    response = await client.post(f"/rest/v1/{table_name}", json=data)
    response.raise_for_status()
    return response.json()


async def update_data(client, table_name, data, filter_str):
    """Update data in a Supabase table based on filter"""
    params = {}

    # Parse the filter string and add appropriate query parameters
    if filter_str:
        for filter_part in filter_str.split(","):
            if "=" in filter_part:
                key, value = filter_part.split("=", 1)
                params[key] = f"eq.{value}"

    response = await client.patch(f"/rest/v1/{table_name}", params=params, json=data)
    response.raise_for_status()
    return response.json()


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("supabase-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(cursor: Optional[str] = None) -> list[Resource]:
        """List Supabase projects and their tables as resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        access_token = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )
        if not access_token:
            raise ValueError(
                "No access token found. Please authenticate with Supabase."
            )

        projects = await get_projects(access_token)

        resources = []
        for project in projects:
            project_id = project["id"]
            project_name = project.get("name", project_id)

            # Add project as a resource
            resources.append(
                Resource(
                    uri=f"supabase://project/{project_id}",
                    mimeType="application/json",
                    name=f"Project: {project_name}",
                )
            )

            # Create client for this project to list tables
            client = await create_supabase_client(access_token, project_id)
            if not client:
                continue

            try:
                result = client.rpc("get_tables").execute()
                tables = result.data

                for table in tables:
                    table_name = table.get("tablename")
                    if table_name:
                        resources.append(
                            Resource(
                                uri=f"supabase://project/{project_id}/table/{table_name}",
                                mimeType="application/json",
                                name=f"Table: {table_name} (in {project_name})",
                            )
                        )
                        resources.append(
                            Resource(
                                uri=f"supabase://project/{project_id}/schema/{table_name}",
                                mimeType="application/json",
                                name=f"Schema: {table_name} (in {project_name})",
                            )
                        )
            finally:
                if client:
                    await client.aclose()

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read data from Supabase resources"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )
        if not access_token:
            raise ValueError(
                "No access token found. Please authenticate with Supabase."
            )

        uri_str = str(uri)

        # Parse project ID from URI
        if not uri_str.startswith("supabase://project/"):
            raise ValueError(f"Invalid resource URI format: {uri_str}")

        parts = uri_str.split("/")
        if len(parts) < 4:
            raise ValueError(f"Invalid resource URI format: {uri_str}")

        project_id = parts[3]
        client = await create_supabase_client(access_token, project_id)

        try:
            if uri_str.startswith(f"supabase://project/{project_id}/table/"):
                table_name = parts[5]
                data = await get_table_data(client, table_name)
                return [
                    ReadResourceContents(
                        content=json.dumps(data, indent=2), mime_type="application/json"
                    )
                ]

            elif uri_str.startswith(f"supabase://project/{project_id}/schema/"):
                table_name = parts[5]
                schema = await get_table_schema(client, table_name)
                return [
                    ReadResourceContents(
                        content=json.dumps(schema, indent=2),
                        mime_type="application/json",
                    )
                ]

            elif uri_str == f"supabase://project/{project_id}":
                # Return project details
                projects = await get_projects(access_token)
                project = next((p for p in projects if p["id"] == project_id), None)
                if not project:
                    raise ValueError(f"Project {project_id} not found")
                return [
                    ReadResourceContents(
                        content=json.dumps(project, indent=2),
                        mime_type="application/json",
                    )
                ]

            else:
                raise ValueError(f"Unknown resource URI format: {uri_str}")
        finally:
            await client.aclose()

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available Supabase tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="read_table",
                description="Read data from a Supabase table with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID of the Supabase project",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to read",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Number of rows to skip (default: 0)",
                        },
                        "filter": {
                            "type": "string",
                            "description": "Optional filter in the format 'column=value,column2=value2'",
                        },
                    },
                    "required": ["project_id", "table_name"],
                },
            ),
            Tool(
                name="write_table",
                description="Insert data into a Supabase table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID of the Supabase project",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to write to",
                        },
                        "data": {
                            "type": "object",
                            "description": "Data to insert as JSON object or array of objects",
                        },
                    },
                    "required": ["project_id", "table_name", "data"],
                },
            ),
            Tool(
                name="update_table",
                description="Update data in a Supabase table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID of the Supabase project",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to update",
                        },
                        "data": {
                            "type": "object",
                            "description": "New values as JSON object",
                        },
                        "filter": {
                            "type": "string",
                            "description": "Filter to select rows in the format 'column=value,column2=value2'",
                        },
                    },
                    "required": ["project_id", "table_name", "data", "filter"],
                },
            ),
            Tool(
                name="execute_sql",
                description="Execute an arbitrary SQL query (read-only unless explicitly permitted)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID of the Supabase project",
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL query to execute",
                        },
                        "params": {
                            "type": "object",
                            "description": "Optional query parameters",
                        },
                    },
                    "required": ["project_id", "query"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle Supabase tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if not arguments:
            raise ValueError("Missing arguments")

        access_token = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )
        if not access_token:
            raise ValueError(
                "No access token found. Please authenticate with Supabase."
            )

        project_id = arguments.get("project_id")
        if not project_id:
            raise ValueError("Missing project_id parameter")

        client = await create_supabase_client(access_token, project_id)

        try:
            if name == "read_table":
                if "table_name" not in arguments:
                    raise ValueError("Missing table_name parameter")

                table_name = arguments["table_name"]
                limit = arguments.get("limit", 100)
                offset = arguments.get("offset", 0)
                filter_str = arguments.get("filter")

                data = await get_table_data(
                    client, table_name, limit, offset, filter_str
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Results from table '{table_name}' in project '{project_id}':\n\n{json.dumps(data, indent=2)}",
                    )
                ]

            elif name == "write_table":
                if "table_name" not in arguments or "data" not in arguments:
                    raise ValueError("Missing table_name or data parameter")

                table_name = arguments["table_name"]
                data = arguments["data"]

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        raise ValueError("Invalid JSON data string")

                result = await insert_data(client, table_name, data)

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully inserted data into '{table_name}' in project '{project_id}':\n\n{json.dumps(result, indent=2)}",
                    )
                ]

            elif name == "update_table":
                if (
                    "table_name" not in arguments
                    or "data" not in arguments
                    or "filter" not in arguments
                ):
                    raise ValueError("Missing table_name, data, or filter parameter")

                table_name = arguments["table_name"]
                data = arguments["data"]
                filter_str = arguments["filter"]

                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError:
                        raise ValueError("Invalid JSON data string")

                result = await update_data(client, table_name, data, filter_str)

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated data in '{table_name}' in project '{project_id}':\n\n{json.dumps(result, indent=2)}",
                    )
                ]

            elif name == "execute_sql":
                if "query" not in arguments:
                    raise ValueError("Missing query parameter")

                query = arguments["query"]
                params = arguments.get("params")

                # Basic check to prevent destructive queries
                query_lower = query.lower().strip()
                if any(
                    keyword in query_lower
                    for keyword in ["drop table", "truncate table", "delete from"]
                ):
                    # Check if an environment variable allows destructive queries
                    if (
                        not os.environ.get("ALLOW_DESTRUCTIVE_QUERIES", "").lower()
                        == "true"
                    ):
                        raise ValueError("Destructive SQL queries are not allowed")

                result = await execute_query(client, query, params)

                return [
                    TextContent(
                        type="text",
                        text=f"SQL query results from project '{project_id}':\n\n{json.dumps(result, indent=2)}",
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        finally:
            await client.aclose()

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="supabase-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler for OAuth authentication
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run OAuth authentication flow")
        print("Note: To run the server normally, use the MCP server framework.")
