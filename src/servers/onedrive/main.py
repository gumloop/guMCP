import os
import sys
import json
import logging
from pathlib import Path
import types
import requests


# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from src.utils.microsoft.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name

SCOPES = ["https://graph.microsoft.com/Files.ReadWrite.All", "offline_access"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_onedrive_client(user_id, api_key=None):
    """Create a new OneDrive client for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return credentials


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("onedrive-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            types.Tool(
                name="list_files",
                description="Lists files and folders in a OneDrive directory",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_path": {
                            "type": "string",
                            "description": "The path to the folder (e.g., '/Documents' or '/')",
                            "default": "/",
                        },
                    },
                },
            ),
            types.Tool(
                name="upload_file",
                description="Uploads a file to OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "local_file_path": {
                            "type": "string",
                            "description": "The local path to the file to upload",
                        },
                        "destination_path": {
                            "type": "string",
                            "description": "The destination path in OneDrive including filename",
                        },
                    },
                    "required": ["local_file_path", "destination_path"],
                },
            ),
            types.Tool(
                name="download_file",
                description="Downloads a file from OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "onedrive_path": {
                            "type": "string",
                            "description": "The path to the file in OneDrive",
                        },
                        "local_destination_path": {
                            "type": "string",
                            "description": "The local path where the file should be saved",
                        },
                    },
                    "required": ["onedrive_path", "local_destination_path"],
                },
            ),
            types.Tool(
                name="create_folder",
                description="Creates a new folder in OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_path": {
                            "type": "string",
                            "description": "The path where the folder should be created",
                        },
                        "folder_name": {
                            "type": "string",
                            "description": "The name of the new folder",
                        },
                    },
                    "required": ["folder_path", "folder_name"],
                },
            ),
            types.Tool(
                name="delete_item",
                description="Deletes a file or folder from OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_path": {
                            "type": "string",
                            "description": "The path to the file or folder to delete",
                        },
                    },
                    "required": ["item_path"],
                },
            ),
            types.Tool(
                name="search_files",
                description="Searches for files in OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "The term to search for",
                        },
                    },
                    "required": ["search_term"],
                },
            ),
            types.Tool(
                name="get_file_sharing_link",
                description="Gets sharing link for a OneDrive file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await create_onedrive_client(
            server.user_id, api_key=server.api_key
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        if name == "list_files":
            try:
                folder_path = arguments.get("folder_path", "/")

                # Handle root folder specially
                if folder_path == "/" or not folder_path:
                    api_path = "https://graph.microsoft.com/v1.0/me/drive/root/children"
                else:
                    # Remove leading slash if present
                    if folder_path.startswith("/"):
                        folder_path = folder_path[1:]
                    api_path = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"

                params = {
                    "$select": "id,name,folder,file,size,createdDateTime,lastModifiedDateTime",
                    "$orderby": "name asc",
                }

                response = requests.get(
                    api_path,
                    headers=headers,
                    params=params,
                )

                if response.status_code != 200:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Error retrieving files: {error_message}",
                        )
                    ]

                items = response.json().get("value", [])

                if not items:
                    return [
                        TextContent(
                            type="text", text=f"No files found in folder: {folder_path}"
                        )
                    ]

                item_list = []
                for item in items:
                    name = item.get("name", "Unnamed")
                    item_type = "Folder" if "folder" in item else "File"
                    size = item.get("size", 0)
                    created = item.get("createdDateTime", "")
                    modified = item.get("lastModifiedDateTime", "")

                    item_info = (
                        f"{item_type}: {name}\n"
                        f"Size: {size} bytes\n"
                        f"Created: {created}\n"
                        f"Modified: {modified}\n"
                    )
                    item_list.append(item_info)

                return [
                    TextContent(
                        type="text",
                        text=f"Contents of folder '{folder_path}':\n\n"
                        + "\n---\n".join(item_list),
                    )
                ]

            except Exception as e:
                logger.error(f"Error in list_files: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "upload_file":
            try:
                local_file_path = arguments.get("local_file_path")
                destination_path = arguments.get("destination_path")

                if not local_file_path or not destination_path:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (local_file_path, destination_path)",
                        )
                    ]

                # Remove leading slash if present
                if destination_path.startswith("/"):
                    destination_path = destination_path[1:]

                # Read the file
                with open(local_file_path, "rb") as file:
                    file_content = file.read()

                response = requests.put(
                    f"https://graph.microsoft.com/v1.0/me/drive/root:/{destination_path}:/content",
                    headers=headers,
                    data=file_content,
                )

                if response.status_code in [200, 201]:
                    file_data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"File uploaded successfully to {destination_path}\nID: {file_data.get('id')}",
                        )
                    ]
                else:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to upload file: {error_message}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error in upload_file: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "create_folder":
            try:
                folder_path = arguments.get("folder_path", "/")
                folder_name = arguments.get("folder_name")

                if not folder_name:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (folder_name)",
                        )
                    ]

                # Remove leading slash if present
                if folder_path.startswith("/"):
                    folder_path = folder_path[1:]

                # Prepare API endpoint
                if folder_path == "":
                    api_path = "https://graph.microsoft.com/v1.0/me/drive/root/children"
                else:
                    api_path = f"https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children"

                # Prepare folder creation payload
                folder_payload = {
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename",
                }

                response = requests.post(
                    api_path,
                    headers=headers,
                    data=json.dumps(folder_payload),
                )

                if response.status_code in [200, 201]:
                    folder_data = response.json()
                    return [
                        TextContent(
                            type="text",
                            text=f"Folder '{folder_name}' created successfully in {folder_path}\nID: {folder_data.get('id')}",
                        )
                    ]
                else:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create folder: {error_message}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error in create_folder: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "delete_item":
            try:
                item_path = arguments.get("item_path")

                if not item_path:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (item_path)",
                        )
                    ]

                # Remove leading slash if present
                if item_path.startswith("/"):
                    item_path = item_path[1:]

                # Prepare API endpoint
                api_path = (
                    f"https://graph.microsoft.com/v1.0/me/drive/root:/{item_path}"
                )

                response = requests.delete(
                    api_path,
                    headers=headers,
                )

                if response.status_code in [200, 204]:
                    return [
                        TextContent(
                            type="text",
                            text=f"Item '{item_path}' deleted successfully.",
                        )
                    ]
                else:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to delete item: {error_message}",
                        )
                    ]

            except Exception as e:
                logger.error(f"Error in delete_item: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "download_file":
            try:
                onedrive_path = arguments.get("onedrive_path")
                local_destination_path = arguments.get("local_destination_path")

                if not onedrive_path or not local_destination_path:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (onedrive_path, local_destination_path)",
                        )
                    ]

                # Remove leading slash if present
                if onedrive_path.startswith("/"):
                    onedrive_path = onedrive_path[1:]

                # Prepare API endpoint
                api_path = f"https://graph.microsoft.com/v1.0/me/drive/root:/{onedrive_path}:/content"

                response = requests.get(
                    api_path,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to download file: {error_message}",
                        )
                    ]

                # Write the content to the local file
                with open(local_destination_path, "wb") as file:
                    file.write(response.content)

                return [
                    TextContent(
                        type="text",
                        text=f"File downloaded successfully to {local_destination_path}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error in download_file: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        elif name == "search_files":
            try:
                search_term = arguments.get("search_term")

                if not search_term:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (search_term)",
                        )
                    ]

                # Prepare API endpoint
                api_path = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{search_term}')"

                response = requests.get(
                    api_path,
                    headers=headers,
                )

                if response.status_code != 200:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Error searching files: {error_message}",
                        )
                    ]

                items = response.json().get("value", [])

                if not items:
                    return [
                        TextContent(
                            type="text",
                            text=f"No files found matching '{search_term}'",
                        )
                    ]

                item_list = []
                for item in items:
                    name = item.get("name", "Unnamed")
                    item_type = "Folder" if "folder" in item else "File"
                    size = item.get("size", 0)

                    item_info = f"{item_type}: {name}\n" f"Size: {size} bytes\n"
                    item_list.append(item_info)

                return [
                    TextContent(
                        type="text",
                        text=f"Search results for '{search_term}':\n\n"
                        + "\n---\n".join(item_list),
                    )
                ]

            except Exception as e:
                logger.error(f"Error in search_files: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "get_file_sharing_link":
            try:
                file_path = arguments.get("file_path")

                if not file_path:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (file_path)",
                        )
                    ]
                if file_path.startswith("/"):
                    file_path = file_path[1:]

                # Get the file/folder item first
                item_response = requests.get(
                    f"https://graph.microsoft.com/v1.0/me/drive/root:/{file_path}",
                    headers=headers,
                )

                if item_response.status_code != 200:
                    error_message = (
                        item_response.json()
                        .get("error", {})
                        .get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to find item: {error_message}",
                        )
                    ]

                item_data = item_response.json()
                item_id = item_data.get("id")

                # Create sharing link using item ID
                response = requests.post(
                    f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/createLink",
                    headers=headers,
                    # data=json.dumps(payload)
                )

                if response.status_code != 200:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create sharing link: {error_message}",
                        )
                    ]

                link_data = response.json()
                sharing_link = link_data.get("link", {}).get("webUrl", "")

                return [
                    TextContent(
                        type="text",
                        text=f"Sharing link for '{file_path}': {sharing_link}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error in get_sharing_link: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        else:
            logger.error(f"Unknown tool: {name}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'",
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="onedrive-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the MCP server framework.")
