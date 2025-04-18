import os
import sys
from pathlib import Path
import json
import logging
import snowflake.connector

from mcp.types import TextContent, Tool
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.utils.snowflake.util import (
    get_snowflake_credentials,
    authenticate_and_save_snowflake_credentials,
)

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id, api_key=None):
    server = Server("snowflake-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_database",
                description="Create a new database in Snowflake",
                inputSchema={
                    "type": "object",
                    "properties": {"db_name": {"type": "string"}},
                    "required": ["db_name"],
                },
            ),
            Tool(
                name="list_databases",
                description="List all databases in Snowflake",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="create_table",
                description="Create a table in a specified database and schema",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string"},
                        "warehouse_name": {"type": "string"},
                        "schema_name": {"type": "string", "default": "PUBLIC"},
                        "table_name": {"type": "string"},
                        "columns": {"type": "string"},
                    },
                    "required": ["database_name", "table_name", "columns"],
                },
            ),
            Tool(
                name="list_tables",
                description="List all tables in a database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string"},
                        "warehouse_name": {"type": "string"},
                    },
                    "required": ["database_name"],
                },
            ),
            Tool(
                name="describe_table",
                description="Describe structure of a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string"},
                        "warehouse_name": {"type": "string"},
                        "schema_name": {"type": "string", "default": "PUBLIC"},
                        "table_name": {"type": "string"},
                    },
                    "required": ["database_name", "table_name"],
                },
            ),
            Tool(
                name="list_warehouses",
                description="List all warehouses",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="create_warehouse",
                description="Create a new warehouse",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "warehouse_name": {"type": "string"},
                        "warehouse_size": {"type": "string", "default": "X-SMALL"},
                        "auto_suspend": {"type": "integer", "default": 300},
                        "auto_resume": {"type": "boolean", "default": True},
                    },
                    "required": ["warehouse_name"],
                },
            ),
            Tool(
                name="execute_query",
                description="Execute a SQL query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database_name": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["database_name", "query"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(f"Tool call: {name} with args: {arguments}")
        credentials = get_snowflake_credentials(server.user_id, server.api_key)

        conn = snowflake.connector.connect(
            user=credentials["username"],
            password=credentials["password"],
            account=credentials["account"],
            client_session_keep_alive=True,
        )
        cursor = conn.cursor()

        try:
            if arguments is None:
                arguments = {}

            db = arguments.get("database_name")
            if db:
                cursor.execute(f"USE DATABASE {db}")

            if name == "create_database":
                cursor.execute(f"CREATE DATABASE {arguments['db_name']}")
                return [TextContent(type="text", text="Database created successfully")]

            elif name == "list_databases":
                cursor.execute("SHOW DATABASES")
                return [TextContent(type="text", text=str(cursor.fetchall()))]

            elif name == "create_table":
                schema = arguments.get("schema_name", "PUBLIC")
                query = f"CREATE TABLE {schema}.{arguments['table_name']} ({arguments['columns']})"
                cursor.execute(query)
                return [TextContent(type="text", text="Table created successfully")]

            elif name == "list_tables":
                cursor.execute("SHOW TABLES")
                return [TextContent(type="text", text=str(cursor.fetchall()))]

            elif name == "describe_table":
                schema = arguments.get("schema_name", "PUBLIC")
                cursor.execute(f"DESCRIBE TABLE {schema}.{arguments['table_name']}")
                return [TextContent(type="text", text=str(cursor.fetchall()))]

            elif name == "list_warehouses":
                cursor.execute("SHOW WAREHOUSES")
                return [TextContent(type="text", text=str(cursor.fetchall()))]

            elif name == "create_warehouse":
                cursor.execute(
                    f"""
                    CREATE WAREHOUSE IF NOT EXISTS {arguments['warehouse_name']} 
                    WITH WAREHOUSE_SIZE = '{arguments.get('warehouse_size', 'X-SMALL')}'
                    AUTO_SUSPEND = {arguments.get('auto_suspend', 300)}
                    AUTO_RESUME = {'TRUE' if arguments.get('auto_resume', True) else 'FALSE'}
                    """
                )
                return [TextContent(type="text", text="Warehouse created successfully")]

            elif name == "execute_query":
                cursor.execute(arguments["query"])
                return [TextContent(type="text", text=str(cursor.fetchall()))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(
                f"Error executing tool {name}: {str(e)} {e.__traceback__.tb_lineno}"
            )
            return [TextContent(type="text", text=str(e))]

        finally:
            cursor.close()
            conn.close()

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="snowflake-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_snowflake_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
