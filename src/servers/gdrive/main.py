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


SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Configure logging
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
            # Map Google Drive mime types to resource_type
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

        # mcp Python sdk (1.4.1) doesn't seem to support returning cursors for pagination here
        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a file from Google Drive by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        drive_service = await create_drive_service(
            server.user_id, api_key=server.api_key
        )

        # Extract file_id from the new URI format
        uri_parts = str(uri).split("://")
        if len(uri_parts) > 1:
            path_parts = uri_parts[1].split("/", 1)
            if len(path_parts) > 1:
                file_id = path_parts[1]
            else:
                raise ValueError(f"Invalid URI format: {uri}")
        else:
            # Handle legacy format for backward compatibility
            file_id = str(uri).replace("gdrive:///", "")

        # First get file metadata to check mime type
        file_metadata = (
            drive_service.files().get(fileId=file_id, fields="mimeType").execute()
        )

        mime_type = file_metadata.get("mimeType", "application/octet-stream")

        # For Google Docs/Sheets/etc we need to export
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

        # For regular files download content
        file_content = drive_service.files().get_media(fileId=file_id).execute()

        if mime_type.startswith("text/") or mime_type == "application/json":
            if isinstance(file_content, bytes):
                file_content = file_content.decode("utf-8")

            return [ReadResourceContents(content=file_content, mime_type=mime_type)]
        else:
            # Handle binary content
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
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if name == "search":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            drive_service = await create_drive_service(
                server.user_id, api_key=server.api_key
            )

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
            file_list = "\n".join(
                [f"{file['name']} ({file['mimeType']})" for file in files]
            )

            return [
                TextContent(type="text", text=f"Found {len(files)} files:\n{file_list}")
            ]

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
