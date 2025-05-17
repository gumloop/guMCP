import os
import sys
import json
from pathlib import Path
import logging
from mailchimp_marketing import Client

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.types import TextContent, Resource, AnyUrl
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents
from typing import Optional, Iterable

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

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """
        List Mailchimp campaigns as resources.

        Args:
            cursor (Optional[str]): Pagination cursor for fetching next batch of resources.

        Returns:
            list[Resource]: List of Mailchimp campaign resources.
        """
        logger.info(f"Listing campaign resources for user: {user_id}")

        credential = await get_credentials("local", SERVICE_NAME)
        access_token = credential.get("access_token")
        server_prefix = credential.get("dc")

        mailchimp = Client()
        mailchimp.set_config({"access_token": access_token, "server": server_prefix})

        try:
            # Get list of campaigns
            response = mailchimp.campaigns.list()
            campaigns = response.get("campaigns", [])

            resources = []
            for campaign in campaigns:
                campaign_id = campaign.get("id")
                campaign_name = campaign.get("settings", {}).get(
                    "title", "Untitled Campaign"
                )
                campaign_type = campaign.get("type", "regular")
                campaign_status = campaign.get("status", "unknown")

                # Create resource representation
                resource = Resource(
                    uri=f"mailchimp://campaign/{campaign_id}",
                    mimeType="application/json",
                    name=campaign_name,
                    description=f"{campaign_type.capitalize()} campaign: {campaign_status}",
                )
                resources.append(resource)

            return resources

        except Exception as e:
            logger.error(f"Error listing campaign resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """
        Read a Mailchimp resource.

        Args:
            uri (AnyUrl): Resource URI to read.

        Returns:
            Iterable[ReadResourceContents]: Content of the resource.
        """
        logger.info(f"Reading resource: {uri}")

        credential = await get_credentials("local", SERVICE_NAME)
        access_token = credential.get("access_token")
        server_prefix = credential.get("dc")

        mailchimp = Client()
        mailchimp.set_config({"access_token": access_token, "server": server_prefix})

        uri_str = str(uri)
        if not uri_str.startswith("mailchimp://"):
            raise ValueError(f"Invalid Mailchimp URI: {uri_str}")

        parts = uri_str.replace("mailchimp://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid Mailchimp URI format: {uri_str}")

        resource_type, resource_id = parts

        try:
            if resource_type == "campaign":
                # Get campaign details
                response = mailchimp.campaigns.get(resource_id)

                return [
                    ReadResourceContents(
                        content=json.dumps(response, indent=2),
                        mime_type="application/json",
                    )
                ]
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Individual Mailchimp audience details, one per TextContent item",
                    "examples": [
                        '{"id": "abc123def", "name": "Newsletter", "stats": {"member_count": 6, "unsubscribe_count": 0, "cleaned_count": 0}, "date_created": "2023-01-15T12:30:27+00:00"}'
                    ],
                },
            ),
            types.Tool(
                name="get_all_list",
                description="Get all lists available in account.",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Individual Mailchimp list details, one per TextContent item",
                    "examples": [
                        '{"id": "abc123def", "name": "Newsletter", "stats": {"member_count": 6, "unsubscribe_count": 0, "cleaned_count": 0}, "date_created": "2023-01-15T12:30:27+00:00"}'
                    ],
                },
            ),
            types.Tool(
                name="list_all_campaigns",
                description="Get a list of all the campaigns.",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Individual campaign details, one per TextContent item",
                    "examples": [
                        '{"id": "abc123def", "type": "regular", "status": "sent", "create_time": "2023-04-15T13:27:36+00:00", "settings": {"subject_line": "Newsletter: April Update", "title": "April Newsletter"}, "report_summary": {"opens": 0, "unique_opens": 0, "open_rate": 0, "clicks": 0, "click_rate": 0}}'
                    ],
                },
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about a specific campaign including settings, tracking configuration, recipient details, and performance metrics",
                    "examples": [
                        '{"id": "abc123def", "type": "regular", "status": "sent", "create_time": "2023-04-15T13:27:36+00:00", "settings": {"subject_line": "Newsletter: April Update", "title": "April Newsletter"}, "recipients": {"list_id": "xyz789", "list_name": "Newsletter", "recipient_count": 1}, "report_summary": {"opens": 0, "unique_opens": 0, "open_rate": 0, "clicks": 0, "click_rate": 0}}'
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Individual daily activity metrics for the specified list, one per TextContent item",
                    "examples": [
                        '{"day": "2023-05-17", "emails_sent": 0, "unique_opens": 0, "recipient_clicks": 0, "hard_bounce": 0, "soft_bounce": 0, "subs": 0, "unsubs": 0, "other_adds": 0, "other_removes": 0}'
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the added or updated subscriber including email, status, merge fields, and subscription details",
                    "examples": [
                        '{"id": "abc123def", "email_address": "example@example.com", "status": "subscribed", "merge_fields": {"FNAME": "John", "LNAME": "Doe"}, "list_id": "xyz456", "timestamp_opt": "2023-05-17T05:05:13+00:00"}'
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the tag operation, confirming tags were successfully added to the subscriber",
                    "examples": [
                        '{"success": true, "email": "example@example.com", "list_id": "abc123def", "tags_added": ["tag1", "tag2"]}'
                    ],
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
                # Return each list item individually
                if "lists" in response and isinstance(response["lists"], list):
                    return [
                        TextContent(type="text", text=json.dumps(item))
                        for item in response["lists"]
                    ]
                return [TextContent(type="text", text=json.dumps(response))]

            elif name == "get_all_list":
                response = mailchimp.lists.get_all_lists()
                # Return each list item individually
                if "lists" in response and isinstance(response["lists"], list):
                    return [
                        TextContent(type="text", text=json.dumps(item))
                        for item in response["lists"]
                    ]
                return [TextContent(type="text", text=json.dumps(response))]

            elif name == "list_all_campaigns":
                response = mailchimp.campaigns.list()
                # Return each campaign individually
                if "campaigns" in response and isinstance(response["campaigns"], list):
                    return [
                        TextContent(type="text", text=json.dumps(item))
                        for item in response["campaigns"]
                    ]
                return [TextContent(type="text", text=json.dumps(response))]

            elif name == "campaign_info":
                campaign_id = arguments.get("campaign_id")
                response = mailchimp.campaigns.get(campaign_id)
                return [TextContent(type="text", text=json.dumps(response))]

            elif name == "recent_activity":
                list_id = arguments.get("list_id")
                response = mailchimp.lists.get_list_recent_activity(list_id)
                # Return each activity item individually
                if "activity" in response and isinstance(response["activity"], list):
                    return [
                        TextContent(type="text", text=json.dumps(item))
                        for item in response["activity"]
                    ]
                return [TextContent(type="text", text=json.dumps(response))]

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

                return [TextContent(type="text", text=json.dumps(response))]

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

                # API doesn't return data for this call, so create our own response object
                result = {
                    "success": True,
                    "email": email,
                    "list_id": list_id,
                    "tags_added": tags,
                }

                return [TextContent(type="text", text=json.dumps(result))]

            return [
                TextContent(
                    type="text", text=json.dumps({"error": f"Unknown tool: {name}"})
                )
            ]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
