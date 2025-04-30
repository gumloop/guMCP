import os
import sys
from typing import Optional, Iterable

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
import json
from datetime import datetime
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

from src.utils.slack.util import authenticate_and_save_credentials, get_credentials

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "channels:history",
    "channels:read",
    "chat:write",
    "chat:write.customize",
    "users:read",
    "groups:read",
    "groups:write",
    "groups:history",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_slack_client(user_id, api_key=None):
    """Create a new Slack client instance for this request"""
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return WebClient(token=token)


async def enrich_message_with_user_info(slack_client, message):
    """Add user info to the message"""
    user_id = message.get("user", "Unknown")

    if user_id != "Unknown":
        try:
            user_info = slack_client.users_info(user=user_id)
            if user_info["ok"]:
                user_data = user_info["user"]
                message["user_name"] = user_data.get("real_name") or user_data.get(
                    "name", "Unknown"
                )
                message["user_profile"] = user_data.get("profile", {})
        except SlackApiError:
            message["user_name"] = "Unknown"

    return message


async def get_channel_id(slack_client, server, channel_name):
    """Helper function to get channel ID from channel name with pagination support"""
    # Create a channel name to ID map if it doesn't exist
    if not hasattr(server, "channel_name_to_id_map"):
        server.channel_name_to_id_map = {}

    # Check if we already have this channel in our map
    if channel_name in server.channel_name_to_id_map:
        return server.channel_name_to_id_map[channel_name]

    # Look up channel ID with pagination
    cursor = None
    while True:
        pagination_params = {
            "types": "public_channel,private_channel",
            "limit": 200,
        }
        if cursor:
            pagination_params["cursor"] = cursor

        response = slack_client.conversations_list(**pagination_params)

        # Update our channel map with all channels in this batch
        for ch in response["channels"]:
            server.channel_name_to_id_map[ch["name"]] = ch["id"]
            if ch["name"] == channel_name:
                return ch["id"]

        # Check if there are more channels to fetch
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return None


