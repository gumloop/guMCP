import os
import sys
import requests
import io
from typing import Optional, Iterable

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path

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

from src.utils.google.util import authenticate_and_save_credentials, get_credentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload, MediaIoBaseUpload


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_drive_service(user_id, api_key=None):
    """Create a new Drive service instance for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return build("drive", "v3", credentials=credentials)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("gdrive-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List files from Google Drive"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        drive_service = await create_drive_service(
            server.user_id, api_key=server.api_key
        )

        page_size = 10
        params = {
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType)",
        }

        if cursor:
            params["pageToken"] = cursor

        results = drive_service.files().list(**params).execute()
        files = results.get("files", [])

        resources = []
        for file in files:
            mime_type = file["mimeType"]
            if mime_type.startswith("application/vnd.google-apps.folder"):
                resource_type = "folder"
            elif mime_type.startswith("application/vnd.google-apps.document"):
                resource_type = "document"
            elif mime_type.startswith("application/vnd.google-apps.spreadsheet"):
                resource_type = "spreadsheet"
            elif mime_type.startswith("application/vnd.google-apps.presentation"):
                resource_type = "presentation"
            else:
                resource_type = "file"

            resource = Resource(
                uri=f"gdrive://{resource_type}/{file['id']}",
                mimeType=file["mimeType"],
                name=file["name"],
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a file from Google Drive by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        drive_service = await create_drive_service(
            server.user_id, api_key=server.api_key
        )

        uri_parts = str(uri).split("://")
        if len(uri_parts) > 1:
            path_parts = uri_parts[1].split("/", 1)
            if len(path_parts) > 1:
                file_id = path_parts[1]
            else:
                raise ValueError(f"Invalid URI format: {uri}")
        else:
            file_id = str(uri).replace("gdrive:///", "")

        file_metadata = (
            drive_service.files().get(fileId=file_id, fields="mimeType").execute()
        )

        mime_type = file_metadata.get("mimeType", "application/octet-stream")
        if mime_type.startswith("application/vnd.google-apps"):
            export_mime_type = "text/plain"

            if mime_type == "application/vnd.google-apps.document":
                export_mime_type = "text/markdown"
            elif mime_type == "application/vnd.google-apps.spreadsheet":
                export_mime_type = "text/csv"
            elif mime_type == "application/vnd.google-apps.presentation":
                export_mime_type = "text/plain"
            elif mime_type == "application/vnd.google-apps.drawing":
                export_mime_type = "image/png"

            file_content = (
                drive_service.files()
                .export(fileId=file_id, mimeType=export_mime_type)
                .execute()
            )

            file_content = file_content.decode("utf-8")

            return [
                ReadResourceContents(content=file_content, mime_type=export_mime_type)
            ]

        file_content = drive_service.files().get_media(fileId=file_id).execute()

        if mime_type.startswith("text/") or mime_type == "application/json":
            if isinstance(file_content, bytes):
                file_content = file_content.decode("utf-8")

            return [ReadResourceContents(content=file_content, mime_type=mime_type)]
        else:
            if not isinstance(file_content, bytes):
                file_content = file_content.encode("utf-8")

            return [ReadResourceContents(content=file_content, mime_type=mime_type)]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search",
                description="Search for files in Google Drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of files matching the search query",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Document Title", "mimeType": "application/vnd.google-apps.document", "modifiedTime": "2023-05-14T02:54:07.606Z", "size": "5059"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.readonly"],
            ),
            Tool(
                name="copy_file",
                description="Create a copy of the specified file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to copy",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the copy (optional)",
                        },
                        "folder_id": {
                            "type": "string",
                            "description": "Parent folder ID for the copy (optional)",
                        },
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metadata of the copied file",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Copy of Document Title", "mimeType": "application/vnd.google-apps.document"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="create_folder",
                description="Create a new, empty folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the folder to create",
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "ID of the parent folder (optional)",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metadata of the created folder",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Test Folder", "parents": ["0ABC123DEF"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="move_file",
                description="Move a file from one folder to another.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to move",
                        },
                        "folder_id": {
                            "type": "string",
                            "description": "ID of the destination folder",
                        },
                        "remove_parents": {
                            "type": "boolean",
                            "description": "Whether to remove the file from its current parent folders (optional)",
                        },
                    },
                    "required": ["file_id", "folder_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated file metadata after moving",
                    "examples": ['{"id": "1abc123XYZ", "parents": ["0ABC123DEF"]}'],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="create_file_from_text",
                description="Create a new file from plain text.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the file to create",
                        },
                        "content": {
                            "type": "string",
                            "description": "Text content of the file",
                        },
                        "mime_type": {
                            "type": "string",
                            "description": "MIME type (default: text/plain)",
                        },
                        "folder_id": {
                            "type": "string",
                            "description": "Parent folder ID (optional)",
                        },
                    },
                    "required": ["name", "content"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metadata of the created file",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Test File.txt", "mimeType": "text/plain", "parents": ["0ABC123DEF"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="replace_file",
                description="Upload a file to Drive, that replaces an existing file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to replace",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL of the new file content",
                        },
                        "mime_type": {
                            "type": "string",
                            "description": "MIME type of the new content (optional)",
                        },
                    },
                    "required": ["file_id", "url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated file metadata",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "File Name", "mimeType": "text/plain"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="add_file_sharing_preference",
                description="Adds a sharing scope to the sharing preference of a file. Does not remove existing sharing settings. Provides a sharing URL.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to share",
                        },
                        "role": {
                            "type": "string",
                            "description": "Role to grant (reader, commenter, writer, fileOrganizer, organizer, owner)",
                            "enum": [
                                "reader",
                                "commenter",
                                "writer",
                                "fileOrganizer",
                                "organizer",
                                "owner",
                            ],
                        },
                        "type": {
                            "type": "string",
                            "description": "Type of sharing (user, group, domain, anyone)",
                            "enum": ["user", "group", "domain", "anyone"],
                        },
                        "email_address": {
                            "type": "string",
                            "description": "Email address for user or group sharing (required for user/group types)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domain for domain sharing (required for domain type)",
                        },
                    },
                    "required": ["file_id", "role", "type"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Sharing information including permission details and link",
                    "examples": [
                        '{"permission": {"id": "anyoneWithLink", "type": "anyone", "role": "reader"}, "webViewLink": "https://drive.google.com/file/d/1abc123XYZ/view?usp=drivesdk"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="create_shortcut",
                description="Create a shortcut to a file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the shortcut",
                        },
                        "target_id": {
                            "type": "string",
                            "description": "ID of the target file or folder",
                        },
                        "folder_id": {
                            "type": "string",
                            "description": "ID of the folder to create the shortcut in (optional)",
                        },
                    },
                    "required": ["name", "target_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Metadata of the created shortcut",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Shortcut to File", "mimeType": "application/vnd.google-apps.shortcut", "shortcutDetails": {"targetId": "1def456UVW", "targetMimeType": "text/plain"}}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="update_file_folder_name",
                description="Update the name of a file or folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file or folder to rename",
                        },
                        "new_name": {
                            "type": "string",
                            "description": "New name for the file or folder",
                        },
                    },
                    "required": ["file_id", "new_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated file metadata",
                    "examples": ['{"id": "1abc123XYZ", "name": "Updated File Name"}'],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
            ),
            Tool(
                name="retrieve_files",
                description="This action sends a GET request to the Google Drive API to retrieve a list of files based on specific query parameters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query using Google Drive query syntax",
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Maximum number of files to return (optional)",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "Field to sort results by (optional)",
                        },
                        "include_trashed": {
                            "type": "boolean",
                            "description": "Whether to include files in trash (optional)",
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files matching the query parameters",
                    "examples": [
                        '{"files": [{"id": "1abc123XYZ", "name": "Test File.txt", "mimeType": "text/plain", "parents": ["0ABC123DEF"], "webViewLink": "https://drive.google.com/file/d/1abc123XYZ/view?usp=drivesdk", "modifiedTime": "2023-05-14T09:42:01.195Z", "size": "47"}, {"id": "2def456UVW", "name": "Test Folder", "mimeType": "application/vnd.google-apps.folder", "parents": ["0ABC123DEF"], "webViewLink": "https://drive.google.com/drive/folders/2def456UVW", "modifiedTime": "2023-05-14T09:41:50.867Z"}]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.readonly"],
            ),
            Tool(
                name="retrieve_file_or_folder_by_id",
                description="Get a file or folder by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "ID of the file or folder to retrieve",
                        },
                        "fields": {
                            "type": "string",
                            "description": "File fields to include in the response (optional)",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed metadata for the requested file or folder",
                    "examples": [
                        '{"id": "1abc123XYZ", "name": "Test File.txt", "mimeType": "text/plain", "parents": ["0ABC123DEF"], "webViewLink": "https://drive.google.com/file/d/1abc123XYZ/view?usp=drivesdk", "modifiedTime": "2023-05-14T09:42:01.195Z", "size": "47"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.readonly"],
            ),
            Tool(
                name="delete_file",
                description="This action will delete a file in Google Drive. You will need to provide the file ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "ID of the file to delete",
                        },
                    },
                    "required": ["file_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Success message or error details",
                    "examples": ['"File with ID 1abc123XYZ deleted successfully."'],
                },
                requiredScopes=["https://www.googleapis.com/auth/drive.file"],
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

        if arguments is None:
            arguments = {}

        drive_service = await create_drive_service(
            server.user_id, api_key=server.api_key
        )

        if name == "search":
            user_query = arguments["query"]
            escaped_query = user_query.replace("\\", "\\\\").replace("'", "\\'")
            formatted_query = f"fullText contains '{escaped_query}'"

            results = (
                drive_service.files()
                .list(
                    q=formatted_query,
                    pageSize=10,
                    fields="files(id, name, mimeType, modifiedTime, size)",
                )
                .execute()
            )

            files = results.get("files", [])
            return [TextContent(type="text", text=str(file)) for file in files]

        elif name == "copy_file":
            file_id = arguments["file_id"]
            body = {}

            if "name" in arguments:
                body["name"] = arguments["name"]

            if "folder_id" in arguments:
                body["parents"] = [arguments["folder_id"]]

            result = drive_service.files().copy(fileId=file_id, body=body).execute()

            return [TextContent(type="text", text=str(result))]

        elif name == "create_folder":
            file_metadata = {
                "name": arguments["name"],
                "mimeType": "application/vnd.google-apps.folder",
            }

            if "parent_folder_id" in arguments:
                file_metadata["parents"] = [arguments["parent_folder_id"]]

            result = (
                drive_service.files()
                .create(body=file_metadata, fields="id, name, parents")
                .execute()
            )

            return [TextContent(type="text", text=str(result))]

        elif name == "move_file":
            file_id = arguments["file_id"]
            folder_id = arguments["folder_id"]

            file = drive_service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))
            remove_parents = arguments.get("remove_parents", True)
            if remove_parents:
                result = (
                    drive_service.files()
                    .update(
                        fileId=file_id,
                        addParents=folder_id,
                        removeParents=previous_parents,
                        fields="id, parents",
                    )
                    .execute()
                )
            else:
                result = (
                    drive_service.files()
                    .update(fileId=file_id, addParents=folder_id, fields="id, parents")
                    .execute()
                )

            return [TextContent(type="text", text=str(result))]

        elif name == "create_file_from_text":
            file_metadata = {
                "name": arguments["name"],
                "mimeType": arguments.get("mime_type", "text/plain"),
            }

            if "folder_id" in arguments:
                file_metadata["parents"] = [arguments["folder_id"]]

            media = MediaInMemoryUpload(
                arguments["content"].encode("utf-8"), mimetype=file_metadata["mimeType"]
            )

            result = (
                drive_service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id, name, parents, mimeType",
                )
                .execute()
            )

            return [TextContent(type="text", text=str(result))]

        elif name == "replace_file":

            file_id = arguments["file_id"]
            url = arguments["url"]

            response = requests.get(url)
            response.raise_for_status()

            file_metadata = (
                drive_service.files()
                .get(fileId=file_id, fields="name,mimeType")
                .execute()
            )

            mime_type = arguments.get(
                "mime_type", file_metadata.get("mimeType", "application/octet-stream")
            )
            media = MediaIoBaseUpload(
                io.BytesIO(response.content), mimetype=mime_type, resumable=True
            )

            result = (
                drive_service.files()
                .update(fileId=file_id, media_body=media, fields="id, name, mimeType")
                .execute()
            )

            return [TextContent(type="text", text=str(result))]

        elif name == "add_file_sharing_preference":
            file_id = arguments["file_id"]
            role = arguments["role"]
            type_value = arguments["type"]

            permission = {"role": role, "type": type_value}

            if type_value == "user" or type_value == "group":
                if "email_address" in arguments:
                    permission["emailAddress"] = arguments["email_address"]
            elif type_value == "domain":
                if "domain" in arguments:
                    permission["domain"] = arguments["domain"]
            result = (
                drive_service.permissions()
                .create(fileId=file_id, body=permission, fields="id, type, role")
                .execute()
            )

            file_data = (
                drive_service.files()
                .get(fileId=file_id, fields="webViewLink")
                .execute()
            )

            share_info = {
                "permission": result,
                "webViewLink": file_data.get("webViewLink", "Link not available"),
            }

            return [TextContent(type="text", text=str(share_info))]

        elif name == "create_shortcut":
            file_metadata = {
                "name": arguments["name"],
                "mimeType": "application/vnd.google-apps.shortcut",
                "shortcutDetails": {"targetId": arguments["target_id"]},
            }

            if "folder_id" in arguments:
                file_metadata["parents"] = [arguments["folder_id"]]

            result = (
                drive_service.files()
                .create(
                    body=file_metadata, fields="id, name, mimeType, shortcutDetails"
                )
                .execute()
            )

            return [TextContent(type="text", text=str(result))]

        elif name == "update_file_folder_name":
            file_id = arguments["file_id"]
            new_name = arguments["new_name"]

            file_metadata = {"name": new_name}

            result = (
                drive_service.files()
                .update(fileId=file_id, body=file_metadata, fields="id, name")
                .execute()
            )

            return [TextContent(type="text", text=str(result))]

        elif name == "retrieve_files":
            query = arguments["query"]
            page_size = arguments.get("page_size", 10)
            order_by = arguments.get("order_by", None)
            include_trashed = arguments.get("include_trashed", False)

            if not include_trashed and "trashed" not in query:
                query = f"{query} and trashed = false"

            params = {
                "q": query,
                "pageSize": page_size,
                "fields": "files(id, name, mimeType, modifiedTime, size, parents, webViewLink)",
            }

            if order_by:
                params["orderBy"] = order_by

            results = drive_service.files().list(**params).execute()

            return [TextContent(type="text", text=str(results))]

        elif name == "retrieve_file_or_folder_by_id":
            file_id = arguments["id"]
            fields = arguments.get(
                "fields", "id, name, mimeType, modifiedTime, size, parents, webViewLink"
            )

            result = drive_service.files().get(fileId=file_id, fields=fields).execute()

            return [TextContent(type="text", text=str(result))]
        elif name == "delete_file":
            file_id = arguments["file_id"]
            drive_service.files().delete(fileId=file_id).execute()

            return [
                TextContent(
                    type="text", text=f"File with ID {file_id} deleted successfully."
                )
            ]

        else:
            raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gdrive-server",
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
        print("Note: To run the server normally, use the guMCP server framework.")
