"""
This file is the main entry point for the Hacker News MCP server.
"""

import os
import sys
from pathlib import Path
import json
import logging
import requests
from datetime import datetime

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

SERVICE_NAME = Path(__file__).parent.name
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def format_item(item):
    """Format a HN item for display"""
    item_type = item.get("type", "unknown")

    if item_type == "story":
        title = item.get("title", "Untitled")
        item_id = item.get("id", "")
        url = item.get("url", "")
        score = item.get("score", 0)
        by = item.get("by", "anonymous")
        time_posted = datetime.fromtimestamp(item.get("time", 0))
        formatted_time = time_posted.strftime("%Y-%m-%d %H:%M:%S")
        descendants = item.get("descendants", 0)

        result = f"ID : {item_id} | Title: {title}\n"
        result += f"By: {by} | Score: {score} | Comments: {descendants} | Posted: {formatted_time}\n"
        if url:
            result += f"URL: {url}\n"
        return result

    elif item_type == "comment":
        by = item.get("by", "anonymous")
        text = item.get("text", "")
        time_posted = datetime.fromtimestamp(item.get("time", 0))
        formatted_time = time_posted.strftime("%Y-%m-%d %H:%M:%S")

        return f"Comment by {by} at {formatted_time}:\n{text}\n"

    else:
        return f"Item type '{item_type}' with id {item.get('id', 'unknown')}"


