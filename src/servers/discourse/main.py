import os
import sys
import json
import logging
from pathlib import Path
import httpx
from typing import Optional, Iterable, Dict, Any, List

# Add both project root and src directory to Python path
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

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_discourse_credentials(user_id, base_url=None):
    """Authenticate with Discourse and save API key"""
    logger.info(f"Starting Discourse authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    if not base_url:
        base_url = input(
            "Please enter your Discourse instance URL (e.g., https://forum.example.com): "
        ).strip()
        if not base_url:
            raise ValueError("Discourse instance URL cannot be empty")

        # Ensure the URL doesn't have a trailing slash
        if base_url.endswith("/"):
            base_url = base_url[:-1]

    # Prompt user for API key
    api_key = input("Please enter your Discourse API key: ").strip()
    if not api_key:
        raise ValueError("API key cannot be empty")

    # Prompt for username associated with the API key
    username = input("Please enter the username associated with this API key: ").strip()
    if not username:
        raise ValueError("Username cannot be empty")

    # Save credentials in the new metadata format
    auth_client.save_user_credentials(
        SERVICE_NAME,
        user_id,
        {
            "metadata": [
                {
                    "name": "Username",
                    "placeholder": "Your Discourse username",
                    "value": username,
                },
                {
                    "name": "Discourse URL",
                    "placeholder": "https://example.discourse.com",
                    "value": base_url,
                },
            ],
            "value": api_key,
        },
    )

    logger.info(
        f"Discourse credentials saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_discourse_credentials(user_id, api_key=None):
    """Get Discourse credentials for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    def handle_missing_credentials():
        error_str = f"Discourse credentials not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    if isinstance(credentials_data, str):
        # If the credentials data are a string, assume it's a JSON string with the correct keys (value, Discourse URL, username)
        credentials_data = json.loads(credentials_data)

    # Handle the new metadata format for remote usage
    if (
        isinstance(credentials_data, dict)
        and "metadata" in credentials_data
        and "value" in credentials_data
    ):
        metadata = {
            item["name"]: item["value"] for item in credentials_data.get("metadata", [])
        }
        return {
            "api_key": credentials_data.get("value"),
            "base_url": metadata.get("Discourse URL"),
            "username": metadata.get("Username"),
        }

    # Handle original format (dictionary with direct fields)
    # Validate credentials
    if not credentials_data.get("api_key") or not credentials_data.get("base_url"):
        handle_missing_credentials()

    return credentials_data


async def make_discourse_request(
    method, endpoint, credentials, params=None, data=None, files=None
):
    """Make a request to the Discourse API"""
    base_url = credentials["base_url"]
    api_key = credentials["api_key"]
    username = credentials["username"]

    # Construct full URL
    url = f"{base_url}/{endpoint.lstrip('/')}"

    headers = {
        "Api-Key": api_key,
        "Api-Username": username,
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(
                    url, headers=headers, params=params, timeout=30.0
                )
            elif method.upper() == "POST":
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    json=data,
                    files=files,
                    timeout=30.0,
                )
            elif method.upper() == "PUT":
                response = await client.put(
                    url, headers=headers, params=params, json=data, timeout=30.0
                )
            elif method.upper() == "DELETE":
                response = await client.delete(
                    url, headers=headers, params=params, timeout=30.0
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json() if response.content else {}

    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        )
        raise ValueError(
            f"Discourse API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error making request to Discourse API: {str(e)}")
        raise ValueError(f"Error communicating with Discourse API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("discourse-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List categories and topics from Discourse"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = await get_discourse_credentials(server.user_id, server.api_key)

        resources = []

        try:
            # Get categories
            categories_result = await make_discourse_request(
                "GET", "categories.json", credentials
            )

            category_list = categories_result.get("category_list", {}).get(
                "categories", []
            )

            # Add categories as resources
            for category in category_list:
                resources.append(
                    Resource(
                        uri=f"discourse://category/{category['id']}",
                        mimeType="application/json",
                        name=f"Category: {category['name']}",
                    )
                )

            # Get latest topics
            topics_result = await make_discourse_request(
                "GET", "latest.json", credentials
            )

            topic_list = topics_result.get("topic_list", {}).get("topics", [])

            # Add topics as resources
            for topic in topic_list:
                resources.append(
                    Resource(
                        uri=f"discourse://topic/{topic['id']}",
                        mimeType="application/json",
                        name=f"Topic: {topic['title']}",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error fetching Discourse resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a category or topic from Discourse by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = await get_discourse_credentials(server.user_id, server.api_key)

        uri_str = str(uri)

        if uri_str.startswith("discourse://category/"):
            # Handle category resource
            category_id = uri_str.replace("discourse://category/", "")

            category_result = await make_discourse_request(
                "GET", f"c/{category_id}/show.json", credentials
            )

            if not category_result:
                raise ValueError(f"Category not found: {category_id}")

            formatted_content = json.dumps(category_result, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        elif uri_str.startswith("discourse://topic/"):
            # Handle topic resource
            topic_id = uri_str.replace("discourse://topic/", "")

            topic_result = await make_discourse_request(
                "GET", f"t/{topic_id}.json", credentials
            )

            if not topic_result:
                raise ValueError(f"Topic not found: {topic_id}")

            formatted_content = json.dumps(topic_result, indent=2)
            return [
                ReadResourceContents(
                    content=formatted_content, mime_type="application/json"
                )
            ]

        raise ValueError(f"Unsupported resource URI: {uri_str}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Discourse"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="list_categories",
                description="List all categories in the Discourse forum",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="search_topics",
                description="Search for topics in Discourse",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for topics",
                        },
                        "category_id": {
                            "type": "integer",
                            "description": "Optional category ID to filter results",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="create_topic",
                description="Create a new topic in Discourse",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the topic",
                        },
                        "raw": {
                            "type": "string",
                            "description": "Raw content of the topic",
                        },
                        "category_id": {
                            "type": "integer",
                            "description": "Category ID for the topic",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags for the topic",
                        },
                    },
                    "required": ["title", "raw", "category_id"],
                },
            ),
            Tool(
                name="create_post",
                description="Create a new post in a topic",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic_id": {
                            "type": "integer",
                            "description": "ID of the topic to post in",
                        },
                        "raw": {
                            "type": "string",
                            "description": "Raw content of the post",
                        },
                        "reply_to_post_number": {
                            "type": "integer",
                            "description": "Optional post number to reply to",
                        },
                    },
                    "required": ["topic_id", "raw"],
                },
            ),
            Tool(
                name="get_user_info",
                description="Get information about a Discourse user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "Username of the user",
                        }
                    },
                    "required": ["username"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Discourse"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        credentials = await get_discourse_credentials(server.user_id, server.api_key)

        if name == "list_categories":
            try:
                # Get categories
                categories_result = await make_discourse_request(
                    "GET", "categories.json", credentials
                )

                return [
                    TextContent(
                        type="text", text=json.dumps(categories_result, indent=2)
                    )
                ]

            except Exception as e:
                logger.error(f"Error listing categories: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error listing categories: {str(e)}")
                ]

        elif name == "search_topics":
            if not arguments or "query" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Missing required parameter: query",
                    )
                ]

            try:
                # Prepare query parameters
                params = {"q": arguments["query"]}

                # Add category filter if provided
                if "category_id" in arguments and arguments["category_id"]:
                    params["category_id"] = arguments["category_id"]

                # Make search request
                search_result = await make_discourse_request(
                    "GET", "search.json", credentials, params=params
                )

                return [
                    TextContent(type="text", text=json.dumps(search_result, indent=2))
                ]

            except Exception as e:
                logger.error(f"Error searching topics: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error searching topics: {str(e)}")
                ]

        elif name == "create_topic":
            required_fields = ["title", "raw", "category_id"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Missing required parameter: {field}",
                        )
                    ]

            try:
                # Prepare request data
                request_data = {
                    "title": arguments["title"],
                    "raw": arguments["raw"],
                    "category": arguments["category_id"],
                }

                # Add tags if provided
                if "tags" in arguments and arguments["tags"]:
                    request_data["tags"] = arguments["tags"]

                # Make create topic request
                create_result = await make_discourse_request(
                    "POST", "posts.json", credentials, data=request_data
                )

                # Check for successful creation
                return [
                    TextContent(type="text", text=json.dumps(create_result, indent=2))
                ]

            except Exception as e:
                logger.error(f"Error creating topic: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error creating topic: {str(e)}")
                ]

        elif name == "create_post":
            required_fields = ["topic_id", "raw"]
            for field in required_fields:
                if not arguments or field not in arguments:
                    return [
                        TextContent(
                            type="text",
                            text=f"Missing required parameter: {field}",
                        )
                    ]

            try:
                # Prepare request data
                request_data = {
                    "topic_id": arguments["topic_id"],
                    "raw": arguments["raw"],
                }

                # Add reply_to_post_number if provided
                if (
                    "reply_to_post_number" in arguments
                    and arguments["reply_to_post_number"]
                ):
                    request_data["reply_to_post_number"] = arguments[
                        "reply_to_post_number"
                    ]

                # Make create post request
                create_result = await make_discourse_request(
                    "POST", "posts.json", credentials, data=request_data
                )

                # Check for successful creation
                return [
                    TextContent(type="text", text=json.dumps(create_result, indent=2))
                ]

            except Exception as e:
                logger.error(f"Error creating post: {str(e)}")
                return [TextContent(type="text", text=f"Error creating post: {str(e)}")]

        elif name == "get_user_info":
            if not arguments or "username" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Missing required parameter: username",
                    )
                ]

            try:
                # Make user info request
                username = arguments["username"]
                user_result = await make_discourse_request(
                    "GET", f"users/{username}.json", credentials
                )

                return [
                    TextContent(type="text", text=json.dumps(user_result, indent=2))
                ]

            except Exception as e:
                logger.error(f"Error getting user info: {str(e)}")
                return [
                    TextContent(type="text", text=f"Error getting user info: {str(e)}")
                ]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="discourse-server",
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
        authenticate_and_save_discourse_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
