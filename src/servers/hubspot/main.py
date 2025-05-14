import os
import sys
from typing import Optional, Iterable

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
import requests
from pathlib import Path
import json

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

from src.utils.hubspot.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "crm.objects.contacts.read",
    "crm.objects.contacts.write",
    "crm.objects.companies.read",
    "crm.objects.companies.write",
    "crm.objects.deals.read",
    "crm.objects.deals.write",
    "tickets",
    "crm.objects.line_items.read",
    "crm.objects.line_items.write",
    "crm.objects.quotes.read",
    "crm.objects.quotes.write",
    "crm.lists.read",
    "e-commerce",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_hubspot_access_token(user_id, api_key=None):
    """Create a new HubSpot API client instance for this request by getting fresh credentials"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

    # Return access token to be used in API requests
    return credentials


async def get_contact_properties(access_token):
    """Get all available contact properties from HubSpot API"""
    url = "https://api.hubapi.com/properties/v2/contacts/properties"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Extract property names
        properties = response.json()
        property_names = [prop["name"] for prop in properties]
        return property_names
    except Exception as e:
        logger.error(f"Error fetching contact properties: {str(e)}")
        # Fallback to basic properties if we can't fetch all
        return [
            "firstname",
            "lastname",
            "email",
            "phone",
            "company",
            "website",
            "address",
            "city",
            "state",
            "zip",
            "country",
            "jobtitle",
        ]


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("hubspot-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List HubSpot resources including contacts, companies, deals, etc."""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        # Get access token
        access_token = await get_hubspot_access_token(
            server.user_id, api_key=server.api_key
        )

        resources = []
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Define configuration for resource fetching
        resource_configs = [
            {
                "type": "contact",
                "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts",
                "params": {
                    "limit": 10,
                    "properties": ["firstname", "lastname", "email", "phone"],
                },
                "name_formatter": lambda props: f"{props.get('firstname', '')} {props.get('lastname', '')}".strip()
                or props.get("email", f"Contact {contact_id}"),
                "description": "HubSpot Contact Record",
            },
            {
                "type": "company",
                "endpoint": "https://api.hubapi.com/crm/v3/objects/companies",
                "params": {
                    "limit": 10,
                    "properties": ["name", "domain", "industry"],
                },
                "name_formatter": lambda props: props.get(
                    "name", f"Company {company_id}"
                ),
                "description": "HubSpot Company Record",
            },
            {
                "type": "deal",
                "endpoint": "https://api.hubapi.com/crm/v3/objects/deals",
                "params": {
                    "limit": 10,
                    "properties": ["dealname", "amount", "dealstage"],
                },
                "name_formatter": lambda props: props.get(
                    "dealname", f"Deal {deal_id}"
                ),
                "description": "HubSpot Deal Record",
            },
            {
                "type": "ticket",
                "endpoint": "https://api.hubapi.com/crm/v3/objects/tickets",
                "params": {
                    "limit": 10,
                    "properties": ["subject", "content", "hs_pipeline_stage"],
                },
                "name_formatter": lambda props: props.get(
                    "subject", f"Ticket {ticket_id}"
                ),
                "description": "HubSpot Ticket Record",
            },
            {
                "type": "product",
                "endpoint": "https://api.hubapi.com/crm/v3/objects/products",
                "params": {
                    "limit": 5,
                    "properties": ["name", "description", "price"],
                },
                "name_formatter": lambda props: props.get(
                    "name", f"Product {product_id}"
                ),
                "description": "HubSpot Product Definition",
            },
            {
                "type": "list",
                "endpoint": "https://api.hubapi.com/contacts/v1/lists",
                "params": {
                    "count": 5,
                },
                "special_handler": fetch_lists,
            },
        ]

        # Fetch resources using the configurations
        for config in resource_configs:
            try:
                if "special_handler" in config and config["special_handler"]:
                    # Use special handler for this resource type
                    results = await config["special_handler"](headers, config)
                    resources.extend(results)
                    continue

                # Standard API call for most resource types
                response = requests.get(
                    config["endpoint"], headers=headers, params=config["params"]
                )

                if response.status_code == 200:
                    data = response.json()

                    # Handle standard HubSpot API response format
                    for item in data.get("results", []):
                        item_id = item.get("id")
                        props = item.get("properties", {})

                        # Using the config's name_formatter with dynamic variables in scope
                        locals()[f"{config['type']}_id"] = item_id
                        name = config["name_formatter"](props)

                        resources.append(
                            Resource(
                                uri=f"hubspot://{config['type']}/{item_id}",
                                mimeType="application/json",
                                name=name,
                                description=config["description"],
                            )
                        )
            except Exception as e:
                logger.error(f"Error fetching {config['type']}: {str(e)}")

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a HubSpot resource by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        # Get access token
        access_token = await get_hubspot_access_token(
            server.user_id, api_key=server.api_key
        )

        # Parse URI to get resource type and ID
        uri_str = str(uri)
        if not uri_str.startswith("hubspot://"):
            return []

        parts = uri_str.replace("hubspot://", "").split("/")

        if len(parts) < 2:
            return []

        resource_type = parts[0]
        resource_id = parts[1]

        # Handle custom object which has an additional part (object type ID)
        object_type_id = None
        if resource_type == "custom_object" and len(parts) >= 3:
            object_type_id = resource_id
            resource_id = parts[2]

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Define resources config
        resource_configs = {
            "contact": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/contacts/{resource_id}",
                "params": {
                    "properties": [
                        "firstname",
                        "lastname",
                        "email",
                        "phone",
                        "company",
                        "website",
                        "address",
                        "city",
                        "state",
                        "zip",
                        "country",
                        "jobtitle",
                    ]
                },
                "associations": [
                    {
                        "type": "companies",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/contacts/{resource_id}/associations/companies",
                    }
                ],
            },
            "company": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/companies/{resource_id}",
                "params": {
                    "properties": [
                        "name",
                        "domain",
                        "description",
                        "industry",
                        "city",
                        "state",
                        "country",
                        "phone",
                        "website",
                        "numberofemployees",
                    ]
                },
                "associations": [
                    {
                        "type": "contacts",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/companies/{resource_id}/associations/contacts",
                    }
                ],
            },
            "deal": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/deals/{resource_id}",
                "params": {
                    "properties": [
                        "dealname",
                        "amount",
                        "dealstage",
                        "closedate",
                        "pipeline",
                        "description",
                    ]
                },
                "associations": [
                    {
                        "type": "contacts",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/deals/{resource_id}/associations/contacts",
                    },
                    {
                        "type": "companies",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/deals/{resource_id}/associations/companies",
                    },
                ],
            },
            "ticket": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/tickets/{resource_id}",
                "params": {
                    "properties": [
                        "subject",
                        "content",
                        "hs_pipeline_stage",
                        "hs_ticket_priority",
                        "hs_ticket_category",
                    ]
                },
                "associations": [
                    {
                        "type": "contacts",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/tickets/{resource_id}/associations/contacts",
                    }
                ],
            },
            "product": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/products/{resource_id}",
                "params": {
                    "properties": [
                        "name",
                        "description",
                        "price",
                        "hs_sku",
                        "hs_cost_of_goods_sold",
                        "hs_recurring_billing_period",
                    ]
                },
                "associations": [],
            },
            "line_item": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/line_items/{resource_id}",
                "params": {
                    "properties": ["name", "quantity", "price", "amount", "hs_sku"]
                },
                "associations": [
                    {
                        "type": "deals",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/line_items/{resource_id}/associations/deals",
                    }
                ],
            },
            "quote": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/quotes/{resource_id}",
                "params": {
                    "properties": [
                        "hs_title",
                        "hs_expiration_date",
                        "hs_status",
                        "hs_quote_amount",
                    ]
                },
                "associations": [
                    {
                        "type": "deals",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/quotes/{resource_id}/associations/deals",
                    }
                ],
            },
            "engagement": {
                "endpoint": f"https://api.hubapi.com/crm/v3/objects/engagements/{resource_id}",
                "params": {
                    "properties": [
                        "hs_activity_type",
                        "hs_timestamp",
                        "subject",
                        "hs_email_text",
                        "hs_meeting_outcome",
                        "hs_call_direction",
                        "hs_task_status",
                    ]
                },
                "associations": [
                    {
                        "type": "contacts",
                        "endpoint": f"https://api.hubapi.com/crm/v3/objects/engagements/{resource_id}/associations/contacts",
                    }
                ],
            },
            "list": {"special_handler": read_list_resource},
            "custom_object": {"special_handler": read_custom_object_resource},
        }

        try:
            # Check if this resource type has a special handler
            if (
                resource_type in resource_configs
                and "special_handler" in resource_configs[resource_type]
            ):
                return await resource_configs[resource_type]["special_handler"](
                    resource_id, object_type_id, headers
                )

            # Otherwise process standard resource types
            if resource_type in resource_configs:
                config = resource_configs[resource_type]
                response = requests.get(
                    config["endpoint"], headers=headers, params=config["params"]
                )

                if response.status_code == 200:
                    data = response.json()

                    # Get associations if any are defined
                    if config["associations"]:
                        assocs = {}

                        for assoc in config["associations"]:
                            assoc_response = requests.get(
                                assoc["endpoint"], headers=headers
                            )

                            if assoc_response.status_code == 200:
                                assocs[assoc["type"]] = assoc_response.json().get(
                                    "results", []
                                )

                        if assocs:
                            data["associations"] = assocs

                    return [
                        ReadResourceContents(
                            content=json.dumps(data, indent=2),
                            mime_type="application/json",
                        )
                    ]

            # If we reach here, resource was not found or not handled
            return [
                ReadResourceContents(
                    content=json.dumps({"error": "Resource not found"}, indent=2),
                    mime_type="application/json",
                )
            ]

        except Exception as e:
            logger.error(f"Error reading resource: {str(e)}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}, indent=2),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="list_contacts",
                description="List HubSpot contacts with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for contacts",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of contacts to return",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific contact properties to return (optional)",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing contacts",
                    "examples": [
                        '[{"total":88,"results":[{"id":"<ID1>","properties":{"email":"alice@example.com","firstname":"Alice","lastname":"Smith","company":"CompanyA"}},{"id":"<ID2>","properties":{"email":"bob@example.com","firstname":"Bob","lastname":"Jones","company":"CompanyB"}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="create_contact",
                description="Create a new HubSpot contact",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address (required)",
                        },
                        "firstname": {"type": "string", "description": "First name"},
                        "lastname": {"type": "string", "description": "Last name"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "company": {"type": "string", "description": "Company name"},
                        "website": {"type": "string", "description": "Website URL"},
                        "jobtitle": {"type": "string", "description": "Job title"},
                        "address": {"type": "string", "description": "Street address"},
                        "city": {"type": "string", "description": "City"},
                        "state": {
                            "type": "string",
                            "description": "State/province/region",
                        },
                        "zip": {"type": "string", "description": "Postal/ZIP code"},
                        "country": {"type": "string", "description": "Country"},
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the contact (key-value pairs)",
                        },
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating a contact",
                    "examples": [
                        '[{"id":"<ID>","properties":{"email":"test123@example.com","firstname":"Test","lastname":"User","company":"Test Company","jobtitle":"QA Tester"},"_status_code":201}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="update_contact",
                description="Update an existing HubSpot contact",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "HubSpot contact ID (required)",
                        },
                        "email": {"type": "string", "description": "Email address"},
                        "firstname": {"type": "string", "description": "First name"},
                        "lastname": {"type": "string", "description": "Last name"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "company": {"type": "string", "description": "Company name"},
                        "website": {"type": "string", "description": "Website URL"},
                        "jobtitle": {"type": "string", "description": "Job title"},
                        "address": {"type": "string", "description": "Street address"},
                        "city": {"type": "string", "description": "City"},
                        "state": {
                            "type": "string",
                            "description": "State/province/region",
                        },
                        "zip": {"type": "string", "description": "Postal/ZIP code"},
                        "country": {"type": "string", "description": "Country"},
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the contact (key-value pairs)",
                        },
                    },
                    "required": ["contact_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating a contact",
                    "examples": [
                        '[{"id":"<ID>","properties":{"company":"Updated Company","jobtitle":"Senior QA Engineer"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="search_contacts",
                description="Search for HubSpot contacts using advanced filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter_property": {
                            "type": "string",
                            "description": "Property to filter on (e.g., 'email', 'firstname')",
                        },
                        "filter_operator": {
                            "type": "string",
                            "description": "Filter operator (e.g., 'EQ', 'CONTAINS_TOKEN', 'GT')",
                        },
                        "filter_value": {
                            "type": "string",
                            "description": "Value to filter for",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of contacts to return",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific contact properties to return",
                        },
                    },
                    "required": ["filter_property", "filter_operator", "filter_value"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for searching contacts",
                    "examples": [
                        '[{"total":1,"results":[{"id":"<ID>","properties":{"email":"test@example.com"}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="list_companies",
                description="List HubSpot companies with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for companies",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of companies to return",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific company properties to return",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing companies",
                    "examples": [
                        '[{"results":[{"id":"<ID1>","properties":{"name":"CompanyA","domain":"companyA.com","industry":"COMPUTER_SOFTWARE"}},{"id":"<ID2>","properties":{"name":"CompanyB","domain":"companyB.com","industry":"COMPUTER_SOFTWARE"}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.companies.read"],
            ),
            Tool(
                name="create_company",
                description="Create a new HubSpot company",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Company name (required)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Company website domain",
                        },
                        "description": {
                            "type": "string",
                            "description": "Company description",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Company industry",
                        },
                        "city": {"type": "string", "description": "City"},
                        "state": {
                            "type": "string",
                            "description": "State/province/region",
                        },
                        "country": {"type": "string", "description": "Country"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the company",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating a company",
                    "examples": [
                        '[{"id":"<ID>","properties":{"name":"Test Company","domain":"testco.com","industry":"COMPUTER_SOFTWARE"},"_status_code":201}]'
                    ],
                },
                requiredScopes=["crm.objects.companies.write"],
            ),
            Tool(
                name="update_company",
                description="Update an existing HubSpot company",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "company_id": {
                            "type": "string",
                            "description": "HubSpot company ID (required)",
                        },
                        "name": {"type": "string", "description": "Company name"},
                        "domain": {
                            "type": "string",
                            "description": "Company website domain",
                        },
                        "description": {
                            "type": "string",
                            "description": "Company description",
                        },
                        "industry": {
                            "type": "string",
                            "description": "Company industry",
                        },
                        "city": {"type": "string", "description": "City"},
                        "state": {
                            "type": "string",
                            "description": "State/province/region",
                        },
                        "country": {"type": "string", "description": "Country"},
                        "phone": {"type": "string", "description": "Phone number"},
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the company",
                        },
                    },
                    "required": ["company_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating a company",
                    "examples": [
                        '[{"id":"<ID>","properties":{"description":"Updated description","industry":"COMPUTER_SOFTWARE"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.companies.write"],
            ),
            Tool(
                name="list_deals",
                description="List HubSpot deals with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for deals",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of deals to return",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific deal properties to return",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing deals",
                    "examples": [
                        '[{"results":[{"id":"<ID1>","properties":{"dealname":"Deal A","amount":"5000","dealstage":"qualified"}},{"id":"<ID2>","properties":{"dealname":"Deal B","amount":"10000","dealstage":null}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.deals.read"],
            ),
            Tool(
                name="create_deal",
                description="Create a new HubSpot deal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dealname": {
                            "type": "string",
                            "description": "Deal name (required)",
                        },
                        "amount": {"type": "number", "description": "Deal amount"},
                        "dealstage": {
                            "type": "string",
                            "description": "Deal stage (e.g., 'appointmentscheduled')",
                        },
                        "pipeline": {"type": "string", "description": "Pipeline ID"},
                        "closedate": {
                            "type": "string",
                            "description": "Expected close date (yyyy-MM-dd)",
                        },
                        "contact_id": {
                            "type": "string",
                            "description": "Associated contact ID",
                        },
                        "company_id": {
                            "type": "string",
                            "description": "Associated company ID",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the deal",
                        },
                    },
                    "required": ["dealname"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating a deal",
                    "examples": [
                        '[{"id":"<ID>","properties":{"dealname":"Test Deal","amount":5000},"_status_code":201}]'
                    ],
                },
                requiredScopes=["crm.objects.deals.write"],
            ),
            Tool(
                name="update_deal",
                description="Update an existing HubSpot deal",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "deal_id": {
                            "type": "string",
                            "description": "HubSpot deal ID (required)",
                        },
                        "dealname": {"type": "string", "description": "Deal name"},
                        "amount": {"type": "number", "description": "Deal amount"},
                        "dealstage": {
                            "type": "string",
                            "description": "Deal stage (e.g., 'appointmentscheduled')",
                        },
                        "pipeline": {"type": "string", "description": "Pipeline ID"},
                        "closedate": {
                            "type": "string",
                            "description": "Expected close date (yyyy-MM-dd)",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the deal",
                        },
                    },
                    "required": ["deal_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating a deal",
                    "examples": [
                        '[{"id":"<ID>","properties":{"amount":"7500","dealstage":"qualifiedtobuy"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.deals.write"],
            ),
            Tool(
                name="get_engagements",
                description="Get engagement data (calls, emails, meetings, etc.) for a contact",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "HubSpot contact ID",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of engagements to return",
                        },
                        "engagement_type": {
                            "type": "string",
                            "description": "Type of engagement (EMAIL, CALL, MEETING, etc.)",
                        },
                    },
                    "required": ["contact_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for getting engagements",
                    "examples": ['[{"total":0,"results":[],"_status_code":200}]'],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="send_email",
                description="Send an email to a HubSpot contact",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "HubSpot contact ID (required)",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject line (required)",
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content (required)",
                        },
                        "from_name": {"type": "string", "description": "Sender name"},
                    },
                    "required": ["contact_id", "subject", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for sending an email",
                    "examples": ['[{"_status_code":200}]'],
                },
                requiredScopes=[
                    "crm.objects.contacts.read",
                    "crm.objects.contacts.write",
                ],
            ),
            Tool(
                name="list_tickets",
                description="List HubSpot tickets with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of tickets to return",
                        },
                        "after": {
                            "type": "string",
                            "description": "Paging cursor token for retrieving the next page",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific ticket properties to return",
                        },
                        "associations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Object types to retrieve associated IDs for",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to return archived tickets",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing tickets",
                    "examples": [
                        '[{"results":[{"id":"<ID>","properties":{"subject":"Test Ticket","content":"...","hs_ticket_priority":"MEDIUM"}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="get_ticket",
                description="Get a specific HubSpot ticket by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "HubSpot ticket ID (required)",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific ticket properties to return",
                        },
                        "associations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Object types to retrieve associated IDs for",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to return archived tickets",
                        },
                    },
                    "required": ["ticket_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for getting a ticket",
                    "examples": [
                        '[{"id":"<ID>","properties":{"subject":"Test Ticket","content":"...","hs_ticket_priority":"MEDIUM"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="create_ticket",
                description="Create a new HubSpot ticket",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "Ticket subject (required)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Ticket content/description",
                        },
                        "hs_pipeline": {
                            "type": "string",
                            "description": "Ticket pipeline ID",
                        },
                        "hs_pipeline_stage": {
                            "type": "string",
                            "description": "Ticket pipeline stage",
                        },
                        "hs_ticket_priority": {
                            "type": "string",
                            "description": "Ticket priority (LOW, MEDIUM, HIGH)",
                        },
                        "hs_ticket_category": {
                            "type": "string",
                            "description": "Ticket category",
                        },
                        "contact_id": {
                            "type": "string",
                            "description": "Associated contact ID",
                        },
                        "company_id": {
                            "type": "string",
                            "description": "Associated company ID",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the ticket",
                        },
                    },
                    "required": ["subject"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating a ticket",
                    "examples": [
                        '[{"id":"<ID>","properties":{"subject":"Test Ticket","hs_ticket_priority":"MEDIUM"},"_status_code":201}]'
                    ],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="update_ticket",
                description="Update an existing HubSpot ticket",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "HubSpot ticket ID (required)",
                        },
                        "subject": {"type": "string", "description": "Ticket subject"},
                        "content": {
                            "type": "string",
                            "description": "Ticket content/description",
                        },
                        "hs_pipeline": {
                            "type": "string",
                            "description": "Ticket pipeline ID",
                        },
                        "hs_pipeline_stage": {
                            "type": "string",
                            "description": "Ticket pipeline stage",
                        },
                        "hs_ticket_priority": {
                            "type": "string",
                            "description": "Ticket priority (LOW, MEDIUM, HIGH)",
                        },
                        "hs_ticket_category": {
                            "type": "string",
                            "description": "Ticket category",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the ticket",
                        },
                    },
                    "required": ["ticket_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating a ticket",
                    "examples": [
                        '[{"id":"<ID>","properties":{"subject":"Updated Ticket","hs_ticket_priority":"HIGH"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="delete_ticket",
                description="Archive/delete a HubSpot ticket",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ticket_id": {
                            "type": "string",
                            "description": "HubSpot ticket ID (required)",
                        },
                    },
                    "required": ["ticket_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for deleting a ticket",
                    "examples": ['[{"_status_code":204}]'],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="merge_tickets",
                description="Merge two HubSpot tickets into one",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "primary_ticket_id": {
                            "type": "string",
                            "description": "Primary ticket ID that will remain after the merge (required)",
                        },
                        "secondary_ticket_id": {
                            "type": "string",
                            "description": "Secondary ticket ID that will be merged into the primary ticket (required)",
                        },
                    },
                    "required": ["primary_ticket_id", "secondary_ticket_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for merging tickets",
                    "examples": ['[{"id":"<MERGED_ID>","_status_code":200}]'],
                },
                requiredScopes=["tickets"],
            ),
            Tool(
                name="list_products",
                description="List HubSpot products with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of products to return",
                        },
                        "after": {
                            "type": "string",
                            "description": "Paging cursor token for retrieving the next page",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific product properties to return",
                        },
                        "archived": {
                            "type": "boolean",
                            "description": "Whether to return archived products",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing products",
                    "examples": [
                        '[{"results":[{"id":"<ID>","properties":{"name":"Product A","price":"99.99"}}],"_status_code":200}]'
                    ],
                },
                requiredScopes=["e-commerce"],
            ),
            Tool(
                name="get_product",
                description="Get a specific HubSpot product by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "HubSpot product ID (required)",
                        },
                        "properties": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific product properties to return",
                        },
                        "properties_with_history": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Properties to return with their history of previous values",
                        },
                    },
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for getting a product",
                    "examples": [
                        '[{"id":"<ID>","properties":{"name":"Test Product","description":null,"price":null,"hs_sku":null},"_status_code":200}]'
                    ],
                },
                requiredScopes=["e-commerce"],
            ),
            Tool(
                name="create_product",
                description="Create a new HubSpot product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Product name (required)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Product description",
                        },
                        "price": {
                            "type": "number",
                            "description": "Product price",
                        },
                        "hs_sku": {
                            "type": "string",
                            "description": "Product SKU",
                        },
                        "hs_cost_of_goods_sold": {
                            "type": "number",
                            "description": "Cost of goods sold",
                        },
                        "hs_recurring_billing_period": {
                            "type": "string",
                            "description": "Recurring billing period",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the product",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating a product",
                    "examples": [
                        '[{"id":"<ID>","properties":{"name":"Test Product","price":"99.99"},"_status_code":201}]'
                    ],
                },
                requiredScopes=["e-commerce"],
            ),
            Tool(
                name="update_product",
                description="Update an existing HubSpot product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "HubSpot product ID (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Product name",
                        },
                        "description": {
                            "type": "string",
                            "description": "Product description",
                        },
                        "price": {
                            "type": "number",
                            "description": "Product price",
                        },
                        "hs_sku": {
                            "type": "string",
                            "description": "Product SKU",
                        },
                        "hs_cost_of_goods_sold": {
                            "type": "number",
                            "description": "Cost of goods sold",
                        },
                        "hs_recurring_billing_period": {
                            "type": "string",
                            "description": "Recurring billing period",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties to set on the product",
                        },
                    },
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating a product",
                    "examples": [
                        '[{"id":"<ID>","properties":{"name":"Updated Prod","price":"129.99"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["e-commerce"],
            ),
            Tool(
                name="delete_product",
                description="Archive/delete a HubSpot product",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "HubSpot product ID (required)",
                        },
                    },
                    "required": ["product_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for deleting a product",
                    "examples": ['[{"_status_code":204}]'],
                },
                requiredScopes=["e-commerce"],
            ),
            Tool(
                name="get_engagement",
                description="Get a specific HubSpot engagement by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "engagement_id": {
                            "type": "string",
                            "description": "HubSpot engagement ID (required)",
                        },
                    },
                    "required": ["engagement_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for getting an engagement",
                    "examples": ['[{"engagement":{"id":"<ID>"},"_status_code":200}]'],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="list_engagements",
                description="List HubSpot engagements with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of engagements to return (max 250)",
                        },
                        "offset": {
                            "type": "string",
                            "description": "Paging offset for retrieving the next page",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for listing engagements",
                    "examples": [
                        '[{"results":[{"engagement":{"id":"<ID>"}}],"hasMore":true,"offset":<OFFSET>,"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="get_recent_engagements",
                description="Get recently created or updated HubSpot engagements",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Maximum number of engagements to return (max 100)",
                        },
                        "offset": {
                            "type": "string",
                            "description": "Paging offset for retrieving the next page",
                        },
                        "since": {
                            "type": "integer",
                            "description": "Unix timestamp in milliseconds to filter engagements modified after",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for getting recent engagements",
                    "examples": ['[{"total":0,"results":[],"_status_code":200}]'],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="get_call_dispositions",
                description="Get all possible dispositions for sales calls in HubSpot",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                    "description": "Array of JSON objects containing call disposition IDs and labels",
                    "examples": [
                        '[{"id":"<UUID1>","label":"Busy"},{"id":"<UUID2>","label":"Connected"}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.read"],
            ),
            Tool(
                name="create_engagement",
                description="Create a new HubSpot engagement (email, call, meeting, task, or note)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Engagement type (EMAIL, CALL, MEETING, TASK, NOTE)",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Engagement metadata (varies by type)",
                        },
                        "metadata_body": {
                            "type": "string",
                            "description": "Engagement metadata body",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "Owner ID for the engagement",
                        },
                        "timestamp": {
                            "type": "integer",
                            "description": "Time of engagement (in milliseconds)",
                        },
                        "contact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Contact IDs to associate with this engagement",
                        },
                        "company_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Company IDs to associate with this engagement",
                        },
                        "deal_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Deal IDs to associate with this engagement",
                        },
                        "ticket_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ticket IDs to associate with this engagement",
                        },
                    },
                    "required": ["type"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for creating an engagement",
                    "examples": ['[{"_status_code":200}]'],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="update_engagement",
                description="Update an existing HubSpot engagement",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "engagement_id": {
                            "type": "string",
                            "description": "HubSpot engagement ID (required)",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "Owner ID for the engagement",
                        },
                        "timestamp": {
                            "type": "integer",
                            "description": "Time of engagement (in milliseconds)",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Engagement metadata (varies by type)",
                        },
                        "metadata_body": {
                            "type": "string",
                            "description": "Engagement metadata body text",
                        },
                    },
                    "required": ["engagement_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for updating an engagement",
                    "examples": [
                        '[{"_engagement":{"id":"<ID>","bodyPreview":"Updated note"},"_status_code":200}]'
                    ],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="delete_engagement",
                description="Delete a HubSpot engagement",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "engagement_id": {
                            "type": "string",
                            "description": "HubSpot engagement ID (required)",
                        },
                    },
                    "required": ["engagement_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for deleting an engagement",
                    "examples": ['[{"_status_code":204}]'],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="merge_contacts",
                description="Merge two HubSpot contacts into one",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "primary_contact_id": {
                            "type": "string",
                            "description": "Primary contact ID that will remain after the merge (required)",
                        },
                        "secondary_contact_id": {
                            "type": "string",
                            "description": "Secondary contact ID that will be merged into the primary contact (required)",
                        },
                    },
                    "required": ["primary_contact_id", "secondary_contact_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for merging contacts",
                    "examples": ['[{"id":"<ID>","status_code":200}]'],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
            Tool(
                name="gdpr_delete_contact",
                description="Permanently delete a contact and all associated content to follow GDPR",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "The ID of the contact to permanently delete",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of the contact to permanently delete (alternative to contact_id)",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the API response for GDPR deletion of a contact",
                    "examples": ['[{"_status_code":204}]'],
                },
                requiredScopes=["crm.objects.contacts.write"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        # Get access token once for any tool that needs it
        access_token = await get_hubspot_access_token(
            server.user_id, api_key=server.api_key
        )

        arguments = arguments or {}

        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Define tool mapping
            tool_endpoints = {
                "list_contacts": {
                    "get_endpoint": lambda args: (
                        "https://api.hubapi.com/crm/v3/objects/contacts"
                        if not args.get("query")
                        else "https://api.hubapi.com/crm/v3/objects/contacts/search"
                    ),
                    "method": lambda args: "get" if not args.get("query") else "post",
                    "prepare_request": lambda args, token: {
                        "payload": (
                            {
                                "filterGroups": [
                                    {
                                        "filters": [
                                            {
                                                "propertyName": "email",
                                                "operator": "CONTAINS_TOKEN",
                                                "value": args.get("query", ""),
                                            }
                                        ]
                                    }
                                ],
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get("properties", []),
                            }
                            if args.get("query")
                            else None
                        ),
                        "params": (
                            {
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get("properties", []),
                            }
                            if not args.get("query")
                            else None
                        ),
                    },
                },
                "create_contact": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "email",
                                    "firstname",
                                    "lastname",
                                    "phone",
                                    "company",
                                    "website",
                                    "jobtitle",
                                    "address",
                                    "city",
                                    "state",
                                    "zip",
                                    "country",
                                ],
                            ),
                        }
                    },
                },
                "update_contact": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/contacts/{args.get('contact_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "email",
                                    "firstname",
                                    "lastname",
                                    "phone",
                                    "company",
                                    "website",
                                    "jobtitle",
                                    "address",
                                    "city",
                                    "state",
                                    "zip",
                                    "country",
                                ],
                            ),
                        }
                    },
                },
                "search_contacts": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts/search",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "filterGroups": [
                                {
                                    "filters": [
                                        {
                                            "propertyName": args.get("filter_property"),
                                            "operator": args.get("filter_operator"),
                                            "value": args.get("filter_value"),
                                        }
                                    ]
                                }
                            ],
                            "limit": min(args.get("limit", 10), 50),
                            "properties": args.get("properties", []),
                        }
                    },
                },
                "list_companies": {
                    "get_endpoint": lambda args: (
                        "https://api.hubapi.com/crm/v3/objects/companies"
                        if not args.get("query")
                        else "https://api.hubapi.com/crm/v3/objects/companies/search"
                    ),
                    "method": lambda args: "get" if not args.get("query") else "post",
                    "prepare_request": lambda args, token: {
                        "payload": (
                            {
                                "filterGroups": [
                                    {
                                        "filters": [
                                            {
                                                "propertyName": "name",
                                                "operator": "CONTAINS_TOKEN",
                                                "value": args.get("query", ""),
                                            }
                                        ]
                                    }
                                ],
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get(
                                    "properties",
                                    [
                                        "name",
                                        "domain",
                                        "description",
                                        "industry",
                                        "city",
                                        "state",
                                        "country",
                                        "phone",
                                    ],
                                ),
                            }
                            if args.get("query")
                            else None
                        ),
                        "params": (
                            {
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get(
                                    "properties",
                                    [
                                        "name",
                                        "domain",
                                        "description",
                                        "industry",
                                        "city",
                                        "state",
                                        "country",
                                        "phone",
                                    ],
                                ),
                            }
                            if not args.get("query")
                            else None
                        ),
                    },
                },
                "create_company": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/companies",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "name",
                                    "domain",
                                    "description",
                                    "industry",
                                    "city",
                                    "state",
                                    "country",
                                    "phone",
                                ],
                            ),
                        }
                    },
                },
                "update_company": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/companies/{args.get('company_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "name",
                                    "domain",
                                    "description",
                                    "industry",
                                    "city",
                                    "state",
                                    "country",
                                    "phone",
                                ],
                            ),
                        }
                    },
                },
                "list_deals": {
                    "get_endpoint": lambda args: (
                        "https://api.hubapi.com/crm/v3/objects/deals"
                        if not args.get("query")
                        else "https://api.hubapi.com/crm/v3/objects/deals/search"
                    ),
                    "method": lambda args: "get" if not args.get("query") else "post",
                    "prepare_request": lambda args, token: {
                        "payload": (
                            {
                                "filterGroups": [
                                    {
                                        "filters": [
                                            {
                                                "propertyName": "dealname",
                                                "operator": "CONTAINS_TOKEN",
                                                "value": args.get("query", ""),
                                            }
                                        ]
                                    }
                                ],
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get(
                                    "properties",
                                    [
                                        "dealname",
                                        "amount",
                                        "dealstage",
                                        "closedate",
                                        "pipeline",
                                    ],
                                ),
                            }
                            if args.get("query")
                            else None
                        ),
                        "params": (
                            {
                                "limit": min(args.get("limit", 10), 50),
                                "properties": args.get(
                                    "properties",
                                    [
                                        "dealname",
                                        "amount",
                                        "dealstage",
                                        "closedate",
                                        "pipeline",
                                    ],
                                ),
                            }
                            if not args.get("query")
                            else None
                        ),
                    },
                },
                "create_deal": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/deals",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": prepare_deal_payload(args)
                    },
                },
                "update_deal": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/deals/{args.get('deal_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "dealname",
                                    "amount",
                                    "dealstage",
                                    "pipeline",
                                    "closedate",
                                ],
                                convert_to_str=True,
                            ),
                        }
                    },
                },
                "get_engagements": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/contacts/{args.get('contact_id')}/associations/engagements",
                    "method": "get",
                    "custom_handler": get_engagements_handler,
                },
                "send_email": {
                    "endpoint": None,  # Special case handled separately
                    "method": None,
                    "custom_handler": send_email_handler,
                },
                "list_tickets": {
                    "get_endpoint": lambda args: "https://api.hubapi.com/crm/v3/objects/tickets",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "limit": min(args.get("limit", 10), 50),
                            "after": args.get("after"),
                            "properties": args.get("properties", []),
                            "associations": args.get("associations", []),
                            "archived": args.get("archived", False),
                        }
                    },
                },
                "get_ticket": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/tickets/{args.get('ticket_id')}",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "properties": args.get("properties", []),
                            "associations": args.get("associations", []),
                            "archived": args.get("archived", False),
                        }
                    },
                },
                "create_ticket": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/tickets",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": prepare_ticket_payload(args)
                    },
                },
                "update_ticket": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/tickets/{args.get('ticket_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "subject",
                                    "content",
                                    "hs_pipeline",
                                    "hs_pipeline_stage",
                                    "hs_ticket_priority",
                                    "hs_ticket_category",
                                ],
                            ),
                        }
                    },
                },
                "delete_ticket": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/tickets/{args.get('ticket_id')}",
                    "method": "delete",
                    "prepare_request": lambda args, token: {},
                },
                "merge_tickets": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/tickets/merge",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "primaryObjectId": args.get("primary_ticket_id"),
                            "objectIdToMerge": args.get("secondary_ticket_id"),
                        }
                    },
                },
                "list_products": {
                    "get_endpoint": lambda args: "https://api.hubapi.com/crm/v3/objects/products",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "limit": min(args.get("limit", 10), 50),
                            "after": args.get("after"),
                            "properties": args.get("properties", []),
                            "archived": args.get("archived", False),
                        }
                    },
                },
                "get_product": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/products/{args.get('product_id')}",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "properties": args.get("properties", []),
                            "propertiesWithHistory": args.get(
                                "properties_with_history", []
                            ),
                            "archived": args.get("archived", False),
                        }
                    },
                },
                "create_product": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/products",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": prepare_product_payload(args)
                    },
                },
                "update_product": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/products/{args.get('product_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "properties": prepare_properties(
                                args,
                                [
                                    "name",
                                    "description",
                                    "price",
                                    "hs_sku",
                                    "hs_cost_of_goods_sold",
                                    "hs_recurring_billing_period",
                                ],
                                convert_to_str=True,
                            ),
                        }
                    },
                },
                "delete_product": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/crm/v3/objects/products/{args.get('product_id')}",
                    "method": "delete",
                    "prepare_request": lambda args, token: {},
                },
                "get_engagement": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/engagements/v1/engagements/{args.get('engagement_id')}",
                    "method": "get",
                    "prepare_request": lambda args, token: {},
                },
                "list_engagements": {
                    "endpoint": "https://api.hubapi.com/engagements/v1/engagements/paged",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "limit": min(args.get("limit", 100), 250),
                            "offset": args.get("offset"),
                        }
                    },
                },
                "get_recent_engagements": {
                    "endpoint": "https://api.hubapi.com/engagements/v1/engagements/recent/modified",
                    "method": "get",
                    "prepare_request": lambda args, token: {
                        "params": {
                            "count": min(args.get("count", 20), 100),
                            "offset": args.get("offset"),
                            "since": args.get("since"),
                        }
                    },
                },
                "get_call_dispositions": {
                    "endpoint": "https://api.hubapi.com/calling/v1/dispositions",
                    "method": "get",
                    "prepare_request": lambda args, token: {},
                },
                "create_engagement": {
                    "endpoint": "https://api.hubapi.com/engagements/v1/engagements",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": build_engagement_payload(args)
                    },
                },
                "update_engagement": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/engagements/v1/engagements/{args.get('engagement_id')}",
                    "method": "patch",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "engagement": {},
                            "metadata": {"body": args.get("metadata_body", "")},
                        }
                    },
                },
                "delete_engagement": {
                    "get_endpoint": lambda args: f"https://api.hubapi.com/engagements/v1/engagements/{args.get('engagement_id')}",
                    "method": "delete",
                    "prepare_request": lambda args, token: {},
                },
                "merge_contacts": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts/merge",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": {
                            "primaryObjectId": args.get("primary_contact_id"),
                            "objectIdToMerge": args.get("secondary_contact_id"),
                        }
                    },
                },
                "gdpr_delete_contact": {
                    "endpoint": "https://api.hubapi.com/crm/v3/objects/contacts/gdpr-delete",
                    "method": "post",
                    "prepare_request": lambda args, token: {
                        "payload": prepare_gdpr_delete_payload(args)
                    },
                },
            }

            # Handle unknown tool
            if name not in tool_endpoints:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2),
                    )
                ]

            tool_config = tool_endpoints[name]

            # Check if tool has a custom handler
            if "custom_handler" in tool_config and tool_config["custom_handler"]:
                return await tool_config["custom_handler"](
                    arguments, headers, access_token
                )

            # Get the endpoint - either static or dynamic
            endpoint = tool_config.get("endpoint")
            if not endpoint and "get_endpoint" in tool_config:
                endpoint = tool_config["get_endpoint"](arguments)

            # Get the method - either static or dynamic
            method = tool_config.get("method")
            if callable(method):
                method = method(arguments)

            # Prepare request data
            request_data = {}
            if "prepare_request" in tool_config:
                request_data = tool_config["prepare_request"](arguments, access_token)

            # Make the request
            payload = request_data.get("payload")
            params = request_data.get("params")

            if method.lower() == "get":
                response = requests.get(endpoint, headers=headers, params=params)
            elif method.lower() == "post":
                response = requests.post(endpoint, headers=headers, json=payload)
            elif method.lower() == "patch":
                response = requests.patch(endpoint, headers=headers, json=payload)
            elif method.lower() == "delete":
                response = requests.delete(endpoint, headers=headers)
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"Unsupported HTTP method: {method}"}, indent=2
                        ),
                    )
                ]

            # Process the response
            status_code = response.status_code

            try:
                response_data = response.json()
                response_data["_status_code"] = status_code
            except:
                response_data = {"_status_code": status_code, "result": response.text}

            if 200 <= status_code < 300:
                return [
                    TextContent(type="text", text=json.dumps(response_data, indent=2))
                ]
            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "error": f"Status {status_code}",
                                "details": response_data,
                            },
                            indent=2,
                        ),
                    )
                ]

        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": f"Error using {name} tool: {str(e)}"}, indent=2
                    ),
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="hubspot-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")

