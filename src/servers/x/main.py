import os
import sys
from typing import Optional, Iterable, Dict, Any
import logging
from pathlib import Path
import httpx
from datetime import datetime

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

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

from src.utils.x.util import (
    authenticate_and_save_credentials,
    get_credentials,
)

SERVICE_NAME = Path(__file__).parent.name
API_BASE_URL = "https://api.x.com/2"

# Define the scopes needed for X API
SCOPES = ["tweet.read", "users.read", "follows.read", "tweet.write", "offline.access"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_x_client(
    user_id: str, api_key: Optional[str] = None
) -> httpx.AsyncClient:
    """Create a configured X API client"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

    headers = {
        "Authorization": f"Bearer {credentials['access_token']}",
        "Content-Type": "application/json",
    }

    return httpx.AsyncClient(
        base_url=API_BASE_URL,
        headers=headers,
        timeout=30.0,
    )


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """Create a new server instance with optional user context"""
    server = Server("x-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List tweets from the user's timeline"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        client = await create_x_client(server.user_id, api_key=server.api_key)

        # Get the user profile first to get user ID
        response = await client.get("/users/me")

        if response.status_code != 200:
            logger.error(
                f"Could not retrieve user profile: {response.status_code} - {response.text}"
            )
            return []

        user_profile = response.json()
        if not user_profile or "data" not in user_profile:
            logger.error("Could not retrieve user profile data")
            return []

        user_id = user_profile["data"]["id"]

        # Use the cursor as the pagination token if provided
        params = {"max_results": 20, "tweet.fields": "created_at,text,author_id"}
        if cursor:
            params["pagination_token"] = cursor

        # Get user timeline
        response = await client.get(
            f"/users/{user_id}/timelines/reverse_chronological", params=params
        )

        if response.status_code != 200:
            logger.error(
                f"Error fetching timeline: {response.status_code} - {response.text}"
            )
            return []

        data = response.json()
        tweets = data.get("data", [])
        resources = []

        for tweet in tweets:
            resource = Resource(
                uri=f"x:///{tweet['id']}",
                mimeType="text/plain",
                name=f"Tweet: {tweet['text'][:30]}...",
                metadata={
                    "id": tweet["id"],
                    "created_at": tweet.get("created_at", ""),
                    "author_id": tweet.get("author_id", ""),
                },
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a tweet by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        tweet_id = str(uri).replace("x:///", "")
        client = await create_x_client(server.user_id, api_key=server.api_key)

        # Get the specific tweet with user info
        params = {
            "tweet.fields": "created_at,text,author_id",
            "expansions": "author_id",
            "user.fields": "name,username",
        }

        response = await client.get(f"/tweets/{tweet_id}", params=params)

        if response.status_code != 200:
            logger.error(
                f"Error fetching tweet: {response.status_code} - {response.text}"
            )
            return []

        data = response.json()
        tweet = data.get("data", {})
        users = {user["id"]: user for user in data.get("includes", {}).get("users", [])}

        author = users.get(tweet.get("author_id", ""), {})
        author_name = author.get("name", "Unknown")
        author_username = author.get("username", "unknown")

        content = f"""Tweet by {author_name} (@{author_username})
Date: {tweet.get('created_at', 'Unknown')}
{tweet.get('text', 'No content')}

Tweet URL: https://x.com/{author_username}/status/{tweet_id}
"""

        return [ReadResourceContents(content=content, mime_type="text/plain")]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_recent_tweet",
                description="Search for recent tweets (last 7 days) matching a query",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Required. Search query for matching tweets.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return (10-100)",
                            "default": 10,
                            "minimum": 10,
                            "maximum": 100,
                        },
                        "start_time": {
                            "type": "string",
                            "description": "The oldest UTC timestamp from which to start searching (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "The newest UTC timestamp to end search at (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "since_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID greater than (more recent than) this ID",
                        },
                        "until_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID less than (older than) this ID",
                        },
                        "next_token": {
                            "type": "string",
                            "description": "Token for pagination of results",
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Order in which to return results",
                            "enum": ["recency", "relevancy"],
                        },
                        "expansions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand in the response (e.g. author_id, referenced_tweets.id)",
                        },
                        "tweet_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tweet fields to include in response",
                        },
                        "user_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "User fields to include in response",
                        },
                        "media_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Media fields to include in response",
                        },
                        "place_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Place fields to include in response",
                        },
                        "poll_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Poll fields to include in response",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_user_profile",
                description="Get an X user's profile information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "X username (without @)",
                        }
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="get_user_posts",
                description="Get a user's posts (tweets created by the user)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "X username (without @)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return (5-100)",
                            "default": 10,
                            "minimum": 5,
                            "maximum": 100,
                        },
                        "start_time": {
                            "type": "string",
                            "description": "The oldest UTC timestamp from which to start fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "The newest UTC timestamp to end fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "since_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID greater than (more recent than) this ID",
                        },
                        "until_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID less than (older than) this ID",
                        },
                        "pagination_token": {
                            "type": "string",
                            "description": "Token for pagination of results",
                        },
                        "tweet_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tweet fields to include in response",
                        },
                        "expansions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand in the response (e.g. attachments.media_keys)",
                        },
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="get_user_home_timeline",
                description="Get a user's home timeline (tweets from users they follow)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "X username (without @)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return (5-100)",
                            "default": 10,
                            "minimum": 5,
                            "maximum": 100,
                        },
                        "start_time": {
                            "type": "string",
                            "description": "The oldest UTC timestamp from which to start fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "The newest UTC timestamp to end fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "since_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID greater than (more recent than) this ID",
                        },
                        "until_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID less than (older than) this ID",
                        },
                        "pagination_token": {
                            "type": "string",
                            "description": "Token for pagination of results",
                        },
                        "tweet_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tweet fields to include in response",
                        },
                        "expansions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand in the response (e.g. attachments.media_keys)",
                        },
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="get_user_mentions",
                description="Get tweets that mention a specific user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "X username (without @)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of tweets to return (5-100)",
                            "default": 10,
                            "minimum": 5,
                            "maximum": 100,
                        },
                        "start_time": {
                            "type": "string",
                            "description": "The oldest UTC timestamp from which to start fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "The newest UTC timestamp to end fetching tweets (format: YYYY-MM-DDTHH:mm:ssZ)",
                        },
                        "since_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID greater than (more recent than) this ID",
                        },
                        "until_id": {
                            "type": "string",
                            "description": "Returns results with tweet ID less than (older than) this ID",
                        },
                        "pagination_token": {
                            "type": "string",
                            "description": "Token for pagination of results",
                        },
                        "tweet_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tweet fields to include in response",
                        },
                        "expansions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand in the response (e.g. attachments.media_keys)",
                        },
                    },
                    "required": ["username"],
                },
            ),
            Tool(
                name="get_tweet_by_id",
                description="Look up a specific tweet by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The tweet ID to look up",
                        },
                        "tweet_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tweet fields to include in response (e.g. created_at, author_id, text)",
                        },
                        "expansions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to expand in the response (e.g. author_id, referenced_tweets.id)",
                        },
                        "user_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "User fields to include in response (e.g. name, username, verified)",
                        },
                        "media_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Media fields to include in response",
                        },
                        "poll_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Poll fields to include in response",
                        },
                        "place_fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Place fields to include in response",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="create_tweet",
                description="Create a new tweet on behalf of the authenticated user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The content of the tweet",
                        },
                        "reply_to_tweet_id": {
                            "type": "string",
                            "description": "Tweet ID to reply to",
                        },
                        "quote_tweet_id": {
                            "type": "string",
                            "description": "Tweet ID to quote",
                        },
                        "poll_options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Options for a poll (2-4 options required if included)",
                        },
                        "poll_duration_minutes": {
                            "type": "integer",
                            "description": "Duration for the poll in minutes (between 5 and 10080)",
                        },
                        "reply_settings": {
                            "type": "string",
                            "description": "Who can reply to the tweet",
                            "enum": ["following", "mentionedUsers", "subscribers"],
                        },
                        "for_super_followers_only": {
                            "type": "boolean",
                            "description": "Whether the tweet is for super followers only",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="delete_tweet",
                description="Delete a tweet by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the tweet to delete",
                        }
                    },
                    "required": ["id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if not arguments:
            arguments = {}

        client = await create_x_client(server.user_id, api_key=server.api_key)

        try:
            if name == "search_recent_tweet":
                if "query" not in arguments:
                    raise ValueError("Missing required parameter: query")

                # Build the request parameters
                params = {
                    "query": arguments["query"],
                    "max_results": min(int(arguments.get("max_results", 10)), 100),
                }

                # Add optional date/time parameters if provided
                for time_param in ["start_time", "end_time"]:
                    if time_param in arguments:
                        # Validate ISO 8601 format
                        try:
                            datetime.fromisoformat(
                                arguments[time_param].replace("Z", "+00:00")
                            )
                            params[time_param] = arguments[time_param]
                        except ValueError:
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Invalid {time_param} format. Use ISO 8601 format: YYYY-MM-DDTHH:mm:ssZ",
                                )
                            ]

                # Add ID-based parameters
                for id_param in ["since_id", "until_id", "next_token"]:
                    if id_param in arguments and arguments[id_param]:
                        params[id_param] = arguments[id_param]

                # Add sort order if provided
                if "sort_order" in arguments and arguments["sort_order"] in [
                    "recency",
                    "relevancy",
                ]:
                    params["sort_order"] = arguments["sort_order"]

                # Handle field specifications
                field_mappings = {
                    "tweet_fields": "tweet.fields",
                    "user_fields": "user.fields",
                    "media_fields": "media.fields",
                    "place_fields": "place.fields",
                    "poll_fields": "poll.fields",
                }

                # Add expansions
                if "expansions" in arguments and isinstance(
                    arguments["expansions"], list
                ):
                    params["expansions"] = ",".join(arguments["expansions"])

                # Add fields based on mappings
                for client_field, api_field in field_mappings.items():
                    if client_field in arguments and isinstance(
                        arguments[client_field], list
                    ):
                        params[api_field] = ",".join(arguments[client_field])

                # Set default fields if none provided
                if "tweet.fields" not in params:
                    params["tweet.fields"] = "created_at,text,author_id"
                if "expansions" not in params:
                    params["expansions"] = "author_id"
                if "user.fields" not in params:
                    params["user.fields"] = "name,username"

                # Execute the search request
                response = await client.get("/tweets/search/recent", params=params)

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error searching tweets: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                tweets = data.get("data", [])

                # Extract users if included in the response
                users = {}
                if "includes" in data and "users" in data["includes"]:
                    users = {user["id"]: user for user in data["includes"]["users"]}

                # Prepare pagination info
                meta = data.get("meta", {})
                pagination_info = ""
                if "next_token" in meta:
                    pagination_info = f"\n\nPagination Token: {meta['next_token']}"
                    pagination_info += (
                        f"\nResult Count: {meta.get('result_count', len(tweets))}"
                    )

                # Format tweet results
                tweets_text = "\n\n".join(
                    [
                        f"{i+1}. [@{users.get(tweet.get('author_id', ''), {}).get('username', 'unknown')}] "
                        f"{tweet.get('created_at', 'Unknown')}: {tweet.get('text', 'No content')[:150]}..."
                        f"\nTweet URL: https://x.com/i/web/status/{tweet['id']}"
                        for i, tweet in enumerate(tweets)
                    ]
                )

                if not tweets:
                    return [
                        TextContent(
                            type="text",
                            text=f"No tweets found matching '{arguments['query']}'",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(tweets)} tweets matching '{arguments['query']}':{pagination_info}\n\n{tweets_text}",
                    )
                ]

            elif name == "get_user_profile":
                if "username" not in arguments:
                    raise ValueError("Missing username parameter")

                username = arguments["username"]

                params = {
                    "user.fields": "name,username,description,created_at,public_metrics,profile_image_url,verified"
                }

                response = await client.get(
                    f"/users/by/username/{username}", params=params
                )

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error getting user profile: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                user = data.get("data", {})

                if not user:
                    return [
                        TextContent(
                            type="text", text=f"No user found with username @{username}"
                        )
                    ]

                metrics = user.get("public_metrics", {})

                profile_text = f"""User Profile: @{user.get('username')}
Name: {user.get('name')}
Bio: {user.get('description', 'No bio')}
Verified: {'Yes' if user.get('verified', False) else 'No'}
Joined: {user.get('created_at', 'Unknown')}
Following: {metrics.get('following_count', 0)}
Followers: {metrics.get('followers_count', 0)}
Tweets: {metrics.get('tweet_count', 0)}
Profile URL: https://x.com/{user.get('username')}
"""

                return [TextContent(type="text", text=profile_text)]

            elif name in [
                "get_user_posts",
                "get_user_home_timeline",
                "get_user_mentions",
            ]:
                if "username" not in arguments:
                    raise ValueError("Missing username parameter")

                username = arguments["username"]

                # First get user ID from username
                response = await client.get(f"/users/by/username/{username}")

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error getting user ID: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                user = data.get("data", {})

                if not user:
                    return [
                        TextContent(
                            type="text", text=f"No user found with username @{username}"
                        )
                    ]

                user_id = user["id"]

                # Process parameters for timeline
                # Build the basic parameters
                params = {
                    "max_results": min(int(arguments.get("max_results", 10)), 100),
                }

                # Add optional date/time parameters if provided
                for time_param in ["start_time", "end_time"]:
                    if time_param in arguments and arguments[time_param]:
                        try:
                            # Validate ISO 8601 format
                            datetime.fromisoformat(
                                arguments[time_param].replace("Z", "+00:00")
                            )
                            params[time_param] = arguments[time_param]
                        except ValueError:
                            return [
                                TextContent(
                                    type="text",
                                    text=f"Invalid {time_param} format. Use ISO 8601 format: YYYY-MM-DDTHH:mm:ssZ",
                                )
                            ]

                # Add ID-based parameters
                for id_param in ["since_id", "until_id", "pagination_token"]:
                    if id_param in arguments and arguments[id_param]:
                        params[id_param] = arguments[id_param]

                # Add expansions
                if "expansions" in arguments and isinstance(
                    arguments["expansions"], list
                ):
                    params["expansions"] = ",".join(arguments["expansions"])
                else:
                    params["expansions"] = "author_id"

                # Add tweet fields
                if "tweet_fields" in arguments and isinstance(
                    arguments["tweet_fields"], list
                ):
                    params["tweet.fields"] = ",".join(arguments["tweet_fields"])
                else:
                    params["tweet.fields"] = "created_at,text,author_id"

                # Add user fields
                params["user.fields"] = "name,username"

                # Determine which endpoint to call based on the tool name
                if name == "get_user_posts":
                    endpoint = f"/users/{user_id}/tweets"
                    timeline_type = "posts timeline"
                elif name == "get_user_home_timeline":
                    endpoint = f"/users/{user_id}/timelines/reverse_chronological"
                    timeline_type = "home timeline"
                else:  # get_user_mentions
                    endpoint = f"/users/{user_id}/mentions"
                    timeline_type = "mentions timeline"

                # Now get the timeline data
                response = await client.get(endpoint, params=params)

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error getting {timeline_type}: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                tweets = data.get("data", [])

                # Extract users if included in the response
                users = {}
                if "includes" in data and "users" in data["includes"]:
                    users = {user["id"]: user for user in data["includes"]["users"]}

                # Prepare pagination info
                meta = data.get("meta", {})
                pagination_info = ""
                if meta:
                    if "next_token" in meta:
                        pagination_info += (
                            f"\nNext Pagination Token: {meta['next_token']}"
                        )
                    if "previous_token" in meta:
                        pagination_info += (
                            f"\nPrevious Pagination Token: {meta['previous_token']}"
                        )
                    if "result_count" in meta:
                        pagination_info += (
                            f"\nResult Count: {meta.get('result_count', len(tweets))}"
                        )
                    if "newest_id" in meta:
                        pagination_info += f"\nNewest Tweet ID: {meta['newest_id']}"
                    if "oldest_id" in meta:
                        pagination_info += f"\nOldest Tweet ID: {meta['oldest_id']}"

                # Format tweet results
                tweets_text = "\n\n".join(
                    [
                        f"{i+1}. [@{users.get(tweet.get('author_id', ''), {}).get('username', 'unknown')}] "
                        f"{tweet.get('created_at', 'Unknown')}: {tweet.get('text', 'No content')[:150]}..."
                        f"\nTweet URL: https://x.com/{users.get(tweet.get('author_id', ''), {}).get('username', 'unknown')}/status/{tweet['id']}"
                        for i, tweet in enumerate(tweets)
                    ]
                )

                if not tweets:
                    return [
                        TextContent(
                            type="text",
                            text=f"No tweets found in the {timeline_type} for @{username}",
                        )
                    ]

                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(tweets)} tweets in the {timeline_type} for @{username}:{pagination_info}\n\n{tweets_text}",
                    )
                ]

            elif name == "get_tweet_by_id":
                if "id" not in arguments:
                    raise ValueError("Missing required parameter: id")

                tweet_id = arguments["id"]
                params = {}

                # Add tweet fields
                if "tweet_fields" in arguments and isinstance(
                    arguments["tweet_fields"], list
                ):
                    params["tweet.fields"] = ",".join(arguments["tweet_fields"])
                else:
                    params["tweet.fields"] = "created_at,text,author_id,public_metrics"

                # Add expansions
                if "expansions" in arguments and isinstance(
                    arguments["expansions"], list
                ):
                    params["expansions"] = ",".join(arguments["expansions"])
                else:
                    params["expansions"] = "author_id"

                # Add user fields
                if "user_fields" in arguments and isinstance(
                    arguments["user_fields"], list
                ):
                    params["user.fields"] = ",".join(arguments["user_fields"])
                else:
                    params["user.fields"] = "name,username,verified,profile_image_url"

                # Add optional fields if provided
                field_mappings = {
                    "media_fields": "media.fields",
                    "poll_fields": "poll.fields",
                    "place_fields": "place.fields",
                }

                for client_field, api_field in field_mappings.items():
                    if client_field in arguments and isinstance(
                        arguments[client_field], list
                    ):
                        params[api_field] = ",".join(arguments[client_field])

                # Execute the API request
                response = await client.get(f"/tweets/{tweet_id}", params=params)

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error getting tweet: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                tweet = data.get("data", {})

                if not tweet:
                    return [
                        TextContent(
                            type="text", text=f"No tweet found with ID {tweet_id}"
                        )
                    ]

                # Get author information if available
                author_info = ""
                if "includes" in data and "users" in data["includes"]:
                    users = {user["id"]: user for user in data["includes"]["users"]}
                    author = users.get(tweet.get("author_id", ""), {})
                    if author:
                        verified_badge = "✓" if author.get("verified", False) else ""
                        author_info = f"Author: {author.get('name', 'Unknown')} (@{author.get('username', 'unknown')}) {verified_badge}\n"

                # Get metrics if available
                metrics_info = ""
                if "public_metrics" in tweet:
                    metrics = tweet["public_metrics"]
                    metrics_info = (
                        f"Retweets: {metrics.get('retweet_count', 0)} | "
                        f"Likes: {metrics.get('like_count', 0)} | "
                        f"Replies: {metrics.get('reply_count', 0)} | "
                        f"Quote Tweets: {metrics.get('quote_count', 0)}\n"
                    )

                # Format the tweet content
                created_at = tweet.get("created_at", "Unknown time")
                text = tweet.get("text", "No content")

                tweet_content = f"""Tweet ID: {tweet_id}
{author_info}Created: {created_at}
{metrics_info}
{text}

Tweet URL: https://x.com/i/web/status/{tweet_id}
"""

                # Add referenced tweets if available
                if "referenced_tweets" in tweet:
                    ref_tweets = tweet["referenced_tweets"]
                    ref_info = "\nReferenced Tweets:\n"
                    for ref in ref_tweets:
                        ref_info += f"- Type: {ref.get('type', 'Unknown')} | ID: {ref.get('id', 'Unknown')}\n"
                    tweet_content += ref_info

                return [TextContent(type="text", text=tweet_content)]

            elif name == "create_tweet":
                if "text" not in arguments:
                    raise ValueError("Missing required parameter: text")

                # Build the request payload
                payload = {"text": arguments["text"]}

                # Add optional reply information
                if "reply_to_tweet_id" in arguments and arguments["reply_to_tweet_id"]:
                    payload["reply"] = {
                        "in_reply_to_tweet_id": arguments["reply_to_tweet_id"]
                    }

                # Add optional quote tweet information
                if "quote_tweet_id" in arguments and arguments["quote_tweet_id"]:
                    payload["quote_tweet_id"] = arguments["quote_tweet_id"]

                # Add optional poll information
                if "poll_options" in arguments and isinstance(
                    arguments["poll_options"], list
                ):
                    if (
                        len(arguments["poll_options"]) < 2
                        or len(arguments["poll_options"]) > 4
                    ):
                        return [
                            TextContent(
                                type="text",
                                text="Poll must have between 2 and 4 options",
                            )
                        ]

                    poll_data = {
                        "options": arguments["poll_options"],
                        "duration_minutes": arguments.get(
                            "poll_duration_minutes", 1440
                        ),  # Default 24 hours
                    }

                    # Validate duration is within allowed range (5 minutes to 7 days)
                    if (
                        poll_data["duration_minutes"] < 5
                        or poll_data["duration_minutes"] > 10080
                    ):
                        return [
                            TextContent(
                                type="text",
                                text="Poll duration must be between 5 minutes and 10080 minutes (7 days)",
                            )
                        ]

                    payload["poll"] = poll_data

                # Add reply settings if specified
                if "reply_settings" in arguments:
                    payload["reply_settings"] = arguments["reply_settings"]

                # Add super followers only flag if specified
                if "for_super_followers_only" in arguments:
                    payload["for_super_followers_only"] = arguments[
                        "for_super_followers_only"
                    ]

                # Execute the API request to create the tweet
                response = await client.post("/tweets", json=payload)

                if response.status_code not in (200, 201):
                    return [
                        TextContent(
                            type="text",
                            text=f"Error creating tweet: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                tweet_data = data.get("data", {})

                if not tweet_data:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error: Tweet was not created. Response: {response.text}",
                        )
                    ]

                tweet_id = tweet_data.get("id")
                tweet_text = tweet_data.get("text", "No content")

                return [
                    TextContent(
                        type="text",
                        text=f"Tweet created successfully!\n\nID: {tweet_id}\nContent: {tweet_text}\n\nURL: https://x.com/i/web/status/{tweet_id}",
                    )
                ]

            elif name == "delete_tweet":
                if "id" not in arguments:
                    raise ValueError("Missing required parameter: id")

                tweet_id = arguments["id"]

                # Execute the API request to delete the tweet
                response = await client.delete(f"/tweets/{tweet_id}")

                if response.status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error deleting tweet: {response.status_code} - {response.text}",
                        )
                    ]

                data = response.json()
                deleted = data.get("data", {}).get("deleted", False)

                if deleted:
                    return [
                        TextContent(
                            type="text",
                            text=f"Tweet with ID {tweet_id} was successfully deleted.",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Tweet with ID {tweet_id} could not be deleted. Response: {response.text}",
                        )
                    ]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return [
                TextContent(
                    type="text", text=f"Error executing tool '{name}': {str(e)}"
                )
            ]

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
        print("Note: To run the server normally, use the guMCP server framework.")
