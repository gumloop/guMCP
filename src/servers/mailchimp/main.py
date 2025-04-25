import os
import sys
from pathlib import Path
import logging
from mailchimp_marketing import Client

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.types import TextContent
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.mailchimp.utils import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = []

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Mailchimp MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Mailchimp tools registered.
    """
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Mailchimp API.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="get_audience_list",
                description="List all available audiences",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="get_all_list",
                description="Get all lists available in account.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="list_all_campaigns",
                description="Get a list of all the campaigns.",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="campaign_info",
                description="Get information about a particular campaign for campaign id.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign to get information about",
                        }
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="recent_activity",
                description="Get up to the previous 180 days of recent activities in a list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the Mailchimp audience/list",
                        }
                    },
                    "required": ["list_id"],
                },
            ),
            types.Tool(
                name="add_update_subscriber",
                description="Add or update a subscriber in a Mailchimp audience.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the Mailchimp audience/list",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of the subscriber",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "First name of the subscriber",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Last name of the subscriber",
                        },
                    },
                    "required": ["list_id", "email"],
                },
            ),
            types.Tool(
                name="add_subscriber_tags",
                description="Add tags to a Mailchimp list subscriber.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the Mailchimp audience/list",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of the subscriber",
                        },
                        "tags": {
                            "type": "array",
                            "description": "List of tags to add to the subscriber",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["list_id", "email", "tags"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Handles the execution of a specific tool based on the provided name and arguments.
        """
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        credential = await get_credentials("local", SERVICE_NAME)

        access_token = credential.get("access_token")
        server_prefix = credential.get("dc")

        mailchimp = Client()
        mailchimp.set_config({"access_token": access_token, "server": server_prefix})

        try:
            if name == "get_audience_list":
                response = mailchimp.lists.get_all_lists()
                return [
                    TextContent(type="text", text=f"Available Audiences:\n{response}")
                ]
            elif name == "get_all_list":
                response = mailchimp.lists.get_all_lists()
                return [
                    TextContent(
                        type="text", text=f"List of all available accounts: {response}"
                    )
                ]
            elif name == "list_all_campaigns":
                response = mailchimp.campaigns.list()
                return [
                    TextContent(type="text", text=f"List of all campaigns: {response}")
                ]
            elif name == "campaign_info":
                campaign_id = arguments.get("campaign_id")
                response = mailchimp.campaigns.get(campaign_id)
                return [
                    TextContent(
                        type="text",
                        text=f"Information about campaign {campaign_id}: {response}",
                    )
                ]
            elif name == "recent_activity":
                list_id = arguments.get("list_id")
                response = mailchimp.lists.get_list_recent_activity(list_id)
                return [
                    TextContent(
                        type="text",
                        text=f"Recent activities in list {list_id}: {response}",
                    )
                ]

            elif name == "add_update_subscriber":
                if not arguments:
                    raise ValueError("Missing required arguments")

                list_id = arguments.get("list_id")
                email = arguments.get("email")
                first_name = arguments.get("first_name", "")
                last_name = arguments.get("last_name", "")

                if not list_id or not email:
                    raise ValueError("list_id and email are required")

                subscriber_info = {
                    "email_address": email,
                    "status_if_new": "subscribed",
                    "merge_fields": {"FNAME": first_name, "LNAME": last_name},
                }

                response = mailchimp.lists.set_list_member(
                    list_id, email.lower(), subscriber_info
                )

                return [
                    TextContent(
                        type="text", text=f"✅ Subscriber added/updated: {email}"
                    )
                ]
            elif name == "add_subscriber_tags":
                if not arguments:
                    raise ValueError("Missing required arguments")

                list_id = arguments.get("list_id")
                email = arguments.get("email")
                tags = arguments.get("tags", [])

                if not list_id or not email:
                    raise ValueError("list_id and email are required")
                if not tags:
                    raise ValueError("At least one tag is required")

                tag_data = {"tags": [{"name": tag, "status": "active"} for tag in tags]}

                response = mailchimp.lists.update_list_member_tags(
                    list_id, email.lower(), tag_data
                )

                return [
                    TextContent(
                        type="text",
                        text=f"✅ Tags added to subscriber {email}: {', '.join(tags)}",
                    )
                ]

            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options for the server instance.
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
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("python -m src.servers.mailchimp.main auth")
