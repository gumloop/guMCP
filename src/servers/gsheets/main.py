import os
import sys
from typing import Optional

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

"""
Main entry point for the Google Sheets server integration.

This module handles:
1) Google OAuth authentication and credential handling.
2) Creation of a guMCP server exposing tools to interact with the Sheets API.
3) A simple CLI flow for local authentication.
"""

import base64
import logging
from pathlib import Path

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re

from src.utils.google.util import authenticate_and_save_credentials
from src.auth.factory import create_auth_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gsheets-server")

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def extract_spreadsheet_id(sheet_url: str) -> str:
    """Extracts the spreadsheetId from a Google Sheets URL.

    Args:
        sheet_url (str): The full URL of the Google Sheets.

    Returns:
        str: The extracted spreadsheet ID.

    Raises:
        ValueError: If the URL is invalid or ID is not found.
    """
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Google Sheets URL: could not extract spreadsheetId")


async def get_credentials(user_id, api_key=None):
    """Get credentials for the specified user

    Args:
        user_id (str): The identifier of the user whose credentials are needed.
        api_key (Optional[str]): Optional API key for different environments.

    Returns:
        Credentials: The Google OAuth2 credentials for the specified user.

    Raises:
        ValueError: If no valid credentials can be found.
    """
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    def handle_missing_credentials():
        error_str = f"Credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += "Please run with 'auth' argument first."
        logging.error(error_str)
        raise ValueError(f"Credentials not found for user {user_id}")

    if not credentials_data:
        handle_missing_credentials()

    token = credentials_data.get("token")
    if token:
        return Credentials.from_authorized_user_info(credentials_data)

    # If the auth client doesn't return key 'token', but instead returns 'access_token',
    # assume that refreshing is taken care of on the auth client side
    token = credentials_data.get("access_token")
    if token:
        return Credentials(token=token)

    handle_missing_credentials()


