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
    "contacts.read",
    "contacts.write",
    "conversations.read",
    "conversations.write",
    "companies.read",
    "companies.write",
    "articles.read",
    "articles.write",
    "tickets.read",
    "tickets.write",
    "admins.read",
    "teams.read",
    "tags.read",
    "tags.write",
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
            try:
                test_result = await execute_intercom_request(
                    "get", "contacts", params={"per_page": 1}, access_token=access_token
                )
                logger.info("API token validation successful")
            except Exception as test_error:
                logger.error(f"API token validation failed: {str(test_error)}")
                return []

            conversations_result = await execute_intercom_request(
                "get", "conversations", params=params, access_token=access_token
            )

            conversations = conversations_result.get("conversations", [])
            conversation_resources = []

            for conversation in conversations:
                title = f"Conversation with {conversation.get('source', {}).get('author', {}).get('name', 'Unknown')}"

                conversation_resources.append(
                    Resource(
                        uri=f"intercom://conversation/{conversation['id']}",
                        mimeType="application/json",
                        name=title,
                    )
                )

            if not conversation_resources:
                conversation_resources.append(
                    Resource(
                        uri="intercom://placeholder/no-conversations",
                        mimeType="application/json",
                        name="No conversations available",
                        description="Your Intercom account has no conversations or your API token lacks permission to access them",
                    )
                )

            return conversation_resources

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

        if uri_str.startswith("intercom://placeholder/"):
            # Handle placeholder resources
            placeholder_info = {
                "message": "No conversations available",
                "possible_reasons": [
                    "Your Intercom account has no conversations",
                    "Your API token lacks permission to access conversations",
                    "You need a token with admin access",
                ],
                "help": "Check your Intercom account and ensure your API token has appropriate access",
            }
            return [
                ReadResourceContents(
                    content=json.dumps(placeholder_info, indent=2),
                    mime_type="application/json",
                )
            ]
        elif uri_str.startswith("intercom://conversation/"):
            conversation_id = uri_str.replace("intercom://conversation/", "")

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
                requiredScopes=["contacts.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Contact data including ID, name, email and other attributes",
                    "examples": [
                        '{"id":"5f1234abc5678de90123f456","role":"user","email":"user@example.com","name":"John Smith","created_at":1642579234}'
                    ],
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
                requiredScopes=["contacts.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created contact data including ID, name, email and other attributes",
                    "examples": [
                        '{"id":"5f1234abc5678de90123f456","role":"user","email":"user@example.com","name":"John Smith","created_at":1642579234}'
                    ],
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
                requiredScopes=["conversations.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created conversation data including ID, author, parts, and timestamps",
                    "examples": [
                        '{"id":"123456789","type":"conversation","created_at":1642579234,"updated_at":1642579234,"source":{"id":"abc123","type":"user"},"state":"open"}'
                    ],
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
                requiredScopes=["conversations.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Reply data including ID, author, body, and timestamps",
                    "examples": [
                        '{"id":"reply123","type":"conversation_part","part_type":"comment","body":"This is a reply message","created_at":1642579234,"updated_at":1642579234,"author":{"id":"abc123","type":"admin"}}'
                    ],
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
                requiredScopes=["conversations.write", "tags.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of tagging operation with status and updated conversation data",
                    "examples": [
                        '{"type":"conversation","id":"123456789","tags":{"tags":[{"id":"tag123","name":"Support"},{"id":"tag456","name":"High Priority"}]}}'
                    ],
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
                requiredScopes=["conversations.write", "tags.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the tag removal operation with success status and details",
                    "examples": [
                        '{"success":true,"conversation_id":"123456789","removed_tag_ids":["tag123","tag456"],"results":[{"success":true},{"success":true}]}'
                    ],
                },
            ),
            Tool(
                name="list_admins",
                description="List all admins/team members in the Intercom workspace",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                requiredScopes=["admins.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Admin details including ID, name, email and role",
                    "examples": [
                        '{"id":"admin123","type":"admin","name":"Admin User","email":"admin@example.com","job_title":"Support Manager","away_mode_enabled":false,"away_mode_reassign":false}'
                    ],
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
                requiredScopes=["companies.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Company data including ID, name, and other attributes",
                    "examples": [
                        '{"id":"comp123","name":"Example Corp","company_id":"EC123","created_at":1642579234,"updated_at":1642579234,"industry":"Technology","size":250}'
                    ],
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
                requiredScopes=["companies.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created company data including ID, name, and timestamps",
                    "examples": [
                        '{"id":"comp123","name":"New Company","company_id":"NC123","created_at":1642579234,"updated_at":1642579234,"industry":"Technology","website":"https://example.com"}'
                    ],
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
                requiredScopes=["contacts.write", "companies.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the association operation with updated contact data",
                    "examples": [
                        '{"type":"contact","id":"contact123","companies":{"companies":[{"id":"comp123","name":"Example Corp","company_id":"EC123"}]}}'
                    ],
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
                requiredScopes=["articles.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Help center article data including title, body, author and state",
                    "examples": [
                        '{"id":"article123","type":"article","title":"Getting Started Guide","author_id":"admin123","created_at":1642579234,"updated_at":1642579234,"state":"published","url":"https://example.intercom.help/article/123-getting-started-guide"}'
                    ],
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
                requiredScopes=["articles.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Full article data including title, body, author and state",
                    "examples": [
                        '{"id":"article123","type":"article","title":"Getting Started Guide","body":"<p>This is the article content in HTML format.</p>","author_id":"admin123","created_at":1642579234,"updated_at":1642579234,"state":"published","url":"https://example.intercom.help/article/123-getting-started-guide"}'
                    ],
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
                requiredScopes=["articles.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created article data including ID, title, state and URL",
                    "examples": [
                        '{"id":"article123","type":"article","title":"New Article","author_id":"admin123","created_at":1642579234,"updated_at":1642579234,"state":"draft","url":"https://example.intercom.help/article/123-new-article"}'
                    ],
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
                requiredScopes=["tickets.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Support ticket data including ID, title, status and contact information",
                    "examples": [
                        '{"id":"ticket123","ticket_type_id":"type123","ticket_state":"in_progress","created_at":1642579234,"updated_at":1642579234,"ticket_attributes":{"_default_title_":"Billing question","_default_description_":"I have a question about my invoice"}}'
                    ],
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
                requiredScopes=["tickets.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed ticket data including ID, status, attributes, contact info and conversation history",
                    "examples": [
                        '{"id":"ticket123","ticket_type_id":"type123","ticket_state":"in_progress","created_at":1642579234,"updated_at":1642579234,"ticket_attributes":{"_default_title_":"Billing question","_default_description_":"I have a question about my invoice"},"contacts":{"contacts":[{"id":"contact123","name":"John Smith","email":"john@example.com"}]},"ticket_parts":{"ticket_parts":[{"id":"part123","body":"This is a comment on the ticket","created_at":1642579235,"author":{"id":"admin123","type":"admin","name":"Support Agent"}}]}}'
                    ],
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
                requiredScopes=["tickets.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Created ticket data including ID, type, status, title and description",
                    "examples": [
                        '{"id":"ticket123","ticket_type_id":"type123","ticket_state":"submitted","created_at":1642579234,"updated_at":1642579234,"ticket_attributes":{"_default_title_":"Billing question","_default_description_":"I have a question about my invoice"}}'
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
                requiredScopes=["tickets.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated ticket data including ID, new status, title, and other modified attributes",
                    "examples": [
                        '{"id":"ticket123","ticket_type_id":"type123","ticket_state":"in_progress","created_at":1642579234,"updated_at":1642589234,"ticket_attributes":{"_default_title_":"Updated Billing Question","_default_description_":"I have a question about my invoice"},"admin_assignee_id":"admin123"}'
                    ],
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
                requiredScopes=["tickets.write"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Comment data including ID, body, author and timestamp",
                    "examples": [
                        '{"id":"part123","type":"ticket_part","part_type":"note","body":"This is an internal note on the ticket","created_at":1642579234,"updated_at":1642579234,"author":{"id":"admin123","type":"admin","name":"Support Agent"}}'
                    ],
                },
            ),
            Tool(
                name="list_ticket_types",
                description="List all available ticket types in the Intercom workspace",
                inputSchema={"type": "object", "properties": {}},
                requiredScopes=["tickets.read"],
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Ticket type definitions including ID, name and description",
                    "examples": [
                        '{"id":"type123","name":"Technical Support","description":"Technical issues requiring engineering support"}'
                    ],
                },
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
                            type="text",
                            text=json.dumps(
                                {"message": "No contacts found", "count": 0, "data": []}
                            ),
                        )
                    ]

                return [
                    TextContent(type="text", text=json.dumps(contact))
                    for contact in contacts
                ]

            except Exception as e:
                logger.error(f"Error searching contacts: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": f"Failed to create contact",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(contact_result))]

            except Exception as e:
                logger.error(f"Error creating contact: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to create conversation",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(conversation_result))]

            except Exception as e:
                logger.error(f"Error creating conversation: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps({"error": "Invalid conversation ID"}),
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
                            text=json.dumps(
                                {
                                    "error": f"Failed to reply to conversation",
                                    "conversation_id": conversation_id,
                                }
                            ),
                        )
                    ]

                if "errors" in reply_result:
                    error_message = reply_result.get(
                        "errors", [{"message": "Unknown error"}]
                    )[0].get("message")
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "Failed to reply to conversation",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(reply_result))]

            except Exception as e:
                logger.error(f"Error replying to conversation: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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

                return [TextContent(type="text", text=json.dumps(result))]

            except Exception as e:
                logger.error(f"Error adding tags to conversation: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        elif name == "remove_tags_from_conversation":
            required_fields = ["conversation_id", "tag_ids"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    raise ValueError(f"Missing required parameter: {field}")

            conversation_id = arguments["conversation_id"]
            tag_ids = arguments["tag_ids"]

            try:
                results = []
                # For each tag ID, send a separate request to remove it
                for tag_id in tag_ids:
                    result = await execute_intercom_request(
                        "delete",
                        f"conversations/{conversation_id}/tags/{tag_id}",
                        access_token=access_token,
                    )
                    results.append(result)

                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": True,
                                "conversation_id": conversation_id,
                                "removed_tag_ids": tag_ids,
                                "results": results,
                            }
                        ),
                    )
                ]

            except Exception as e:
                logger.error(f"Error removing tags from conversation: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        elif name == "list_admins":
            try:
                admins_result = await execute_intercom_request(
                    "get", "admins", access_token=access_token
                )

                admins = admins_result.get("admins", [])

                if not admins:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"message": "No admins found", "count": 0, "data": []}
                            ),
                        )
                    ]

                if len(admins) == 1:
                    return [TextContent(type="text", text=json.dumps(admins[0]))]
                else:
                    return [
                        TextContent(type="text", text=json.dumps(admin))
                        for admin in admins
                    ]

            except Exception as e:
                logger.error(f"Error listing admins: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            type="text",
                            text=json.dumps(
                                {
                                    "message": "No companies found",
                                    "count": 0,
                                    "data": [],
                                }
                            ),
                        )
                    ]

                if len(companies) == 1:
                    return [TextContent(type="text", text=json.dumps(companies[0]))]
                else:
                    return [
                        TextContent(type="text", text=json.dumps(company))
                        for company in companies
                    ]

            except Exception as e:
                logger.error(f"Error searching companies: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to create company",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(company_result))]

            except Exception as e:
                logger.error(f"Error creating company: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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

                return [TextContent(type="text", text=json.dumps(result))]

            except Exception as e:
                logger.error(f"Error associating contact with company: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"message": "No articles found", "count": 0, "data": []}
                            ),
                        )
                    ]

                if len(articles) == 1:
                    return [TextContent(type="text", text=json.dumps(articles[0]))]
                else:
                    return [
                        TextContent(type="text", text=json.dumps(article))
                        for article in articles
                    ]

            except Exception as e:
                logger.error(f"Error listing articles: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        elif name == "retrieve_article":
            try:
                if not arguments or "id" not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "Missing required article ID parameter"}
                            ),
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
                            text=json.dumps(
                                {
                                    "error": f"No article found with ID: {arguments['id']}"
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(article_result))]

            except Exception as e:
                logger.error(f"Error retrieving article: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to create article",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(article_result))]

            except Exception as e:
                logger.error(f"Error creating article: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"message": "No tickets found", "count": 0, "data": []}
                            ),
                        )
                    ]

                return [
                    TextContent(type="text", text=json.dumps(ticket))
                    for ticket in tickets
                ]

            except Exception as e:
                logger.error(f"Error listing tickets: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            type="text",
                            text=json.dumps(
                                {"error": f"Ticket with ID {ticket_id} not found"}
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(ticket_result))]

            except Exception as e:
                logger.error(f"Error retrieving ticket: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to create ticket",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(ticket_result))]

            except Exception as e:
                logger.error(f"Error creating ticket: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": "No fields provided to update",
                                "ticket_id": ticket_id,
                            }
                        ),
                    )
                ]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to update ticket",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(ticket_result))]

            except Exception as e:
                logger.error(f"Error updating ticket: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
                            text=json.dumps(
                                {
                                    "error": "Failed to add comment",
                                    "message": error_message,
                                }
                            ),
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(comment_result))]

            except Exception as e:
                logger.error(f"Error adding comment to ticket: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

        elif name == "list_ticket_types":
            try:
                ticket_types_result = await execute_intercom_request(
                    "get", "ticket_types", access_token=access_token
                )

                ticket_types = ticket_types_result.get("data", [])

                if not ticket_types:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "message": "No ticket types found",
                                    "count": 0,
                                    "data": [],
                                }
                            ),
                        )
                    ]

                return [
                    TextContent(type="text", text=json.dumps(ticket_type))
                    for ticket_type in ticket_types
                ]

            except Exception as e:
                logger.error(f"Error listing ticket types: {str(e)}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
        print("\nAuthentication complete!")
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
