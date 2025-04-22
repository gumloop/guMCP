import os
import sys
import logging
import json
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
    method, endpoint, data=None, params=None, access_token=None
):
    """Make a request to the Microsoft Graph API"""
    if not access_token:
        raise ValueError("Microsoft access token is required")

    url = f"{MICROSOFT_GRAPH_API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "post":
                response = await client.post(
                    url, json=data, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "patch":
                response = await client.patch(
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
                return {"success": True}
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        error_message = f"Microsoft Graph API error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            if "error" in error_details:
                error_message = f"{error_details['error'].get('code', 'Error')}: {error_details['error'].get('message', 'Unknown error')}"
        except:
            pass
        raise ValueError(error_message)

    except Exception as e:
        logger.error(f"Error making request to Microsoft Graph API: {str(e)}")
        raise ValueError(f"Error communicating with Microsoft Graph API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance for Excel operations"""
    server = Server("mexcel-server")
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
        logger.info(f"Listing Excel resources for user: {server.user_id}")

        access_token = await get_microsoft_client()

        try:
            # Get Excel files from OneDrive
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
                        uri=f"excel:///file/{item['id']}",
                        mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        name=f"{item['name']}",
                    )
                )

            # Include pagination token if available
            next_link = result.get("@odata.nextLink", "")
            next_cursor = None
            if next_link:
                # Extract skiptoken from nextLink
                import re

                match = re.search(r"\$skiptoken=([^&]+)", next_link)
                if match:
                    next_cursor = match.group(1)

            return resources

        except Exception as e:
            logger.error(f"Error fetching Excel resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read an Excel workbook from OneDrive"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await get_microsoft_client()

        uri_str = str(uri)

        if uri_str.startswith("excel:///file/"):
            # Handle Excel file resource
            file_id = uri_str.replace("excel:///file/", "")

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
                logger.error(f"Error reading Excel resource: {str(e)}")
                raise ValueError(f"Error reading Excel file: {str(e)}")

        raise ValueError(f"Unsupported resource URI: {uri_str}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Excel"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
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
            ),
            Tool(
                name="create_worksheet",
                description="Create a new worksheet in an existing workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the Excel file",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name for the new worksheet",
                        },
                    },
                    "required": ["file_id", "name"],
                },
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
            ),
            Tool(
                name="create_workbook",
                description="Create a new Excel workbook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the new workbook (include .xlsx extension)",
                        },
                    },
                    "required": ["name"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Excel"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_microsoft_client()
        arguments = arguments or {}

        try:
            if name == "list_worksheets":
                if "file_id" not in arguments:
                    raise ValueError("Missing required parameter: file_id")

                endpoint = f"me/drive/items/{arguments['file_id']}/workbook/worksheets"
                result = await make_graph_api_request(
                    "get", endpoint, access_token=access_token
                )

                worksheets = result.get("value", [])
                if not worksheets:
                    return [
                        TextContent(
                            type="text", text="No worksheets found in this workbook."
                        )
                    ]

                worksheet_list = []
                for ws in worksheets:
                    worksheet_list.append(
                        f"Name: {ws.get('name')}\n"
                        f"  ID: {ws.get('id')}\n"
                        f"  Position: {ws.get('position')}\n"
                        f"  Visibility: {ws.get('visibility')}"
                    )

                formatted_result = "\n\n".join(worksheet_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(worksheets)} worksheets:\n\n{formatted_result}",
                    )
                ]

            elif name == "read_worksheet":
                if "file_id" not in arguments or "worksheet_name" not in arguments:
                    raise ValueError(
                        "Missing required parameters: file_id and worksheet_name"
                    )

                file_id = arguments["file_id"]
                worksheet_name = arguments["worksheet_name"]
                range_param = arguments.get("range")

                if range_param:
                    endpoint = f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/range(address='{range_param}')"
                else:
                    endpoint = f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/usedRange"

                result = await make_graph_api_request(
                    "get", endpoint, access_token=access_token
                )

                values = result.get("values", [])
                if not values:
                    return [
                        TextContent(
                            type="text", text="No data found in the specified range."
                        )
                    ]

                # Format as a table
                table_rows = []
                for row in values:
                    table_rows.append(" | ".join([str(cell) for cell in row]))

                formatted_result = "\n".join(table_rows)
                range_address = result.get("address", "unknown range")

                return [
                    TextContent(
                        type="text",
                        text=f"Data from {worksheet_name}, {range_address}:\n\n{formatted_result}",
                    )
                ]

            elif name == "update_cells":
                required_fields = ["file_id", "worksheet_name", "range", "values"]
                for field in required_fields:
                    if field not in arguments:
                        raise ValueError(f"Missing required parameter: {field}")

                file_id = arguments["file_id"]
                worksheet_name = arguments["worksheet_name"]
                range_param = arguments["range"]
                values = arguments["values"]

                endpoint = f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/range(address='{range_param}')"
                data = {"values": values}

                await make_graph_api_request(
                    "patch", endpoint, data=data, access_token=access_token
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated range {range_param} in worksheet '{worksheet_name}'",
                    )
                ]

            elif name == "create_worksheet":
                if "file_id" not in arguments or "name" not in arguments:
                    raise ValueError("Missing required parameters: file_id and name")

                file_id = arguments["file_id"]
                worksheet_name = arguments["name"]

                endpoint = f"me/drive/items/{file_id}/workbook/worksheets"
                data = {"name": worksheet_name}

                result = await make_graph_api_request(
                    "post", endpoint, data=data, access_token=access_token
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully created worksheet '{worksheet_name}' at position {result.get('position')}",
                    )
                ]

            elif name == "add_formula":
                required_fields = ["file_id", "worksheet_name", "cell", "formula"]
                for field in required_fields:
                    if field not in arguments:
                        raise ValueError(f"Missing required parameter: {field}")

                file_id = arguments["file_id"]
                worksheet_name = arguments["worksheet_name"]
                cell = arguments["cell"]
                formula = arguments["formula"]

                endpoint = f"me/drive/items/{file_id}/workbook/worksheets/{worksheet_name}/range(address='{cell}')"
                data = {"formulas": [[formula]]}

                await make_graph_api_request(
                    "patch", endpoint, data=data, access_token=access_token
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added formula '{formula}' to cell {cell} in worksheet '{worksheet_name}'",
                    )
                ]

            elif name == "create_workbook":
                if "name" not in arguments:
                    raise ValueError("Missing required parameter: name")

                workbook_name = arguments["name"]

                # Ensure filename has .xlsx extension
                if not workbook_name.lower().endswith(".xlsx"):
                    workbook_name += ".xlsx"

                endpoint = "me/drive/root/children"
                data = {
                    "name": workbook_name,
                    "@microsoft.graph.conflictBehavior": "rename",
                    "file": {},
                }

                # Create empty file first
                new_file = await make_graph_api_request(
                    "post", endpoint, data=data, access_token=access_token
                )

                file_id = new_file.get("id")

                # Initialize as Excel file by creating a session
                workbook_endpoint = f"me/drive/items/{file_id}/workbook"
                await make_graph_api_request(
                    "post",
                    f"{workbook_endpoint}/createSession",
                    data={"persistChanges": True},
                    access_token=access_token,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully created new workbook: {workbook_name}\nFile ID: {file_id}\nURL: {new_file.get('webUrl')}",
                    )
                ]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="mexcel-server",
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
