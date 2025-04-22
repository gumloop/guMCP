import os
import sys
from pathlib import Path
import logging
from typing import Dict, Any, List
import requests

from mcp.types import TextContent
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

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
            ),
            types.Tool(
                name="account_info",
                description="Get your Hunter.io account information.",
                inputSchema={"type": "object", "properties": {}},
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
            ),
            # Leads Lists Tools
            types.Tool(
                name="list_leads_lists",
                description="Get all leads lists or filter them.",
                inputSchema={"type": "object", "properties": {}},
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
            ),
            # Campaign Tools
            types.Tool(
                name="list_campaigns",
                description="List all campaigns in your account.",
                inputSchema={"type": "object", "properties": {}},
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
            return [TextContent(type="text", text="Error: Hunter.io API key not found")]

        try:
            if name == "domain_search":
                domain = arguments.get("domain")
                if not domain:
                    return [
                        TextContent(
                            type="text", text="Error: Domain parameter is required"
                        )
                    ]

                limit = arguments.get("limit")
                params = {"domain": domain, "limit": limit, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/domain-search", params=params)

                return [
                    TextContent(
                        type="text", text=f"Domain search results: {response.json()}"
                    )
                ]

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
                        text=f"Email finder results for {domain} with first name {first_name} and last name {last_name}: {response.json()}",
                    )
                ]

            elif name == "email_verifier":
                email = arguments.get("email")
                params = {"email": email, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/email-verifier", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Email verifier results for {email}: {response.json()}",
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
                        text=f"Number of email addresses for the {domain} name: {response.json()}",
                    )
                ]

            elif name == "email_enrichment":
                email = arguments.get("email")
                params = {"email": email, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}people/find", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Email enrichment results for {email}: {response.json()}",
                    )
                ]

            elif name == "company_enrichment":
                domain = arguments.get("domain")
                params = {"domain": domain, "api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/companies/find", params=params)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Company enrichment results for {domain}: {response.json()}",
                    )
                ]

            elif name == "account_info":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/account", params=params)
                return [
                    types.TextContent(
                        type="text", text=f"Account information: {response.json()}"
                    )
                ]

            elif name == "list_leads":
                params = {}

                # Add all provided arguments to params
                for key, value in arguments.items():
                    if value is not None:
                        params[key] = value
                params["api_key"] = api_key

                response = requests.get(f"{API_ENDPOINT}/leads", params=params)

                return [
                    TextContent(type="text", text=f"List of leads: {response.json()}")
                ]

            elif name == "get_lead":
                lead_id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/leads/{lead_id}", params=params
                )
                return [
                    TextContent(
                        type="text", text=f"Lead information: {response.json()}"
                    )
                ]

            elif name == "create_lead":
                params = {}

                for key, value in arguments.items():
                    if value is not None:
                        params[key] = value
                params["api_key"] = api_key
                response = requests.post(f"{API_ENDPOINT}/leads", params=params)
                return [
                    TextContent(type="text", text=f"Lead created: {response.json()}")
                ]

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
                    return [TextContent(type="text", text="Lead updated Successfully")]
                else:
                    return [
                        TextContent(
                            type="text", text=f"Lead updated Failed {response.text}"
                        )
                    ]

            elif name == "delete_lead":
                lead_id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.delete(
                    f"{API_ENDPOINT}/leads/{lead_id}", params=params
                )
                if response.status_code == 204:
                    return [TextContent(type="text", text="Lead deleted Successfully")]
                else:
                    return [
                        TextContent(
                            type="text", text=f"Lead deleted Failed {response.text}"
                        )
                    ]

            # lead lists
            elif name == "list_leads_lists":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/leads_lists", params=params)
                return [
                    TextContent(
                        type="text", text=f"List of leads lists: {response.json()}"
                    )
                ]
            elif name == "list_campaigns":
                params = {"api_key": api_key}
                response = requests.get(f"{API_ENDPOINT}/campaigns", params=params)
                return [
                    TextContent(
                        type="text", text=f"List of campaigns: {response.json()}"
                    )
                ]
            elif name == "get_leads_list":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/leads_lists/{id}", params=params
                )
                return [TextContent(type="text", text=f"Leads list: {response.json()}")]
            elif name == "create_leads_list":
                name_list = arguments.get("name")
                params = {"name": name_list, "api_key": api_key}
                response = requests.post(f"{API_ENDPOINT}/leads_lists", params=params)
                return [
                    TextContent(
                        type="text", text=f"Leads list created: {response.json()}"
                    )
                ]
            elif name == "update_leads_list":
                id = arguments.get("id")
                name_list = arguments.get("name")
                params = {"name": name_list, "api_key": api_key}
                response = requests.put(
                    f"{API_ENDPOINT}/leads_lists/{id}", params=params
                )
                if response.status_code == 204:
                    return [
                        TextContent(type="text", text="Leads list Updated Successfully")
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Leads list Updated Failed {response.text}",
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
                        TextContent(type="text", text="Leads list deleted Successfully")
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Leads list deleted Failed {response.text}",
                        )
                    ]
            elif name == "list_campaign_recipients":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.get(
                    f"{API_ENDPOINT}/campaigns/{id}/recipients", params=params
                )
                return [
                    TextContent(
                        type="text",
                        text=f"List of campaign recipients: {response.json()}",
                    )
                ]

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
                        text=f"Recipients added to campaign: {response.json()}",
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
                        text=f"Recipients cancelled from campaign: {response.json()}",
                    )
                ]

            elif name == "start_campaign":
                id = arguments.get("id")
                params = {"api_key": api_key}
                response = requests.post(
                    f"{API_ENDPOINT}/campaigns/{id}/start", params=params
                )
                return [
                    TextContent(
                        type="text", text=f"Campaign started: {response.json()}"
                    )
                ]

            else:
                return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return [TextContent(type="text", text=f"API request failed: {str(e)}")]
        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

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
