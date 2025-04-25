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

import json
import logging
from html import unescape
from pathlib import Path

import requests
from bs4 import BeautifulSoup

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

from src.utils.microsoft.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "offline_access",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_outlook_client(user_id, api_key=None):
    """Create a new Outlook client for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return credentials


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("outlook-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List email folders from Outlook"""
        logger.info(f"Listing folders for user: {server.user_id} with cursor: {cursor}")

        access_token = await create_outlook_client(
            server.user_id, api_key=server.api_key
        )

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            "https://graph.microsoft.com/v1.0/me/mailFolders",
            headers=headers,
        )

        if response.status_code != 200:
            logger.error(
                f"Error listing folders: {response.status_code} {response.text}"
            )
            return []

        data = response.json()
        folders = data.get("value", [])

        resources = []
        for folder in folders:
            folder_id = folder.get("id")
            display_name = folder.get("displayName", "Unknown Folder")
            total_items = folder.get("totalItemCount", 0)

            resource = Resource(
                uri=f"outlook://folder/{folder_id}",
                name=display_name,
                description=f"{display_name} folder with {total_items} emails",
                mimeType="application/outlook.folder",
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read emails from a folder in Outlook by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await create_outlook_client(
            server.user_id, api_key=server.api_key
        )
        folder_id = str(uri).replace("outlook://folder/", "")

        page_size = 25
        params = {
            "$select": "id,subject,from,receivedDateTime,isRead",
            "$top": page_size,
            "$orderby": "receivedDateTime desc",
        }

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages",
            headers=headers,
            params=params,
        )

        if response.status_code != 200:
            logger.error(
                f"Error fetching emails in folder: {response.status_code} {response.text}"
            )
            return [
                ReadResourceContents(
                    content="Error fetching emails in this folder",
                    mime_type="text/plain",
                )
            ]

        emails_data = response.json()
        emails = emails_data.get("value", [])

        if not emails:
            return [
                ReadResourceContents(
                    content="No emails found in this folder", mime_type="text/plain"
                )
            ]

        formatted_emails = []
        for email in emails:
            email_id = email.get("id")
            subject = email.get("subject", "No Subject")
            from_name = email.get("from", {}).get("emailAddress", {}).get("name", "")
            from_email = (
                email.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
            )
            received_date = email.get("receivedDateTime", "")
            read_status = "Read" if email.get("isRead", False) else "Unread"

            email_entry = (
                f"ID: outlook://email/{email_id}\n"
                f"Subject: {subject}\n"
                f"From: {from_name} <{from_email}>\n"
                f"Date: {received_date}\n"
                f"Status: {read_status}\n"
            )
            formatted_emails.append(email_entry)

        all_emails = "\n---\n".join(formatted_emails)
        return [ReadResourceContents(content=all_emails, mime_type="text/plain")]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="read_emails",
                description="Read emails from Outlook. Fetches emails based on specified filters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder": {
                            "type": "string",
                            "description": "Folder to search in. Default is 'inbox'",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Number of emails to retrieve. Default is 10",
                        },
                        "filter": {
                            "type": "string",
                            "description": "Filter query. For example, 'isRead eq false' for unread emails",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search query for email content",
                        },
                    },
                },
            ),
            Tool(
                name="send_email",
                description="Send an email using Outlook",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email addresses (comma-separated)",
                        },
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body content"},
                        "cc": {
                            "type": "string",
                            "description": "CC email addresses (comma-separated)",
                        },
                        "bcc": {
                            "type": "string",
                            "description": "BCC email addresses (comma-separated)",
                        },
                    },
                    "required": ["to", "subject", "body"],
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

        access_token = await create_outlook_client(
            server.user_id, api_key=server.api_key
        )

        if name == "read_emails":
            try:
                folder = arguments.get("folder", "inbox").lower()
                count = int(arguments.get("count", 10))
                filter_query = arguments.get("filter", "")
                search_query = arguments.get("search", "")

                # Get folder ID
                folder_id = folder
                if folder != "inbox" and folder != "sentitems" and folder != "drafts":
                    # Try to look up folder ID if it's a custom folder
                    folder_id = get_folder_id(access_token, folder)

                # Build request parameters
                params = {
                    "$select": "id,subject,from,toRecipients,receivedDateTime,bodyPreview",
                    "$top": count,
                    "$orderby": "receivedDateTime desc",
                }

                if filter_query:
                    params["$filter"] = filter_query

                if search_query:
                    params["$search"] = f'"{search_query}"'

                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(
                    f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages",
                    headers=headers,
                    params=params,
                )

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error retrieving emails: {response.json().get('error', {}).get('message', 'Unknown error')}",
                        )
                    ]

                emails = response.json().get("value", [])

                if not emails:
                    return [
                        TextContent(
                            type="text", text="No emails found matching your criteria."
                        )
                    ]

                email_list = []
                for email in emails:
                    subject = email.get("subject", "No Subject")
                    from_name = (
                        email.get("from", {}).get("emailAddress", {}).get("name", "")
                    )
                    from_email = (
                        email.get("from", {})
                        .get("emailAddress", {})
                        .get("address", "Unknown")
                    )
                    date = email.get("receivedDateTime", "")
                    preview = email.get("bodyPreview", "")

                    email_info = (
                        f"Subject: {subject}\n"
                        f"From: {from_name} <{from_email}>\n"
                        f"Date: {date}\n"
                        f"Preview: {preview}\n"
                        f"ID: {email.get('id')}\n"
                    )
                    email_list.append(email_info)

                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(emails)} emails:\n\n"
                        + "\n---\n".join(email_list),
                    )
                ]

            except Exception as e:
                logger.error(f"Error in read_emails: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        elif name == "send_email":
            try:
                to_recipients = arguments.get("to", "").split(",")
                cc_recipients = (
                    arguments.get("cc", "").split(",") if arguments.get("cc") else []
                )
                bcc_recipients = (
                    arguments.get("bcc", "").split(",") if arguments.get("bcc") else []
                )
                subject = arguments.get("subject", "")
                body = arguments.get("body", "")

                if not to_recipients or not subject or not body:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (to, subject, body)",
                        )
                    ]

                # Prepare recipients in the format expected by Microsoft Graph
                to_list = [
                    {"emailAddress": {"address": email.strip()}}
                    for email in to_recipients
                    if email.strip()
                ]
                cc_list = [
                    {"emailAddress": {"address": email.strip()}}
                    for email in cc_recipients
                    if email.strip()
                ]
                bcc_list = [
                    {"emailAddress": {"address": email.strip()}}
                    for email in bcc_recipients
                    if email.strip()
                ]

                # Prepare the email payload
                email_payload = {
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "Text", "content": body},
                        "toRecipients": to_list,
                        "ccRecipients": cc_list,
                        "bccRecipients": bcc_list,
                    },
                    "saveToSentItems": "true",
                }

                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }

                response = requests.post(
                    "https://graph.microsoft.com/v1.0/me/sendMail",
                    headers=headers,
                    data=json.dumps(email_payload),
                )

                if response.status_code == 202:
                    return [
                        TextContent(
                            type="text",
                            text=f"Email sent successfully to {', '.join(to_recipients)}",
                        )
                    ]
                else:
                    error_message = (
                        response.json().get("error", {}).get("message", "Unknown error")
                    )
                    return [
                        TextContent(
                            type="text", text=f"Failed to send email: {error_message}"
                        )
                    ]

            except Exception as e:
                logger.error(f"Error in send_email: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


def get_folder_id(access_token, folder_name):
    """Get folder ID by name"""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        "https://graph.microsoft.com/v1.0/me/mailFolders", headers=headers
    )

    if response.status_code != 200:
        return "inbox"  # Default to inbox if folder lookup fails

    folders = response.json().get("value", [])

    for folder in folders:
        if folder.get("displayName", "").lower() == folder_name.lower():
            return folder.get("id")

    return "inbox"  # Default to inbox if folder not found


def extract_text_from_html(html_content):
    """Extract plain text from HTML content"""
    soup = BeautifulSoup(html_content, "html.parser")
    extracted_text = unescape(soup.get_text())

    # Cleanup: Replace multiple newlines with a single newline
    cleaned_text = "\n".join(
        line for line in extracted_text.splitlines() if line.strip()
    )

    # Replace newlines with the combination of carriage return and newline
    formatted_text = cleaned_text.replace("\n", "\r\n")

    # Replace non-breaking spaces with regular spaces
    formatted_text = formatted_text.replace("\xa0", " ")

    return formatted_text


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="outlook-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the MCP server framework.")
