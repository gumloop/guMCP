import os
import sys
from typing import Optional, Iterable
import json
import uuid  # Add import for uuid

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx

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

from src.utils.intercom.utils import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
INTERCOM_API_URL = "https://api.intercom.io"
SCOPES = [
    "read",
    "write",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def execute_intercom_request(
    method, path, data=None, params=None, access_token=None
):
    """Execute a request against the Intercom API"""
    if not access_token:
        raise ValueError("Intercom access token is required")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Intercom-Version": "2.9",
    }

    url = f"{INTERCOM_API_URL}/{path}"

    async with httpx.AsyncClient() as client:
        if method.lower() == "get":
            response = await client.get(url, params=params, headers=headers)
        elif method.lower() == "post":
            response = await client.post(url, json=data, headers=headers)
        elif method.lower() == "put":
            response = await client.put(url, json=data, headers=headers)
        elif method.lower() == "delete":
            response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response_data = response.json()
        response.raise_for_status()
        return response_data


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("intercom-server")

    server.user_id = user_id

    async def get_intercom_client():
        """Get Intercom access token for the current user"""
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return access_token

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List conversations from Intercom"""
        access_token = await get_intercom_client()

        params = {}
        if cursor:
            params["starting_after"] = cursor

        try:
            tags_result = await execute_intercom_request(
                "get", "tags", params=None, access_token=access_token
            )

            tags = tags_result.get("data", [])
            tag_resources = []

            for tag in tags:
                tag_resources.append(
                    Resource(
                        uri=f"intercom:///tag/{tag['id']}",
                        mimeType="application/json",
                        name=f"Tag: {tag['name']}",
                    )
                )

            conversations_result = await execute_intercom_request(
                "get", "conversations", params=params, access_token=access_token
            )

            conversations = conversations_result.get("conversations", [])
            conversation_resources = []

            for conversation in conversations:
                title = f"Conversation with {conversation.get('source', {}).get('author', {}).get('name', 'Unknown')}"

                conversation_resources.append(
                    Resource(
                        uri=f"intercom:///conversation/{conversation['id']}",
                        mimeType="application/json",
                        name=title,
                    )
                )

            contacts_result = await execute_intercom_request(
                "get", "contacts", params=params, access_token=access_token
            )

            contacts = contacts_result.get("data", [])
            contact_resources = []

            for contact in contacts:
                contact_type = "User" if contact.get("role") == "user" else "Lead"
                name = contact.get("name", "Unnamed Contact")
                email = contact.get("email", "No Email")

                contact_resources.append(
                    Resource(
                        uri=f"intercom:///contact/{contact['id']}",
                        mimeType="application/json",
                        name=f"{contact_type}: {name} ({email})",
                    )
                )

            return tag_resources + conversation_resources + contact_resources

        except Exception as e:
            import traceback

            logger.error(f"Error fetching Intercom resources: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from Intercom by URI"""
        access_token = await get_intercom_client()
        uri_str = str(uri)

        if uri_str.startswith("intercom:///tag/"):
            tag_id = uri_str.replace("intercom:///tag/", "")

            tag_result = await execute_intercom_request(
                "get", f"tags/{tag_id}", access_token=access_token
            )

            if not tag_result:
                raise ValueError(f"Tag not found: {tag_id}")

            formatted_content = json.dumps(tag_result, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        elif uri_str.startswith("intercom:///conversation/"):
            conversation_id = uri_str.replace("intercom:///conversation/", "")

            conversation_result = await execute_intercom_request(
                "get", f"conversations/{conversation_id}", access_token=access_token
            )

            if not conversation_result:
                raise ValueError(f"Conversation not found: {conversation_id}")

            formatted_content = json.dumps(conversation_result, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        elif uri_str.startswith("intercom:///contact/"):
            contact_id = uri_str.replace("intercom:///contact/", "")

            contact_result = await execute_intercom_request(
                "get", f"contacts/{contact_id}", access_token=access_token
            )

            if not contact_result:
                raise ValueError(f"Contact not found: {contact_id}")

            formatted_content = json.dumps(contact_result, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        raise ValueError(f"Unsupported resource URI: {uri_str}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Intercom"""
        return [
            Tool(
                name="search_contacts",
                description="Search for contacts in Intercom by name or email",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for contacts (name or email)",
                        }
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_contact",
                description="Create a new contact in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email of the contact",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the contact",
                        },
                        "role": {
                            "type": "string",
                            "description": "Role of the contact (user or lead)",
                            "enum": ["user", "lead"],
                        },
                        "custom_attributes": {
                            "type": "object",
                            "description": "Custom attributes for the contact (optional)",
                        },
                    },
                    "required": ["email"],
                },
            ),
            Tool(
                name="create_conversation",
                description="Create a new conversation in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "ID of the contact to create conversation with",
                        },
                        "message": {
                            "type": "string",
                            "description": "Initial message for the conversation",
                        },
                        "admin_id": {
                            "type": "string",
                            "description": "ID of the admin initiating the conversation (optional)",
                        },
                        "tag_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tag IDs to apply to the conversation (optional)",
                        },
                    },
                    "required": ["contact_id", "message"],
                },
            ),
            Tool(
                name="reply_to_conversation",
                description="Reply to an existing conversation in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Reply message",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "ID of the contact/user sending the reply (use this for replies from contacts)",
                        },
                        "admin_id": {
                            "type": "string",
                            "description": "ID of the admin sending the reply (use this for replies from admins)",
                        },
                        "attachment_urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs of attachments to include (optional)",
                        },
                    },
                    "required": ["message"],
                },
            ),
            Tool(
                name="add_tags_to_conversation",
                description="Add tags to an existing conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "ID of the conversation to tag",
                        },
                        "tag_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of tags to apply to the conversation",
                        },
                    },
                    "required": ["conversation_id", "tag_ids"],
                },
            ),
            Tool(
                name="remove_tags_from_conversation",
                description="Remove tags from an existing conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "conversation_id": {
                            "type": "string",
                            "description": "ID of the conversation to untag",
                        },
                        "tag_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "IDs of tags to remove from the conversation",
                        },
                    },
                    "required": ["conversation_id", "tag_ids"],
                },
            ),
            Tool(
                name="list_admins",
                description="List all admins/team members in the Intercom workspace",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="search_companies",
                description="Search for companies in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for companies (name)",
                        }
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_company",
                description="Create a new company in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the company",
                        },
                        "company_id": {
                            "type": "string",
                            "description": "Unique identifier for the company in your system (optional)",
                        },
                        "website": {
                            "type": "string",
                            "description": "Website URL of the company (optional)",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Industry of the company (optional)",
                        },
                        "custom_attributes": {
                            "type": "object",
                            "description": "Custom attributes for the company (optional)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="associate_contact_with_company",
                description="Associate a contact with a company",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "ID of the contact",
                        },
                        "company_id": {
                            "type": "string",
                            "description": "ID of the company",
                        },
                    },
                    "required": ["contact_id", "company_id"],
                },
            ),
            Tool(
                name="list_articles",
                description="List articles",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "ID of the article collection (optional)",
                        }
                    },
                },
            ),
            Tool(
                name="retrieve_article",
                description="Retrieve articles by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "ID of the help center",
                        }
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="create_article",
                description="Create a new help center article",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the article",
                        },
                        "body": {
                            "type": "string",
                            "description": "HTML content of the article",
                        },
                        "author_id": {
                            "type": "string",
                            "description": "ID of the admin authoring the article",
                        },
                        "collection_id": {
                            "type": "string",
                            "description": "ID of the collection to add the article to (optional)",
                        },
                        "state": {
                            "type": "string",
                            "description": "State of the article",
                            "enum": ["draft", "published"],
                        },
                    },
                    "required": ["title", "body", "author_id"],
                },
            ),
            # Ticket management tools
            Tool(
                name="list_tickets",
                description="List support tickets in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": "Filter tickets by state (submitted, in_progress, waiting_on_customer, resolved)",
                            "enum": [
                                "submitted",
                                "in_progress",
                                "waiting_on_customer",
                                "resolved",
                                "all",
                            ],
                        },
                        "tag_id": {
                            "type": "string",
                            "description": "Filter tickets by tag ID (optional)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tickets to return (optional)",
                        },
                    },
                },
            ),
            Tool(
                name="get_ticket",
                description="Get details of a specific support ticket",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "ID of the ticket to retrieve",
                        }
                    },
                    "required": ["ticket_id"],
                },
            ),
            Tool(
                name="create_ticket",
                description="Create a new support ticket in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "ID of the contact associated with the ticket",
                        },
                        "ticket_type_id": {
                            "type": "string",
                            "description": "ID of the ticket type",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title/subject of the ticket",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the issue",
                        },
                        "company_id": {
                            "type": "string",
                            "description": "ID of the company to associate with the ticket (optional)",
                        },
                    },
                    "required": [
                        "contact_id",
                        "title",
                        "description",
                        "ticket_type_id",
                    ],
                },
            ),
            Tool(
                name="update_ticket",
                description="Update an existing support ticket in Intercom",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "ID of the ticket to update",
                        },
                        "title": {
                            "type": "string",
                            "description": "New title/subject of the ticket (optional)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description of the ticket (optional)",
                        },
                        "state": {
                            "type": "string",
                            "description": "New state of the ticket (optional)",
                            "enum": ["in_progress", "waiting_on_customer", "resolved"],
                        },
                        "admin_id": {
                            "type": "string",
                            "description": "ID of the admin to assign the ticket to (optional)",
                        },
                        "is_shared": {
                            "type": "boolean",
                            "description": "Whether the ticket is visible to users (optional)",
                        },
                    },
                    "required": ["ticket_id"],
                },
            ),
            Tool(
                name="add_comment_to_ticket",
                description="Add a comment to an existing support ticket",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "ID of the ticket to add a comment to",
                        },
                        "comment": {
                            "type": "string",
                            "description": "Content of the comment",
                        },
                        "admin_id": {
                            "type": "string",
                            "description": "ID of the admin adding the comment (required)",
                        },
                        "message_type": {
                            "type": "string",
                            "description": "Type of message (only note is supported)",
                            "enum": ["note"],
                        },
                    },
                    "required": ["ticket_id", "comment", "admin_id"],
                },
            ),
            Tool(
                name="list_ticket_types",
                description="List all available ticket types in the Intercom workspace",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Intercom"""
        access_token = await get_intercom_client()

        if name == "search_contacts":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            query = arguments["query"]

            # Search contacts by query
            try:
                search_params = {
                    "query": {"field": "email", "operator": "~", "value": query}
                }
                search_result = await execute_intercom_request(
                    "post",
                    "contacts/search",
                    data=search_params,
                    access_token=access_token,
                )

                contacts = search_result.get("data", [])

                if not contacts:
                    # Try searching by name if email search returns no results
                    search_params = {
                        "query": {"field": "name", "operator": "~", "value": query}
                    }
                    search_result = await execute_intercom_request(
                        "post",
                        "contacts/search",
                        data=search_params,
                        access_token=access_token,
                    )
                    contacts = search_result.get("data", [])

                if not contacts:
                    return [
                        TextContent(
                            type="text", text="No contacts found matching your query."
                        )
                    ]

                contact_list = []
                for contact in contacts:
                    contact_type = "User" if contact.get("role") == "user" else "Lead"
                    contact_list.append(
                        f"{contact_type}: {contact.get('name', 'Unnamed')}\n"
                        f"  Email: {contact.get('email', 'No Email')}\n"
                        f"  ID: {contact.get('id')}\n"
                        f"  Created: {contact.get('created_at')}"
                    )

                formatted_result = "\n\n".join(contact_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(contacts)} contacts:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error searching contacts: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error searching contacts: {str(e)}")
                ]

        elif name == "create_contact":
            required_fields = ["email"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            data = {
                "role": arguments.get("role", "user"),
                "email": arguments["email"],
            }

            if "name" in arguments:
                data["name"] = arguments["name"]

            if "custom_attributes" in arguments:
                data["custom_attributes"] = arguments["custom_attributes"]

            try:
                contact_result = await execute_intercom_request(
                    "post", "contacts", data=data, access_token=access_token
                )

                if not contact_result or "id" not in contact_result:
                    error_message = contact_result.get(
                        "errors", [{"message": "Unknown error"}]
                    )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create contact: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Contact created successfully!\n\n"
                        f"ID: {contact_result.get('id')}\n"
                        f"Name: {contact_result.get('name', 'Not provided')}\n"
                        f"Email: {contact_result.get('email')}\n"
                        f"Role: {contact_result.get('role', 'user')}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error creating contact: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating contact: {str(e)}")
                ]

        elif name == "create_conversation":
            required_fields = ["contact_id", "message"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            # Fix the data structure for creating a conversation
            # According to Intercom OpenAPI spec, we need to use the /conversations endpoint
            # with proper format for message creation
            data = {
                "from": {"type": "user", "id": arguments["contact_id"]},
                "body": arguments["message"],
            }

            # If admin_id is specified, use it as the author
            if "admin_id" in arguments:
                data["from"] = {"type": "admin", "id": arguments["admin_id"]}

            if "tag_ids" in arguments:
                data["tags"] = {"ids": arguments["tag_ids"]}

            try:
                conversation_result = await execute_intercom_request(
                    "post", "conversations", data=data, access_token=access_token
                )

                if not conversation_result or "id" not in conversation_result:
                    error_message = (
                        conversation_result.get(
                            "errors", [{"message": "Unknown error"}]
                        )[0].get("message")
                        if conversation_result
                        else "Unknown error"
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create conversation: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Conversation created successfully!\n\n"
                        f"ID: {conversation_result.get('id')}\n"
                        f"Created: {conversation_result.get('created_at')}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error creating conversation: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error creating conversation: {str(e)}"
                    )
                ]

        elif name == "reply_to_conversation":
            required_fields = ["message"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            conversation_id = arguments["conversation_id"]

            data = {
                "message_type": "comment",
                "body": arguments["message"],
            }

            if "user_id" in arguments:
                data["type"] = "user"
                data["intercom_user_id"] = arguments["user_id"]
            elif "admin_id" in arguments:
                data["type"] = "admin"
                data["admin_id"] = arguments["admin_id"]

            if "attachment_urls" in arguments:
                data["attachment_urls"] = arguments["attachment_urls"]

            try:
                if not conversation_id:
                    return [
                        TextContent(
                            type="text",
                            text="Invalid conversation ID. Please provide a valid ID.",
                        )
                    ]

                reply_result = await execute_intercom_request(
                    "post",
                    f"conversations/last/reply",
                    data=data,
                    access_token=access_token,
                )

                if not reply_result:
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to reply to conversation. The conversation ID {conversation_id} may be invalid.",
                        )
                    ]

                if "errors" in reply_result:
                    error_message = reply_result.get(
                        "errors", [{"message": "Unknown error"}]
                    )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to reply to conversation: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Reply sent successfully to conversation {conversation_id}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error replying to conversation: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error replying to conversation: {str(e)}"
                    )
                ]

        elif name == "add_tags_to_conversation":
            required_fields = ["conversation_id", "tag_ids"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            conversation_id = arguments["conversation_id"]
            tag_ids = arguments["tag_ids"]

            data = {"tags": {"ids": tag_ids}}

            try:
                result = await execute_intercom_request(
                    "post",
                    f"conversations/{conversation_id}/tags",
                    data=data,
                    access_token=access_token,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully added {len(tag_ids)} tags to conversation {conversation_id}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error adding tags to conversation: {str(e)}")
                return [TextContent(type="text", text=f"Error adding tags: {str(e)}")]

        elif name == "remove_tags_from_conversation":
            required_fields = ["conversation_id", "tag_ids"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            conversation_id = arguments["conversation_id"]
            tag_ids = arguments["tag_ids"]

            try:
                # For each tag ID, send a separate request to remove it
                for tag_id in tag_ids:
                    await execute_intercom_request(
                        "delete",
                        f"conversations/{conversation_id}/tags/{tag_id}",
                        access_token=access_token,
                    )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully removed {len(tag_ids)} tags from conversation {conversation_id}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error removing tags from conversation: {str(e)}")
                return [TextContent(type="text", text=f"Error removing tags: {str(e)}")]

        elif name == "list_admins":
            try:
                admins_result = await execute_intercom_request(
                    "get", "admins", access_token=access_token
                )

                admins = admins_result.get("admins", [])

                if not admins:
                    return [TextContent(type="text", text="No admins found.")]

                admin_list = []
                for admin in admins:
                    admin_list.append(
                        f"Admin: {admin.get('name')}\n"
                        f"  Email: {admin.get('email')}\n"
                        f"  ID: {admin.get('id')}\n"
                        f"  Role: {admin.get('job_title', 'Not specified')}"
                    )

                formatted_result = "\n\n".join(admin_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(admins)} admins:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error listing admins: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error listing admins: {str(e)}")
                ]

        elif name == "search_companies":
            if not arguments or "query" not in arguments:
                raise ValueError("Missing query parameter")

            query = arguments["query"]

            try:
                search_params = {
                    "filter": {"field": "name", "operator": "~", "value": query}
                }
                search_result = await execute_intercom_request(
                    "post",
                    "companies/list",
                    data=search_params,
                    access_token=access_token,
                )

                companies = search_result.get("data", [])

                if not companies:
                    return [
                        TextContent(
                            type="text", text="No companies found matching your query."
                        )
                    ]

                company_list = []
                for company in companies:
                    company_list.append(
                        f"Company: {company.get('name', 'Unnamed')}\n"
                        f"  ID: {company.get('id')}\n"
                        f"  Company ID: {company.get('company_id', 'Not specified')}\n"
                        f"  Created: {company.get('created_at')}"
                    )

                formatted_result = "\n\n".join(company_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(companies)} companies:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error searching companies: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error searching companies: {str(e)}"
                    )
                ]

        elif name == "create_company":
            data = {"name": arguments["name"]}

            # Add optional fields if provided
            optional_fields = ["company_id", "website", "industry"]
            for field in optional_fields:
                if field in arguments:
                    data[field] = arguments[field]

            # Generate a random company_id if not provided
            if "company_id" not in data:
                data["company_id"] = str(uuid.uuid4())

            if "custom_attributes" in arguments:
                data["custom_attributes"] = arguments["custom_attributes"]

            logger.info(f"Creating company with data: {data}")
            try:
                company_result = await execute_intercom_request(
                    "post", "companies", data=data, access_token=access_token
                )

                logger.info(f"Company result: {company_result}")
                if not company_result or "id" not in company_result:
                    error_message = (
                        company_result.get("errors", [{"message": "Unknown error"}])[
                            0
                        ].get("message")
                        if company_result
                        else "Unknown error"
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create company: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Company created successfully!\n\n"
                        f"ID: {company_result.get('id')}\n"
                        f"Name: {company_result.get('name')}\n"
                        f"Created: {company_result.get('created_at')}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error creating company: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating company: {str(e)}")
                ]

        elif name == "associate_contact_with_company":
            required_fields = ["contact_id", "company_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            contact_id = arguments["contact_id"]
            company_id = arguments["company_id"]

            data = {"companies": [{"id": company_id}]}

            try:
                result = await execute_intercom_request(
                    "post",
                    f"contacts/{contact_id}/companies",
                    data=data,
                    access_token=access_token,
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Successfully associated contact {contact_id} with company {company_id}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error associating contact with company: {str(e)}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error associating contact with company: {str(e)}",
                    )
                ]

        elif name == "list_articles":
            params = {}
            if arguments and "collection_id" in arguments:
                params["collection_id"] = arguments["collection_id"]

            try:
                articles_result = await execute_intercom_request(
                    "get", "articles", params=params, access_token=access_token
                )

                articles = articles_result.get("data", [])
                total_count = articles_result.get("total_count", 0)

                if not articles:
                    return [TextContent(type="text", text="No articles found.")]

                article_list = []
                for article in articles:
                    article_list.append(
                        f"Article: {article.get('title')}\n"
                        f"  ID: {article.get('id')}\n"
                        f"  State: {article.get('state')}\n"
                        f"  URL: {article.get('url', 'No URL')}\n"
                        f"  Updated: {article.get('updated_at')}"
                    )

                formatted_result = "\n\n".join(article_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {total_count} articles (showing {len(articles)}):\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error listing articles: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error listing articles: {str(e)}")
                ]

        elif name == "retrieve_article":
            try:
                if not arguments or "id" not in arguments:
                    return [
                        TextContent(
                            type="text", text="Missing required article ID parameter"
                        )
                    ]

                article_result = await execute_intercom_request(
                    "get",
                    f"articles/{arguments['id']}",
                    access_token=access_token,
                )

                logger.info(f"Article result: {article_result}")

                if not article_result or "id" not in article_result:
                    return [
                        TextContent(
                            type="text",
                            text=f"No article found with ID: {arguments['id']}",
                        )
                    ]

                article_details = (
                    f"Title: {article_result.get('title')}\n"
                    f"ID: {article_result.get('id')}\n"
                    f"State: {article_result.get('state', 'Unknown')}\n"
                    f"URL: {article_result.get('url', 'No URL')}\n"
                    f"Author: {article_result.get('author_id', 'Unknown')}\n"
                    f"Updated: {article_result.get('updated_at', 'Unknown')}"
                )

                # Add more detailed content preview
                if article_result.get("body"):
                    preview_length = 500  # Increased preview length
                    preview = article_result.get("body")[:preview_length]
                    if len(article_result.get("body", "")) > preview_length:
                        preview += "..."
                    article_details += f"\n\nPreview: {preview}"

                # Add created date if available
                if article_result.get("created_at"):
                    article_details += (
                        f"\n\nCreated: {article_result.get('created_at')}"
                    )

                logger.info(f"Article details: {article_details}")

                return [TextContent(type="text", text=article_details)]

            except Exception as e:
                logger.error(f"Error retrieving article: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error retrieving article: {str(e)}")
                ]

        elif name == "create_article":
            required_fields = ["title", "body", "author_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            data = {
                "title": arguments["title"],
                "body": arguments["body"],
                "author_id": arguments["author_id"],
                "state": arguments.get("state", "draft"),
            }

            if "collection_id" in arguments:
                data["parent_id"] = arguments["collection_id"]
                data["parent_type"] = "collection"

            try:
                article_result = await execute_intercom_request(
                    "post", "articles", data=data, access_token=access_token
                )

                if not article_result or "id" not in article_result:
                    error_message = article_result.get(
                        "errors", [{"message": "Unknown error"}]
                    )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create article: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Article created successfully!\n\n"
                        f"ID: {article_result.get('id')}\n"
                        f"Title: {article_result.get('title')}\n"
                        f"State: {article_result.get('state')}\n"
                        f"URL: {article_result.get('url')}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error creating article: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating article: {str(e)}")
                ]

        # Ticket management tool implementations
        elif name == "list_tickets":
            params = {}

            if arguments:
                if "state" in arguments and arguments["state"] != "all":
                    params["state"] = arguments["state"]
                if "tag_id" in arguments:
                    params["tag_id"] = arguments["tag_id"]
                if "limit" in arguments:
                    params["per_page"] = arguments["limit"]

            try:
                tickets_result = await execute_intercom_request(
                    "get", "tickets", params=params, access_token=access_token
                )

                tickets = tickets_result.get("tickets", [])

                if not tickets:
                    return [TextContent(type="text", text="No tickets found.")]

                ticket_list = []
                for ticket in tickets:
                    contact_name = (
                        ticket.get("contacts", {})
                        .get("contacts", [{}])[0]
                        .get("name", "Unknown contact")
                    )
                    status = ticket.get("ticket_state", "unknown")
                    created_at = ticket.get("created_at", "Unknown date")

                    ticket_list.append(
                        f"Ticket: {ticket.get('ticket_attributes', {}).get('_default_title_', 'No title')}\n"
                        f"  ID: {ticket.get('id')}\n"
                        f"  Status: {status}\n"
                        f"  Contact: {contact_name}\n"
                        f"  Created: {created_at}"
                    )

                formatted_result = "\n\n".join(ticket_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(tickets)} tickets:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error listing tickets: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error listing tickets: {str(e)}")
                ]

        elif name == "get_ticket":
            required_fields = ["ticket_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            ticket_id = arguments["ticket_id"]

            try:
                ticket_result = await execute_intercom_request(
                    "get", f"tickets/{ticket_id}", access_token=access_token
                )

                if not ticket_result or "id" not in ticket_result:
                    return [
                        TextContent(
                            type="text", text=f"Ticket with ID {ticket_id} not found."
                        )
                    ]

                title = ticket_result.get("ticket_attributes", {}).get(
                    "_default_title_", "No title"
                )
                description = ticket_result.get("ticket_attributes", {}).get(
                    "_default_description_", "No description"
                )
                status = ticket_result.get("ticket_state", "unknown")
                created_at = ticket_result.get("created_at", "Unknown")
                updated_at = ticket_result.get("updated_at", "Unknown")
                ticket_parts = ticket_result.get("ticket_parts", {}).get(
                    "ticket_parts", []
                )

                contact_info = "Unknown contact"
                if ticket_result.get("contacts", {}).get("contacts"):
                    contact = ticket_result.get("contacts", {}).get("contacts", [])[0]
                    contact_info = f"{contact.get('name', 'Unknown')} ({contact.get('email', 'No email')})"

                admin_assignee = ticket_result.get("admin_assignee_id", "None")

                ticket_details = (
                    f"Ticket: {title}\n"
                    f"ID: {ticket_result.get('id')}\n"
                    f"Status: {status}\n"
                    f"Contact: {contact_info}\n"
                    f"Assignee: {admin_assignee}\n"
                    f"Created: {created_at}\n"
                    f"Updated: {updated_at}\n\n"
                    f"Description:\n{description}\n\n"
                )

                if ticket_parts:
                    parts_text = "Activity & Comments:\n\n"
                    for part in ticket_parts:
                        part_type = part.get("part_type", "Unknown")
                        author_info = "System"
                        if part.get("author"):
                            author_type = part["author"].get("type", "unknown")
                            author_name = part["author"].get("name", "Unknown")
                            author_info = f"{author_name} ({author_type})"

                        created_at = part.get("created_at", "Unknown")

                        parts_text += f"[{created_at}] {author_info} - {part_type}:\n"

                        if part.get("body"):
                            parts_text += f"{part.get('body')}\n\n"
                        else:
                            parts_text += "No content\n\n"

                    ticket_details += parts_text

                return [TextContent(type="text", text=ticket_details)]

            except Exception as e:
                logger.error(f"Error retrieving ticket: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error retrieving ticket: {str(e)}")
                ]

        elif name == "create_ticket":
            required_fields = ["contact_id", "title", "description"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            contacts = [{"id": arguments["contact_id"]}]
            ticket_type_id = arguments.get("ticket_type_id", "")

            ticket_attributes = {
                "_default_title_": arguments["title"],
                "_default_description_": arguments["description"],
            }

            data = {
                "contacts": contacts,
                "ticket_attributes": ticket_attributes,
                "ticket_type_id": ticket_type_id,
            }

            if "company_id" in arguments:
                data["company_id"] = arguments["company_id"]

            try:
                ticket_result = await execute_intercom_request(
                    "post", "tickets", data=data, access_token=access_token
                )

                if not ticket_result or "id" not in ticket_result:
                    error_message = "Unknown error"
                    if ticket_result and "errors" in ticket_result:
                        error_message = ticket_result.get(
                            "errors", [{"message": "Unknown error"}]
                        )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to create ticket: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Ticket created successfully!\n\n"
                        f"ID: {ticket_result.get('id')}\n"
                        f"Title: {arguments['title']}\n"
                        f"Status: {ticket_result.get('ticket_state', 'submitted')}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error creating ticket: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating ticket: {str(e)}")
                ]

        elif name == "update_ticket":
            required_fields = ["ticket_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            ticket_id = arguments["ticket_id"]
            data = {}

            if "title" in arguments or "description" in arguments:
                ticket_attributes = {}
                if "title" in arguments:
                    ticket_attributes["_default_title_"] = arguments["title"]
                if "description" in arguments:
                    ticket_attributes["_default_description_"] = arguments[
                        "description"
                    ]
                data["ticket_attributes"] = ticket_attributes

            if "state" in arguments:
                data["state"] = arguments["state"]

            if "admin_id" in arguments:
                data["assignment"] = {"admin_id": arguments["admin_id"]}

            if "is_shared" in arguments:
                data["is_shared"] = arguments["is_shared"]

            if not data:
                return [TextContent(type="text", text="No fields provided to update.")]

            try:
                ticket_result = await execute_intercom_request(
                    "put", f"tickets/{ticket_id}", data=data, access_token=access_token
                )

                if not ticket_result or "id" not in ticket_result:
                    error_message = "Unknown error"
                    if ticket_result and "errors" in ticket_result:
                        error_message = ticket_result.get(
                            "errors", [{"message": "Unknown error"}]
                        )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to update ticket: {error_message}",
                        )
                    ]

                update_summary = []
                if "state" in arguments:
                    update_summary.append(f"Status: {arguments['state']}")
                if "admin_id" in arguments:
                    update_summary.append(f"Assigned to: Admin {arguments['admin_id']}")
                if "title" in arguments:
                    update_summary.append(f"Title: {arguments['title']}")

                status_message = (
                    ", ".join(update_summary) if update_summary else "Fields updated"
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Ticket updated successfully!\n\n"
                        f"ID: {ticket_result.get('id')}\n"
                        f"{status_message}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error updating ticket: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error updating ticket: {str(e)}")
                ]

        elif name == "add_comment_to_ticket":
            required_fields = ["ticket_id", "comment", "admin_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            ticket_id = arguments["ticket_id"]

            data = {
                "message_type": arguments.get("message_type", "note"),
                "type": "admin",
                "admin_id": arguments["admin_id"],
                "body": arguments["comment"],
            }

            try:
                comment_result = await execute_intercom_request(
                    "post",
                    f"tickets/{ticket_id}/reply",
                    data=data,
                    access_token=access_token,
                )

                if not comment_result or "id" not in comment_result:
                    error_message = "Unknown error"
                    if comment_result and "errors" in comment_result:
                        error_message = comment_result.get(
                            "errors", [{"message": "Unknown error"}]
                        )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=f"Failed to add comment: {error_message}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Note added successfully to ticket {ticket_id}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error adding comment to ticket: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error adding comment to ticket: {str(e)}"
                    )
                ]

        elif name == "list_ticket_types":
            try:
                ticket_types_result = await execute_intercom_request(
                    "get", "ticket_types", access_token=access_token
                )

                ticket_types = ticket_types_result.get("data", [])

                if not ticket_types:
                    return [
                        TextContent(
                            type="text", text="No ticket types found in this workspace."
                        )
                    ]

                ticket_type_list = []
                for ticket_type in ticket_types:
                    ticket_type_list.append(
                        f"Ticket Type: {ticket_type.get('name', 'Unnamed')}\n"
                        f"  ID: {ticket_type.get('id')}\n"
                        f"  Description: {ticket_type.get('description', 'No description')}"
                    )

                formatted_result = "\n\n".join(ticket_type_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(ticket_types)} ticket types:\n\n{formatted_result}",
                    )
                ]

            except Exception as e:
                logger.error(f"Error listing ticket types: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error listing ticket types: {str(e)}"
                    )
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="intercom-server",
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
