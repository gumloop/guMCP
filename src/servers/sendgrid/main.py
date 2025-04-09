import os
import sys
import httpx
from typing import List, Dict
import json
from datetime import datetime

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path

from mcp.types import TextContent, Tool, ImageContent, EmbeddedResource
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
SENDGRID_API_URL = "https://api.sendgrid.com/v3"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_sendgrid_key(user_id):
    """Authenticate with SendGrid and save API key"""
    logger = logging.getLogger("sendgrid")

    logger.info(f"Starting SendGrid authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your SendGrid API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("sendgrid", user_id, {"api_key": api_key})

    logger.info(
        f"SendGrid API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_sendgrid_credentials(user_id, api_key=None):
    """Get SendGrid API key for the specified user"""
    logger = logging.getLogger("sendgrid")

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("sendgrid", user_id)

    def handle_missing_credentials():
        error_str = f"SendGrid API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        # In the case of GumloopAuthClient, api key is returned directly
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("sendgrid-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")

        return [
            Tool(
                name="send_email",
                description="Send an email using SendGrid",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject",
                        },
                        "content": {
                            "type": "string",
                            "description": "Email content (HTML or plain text)",
                        },
                        "from_email": {
                            "type": "string",
                            "description": "Sender email address",
                        },
                        "from_name": {
                            "type": "string",
                            "description": "Sender name (optional)",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "Template ID to use (optional)",
                        },
                        "schedule_time": {
                            "type": "string",
                            "description": "Schedule time in ISO format (optional)",
                        },
                    },
                    "required": ["to", "subject", "content", "from_email"],
                },
            ),
            Tool(
                name="get_email_stats",
                description="Get email statistics from SendGrid",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            ),
            Tool(
                name="create_template",
                description="Create a new email template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Template name",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Default subject line",
                        },
                        "html_content": {
                            "type": "string",
                            "description": "HTML content with variables in {{variable}} format",
                        },
                        "plain_content": {
                            "type": "string",
                            "description": "Plain text content with variables in {{variable}} format",
                        },
                    },
                    "required": ["name", "subject", "html_content"],
                },
            ),
            Tool(
                name="list_templates",
                description="List all email templates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "description": "Number of templates per page",
                        },
                        "page_token": {
                            "type": "string",
                            "description": "Token for pagination",
                        },
                    },
                },
            ),
            Tool(
                name="add_contact",
                description="Add a contact to SendGrid",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Contact email address",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Contact first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Contact last name",
                        },
                        "custom_fields": {
                            "type": "object",
                            "description": "Custom fields for the contact",
                        },
                    },
                    "required": ["email"],
                },
            ),
            Tool(
                name="manage_suppression",
                description="Add or remove email from suppression list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to take (add/remove)",
                            "enum": ["add", "remove"],
                        },
                        "group": {
                            "type": "string",
                            "description": "Suppression group (bounces/blocks/spam_reports/unsubscribes)",
                            "enum": [
                                "bounces",
                                "blocks",
                                "spam_reports",
                                "unsubscribes",
                            ],
                        },
                    },
                    "required": ["email", "action", "group"],
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

        api_key = await get_sendgrid_credentials(server.user_id, api_key=server.api_key)

        if not api_key:
            return [
                TextContent(
                    type="text",
                    text="Error: SendGrid API key not provided. Please configure your API key.",
                )
            ]

        if not arguments:
            return [TextContent(type="text", text="Error: No arguments provided.")]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if name == "send_email":
            required_fields = ["to", "subject", "content", "from_email"]
            for field in required_fields:
                if field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Missing required parameter: {field}",
                        )
                    ]

            try:
                async with httpx.AsyncClient() as client:
                    data = {
                        "personalizations": [
                            {
                                "to": [{"email": arguments["to"]}],
                            }
                        ],
                        "from": {
                            "email": arguments["from_email"],
                            "name": arguments.get("from_name", ""),
                        },
                        "subject": arguments["subject"],
                        "content": [
                            {
                                "type": "text/plain",
                                "value": arguments["content"],
                            }
                        ],
                    }

                    if "template_id" in arguments:
                        data["template_id"] = arguments["template_id"]

                    if "schedule_time" in arguments:
                        data["send_at"] = int(
                            datetime.fromisoformat(
                                arguments["schedule_time"]
                            ).timestamp()
                        )

                    response = await client.post(
                        f"{SENDGRID_API_URL}/mail/send",
                        headers=headers,
                        json=data,
                    )

                    if response.status_code == 202:
                        return [
                            TextContent(
                                type="text",
                                text="Email sent successfully!",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error sending email: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error sending email: {str(e)}")
                return [TextContent(type="text", text=f"Error sending email: {str(e)}")]

        elif name == "get_email_stats":
            required_fields = ["start_date", "end_date"]
            for field in required_fields:
                if field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Missing required parameter: {field}",
                        )
                    ]

            try:
                async with httpx.AsyncClient() as client:
                    params = {
                        "start_date": arguments["start_date"],
                        "end_date": arguments["end_date"],
                    }

                    response = await client.get(
                        f"{SENDGRID_API_URL}/stats",
                        headers=headers,
                        params=params,
                    )

                    if response.status_code == 200:
                        stats = response.json()
                        formatted_stats = "\n".join(
                            [
                                f"Date: {stat['date']}",
                                f"  Delivered: {stat['stats'][0]['metrics']['delivered']}",
                                f"  Bounces: {stat['stats'][0]['metrics']['bounces']}",
                                f"  Opens: {stat['stats'][0]['metrics']['opens']}",
                                f"  Clicks: {stat['stats'][0]['metrics']['clicks']}",
                                f"  Spam Reports: {stat['stats'][0]['metrics']['spam_reports']}",
                                "---",
                            ]
                            for stat in stats
                        )
                        return [
                            TextContent(
                                type="text",
                                text=f"Email Statistics:\n\n{formatted_stats}",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error getting email stats: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error getting email stats: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error getting email stats: {str(e)}"
                    )
                ]

        elif name == "create_template":
            required_fields = ["name", "subject", "html_content"]
            for field in required_fields:
                if field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Missing required parameter: {field}",
                        )
                    ]

            try:
                async with httpx.AsyncClient() as client:
                    data = {
                        "name": arguments["name"],
                        "generation": "dynamic",
                        "html_content": arguments["html_content"],
                        "subject": arguments["subject"],
                    }

                    if "plain_content" in arguments:
                        data["plain_content"] = arguments["plain_content"]

                    response = await client.post(
                        f"{SENDGRID_API_URL}/templates",
                        headers=headers,
                        json=data,
                    )

                    if response.status_code == 201:
                        template = response.json()
                        return [
                            TextContent(
                                type="text",
                                text=f"Template created successfully!\nID: {template['id']}",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error creating template: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error creating template: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating template: {str(e)}")
                ]

        elif name == "list_templates":
            try:
                async with httpx.AsyncClient() as client:
                    params = {}
                    if arguments:
                        if "page_size" in arguments:
                            params["page_size"] = arguments["page_size"]
                        if "page_token" in arguments:
                            params["page_token"] = arguments["page_token"]

                    response = await client.get(
                        f"{SENDGRID_API_URL}/templates",
                        headers=headers,
                        params=params,
                    )

                    if response.status_code == 200:
                        templates = response.json()
                        formatted_templates = "\n".join(
                            [
                                f"ID: {template['id']}",
                                f"Name: {template['name']}",
                                f"Generation: {template['generation']}",
                                "---",
                            ]
                            for template in templates.get("templates", [])
                        )
                        return [
                            TextContent(
                                type="text",
                                text=f"Templates:\n\n{formatted_templates}",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error listing templates: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error listing templates: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error listing templates: {str(e)}")
                ]

        elif name == "add_contact":
            if "email" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Missing required parameter: email",
                    )
                ]

            try:
                async with httpx.AsyncClient() as client:
                    data = {
                        "contacts": [
                            {
                                "email": arguments["email"],
                                "first_name": arguments.get("first_name", ""),
                                "last_name": arguments.get("last_name", ""),
                                "custom_fields": arguments.get("custom_fields", {}),
                            }
                        ]
                    }

                    response = await client.put(
                        f"{SENDGRID_API_URL}/marketing/contacts",
                        headers=headers,
                        json=data,
                    )

                    if response.status_code in [200, 202]:
                        return [
                            TextContent(
                                type="text",
                                text="Contact added successfully!",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error adding contact: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error adding contact: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error adding contact: {str(e)}")
                ]

        elif name == "manage_suppression":
            required_fields = ["email", "action", "group"]
            for field in required_fields:
                if field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Missing required parameter: {field}",
                        )
                    ]

            try:
                async with httpx.AsyncClient() as client:
                    if arguments["action"] == "add":
                        response = await client.post(
                            f"{SENDGRID_API_URL}/suppression/{arguments['group']}",
                            headers=headers,
                            json={"emails": [arguments["email"]]},
                        )
                    else:  # remove
                        response = await client.delete(
                            f"{SENDGRID_API_URL}/suppression/{arguments['group']}/{arguments['email']}",
                            headers=headers,
                        )

                    if response.status_code in [200, 201, 204]:
                        return [
                            TextContent(
                                type="text",
                                text=f"Successfully {arguments['action']}ed email from {arguments['group']} list",
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text",
                                text=f"Error managing suppression: {response.text}",
                            )
                        ]

            except Exception as e:
                logger.error(f"Error managing suppression: {str(e)}")
                return [
                    TextContent(
                        type="text", text=f"Error managing suppression: {str(e)}"
                    )
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="sendgrid-server",
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
        authenticate_and_save_sendgrid_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
