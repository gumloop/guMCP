import json
import os
from pathlib import Path
import logging
import sys
from simple_salesforce import Salesforce

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from src.utils.salesforce.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name

SCOPES = [  # Required scopes for Salesforce integration
    "api",
    "refresh_token",
]


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def get_salesforce_token(user_id, api_key=None):
    """
    This function is used to get the Salesforce access token for a specific user.

    Args:
        user_id (str): The user identifier.
        api_key (Optional[str]): Optional API key.

    Returns:
        str: The access token to authenticate with the Snowflake API.
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key)
    return token


def create_server(user_id, api_key=None):
    """
    Initializes and configures a Salesforce MCP server instance.

    Args:
        user_id (str): The unique user identifier for session context.
        api_key (Optional[str]): Optional API key for user auth context.

    Returns:
        Server: Configured server instance with all Snowflake tools registered.
    """
    server = Server("salesforce-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Lists all available tools for interacting with the Salesforce API.

        Returns:
            list[types.Tool]: A list of tool metadata with schema definitions.
        """
        logger.info(f"Listing tools for user: {user_id}")
        return [
            types.Tool(
                name="soql_query",
                description="Executes a SOQL query to retrieve Salesforce records with support for relationships and complex filters",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SOQL query to execute (e.g., 'SELECT Id, Name FROM Account WHERE Industry = \\'Technology\\'')",
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing a single Salesforce record from the SOQL query",
                    "examples": [
                        '{\n  "attributes": {\n    "type": "Account",\n    "url": "/services/data/v59.0/sobjects/Account/<ID>"\n  },\n  "Id": "<ID>",\n  "Name": "Instacart"\n}',
                        '{\n  "attributes": {\n    "type": "Account",\n    "url": "/services/data/v59.0/sobjects/Account/<ID>"\n  },\n  "Id": "<ID>",\n  "Name": "Samsara"\n}',
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="sosl_search",
                description="Performs a text-based search across multiple Salesforce objects using SOSL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "The SOSL search string (e.g., 'FIND {Cloud} IN ALL FIELDS RETURNING Account, Opportunity')",
                        },
                    },
                    "required": ["search"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing a single record from the SOSL search results",
                    "examples": [
                        '{\n  "attributes": {\n    "type": "Account",\n    "url": "/services/data/v59.0/sobjects/Account/<ID>"\n  },\n  "Id": "<ID>",\n  "Name": "Example"\n}'
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="describe_object",
                description="Retrieves detailed metadata about a Salesforce object including fields, relationships, and permissions",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact', 'Custom_Object__c')",
                        },
                    },
                    "required": ["object_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string representing the full object metadata",
                    "examples": [
                        '{\n  "fields": [{"name": "Id", "label": "Account ID", "type": "id"}],\n  "childRelationships": [],\n  "name": "Account"\n}'
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="get_record",
                description="Retrieves a specific Salesforce record by ID with all accessible fields",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific fields to retrieve (retrieves all accessible fields if not specified)",
                        },
                    },
                    "required": ["object_name", "record_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string representing the Salesforce record data",
                    "examples": [
                        '{\n  "attributes": {\n    "type": "Account",\n    "url": "/services/data/v59.0/sobjects/Account/<ID>"\n  },\n  "Id": "<ID>",\n  "Name": "Test Account"\n}'
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="create_record",
                description="Creates a new record in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "data": {
                            "type": "object",
                            "description": "Field data for the new record as key-value pairs",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["object_name", "data"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string of the create record result",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="update_record",
                description="Updates an existing Salesforce record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record to update",
                        },
                        "data": {
                            "type": "object",
                            "description": "Field data to update as key-value pairs",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["object_name", "record_id", "data"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the HTTP status code of the update operation",
                    "examples": ['{"status_code": 204}'],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="delete_record",
                description="Deletes a Salesforce record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "object_name": {
                            "type": "string",
                            "description": "The API name of the Salesforce object (e.g., 'Account', 'Contact')",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record to delete",
                        },
                    },
                    "required": ["object_name", "record_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the HTTP status code of the delete operation",
                    "examples": ['{"status_code": 204}'],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="get_org_limits",
                description="Retrieves current organization limits and usage",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit_type": {
                            "type": "string",
                            "description": "Optional specific limit to check (e.g., 'DailyApiRequests', 'DataStorageMB')",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string representing the organization limits or a specific limit type",
                    "examples": [
                        '{\n  "DailyApiRequests": {\n    "Max": 103000,\n    "Remaining": 102934\n  },\n  "DailyBulkApiBatches": {"Max": 15000, "Remaining": 15000}\n}'
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="add_contact_to_campaign",
                description="Adds an existing contact to an existing campaign",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "contact_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the contact",
                        },
                        "campaign_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the campaign",
                        },
                        "status": {
                            "type": "string",
                            "description": "The campaign member status to assign (e.g., 'Sent', 'Responded')",
                        },
                    },
                    "required": ["contact_id", "campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the campaign member creation result",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="add_file_to_record",
                description="Adds an existing file to an existing record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the ContentDocument",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the record to link the file to",
                        },
                        "share_type": {
                            "type": "string",
                            "description": "The sharing type (e.g., 'V' for Viewer, 'C' for Collaborator, 'I' for Inferred)",
                            "default": "V",
                        },
                    },
                    "required": ["file_id", "record_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the ContentDocumentLink creation result",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="add_lead_to_campaign",
                description="Adds an existing lead to an existing campaign",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the lead",
                        },
                        "campaign_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the campaign",
                        },
                        "status": {
                            "type": "string",
                            "description": "The campaign member status to assign (e.g., 'Sent', 'Responded')",
                        },
                    },
                    "required": ["lead_id", "campaign_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the campaign member creation result",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="convert_lead",
                description="Converts a lead to an account, contact, and optionally an opportunity",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "lead_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the lead to convert",
                        },
                        "account_id": {
                            "type": "string",
                            "description": "Optional account ID to use instead of creating a new account",
                        },
                        "contact_id": {
                            "type": "string",
                            "description": "Optional contact ID to use instead of creating a new contact",
                        },
                        "owner_id": {
                            "type": "string",
                            "description": "Optional user ID to assign as the owner of the resulting records",
                        },
                        "opportunity_name": {
                            "type": "string",
                            "description": "Name for the opportunity to create (if create_opportunity is true)",
                        },
                        "create_opportunity": {
                            "type": "boolean",
                            "description": "Whether to create an opportunity during conversion",
                            "default": False,
                        },
                        "converted_status": {
                            "type": "string",
                            "description": "Lead status to assign after conversion",
                        },
                        "send_notification_email": {
                            "type": "boolean",
                            "description": "Whether to send a notification email to the owner",
                            "default": False,
                        },
                    },
                    "required": ["lead_id", "converted_status"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the lead conversion result",
                    "examples": [
                        '{\n  "accountId": "<ID>",\n  "contactId": "<ID>",\n  "leadId": "<ID>",\n  "opportunityId": "<ID>",\n  "success": true\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="create_child_records",
                description="Creates child records from line items and sets the parent-child relationship",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the parent record",
                        },
                        "child_object_name": {
                            "type": "string",
                            "description": "The API name of the child Salesforce object (e.g., 'LineItem__c')",
                        },
                        "parent_field_name": {
                            "type": "string",
                            "description": "The API name of the field that links to the parent (e.g., 'Order__c')",
                        },
                        "records": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": True,
                            },
                            "description": "Array of records to create as children, each with field data as key-value pairs",
                        },
                    },
                    "required": [
                        "parent_id",
                        "child_object_name",
                        "parent_field_name",
                        "records",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing the result of creating each child record",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="create_enhanced_note",
                description="Creates a new enhanced note (ContentNote) with optional record attachment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the note",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content of the note in HTML format",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "Optional record ID to link this note to",
                        },
                        "share_type": {
                            "type": "string",
                            "description": "Optional sharing type if record_id is provided (e.g., 'V' for Viewer)",
                            "default": "V",
                        },
                    },
                    "required": ["title", "content"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the note creation result and optional link result",
                    "examples": [
                        '{\n  "note": {\n    "id": "<ID>",\n    "success": true\n  },\n  "link": {\n    "id": "<ID>",\n    "success": true\n  }\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="create_file",
                description="Creates a new file (ContentVersion) with optional record attachment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the file",
                        },
                        "path_on_client": {
                            "type": "string",
                            "description": "Filename with extension (e.g., 'document.pdf')",
                        },
                        "version_data": {
                            "type": "string",
                            "description": "Base64-encoded file content",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description of the file",
                        },
                        "record_id": {
                            "type": "string",
                            "description": "Optional record ID to link this file to",
                        },
                        "share_type": {
                            "type": "string",
                            "description": "Optional sharing type if record_id is provided (e.g., 'V' for Viewer)",
                            "default": "V",
                        },
                    },
                    "required": ["title", "path_on_client", "version_data"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the file creation result and optional link result",
                    "examples": [
                        '{\n  "file": {\n    "id": "<ID>",\n    "success": true\n  },\n  "link": {\n    "id": "<ID>",\n    "success": true\n  }\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="create_note",
                description="Creates a new note (legacy Note object) and links it to a parent record",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the parent record",
                        },
                        "title": {
                            "type": "string",
                            "description": "Title of the note",
                        },
                        "body": {
                            "type": "string",
                            "description": "Content of the note",
                        },
                        "private": {
                            "type": "boolean",
                            "description": "Whether the note is private",
                            "default": False,
                        },
                    },
                    "required": ["parent_id", "title", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where the single item is a JSON string with the note creation result",
                    "examples": [
                        '{\n  "id": "<ID>",\n  "success": true,\n  "errors": []\n}'
                    ],
                },
                requiredScopes=["api", "refresh_token"],
            ),
            types.Tool(
                name="find_child_records",
                description="Finds child records for a given parent ID and returns them as line items",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "The 15 or 18-character Salesforce ID of the parent record",
                        },
                        "child_object_name": {
                            "type": "string",
                            "description": "The API name of the child Salesforce object (e.g., 'LineItem__c')",
                        },
                        "parent_field_name": {
                            "type": "string",
                            "description": "The API name of the field that links to the parent (e.g., 'Order__c')",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of fields to retrieve (retrieves all fields if not specified)",
                        },
                    },
                    "required": ["parent_id", "child_object_name", "parent_field_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing a child record",
                    "examples": [
                        '{\n  "attributes": {\n    "type": "LineItem__c",\n    "url": "/services/data/v59.0/sobjects/LineItem__c/<ID>"\n  },\n  "Id": "<ID>",\n  "Name": "Line Item 1"\n}'
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="list_campaigns",
                description="Lists existing campaigns in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of campaigns to return (default: 10)",
                            "default": 10,
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter by campaign status (e.g., 'Active', 'Completed', 'Planned')",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing a campaign record",
                    "examples": [
                        '{\n  "Id": "<ID>",\n  "Name": "Summer Promotion",\n  "IsActive": true,\n  "Status": "In Progress",\n  "Type": "Email"\n}',
                        '{\n  "campaign_count": 3,\n  "message": "Found 3 campaigns"\n}',
                    ],
                },
                requiredScopes=["api"],
            ),
            types.Tool(
                name="list_email_templates",
                description="Retrieves available email templates in Salesforce",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of templates to return (default: 10)",
                            "default": 10,
                        },
                        "folder_id": {
                            "type": "string",
                            "description": "Optional folder ID to filter templates by folder",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array where each item is a JSON string representing an email template",
                    "examples": [
                        '{\n  "Id": "<ID>",\n  "Name": "Welcome Email",\n  "TemplateType": "text",\n  "Subject": "Welcome to Our Service"\n}',
                        '{\n  "template_count": 5,\n  "message": "Found 5 email templates"\n}',
                    ],
                },
                requiredScopes=["api"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        """
        Dispatches a tool call to the corresponding Salesforce API method.

        Args:
            name (str): The tool name to execute.
            arguments (dict | None): Arguments to pass to the tool.

        Returns:
            list[types.TextContent]: The JSON-formatted result of the API call.

        Raises:
            ValueError: If an unknown tool name is provided.
        """
        logger.info(f"User {user_id} calling tool: {name} with args: {arguments}")

        token = await get_salesforce_token(server.user_id, server.api_key)
        salesforce_client = Salesforce(
            instance_url=token["instance_url"], session_id=token["access_token"]
        )
        if arguments is None:
            arguments = {}

        try:
            if name == "soql_query":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing 'query' argument")

                results = salesforce_client.query_all(query)
                records = results.get("records", [])
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(record, indent=2),
                    )
                    for record in records
                ]
            elif name == "sosl_search":
                search = arguments.get("search")
                if not search:
                    raise ValueError("Missing 'search' argument")

                results = salesforce_client.search(search)
                records = results.get("searchRecords", [])
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(record, indent=2),
                    )
                    for record in records
                ]
            elif name == "describe_object":
                object_name = arguments.get("object_name")
                if not object_name:
                    raise ValueError("Missing 'object_name' argument")

                # Get object description
                sf_object = getattr(salesforce_client, object_name)
                describe_result = sf_object.describe()

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(describe_result, indent=2),
                    )
                ]
            elif name == "get_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                if not object_name or not record_id:
                    raise ValueError("Missing 'object_name' or 'record_id' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.get(record_id)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]
            elif name == "create_record":
                object_name = arguments.get("object_name")
                data = arguments.get("data")
                if not object_name or not data:
                    raise ValueError("Missing 'object_name' or 'data' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.create(data)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]
            elif name == "update_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                data = arguments.get("data")
                if not object_name or not record_id or not data:
                    raise ValueError(
                        "Missing 'object_name', 'record_id', or 'data' argument"
                    )

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.update(record_id, data)
                # Status code needs to be wrapped in a JSON object
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"status_code": results}, indent=2),
                    )
                ]
            elif name == "delete_record":
                object_name = arguments.get("object_name")
                record_id = arguments.get("record_id")
                if not object_name or not record_id:
                    raise ValueError("Missing 'object_name' or 'record_id' argument")

                sf_object = getattr(salesforce_client, object_name)
                results = sf_object.delete(record_id)
                # Status code needs to be wrapped in a JSON object
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"status_code": results}, indent=2),
                    )
                ]

            elif name == "get_org_limits":
                limit_type = arguments.get("limit_type")

                # Get all organization limits
                org_limits = salesforce_client.limits()

                # If a specific limit type is requested, filter the results
                if limit_type:
                    if limit_type in org_limits:
                        results = {limit_type: org_limits[limit_type]}
                    else:
                        available_limits = list(org_limits.keys())
                        return [
                            types.TextContent(
                                type="text",
                                text=json.dumps(
                                    {
                                        "error": f"Limit type '{limit_type}' not found",
                                        "available_limits": available_limits,
                                    },
                                    indent=2,
                                ),
                            )
                        ]
                else:
                    results = org_limits

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "add_contact_to_campaign":
                contact_id = arguments.get("contact_id")
                campaign_id = arguments.get("campaign_id")
                status = arguments.get("status")

                if not contact_id or not campaign_id:
                    raise ValueError("Missing 'contact_id' or 'campaign_id' argument")

                # Prepare the CampaignMember data
                data = {"ContactId": contact_id, "CampaignId": campaign_id}

                if status:
                    data["Status"] = status

                # Create the CampaignMember
                results = salesforce_client.CampaignMember.create(data)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "add_file_to_record":
                file_id = arguments.get("file_id")
                record_id = arguments.get("record_id")
                share_type = arguments.get("share_type", "V")

                if not file_id or not record_id:
                    raise ValueError("Missing 'file_id' or 'record_id' argument")

                # Create ContentDocumentLink to link the file to the record
                data = {
                    "ContentDocumentId": file_id,
                    "LinkedEntityId": record_id,
                    "ShareType": share_type,
                }

                results = salesforce_client.ContentDocumentLink.create(data)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "add_lead_to_campaign":
                lead_id = arguments.get("lead_id")
                campaign_id = arguments.get("campaign_id")
                status = arguments.get("status")

                if not lead_id or not campaign_id:
                    raise ValueError("Missing 'lead_id' or 'campaign_id' argument")

                # Prepare the CampaignMember data
                data = {"LeadId": lead_id, "CampaignId": campaign_id}

                if status:
                    data["Status"] = status

                # Create the CampaignMember
                results = salesforce_client.CampaignMember.create(data)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "convert_lead":
                lead_id = arguments.get("lead_id")
                converted_status = arguments.get("converted_status")

                if not lead_id or not converted_status:
                    raise ValueError("Missing 'lead_id' or 'converted_status' argument")

                # Prepare the LeadConvert data
                data = {
                    "leadId": lead_id,
                    "convertedStatus": converted_status,
                }

                # Add optional parameters if provided
                if "account_id" in arguments and arguments["account_id"]:
                    data["accountId"] = arguments["account_id"]

                if "contact_id" in arguments and arguments["contact_id"]:
                    data["contactId"] = arguments["contact_id"]

                if "owner_id" in arguments and arguments["owner_id"]:
                    data["ownerId"] = arguments["owner_id"]

                if "opportunity_name" in arguments and arguments["opportunity_name"]:
                    data["opportunityName"] = arguments["opportunity_name"]

                if "create_opportunity" in arguments:
                    data["doNotCreateOpportunity"] = not arguments["create_opportunity"]

                if "send_notification_email" in arguments:
                    data["sendNotificationEmail"] = arguments["send_notification_email"]

                # Use the Salesforce API to convert the lead
                url = f"{salesforce_client.base_url}sobjects/Lead/{lead_id}/convert"
                result = salesforce_client._call_salesforce("POST", url, json=data)
                results = result.json()

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "create_child_records":
                parent_id = arguments.get("parent_id")
                child_object_name = arguments.get("child_object_name")
                parent_field_name = arguments.get("parent_field_name")
                records = arguments.get("records")

                if (
                    not parent_id
                    or not child_object_name
                    or not parent_field_name
                    or not records
                ):
                    raise ValueError(
                        "Missing required arguments for creating child records"
                    )

                # Set the parent ID in each child record
                for record in records:
                    record[parent_field_name] = parent_id

                # Get the child object from Salesforce
                sf_object = getattr(salesforce_client, child_object_name)

                # Create the records
                results = []
                for record in records:
                    result = sf_object.create(record)
                    results.append(result)

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result, indent=2),
                    )
                    for result in results
                ]

            elif name == "create_enhanced_note":
                title = arguments.get("title")
                content = arguments.get("content")
                record_id = arguments.get("record_id")
                share_type = arguments.get("share_type", "V")

                if not title or not content:
                    raise ValueError("Missing 'title' or 'content' argument")

                # Create the ContentNote
                note_data = {
                    "Title": title,
                    "Content": content,  # Content should be HTML-formatted
                }

                note_result = salesforce_client.ContentNote.create(note_data)
                note_id = note_result.get("id")

                # If a record ID is provided, link the note to the record
                if record_id:
                    link_data = {
                        "ContentDocumentId": note_id,
                        "LinkedEntityId": record_id,
                        "ShareType": share_type,
                    }
                    link_result = salesforce_client.ContentDocumentLink.create(
                        link_data
                    )

                    # Return both the note creation and link results
                    results = {"note": note_result, "link": link_result}
                else:
                    results = {"note": note_result}

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "create_file":
                title = arguments.get("title")
                path_on_client = arguments.get("path_on_client")
                version_data = arguments.get("version_data")
                record_id = arguments.get("record_id")
                share_type = arguments.get("share_type", "V")

                if not title or not path_on_client or not version_data:
                    raise ValueError("Missing required arguments for creating file")

                # Create the ContentVersion (file)
                file_data = {
                    "Title": title,
                    "PathOnClient": path_on_client,
                    "VersionData": version_data,
                }

                if "description" in arguments and arguments["description"]:
                    file_data["Description"] = arguments["description"]

                file_result = salesforce_client.ContentVersion.create(file_data)

                # Query to get the ContentDocumentId
                if record_id:
                    # Need to get the ContentDocumentId from the ContentVersion
                    query = f"SELECT ContentDocumentId FROM ContentVersion WHERE Id = '{file_result.get('id')}'"
                    doc_query_result = salesforce_client.query(query)
                    content_document_id = doc_query_result["records"][0][
                        "ContentDocumentId"
                    ]

                    # Create ContentDocumentLink to link the file to the record
                    link_data = {
                        "ContentDocumentId": content_document_id,
                        "LinkedEntityId": record_id,
                        "ShareType": share_type,
                    }
                    link_result = salesforce_client.ContentDocumentLink.create(
                        link_data
                    )

                    # Return both results
                    results = {"file": file_result, "link": link_result}
                else:
                    results = {"file": file_result}

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "create_note":
                parent_id = arguments.get("parent_id")
                title = arguments.get("title")
                body = arguments.get("body")
                private = arguments.get("private", False)

                if not parent_id or not title or not body:
                    raise ValueError("Missing required arguments for creating note")

                # Create the Note
                note_data = {
                    "ParentId": parent_id,
                    "Title": title,
                    "Body": body,
                    "IsPrivate": private,
                }

                results = salesforce_client.Note.create(note_data)
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(results, indent=2),
                    )
                ]

            elif name == "list_email_templates":
                limit = arguments.get("limit", 10)
                folder_id = arguments.get("folder_id")

                # Build the SOQL query for email templates
                query = "SELECT Id, Name, FolderId, Subject, ApiVersion, TemplateType, TemplateStyle FROM EmailTemplate"

                # Add folder filter if provided
                if folder_id:
                    query += f" WHERE FolderId = '{folder_id}'"

                # Add limit and order
                query += f" ORDER BY CreatedDate DESC LIMIT {limit}"

                # Execute the query
                results = salesforce_client.query_all(query)

                # Return each record as a separate item
                templates = results.get("records", [])

                # First, return a summary with count
                summary = {
                    "template_count": len(templates),
                    "message": f"Found {len(templates)} email templates",
                }

                response_items = [
                    types.TextContent(
                        type="text",
                        text=json.dumps(summary, indent=2),
                    )
                ]

                # Then add each template as a separate item
                for template in templates:
                    response_items.append(
                        types.TextContent(
                            type="text",
                            text=json.dumps(template, indent=2),
                        )
                    )

                return (
                    response_items
                    if templates
                    else [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "template_count": 0,
                                    "message": "No email templates found",
                                },
                                indent=2,
                            ),
                        )
                    ]
                )
            elif name == "find_child_records":
                parent_id = arguments.get("parent_id")
                child_object_name = arguments.get("child_object_name")
                parent_field_name = arguments.get("parent_field_name")
                fields = arguments.get("fields")

                if not parent_id or not child_object_name or not parent_field_name:
                    raise ValueError(
                        "Missing required arguments for finding child records"
                    )

                # Build the query - Salesforce doesn't support "SELECT *"
                if not fields:
                    # Default to some standard fields instead of *
                    fields = ["Id", "Name", "CreatedDate"]

                fields_str = ",".join(fields)
                query = f"SELECT {fields_str} FROM {child_object_name} WHERE {parent_field_name} = '{parent_id}'"

                # Execute the query
                results = salesforce_client.query_all(query)

                # Return each record as a separate item
                records = results.get("records", [])
                return (
                    [
                        types.TextContent(
                            type="text",
                            text=json.dumps(record, indent=2),
                        )
                        for record in records
                    ]
                    if records
                    else [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {"message": "No child records found"}, indent=2
                            ),
                        )
                    ]
                )

            elif name == "list_campaigns":
                limit = arguments.get("limit", 10)
                status_filter = arguments.get("status")

                # Build the SOQL query for campaigns
                query = "SELECT Id, Name, IsActive, Status, Type, StartDate, EndDate FROM Campaign"

                # Add status filter if provided
                if status_filter:
                    query += f" WHERE Status = '{status_filter}'"

                # Add limit and order
                query += f" ORDER BY CreatedDate DESC LIMIT {limit}"

                # Execute the query
                results = salesforce_client.query_all(query)

                # Return each record as a separate item
                campaigns = results.get("records", [])

                # First, return a summary with count
                summary = {
                    "campaign_count": len(campaigns),
                    "message": f"Found {len(campaigns)} campaigns",
                }

                response_items = [
                    types.TextContent(
                        type="text",
                        text=json.dumps(summary, indent=2),
                    )
                ]

                # Then add each campaign as a separate item
                for campaign in campaigns:
                    response_items.append(
                        types.TextContent(
                            type="text",
                            text=json.dumps(campaign, indent=2),
                        )
                    )

                return (
                    response_items
                    if campaigns
                    else [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {"campaign_count": 0, "message": "No campaigns found"},
                                indent=2,
                            ),
                        )
                    ]
                )

        except Exception as e:
            logger.error(
                f"Error calling Salesforce API: {e} on line {e.__traceback__.tb_lineno}"
            )
            return [
                types.TextContent(
                    type="text", text=json.dumps({"error": str(e)}, indent=2)
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Provides initialization options required for registering the server.
    """
    return InitializationOptions(
        server_name="salesforce-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)

    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
