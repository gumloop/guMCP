import os
import sys
from pathlib import Path
import logging
import dropbox
from dropbox.exceptions import ApiError, AuthError
from typing import Dict, Any
import asyncio


# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# from src.auth.factory import create_auth_client
from src.utils.dropbox.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "account_info.write",
    "account_info.read",
    "files.metadata.read",
    "files.metadata.write",
    "files.content.read",
    "files.content.write",
    "file_requests.read",
    "file_requests.write",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_credentials(user_id: str, service_name: str, api_key: str = None) -> str:
    """
    Retrieve (or refresh if needed) the access token for Dropbox.

    Args:
        user_id: ID of the user.
        service_name: Name of the service (dropbox).
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A valid access token string.
    """
    from src.utils.dropbox.util import get_credentials as get_dropbox_credentials

    return await get_dropbox_credentials(user_id, service_name, api_key)


async def create_dropbox_client(user_id, api_key=None):
    """
    Create a new Dropbox client instance using the stored OAuth credentials.

    Args:
        user_id (str): The user ID associated with the credentials.
        api_key (str, optional): Optional override for authentication.

    Returns:
        dropbox.Dropbox: Dropbox API client with credentials initialized.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key)
    if not token:
        raise AuthError("Failed to get valid credentials")

    dbx = dropbox.Dropbox(token)
    return dbx


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Dropbox MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Dropbox tools registered.
    """
    server = Server(SERVICE_NAME)
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Dropbox API.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="list_files",
                description="List files or folders in a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the directory to list files from, root directory is "
                            " ",
                        },
                    },
                    "required": ["path"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files and folders with their details including name, path, and type",
                    "examples": [
                        "name: document.txt, path_lower: /folder/document.txt, type: FileMetadata",
                        "name: images, path_lower: /folder/images, type: FolderMetadata",
                    ],
                },
                requiredScopes=["files.metadata.read"],
            ),
            types.Tool(
                name="upload_file",
                description="Upload a file to a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dropbox_path": {
                            "type": "string",
                            "description": "The path to the directory to upload the file to, root directory is "
                            " ",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to upload",
                        },
                        "file_name": {
                            "type": "string",
                            "description": "The name of the file to upload",
                        },
                        "mode": {
                            "type": "string",
                            "description": "The mode to upload the file in",
                            "enum": ["overwrite", "add"],
                            "default": "add",
                        },
                    },
                    "required": ["path", "file_path", "file_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the upload operation with file path",
                    "examples": [
                        "Successfully uploaded file to: /path/to/uploaded/file.txt"
                    ],
                },
                requiredScopes=["files.content.write"],
            ),
            types.Tool(
                name="create_folder",
                description="Create a folder in a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_name": {
                            "type": "string",
                            "description": "The name of the folder to create",
                        },
                        "path": {
                            "type": "string",
                            "description": "The path to the directory to create the folder in, root directory is "
                            " ",
                        },
                    },
                    "required": ["folder_name", "path"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the folder creation operation with path",
                    "examples": [
                        "Successfully created folder at: /path/to/created/folder"
                    ],
                },
                requiredScopes=["files.metadata.write"],
            ),
            types.Tool(
                name="delete",
                description="Delete a file or folder from a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file or folder to delete, root directory is "
                            " ",
                            "default": "",
                        },
                    },
                    "required": ["path"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the delete operation with path",
                    "examples": [
                        "Successfully deleted: /path/to/deleted/file.txt",
                        "Successfully deleted: /path/to/deleted/folder",
                    ],
                },
                requiredScopes=["files.content.write", "files.metadata.write"],
            ),
            types.Tool(
                name="download",
                description="Download a file from a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to download, root directory is "
                            " ",
                        },
                        "local_path": {
                            "type": "string",
                            "description": "The path to the local directory to save the file to",
                        },
                        "file_name": {
                            "type": "string",
                            "description": "The name of the file to download",
                        },
                    },
                    "required": ["path", "local_path", "file_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the download operation with local file path",
                    "examples": [
                        "Successfully downloaded file to: /local/path/to/downloaded/file.txt"
                    ],
                },
                requiredScopes=["files.content.read"],
            ),
            types.Tool(
                name="search",
                description="Search for a file or a folder in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The query to search for, name of the file or a folder you are looking for with the extension",
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search results showing matching file or folder paths",
                    "examples": [
                        "Search results:\n- /path/to/match1.txt\n- /path/to/match2.pdf"
                    ],
                },
                requiredScopes=["files.metadata.read"],
            ),
            types.Tool(
                name="move",
                description="Move a file or a folder to a specific directory in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_path": {
                            "type": "string",
                            "description": "The path to the file or folder to move, root directory is "
                            " ",
                        },
                        "to_path": {
                            "type": "string",
                            "description": "The path to the directory to move the file or folder to, root directory is "
                            " ",
                        },
                        "file_name": {
                            "type": "string",
                            "description": "The name of the file or folder to move",
                        },
                    },
                    "required": ["from_path", "to_path", "file_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the move operation with new file or folder path",
                    "examples": ["Successfully moved file to: /new/path/to/file.txt"],
                },
                requiredScopes=["files.metadata.write"],
            ),
            types.Tool(
                name="get_user_info",
                description="Get information about the current user",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "User information including name, email, account ID, and country",
                    "examples": [
                        "User Information:\nName: Example User\nEmail: user@example.com\nAccount ID: dbid:ABC123\nCountry: US"
                    ],
                },
                requiredScopes=["account_info.read"],
            ),
            types.Tool(
                name="get_file_metadata",
                description="Get metadata/information about a file in Dropbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to get metadata about, root directory is "
                            " ",
                        },
                    },
                    "required": ["path"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File metadata including name, path, and size",
                    "examples": [
                        "File Metadata:\nName: example.txt\nPath: /path/to/example.txt\nSize: 1024 bytes"
                    ],
                },
                requiredScopes=["files.metadata.read"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Handles the execution of a specific tool based on the provided name and arguments.
        """
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        # Get Dropbox client
        dbx = await create_dropbox_client(user_id, server.api_key)

        try:
            if name == "list_files":
                dbx.users_get_current_account()  # Ensures token is valid
                result = await asyncio.to_thread(
                    lambda: dbx.files_list_folder(path=arguments["path"])
                )
                entries = []
                for entry in result.entries:
                    entries.append(
                        types.TextContent(
                            type="text",
                            text=f"name: {entry.name}, path_lower: {entry.path_lower}, type: {entry.__class__.__name__}",
                        )
                    )
                return entries

            elif name == "upload_file":
                # Construct the destination path
                dbx.users_get_current_account()
                dropbox_destination_path = (
                    f"{arguments['dropbox_path']}/{arguments['file_name']}"
                )
                mode = (
                    dropbox.files.WriteMode.overwrite
                    if arguments.get("mode") == "overwrite"
                    else dropbox.files.WriteMode.add
                )
                with open(arguments["file_path"], "rb") as f:
                    dbx.files_upload(f.read(), dropbox_destination_path, mode=mode)

                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully uploaded file to: {dropbox_destination_path}",
                    )
                ]

                # Check if file exists locally

            elif name == "create_folder":
                new_folder_path = f"{arguments['path']}/{arguments['folder_name']}"
                result = await asyncio.to_thread(
                    lambda: dbx.files_create_folder_v2(new_folder_path, autorename=True)
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully created folder at: {result.metadata.path_display}",
                    )
                ]

            elif name == "delete":
                result = await asyncio.to_thread(
                    lambda: dbx.files_delete_v2(arguments["path"])
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully deleted: {result.metadata.path_display}",
                    )
                ]

            elif name == "download":
                # Create local directory if it doesn't exist
                os.makedirs(arguments["local_path"], exist_ok=True)
                local_file_path = os.path.join(
                    arguments["local_path"], arguments["file_name"]
                )

                # Download the file
                metadata, response = await asyncio.to_thread(
                    lambda: dbx.files_download(path=arguments["path"])
                )

                # Write to local file
                with open(local_file_path, "wb") as f:
                    f.write(response.content)

                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully downloaded file to: {local_file_path}",
                    )
                ]

            elif name == "search":
                results = await asyncio.to_thread(
                    lambda: dbx.files_search_v2(query=arguments["query"])
                )
                matches = []
                for match in results.matches:
                    metadata = match.metadata.get_metadata()
                    matches.append(metadata.path_display)
                return [
                    types.TextContent(
                        type="text",
                        text="Search results:\n"
                        + "\n".join([f"- {match}" for match in matches]),
                    )
                ]

            elif name == "move":
                to_actual_path = f"{arguments['to_path']}/{arguments['file_name']}"
                result = await asyncio.to_thread(
                    lambda: dbx.files_move_v2(arguments["from_path"], to_actual_path)
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"Successfully moved file to: {result.metadata.path_display}",
                    )
                ]

            elif name == "get_user_info":
                account = await asyncio.to_thread(
                    lambda: dbx.users_get_current_account()
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"User Information:\n"
                        f"Name: {account.name.display_name}\n"
                        f"Email: {account.email}\n"
                        f"Account ID: {account.account_id}\n"
                        f"Country: {account.country}",
                    )
                ]
            elif name == "get_file_metadata":
                metadata = await asyncio.to_thread(
                    lambda: dbx.files_get_metadata(path=arguments["path"])
                )
                return [
                    types.TextContent(
                        type="text",
                        text=f"File Metadata:\n"
                        f"Name: {metadata.name}\n"
                        f"Path: {metadata.path_display}\n"
                        f"Size: {metadata.size} bytes",
                    )
                ]
            else:
                raise ValueError(f"Unsupported tool: {name}")

        except AuthError as e:
            logger.error(f"Authentication error: {e}")
            return [
                types.TextContent(
                    type="text",
                    text="Authentication failed. Please check your credentials.",
                )
            ]
        except ApiError as e:
            logger.error(f"Dropbox API error: {e}")
            return [types.TextContent(type="text", text=f"Dropbox API error: {str(e)}")]
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return [
                types.TextContent(
                    type="text", text=f"An unexpected error occurred: {str(e)}"
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options for the server instance.
    """
    return InitializationOptions(
        server_name="dropbox-server",
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
        print("python -m src.servers.dropbox.main auth")
