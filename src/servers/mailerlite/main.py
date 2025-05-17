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
            """List MailerLite resources (forms, campaigns)"""
            logger.info(
                f"Listing resources for user: {server.user_id} with cursor: {cursor}"
            )

            mailer = MailerLiteClient()
            try:
                client = await mailer.ensure_client()
                resources = []

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

                if uri_str.startswith("mailerlite://form/"):
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual subscriber items, one per TextContent. Each item contains subscriber details including ID, email, status, and fields.",
                        "examples": [
                            '{"id": 123456789, "email": "example@email.com", "status": "active", "fields": {"name": "John", "last_name": "Doe"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the newly created subscriber",
                        "examples": [
                            '{"data": {"id": 123456789, "email": "example@email.com", "status": "active", "fields": {"name": "John", "last_name": "Doe"}}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated subscriber",
                        "examples": [
                            '{"data": {"id": 123456789, "email": "example@email.com", "status": "active", "fields": {"name": "Updated Name", "last_name": "Updated Last Name"}}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Detailed information about the requested subscriber",
                        "examples": [
                            '{"data": {"id": 123456789, "email": "example@email.com", "status": "active", "fields": {"name": "John", "last_name": "Doe"}, "subscribed_at": "2023-01-15 10:00:00", "updated_at": "2023-01-20 12:30:45"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual group items, one per TextContent. Each item contains group details including ID, name, and subscriber counts.",
                        "examples": [
                            '{"id": 12345, "name": "Newsletter Subscribers", "active_count": 42, "sent_count": 15, "opened_count": 10, "clicked_count": 5, "unsubscribed_count": 2, "created_at": "2023-01-15 10:00:00"}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the newly created group",
                        "examples": [
                            '{"data": {"id": 12345, "name": "New Group", "total": 0, "active_count": 0, "unsubscribed_count": 0, "bounced_count": 0, "created_at": "2023-04-10 09:30:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated group",
                        "examples": [
                            '{"data": {"id": 12345, "name": "Updated Group Name", "total": 42, "active_count": 40, "unsubscribed_count": 2, "bounced_count": 0, "created_at": "2023-01-15 10:00:00", "updated_at": "2023-04-10 14:25:30"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual subscribers in the group, one per TextContent. Each item contains subscriber details.",
                        "examples": [
                            '{"id": 123456789, "email": "subscriber@example.com", "status": "active", "fields": {"name": "John", "last_name": "Doe"}, "subscribed_at": "2023-02-10 15:20:00"}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of assigning the subscriber to the group",
                        "examples": ['{"success": true}'],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of removing the subscriber from the group",
                        "examples": ['{"success": true}'],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual custom fields, one per TextContent. Each item contains field details.",
                        "examples": [
                            '{"id": 789, "name": "phone_number", "key": "phone_number", "type": "text", "created_at": "2023-01-05 08:15:30"}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the newly created custom field",
                        "examples": [
                            '{"data": {"id": 789, "name": "Company Size", "key": "company_size", "type": "number", "created_at": "2023-04-20 11:30:45"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated custom field",
                        "examples": [
                            '{"data": {"id": 789, "name": "Updated Field Name", "key": "company_size", "type": "number", "created_at": "2023-04-20 11:30:45", "updated_at": "2023-04-22 09:15:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual campaign items, one per TextContent. Each item contains campaign details including ID, name, status, and statistics.",
                        "examples": [
                            '{"id": 456789, "name": "Monthly Newsletter", "type": "regular", "status": "sent", "sent_at": "2023-03-15 09:00:00", "created_at": "2023-03-10 14:30:00", "stats": {"sent": 1000, "opened": 450, "clicked": 200}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Detailed information about the requested campaign",
                        "examples": [
                            '{"data": {"id": 456789, "name": "Monthly Newsletter", "type": "regular", "status": "sent", "subject": "March Updates", "from_name": "Marketing Team", "from_email": "marketing@example.com", "language_id": 1, "emails": [{"id": 123, "subject": "March Updates", "from_name": "Marketing Team", "from": "marketing@example.com", "content": "Newsletter content here"}], "created_at": "2023-03-10 14:30:00", "updated_at": "2023-03-15 08:55:00", "scheduled_for": "2023-03-15 09:00:00", "sent_at": "2023-03-15 09:00:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the newly created campaign",
                        "examples": [
                            '{"data": {"id": 456789, "name": "New Campaign", "type": "regular", "status": "draft", "language_id": 1, "emails": [{"id": 123, "subject": "Welcome", "from_name": "Marketing", "from": "marketing@example.com", "content": "Welcome content"}], "created_at": "2023-04-25 10:20:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated campaign",
                        "examples": [
                            '{"data": {"id": 456789, "name": "Updated Campaign", "type": "regular", "status": "draft", "language_id": 7, "emails": [{"id": 123, "subject": "Updated Subject", "from_name": "Updated Name", "from": "updated@example.com", "content": "Updated content"}], "created_at": "2023-04-20 10:00:00", "updated_at": "2023-04-25 15:30:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the scheduling operation",
                        "examples": [
                            '{"data": {"campaign_id": 456789, "scheduled_for": "2023-12-31 12:00:00", "status": "scheduled"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the cancel operation",
                        "examples": [
                            '{"success": true, "campaign_id": 456789, "status": "draft"}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
                    },
                ),
                types.Tool(
                    name="list_forms",
                    description="List all forms with optional filtering by type and name.",
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual form items, one per TextContent. Each item contains form details including ID, name, type, and status.",
                        "examples": [
                            '{"id": 987654, "name": "Newsletter Signup", "type": "popup", "status": "active", "created_at": "2023-02-05 11:20:00", "updated_at": "2023-02-05 11:20:00", "total_subscribers": 150}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Detailed information about the requested form",
                        "examples": [
                            '{"data": {"id": 987654, "name": "Newsletter Signup", "type": "popup", "status": "active", "settings": {"title": "Join Our Newsletter", "button_text": "Subscribe"}, "created_at": "2023-02-05 11:20:00", "updated_at": "2023-02-05 11:20:00", "total_subscribers": 150}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated form",
                        "examples": [
                            '{"data": {"id": 987654, "name": "Updated Form Name", "type": "popup", "status": "active", "created_at": "2023-02-05 11:20:00", "updated_at": "2023-04-10 09:45:00", "total_subscribers": 150}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
                    },
                ),
                types.Tool(
                    name="list_campaign_languages",
                    description="Get a list of available languages for campaigns",
                    inputSchema={"type": "object", "properties": {}},
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of available language options for campaign creation and editing",
                        "examples": [
                            '{"data": [{"id": 1, "name": "English", "code": "en"}, {"id": 7, "name": "Spanish", "code": "es"}]}'
                        ],
                    },
                ),
                types.Tool(
                    name="list_webhooks",
                    description="List all webhooks in the MailerLite account",
                    inputSchema={"type": "object", "properties": {}},
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Individual webhook items, one per TextContent. Each item contains webhook details including ID, name, URL, and event types.",
                        "examples": [
                            '{"id": 54321, "name": "Subscriber Webhook", "url": "https://example.com/webhook", "events": ["subscriber.created", "subscriber.updated"], "status": "enabled", "created_at": "2023-01-20 14:10:30"}'
                        ],
                    },
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Detailed information about the requested webhook",
                        "examples": [
                            '{"data": {"id": 54321, "name": "Subscriber Webhook", "url": "https://example.com/webhook", "events": ["subscriber.created", "subscriber.updated"], "status": "enabled", "created_at": "2023-01-20 14:10:30", "updated_at": "2023-01-20 14:10:30"}}'
                        ],
                    },
                ),
                types.Tool(
                    name="create_webhook",
                    description="Create a new webhook for event notifications",
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the newly created webhook",
                        "examples": [
                            '{"data": {"id": 54321, "name": "New Webhook", "url": "https://example.com/new-webhook", "events": ["subscriber.created"], "status": "enabled", "created_at": "2023-04-25 16:45:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Details of the updated webhook",
                        "examples": [
                            '{"data": {"id": 54321, "name": "Updated Webhook", "url": "https://example.com/updated-webhook", "events": ["subscriber.created", "subscriber.deleted"], "status": "enabled", "created_at": "2023-01-20 14:10:30", "updated_at": "2023-04-25 17:30:00"}}'
                        ],
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
                    outputSchema={
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Result of the delete operation",
                        "examples": ['{"success": true}'],
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

                # Helper function to handle array responses
                def process_response(response):
                    # Check if response contains an array of items in data field
                    if "data" in response and isinstance(response["data"], list):
                        return [
                            TextContent(
                                type="text",
                                text=json.dumps(item),
                            )
                            for item in response["data"]
                        ]
                    # Handle non-array responses
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                # Subscriber Management
                if name == "list_all_subscribers":
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status", "active")
                    response = client.subscribers.list(
                        limit=limit, filter={"status": filter_status}
                    )
                    return process_response(response)

                elif name == "create_subscriber":
                    email = arguments.get("email")
                    fields = arguments.get("fields", {})
                    response = client.subscribers.create(email, fields=fields)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "update_subscriber":
                    email = arguments.get("email")
                    fields = arguments.get("fields", {})
                    response = client.subscribers.update(email, fields=fields)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "get_subscriber":
                    email = arguments.get("email")
                    response = client.subscribers.get(email)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_subscriber":
                    subscriber_id = arguments.get("subscriber_id")
                    response = client.subscribers.delete(subscriber_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                # Group Management
                elif name == "list_groups":
                    limit = arguments.get("limit", 10)
                    filter_name = arguments.get("filter", {}).get("name")
                    sort = arguments.get("sort", "name")
                    response = client.groups.list(
                        limit=limit, filter={"name": filter_name}, sort=sort
                    )
                    return process_response(response)

                elif name == "create_group":
                    group_name = arguments.get("group_name")
                    response = client.groups.create(group_name)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "update_group":
                    group_id = arguments.get("group_id")
                    group_name = arguments.get("group_name")
                    response = client.groups.update(group_id, group_name)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_group":
                    group_id = arguments.get("group_id")
                    response = client.groups.delete(group_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "get_group_subscribers":
                    group_id = arguments.get("group_id")
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status", "active")
                    response = client.groups.get_group_subscribers(
                        group_id, limit=limit, filter={"status": filter_status}
                    )
                    return process_response(response)

                elif name == "assign_subscriber_to_group":
                    subscriber_id = arguments.get("subscriber_id")
                    group_id = arguments.get("group_id")
                    response = client.subscribers.assign_subscriber_to_group(
                        subscriber_id, group_id
                    )
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
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
                            text=json.dumps(response),
                        )
                    ]

                # Field Management
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
                    return process_response(response)

                elif name == "create_field":
                    name = arguments.get("name")
                    field_type = arguments.get("type")
                    response = client.fields.create(name, field_type)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "update_field":
                    field_id = arguments.get("field_id")
                    name = arguments.get("name")
                    response = client.fields.update(field_id, name)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_field":
                    field_id = arguments.get("field_id")
                    response = client.fields.delete(field_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                # Campaign Management
                elif name == "list_campaigns":
                    limit = arguments.get("limit", 10)
                    filter_status = arguments.get("filter", {}).get("status")
                    response = client.campaigns.list(
                        limit=limit, filter={"status": filter_status}
                    )
                    return process_response(response)

                elif name == "get_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.get(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
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
                            text=json.dumps(response),
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
                            text=json.dumps(response),
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
                            text=json.dumps(response),
                        )
                    ]
                elif name == "cancel_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.cancel(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_campaign":
                    campaign_id = arguments.get("campaign_id")
                    response = client.campaigns.delete(campaign_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "list_campaign_languages":
                    response = client.campaigns.languages()
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                # Form Management
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
                    return process_response(response)

                elif name == "get_form":
                    form_id = arguments.get("form_id")
                    response = client.forms.get(form_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "update_form":
                    form_id = arguments.get("form_id")
                    name = arguments.get("name")
                    response = client.forms.update(form_id, name)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_form":
                    form_id = arguments.get("form_id")
                    response = client.forms.delete(form_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                # Webhook Management
                elif name == "list_webhooks":
                    response = client.webhooks.list()
                    return process_response(response)
                elif name == "get_webhook":
                    webhook_id = arguments.get("webhook_id")
                    response = client.webhooks.get(webhook_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
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
                            text=json.dumps(response),
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
                            text=json.dumps(response),
                        )
                    ]
                elif name == "delete_webhook":
                    webhook_id = arguments.get("webhook_id")
                    response = client.webhooks.delete(webhook_id)
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(response),
                        )
                    ]

                else:
                    raise ValueError(f"Tool {name} not found")

            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

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
