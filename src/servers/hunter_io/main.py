import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional, Iterable
import requests
import json

from mcp.types import TextContent, AnyUrl, Resource
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.helper_types import ReadResourceContents

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types

from src.utils.hunter_io.util import (
    authenticate_and_save_hunter_key,
    get_hunter_credentials,
)

SERVICE_NAME = Path(__file__).parent.name
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

API_ENDPOINT = "https://api.hunter.io/v2/"


def create_server(user_id, api_key=None):
    server = Server(SERVICE_NAME)
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List leads and campaigns as resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = await get_hunter_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        if not api_key:
            logger.error("Hunter.io API key not found")
            return []

        resources = []

        try:
            # Get list of leads
            params = {"api_key": api_key}
            if cursor:
                params["continuation"] = cursor

            lead_response = requests.get(f"{API_ENDPOINT}/leads", params=params)
            lead_data = lead_response.json()

            leads = lead_data.get("data", {}).get("leads", [])

            for lead in leads:
                lead_id = lead.get("id")
                email = lead.get("email")
                first_name = lead.get("first_name", "")
                last_name = lead.get("last_name", "")
                company = lead.get("company", "")

                name = f"{first_name} {last_name}".strip()
                if not name:
                    name = email

                description = f"Lead: {name}"
                if company:
                    description += f" at {company}"

                resource = Resource(
                    uri=f"hunter_io://lead/{lead_id}",
                    mimeType="application/json",
                    name=name,
                    description=description,
                )
                resources.append(resource)

            # Get list of campaigns
            campaign_response = requests.get(f"{API_ENDPOINT}/campaigns", params=params)
            campaign_data = campaign_response.json()

            campaigns = campaign_data.get("data", {}).get("campaigns", [])

            for campaign in campaigns:
                campaign_id = campaign.get("id")
                name = campaign.get("name", "")

                resource = Resource(
                    uri=f"hunter_io://campaign/{campaign_id}",
                    mimeType="application/json",
                    name=name,
                    description=f"Campaign: {name}",
                )
                resources.append(resource)

            return resources

        except Exception as e:
            logger.error(f"Error listing Hunter.io resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a lead or campaign resource"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = await get_hunter_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        if not api_key:
            return [
                ReadResourceContents(
                    content=json.dumps({"error": "Hunter.io API key not found"}),
                    mime_type="application/json",
                )
            ]

        uri_str = str(uri)
        if not uri_str.startswith("hunter_io://"):
            raise ValueError(f"Invalid Hunter.io URI: {uri_str}")

        parts = uri_str.replace("hunter_io://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid Hunter.io URI format: {uri_str}")

        resource_type, resource_id = parts

        try:
            if resource_type == "lead":
                # Get lead details
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/leads/{resource_id}", params=params
                )

                return [
                    ReadResourceContents(
                        content=json.dumps(response.json()),
                        mime_type="application/json",
                    )
                ]

            elif resource_type == "campaign":
                # Get campaign details - first fetch campaign info
                params = {"api_key": api_key}
                campaign_response = requests.get(
                    f"{API_ENDPOINT}/campaigns", params=params
                )
                campaign_data = campaign_response.json()
                campaigns = campaign_data.get("data", {}).get("campaigns", [])

                campaign_info = next(
                    (c for c in campaigns if str(c.get("id")) == resource_id), None
                )

                # Then fetch campaign recipients
                recipients_response = requests.get(
                    f"{API_ENDPOINT}/campaigns/{resource_id}/recipients", params=params
                )
                recipients_data = recipients_response.json()

                # Combine the data
                result = {
                    "campaign": campaign_info,
                    "recipients": recipients_data.get("data", {}).get("recipients", []),
                }

                return [
                    ReadResourceContents(
                        content=json.dumps(result),
                        mime_type="application/json",
                    )
                ]

            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading Hunter.io resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Hunter.io API.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            # Core API Tools
            types.Tool(
                name="domain_search",
                description="Search all email addresses for a given domain.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain to search for email addresses",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results to return",
                            "default": 10,
                        },
                    },
                    "required": ["domain"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with domain email search results",
                    "examples": [
                        '{"data": {"domain": "example.com", "disposable": false, "emails": [{"value": "user@example.com", "type": "personal", "confidence": 90}]}}'
                    ],
                },
            ),
            types.Tool(
                name="email_finder",
                description="Find a specific email address using domain and name and full name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain to search for email",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the person",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the person",
                        },
                    },
                    "required": ["domain", "first_name", "last_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with email finder results",
                    "examples": [
                        '{"data": {"first_name": "John", "last_name": "Doe", "email": "john@example.com", "score": 90, "domain": "example.com"}}'
                    ],
                },
            ),
            types.Tool(
                name="email_verifier",
                description="Check the deliverability of a given email address.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address to verify",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with email verification results",
                    "examples": [
                        '{"data": {"status": "deliverable", "result": "deliverable", "score": 85, "email": "user@example.com", "regexp": true, "gibberish": false, "disposable": false}}'
                    ],
                },
            ),
            types.Tool(
                name="email_count",
                description="Check how many email addresses Hunter has for a given domain .",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain to count emails for",
                        }
                    },
                    "required": ["domain"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with domain email count statistics",
                    "examples": [
                        '{"data": {"total": 5, "personal_emails": 3, "generic_emails": 2, "department": {"executive": 1, "it": 1}}}'
                    ],
                },
            ),
            types.Tool(
                name="email_enrichment",
                description="Get detailed information about an email address.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address to enrich",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with detailed email information",
                    "examples": [
                        '{"data": {"email": "user@example.com", "name": {"fullName": "John Doe"}, "employment": {"domain": "example.com", "name": "Example Inc", "title": "Developer"}}}'
                    ],
                },
            ),
            types.Tool(
                name="company_enrichment",
                description="Get detailed information about a company.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The company domain to enrich",
                        },
                    },
                    "required": ["domain"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with detailed company information",
                    "examples": [
                        '{"data": {"name": "Example Inc", "domain": "example.com", "description": "Company description", "foundedYear": 2010}}'
                    ],
                },
            ),
            types.Tool(
                name="account_info",
                description="Get your Hunter.io account information.",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with account details",
                    "examples": [
                        '{"data": {"first_name": "User", "last_name": "Name", "email": "user@example.com", "plan_name": "Free", "requests": {"searches": {"used": 5, "available": 25}}}}'
                    ],
                },
            ),
            # Leads Tools
            types.Tool(
                name="list_leads",
                description="Get all leads or filter them by various criteria.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of results to return",
                        },
                        "lead_list_id": {
                            "type": "integer",
                            "description": "Filter by leads list ID",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Filter by first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Filter by last name",
                        },
                        "email": {"type": "string", "description": "Filter by email"},
                        "company": {
                            "type": "string",
                            "description": "Filter by company",
                        },
                        "phone_number": {
                            "type": "string",
                            "description": "Filter by phone number",
                        },
                        "twitter": {
                            "type": "string",
                            "description": "Filter by Twitter handle",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with individual lead. Each lead is returned as a separate TextContent object.",
                    "examples": [
                        '{"id": 12345, "email": "user@example.com", "first_name": "User", "last_name": "Name"}'
                    ],
                },
            ),
            types.Tool(
                name="get_lead",
                description="Get a specific lead by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the lead to retrieve",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with detailed lead information",
                    "examples": [
                        '{"id": 12345, "email": "user@example.com", "first_name": "User", "last_name": "Name", "company": "Example Inc"}'
                    ],
                },
            ),
            types.Tool(
                name="create_lead",
                description="Create a new lead with detailed information.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the lead",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the lead",
                        },
                        "position": {
                            "type": "string",
                            "description": "The job title of the lead",
                        },
                        "company": {
                            "type": "string",
                            "description": "The company name",
                        },
                        "company_size": {
                            "type": "integer",
                            "description": "The size of the company",
                        },
                        "confidence_score": {
                            "type": "integer",
                            "description": "Confidence score (0-100)",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "website": {
                            "type": "string",
                            "description": "The company website",
                        },
                        "country_code": {
                            "type": "string",
                            "description": "The country code (ISO 3166-1 alpha-2)",
                        },
                        "postal_code": {
                            "type": "integer",
                            "description": "The postal code",
                        },
                        "source": {
                            "type": "string",
                            "description": "The source of the lead",
                        },
                        "linkedin_url": {
                            "type": "string",
                            "description": "LinkedIn profile URL",
                        },
                        "phone_number": {
                            "type": "string",
                            "description": "Phone number",
                        },
                        "twitter": {"type": "string", "description": "Twitter handle"},
                        "leads_list_id": {
                            "type": "integer",
                            "description": "ID of the leads list to add to",
                        },
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with created lead information",
                    "examples": [
                        '{"id": 12345, "email": "user@example.com", "first_name": "User", "last_name": "Name", "created_at": "2025-01-01 00:00:00 UTC"}'
                    ],
                },
            ),
            types.Tool(
                name="update_lead",
                description="Update an existing lead by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the lead to update",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the lead",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the lead",
                        },
                        "position": {
                            "type": "string",
                            "description": "The job title of the lead",
                        },
                        "company": {
                            "type": "string",
                            "description": "The company name",
                        },
                        "company_size": {
                            "type": "integer",
                            "description": "The size of the company",
                        },
                        "confidence_score": {
                            "type": "integer",
                            "description": "Confidence score (0-100)",
                            "minimum": 0,
                            "maximum": 100,
                        },
                        "website": {
                            "type": "string",
                            "description": "The company website",
                        },
                        "country_code": {
                            "type": "string",
                            "description": "The country code (ISO 3166-1 alpha-2)",
                        },
                        "postal_code": {
                            "type": "integer",
                            "description": "The postal code",
                        },
                        "source": {
                            "type": "string",
                            "description": "The source of the lead",
                        },
                        "linkedin_url": {
                            "type": "string",
                            "description": "LinkedIn profile URL",
                        },
                        "phone_number": {
                            "type": "string",
                            "description": "Phone number",
                        },
                        "twitter": {"type": "string", "description": "Twitter handle"},
                        "leads_list_id": {
                            "type": "integer",
                            "description": "ID of the leads list to add to",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with update status",
                    "examples": [
                        '{"status": "success", "message": "Lead updated Successfully"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_lead",
                description="Delete a lead by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the lead to delete",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with deletion status",
                    "examples": [
                        '{"status": "success", "message": "Lead deleted Successfully"}'
                    ],
                },
            ),
            # Leads Lists Tools
            types.Tool(
                name="list_leads_lists",
                description="Get all leads lists or filter them.",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with individual leads list. Each leads list is returned as a separate TextContent object.",
                    "examples": [
                        '{"id": 12345, "name": "Example List", "leads_count": 10, "created_at": "2025-01-01 00:00:00 UTC"}'
                    ],
                },
            ),
            types.Tool(
                name="get_leads_list",
                description="Get a specific leads list by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the leads list to retrieve",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with leads list information",
                    "examples": [
                        '{"id": 12345, "name": "Example List", "leads_count": 10, "created_at": "2025-01-01 00:00:00 UTC", "leads": []}'
                    ],
                },
            ),
            types.Tool(
                name="create_leads_list",
                description="Create a new leads list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the leads list",
                        }
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with created leads list information",
                    "examples": [
                        '{"id": 12345, "name": "Example List", "leads_count": 0, "created_at": "2025-01-01 00:00:00 UTC"}'
                    ],
                },
            ),
            types.Tool(
                name="update_leads_list",
                description="Update a leads list by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the leads list to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "The new name of the leads list",
                        },
                    },
                    "required": ["id", "name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with update status",
                    "examples": [
                        '{"status": "success", "message": "Leads list Updated Successfully"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_leads_list",
                description="Delete a leads list by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the leads list to delete",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with deletion status",
                    "examples": [
                        '{"status": "success", "message": "Leads list deleted Successfully"}'
                    ],
                },
            ),
            # Campaign Tools
            types.Tool(
                name="list_campaigns",
                description="List all campaigns in your account.",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with individual campaign. Each campaign is returned as a separate TextContent object.",
                    "examples": [
                        '{"id": 12345, "name": "Example Campaign", "recipients_count": 10, "editable": true, "started": true}'
                    ],
                },
            ),
            types.Tool(
                name="list_campaign_recipients",
                description="List all recipients of a campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the campaign",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with individual campaign recipient. Each recipient is returned as a separate TextContent object.",
                    "examples": [
                        '{"email": "user@example.com", "first_name": "User", "sending_status": "pending", "lead_id": 12345}'
                    ],
                },
            ),
            types.Tool(
                name="add_campaign_recipients",
                description="Add recipients to a campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the campaign",
                        },
                        "emails": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of email addresses to add (max 50)",
                        },
                        "lead_ids": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Array of lead IDs to add (max 50)",
                        },
                    },
                    "required": ["id", "emails", "lead_ids"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with recipients addition status",
                    "examples": [
                        '{"data": {"recipients_added": 2, "skipped_recipients": null}}'
                    ],
                },
            ),
            types.Tool(
                name="cancel_campaign_recipients",
                description="Cancel scheduled emails to recipients in a campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the campaign",
                        },
                        "emails": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Array of email addresses to cancel (max 50)",
                        },
                    },
                    "required": ["id", "emails"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with recipients cancellation status",
                    "examples": [
                        '{"data": {"recipients_canceled": ["user@example.com"], "messages_canceled": 1}}'
                    ],
                },
            ),
            types.Tool(
                name="start_campaign",
                description="Start a campaign that is in draft state.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "description": "The ID of the campaign to start",
                        }
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON response with campaign start status",
                    "examples": [
                        '{"data": {"message": "Campaign started successfully", "recipients_count": 10}}',
                        '{"data": {"message": "Campaign already started.", "recipients_count": 3}}',
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent]:
        """
        Handle tool calls from the user, executing the appropriate Hunter.io API operations.

        Args:
            name (str): The name of the tool to execute
            arguments (Optional[Dict[str, Any]]): The arguments for the tool call

        Returns:
            List[types.TextContent]: A list of formatted text responses

        Raises:
            ValueError: If the tool name is unknown or arguments are invalid
            Exception: For any API or execution errors
        """
        logger.info(f"Calling tool: {name} with arguments: {arguments}")
        credentials = await get_hunter_credentials(
            server.user_id, SERVICE_NAME, server.api_key
        )
        api_key = credentials.get("api_key", None)
        if not api_key:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": "Hunter.io API key not found"}),
                )
            ]

        try:
            if name == "domain_search":
                domain = arguments.get("domain")
                if not domain:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": "Domain parameter is required"}),
                        )
                    ]

                limit = arguments.get("limit")
                params = {"domain": domain, "limit": limit, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/domain-search", params=params)

                return [TextContent(type="text", text=json.dumps(response.json()))]

            elif name == "email_finder":
                domain = arguments.get("domain")
                first_name = arguments.get("first_name")
                last_name = arguments.get("last_name")
                params = {
                    "domain": domain,
                    "first_name": first_name,
                    "last_name": last_name,
                    "api_key": api_key,
                }
                response = requests.get(f"{API_ENDPOINT}/email-finder", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "email_verifier":
                email = arguments.get("email")
                params = {"email": email, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/email-verifier", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "email_count":
                domain = arguments.get("domain")
                params = {
                    "domain": domain,
                }
                response = requests.get(f"{API_ENDPOINT}/email-count", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "email_enrichment":
                email = arguments.get("email")
                params = {"email": email, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}people/find", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "company_enrichment":
                domain = arguments.get("domain")
                params = {"domain": domain, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/companies/find", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "account_info":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/account", params=params)
                return [
                    types.TextContent(type="text", text=json.dumps(response.json()))
                ]

            elif name == "list_leads":
                params = {}

                # Add all provided arguments to params
                for key, value in arguments.items():
                    if value is not None:
                        params[key] = value
                params["api_key"] = api_key

                response = requests.get(f"{API_ENDPOINT}/leads", params=params)
                response_data = response.json()

                # Process leads individually if there are leads in the response
                if (
                    "data" in response_data
                    and "leads" in response_data["data"]
                    and isinstance(response_data["data"]["leads"], list)
                ):
                    leads = response_data["data"]["leads"]
                    if leads:
                        # Return each lead as a separate TextContent
                        return [
                            TextContent(type="text", text=json.dumps(lead))
                            for lead in leads
                        ]

                # Fall back to returning the full response if no leads or different format
                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "get_lead":
                lead_id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/leads/{lead_id}", params=params
                )
                return [TextContent(type="text", text=json.dumps(response.json()))]

            elif name == "create_lead":
                params = {}

                for key, value in arguments.items():
                    if value is not None:
                        params[key] = value
                params["api_key"] = api_key
                response = requests.post(f"{API_ENDPOINT}/leads", params=params)
                return [TextContent(type="text", text=json.dumps(response.json()))]

            elif name == "update_lead":
                lead_id = arguments.get("id")
                params = {}

                for key, value in arguments.items():
                    if value is not None:
                        params[key] = value
                params["api_key"] = api_key
                response = requests.put(
                    f"{API_ENDPOINT}/leads/{lead_id}", params=params
                )
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "status": "success",
                                    "message": "Lead updated Successfully",
                                }
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"status": "error", "message": response.text}
                            ),
                        )
                    ]

            elif name == "delete_lead":
                lead_id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.delete(
                    f"{API_ENDPOINT}/leads/{lead_id}", params=params
                )
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "status": "success",
                                    "message": "Lead deleted Successfully",
                                }
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"status": "error", "message": response.text}
                            ),
                        )
                    ]

            # lead lists
            elif name == "list_leads_lists":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/leads_lists", params=params)
                response_data = response.json()

                # Process leads lists individually if there are leads lists in the response
                if (
                    "data" in response_data
                    and "leads_lists" in response_data["data"]
                    and isinstance(response_data["data"]["leads_lists"], list)
                ):
                    leads_lists = response_data["data"]["leads_lists"]
                    if leads_lists:
                        # Return each leads list as a separate TextContent
                        return [
                            TextContent(type="text", text=json.dumps(leads_list))
                            for leads_list in leads_lists
                        ]

                # Fall back to returning the full response if no leads lists or different format
                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "get_leads_list":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/leads_lists/{id}", params=params
                )
                return [TextContent(type="text", text=json.dumps(response.json()))]

            elif name == "create_leads_list":
                name_list = arguments.get("name")
                params = {"name": name_list, "api_key": api_key}
                response = requests.post(f"{API_ENDPOINT}/leads_lists", params=params)
                return [TextContent(type="text", text=json.dumps(response.json()))]

            elif name == "update_leads_list":
                id = arguments.get("id")
                name_list = arguments.get("name")
                params = {"name": name_list, "api_key": api_key}
                response = requests.put(
                    f"{API_ENDPOINT}/leads_lists/{id}", params=params
                )
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "status": "success",
                                    "message": "Leads list Updated Successfully",
                                }
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"status": "error", "message": response.text}
                            ),
                        )
                    ]

            elif name == "delete_leads_list":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.delete(
                    f"{API_ENDPOINT}/leads_lists/{id}", params=params
                )
                if response.status_code == 204:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "status": "success",
                                    "message": "Leads list deleted Successfully",
                                }
                            ),
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"status": "error", "message": response.text}
                            ),
                        )
                    ]

            elif name == "list_campaigns":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/campaigns", params=params)
                response_data = response.json()

                # Process campaigns individually if there are campaigns in the response
                if (
                    "data" in response_data
                    and "campaigns" in response_data["data"]
                    and isinstance(response_data["data"]["campaigns"], list)
                ):
                    campaigns = response_data["data"]["campaigns"]
                    if campaigns:
                        # Return each campaign as a separate TextContent
                        return [
                            TextContent(type="text", text=json.dumps(campaign))
                            for campaign in campaigns
                        ]

                # Fall back to returning the full response if no campaigns or different format
                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "list_campaign_recipients":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/campaigns/{id}/recipients", params=params
                )
                response_data = response.json()

                # Process recipients individually if there are recipients in the response
                if (
                    "data" in response_data
                    and "recipients" in response_data["data"]
                    and isinstance(response_data["data"]["recipients"], list)
                ):
                    recipients = response_data["data"]["recipients"]
                    if recipients:
                        # Return each recipient as a separate TextContent
                        return [
                            TextContent(type="text", text=json.dumps(recipient))
                            for recipient in recipients
                        ]

                # Fall back to returning the full response if no recipients or different format
                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "add_campaign_recipients":
                id = arguments.get("id")
                emails = arguments.get("emails")
                lead_ids = arguments.get("lead_ids")

                params = {
                    "emails": emails,
                    "lead_ids": lead_ids,
                    "api_key": api_key,
                }

                response = requests.post(
                    f"{API_ENDPOINT}/campaigns/{id}/recipients", params=params
                )
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "cancel_campaign_recipients":
                id = arguments.get("id")
                emails = arguments.get("emails")
                params = {"emails": emails, "api_key": api_key}
                response = requests.delete(
                    f"{API_ENDPOINT}/campaigns/{id}/recipients", params=params
                )
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(response.json()),
                    )
                ]

            elif name == "start_campaign":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.post(
                    f"{API_ENDPOINT}/campaigns/{id}/start", params=params
                )
                return [TextContent(type="text", text=json.dumps(response.json()))]

            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool '{name}'"}),
                    )
                ]

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options for the server instance.
    """
    return InitializationOptions(
        server_name="hunter-io-server",
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
        authenticate_and_save_hunter_key(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
