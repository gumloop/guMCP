import sys
import logging
import json
import os
import requests
from pathlib import Path
from typing import Optional, Any, Iterable

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from src.utils.klaviyo.util import (
    get_credentials,
    authenticate_and_save_credentials,
)
from mcp.types import (
    Tool,
    Resource,
    AnyUrl,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "lists:read",
    "lists:write",
    "profiles:write",
    "profiles:read",
    "campaigns:write",
    "campaigns:read",
    "metrics:read",
]

KLAVIYO_API_BASE_URL = "https://a.klaviyo.com/api/"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_klaviyo_client(access_token: str) -> Any:
    """
    Create a Klaviyo client instance using the provided credentials.

    Args:
        access_token: The OAuth access token.

    Returns:
        dict: A dictionary containing:
            - token: The access token
            - headers: Standard HTTP headers for Klaviyo API requests
            - base_url: The base URL for Klaviyo API endpoints
    """
    # Get the access token and token type
    token_type = "Bearer"

    logger.info(f"Using token type: {token_type}")

    # Standard headers for API requests
    standard_headers = {
        "Authorization": f"{token_type} {access_token}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/json",
        "revision": "2025-04-15",
    }

    return {
        "token": access_token,
        "headers": standard_headers,
        "base_url": KLAVIYO_API_BASE_URL,
    }


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Create a new Klaviyo MCP server instance.

    Args:
        user_id: The user ID to create the server for
        api_key: Optional API key for authentication

    Returns:
        An MCP Server instance configured for Klaviyo operations
    """
    server = Server("klaviyo-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Klaviyo resources (campaigns)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        klaviyo_client = await create_klaviyo_client(credentials)
        headers = klaviyo_client["headers"].copy()

        if server.api_key:
            headers["Klaviyo-API-Key"] = server.api_key

        try:
            resources = []

            # List all campaigns with filtering
            campaigns_url = klaviyo_client["base_url"] + "campaigns"
            email_campaigns_params = {
                "filter": "equals(messages.channel,'email')",  # Default to email campaigns
                "fields[campaign]": "name,status,created_at,updated_at",
            }
            sms_campaigns_params = {
                "filter": "equals(messages.channel,'sms')",  # Default to email campaigns
                "fields[campaign]": "name,status,created_at,updated_at",
            }
            email_campaigns_response = requests.get(
                campaigns_url,
                headers=headers,
                params=email_campaigns_params,
                timeout=30,
            )
            sms_campaigns_response = requests.get(
                campaigns_url,
                headers=headers,
                params=sms_campaigns_params,
                timeout=30,
            )

            campaign_responses = email_campaigns_response.json().get(
                "data", []
            ) + sms_campaigns_response.json().get("data", [])

            for campaign_response in campaign_responses:
                campaign_id = campaign_response.get("id")
                campaign_name = campaign_response.get("attributes", {}).get(
                    "name", "Unknown Campaign"
                )
                status = campaign_response.get("attributes", {}).get(
                    "status", "unknown"
                )
                created_at = campaign_response.get("attributes", {}).get(
                    "created_at", "Unknown date"
                )
                resources.append(
                    Resource(
                        uri=f"klaviyo://campaign/{campaign_id}",
                        mimeType="application/json",
                        name=f"Campaign: {campaign_name}",
                        description=f"Klaviyo campaign (Status: {status}, Created: {created_at})",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error listing Klaviyo resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from Klaviyo by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        klaviyo_client = await create_klaviyo_client(credentials)
        headers = klaviyo_client["headers"].copy()

        if server.api_key:
            headers["Klaviyo-API-Key"] = server.api_key

        uri_str = str(uri)
        if not uri_str.startswith("klaviyo://"):
            raise ValueError(f"Invalid Klaviyo URI: {uri_str}")

        try:
            if uri_str.startswith("klaviyo://campaign/"):
                # Handle campaign resource
                campaign_id = uri_str.replace("klaviyo://campaign/", "")
                campaign_url = klaviyo_client["base_url"] + f"campaigns/{campaign_id}"
                campaign_response = requests.get(
                    campaign_url, headers=headers, timeout=30
                )

                if campaign_response.status_code == 200:
                    campaign_data = campaign_response.json()
                    return [
                        ReadResourceContents(
                            content=json.dumps(campaign_data, indent=2),
                            mime_type="application/json",
                        )
                    ]
                else:
                    error_message = f"Error reading campaign: {campaign_response.text}"
                    logger.error(error_message)
                    return [
                        ReadResourceContents(
                            content=error_message, mime_type="text/plain"
                        )
                    ]
            else:
                raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading Klaviyo resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return the list of available Klaviyo tools."""
        return [
            types.Tool(
                name="create_profile",
                description="Creates a new profile with the specified attributes in Klaviyo.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Individual's email address",
                        },
                        "phone_number": {
                            "type": "string",
                            "description": "Individual's phone number in E.164 format",
                        },
                        "external_id": {
                            "type": "string",
                            "description": "A unique identifier used to associate Klaviyo profiles with profiles in an external system",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Individual's first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Individual's last name",
                        },
                        "organization": {
                            "type": "string",
                            "description": "Name of the company or organization within the company for whom the individual works",
                        },
                        "locale": {
                            "type": "string",
                            "description": "The locale of the profile, in the IETF BCP 47 language tag format",
                        },
                        "title": {
                            "type": "string",
                            "description": "Individual's job title",
                        },
                        "image": {
                            "type": "string",
                            "description": "URL pointing to the location of a profile image",
                        },
                        "address1": {
                            "type": "string",
                            "description": "First line of street address",
                        },
                        "address2": {
                            "type": "string",
                            "description": "Second line of street address",
                        },
                        "city": {"type": "string", "description": "City name"},
                        "country": {"type": "string", "description": "Country name"},
                        "latitude": {
                            "type": ["string", "number"],
                            "description": "Latitude coordinate (recommended precision of four decimal places)",
                        },
                        "longitude": {
                            "type": ["string", "number"],
                            "description": "Longitude coordinate (recommended precision of four decimal places)",
                        },
                        "region": {
                            "type": "string",
                            "description": "Region within a country, such as state or province",
                        },
                        "zip": {"type": "string", "description": "Zip code"},
                        "timezone": {
                            "type": "string",
                            "description": "Time zone name (recommend using from IANA Time Zone Database)",
                        },
                        "ip": {"type": "string", "description": "IP Address"},
                        "properties": {
                            "type": "object",
                            "description": "An object containing key/value pairs for any custom properties assigned to this profile",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the created profile data with ID and attributes",
                    "examples": [
                        '{"data":{"type":"profile","id":"01ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"example@example.com","first_name":"John","last_name":"Doe","phone_number":"+11234567890"},"links":{"self":"https://a.klaviyo.com/api/profiles/01ABCDEF-0123-4567-89AB-CDEF01234567"}}}'
                    ],
                },
                requiredScopes=["profiles:write"],
            ),
            Tool(
                name="get_profiles",
                description="Retrieves all profiles from the Klaviyo account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional filter expression to filter profiles (e.g., 'equals(email,test@example.com)')",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of profile objects with each item representing a single profile",
                    "examples": [
                        '{"type":"profile","id":"01ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"customer@example.com","first_name":"Jane","last_name":"Smith","phone_number":"+11234567890","created":"2022-01-01T12:00:00+00:00"}}',
                        '{"type":"profile","id":"02ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"another@example.com","first_name":"John","last_name":"Doe","created":"2022-02-15T14:30:00+00:00"}}',
                    ],
                },
                requiredScopes=["profiles:read"],
            ),
            Tool(
                name="get_profile",
                description="Retrieves a specific profile by its ID from the Klaviyo account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile_id": {
                            "type": "string",
                            "description": "The ID of the profile to retrieve (required)",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["profile_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the requested profile data including ID and attributes",
                    "examples": [
                        '{"data":{"type":"profile","id":"01ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"customer@example.com","phone_number":"+11234567890","first_name":"Jane","last_name":"Smith","organization":"Acme Inc","properties":{"loyalty_points":120}},"links":{"self":"https://a.klaviyo.com/api/profiles/01ABCDEF-0123-4567-89AB-CDEF01234567"}}}'
                    ],
                },
                requiredScopes=["profiles:read"],
            ),
            Tool(
                name="update_profile",
                description="Updates an existing profile with the given profile ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "profile_id": {
                            "type": "string",
                            "description": "The ID of the profile to update (required)",
                        },
                        "email": {
                            "type": "string",
                            "description": "Individual's email address",
                        },
                        "phone_number": {
                            "type": "string",
                            "description": "Individual's phone number in E.164 format",
                        },
                        "external_id": {
                            "type": "string",
                            "description": "A unique identifier used to associate Klaviyo profiles with profiles in an external system",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Individual's first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Individual's last name",
                        },
                        "organization": {
                            "type": "string",
                            "description": "Name of the company or organization within the company for whom the individual works",
                        },
                        "locale": {
                            "type": "string",
                            "description": "The locale of the profile, in the IETF BCP 47 language tag format",
                        },
                        "title": {
                            "type": "string",
                            "description": "Individual's job title",
                        },
                        "image": {
                            "type": "string",
                            "description": "URL pointing to the location of a profile image",
                        },
                        "address1": {
                            "type": "string",
                            "description": "First line of street address",
                        },
                        "address2": {
                            "type": "string",
                            "description": "Second line of street address",
                        },
                        "city": {"type": "string", "description": "City name"},
                        "country": {"type": "string", "description": "Country name"},
                        "latitude": {
                            "type": ["string", "number"],
                            "description": "Latitude coordinate (recommended precision of four decimal places)",
                        },
                        "longitude": {
                            "type": ["string", "number"],
                            "description": "Longitude coordinate (recommended precision of four decimal places)",
                        },
                        "region": {
                            "type": "string",
                            "description": "Region within a country, such as state or province",
                        },
                        "zip": {"type": "string", "description": "Zip code"},
                        "timezone": {
                            "type": "string",
                            "description": "Time zone name (recommend using from IANA Time Zone Database)",
                        },
                        "ip": {"type": "string", "description": "IP Address"},
                        "properties": {
                            "type": "object",
                            "description": "An object containing key/value pairs for any custom properties assigned to this profile",
                        },
                    },
                    "required": ["profile_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the updated profile data with the modified attributes",
                    "examples": [
                        '{"data":{"type":"profile","id":"01ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"updated@example.com","first_name":"Jane","last_name":"Smith","phone_number":"+19876543210","organization":"New Company Inc"},"links":{"self":"https://a.klaviyo.com/api/profiles/01ABCDEF-0123-4567-89AB-CDEF01234567"}}}'
                    ],
                },
                requiredScopes=["profiles:write"],
            ),
            Tool(
                name="list_campaigns",
                description="Returns campaigns based on the selected channel filter.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "The channel type to filter campaigns (required)",
                            "enum": ["email", "sms", "mobile_push"],
                        },
                        "additional_filter": {
                            "type": "string",
                            "description": "Optional additional filter expression (will be combined with channel filter)",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["channel"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of campaign objects with each item representing a single campaign",
                    "examples": [
                        '{"type":"campaign","id":"ABC123DEF456","attributes":{"name":"Summer Sale Announcement","status":"draft","created_at":"2023-06-15T10:00:00+00:00","updated_at":"2023-06-16T14:30:00+00:00","messages":{"channel":"email"}}}',
                        '{"type":"campaign","id":"GHI789JKL012","attributes":{"name":"Product Launch","status":"scheduled","created_at":"2023-07-01T09:15:00+00:00","updated_at":"2023-07-02T11:45:00+00:00","messages":{"channel":"email"}}}',
                    ],
                },
                requiredScopes=["campaigns:read"],
            ),
            Tool(
                name="update_campaign",
                description="Updates an existing campaign with the given campaign ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign to update (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the campaign",
                        },
                        "included_audiences": {
                            "type": "array",
                            "description": "List of audience IDs to include",
                            "items": {"type": "string"},
                        },
                        "excluded_audiences": {
                            "type": "array",
                            "description": "List of audience IDs to exclude",
                            "items": {"type": "string"},
                        },
                        "send_strategy": {
                            "type": "string",
                            "description": "The send strategy (Immediate, Static, Throttled, or SmartSendTime)",
                            "enum": [
                                "Immediate",
                                "Static",
                                "Throttled",
                                "SmartSendTime",
                            ],
                        },
                        "smart_send_time": {
                            "type": "string",
                            "description": "Date to send (required for SmartSendTime strategy, format: YYYY-MM-DD)",
                        },
                        "use_smart_sending": {
                            "type": "boolean",
                            "description": "Whether to use smart sending",
                        },
                        "add_tracking_params": {
                            "type": "boolean",
                            "description": "Whether to add tracking parameters to links",
                        },
                        "message_content": {
                            "type": "string",
                            "description": "The email content for the campaign message",
                        },
                        "subject_line": {
                            "type": "string",
                            "description": "The subject line for the email",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "The ID of the template to use for the campaign message",
                        },
                    },
                    "required": ["campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the updated campaign data with modified attributes",
                    "examples": [
                        '{"data":{"type":"campaign","id":"ABC123DEF456","attributes":{"name":"Updated Campaign Name","send_strategy":{"method":"immediate"},"send_options":{"use_smart_sending":true},"tracking_options":{"add_tracking_params":true},"status":"draft","created_at":"2023-06-15T10:00:00+00:00","updated_at":"2023-06-17T09:30:00+00:00"}}}'
                    ],
                },
                requiredScopes=["campaigns:write"],
            ),
            Tool(
                name="get_campaign",
                description="Retrieves a specific campaign by its ID from the Klaviyo account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign to retrieve (required)",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                        "include_related": {
                            "type": "array",
                            "description": "Optional list of related objects to include (e.g., campaign-messages)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the requested campaign data including ID and attributes",
                    "examples": [
                        '{"data":{"type":"campaign","id":"ABC123DEF456","attributes":{"name":"Weekly Newsletter","status":"sent","created_at":"2023-05-10T08:00:00+00:00","updated_at":"2023-05-11T14:20:00+00:00","send_time":"2023-05-12T09:00:00+00:00","audiences":{"included":["LIST123"],"excluded":[]},"send_strategy":{"method":"static"},"messages":{"channel":"email"}},"links":{"self":"https://a.klaviyo.com/api/campaigns/ABC123DEF456"}}}'
                    ],
                },
                requiredScopes=["campaigns:read"],
            ),
            Tool(
                name="send_campaign",
                description="Triggers a campaign to send asynchronously.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign to send (required)",
                        }
                    },
                    "required": ["campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the campaign send job result with status information",
                    "examples": [
                        '{"data":{"type":"campaign-send-job","id":"ABC123DEF456","status":"draft","campaign_id":"CAMPAIGN456"},"links":{"self":"https://a.klaviyo.com/api/campaign-send-jobs/ABC123DEF456"}}'
                    ],
                },
                requiredScopes=["campaigns:write"],
            ),
            Tool(
                name="delete_campaign",
                description="Deletes a campaign with the given campaign ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign to delete (required)",
                        }
                    },
                    "required": ["campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response indicating successful deletion of the campaign",
                    "examples": ['{"success":true,"campaign_id":"ABC123DEF456"}'],
                },
                requiredScopes=["campaigns:write"],
            ),
            Tool(
                name="list_metrics",
                description="Gets all metrics in a Klaviyo account with filtering options.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "integration_name": {
                            "type": "string",
                            "description": "Filter metrics by integration name (e.g., 'Shopify', 'Magento')",
                        },
                        "integration_category": {
                            "type": "string",
                            "description": "Filter metrics by integration category (e.g., 'ecommerce', 'custom')",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of metric objects with each item representing a single metric",
                    "examples": [
                        '{"type":"metric","id":"METRIC123","attributes":{"name":"Placed Order","integration":{"name":"Shopify","category":"ecommerce"},"created":"2022-01-15T12:00:00+00:00"}}',
                        '{"type":"metric","id":"METRIC456","attributes":{"name":"Viewed Product","integration":{"name":"Shopify","category":"ecommerce"},"created":"2022-01-15T12:00:00+00:00"}}',
                    ],
                },
                requiredScopes=["metrics:read"],
            ),
            Tool(
                name="get_metric",
                description="Gets a specific metric by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metric_id": {
                            "type": "string",
                            "description": "The ID of the metric to retrieve (required)",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["metric_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the requested metric data with ID and attributes",
                    "examples": [
                        '{"data":{"type":"metric","id":"METRIC123","attributes":{"name":"Placed Order","integration":{"name":"Shopify","category":"ecommerce"},"created":"2022-01-15T12:00:00+00:00","updated":"2022-02-10T09:30:00+00:00","analytics":{"total_occurrences":12543,"unique_occurrences":8976}},"links":{"self":"https://a.klaviyo.com/api/metrics/METRIC123"}}}'
                    ],
                },
                requiredScopes=["metrics:read"],
            ),
            Tool(
                name="create_list",
                description="Creates a new list in Klaviyo.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "A helpful name to label the list (required)",
                        }
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the created list data with ID and name",
                    "examples": [
                        '{"data":{"type":"list","id":"LIST123456","attributes":{"name":"Newsletter Subscribers","created":"2023-08-15T10:30:00+00:00"},"links":{"self":"https://a.klaviyo.com/api/lists/LIST123456"}}}'
                    ],
                },
                requiredScopes=["lists:write"],
            ),
            Tool(
                name="add_profiles_to_list",
                description="Adds profiles to a list with the given list ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to add profiles to (required)",
                        },
                        "profile_ids": {
                            "type": "array",
                            "description": "Array of profile IDs to add to the list (required)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["list_id", "profile_ids"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response indicating successful addition of profiles to the list",
                    "examples": [
                        '{"success":true,"list_id":"LIST123456","added_profiles":3}'
                    ],
                },
                requiredScopes=["lists:write", "profiles:read"],
            ),
            Tool(
                name="remove_profiles_from_list",
                description="Removes profiles from a list with the given list ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to remove profiles from (required)",
                        },
                        "profile_ids": {
                            "type": "array",
                            "description": "Array of profile IDs to remove from the list (required)",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["list_id", "profile_ids"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response indicating successful removal of profiles from the list",
                    "examples": [
                        '{"success":true,"list_id":"LIST123456","removed_profiles":2}'
                    ],
                },
                requiredScopes=["lists:write", "profiles:read"],
            ),
            Tool(
                name="get_list_profiles",
                description="Gets all profiles within a list with the given list ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to get profiles from (required)",
                        },
                        "filter": {
                            "type": "string",
                            "description": "Optional filter expression to filter profiles within the list",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["list_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of profile objects from the specified list with each item representing a single profile",
                    "examples": [
                        '{"type":"profile","id":"01ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"subscriber1@example.com","first_name":"Jane","last_name":"Doe","created":"2023-01-15T12:30:00+00:00"}}',
                        '{"type":"profile","id":"02ABCDEF-0123-4567-89AB-CDEF01234567","attributes":{"email":"subscriber2@example.com","first_name":"John","last_name":"Smith","created":"2023-02-20T09:45:00+00:00"}}',
                    ],
                },
                requiredScopes=["lists:read", "profiles:read"],
            ),
            Tool(
                name="get_list",
                description="Gets a specific list by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to retrieve (required)",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["list_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response containing the requested list data with ID and attributes",
                    "examples": [
                        '{"data":{"type":"list","id":"LIST123456","attributes":{"name":"Newsletter Subscribers","created":"2023-08-15T10:30:00+00:00","updated":"2023-09-01T14:15:00+00:00","folder_id":null,"profile_count":1240},"links":{"self":"https://a.klaviyo.com/api/lists/LIST123456"}}}'
                    ],
                },
                requiredScopes=["lists:read"],
            ),
            Tool(
                name="get_lists",
                description="Retrieves all lists from the Klaviyo account.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional filter expression to filter lists (e.g., 'equals(name,Newsletter Subscribers)')",
                        },
                        "include_fields": {
                            "type": "array",
                            "description": "Optional list of specific fields to include in the response",
                            "items": {"type": "string"},
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of list objects with each item representing a single list",
                    "examples": [
                        '{"type":"list","id":"LIST123456","attributes":{"name":"Newsletter Subscribers","created":"2023-08-15T10:30:00+00:00","updated":"2023-09-01T14:15:00+00:00","profile_count":1240}}',
                        '{"type":"list","id":"LIST789012","attributes":{"name":"Abandoned Cart","created":"2023-07-10T09:00:00+00:00","updated":"2023-08-20T11:30:00+00:00","profile_count":567}}',
                    ],
                },
                requiredScopes=["lists:read"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent]:
        """Handle Klaviyo tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        klaviyo_client = await create_klaviyo_client(credentials)

        if arguments is None:
            arguments = {}

        if name == "create_profile":
            # Extract all profile attributes from arguments
            profile_data = {"data": {"type": "profile", "attributes": {}}}

            # Add basic profile attributes
            for attr in [
                "email",
                "phone_number",
                "external_id",
                "first_name",
                "last_name",
                "organization",
                "locale",
                "title",
                "image",
                "timezone",
                "ip",
            ]:
                if attr in arguments and arguments[attr]:
                    profile_data["data"]["attributes"][attr] = arguments[attr]

            # Add location information
            location = {}
            for loc_attr in [
                "address1",
                "address2",
                "city",
                "country",
                "latitude",
                "longitude",
                "region",
                "zip",
            ]:
                if loc_attr in arguments and arguments[loc_attr]:
                    location[loc_attr] = arguments[loc_attr]

            # Only add location if at least one location attribute is present
            if location:
                profile_data["data"]["attributes"]["location"] = location

            # Add custom properties if present
            if "properties" in arguments and arguments["properties"]:
                profile_data["data"]["attributes"]["properties"] = arguments[
                    "properties"
                ]

            # Make API request to create profile
            profiles_url = klaviyo_client["base_url"] + "profiles"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.post(
                    profiles_url, headers=headers, json=profile_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 201, 202]:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error creating profile: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error creating profile", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "update_profile":
            # Extract parameters
            profile_id = arguments.get("profile_id")

            # Validate required parameters
            if not profile_id:
                return [
                    types.TextContent(type="text", text="Error: Profile ID is required")
                ]

            # Prepare request payload
            profile_data = {
                "data": {"type": "profile", "id": profile_id, "attributes": {}}
            }

            # Add basic profile attributes
            for attr in [
                "email",
                "phone_number",
                "external_id",
                "first_name",
                "last_name",
                "organization",
                "locale",
                "title",
                "image",
                "timezone",
                "ip",
            ]:
                if attr in arguments and arguments[attr] is not None:
                    profile_data["data"]["attributes"][attr] = arguments[attr]

            # Add location information
            location = {}
            for loc_attr in [
                "address1",
                "address2",
                "city",
                "country",
                "latitude",
                "longitude",
                "region",
                "zip",
            ]:
                if loc_attr in arguments and arguments[loc_attr] is not None:
                    location[loc_attr] = arguments[loc_attr]

            # Only add location if at least one location attribute is present
            if location:
                profile_data["data"]["attributes"]["location"] = location

            # Add custom properties if present
            if "properties" in arguments and arguments["properties"] is not None:
                profile_data["data"]["attributes"]["properties"] = arguments[
                    "properties"
                ]

            # Check if we have any attributes to update
            if not profile_data["data"]["attributes"]:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: No profile attributes provided for update",
                    )
                ]

            # Make API request to update the profile
            profile_url = klaviyo_client["base_url"] + f"profiles/{profile_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.patch(
                    profile_url, headers=headers, json=profile_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 202]:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Profile not found",
                        "profile_id": profile_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error updating profile: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error updating profile", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_profile":
            # Extract parameters
            profile_id = arguments.get("profile_id")
            include_fields = arguments.get("include_fields")

            # Validate required parameters
            if not profile_id:
                return [
                    types.TextContent(type="text", text="Error: Profile ID is required")
                ]

            # Build query parameters
            params = {}

            # Add fields to include if provided
            if include_fields:
                params["fields[profile]"] = ",".join(include_fields)

            # Make API request to get the specific profile
            profile_url = klaviyo_client["base_url"] + f"profiles/{profile_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    profile_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Profile not found",
                        "profile_id": profile_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error retrieving profile: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error retrieving profile",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_profiles":
            # Extract parameters
            filter_expr = arguments.get("filter")
            include_fields = arguments.get("include_fields")

            # Build query parameters
            params = {}

            # Add filter if provided
            if filter_expr:
                params["filter"] = filter_expr

            # Add fields to include if provided
            if include_fields:
                params["fields[profile]"] = ",".join(include_fields)

            # Make API request to get profiles
            profiles_url = klaviyo_client["base_url"] + "profiles"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    profiles_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()

                    # If we have an array of items, return each as a separate TextContent
                    if "data" in result and isinstance(result["data"], list):
                        return [
                            types.TextContent(type="text", text=json.dumps(item))
                            for item in result["data"]
                        ]

                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error retrieving profiles: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error retrieving profiles",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "update_campaign":
            # Extract parameters
            campaign_id = arguments.get("campaign_id")

            # Validate required parameters
            if not campaign_id:
                return [
                    types.TextContent(
                        type="text", text="Error: Campaign ID is required"
                    )
                ]

            # Prepare request payload
            campaign_data = {
                "data": {"type": "campaign", "id": campaign_id, "attributes": {}}
            }

            # Add campaign name if provided
            if "name" in arguments and arguments["name"]:
                campaign_data["data"]["attributes"]["name"] = arguments["name"]

            # Add audience information if provided
            if "included_audiences" in arguments or "excluded_audiences" in arguments:
                campaign_data["data"]["attributes"]["audiences"] = {}

                if (
                    "included_audiences" in arguments
                    and arguments["included_audiences"]
                ):
                    campaign_data["data"]["attributes"]["audiences"]["included"] = (
                        arguments["included_audiences"]
                    )

                if (
                    "excluded_audiences" in arguments
                    and arguments["excluded_audiences"]
                ):
                    campaign_data["data"]["attributes"]["audiences"]["excluded"] = (
                        arguments["excluded_audiences"]
                    )

            # Add send options if provided
            if "use_smart_sending" in arguments:
                if "send_options" not in campaign_data["data"]["attributes"]:
                    campaign_data["data"]["attributes"]["send_options"] = {}
                campaign_data["data"]["attributes"]["send_options"][
                    "use_smart_sending"
                ] = arguments["use_smart_sending"]

            # Add tracking options if provided
            if "add_tracking_params" in arguments:
                if "tracking_options" not in campaign_data["data"]["attributes"]:
                    campaign_data["data"]["attributes"]["tracking_options"] = {}
                campaign_data["data"]["attributes"]["tracking_options"][
                    "add_tracking_params"
                ] = arguments["add_tracking_params"]

            # Configure send strategy if provided
            if "send_strategy" in arguments and arguments["send_strategy"]:
                send_strategy = arguments["send_strategy"]

                if send_strategy == "Immediate":
                    campaign_data["data"]["attributes"]["send_strategy"] = {
                        "method": "immediate"
                    }
                elif send_strategy == "SmartSendTime":
                    # Check if smart_send_time is provided when using SmartSendTime strategy
                    smart_send_time = arguments.get("smart_send_time")
                    if not smart_send_time:
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: Smart send time is required when using SmartSendTime strategy",
                            )
                        ]

                    campaign_data["data"]["attributes"]["send_strategy"] = {
                        "method": "smart-send-time",
                        "date": smart_send_time,
                    }
                elif send_strategy == "Static":
                    campaign_data["data"]["attributes"]["send_strategy"] = {
                        "method": "static",
                        "options_static": {
                            "datetime": smart_send_time if smart_send_time else None
                        },
                    }
                elif send_strategy == "Throttled":
                    campaign_data["data"]["attributes"]["send_strategy"] = {
                        "method": "throttled"
                    }

            # Add message content if provided
            if ("message_content" in arguments and arguments["message_content"]) or (
                "subject_line" in arguments and arguments["subject_line"]
            ):
                campaign_data["data"]["relationships"] = {
                    "campaign-messages": {
                        "data": [{"type": "campaign-message", "attributes": {}}]
                    }
                }

                if "message_content" in arguments and arguments["message_content"]:
                    campaign_data["data"]["relationships"]["campaign-messages"]["data"][
                        0
                    ]["attributes"]["content"] = arguments["message_content"]

                if "subject_line" in arguments and arguments["subject_line"]:
                    campaign_data["data"]["relationships"]["campaign-messages"]["data"][
                        0
                    ]["attributes"]["subject"] = arguments["subject_line"]

            # Check if we have any attributes to update
            if (
                not campaign_data["data"]["attributes"]
                and "relationships" not in campaign_data["data"]
            ):
                return [
                    types.TextContent(
                        type="text",
                        text="Error: No campaign attributes provided for update",
                    )
                ]

            # Make API request to update campaign
            campaign_url = klaviyo_client["base_url"] + f"campaigns/{campaign_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.patch(
                    campaign_url, headers=headers, json=campaign_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 202]:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Campaign not found",
                        "campaign_id": campaign_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error updating campaign: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error updating campaign", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "list_campaigns":
            # Extract parameters
            channel = arguments.get("channel")
            additional_filter = arguments.get("additional_filter")
            include_fields = arguments.get("include_fields")

            # Validate required parameters
            if not channel or channel not in ["email", "sms", "mobile_push"]:
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Valid channel (email, sms, or mobile_push) is required",
                    )
                ]

            # Build query parameters
            params = {"filter": f"equals(messages.channel,'{channel}')"}

            # Add additional filter if provided (using AND operator)
            if additional_filter:
                params["filter"] = f"and({params['filter']},{additional_filter})"

            # Add fields to include if provided
            if include_fields:
                params["fields[campaign]"] = ",".join(include_fields)

            # Make API request to get campaigns
            campaigns_url = klaviyo_client["base_url"] + "campaigns"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    campaigns_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()

                    # If we have an array of items, return each as a separate TextContent
                    if "data" in result and isinstance(result["data"], list):
                        return [
                            types.TextContent(type="text", text=json.dumps(item))
                            for item in result["data"]
                        ]

                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error retrieving campaigns: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error retrieving campaigns",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_campaign":
            # Extract parameters
            campaign_id = arguments.get("campaign_id")
            include_fields = arguments.get("include_fields")
            include_related = arguments.get("include_related")

            # Validate required parameters
            if not campaign_id:
                return [
                    types.TextContent(
                        type="text", text="Error: Campaign ID is required"
                    )
                ]

            # Build query parameters
            params = {}

            # Add fields to include if provided
            if include_fields:
                params["fields[campaign]"] = ",".join(include_fields)

            # Add related objects to include if provided
            if include_related:
                params["include"] = ",".join(include_related)

            # Make API request to get the specific campaign
            campaign_url = klaviyo_client["base_url"] + f"campaigns/{campaign_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    campaign_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Campaign not found",
                        "campaign_id": campaign_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error retrieving campaign: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error retrieving campaign",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "list_metrics":
            # Extract parameters
            integration_name = arguments.get("integration_name")
            integration_category = arguments.get("integration_category")
            include_fields = arguments.get("include_fields")

            # Build query parameters
            params = {}

            # Build filter based on provided parameters
            filter_expressions = []

            if integration_name:
                filter_expressions.append(
                    f"equals(integration.name,'{integration_name}')"
                )

            if integration_category:
                filter_expressions.append(
                    f"equals(integration.category,'{integration_category}')"
                )

            # Combine filter expressions if multiple are provided
            if filter_expressions:
                if len(filter_expressions) == 1:
                    params["filter"] = filter_expressions[0]
                else:
                    params["filter"] = f"and({','.join(filter_expressions)})"

            # Add fields to include if provided
            if include_fields:
                params["fields[metric]"] = ",".join(include_fields)

            # Make API request to get metrics
            metrics_url = klaviyo_client["base_url"] + "metrics"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    metrics_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()

                    # If we have an array of items, return each as a separate TextContent
                    if "data" in result and isinstance(result["data"], list):
                        return [
                            types.TextContent(type="text", text=json.dumps(item))
                            for item in result["data"]
                        ]

                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error retrieving metrics: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error retrieving metrics",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "delete_campaign":
            # Extract parameters
            campaign_id = arguments.get("campaign_id")

            # Validate required parameters
            if not campaign_id:
                return [
                    types.TextContent(
                        type="text", text="Error: Campaign ID is required"
                    )
                ]

            # Make API request to delete the campaign
            campaign_url = klaviyo_client["base_url"] + f"campaigns/{campaign_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.delete(campaign_url, headers=headers, timeout=30)

                # Check if request was successful
                if response.status_code in [200, 202, 204]:
                    success_response = {"success": True, "campaign_id": campaign_id}
                    return [
                        types.TextContent(
                            type="text", text=json.dumps(success_response)
                        )
                    ]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Campaign not found",
                        "campaign_id": campaign_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error deleting campaign: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error deleting campaign", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "send_campaign":
            # Extract parameters
            campaign_id = arguments.get("campaign_id")

            # Validate required parameters
            if not campaign_id:
                return [
                    types.TextContent(
                        type="text", text="Error: Campaign ID is required"
                    )
                ]

            # First get the campaign status
            campaign_url = klaviyo_client["base_url"] + f"campaigns/{campaign_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                # Get campaign details first
                get_response = requests.get(campaign_url, headers=headers, timeout=30)

                if get_response.status_code != 200:
                    error_message = f"Error getting campaign: {get_response.status_code} - {get_response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

                campaign_data = get_response.json()
                campaign_status = (
                    campaign_data.get("data", {})
                    .get("attributes", {})
                    .get("status", "")
                )

                # Only update send strategy if campaign is in draft
                if campaign_status.lower() == "draft":
                    # Update campaign send strategy
                    update_data = {
                        "data": {
                            "type": "campaign",
                            "id": campaign_id,
                            "attributes": {"send_strategy": {"method": "immediate"}},
                        }
                    }

                    update_response = requests.patch(
                        campaign_url, headers=headers, json=update_data, timeout=30
                    )

                    if update_response.status_code not in [200, 202]:
                        error_message = f"Error updating campaign: {update_response.status_code} - {update_response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                # Now send the campaign
                send_job_data = {
                    "data": {"type": "campaign-send-job", "id": campaign_id}
                }
                send_job_url = klaviyo_client["base_url"] + "campaign-send-jobs"

                response = requests.post(
                    send_job_url, headers=headers, json=send_job_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 201, 202]:
                    result = response.json()
                    result["status"] = campaign_status.lower()
                    result["campaign_id"] = campaign_id
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Campaign not found",
                        "campaign_id": campaign_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error sending campaign: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error sending campaign", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_metric":
            # Extract parameters
            metric_id = arguments.get("metric_id")
            include_fields = arguments.get("include_fields")

            # Validate required parameters
            if not metric_id:
                return [
                    types.TextContent(type="text", text="Error: Metric ID is required")
                ]

            # Build query parameters
            params = {}

            # Add fields to include if provided
            if include_fields:
                params["fields[metric]"] = ",".join(include_fields)

            # Make API request to get the specific metric
            metric_url = klaviyo_client["base_url"] + f"metrics/{metric_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    metric_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {
                        "error": "Metric not found",
                        "metric_id": metric_id,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error retrieving metric: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error retrieving metric", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "add_profiles_to_list":
            # Extract parameters
            list_id = arguments.get("list_id")
            profile_ids = arguments.get("profile_ids", [])

            # Validate required parameters
            if not list_id:
                return [
                    types.TextContent(type="text", text="Error: List ID is required")
                ]

            if not profile_ids:
                return [
                    types.TextContent(
                        type="text", text="Error: At least one profile ID is required"
                    )
                ]

            # Prepare request payload
            profiles_data = {
                "data": [
                    {"type": "profile", "id": profile_id} for profile_id in profile_ids
                ]
            }

            # Make API request to add profiles to the list
            relationship_url = (
                klaviyo_client["base_url"] + f"lists/{list_id}/relationships/profiles"
            )
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.post(
                    relationship_url, headers=headers, json=profiles_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 201, 202, 204]:
                    success_response = {
                        "success": True,
                        "list_id": list_id,
                        "added_profiles": len(profile_ids),
                    }
                    return [
                        types.TextContent(
                            type="text", text=json.dumps(success_response)
                        )
                    ]
                elif response.status_code == 404:
                    error_response = {"error": "List not found", "list_id": list_id}
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error adding profiles to list: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error adding profiles to list",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "remove_profiles_from_list":
            # Extract parameters
            list_id = arguments.get("list_id")
            profile_ids = arguments.get("profile_ids", [])

            # Validate required parameters
            if not list_id:
                return [
                    types.TextContent(type="text", text="Error: List ID is required")
                ]

            if not profile_ids:
                return [
                    types.TextContent(
                        type="text", text="Error: At least one profile ID is required"
                    )
                ]

            # Prepare request payload
            profiles_data = {
                "data": [
                    {"type": "profile", "id": profile_id} for profile_id in profile_ids
                ]
            }

            # Make API request to remove profiles from the list
            relationship_url = (
                klaviyo_client["base_url"] + f"lists/{list_id}/relationships/profiles"
            )
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.delete(
                    relationship_url, headers=headers, json=profiles_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 202, 204]:
                    success_response = {
                        "success": True,
                        "list_id": list_id,
                        "removed_profiles": len(profile_ids),
                    }
                    return [
                        types.TextContent(
                            type="text", text=json.dumps(success_response)
                        )
                    ]
                elif response.status_code == 404:
                    error_response = {"error": "List not found", "list_id": list_id}
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error removing profiles from list: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {
                    "error": "Error removing profiles from list",
                    "details": str(e),
                }
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "create_list":
            # Extract parameters
            list_name = arguments.get("name")

            # Validate required parameters
            if not list_name:
                return [
                    types.TextContent(type="text", text="Error: List name is required")
                ]

            # Prepare request payload
            list_data = {"data": {"type": "list", "attributes": {"name": list_name}}}

            # Make API request to create the list
            lists_url = klaviyo_client["base_url"] + "lists"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.post(
                    lists_url, headers=headers, json=list_data, timeout=30
                )

                # Check if request was successful
                if response.status_code in [200, 201, 202]:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error creating list: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error creating list", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_list_profiles":
            # Extract parameters
            list_id = arguments.get("list_id")
            filter_expr = arguments.get("filter")
            include_fields = arguments.get("include_fields")

            # Validate required parameters
            if not list_id:
                return [
                    types.TextContent(type="text", text="Error: List ID is required")
                ]

            # Build query parameters
            params = {}

            # Add filter if provided
            if filter_expr:
                params["filter"] = filter_expr

            # Add fields to include if provided
            if include_fields:
                params["fields[profile]"] = ",".join(include_fields)

            # Make API request to get profiles from the list
            list_profiles_url = klaviyo_client["base_url"] + f"lists/{list_id}/profiles"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    list_profiles_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()

                    # If we have an array of items, return each as a separate TextContent
                    if "data" in result and isinstance(result["data"], list):
                        return [
                            types.TextContent(type="text", text=json.dumps(item))
                            for item in result["data"]
                        ]

                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {"error": "List not found", "list_id": list_id}
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error retrieving profiles from list: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_list":
            # Extract parameters
            list_id = arguments.get("list_id")
            include_fields = arguments.get("include_fields")

            # Validate required parameters
            if not list_id:
                return [
                    types.TextContent(type="text", text="Error: List ID is required")
                ]

            # Build query parameters
            params = {}

            # Add fields to include if provided
            if include_fields:
                params["fields[list]"] = ",".join(include_fields)

            # Make API request to get the specific list
            list_url = klaviyo_client["base_url"] + f"lists/{list_id}"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    list_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()
                    return [types.TextContent(type="text", text=json.dumps(result))]
                elif response.status_code == 404:
                    error_response = {"error": "List not found", "list_id": list_id}
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]
                else:
                    error_response = {
                        "error": f"Error retrieving list: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        elif name == "get_lists":
            # Extract parameters
            filter_expr = arguments.get("filter")
            include_fields = arguments.get("include_fields")

            # Build query parameters
            params = {}

            # Add filter if provided
            if filter_expr:
                params["filter"] = filter_expr

            # Add fields to include if provided
            if include_fields:
                params["fields[list]"] = ",".join(include_fields)

            # Make API request to get lists
            lists_url = klaviyo_client["base_url"] + "lists"
            headers = klaviyo_client["headers"].copy()

            # Add API key header if available
            if server.api_key:
                headers["Klaviyo-API-Key"] = server.api_key

            try:
                response = requests.get(
                    lists_url, headers=headers, params=params, timeout=30
                )

                # Check if request was successful
                if response.status_code == 200:
                    result = response.json()

                    # If we have an array of items, return each as a separate TextContent
                    if "data" in result and isinstance(result["data"], list):
                        return [
                            types.TextContent(type="text", text=json.dumps(item))
                            for item in result["data"]
                        ]

                    return [types.TextContent(type="text", text=json.dumps(result))]
                else:
                    error_response = {
                        "error": f"Error retrieving lists: {response.status_code}",
                        "details": response.text,
                    }
                    return [
                        types.TextContent(type="text", text=json.dumps(error_response))
                    ]

            except Exception as e:
                error_response = {"error": "Error retrieving lists", "details": str(e)}
                return [types.TextContent(type="text", text=json.dumps(error_response))]

        else:
            error_response = {"error": "Tool not implemented", "tool": name}
            return [types.TextContent(type="text", text=json.dumps(error_response))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="klaviyo-server",
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
        print("  python main.py auth - Run authentication flow for a user")
        print("  python main.py - Run the server")
