import os
import sys
from typing import Optional, Iterable

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
    # Bot Token Scopes
    "channels:history",
    "channels:read",
    "chat:write",
    "chat:write.customize",
    "groups:read",
    "groups:write",
    "groups:history",
    "pins:read",
    "pins:write",
    "reactions:write",
    "files:read",
    "files:write",
    "im:read",
    "channels:manage",
    # User Token Scopes
    "users:read",
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
            resources = []

            # Get list of channels
            response = slack_client.conversations_list(
                types="public_channel,private_channel", limit=100, cursor=cursor or None
            )

            channels = response.get("channels", [])

            for channel in channels:
                channel_id = channel.get("id")
                channel_name = channel.get("name")
                is_private = channel.get("is_private", False)

                # Add channel resource
                resource = Resource(
                    uri=f"slack://channel/{channel_id}",
                    mimeType="text/plain",
                    name=f"#{channel_name}",
                    description=f"{'Private' if is_private else 'Public'} Slack channel: #{channel_name}",
                )
                resources.append(resource)

            return resources

        except SlackApiError as e:
            logger.error(f"Error listing Slack resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read resources from Slack"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        slack_client = await create_slack_client(server.user_id, api_key=server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("slack://"):
            raise ValueError(f"Invalid Slack URI: {uri_str}")

        parts = uri_str.replace("slack://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid Slack URI format: {uri_str}")

        resource_type, resource_id = parts

        try:
            if resource_type == "channel":
                response = slack_client.conversations_history(
                    channel=resource_id, limit=50
                )

                messages = response.get("messages", [])
                messages.reverse()

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

            else:
                raise ValueError(f"Unknown resource type: {resource_type}")

        except SlackApiError as e:
            logger.error(f"Error reading Slack resource: {e}")
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
                        '{"user":"U12345","type":"message","ts":"1234567890.123456","text":"This is a test message","team":"T12345","user_name":"test_user","user_profile":{"real_name":"Test User","display_name":"Test User"}}',
                        '{"user":"U67890","type":"message","ts":"1234567891.123456","text":"Hello there","team":"T12345","user_name":"another_user","user_profile":{"real_name":"Another User","display_name":"Another User"}}',
                    ],
                },
                requiredScopes=["channels:history", "groups:history", "im:read"],
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
                requiredScopes=["chat:write", "chat:write.customize"],
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
                            "items": {"type": "object"},
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
                requiredScopes=["chat:write", "chat:write.customize"],
            ),
            Tool(
                name="add_user_to_channel",
                description="Add a user to a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (with # for names)",
                        },
                        "user": {
                            "type": "string",
                            "description": "User ID or email to add to the channel",
                        },
                    },
                    "required": ["channel", "user"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of adding a user to a channel",
                    "examples": [
                        '{"ok": true, "channel": {"id": "C12345", "name": "general", "is_channel": true, "is_group": false, "is_private": false, "created": 1234567890, "creator": "U12345", "team_id": "T12345"}}'
                    ],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="react_to_message",
                description="Add a reaction to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name where the message is located",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Timestamp of the message to react to",
                        },
                        "reaction": {
                            "type": "string",
                            "description": "Emoji name to use as reaction (without colons)",
                        },
                    },
                    "required": ["channel", "timestamp", "reaction"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of adding a reaction",
                    "examples": ['{"ok": true}'],
                },
                requiredScopes=["reactions:write"],
            ),
            Tool(
                name="delete_message",
                description="Delete a Slack message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name where the message is located",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Timestamp of the message to delete",
                        },
                    },
                    "required": ["channel", "timestamp"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of delete operation",
                    "examples": [
                        '{"ok": true, "channel": "C12345", "ts": "1234567890.123456"}'
                    ],
                },
                requiredScopes=["chat:write"],
            ),
            Tool(
                name="get_message_thread",
                description="Retrieve a message and its replies",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name where the thread is located",
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Timestamp of the parent message of the thread",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of replies to return",
                        },
                    },
                    "required": ["channel", "thread_ts"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing parent message and its replies",
                    "examples": [
                        '{"user":"U12345","type":"message","ts":"1234567890.123456","text":"Thread reply message","thread_ts":"1234567890.123456","team":"T12345","user_name":"test_user","user_profile":{"real_name":"Test User","display_name":"Test User"}}'
                    ],
                },
                requiredScopes=["channels:history", "groups:history", "im:read"],
            ),
            Tool(
                name="pin_message",
                description="Pin a message in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name where the message is located",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Timestamp of the message to pin",
                        },
                    },
                    "required": ["channel", "timestamp"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of pin operation",
                    "examples": ['{"ok": true}'],
                },
                requiredScopes=["pins:write"],
            ),
            Tool(
                name="unpin_message",
                description="Unpin a message from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name where the message is located",
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Timestamp of the message to unpin",
                        },
                    },
                    "required": ["channel", "timestamp"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of unpin operation",
                    "examples": ['{"ok": true}'],
                },
                requiredScopes=["pins:write"],
            ),
            Tool(
                name="get_user_presence",
                description="Check a user's online status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "string",
                            "description": "User ID or email to check presence for",
                        },
                    },
                    "required": ["user"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing user presence information",
                    "examples": [
                        '{"ok": true, "presence": "active", "online": true, "auto_away": false, "manual_away": false, "connection_count": 1}'
                    ],
                },
                requiredScopes=["users:read"],
            ),
            Tool(
                name="invite_to_channel",
                description="Invite users to a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name to invite users to",
                        },
                        "users": {
                            "type": "string",
                            "description": "Comma-separated list of user IDs to invite",
                        },
                    },
                    "required": ["channel", "users"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of invitation operation",
                    "examples": [
                        '{"ok": true, "channel": {"id": "C12345", "name": "general", "is_channel": true, "is_group": false, "is_private": false, "created": 1234567890, "creator": "U12345", "team_id": "T12345"}}'
                    ],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="remove_from_channel",
                description="Remove a user from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name to remove user from",
                        },
                        "user": {
                            "type": "string",
                            "description": "User ID to remove from channel",
                        },
                    },
                    "required": ["channel", "user"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing response of removal operation",
                    "examples": ['{"ok": true, "errors": {}}'],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="list_pinned_items",
                description="List pinned items in a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name to list pinned items for",
                        },
                    },
                    "required": ["channel"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing pinned items in a channel",
                    "examples": [
                        '{"type":"message","created":1234567890,"created_by":"U12345","channel":"C12345","message":{"user":"U12345","type":"message","ts":"1234567890.123456","text":"Pinned message","pinned_to":["C12345"]}}'
                    ],
                },
                requiredScopes=["pins:read"],
            ),
            Tool(
                name="create_channel",
                description="Create a new public or private Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Channel name (lowercase, no spaces/periods, max 80 chars)",
                        },
                        "is_private": {
                            "type": "boolean",
                            "description": "Whether the channel should be private (default: false)",
                        },
                        "team_id": {
                            "type": "string",
                            "description": "Team ID to create the channel in (optional)",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing details of the created channel",
                    "examples": [
                        '{"ok": true, "channel": {"id": "C12345", "name": "testchannel", "is_channel": true, "is_group": false, "is_im": false, "is_private": false, "created": 1234567890, "is_archived": false, "is_general": false, "creator": "U12345", "team_id": "T12345"}}'
                    ],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="update_channel_topic",
                description="Update a channel's topic",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (with # for names)",
                        },
                        "topic": {
                            "type": "string",
                            "description": "New channel topic text",
                        },
                    },
                    "required": ["channel", "topic"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing result of the channel topic update",
                    "examples": [
                        '{"ok": true, "channel": {"id": "C12345", "name": "channelname", "topic": {"value": "Channel Topic Example", "creator": "U12345", "last_set": 1234567890}}}'
                    ],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="update_channel_purpose",
                description="Update a channel's purpose",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (with # for names)",
                        },
                        "purpose": {
                            "type": "string",
                            "description": "New channel purpose text",
                        },
                    },
                    "required": ["channel", "purpose"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing result of the channel purpose update",
                    "examples": [
                        '{"ok": true, "channel": {"id": "C12345", "name": "channelname", "purpose": {"value": "Channel Purpose Example", "creator": "U12345", "last_set": 1234567890}}}'
                    ],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="archive_channel",
                description="Archive a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (with # for names)",
                        },
                    },
                    "required": ["channel"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing result of the channel archiving operation",
                    "examples": ['{"ok": true}'],
                },
                requiredScopes=["channels:manage", "groups:write"],
            ),
            Tool(
                name="unarchive_channel",
                description="Unarchive a Slack channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel ID or name (with # for names)",
                        },
                    },
                    "required": ["channel"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing result of the channel unarchiving operation",
                    "examples": ['{"ok": true}'],
                },
                requiredScopes=["channels:manage", "groups:write"],
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

        def raw_response_processor(response):
            """Process Slack API responses into JSON"""
            if hasattr(response, "data"):
                response = response.data

            if isinstance(response, list):
                return [
                    TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in response
                ]

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        tool_config = {
            "read_messages": {
                "handler": lambda args: slack_client.conversations_history(
                    channel=args["resolved_channel"], limit=args.get("limit", 20)
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "limit": args.get("limit", 20),
                },
                "postprocess": lambda response: [
                    TextContent(type="text", text=json.dumps(message, indent=2))
                    for message in enrich_messages_sync(
                        slack_client, response.get("messages", [])
                    )
                ],
            },
            "send_message": {
                "handler": lambda args: slack_client.chat_postMessage(
                    channel=args["resolved_channel"],
                    text=args["text"],
                    thread_ts=args.get("thread_ts"),
                ),
                "preprocess": lambda args: {
                    "resolved_channel": get_channel_or_user_id(
                        slack_client, server, args["channel"]
                    ),
                    "text": args["text"],
                    "thread_ts": args.get("thread_ts"),
                },
                "postprocess": lambda response: [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [
                                {
                                    "status": "success",
                                    "channel": response["channel"],
                                    "ts": response["ts"],
                                    "message": response.get("message", {}),
                                }
                            ],
                            indent=2,
                        ),
                    )
                ],
            },
            "create_canvas": {
                "handler": lambda args: slack_client.chat_postMessage(
                    channel=args["resolved_channel"],
                    blocks=process_blocks(args["blocks"], args["title"]),
                    text=args["title"],
                    thread_ts=args.get("thread_ts"),
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "title": args["title"],
                    "blocks": args["blocks"],
                    "thread_ts": args.get("thread_ts"),
                },
                "postprocess": lambda response: [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            [
                                {
                                    "status": "success",
                                    "channel": response["channel"],
                                    "ts": response["ts"],
                                    "message": response.get("message", {}),
                                }
                            ],
                            indent=2,
                        ),
                    )
                ],
            },
            "get_message_thread": {
                "handler": lambda args: {
                    "parent": slack_client.conversations_history(
                        channel=args["resolved_channel"],
                        latest=args["thread_ts"],
                        limit=1,
                        inclusive=True,
                    ),
                    "replies": slack_client.conversations_replies(
                        channel=args["resolved_channel"],
                        ts=args["thread_ts"],
                        limit=args.get("limit", 20),
                    ),
                },
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "thread_ts": args["thread_ts"],
                    "limit": args.get("limit", 20),
                },
                "postprocess": lambda response: [
                    TextContent(type="text", text=json.dumps(message, indent=2))
                    for message in enrich_messages_sync(
                        slack_client, response["replies"].get("messages", [])
                    )
                ],
            },
            "list_pinned_items": {
                "handler": lambda args: slack_client.pins_list(
                    channel=args["resolved_channel"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    )
                },
                "postprocess": lambda response: [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            enrich_message_with_user_info_sync(slack_client, item),
                            indent=2,
                        ),
                    )
                    for item in response.get("items", [])
                ],
            },
            "add_user_to_channel": {
                "handler": lambda args: slack_client.conversations_invite(
                    channel=args["resolved_channel"], users=[args["resolved_user"]]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "resolved_user": (
                        get_user_id_sync(slack_client, server, args["user"])
                        if "@" in args["user"] or not args["user"].startswith("U")
                        else args["user"]
                    ),
                },
            },
            "react_to_message": {
                "handler": lambda args: slack_client.reactions_add(
                    channel=args["resolved_channel"],
                    timestamp=args["timestamp"],
                    name=args["clean_reaction"],
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "timestamp": args["timestamp"],
                    "clean_reaction": (
                        args["reaction"].strip(":")
                        if args["reaction"].startswith(":")
                        and args["reaction"].endswith(":")
                        else args["reaction"]
                    ),
                },
            },
            "delete_message": {
                "handler": lambda args: slack_client.chat_delete(
                    channel=args["resolved_channel"], ts=args["timestamp"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "timestamp": args["timestamp"],
                },
            },
            "pin_message": {
                "handler": lambda args: slack_client.pins_add(
                    channel=args["resolved_channel"], timestamp=args["timestamp"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "timestamp": args["timestamp"],
                },
            },
            "unpin_message": {
                "handler": lambda args: slack_client.pins_remove(
                    channel=args["resolved_channel"], timestamp=args["timestamp"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "timestamp": args["timestamp"],
                },
            },
            "get_user_presence": {
                "handler": lambda args: slack_client.users_getPresence(
                    user=args["resolved_user"]
                ),
                "preprocess": lambda args: {
                    "resolved_user": (
                        get_user_id_sync(slack_client, server, args["user"])
                        if "@" in args["user"] or not args["user"].startswith("U")
                        else args["user"]
                    )
                },
            },
            "invite_to_channel": {
                "handler": lambda args: slack_client.conversations_invite(
                    channel=args["resolved_channel"], users=args["user_ids"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "user_ids": [u.strip() for u in args["users"].split(",")],
                },
            },
            "remove_from_channel": {
                "handler": lambda args: slack_client.conversations_kick(
                    channel=args["resolved_channel"], user=args["resolved_user"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "resolved_user": (
                        get_user_id_sync(slack_client, server, args["user"])
                        if not args["user"].startswith("U")
                        else args["user"]
                    ),
                },
            },
            "create_channel": {
                "handler": lambda args: slack_client.conversations_create(
                    name=args["name"],
                    is_private=args.get("is_private", False),
                    team_id=args.get("team_id"),
                ),
                "preprocess": lambda args: args,
            },
            "update_channel_topic": {
                "handler": lambda args: slack_client.conversations_setTopic(
                    channel=args["resolved_channel"], topic=args["topic"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "topic": args["topic"],
                },
            },
            "update_channel_purpose": {
                "handler": lambda args: slack_client.conversations_setPurpose(
                    channel=args["resolved_channel"], purpose=args["purpose"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    ),
                    "purpose": args["purpose"],
                },
            },
            "archive_channel": {
                "handler": lambda args: slack_client.conversations_archive(
                    channel=args["resolved_channel"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    )
                },
            },
            "unarchive_channel": {
                "handler": lambda args: slack_client.conversations_unarchive(
                    channel=args["resolved_channel"]
                ),
                "preprocess": lambda args: {
                    "resolved_channel": (
                        get_channel_id_sync(slack_client, server, args["channel"])
                        if args["channel"].startswith("#")
                        else args["channel"]
                    )
                },
            },
        }

        try:
            if name in tool_config:
                config = tool_config[name]

                args = config["preprocess"](arguments)
                response = config["handler"](args)

                if "postprocess" in config:
                    return config["postprocess"](response)
                return raw_response_processor(response)
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


# Helper functions for the refactored approach
def get_channel_id_sync(slack_client, server, channel):
    """Synchronous wrapper to get channel ID from channel name"""
    if not channel.startswith("#"):
        return channel

    channel_name = channel[1:]

    if not hasattr(server, "channel_name_to_id_map"):
        server.channel_name_to_id_map = {}

    if channel_name in server.channel_name_to_id_map:
        return server.channel_name_to_id_map[channel_name]

    cursor = None
    while True:
        pagination_params = {
            "types": "public_channel,private_channel",
            "limit": 200,
        }
        if cursor:
            pagination_params["cursor"] = cursor

        response = slack_client.conversations_list(**pagination_params)

        for ch in response["channels"]:
            server.channel_name_to_id_map[ch["name"]] = ch["id"]
            if ch["name"] == channel_name:
                return ch["id"]

        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise ValueError(f"Channel {channel} not found")


def get_user_id_sync(slack_client, server, user):
    """Synchronous wrapper to get user ID from username or email"""
    if "@" in user:
        response = slack_client.users_lookupByEmail(email=user)
        if response["ok"]:
            return response["user"]["id"]
        else:
            raise ValueError(f"User with email {user} not found")

    if user.startswith("U"):
        return user

    if not hasattr(server, "user_name_to_id_map"):
        server.user_name_to_id_map = {}

    if user in server.user_name_to_id_map:
        return server.user_name_to_id_map[user]

    cursor = None
    while True:
        pagination_params = {"limit": 200}
        if cursor:
            pagination_params["cursor"] = cursor

        response = slack_client.users_list(**pagination_params)

        for u in response["members"]:
            if u.get("name"):
                server.user_name_to_id_map[u.get("name")] = u["id"]
            if u.get("real_name"):
                server.user_name_to_id_map[u.get("real_name")] = u["id"]

            if u.get("name") == user or u.get("real_name") == user:
                return u["id"]

        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    raise ValueError(f"User {user} not found")


def get_channel_or_user_id(slack_client, server, channel_or_user):
    """Resolve channel or user references to IDs"""
    if channel_or_user.startswith("#"):
        return get_channel_id_sync(slack_client, server, channel_or_user)
    elif channel_or_user.startswith("@"):
        user_name = channel_or_user[1:]
        user_id = get_user_id_sync(slack_client, server, user_name)

        dm_response = slack_client.conversations_open(users=user_id)
        return dm_response["channel"]["id"]
    else:
        return channel_or_user


def process_blocks(blocks, title):
    """Process blocks for canvas creation"""
    if blocks is None:
        blocks = []

    if isinstance(blocks, str):
        try:
            blocks = json.loads(blocks)
        except json.JSONDecodeError:
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": blocks}}]

    if not isinstance(blocks, list):
        blocks = [blocks]

    has_header = False
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "header":
            has_header = True
            break

    if not has_header and blocks:
        blocks.insert(
            0, {"type": "header", "text": {"type": "plain_text", "text": title}}
        )

    return blocks


def format_emoji(emoji):
    """Format emoji for status"""
    if not emoji.startswith(":"):
        emoji = f":{emoji}"
    if not emoji.endswith(":"):
        emoji = f"{emoji}:"
    return emoji


def enrich_message_with_user_info_sync(slack_client, message):
    """Synchronous version of enrich_message_with_user_info"""
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


def enrich_pinned_items(slack_client, items):
    """Enrich pinned items with user info"""
    for item in items:
        if item.get("type") == "message":
            message = item.get("message", {})
            item["message"] = enrich_message_with_user_info_sync(slack_client, message)
    return items


def enrich_messages_sync(slack_client, messages):
    """Enrich and reverse a list of messages"""
    # Reverse to get chronological order
    messages_copy = messages.copy()
    messages_copy.reverse()

    # Enrich messages with user information
    enriched_messages = []
    for message in messages_copy:
        enriched_message = enrich_message_with_user_info_sync(slack_client, message)
        enriched_messages.append(enriched_message)

    return enriched_messages
