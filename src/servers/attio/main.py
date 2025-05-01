import os
import sys
from typing import Optional, Iterable, Dict, Any
import json

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx
from urllib.parse import quote

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

from src.utils.attio.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["read", "write"]  # Attio API scopes
API_BASE_URL = "https://api.attio.com/v2"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_attio_client(user_id, api_key=None):
    """Create a configured Attio API client"""
    access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    return httpx.AsyncClient(
        base_url=API_BASE_URL,
        headers=headers,
        timeout=30.0,
    )


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("attio-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List available Attio resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        client = await create_attio_client(server.user_id, api_key=server.api_key)

        resources = []

        # List companies collection
        resources.append(
            Resource(
                uri="attio://collection/companies",
                mimeType="application/json",
                name="Companies Collection",
            )
        )

        # List contacts collection
        resources.append(
            Resource(
                uri="attio://collection/people",
                mimeType="application/json",
                name="People Collection",
            )
        )

        # List available lists
        try:
            response = await client.get("/lists")
            if response.status_code == 200:
                lists = response.json().get("data", [])
                for list_item in lists:
                    resources.append(
                        Resource(
                            uri=f"attio://list/{list_item['id']}",
                            mimeType="application/json",
                            name=f"List: {list_item['attributes']['title']}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error listing Attio lists: {e}")

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read data from Attio by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        client = await create_attio_client(server.user_id, api_key=server.api_key)
        uri_str = str(uri)

        try:
            if uri_str.startswith("attio://collection/companies"):
                # Get companies with pagination (limit to 50)
                payload = {"limit": 50, "offset": 0}
                response = await client.post(
                    "/objects/companies/records/query", json=payload
                )
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]

            elif uri_str.startswith("attio://collection/people"):
                # Get people with pagination (limit to 50)
                payload = {"limit": 50, "offset": 0}
                response = await client.post(
                    "/objects/people/records/query", json=payload
                )
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]

            elif uri_str.startswith("attio://list/"):
                list_id = uri_str.replace("attio://list/", "")
                # Get items from the list
                response = await client.get(f"/lists/{list_id}/entries")
                if response.status_code == 200:
                    return [
                        ReadResourceContents(
                            content=json.dumps(response.json(), indent=2),
                            mime_type="application/json",
                        )
                    ]

            # If we've reached here, the resource wasn't found or couldn't be read
            return [
                ReadResourceContents(
                    content=json.dumps(
                        {"error": "Resource not found or access denied"}
                    ),
                    mime_type="application/json",
                )
            ]

        except Exception as e:
            logger.error(f"Error reading Attio resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}), mime_type="application/json"
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Attio interaction"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="search_companies",
                description="Search for companies in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing a list of companies matching the search query",
                    "examples": [
                        'Found 2 companies:\n[\n  {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": "Acme Inc",\n      "domains": ["acme.com"]\n    }\n  },\n  {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": "Acme Corp",\n      "domains": ["acmecorp.com"]\n    }\n  }\n]'
                    ],
                },
            ),
            Tool(
                name="read_company",
                description="Read a specific company by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Company ID"}
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing detailed information about the requested company",
                    "examples": [
                        'Company details:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": "Acme Inc",\n      "domains": ["acme.com"],\n      "description": "Technology company"\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="create_company",
                description="Create a new company in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Company name"},
                        "domain": {"type": "string", "description": "Company domain"},
                        "attributes": {
                            "type": "object",
                            "description": "Additional attributes for the company as key-value pairs",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing the details of the newly created company",
                    "examples": [
                        'Company created successfully:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": "New Company",\n      "domains": ["newcompany.com"]\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="update_company",
                description="Update an existing company in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Company ID"},
                        "attributes": {
                            "type": "object",
                            "description": "Attributes to update as key-value pairs",
                        },
                    },
                    "required": ["id", "attributes"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing the details of the updated company",
                    "examples": [
                        'Company updated successfully:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": "Updated Company",\n      "domains": ["updatedcompany.com"],\n      "description": "Technology company"\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="search_contacts",
                description="Search for contacts in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing a list of contacts matching the search query",
                    "examples": [
                        'Found 2 contacts:\n[\n  {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": {\n        "first_name": "John",\n        "last_name": "Doe",\n        "full_name": "John Doe"\n      },\n      "email_addresses": [{\n        "email_address": "john@example.com"\n      }]\n    }\n  },\n  {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": {\n        "first_name": "Jane",\n        "last_name": "Doe",\n        "full_name": "Jane Doe"\n      },\n      "email_addresses": [{\n        "email_address": "jane@example.com"\n      }]\n    }\n  }\n]'
                    ],
                },
            ),
            Tool(
                name="read_contact",
                description="Read a specific contact by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Contact ID"}
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing detailed information about the requested contact",
                    "examples": [
                        'Contact details:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": {\n        "first_name": "John",\n        "last_name": "Doe",\n        "full_name": "John Doe"\n      },\n      "email_addresses": [{\n        "email_address": "john@example.com"\n      }],\n      "job_title": "Software Engineer"\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="create_contact",
                description="Create a new contact in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "Contact email"},
                        "first_name": {"type": "string", "description": "First name"},
                        "last_name": {"type": "string", "description": "Last name"},
                        "company_id": {
                            "type": "string",
                            "description": "Optional company ID to associate with",
                        },
                        "attributes": {
                            "type": "object",
                            "description": "Additional attributes for the contact as key-value pairs",
                        },
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing the details of the newly created contact",
                    "examples": [
                        'Contact created successfully:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": {\n        "first_name": "John",\n        "last_name": "Doe",\n        "full_name": "John Doe"\n      },\n      "email_addresses": [{\n        "email_address": "john@example.com"\n      }]\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="update_contact",
                description="Update an existing contact in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Contact ID"},
                        "attributes": {
                            "type": "object",
                            "description": "Attributes to update as key-value pairs",
                        },
                    },
                    "required": ["id", "attributes"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing the details of the updated contact",
                    "examples": [
                        'Contact updated successfully:\n{\n  "data": {\n    "id": {\n      "workspace_id": "<ID>",\n      "object_id": "<ID>",\n      "record_id": "<ID>"\n    },\n    "values": {\n      "name": {\n        "first_name": "John",\n        "last_name": "Doe",\n        "full_name": "John Doe"\n      },\n      "email_addresses": [{\n        "email_address": "john@example.com"\n      }],\n      "job_title": "Software Engineer"\n    }\n  }\n}'
                    ],
                },
            ),
            Tool(
                name="list_lists",
                description="List all available lists in Attio",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing all available lists in Attio",
                    "examples": [
                        'Available lists:\n[\n  {\n    "id": "<ID>",\n    "attributes": {\n      "title": "Prospect List",\n      "description": "List of prospective customers"\n    }\n  },\n  {\n    "id": "<ID>",\n    "attributes": {\n      "title": "Customer List",\n      "description": "List of current customers"\n    }\n  }\n]'
                    ],
                },
            ),
            Tool(
                name="read_list",
                description="Read records from a specific list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {"type": "string", "description": "List ID"},
                    },
                    "required": ["list_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing records from the specified list",
                    "examples": [
                        'List records:\n{\n  "data": [\n    {\n      "id": "<ID>",\n      "type": "company",\n      "attributes": {\n        "name": "Acme Inc",\n        "domains": ["acme.com"]\n      }\n    },\n    {\n      "id": "<ID>",\n      "type": "contact",\n      "attributes": {\n        "name": "John Doe",\n        "email": "john@example.com"\n      }\n    }\n  ]\n}'
                    ],
                },
            ),
            Tool(
                name="add_to_list",
                description="Add a record to a list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "list_id": {"type": "string", "description": "List ID"},
                        "record_id": {
                            "type": "string",
                            "description": "Record ID to add",
                        },
                        "record_type": {
                            "type": "string",
                            "description": "Type of record (company or contact)",
                            "enum": ["company", "contact"],
                        },
                    },
                    "required": ["list_id", "record_id", "record_type"],
                },
                outputSchema={
                    "type": "string",
                    "description": "JSON string containing the result of adding a record to a list",
                    "examples": [
                        'Record added to list successfully:\n{\n  "data": {\n    "id": "<ID>",\n    "record_id": "<RECORD_ID>",\n    "type": "company",\n    "list_id": "<LIST_ID>"\n  }\n}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle Attio tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if not arguments:
            arguments = {}

        client = await create_attio_client(server.user_id, api_key=server.api_key)

        try:
            # COMPANY TOOLS
            if name == "search_companies":
                if "query" not in arguments:
                    raise ValueError("Missing query parameter")

                payload = {
                    "filter": {"name": {"$contains": arguments["query"]}},
                    "limit": 50,
                }
                response = await client.post(
                    "/objects/companies/records/query", json=payload
                )

                if response.status_code == 200:
                    companies = response.json().get("data", [])
                    company_list = json.dumps(companies, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Found {len(companies)} companies:\n{company_list}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error searching companies: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "read_company":
                if "id" not in arguments:
                    raise ValueError("Missing id parameter")

                company_id = arguments["id"]
                response = await client.get(f"/objects/companies/records/{company_id}")

                if response.status_code == 200:
                    company_data = response.json()
                    formatted_data = json.dumps(company_data, indent=2)
                    return [
                        TextContent(
                            type="text", text=f"Company details:\n{formatted_data}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error reading company: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "create_company":
                if "name" not in arguments:
                    raise ValueError("Missing name parameter")

                values = {"name": arguments["name"]}

                if "domain" in arguments:
                    values["domains"] = [
                        arguments["domain"]
                    ]  # Domains should be a list

                if "attributes" in arguments:
                    # Add any additional attributes to values
                    for key, value in arguments["attributes"].items():
                        if key not in [
                            "name",
                            "domains",
                        ]:  # Skip these as they're handled above
                            values[key] = value

                payload = {"data": {"values": values}}

                response = await client.post("/objects/companies/records", json=payload)

                if response.status_code in (200, 201):
                    company_data = response.json()
                    formatted_data = json.dumps(company_data, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Company created successfully:\n{formatted_data}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error creating company: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "update_company":
                if "id" not in arguments or "attributes" not in arguments:
                    raise ValueError("Missing required parameters (id and attributes)")

                company_id = arguments["id"]
                payload = {"data": {"values": arguments["attributes"]}}

                response = await client.patch(
                    f"/objects/companies/records/{company_id}", json=payload
                )

                if response.status_code == 200:
                    company_data = response.json()
                    formatted_data = json.dumps(company_data, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Company updated successfully:\n{formatted_data}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error updating company: {response.status_code} - {response.text}",
                        )
                    ]

            # CONTACT TOOLS
            elif name == "search_contacts":
                if "query" not in arguments:
                    raise ValueError("Missing query parameter")

                payload = {
                    "filter": {
                        "$or": [
                            {"name": {"full_name": {"$contains": arguments["query"]}}},
                            {
                                "email_addresses": {
                                    "email_address": {"$contains": arguments["query"]}
                                }
                            },
                        ]
                    },
                    "limit": 50,
                }
                response = await client.post(
                    "/objects/people/records/query", json=payload
                )

                if response.status_code == 200:
                    contacts = response.json().get("data", [])
                    contact_list = json.dumps(contacts, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Found {len(contacts)} contacts:\n{contact_list}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error searching contacts: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "read_contact":
                if "id" not in arguments:
                    raise ValueError("Missing id parameter")

                contact_id = arguments["id"]
                response = await client.get(f"/contacts/{contact_id}")

                if response.status_code == 200:
                    contact_data = response.json()
                    formatted_data = json.dumps(contact_data, indent=2)
                    return [
                        TextContent(
                            type="text", text=f"Contact details:\n{formatted_data}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error reading contact: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "create_contact":
                if "email" not in arguments:
                    raise ValueError("Missing email parameter")

                values = {}

                if "email" in arguments:
                    values["email_addresses"] = [{"email_address": arguments["email"]}]

                # Handle name fields
                if "first_name" in arguments or "last_name" in arguments:
                    values["name"] = {}
                    first_name = arguments.get("first_name", "")
                    last_name = arguments.get("last_name", "")
                    values["name"]["full_name"] = f"{first_name} {last_name}".strip()
                    if first_name:
                        values["name"]["first_name"] = first_name
                    if last_name:
                        values["name"]["last_name"] = last_name

                if "company_id" in arguments:
                    values["company"] = {"id": arguments["company_id"]}

                if "attributes" in arguments:
                    values.update(arguments["attributes"])

                payload = {"data": {"values": values}}

                response = await client.post("/objects/people/records", json=payload)

                if response.status_code in (200, 201):
                    contact_data = response.json()

                    # Extract the record ID from the response
                    data = contact_data.get("data", {})
                    record_id = None

                    if isinstance(data, list) and data:
                        record_id = data[0].get("id", {}).get("record_id")
                    elif isinstance(data, dict):
                        record_id = data.get("id", {}).get("record_id")

                    formatted_data = json.dumps(contact_data, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Contact created successfully:\n{formatted_data}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error creating contact: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "update_contact":
                if "id" not in arguments or "attributes" not in arguments:
                    raise ValueError("Missing required parameters (id and attributes)")

                contact_id = arguments["id"]
                values = {}

                # Add attributes to values
                if "attributes" in arguments:
                    values.update(arguments["attributes"])

                payload = {"data": {"values": values}}

                response = await client.patch(
                    f"/objects/people/records/{contact_id}", json=payload
                )

                if response.status_code == 200:
                    contact_data = response.json()
                    formatted_data = json.dumps(contact_data, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Contact updated successfully:\n{formatted_data}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error updating contact: {response.status_code} - {response.text}",
                        )
                    ]

            # LIST TOOLS
            elif name == "list_lists":
                response = await client.get("/lists")

                if response.status_code == 200:
                    lists = response.json().get("data", [])
                    formatted_lists = json.dumps(lists, indent=2)
                    return [
                        TextContent(
                            type="text", text=f"Available lists:\n{formatted_lists}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error listing lists: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "read_list":
                if "list_id" not in arguments:
                    raise ValueError("Missing list_id parameter")

                list_id = arguments["list_id"]
                response = await client.get(f"/lists/{list_id}/entries")

                if response.status_code == 200:
                    list_data = response.json()
                    formatted_data = json.dumps(list_data, indent=2)
                    return [
                        TextContent(
                            type="text", text=f"List records:\n{formatted_data}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error reading list: {response.status_code} - {response.text}",
                        )
                    ]

            elif name == "add_to_list":
                if (
                    "list_id" not in arguments
                    or "record_id" not in arguments
                    or "record_type" not in arguments
                ):
                    raise ValueError(
                        "Missing required parameters (list_id, record_id, and record_type)"
                    )

                list_id = arguments["list_id"]
                record_id = arguments["record_id"]
                record_type = arguments["record_type"]

                if record_type not in ("company", "contact"):
                    raise ValueError(
                        "record_type must be either 'company' or 'contact'"
                    )

                payload = {"type": record_type, "id": record_id}

                response = await client.post(f"/lists/{list_id}/entries", json=payload)

                if response.status_code in (200, 201):
                    result = response.json()
                    formatted_result = json.dumps(result, indent=2)
                    return [
                        TextContent(
                            type="text",
                            text=f"Record added to list successfully:\n{formatted_result}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error adding to list: {response.status_code} - {response.text}",
                        )
                    ]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}")
            return [
                TextContent(
                    type="text", text=f"Error executing tool '{name}': {str(e)}"
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="attio-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
