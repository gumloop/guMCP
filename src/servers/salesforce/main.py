import json
import os
from pathlib import Path
import logging
import sys
from simple_salesforce import Salesforce

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from src.utils.salesforce.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name

SCOPES = [  # Basic web integration capabilities
    "full",
    "api",
    "id",
    "profile",
    "email",
    "address",
    "phone",
    "web",
    "refresh_token",
    "offline_access",
    "openid",
    "custom_permissions",
    # Full access to all resources the user has access to
]


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_salesforce_token(user_id, api_key=None):
    """
    This function is used to get the Salesforce access token for a specific user.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        str: The access token to authenticate with the Snowflake API.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key)
    return token


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Salesforce MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Snowflake tools registered.
    """
    server = Server("salesforce-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Salesforce API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="soql_query",
                description="Executes a SOQL query to retrieve Salesforce records with support for relationships and complex filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SOQL query to execute (e.g., 'SELECT Id, Name FROM Account WHERE Industry = \\'Technology\\'')",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="sosl_search",
                description="Performs a text-based search across multiple Salesforce objects using SOSL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "The SOSL search string (e.g., 'FIND {Cloud} IN ALL FIELDS RETURNING Account, Opportunity')",
                        },
                    },
                    "required": ["search"],
                },
            ),
            types.Tool(
                name="describe_object",
                description="Retrieves detailed metadata about a Salesforce object including fields, relationships, and permissions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact', 'Custom_Object__c')",
                        },
                    },
                    "required": ["object_name"],
                },
            ),
            types.Tool(
                name="get_record",
                description="Retrieves a specific Salesforce record by ID with all accessible fields",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific fields to retrieve (retrieves all accessible fields if not specified)",
                        },
                    },
                    "required": ["object_name", "record_id"],
                },
            ),
            types.Tool(
                name="create_record",
                description="Creates a new record in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "data": {
                            "type": "object",
                            "description": "Field data for the new record as key-value pairs",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["object_name", "data"],
                },
            ),
            types.Tool(
                name="update_record",
                description="Updates an existing Salesforce record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record to update",
                        },
                        "data": {
                            "type": "object",
                            "description": "Field data to update as key-value pairs",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["object_name", "record_id", "data"],
                },
            ),
            types.Tool(
                name="delete_record",
                description="Deletes a Salesforce record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record to delete",
                        },
                    },
                    "required": ["object_name", "record_id"],
                },
            ),
            types.Tool(
                name="get_org_limits",
                description="Retrieves current organization limits and usage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit_type": {
                            "type": "string",
                            "description": "Optional specific limit to check (e.g., 'DailyApiRequests', 'DataStorageMB')",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Salesforce API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        token = await get_salesforce_token(server.user_id, server.api_key)
        salesforce_client = Salesforce(
            instance_url=token["instance_url"], session_id=token["access_token"]
        )
        if arguments is None:
            arguments = {}

        try:
            if name == "soql_query":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing 'query' argument")

                results = salesforce_client.query_all(query)
                return [
                    types.TextContent(
                        type="text",
                        text=f"SOQL Query Results (JSON):\n{json.dumps(results, indent=2)}",
                    )
                ]
            elif name == "sosl_search":
                search = arguments.get("search")
                if not search:
                    raise ValueError("Missing 'search' argument")

                results = salesforce_client.search(search)
                return [
                    types.TextContent(
                        type="text",
                        text=f"SOSL Search Results (JSON):\n{json.dumps(results, indent=2)}",
                    )
                ]
            elif name == "describe_object":
                object_name = arguments.get("object_name")
                if not object_name:
                    raise ValueError("Missing 'object_name' argument")

                # Get object description
                sf_object = getattr(salesforce_client, object_name)
                describe_result = sf_object.describe()

                # Format field information
                fields_info = []
                for field in describe_result["fields"]:
                    field_info = {
                        "name": field["name"],
                        "label": field["label"],
                        "type": field["type"],
                        "required": not field["nillable"],
                        "updateable": field["updateable"],
                        "createable": field["createable"],
                    }
                    if field["type"] == "picklist":
                        field_info["picklistValues"] = [
                            {"label": pv["label"], "value": pv["value"]}
                            for pv in field["picklistValues"]
                            if pv["active"]
                        ]
                    fields_info.append(field_info)

                return [
                    types.TextContent(
                        type="text",
                        text=f"{object_name} Metadata (JSON):\n{json.dumps(fields_info, indent=2)}",
                    )
                ]
            elif name == "get_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                if not object_name or not record_id:
                    raise ValueError("Missing 'object_name' or 'record_id' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.get(record_id)
                return [
                    types.TextContent(
                        type="text",
                        text=f"{object_name} Record (JSON):\n{json.dumps(results, indent=2)}",
                    )
                ]
            elif name == "create_record":
                object_name = arguments.get("object_name")
                data = arguments.get("data")
                if not object_name or not data:
                    raise ValueError("Missing 'object_name' or 'data' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.create(data)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Create {object_name} Record Result (JSON):\n{json.dumps(results, indent=2)}",
                    )
                ]
            elif name == "update_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                data = arguments.get("data")
                if not object_name or not record_id or not data:
                    raise ValueError(
                        "Missing 'object_name', 'record_id', or 'data' argument"
                    )

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.update(record_id, data)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Update {object_name} Record Result: {results}",
                    )
                ]
            elif name == "delete_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                if not object_name or not record_id:
                    raise ValueError("Missing 'object_name' or 'record_id' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.delete(record_id)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Delete {object_name} Record Result: {results}",
                    )
                ]

            elif name == "get_org_limits":
                limit_type = arguments.get("limit_type")

                # Get all organization limits
                org_limits = salesforce_client.limits()

                # If a specific limit type is requested, filter the results
                if limit_type:
                    if limit_type in org_limits:
                        results = {limit_type: org_limits[limit_type]}
                    else:
                        available_limits = list(org_limits.keys())
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Limit type '{limit_type}' not found. Available limit types: {json.dumps(available_limits, indent=2)}",
                            )
                        ]
                else:
                    results = org_limits

                # Format the results with usage percentages for better readability
                formatted_results = {}
                for key, value in results.items():
                    if (
                        isinstance(value, dict)
                        and "Max" in value
                        and "Remaining" in value
                    ):
                        used = value["Max"] - value["Remaining"]
                        percentage = (
                            (used / value["Max"] * 100) if value["Max"] > 0 else 0
                        )
                        formatted_results[key] = {
                            "Max": value["Max"],
                            "Used": used,
                            "Remaining": value["Remaining"],
                            "UsagePercentage": f"{percentage:.2f}%",
                        }
                    else:
                        formatted_results[key] = value

                return [
                    types.TextContent(
                        type="text",
                        text=f"Organization Limits (JSON):\n{json.dumps(formatted_results, indent=2)}",
                    )
                ]

            raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(
                f"Error calling Salesforce API: {e} on line {e.__traceback__.tb_lineno}"
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
