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
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_drive_service(user_id, api_key=None):
    """Create a new Drive service instance for this request"""
    service_name = SERVICE_NAME
    # If using Gumloop's hosted MCP Server, we'll use the Google Drive credential here
    if os.getenv("ENVIRONMENT") == "gumloop":
        service_name = "gdrive"

    credentials = await get_credentials(user_id, service_name, api_key=api_key)
    return build("drive", "v3", credentials=credentials)


async def create_docs_service(user_id, api_key=None):
    """Create a new Docs service instance for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return build("docs", "v1", credentials=credentials)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("gdocs-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Google Docs from Google Drive"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        drive_service = await create_drive_service(
            server.user_id, api_key=server.api_key
        )

        page_size = 20
        params = {
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType)",
            "q": "mimeType='application/vnd.google-apps.document'",
        }

        if cursor:
            params["pageToken"] = cursor

        results = drive_service.files().list(**params).execute()
        files = results.get("files", [])

        resources = []
        for file in files:
            resource = Resource(
                uri=f"gdocs://document/{file['id']}",
                mimeType="application/vnd.google-apps.document",
                name=file["name"],
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a Google Doc by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        # New URI format: gdocs://document/{doc_id}
        uri_str = str(uri)
        doc_id = uri_str.split("/")[-1]

        docs_service = await create_docs_service(server.user_id, api_key=server.api_key)

        # Get the document content
        document = docs_service.documents().get(documentId=doc_id).execute()

        # Extract text content from document
        doc_content = document.get("body", {}).get("content", [])
        text_content = ""

        def extract_text(elements):
            nonlocal text_content
            for element in elements:
                if "paragraph" in element:
                    for para_element in element["paragraph"]["elements"]:
                        if "textRun" in para_element:
                            text_content += para_element["textRun"].get("content", "")
                elif "table" in element:
                    for row in element["table"].get("tableRows", []):
                        for cell in row.get("tableCells", []):
                            extract_text(cell.get("content", []))
                elif "tableOfContents" in element:
                    extract_text(element["tableOfContents"].get("content", []))

        extract_text(doc_content)

        return [ReadResourceContents(content=text_content, mime_type="text/plain")]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_docs",
                description="Search for Google Docs in Drive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_doc",
                description="Create a new Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Document title"},
                        "content": {
                            "type": "string",
                            "description": "Document content",
                        },
                    },
                    "required": ["title", "content"],
                },
            ),
            Tool(
                name="append_to_doc",
                description="Append content to an existing Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID"},
                        "content": {
                            "type": "string",
                            "description": "Content to append",
                        },
                    },
                    "required": ["doc_id", "content"],
                },
            ),
            Tool(
                name="update_doc",
                description="Update content in an existing Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "doc_id": {"type": "string", "description": "Document ID"},
                        "content": {
                            "type": "string",
                            "description": "New document content",
                        },
                    },
                    "required": ["doc_id", "content"],
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

        if name == "search_docs":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            drive_service = await create_drive_service(
                server.user_id, api_key=server.api_key
            )

            user_query = arguments["query"]
            escaped_query = user_query.replace("\\", "\\\\").replace("'", "\\'")
            formatted_query = f"mimeType='application/vnd.google-apps.document' and fullText contains '{escaped_query}'"

            results = (
                drive_service.files()
                .list(
                    q=formatted_query,
                    pageSize=10,
                    fields="files(id, name, modifiedTime)",
                )
                .execute()
            )

            files = results.get("files", [])
            file_list = "\n".join(
                [
                    f"{file['name']} (URI: gdocs://document/{file['id']}, Modified: {file['modifiedTime']})"
                    for file in files
                ]
            )

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(files)} Google Docs matching '{user_query}':\n{file_list}",
                )
            ]

        elif name == "create_doc":
            if not arguments or "title" not in arguments or "content" not in arguments:
                raise ValueError("Missing required parameters: title and content")

            title = arguments["title"]
            content = arguments["content"]

            # First create an empty document
            drive_service = await create_drive_service(
                server.user_id, api_key=server.api_key
            )

            docs_service = await create_docs_service(
                server.user_id, api_key=server.api_key
            )

            # Create the document
            doc_metadata = {
                "name": title,
                "mimeType": "application/vnd.google-apps.document",
            }

            doc = drive_service.files().create(body=doc_metadata).execute()
            doc_id = doc.get("id")

            # Now add content to the document
            requests = [
                {
                    "insertText": {
                        "location": {
                            "index": 1,
                        },
                        "text": content,
                    }
                }
            ]

            docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()

            return [
                TextContent(
                    type="text",
                    text=f"Created new Google Doc '{title}'\nResource URI: gdocs://document/{doc_id}\nDocument link: https://docs.google.com/document/d/{doc_id}/edit",
                )
            ]

        elif name == "append_to_doc":
            if not arguments or "doc_id" not in arguments or "content" not in arguments:
                raise ValueError("Missing required parameters: doc_id and content")

            doc_id = arguments["doc_id"]
            content = arguments["content"]

            docs_service = await create_docs_service(
                server.user_id, api_key=server.api_key
            )

            # Get the current document to find the end index
            document = docs_service.documents().get(documentId=doc_id).execute()

            # Find the end index of the document
            end_index = 1  # Default to beginning if document is empty
            for element in document.get("body", {}).get("content", []):
                if "endIndex" in element:
                    end_index = max(end_index, element["endIndex"])

            # Create append request
            requests = [
                {
                    "insertText": {
                        "location": {
                            "index": end_index
                            - 1,  # -1 to account for document end marker
                        },
                        "text": "\n" + content,  # Add new line before appending
                    }
                }
            ]

            result = (
                docs_service.documents()
                .batchUpdate(documentId=doc_id, body={"requests": requests})
                .execute()
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully appended content to Google Doc\nResource URI: gdocs://document/{doc_id}\nDocument link: https://docs.google.com/document/d/{doc_id}/edit",
                )
            ]

        elif name == "update_doc":
            if not arguments or "doc_id" not in arguments or "content" not in arguments:
                raise ValueError("Missing required parameters: doc_id and content")

            doc_id = arguments["doc_id"]
            content = arguments["content"]

            docs_service = await create_docs_service(
                server.user_id, api_key=server.api_key
            )

            # Get the document to determine its size
            document = docs_service.documents().get(documentId=doc_id).execute()

            # Find the end index of the document
            end_index = 1
            for element in document.get("body", {}).get("content", []):
                if "endIndex" in element:
                    end_index = max(end_index, element["endIndex"])

            # First delete all content
            requests = [
                {
                    "deleteContentRange": {
                        "range": {"startIndex": 1, "endIndex": end_index - 1}
                    }
                },
                {
                    "insertText": {
                        "location": {
                            "index": 1,
                        },
                        "text": content,
                    }
                },
            ]

            result = (
                docs_service.documents()
                .batchUpdate(documentId=doc_id, body={"requests": requests})
                .execute()
            )

            return [
                TextContent(
                    type="text",
                    text=f"Successfully updated Google Doc\nResource URI: gdocs://document/{doc_id}\nDocument link: https://docs.google.com/document/d/{doc_id}/edit",
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gdocs-server",
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
