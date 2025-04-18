import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    AnyUrl,
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

from src.utils.docusign.util import (
    get_credentials,
    authenticate_and_save_credentials,
    process_docusign_token_response,
    refresh_token_if_needed,
)

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["signature", "impersonation"]
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

# DocuSign API base URLs
DOCUSIGN_BASE_URL = (
    "https://demo.docusign.net/restapi/v2.1"  # Use production URL in production
)
DOCUSIGN_OAUTH_TOKEN_URL = (
    "https://account-d.docusign.com/oauth/token"  # Demo environment
)
DOCUSIGN_USER_INFO_URL = (
    "https://account-d.docusign.com/oauth/userinfo"  # For getting account information
)


async def create_docusign_client(user_id, api_key=None):
    """
    Create a new DocuSign API client using stored OAuth credentials.

    Args:
        user_id (str): The user ID associated with the credentials.
        api_key (str, optional): Optional override for authentication.

    Returns:
        dict: DocuSign client configuration with necessary auth details.
    """
    credentials = await refresh_token_if_needed(
        user_id=user_id,
        service_name=SERVICE_NAME,
        token_url=DOCUSIGN_OAUTH_TOKEN_URL,
        token_data_builder=lambda oauth_config, refresh_token, credentials: {
            "client_id": oauth_config.get("client_id"),
            "client_secret": oauth_config.get("client_secret"),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        process_token_response=process_docusign_token_response,
        api_key=api_key,
        return_full_credentials=True,
    )

    # Extract token from credentials
    token = credentials.get("access_token")
    token_type = credentials.get("token_type", "Bearer")

    # Make sure token_type is capitalized correctly
    if token_type.lower() == "bearer":
        token_type = "Bearer"

    logger.info(f"Using token type: {token_type}")

    # Standard headers for API requests
    standard_headers = {
        "Authorization": f"{token_type} {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    return {"token": token, "headers": standard_headers, "base_url": DOCUSIGN_BASE_URL}


async def get_account_id(docusign, account_id=None):
    """
    Get the DocuSign account ID, either from the provided value or by fetching from userInfo.

    Args:
        docusign (dict): The DocuSign client configuration.
        account_id (str, optional): An account ID if already known.

    Returns:
        str: The DocuSign account ID.

    Raises:
        Exception: If no account is found or if multiple accounts exist and none is specified.
    """
    if account_id:
        return account_id

    # Fetch user info to get accounts
    logger.info("Account ID not provided. Fetching user account information...")

    headers = docusign["headers"]

    # Call the userInfo endpoint
    user_info_response = requests.get(
        DOCUSIGN_USER_INFO_URL, headers=headers, timeout=30
    )

    if user_info_response.status_code != 200:
        raise Exception(
            f"Error fetching user info: {user_info_response.status_code} - {user_info_response.text}"
        )

    user_info = user_info_response.json()
    accounts = user_info.get("accounts", [])

    if not accounts:
        raise Exception("No DocuSign accounts found for this user.")

    # If there's only one account, use it automatically
    if len(accounts) == 1:
        account_id = accounts[0]["account_id"]
        account_name = accounts[0]["account_name"]
        logger.info(f"Using the only available account: {account_name} ({account_id})")
        return account_id

    # Format account information for selection
    account_options = []
    for i, account in enumerate(accounts, 1):
        is_default = " (Default)" if account.get("is_default") else ""
        account_options.append(
            f"{i}. {account['account_name']}{is_default} - ID: {account['account_id']}"
        )

    account_list = "\n".join(account_options)

    # Return None to indicate multiple accounts, requiring user selection
    return None, accounts, account_list


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Initialize and configure the DocuSign MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("docusign-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return a list of available DocuSign tools."""
        tools = []

        # Templates tools
        tools.extend(
            [
                types.Tool(
                    name="list_templates",
                    description="Retrieve a list of templates from your DocuSign account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "search_text": {
                                "type": "string",
                                "description": "The search text used to search template names/subjects",
                            },
                            "folder_ids": {
                                "type": "string",
                                "description": "A comma-separated list of folder IDs to filter templates",
                            },
                            "folder_types": {
                                "type": "string",
                                "description": "A comma-separated list of folder types to filter templates",
                            },
                            "include": {
                                "type": "string",
                                "description": "A comma-separated list of additional template data to include",
                            },
                            "created_from_date": {
                                "type": "string",
                                "description": "Filter for templates created after this date (format: YYYY-MM-DD)",
                            },
                            "created_to_date": {
                                "type": "string",
                                "description": "Filter for templates created before this date (format: YYYY-MM-DD)",
                            },
                            "order_by": {
                                "type": "string",
                                "description": "The property to sort by (e.g., name, modified, used)",
                            },
                            "order": {
                                "type": "string",
                                "description": "The sort order (asc or desc)",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of records to return",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="get_template",
                    description="Retrieve detailed information about a specific DocuSign template",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "template_id": {
                                "type": "string",
                                "description": "The ID of the template to retrieve",
                            },
                        },
                        "required": ["template_id"],
                    },
                ),
                types.Tool(
                    name="create_template",
                    description="Create a new template in your DocuSign account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "name": {
                                "type": "string",
                                "description": "Name of the template to create",
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the template (optional)",
                            },
                            "email_subject": {
                                "type": "string",
                                "description": "Default email subject for envelopes created from this template",
                            },
                            "email_blurb": {
                                "type": "string",
                                "description": "Default email message for envelopes created from this template",
                            },
                            "document_name": {
                                "type": "string",
                                "description": "Name of the document to include in the template",
                            },
                            "document_base64": {
                                "type": "string",
                                "description": "Base64-encoded document content (PDF, DOCX, etc.)",
                            },
                            "file_extension": {
                                "type": "string",
                                "description": "File extension of the document (pdf, docx, etc.)",
                            },
                        },
                        "required": [
                            "name",
                            "document_name",
                            "document_base64",
                            "file_extension",
                        ],
                    },
                ),
                types.Tool(
                    name="create_envelope",
                    description="Create a new envelope in DocuSign for sending documents for signature. Must include document(s), recipient(s) with tabs, and a subject line.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "template_id": {
                                "type": "string",
                                "description": "The ID of a template to use (optional)",
                            },
                            "email_subject": {
                                "type": "string",
                                "description": "Email subject line for envelope recipients (required)",
                            },
                            "email_blurb": {
                                "type": "string",
                                "description": "Email message for envelope recipients",
                            },
                            "status": {
                                "type": "string",
                                "description": "Envelope status: 'sent' to send immediately, 'created' to save as draft",
                                "enum": ["sent", "created"],
                            },
                            "recipients": {
                                "type": "array",
                                "description": "List of recipients who will sign or receive the envelope (required)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "email": {
                                            "type": "string",
                                            "description": "Recipient's email address",
                                        },
                                        "name": {
                                            "type": "string",
                                            "description": "Recipient's full name",
                                        },
                                        "role_name": {
                                            "type": "string",
                                            "description": "Role name for the recipient in the template (required for template-based envelopes)",
                                        },
                                        "routing_order": {
                                            "type": "string",
                                            "description": "Order in which recipient receives the envelope (1 is first)",
                                        },
                                        "recipient_id": {
                                            "type": "string",
                                            "description": "Unique ID for this recipient (optional, will be assigned automatically if not provided)",
                                        },
                                        "tabs": {
                                            "type": "object",
                                            "description": "Signature and form fields for this recipient (required for signers)",
                                            "properties": {
                                                "signHereTabs": {
                                                    "type": "array",
                                                    "description": "Signature fields where the recipient will sign",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "anchorString": {
                                                                "type": "string",
                                                                "description": "Text in the document that will be replaced with this tab",
                                                            },
                                                            "anchorUnits": {
                                                                "type": "string",
                                                                "description": "Units for anchor positioning (pixels, inches, etc.)",
                                                            },
                                                            "anchorXOffset": {
                                                                "type": "string",
                                                                "description": "X offset from anchor position",
                                                            },
                                                            "anchorYOffset": {
                                                                "type": "string",
                                                                "description": "Y offset from anchor position",
                                                            },
                                                        },
                                                        "required": ["anchorString"],
                                                    },
                                                },
                                                "dateSignedTabs": {
                                                    "type": "array",
                                                    "description": "Fields that will display the date when signed",
                                                },
                                                "textTabs": {
                                                    "type": "array",
                                                    "description": "Text fields the recipient can fill out",
                                                },
                                            },
                                            "required": ["signHereTabs"],
                                        },
                                    },
                                    "required": ["email", "name", "tabs"],
                                },
                            },
                            "documents": {
                                "type": "array",
                                "description": "List of documents to include in the envelope (required if not using a template)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name/title of the document",
                                        },
                                        "document_id": {
                                            "type": "string",
                                            "description": "Document ID (must be unique within the envelope)",
                                        },
                                        "file_extension": {
                                            "type": "string",
                                            "description": "File extension (pdf, docx, etc.)",
                                        },
                                        "document_base64": {
                                            "type": "string",
                                            "description": "Base64-encoded document content",
                                        },
                                    },
                                    "required": [
                                        "name",
                                        "document_id",
                                        "file_extension",
                                        "document_base64",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "email_subject",
                            "status",
                            "recipients",
                            "documents",
                        ],
                    },
                ),
                types.Tool(
                    name="get_envelope",
                    description="Retrieve detailed information about a specific DocuSign envelope",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "envelope_id": {
                                "type": "string",
                                "description": "The ID of the envelope to retrieve",
                            },
                            "include": {
                                "type": "string",
                                "description": "A comma-separated list of envelope parts to include (e.g., 'recipients,documents,custom_fields')",
                            },
                        },
                        "required": ["envelope_id"],
                    },
                ),
                types.Tool(
                    name="send_envelope",
                    description="Send a draft envelope that was previously created but not sent. The envelope must be complete with all required components (documents, recipients, tabs, and subject line) before it can be sent. You can provide missing components to complete the envelope.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "envelope_id": {
                                "type": "string",
                                "description": "The ID of the draft envelope to send",
                            },
                            "email_subject": {
                                "type": "string",
                                "description": "Email subject line if not already set in the envelope",
                            },
                            "email_blurb": {
                                "type": "string",
                                "description": "Email message for envelope recipients if not already set",
                            },
                            "documents": {
                                "type": "array",
                                "description": "List of documents to add to the envelope if needed",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name/title of the document",
                                        },
                                        "document_id": {
                                            "type": "string",
                                            "description": "Document ID (must be unique within the envelope)",
                                        },
                                        "file_extension": {
                                            "type": "string",
                                            "description": "File extension (pdf, docx, txt, etc.)",
                                        },
                                        "document_base64": {
                                            "type": "string",
                                            "description": "Base64-encoded document content",
                                        },
                                    },
                                    "required": [
                                        "name",
                                        "document_id",
                                        "file_extension",
                                        "document_base64",
                                    ],
                                },
                            },
                            "recipients": {
                                "type": "array",
                                "description": "List of recipients to add to the envelope if needed",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "email": {
                                            "type": "string",
                                            "description": "Recipient's email address",
                                        },
                                        "name": {
                                            "type": "string",
                                            "description": "Recipient's full name",
                                        },
                                        "recipient_id": {
                                            "type": "string",
                                            "description": "Unique ID for this recipient (optional)",
                                        },
                                        "routing_order": {
                                            "type": "string",
                                            "description": "Order in which recipient receives the envelope (1 is first)",
                                        },
                                        "tabs": {
                                            "type": "object",
                                            "description": "Signature and form fields for this recipient",
                                            "properties": {
                                                "signHereTabs": {
                                                    "type": "array",
                                                    "description": "Signature fields where the recipient will sign",
                                                    "items": {
                                                        "type": "object",
                                                        "properties": {
                                                            "anchorString": {
                                                                "type": "string",
                                                                "description": "Text in the document that will be replaced with this tab",
                                                            },
                                                            "anchorUnits": {
                                                                "type": "string",
                                                                "description": "Units for anchor positioning (pixels, inches, etc.)",
                                                            },
                                                            "anchorXOffset": {
                                                                "type": "string",
                                                                "description": "X offset from anchor position",
                                                            },
                                                            "anchorYOffset": {
                                                                "type": "string",
                                                                "description": "Y offset from anchor position",
                                                            },
                                                            "documentId": {
                                                                "type": "string",
                                                                "description": "ID of the document this tab belongs to",
                                                            },
                                                            "pageNumber": {
                                                                "type": "string",
                                                                "description": "Page number where the tab should be placed (1-based)",
                                                            },
                                                        },
                                                        "required": ["anchorString"],
                                                    },
                                                },
                                                "dateSignedTabs": {
                                                    "type": "array",
                                                    "description": "Fields that will display the date when signed",
                                                },
                                                "textTabs": {
                                                    "type": "array",
                                                    "description": "Text fields the recipient can fill out",
                                                },
                                            },
                                            "required": ["signHereTabs"],
                                        },
                                    },
                                    "required": ["email", "name", "tabs"],
                                },
                            },
                        },
                        "required": [
                            "envelope_id",
                            "email_subject",
                            "recipients",
                            "documents",
                        ],
                    },
                ),
                types.Tool(
                    name="get_envelope_status_bulk",
                    description="Retrieve status information for multiple DocuSign envelopes in a single request",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "envelope_ids": {
                                "type": "array",
                                "description": "List of envelope IDs to check status for",
                                "items": {"type": "string"},
                            },
                            "include": {
                                "type": "string",
                                "description": "A comma-separated list of envelope parts to include (e.g., 'recipients,documents,custom_fields')",
                            },
                        },
                        "required": ["envelope_ids"],
                    },
                ),
                types.Tool(
                    name="create_user",
                    description="Add a new user to your DocuSign account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "users": {
                                "type": "array",
                                "description": "List of users to create",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "userName": {
                                            "type": "string",
                                            "description": "Username for the new user (required)",
                                        },
                                        "email": {
                                            "type": "string",
                                            "description": "Email address for the new user (required)",
                                        },
                                        "firstName": {
                                            "type": "string",
                                            "description": "First name of the user",
                                        },
                                        "lastName": {
                                            "type": "string",
                                            "description": "Last name of the user",
                                        },
                                        "middleName": {
                                            "type": "string",
                                            "description": "Middle name of the user",
                                        },
                                        "title": {
                                            "type": "string",
                                            "description": "Job title of the user",
                                        },
                                        "isAdmin": {
                                            "type": "boolean",
                                            "description": "Whether the user has admin privileges",
                                        },
                                        "permissionProfileId": {
                                            "type": "string",
                                            "description": "Permission profile ID to assign to the user",
                                        },
                                        "groupId": {
                                            "type": "string",
                                            "description": "Group ID to add the user to",
                                        },
                                    },
                                    "required": ["userName", "email"],
                                },
                            },
                        },
                        "required": ["users"],
                    },
                ),
                types.Tool(
                    name="list_users",
                    description="Retrieve a list of users from your DocuSign account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "email": {
                                "type": "string",
                                "description": "Filter users by email address",
                            },
                            "username": {
                                "type": "string",
                                "description": "Filter users by username",
                            },
                            "status": {
                                "type": "string",
                                "description": "Filter users by status (e.g., 'active', 'closed')",
                            },
                            "additional_info": {
                                "type": "string",
                                "description": "A comma-separated list of additional user data to include",
                            },
                            "count": {
                                "type": "integer",
                                "description": "Number of records to return (default is 100)",
                            },
                            "start_position": {
                                "type": "integer",
                                "description": "Starting position for pagination",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="get_user",
                    description="Retrieve detailed information about a specific DocuSign user",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "The DocuSign account ID (optional, will prompt for selection if not provided)",
                            },
                            "user_id": {
                                "type": "string",
                                "description": "The ID of the user to retrieve information for",
                            },
                            "additional_info": {
                                "type": "string",
                                "description": "A comma-separated list of additional user data to include (e.g., 'group_information,user_settings')",
                            },
                        },
                        "required": ["user_id"],
                    },
                ),
            ]
        )

        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent]:
        """Handle DocuSign tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        token = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )
        docusign = await create_docusign_client(server.user_id, api_key=server.api_key)

        if arguments is None:
            arguments = {}

        # Ensure arguments is a dictionary - handle string inputs
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"error": "Invalid JSON input"}
                logger.error(f"Invalid arguments format: {arguments}")
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Invalid arguments format. Arguments must be a valid JSON object.",
                    )
                ]

        try:
            if name == "list_templates":
                # Step 1: If account_id is not provided, we need to fetch user information to get accounts
                account_id = arguments.get("account_id")

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                # Now we have an account ID, so let's fetch the templates
                account_id = result
                logger.info(f"Fetching templates for account ID: {account_id}")

                # Construct query parameters
                params = {}

                # Add optional query parameters if provided
                for param in ["search_text", "order_by", "order", "count"]:
                    if param in arguments and arguments[param]:
                        params[param] = arguments[param]

                # Handle special parameters
                if "folder_ids" in arguments and arguments["folder_ids"]:
                    params["folder_ids"] = arguments["folder_ids"]

                if "folder_types" in arguments and arguments["folder_types"]:
                    params["folder_types"] = arguments["folder_types"]

                if "include" in arguments and arguments["include"]:
                    params["include"] = arguments["include"]

                if "created_from_date" in arguments and arguments["created_from_date"]:
                    params["created_from_date"] = arguments["created_from_date"]

                if "created_to_date" in arguments and arguments["created_to_date"]:
                    params["created_to_date"] = arguments["created_to_date"]

                # Make the API request to get templates
                templates_url = (
                    f"{docusign['base_url']}/accounts/{account_id}/templates"
                )

                logger.info(f"Making request to: {templates_url}")
                logger.info(f"With params: {params}")

                templates_response = requests.get(
                    templates_url,
                    headers=docusign["headers"],
                    params=params,
                    timeout=30,
                )

                if templates_response.status_code != 200:
                    raise Exception(
                        f"Error fetching templates: {templates_response.status_code} - {templates_response.text}"
                    )

                result = templates_response.json()

                # Format the response for better readability
                templates_list = result.get("envelopeTemplates", [])
                template_count = len(templates_list)

                if template_count == 0:
                    return [
                        types.TextContent(
                            type="text",
                            text="No templates found for the specified criteria.",
                        )
                    ]

                # Create a more readable summary
                summary = (
                    f"Found {template_count} templates in account {account_id}:\n\n"
                )

                for i, template in enumerate(templates_list, 1):
                    template_id = template.get("templateId", "N/A")
                    name = template.get("name", "Unnamed Template")
                    created = template.get("created", "Unknown date")
                    owner = template.get("owner", {}).get("userName", "Unknown owner")

                    summary += f"{i}. {name}\n   ID: {template_id}\n   Created: {created}\n   Owner: {owner}\n\n"

                # Also include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "get_template":
                # Get required parameters
                account_id = arguments.get("account_id")
                template_id = arguments.get("template_id")

                if not template_id:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required field. Please provide template_id.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Step 2: Now we have an account ID and template ID, let's fetch the template details
                logger.info(
                    f"Fetching template {template_id} for account ID: {account_id}"
                )

                # Create the URL for fetching a specific template
                template_url = f"{docusign['base_url']}/accounts/{account_id}/templates/{template_id}"

                logger.info(f"Making request to: {template_url}")

                template_response = requests.get(
                    template_url, headers=docusign["headers"], timeout=30
                )

                if template_response.status_code != 200:
                    raise Exception(
                        f"Error fetching template details: {template_response.status_code} - {template_response.text}"
                    )

                template = template_response.json()

                # Format a human-readable summary of the template
                summary_parts = []

                # Basic template information
                summary_parts.append(
                    f"Template Name: {template.get('name', 'Unnamed Template')}"
                )
                summary_parts.append(
                    f"Template ID: {template.get('templateId', 'N/A')}"
                )

                if template.get("description"):
                    summary_parts.append(f"Description: {template['description']}")

                if template.get("created"):
                    summary_parts.append(f"Created: {template['created']}")

                if template.get("lastModified"):
                    summary_parts.append(f"Last Modified: {template['lastModified']}")

                # Email settings
                summary_parts.append(
                    f"Email Subject: {template.get('emailSubject', 'N/A')}"
                )
                if template.get("emailBlurb"):
                    summary_parts.append(f"Email Message: {template['emailBlurb']}")

                # Documents
                documents = template.get("documents", [])
                if documents:
                    summary_parts.append(f"\nDocuments ({len(documents)}):")
                    for i, doc in enumerate(documents, 1):
                        summary_parts.append(
                            f"  {i}. {doc.get('name', 'Unnamed Document')} (ID: {doc.get('documentId', 'N/A')})"
                        )

                # Recipients
                recipients = template.get("recipients", {})
                recipient_types = [
                    ("signers", "Signers"),
                    ("carbonCopies", "Carbon Copies"),
                    ("certifiedDeliveries", "Certified Deliveries"),
                    ("inPersonSigners", "In-Person Signers"),
                    ("editors", "Editors"),
                ]

                summary_parts.append("\nRecipients:")
                has_recipients = False

                for field, label in recipient_types:
                    recipients_list = recipients.get(field, [])
                    if recipients_list:
                        has_recipients = True
                        summary_parts.append(f"  {label} ({len(recipients_list)}):")
                        for i, recipient in enumerate(recipients_list, 1):
                            role = recipient.get("roleName", "N/A")
                            name = recipient.get("name", "Unnamed")
                            email = recipient.get("email", "No email")
                            routing_order = recipient.get("routingOrder", "N/A")
                            summary_parts.append(
                                f"    {i}. {name} ({email}) - Role: {role}, Order: {routing_order}"
                            )

                if not has_recipients:
                    summary_parts.append("  No recipients configured")

                # Include shared status
                template_def = template.get("envelopeTemplateDefinition", {})
                shared = template_def.get("shared", "false")
                summary_parts.append(f"\nShared: {'Yes' if shared == 'true' else 'No'}")

                # Join all parts into a summary
                summary = "\n".join(summary_parts)

                # Include the raw JSON for complete information
                detail_json = json.dumps(template, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "create_template":
                # Step 1: If account_id is not provided, we need to fetch user information to get accounts
                account_id = arguments.get("account_id")

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Step 2: Prepare the template creation request with minimal required fields
                template_name = arguments.get("name")
                document_name = arguments.get("document_name")
                document_base64 = arguments.get("document_base64")
                file_extension = arguments.get("file_extension")

                if (
                    not template_name
                    or not document_name
                    or not document_base64
                    or not file_extension
                ):
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required fields. Please provide name, document_name, document_base64, and file_extension.",
                        )
                    ]

                # Prepare the template payload with only necessary fields
                template_payload = {
                    "envelopeTemplateDefinition": {
                        "name": template_name,
                        "description": arguments.get("description", ""),
                        "shared": "false",
                    },
                    "documents": [
                        {
                            "documentId": "1",
                            "name": document_name,
                            "fileExtension": file_extension,
                            "documentBase64": document_base64,
                        }
                    ],
                    "emailSubject": arguments.get(
                        "email_subject", f"Please sign: {template_name}"
                    ),
                    "emailBlurb": arguments.get(
                        "email_blurb", "Please review and sign this document"
                    ),
                }

                # Send the request to create the template
                template_url = f"{docusign['base_url']}/accounts/{account_id}/templates"

                logger.info(
                    f"Creating template: {template_name} for account ID: {account_id}"
                )

                template_response = requests.post(
                    template_url,
                    headers=docusign["headers"],
                    json=template_payload,
                    timeout=30,
                )

                if template_response.status_code not in [201, 200]:
                    raise Exception(
                        f"Error creating template: {template_response.status_code} - {template_response.text}"
                    )

                result = template_response.json()

                # Format the response for better readability
                template_id = result.get("templateId")
                template_name = result.get("name", template_name)

                success_message = f"Template created successfully!\n\nName: {template_name}\nTemplate ID: {template_id}\n"

                if "uri" in result:
                    success_message += f"\nTemplate URI: {result['uri']}"

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=success_message),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "create_envelope":
                # Step 1: If account_id is not provided, we need to fetch user information to get accounts
                account_id = arguments.get("account_id")

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Step 2: Prepare the envelope creation request with required fields
                status = arguments.get("status")
                email_subject = arguments.get("email_subject")

                if not status or not email_subject:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required fields. Please provide status and email_subject.",
                        )
                    ]

                # Validate status is either 'sent' or 'created'
                if status not in ["sent", "created"]:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: status must be either 'sent' to send immediately or 'created' to save as draft.",
                        )
                    ]

                # Prepare the envelope payload
                envelope_payload = {
                    "emailSubject": email_subject,
                    "emailBlurb": arguments.get(
                        "email_blurb", "Please review and sign this document"
                    ),
                    "status": status,
                }

                # Check if using a template or direct documents
                template_id = arguments.get("template_id")
                documents = arguments.get("documents", [])
                recipients = arguments.get("recipients", [])

                if template_id:
                    # Template-based envelope
                    logger.info(f"Creating envelope from template: {template_id}")

                    envelope_payload["templateId"] = template_id

                    if recipients:
                        # Format template roles
                        template_roles = []
                        for recipient in recipients:
                            if "email" not in recipient or "name" not in recipient:
                                return [
                                    types.TextContent(
                                        type="text",
                                        text="Error: Each recipient must have at least 'email' and 'name' properties.",
                                    )
                                ]

                            if "role_name" not in recipient:
                                return [
                                    types.TextContent(
                                        type="text",
                                        text="Error: When using a template, each recipient must have a 'role_name' property to match template roles.",
                                    )
                                ]

                            template_role = {
                                "email": recipient["email"],
                                "name": recipient["name"],
                                "roleName": recipient["role_name"],
                            }

                            if "routing_order" in recipient:
                                template_role["routingOrder"] = recipient[
                                    "routing_order"
                                ]

                            template_roles.append(template_role)

                        envelope_payload["templateRoles"] = template_roles
                else:
                    # Document-based envelope (direct documents)
                    if not documents:
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: When not using a template, you must provide documents in the 'documents' array.",
                            )
                        ]

                    # Format documents
                    formatted_documents = []
                    for doc in documents:
                        if (
                            "name" not in doc
                            or "document_id" not in doc
                            or "file_extension" not in doc
                            or "document_base64" not in doc
                        ):
                            return [
                                types.TextContent(
                                    type="text",
                                    text="Error: Each document must include 'name', 'document_id', 'file_extension', and 'document_base64'.",
                                )
                            ]

                        formatted_doc = {
                            "name": doc["name"],
                            "documentId": doc["document_id"],
                            "fileExtension": doc["file_extension"],
                            "documentBase64": doc["document_base64"],
                        }
                        formatted_documents.append(formatted_doc)

                    envelope_payload["documents"] = formatted_documents

                    if recipients:
                        # Format direct recipients
                        formatted_recipients = {"signers": []}

                        for i, recipient in enumerate(recipients, 1):
                            if "email" not in recipient or "name" not in recipient:
                                return [
                                    types.TextContent(
                                        type="text",
                                        text="Error: Each recipient must have at least 'email' and 'name' properties.",
                                    )
                                ]

                            signer = {
                                "email": recipient["email"],
                                "name": recipient["name"],
                                "recipientId": str(i),
                            }

                            if "routing_order" in recipient:
                                signer["routingOrder"] = recipient["routing_order"]
                            else:
                                signer["routingOrder"] = str(i)

                            # Handle tabs if provided (signature fields, form fields, etc.)
                            if "tabs" in recipient:
                                signer["tabs"] = recipient["tabs"]

                            formatted_recipients["signers"].append(signer)

                        envelope_payload["recipients"] = formatted_recipients

                # Send the request to create the envelope
                envelope_url = f"{docusign['base_url']}/accounts/{account_id}/envelopes"

                logger.info(f"Creating envelope for account ID: {account_id}")
                logger.info(
                    f"Envelope payload: {json.dumps(envelope_payload, indent=2)}"
                )

                envelope_response = requests.post(
                    envelope_url,
                    headers=docusign["headers"],
                    json=envelope_payload,
                    timeout=30,
                )

                if envelope_response.status_code not in [201, 200]:
                    raise Exception(
                        f"Error creating envelope: {envelope_response.status_code} - {envelope_response.text}"
                    )

                result = envelope_response.json()

                # Format the response for better readability
                envelope_id = result.get("envelopeId")
                status = result.get("status", status)

                status_message = (
                    "sent to recipients" if status == "sent" else "saved as a draft"
                )
                success_message = f"Envelope created successfully and {status_message}!\n\nEnvelope ID: {envelope_id}\nStatus: {status}\n"

                if "uri" in result:
                    success_message += f"Envelope URI: {result['uri']}\n"

                # Include additional details for sent envelopes
                if status == "sent":
                    success_message += (
                        "\nThe document has been sent to the following recipients:\n"
                    )

                    if template_id and "templateRoles" in envelope_payload:
                        for role in envelope_payload["templateRoles"]:
                            success_message += f"- {role['name']} ({role['email']}) as {role['roleName']}\n"
                    elif (
                        "recipients" in envelope_payload
                        and "signers" in envelope_payload["recipients"]
                    ):
                        for signer in envelope_payload["recipients"]["signers"]:
                            success_message += (
                                f"- {signer['name']} ({signer['email']})\n"
                            )

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=success_message),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "get_envelope":
                # Get required parameters
                account_id = arguments.get("account_id")
                envelope_id = arguments.get("envelope_id")

                if not envelope_id:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required field. Please provide envelope_id.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Step 2: Now we have an account ID and envelope ID, let's fetch the envelope details
                logger.info(
                    f"Fetching envelope {envelope_id} for account ID: {account_id}"
                )

                # Create the URL for fetching a specific envelope
                envelope_url = f"{docusign['base_url']}/accounts/{account_id}/envelopes/{envelope_id}"

                # Set up query parameters
                params = {}
                if "include" in arguments and arguments["include"]:
                    params["include"] = arguments["include"]

                logger.info(f"Making request to: {envelope_url}")
                logger.info(f"With params: {params}")

                envelope_response = requests.get(
                    envelope_url, headers=docusign["headers"], params=params, timeout=30
                )

                if envelope_response.status_code != 200:
                    raise Exception(
                        f"Error fetching envelope details: {envelope_response.status_code} - {envelope_response.text}"
                    )

                envelope = envelope_response.json()

                # Format a human-readable summary of the envelope
                summary_parts = []

                # Basic envelope information
                summary_parts.append(
                    f"Envelope ID: {envelope.get('envelopeId', 'N/A')}"
                )
                summary_parts.append(f"Status: {envelope.get('status', 'N/A')}")

                if envelope.get("emailSubject"):
                    summary_parts.append(f"Email Subject: {envelope['emailSubject']}")

                if envelope.get("emailBlurb"):
                    summary_parts.append(f"Email Message: {envelope['emailBlurb']}")

                # Dates
                date_fields = [
                    ("createdDateTime", "Created"),
                    ("sentDateTime", "Sent"),
                    ("deliveredDateTime", "Delivered"),
                    ("completedDateTime", "Completed"),
                    ("voidedDateTime", "Voided"),
                ]

                summary_parts.append("\nTimeline:")
                for field, label in date_fields:
                    if field in envelope and envelope[field]:
                        summary_parts.append(f"  {label}: {envelope[field]}")

                # Documents
                if "documents" in envelope:
                    documents = envelope.get("documents", [])
                    summary_parts.append(f"\nDocuments ({len(documents)}):")
                    for i, doc in enumerate(documents, 1):
                        summary_parts.append(
                            f"  {i}. {doc.get('name', 'Unnamed Document')} (ID: {doc.get('documentId', 'N/A')})"
                        )

                # Recipients
                if "recipients" in envelope:
                    recipients = envelope.get("recipients", {})
                    recipient_types = [
                        ("signers", "Signers"),
                        ("carbonCopies", "Carbon Copies"),
                        ("certifiedDeliveries", "Certified Deliveries"),
                        ("inPersonSigners", "In-Person Signers"),
                        ("editors", "Editors"),
                    ]

                    summary_parts.append("\nRecipients:")
                    has_recipients = False

                    for field, label in recipient_types:
                        recipients_list = recipients.get(field, [])
                        if recipients_list:
                            has_recipients = True
                            summary_parts.append(f"  {label} ({len(recipients_list)}):")
                            for i, recipient in enumerate(recipients_list, 1):
                                name = recipient.get("name", "Unnamed")
                                email = recipient.get("email", "No email")
                                status = recipient.get("status", "Unknown status")
                                routing_order = recipient.get("routingOrder", "N/A")
                                summary_parts.append(
                                    f"    {i}. {name} ({email}) - Status: {status}, Order: {routing_order}"
                                )

                    if not has_recipients:
                        summary_parts.append("  No recipients found")

                # Custom fields if included
                if "customFields" in envelope:
                    custom_fields = envelope.get("customFields", {})
                    text_fields = custom_fields.get("textCustomFields", [])
                    list_fields = custom_fields.get("listCustomFields", [])

                    if text_fields or list_fields:
                        summary_parts.append("\nCustom Fields:")

                        for field in text_fields:
                            summary_parts.append(
                                f"  {field.get('name', 'Unnamed')}: {field.get('value', '')}"
                            )

                        for field in list_fields:
                            list_items = field.get("listItems", [])
                            list_values = ", ".join(list_items) if list_items else ""
                            summary_parts.append(
                                f"  {field.get('name', 'Unnamed')}: {list_values}"
                            )

                # Join all parts into a summary
                summary = "\n".join(summary_parts)

                # Include the raw JSON for complete information
                detail_json = json.dumps(envelope, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "send_envelope":
                # Get required parameters
                account_id = arguments.get("account_id")
                envelope_id = arguments.get("envelope_id")
                email_subject = arguments.get("email_subject")
                documents = arguments.get("documents", [])
                recipients = arguments.get("recipients", [])

                # Validate required parameters are provided
                missing_required = []
                if not envelope_id:
                    missing_required.append("envelope_id")
                if not email_subject:
                    missing_required.append("email_subject")
                if not documents:
                    missing_required.append("documents")
                if not recipients:
                    missing_required.append("recipients")

                if missing_required:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required fields: {', '.join(missing_required)}. These fields are required for sending an envelope.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # First, check the envelope status and content to make sure it's ready to be sent
                logger.info(
                    f"Checking envelope {envelope_id} in account ID: {account_id} before sending"
                )

                # Get the current envelope details with recipient information including tabs
                envelope_url = f"{docusign['base_url']}/accounts/{account_id}/envelopes/{envelope_id}"

                # Include recipients and tabs in the request to fully validate the envelope
                envelope_params = {"include": "recipients,tabs"}

                envelope_response = requests.get(
                    envelope_url,
                    headers=docusign["headers"],
                    params=envelope_params,
                    timeout=30,
                )

                if envelope_response.status_code != 200:
                    raise Exception(
                        f"Error retrieving envelope: {envelope_response.status_code} - {envelope_response.text}"
                    )

                envelope = envelope_response.json()

                # Check if the envelope is already sent
                if envelope.get("status") not in ["created", "draft"]:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Cannot send envelope. Current status is '{envelope.get('status')}'. Only draft envelopes can be sent.",
                        )
                    ]

                # Prepare update payload with required fields
                update_payload = {
                    "emailSubject": email_subject,
                    "emailBlurb": arguments.get(
                        "email_blurb", "Please review and sign this document"
                    ),
                }
                update_needed = True
                logger.info(f"Setting email subject: {email_subject}")

                # Format documents - always include since they're required
                formatted_documents = []
                for doc in documents:
                    if (
                        "name" not in doc
                        or "document_id" not in doc
                        or "file_extension" not in doc
                        or "document_base64" not in doc
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: Each document must include 'name', 'document_id', 'file_extension', and 'document_base64'.",
                            )
                        ]

                    formatted_doc = {
                        "name": doc["name"],
                        "documentId": doc["document_id"],
                        "fileExtension": doc["file_extension"],
                        "documentBase64": doc["document_base64"],
                    }
                    formatted_documents.append(formatted_doc)

                update_payload["documents"] = formatted_documents
                logger.info(f"Adding {len(formatted_documents)} documents")

                # Format recipients - always include since they're required
                formatted_recipients = {"signers": []}

                for i, recipient in enumerate(recipients, 1):
                    if "email" not in recipient or "name" not in recipient:
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: Each recipient must have at least 'email' and 'name' properties.",
                            )
                        ]

                    # Verify all recipients have tabs (required)
                    if "tabs" not in recipient:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Recipient '{recipient['name']}' is missing required tabs (signature fields).",
                            )
                        ]

                    # Use provided recipient_id or generate one based on position
                    recipient_id = recipient.get("recipient_id", str(i))

                    signer = {
                        "email": recipient["email"],
                        "name": recipient["name"],
                        "recipientId": recipient_id,
                    }

                    if "routing_order" in recipient:
                        signer["routingOrder"] = recipient["routing_order"]
                    else:
                        signer["routingOrder"] = str(i)

                    # Handle tabs - required
                    signer["tabs"] = recipient["tabs"]

                    formatted_recipients["signers"].append(signer)

                update_payload["recipients"] = formatted_recipients
                logger.info(
                    f"Adding {len(formatted_recipients['signers'])} recipients with tabs"
                )

                # Make the PUT request to update the envelope with all components
                logger.info(f"Updating envelope with provided components")
                update_response = requests.put(
                    envelope_url,
                    headers=docusign["headers"],
                    json=update_payload,
                    timeout=30,
                )

                if update_response.status_code != 200:
                    error_message = update_response.text
                    raise Exception(
                        f"Error updating envelope with components: {update_response.status_code} - {error_message}"
                    )

                # Get the updated envelope
                envelope_response = requests.get(
                    envelope_url,
                    headers=docusign["headers"],
                    params=envelope_params,
                    timeout=30,
                )

                if envelope_response.status_code != 200:
                    raise Exception(
                        f"Error retrieving updated envelope: {envelope_response.status_code} - {envelope_response.text}"
                    )

                envelope = envelope_response.json()

                # Now try to send the envelope
                logger.info(
                    f"Sending envelope {envelope_id} for account ID: {account_id}"
                )

                # Create the payload to change the status to "sent"
                payload = {"status": "sent"}

                # Make the PUT request to update the envelope status
                send_response = requests.put(
                    envelope_url, headers=docusign["headers"], json=payload, timeout=30
                )

                if send_response.status_code != 200:
                    error_message = send_response.text
                    raise Exception(
                        f"Error sending envelope: {send_response.status_code} - {error_message}"
                    )

                result = send_response.json()

                # Format the response for better readability
                success_message = (
                    f"Envelope {envelope_id} has been successfully sent!\n\n"
                    f"Status: {result.get('status', 'sent')}\n"
                )

                if "sentDateTime" in result:
                    success_message += f"Sent timestamp: {result['sentDateTime']}\n"

                # Include summary of what was in the envelope
                success_message += "\nEnvelope details:\n"
                success_message += f'- Email subject: "{email_subject}"\n'

                if "emailBlurb" in update_payload:
                    success_message += f"- Email message included\n"

                success_message += (
                    f"- Documents: {len(formatted_documents)} document(s)\n"
                )

                signers = formatted_recipients["signers"]
                success_message += f"- Recipients: {len(signers)} recipient(s)\n"
                for signer in signers:
                    success_message += f"  - {signer['name']} ({signer['email']})\n"

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=success_message),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "get_envelope_status_bulk":
                # Get required parameters
                account_id = arguments.get("account_id")
                envelope_ids = arguments.get("envelope_ids", [])

                if not envelope_ids:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required field. Please provide envelope_ids as an array of envelope IDs.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Create the URL for fetching envelope statuses
                envelope_status_url = (
                    f"{docusign['base_url']}/accounts/{account_id}/envelopes"
                )

                # Set up query parameters - using query parameters instead of request body
                params = {"envelope_ids": ",".join(envelope_ids)}

                if "include" in arguments and arguments["include"]:
                    params["include"] = arguments["include"]

                logger.info(
                    f"Fetching status for {len(envelope_ids)} envelopes in account ID: {account_id}"
                )
                logger.info(f"Making request to: {envelope_status_url}")
                logger.info(f"With params: {params}")

                # Make the API request - using GET instead of PUT
                envelope_status_response = requests.get(
                    envelope_status_url,
                    headers=docusign["headers"],
                    params=params,
                    timeout=30,
                )

                if envelope_status_response.status_code != 200:
                    raise Exception(
                        f"Error fetching envelope statuses: {envelope_status_response.status_code} - {envelope_status_response.text}"
                    )

                result = envelope_status_response.json()

                # Format the response for better readability
                envelopes = result.get("envelopes", [])
                envelope_count = len(envelopes)

                if envelope_count == 0:
                    return [
                        types.TextContent(
                            type="text",
                            text="No envelope status information found for the specified IDs.",
                        )
                    ]

                # Create a more readable summary
                summary = f"Found status information for {envelope_count} envelopes in account {account_id}:\n\n"

                # Group envelopes by status
                status_groups = {}
                for envelope in envelopes:
                    status = envelope.get("status", "Unknown")
                    if status not in status_groups:
                        status_groups[status] = []
                    status_groups[status].append(envelope)

                # Add summary by status group
                for status, status_envelopes in status_groups.items():
                    summary += f"## {status.capitalize()} ({len(status_envelopes)})\n"

                    for envelope in status_envelopes:
                        envelope_id = envelope.get("envelopeId", "N/A")
                        subject = envelope.get("emailSubject", "No subject")

                        # Format dates for readability
                        created_date = envelope.get("createdDateTime", "N/A")
                        status_date_field = None
                        if status == "sent":
                            status_date_field = "sentDateTime"
                        elif status == "delivered":
                            status_date_field = "deliveredDateTime"
                        elif status == "completed":
                            status_date_field = "completedDateTime"
                        elif status == "declined":
                            status_date_field = "declinedDateTime"
                        elif status == "voided":
                            status_date_field = "voidedDateTime"

                        status_date = (
                            envelope.get(status_date_field, "N/A")
                            if status_date_field
                            else "N/A"
                        )

                        summary += f"- {subject}\n"
                        summary += f"  ID: {envelope_id}\n"
                        summary += f"  Created: {created_date}\n"

                        if status_date != "N/A":
                            status_label = status.capitalize()
                            summary += f"  {status_label}: {status_date}\n"

                        # Add recipient info if available
                        if "recipients" in envelope:
                            recipients = envelope.get("recipients", {})
                            signers = recipients.get("signers", [])
                            if signers:
                                summary += f"  Recipients:\n"
                                for signer in signers:
                                    name = signer.get("name", "Unnamed")
                                    email = signer.get("email", "No email")
                                    recipient_status = signer.get(
                                        "status", "Unknown status"
                                    )
                                    summary += (
                                        f"    - {name} ({email}): {recipient_status}\n"
                                    )

                        summary += "\n"

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "create_user":
                # Get required parameters
                account_id = arguments.get("account_id")
                users = arguments.get("users", [])

                if not users:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required field. Please provide at least one user in the 'users' array.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Validate each user has the required fields
                for i, user in enumerate(users):
                    if "userName" not in user:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: User at index {i} is missing the required 'userName' field.",
                            )
                        ]

                    if "email" not in user:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: User at index {i} is missing the required 'email' field.",
                            )
                        ]

                # Prepare the request payload
                request_payload = {"newUsers": []}

                # Format the users for the API request
                for user in users:
                    new_user = {"userName": user["userName"], "email": user["email"]}

                    # Add optional fields if provided
                    optional_fields = [
                        "firstName",
                        "lastName",
                        "middleName",
                        "title",
                        "permissionProfileId",
                        "isAdmin",
                    ]

                    for field in optional_fields:
                        if field in user and user[field] is not None:
                            new_user[field] = user[field]

                    # Add user to newUsers array
                    request_payload["newUsers"].append(new_user)

                # Create the URL for creating users
                users_url = f"{docusign['base_url']}/accounts/{account_id}/users"

                logger.info(
                    f"Creating {len(users)} user(s) for account ID: {account_id}"
                )
                logger.info(f"User creation payload: {json.dumps(request_payload)}")

                # Make the API request
                users_response = requests.post(
                    users_url,
                    headers=docusign["headers"],
                    json=request_payload,
                    timeout=30,
                )

                if users_response.status_code not in [201, 200]:
                    error_message = users_response.text
                    raise Exception(
                        f"Error creating users: {users_response.status_code} - {error_message}"
                    )

                result = users_response.json()

                # Format the response for better readability
                new_users = result.get("newUsers", [])
                success_count = len(new_users)

                if success_count == 0:
                    return [
                        types.TextContent(
                            type="text",
                            text="No users were created. Please check the request payload and try again.",
                        )
                    ]

                # Create a readable summary
                summary = f"Successfully created {success_count} user(s) in account {account_id}:\n\n"

                for i, user in enumerate(new_users, 1):
                    username = user.get("userName", "N/A")
                    email = user.get("email", "N/A")
                    user_id = user.get("userId", "N/A")

                    summary += f"{i}. {username} ({email})\n"
                    summary += f"   User ID: {user_id}\n"

                    if "firstName" in user and "lastName" in user:
                        name = f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()
                        if name:
                            summary += f"   Name: {name}\n"

                    if "permissionProfileName" in user:
                        summary += (
                            f"   Permission Profile: {user['permissionProfileName']}\n"
                        )

                    if "userStatus" in user:
                        summary += f"   Status: {user['userStatus']}\n"

                    # Check if activation email was sent
                    if (
                        "sendActivationEmail" in user
                        and user["sendActivationEmail"] == "true"
                    ):
                        summary += f"   Activation email sent: Yes\n"

                    summary += "\n"

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "list_users":
                # Get required parameters
                account_id = arguments.get("account_id")

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Create the URL for fetching users
                users_url = f"{docusign['base_url']}/accounts/{account_id}/users"

                # Set up query parameters
                params = {}

                # Add optional query parameters if provided
                for param in [
                    "email",
                    "status",
                    "username",
                    "additional_info",
                    "count",
                    "start_position",
                ]:
                    if param in arguments and arguments[param]:
                        # Convert parameter names to API expected format (snake_case to camelCase)
                        api_param = param
                        if param == "additional_info":
                            api_param = "additional_info"
                        elif param == "start_position":
                            api_param = "start_position"
                        params[api_param] = arguments[param]

                logger.info(f"Fetching users for account ID: {account_id}")
                logger.info(f"Making request to: {users_url}")
                logger.info(f"With params: {params}")

                # Make the API request
                users_response = requests.get(
                    users_url, headers=docusign["headers"], params=params, timeout=30
                )

                if users_response.status_code != 200:
                    raise Exception(
                        f"Error fetching users: {users_response.status_code} - {users_response.text}"
                    )

                result = users_response.json()

                # Format the response for better readability
                users = result.get("users", [])
                user_count = len(users)

                if user_count == 0:
                    return [
                        types.TextContent(
                            type="text",
                            text="No users found for the specified criteria.",
                        )
                    ]

                # Create a more readable summary
                summary = f"Found {user_count} users in account {account_id}:\n\n"

                for i, user in enumerate(users, 1):
                    user_id = user.get("userId", "N/A")
                    username = user.get("userName", "N/A")
                    email = user.get("email", "N/A")
                    user_status = user.get("userStatus", "N/A")

                    summary += f"{i}. {username}\n"
                    summary += f"   ID: {user_id}\n"
                    summary += f"   Email: {email}\n"
                    summary += f"   Status: {user_status}\n"

                    # Add name if available
                    if "firstName" in user or "lastName" in user:
                        name_parts = []
                        if "firstName" in user and user["firstName"]:
                            name_parts.append(user["firstName"])
                        if "lastName" in user and user["lastName"]:
                            name_parts.append(user["lastName"])

                        if name_parts:
                            full_name = " ".join(name_parts)
                            summary += f"   Name: {full_name}\n"

                    # Add user type/role if available
                    if "userType" in user:
                        summary += f"   User Type: {user['userType']}\n"

                    if "permissionProfileName" in user:
                        summary += (
                            f"   Permission Profile: {user['permissionProfileName']}\n"
                        )

                    # Add creation date if available
                    if "createdDateTime" in user:
                        summary += f"   Created: {user['createdDateTime']}\n"

                    summary += "\n"

                # Add pagination info if available
                if "resultSetSize" in result and "totalSetSize" in result:
                    result_size = result.get("resultSetSize")
                    total_size = result.get("totalSetSize")

                    if int(total_size) > int(result_size):
                        summary += f"\nShowing {result_size} of {total_size} total users. Use the 'start_position' parameter to view more results.\n"

                # Include the raw JSON for complete information
                detail_json = json.dumps(result, indent=2)

                return [
                    types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    ),
                ]

            elif name == "get_user":
                # Get required parameters
                account_id = arguments.get("account_id")
                user_id = arguments.get("user_id")

                if not user_id:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Missing required field. Please provide user_id.",
                        )
                    ]

                # Use the helper function to get the account ID
                result = await get_account_id(docusign, account_id)

                # If result is a tuple, it means we have multiple accounts
                if isinstance(result, tuple):
                    _, accounts, account_list = result
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Multiple DocuSign accounts found. Please specify an account_id in your request:\n\n{account_list}",
                        )
                    ]

                account_id = result

                # Create the URL for fetching a specific user
                user_url = (
                    f"{docusign['base_url']}/accounts/{account_id}/users/{user_id}"
                )

                # Set up query parameters
                params = {}
                if "additional_info" in arguments and arguments["additional_info"]:
                    params["additional_info"] = arguments["additional_info"]

                logger.info(f"Fetching user {user_id} for account ID: {account_id}")
                logger.info(f"Making request to: {user_url}")
                logger.info(f"With params: {params}")

                # Make the API request
                user_response = requests.get(
                    user_url, headers=docusign["headers"], params=params, timeout=30
                )

                if user_response.status_code != 200:
                    raise Exception(
                        f"Error fetching user details: {user_response.status_code} - {user_response.text}"
                    )

                user = user_response.json()

                # Include the raw JSON for complete information
                detail_json = json.dumps(user, indent=2)

                return [
                    # types.TextContent(type="text", text=summary),
                    types.TextContent(
                        type="text", text=f"Raw response:\n\n{detail_json}"
                    )
                ]

            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error calling DocuSign API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="docusign-server",
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
