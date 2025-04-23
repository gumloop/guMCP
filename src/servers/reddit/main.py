"""
This file is the main entry point for the Reddit MCP server.
"""

import os
import sys
from pathlib import Path
import json
import logging
import requests

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client
from src.utils.reddit.util import authenticate_and_save_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["identity", "read", "submit", "edit", "history", "flair"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_credentials(user_id, api_key=None):
    """
    Retrieves the OAuth access token for a specific Reddit user.

    Args:
        user_id (str): The identifier of the user.
        api_key (Optional[str]): Optional API key passed during server creation.

    Returns:
        str: The access token to authenticate with the Reddit API.

    Raises:
        ValueError: If credentials are missing or invalid.
    """
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    def handle_missing():
        err = f"Reddit credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            err += " Please run with 'auth' argument first."
        logger.error(err)
        raise ValueError(err)

    if not credentials_data:
        handle_missing()

    token = credentials_data.get("access_token") or credentials_data.get("api_key")
    if token:
        return token
    handle_missing()


async def get_reddit_token(user_id, api_key=None):
    """
    This function is used to get the Reddit access token for a specific user.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        str: The access token to authenticate with the Reddit API.
    """
    token = await get_credentials(user_id, api_key)
    return token


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Reddit MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Reddit tools registered.
    """
    server = Server("reddit-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Reddit API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="retrieve_reddit_post",
                description="Fetch top posts in a subreddit with optional size limit.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sort": {
                            "type": "string",
                            "enum": ["hot", "new", "top", "controversial", "rising"],
                        },
                        "subreddit": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["subreddit"],
                },
            ),
            types.Tool(
                name="get_reddit_post_details",
                description="Get detailed content about a specific Reddit post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string"},
                    },
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="create_reddit_post",
                description="Create a new Reddit post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subreddit": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["subreddit", "title", "content"],
                },
            ),
            types.Tool(
                name="fetch_post_comments",
                description="Fetch comments for a specific Reddit post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string"},
                        "limit": {"type": "integer"},
                        "sort": {"type": "string", "enum": ["new", "old", "top"]},
                    },
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="edit_reddit_post",
                description="Edit a specific Reddit post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["post_id", "content"],
                },
            ),
            types.Tool(
                name="create_reddit_comment",
                description="Create a new Reddit comment on a specific post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["parent_id", "content"],
                },
            ),
            types.Tool(
                name="edit_reddit_comment",
                description="Edit a specific Reddit comment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "comment_id": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["comment_id", "content"],
                },
            ),
            types.Tool(
                name="delete_reddit_post",
                description="Delete a specific Reddit post",
                inputSchema={
                    "type": "object",
                    "properties": {"post_id": {"type": "string"}},
                    "required": ["post_id"],
                },
            ),
            types.Tool(
                name="delete_reddit_comment",
                description="Delete a specific Reddit comment",
                inputSchema={
                    "type": "object",
                    "properties": {"comment_id": {"type": "string"}},
                    "required": ["comment_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Reddit API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        access_token = await get_reddit_token(server.user_id, server.api_key)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "PythonScript/1.0",
        }

        if arguments is None:
            arguments = {}

        try:
            if name == "retrieve_reddit_post":
                base_url = f"https://oauth.reddit.com/r/{arguments['subreddit']}/{arguments.get('sort', 'hot')}"
                params = {"limit": arguments.get("limit", 10)}
                response = requests.get(
                    base_url, headers=headers, params=params, timeout=30
                )
                result = []
                if response.status_code == 200:
                    data = response.json()

                    for post in data["data"]["children"]:
                        post_data = post["data"]

                        result.append(
                            {
                                "id": post_data["id"],
                                "title": post_data["title"],
                                "author": post_data["author"],
                                "selftext": post_data["selftext"],
                                "score": post_data["score"],
                                "url": post_data["url"],
                                "num_comments": post_data["num_comments"],
                                "created_utc": post_data["created_utc"],
                                "permalink": post_data["permalink"],
                                "is_self": post_data["is_self"],
                            }
                        )
                else:
                    result = {
                        "error": f"Failed to retrieve posts: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "get_reddit_post_details":
                post_id = arguments["post_id"]
                if post_id.startswith("t3_"):
                    post_id = post_id[3:]
                url = f"https://oauth.reddit.com/api/info?id=t3_{post_id}"

                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    if data["data"]["children"]:
                        post_data = data["data"]["children"][0]["data"]
                        result = {
                            "id": post_data["id"],
                            "title": post_data["title"],
                            "author": post_data["author"],
                            "author_fullname": post_data.get("author_fullname"),
                            "subreddit": post_data["subreddit"],
                            "subreddit_id": post_data["subreddit_id"],
                            "selftext": post_data["selftext"],
                            "selftext_html": post_data.get("selftext_html"),
                            "score": post_data["score"],
                            "upvote_ratio": post_data.get("upvote_ratio"),
                            "created_utc": post_data["created_utc"],
                            "permalink": post_data["permalink"],
                            "url": post_data["url"],
                            "domain": post_data.get("domain"),
                            "num_comments": post_data["num_comments"],
                            "is_self": post_data["is_self"],
                            "is_video": post_data.get("is_video", False),
                            "is_original_content": post_data.get(
                                "is_original_content", False
                            ),
                            "over_18": post_data.get("over_18", False),
                            "spoiler": post_data.get("spoiler", False),
                            "locked": post_data.get("locked", False),
                            "stickied": post_data.get("stickied", False),
                            "post_hint": post_data.get("post_hint"),
                        }

                        if "media" in post_data and post_data["media"]:
                            result["media"] = post_data["media"]

                        if "gallery_data" in post_data and post_data["gallery_data"]:
                            result["gallery_data"] = post_data["gallery_data"]

                else:
                    result = {
                        "error": f"Failed to retrieve post details: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "create_reddit_post":
                url = "https://oauth.reddit.com/api/submit"

                payload = {
                    "api_type": "json",
                    "sr": arguments["subreddit"],
                    "title": arguments["title"],
                    "text": arguments["content"],
                    "kind": "self",
                }

                response = requests.post(url, headers=headers, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                else:
                    result = {
                        "error": f"Failed to create post: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "create_reddit_comment":
                try:
                    url = "https://oauth.reddit.com/api/comment"

                    parent_id = arguments["parent_id"]

                    if not parent_id.startswith("t3_"):
                        parent_id = f"t3_{parent_id}"

                    payload = {
                        "thing_id": parent_id,
                        "text": arguments["content"],
                        "api_type": "json",
                    }

                    response = requests.post(
                        url, headers=headers, data=payload, timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                    else:
                        result = {
                            "error": f"Failed to create comment: {response.status_code}",
                            "details": response.text,
                        }

                except Exception as e:
                    logger.error(
                        f"Error creating Reddit comment: {e} on line {e.__traceback__.tb_lineno}"
                    )

            elif name == "fetch_post_comments":
                post_id = arguments["post_id"]
                if post_id.startswith("t3_"):
                    post_id = post_id[3:]
                params = {
                    "sort": arguments.get("sort", "new"),
                    "limit": arguments.get("limit", 10),
                }
                response = requests.get(
                    f"https://oauth.reddit.com/comments/{post_id}",
                    headers=headers,
                    params=params,
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()

                    def process_comments(comments_list):
                        return [
                            {
                                "id": c["data"]["id"],
                                "author": c["data"]["author"],
                                "body": c["data"]["body"],
                                "score": c["data"]["score"],
                                "created_utc": c["data"]["created_utc"],
                                "permalink": c["data"]["permalink"],
                                "edited": c["data"]["edited"],
                                "is_submitter": c["data"]["is_submitter"],
                                "stickied": c["data"]["stickied"],
                                "replies": (
                                    process_comments(
                                        c["data"]["replies"]["data"]["children"]
                                    )
                                    if c["data"].get("replies")
                                    and isinstance(c["data"]["replies"], dict)
                                    else []
                                ),
                            }
                            for c in comments_list
                            if c["kind"] == "t1"
                        ]

                    result = process_comments(data[1]["data"]["children"])

                else:
                    result = {
                        "error": f"Failed to retrieve comments: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "edit_reddit_post":
                post_id = arguments["post_id"]
                if post_id.startswith("t3_"):
                    post_id = post_id[3:]
                url = "https://oauth.reddit.com/api/editusertext"

                payload = {
                    "api_type": "json",
                    "thing_id": f"t3_{post_id}",
                    "text": arguments["content"],
                }

                response = requests.post(url, headers=headers, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                else:
                    result = {
                        "error": f"Failed to edit post: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "edit_reddit_comment":
                comment_id = arguments["comment_id"]
                if comment_id.startswith("t1_"):
                    comment_id = comment_id[3:]
                url = "https://oauth.reddit.com/api/editusertext"

                payload = {
                    "api_type": "json",
                    "thing_id": f"t1_{comment_id}",
                    "text": arguments["content"],
                }

                response = requests.post(url, headers=headers, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                else:
                    result = {
                        "error": f"Failed to edit comment: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "delete_reddit_post":
                post_id = arguments["post_id"]
                if post_id.startswith("t3_"):
                    post_id = post_id[3:]
                url = "https://oauth.reddit.com/api/del"

                payload = {
                    "api_type": "json",
                    "id": f"t3_{post_id}",
                }

                response = requests.post(url, headers=headers, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                else:
                    result = {
                        "error": f"Failed to delete post: {response.status_code}",
                        "details": response.text,
                    }

            elif name == "delete_reddit_comment":
                comment_id = arguments["comment_id"]
                if comment_id.startswith("t1_"):
                    comment_id = comment_id[3:]
                url = "https://oauth.reddit.com/api/del"

                payload = {
                    "api_type": "json",
                    "id": f"t1_{comment_id}",
                }

                response = requests.post(url, headers=headers, data=payload, timeout=30)

                if response.status_code == 200:
                    result = response.json()
                else:
                    result = {
                        "error": f"Failed to delete comment: {response.status_code}",
                        "details": response.text,
                    }

            else:
                raise ValueError(f"Unknown tool: {name}")
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling Reddit API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options required for registering the server.

    Args:
        server_instance (Server): The guMCP server instance.

    Returns:
        InitializationOptions: The initialization configuration block.
    """
    return InitializationOptions(
        server_name="reddit-server",
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
