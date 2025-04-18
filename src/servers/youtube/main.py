import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.utils.google.util import authenticate_and_save_credentials
from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("youtube-server")


async def get_credentials(user_id, api_key=None):
    """Get stored or active credentials for YouTube API."""
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    if not credentials_data:
        raise ValueError(
            f"Credentials not found for user {user_id}. Run with 'auth' first."
        )

    token = credentials_data.get("token")
    if token:
        return Credentials.from_authorized_user_info(credentials_data)
    access_token = credentials_data.get("access_token")
    if access_token:
        return Credentials(token=access_token)

    raise ValueError(f"Valid token not found for user {user_id}")


async def create_youtube_service(user_id, api_key=None):
    """Create an authorized YouTube API service."""
    credentials = await get_credentials(user_id, api_key=api_key)
    return build("youtube", "v3", credentials=credentials)


def create_server(user_id, api_key=None):
    server = Server("youtube-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Register all supported tools for YouTube."""
        return [
            types.Tool(
                name="get_video_details",
                description="Get details of a video by ID",
                inputSchema={
                    "type": "object",
                    "properties": {"video_id": {"type": "string"}},
                    "required": ["video_id"],
                },
            ),
            types.Tool(
                name="list_channel_videos",
                description="List videos for a channel",
                inputSchema={
                    "type": "object",
                    "properties": {"channel_id": {"type": "string"}},
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="get_video_statistics",
                description="Get statistics for a video",
                inputSchema={
                    "type": "object",
                    "properties": {"video_id": {"type": "string"}},
                    "required": ["video_id"],
                },
            ),
            types.Tool(
                name="search_videos",
                description="Search videos across YouTube",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="get_channel_details",
                description="Get details for a channel",
                inputSchema={
                    "type": "object",
                    "properties": {"channel_id": {"type": "string"}},
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="list_channel_playlists",
                description="List playlists of a channel",
                inputSchema={
                    "type": "object",
                    "properties": {"channel_id": {"type": "string"}},
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="get_channel_statistics",
                description="Get statistics for a channel",
                inputSchema={
                    "type": "object",
                    "properties": {"channel_id": {"type": "string"}},
                    "required": ["channel_id"],
                },
            ),
            types.Tool(
                name="list_playlist_items",
                description="List videos in a playlist",
                inputSchema={
                    "type": "object",
                    "properties": {"playlist_id": {"type": "string"}},
                    "required": ["playlist_id"],
                },
            ),
            types.Tool(
                name="get_playlist_details",
                description="Get details of a playlist",
                inputSchema={
                    "type": "object",
                    "properties": {"playlist_id": {"type": "string"}},
                    "required": ["playlist_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        yt = await create_youtube_service(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            if name == "get_video_details":
                result = (
                    yt.videos()
                    .list(part="snippet,contentDetails", id=arguments["video_id"])
                    .execute()
                )
            elif name == "list_channel_videos":
                result = (
                    yt.search()
                    .list(
                        part="snippet",
                        channelId=arguments["channel_id"],
                        type="video",
                        maxResults=25,
                    )
                    .execute()
                )
            elif name == "get_video_statistics":
                result = (
                    yt.videos()
                    .list(part="statistics", id=arguments["video_id"])
                    .execute()
                )
            elif name == "search_videos":
                result = (
                    yt.search()
                    .list(
                        part="snippet",
                        q=arguments["query"],
                        type="video",
                        maxResults=25,
                    )
                    .execute()
                )
            elif name == "get_channel_details":
                result = (
                    yt.channels()
                    .list(part="snippet", id=arguments["channel_id"])
                    .execute()
                )
            elif name == "list_channel_playlists":
                result = (
                    yt.playlists()
                    .list(
                        part="snippet", channelId=arguments["channel_id"], maxResults=25
                    )
                    .execute()
                )
            elif name == "get_channel_statistics":
                result = (
                    yt.channels()
                    .list(part="statistics", id=arguments["channel_id"])
                    .execute()
                )
            elif name == "list_playlist_items":
                result = (
                    yt.playlistItems()
                    .list(
                        part="snippet",
                        playlistId=arguments["playlist_id"],
                        maxResults=25,
                    )
                    .execute()
                )
            elif name == "get_playlist_details":
                result = (
                    yt.playlists()
                    .list(part="snippet", id=arguments["playlist_id"])
                    .execute()
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling YouTube API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="youtube-server",
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
