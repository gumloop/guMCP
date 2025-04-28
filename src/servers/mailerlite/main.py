import os
import sys
from pathlib import Path
import logging
from typing import List, Optional, Iterable
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import mailerlite
import json

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
    Resource,
    AnyUrl,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

from src.utils.mailerlite.util import (
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
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    class MailerLiteClient:
        def __init__(self):
            self.client = None

        async def ensure_client(self):
            if not self.client:
                credentials = get_credentials(
                    server.user_id, server.api_key, SERVICE_NAME
                )
                self.client = mailerlite.Client({"api_key": credentials["client_key"]})

                if not self.client:
                    raise ValueError("Failed to authenticate with MailerLite")
            return self.client

        @server.list_resources()
        async def handle_list_resources(
            cursor: Optional[str] = None,
        ) -> list[Resource]:
            """List MailerLite resources (lists, campaigns, subscribers)"""
            logger.info(
                f"Listing resources for user: {server.user_id} with cursor: {cursor}"
            )

            mailer = MailerLiteClient()
            try:
                client = await mailer.ensure_client()
                resources = []

                # List all webhooks
                webhooks_response = client.webhooks.list()
                logger.info(f"Webhooks response: {webhooks_response}")
                for webhook in webhooks_response.get("data", []):
                    resources.append(
                        Resource(
                            uri=f"mailerlite://webhook/{webhook['id']}",
                            mimeType="application/json",
                            name=f"Webhook: {webhook['name']}",
                            description=f"MailerLite webhook ({webhook.get('status', 'unknown')})",
                        )
                    )

                # List all forms
                popup_forms_response = client.forms.list(
                    type="popup",
                    sort="name",
                )
                embedded_forms_response = client.forms.list(
                    type="embedded",
                    sort="name",
                )
                promotion_forms_response = client.forms.list(
                    type="promotion",
                    sort="name",
                )
                forms_response = [
                    *popup_forms_response.get("data", []),
                    *embedded_forms_response.get("data", []),
                    *promotion_forms_response.get("data", []),
                ]
                for form in forms_response:
                    resources.append(
                        Resource(
                            uri=f"mailerlite://form/{form['id']}",
                            mimeType="application/json",
                            name=f"Form: {form['name']}",
                            description=f"MailerLite form ({form.get('type', 'unknown')})",
                        )
                    )

                # List all campaigns
                draft_campaigns_response = client.campaigns.list(
                    filter={"status": "draft"}
                )
                ready_campaigns_response = client.campaigns.list(
                    filter={"status": "ready"}
                )
                sent_campaigns_response = client.campaigns.list(
                    filter={"status": "sent"}
                )
                campaigns_response = [
                    *draft_campaigns_response.get("data", []),
                    *ready_campaigns_response.get("data", []),
                    *sent_campaigns_response.get("data", []),
                ]
                for campaign in campaigns_response:
                    resources.append(
                        Resource(
                            uri=f"mailerlite://campaign/{campaign['id']}",
                            mimeType="application/json",
                            name=f"Campaign: {campaign['name']}",
                            description=f"MailerLite campaign ({campaign.get('status', 'unknown')})",
                        )
                    )

                # List all groups
                groups_response = client.groups.list()
                for group in groups_response.get("data", []):
                    resources.append(
                        Resource(
                            uri=f"mailerlite://group/{group['id']}",
                            mimeType="application/json",
                            name=f"Group: {group['name']}",
                            description=f"MailerLite group with {group.get('total', 0)} subscribers",
                        )
                    )

                return resources

            except Exception as e:
                logger.error(
                    f"Error listing MailerLite resources: {e} {e.__traceback__.tb_lineno}"
                )
                return []

        @server.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
            """Read a resource from MailerLite by URI"""
            logger.info(f"Reading resource: {uri} for user: {server.user_id}")

            mailer = MailerLiteClient()
            try:
                client = await mailer.ensure_client()
                uri_str = str(uri)

                if uri_str.startswith("mailerlite://webhook/"):
                    # Handle webhook resource
                    webhook_id = uri_str.replace("mailerlite://webhook/", "")
                    webhook_data = client.webhooks.get(int(webhook_id))
                    return [
                        ReadResourceContents(
                            content=json.dumps(webhook_data, indent=2),
                            mime_type="application/json",
                        )
                    ]

                elif uri_str.startswith("mailerlite://form/"):
                    # Handle form resource
                    form_id = uri_str.replace("mailerlite://form/", "")
                    form_data = client.forms.get(int(form_id))
                    return [
                        ReadResourceContents(
                            content=json.dumps(form_data, indent=2),
                            mime_type="application/json",
                        )
                    ]

                elif uri_str.startswith("mailerlite://campaign/"):
                    # Handle campaign resource
                    campaign_id = uri_str.replace("mailerlite://campaign/", "")
                    campaign_data = client.campaigns.get(int(campaign_id))
                    return [
                        ReadResourceContents(
                            content=json.dumps(campaign_data, indent=2),
                            mime_type="application/json",
                        )
                    ]

                elif uri_str.startswith("mailerlite://group/"):
                    # Handle group resource
                    group_id = uri_str.replace("mailerlite://group/", "")
                    subscribers = client.groups.get_group_subscribers(int(group_id))

                    combined_data = {"group_id": group_id, "subscribers": subscribers}
                    return [
                        ReadResourceContents(
                            content=json.dumps(combined_data, indent=2),
                            mime_type="application/json",
                        )
                    ]

                raise ValueError(f"Unsupported resource URI: {uri_str}")

            except Exception as e:
                logger.error(
                    f"Error reading MailerLite resource: {e} {e.__traceback__.tb_lineno}"
                )
                return [
                    ReadResourceContents(
                        content=json.dumps({"error": str(e)}),
                        mime_type="application/json",
                    )
                ]

        @server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [
                types.Tool(
                    name="list_all_subscribers",
                    description="List all subscribers in the MailerLite account",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of subscribers to return per page",
                                "default": 10,
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "status": {
                                        "type": "string",
                                        "description": "Filter subscribers by status (active, unsubscribed, etc.)",
                                        "default": "active",
                                    }
                                },
                            },
                        },
                    },
                ),
                types.Tool(
                    name="create_subscriber",
                    description="Create a new subscriber in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Email address of the subscriber",
                            },
                            "fields": {
                                "type": "object",
                                "description": "Additional fields for the subscriber (name, last_name, etc.)",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "First name of the subscriber",
                                    },
                                    "last_name": {
                                        "type": "string",
                                        "description": "Last name of the subscriber",
                                    },
                                },
                            },
                        },
                        "required": ["email"],
                    },
                ),
                types.Tool(
                    name="update_subscriber",
                    description="Update an existing subscriber in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Email address of the subscriber to update",
                            },
                            "fields": {
                                "type": "object",
                                "description": "Fields to update for the subscriber (name, last_name, etc.)",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "New first name of the subscriber",
                                    },
                                    "last_name": {
                                        "type": "string",
                                        "description": "New last name of the subscriber",
                                    },
                                },
                            },
                        },
                        "required": ["email", "fields"],
                    },
                ),
                types.Tool(
                    name="get_subscriber",
                    description="Get a subscriber's details from MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "email": {
                                "type": "string",
                                "description": "Email address of the subscriber to retrieve",
                            }
                        },
                        "required": ["email"],
                    },
                ),
                types.Tool(
                    name="delete_subscriber",
                    description="Delete a subscriber from MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subscriber_id": {
                                "type": "number",
                                "description": "ID of the subscriber to delete",
                            }
                        },
                        "required": ["subscriber_id"],
                    },
                ),
                types.Tool(
                    name="list_groups",
                    description="List all groups in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of groups to return per page",
                                "default": 10,
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Filter groups by name",
                                    }
                                },
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort groups by field (e.g., 'name')",
                                "default": "name",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="create_group",
                    description="Create a new group in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_name": {
                                "type": "string",
                                "description": "Name of the group to create",
                            }
                        },
                        "required": ["group_name"],
                    },
                ),
                types.Tool(
                    name="update_group",
                    description="Update an existing group in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_id": {
                                "type": "number",
                                "description": "ID of the group to update",
                            },
                            "group_name": {
                                "type": "string",
                                "description": "New name for the group",
                            },
                        },
                        "required": ["group_id", "group_name"],
                    },
                ),
                types.Tool(
                    name="delete_group",
                    description="Delete a group from MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_id": {
                                "type": "number",
                                "description": "ID of the group to delete",
                            }
                        },
                        "required": ["group_id"],
                    },
                ),
                types.Tool(
                    name="get_group_subscribers",
                    description="Get subscribers belonging to a group",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_id": {
                                "type": "number",
                                "description": "ID of the group",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of subscribers to return per page",
                                "default": 10,
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "status": {
                                        "type": "string",
                                        "description": "Filter subscribers by status (active, unsubscribed, etc.)",
                                        "default": "active",
                                    }
                                },
                            },
                        },
                        "required": ["group_id"],
                    },
                ),
                types.Tool(
                    name="assign_subscriber_to_group",
                    description="Assign a subscriber to a group",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subscriber_id": {
                                "type": "number",
                                "description": "ID of the subscriber",
                            },
                            "group_id": {
                                "type": "number",
                                "description": "ID of the group",
                            },
                        },
                        "required": ["subscriber_id", "group_id"],
                    },
                ),
                types.Tool(
                    name="unassign_subscriber_from_group",
                    description="Remove a subscriber from a group",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "subscriber_id": {
                                "type": "number",
                                "description": "ID of the subscriber",
                            },
                            "group_id": {
                                "type": "number",
                                "description": "ID of the group",
                            },
                        },
                        "required": ["subscriber_id", "group_id"],
                    },
                ),
                types.Tool(
                    name="list_fields",
                    description="List all fields in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of fields to return per page",
                                "default": 10,
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "keyword": {
                                        "type": "string",
                                        "description": "Filter fields by keyword",
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Filter fields by type (text, number, etc.)",
                                    },
                                },
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort fields by field (e.g., 'name')",
                                "default": "name",
                            },
                        },
                    },
                ),
                types.Tool(
                    name="create_field",
                    description="Create a new field in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the field to create",
                            },
                            "type": {
                                "type": "string",
                                "description": "Type of the field (text, number, etc.)",
                            },
                        },
                        "required": ["name", "type"],
                    },
                ),
                types.Tool(
                    name="update_field",
                    description="Update an existing field in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "field_id": {
                                "type": "number",
                                "description": "ID of the field to update",
                            },
                            "name": {
                                "type": "string",
                                "description": "New name for the field",
                            },
                        },
                        "required": ["field_id", "name"],
                    },
                ),
                types.Tool(
                    name="delete_field",
                    description="Delete a field from MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "field_id": {
                                "type": "number",
                                "description": "ID of the field to delete",
                            }
                        },
                        "required": ["field_id"],
                    },
                ),
                types.Tool(
                    name="list_campaigns",
                    description="List all campaigns in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Number of campaigns to return per page",
                                "default": 10,
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "status": {
                                        "type": "string",
                                        "description": "Filter campaigns by status (ready, draft, etc.)",
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Filter campaigns by type (regular, etc.)",
                                    },
                                },
                            },
                        },
                    },
                ),
                types.Tool(
                    name="get_campaign",
                    description="Get details of a specific campaign",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "number",
                                "description": "ID of the campaign",
                            }
                        },
                        "required": ["campaign_id"],
                    },
                ),
                types.Tool(
                    name="create_campaign",
                    description="Create a new campaign in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Name of the campaign",
                            },
                            "language_id": {
                                "type": "number",
                                "description": "Language ID for the campaign",
                            },
                            "type": {
                                "type": "string",
                                "description": "Type of campaign (regular, etc.)",
                            },
                            "emails": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "subject": {
                                            "type": "string",
                                            "description": "Email subject",
                                        },
                                        "from_name": {
                                            "type": "string",
                                            "description": "Sender name",
                                        },
                                        "from": {
                                            "type": "string",
                                            "description": "Sender email",
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Email content",
                                        },
                                    },
                                    "required": [
                                        "subject",
                                        "from_name",
                                        "from",
                                        "content",
                                    ],
                                },
                            },
                        },
                        "required": ["name", "language_id", "type", "emails"],
                    },
                ),
                types.Tool(
                    name="update_campaign",
                    description="Update an existing campaign",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "number",
                                "description": "ID of the campaign to update",
                            },
                            "name": {
                                "type": "string",
                                "description": "New name for the campaign",
                            },
                            "language_id": {
                                "type": "number",
                                "description": "New language ID for the campaign",
                            },
                            "emails": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "subject": {
                                            "type": "string",
                                            "description": "Email subject",
                                        },
                                        "from_name": {
                                            "type": "string",
                                            "description": "Sender name",
                                        },
                                        "from": {
                                            "type": "string",
                                            "description": "Sender email",
                                        },
                                        "content": {
                                            "type": "string",
                                            "description": "Email content",
                                        },
                                    },
                                    "required": [
                                        "subject",
                                        "from_name",
                                        "from",
                                        "content",
                                    ],
                                },
                            },
                        },
                        "required": ["campaign_id", "name", "language_id", "emails"],
                    },
                ),
                types.Tool(
                    name="schedule_campaign",
                    description="Schedule a campaign for delivery",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "number",
                                "description": "ID of the campaign to schedule",
                            },
                            "date": {
                                "type": "string",
                                "description": "Scheduled date (YYYY-MM-DD)",
                            },
                            "hours": {
                                "type": "number",
                                "description": "Scheduled hour (00-23)",
                            },
                            "minutes": {
                                "type": "number",
                                "description": "Scheduled minutes (00-59)",
                            },
                        },
                        "required": ["campaign_id", "date", "hours", "minutes"],
                    },
                ),
                types.Tool(
                    name="cancel_campaign",
                    description="Cancel a scheduled campaign",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "number",
                                "description": "ID of the campaign to cancel",
                            }
                        },
                        "required": ["campaign_id"],
                    },
                ),
                types.Tool(
                    name="delete_campaign",
                    description="Delete a campaign",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "campaign_id": {
                                "type": "number",
                                "description": "ID of the campaign to delete",
                            }
                        },
                        "required": ["campaign_id"],
                    },
                ),
                types.Tool(
                    name="list_forms",
                    description="List all forms in MailerLite",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Type of form to list (popup, embedded, landing_page)",
                                "default": "popup",
                            },
                            "limit": {
                                "type": "number",
                                "description": "Number of forms to return per page",
                                "default": 10,
                            },
                            "page": {
                                "type": "number",
                                "description": "Page number to return",
                                "default": 1,
                            },
                            "sort": {
                                "type": "string",
                                "description": "Sort field (e.g., 'name')",
                                "default": "name",
                            },
                            "filter": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Filter forms by name",
                                    }
                                },
                            },
                        },
                        "required": ["type"],
                    },
                ),
                types.Tool(
                    name="get_form",
                    description="Get details of a specific form",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "form_id": {
                                "type": "number",
                                "description": "ID of the form",
                            }
                        },
                        "required": ["form_id"],
                    },
                ),
                types.Tool(
                    name="update_form",
                    description="Update a form's name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "form_id": {
                                "type": "number",
                                "description": "ID of the form to update",
                            },
                            "name": {
                                "type": "string",
                                "description": "New name for the form",
                            },
                        },
                        "required": ["form_id", "name"],
                    },
                ),
                types.Tool(
                    name="delete_form",
                    description="Delete a form",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "form_id": {
                                "type": "number",
                                "description": "ID of the form to delete",
                            }
                        },
                        "required": ["form_id"],
                    },
                ),
                types.Tool(
                    name="list_campaign_languages",
                    description="Get a list of available languages for campaigns",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="list_webhooks",
                    description="List all webhooks in MailerLite",
                    inputSchema={"type": "object", "properties": {}},
                ),
                types.Tool(
                    name="get_webhook",
                    description="Get details of a specific webhook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "webhook_id": {
                                "type": "number",
                                "description": "ID of the webhook",
                            }
                        },
                        "required": ["webhook_id"],
                    },
                ),
                types.Tool(
                    name="create_webhook",
                    description="Create a new webhook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "events": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of events to subscribe to (e.g., subscriber.created, subscriber.updated)",
                            },
                            "url": {
                                "type": "string",
                                "description": "URL where webhook events will be sent",
                            },
                            "name": {
                                "type": "string",
                                "description": "Name of the webhook",
                            },
                        },
                        "required": ["events", "url", "name"],
                    },
                ),
                types.Tool(
                    name="update_webhook",
                    description="Update an existing webhook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "webhook_id": {
                                "type": "number",
                                "description": "ID of the webhook to update",
                            },
                            "events": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of events to subscribe to (e.g., subscriber.created, subscriber.updated)",
                            },
                            "url": {
                                "type": "string",
                                "description": "URL where webhook events will be sent",
                            },
                            "name": {
                                "type": "string",
                                "description": "New name for the webhook",
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether the webhook is enabled",
                                "default": True,
                            },
                        },
                        "required": ["webhook_id", "events", "url", "name"],
                    },
                ),
                types.Tool(
                    name="delete_webhook",
                    description="Delete a webhook",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "webhook_id": {
                                "type": "number",
                                "description": "ID of the webhook to delete",
                            }
                        },
                        "required": ["webhook_id"],
                    },
                ),
            ]

        @server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None = None
        ) -> List[TextContent | ImageContent | EmbeddedResource]:
            logger.info(
                "User %s calling tool: %s with arguments: %s",
                server.user_id,
                name,
                arguments,
            )

            mailer = MailerLiteClient()

            try:
                client = await mailer.ensure_client()
                if name == "list_all_subscribers":
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status", "active")
                    response = client.subscribers.list(
                        limit=limit, filter={"status": filter_status}
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]

                elif name == "create_subscriber":
                    email = arguments.get("email")
                    fields = arguments.get("fields", {})
                    response = client.subscribers.create(email, fields=fields)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_subscriber":
                    email = arguments.get("email")
                    fields = arguments.get("fields", {})
                    response = client.subscribers.update(email, fields=fields)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "get_subscriber":
                    email = arguments.get("email")
                    response = client.subscribers.get(email)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_subscriber":
                    subscriber_id = arguments.get("subscriber_id")
                    response = client.subscribers.delete(subscriber_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "list_groups":
                    limit = arguments.get("limit", 10)
                    filter_name = arguments.get("filter", {}).get("name")
                    sort = arguments.get("sort", "name")
                    response = client.groups.list(
                        limit=limit, filter={"name": filter_name}, sort=sort
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "create_group":
                    group_name = arguments.get("group_name")
                    response = client.groups.create(group_name)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_group":
                    group_id = arguments.get("group_id")
                    group_name = arguments.get("group_name")
                    response = client.groups.update(group_id, group_name)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_group":
                    group_id = arguments.get("group_id")
                    response = client.groups.delete(group_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "get_group_subscribers":
                    group_id = arguments.get("group_id")
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status", "active")
                    response = client.groups.get_group_subscribers(
                        group_id, limit=limit, filter={"status": filter_status}
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "assign_subscriber_to_group":
                    subscriber_id = arguments.get("subscriber_id")
                    group_id = arguments.get("group_id")
                    response = client.subscribers.assign_subscriber_to_group(
                        subscriber_id, group_id
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "unassign_subscriber_from_group":
                    subscriber_id = arguments.get("subscriber_id")
                    group_id = arguments.get("group_id")
                    response = client.subscribers.unassign_subscriber_from_group(
                        subscriber_id, group_id
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "list_fields":
                    limit = arguments.get("limit", 10)
                    filter_keyword = arguments.get("filter", {}).get("keyword")
                    filter_type = arguments.get("filter", {}).get("type")
                    sort = arguments.get("sort", "name")
                    response = client.fields.list(
                        limit=limit,
                        filter={"keyword": filter_keyword, "type": filter_type},
                        sort=sort,
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "create_field":
                    name = arguments.get("name")
                    field_type = arguments.get("type")
                    response = client.fields.create(name, field_type)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_field":
                    field_id = arguments.get("field_id")
                    name = arguments.get("name")
                    response = client.fields.update(field_id, name)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_field":
                    field_id = arguments.get("field_id")
                    response = client.fields.delete(field_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "list_campaigns":
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status")
                    response = client.campaigns.list(
                        limit=limit, filter={"status": filter_status}
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "get_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.get(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "create_campaign":
                    params = {
                        "name": arguments.get("name"),
                        "language_id": arguments.get("language_id"),
                        "type": arguments.get("type"),
                        "emails": arguments.get("emails", []),
                    }
                    response = client.campaigns.create(params)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_campaign":
                    campaign_id = arguments.get("campaign_id")
                    params = {
                        "name": arguments.get("name"),
                        "language_id": arguments.get("language_id"),
                        "emails": arguments.get("emails", []),
                    }
                    response = client.campaigns.update(campaign_id, params)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "schedule_campaign":
                    campaign_id = arguments.get("campaign_id")
                    params = {
                        "date": arguments.get("date"),
                        "hours": arguments.get("hours"),
                        "minutes": arguments.get("minutes"),
                    }
                    response = client.campaigns.schedule(campaign_id, params)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "cancel_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.cancel(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.delete(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]

                elif name == "list_forms":
                    form_type = arguments.get("type", "popup")
                    limit = arguments.get("limit", 10)
                    page = arguments.get("page", 1)
                    sort = arguments.get("sort", "name")
                    filter_name = arguments.get("filter", {}).get("name")
                    response = client.forms.list(
                        type=form_type,
                        limit=limit,
                        page=page,
                        sort=sort,
                        filter={"name": filter_name},
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "get_form":
                    form_id = arguments.get("form_id")
                    response = client.forms.get(form_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_form":
                    form_id = arguments.get("form_id")
                    name = arguments.get("name")
                    response = client.forms.update(form_id, name)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_form":
                    form_id = arguments.get("form_id")
                    response = client.forms.delete(form_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "list_campaign_languages":
                    response = client.campaigns.languages()
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "list_webhooks":
                    response = client.webhooks.list()
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "get_webhook":
                    webhook_id = arguments.get("webhook_id")
                    response = client.webhooks.get(webhook_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "create_webhook":
                    events = arguments.get("events")
                    url = arguments.get("url")
                    name = arguments.get("name")
                    response = client.webhooks.create(events, url, name)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "update_webhook":
                    webhook_id = arguments.get("webhook_id")
                    events = arguments.get("events")
                    url = arguments.get("url")
                    name = arguments.get("name")
                    enabled = arguments.get("enabled", True)
                    response = client.webhooks.update(
                        webhook_id, events, url, name, enabled
                    )
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]
                elif name == "delete_webhook":
                    webhook_id = arguments.get("webhook_id")
                    response = client.webhooks.delete(webhook_id)
                    return [
                        TextContent(
                            type="text",
                            text=str(response),
                        )
                    ]

                else:
                    raise ValueError(f"Tool {name} not found")

            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name=f"{SERVICE_NAME}-server",
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
