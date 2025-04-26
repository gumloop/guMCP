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
        """List HubSpot contact and company lists as resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        # Get access token
        access_token = await get_hubspot_access_token(
            server.user_id, api_key=server.api_key
        )

        resources = []

        # API endpoint for listing contact lists
        contact_lists_url = "https://api.hubapi.com/contacts/v1/lists"

        contact_params = {
            "count": 10,  # Reduced to accommodate both types
        }

        if cursor and cursor.startswith("contact_"):
            contact_params["offset"] = cursor.replace("contact_", "")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        contact_response = requests.get(
            contact_lists_url, headers=headers, params=contact_params
        )

        if contact_response.status_code == 200:
            contact_data = contact_response.json()
            contact_lists = contact_data.get("lists", [])

            for list_item in contact_lists:
                list_id = list_item.get("listId")
                name = list_item.get("name", f"Contact List {list_id}")
                dynamic = list_item.get("dynamic", False)
                list_type = "Dynamic" if dynamic else "Static"

                resource = Resource(
                    uri=f"hubspot://contact_list/{list_id}",
                    mimeType="application/json",
                    name=f"Contact: {name} ({list_type})",
                )
                resources.append(resource)

            contact_next_cursor = contact_data.get("offset")
        else:
            logger.error(f"Error fetching contact lists: {contact_response.text}")
            contact_next_cursor = None

        # Determine next cursor for pagination
        if contact_next_cursor:
            # Prioritize contact lists pagination
            next_cursor = f"contact_{contact_next_cursor}"
        else:
            next_cursor = None

        if next_cursor:
            # The next function call would include this cursor
            pass

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a HubSpot list by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        # Parse list ID and type from URI
        uri_str = str(uri)

        # Handle contact lists
        if uri_str.startswith("hubspot://contact_list/"):
            list_id = uri_str.replace("hubspot://contact_list/", "")
            list_type = "contact"
        else:
            return []

        # Get access token
        access_token = await get_hubspot_access_token(
            server.user_id, api_key=server.api_key
        )

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        if list_type == "contact":
            # API endpoint for getting a contact list
            list_url = f"https://api.hubapi.com/contacts/v1/lists/{list_id}"
            members_url = (
                f"https://api.hubapi.com/contacts/v1/lists/{list_id}/contacts/all"
            )

            params = {
                "count": 20,
            }

        # Get list details
        response = requests.get(list_url, headers=headers)

        if response.status_code != 200:
            logger.error(f"Error fetching {list_type} list: {response.text}")
            return []

        list_data = response.json()

        # Get members in the list
        members_response = requests.get(members_url, headers=headers, params=params)

        if members_response.status_code == 200:
            members_data = members_response.json()
            if list_type == "contact":
                list_data["contacts"] = members_data.get("contacts", [])
        else:
            if list_type == "contact":
                list_data["contacts"] = []
            logger.error(
                f"Error fetching {list_type} list members: {members_response.text}"
            )

        return [
            ReadResourceContents(content=str(list_data), mime_type="application/json")
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

        if name == "list_contacts":
            # Get contact properties to return
            if arguments and "properties" in arguments and arguments["properties"]:
                # Use the properties specified in the request
                properties_to_fetch = arguments["properties"]
            else:
                # Get all available properties
                properties_to_fetch = await get_contact_properties(access_token)
                # Limit to essential properties if the list is too large
                if len(properties_to_fetch) > 20:
                    properties_to_fetch = [
                        "firstname",
                        "lastname",
                        "email",
                        "phone",
                        "company",
                        "website",
                        "jobtitle",
                        "address",
                        "city",
                        "state",
                        "zip",
                        "country",
                    ]

            # API endpoint for listing contacts
            url = "https://api.hubapi.com/crm/v3/objects/contacts"

            # Extract parameters
            query = arguments.get("query", "") if arguments else ""
            limit = min(
                arguments.get("limit", 10) if arguments else 10, 50
            )  # Cap at 50

            params = {
                "limit": limit,
                "properties": properties_to_fetch,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # If a search query is provided, use the search endpoint instead
            if query:
                url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "email",
                                    "operator": "CONTAINS_TOKEN",
                                    "value": query,
                                }
                            ]
                        }
                    ],
                    "limit": limit,
                    "properties": properties_to_fetch,
                }
                response = requests.post(url, headers=headers, json=payload)
            else:
                response = requests.get(url, headers=headers, params=params)

            if response.status_code not in (200, 201):
                logger.error(f"Error listing contacts: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error listing contacts: {response.status_code} - {response.text[:500]}",
                    )
                ]

            data = response.json()
            contacts = data.get("results", [])

            if not contacts:
                return [
                    TextContent(
                        type="text",
                        text=f"No contacts found matching the criteria.",
                    )
                ]

            # Format the response
            contact_list = []
            for contact in contacts:
                props = contact.get("properties", {})

                # Create a full contact info dictionary with all properties
                contact_info = {
                    "id": contact.get("id"),
                }

                # Add all available properties
                for prop, value in props.items():
                    contact_info[prop] = value

                contact_list.append(contact_info)

            # Format response text - show basic info and some properties
            formatted_contacts = []
            for c in contact_list:
                name = f"{c.get('firstname', '')} {c.get('lastname', '')}".strip()
                if not name:
                    name = c.get("email", f"Contact {c['id']}")

                contact_str = f"- {name} (ID: {c['id']})\n"
                contact_str += f"  Email: {c.get('email', 'N/A')}\n"

                # Add other important properties if they exist
                for prop in ["phone", "company", "jobtitle", "address", "city"]:
                    if prop in c and c.get(prop):
                        contact_str += f"  {prop.capitalize()}: {c.get(prop)}\n"

                formatted_contacts.append(contact_str)

            contacts_text = "\n".join(formatted_contacts)

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(contacts)} contacts:\n\n{contacts_text}",
                )
            ]

        elif name == "create_contact":
            if not arguments or "email" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Email is required to create a contact.",
                    )
                ]

            # API endpoint for creating a contact
            url = "https://api.hubapi.com/crm/v3/objects/contacts"

            # Prepare contact properties
            properties = {}

            # Add standard properties
            standard_props = [
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
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = arguments[key]

            # Add any additional properties provided in the 'properties' object
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = value

            payload = {"properties": properties}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 201:
                logger.error(f"Error creating contact: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error creating contact: {response.status_code} - {response.text[:500]}",
                    )
                ]

            contact_data = response.json()
            contact_id = contact_data.get("id")

            return [
                TextContent(
                    type="text",
                    text=f"Contact created successfully!\nID: {contact_id}\nEmail: {arguments['email']}",
                )
            ]

        elif name == "update_contact":
            if not arguments or "contact_id" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Contact ID is required to update a contact.",
                    )
                ]

            contact_id = arguments["contact_id"]

            # API endpoint for updating a contact
            url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"

            # Prepare contact properties
            properties = {}

            # Add standard properties
            standard_props = [
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
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = arguments[key]

            # Add any additional properties provided in the 'properties' object
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = value

            # Skip update if no properties to update
            if not properties:
                return [
                    TextContent(
                        type="text",
                        text="No properties provided to update. Contact remains unchanged.",
                    )
                ]

            payload = {"properties": properties}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.patch(url, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"Error updating contact: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error updating contact: {response.status_code} - {response.text[:500]}",
                    )
                ]

            contact_data = response.json()

            # Format successful response
            updated_props = ", ".join([f"{k}" for k in properties.keys()])

            return [
                TextContent(
                    type="text",
                    text=f"Contact updated successfully!\nID: {contact_id}\nUpdated properties: {updated_props}",
                )
            ]

        elif name == "search_contacts":
            if (
                not arguments
                or "filter_property" not in arguments
                or "filter_operator" not in arguments
                or "filter_value" not in arguments
            ):
                return [
                    TextContent(
                        type="text",
                        text="Error: Missing required search parameters (filter_property, filter_operator, filter_value).",
                    )
                ]

            # Get properties to return
            if "properties" in arguments and arguments["properties"]:
                # Use the properties specified in the request
                properties_to_fetch = arguments["properties"]
            else:
                # Get all available properties
                properties_to_fetch = await get_contact_properties(access_token)
                # Limit to essential properties if the list is too large
                if len(properties_to_fetch) > 20:
                    properties_to_fetch = [
                        "firstname",
                        "lastname",
                        "email",
                        "phone",
                        "company",
                        "website",
                        "jobtitle",
                    ]

            # API endpoint for searching contacts
            url = "https://api.hubapi.com/crm/v3/objects/contacts/search"

            # Extract search parameters
            filter_property = arguments["filter_property"]
            filter_operator = arguments["filter_operator"]
            filter_value = arguments["filter_value"]
            limit = min(arguments.get("limit", 10), 50)  # Cap at 50

            # Create payload for search
            payload = {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": filter_property,
                                "operator": filter_operator,
                                "value": filter_value,
                            }
                        ]
                    }
                ],
                "limit": limit,
                "properties": properties_to_fetch,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code not in (200, 201):
                logger.error(f"Error searching contacts: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error searching contacts: {response.status_code} - {response.text[:500]}",
                    )
                ]

            data = response.json()
            contacts = data.get("results", [])

            if not contacts:
                return [
                    TextContent(
                        type="text",
                        text=f"No contacts found matching filter: {filter_property} {filter_operator} '{filter_value}'",
                    )
                ]

            # Format the response
            contact_list = []
            for contact in contacts:
                props = contact.get("properties", {})

                # Create a full contact info dictionary with all properties
                contact_info = {
                    "id": contact.get("id"),
                }

                # Add all available properties
                for prop, value in props.items():
                    contact_info[prop] = value

                contact_list.append(contact_info)

            # Format response text - show basic info and some properties
            formatted_contacts = []
            for c in contact_list:
                name = f"{c.get('firstname', '')} {c.get('lastname', '')}".strip()
                if not name:
                    name = c.get("email", f"Contact {c['id']}")

                contact_str = f"- {name} (ID: {c['id']})\n"
                contact_str += f"  Email: {c.get('email', 'N/A')}\n"

                # Add property that was searched for
                if filter_property in c:
                    contact_str += f"  {filter_property}: {c.get(filter_property)}\n"

                # Add other important properties if they exist
                for prop in ["phone", "company", "jobtitle"]:
                    if prop != filter_property and prop in c and c.get(prop):
                        contact_str += f"  {prop.capitalize()}: {c.get(prop)}\n"

                formatted_contacts.append(contact_str)

            contacts_text = "\n".join(formatted_contacts)

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(contacts)} contacts matching filter: {filter_property} {filter_operator} '{filter_value}':\n\n{contacts_text}",
                )
            ]

        elif name == "list_companies":
            # Get properties to return
            if arguments and "properties" in arguments and arguments["properties"]:
                properties_to_fetch = arguments["properties"]
            else:
                # Default company properties
                properties_to_fetch = [
                    "name",
                    "domain",
                    "description",
                    "industry",
                    "city",
                    "state",
                    "country",
                    "phone",
                ]

            # API endpoint for listing companies
            url = "https://api.hubapi.com/crm/v3/objects/companies"

            # Extract parameters
            query = arguments.get("query", "") if arguments else ""
            limit = min(
                arguments.get("limit", 10) if arguments else 10, 50
            )  # Cap at 50

            params = {
                "limit": limit,
                "properties": properties_to_fetch,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # If a search query is provided, use the search endpoint instead
            if query:
                url = "https://api.hubapi.com/crm/v3/objects/companies/search"
                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "name",
                                    "operator": "CONTAINS_TOKEN",
                                    "value": query,
                                }
                            ]
                        }
                    ],
                    "limit": limit,
                    "properties": properties_to_fetch,
                }
                response = requests.post(url, headers=headers, json=payload)
            else:
                response = requests.get(url, headers=headers, params=params)

            if response.status_code not in (200, 201):
                logger.error(f"Error listing companies: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error listing companies: {response.status_code} - {response.text[:500]}",
                    )
                ]

            data = response.json()
            companies = data.get("results", [])

            if not companies:
                return [
                    TextContent(
                        type="text", text=f"No companies found matching the criteria."
                    )
                ]

            # Format the response
            company_list = []
            for company in companies:
                props = company.get("properties", {})

                # Create a company info dictionary
                company_info = {
                    "id": company.get("id"),
                }

                # Add all available properties
                for prop, value in props.items():
                    company_info[prop] = value

                company_list.append(company_info)

            # Format response text
            formatted_companies = []
            for c in company_list:
                company_str = f"- {c.get('name', 'Unnamed')} (ID: {c['id']})\n"

                if c.get("domain"):
                    company_str += f"  Domain: {c.get('domain')}\n"

                for prop in ["industry", "city", "state", "country", "phone"]:
                    if prop in c and c.get(prop):
                        company_str += f"  {prop.capitalize()}: {c.get(prop)}\n"

                formatted_companies.append(company_str)

            companies_text = "\n".join(formatted_companies)

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(companies)} companies:\n\n{companies_text}",
                )
            ]

        elif name == "create_company":
            if not arguments or "name" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Company name is required to create a company.",
                    )
                ]

            # API endpoint for creating a company
            url = "https://api.hubapi.com/crm/v3/objects/companies"

            # Prepare company properties
            properties = {}

            # Add standard properties
            standard_props = [
                "name",
                "domain",
                "description",
                "industry",
                "city",
                "state",
                "country",
                "phone",
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = arguments[key]

            # Add any additional properties
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = value

            payload = {"properties": properties}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 201:
                logger.error(f"Error creating company: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error creating company: {response.status_code} - {response.text[:500]}",
                    )
                ]

            company_data = response.json()
            company_id = company_data.get("id")

            return [
                TextContent(
                    type="text",
                    text=f"Company created successfully!\nID: {company_id}\nName: {arguments['name']}",
                )
            ]

        elif name == "update_company":
            if not arguments or "company_id" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Company ID is required to update a company.",
                    )
                ]

            company_id = arguments["company_id"]

            # API endpoint for updating a company
            url = f"https://api.hubapi.com/crm/v3/objects/companies/{company_id}"

            # Prepare company properties
            properties = {}

            # Add standard properties
            standard_props = [
                "name",
                "domain",
                "description",
                "industry",
                "city",
                "state",
                "country",
                "phone",
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = arguments[key]

            # Add any additional properties
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = value

            # Skip update if no properties to update
            if not properties:
                return [
                    TextContent(
                        type="text",
                        text="No properties provided to update. Company remains unchanged.",
                    )
                ]

            payload = {"properties": properties}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.patch(url, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"Error updating company: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error updating company: {response.status_code} - {response.text[:500]}",
                    )
                ]

            company_data = response.json()

            # Format successful response
            updated_props = ", ".join([f"{k}" for k in properties.keys()])

            return [
                TextContent(
                    type="text",
                    text=f"Company updated successfully!\nID: {company_id}\nUpdated properties: {updated_props}",
                )
            ]

        elif name == "list_deals":
            # Get properties to return
            if arguments and "properties" in arguments and arguments["properties"]:
                properties_to_fetch = arguments["properties"]
            else:
                # Default deal properties
                properties_to_fetch = [
                    "dealname",
                    "amount",
                    "dealstage",
                    "closedate",
                    "pipeline",
                ]

            # API endpoint for listing deals
            url = "https://api.hubapi.com/crm/v3/objects/deals"

            # Extract parameters
            query = arguments.get("query", "") if arguments else ""
            limit = min(
                arguments.get("limit", 10) if arguments else 10, 50
            )  # Cap at 50

            params = {
                "limit": limit,
                "properties": properties_to_fetch,
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # If a search query is provided, use the search endpoint instead
            if query:
                url = "https://api.hubapi.com/crm/v3/objects/deals/search"
                payload = {
                    "filterGroups": [
                        {
                            "filters": [
                                {
                                    "propertyName": "dealname",
                                    "operator": "CONTAINS_TOKEN",
                                    "value": query,
                                }
                            ]
                        }
                    ],
                    "limit": limit,
                    "properties": properties_to_fetch,
                }
                response = requests.post(url, headers=headers, json=payload)
            else:
                response = requests.get(url, headers=headers, params=params)

            if response.status_code not in (200, 201):
                logger.error(f"Error listing deals: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error listing deals: {response.status_code} - {response.text[:500]}",
                    )
                ]

            data = response.json()
            deals = data.get("results", [])

            if not deals:
                return [
                    TextContent(
                        type="text", text=f"No deals found matching the criteria."
                    )
                ]

            # Format the response
            deal_list = []
            for deal in deals:
                props = deal.get("properties", {})

                # Create a deal info dictionary
                deal_info = {
                    "id": deal.get("id"),
                }

                # Add all available properties
                for prop, value in props.items():
                    deal_info[prop] = value

                deal_list.append(deal_info)

            # Format response text
            formatted_deals = []
            for d in deal_list:
                deal_str = f"- {d.get('dealname', 'Unnamed')} (ID: {d['id']})\n"

                if d.get("amount"):
                    deal_str += f"  Amount: {d.get('amount')}\n"

                for prop in ["dealstage", "closedate", "pipeline"]:
                    if prop in d and d.get(prop):
                        prop_name = prop.capitalize()
                        if prop == "dealstage":
                            prop_name = "Deal Stage"
                        elif prop == "closedate":
                            prop_name = "Close Date"
                        deal_str += f"  {prop_name}: {d.get(prop)}\n"

                formatted_deals.append(deal_str)

            deals_text = "\n".join(formatted_deals)

            return [
                TextContent(
                    type="text", text=f"Found {len(deals)} deals:\n\n{deals_text}"
                )
            ]

        elif name == "create_deal":
            if not arguments or "dealname" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Deal name is required to create a deal.",
                    )
                ]

            # API endpoint for creating a deal
            url = "https://api.hubapi.com/crm/v3/objects/deals"

            # Prepare deal properties
            properties = {}

            # Add standard properties
            standard_props = [
                "dealname",
                "amount",
                "dealstage",
                "pipeline",
                "closedate",
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = str(
                        arguments[key]
                    )  # Convert all values to strings

            # Add any additional properties
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = str(value)  # Convert all values to strings

            payload = {"properties": properties}

            # Handle associations
            associations = []

            if "contact_id" in arguments and arguments["contact_id"]:
                associations.append(
                    {
                        "to": {"id": arguments["contact_id"]},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 3,
                            }
                        ],
                    }
                )

            if "company_id" in arguments and arguments["company_id"]:
                associations.append(
                    {
                        "to": {"id": arguments["company_id"]},
                        "types": [
                            {
                                "associationCategory": "HUBSPOT_DEFINED",
                                "associationTypeId": 5,
                            }
                        ],
                    }
                )

            if associations:
                payload["associations"] = associations

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code != 201:
                logger.error(f"Error creating deal: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error creating deal: {response.status_code} - {response.text[:500]}",
                    )
                ]

            deal_data = response.json()
            deal_id = deal_data.get("id")

            # Format the response
            associated_with = ""
            if "contact_id" in arguments and arguments["contact_id"]:
                associated_with += (
                    f"\nAssociated with contact ID: {arguments['contact_id']}"
                )
            if "company_id" in arguments and arguments["company_id"]:
                associated_with += (
                    f"\nAssociated with company ID: {arguments['company_id']}"
                )

            return [
                TextContent(
                    type="text",
                    text=f"Deal created successfully!\nID: {deal_id}\nName: {arguments['dealname']}{associated_with}",
                )
            ]

        elif name == "update_deal":
            if not arguments or "deal_id" not in arguments:
                return [
                    TextContent(
                        type="text", text="Error: Deal ID is required to update a deal."
                    )
                ]

            deal_id = arguments["deal_id"]

            # API endpoint for updating a deal
            url = f"https://api.hubapi.com/crm/v3/objects/deals/{deal_id}"

            # Prepare deal properties
            properties = {}

            # Add standard properties
            standard_props = [
                "dealname",
                "amount",
                "dealstage",
                "pipeline",
                "closedate",
            ]

            for key in standard_props:
                if key in arguments and arguments[key]:
                    properties[key] = str(
                        arguments[key]
                    )  # Convert all values to strings

            # Add any additional properties
            if "properties" in arguments and isinstance(arguments["properties"], dict):
                for key, value in arguments["properties"].items():
                    if value:  # Only add non-empty values
                        properties[key] = str(value)  # Convert all values to strings

            # Skip update if no properties to update
            if not properties:
                return [
                    TextContent(
                        type="text",
                        text="No properties provided to update. Deal remains unchanged.",
                    )
                ]

            payload = {"properties": properties}

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.patch(url, headers=headers, json=payload)

            if response.status_code != 200:
                logger.error(f"Error updating deal: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error updating deal: {response.status_code} - {response.text[:500]}",
                    )
                ]

            deal_data = response.json()

            # Format successful response
            updated_props = ", ".join([f"{k}" for k in properties.keys()])

            return [
                TextContent(
                    type="text",
                    text=f"Deal updated successfully!\nID: {deal_id}\nUpdated properties: {updated_props}",
                )
            ]

        elif name == "get_engagements":
            if not arguments or "contact_id" not in arguments:
                return [
                    TextContent(
                        type="text",
                        text="Error: Contact ID is required to get engagement data.",
                    )
                ]

            contact_id = arguments["contact_id"]
            limit = min(arguments.get("limit", 10) if arguments else 10, 50)
            engagement_type = arguments.get("engagement_type", None)

            # API endpoint for associations
            url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}/associations/engagements"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                logger.error(f"Error getting engagement associations: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error getting engagement data: {response.status_code} - {response.text[:500]}",
                    )
                ]

            association_data = response.json()
            engagement_ids = []

            # Extract engagement IDs from associations
            for result in association_data.get("results", []):
                engagement_ids.append(result.get("id"))

                # Respect the limit
                if len(engagement_ids) >= limit:
                    break

            if not engagement_ids:
                return [
                    TextContent(
                        type="text",
                        text=f"No engagements found for contact ID: {contact_id}",
                    )
                ]

            # Now get the engagement details
            engagement_details = []

            for engagement_id in engagement_ids:
                # Get engagement details
                engagement_url = (
                    f"https://api.hubapi.com/crm/v3/objects/engagements/{engagement_id}"
                )
                engagement_response = requests.get(engagement_url, headers=headers)

                if engagement_response.status_code == 200:
                    engagement_data = engagement_response.json()
                    engagement_props = engagement_data.get("properties", {})

                    # Filter by engagement type if specified
                    if (
                        engagement_type
                        and engagement_props.get("type", "").upper()
                        != engagement_type.upper()
                    ):
                        continue

                    engagement_details.append(
                        {
                            "id": engagement_id,
                            "type": engagement_props.get("type", "Unknown"),
                            "title": engagement_props.get("title", ""),
                            "timestamp": engagement_props.get("timestamp", ""),
                            "hs_activity_type": engagement_props.get(
                                "hs_activity_type", ""
                            ),
                            "hs_email_subject": engagement_props.get(
                                "hs_email_subject", ""
                            ),
                            "hs_email_text": engagement_props.get("hs_email_text", ""),
                        }
                    )

            if not engagement_details:
                type_message = f" of type {engagement_type}" if engagement_type else ""
                return [
                    TextContent(
                        type="text",
                        text=f"No engagements{type_message} found for contact ID: {contact_id}",
                    )
                ]

            # Format the response
            formatted_engagements = []

            for e in engagement_details:
                engagement_str = (
                    f"- {e.get('title') or e.get('type')} (ID: {e['id']})\n"
                )
                engagement_str += f"  Type: {e.get('type')}\n"

                if e.get("timestamp"):
                    engagement_str += f"  Time: {e.get('timestamp')}\n"

                if e.get("hs_activity_type"):
                    engagement_str += f"  Activity: {e.get('hs_activity_type')}\n"

                if e.get("hs_email_subject"):
                    engagement_str += f"  Subject: {e.get('hs_email_subject')}\n"

                if e.get("hs_email_text"):
                    # Truncate email text to prevent overly long responses
                    email_text = e.get("hs_email_text")
                    if len(email_text) > 100:
                        email_text = email_text[:100] + "..."
                    engagement_str += f"  Content: {email_text}\n"

                formatted_engagements.append(engagement_str)

            engagements_text = "\n".join(formatted_engagements)

            type_filter = f" of type {engagement_type}" if engagement_type else ""
            return [
                TextContent(
                    type="text",
                    text=f"Found {len(engagement_details)} engagements{type_filter} for contact ID {contact_id}:\n\n{engagements_text}",
                )
            ]

        elif name == "send_email":
            if (
                not arguments
                or "contact_id" not in arguments
                or "subject" not in arguments
                or "body" not in arguments
            ):
                return [
                    TextContent(
                        type="text",
                        text="Error: Contact ID, subject, and body are required to send an email.",
                    )
                ]

            contact_id = arguments["contact_id"]
            subject = arguments["subject"]
            body = arguments["body"]
            from_name = arguments.get("from_name", "")

            # First get the contact email
            url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"

            params = {
                "properties": ["email", "firstname", "lastname"],
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(f"Error getting contact: {response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error getting contact email: {response.status_code} - {response.text[:500]}",
                    )
                ]

            contact_data = response.json()
            contact_properties = contact_data.get("properties", {})
            contact_email = contact_properties.get("email")

            if not contact_email:
                return [
                    TextContent(
                        type="text",
                        text=f"Error: Contact ID {contact_id} doesn't have an email address.",
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
                        "firstName": from_name,
                    },
                    "to": [{"email": contact_email}],
                    "subject": subject,
                    "text": body,
                    "html": body.replace("\n", "<br>"),  # Simple HTML conversion
                },
                "associations": {"contactIds": [contact_id]},
            }

            email_response = requests.post(
                engagement_url, headers=headers, json=engagement_data
            )

            if email_response.status_code not in (200, 201, 204):
                logger.error(f"Error sending email: {email_response.text}")
                return [
                    TextContent(
                        type="text",
                        text=f"Error sending email: {email_response.status_code} - {email_response.text[:500]}",
                    )
                ]

            # Note: This doesn't actually send the email in most HubSpot plans,
            # it just records it as an engagement. For actual sending,
            # you would need to use the HubSpot Marketing API with proper permissions.

            return [
                TextContent(
                    type="text",
                    text=f"Email recorded successfully to contact {contact_email}.\nSubject: {subject}\n\nNote: This creates an email engagement in HubSpot but may not actually send the email depending on your HubSpot plan and settings.",
                )
            ]

        else:
            return [
                TextContent(
                    type="text",
                    text=f"Unknown tool: {name}",
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
