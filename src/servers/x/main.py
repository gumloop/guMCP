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

from src.utils.x.util import authenticate_and_save_credentials, get_credentials

import requests


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "tweet.read",
    "tweet.write",
    "users.read",
    "offline.access",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_x_client(user_id, api_key=None):
    """Create a new X client instance for this request"""
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return XClient(token)


class XClient:
    """Simple client wrapper for X API"""

    def __init__(self, token):
        self.token = token
        self.api_base = "https://api.twitter.com/2"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    
    def get_user_me(self):
        """Get current user's info"""
        url = f"{self.api_base}/users/me"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_home_timeline(self, max_results=20):
        """Get home timeline"""
        url = f"{self.api_base}/timelines/reverse_chronological"
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,author_id,text,entities",
            "expansions": "author_id",
            "user.fields": "name,username",
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_user_tweets(self, user_id, max_results=20):
        """Get tweets for a user"""
        url = f"{self.api_base}/users/{user_id}/tweets"
        params = {
            "max_results": max_results,
            "tweet.fields": "created_at,text,entities",
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def post_tweet(self, text):
        """Post a new tweet"""
        url = f"{self.api_base}/tweets"
        data = {
            "text": text
        }
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_user_by_username(self, username):
        """Look up user by username"""
        username = username.lstrip('@')
        url = f"{self.api_base}/users/by/username/{username}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_tweet(self, tweet_id):
        """Get a specific tweet"""
        url = f"{self.api_base}/tweets/{tweet_id}"
        params = {
            "tweet.fields": "created_at,author_id,text,entities",
            "expansions": "author_id",
            "user.fields": "name,username",
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()


def format_tweet(tweet, users=None):
    """Format a tweet for display"""
    created_at = datetime.fromisoformat(tweet.get("created_at", "").replace("Z", "+00:00"))
    formatted_time = created_at.strftime("%Y-%m-%d %H:%M:%S")
    
    text = tweet.get("text", "")
    author_id = tweet.get("author_id", "Unknown")
    
    # Try to get username if users provided
    username = "Unknown"
    if users and author_id in users:
        username = f"@{users[author_id].get('username', 'Unknown')}"
    
    return f"[{formatted_time}] {username}: {text}"


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("x-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List X timelines/feeds"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        x_client = await create_x_client(server.user_id, api_key=server.api_key)

        try:
            # Get user info for the authenticated user
            user_info = x_client.get_user_me()
            user_id = user_info["data"]["id"]
            username = user_info["data"]["username"]
            
            resources = [
                Resource(
                    uri=f"x://timeline/home",
                    mimeType="text/plain",
                    name="Home Timeline",
                    description="Your X home timeline",
                ),
                Resource(
                    uri=f"x://user/{user_id}",
                    mimeType="text/plain",
                    name=f"@{username}'s Tweets",
                    description=f"Tweets from @{username}",
                ),
            ]

            return resources

        except Exception as e:
            logger.error(f"Error listing X resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read tweets from X timeline or user feed"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        x_client = await create_x_client(server.user_id, api_key=server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("x://"):
            raise ValueError(f"Invalid X URI: {uri_str}")

        # Parse the URI to get resource type and ID
        parts = uri_str.replace("x://", "").split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid X URI format: {uri_str}")

        resource_type, resource_id = parts[0], parts[1]

        try:
            if resource_type == "timeline" and resource_id == "home":
                # Get home timeline
                response = x_client.get_home_timeline(max_results=20)
                
                tweets = response.get("data", [])
                users = {}
                
                # Create a user ID to user object map for easier lookup
                if "includes" in response and "users" in response["includes"]:
                    for user in response["includes"]["users"]:
                        users[user["id"]] = user
                
                # Format tweets
                formatted_tweets = []
                for tweet in tweets:
                    formatted_tweets.append(format_tweet(tweet, users))
                
                content = "\n".join(formatted_tweets)
                
            elif resource_type == "user":
                # Get user tweets
                response = x_client.get_user_tweets(resource_id, max_results=20)
                
                tweets = response.get("data", [])
                
                # Format tweets
                formatted_tweets = []
                for tweet in tweets:
                    formatted_tweets.append(format_tweet(tweet))
                
                content = "\n".join(formatted_tweets)
                
            else:
                content = f"Unknown resource type: {resource_type}/{resource_id}"

            return [ReadResourceContents(content=content, mime_type="text/plain")]

        except Exception as e:
            logger.error(f"Error reading X resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="read_home_timeline",
                description="Read tweets from your X home timeline",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return (default: 20)",
                        },
                    },
                },
            ),
            Tool(
                name="read_user_tweets",
                description="Read tweets from a specific X user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "X username (with or without @ symbol)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return (default: 20)",
                        },
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="post_tweet",
                description="Post a new tweet to X",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Tweet text to post",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="get_tweet",
                description="Get a specific tweet by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tweet_id": {
                            "type": "string",
                            "description": "ID of the tweet to retrieve",
                        },
                    },
                    "required": ["tweet_id"],
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

        x_client = await create_x_client(server.user_id, api_key=server.api_key)

        try:
            if name == "read_home_timeline":
                limit = arguments.get("limit", 20)
                
                # Get home timeline
                response = x_client.get_home_timeline(max_results=limit)
                
                tweets = response.get("data", [])
                users = {}
                
                # Create a user ID to user object map for easier lookup
                if "includes" in response and "users" in response["includes"]:
                    for user in response["includes"]["users"]:
                        users[user["id"]] = user
                
                # Format tweets
                formatted_tweets = []
                for tweet in tweets:
                    formatted_tweets.append(format_tweet(tweet, users))
                
                result = "\n".join(formatted_tweets)
                
                return [TextContent(type="text", text=result)]
                
            elif name == "read_user_tweets":
                if "username" not in arguments:
                    raise ValueError("Missing required parameter: username")
                
                username = arguments["username"].lstrip('@')
                limit = arguments.get("limit", 20)
                
                # Get user ID from username
                user_response = x_client.get_user_by_username(username)
                user_id = user_response["data"]["id"]
                
                # Get user tweets
                tweets_response = x_client.get_user_tweets(user_id, max_results=limit)
                
                tweets = tweets_response.get("data", [])
                
                # Format tweets
                formatted_tweets = []
                for tweet in tweets:
                    formatted_tweets.append(format_tweet(tweet))
                
                result = "\n".join(formatted_tweets)
                
                return [TextContent(type="text", text=result)]
                
            elif name == "post_tweet":
                if "text" not in arguments:
                    raise ValueError("Missing required parameter: text")
                
                text = arguments["text"]
                
                # Post tweet
                response = x_client.post_tweet(text)
                tweet_id = response["data"]["id"]
                
                return [
                    TextContent(
                        type="text",
                        text=f"Tweet posted successfully\nTweet ID: {tweet_id}",
                    )
                ]
                
            elif name == "get_tweet":
                if "tweet_id" not in arguments:
                    raise ValueError("Missing required parameter: tweet_id")
                
                tweet_id = arguments["tweet_id"]
                
                # Get tweet
                response = x_client.get_tweet(tweet_id)
                
                tweet = response.get("data", {})
                users = {}
                
                # Create a user ID to user object map for easier lookup
                if "includes" in response and "users" in response["includes"]:
                    for user in response["includes"]["users"]:
                        users[user["id"]] = user
                
                # Format tweet
                formatted_tweet = format_tweet(tweet, users)
                
                return [TextContent(type="text", text=formatted_tweet)]
                
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"X API error: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="x-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
