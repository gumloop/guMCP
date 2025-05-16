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
                outputSchema={
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of top stories with metadata. First item is metadata about the response, followed by individual story objects.",
                    "examples": [
                        '{"metadata": {"type": "stories", "count": 1, "endpoint": "topstories"}}',
                        '{"by": "username", "descendants": 11, "id": 12345678, "kids": [12345680, 12345681], "score": 118, "text": "Story content here...", "time": 1600000000, "title": "Show HN: Project Name", "type": "story", "url": "https://example.com/project"}',
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of latest stories with metadata. First item is metadata about the response, followed by individual story objects.",
                    "examples": [
                        '{"metadata": {"type": "stories", "count": 2, "endpoint": "newstories"}}',
                        '{"by": "username", "descendants": 0, "id": 12345678, "score": 1, "time": 1600000000, "title": "News Article Title", "type": "story", "url": "https://example.com/news"}',
                    ],
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
                outputSchema={
                    "type": "object",
                    "description": "Detailed information about a specific story including title, author, score, and content.",
                    "examples": [
                        '{"by": "username", "descendants": 11, "id": 12345678, "kids": [12345680, 12345681], "score": 118, "text": "Story content here...", "time": 1600000000, "title": "Story Title", "type": "story", "url": "https://example.com/story"}'
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of comments with metadata. First item is metadata about the response, followed by individual comment objects.",
                    "examples": [
                        '{"metadata": {"type": "comments", "count": 2, "story_id": 12345678, "story_title": "Story Title"}}',
                        '{"by": "username", "id": 12345680, "parent": 12345678, "text": "Comment text here...", "time": 1600000000, "type": "comment"}',
                    ],
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
                outputSchema={
                    "type": "object",
                    "description": "User information including creation date, karma score, and submitted items.",
                    "examples": [
                        '{"created": 1600000000, "id": "username", "karma": 48, "submitted": [12345678, 12345679, 12345680]}'
                    ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of stories of specified type with metadata. First item is metadata about the response, followed by individual story objects.",
                    "examples": [
                        '{"metadata": {"type": "stories", "count": 2, "story_type": "job", "endpoint": "jobstories"}}',
                        '{"by": "username", "id": 12345678, "score": 1, "time": 1600000000, "title": "Company is Hiring – Position", "type": "job", "url": "https://example.com/jobs"}',
                    ],
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
                            stories.append(story)

                    # Return each story as a separate TextContent with metadata first
                    result = [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "metadata": {
                                        "type": "stories",
                                        "count": len(stories),
                                        "endpoint": "topstories",
                                    }
                                },
                                indent=2,
                            ),
                        )
                    ]

                    # Add each story as a separate item
                    result.extend(
                        [
                            types.TextContent(
                                type="text", text=json.dumps(story, indent=2)
                            )
                            for story in stories
                        ]
                    )
                    return result
                else:
                    error = {
                        "error": "Failed to fetch top stories",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

            elif name == "get_latest_posts":
                limit = arguments.get("limit", 10)
                response = requests.get(f"{HN_API_BASE}/newstories.json", timeout=20)

                if response.status_code == 200:
                    story_ids = response.json()[:limit]

                    stories = []
                    for story_id in story_ids:
                        story = get_item(story_id)
                        if story:
                            stories.append(story)

                    # Return each story as a separate TextContent with metadata first
                    result = [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "metadata": {
                                        "type": "stories",
                                        "count": len(stories),
                                        "endpoint": "newstories",
                                    }
                                },
                                indent=2,
                            ),
                        )
                    ]

                    # Add each story as a separate item
                    result.extend(
                        [
                            types.TextContent(
                                type="text", text=json.dumps(story, indent=2)
                            )
                            for story in stories
                        ]
                    )
                    return result
                else:
                    error = {
                        "error": "Failed to fetch latest posts",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

            elif name == "get_story_details":
                story_id = arguments["id"]
                story = get_item(story_id)

                if story:
                    return [
                        types.TextContent(type="text", text=json.dumps(story, indent=2))
                    ]
                else:
                    error = {
                        "error": "Failed to fetch story",
                        "message": "Story not found",
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

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
                                comments.append(comment)

                        # Return each comment as a separate TextContent with metadata first
                        result = [
                            types.TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "metadata": {
                                            "type": "comments",
                                            "count": len(comments),
                                            "story_id": story_id,
                                            "story_title": story.get(
                                                "title", "Unknown"
                                            ),
                                        }
                                    },
                                    indent=2,
                                ),
                            )
                        ]

                        # Add each comment as a separate item
                        result.extend(
                            [
                                types.TextContent(
                                    type="text", text=json.dumps(comment, indent=2)
                                )
                                for comment in comments
                            ]
                        )
                        return result
                    else:
                        error = {
                            "error": "Failed to fetch comments",
                            "message": "No comments found",
                        }
                        return [
                            types.TextContent(
                                type="text", text=json.dumps(error, indent=2)
                            )
                        ]
                else:
                    error = {
                        "error": "Failed to fetch comments",
                        "message": "Story not found",
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

            elif name == "get_user":
                username = arguments["username"]
                response = requests.get(
                    f"{HN_API_BASE}/user/{username}.json", timeout=20
                )

                if response.status_code == 200:
                    user = response.json()
                    if user:
                        # Return raw user data
                        return [
                            types.TextContent(
                                type="text", text=json.dumps(user, indent=2)
                            )
                        ]
                    else:
                        error = {
                            "error": "Failed to fetch user",
                            "message": "User not found",
                        }
                        return [
                            types.TextContent(
                                type="text", text=json.dumps(error, indent=2)
                            )
                        ]
                else:
                    error = {
                        "error": "Failed to fetch user",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

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
                    error = {
                        "error": "Invalid story type",
                        "message": f"Invalid story type '{story_type}'",
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

                response = requests.get(f"{HN_API_BASE}/{endpoint}.json", timeout=20)
                if response.status_code == 200:
                    story_ids = response.json()[:limit]

                    stories = []
                    for story_id in story_ids:
                        story = get_item(story_id)
                        if story:
                            stories.append(story)

                    # Return each story as a separate TextContent with metadata first
                    result = [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "metadata": {
                                        "type": "stories",
                                        "count": len(stories),
                                        "story_type": story_type,
                                        "endpoint": endpoint,
                                    }
                                },
                                indent=2,
                            ),
                        )
                    ]

                    # Add each story as a separate item
                    result.extend(
                        [
                            types.TextContent(
                                type="text", text=json.dumps(story, indent=2)
                            )
                            for story in stories
                        ]
                    )
                    return result
                else:
                    error = {
                        "error": "Failed to fetch stories",
                        "status_code": response.status_code,
                        "message": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error, indent=2))
                    ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error calling Hacker News API: {e}")
            error = {"error": "API Error", "message": str(e)}
            return [types.TextContent(type="text", text=json.dumps(error, indent=2))]

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
