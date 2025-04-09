"""
This file is the main entry point for the Snowflake MCP server.
"""

import os
import sys
from pathlib import Path
import logging

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client
from src.utils.snowflake.util import authenticate_and_save_credentials

import snowflake.connector

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["session:role:SYSADMIN"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_credentials(user_id, api_key=None):
    """
    Retrieves the OAuth access token for a specific Snowflake user.

    Args:
        user_id (str): The identifier of the user.
        api_key (Optional[str]): Optional API key passed during server creation.

    Returns:
        str: The access token to authenticate with the Snowflake API.

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

    return credentials_data


async def get_snowflake_token(user_id, api_key=None):
    """
    This function is used to get the Snowflake access token for a specific user.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        str: The access token to authenticate with the Snowflake API.
    """
    token = await get_credentials(user_id, api_key)
    return token


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Snowflake MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Snowflake tools registered.
    """
    server = Server("snowflake-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Snowflake API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="create_database",
                description="Create a new database in Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {
                            "type": "string",
                            "description": "Name of the database to create",
                        },
                    },
                    "required": ["database_name"],
                },
            ),
            types.Tool(
                name="create_schema",
                description="Create a new schema in Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schema_name": {
                            "type": "string",
                            "description": "Name of the schema to create",
                        },
                        "database_name": {
                            "type": "string",
                            "description": "Name of the database to create",
                        },
                    },
                    "required": ["schema_name", "database_name"],
                },
            ),
            types.Tool(
                name="list_schemas",
                description="List all schemas in a database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {
                            "type": "string",
                            "description": "Name of the database to list schemas from",
                        },
                    },
                    "required": ["database_name"],
                },
            ),
            types.Tool(
                name="list_databases",
                description="List all databases in Snowflake",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="create_table",
                description="Create a new table in Snowflake with support for constraints and indexes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to create",
                        },
                        "schema_name": {
                            "type": "string",
                            "description": "Schema name to create the table in",
                        },
                        "database_name": {
                            "type": "string",
                            "description": "Database name to create the table in",
                        },
                        "columns": {
                            "type": "string",
                            "description": "Column definitions (name, type, constraints)",
                        },
                        "primary_key": {
                            "type": "string",
                            "description": "Primary key column(s)",
                        },
                        "indexes": {
                            "type": "string",
                            "description": "Index definitions",
                        },
                    },
                    "required": [
                        "table_name",
                        "database_name",
                        "columns",
                    ],
                },
            ),
            types.Tool(
                name="list_tables",
                description="List all tables in a database with filtering and sorting options",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {
                            "type": "string",
                            "description": "Database name to list tables from",
                        }
                    },
                    "required": ["database_name"],
                },
            ),
            types.Tool(
                name="describe_table",
                description="Describe the structure of a table in Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to describe",
                        },
                        "database_name": {
                            "type": "string",
                            "description": "Database name to describe the table in",
                        },
                        "schema_name": {
                            "type": "string",
                            "description": "Schema name to describe the table in (default: PUBLIC)",
                        },
                    },
                    "required": ["table_name", "database_name"],
                },
            ),
            types.Tool(
                name="create_warehouse",
                description="Create a new warehouse in Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "warehouse_name": {
                            "type": "string",
                            "description": "Name of the warehouse to create",
                        }
                    },
                    "required": ["warehouse_name"],
                },
            ),
            types.Tool(
                name="list_warehouses",
                description="List all warehouses in Snowflake",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            types.Tool(
                name="execute_query",
                description="Execute a SQL query on Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute in format (DB_NAME.SCHEMA_NAME.TABLE_NAME)",
                        },
                        "warehouse": {
                            "type": "string",
                            "description": "The warehouse to use for the query",
                        },
                    },
                    "required": ["query", "warehouse"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Snowflake API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        token = await get_snowflake_token(server.user_id, server.api_key)
        snowflake_client = snowflake.connector.connect(
            user=token["username"],
            account=token["account"],
            authenticator="oauth",
            token=token["access_token"],
        )

        if arguments is None:
            arguments = {}

        try:
            if name == "create_database":
                database_name = arguments["database_name"]
                cursor = snowflake_client.cursor()
                cursor.execute(f"CREATE DATABASE {database_name}")
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Database {database_name} created successfully",
                    )
                ]
            elif name == "create_schema":
                schema_name = arguments["schema_name"]
                database_name = arguments["database_name"]
                cursor = snowflake_client.cursor()
                cursor.execute(f"CREATE SCHEMA {database_name}.{schema_name}")
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Schema {schema_name} created successfully",
                    )
                ]

            elif name == "list_schemas":
                database_name = arguments["database_name"]
                cursor = snowflake_client.cursor()
                cursor.execute(f"SHOW SCHEMAS IN DATABASE {database_name}")
                schemas = cursor.fetchall()
                description = cursor.description
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here are all the schemas in database {database_name}: {description} {schemas}",
                    )
                ]

            elif name == "list_databases":
                cursor = snowflake_client.cursor()
                cursor.execute("SHOW DATABASES")
                databases = cursor.fetchall()
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here are all the databases: {databases}",
                    )
                ]

            elif name == "create_table":
                if not all(k in arguments for k in ["table_name", "columns"]):
                    raise ValueError(
                        "Missing required parameters: table_name and columns"
                    )

                table_name = arguments["table_name"]
                columns = arguments["columns"]
                schema_name = arguments.get("schema_name", "PUBLIC")
                database_name = arguments.get("database_name")

                # Build the create table query
                query = f"CREATE TABLE {database_name}.{schema_name}.{table_name} ({columns})"

                try:
                    cursor = snowflake_client.cursor()
                    cursor.execute(query)
                    cursor.close()

                    return [
                        types.TextContent(
                            type="text", text=f"Table {table_name} created successfully"
                        )
                    ]
                except Exception as e:
                    error_message = f"Error creating table: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "list_tables":
                database_name = arguments["database_name"]
                cursor = snowflake_client.cursor()
                cursor.execute(f"SHOW TABLES IN DATABASE {database_name}")
                tables = cursor.fetchall()
                description = cursor.description
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here are all the tables in database {database_name}: {description} {tables}",
                    )
                ]

            elif name == "describe_table":
                table_name = arguments["table_name"]
                database_name = arguments["database_name"]
                schema_name = arguments.get("schema_name", "PUBLIC")

                cursor = snowflake_client.cursor()
                cursor.execute(
                    f"DESCRIBE TABLE {database_name}.{schema_name}.{table_name}"
                )
                data = cursor.fetchall()
                description = cursor.description

                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here is the description of the table {table_name}: {description} {data}",
                    )
                ]

            elif name == "create_warehouse":
                warehouse_name = arguments["warehouse_name"]
                cursor = snowflake_client.cursor()
                cursor.execute(f"CREATE WAREHOUSE {warehouse_name}")
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Warehouse {warehouse_name} created successfully",
                    )
                ]

            elif name == "list_warehouses":
                cursor = snowflake_client.cursor()
                cursor.execute("SHOW WAREHOUSES")
                warehouses = cursor.fetchall()
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here are all the warehouses: {warehouses}",
                    )
                ]

            elif name == "execute_query":
                query = arguments["query"]
                warehouse = arguments.get("warehouse")

                cursor = snowflake_client.cursor()

                # Set the warehouse before executing the query
                cursor.execute("USE ROLE SYSADMIN")
                cursor.execute(f"USE WAREHOUSE {warehouse}")
                cursor.execute(query)
                result = cursor.fetchall()
                description = cursor.description
                cursor.close()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Here is the result of the query: {result} {description}",
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(
                f"Error calling Snowflake API: {e} on line {e.__traceback__.tb_lineno}"
            )
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
        server_name="snowflake-server",
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
