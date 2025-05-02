import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import Optional

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    TextContent,
    ImageContent,
    EmbeddedResource,
)
from src.auth.factory import create_auth_client


SERVICE_NAME = Path(__file__).parent.name
API_BASE_URL = "https://api.apollo.io/api/v1"

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_apollo_key(user_id):
    """Authenticate with Apollo and save API key"""
    logger.info("Starting Apollo authentication for user %s...", user_id)

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Apollo API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("apollo", user_id, {"api_key": api_key})

    logger.info(
        "Apollo API key saved for user %s. You can now run the server.", user_id
    )
    return api_key


async def get_apollo_credentials(user_id, api_key=None):
    """Get Apollo API key for the specified user"""
    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("apollo", user_id)

    def handle_missing_credentials():
        error_str = f"Apollo API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logger.error(error_str)
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


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Initialize and configure the Apollo MCP server.

    Args:
        user_id (str): The user ID associated with the current session.
        api_key (str, optional): Optional API key override.

    Returns:
        Server: Configured MCP server instance with registered tools.
    """
    server = Server("apollo-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available Apollo tools.

        Returns:
            list[Tool]: List of tool definitions supported by this server.
        """
        return [
            # SEARCH TOOLS
            # Tools for searching Apollo's database and your account
            types.Tool(
                name="search_contacts",
                description="Search for contacts in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q_keywords": {
                            "type": "string",
                            "description": "Search keywords to match across contact fields",
                        },
                        "contact_stage_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The Apollo IDs for the contact stages to filter by",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "Filter by specific account ID",
                        },
                        "organization_name": {
                            "type": "string",
                            "description": "Filter by company/organization name",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Filter by first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Filter by last name",
                        },
                        "title": {
                            "type": "string",
                            "description": "Filter by job title",
                        },
                        "email": {
                            "type": "string",
                            "description": "Filter by email address",
                        },
                        "sort_by_field": {
                            "type": "string",
                            "description": "Field to sort by (e.g., contact_created_at, contact_updated_at)",
                        },
                        "sort_ascending": {
                            "type": "boolean",
                            "description": "Sort in ascending order if true, descending if false",
                        },
                        "page": {
                            "type": "integer",
                            "description": "The page number of results to retrieve",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Number of results per page",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing search results for contacts",
                    "examples": [
                        '{"contacts":[{"id":"<ID>","first_name":"Test","last_name":"User"}],"total":1}'
                    ],
                },
            ),
            types.Tool(
                name="search_accounts",
                description="Search for accounts that have been added to your team's Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q_organization_name": {
                            "type": "string",
                            "description": "Add keywords to narrow the search of the accounts in your team's Apollo account",
                        },
                        "account_stage_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The Apollo IDs for the account stages that you want to include in your search results",
                        },
                        "sort_by_field": {
                            "type": "string",
                            "description": "Sort the matching accounts by one of: account_last_activity_date, account_created_at, account_updated_at",
                        },
                        "sort_ascending": {
                            "type": "boolean",
                            "description": "Set to true to sort the matching contacts in ascending order. Defaults to false.",
                        },
                        "page": {
                            "type": "integer",
                            "description": "The page number of the Apollo data that you want to retrieve",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "The number of search results that should be returned for each page",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing search results for accounts",
                    "examples": [
                        '{"accounts":[{"id":"<ID>","name":"<Org Name>"}],"total":5}'
                    ],
                },
            ),
            # ENRICHMENT TOOLS
            # Tools for enriching data using Apollo
            types.Tool(
                name="enrich_person",
                description="Enrich data for a person using Apollo's People Enrichment API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the person",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the person",
                        },
                        "name": {
                            "type": "string",
                            "description": "The full name of the person",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the person",
                        },
                        "hashed_email": {
                            "type": "string",
                            "description": "The hashed email of the person (MD5 or SHA-256)",
                        },
                        "organization_name": {
                            "type": "string",
                            "description": "The name of the person's employer",
                        },
                        "domain": {
                            "type": "string",
                            "description": "The domain name for the person's employer",
                        },
                        "id": {
                            "type": "string",
                            "description": "The Apollo ID for the person",
                        },
                        "linkedin_url": {
                            "type": "string",
                            "description": "The URL for the person's LinkedIn profile",
                        },
                        "reveal_personal_emails": {
                            "type": "boolean",
                            "description": "Set to true to reveal personal emails",
                        },
                        "reveal_phone_number": {
                            "type": "boolean",
                            "description": "Set to true to reveal phone numbers",
                        },
                        "webhook_url": {
                            "type": "string",
                            "description": "Webhook URL for phone number verification",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing enriched person data",
                    "examples": [
                        '{"id":"<ID>","name":"John Doe","email":"john.doe@example.com","organization_name":"<Org>","linkedin_url":"<URL>"}'
                    ],
                },
            ),
            types.Tool(
                name="enrich_organization",
                description="Enrich data for a company using Apollo's Organization Enrichment API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "The domain of the company to enrich (e.g., apollo.io, microsoft.com)",
                        }
                    },
                    "required": ["domain"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing enriched organization data",
                    "examples": [
                        '{"id":"<ID>","name":"<Org>","website":"<URL>","employees":100}'
                    ],
                },
            ),
            # CONTACT MANAGEMENT TOOLS
            # Tools for managing contacts in your Apollo account
            types.Tool(
                name="create_contact",
                description="Create a new contact in Apollo",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the contact you want to create",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the contact you want to create",
                        },
                        "organization_name": {
                            "type": "string",
                            "description": "The name of the contact's employer (company)",
                        },
                        "title": {
                            "type": "string",
                            "description": "The current job title that the contact holds",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "The Apollo ID for the account to which you want to assign the contact",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the contact",
                        },
                        "website_url": {
                            "type": "string",
                            "description": "The corporate website URL for the contact's current employer",
                        },
                        "label_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Add the contact to lists within your team's Apollo account",
                        },
                        "contact_stage_id": {
                            "type": "string",
                            "description": "The Apollo ID for the contact stage to which you want to assign the contact",
                        },
                        "present_raw_address": {
                            "type": "string",
                            "description": "The personal location for the contact",
                        },
                        "direct_phone": {
                            "type": "string",
                            "description": "The primary phone number for the contact",
                        },
                        "corporate_phone": {
                            "type": "string",
                            "description": "The work/office phone number for the contact",
                        },
                        "mobile_phone": {
                            "type": "string",
                            "description": "The mobile phone number for the contact",
                        },
                        "home_phone": {
                            "type": "string",
                            "description": "The home phone number for the contact",
                        },
                        "other_phone": {
                            "type": "string",
                            "description": "An unknown type of phone number or an alternative phone number for the contact",
                        },
                    },
                    "required": ["first_name", "last_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the created contact data",
                    "examples": [
                        '{"id":"<ID>","first_name":"Test","last_name":"User","email":"test.user@testorg.com"}'
                    ],
                },
            ),
            types.Tool(
                name="update_contact",
                description="Update an existing contact in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "The Apollo ID for the contact that you want to update",
                        },
                        "first_name": {
                            "type": "string",
                            "description": "Update the contact's first name",
                        },
                        "last_name": {
                            "type": "string",
                            "description": "Update the contact's last name",
                        },
                        "organization_name": {
                            "type": "string",
                            "description": "Update the name of the contact's employer",
                        },
                        "title": {
                            "type": "string",
                            "description": "Update the contact's job title",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "Update the Apollo ID for the account associated with the contact",
                        },
                        "email": {
                            "type": "string",
                            "description": "Update the contact's email address",
                        },
                        "website_url": {
                            "type": "string",
                            "description": "Update the corporate website URL for the contact's employer",
                        },
                        "label_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Update the lists the contact belongs to",
                        },
                        "contact_stage_id": {
                            "type": "string",
                            "description": "Update the contact stage for the contact",
                        },
                        "present_raw_address": {
                            "type": "string",
                            "description": "Update the contact's personal location",
                        },
                        "direct_phone": {
                            "type": "string",
                            "description": "Update the contact's primary phone number",
                        },
                        "corporate_phone": {
                            "type": "string",
                            "description": "Update the contact's work phone number",
                        },
                        "mobile_phone": {
                            "type": "string",
                            "description": "Update the contact's mobile phone number",
                        },
                        "home_phone": {
                            "type": "string",
                            "description": "Update the contact's home phone number",
                        },
                        "other_phone": {
                            "type": "string",
                            "description": "Update an alternative phone number for the contact",
                        },
                    },
                    "required": ["contact_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the updated contact data",
                    "examples": [
                        '{"id":"<ID>","first_name":"Test","last_name":"User Updated","email":"test.user.updated@testorg.com"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_contact",
                description="Delete a contact from your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "The Apollo ID for the contact that you want to delete",
                        }
                    },
                    "required": ["contact_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings confirming contact deletion",
                    "examples": ['{"deleted":true,"id":"<ID>"}'],
                },
            ),
            types.Tool(
                name="list_contact_stages",
                description="Retrieve the IDs for available contact stages in your Apollo account",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing contact stage IDs and names",
                    "examples": [
                        '{"contact_stages":[{"id":"<ID>","name":"Stage Name"}]}'
                    ],
                },
            ),
            # ACCOUNT MANAGEMENT TOOLS
            # Tools for managing accounts in your Apollo account
            types.Tool(
                name="create_account",
                description="Add a new account to your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the account you are creating (human-readable)",
                        },
                        "domain": {
                            "type": "string",
                            "description": "The domain name for the account (e.g., apollo.io)",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "The ID for the account owner within your team's Apollo account",
                        },
                        "account_stage_id": {
                            "type": "string",
                            "description": "The Apollo ID for the account stage to assign the account to",
                        },
                        "phone": {
                            "type": "string",
                            "description": "The primary phone number for the account",
                        },
                        "raw_address": {
                            "type": "string",
                            "description": "The corporate location for the account",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the created account data",
                    "examples": [
                        '{"id":"<ID>","name":"Test Organization","domain":"testorg.com"}'
                    ],
                },
            ),
            types.Tool(
                name="update_account",
                description="Update an existing account in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "account_id": {
                            "type": "string",
                            "description": "The Apollo ID for the account that you want to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "Update the account's name",
                        },
                        "domain": {
                            "type": "string",
                            "description": "Update the domain name for the account (e.g., apollo.io)",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "The ID for the account owner within your team's Apollo account",
                        },
                        "account_stage_id": {
                            "type": "string",
                            "description": "The Apollo ID for the account stage to assign the account to",
                        },
                        "raw_address": {
                            "type": "string",
                            "description": "Update the corporate location for the account",
                        },
                        "phone": {
                            "type": "string",
                            "description": "Update the primary phone number for the account",
                        },
                    },
                    "required": ["account_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the updated account data",
                    "examples": [
                        '{"id":"<ID>","name":"Test Organization Updated","domain":"testorg-updated.com"}'
                    ],
                },
            ),
            types.Tool(
                name="list_account_stages",
                description="Retrieve the IDs for available account stages in your Apollo account",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing account stage IDs and names",
                    "examples": [
                        '{"account_stages":[{"id":"<ID>","name":"Stage Name"}]}'
                    ],
                },
            ),
            # DEAL MANAGEMENT TOOLS
            # Tools for managing deals in your Apollo account
            types.Tool(
                name="create_deal",
                description="Create a new deal for an Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the deal you are creating (human-readable)",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "The ID for the deal owner within your team's Apollo account",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "The ID for the account within your Apollo instance",
                        },
                        "amount": {
                            "type": "string",
                            "description": "The monetary value of the deal (no commas or currency symbols)",
                        },
                        "opportunity_stage_id": {
                            "type": "string",
                            "description": "The ID for the deal stage within your team's Apollo account",
                        },
                        "closed_date": {
                            "type": "string",
                            "description": "The estimated close date for the deal, formatted as YYYY-MM-DD",
                        },
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the created deal data",
                    "examples": ['{"id":"<ID>","name":"Test Deal","amount":"10000"}'],
                },
            ),
            types.Tool(
                name="update_deal",
                description="Update an existing deal in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "opportunity_id": {
                            "type": "string",
                            "description": "The ID for the deal you want to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "Update the name of the deal",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "The ID for the deal owner within your team's Apollo account",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "The ID for the account within your Apollo instance",
                        },
                        "amount": {
                            "type": "string",
                            "description": "The monetary value of the deal (no commas or currency symbols)",
                        },
                        "opportunity_stage_id": {
                            "type": "string",
                            "description": "The ID for the deal stage within your team's Apollo account",
                        },
                        "closed_date": {
                            "type": "string",
                            "description": "The estimated close date for the deal, formatted as YYYY-MM-DD",
                        },
                        "is_closed": {
                            "type": "boolean",
                            "description": "Set to true to update the status of the deal to closed",
                        },
                        "is_won": {
                            "type": "boolean",
                            "description": "Set to true to update the status of the deal to won",
                        },
                        "source": {
                            "type": "string",
                            "description": "Update the source of the deal",
                        },
                    },
                    "required": ["opportunity_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the updated deal data",
                    "examples": [
                        '{"id":"<ID>","name":"Test Deal Updated","amount":"15000"}'
                    ],
                },
            ),
            types.Tool(
                name="list_deals",
                description="List all deals in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "description": "The page number of results to retrieve",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "Number of results per page",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing deal listings",
                    "examples": ['{"deals":[{"id":"<ID>","name":"Test Deal"}]}'],
                },
            ),
            types.Tool(
                name="list_deal_stages",
                description="Retrieve information about every deal stage in your Apollo account",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing deal stage IDs and names",
                    "examples": ['{"deal_stages":[{"id":"<ID>","name":"Stage Name"}]}'],
                },
            ),
            # TASK AND USER MANAGEMENT TOOLS
            # Tools for managing tasks and users in your Apollo account
            types.Tool(
                name="create_task",
                description="Create tasks in Apollo for you and your team",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The ID for the task owner within your team's Apollo account",
                        },
                        "contact_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The Apollo IDs for the contacts that will receive the action",
                        },
                        "priority": {
                            "type": "string",
                            "description": "Priority level: high, medium, or low",
                        },
                        "due_at": {
                            "type": "string",
                            "description": "The due date and time in ISO 8601 format (e.g., 2025-02-15T08:10:30Z)",
                        },
                        "type": {
                            "type": "string",
                            "description": "Task type: call, outreach_manual_email, linkedin_step_connect, linkedin_step_message, linkedin_step_view_profile, linkedin_step_interact_post, action_item",
                        },
                        "status": {
                            "type": "string",
                            "description": "Status: scheduled, completed, or archived",
                        },
                        "note": {
                            "type": "string",
                            "description": "Description for the task (human-readable message)",
                        },
                    },
                    "required": [
                        "user_id",
                        "contact_ids",
                        "priority",
                        "due_at",
                        "type",
                        "status",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing created task data",
                    "examples": [
                        '{"tasks":[{"id":"<ID>","type":"call","status":"scheduled"}]}'
                    ],
                },
            ),
            types.Tool(
                name="list_users",
                description="Get a list of all users (teammates) in your Apollo account",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "description": "The page number of the Apollo data that you want to retrieve",
                        },
                        "per_page": {
                            "type": "integer",
                            "description": "The number of search results that should be returned for each page",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing user listings",
                    "examples": [
                        '{"users":[{"id":"<ID>","name":"Test User"}],"total":10}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Handle Apollo tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called.
            arguments (dict | None): Parameters passed to the tool.

        Returns:
            list[Union[TextContent, ImageContent, EmbeddedResource]]:
                Output content from tool execution.
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        # Get credentials
        api_key = await get_apollo_credentials(server.user_id, api_key=server.api_key)

        if not api_key:
            logger.error("Apollo API key not found. Please set your API key.")
            return [
                TextContent(
                    type="text",
                    text="Apollo API key not found. Please set your API key.",
                )
            ]

        try:
            match name:
                case "enrich_person":
                    # Call the People Enrichment endpoint
                    url = f"{API_BASE_URL}/people/match"

                    # Prepare headers - Apollo expects the API key in the X-Api-Key header
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add optional parameters if provided
                    for param in [
                        "first_name",
                        "last_name",
                        "name",
                        "email",
                        "hashed_email",
                        "organization_name",
                        "domain",
                        "id",
                        "linkedin_url",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Add boolean parameters
                    if "reveal_personal_emails" in arguments:
                        data["reveal_personal_emails"] = arguments[
                            "reveal_personal_emails"
                        ]

                    if "reveal_phone_number" in arguments:
                        data["reveal_phone_number"] = arguments["reveal_phone_number"]
                        if "webhook_url" in arguments:
                            data["webhook_url"] = arguments["webhook_url"]

                    # Log the request details (without sensitive data)
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "enrich_organization":
                    # Call the Organization Enrichment endpoint
                    url = f"{API_BASE_URL}/organizations/enrich"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Check if domain parameter is provided
                    if "domain" not in arguments:
                        error_message = "Error: The 'domain' parameter is required for organization enrichment"
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Prepare query parameters
                    params = {"domain": arguments["domain"]}

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Params: {params}")

                    # Make the API request (GET request with query parameters)
                    response = requests.get(
                        url, headers=headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "create_contact":
                    # Call the Create Contact endpoint
                    url = f"{API_BASE_URL}/contacts"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "first_name",
                        "last_name",
                        "organization_name",
                        "title",
                        "account_id",
                        "email",
                        "website_url",
                        "contact_stage_id",
                        "present_raw_address",
                        "direct_phone",
                        "corporate_phone",
                        "mobile_phone",
                        "home_phone",
                        "other_phone",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Handle array parameters
                    if "label_names" in arguments:
                        data["label_names"] = arguments["label_names"]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "update_contact":
                    # Check if contact_id parameter is provided
                    if "contact_id" not in arguments:
                        error_message = "Error: The 'contact_id' parameter is required for contact update"
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Extract contact_id from arguments
                    contact_id = arguments.pop("contact_id")

                    # Call the Update Contact endpoint
                    url = f"{API_BASE_URL}/contacts/{contact_id}"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "first_name",
                        "last_name",
                        "organization_name",
                        "title",
                        "account_id",
                        "email",
                        "website_url",
                        "contact_stage_id",
                        "present_raw_address",
                        "direct_phone",
                        "corporate_phone",
                        "mobile_phone",
                        "home_phone",
                        "other_phone",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Handle array parameters
                    if "label_names" in arguments:
                        data["label_names"] = arguments["label_names"]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.put(url, headers=headers, json=data, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "create_account":
                    # Call the Create Account endpoint
                    url = f"{API_BASE_URL}/accounts"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "name",
                        "domain",
                        "owner_id",
                        "account_stage_id",
                        "phone",
                        "raw_address",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "update_account":
                    # Check if account_id parameter is provided
                    if "account_id" not in arguments:
                        error_message = "Error: The 'account_id' parameter is required for account update"
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Extract account_id from arguments
                    account_id = arguments.pop("account_id")

                    # Call the Update Account endpoint
                    url = f"{API_BASE_URL}/accounts/{account_id}"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "name",
                        "domain",
                        "owner_id",
                        "account_stage_id",
                        "raw_address",
                        "phone",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.put(url, headers=headers, json=data, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "list_account_stages":
                    # Call the List Account Stages endpoint
                    url = f"{API_BASE_URL}/account_stages"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")

                    # Make the API request
                    response = requests.get(url, headers=headers, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "create_deal":
                    # Call the Create Deal endpoint
                    url = f"{API_BASE_URL}/opportunities"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "name",
                        "owner_id",
                        "account_id",
                        "amount",
                        "opportunity_stage_id",
                        "closed_date",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "update_deal":
                    # Check if opportunity_id parameter is provided
                    if "opportunity_id" not in arguments:
                        error_message = "Error: The 'opportunity_id' parameter is required for deal update"
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Extract opportunity_id from arguments
                    opportunity_id = arguments.pop("opportunity_id")

                    # Call the Update Deal endpoint
                    url = f"{API_BASE_URL}/opportunities/{opportunity_id}"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add parameters if provided
                    for param in [
                        "name",
                        "owner_id",
                        "account_id",
                        "amount",
                        "opportunity_stage_id",
                        "closed_date",
                        "is_closed",
                        "is_won",
                        "source",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request - PATCH request per API docs
                    response = requests.patch(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "list_deals":
                    # Call the List Deals endpoint
                    url = f"{API_BASE_URL}/opportunities/search"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare query parameters
                    params = {}

                    # Add pagination parameters if provided
                    if "page" in arguments:
                        params["page"] = arguments["page"]
                    if "per_page" in arguments:
                        params["per_page"] = arguments["per_page"]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Params: {params}")

                    # Make the API request
                    response = requests.get(
                        url, headers=headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "list_deal_stages":
                    # Call the List Deal Stages endpoint
                    url = f"{API_BASE_URL}/opportunity_stages"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")

                    # Make the API request
                    response = requests.get(url, headers=headers, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "list_contact_stages":
                    # Call the List Contact Stages endpoint
                    url = f"{API_BASE_URL}/contact_stages"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")

                    # Make the API request
                    response = requests.get(url, headers=headers)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "list_users":
                    # Call the List Users endpoint
                    url = f"{API_BASE_URL}/users/search"

                    # Prepare headers - requires master API key
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare query parameters
                    params = {}

                    # Add pagination parameters if provided
                    if "page" in arguments:
                        params["page"] = arguments["page"]
                    if "per_page" in arguments:
                        params["per_page"] = arguments["per_page"]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Params: {params}")

                    # Make the API request
                    response = requests.get(
                        url, headers=headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "search_accounts":
                    # Call the Search Accounts endpoint
                    url = f"{API_BASE_URL}/accounts/search"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare query parameters
                    params = {}

                    # Add search parameters if provided
                    if "q_organization_name" in arguments:
                        params["q_organization_name"] = arguments["q_organization_name"]

                    # Add sorting parameters if provided
                    if "sort_by_field" in arguments:
                        params["sort_by_field"] = arguments["sort_by_field"]

                    if "sort_ascending" in arguments:
                        params["sort_ascending"] = arguments["sort_ascending"]

                    # Add pagination parameters if provided
                    if "page" in arguments:
                        params["page"] = arguments["page"]

                    if "per_page" in arguments:
                        params["per_page"] = arguments["per_page"]

                    # Handle array parameters
                    if "account_stage_ids" in arguments:
                        account_stage_ids = arguments["account_stage_ids"]
                        if isinstance(account_stage_ids, list):
                            for i, stage_id in enumerate(account_stage_ids):
                                params[f"account_stage_ids[{i}]"] = stage_id

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Params: {params}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This feature is not accessible to Apollo users on free plans. Please check your account permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "organization_search":
                    # Call the Organization Search endpoint
                    url = f"{API_BASE_URL}/mixed_companies/search"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add scalar parameters if provided
                    for param in ["q_organization_name", "page", "per_page"]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Handle revenue range parameters
                    if "revenue_range_min" in arguments:
                        if "revenue_range" not in data:
                            data["revenue_range"] = {}
                        data["revenue_range"]["min"] = arguments["revenue_range_min"]

                    if "revenue_range_max" in arguments:
                        if "revenue_range" not in data:
                            data["revenue_range"] = {}
                        data["revenue_range"]["max"] = arguments["revenue_range_max"]

                    # Handle array parameters
                    for param in [
                        "organization_num_employees_ranges",
                        "organization_locations",
                        "organization_not_locations",
                        "currently_using_any_of_technology_uids",
                        "q_organization_keyword_tags",
                        "organization_ids",
                    ]:
                        if param in arguments:
                            array_val = arguments[param]
                            if isinstance(array_val, list):
                                data[param] = array_val

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "people_search":
                    # Call the People Search endpoint
                    url = f"{API_BASE_URL}/mixed_people/search"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add scalar parameters if provided
                    for param in [
                        "q_keywords",
                        "include_similar_titles",
                        "page",
                        "per_page",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Handle array parameters
                    for param in [
                        "person_titles",
                        "person_locations",
                        "person_seniorities",
                        "organization_locations",
                        "q_organization_domains_list",
                        "contact_email_status",
                        "organization_ids",
                        "organization_num_employees_ranges",
                    ]:
                        if param in arguments:
                            array_val = arguments[param]
                            if isinstance(array_val, list):
                                data[param] = array_val

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "search_contacts":
                    # Call the Search Contacts endpoint
                    url = f"{API_BASE_URL}/contacts/search"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Prepare request data
                    data = {}

                    # Add search parameters if provided
                    for param in [
                        "q_keywords",
                        "account_id",
                        "organization_name",
                        "first_name",
                        "last_name",
                        "title",
                        "email",
                    ]:
                        if param in arguments:
                            data[param] = arguments[param]

                    # Add sorting parameters if provided
                    if "sort_by_field" in arguments:
                        data["sort_by_field"] = arguments["sort_by_field"]

                    if "sort_ascending" in arguments:
                        data["sort_ascending"] = arguments["sort_ascending"]

                    # Add pagination parameters if provided
                    if "page" in arguments:
                        data["page"] = arguments["page"]

                    if "per_page" in arguments:
                        data["per_page"] = arguments["per_page"]

                    # Handle array parameters
                    if "contact_stage_ids" in arguments:
                        contact_stage_ids = arguments["contact_stage_ids"]
                        if isinstance(contact_stage_ids, list):
                            data["contact_stage_ids"] = contact_stage_ids

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This feature is not accessible to Apollo users on free plans. Please check your account permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case "create_task":
                    # Call the Create Task endpoint
                    url = f"{API_BASE_URL}/tasks/bulk_create"

                    # Prepare headers
                    headers = {
                        "Cache-Control": "no-cache",
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                    }

                    # Check if required parameters are provided
                    required_params = [
                        "user_id",
                        "contact_ids",
                        "priority",
                        "due_at",
                        "type",
                        "status",
                    ]
                    missing_params = [
                        param for param in required_params if param not in arguments
                    ]

                    if missing_params:
                        error_message = f"Error: Missing required parameters: {', '.join(missing_params)}"
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Prepare request data
                    data = {}

                    # Add required parameters
                    for param in ["user_id", "priority", "due_at", "type", "status"]:
                        data[param] = arguments[param]

                    # Add contact_ids as array
                    contact_ids = arguments["contact_ids"]
                    if isinstance(contact_ids, list):
                        data["contact_ids"] = contact_ids
                    else:
                        error_message = (
                            "Error: contact_ids must be an array of string IDs"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                    # Add optional parameters if provided
                    if "note" in arguments:
                        data["note"] = arguments["note"]

                    # Log the request details
                    logger.info(f"Making request to {url}")
                    logger.info(f"Headers: {headers}")
                    logger.info(f"Data: {data}")

                    # Make the API request
                    response = requests.post(
                        url, headers=headers, json=data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        return [
                            TextContent(type="text", text=json.dumps(result, indent=2))
                        ]
                    elif response.status_code == 403:
                        error_message = "Error: 403 - This endpoint requires a master API key. Please check your API key permissions."
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]
                    else:
                        error_message = (
                            f"Error: {response.status_code} - {response.text}"
                        )
                        logger.error(error_message)
                        return [TextContent(type="text", text=error_message)]

                case _:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error calling Apollo API: {e}")
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the Apollo MCP server.

    Args:
        server_instance (Server): The server instance to describe.

    Returns:
        InitializationOptions: MCP-compatible initialization configuration.
    """
    return InitializationOptions(
        server_name="apollo-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_apollo_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
