import os
import sys

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from pathlib import Path
import logging
import tweepy
import asyncio


from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.twitter.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_twitter_api(user_id, api_key=None, api_secret=None):
    """Create a Twitter API client for this request"""
    credentials = await get_credentials(
        user_id, SERVICE_NAME, api_key=api_key, api_secret=api_secret
    )

    # Create tweepy client using OAuth 1.0 credentials
    auth = tweepy.OAuth1UserHandler(
        consumer_key=credentials["consumer_key"],
        consumer_secret=credentials["consumer_secret"],
        access_token=credentials["access_token"],
        access_token_secret=credentials["access_token_secret"],
    )

    return tweepy.API(auth)


def create_server(user_id, api_key=None, api_secret=None):
    """Create a new server instance with optional user context"""
    server = Server("twitter-server")

    server.user_id = user_id
    server.api_key = api_key
    server.api_secret = api_secret

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="post_tweet",
                description="Post a single tweet to Twitter",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text content of the tweet (max 280 characters)",
                        }
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="post_thread",
                description="Post a Twitter thread (multiple connected tweets)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "tweets": {
                            "type": "array",
                            "description": "Array of tweet texts to post as a thread",
                            "items": {
                                "type": "string",
                                "description": "Text content of a single tweet (max 280 characters)",
                            },
                        }
                    },
                    "required": ["tweets"],
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

        twitter_api = await create_twitter_api(
            server.user_id, api_key=server.api_key, api_secret=server.api_secret
        )

        if name == "post_tweet":
            if not arguments or "text" not in arguments:
                raise ValueError("Missing text parameter")

            tweet_text = arguments["text"]

            # Check tweet length
            if len(tweet_text) > 280:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Tweet exceeds 280 character limit. Current length: {len(tweet_text)} characters.",
                    )
                ]

            try:
                # Post the tweet using Twitter API v1.1
                loop = asyncio.get_event_loop()
                status = await loop.run_in_executor(
                    None, lambda: twitter_api.update_status(status=tweet_text)
                )

                tweet_url = (
                    f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Tweet posted successfully!\nView tweet: {tweet_url}",
                    )
                ]
            except Exception as e:
                logger.error(f"Error posting tweet: {str(e)}")
                return [TextContent(type="text", text=f"Error posting tweet: {str(e)}")]

        elif name == "post_thread":
            if not arguments or "tweets" not in arguments:
                raise ValueError("Missing tweets parameter")

            tweets = arguments["tweets"]
            if not tweets or not isinstance(tweets, list) or len(tweets) == 0:
                raise ValueError("Tweets must be a non-empty array of strings")

            # Check each tweet length
            for i, tweet_text in enumerate(tweets):
                if len(tweet_text) > 280:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Tweet #{i+1} exceeds 280 character limit. Current length: {len(tweet_text)} characters.",
                        )
                    ]

            try:
                # Post the thread
                previous_status = None
                tweet_urls = []
                loop = asyncio.get_event_loop()

                for i, tweet_text in enumerate(tweets):
                    # If this is a reply to a previous tweet
                    if previous_status:
                        status = await loop.run_in_executor(
                            None,
                            lambda: twitter_api.update_status(
                                status=tweet_text,
                                in_reply_to_status_id=previous_status.id,
                                auto_populate_reply_metadata=True,
                            ),
                        )
                    else:
                        # First tweet in the thread
                        status = await loop.run_in_executor(
                            None, lambda: twitter_api.update_status(status=tweet_text)
                        )

                    previous_status = status
                    tweet_url = f"https://twitter.com/{status.user.screen_name}/status/{status.id}"
                    tweet_urls.append(tweet_url)

                # Format the success message
                thread_start_url = tweet_urls[0] if tweet_urls else "N/A"
                thread_details = "\n".join(
                    [f"Tweet #{i+1}: {url}" for i, url in enumerate(tweet_urls)]
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Thread posted successfully!\nView thread: {thread_start_url}\n\n{thread_details}",
                    )
                ]
            except Exception as e:
                logger.error(f"Error posting thread: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error posting thread: {str(e)}")
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="twitter-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the GuMCP server framework.")
