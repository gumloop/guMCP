import logging
import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Google API imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gdrive-server")

# Create server instance
server = Server("gdrive-server")

# Google Drive API configuration
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_PATH = os.environ.get(
    "GDRIVE_CREDENTIALS_PATH", 
    str(Path(__file__).parent.parent.parent.parent / ".gdrive-server-credentials.json")
)
OAUTH_PATH = os.environ.get(
    "GDRIVE_OAUTH_PATH", 
    str(Path(__file__).parent.parent.parent.parent / "gcp-oauth.keys.json")
)

# Global API service
drive_service = None

def authenticate_and_save_credentials():
    """Authenticate with Google and save credentials to file"""
    logger.info("Launching auth flow...")
    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_PATH, SCOPES)
    credentials = flow.run_local_server(port=0)
    
    # Save credentials to file
    with open(CREDENTIALS_PATH, 'w') as f:
        f.write(credentials.to_json())
    
    logger.info("Credentials saved. You can now run the server.")
    return credentials

def load_credentials():
    """Load credentials from file"""
    if not os.path.exists(CREDENTIALS_PATH):
        logger.error("Credentials not found. Please run with 'auth' argument first.")
        raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_PATH}")
    
    with open(CREDENTIALS_PATH, 'r') as f:
        credentials_data = json.load(f)
    
    return Credentials.from_authorized_user_info(credentials_data)

@server.list_resources()
async def handle_list_resources(cursor: str = None) -> dict:
    """List files from Google Drive"""
    logger.info(f"Listing resources with cursor: {cursor}")
    
    page_size = 10
    params = {
        "pageSize": page_size,
        "fields": "nextPageToken, files(id, name, mimeType)"
    }
    
    if cursor:
        params["pageToken"] = cursor
    
    results = drive_service.files().list(**params).execute()
    files = results.get('files', [])
    
    resources = []
    for file in files:
        resources.append(types.Resource(
            uri=f"gdrive:///{file['id']}",
            mimeType=file['mimeType'],
            name=file['name']
        ))
    
    return {
        "resources": resources,
        "nextCursor": results.get('nextPageToken', None)
    }

@server.read_resource()
async def handle_read_resource(uri: str) -> dict:
    """Read a file from Google Drive by URI"""
    logger.info(f"Reading resource: {uri}")
    
    file_id = uri.replace("gdrive:///", "")
    
    # First get file metadata to check mime type
    file_metadata = drive_service.files().get(
        fileId=file_id,
        fields="mimeType"
    ).execute()
    
    mime_type = file_metadata.get('mimeType', 'application/octet-stream')
    
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
        
        file_content = drive_service.files().export(
            fileId=file_id,
            mimeType=export_mime_type
        ).execute()
        
        return {
            "contents": [
                types.TextContent(
                    uri=uri,
                    mimeType=export_mime_type,
                    text=file_content
                )
            ]
        }
    
    # For regular files download content
    file_content = drive_service.files().get_media(fileId=file_id).execute()
    
    if mime_type.startswith("text/") or mime_type == "application/json":
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
        
        return {
            "contents": [
                types.TextContent(
                    uri=uri,
                    mimeType=mime_type,
                    text=file_content
                )
            ]
        }
    else:
        # Handle binary content
        if not isinstance(file_content, bytes):
            file_content = file_content.encode('utf-8')
        
        return {
            "contents": [
                types.BlobContent(
                    uri=uri,
                    mimeType=mime_type,
                    blob=base64.b64encode(file_content).decode('ascii')
                )
            ]
        }

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    logger.info("Listing tools")
    return [
        types.Tool(
            name="search",
            description="Search for files in Google Drive",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests"""
    logger.info(f"Calling tool: {name} with arguments: {arguments}")
    
    if name == "search":
        if not arguments or "query" not in arguments:
            raise ValueError("Missing query parameter")
        
        user_query = arguments["query"]
        escaped_query = user_query.replace("\\", "\\\\").replace("'", "\\'")
        formatted_query = f"fullText contains '{escaped_query}'"
        
        results = drive_service.files().list(
            q=formatted_query,
            pageSize=10,
            fields="files(id, name, mimeType, modifiedTime, size)"
        ).execute()
        
        files = results.get('files', [])
        file_list = "\n".join([f"{file['name']} ({file['mimeType']})" for file in files])
        
        return [
            types.TextContent(
                type="text",
                text=f"Found {len(files)} files:\n{file_list}"
            )
        ]
    
    raise ValueError(f"Unknown tool: {name}")

def get_initialization_options() -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gdrive-server",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
