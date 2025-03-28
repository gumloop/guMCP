import os
import sys
from typing import Optional, List, Dict, Any

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import json

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

import discord
from discord.ext import commands
import asyncio
import aiohttp

from utils.discord.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


# Discord bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Global bot instance
bot = None

# Required OAuth2 scopes for Discord
SCOPES = ["bot", "identify", "guilds", "email"]


async def create_discord_bot(user_id, api_key=None):
    """Create a Discord bot instance for this user"""
    global bot

    if bot is not None:
        return bot

    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

    logger.info(f"Using OAuth access token for Discord API access")

    # Make sure intents are properly configured
    bot = commands.Bot(command_prefix="!", intents=intents)

    # Log the token type for debugging (not the actual token)
    logger.info(
        f"Got token of type: {type(token).__name__}, length: {len(token) if isinstance(token, str) else 'not a string'}"
    )

    return bot


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("discord-server")

    server.user_id = user_id
    server.api_key = api_key
    server.bot_task = None
    server.bot_ready = asyncio.Event()

    async def start_bot_background():
        """Start the Discord REST API client in the background"""
        try:
            # Get credentials
            token = await get_credentials(
                server.user_id, SERVICE_NAME, api_key=server.api_key
            )
            # Create a session with the token for REST API calls
            server.headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            server.session = aiohttp.ClientSession(headers=server.headers)

            # Test the connection
            async with server.session.get(
                "https://discord.com/api/v10/users/@me"
            ) as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    logger.info(
                        f"Connected as {user_data.get('username', 'Unknown user')}"
                    )
                    server.user_data = user_data
                else:
                    error_text = await resp.text()
                    logger.error(
                        f"Failed to connect to Discord API: {resp.status} {error_text}"
                    )
                    raise ValueError(f"Discord API connection failed: {resp.status}")

            # Get guilds the user has access to
            async with server.session.get(
                "https://discord.com/api/v10/users/@me/guilds"
            ) as resp:
                if resp.status == 200:
                    server.guilds = await resp.json()
                    logger.info(f"Retrieved {len(server.guilds)} guilds")
                else:
                    error_text = await resp.text()
                    logger.error(f"Failed to fetch guilds: {resp.status} {error_text}")
                    server.guilds = []

            # Signal that we're ready
            server.bot_ready.set()

        except Exception as e:
            logger.error(f"Error in API connection: {e}")
            raise

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[types.Resource]:
        """List channels from Discord server"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        if server.bot_task is None:
            server.bot_task = asyncio.create_task(start_bot_background())
            await asyncio.wait_for(server.bot_ready.wait(), timeout=30)

        resources = []

        # Use REST API to get channels for each guild
        for guild in server.guilds:
            guild_id = guild["id"]
            guild_name = guild["name"]

            # Get channels for this guild
            async with server.session.get(
                f"https://discord.com/api/v10/guilds/{guild_id}/channels"
            ) as resp:
                if resp.status == 200:
                    channels = await resp.json()

                    # Add text channels to resources
                    for channel in channels:
                        if channel["type"] == 0:  # 0 is text channel
                            resources.append(
                                types.Resource(
                                    uri=f"discord:///{guild_id}/{channel['id']}",
                                    mime_type="text/plain",
                                    name=f"{guild_name}/{channel['name']}",
                                )
                            )
                else:
                    error_text = await resp.text()
                    logger.error(
                        f"Failed to fetch channels for guild {guild_id}: {resp.status} {error_text}"
                    )

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: types.AnyUrl) -> list[types.TextContent]:
        """Read messages from a Discord channel by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        if server.bot_task is None:
            server.bot_task = asyncio.create_task(start_bot_background())
            await asyncio.wait_for(server.bot_ready.wait(), timeout=30)

        # Convert AnyUrl to string before using string methods
        uri_str = str(uri)
        logger.info(f"URI string representation: {uri_str}")

        try:
            # Parse the URI safely
            if uri_str.startswith("discord:///"):
                path = uri_str.replace("discord:///", "")
                parts = path.split("/", 1)
                if len(parts) >= 2:
                    guild_id, channel_id = parts[0], parts[1]
                else:
                    raise ValueError(f"Invalid URI format: {uri_str}, parts: {parts}")
            else:
                raise ValueError(f"Unexpected URI format: {uri_str}")

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Channel not found: {channel_id}",
                            mime_type="text/plain",
                        )
                    ]

            messages = []
            async for message in channel.history(limit=25):
                messages.append(
                    f"{message.author.name} ({message.created_at}): {message.content}"
                )

            content = "\n".join(messages)

            return [
                types.TextContent(type="text", text=content, mime_type="text/plain")
            ]
        except Exception as e:
            logger.error(f"Error reading resource: {e}")
            return [
                types.TextContent(
                    type="text",
                    text=f"Error reading resource: {e}",
                    mime_type="text/plain",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            types.Tool(
                name="send_message",
                description="Send a message to a Discord channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "content": {
                            "type": "string",
                            "description": "Message content to send",
                        },
                    },
                    "required": ["channel_id", "content"],
                },
            ),
            types.Tool(
                name="read_messages",
                description="Read recent messages from a Discord channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Number of messages to read (default: 10)",
                        },
                    },
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="add_reaction",
                description="Add a reaction to a message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message ID to react to",
                        },
                        "emoji": {
                            "type": "string",
                            "description": "Emoji to react with",
                        },
                    },
                    "required": ["channel_id", "message_id", "emoji"],
                },
            ),
            # New tools
            types.Tool(
                name="edit_message",
                description="Edit an existing message sent by the bot",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message ID to edit",
                        },
                        "content": {
                            "type": "string",
                            "description": "New message content",
                        },
                    },
                    "required": ["channel_id", "message_id", "content"],
                },
            ),
            types.Tool(
                name="delete_message",
                description="Delete a message from a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "message_id": {
                            "type": "string",
                            "description": "Message ID to delete",
                        },
                    },
                    "required": ["channel_id", "message_id"],
                },
            ),
            types.Tool(
                name="send_embed",
                description="Send a rich embed message to a channel",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel_id": {
                            "type": "string",
                            "description": "Discord channel ID",
                        },
                        "title": {"type": "string", "description": "Embed title"},
                        "description": {
                            "type": "string",
                            "description": "Embed description",
                        },
                        "color": {
                            "type": "string",
                            "description": "Embed color in hex (e.g., '#FF0000')",
                        },
                        "footer": {
                            "type": "string",
                            "description": "Embed footer text",
                        },
                        "image_url": {
                            "type": "string",
                            "description": "URL for embed image",
                        },
                        "thumbnail_url": {
                            "type": "string",
                            "description": "URL for embed thumbnail",
                        },
                        "fields": {
                            "type": "array",
                            "description": "List of fields (name, value, inline)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"},
                                    "inline": {"type": "boolean"},
                                },
                            },
                        },
                    },
                    "required": ["channel_id", "title"],
                },
            ),
            types.Tool(
                name="get_user_info",
                description="Retrieve information about a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Discord user ID"},
                    },
                    "required": ["user_id"],
                },
            ),
            types.Tool(
                name="send_dm",
                description="Send a direct message to a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Discord user ID"},
                        "content": {
                            "type": "string",
                            "description": "Message content to send",
                        },
                    },
                    "required": ["user_id", "content"],
                },
            ),
            types.Tool(
                name="ban_member",
                description="Ban a member from a server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "Discord server/guild ID",
                        },
                        "user_id": {"type": "string", "description": "User ID to ban"},
                        "reason": {
                            "type": "string",
                            "description": "Reason for the ban",
                        },
                        "delete_message_days": {
                            "type": "number",
                            "description": "Number of days of messages to delete (0-7)",
                        },
                    },
                    "required": ["guild_id", "user_id"],
                },
            ),
            types.Tool(
                name="kick_member",
                description="Kick a member from a server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "Discord server/guild ID",
                        },
                        "user_id": {"type": "string", "description": "User ID to kick"},
                        "reason": {
                            "type": "string",
                            "description": "Reason for the kick",
                        },
                    },
                    "required": ["guild_id", "user_id"],
                },
            ),
            types.Tool(
                name="mute_member",
                description="Mute or unmute a member in voice channels",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "Discord server/guild ID",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "User ID to mute/unmute",
                        },
                        "mute": {
                            "type": "boolean",
                            "description": "True to mute, False to unmute",
                        },
                    },
                    "required": ["guild_id", "user_id", "mute"],
                },
            ),
            types.Tool(
                name="assign_role",
                description="Add or remove a role from a member",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "Discord server/guild ID",
                        },
                        "user_id": {"type": "string", "description": "User ID"},
                        "role_id": {
                            "type": "string",
                            "description": "Role ID to add/remove",
                        },
                        "add": {
                            "type": "boolean",
                            "description": "True to add the role, False to remove it",
                        },
                    },
                    "required": ["guild_id", "user_id", "role_id", "add"],
                },
            ),
            types.Tool(
                name="list_members",
                description="Get a list of members in a server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "guild_id": {
                            "type": "string",
                            "description": "Discord server/guild ID",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of members to fetch (default: 50, max: 1000)",
                        },
                    },
                    "required": ["guild_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if server.bot_task is None:
            server.bot_task = asyncio.create_task(start_bot_background())
            await asyncio.wait_for(server.bot_ready.wait(), timeout=30)

        if name == "send_message":
            if (
                not arguments
                or "channel_id" not in arguments
                or "content" not in arguments
            ):
                raise ValueError("Missing required parameters: channel_id and content")

            channel_id = arguments["channel_id"]
            content = arguments["content"]

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Channel not found: {channel_id}",
                            mime_type="text/plain",
                        )
                    ]

            message = await channel.send(content)

            return [
                types.TextContent(
                    type="text",
                    text=f"Message sent successfully. Message ID: {message.id}",
                    mime_type="text/plain",
                )
            ]

        elif name == "read_messages":
            if not arguments or "channel_id" not in arguments:
                raise ValueError("Missing required parameter: channel_id")

            channel_id = arguments["channel_id"]
            limit = int(arguments.get("limit", 10))

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Channel not found: {channel_id}",
                            mime_type="text/plain",
                        )
                    ]

            messages = []
            async for message in channel.history(limit=limit):
                reactions = []
                for reaction in message.reactions:
                    emoji = str(reaction.emoji)
                    count = reaction.count
                    reactions.append(f"{emoji}({count})")

                reaction_text = ", ".join(reactions) if reactions else "No reactions"

                messages.append(
                    f"{message.author.name} ({message.created_at}): {message.content}\n"
                    f"Message ID: {message.id} | Reactions: {reaction_text}"
                )

            content = "\n\n".join(messages)

            return [
                types.TextContent(
                    type="text",
                    text=f"Recent messages from channel {channel.name}:\n\n{content}",
                    mime_type="text/plain",
                )
            ]

        elif name == "add_reaction":
            if (
                not arguments
                or "channel_id" not in arguments
                or "message_id" not in arguments
                or "emoji" not in arguments
            ):
                raise ValueError(
                    "Missing required parameters: channel_id, message_id, and emoji"
                )

            channel_id = arguments["channel_id"]
            message_id = arguments["message_id"]
            emoji = arguments["emoji"]

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Channel not found: {channel_id}",
                            mime_type="text/plain",
                        )
                    ]

            # Get the message
            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Message not found: {message_id}",
                        mime_type="text/plain",
                    )
                ]

            try:
                await message.add_reaction(emoji)
            except discord.HTTPException as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Failed to add reaction: {str(e)}",
                        mime_type="text/plain",
                    )
                ]

            return [
                types.TextContent(
                    type="text",
                    text=f"Added reaction {emoji} to message {message_id}",
                    mime_type="text/plain",
                )
            ]

        elif name == "edit_message":
            if (
                not arguments
                or "channel_id" not in arguments
                or "message_id" not in arguments
                or "content" not in arguments
            ):
                raise ValueError(
                    "Missing required parameters: channel_id, message_id, and content"
                )

            channel_id = arguments["channel_id"]
            message_id = arguments["message_id"]
            content = arguments["content"]

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text", text=f"Channel not found: {channel_id}"
                        )
                    ]

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return [
                    types.TextContent(
                        type="text", text=f"Message not found: {message_id}"
                    )
                ]

            if message.author.id != bot.user.id:
                return [
                    types.TextContent(
                        type="text", text="Cannot edit messages sent by other users"
                    )
                ]

            await message.edit(content=content)

            return [
                types.TextContent(
                    type="text", text=f"Message {message_id} edited successfully"
                )
            ]

        elif name == "delete_message":
            if (
                not arguments
                or "channel_id" not in arguments
                or "message_id" not in arguments
            ):
                raise ValueError(
                    "Missing required parameters: channel_id and message_id"
                )

            channel_id = arguments["channel_id"]
            message_id = arguments["message_id"]

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text", text=f"Channel not found: {channel_id}"
                        )
                    ]

            try:
                message = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                return [
                    types.TextContent(
                        type="text", text=f"Message not found: {message_id}"
                    )
                ]

            await message.delete()

            return [
                types.TextContent(
                    type="text", text=f"Message {message_id} deleted successfully"
                )
            ]

        elif name == "send_embed":
            if (
                not arguments
                or "channel_id" not in arguments
                or "title" not in arguments
            ):
                raise ValueError("Missing required parameters: channel_id and title")

            channel_id = arguments["channel_id"]

            channel = bot.get_channel(int(channel_id))
            if not channel:
                try:
                    channel = await bot.fetch_channel(int(channel_id))
                except discord.NotFound:
                    return [
                        types.TextContent(
                            type="text", text=f"Channel not found: {channel_id}"
                        )
                    ]

            embed = discord.Embed(
                title=arguments["title"],
                description=arguments.get("description", ""),
                color=(
                    int(arguments.get("color", "#0099ff").lstrip("#"), 16)
                    if "color" in arguments
                    else discord.Color.blue()
                ),
            )

            if "footer" in arguments:
                embed.set_footer(text=arguments["footer"])

            if "image_url" in arguments:
                embed.set_image(url=arguments["image_url"])

            if "thumbnail_url" in arguments:
                embed.set_thumbnail(url=arguments["thumbnail_url"])

            if "fields" in arguments and isinstance(arguments["fields"], list):
                for field in arguments["fields"]:
                    if isinstance(field, dict) and "name" in field and "value" in field:
                        embed.add_field(
                            name=field["name"],
                            value=field["value"],
                            inline=field.get("inline", False),
                        )

            message = await channel.send(embed=embed)

            return [
                types.TextContent(
                    type="text",
                    text=f"Embed sent successfully. Message ID: {message.id}",
                )
            ]

        elif name == "get_user_info":
            if not arguments or "user_id" not in arguments:
                raise ValueError("Missing required parameter: user_id")

            user_id = arguments["user_id"]

            try:
                user = await bot.fetch_user(int(user_id))
            except discord.NotFound:
                return [
                    types.TextContent(type="text", text=f"User not found: {user_id}")
                ]

            user_info = {
                "id": str(user.id),
                "name": user.name,
                "display_name": user.display_name,
                "discriminator": user.discriminator,
                "avatar_url": str(user.avatar.url) if user.avatar else None,
                "bot": user.bot,
                "system": user.system,
                "created_at": user.created_at.isoformat(),
            }

            return [
                types.TextContent(type="text", text=json.dumps(user_info, indent=2))
            ]

        elif name == "send_dm":
            if (
                not arguments
                or "user_id" not in arguments
                or "content" not in arguments
            ):
                raise ValueError("Missing required parameters: user_id and content")

            user_id = arguments["user_id"]
            content = arguments["content"]

            try:
                user = await bot.fetch_user(int(user_id))
            except discord.NotFound:
                return [
                    types.TextContent(type="text", text=f"User not found: {user_id}")
                ]

            dm_channel = await user.create_dm()
            message = await dm_channel.send(content)

            return [
                types.TextContent(
                    type="text", text=f"DM sent successfully. Message ID: {message.id}"
                )
            ]

        elif name == "ban_member":
            if (
                not arguments
                or "guild_id" not in arguments
                or "user_id" not in arguments
            ):
                raise ValueError("Missing required parameters: guild_id and user_id")

            guild_id = arguments["guild_id"]
            user_id = arguments["user_id"]
            reason = arguments.get("reason", "No reason provided")
            delete_message_days = min(
                7, max(0, int(arguments.get("delete_message_days", 0)))
            )

            guild = bot.get_guild(int(guild_id))
            if not guild:
                return [
                    types.TextContent(type="text", text=f"Server not found: {guild_id}")
                ]

            if not guild.me.guild_permissions.ban_members:
                return [
                    types.TextContent(
                        type="text", text="Bot does not have permission to ban members"
                    )
                ]

            try:
                await guild.ban(
                    discord.Object(id=int(user_id)),
                    reason=reason,
                    delete_message_days=delete_message_days,
                )
            except discord.Forbidden:
                return [
                    types.TextContent(
                        type="text", text="Insufficient permissions to ban this user"
                    )
                ]
            except discord.NotFound:
                return [
                    types.TextContent(type="text", text=f"User not found: {user_id}")
                ]
            except discord.HTTPException as e:
                return [
                    types.TextContent(type="text", text=f"Failed to ban user: {str(e)}")
                ]

            return [
                types.TextContent(
                    type="text", text=f"User {user_id} banned successfully"
                )
            ]

        elif name == "kick_member":
            if (
                not arguments
                or "guild_id" not in arguments
                or "user_id" not in arguments
            ):
                raise ValueError("Missing required parameters: guild_id and user_id")

            guild_id = arguments["guild_id"]
            user_id = arguments["user_id"]
            reason = arguments.get("reason", "No reason provided")

            guild = bot.get_guild(int(guild_id))
            if not guild:
                return [
                    types.TextContent(type="text", text=f"Server not found: {guild_id}")
                ]

            if not guild.me.guild_permissions.kick_members:
                return [
                    types.TextContent(
                        type="text", text="Bot does not have permission to kick members"
                    )
                ]

            try:
                member = guild.get_member(int(user_id))
                if not member:
                    return [
                        types.TextContent(
                            type="text", text=f"Member not found in server: {user_id}"
                        )
                    ]

                await guild.kick(member, reason=reason)
            except discord.Forbidden:
                return [
                    types.TextContent(
                        type="text", text="Insufficient permissions to kick this user"
                    )
                ]
            except discord.HTTPException as e:
                return [
                    types.TextContent(
                        type="text", text=f"Failed to kick user: {str(e)}"
                    )
                ]

            return [
                types.TextContent(
                    type="text", text=f"User {user_id} kicked successfully"
                )
            ]

        elif name == "mute_member":
            if (
                not arguments
                or "guild_id" not in arguments
                or "user_id" not in arguments
                or "mute" not in arguments
            ):
                raise ValueError(
                    "Missing required parameters: guild_id, user_id, and mute"
                )

            guild_id = arguments["guild_id"]
            user_id = arguments["user_id"]
            mute = arguments["mute"]

            guild = bot.get_guild(int(guild_id))
            if not guild:
                return [
                    types.TextContent(type="text", text=f"Server not found: {guild_id}")
                ]

            if not guild.me.guild_permissions.mute_members:
                return [
                    types.TextContent(
                        type="text", text="Bot does not have permission to mute members"
                    )
                ]

            member = guild.get_member(int(user_id))
            if not member:
                return [
                    types.TextContent(
                        type="text", text=f"Member not found in server: {user_id}"
                    )
                ]

            if not member.voice:
                return [
                    types.TextContent(
                        type="text", text=f"Member is not in a voice channel"
                    )
                ]

            try:
                await member.edit(mute=mute)
            except discord.Forbidden:
                return [
                    types.TextContent(
                        type="text", text="Insufficient permissions to mute this user"
                    )
                ]
            except discord.HTTPException as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Failed to {'mute' if mute else 'unmute'} user: {str(e)}",
                    )
                ]

            return [
                types.TextContent(
                    type="text",
                    text=f"User {user_id} {'muted' if mute else 'unmuted'} successfully",
                )
            ]

        elif name == "assign_role":
            if (
                not arguments
                or "guild_id" not in arguments
                or "user_id" not in arguments
                or "role_id" not in arguments
                or "add" not in arguments
            ):
                raise ValueError(
                    "Missing required parameters: guild_id, user_id, role_id, and add"
                )

            guild_id = arguments["guild_id"]
            user_id = arguments["user_id"]
            role_id = arguments["role_id"]
            add = arguments["add"]

            guild = bot.get_guild(int(guild_id))
            if not guild:
                return [
                    types.TextContent(type="text", text=f"Server not found: {guild_id}")
                ]

            if not guild.me.guild_permissions.manage_roles:
                return [
                    types.TextContent(
                        type="text", text="Bot does not have permission to manage roles"
                    )
                ]

            member = guild.get_member(int(user_id))
            if not member:
                return [
                    types.TextContent(
                        type="text", text=f"Member not found in server: {user_id}"
                    )
                ]

            role = guild.get_role(int(role_id))
            if not role:
                return [
                    types.TextContent(type="text", text=f"Role not found: {role_id}")
                ]

            if guild.me.top_role <= role:
                return [
                    types.TextContent(
                        type="text",
                        text="Bot's highest role is not high enough to assign this role",
                    )
                ]

            try:
                if add:
                    await member.add_roles(role)
                else:
                    await member.remove_roles(role)
            except discord.Forbidden:
                return [
                    types.TextContent(
                        type="text",
                        text="Insufficient permissions to manage roles for this user",
                    )
                ]
            except discord.HTTPException as e:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Failed to {'add' if add else 'remove'} role: {str(e)}",
                    )
                ]

            return [
                types.TextContent(
                    type="text",
                    text=f"Role {role.name} {'added to' if add else 'removed from'} user {user_id} successfully",
                )
            ]

        elif name == "list_members":
            if not arguments or "guild_id" not in arguments:
                raise ValueError("Missing required parameter: guild_id")

            guild_id = arguments["guild_id"]
            limit = min(1000, max(1, int(arguments.get("limit", 50))))

            guild = bot.get_guild(int(guild_id))
            if not guild:
                return [
                    types.TextContent(type="text", text=f"Server not found: {guild_id}")
                ]

            # Fetch members if needed (for large guilds)
            if guild.large and len(guild.members) < limit:
                await guild.chunk()

            # Get members
            members = list(guild.members)[:limit]

            # Format member list
            member_info = []
            for member in members:
                member_info.append(
                    {
                        "id": str(member.id),
                        "name": member.name,
                        "display_name": member.display_name,
                        "discriminator": member.discriminator,
                        "bot": member.bot,
                        "joined_at": (
                            member.joined_at.isoformat() if member.joined_at else None
                        ),
                        "roles": [
                            str(role.id) for role in member.roles[1:]
                        ],  # Exclude @everyone role
                    }
                )

            return [
                types.TextContent(
                    type="text", text=json.dumps({"members": member_info}, indent=2)
                )
            ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="discord-server",
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
        # Run authentication flow with OAuth
        try:
            token_data = authenticate_and_save_credentials(
                user_id, SERVICE_NAME, SCOPES
            )
            print(
                f"Authentication successful! Token type: {token_data.get('token_type', 'unknown')}"
            )
            print(f"You can now run the Discord server.")
        except Exception as e:
            print(f"Authentication failed: {e}")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
