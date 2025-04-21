import sys
import logging
import json
import os
import requests
from pathlib import Path
from typing import Optional, Any

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from src.utils.microsoft.util import (
    get_credentials,
    authenticate_and_save_credentials,
)


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "User.Read",
    "User.ReadBasic.All",
    "Team.ReadBasic.All",
    "Group.Read.All",
    "Directory.Read.All",
    "Chat.ReadWrite",
    "ChatMessage.Read",
    "ChatMessage.Send",
    "ChannelMessage.Read.All",
    "ChannelMessage.Send",
    "TeamMember.Read.All",
    "TeamMember.ReadWrite.All",
    "Channel.ReadBasic.All",
    "OnlineMeetings.ReadWrite",
    "offline_access",
]

TEAMS_OAUTH_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0/"
GRAPH_USERS_URL = GRAPH_BASE_URL + "users/"
GRAPH_TEAMS_URL = GRAPH_BASE_URL + "teams/"
GRAPH_GROUPS_URL = GRAPH_BASE_URL + "groups/"
GRAPH_CHATS_URL = GRAPH_BASE_URL + "chats/"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_teams_client(access_token: str) -> Any:
    """
    Create a Microsoft Teams client instance using the provided credentials.

    Args:
        credentials: A dictionary containing authentication credentials including:
            - access_token: The OAuth access token
            - token_type: The type of token (defaults to "Bearer")

    Returns:
        dict: A dictionary containing:
            - token: The access token
            - headers: Standard HTTP headers for Microsoft Graph API requests
            - base_url: The base URL for Microsoft Graph API endpoints
    """
    # Get the access token and token type from the credentials
    token_type = "Bearer"

    # Check if token type is in lowercase and convert to proper case
    if token_type.lower() == "bearer":
        token_type = "Bearer"

    logger.info(f"Using token type: {token_type}")

    # Standard headers for API requests
    standard_headers = {
        "Authorization": f"{token_type} {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    return {
        "token": access_token,
        "headers": standard_headers,
        "base_url": GRAPH_BASE_URL,
    }


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Create a new Microsoft Teams MCP server instance.

    Args:
        user_id: The user ID to create the server for
        api_key: Optional API key for authentication

    Returns:
        An MCP Server instance configured for Microsoft Teams operations
    """
    server = Server("teams-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return the list of available Microsoft Teams tools."""
        tools = [
            # TEAM MANAGEMENT TOOLS
            types.Tool(
                name="get_teams",
                description="Get the list of teams the user is a member of",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "OData filter for filtering teams",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of properties to include in the response",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_team_details",
                description="Get details of a specific Microsoft Teams team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team to retrieve details for",
                        }
                    },
                    "required": ["team_id"],
                },
            ),
            # CHANNEL MANAGEMENT TOOLS
            types.Tool(
                name="get_channels",
                description="Get the list of channels in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team to get channels from",
                        }
                    },
                    "required": ["team_id"],
                },
            ),
            types.Tool(
                name="create_channel",
                description="Create a new channel in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team where the channel will be created",
                        },
                        "display_name": {
                            "type": "string",
                            "description": "The display name of the channel (required)",
                        },
                        "description": {
                            "type": "string",
                            "description": "A description of the channel",
                        },
                        "membership_type": {
                            "type": "string",
                            "description": "Type of channel membership: 'standard' (visible to everyone) or 'private' (visible only to channel members)",
                            "enum": ["standard", "private"],
                        },
                    },
                    "required": ["team_id", "display_name"],
                },
            ),
            # CHAT AND MESSAGE TOOLS
            types.Tool(
                name="get_chats",
                description="Get the list of chats for the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "OData filter for filtering chats",
                        }
                    },
                },
            ),
            types.Tool(
                name="get_chat_messages",
                description="Get messages from a specific chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "The ID of the chat",
                        },
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of messages to return (default: 30)",
                        },
                    },
                    "required": ["chat_id"],
                },
            ),
            types.Tool(
                name="send_chat_message",
                description="Send a message in a chat",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "chat_id": {
                            "type": "string",
                            "description": "The ID of the chat",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content of the message (HTML format supported)",
                        },
                    },
                    "required": ["chat_id", "content"],
                },
            ),
            types.Tool(
                name="get_channel_messages",
                description="Get messages from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team",
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel",
                        },
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of messages to return (default: 20)",
                        },
                    },
                    "required": ["team_id", "channel_id"],
                },
            ),
            types.Tool(
                name="send_channel_message",
                description="Send a message to a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team",
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content of the message (HTML format supported)",
                        },
                    },
                    "required": ["team_id", "channel_id", "content"],
                },
            ),
            types.Tool(
                name="post_message_reply",
                description="Post a reply to a message in a Teams channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team",
                        },
                        "channel_id": {
                            "type": "string",
                            "description": "The ID of the channel",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "The ID of the message to reply to",
                        },
                        "content": {
                            "type": "string",
                            "description": "The content of the reply (HTML format supported)",
                        },
                    },
                    "required": ["team_id", "channel_id", "message_id", "content"],
                },
            ),
            # TEAM MEMBERSHIP TOOLS
            types.Tool(
                name="get_team_members",
                description="Get the list of members in a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team to get members from",
                        },
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of members to return (default: 50)",
                        },
                    },
                    "required": ["team_id"],
                },
            ),
            types.Tool(
                name="add_team_member",
                description="Add a user to a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team to add a member to",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to add to the team",
                        },
                        "roles": {
                            "type": "array",
                            "description": "The roles assigned to the user (e.g., 'owner', 'member')",
                            "items": {"type": "string", "enum": ["owner", "member"]},
                        },
                    },
                    "required": ["team_id", "user_id"],
                },
            ),
            types.Tool(
                name="remove_team_member",
                description="Remove a user from a team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "team_id": {
                            "type": "string",
                            "description": "The ID of the team to remove a member from",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to remove from the team",
                        },
                    },
                    "required": ["team_id", "user_id"],
                },
            ),
            # MEETINGS TOOLS
            types.Tool(
                name="create_meeting",
                description="Create a new online meeting in Microsoft Teams",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "The subject of the meeting (required)",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time of the meeting in ISO 8601 format (e.g., '2025-04-20T10:00:00Z') (required)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time of the meeting in ISO 8601 format (e.g., '2025-04-20T11:00:00Z') (required)",
                        },
                        "attendees": {
                            "type": "array",
                            "description": "List of email addresses of attendees",
                            "items": {"type": "string"},
                        },
                        "content": {
                            "type": "string",
                            "description": "The agenda or content of the meeting",
                        },
                    },
                    "required": ["subject", "start_time", "end_time"],
                },
            ),
        ]
        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent]:
        """Handle Microsoft Teams tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        teams_client = await create_teams_client(credentials)

        if arguments is None:
            arguments = {}

        try:
            if name == "get_teams":
                # Extract parameters for getting teams
                filter_query = arguments.get("filter")
                select = arguments.get("select")

                # Build the request URL
                # The /me/joinedTeams endpoint gets the teams the current user is a member of
                url = GRAPH_BASE_URL + "me/joinedTeams"

                # Prepare query parameters
                params = {}

                # Add optional parameters if provided
                if filter_query:
                    params["$filter"] = filter_query

                if select:
                    params["$select"] = select

                # Make the API request to get teams
                response = requests.get(
                    url, headers=teams_client["headers"], params=params, timeout=30
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    teams = result.get("value", [])
                    team_count = len(teams)

                    # Format the response for readability
                    formatted_result = {"totalTeams": team_count, "teams": teams}

                    # Check if there's a next page link
                    if "@odata.nextLink" in result:
                        formatted_result["nextLink"] = result["@odata.nextLink"]
                        formatted_result["note"] = (
                            "There are more teams available. Refine your query or use the nextLink to retrieve more."
                        )

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {team_count} teams:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving teams: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_team_details":
                # Extract team ID
                team_id = arguments.get("team_id")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}"

                # Make the API request to get the team details
                response = requests.get(
                    url, headers=teams_client["headers"], timeout=30
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    team_name = result.get("displayName", "Unknown Team")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved details for team '{team_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving team details: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_channels":
                # Extract team ID
                team_id = arguments.get("team_id")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/channels"

                # Make the API request to get channels
                response = requests.get(
                    url, headers=teams_client["headers"], timeout=30
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    channels = result.get("value", [])
                    channel_count = len(channels)

                    # Format the response for readability
                    formatted_result = {
                        "totalChannels": channel_count,
                        "teamId": team_id,
                        "channels": channels,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {channel_count} channels for team ID {team_id}:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving channels: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_channel":
                # Extract parameters
                team_id = arguments.get("team_id")
                display_name = arguments.get("display_name")
                description = arguments.get("description", "")
                membership_type = arguments.get("membership_type", "standard")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not display_name:
                    return [
                        types.TextContent(
                            type="text", text="Error: display_name is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/channels"

                # Prepare the request payload
                channel_data = {
                    "displayName": display_name,
                    "description": description,
                    "membershipType": membership_type,
                }

                # Make the API request to create the channel
                response = requests.post(
                    url, headers=teams_client["headers"], json=channel_data, timeout=30
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    channel_name = result.get("displayName", "Unknown Channel")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created channel '{channel_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error creating channel: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_chats":

                # Extract parameters
                filter_query = arguments.get("filter", None)

                # Build the request URL
                url = f"{GRAPH_BASE_URL}me/chats"

                # Prepare query parameters
                params = {"$expand": "members"}

                if filter_query:
                    params["$filter"] = filter_query

                # Make the API request to get chats
                response = requests.get(
                    url, headers=teams_client["headers"], params=params
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    chats = result.get("value", [])
                    chat_count = len(chats)

                    # Format the response for readability
                    formatted_result = {"totalChats": chat_count, "chats": chats}

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {chat_count} chats:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving chats: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_chat_messages":
                # Extract parameters
                chat_id = arguments.get("chat_id")
                top = arguments.get("top", 30)  # Default to 30 messages

                # Validate required parameters
                if not chat_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: chat_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_CHATS_URL}{chat_id}/messages"

                # Prepare query parameters
                params = {}

                if top:
                    params["$top"] = top

                # Make the API request to get chat messages
                response = requests.get(
                    url, headers=teams_client["headers"], params=params
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    messages = result.get("value", [])
                    message_count = len(messages)

                    # Format the response for readability
                    formatted_result = {
                        "totalMessages": message_count,
                        "chatId": chat_id,
                        "messages": messages,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {message_count} messages from chat {chat_id}:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving chat messages: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "send_chat_message":
                # Extract parameters
                chat_id = arguments.get("chat_id")
                content = arguments.get("content")

                # Validate required parameters
                if not chat_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: chat_id is required"
                        )
                    ]

                if not content:
                    return [
                        types.TextContent(
                            type="text", text="Error: content is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_CHATS_URL}{chat_id}/messages"

                # Prepare the message payload
                message_data = {"body": {"content": content, "contentType": "html"}}

                # Make the API request to send the message
                response = requests.post(
                    url, headers=teams_client["headers"], json=message_data
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully sent message to chat {chat_id}:\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error sending message: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_channel_messages":
                # Extract parameters
                team_id = arguments.get("team_id")
                channel_id = arguments.get("channel_id")
                top = arguments.get("top", 20)

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not channel_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: channel_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/channels/{channel_id}/messages"

                # Prepare query parameters
                params = {}

                if top:
                    params["$top"] = top

                # Make the API request to get channel messages
                response = requests.get(
                    url, headers=teams_client["headers"], params=params
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    messages = result.get("value", [])
                    message_count = len(messages)

                    # Format the response for readability
                    formatted_result = {
                        "totalMessages": message_count,
                        "teamId": team_id,
                        "channelId": channel_id,
                        "messages": messages,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {message_count} messages from channel:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving channel messages: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "send_channel_message":
                # Extract parameters
                team_id = arguments.get("team_id")
                channel_id = arguments.get("channel_id")
                content = arguments.get("content")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not channel_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: channel_id is required"
                        )
                    ]

                if not content:
                    return [
                        types.TextContent(
                            type="text", text="Error: content is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/channels/{channel_id}/messages"

                # Prepare the message payload
                message_data = {"body": {"content": content, "contentType": "html"}}

                # Make the API request to send the message
                response = requests.post(
                    url, headers=teams_client["headers"], json=message_data
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully sent message to channel:\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error sending channel message: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "post_message_reply":
                # Extract parameters
                team_id = arguments.get("team_id")
                channel_id = arguments.get("channel_id")
                message_id = arguments.get("message_id")
                content = arguments.get("content")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not channel_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: channel_id is required"
                        )
                    ]

                if not message_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: message_id is required"
                        )
                    ]

                if not content:
                    return [
                        types.TextContent(
                            type="text", text="Error: content is required"
                        )
                    ]

                # Build the request URL for posting a reply
                url = f"{GRAPH_TEAMS_URL}{team_id}/channels/{channel_id}/messages/{message_id}/replies"

                # Prepare the reply payload
                reply_data = {"body": {"content": content, "contentType": "html"}}

                # Make the API request to send the reply
                response = requests.post(
                    url, headers=teams_client["headers"], json=reply_data
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully posted reply to message {message_id}:\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = (
                        f"Error posting reply: {response.status_code} - {response.text}"
                    )
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_team_members":
                # Extract parameters
                team_id = arguments.get("team_id")
                top = arguments.get("top", 50)

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/members"

                # Prepare query parameters
                params = {}

                if top:
                    params["$top"] = top

                # Make the API request to get team members
                response = requests.get(
                    url, headers=teams_client["headers"], params=params
                )

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    members = result.get("value", [])
                    member_count = len(members)

                    # Format the response for readability
                    formatted_result = {
                        "totalMembers": member_count,
                        "teamId": team_id,
                        "members": members,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {member_count} members from team:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving team members: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "add_team_member":
                # Extract parameters
                team_id = arguments.get("team_id")
                user_id = arguments.get("user_id")
                roles = arguments.get("roles", ["member"])

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not user_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: user_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_TEAMS_URL}{team_id}/members"

                # Prepare the request payload
                member_data = {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": roles,
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users/{user_id}",
                }

                # Make the API request to add the team member
                response = requests.post(
                    url, headers=teams_client["headers"], json=member_data
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully added user {user_id} to team {team_id}:\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error adding team member: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "remove_team_member":
                # Extract parameters
                team_id = arguments.get("team_id")
                user_id = arguments.get("user_id")

                # Validate required parameters
                if not team_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: team_id is required"
                        )
                    ]

                if not user_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: user_id is required"
                        )
                    ]

                # First, we need to get the membership ID for this user in the team
                members_url = f"{GRAPH_TEAMS_URL}{team_id}/members"

                members_response = requests.get(
                    members_url, headers=teams_client["headers"]
                )

                if members_response.status_code != 200:
                    error_message = f"Error retrieving team members: {members_response.status_code} - {members_response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

                members_data = members_response.json()
                members = members_data.get("value", [])

                # Find the member with the matching user ID
                member_id = None
                for member in members:
                    if member.get("userId") == user_id:
                        member_id = member.get("id")
                        break

                if not member_id:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: User {user_id} is not a member of team {team_id}",
                        )
                    ]

                # Build the request URL to delete the member
                url = f"{GRAPH_TEAMS_URL}{team_id}/members/{member_id}"

                # Make the API request to remove the team member
                response = requests.delete(url, headers=teams_client["headers"])

                # Check if the request was successful
                # DELETE operations return 204 No Content when successful
                if response.status_code == 204:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully removed user {user_id} from team {team_id}",
                        )
                    ]
                else:
                    error_message = f"Error removing team member: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_meeting":
                # Extract parameters for creating a meeting
                subject = arguments.get("subject")
                start_time = arguments.get("start_time")
                end_time = arguments.get("end_time")
                attendees = arguments.get("attendees", [])
                content = arguments.get("content", "")

                # Validate required parameters
                if not subject:
                    return [
                        types.TextContent(
                            type="text", text="Error: subject is required"
                        )
                    ]

                if not start_time:
                    return [
                        types.TextContent(
                            type="text", text="Error: start_time is required"
                        )
                    ]

                if not end_time:
                    return [
                        types.TextContent(
                            type="text", text="Error: end_time is required"
                        )
                    ]

                # Build the request URL for creating an online meeting
                url = f"{GRAPH_BASE_URL}me/onlineMeetings"

                # Prepare the attendees list if provided
                attendee_list = []
                for attendee_email in attendees:
                    attendee_list.append(
                        {"identity": {"emailAddress": {"address": attendee_email}}}
                    )

                # Prepare the meeting payload
                meeting_data = {
                    "subject": subject,
                    "startDateTime": start_time,
                    "endDateTime": end_time,
                    "participants": {"attendees": attendee_list},
                }

                # Add content/agenda if provided
                if content:
                    meeting_data["agenda"] = content

                # Make the API request to create the meeting
                response = requests.post(
                    url, headers=teams_client["headers"], json=meeting_data, timeout=30
                )

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    meeting_id = result.get("id", "Unknown ID")
                    join_url = result.get("joinUrl", "Unknown Join URL")

                    formatted_result = {
                        "id": meeting_id,
                        "subject": subject,
                        "startDateTime": start_time,
                        "endDateTime": end_time,
                        "joinUrl": join_url,
                        "fullDetails": result,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created meeting '{subject}':\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error creating meeting: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(
                f"Error calling Microsoft Teams API: {e} {e.__traceback__.tb_lineno}"
            )
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="teams-server",
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
        print("  python main.py auth - Run authentication flow for a user")
        print("  python main.py - Run the server")