# Helper functions for the tool mapping


def prepare_properties(args, standard_props, convert_to_str=False):
    """Helper to prepare properties from arguments"""
    properties = {}

    # Add standard properties
    for key in standard_props:
        if key in args and args[key]:
            properties[key] = str(args[key]) if convert_to_str else args[key]

    # Add any additional properties
    if "properties" in args and isinstance(args["properties"], dict):
        for key, value in args["properties"].items():
            if value:  # Only add non-empty values
                properties[key] = str(value) if convert_to_str else value

    return properties


def prepare_deal_payload(args):
    """Helper to prepare deal payload including associations"""
    properties = prepare_properties(
        args,
        [
            "dealname",
            "amount",
            "dealstage",
            "pipeline",
            "closedate",
        ],
        convert_to_str=True,
    )

    payload = {"properties": properties}

    # Handle associations
    associations = []
    if "contact_id" in args and args["contact_id"]:
        associations.append(
            {
                "to": {"id": args["contact_id"]},
                "types": [
                    {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}
                ],
            }
        )

    if "company_id" in args and args["company_id"]:
        associations.append(
            {
                "to": {"id": args["company_id"]},
                "types": [
                    {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 5}
                ],
            }
        )

    if associations:
        payload["associations"] = associations

    return payload


async def get_engagements_handler(args, headers, access_token):
    """Custom handler for get_engagements tool"""
    contact_id = args.get("contact_id")
    url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}/associations/engagements"

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        association_data = response.json()
        results = []

        # Extract engagement IDs from associations
        engagement_ids = []
        for result in association_data.get("results", []):
            engagement_ids.append(result.get("id"))

        # Respect the limit
        if len(engagement_ids) >= min(args.get("limit", 10), 50):
            engagement_ids = engagement_ids[: min(args.get("limit", 10), 50)]

        # Get details for each engagement
        for engagement_id in engagement_ids:
            engagement_url = (
                f"https://api.hubapi.com/crm/v3/objects/engagements/{engagement_id}"
            )
            engagement_response = requests.get(engagement_url, headers=headers)

            if engagement_response.status_code == 200:
                engagement_data = engagement_response.json()
                # Filter by engagement type if specified
                if (
                    args.get("engagement_type")
                    and engagement_data.get("properties", {}).get("type", "").upper()
                    != args.get("engagement_type").upper()
                ):
                    continue

                results.append(engagement_data)

        # Create a combined response
        combined_response = {"total": len(results), "results": results}
        return [TextContent(type="text", text=json.dumps(combined_response, indent=2))]

    # Handle error
    try:
        response_data = response.json()
        response_data["_status_code"] = response.status_code
    except:
        response_data = {"_status_code": response.status_code, "result": response.text}

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {"error": f"Status {response.status_code}", "details": response_data},
                indent=2,
            ),
        )
    ]


