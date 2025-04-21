import os
import sys
from pathlib import Path
import logging
import urllib.parse
import json
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

from src.utils.linkedin.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "openid",
    "profile",
    "email",
    "w_member_social",
]
API_BASE_URL = "https://api.linkedin.com/v2"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_linkedin_client(user_id, api_key=None):
    """
    Create a new LinkedIn client instance using the stored OAuth credentials.

    Args:
        user_id: ID of the user.
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A new LinkedIn client instance.
    """
    from src.utils.linkedin.util import (
        create_linkedin_client as create_linkedin_client_util,
    )

    return await create_linkedin_client_util(user_id, api_key)


def create_server(user_id, api_key=None):
    """
    Create a new LinkedIn server instance.

    Args:
        user_id: ID of the user.
        api_key: Optional API key (used by auth client abstraction).

    Returns:
        A new LinkedIn server instance.
    """
    server = Server(SERVICE_NAME)
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the LinkedIn API.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="get_user_info",
                description="Get information about the authenticated user including profile and email",
                inputSchema={"type": "object", "properties": {}},
            ),
            types.Tool(
                name="create_text_post",
                description="Create a text post on LinkedIn",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The content of the post",
                        }
                    },
                    "required": ["text"],
                },
            ),
            types.Tool(
                name="create_article_post",
                description="Create a post on LinkedIn with an article",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_content": {
                            "type": "string",
                            "description": "The content of the post",
                        },
                        "article_url": {
                            "type": "string",
                            "description": "The URL of the article to be shared",
                        },
                        "article_description": {
                            "type": "string",
                            "description": "The description of the article to be shared",
                        },
                        "article_title": {
                            "type": "string",
                            "description": "The title of the article to be shared",
                        },
                    },
                    "required": [
                        "post_content",
                        "article_url",
                        "article_title",
                        "article_description",
                    ],
                },
            ),
            types.Tool(
                name="create_image_post",
                description="Create an image post on LinkedIn",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_path": {
                            "type": "string",
                            "description": "The path to the image to be shared",
                        },
                        "caption": {
                            "type": "string",
                            "description": "The text of the post with image ",
                        },
                        "image_description": {
                            "type": "string",
                            "description": "The description of the image to be shared",
                        },
                        "image_title": {
                            "type": "string",
                            "description": "The title of the image to be shared",
                        },
                    },
                    "required": [
                        "image_path",
                        "caption",
                        "image_description",
                        "image_title",
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Calls a specific tool with the given name and arguments.
        """
        logger.info(f"Calling tool: {name} with arguments: {arguments}")

        access_token = await get_credentials(user_id, SERVICE_NAME, server.api_key)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

        try:
            if name == "get_user_info":
                # Get user profile information using direct API call
                response = requests.get(f"{API_BASE_URL}/userinfo", headers=headers)
                response.raise_for_status()
                user_info = response.json()
                formatted_info = json.dumps(user_info, indent=2)

                return [
                    types.TextContent(
                        type="text", text=f"User Information:\n{formatted_info}"
                    )
                ]
            elif name == "create_text_post":
                # Get user's URN first
                user_response = requests.get(
                    f"{API_BASE_URL}/userinfo", headers=headers
                )
                user_response.raise_for_status()
                urn = user_response.json()["sub"]
                PERSON_URN = f"urn:li:person:{urn}"

                post_data = {
                    "author": PERSON_URN,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": arguments["text"]},
                            "shareMediaCategory": "NONE",
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                }

                response = requests.post(
                    f"{API_BASE_URL}/ugcPosts", headers=headers, json=post_data
                )
                response.raise_for_status()
                return [
                    types.TextContent(
                        type="text",
                        text=f"Post created successfully! Post ID: {response.headers.get('X-RestLi-Id')}",
                    )
                ]
            elif name == "create_article_post":
                # Get user's URN first
                user_response = requests.get(
                    f"{API_BASE_URL}/userinfo", headers=headers
                )
                user_response.raise_for_status()
                urn = user_response.json()["sub"]
                PERSON_URN = f"urn:li:person:{urn}"

                post_data = {
                    "author": PERSON_URN,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": arguments["post_content"]},
                            "shareMediaCategory": "ARTICLE",
                            "media": [
                                {
                                    "status": "READY",
                                    "description": {
                                        "text": arguments["article_description"]
                                    },
                                    "originalUrl": arguments["article_url"],
                                    "title": {"text": arguments["article_title"]},
                                }
                            ],
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                }

                response = requests.post(
                    f"{API_BASE_URL}/ugcPosts", headers=headers, json=post_data
                )
                response.raise_for_status()
                return [
                    types.TextContent(
                        type="text",
                        text=f"Post created successfully! Post ID: {response.headers.get('X-RestLi-Id')}",
                    )
                ]
            elif name == "create_image_post":
                # Get user's URN first
                user_response = requests.get(
                    f"{API_BASE_URL}/userinfo", headers=headers
                )
                user_response.raise_for_status()
                urn = user_response.json()["sub"]
                PERSON_URN = f"urn:li:person:{urn}"

                # Register image upload
                register_url = f"{API_BASE_URL}/assets?action=registerUpload"
                register_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                }
                register_body = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": PERSON_URN,
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent",
                            }
                        ],
                    }
                }

                res = requests.post(
                    register_url, headers=register_headers, json=register_body
                )
                res.raise_for_status()
                upload_info = res.json()
                upload_url = upload_info["value"]["uploadMechanism"][
                    "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"
                ]["uploadUrl"]
                asset_urn = upload_info["value"]["asset"]

                # Upload image binary
                with open(arguments["image_path"], "rb") as f:
                    image_data = f.read()

                upload_headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/octet-stream",
                }
                upload_res = requests.post(
                    upload_url, headers=upload_headers, data=image_data
                )
                upload_res.raise_for_status()

                # Create post with image
                post_body = {
                    "author": PERSON_URN,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": arguments["caption"]},
                            "shareMediaCategory": "IMAGE",
                            "media": [
                                {
                                    "status": "READY",
                                    "description": {
                                        "text": arguments["image_description"]
                                    },
                                    "media": asset_urn,
                                    "title": {"text": arguments["image_title"]},
                                }
                            ],
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    },
                }

                final_res = requests.post(
                    f"{API_BASE_URL}/ugcPosts", headers=headers, json=post_body
                )
                final_res.raise_for_status()

                return [
                    types.TextContent(
                        type="text",
                        text=f"Post created successfully! Post ID: {final_res.headers.get('X-RestLi-Id')}",
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error calling tool: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Get the initialization options for the server.
    """
    return InitializationOptions(
        server_name="LinkedIn-Server",
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
        print("python -m src.servers.linkedin.main auth")