def get_item(item_id):
    """Get a HN item by ID
    Args:
        item_id (str): id for respective item associated with the json

    Returns :
        json: response in json format
    """
    response = requests.get(f"{HN_API_BASE}/item/{item_id}.json", timeout=20)
    if response.status_code == 200:
        return response.json()
    return None


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Hacker News MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Hacker News tools registered.
    """
    server = Server("hackernews-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Hacker News API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="get_top_stories",
                description="Get the top stories from Hacker News with optional limit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of stories to return (default: 10, max: 30)",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_latest_posts",
                description="Get the latest stories from Hacker News with optional limit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of stories to return (default: 10, max: 30)",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_story_details",
                description="Get a specific story by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "Hacker News story ID",
                        },
                    },
                    "required": ["id"],
                },
            ),
            types.Tool(
                name="get_comments",
                description="Get comments for a specific story with optional limit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "story_id": {
                            "type": "integer",
                            "description": "Hacker News story ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of comments to return (default: 10)",
                        },
                    },
                    "required": ["story_id"],
                },
            ),
            types.Tool(
                name="get_user",
                description="Get information about a Hacker News user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Hacker News username",
                        },
                    },
                    "required": ["username"],
                },
            ),
            types.Tool(
                name="get_stories_by_type",
                description="Get stories by type (top, new, best, ask, show, job) with optional limit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Story type (top, new, best, ask, show, job)",
                            "enum": ["top", "new", "best", "ask", "show", "job"],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of stories to return (default: 10)",
                        },
                    },
                    "required": ["type"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Hacker News API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        if arguments is None:
            arguments = {}

        try:
            if name == "get_top_stories":
                limit = arguments.get("limit", 10)

                response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=20)

                if response.status_code == 200:
                    story_ids = response.json()[:limit]

                    stories = []
                    for story_id in story_ids:
                        story = get_item(story_id)
                        if story:
                            stories.append(format_item(story))

                    result = {"stories": stories}

                else:
                    result = {
                        "error": "Failed to fetch top stories",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
            elif name == "get_latest_posts":
                limit = arguments.get("limit", 10)
                response = requests.get(f"{HN_API_BASE}/newstories.json", timeout=20)
                if response.status_code == 200:
                    story_ids = response.json()[:limit]

                    stories = []
                    stories_details = []
                    for story_id in story_ids:
                        story = get_item(story_id)
                        if story:
                            stories.append(format_item(story))
                            # Add detailed information for each story
                            story_detail = {
                                "id": story.get("id"),
                                "title": story.get("title", "Untitled"),
                                "url": story.get("url", ""),
                                "score": story.get("score", 0),
                                "by": story.get("by", "anonymous"),
                                "time": datetime.fromtimestamp(
                                    story.get("time", 0)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "descendants": story.get("descendants", 0),
                                "type": story.get("type", "unknown"),
                                "kids": story.get("kids", []),
                                "text": story.get("text", ""),
                                "comment_count": len(story.get("kids", [])),
                            }
                            stories_details.append(story_detail)

                    result = {
                        "type": "latest",
                        "count": len(stories),
                        "formatted_stories": "Latest stories:\n\n"
                        + "\n---\n".join(stories),
                        "stories": stories_details,
                        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

                else:
                    result = {
                        "error": "Failed to fetch latest posts",
                        "status_code": response.status_code,
                        "message": response.text,
                    }

            elif name == "get_story_details":
                story_id = arguments["id"]
                story = get_item(story_id)

                if story:
                    result = format_item(story)
                else:
                    result = {
                        "error": "Failed to fetch story",
                        "message": "Story not found",
                    }

            elif name == "get_comments":
                story_id = arguments["story_id"]
                limit = arguments.get("limit", 10)

                story = get_item(story_id)

                if story:
                    comment_ids = story.get("kids", [])[:limit]

                    if comment_ids:
                        comments = []
                        for comment_id in comment_ids:
                            comment = get_item(comment_id)
                            if (
                                comment
                                and not comment.get("deleted")
                                and not comment.get("dead")
                            ):
                                comments.append(format_item(comment))

                        result = (
                            f"Comments for: {story.get('title', 'Unknown story')}\n\n"
                        )
                        result += "\n---\n".join(comments)

                    else:
                        result = {
                            "error": "Failed to fetch comments",
                            "message": "No comments found",
                        }
                else:
                    result = {
                        "error": "Failed to fetch comments",
                        "message": "Story not found",
                    }

            elif name == "get_user":
                username = arguments["username"]

                response = requests.get(
                    f"{HN_API_BASE}/user/{username}.json", timeout=20
                )
                if response.status_code == 200:

                    user = response.json()
                    if user:

                        created = datetime.fromtimestamp(user.get("created", 0))
                        formatted_created = created.strftime("%Y-%m-%d %H:%M:%S")

                        result = f"User: {user.get('id')}\n"
                        result += f"Created: {formatted_created}\n"
                        result += f"Karma: {user.get('karma', 0)}\n"
                        result += f"About: {user.get('about', 'No about section')}\n"
                        result += f"Submitted: {user.get('submitted', [])}"
                        # Add number of submissions
                        submission_count = len(user.get("submitted", []))
                        result += f"\nSubmission Count: {submission_count}"

                        # Add full name if available
                        if "fullname" in user:
                            result += f"\nFull Name: {user.get('fullname')}"

                        # Add additional user details if available
                        if "delay" in user:
                            result += f"\nDelay: {user.get('delay')}"

                        if "created" in user:
                            account_age_days = (
                                datetime.now()
                                - datetime.fromtimestamp(user.get("created", 0))
                            ).days
                            result += f"\nAccount Age: {account_age_days} days"

                        # Add average karma per day if account is older than 1 day
                        if account_age_days > 0:
                            karma_per_day = round(
                                user.get("karma", 0) / account_age_days, 2
                            )
                            result += f"\nAverage Karma Per Day: {karma_per_day}"

                        if "about" in user and user["about"]:
                            result += f"About: {user['about']}\n"

                    else:
                        result = {
                            "error": "Failed to fetch user",
                            "message": "User not found",
                        }

                else:
                    result = {
                        "error": "Failed to fetch user",
                        "status_code": response.status_code,
                        "message": response.text,
                    }

            elif name == "get_stories_by_type":

                story_type = arguments["type"]
                limit = arguments.get("limit", 10)

                if story_type == "top":
                    endpoint = "topstories"
                elif story_type == "new":
                    endpoint = "newstories"
                elif story_type == "best":
                    endpoint = "beststories"
                elif story_type == "ask":
                    endpoint = "askstories"
                elif story_type == "show":
                    endpoint = "showstories"
                elif story_type == "job":
                    endpoint = "jobstories"
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "Invalid story type",
                                    "message": f"Invalid story type '{story_type}'",
                                },
                                indent=2,
                            ),
                        )
                    ]

                response = requests.get(f"{HN_API_BASE}/{endpoint}.json", timeout=20)
                if response.status_code == 200:
                    story_ids = response.json()[:limit]

                    stories = []
                    stories_details = []
                    for story_id in story_ids:
                        story = get_item(story_id)
                        if story:
                            stories.append(format_item(story))
                            # Add detailed information for each story
                            story_detail = {
                                "id": story.get("id"),
                                "title": story.get("title", "Untitled"),
                                "url": story.get("url", ""),
                                "score": story.get("score", 0),
                                "by": story.get("by", "anonymous"),
                                "time": datetime.fromtimestamp(
                                    story.get("time", 0)
                                ).strftime("%Y-%m-%d %H:%M:%S"),
                                "descendants": story.get("descendants", 0),
                                "type": story.get("type", "unknown"),
                                "kids": story.get("kids", []),
                                "text": story.get("text", ""),
                                "comment_count": len(story.get("kids", [])),
                            }
                            stories_details.append(story_detail)

                    result = {
                        "type": story_type,
                        "count": len(stories),
                        "formatted_stories": f"{story_type.capitalize()} stories:\n\n"
                        + "\n---\n".join(stories),
                        "stories": stories_details,
                        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }

                else:
                    result = {
                        "error": "Failed to fetch stories",
                        "status_code": response.status_code,
                        "message": response.text,
                    }

            else:
                raise ValueError(f"Unknown tool: {name}")
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling Hacker News API: {e}")
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
        server_name="hackernews-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    print("Usage:")
    print("  python main.py auth - Run authentication flow for a user")
