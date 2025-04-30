import asyncio
import datetime
import json
import os
import sys
from pathlib import Path
import logging
from typing import List, Optional, Iterable
from atproto import Client, AtUri, SessionEvent, Session
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    TextContent,
    AnyUrl,
    Tool,
    ImageContent,
    EmbeddedResource,
    Resource,
)

from mcp.server.lowlevel.helper_types import ReadResourceContents


from src.utils.bluesky.util import (
    get_credentials,
    authenticate_and_save_credentials,
)

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id, api_key=None):
    server = Server("bluesky-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Bluesky resources for the user"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = get_credentials(server.user_id, server.api_key, SERVICE_NAME)
        client = Client()
        client._set_session(
            SessionEvent.CREATE,
            Session(
                access_jwt=credentials["accessJwt"],
                refresh_jwt=credentials["refreshJwt"],
                handle=credentials["handle"],
                did=credentials["did"],
            ),
        )

        resources = []

        try:
            # Add user's profile as a resource
            resources.append(
                Resource(
                    uri=f"bluesky://profile/{credentials['handle']}",
                    mimeType="application/json",
                    name="My Profile",
                    description="Your Bluesky profile information",
                )
            )

            # Add user's posts as a resource
            resources.append(
                Resource(
                    uri=f"bluesky://posts/{credentials['handle']}",
                    mimeType="application/json",
                    name="My Posts",
                    description="Your recent Bluesky posts",
                )
            )

            # Add user's likes as a resource
            resources.append(
                Resource(
                    uri=f"bluesky://likes/{credentials['handle']}",
                    mimeType="application/json",
                    name="My Likes",
                    description="Posts you've liked on Bluesky",
                )
            )

            # Add user's follows as a resource
            resources.append(
                Resource(
                    uri=f"bluesky://follows/{credentials['handle']}",
                    mimeType="application/json",
                    name="My Follows",
                    description="Accounts you follow on Bluesky",
                )
            )

            # Add user's followers as a resource
            resources.append(
                Resource(
                    uri=f"bluesky://followers/{credentials['handle']}",
                    mimeType="application/json",
                    name="My Followers",
                    description="Accounts following you on Bluesky",
                )
            )

            return resources

        except Exception as e:
            logger.error(f"Error listing Bluesky resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a Bluesky resource by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = get_credentials(server.user_id, server.api_key, SERVICE_NAME)
        client = Client()
        client._set_session(
            SessionEvent.CREATE,
            Session(
                access_jwt=credentials["accessJwt"],
                refresh_jwt=credentials["refreshJwt"],
                handle=credentials["handle"],
                did=credentials["did"],
            ),
        )

        uri_str = str(uri)
        if not uri_str.startswith("bluesky://"):
            raise ValueError(f"Invalid Bluesky URI: {uri_str}")

        try:
            # Parse the URI to get resource type and handle
            parts = uri_str.replace("bluesky://", "").split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid Bluesky URI format: {uri_str}")

            resource_type, handle = parts

            if resource_type == "profile":
                # Get profile information
                response = await asyncio.to_thread(
                    client.app.bsky.actor.get_profile, {"actor": handle}
                )
                if hasattr(response, "error") and response.error:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.error}", mime_type="text/plain"
                        )
                    ]
                return [
                    ReadResourceContents(
                        content=json.dumps(response.model_dump(), indent=2),
                        mime_type="application/json",
                    )
                ]

            elif resource_type == "posts":
                # Get user's posts
                response = await asyncio.to_thread(
                    client.app.bsky.feed.get_author_feed, {"actor": handle, "limit": 20}
                )
                if hasattr(response, "error") and response.error:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.error}", mime_type="text/plain"
                        )
                    ]
                return [
                    ReadResourceContents(
                        content=json.dumps(response.model_dump(), indent=2),
                        mime_type="application/json",
                    )
                ]

            elif resource_type == "likes":
                # Get user's liked posts
                response = await asyncio.to_thread(
                    client.app.bsky.feed.get_actor_likes, {"actor": handle, "limit": 20}
                )
                if hasattr(response, "error") and response.error:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.error}", mime_type="text/plain"
                        )
                    ]
                return [
                    ReadResourceContents(
                        content=json.dumps(response.model_dump(), indent=2),
                        mime_type="application/json",
                    )
                ]

            elif resource_type == "follows":
                # Get user's follows
                response = await asyncio.to_thread(
                    client.app.bsky.graph.get_follows, {"actor": handle, "limit": 20}
                )
                if hasattr(response, "error") and response.error:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.error}", mime_type="text/plain"
                        )
                    ]
                return [
                    ReadResourceContents(
                        content=json.dumps(response.model_dump(), indent=2),
                        mime_type="application/json",
                    )
                ]

            elif resource_type == "followers":
                # Get user's followers
                response = await asyncio.to_thread(
                    client.app.bsky.graph.get_followers, {"actor": handle, "limit": 20}
                )
                if hasattr(response, "error") and response.error:
                    return [
                        ReadResourceContents(
                            content=f"Error: {response.error}", mime_type="text/plain"
                        )
                    ]
                return [
                    ReadResourceContents(
                        content=json.dumps(response.model_dump(), indent=2),
                        mime_type="application/json",
                    )
                ]

            else:
                return [
                    ReadResourceContents(
                        content=f"Unsupported resource type: {resource_type}",
                        mime_type="text/plain",
                    )
                ]

        except Exception as e:
            logger.error(f"Error reading Bluesky resource: {str(e)}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            types.Tool(
                name="get_my_profile",
                description="Get a user's profile information",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="search_posts",
                description="Search the related posts on the Bluesky",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of posts to return (default 25, max 100)",
                            "default": 25,
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="search_profiles",
                description="Search for profiles in Bluesky",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default 25, max 100)",
                            "default": 25,
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results",
                        },
                    },
                    "required": ["query"],
                },
            ),
            types.Tool(
                name="get_liked_posts",
                description="Get a list of posts liked by the user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of liked posts to return (default 50, max 100)",
                            "default": 50,
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_follows",
                description="Get a list of accounts the user follows",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of follows to return (default 50, max 100)",
                            "default": 50,
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_posts",
                description="Get recent posts from a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of posts to return (default 50, max 100)",
                            "default": 50,
                        },
                        "cursor": {
                            "type": "string",
                            "description": "Pagination cursor for next page of results",
                        },
                    },
                },
            ),
            types.Tool(
                name="create_post",
                description="Publish a new post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Post content"},
                        "facets": {
                            "type": "array",
                            "description": "Rich text facets (links, mentions)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "index": {
                                        "type": "object",
                                        "properties": {
                                            "byteStart": {"type": "number"},
                                            "byteEnd": {"type": "number"},
                                        },
                                        "required": ["byteStart", "byteEnd"],
                                    },
                                    "features": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    },
                                },
                                "required": ["index", "features"],
                            },
                        },
                    },
                    "required": ["text"],
                },
            ),
            types.Tool(
                name="delete_post",
                description="Delete an existing post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_uri": {
                            "type": "string",
                            "description": "URI of post to delete",
                        },
                    },
                    "required": ["post_uri"],
                },
            ),
            types.Tool(
                name="follow_user",
                description="Follow another user on bluesky account by passing either DID or account name ",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "did_uri": {
                            "type": "string",
                            "description": "DID of the user to follow",
                        },
                        "handle": {
                            "type": "string",
                            "description": "username of the account to follow",
                        },
                    },
                    "required": ["handle"],
                },
            ),
            types.Tool(
                name="unfollow_user",
                description="Unfollow a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "handle": {
                            "type": "string",
                            "description": "username of the account to unfollow",
                        },
                    },
                    "required": ["handle"],
                },
            ),
            types.Tool(
                name="mute_user",
                description="Mute a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "did_uri": {
                            "type": "string",
                            "description": "DID of user to mute",
                        },
                        "handle": {
                            "type": "string",
                            "description": "handle of the user to mute",
                        },
                    },
                    "required": ["handle"],
                },
            ),
            types.Tool(
                name="unmute_user",
                description="Unmute a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "did_uri": {
                            "type": "string",
                            "description": "DID of user to mute",
                        },
                        "handle": {
                            "type": "string",
                            "description": "handle of the user to unmute",
                        },
                    },
                    "required": ["handle"],
                },
            ),
            types.Tool(
                name="block_user",
                description="Block a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "did_uri": {
                            "type": "string",
                            "description": "DID of user to block",
                        },
                        "reason": {
                            "type": "string",
                            "enum": ["spam", "harassment", "other"],
                        },
                        "handle": {
                            "type": "string",
                            "description": "user handle to block",
                        },
                    },
                    "required": ["handle", "reason"],
                },
            ),
            types.Tool(
                name="unblock_user",
                description="Unblock a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        # "did_uri": {"type": "string", "description": "DID of user to unblock"},
                        "handle": {
                            "type": "string",
                            "description": "handle of the user to unblock",
                        }
                    },
                    "required": ["handle"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None = None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle the call to the specific tool."""
        logger.info(
            "User %s calling tool: %s with arguments: %s",
            server.user_id,
            name,
            arguments,
        )

        credentials = get_credentials(server.user_id, server.api_key, SERVICE_NAME)
        client = Client()
        client._set_session(
            SessionEvent.CREATE,
            Session(
                access_jwt=credentials["accessJwt"],
                refresh_jwt=credentials["refreshJwt"],
                handle=credentials["handle"],
                did=credentials["did"],
            ),
        )
        try:

            if name == "get_my_profile":
                response = await asyncio.to_thread(
                    client.app.bsky.actor.get_profile, {"actor": credentials["handle"]}
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "search_posts":
                query = arguments.get("query")
                limit = arguments.get("limit", 25)
                cursor = arguments.get("cursor")
                if not query:
                    return [
                        types.TextContent(
                            type="text", text="Missing required argument: query"
                        )
                    ]

                response = await asyncio.to_thread(
                    client.app.bsky.feed.search_posts,
                    {"q": query, "limit": limit, "cursor": cursor},
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "search_profiles":
                query = arguments.get("query")
                limit = arguments.get("limit", 25)
                cursor = arguments.get("cursor")
                handle = arguments.get("handle")

                if not query:
                    return [
                        types.TextContent(
                            type="text", text="Missing required argument: query"
                        )
                    ]

                response = await asyncio.to_thread(
                    client.app.bsky.actor.search_actors,
                    {"term": query, "limit": limit, "cursor": cursor},
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "get_liked_posts":
                limit = arguments.get("limit", 25)
                cursor = arguments.get("cursor")

                response = await asyncio.to_thread(
                    client.app.bsky.feed.get_actor_likes,
                    {"actor": credentials["handle"], "limit": limit, "cursor": cursor},
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "get_follows":
                limit = arguments.get("limit", 25)
                cursor = arguments.get("cursor")

                response = await asyncio.to_thread(
                    client.app.bsky.graph.get_follows,
                    {"actor": credentials["handle"], "limit": limit, "cursor": cursor},
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "get_posts":
                limit = arguments.get("limit", 25)
                cursor = arguments.get("cursor")

                response = await asyncio.to_thread(
                    client.app.bsky.feed.get_author_feed,
                    {"actor": credentials["handle"], "limit": limit, "cursor": cursor},
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "create_post":
                text = arguments.get("text")
                facets = arguments.get("facets", [])

                record = {
                    "text": text,
                    "createdAt": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "facets": facets,
                }

                response = await asyncio.to_thread(
                    client.com.atproto.repo.create_record,
                    {
                        "repo": credentials["handle"],
                        "collection": "app.bsky.feed.post",
                        "record": record,
                    },
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "delete_post":
                post_uri = arguments.get("post_uri")
                response = await asyncio.to_thread(
                    client.com.atproto.repo.delete_record,
                    {
                        "repo": credentials["handle"],
                        "collection": "app.bsky.feed.post",
                        "rkey": post_uri.split("/")[-1],
                    },
                )

                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "unfollow_user":
                handle = arguments.get("handle")

                if not handle:
                    return [
                        types.TextContent(text="Handle is required to unfollow a user")
                    ]

                # First get the DID of the user to unfollow
                try:
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )
                    if hasattr(profile, "error"):
                        return [
                            types.TextContent(
                                text=f"Error resolving handle: {profile.error}"
                            )
                        ]
                    target_did = profile.did

                    # Get the user's follows
                    follows_response = await asyncio.to_thread(
                        client.app.bsky.graph.get_follows,
                        {"actor": credentials["handle"], "limit": 100},
                    )

                    # Find the follow record for target DID
                    follow_record = None
                    for follow in follows_response.follows:
                        if follow.did == target_did:
                            # Get the specific follow record
                            record_response = await asyncio.to_thread(
                                client.com.atproto.repo.list_records,
                                {
                                    "repo": credentials["handle"],
                                    "collection": "app.bsky.graph.follow",
                                },
                            )

                            # Find the matching record
                            for record in record_response.records:
                                if record.value.subject == target_did:
                                    follow_record = record
                                    break
                            break

                    if not follow_record:
                        return [types.TextContent(text=f"Not following @{handle}")]

                    # Extract rkey from the record's URI
                    uri = AtUri.from_str(follow_record.uri)

                    # Delete the follow record using its rkey
                    response = await asyncio.to_thread(
                        client.com.atproto.repo.delete_record,
                        {
                            "repo": credentials["handle"],
                            "collection": "app.bsky.graph.follow",
                            "rkey": uri.rkey,
                        },
                    )

                    if hasattr(response, "error") and response.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error unfollowing user: {response.error}",
                            )
                        ]
                    else:
                        return [
                            types.TextContent(
                                type="text", text=f"Successfully unfollowed @{handle}"
                            )
                        ]

                except Exception as e:
                    logger.error(f"Error in unfollow_user: {str(e)}")
                    return [
                        types.TextContent(
                            type="text", text=f"Error unfollowing user: {str(e)}"
                        )
                    ]

            elif name == "mute_user":
                did_uri = arguments.get("did_uri")
                handle = arguments.get("handle")

                if handle and not did_uri:
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )

                    if hasattr(profile, "error") and profile.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error resolving handle: {profile.error}",
                            )
                        ]

                    did_uri = profile.model_dump().get("did")

                # did = did_uri.split(":")[-1]
                response = await asyncio.to_thread(
                    client.app.bsky.graph.mute_actor, {"actor": did_uri}
                )
                if response is True:
                    return [
                        types.TextContent(
                            type="text", text=f"User {did_uri} muted successfully."
                        )
                    ]
                else:
                    # If response is not True, show what it is
                    return [
                        types.TextContent(type="text", text=f"Response: {response}")
                    ]

            elif name == "follow_user":
                did_uri = arguments.get("did_uri")
                handle = arguments.get("handle")

                if handle and not did_uri:
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )

                    if hasattr(profile, "error") and profile.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error resolving handle: {profile.error}",
                            )
                        ]

                    did = profile.model_dump().get("did")

                else:
                    did = did_uri.split(":")[-1]

                record = {
                    "$type": "app.bsky.graph.follow",
                    "createdAt": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "subject": did,
                }

                response = await asyncio.to_thread(
                    client.com.atproto.repo.create_record,
                    {
                        "repo": credentials["handle"],
                        "collection": "app.bsky.graph.follow",
                        "record": record,
                    },
                )
                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "unmute_user":
                did_uri = arguments.get("did_uri")
                handle = arguments.get("handle")

                if handle and not did_uri:
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )

                    if hasattr(profile, "error") and profile.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error resolving handle: {profile.error}",
                            )
                        ]

                    did_uri = profile.model_dump().get("did")

                response = await asyncio.to_thread(
                    client.app.bsky.graph.unmute_actor, {"actor": did_uri}
                )

                if response is True:
                    return [
                        types.TextContent(
                            type="text", text=f"User {did_uri} unmuted successfully."
                        )
                    ]
                else:
                    # If response is not True, show what it is
                    return [
                        types.TextContent(type="text", text=f"Response: {response}")
                    ]

            elif name == "block_user":
                handle = arguments.get("handle")
                did_uri = arguments.get("did_uri")
                reason = arguments.get("reason", "other")

                if handle and not did_uri:
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )

                    if hasattr(profile, "error") and profile.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error resolving handle: {profile.error}",
                            )
                        ]

                    did = profile.model_dump().get("did")
                else:
                    did = did_uri.split(":")[-1]

                record = {
                    "$type": "app.bsky.graph.block",
                    "createdAt": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "subject": did,
                    "reason": reason,
                }

                response = await asyncio.to_thread(
                    client.com.atproto.repo.create_record,
                    {
                        "repo": credentials["handle"],
                        "collection": "app.bsky.graph.block",
                        "record": record,
                    },
                )
                if hasattr(response, "error") and response.error:
                    return [
                        types.TextContent(type="text", text=f"Error {response.error}")
                    ]
                else:
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(response.model_dump(), indent=2),
                        )
                    ]

            elif name == "unblock_user":
                handle = arguments.get("handle")

                if not handle:
                    return [
                        types.TextContent(text="Handle is required to unblock a user")
                    ]

                try:
                    # First get the DID of the user to unblock
                    profile = await asyncio.to_thread(
                        client.app.bsky.actor.get_profile, {"actor": handle}
                    )
                    if hasattr(profile, "error"):
                        return [
                            types.TextContent(
                                text=f"Error resolving handle: {profile.error}"
                            )
                        ]
                    target_did = profile.did

                    # Get the user's blocks
                    blocks_response = await asyncio.to_thread(
                        client.app.bsky.graph.get_blocks,
                        {"actor": credentials["handle"], "limit": 100},
                    )

                    # Find the block record for target DID
                    block_record = None
                    for block in blocks_response.blocks:
                        if block.did == target_did:
                            # Get the specific block record
                            record_response = await asyncio.to_thread(
                                client.com.atproto.repo.list_records,
                                {
                                    "repo": credentials["handle"],
                                    "collection": "app.bsky.graph.block",
                                },
                            )

                            # Find the matching record
                            for record in record_response.records:
                                if record.value.subject == target_did:
                                    block_record = record
                                    break
                            break

                    if not block_record:
                        return [types.TextContent(text=f"No block found for @{handle}")]

                    # Extract rkey from the record's URI
                    uri = AtUri.from_str(block_record.uri)

                    # Delete the block record using its rkey
                    response = await asyncio.to_thread(
                        client.com.atproto.repo.delete_record,
                        {
                            "repo": credentials["handle"],
                            "collection": "app.bsky.graph.block",
                            "rkey": uri.rkey,
                        },
                    )

                    if hasattr(response, "error") and response.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error unblocking user: {response.error}",
                            )
                        ]
                    else:
                        return [
                            types.TextContent(
                                type="text", text=f"Successfully unblocked @{handle}"
                            )
                        ]

                except Exception as e:
                    logger.error(f"Error in unblock_user: {str(e)}")
                    return [
                        types.TextContent(
                            type="text", text=f"Error unblocking user: {str(e)}"
                        )
                    ]

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="bluesky-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