async def create_sheets_service(user_id, api_key=None):
    """Create a new Sheets service instance for this request

    Args:
        user_id (str): The identifier of the user for whom the service is created.
        api_key (Optional[str]): Optional API key if needed.

    Returns:
        googleapiclient.discovery.Resource: Authorized Sheets API client.
    """
    credentials = await get_credentials(user_id, api_key=api_key)
    return build("sheets", "v4", credentials=credentials)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context

    Args:
        user_id (str): The identifier of the user for this server session.
        api_key (Optional[str]): Optional API key for server context.

    Returns:
        Server: An instance of the Server class configured for Google Sheets.
    """
    server = Server("gsheets-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create-sheet",
                description="Create a new Google Sheets",
                inputSchema={
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                    "required": ["title"],
                },
            ),
            types.Tool(
                name="get-spreadsheet-info",
                description="Get spreadsheet metadata",
                inputSchema={
                    "type": "object",
                    "properties": {"spreadsheet_url": {"type": "string"}},
                    "required": ["spreadsheet_url"],
                },
            ),
            types.Tool(
                name="get-sheet-names",
                description="List sheet names in spreadsheet",
                inputSchema={
                    "type": "object",
                    "properties": {"spreadsheet_url": {"type": "string"}},
                    "required": ["spreadsheet_url"],
                },
            ),
            types.Tool(
                name="batch-get",
                description="Get values from multiple ranges",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {"type": "string"},
                        "ranges": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["spreadsheet_url", "ranges"],
                },
            ),
            types.Tool(
                name="batch-update",
                description="Update values in multiple ranges",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {"type": "string"},
                        "data": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["spreadsheet_url", "data"],
                },
            ),
            types.Tool(
                name="append-values",
                description="Append values to a sheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {"type": "string"},
                        "range": {"type": "string"},
                        "values": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    "required": ["spreadsheet_url", "range", "values"],
                },
            ),
            types.Tool(
                name="lookup-row",
                description="Find a row by value in a column",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {"type": "string"},
                        "range": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["spreadsheet_url", "range", "value"],
                },
            ),
            types.Tool(
                name="clear-values",
                description="Clear a sheet range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {"type": "string"},
                        "range": {"type": "string"},
                    },
                    "required": ["spreadsheet_url", "range"],
                },
            ),
            types.Tool(
                name="copy-sheet",
                description="Copy a sheet from one spreadsheet to another",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_spreadsheet_id": {"type": "string"},
                        "source_sheet_id": {"type": "integer"},
                        "destination_spreadsheet_id": {"type": "string"},
                    },
                    "required": [
                        "source_spreadsheet_id",
                        "source_sheet_id",
                        "destination_spreadsheet_id",
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Dispatch and handle tool execution

        Args:
            name (str): The name of the tool to call.
            arguments (dict | None): The arguments required by the tool.

        Returns:
            list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
                The resulting content from the executed tool.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        service = await create_sheets_service(server.user_id, server.api_key)

        if "spreadsheet_url" in arguments:
            arguments["spreadsheet_id"] = extract_spreadsheet_id(
                arguments["spreadsheet_url"]
            )

        if name == "create-sheet":
            title = arguments.get("title", "New Spreadsheet")
            body = {"properties": {"title": title}}
            response = service.spreadsheets().create(body=body).execute()
            sheet_url = (
                f"https://docs.google.com/spreadsheets/d/{response['spreadsheetId']}"
            )
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Created new spreadsheet: {response['properties']['title']}\nURL: {sheet_url}"
                    ),
                )
            ]

        if name == "get-spreadsheet-info":
            spreadsheet_id = arguments["spreadsheet_id"]
            info = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            return [types.TextContent(type="text", text=str(info))]

        if name == "get-sheet-names":
            spreadsheet_id = arguments["spreadsheet_id"]
            info = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            names = [s["properties"]["title"] for s in info["sheets"]]
            return [types.TextContent(type="text", text="\n".join(names))]

        if name == "batch-get":
            spreadsheet_id = arguments["spreadsheet_id"]
            result = (
                service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=spreadsheet_id, ranges=arguments["ranges"])
                .execute()
            )
            return [types.TextContent(type="text", text=str(result))]

        if name == "batch-update":
            spreadsheet_id = arguments["spreadsheet_id"]
            body = {"valueInputOption": "RAW", "data": arguments["data"]}
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
            return [types.TextContent(type="text", text="Batch update successful.")]

        if name == "append-values":
            spreadsheet_id = arguments["spreadsheet_id"]
            result = (
                service.spreadsheets()
                .values()
                .append(
                    spreadsheetId=spreadsheet_id,
                    range=arguments["range"],
                    valueInputOption="RAW",
                    body={"values": arguments["values"]},
                )
                .execute()
            )
            updates = result.get("updates", {})
            return [
                types.TextContent(
                    type="text",
                    text=f"Appended {updates.get('updatedRows', '?')} rows.",
                )
            ]

        if name == "lookup-row":
            spreadsheet_id = arguments["spreadsheet_id"]
            values = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=arguments["range"])
                .execute()
                .get("values", [])
            )
            for row in values:
                if arguments["value"] in row:
                    return [types.TextContent(type="text", text=f"Found row: {row}")]
            return [types.TextContent(type="text", text="Value not found.")]

        if name == "clear-values":
            spreadsheet_id = arguments["spreadsheet_id"]
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=arguments["range"], body={}
            ).execute()
            return [types.TextContent(type="text", text="Range cleared successfully.")]

        if name == "copy-sheet":
            response = (
                service.spreadsheets()
                .sheets()
                .copyTo(
                    spreadsheetId=arguments["source_spreadsheet_id"],
                    sheetId=arguments["source_sheet_id"],
                    body={
                        "destinationSpreadsheetId": arguments[
                            "destination_spreadsheet_id"
                        ]
                    },
                )
                .execute()
            )
            dest_id = response.get("spreadsheetId", "")
            return [
                types.TextContent(
                    type="text", text=f"Sheet copied to spreadsheet ID: {dest_id}"
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server

    Args:
        server_instance (Server): The server instance to configure.

    Returns:
        InitializationOptions: Initialization configuration for guMCP.
    """
    return InitializationOptions(
        server_name="gsheets-server",
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
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
