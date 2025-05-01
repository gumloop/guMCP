import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional, Iterable
import requests
import json


from mcp.types import TextContent, Resource, AnyUrl
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types

from src.utils.whatsapp.util import (
    authenticate_and_save_credentials,
    get_credentials,
)

SERVICE_NAME = Path(__file__).parent.name
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

API_ENDPOINT = "https://graph.facebook.com/v22.0"


def create_server(user_id, api_key=None):
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List WhatsApp resources (templates, messages, phone numbers)"""
        logger.info(f"Listing resources for user: {user_id} with cursor: {cursor}")

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        waba_id = credentials.get("waba_id", None)
        phone_number_id = credentials.get("phone_number_id", None)

        if not api_key:
            logger.error("WhatsApp Access Token not found")
            return []
        if not waba_id:
            logger.error("WhatsApp Business Account ID not found")
            return []
        if not phone_number_id:
            logger.error("Phone Number ID not found")
            return []

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        resources = []

        try:
            # List message templates
            templates_url = f"{API_ENDPOINT}/{waba_id}/message_templates"
            templates_response = requests.get(templates_url, headers=headers)
            if templates_response.status_code == 200:
                templates = templates_response.json().get("data", [])
                for template in templates:
                    resources.append(
                        Resource(
                            uri=f"whatsapp://template/{template['id']}",
                            mimeType="application/json",
                            name=f"Template: {template['name']}",
                            description=f"Message template ({template.get('status', 'unknown')})",
                        )
                    )

            # List phone numbers
            numbers_url = f"{API_ENDPOINT}/{waba_id}/phone_numbers"
            numbers_response = requests.get(numbers_url, headers=headers)
            if numbers_response.status_code == 200:
                numbers = numbers_response.json().get("data", [])
                for number in numbers:
                    resources.append(
                        Resource(
                            uri=f"whatsapp://phone/{number['id']}",
                            mimeType="application/json",
                            name=f"Phone: {number['display_phone_number']}",
                            description=f"Business phone number ({number.get('verified_name', 'unknown')})",
                        )
                    )

            # List business profile
            profile_url = f"{API_ENDPOINT}/{phone_number_id}/whatsapp_business_profile"
            profile_response = requests.get(profile_url, headers=headers)
            if profile_response.status_code == 200:
                resources.append(
                    Resource(
                        uri=f"whatsapp://profile/{phone_number_id}",
                        mimeType="application/json",
                        name="Business Profile",
                        description="WhatsApp Business Profile information",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error listing WhatsApp resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a WhatsApp resource by URI"""
        logger.info(f"Reading resource: {uri} for user: {user_id}")

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        waba_id = credentials.get("waba_id", None)
        phone_number_id = credentials.get("phone_number_id", None)

        if not api_key:
            return [
                ReadResourceContents(
                    content="Error: WhatsApp Access Token not found",
                    mime_type="text/plain",
                )
            ]
        if not waba_id:
            return [
                ReadResourceContents(
                    content="Error: WhatsApp Business Account ID not found",
                    mime_type="text/plain",
                )
            ]
        if not phone_number_id:
            return [
                ReadResourceContents(
                    content="Error: Phone Number ID not found", mime_type="text/plain"
                )
            ]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        uri_str = str(uri)
        if not uri_str.startswith("whatsapp://"):
            return [
                ReadResourceContents(
                    content="Error: Invalid WhatsApp URI", mime_type="text/plain"
                )
            ]

        try:
            if uri_str.startswith("whatsapp://template/"):
                # Handle template resource
                template_id = uri_str.replace("whatsapp://template/", "")
                template_url = f"{API_ENDPOINT}/{template_id}"
                response = requests.get(template_url, headers=headers)
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]
                else:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.text}", mime_type="text/plain"
                        )
                    ]

            elif uri_str.startswith("whatsapp://phone/"):
                # Handle phone number resource
                phone_id = uri_str.replace("whatsapp://phone/", "")
                phone_url = f"{API_ENDPOINT}/{phone_id}"
                response = requests.get(phone_url, headers=headers)
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]
                else:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.text}", mime_type="text/plain"
                        )
                    ]

            elif uri_str.startswith("whatsapp://profile/"):
                # Handle business profile resource
                profile_url = (
                    f"{API_ENDPOINT}/{phone_number_id}/whatsapp_business_profile"
                )
                response = requests.get(profile_url, headers=headers)
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]
                else:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.text}", mime_type="text/plain"
                        )
                    ]

            return [
                ReadResourceContents(
                    content="Error: Unsupported resource type", mime_type="text/plain"
                )
            ]

        except Exception as e:
            logger.error(f"Error reading WhatsApp resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Whatsapp Access Token.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="get_account_info",
                description="Get WhatsApp Business Account information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                outputSchema={
                    "type": "object",
                    "description": "WhatsApp Business Account details including ID, name, timezone, and message template namespace",
                    "examples": [
                        '{"id": "0123456789",  "name": "Test WhatsApp Business Account",  "timezone_id": "1", "message_template_namespace": "ahfap-aosjhfeli-32da"}'
                    ],
                },
            ),
            types.Tool(
                name="get_account_verification_status",
                description="Get business verification status",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "object",
                    "description": "Business verification status including verification state and account ID",
                    "examples": [
                        '{"business_verification_status": "not_verified", "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="list_phone_numbers",
                description="List all phone numbers associated with the WABA",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of phone numbers with their verification status, display numbers, quality ratings, and IDs",
                    "examples": [
                        '{"verified_name": "Test Number", "code_verification_status": "NOT_VERIFIED", "display_phone_number": "15556447198", "quality_rating": "GREEN", "platform_type": "CLOUD_API", "throughput": { "level": "STANDARD" }, "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="list_message_templates",
                description="List all message templates",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of message templates with their names, components, status, and IDs",
                    "examples": [
                        '{"name": "test_template_e8a7", "parameter_format": "POSITIONAL", "components": [{"type": "BODY", "text": "Hello from guMCP"}], "language": "en_US", "status": "REJECTED", "category": "MARKETING", "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="create_message_template",
                description="Create a new message template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the template",
                        },
                        "category": {
                            "type": "string",
                            "description": "Category of the template (e.g., MARKETING, AUTHENTICATION)",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code (e.g., en_US)",
                        },
                        "components": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "description": "Component type (e.g., BODY, HEADER, FOOTER)",
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Text content of the component",
                                    },
                                },
                            },
                        },
                    },
                    "required": ["name", "category", "language", "components"],
                },
                outputSchema={
                    "type": "object",
                    "description": "Created template details including ID, status, and category",
                    "examples": [
                        '{  "id": "0123456789", "status": "PENDING", "category": "MARKETING"}'
                    ],
                },
            ),
            types.Tool(
                name="get_template_preview",
                description="Preview a message template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template",
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code (e.g., en_US)",
                        },
                    },
                    "required": ["template_name", "language"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Template preview details including template name, components, status, ID and more",
                    "examples": [
                        '{"name": "test_template_830b", "parameter_format": "POSITIONAL", "components": [{"type": "BODY", "text": "Hello from guMCP"}], "language": "en_US", "status": "REJECTED", "category": "MARKETING", "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="get_phone_number_details",
                description="Get detailed information about a WhatsApp business phone number",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Phone number details including verification status, display number, quality rating, ID and more",
                    "examples": [
                        '{"verified_name": "Test Number", "code_verification_status": "NOT_VERIFIED", "display_phone_number": "0123456789", "quality_rating": "GREEN", "platform_type": "CLOUD_API", "throughput": {"level": "STANDARD"}, "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="get_business_profile",
                description="Get WhatsApp Business Profile information",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "object",
                    "description": "Business profile details including messaging product information",
                    "examples": ['{"data": [{"messaging_product": "whatsapp"}]}'],
                },
            ),
            types.Tool(
                name="get_message_template_details",
                description="Get detailed information about a specific message template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_id": {
                            "type": "string",
                            "description": "ID of the message template",
                        }
                    },
                    "required": ["template_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Template details including name, components, status, ID and more",
                    "examples": [
                        '{"name": "test_template_830b", "parameter_format": "POSITIONAL", "components": [{"type": "BODY", "text": "Hello from guMCP"}], "language": "en_US", "status": "REJECTED", "category": "MARKETING", "id": "0123456789"}'
                    ],
                },
            ),
            types.Tool(
                name="update_message_template",
                description="Update an existing message template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_id": {
                            "type": "string",
                            "description": "ID of the message template",
                        },
                        "category": {
                            "type": "string",
                            "enum": ["UTILITY", "MARKETING", "AUTHENTICATION"],
                            "description": "Template category",
                        },
                        "components": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "description": "Component type (e.g., BODY, HEADER, FOOTER)",
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "Text content of the component",
                                    },
                                },
                            },
                            "description": "Array of components that make up the template",
                        },
                        "message_send_ttl_seconds": {
                            "type": "integer",
                            "description": "Time to live for message template sent",
                        },
                        "parameter_format": {
                            "type": "string",
                            "enum": ["NAMED", "POSITIONAL"],
                            "description": "The parameter format of the template",
                        },
                    },
                    "required": ["template_id"],
                },
                outputSchema={
                    "type": "object",
                    "description": "Update status including success flag, template ID, name, and category",
                    "examples": [
                        '{"success": true, "id": "0123456789", "name": "test_template_830b", "category": "MARKETING"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_message_template",
                description="Delete a message template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "template_id": {
                            "type": "string",
                            "description": "ID of the template to be deleted",
                        },
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template to be deleted",
                        },
                    },
                    "required": ["template_id", "template_name"],
                },
                outputSchema={
                    "type": "object",
                    "description": "Deletion status including success flag",
                    "examples": ['{"success": true}'],
                },
            ),
            types.Tool(
                name="send_template_message",
                description="Send a WhatsApp message using a template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient's phone number in international format",
                        },
                        "template_name": {
                            "type": "string",
                            "description": "Name of the template to use",
                        },
                        "language_code": {
                            "type": "string",
                            "description": "Language code for the template (e.g., en_US)",
                        },
                    },
                    "required": ["to", "template_name", "language_code"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Message template details including name, components, status, ID and more",
                    "examples": [
                        '{"name": "sales_announcement", "parameter_format": "POSITIONAL", "components": [{"type": "BODY", "text": "SALE SALE SALE"}], "language": "en_US", "status": "APPROVED", "category": "MARKETING", "id": "0123456789"}',
                        '{"name": "hello_world", "parameter_format": "POSITIONAL", "components": [{"type": "HEADER", "format": "TEXT", "text": "Hello World"}, {"type": "BODY", "text": "Welcome and congratulations!! This message demonstrates your ability to send a WhatsApp message notification from the Cloud API, hosted by Meta. Thank you for taking the time to test with us."}, {"type": "FOOTER", "text": "WhatsApp Business Platform sample message"}], "language": "en_US", "status": "APPROVED", "category": "UTILITY", "id": "0123456789"}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent]:
        """
        Handle tool calls from the user, executing the appropriate Whatsapp API operations.
        """
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        waba_id = credentials.get("waba_id", None)
        phone_number_id = credentials.get("phone_number_id", None)

        if not api_key:
            return [TextContent(type="text", text="Error: Whatsapp Access Token not found")]
        if not waba_id:
            return [TextContent(type="text", text="Error: WhatsApp Business Account ID not found")]
        if not phone_number_id:
            return [TextContent(type="text", text="Error: Phone Number ID not found")]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            if name == "get_account_info":
                response = requests.get(f"{API_ENDPOINT}/{waba_id}", headers=headers)
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "get_account_verification_status":
                response = requests.get(
                    f"{API_ENDPOINT}/{waba_id}?fields=business_verification_status",
                    headers=headers,
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "list_phone_numbers":
                response = requests.get(
                    f"{API_ENDPOINT}/{waba_id}/phone_numbers", headers=headers
                )
                response.raise_for_status()
                data = response.json()
                if "data" in data:
                    return [
                        TextContent(type="text", text=json.dumps(item, indent=2))
                        for item in data["data"]
                    ]
                return [TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "list_message_templates":
                response = requests.get(
                    f"{API_ENDPOINT}/{waba_id}/message_templates", headers=headers
                )
                response.raise_for_status()
                data = response.json()
                if "data" in data:
                    return [
                        TextContent(type="text", text=json.dumps(item, indent=2))
                        for item in data["data"]
                    ]
                return [TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "create_message_template":
                # Format components according to WhatsApp API requirements
                formatted_components = []
                for component in arguments["components"]:
                    if component["type"] == "BODY":
                        formatted_components.append(
                            {"type": "BODY", "text": component["text"]}
                        )
                    elif component["type"] == "HEADER":
                        formatted_components.append(
                            {
                                "type": "HEADER",
                                "format": "TEXT",
                                "text": component["text"],
                            }
                        )
                    elif component["type"] == "FOOTER":
                        formatted_components.append(
                            {"type": "FOOTER", "text": component["text"]}
                        )

                template_data = {
                    "name": arguments["name"],
                    "category": arguments["category"],
                    "language": arguments["language"],
                    "components": formatted_components,
                }

                response = requests.post(
                    f"{API_ENDPOINT}/{waba_id}/message_templates",
                    headers=headers,
                    json=template_data,
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "get_template_preview":
                template_name = arguments["template_name"]
                language = arguments["language"]
                response = requests.get(
                    f"{API_ENDPOINT}/{waba_id}/message_template_previews",
                    headers=headers,
                    params={"name": template_name, "language": language},
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "get_phone_number_details":
                response = requests.get(
                    f"{API_ENDPOINT}/{phone_number_id}", headers=headers
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "get_business_profile":
                response = requests.get(
                    f"{API_ENDPOINT}/{phone_number_id}/whatsapp_business_profile",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                if "data" in data:
                    return [
                        TextContent(type="text", text=json.dumps(item, indent=2))
                        for item in data["data"]
                    ]
                return [TextContent(type="text", text=json.dumps(data, indent=2))]

            elif name == "get_message_template_details":
                template_id = arguments["template_id"]
                response = requests.get(
                    f"{API_ENDPOINT}/{template_id}", headers=headers
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "update_message_template":
                template_id = arguments["template_id"]
                data = {}
                if "category" in arguments:
                    data["category"] = arguments["category"]
                if "components" in arguments:
                    data["components"] = arguments["components"]
                if "message_send_ttl_seconds" in arguments:
                    data["message_send_ttl_seconds"] = arguments[
                        "message_send_ttl_seconds"
                    ]
                if "parameter_format" in arguments:
                    data["parameter_format"] = arguments["parameter_format"]

                response = requests.post(
                    f"{API_ENDPOINT}/{template_id}", headers=headers, json=data
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "delete_message_template":
                template_id = arguments["template_id"]
                template_name = arguments["template_name"]
                response = requests.delete(
                    f"{API_ENDPOINT}/{waba_id}/message_templates",
                    headers=headers,
                    params={"hsm_id": template_id, "name": template_name},
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            elif name == "send_template_message":
                data = {
                    "messaging_product": "whatsapp",
                    "to": arguments["to"],
                    "type": "template",
                    "template": {
                        "name": arguments["template_name"],
                        "language": {"code": arguments["language_code"]},
                    },
                }
                response = requests.post(
                    f"{API_ENDPOINT}/{phone_number_id}/messages",
                    headers=headers,
                    json=data,
                )
                response.raise_for_status()
                return [TextContent(type="text", text=json.dumps(response.json(), indent=2))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except requests.exceptions.RequestException as e:
            logger.error(f"API Error: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options for the server instance.
    """
    return InitializationOptions(
        server_name="whatsapp-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
