import os
import sys
import json
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
        """List Gmail labels as resources"""
        logger.info(
            f"Listing label resources for user: {server.user_id} with cursor: {cursor}"
        )

        gmail_service = await create_gmail_service(
            server.user_id, api_key=server.api_key
        )

        try:
            # Get all labels
            results = gmail_service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            resources = []
            for label in labels:
                # Skip system labels that aren't useful to show
                if label.get("type") == "system" and label.get("id") in [
                    "CHAT",
                    "SENT",
                    "SPAM",
                    "TRASH",
                    "DRAFT",
                ]:
                    continue

                label_id = label.get("id")
                label_name = label.get("name", "Unknown Label")

                # Get message count for this label
                label_data = (
                    gmail_service.users()
                    .labels()
                    .get(userId="me", id=label_id)
                    .execute()
                )
                total_messages = label_data.get("messagesTotal", 0)
                unread_messages = label_data.get("messagesUnread", 0)

                description = (
                    f"{label_name} ({unread_messages} unread of {total_messages} total)"
                )

                resource = Resource(
                    uri=f"gmail://label/{label_id}",
                    mimeType="application/gmail.label",
                    name=label_name,
                    description=description,
                )
                resources.append(resource)

            return resources
        except Exception as e:
            logger.error(f"Error listing Gmail labels: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read emails from a Gmail label"""
        logger.info(f"Reading label resource: {uri} for user: {server.user_id}")

        gmail_service = await create_gmail_service(
            server.user_id, api_key=server.api_key
        )

        uri_str = str(uri)
        if not uri_str.startswith("gmail://label/"):
            raise ValueError(f"Invalid Gmail label URI: {uri_str}")

        label_id = uri_str.replace("gmail://label/", "")

        # Get messages in this label
        results = (
            gmail_service.users()
            .messages()
            .list(userId="me", labelIds=[label_id], maxResults=10)
            .execute()
        )

        messages = results.get("messages", [])

        if not messages:
            return [
                ReadResourceContents(
                    content="No messages in this label", mime_type="text/plain"
                )
            ]

        # Format messages
        formatted_messages = []

        for message in messages:
            # Get message data
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

            # Extract headers
            headers = {}
            for header in msg_data.get("payload", {}).get("headers", []):
                headers[header["name"]] = header["value"]

            subject = headers.get("Subject", "No Subject")
            sender = headers.get("From", "Unknown")
            date = headers.get("Date", "Unknown date")

            # Format message summary
            message_summary = (
                f"ID: gmail://message/{message['id']}\n"
                f"Subject: {subject}\n"
                f"From: {sender}\n"
                f"Date: {date}\n"
                f"---\n"
            )
            formatted_messages.append(message_summary)

        content = "\n".join(formatted_messages)
        return [ReadResourceContents(content=content, mime_type="text/plain")]

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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Email details including ID, thread ID, labels, headers, and content",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["INBOX", "UNREAD"], "subject": "Meeting Tomorrow", "from": "colleague@example.com", "to": "you@example.com", "date": "Mon, 01 Jan 2023 10:00:00 -0700", "body": "Let\'s discuss the project tomorrow.", "attachments": [], "hasAttachments": false}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="send_email",
                description="Send a new email or reply to an existing thread",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address(es), comma separated",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject",
                        },
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
                        "thread_id": {
                            "type": "string",
                            "description": "Optional: Thread ID to reply to (creates reply in thread)",
                        },
                        "in_reply_to": {
                            "type": "string",
                            "description": "Optional: Message ID to reply to (for threaded conversations)",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the sent email including ID and thread ID",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["SENT", "INBOX"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated email details with modified labels",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["INBOX", "STARRED"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="create_draft",
                description="Prepare emails without sending them",
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
                        "thread_id": {
                            "type": "string",
                            "description": "Optional thread ID to create a draft reply in an existing thread",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Draft email details including ID and message information",
                    "examples": [
                        '{"id": "r123456789", "message": {"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["DRAFT"]}}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="forward_email",
                description="Forward an email to other recipients",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to forward",
                        },
                        "to": {
                            "type": "string",
                            "description": "Recipient email address(es), comma separated",
                        },
                        "additional_text": {
                            "type": "string",
                            "description": "Additional text to include with the forwarded email",
                        },
                    },
                    "required": ["email_id", "to"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Forwarded email details including ID and labels",
                    "examples": [
                        '{"id": "f1g2h3i4j5k6", "threadId": "f1g2h3i4j5k6", "labelIds": ["SENT", "UNREAD", "INBOX"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="create_label",
                description="Create a new Gmail label for organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the new label",
                        },
                        "background_color": {
                            "type": "string",
                            "description": "Optional background color (hex code)",
                        },
                        "text_color": {
                            "type": "string",
                            "description": "Optional text color (hex code)",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created label details including ID and visibility settings",
                    "examples": [
                        '{"id": "Label_123", "name": "Important Projects", "messageListVisibility": "show", "labelListVisibility": "labelShow"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="archive_email",
                description="Move emails out of inbox",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to archive",
                        },
                    },
                    "required": ["email_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Archived email details with updated labels",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["SENT"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="trash_email",
                description="Move emails to trash",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to move to trash",
                        },
                    },
                    "required": ["email_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Trashed email details showing TRASH label",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["TRASH", "SENT"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="star_email",
                description="Flag an email as important by adding a star",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to star",
                        },
                    },
                    "required": ["email_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Starred email details showing STARRED label",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["STARRED", "SENT", "INBOX"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="unstar_email",
                description="Remove the star flag from an email",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to unstar",
                        },
                    },
                    "required": ["email_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Unstarred email details with STARRED label removed",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["SENT", "INBOX"]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="get_attachment_details",
                description="Get details about attachments in an email",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID to get attachment details from",
                        },
                    },
                    "required": ["email_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Complete email message with detailed attachment information",
                    "examples": [
                        '{"id": "a1b2c3d4e5f6", "threadId": "a1b2c3d4e5f6", "labelIds": ["INBOX"], "payload": {"mimeType": "multipart/mixed", "parts": [{"partId": "0", "mimeType": "text/plain"}, {"partId": "1", "mimeType": "application/pdf", "filename": "document.pdf", "body": {"attachmentId": "attachment_id_123", "size": 5000}}]}}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
            ),
            Tool(
                name="download_attachment",
                description="Generate a download link for an email attachment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "Email ID that contains the attachment",
                        },
                        "attachment_id": {
                            "type": "string",
                            "description": "ID of the attachment to download",
                        },
                        "filename": {
                            "type": "string",
                            "description": "Filename to save the attachment as",
                        },
                    },
                    "required": ["email_id", "attachment_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Attachment download information including content data",
                    "examples": [
                        '{"filename": "document.pdf", "mimeType": "application/pdf", "size": 5000, "data": "base64_encoded_content_truncated_for_brevity", "downloadUrl": "temporary_download_url"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/gmail.modify"],
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

            emails = []
            for message in messages:
                msg = (
                    gmail_service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message["id"],
                        format="full",
                    )
                    .execute()
                )

                # Process the message to extract readable content
                readable_msg = {}
                readable_msg["id"] = msg.get("id", "")
                readable_msg["threadId"] = msg.get("threadId", "")
                readable_msg["labelIds"] = msg.get("labelIds", [])

                # Extract headers
                headers = {}
                if "payload" in msg and "headers" in msg["payload"]:
                    for header in msg["payload"]["headers"]:
                        headers[header["name"].lower()] = header["value"]

                readable_msg["subject"] = headers.get("subject", "No Subject")
                readable_msg["from"] = headers.get("from", "Unknown")
                readable_msg["to"] = headers.get("to", "Unknown")
                readable_msg["date"] = headers.get("date", "Unknown")

                # Extract plain text content
                body_text = ""
                if "payload" in msg:
                    body_text = extract_text_from_payload(msg["payload"])

                readable_msg["body"] = body_text or msg.get("snippet", "")

                # Extract attachment info (if any)
                attachments = []
                if "payload" in msg and "parts" in msg["payload"]:
                    for part in msg["payload"]["parts"]:
                        if "filename" in part and part["filename"]:
                            attachment = {
                                "filename": part.get("filename", ""),
                                "mimeType": part.get("mimeType", ""),
                                "attachmentId": part.get("body", {}).get(
                                    "attachmentId", ""
                                ),
                                "size": part.get("body", {}).get("size", 0),
                            }
                            attachments.append(attachment)

                readable_msg["attachments"] = attachments
                readable_msg["hasAttachments"] = len(attachments) > 0

                emails.append(
                    TextContent(
                        type="text", text=f"{json.dumps(readable_msg, indent=4)}"
                    )
                )

            return emails

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

            # Initialize the send parameters
            send_params = {"userId": "me"}
            body_params = {}

            # Handle thread_id if provided (for reply functionality)
            if "thread_id" in arguments and arguments["thread_id"]:
                thread_id = arguments["thread_id"]

                # Add Re: to subject if needed for replies
                if not arguments["subject"].lower().startswith("re:"):
                    message["subject"] = f"Re: {arguments['subject']}"

                # Set In-Reply-To header if provided
                if "in_reply_to" in arguments and arguments["in_reply_to"]:
                    message["In-Reply-To"] = arguments["in_reply_to"]
                    # Set References header for threading
                    message["References"] = arguments["in_reply_to"]

                # Include threadId in the message parameters
                body_params["threadId"] = thread_id

            # Encode the message
            raw_message = urlsafe_b64encode(message.as_bytes()).decode()
            body_params["raw"] = raw_message

            # Send the message
            try:
                sent_message = (
                    gmail_service.users()
                    .messages()
                    .send(userId="me", body=body_params)
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(sent_message, indent=4)}",
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
                        text=f"{json.dumps(result, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to update email: {str(e)}")
                ]

        elif name == "create_draft":
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

            # Create the draft
            try:
                draft_body = {"message": {"raw": raw_message}}

                # Add thread ID if provided for creating a draft reply
                if "thread_id" in arguments and arguments["thread_id"]:
                    draft_body["message"]["threadId"] = arguments["thread_id"]

                # Get the raw API response
                draft = (
                    gmail_service.users()
                    .drafts()
                    .create(userId="me", body=draft_body)
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(draft, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to create draft: {str(e)}")
                ]
        elif name == "forward_email":
            if not arguments or not all(k in arguments for k in ["email_id", "to"]):
                raise ValueError("Missing required parameters: email_id, to")

            email_id = arguments["email_id"]
            to_addresses = arguments["to"]
            additional_text = arguments.get("additional_text", "")

            try:
                # Get the original message
                original_message = (
                    gmail_service.users()
                    .messages()
                    .get(userId="me", id=email_id, format="full")
                    .execute()
                )

                # Extract message details
                headers = {}
                for header in original_message.get("payload", {}).get("headers", []):
                    name = header.get("name", "").lower()
                    if name in ["from", "to", "subject", "date"]:
                        headers[name] = header.get("value", "")

                # Prepare forwarded message
                # Create raw message from original
                # For simplicity, we'll create a new message that references the original
                subject = headers.get("subject", "")
                if not subject.lower().startswith("fwd:"):
                    subject = f"Fwd: {subject}"

                # Original message headers to include in forwarded message
                orig_from = headers.get("from", "Unknown")
                orig_date = headers.get("date", "Unknown")
                orig_to = headers.get("to", "Unknown")

                # Create a simplified forwarded message
                forward_msg = email.mime.text.MIMEText(
                    f"{additional_text}\n\n"
                    f"---------- Forwarded message ----------\n"
                    f"From: {orig_from}\n"
                    f"Date: {orig_date}\n"
                    f"Subject: {headers.get('subject', '')}\n"
                    f"To: {orig_to}\n\n"
                    f"{original_message.get('snippet', '')}\n"
                )

                # Set new headers
                forward_msg["To"] = to_addresses
                forward_msg["Subject"] = subject

                # Encode the message
                raw_message = urlsafe_b64encode(forward_msg.as_bytes()).decode()

                # Send the forwarded message
                forwarded_message = (
                    gmail_service.users()
                    .messages()
                    .send(userId="me", body={"raw": raw_message})
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(forwarded_message, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to forward email: {str(e)}")
                ]

        elif name == "list_labels":
            try:
                include_system = (
                    arguments.get("include_system", True) if arguments else True
                )

                # Get all labels
                results = gmail_service.users().labels().list(userId="me").execute()
                labels = results.get("labels", [])

                # Filter out system labels if requested
                if not include_system:
                    labels = [
                        label for label in labels if label.get("type") != "system"
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(results, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to list labels: {str(e)}")
                ]

        elif name == "create_label":
            if not arguments or "name" not in arguments:
                raise ValueError("Missing required parameter: name")

            label_name = arguments["name"]
            background_color = arguments.get("background_color")
            text_color = arguments.get("text_color")

            try:
                # Prepare the label object
                label_object = {
                    "name": label_name,
                    "messageListVisibility": "show",
                    "labelListVisibility": "labelShow",
                }

                # Add color information if provided
                if background_color or text_color:
                    label_object["color"] = {}
                    if background_color:
                        label_object["color"]["backgroundColor"] = background_color
                    if text_color:
                        label_object["color"]["textColor"] = text_color

                # Create the label
                created_label = (
                    gmail_service.users()
                    .labels()
                    .create(userId="me", body=label_object)
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(created_label, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to create label: {str(e)}")
                ]

        elif name == "archive_email":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing required parameter: email_id")

            email_id = arguments["email_id"]

            try:
                # Archive by removing INBOX label
                result = (
                    gmail_service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=email_id,
                        body={"removeLabelIds": ["INBOX"]},
                    )
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to archive email: {str(e)}")
                ]

        elif name == "trash_email":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing required parameter: email_id")

            email_id = arguments["email_id"]

            try:
                # Move to trash
                result = (
                    gmail_service.users()
                    .messages()
                    .trash(userId="me", id=email_id)
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to trash email: {str(e)}")
                ]

        elif name == "star_email":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing required parameter: email_id")

            email_id = arguments["email_id"]

            try:
                # Add STARRED label to the email
                result = (
                    gmail_service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=email_id,
                        body={"addLabelIds": ["STARRED"]},
                    )
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to star email: {str(e)}")
                ]

        elif name == "unstar_email":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing required parameter: email_id")

            email_id = arguments["email_id"]

            try:
                # Remove STARRED label from the email
                result = (
                    gmail_service.users()
                    .messages()
                    .modify(
                        userId="me",
                        id=email_id,
                        body={"removeLabelIds": ["STARRED"]},
                    )
                    .execute()
                )

                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(result, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to unstar email: {str(e)}")
                ]

        elif name == "get_attachment_details":
            if not arguments or "email_id" not in arguments:
                raise ValueError("Missing required parameter: email_id")

            email_id = arguments["email_id"]

            try:
                # Get the email message with full details
                message = (
                    gmail_service.users()
                    .messages()
                    .get(userId="me", id=email_id, format="full")
                    .execute()
                )

                # Return the raw API response
                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(message, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Failed to get message details: {str(e)}"
                    )
                ]

        elif name == "download_attachment":
            if not arguments or not all(
                k in arguments for k in ["email_id", "attachment_id"]
            ):
                raise ValueError("Missing required parameters: email_id, attachment_id")

            email_id = arguments["email_id"]
            attachment_id = arguments["attachment_id"]

            try:
                # Get the attachment
                attachment = (
                    gmail_service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=email_id, id=attachment_id)
                    .execute()
                )

                # Return the raw API response
                return [
                    TextContent(
                        type="text",
                        text=f"{json.dumps(attachment, indent=4)}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Failed to get attachment: {str(e)}")
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


def extract_text_from_payload(payload):
    """Extract readable text from message payload, handling base64 encoding"""
    if not payload:
        return ""

    # If this part is plain text and has a body
    if (
        payload.get("mimeType") == "text/plain"
        and "body" in payload
        and "data" in payload["body"]
    ):
        try:
            import base64

            data = payload["body"]["data"]
            # Replace URL-safe characters back to normal base64
            data = data.replace("-", "+").replace("_", "/")
            # Add padding if needed
            padding = len(data) % 4
            if padding:
                data += "=" * (4 - padding)
            # Decode base64 to bytes, then to string
            text = base64.b64decode(data).decode("utf-8", errors="replace")
            return text
        except Exception as e:
            return f"[Error decoding text: {str(e)}]"

    # If this is multipart, recursively extract text from parts
    if "parts" in payload:
        text_parts = []
        for part in payload["parts"]:
            # Skip attachments
            if part.get("filename"):
                continue
            # Process text parts
            if part.get("mimeType", "").startswith("text/"):
                text_parts.append(extract_text_from_payload(part))
            # Handle nested multipart
            elif part.get("mimeType", "").startswith("multipart/"):
                text_parts.append(extract_text_from_payload(part))

        return "\n".join(filter(None, text_parts))

    return ""
