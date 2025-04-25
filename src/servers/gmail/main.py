import os
import sys
from typing import Optional, Iterable
from base64 import urlsafe_b64encode

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
import email.utils
import email.mime.text


SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_gmail_service(user_id, api_key=None):
    """Create a new Gmail service instance for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return build("gmail", "v1", credentials=credentials)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("gmail-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List emails from Gmail"""
        logger.info(
            f"Listing email resources for user: {server.user_id} with cursor: {cursor}"
        )

        gmail_service = await create_gmail_service(
            server.user_id, api_key=server.api_key
        )

        page_size = 10
        params = {
            "maxResults": page_size,
            "q": "is:unread",  # Default to unread messages
            "labelIds": ["INBOX"],
        }

        if cursor:
            params["pageToken"] = cursor

        results = gmail_service.users().messages().list(userId="me", **params).execute()
        messages = results.get("messages", [])

        resources = []
        for message in messages:
            # Get minimal message data (headers only)
            msg_data = (
                gmail_service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )

            # Extract subject from headers
            subject = "No Subject"
            sender = "Unknown"
            for header in msg_data.get("payload", {}).get("headers", []):
                if header["name"] == "Subject":
                    subject = header["value"]
                elif header["name"] == "From":
                    sender = header["value"]

            resource = Resource(
                uri=f"gmail://message/{message['id']}",
                mimeType="message/rfc822",
                name=f"{subject} - from {sender}",
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read an email from Gmail by URI"""
        logger.info(f"Reading email resource: {uri} for user: {server.user_id}")

        gmail_service = await create_gmail_service(
            server.user_id, api_key=server.api_key
        )
        message_id = str(uri).replace("gmail://message/", "")

        # Get full message data
        message = (
            gmail_service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )

        # Extract headers and parts
        headers = {}
        for header in message.get("payload", {}).get("headers", []):
            headers[header["name"]] = header["value"]

        # Extract the message body
        parts = []
        parts.append(f"From: {headers.get('From', 'Unknown')}")
        parts.append(f"To: {headers.get('To', 'Unknown')}")
        parts.append(f"Date: {headers.get('Date', 'Unknown')}")
        parts.append(f"Subject: {headers.get('Subject', 'No Subject')}")
        parts.append("")

        # Extract body content (simplified - assumes plain text for demo)
        def extract_body(payload):
            if (
                "body" in payload
                and "data" in payload["body"]
                and payload["body"]["data"]
            ):
                import base64

                return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
            elif "parts" in payload:
                for part in payload["parts"]:
                    if part.get("mimeType") == "text/plain":
                        body_data = part.get("body", {}).get("data", "")
                        if body_data:
                            import base64

                            return base64.urlsafe_b64decode(body_data).decode("utf-8")
            return "No text content available"

        body = extract_body(message.get("payload", {}))
        parts.append(body)

        email_content = "\n".join(parts)
        return [ReadResourceContents(content=email_content, mime_type="text/plain")]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available email tools"""
        logger.info(f"Listing email tools for user: {server.user_id}")
        return [
            Tool(
                name="read_emails",
                description="Search and read emails in Gmail",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'from:someone@example.com' or 'subject:important')",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of emails to return",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="send_email",
                description="Send an email through Gmail",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {
                            "type": "string",
                            "description": "Email body (plain text)",
                        },
                        "cc": {
                            "type": "string",
                            "description": "CC recipients (comma separated)",
                        },
                        "bcc": {
                            "type": "string",
                            "description": "BCC recipients (comma separated)",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            ),
            Tool(
                name="update_email",
                description="Update email labels (mark as read/unread, move to folders)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to modify",
                        },
                        "add_labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to add (e.g., 'INBOX', 'STARRED', 'IMPORTANT')",
                        },
                        "remove_labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to remove (e.g., 'UNREAD')",
                        },
                    },
                    "required": ["email_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle email tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        gmail_service = await create_gmail_service(
            server.user_id, api_key=server.api_key
        )

        if name == "read_emails":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            query = arguments["query"]
            max_results = int(arguments.get("max_results", 10))

            results = (
                gmail_service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return [
                    TextContent(
                        type="text", text="No emails found matching your query."
                    )
                ]

            email_summaries = []
            for message in messages:
                msg = (
                    gmail_service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message["id"],
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date"],
                    )
                    .execute()
                )

                # Extract headers
                subject = "No Subject"
                sender = "Unknown"
                date = "Unknown"
                for header in msg.get("payload", {}).get("headers", []):
                    if header["name"] == "Subject":
                        subject = header["value"]
                    elif header["name"] == "From":
                        sender = header["value"]
                    elif header["name"] == "Date":
                        date = header["value"]

                # Get labels
                labels = msg.get("labelIds", [])
                is_unread = "UNREAD" in labels

                email_summaries.append(
                    f"ID: {message['id']}\n"
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Date: {date}\n"
                    f"Status: {'Unread' if is_unread else 'Read'}\n"
                    f"Labels: {', '.join(labels)}\n"
                )

            result = f"Found {len(messages)} emails:\n\n" + "\n---\n".join(
                email_summaries
            )
            return [TextContent(type="text", text=result)]

        elif name == "send_email":
            if not arguments or not all(
                k in arguments for k in ["to", "subject", "body"]
            ):
                raise ValueError("Missing required parameters: to, subject, body")

            # Create email message
            message = email.mime.text.MIMEText(arguments["body"])
            message["to"] = arguments["to"]
            message["subject"] = arguments["subject"]

            # Add optional CC and BCC if provided
            if "cc" in arguments and arguments["cc"]:
                message["cc"] = arguments["cc"]
            if "bcc" in arguments and arguments["bcc"]:
                message["bcc"] = arguments["bcc"]

            # Encode the message
            raw_message = urlsafe_b64encode(message.as_bytes()).decode()

            # Send the message
            try:
                sent_message = (
                    gmail_service.users()
                    .messages()
                    .send(userId="me", body={"raw": raw_message})
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Email sent successfully to {arguments['to']}. Message ID: {sent_message['id']}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to send email: {str(e)}")
                ]

        elif name == "update_email":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing email_id parameter")

            email_id = arguments["email_id"]
            add_labels = arguments.get("add_labels", [])
            remove_labels = arguments.get("remove_labels", [])

            if not add_labels and not remove_labels:
                return [
                    TextContent(
                        type="text",
                        text="No label changes specified. Please provide labels to add or remove.",
                    )
                ]

            # Modify labels
            try:
                result = (
                    gmail_service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=email_id,
                        body={
                            "addLabelIds": add_labels,
                            "removeLabelIds": remove_labels,
                        },
                    )
                    .execute()
                )

                # Get updated labels
                updated_labels = result.get("labelIds", [])

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully updated email {email_id}.\n"
                        f"Added labels: {', '.join(add_labels) if add_labels else 'None'}\n"
                        f"Removed labels: {', '.join(remove_labels) if remove_labels else 'None'}\n"
                        f"Current labels: {', '.join(updated_labels)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to update email: {str(e)}")
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gmail-server",
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