async def send_email_handler(args, headers, access_token):
    """Custom handler for send_email tool"""
    contact_id = args.get("contact_id")

    # First get the contact email
    url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
    params = {"properties": ["email", "firstname", "lastname"]}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        contact_data = response.json()
        contact_email = contact_data.get("properties", {}).get("email")

        if not contact_email:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Contact ID {contact_id} doesn't have an email address"
                        },
                        indent=2,
                    ),
                )
            ]

        # Create the email engagement
        engagement_url = "https://api.hubapi.com/engagements/v1/engagements"

        # Prepare the engagement data
        engagement_data = {
            "engagement": {"type": "EMAIL", "active": True},
            "metadata": {
                "from": {
                    "email": "",  # This will be filled by HubSpot
                    "firstName": args.get("from_name", ""),
                },
                "to": [{"email": contact_email}],
                "subject": args.get("subject", ""),
                "text": args.get("body", ""),
                "html": args.get("body", "").replace("\n", "<br>"),
            },
            "associations": {"contactIds": [contact_id]},
        }

        response = requests.post(engagement_url, headers=headers, json=engagement_data)

        # Process the response
        try:
            response_data = response.json()
            response_data["_status_code"] = response.status_code
        except:
            response_data = {
                "_status_code": response.status_code,
                "result": response.text,
            }

        if 200 <= response.status_code < 300:
            return [TextContent(type="text", text=json.dumps(response_data, indent=2))]
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "error": f"Status {response.status_code}",
                            "details": response_data,
                        },
                        indent=2,
                    ),
                )
            ]

    # Handle error getting contact
    try:
        response_data = response.json()
        response_data["_status_code"] = response.status_code
    except:
        response_data = {"_status_code": response.status_code, "result": response.text}

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {"error": f"Status {response.status_code}", "details": response_data},
                indent=2,
            ),
        )
    ]


