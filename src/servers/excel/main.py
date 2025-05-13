import os
import sys
import logging
import json
import inspect
from pathlib import Path
from typing import Optional, Iterable

# Add project root and src to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import httpx
from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
    AnyUrl,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.microsoft.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
MICROSOFT_GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
SCOPES = [
    "Files.ReadWrite",
    "Sites.ReadWrite.All",
    "offline_access",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def make_graph_api_request(
    method, endpoint, data=None, params=None, access_token=None, content_type=None
):
    """Make a request to the Microsoft Graph API"""
    if not access_token:
        raise ValueError("Microsoft access token is required")

    url = f"{MICROSOFT_GRAPH_API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": content_type if content_type else "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "post":
                if content_type and content_type != "application/json":
                    response = await client.post(
                        url, content=data, headers=headers, params=params, timeout=60.0
                    )
                else:
                    response = await client.post(
                        url, json=data, headers=headers, params=params, timeout=60.0
                    )
            elif method.lower() == "patch":
                if content_type and content_type != "application/json":
                    response = await client.patch(
                        url, content=data, headers=headers, params=params, timeout=60.0
                    )
                else:
                    response = await client.patch(
                        url, json=data, headers=headers, params=params, timeout=60.0
                    )
            elif method.lower() == "put":
                if content_type and content_type != "application/json":
                    response = await client.put(
                        url, content=data, headers=headers, params=params, timeout=60.0
                    )
                else:
                    response = await client.put(
                        url, json=data, headers=headers, params=params, timeout=60.0
                    )
            elif method.lower() == "delete":
                response = await client.delete(
                    url, headers=headers, params=params, timeout=60.0
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            if response.status_code == 204:  # No content
                return {"success": True, "status_code": 204}
            return response.json()

    except httpx.HTTPStatusError as e:
        error_message = f"Microsoft Graph API error: {e.response.status_code}"
        error_details = {}
        try:
            error_response = e.response.json()
            if "error" in error_response:
                error_details = error_response["error"]
                error_message = f"{error_details.get('code', 'Error')}: {error_details.get('message', 'Unknown error')}"
        except Exception:
            pass

        raise ValueError(error_message)

    except httpx.RequestError as e:
        raise ValueError(f"Failed to connect to Microsoft Graph API: {str(e)}")

    except Exception as e:
        raise ValueError(f"Error communicating with Microsoft Graph API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance for Excel operations"""
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    async def get_microsoft_client():
        """Get Microsoft access token for the current user"""
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return access_token

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Excel files from OneDrive"""
        access_token = await get_microsoft_client()

        try:
            endpoint = "me/drive/root/search(q='.xlsx')"
            query_params = {
                "$top": 50,
                "$select": "id,name,webUrl,lastModifiedDateTime",
                "$orderby": "lastModifiedDateTime desc",
            }

            if cursor:
                query_params["$skiptoken"] = cursor

            result = await make_graph_api_request(
                "get", endpoint, params=query_params, access_token=access_token
            )

            resources = []
            for item in result.get("value", []):
                resources.append(
                    Resource(
                        uri=f"excel://file/{item['id']}",
                        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        name=f"{item['name']}",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error fetching Excel resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read an Excel workbook from OneDrive"""
        access_token = await get_microsoft_client()
        uri_str = str(uri)

        if uri_str.startswith("excel://file/"):
            file_id = uri_str.replace("excel://file/", "")

            try:
                # Get workbook information
                endpoint = f"me/drive/items/{file_id}"
                file_info = await make_graph_api_request(
                    "get", endpoint, access_token=access_token
                )

                # Get worksheets in the workbook
                worksheets_endpoint = f"me/drive/items/{file_id}/workbook/worksheets"
                worksheets_result = await make_graph_api_request(
                    "get", worksheets_endpoint, access_token=access_token
                )

                # Combine file info with worksheet info
                result = {
                    "id": file_info.get("id"),
                    "name": file_info.get("name"),
                    "webUrl": file_info.get("webUrl"),
                    "lastModifiedDateTime": file_info.get("lastModifiedDateTime"),
                    "worksheets": [
                        {
                            "id": ws.get("id"),
                            "name": ws.get("name"),
                            "position": ws.get("position"),
                            "visibility": ws.get("visibility"),
                        }
                        for ws in worksheets_result.get("value", [])
                    ],
                }

                formatted_content = json.dumps(result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            except Exception as e:
                raise ValueError(f"Error reading Excel file: {str(e)}")

        raise ValueError(f"Unsupported resource URI: {uri_str}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Excel"""
        return [
            Tool(
                name="create_workbook",
                description="Create a new Excel workbook in OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the new workbook (will add .xlsx extension if not included)",
                        },
                        "folder_path": {
                            "type": "string",
                            "description": "Path to folder in OneDrive (optional, defaults to root)",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the created Excel workbook including file ID, name, and web URL",
                    "examples": [
                        '{\n  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users(\'user%40example.com\')/drive/root/$entity",\n  "@microsoft.graph.downloadUrl": "https://example.com/download",\n  "id": "1234567890ABC",\n  "name": "Test Workbook.xlsx",\n  "webUrl": "https://onedrive.live.com/edit.aspx?resid=1234567890ABC",\n  "size": 0,\n  "file": {\n    "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"\n  }\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="list_worksheets",
                description="List all worksheets in an Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        }
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of worksheets in the Excel workbook with their properties",
                    "examples": [
                        '{\n  "value": [\n    {\n      "id": "Sheet1",\n      "name": "Sheet1",\n      "position": 0,\n      "visibility": "Visible"\n    },\n    {\n      "id": "Sheet2",\n      "name": "Sheet2",\n      "position": 1,\n      "visibility": "Visible"\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_worksheet",
                description="Add a new worksheet to an Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the new worksheet (optional, Excel will generate a name if not provided)",
                        },
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the newly created worksheet",
                    "examples": [
                        '{\n  "id": "Sheet3",\n  "name": "Test Worksheet-12345",\n  "position": 2,\n  "visibility": "Visible"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="read_worksheet",
                description="Read data from a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet to read",
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range to read (e.g., 'A1:D10'), defaults to used range if not specified",
                        },
                    },
                    "required": ["file_id", "worksheet_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Data from the worksheet with cell values, formulas, and formatting information",
                    "examples": [
                        '{\n  "address": "A1:B3",\n  "values": [\n    ["Header 1", "Header 2"],\n    ["Value 1", "Value 2"],\n    ["Value 3", "Value 4"]\n  ],\n  "formulas": null,\n  "numberFormat": null\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="update_cells",
                description="Update cell values in a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet to update",
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range to update (e.g., 'A1:B2')",
                        },
                        "values": {
                            "type": "array",
                            "items": {"type": "array", "items": {}},
                            "description": "2D array of values to update in the range (rows and columns)",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "range", "values"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of cell update with information about the updated range",
                    "examples": ['{\n  "address": "A1:B3",\n  "updated": true\n}'],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_formula",
                description="Add a formula to a cell in a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "cell": {
                            "type": "string",
                            "description": "Cell reference (e.g., 'A1')",
                        },
                        "formula": {
                            "type": "string",
                            "description": "Excel formula to add (e.g., '=SUM(A1:A10)')",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "cell", "formula"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of formula addition with information about the updated cell",
                    "examples": [
                        '{\n  "address": "C2",\n  "formulaApplied": "=SUM(A2:B2)"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_row",
                description="Add a row to the end of a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "values": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Array of values to add as a new row",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "values"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of row addition with row index and values",
                    "examples": [
                        '{\n  "success": true,\n  "rowAdded": 4,\n  "values": ["New Value 1", "New Value 2"]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_table",
                description="Create a new table in a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the new table",
                        },
                        "range": {
                            "type": "string",
                            "description": "Cell range for the table (e.g., 'A1:D10')",
                        },
                        "has_headers": {
                            "type": "boolean",
                            "description": "Whether the first row contains headers",
                            "default": True,
                        },
                    },
                    "required": ["file_id", "worksheet_name", "range"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the created table including ID, name, and range",
                    "examples": [
                        '{\n  "id": "1",\n  "name": "TestTable-12345",\n  "showHeaders": true,\n  "showTotals": false,\n  "style": "TableStyleMedium2",\n  "worksheet": {\n    "id": "Sheet1",\n    "name": "Sheet1"\n  },\n  "address": "D1:E3"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_table_row",
                description="Add a row to a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to add a row to",
                        },
                        "values": {
                            "type": "object",
                            "description": "Object with key-value pairs for the new row (keys should match table headers)",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "table_name", "values"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the newly added table row",
                    "examples": [
                        '{\n  "index": 3,\n  "values": ["Value 1", "Value 2"]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="find_row",
                description="Find a row by column value",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "column": {
                            "type": "string",
                            "description": "Column name or letter to search in",
                        },
                        "value": {
                            "description": "Value to search for",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "column", "value"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the found row including row index and data",
                    "examples": [
                        '{\n  "found_row": {\n    "Header 1": "Updated Value 1",\n    "Header 2": "Updated Value 2"\n  },\n  "row_index": 2\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="find_or_create_row",
                description="Find a row by column value or create it if not found",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "search_column": {
                            "type": "string",
                            "description": "Column name or letter to search in",
                        },
                        "search_value": {
                            "description": "Value to search for",
                        },
                        "values": {
                            "type": "object",
                            "description": "Object with key-value pairs for the new row if not found",
                        },
                    },
                    "required": [
                        "file_id",
                        "worksheet_name",
                        "search_column",
                        "search_value",
                        "values",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the found or created row including whether it was created",
                    "examples": [
                        '{\n  "row": {\n    "Header 1": "Unique Value-12345",\n    "Header 2": "Associated Value"\n  },\n  "row_index": 4,\n  "created": true\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="update_row",
                description="Update a specific row in a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "row_index": {
                            "type": "integer",
                            "description": "Index of the row to update (1-based)",
                        },
                        "values": {
                            "type": "object",
                            "description": "Object with column-value pairs to update",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "row_index", "values"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the updated row with new values",
                    "examples": [
                        '{\n  "updated": true,\n  "row": {\n    "Header 1": "Updated Value 1",\n    "Header 2": "Updated Value 2"\n  },\n  "row_index": 2\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="delete_worksheet_row",
                description="Delete a row from a worksheet",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet",
                        },
                        "row_index": {
                            "type": "integer",
                            "description": "Index of the row to delete (1-based)",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "row_index"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of row deletion",
                    "examples": [
                        '{\n  "success": true,\n  "message": "Row 4 deleted successfully"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="list_tables",
                description="List all tables in an Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet (optional, if specified will only list tables in this worksheet)",
                        },
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tables in the workbook with their details",
                    "examples": [
                        '{\n  "value": [\n    {\n      "id": "1",\n      "name": "TestTable-12345",\n      "showHeaders": true,\n      "showTotals": false,\n      "style": "TableStyleMedium2",\n      "worksheet": {\n        "id": "Sheet1",\n        "name": "Sheet1"\n      }\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="get_table",
                description="Get table metadata",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to get",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "table_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about the specified table",
                    "examples": [
                        '{\n  "id": "1",\n  "name": "TestTable-12345",\n  "showHeaders": true,\n  "showTotals": false,\n  "style": "TableStyleMedium2",\n  "worksheet": {\n    "id": "Sheet1",\n    "name": "Sheet1"\n  },\n  "address": "D1:E3",\n  "columns": [\n    {\n      "id": "1",\n      "name": "Column1",\n      "index": 0\n    },\n    {\n      "id": "2",\n      "name": "Column2",\n      "index": 1\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="list_table_rows",
                description="List rows in a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "table_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of rows in the table with their values",
                    "examples": [
                        '{\n  "value": [\n    {\n      "index": 0,\n      "values": ["Value 1", "Value 2"]\n    },\n    {\n      "index": 1,\n      "values": ["Value 3", "Value 4"]\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="add_table_column",
                description="Add a column to a table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table",
                        },
                        "column_name": {
                            "type": "string",
                            "description": "Name for the new column",
                        },
                    },
                    "required": [
                        "file_id",
                        "worksheet_name",
                        "table_name",
                        "column_name",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the newly added column",
                    "examples": [
                        '{\n  "id": "3",\n  "name": "NewColumn-12345",\n  "index": 2\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="update_table_column",
                description="Update data in a table column",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table",
                        },
                        "column_name": {
                            "type": "string",
                            "description": "Name of the column to update",
                        },
                        "values": {
                            "type": "array",
                            "items": {},
                            "description": "Array of values for the column",
                        },
                    },
                    "required": [
                        "file_id",
                        "worksheet_name",
                        "table_name",
                        "column_name",
                        "values",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of column update with column information",
                    "examples": [
                        '{\n  "updated": true,\n  "column": {\n    "id": "2",\n    "name": "Column2",\n    "index": 1\n  },\n  "values": ["New Value 1", "New Value 2"]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="delete_table",
                description="Delete a table (data remains, only deletes the table object)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "worksheet_name": {
                            "type": "string",
                            "description": "Name of the worksheet containing the table",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to delete",
                        },
                    },
                    "required": ["file_id", "worksheet_name", "table_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of table deletion",
                    "examples": [
                        '{\n  "success": true,\n  "message": "Table TestTable-12345 deleted successfully"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="download_workbook",
                description="Get a download URL for the workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Download URL for the Excel workbook",
                    "examples": [
                        '{\n  "url": "https://example.com/download/12345",\n  "name": "Test Workbook.xlsx"\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
            Tool(
                name="search_workbooks",
                description="Search for workbooks",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 20,
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search results with matching Excel workbooks",
                    "examples": [
                        '{\n  "value": [\n    {\n      "id": "1234567890ABC",\n      "name": "Test Workbook.xlsx",\n      "webUrl": "https://onedrive.live.com/edit.aspx?resid=1234567890ABC",\n      "lastModifiedDateTime": "2023-06-01T12:00:00Z"\n    },\n    {\n      "id": "0987654321ZYX",\n      "name": "Another Workbook.xlsx",\n      "webUrl": "https://onedrive.live.com/edit.aspx?resid=0987654321ZYX",\n      "lastModifiedDateTime": "2023-05-28T09:30:00Z"\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=["Files.ReadWrite", "offline_access"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Excel"""
        arguments = arguments or {}
        access_token = await get_microsoft_client()

        def prepare_row_values(args):
            """Convert row values to the right format for Excel API"""
            values = args.get("values", {})
            headers = args.get("headers", [])

            if values is None:
                return []

            if isinstance(values, dict) and headers:
                return [values.get(header, "") for header in headers]
            elif isinstance(values, dict):
                return list(values.values())
            elif isinstance(values, list):
                return values
            else:
                return [str(values)]

        async def prepare_add_row_data(args):
            """Prepare data for adding a row"""
            file_id = args.get("file_id")
            worksheet_name = args.get("worksheet_name")

            # Get the used range to determine where to add the row
            used_range_endpoint = f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/usedRange"
            used_range = await make_graph_api_request(
                "get", used_range_endpoint, access_token=access_token
            )

            args["used_range"] = used_range
            args["headers"] = (
                used_range.get("values", [[]])[0] if used_range.get("values") else []
            )
            args["last_row"] = len(used_range.get("values", []))
            args["next_row"] = args["last_row"] + 1

            return args

        def get_add_row_endpoint(args):
            """Generate the endpoint for adding a row to a worksheet"""
            file_id = args.get("file_id")
            worksheet_name = args.get("worksheet_name")
            last_row = args.get("last_row", 0)
            next_row = args.get("next_row", 1)

            # If sheet is empty, start at A1
            if last_row == 0:
                range_param = "A1"
            else:
                row_values = prepare_row_values(args)
                col_count = len(row_values)

                if col_count == 0:
                    return f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/range(address='A{next_row}')"

                # Get the last column letter
                if col_count <= 26:
                    last_col_letter = chr(64 + col_count)
                else:
                    first_char = chr(64 + (col_count // 26))
                    second_char = chr(64 + (col_count % 26))
                    last_col_letter = f"{first_char}{second_char}"

                range_param = f"A{next_row}:{last_col_letter}{next_row}"

            return f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/range(address='{range_param}')"

        async def find_row_by_value(args, result):
            """Find a row by column value"""
            column = args.get("column")
            search_value = args.get("value")

            values = result.get("values", [])
            if not values or len(values) < 2:
                return {"error": "No data found in worksheet or only headers present"}

            # Determine column index
            col_index = None
            headers = values[0]

            # Check if column is a letter (A, B, C, etc.)
            if isinstance(column, str) and len(column) == 1 and column.isalpha():
                col_index = ord(column.upper()) - ord("A")
            else:
                # Try to find column by name
                for i, header in enumerate(headers):
                    if str(header).lower() == str(column).lower():
                        col_index = i
                        break

            if col_index is None or col_index >= len(headers):
                return {"error": f"Column '{column}' not found in worksheet"}

            # Search for the value
            search_value_str = str(search_value).lower()

            for i, row in enumerate(values[1:], 1):
                if col_index < len(row):
                    row_value = (
                        str(row[col_index]).lower()
                        if row[col_index] is not None
                        else ""
                    )
                    if row_value == search_value_str:
                        # Format the result
                        result_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                result_dict[header] = row[i]

                        return {"found_row": result_dict, "row_index": i}

            return {
                "error": f"No row found with value '{search_value}' in column '{column}'"
            }

        async def process_find_or_create(args, result):
            # First try to find the row
            search_column = args.get("search_column")
            search_value = args.get("search_value")

            find_args = {"column": search_column, "value": search_value, **args}

            find_result = await find_row_by_value(find_args, result)

            # If row found, return it
            if "found_row" in find_result:
                return {
                    "row": find_result["found_row"],
                    "row_index": find_result["row_index"],
                    "created": False,
                }

            # Row not found, create it by adding a new row
            values = args.get("values", {})

            # Call add_row endpoint directly
            add_args = await prepare_add_row_data(args)
            endpoint = get_add_row_endpoint(add_args)
            row_values = [
                prepare_row_values(
                    {"values": values, "headers": add_args.get("headers", [])}
                )
            ]

            await make_graph_api_request(
                "patch",
                endpoint,
                data={"values": row_values},
                access_token=access_token,
            )

            return {
                "row": values,
                "row_index": add_args.get("next_row", 0),
                "created": True,
            }

        async def process_update_row(args, result):
            row_index = args.get("row_index")
            values = args.get("values", {})

            # Get the worksheet data
            used_range = result
            headers = (
                used_range.get("values", [[]])[0] if used_range.get("values") else []
            )

            if not headers:
                return {"error": "No headers found in worksheet"}

            # Prepare the update data
            update_data = []

            # Map column names to indices
            header_indices = {}
            for i, header in enumerate(headers):
                header_indices[str(header)] = i

            # Get the row to update
            all_rows = used_range.get("values", [])
            if row_index < 1 or row_index >= len(all_rows):
                return {"error": f"Row index {row_index} is out of range"}

            # Create a copy of the row
            updated_row = list(all_rows[row_index])

            # Update values
            for col_name, value in values.items():
                if col_name in header_indices:
                    col_index = header_indices[col_name]
                    if col_index < len(updated_row):
                        updated_row[col_index] = value

            # Update the row in the spreadsheet
            update_range = (
                f"A{row_index+1}:{chr(65 + len(updated_row) - 1)}{row_index+1}"
            )
            update_endpoint = f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}/range(address='{update_range}')"

            await make_graph_api_request(
                "patch",
                update_endpoint,
                data={"values": [updated_row]},
                access_token=access_token,
            )

            # Format the updated row as a dict
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(updated_row):
                    row_dict[header] = updated_row[i]

            return {"updated": True, "row": row_dict, "row_index": row_index}

        # Define endpoints and their configurations
        endpoints = {
            "create_workbook": {
                "method": "put",
                "endpoint": lambda args: format_create_workbook_endpoint(args),
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "data_transform": lambda args: b"PK\x05\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
                "params_transform": lambda args: {
                    "@microsoft.graph.conflictBehavior": "rename"
                },
            },
            "list_worksheets": {
                "method": "get",
                "endpoint": lambda args: f"me/drive/items/{args.get('file_id')}/workbook/worksheets",
            },
            "add_worksheet": {
                "method": "post",
                "endpoint": lambda args: f"me/drive/items/{args.get('file_id')}/workbook/worksheets",
                "data_transform": lambda args: (
                    {"name": args.get("name")} if "name" in args else {}
                ),
            },
            "read_worksheet": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    + (
                        f"/range(address='{args.get('range')}')"
                        if "range" in args
                        else "/usedRange"
                    )
                ),
            },
            "update_cells": {
                "method": "patch",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/range(address='{args.get('range')}')"
                ),
                "data_transform": lambda args: {"values": args.get("values")},
            },
            "add_formula": {
                "method": "patch",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/range(address='{args.get('cell')}')"
                ),
                "data_transform": lambda args: {"formulas": [[args.get("formula")]]},
            },
            "add_row": {
                "method": "patch",
                "endpoint": get_add_row_endpoint,
                "data_transform": lambda args: {"values": [prepare_row_values(args)]},
                "preprocess": prepare_add_row_data,
            },
            "add_table": {
                "method": "post",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}/tables/add"
                ),
                "data_transform": lambda args: {
                    "address": args.get("range"),
                    "hasHeaders": args.get("has_headers", True),
                    "name": args.get("name") if "name" in args else None,
                },
            },
            "find_row": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}/usedRange"
                ),
                "postprocess": find_row_by_value,
            },
            "find_or_create_row": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}/usedRange"
                ),
                "postprocess": process_find_or_create,
            },
            "update_row": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}/usedRange"
                ),
                "postprocess": process_update_row,
            },
            "delete_worksheet_row": {
                "method": "post",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/range(address='{args.get('row_index')}:{args.get('row_index')}')/delete"
                ),
                "data_transform": lambda args: {"shift": "Up"},
            },
            "list_tables": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}"
                    f"{'/workbook/worksheets/' + args.get('worksheet_name') + '/tables' if 'worksheet_name' in args else '/workbook/tables'}"
                ),
            },
            "get_table": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/tables/{args.get('table_name')}"
                ),
            },
            "list_table_rows": {
                "method": "get",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/tables/{args.get('table_name')}/rows"
                ),
            },
            "add_table_column": {
                "method": "post",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/tables/{args.get('table_name')}/columns"
                ),
                "data_transform": lambda args: {"name": args.get("column_name")},
            },
            "delete_table": {
                "method": "delete",
                "endpoint": lambda args: (
                    f"me/drive/items/{args.get('file_id')}/workbook/worksheets/{args.get('worksheet_name')}"
                    f"/tables/{args.get('table_name')}"
                ),
            },
            "download_workbook": {
                "method": "get",
                "endpoint": lambda args: f"me/drive/items/{args.get('file_id')}",
            },
            "search_workbooks": {
                "method": "get",
                "endpoint": lambda args: f"me/drive/root/search(q='{args.get('query')}.xlsx')",
                "params_transform": lambda args: {
                    "$top": args.get("limit", 20),
                    "$select": "id,name,webUrl,lastModifiedDateTime,createdDateTime,size",
                    "$orderby": "lastModifiedDateTime desc",
                },
            },
        }

        def format_create_workbook_endpoint(args):
            file_name = args.get("name", "")
            if not file_name.lower().endswith(".xlsx"):
                file_name = f"{file_name}.xlsx"

            folder_path = args.get("folder_path", "").strip("/")
            if folder_path:
                return f"me/drive/root:/{folder_path}/{file_name}:/content"
            else:
                return f"me/drive/root:/{file_name}:/content"

        try:
            endpoint_info = endpoints[name]
            method = endpoint_info["method"]

            # Pre-process arguments if needed
            if "preprocess" in endpoint_info:
                try:
                    arguments = await endpoint_info["preprocess"](arguments)
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=f"Error preparing request: {str(e)}"
                        )
                    ]

            # Generate the endpoint URL
            try:
                if callable(endpoint_info["endpoint"]):
                    endpoint = endpoint_info["endpoint"](arguments)
                else:
                    endpoint = endpoint_info["endpoint"]
            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Error generating API endpoint: {str(e)}"
                    )
                ]

            # Prepare data for POST/PATCH
            data = None
            if method in ["post", "patch"] and "data_transform" in endpoint_info:
                try:
                    data = endpoint_info["data_transform"](arguments)
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=f"Error preparing request data: {str(e)}"
                        )
                    ]

            # Prepare params for GET/DELETE
            params = None
            if method in ["get", "delete"] and "params_transform" in endpoint_info:
                try:
                    params = endpoint_info["params_transform"](arguments)
                except Exception as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error preparing request parameters: {str(e)}",
                        )
                    ]

            # Make the API request
            try:
                content_type = endpoint_info.get("content_type", None)
                result = await make_graph_api_request(
                    method,
                    endpoint,
                    data=data,
                    params=params,
                    access_token=access_token,
                    content_type=content_type,
                )

            except ValueError as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Unexpected error occurred: {str(e)}"
                    )
                ]

            # Post-process the result if needed
            if "postprocess" in endpoint_info:
                try:
                    result = await endpoint_info["postprocess"](arguments, result)
                except Exception as e:
                    return [
                        TextContent(
                            type="text", text=f"Error processing results: {str(e)}"
                        )
                    ]

            if isinstance(result, dict) and "error" in result:
                return [TextContent(type="text", text=f"Error: {result['error']}")]

            # Check if the result contains an array
            if isinstance(result, list):
                # For arrays, return multiple TextContent items, one for each element
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result
                ]
            # Or if it's a dict with a 'value' key containing an array
            elif (
                isinstance(result, dict)
                and "value" in result
                and isinstance(result["value"], list)
                and name
                in [
                    "read_messages",
                    "list_worksheets",
                    "list_tables",
                    "list_table_rows",
                    "search_workbooks",
                ]
            ):
                # For arrays in API responses, return multiple TextContent items
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result["value"]
                ]
            else:
                # For object results, return as a single TextContent
                return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name=f"{SERVICE_NAME}-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main entry point for authentication
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
