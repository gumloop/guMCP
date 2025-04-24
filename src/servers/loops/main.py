import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Optional

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.loops.util import authenticate_and_save_credentials, get_credentials

# Base URL as per Loops API reference
BASE_URL = "https://app.loops.so/api/v1"
SERVICE_NAME = Path(__file__).parent.name

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Creates and configures a Loops server instance with the specified tools.

    Arguments:
        user_id: The user ID for authentication
        api_key: Optional API key for the authentication client

    Returns:
        Server: Configured server instance with Loops tools
    """
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="add_contact",
                description="Adds a contact to your Loops account. Include a userId field to enable contact deletion by user ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "body": {
                            "type": "object",
                            "description": "Contact data including email, first_name, last_name, etc. Include user_id for future reference.",
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "description": "Contact's email address",
                                },
                                "userId": {
                                    "type": "string",
                                    "description": "Your unique identifier for this contact",
                                },
                                "firstName": {"type": "string"},
                                "lastName": {"type": "string"},
                                "userGroup": {
                                    "type": "string",
                                    "description": "The user group of the contact",
                                },
                                "subscribed": {"type": "boolean"},
                            },
                        }
                    },
                    "required": ["body"],
                },
            ),
            types.Tool(
                name="add_custom_property",
                description="Adds a new custom property for contacts.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "body": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Name of the custom property",
                                },
                                "type": {
                                    "type": "string",
                                    "description": "Type of the custom property",
                                    "enum": ["string", "boolean", "date", "number"],
                                },
                            },
                            "required": ["name", "type"],
                        }
                    },
                    "required": ["body"],
                },
            ),
            types.Tool(
                name="delete_contact_by_email",
                description="Deletes a contact by email.",
                inputSchema={
                    "type": "object",
                    "properties": {"email": {"type": "string"}},
                    "required": ["email"],
                },
            ),
            types.Tool(
                name="delete_contact_by_user_id",
                description="Deletes a contact by user ID. Only works if user_id was provided when creating the contact.",
                inputSchema={
                    "type": "object",
                    "properties": {"user_id": {"type": "string"}},
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="get_contact_by_email",
                description="Gets a contact by email.",
                inputSchema={
                    "type": "object",
                    "properties": {"email": {"type": "string"}},
                    "required": ["email"],
                },
            ),
            types.Tool(
                name="get_contact_by_user_id",
                description="Gets a contact by user ID.",
                inputSchema={
                    "type": "object",
                    "properties": {"user_id": {"type": "string"}},
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="update_contact_by_email",
                description="Updates a contact by email, or creates one if not existing.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["email", "body"],
                },
            ),
            types.Tool(
                name="update_contact_by_user_id",
                description="Updates a contact by user ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["user_id", "body"],
                },
            ),
            types.Tool(
                name="send_transactional_email",
                description="Sends a transactional email.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to_email": {"type": "string"},
                        "transactional_id": {"type": "string"},
                        "add_to_audience": {"type": "boolean"},
                        "data_variables": {"type": "object"},
                        "attachments": {"type": "array", "items": {"type": "object"}},
                    },
                    "required": ["to_email", "transactional_id"],
                },
            ),
            types.Tool(
                name="send_event_by_email",
                description="Sends an event by email.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "event_name": {"type": "string"},
                        "event_properties": {"type": "object"},
                        "mailing_lists": {"type": "object"},
                    },
                    "required": ["email", "event_name"],
                },
            ),
            types.Tool(
                name="send_event_by_user_id",
                description="Sends an event by user ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string"},
                        "event_name": {"type": "string"},
                        "event_properties": {"type": "object"},
                        "mailing_lists": {"type": "object"},
                    },
                    "required": ["user_id", "event_name"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        creds = await get_credentials(server.user_id, SERVICE_NAME, server.api_key)
        token = creds["key"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if not arguments:
            arguments = {}
        try:
            if name == "add_contact":
                response = requests.post(
                    f"{BASE_URL}/contacts/create",
                    headers=headers,
                    json=arguments["body"],
                )
            elif name == "add_custom_property":
                response = requests.post(
                    f"{BASE_URL}/contacts/properties",
                    headers=headers,
                    json=arguments["body"],
                )
            elif name == "delete_contact_by_email":
                response = requests.post(
                    f"{BASE_URL}/contacts/delete",
                    headers=headers,
                    json={"email": arguments["email"]},
                )
            elif name == "delete_contact_by_user_id":
                response = requests.post(
                    f"{BASE_URL}/contacts/delete",
                    headers=headers,
                    json={"userId": arguments["user_id"]},
                )
            elif name == "get_contact_by_email":
                response = requests.get(
                    f"{BASE_URL}/contacts/find",
                    headers=headers,
                    params={"email": arguments["email"]},
                )
            elif name == "get_contact_by_user_id":
                response = requests.get(
                    f"{BASE_URL}/contacts/find",
                    headers=headers,
                    params={"userId": arguments["user_id"]},
                )
            elif name == "update_contact_by_email":
                response = requests.put(
                    f"{BASE_URL}/contacts/update",
                    headers=headers,
                    json={"email": arguments["email"], **arguments["body"]},
                )
            elif name == "update_contact_by_user_id":
                response = requests.put(
                    f"{BASE_URL}/contacts/update",
                    headers=headers,
                    json={"userId": arguments["user_id"], **arguments["body"]},
                )
            elif name == "send_transactional_email":
                response = requests.post(
                    f"{BASE_URL}/transactional",
                    headers=headers,
                    json={
                        "email": arguments["to_email"],
                        "transactionalId": arguments["transactional_id"],
                        "addToAudience": arguments.get("add_to_audience", False),
                        "dataVariables": arguments.get("data_variables", {}),
                        "attachments": arguments.get("attachments", []),
                    },
                )
            elif name == "send_event_by_email":
                response = requests.post(
                    f"{BASE_URL}/events/send",
                    headers=headers,
                    json={
                        "email": arguments["email"],
                        "eventName": arguments["event_name"],
                        "eventProperties": arguments.get("event_properties", {}),
                        "mailingLists": arguments.get("mailing_lists", {}),
                    },
                )
            elif name == "send_event_by_user_id":
                response = requests.post(
                    f"{BASE_URL}/events/send",
                    headers=headers,
                    json={
                        "userId": arguments["user_id"],
                        "eventName": arguments["event_name"],
                        "eventProperties": arguments.get("event_properties", {}),
                        "mailingLists": arguments.get("mailing_lists", {}),
                    },
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            if response.status_code in [200, 201]:
                return [
                    types.TextContent(
                        type="text", text=json.dumps(response.json(), indent=2)
                    )
                ]
            else:
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": {
                                    "message": f"API Error: {response.text}",
                                    "status_code": response.status_code,
                                }
                            },
                            indent=2,
                        ),
                    )
                ]

        except Exception as e:
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": {
                                "Exception": str(e),
                                "traceback": e.__traceback__.tb_lineno,
                            }
                        },
                        indent=2,
                    ),
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Creates initialization options for the server instance.
    Arguments:
        server_instance: The server instance to create initialization options for
    Returns:
        InitializationOptions: Configured initialization options
    """
    return InitializationOptions(
        server_name=f"{SERVICE_NAME}-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        authenticate_and_save_credentials("local", SERVICE_NAME)
        print(
            f"Authentication complete for local user. You can now run the {SERVICE_NAME} server."
        )
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