async def fetch_lists(headers, config):
    """Special handler for fetching HubSpot lists"""
    results = []
    response = requests.get(
        config["endpoint"], headers=headers, params=config["params"]
    )

    if response.status_code == 200:
        data = response.json()
        for list_item in data.get("lists", []):
            list_id = list_item.get("listId")
            name = list_item.get("name", f"List {list_id}")
            dynamic = list_item.get("dynamic", False)
            list_type = "Dynamic" if dynamic else "Static"

            results.append(
                Resource(
                    uri=f"hubspot://list/{list_id}",
                    mimeType="application/json",
                    name=name,
                    description=f"HubSpot {list_type} List Definition",
                )
            )

    return results


async def read_list_resource(resource_id, object_type_id, headers):
    """Special handler for reading list resources"""
    url = f"https://api.hubapi.com/contacts/v1/lists/{resource_id}"
    list_response = requests.get(url, headers=headers)

    if list_response.status_code == 200:
        list_data = list_response.json()

        # Get list members
        members_url = (
            f"https://api.hubapi.com/contacts/v1/lists/{resource_id}/contacts/all"
        )
        members_params = {"count": 20}
        members_response = requests.get(
            members_url, headers=headers, params=members_params
        )

        if members_response.status_code == 200:
            list_data["contacts"] = members_response.json().get("contacts", [])

        return [
            ReadResourceContents(
                content=json.dumps(list_data, indent=2), mime_type="application/json"
            )
        ]

    return [
        ReadResourceContents(
            content=json.dumps({"error": "List not found"}, indent=2),
            mime_type="application/json",
        )
    ]