async def get_user_id(slack_client, server, user_name):
    """Helper function to get user ID from username with pagination support"""
    # Create a user name to ID map if it doesn't exist
    if not hasattr(server, "user_name_to_id_map"):
        server.user_name_to_id_map = {}

    # Check if we already have this user in our map
    if user_name in server.user_name_to_id_map:
        return server.user_name_to_id_map[user_name]

    # Look up user ID with pagination
    cursor = None
    while True:
        pagination_params = {"limit": 200}
        if cursor:
            pagination_params["cursor"] = cursor

        response = slack_client.users_list(**pagination_params)

        # Update our user map with all users in this batch
        for user in response["members"]:
            if user.get("name"):
                server.user_name_to_id_map[user.get("name")] = user["id"]
            if user.get("real_name"):
                server.user_name_to_id_map[user.get("real_name")] = user["id"]

            if user.get("name") == user_name or user.get("real_name") == user_name:
                return user["id"]

        # Check if there are more users to fetch
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    return None


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("slack-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Slack channels"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        slack_client = await create_slack_client(server.user_id, api_key=server.api_key)

        try:
            # Get list of channels
            response = slack_client.conversations_list(
                types="public_channel,private_channel", limit=100, cursor=cursor or None
            )

            channels = response.get("channels", [])

            resources = []
            for channel in channels:
                channel_id = channel.get("id")
                channel_name = channel.get("name")
                is_private = channel.get("is_private", False)

                resource = Resource(
                    uri=f"slack://channel/{channel_id}",
                    mimeType="text/plain",
                    name=f"#{channel_name}",
                    description=f"{'Private' if is_private else 'Public'} Slack channel: #{channel_name}",
                )
                resources.append(resource)

            return resources

        except SlackApiError as e:
            logger.error(f"Error listing Slack channels: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read messages from a Slack channel"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        slack_client = await create_slack_client(server.user_id, api_key=server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("slack://"):
            raise ValueError(f"Invalid Slack URI: {uri_str}")

        # Parse the URI to get channel type and ID
        parts = uri_str.replace("slack://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid Slack URI format: {uri_str}")

        _, channel_id = parts

        try:
            # Get channel history
            response = slack_client.conversations_history(
                channel=channel_id, limit=50  # Limit to last 50 messages
            )

            messages = response.get("messages", [])

            # Reverse to get chronological order
            messages.reverse()

            # Enrich messages with user information
            enriched_messages = []
            for message in messages:
                enriched_message = await enrich_message_with_user_info(
                    slack_client, message
                )
                enriched_messages.append(enriched_message)

            return [
                ReadResourceContents(
                    content=json.dumps(enriched_messages, indent=2),
                    mime_type="application/json",
                )
            ]

        except SlackApiError as e:
            logger.error(f"Error reading Slack channel: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="read_messages",
                description="Read messages from a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel ID or name (with # for names)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of messages to return (default: 20)",
                        },
                    },
                    "required": ["channel"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing data of messages with user and message details",
                    "examples": [
                        '[{"user":"U12345","type":"message","ts":"1234567890.123456","text":"This is a test message","team":"T12345","user_name":"test_user","user_profile":{"real_name":"Test User","display_name":"Test User"}}, {"user":"U67890","type":"message","ts":"1234567891.123456","text":"Hello there","team":"T12345","user_name":"another_user","user_profile":{"real_name":"Another User","display_name":"Another User"}}]'
                    ],
                },
            ),
            Tool(
                name="send_message",
                description="Send a message to a Slack channel or user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel ID or name (with # for channel names, @ for usernames)",
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text to send",
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Optional thread timestamp to reply to a thread",
                        },
                    },
                    "required": ["channel", "text"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of the message send operation",
                    "examples": [
                        '[{"status":"success","channel":"C12345","ts":"1234567890.123456","message":{"user":"U12345","type":"message","ts":"1234567890.123456","text":"This is a test message","team":"T12345"}}]'
                    ],
                },
            ),
            Tool(
                name="create_canvas",
                description="Create a Slack canvas message with rich content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Slack channel ID or name (with # for names)",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the canvas",
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Array of Slack block kit elements as JSON objects",
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Optional thread timestamp to attach canvas to a thread",
                        },
                    },
                    "required": ["channel", "title", "blocks"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of the canvas creation",
                    "examples": [
                        '[{"status":"success","channel":"C12345","ts":"1234567890.123456","message":{"user":"U12345","type":"message","ts":"1234567890.123456","text":"Test Canvas","team":"T12345","blocks":[{"type":"header","text":{"type":"plain_text","text":"Test Canvas"}},{"type":"section","text":{"type":"mrkdwn","text":"This is a test canvas message"}}]}}]'
                    ],
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

        if arguments is None:
            arguments = {}

        slack_client = await create_slack_client(server.user_id, api_key=server.api_key)

        try:
            if name == "read_messages":
                if "channel" not in arguments:
                    raise ValueError("Missing channel parameter")

                channel = arguments["channel"]
                limit = arguments.get("limit", 20)

                # Handle channel names (starting with #)
                if channel.startswith("#"):
                    channel_name = channel[1:]
                    channel_id = await get_channel_id(
                        slack_client, server, channel_name
                    )
                    if channel_id is None:
                        error_response = {"error": f"Channel {channel} not found"}
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
                            )
                        ]
                    channel = channel_id

                # Get messages
                response = slack_client.conversations_history(
                    channel=channel, limit=limit
                )

                messages = response.get("messages", [])
                messages.reverse()  # Chronological order

                # Enrich messages with user information
                enriched_messages = []
                for message in messages:
                    enriched_message = await enrich_message_with_user_info(
                        slack_client, message
                    )
                    enriched_messages.append(enriched_message)

                return [
                    TextContent(type="text", text=json.dumps(message, indent=2))
                    for message in enriched_messages
                ]

            elif name == "send_message":
                if "channel" not in arguments or "text" not in arguments:
                    raise ValueError("Missing required parameters: channel and text")

                channel = arguments["channel"]
                text = arguments["text"]
                thread_ts = arguments.get("thread_ts")

                # Handle channel or user names
                if channel.startswith("#"):
                    channel_name = channel[1:]
                    channel_id = await get_channel_id(
                        slack_client, server, channel_name
                    )
                    if channel_id is None:
                        error_response = {"error": f"Channel {channel} not found"}
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
                            )
                        ]
                    channel = channel_id

                elif channel.startswith("@"):
                    user_name = channel[1:]
                    user_id = await get_user_id(slack_client, server, user_name)
                    if user_id is None:
                        error_response = {"error": f"User {channel} not found"}
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
                            )
                        ]

                    # Open DM channel
                    dm_response = slack_client.conversations_open(users=user_id)
                    channel = dm_response["channel"]["id"]

                # Send the message
                message_args = {"channel": channel, "text": text}

                if thread_ts:
                    message_args["thread_ts"] = thread_ts

                response = slack_client.chat_postMessage(**message_args)
                result = {
                    "status": "success",
                    "channel": channel,
                    "ts": response["ts"],
                    "message": response.get("message", {}),
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            elif name == "create_canvas":
                if not all(k in arguments for k in ["channel", "title", "blocks"]):
                    raise ValueError(
                        "Missing required parameters: channel, title, blocks"
                    )

                channel = arguments["channel"]
                title = arguments["title"]
                blocks = arguments["blocks"]
                thread_ts = arguments.get("thread_ts")

                # Handle channel names
                if channel.startswith("#"):
                    channel_name = channel[1:]
                    channel_id = await get_channel_id(
                        slack_client, server, channel_name
                    )
                    if channel_id is None:
                        error_response = {"error": f"Channel {channel} not found"}
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
                            )
                        ]
                    channel = channel_id

                # Ensure blocks is valid JSON if it's a string
                if isinstance(blocks, str):
                    try:
                        blocks = json.loads(blocks)
                    except json.JSONDecodeError:
                        error_response = {"error": "Invalid JSON in blocks parameter"}
                        return [
                            TextContent(
                                type="text", text=json.dumps(error_response, indent=2)
                            )
                        ]

                # Add title block at the beginning if blocks don't already have a header
                has_header = False
                for block in blocks:
                    if block.get("type") == "header":
                        has_header = True
                        break

                if not has_header:
                    blocks.insert(
                        0,
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": title},
                        },
                    )

                # Send the message
                message_args = {
                    "channel": channel,
                    "blocks": blocks,
                    "text": title,  # Fallback text
                }

                if thread_ts:
                    message_args["thread_ts"] = thread_ts

                response = slack_client.chat_postMessage(**message_args)
                result = {
                    "status": "success",
                    "channel": channel,
                    "ts": response["ts"],
                    "message": response.get("message", {}),
                }

                return [TextContent(type="text", text=json.dumps(result, indent=2))]

            else:
                error_response = {"error": f"Unknown tool: {name}"}
                return [
                    TextContent(type="text", text=json.dumps(error_response, indent=2))
                ]

        except SlackApiError as e:
            logger.error(f"Slack API error: {e}")
            error_response = {"error": str(e)}
            return [TextContent(type="text", text=json.dumps(error_response, indent=2))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="slack-server",
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
