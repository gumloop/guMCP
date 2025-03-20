import os
import sys

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

import base64
import logging
from pathlib import Path

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from auth.factory import create_auth_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gdrive-server")

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_and_save_credentials(user_id):
    """Authenticate with Google and save credentials"""
    logger.info(f"Launching auth flow for user {user_id}...")
    
    # Get auth client
    auth_client = create_auth_client()
    
    # Get OAuth config
    oauth_config = auth_client.get_oauth_config(SERVICE_NAME)
    
    # Create and run flow
    flow = InstalledAppFlow.from_client_config(oauth_config, SCOPES)
    credentials = flow.run_local_server(
        port=8080,
        redirect_uri_trailing_slash=False,
        prompt='consent' # Forces refresh token
    )
    
    # Save credentials using auth client
    auth_client.save_user_credentials(SERVICE_NAME, user_id, credentials)
    
    logger.info(f"Credentials saved for user {user_id}. You can now run the server.")
    return credentials

async def get_credentials(user_id):
    """Get credentials for the specified user"""
    # Get auth client
    auth_client = create_auth_client()
    
    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)
    
    if not credentials_data:
        logger.error(f"Credentials not found for user {user_id}. Please run with 'auth' argument first.")
        raise FileNotFoundError(f"Credentials not found for user {user_id}")
    
    # Convert to Google credentials object
    return Credentials.from_authorized_user_info(credentials_data)

async def create_drive_service(user_id):
    """Create a new Drive service instance for this request"""
    credentials = await get_credentials(user_id)
    return build('drive', 'v3', credentials=credentials)

def create_server(user_id):
    """Create a new server instance with optional user context"""
    server = Server("gdrive-server")
    
    server.user_id = user_id
    
    @server.list_resources()
    async def handle_list_resources(cursor: str = None) -> dict:
        """List files from Google Drive"""
        logger.info(f"Listing resources for user: {server.user_id} with cursor: {cursor}")
        
        drive_service = await create_drive_service(server.user_id)
        
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
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")
        
        drive_service = await create_drive_service(server.user_id)
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
        logger.info(f"Listing tools for user: {server.user_id}")
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
        logger.info(f"User {server.user_id} calling tool: {name} with arguments: {arguments}")
        
        if name == "search":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")
            
            drive_service = await create_drive_service(server.user_id)
            
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
    
    return server

def server(user_id):
    """Create a server instance with the given user ID"""
    return create_server(user_id)

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
        authenticate_and_save_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
