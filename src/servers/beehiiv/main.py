import os
import sys
import httpx
import logging
import json
from pathlib import Path
from typing import Optional, Iterable

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
    AnyUrl,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
BEEHIIV_API_URL = "https://api.beehiiv.com/v2"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_beehiiv_key(user_id):
    """Authenticate with BeehiiV and save API key"""
    logger = logging.getLogger("beehiiv")
    logger.info(f"Starting BeehiiV authentication for user {user_id}...")

    auth_client = create_auth_client()
    api_key = input("Please enter your BeehiiV API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    auth_client.save_user_credentials("beehiiv", user_id, {"api_key": api_key})
    logger.info(
        f"BeehiiV API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_beehiiv_credentials(user_id, api_key=None):
    """Get BeehiiV API key for the specified user"""
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("beehiiv", user_id)

    def handle_missing_credentials():
        error_str = f"BeehiiV API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


async def make_beehiiv_request(method, endpoint, data=None, api_key=None, params=None):
    """Make a request to the BeehiiV API"""
    if not api_key:
        raise ValueError("BeehiiV API key is required")

    url = f"{BEEHIIV_API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    if data:
        headers["Content-Type"] = "application/json"

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "post":
                response = await client.post(
                    url, json=data, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "put":
                response = await client.put(
                    url, json=data, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "patch":
                response = await client.patch(
                    url, json=data, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "delete":
                response = await client.delete(
                    url, headers=headers, params=params, timeout=60.0
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            try:
                response_json = response.json()
                response_json["_status_code"] = response.status_code
                return response_json
            except:
                return {"_status_code": response.status_code, "result": response.text}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        error_message = f"BeehiiV API error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            if isinstance(error_details, dict) and "error" in error_details:
                error_message = error_details["error"]
        except:
            pass
        raise ValueError(error_message)

    except Exception as e:
        logger.error(f"Error making request to BeehiiV API: {str(e)}")
        raise ValueError(f"Error communicating with BeehiiV API: {str(e)}")


def create_server(user_id, api_key=None):
    server = Server("beehiiv-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        api_key = await get_beehiiv_credentials(server.user_id, server.api_key)
        resources = []

        try:
            # Get publications
            publications_response = await make_beehiiv_request(
                "get", "publications", api_key=api_key, params={"expand": ["stats"]}
            )

            for publication in publications_response.get("data", []):
                pub_id = publication.get("id")
                if pub_id:
                    pub_name = publication.get("name", f"Publication {pub_id}")
                    resources.append(
                        Resource(
                            uri=f"beehiiv://publication/{pub_id}",
                            mimeType="application/json",
                            name=pub_name,
                            description=f"BeehiiV publication: {pub_name}",
                        )
                    )

            return resources
        except Exception as e:
            logger.error(f"Error fetching resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        api_key = await get_beehiiv_credentials(server.user_id, server.api_key)

        try:
            # Parse URI to get resource type and ID
            uri_str = str(uri)
            if not uri_str.startswith("beehiiv://"):
                raise ValueError(f"Unsupported URI format: {uri_str}")

            parts = uri_str.replace("beehiiv://", "").split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid URI format: {uri_str}")

            resource_type = parts[0]
            resource_id = parts[1]

            # Handle publication resources
            if resource_type == "publication":
                # Get publication details
                publication = await make_beehiiv_request(
                    "get",
                    f"publications/{resource_id}",
                    api_key=api_key,
                    params={"expand": ["stats"]},
                )

                return [
                    ReadResourceContents(
                        content=json.dumps(publication, indent=2),
                        mime_type="application/json",
                    )
                ]
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading resource {uri}: {str(e)}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}, indent=2),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_automations",
                description="List automations in a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_automation",
                description="Get a specific automation from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "The prefixed ID of the automation (e.g., aut_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id", "automation_id"],
                },
            ),
            Tool(
                name="list_automation_journeys",
                description="List journeys within a specific BeehiiV automation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "The prefixed ID of the automation (e.g., aut_00000000-0000-0000-0000-000000000000)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                    },
                    "required": ["publication_id", "automation_id"],
                },
            ),
            Tool(
                name="get_automation_journey",
                description="Get a specific automation journey from a BeehiiV automation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "The prefixed ID of the automation (e.g., aut_00000000-0000-0000-0000-000000000000)",
                        },
                        "automation_journey_id": {
                            "type": "string",
                            "description": "The prefixed ID of the automation journey (e.g., aj_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": [
                        "publication_id",
                        "automation_id",
                        "automation_journey_id",
                    ],
                },
            ),
            Tool(
                name="add_subscription_to_automation",
                description="Add an existing subscription to a BeehiiV automation flow",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "automation_id": {
                            "type": "string",
                            "description": "The prefixed ID of the automation (e.g., aut_00000000-0000-0000-0000-000000000000)",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address associated with the subscription (provide either email or subscription_id)",
                        },
                        "subscription_id": {
                            "type": "string",
                            "description": "The prefixed ID of the subscription (e.g., sub_00000000-0000-0000-0000-000000000000) (provide either email or subscription_id)",
                        },
                        "double_opt_override": {
                            "type": "string",
                            "description": "Override publication double-opt settings for this subscription",
                            "enum": ["on", "off"],
                        },
                    },
                    "required": ["publication_id", "automation_id"],
                },
            ),
            Tool(
                name="list_subscription_updates",
                description="List subscription updates for a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_subscription_update",
                description="Get a specific subscription update from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "update_id": {
                            "type": "string",
                            "description": "The ID of the Subscription Update object",
                        },
                    },
                    "required": ["publication_id", "update_id"],
                },
            ),
            Tool(
                name="update_subscriptions",
                description="Bulk update multiple subscriptions fields, including status, custom fields, and tiers",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscriptions": {
                            "type": "array",
                            "description": "An array of objects representing the subscriptions to be updated",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "subscription_id": {
                                        "type": "string",
                                        "description": "The prefixed ID of the subscription",
                                    },
                                    "tier": {
                                        "type": "string",
                                        "description": "The Tier of the Subscription",
                                        "enum": ["free", "premium"],
                                    },
                                    "stripe_customer_id": {
                                        "type": "string",
                                        "description": "The Stripe Customer ID of the subscription",
                                    },
                                    "unsubscribe": {
                                        "type": "boolean",
                                        "description": "A boolean value specifying whether to unsubscribe this subscription from the publication",
                                    },
                                    "custom_fields": {
                                        "type": "array",
                                        "description": "An array of custom field objects to update",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "The name of the custom field",
                                                },
                                                "value": {
                                                    "type": "string",
                                                    "description": "The value of the custom field",
                                                },
                                            },
                                            "required": ["name", "value"],
                                        },
                                    },
                                },
                                "required": ["subscription_id"],
                            },
                        },
                    },
                    "required": ["publication_id", "subscriptions"],
                },
            ),
            Tool(
                name="update_subscriptions_status",
                description="Bulk update subscriptions' status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscription_ids": {
                            "type": "array",
                            "description": "An array of subscription IDs to be updated",
                            "items": {
                                "type": "string",
                            },
                        },
                        "new_status": {
                            "type": "string",
                            "description": "The new status to set for the subscriptions",
                        },
                    },
                    "required": ["publication_id", "subscription_ids", "new_status"],
                },
            ),
            Tool(
                name="create_custom_field",
                description="Create a custom field on a BeehiiV publication, for use in subscriptions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "kind": {
                            "type": "string",
                            "description": "The type of value being stored in the custom field",
                            "enum": [
                                "string",
                                "integer",
                                "boolean",
                                "date",
                                "datetime",
                                "list",
                                "double",
                            ],
                        },
                        "display": {
                            "type": "string",
                            "description": "The display name of the custom field",
                        },
                    },
                    "required": ["publication_id", "kind", "display"],
                },
            ),
            Tool(
                name="get_custom_field",
                description="Get a specific custom field from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "custom_field_id": {
                            "type": "string",
                            "description": "The ID of the custom field",
                        },
                    },
                    "required": ["publication_id", "custom_field_id"],
                },
            ),
            Tool(
                name="list_custom_fields",
                description="List all custom fields on a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="delete_custom_field",
                description="Delete a custom field from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "custom_field_id": {
                            "type": "string",
                            "description": "The ID of the custom field",
                        },
                    },
                    "required": ["publication_id", "custom_field_id"],
                },
            ),
            Tool(
                name="get_referral_program",
                description="Retrieve details about a publication's referral program",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="list_posts",
                description="Retrieve all posts belonging to a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "stats",
                                    "free_web_content",
                                    "free_email_content",
                                    "free_rss_content",
                                    "premium_web_content",
                                    "premium_email_content",
                                ],
                            },
                        },
                        "audience": {
                            "type": "string",
                            "description": "Filter results by audience",
                            "enum": ["free", "premium", "all"],
                        },
                        "platform": {
                            "type": "string",
                            "description": "Filter results by platform",
                            "enum": ["web", "email", "both", "all"],
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter results by status",
                            "enum": ["draft", "confirmed", "archived", "all"],
                        },
                        "content_tags": {
                            "type": "array",
                            "description": "Filter posts by content tags",
                            "items": {"type": "string"},
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "The field to sort by",
                            "enum": ["created", "publish_date", "displayed_date"],
                        },
                        "direction": {
                            "type": "string",
                            "description": "The direction to sort results",
                            "enum": ["asc", "desc"],
                        },
                        "hidden_from_feed": {
                            "type": "string",
                            "description": "Filter by hidden_from_feed attribute",
                            "enum": ["all", "true", "false"],
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_post",
                description="Retrieve a single post from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "post_id": {
                            "type": "string",
                            "description": "The prefixed ID of the post (e.g., post_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "stats",
                                    "free_web_content",
                                    "free_email_content",
                                    "free_rss_content",
                                    "premium_web_content",
                                    "premium_email_content",
                                ],
                            },
                        },
                    },
                    "required": ["publication_id", "post_id"],
                },
            ),
            Tool(
                name="delete_post",
                description="Delete or archive a post from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "post_id": {
                            "type": "string",
                            "description": "The prefixed ID of the post (e.g., post_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id", "post_id"],
                },
            ),
            Tool(
                name="list_segments",
                description="List segments for a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "type": {
                            "type": "string",
                            "description": "Filter results by segment type",
                            "enum": ["dynamic", "static", "manual", "all"],
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter results by segment status",
                            "enum": [
                                "pending",
                                "processing",
                                "completed",
                                "failed",
                                "all",
                            ],
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "The field to sort by",
                            "enum": ["created", "last_calculated"],
                        },
                        "direction": {
                            "type": "string",
                            "description": "The direction to sort results",
                            "enum": ["asc", "desc"],
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {"type": "string", "enum": ["stats"]},
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_segment",
                description="Get a specific segment from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "segment_id": {
                            "type": "string",
                            "description": "The prefixed ID of the segment (e.g., seg_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {"type": "string", "enum": ["stats"]},
                        },
                    },
                    "required": ["publication_id", "segment_id"],
                },
            ),
            Tool(
                name="recalculate_segment",
                description="Recalculate a specific segment in a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "segment_id": {
                            "type": "string",
                            "description": "The prefixed ID of the segment (e.g., seg_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id", "segment_id"],
                },
            ),
            Tool(
                name="list_segment_subscribers",
                description="List subscribers in a specific segment from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "segment_id": {
                            "type": "string",
                            "description": "The prefixed ID of the segment (e.g., seg_00000000-0000-0000-0000-000000000000)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                    },
                    "required": ["publication_id", "segment_id"],
                },
            ),
            Tool(
                name="delete_segment",
                description="Delete a segment from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "segment_id": {
                            "type": "string",
                            "description": "The prefixed ID of the segment (e.g., seg_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id", "segment_id"],
                },
            ),
            Tool(
                name="create_subscription",
                description="Create a new subscription for a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the subscription",
                        },
                        "reactivate_existing": {
                            "type": "boolean",
                            "description": "Whether or not to reactivate the subscription if they have already unsubscribed",
                        },
                        "send_welcome_email": {
                            "type": "boolean",
                            "description": "Whether to send a welcome email",
                        },
                        "utm_source": {
                            "type": "string",
                            "description": "The source of the subscription",
                        },
                        "utm_medium": {
                            "type": "string",
                            "description": "The medium of the subscription",
                        },
                        "utm_campaign": {
                            "type": "string",
                            "description": "The acquisition campaign of the subscription",
                        },
                        "referring_site": {
                            "type": "string",
                            "description": "The website that the subscriber was referred from",
                        },
                        "referral_code": {
                            "type": "string",
                            "description": "A subscriber's referral code to give referral credit for the new subscription",
                        },
                        "custom_fields": {
                            "type": "array",
                            "description": "Custom fields to set for the subscription",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the custom field",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "The value of the custom field",
                                    },
                                },
                                "required": ["name", "value"],
                            },
                        },
                        "double_opt_override": {
                            "type": "string",
                            "description": "Override publication double-opt settings for this subscription",
                        },
                        "tier": {
                            "type": "string",
                            "description": "The tier for this subscription",
                            "enum": ["free", "premium"],
                        },
                        "premium_tiers": {
                            "type": "array",
                            "description": "The names of the premium tiers this subscription is associated with",
                            "items": {
                                "type": "string",
                            },
                        },
                        "premium_tier_ids": {
                            "type": "array",
                            "description": "The ids of the premium tiers this subscription is associated with",
                            "items": {
                                "type": "string",
                            },
                        },
                        "stripe_customer_id": {
                            "type": "string",
                            "description": "The Stripe customer ID for this subscription",
                        },
                        "automation_ids": {
                            "type": "array",
                            "description": "Enroll the subscriber into automations after their subscription has been created",
                            "items": {
                                "type": "string",
                            },
                        },
                    },
                    "required": ["publication_id", "email"],
                },
            ),
            Tool(
                name="list_subscriptions",
                description="List subscriptions for a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "custom_fields", "referrals"],
                            },
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter results by status",
                        },
                        "tier": {
                            "type": "string",
                            "description": "Filter results by tier",
                            "enum": ["free", "premium", "all"],
                        },
                        "premium_tiers": {
                            "type": "array",
                            "description": "Filter results by premium tiers",
                            "items": {
                                "type": "string",
                            },
                        },
                        "premium_tier_ids": {
                            "type": "array",
                            "description": "Filter results by premium tier IDs",
                            "items": {
                                "type": "string",
                            },
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                        "email": {
                            "type": "string",
                            "description": "Filter results by exact email match (case insensitive)",
                        },
                        "order_by": {
                            "type": "string",
                            "description": "The field to sort by",
                            "enum": ["created", "email"],
                        },
                        "direction": {
                            "type": "string",
                            "description": "The direction to sort results",
                            "enum": ["asc", "desc"],
                        },
                        "creation_date": {
                            "type": "string",
                            "description": "Filter results by creation date (YYYY/MM/DD format)",
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_subscription_by_email",
                description="Get a subscription by email from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the subscription to retrieve",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "custom_fields", "referrals", "tags"],
                            },
                        },
                    },
                    "required": ["publication_id", "email"],
                },
            ),
            Tool(
                name="get_subscription",
                description="Get a subscription by ID from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscription_id": {
                            "type": "string",
                            "description": "The prefixed ID of the subscription (e.g., sub_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "custom_fields", "referrals", "tags"],
                            },
                        },
                    },
                    "required": ["publication_id", "subscription_id"],
                },
            ),
            Tool(
                name="update_subscription",
                description="Update a subscription in a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscription_id": {
                            "type": "string",
                            "description": "The prefixed ID of the subscription (e.g., sub_00000000-0000-0000-0000-000000000000)",
                        },
                        "tier": {
                            "type": "string",
                            "description": "The tier for this subscription",
                            "enum": ["free", "premium"],
                        },
                        "stripe_customer_id": {
                            "type": "string",
                            "description": "The Stripe Customer ID of the subscription",
                        },
                        "unsubscribe": {
                            "type": "boolean",
                            "description": "Whether to unsubscribe this subscription from the publication",
                        },
                        "custom_fields": {
                            "type": "array",
                            "description": "Custom fields to update for the subscription",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the custom field",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "The value of the custom field",
                                    },
                                    "delete": {
                                        "type": "boolean",
                                        "description": "Whether to delete this custom field from the subscription",
                                    },
                                },
                                "required": ["name"],
                            },
                        },
                    },
                    "required": ["publication_id", "subscription_id"],
                },
            ),
            Tool(
                name="delete_subscription",
                description="Delete a subscription from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscription_id": {
                            "type": "string",
                            "description": "The prefixed ID of the subscription (e.g., sub_00000000-0000-0000-0000-000000000000)",
                        },
                    },
                    "required": ["publication_id", "subscription_id"],
                },
            ),
            Tool(
                name="add_subscription_tag",
                description="Add tags to a subscription in a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "subscription_id": {
                            "type": "string",
                            "description": "The prefixed ID of the subscription (e.g., sub_00000000-0000-0000-0000-000000000000)",
                        },
                        "tags": {
                            "type": "array",
                            "description": "Tags to add to the subscription",
                            "items": {
                                "type": "string",
                            },
                        },
                    },
                    "required": ["publication_id", "subscription_id", "tags"],
                },
            ),
            Tool(
                name="list_tiers",
                description="List tiers for a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "prices"],
                            },
                        },
                        "limit": {
                            "type": "integer",
                            "description": "A limit on the number of objects to be returned (1-100)",
                        },
                        "page": {
                            "type": "integer",
                            "description": "Page number for paginated results",
                        },
                        "direction": {
                            "type": "string",
                            "description": "The direction to sort results",
                            "enum": ["asc", "desc"],
                        },
                    },
                    "required": ["publication_id"],
                },
            ),
            Tool(
                name="get_tier",
                description="Get a specific tier from a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "tier_id": {
                            "type": "string",
                            "description": "The prefixed ID of the tier (e.g., tier_00000000-0000-0000-0000-000000000000)",
                        },
                        "expand": {
                            "type": "array",
                            "description": "Optionally expand the results with additional information",
                            "items": {
                                "type": "string",
                                "enum": ["stats", "prices"],
                            },
                        },
                    },
                    "required": ["publication_id", "tier_id"],
                },
            ),
            Tool(
                name="update_tier",
                description="Update an existing tier in a BeehiiV publication",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "publication_id": {
                            "type": "string",
                            "description": "The prefixed ID of the publication (e.g., pub_00000000-0000-0000-0000-000000000000)",
                        },
                        "tier_id": {
                            "type": "string",
                            "description": "The prefixed ID of the tier (e.g., tier_00000000-0000-0000-0000-000000000000)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the tier",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the tier",
                        },
                        "prices_attributes": {
                            "type": "array",
                            "description": "Price attributes for the tier",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "ID of the existing price",
                                    },
                                    "currency": {
                                        "type": "string",
                                        "description": "Currency for the price",
                                        "enum": [
                                            "usd",
                                            "gbp",
                                            "eur",
                                            "aud",
                                            "cad",
                                            "nzd",
                                        ],
                                    },
                                    "amount_cents": {
                                        "type": "integer",
                                        "description": "Amount in cents",
                                    },
                                    "interval": {
                                        "type": "string",
                                        "description": "Billing interval",
                                        "enum": ["month", "year"],
                                    },
                                    "interval_display": {
                                        "type": "string",
                                        "description": "Display text for the interval (e.g., 'Monthly')",
                                    },
                                    "cta": {
                                        "type": "string",
                                        "description": "Call to action text",
                                    },
                                    "features": {
                                        "type": "array",
                                        "description": "Features included with this price",
                                        "items": {
                                            "type": "string",
                                        },
                                    },
                                    "delete": {
                                        "type": "boolean",
                                        "description": "Optionally delete the price when updating the tier",
                                    },
                                },
                                "required": [],
                            },
                        },
                    },
                    "required": ["publication_id", "tier_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        api_key = await get_beehiiv_credentials(server.user_id, server.api_key)
        arguments = arguments or {}

        try:
            # Define tool endpoints
            tool_endpoints = {
                "list_automations": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/automations",
                    "params": lambda args: {
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                    },
                },
                "get_automation": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/automations/{args['automation_id']}",
                },
                "list_automation_journeys": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/automations/{args['automation_id']}/journeys",
                    "params": lambda args: {
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                    },
                },
                "get_automation_journey": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/automations/{args['automation_id']}/journeys/{args['automation_journey_id']}",
                },
                "add_subscription_to_automation": {
                    "method": "post",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/automations/{args['automation_id']}/journeys",
                    "data": lambda args: {
                        "email": args.get("email"),
                        "subscription_id": args.get("subscription_id"),
                        "double_opt_override": args.get("double_opt_override"),
                    },
                },
                "list_subscription_updates": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/bulk_subscription_updates",
                },
                "get_subscription_update": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/bulk_subscription_updates/{args['update_id']}",
                },
                "update_subscriptions": {
                    "method": "put",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/bulk_actions",
                    "data": lambda args: {
                        "subscriptions": args.get("subscriptions", []),
                    },
                },
                "update_subscriptions_status": {
                    "method": "put",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions",
                    "data": lambda args: {
                        "subscription_ids": args.get("subscription_ids", []),
                        "new_status": args.get("new_status"),
                    },
                },
                "create_custom_field": {
                    "method": "post",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/custom_fields",
                    "data": lambda args: {
                        "kind": args.get("kind"),
                        "display": args.get("display"),
                    },
                },
                "get_custom_field": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/custom_fields/{args['custom_field_id']}",
                },
                "list_custom_fields": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/custom_fields",
                    "params": lambda args: {
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                    },
                },
                "update_custom_field": {
                    "method": "patch",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/custom_fields/{args['custom_field_id']}",
                    "data": lambda args: {
                        "display": args.get("display"),
                    },
                },
                "delete_custom_field": {
                    "method": "delete",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/custom_fields/{args['custom_field_id']}",
                },
                "get_referral_program": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/referral_program",
                    "params": lambda args: {
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                    },
                },
                "list_posts": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/posts",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                        "audience": args.get("audience"),
                        "platform": args.get("platform"),
                        "status": args.get("status"),
                        "content_tags[]": args.get("content_tags"),
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                        "order_by": args.get("order_by"),
                        "direction": args.get("direction"),
                        "hidden_from_feed": args.get("hidden_from_feed"),
                    },
                },
                "get_post": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/posts/{args['post_id']}",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                    },
                },
                "delete_post": {
                    "method": "delete",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/posts/{args['post_id']}",
                },
                "list_segments": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/segments",
                    "params": lambda args: {
                        "type": args.get("type"),
                        "status": args.get("status"),
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                        "order_by": args.get("order_by"),
                        "direction": args.get("direction"),
                        "expand": args.get("expand"),
                    },
                },
                "get_segment": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/segments/{args['segment_id']}",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                    },
                },
                "recalculate_segment": {
                    "method": "put",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/segments/{args['segment_id']}/recalculate",
                },
                "list_segment_subscribers": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/segments/{args['segment_id']}/results",
                    "params": lambda args: {
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                    },
                },
                "delete_segment": {
                    "method": "delete",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/segments/{args['segment_id']}",
                },
                "create_subscription": {
                    "method": "post",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions",
                    "data": lambda args: {
                        "email": args.get("email"),
                        "reactivate_existing": args.get("reactivate_existing"),
                        "send_welcome_email": args.get("send_welcome_email"),
                        "utm_source": args.get("utm_source"),
                        "utm_medium": args.get("utm_medium"),
                        "utm_campaign": args.get("utm_campaign"),
                        "referring_site": args.get("referring_site"),
                        "referral_code": args.get("referral_code"),
                        "custom_fields": args.get("custom_fields"),
                        "double_opt_override": args.get("double_opt_override"),
                        "tier": args.get("tier"),
                        "premium_tiers": args.get("premium_tiers"),
                        "premium_tier_ids": args.get("premium_tier_ids"),
                        "stripe_customer_id": args.get("stripe_customer_id"),
                        "automation_ids": args.get("automation_ids"),
                    },
                },
                "list_subscriptions": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                        "status": args.get("status"),
                        "tier": args.get("tier"),
                        "premium_tiers[]": args.get("premium_tiers"),
                        "premium_tier_ids[]": args.get("premium_tier_ids"),
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                        "email": args.get("email"),
                        "order_by": args.get("order_by"),
                        "direction": args.get("direction"),
                        "creation_date": args.get("creation_date"),
                    },
                },
                "get_subscription_by_email": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/by_email/{args['email']}",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                    },
                },
                "get_subscription": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/{args['subscription_id']}",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                    },
                },
                "update_subscription": {
                    "method": "patch",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/{args['subscription_id']}",
                    "data": lambda args: {
                        "tier": args.get("tier"),
                        "stripe_customer_id": args.get("stripe_customer_id"),
                        "unsubscribe": args.get("unsubscribe"),
                        "custom_fields": args.get("custom_fields"),
                    },
                },
                "delete_subscription": {
                    "method": "delete",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/{args['subscription_id']}",
                },
                "add_subscription_tag": {
                    "method": "post",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/subscriptions/{args['subscription_id']}/tags",
                    "data": lambda args: {
                        "tags": args.get("tags"),
                    },
                },
                "list_tiers": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/tiers",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                        "limit": args.get("limit", 10),
                        "page": args.get("page", 1),
                        "direction": args.get("direction"),
                    },
                },
                "get_tier": {
                    "method": "get",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/tiers/{args['tier_id']}",
                    "params": lambda args: {
                        "expand": args.get("expand"),
                    },
                },
                "update_tier": {
                    "method": "put",
                    "endpoint": lambda args: f"publications/{args['publication_id']}/tiers/{args['tier_id']}",
                    "data": lambda args: {
                        "name": args.get("name"),
                        "description": args.get("description"),
                        "prices_attributes": args.get("prices_attributes"),
                    },
                },
            }

            # Check if tool exists
            if name not in tool_endpoints:
                return [
                    TextContent(
                        type="text",
                        text=f"Tool {name} not implemented yet",
                    )
                ]

            # Get tool config
            tool_config = tool_endpoints[name]
            method = tool_config["method"]
            endpoint = tool_config["endpoint"](arguments)

            # Get request params and data
            params = (
                tool_config.get("params", lambda args: None)(arguments)
                if "params" in tool_config
                else None
            )
            data = (
                tool_config.get("data", lambda args: None)(arguments)
                if "data" in tool_config
                else None
            )

            # Clean up None values from data and params
            if data:
                data = {k: v for k, v in data.items() if v is not None}
            if params:
                params = {k: v for k, v in params.items() if v is not None}

            # Make the API request
            response = await make_beehiiv_request(
                method, endpoint, data=data, api_key=api_key, params=params
            )

            # Return the response
            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error using {name} tool: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="beehiiv-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_beehiiv_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