async def read_custom_object_resource(resource_id, object_type_id, headers):
    """Special handler for reading custom object resources"""
    url = f"https://api.hubapi.com/crm/v3/objects/{object_type_id}/{resource_id}"
    params = {"properties": "__all__"}

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        # Get schema info for context
        schema_url = f"https://api.hubapi.com/crm/v3/schemas/{object_type_id}"
        schema_response = requests.get(schema_url, headers=headers)

        if schema_response.status_code == 200:
            data["schema"] = schema_response.json()

        return [
            ReadResourceContents(
                content=json.dumps(data, indent=2), mime_type="application/json"
            )
        ]

    return [
        ReadResourceContents(
            content=json.dumps({"error": "Custom object not found"}, indent=2),
            mime_type="application/json",
        )
    ]


def prepare_ticket_payload(args):
    """Helper to prepare ticket payload including associations"""
    properties = prepare_properties(
        args,
        [
            "subject",
            "content",
            "hs_pipeline",
            "hs_pipeline_stage",
            "hs_ticket_priority",
            "hs_ticket_category",
        ],
    )

    payload = {"properties": properties}

    # Handle associations
    associations = []
    if "contact_id" in args and args["contact_id"]:
        associations.append(
            {
                "to": {"id": args["contact_id"]},
                "types": [
                    {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 16}
                ],
            }
        )

    if "company_id" in args and args["company_id"]:
        associations.append(
            {
                "to": {"id": args["company_id"]},
                "types": [
                    {"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 25}
                ],
            }
        )

    if associations:
        payload["associations"] = associations

    return payload


def prepare_product_payload(args):
    """Helper to prepare product payload"""
    properties = prepare_properties(
        args,
        [
            "name",
            "description",
            "price",
            "hs_sku",
            "hs_cost_of_goods_sold",
            "hs_recurring_billing_period",
        ],
        convert_to_str=True,
    )

    payload = {"properties": properties}

    # Handle associations if needed in the future
    return payload


def prepare_gdpr_delete_payload(args):
    """Helper to prepare GDPR delete payload"""
    payload = {}

    if args.get("contact_id"):
        payload["objectId"] = args.get("contact_id")

    if args.get("email"):
        payload["idProperty"] = "email"
        if not args.get("contact_id"):
            payload["objectId"] = args.get("email")

    return payload


def build_engagement_payload(args):
    """Helper to construct the payload for create/update engagement"""
    payload = {
        "engagement": {
            "active": True,
            "type": args.get("type"),
            "timestamp": args.get("timestamp"),
        }
    }
    if args.get("owner_id"):
        payload["engagement"]["ownerId"] = args.get("owner_id")
    # associations
    payload["associations"] = {
        "contactIds": args.get("contact_ids", []),
        "companyIds": args.get("company_ids", []),
        "dealIds": args.get("deal_ids", []),
        "ticketIds": args.get("ticket_ids", []),
    }
    # metadata body or metadata object
    if args.get("metadata_body"):
        payload["metadata"] = {"body": args.get("metadata_body")}
    elif "metadata" in args and isinstance(args.get("metadata"), dict):
        payload["metadata"] = args.get("metadata")
    return payload
