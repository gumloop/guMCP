import os
import sys
from typing import Optional, Iterable

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
import json

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

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
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",  # Add drive.readonly scope for listing files
]


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
    """Get credentials for the specified user without creating a service

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
            error_str += " Please run with 'auth' argument first."
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

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Google Sheets resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        try:
            # Get credentials directly instead of trying to extract from service
            credentials = await get_credentials(server.user_id, api_key=server.api_key)

            # Create Drive service with these credentials
            drive_service = build("drive", "v3", credentials=credentials)

            resources = []
            # Set up pagination parameters
            page_token = cursor
            page_size = 50
            query = "mimeType='application/vnd.google-apps.spreadsheet'"

            # Get spreadsheets from Drive
            response = (
                drive_service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, description, webViewLink, createdTime, modifiedTime)",
                    pageToken=page_token,
                    pageSize=page_size,
                )
                .execute()
            )

            spreadsheets = response.get("files", [])
            next_cursor = response.get("nextPageToken")

            # Create resource objects for each spreadsheet
            for sheet in spreadsheets:
                sheet_id = sheet.get("id")
                sheet_name = sheet.get("name", "Untitled Spreadsheet")
                sheet_description = sheet.get(
                    "description", f"Google Sheets document: {sheet_name}"
                )

                resource = Resource(
                    uri=f"gsheets://spreadsheet/{sheet_id}",
                    mimeType="application/vnd.google-apps.spreadsheet",
                    name=sheet_name,
                    description=sheet_description,
                    required_scopes=SCOPES,
                )
                resources.append(resource)

            return resources

        except Exception as e:
            logger.error(f"Error listing Google Sheets resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read resources from Google Sheets"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        try:
            # Get credentials directly
            credentials = await get_credentials(server.user_id, api_key=server.api_key)
            service = build("sheets", "v4", credentials=credentials)

            uri_str = str(uri)
            if not uri_str.startswith("gsheets://"):
                raise ValueError(f"Invalid Google Sheets URI: {uri_str}")

            parts = uri_str.replace("gsheets://", "").split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid Google Sheets URI format: {uri_str}")

            resource_type, resource_id = parts

            if resource_type == "spreadsheet":
                # Get basic spreadsheet info
                spreadsheet = (
                    service.spreadsheets()
                    .get(spreadsheetId=resource_id, includeGridData=False)
                    .execute()
                )

                # Get sheet names
                sheet_names = [
                    sheet["properties"]["title"]
                    for sheet in spreadsheet.get("sheets", [])
                ]

                # Get a sample of data from the first few sheets
                sheets_data = []
                for i, sheet_name in enumerate(
                    sheet_names[:3]
                ):  # Limit to first 3 sheets
                    range_name = (
                        f"'{sheet_name}'!A1:J10"  # Sample of first 10 rows, 10 columns
                    )
                    result = (
                        service.spreadsheets()
                        .values()
                        .get(
                            spreadsheetId=resource_id,
                            range=range_name,
                            valueRenderOption="FORMATTED_VALUE",
                        )
                        .execute()
                    )

                    values = result.get("values", [])
                    sheets_data.append(
                        {"sheet_name": sheet_name, "sample_data": values}
                    )

                # Combine the metadata with sample data
                resource_data = {
                    "spreadsheet_id": resource_id,
                    "title": spreadsheet.get("properties", {}).get("title", "Untitled"),
                    "url": f"https://docs.google.com/spreadsheets/d/{resource_id}",
                    "sheets": sheet_names,
                    "sample_data": sheets_data,
                }

                return [
                    ReadResourceContents(
                        content=json.dumps(resource_data, indent=2),
                        mime_type="application/json",
                    )
                ]
            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading Google Sheets resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create-sheet",
                description="Create a new Google Sheets",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the new spreadsheet",
                        },
                        "sheets": {
                            "type": "array",
                            "description": "The sheets that should be created with the spreadsheet (optional)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {
                                        "type": "string",
                                        "description": "The title of the sheet",
                                    }
                                },
                            },
                        },
                        "locale": {
                            "type": "string",
                            "description": "The locale of the new spreadsheet (e.g., 'en_US') (optional)",
                        },
                        "timeZone": {
                            "type": "string",
                            "description": "The time zone of the new spreadsheet (e.g., 'America/New_York') (optional)",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for the spreadsheet (optional)",
                        },
                    },
                    "required": ["title"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly created spreadsheet including its ID, properties, sheets, and URLs",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "properties": {"title": "My Spreadsheet", "locale": "en_US", "timeZone": "Etc/GMT"}, "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "sheetType": "GRID"}}], "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/1abc123XYZ/edit", "url": "https://docs.google.com/spreadsheets/d/1abc123XYZ"}'
                    ],
                },
            ),
            types.Tool(
                name="get-spreadsheet-info",
                description="Get spreadsheet metadata",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "include_grid_data": {
                            "type": "boolean",
                            "description": "Whether to include grid data in the response (optional)",
                        },
                        "ranges": {
                            "type": "array",
                            "description": "The ranges to retrieve from the spreadsheet (optional)",
                            "items": {"type": "string"},
                        },
                        "include_filter_views": {
                            "type": "boolean",
                            "description": "Whether to include filter views in the response (optional)",
                        },
                    },
                    "required": ["spreadsheet_url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed metadata about the spreadsheet including ID, properties, and sheets",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "properties": {"title": "My Spreadsheet", "locale": "en_US", "timeZone": "Etc/GMT"}, "sheets": [{"properties": {"sheetId": 0, "title": "Sheet1", "index": 0, "sheetType": "GRID", "gridProperties": {"rowCount": 1000, "columnCount": 26}}}], "spreadsheetUrl": "https://docs.google.com/spreadsheets/d/1abc123XYZ/edit"}'
                    ],
                },
            ),
            types.Tool(
                name="get-sheet-names",
                description="List sheet names in spreadsheet",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        }
                    },
                    "required": ["spreadsheet_url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of sheet names in the spreadsheet",
                    "examples": ['["Sheet1", "Sheet2", "Data"]'],
                },
            ),
            types.Tool(
                name="batch-get",
                description="Get values from multiple ranges",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "ranges": {
                            "type": "array",
                            "description": "The ranges to retrieve from the spreadsheet (e.g. 'Sheet1!A1:C10')",
                            "items": {"type": "string"},
                        },
                        "major_dimension": {
                            "type": "string",
                            "description": "The major dimension of the values (optional, default: 'ROWS')",
                            "enum": ["ROWS", "COLUMNS"],
                        },
                        "value_render_option": {
                            "type": "string",
                            "description": "How values should be rendered in the output (optional)",
                            "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                        },
                        "date_time_render_option": {
                            "type": "string",
                            "description": "How dates, times, and durations should be represented (optional)",
                            "enum": ["SERIAL_NUMBER", "FORMATTED_STRING"],
                        },
                    },
                    "required": ["spreadsheet_url", "ranges"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Values from the requested ranges in the spreadsheet",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "valueRanges": [{"range": "Sheet1!A1:C1", "majorDimension": "ROWS", "values": [["Value1", "Value2", "Value3"]]}]}'
                    ],
                },
            ),
            types.Tool(
                name="batch-update",
                description="Update values in multiple ranges",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "data": {
                            "type": "array",
                            "description": "The data to update in the spreadsheet",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "range": {
                                        "type": "string",
                                        "description": "The range to update (e.g. 'Sheet1!A1:C10')",
                                    },
                                    "values": {
                                        "type": "array",
                                        "description": "The values to update",
                                        "items": {"type": "array", "items": {}},
                                    },
                                    "majorDimension": {
                                        "type": "string",
                                        "description": "The major dimension of the values (optional, default: 'ROWS')",
                                        "enum": ["ROWS", "COLUMNS"],
                                    },
                                },
                                "required": ["range", "values"],
                            },
                        },
                        "value_input_option": {
                            "type": "string",
                            "description": "How the input data should be interpreted (optional, default: 'RAW')",
                            "enum": ["RAW", "USER_ENTERED"],
                        },
                        "include_values_in_response": {
                            "type": "boolean",
                            "description": "Whether to include values in the response (optional)",
                        },
                        "response_value_render_option": {
                            "type": "string",
                            "description": "How values should be rendered in the response (optional)",
                            "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                        },
                        "response_date_time_render_option": {
                            "type": "string",
                            "description": "How dates, times, and durations should be represented in the response (optional)",
                            "enum": ["SERIAL_NUMBER", "FORMATTED_STRING"],
                        },
                    },
                    "required": ["spreadsheet_url", "data"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Results of the batch update operation including total cells updated",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "totalUpdatedRows": 2, "totalUpdatedColumns": 3, "totalUpdatedCells": 6, "totalUpdatedSheets": 1}'
                    ],
                },
            ),
            types.Tool(
                name="append-values",
                description="Append values to a sheet",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "range": {
                            "type": "string",
                            "description": "The range to append to (e.g. 'Sheet1!A1')",
                        },
                        "values": {
                            "type": "array",
                            "description": "The values to append",
                            "items": {"type": "array", "items": {}},
                        },
                        "value_input_option": {
                            "type": "string",
                            "description": "How the input data should be interpreted (optional, default: 'RAW')",
                            "enum": ["RAW", "USER_ENTERED"],
                        },
                        "insert_data_option": {
                            "type": "string",
                            "description": "How the input data should be inserted (optional)",
                            "enum": ["OVERWRITE", "INSERT_ROWS"],
                        },
                        "include_values_in_response": {
                            "type": "boolean",
                            "description": "Whether to include values in the response (optional)",
                        },
                        "response_value_render_option": {
                            "type": "string",
                            "description": "How values should be rendered in the response (optional)",
                            "enum": ["FORMATTED_VALUE", "UNFORMATTED_VALUE", "FORMULA"],
                        },
                        "response_date_time_render_option": {
                            "type": "string",
                            "description": "How dates, times, and durations should be represented in the response (optional)",
                            "enum": ["SERIAL_NUMBER", "FORMATTED_STRING"],
                        },
                    },
                    "required": ["spreadsheet_url", "range", "values"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Results of the append operation including the updated range and cell counts",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "updates": {"spreadsheetId": "1abc123XYZ", "updatedRange": "Sheet1!A1:C1", "updatedRows": 1, "updatedColumns": 3, "updatedCells": 3}}'
                    ],
                },
            ),
            types.Tool(
                name="lookup-row",
                description="Find a row by value in a column",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "range": {
                            "type": "string",
                            "description": "The range to search within (e.g. 'Sheet1!A1:C10')",
                        },
                        "value": {
                            "type": "string",
                            "description": "The value to search for",
                        },
                        "column_index": {
                            "type": "integer",
                            "description": "The specific column index to search within (optional, 0-based)",
                        },
                        "exact_match": {
                            "type": "boolean",
                            "description": "Whether to require an exact match (optional, default: true)",
                        },
                    },
                    "required": ["spreadsheet_url", "range", "value"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Results of the row lookup operation, including whether the value was found and the matching row data",
                    "examples": [
                        '{"found": true, "row": ["Header1", "Header2", "Header3"], "all_values": {"range": "Sheet1!A1:C10", "majorDimension": "ROWS", "values": [["Header1", "Header2", "Header3"], ["Value1", "Value2", "Value3"]]}}'
                    ],
                },
            ),
            types.Tool(
                name="clear-values",
                description="Clear a sheet range",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spreadsheet_url": {
                            "type": "string",
                            "description": "The URL of the Google Sheets document",
                        },
                        "range": {
                            "type": "string",
                            "description": "The range to clear (e.g. 'Sheet1!A1:C10')",
                        },
                    },
                    "required": ["spreadsheet_url", "range"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Results of the clear operation",
                    "examples": [
                        '{"spreadsheetId": "1abc123XYZ", "clearedRange": "Sheet1!A10:C10"}'
                    ],
                },
            ),
            types.Tool(
                name="copy-sheet",
                description="Copy a sheet from one spreadsheet to another",
                required_scopes=SCOPES,
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the spreadsheet containing the sheet to copy",
                        },
                        "source_sheet_id": {
                            "type": "integer",
                            "description": "The ID of the sheet to copy",
                        },
                        "destination_spreadsheet_id": {
                            "type": "string",
                            "description": "The ID of the spreadsheet to copy the sheet to",
                        },
                        "new_sheet_name": {
                            "type": "string",
                            "description": "Optional name for the copied sheet",
                        },
                        "insert_sheet_index": {
                            "type": "integer",
                            "description": "The zero-based index where the new sheet should be inserted (optional)",
                        },
                    },
                    "required": [
                        "source_spreadsheet_id",
                        "source_sheet_id",
                        "destination_spreadsheet_id",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the newly copied sheet",
                    "examples": [
                        '{"sheetId": 1234567890, "title": "Copy of Sheet1", "index": 1, "sheetType": "GRID", "gridProperties": {"rowCount": 1000, "columnCount": 26}}'
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

        if arguments is None:
            arguments = {}

        if "spreadsheet_url" in arguments:
            arguments["spreadsheet_id"] = extract_spreadsheet_id(
                arguments["spreadsheet_url"]
            )

        if name == "create-sheet":
            title = arguments.get("title", "New Spreadsheet")

            # Prepare the request body with required parameters
            body = {"properties": {"title": title}}

            # Add optional parameters to the properties dictionary
            for prop in ["locale", "timeZone"]:
                if prop in arguments:
                    body["properties"][prop] = arguments[prop]

            # Add other top-level parameters
            if "sheets" in arguments:
                body["sheets"] = arguments["sheets"]

            # Merge any additional properties
            if "properties" in arguments:
                body["properties"].update(arguments["properties"])

            response = service.spreadsheets().create(body=body).execute()
            sheet_url = (
                f"https://docs.google.com/spreadsheets/d/{response['spreadsheetId']}"
            )
            response["url"] = sheet_url
            return [types.TextContent(type="text", text=json.dumps(response))]

        if name == "get-spreadsheet-info":
            spreadsheet_id = arguments["spreadsheet_id"]

            params = {
                "spreadsheetId": spreadsheet_id,
                **{
                    k: v
                    for k, v in {
                        "includeGridData": arguments.get("include_grid_data"),
                        "ranges": arguments.get("ranges"),
                    }.items()
                    if v is not None
                },
            }

            info = service.spreadsheets().get(**params).execute()
            return [types.TextContent(type="text", text=json.dumps(info))]

        if name == "get-sheet-names":
            spreadsheet_id = arguments["spreadsheet_id"]
            info = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            names = [s["properties"]["title"] for s in info["sheets"]]
            return [types.TextContent(type="text", text=json.dumps(names))]

        if name == "batch-get":
            spreadsheet_id = arguments["spreadsheet_id"]

            params = {
                "spreadsheetId": spreadsheet_id,
                "ranges": arguments["ranges"],
                **{
                    k: v
                    for k, v in {
                        "majorDimension": arguments.get("major_dimension"),
                        "valueRenderOption": arguments.get("value_render_option"),
                        "dateTimeRenderOption": arguments.get(
                            "date_time_render_option"
                        ),
                    }.items()
                    if v is not None
                },
            }

            result = service.spreadsheets().values().batchGet(**params).execute()
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "batch-update":
            spreadsheet_id = arguments["spreadsheet_id"]

            # Prepare the request body
            body = {
                "valueInputOption": arguments.get("value_input_option", "RAW"),
                "data": arguments["data"],
                **{
                    k: v
                    for k, v in {
                        "includeValuesInResponse": arguments.get(
                            "include_values_in_response"
                        ),
                        "responseValueRenderOption": arguments.get(
                            "response_value_render_option"
                        ),
                        "responseDateTimeRenderOption": arguments.get(
                            "response_date_time_render_option"
                        ),
                    }.items()
                    if v is not None
                },
            }

            result = (
                service.spreadsheets()
                .values()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "append-values":
            spreadsheet_id = arguments["spreadsheet_id"]

            # Prepare parameters
            params = {
                "spreadsheetId": spreadsheet_id,
                "range": arguments["range"],
                "valueInputOption": arguments.get("value_input_option", "RAW"),
                "body": {"values": arguments["values"]},
                **{
                    k: v
                    for k, v in {
                        "insertDataOption": arguments.get("insert_data_option"),
                        "includeValuesInResponse": arguments.get(
                            "include_values_in_response"
                        ),
                        "responseValueRenderOption": arguments.get(
                            "response_value_render_option"
                        ),
                        "responseDateTimeRenderOption": arguments.get(
                            "response_date_time_render_option"
                        ),
                    }.items()
                    if v is not None
                },
            }

            result = service.spreadsheets().values().append(**params).execute()
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "lookup-row":
            spreadsheet_id = arguments["spreadsheet_id"]

            # Get the values from the specified range
            values_response = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=arguments["range"])
                .execute()
            )

            values = values_response.get("values", [])
            found_row = None

            # Search for the value in the rows
            search_value = arguments["value"]
            column_index = arguments.get("column_index")
            exact_match = arguments.get("exact_match", True)

            for row in values:
                # If column_index is specified, search only in that column
                if column_index is not None and 0 <= column_index < len(row):
                    cell_value = row[column_index]
                    if (exact_match and cell_value == search_value) or (
                        not exact_match and search_value in str(cell_value)
                    ):
                        found_row = row
                        break
                # Otherwise search in all columns
                else:
                    if exact_match:
                        if search_value in row:
                            found_row = row
                            break
                    else:
                        # For non-exact match, check if search_value is a substring of any cell
                        for cell in row:
                            if search_value in str(cell):
                                found_row = row
                                break
                        if found_row:
                            break

            result = {
                "found": found_row is not None,
                "row": found_row,
                "all_values": values_response,
            }
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "clear-values":
            spreadsheet_id = arguments["spreadsheet_id"]
            result = (
                service.spreadsheets()
                .values()
                .clear(spreadsheetId=spreadsheet_id, range=arguments["range"], body={})
                .execute()
            )
            return [types.TextContent(type="text", text=json.dumps(result))]

        if name == "copy-sheet":
            # Prepare the request body
            body = {
                "destinationSpreadsheetId": arguments["destination_spreadsheet_id"],
                **{
                    k: v
                    for k, v in {
                        "newSheetName": arguments.get("new_sheet_name"),
                        "insertSheetIndex": arguments.get("insert_sheet_index"),
                    }.items()
                    if v is not None
                },
            }

            result = (
                service.spreadsheets()
                .sheets()
                .copyTo(
                    spreadsheetId=arguments["source_spreadsheet_id"],
                    sheetId=arguments["source_sheet_id"],
                    body=body,
                )
                .execute()
            )
            return [types.TextContent(type="text", text=json.dumps(result))]

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
