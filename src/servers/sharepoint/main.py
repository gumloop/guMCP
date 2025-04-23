import sys
import logging
import json
import os
import requests
from pathlib import Path
from typing import Optional, Any

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.microsoft.util import get_credentials, authenticate_and_save_credentials


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "Sites.Manage.All",  # For creating/updating sites, lists, items, pages
    "Sites.Read.All",  # For reading site data, lists, pages
    "Sites.ReadWrite.All",  # For creating/updating lists, items, pages
    "User.Read.All",  # For listing users
    "Files.Read.All",  # For downloading files
    "Files.ReadWrite.All",  # For creating folders, uploading files
    "offline_access",  # For token refresh
]

SHAREPOINT_OAUTH_TOKEN_URL = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token"
)
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0/"
GRAPH_SITES_URL = GRAPH_BASE_URL + "sites/"
GRAPH_USERS_URL = GRAPH_BASE_URL + "users/"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_sharepoint_client(token: str) -> Any:
    """
    Create a SharePoint client instance using the provided user ID and API key.

    Args:
        user_id: The user ID to create the client for
        api_key: Optional API key for authentication

    Returns:
        dict: SharePoint client configuration including access token and other details.
    """
    # Get the access token and token type from the credentials
    token_type = "Bearer"
    logger.info(f"Using token type: {token_type}")

    # Standard headers for API requests
    standard_headers = {
        "Authorization": f"{token_type} {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    return {"token": token, "headers": standard_headers, "base_url": GRAPH_BASE_URL}


async def get_site_id_from_url(url: str, sharepoint_client: dict) -> str:
    """
    Get the site ID of a SharePoint site from its URL.

    Args:
        url: The URL of the SharePoint site (e.g., 'https://contoso.sharepoint.com/sites/marketing')
        sharepoint_client: The SharePoint client configuration with authentication headers

    Returns:
        str: The site ID in the format 'hostname,siteId,webId'

    Raises:
        ValueError: If the URL is not a valid SharePoint URL or the site is not found
    """
    logger.info(f"Getting site ID for URL: {url}")

    try:
        # Parse the URL to extract hostname and path
        from urllib.parse import urlparse, quote

        # Parse the URL
        parsed_url = urlparse(url)
        hostname = parsed_url.netloc
        path = parsed_url.path.rstrip("/").lstrip("/")  # Normalize path

        # Encode path components
        encoded_path = quote(path, safe="") if path else ""

        # Handle root site
        encoded_site = (
            f"{hostname}:/{encoded_path}" if encoded_path else f"{hostname}:/"
        )

        # Build the request URL
        request_url = f"{GRAPH_SITES_URL}{encoded_site}"

        logger.info(f"Making request to: {request_url}")

        # Make the API request
        response = requests.get(
            request_url, headers=sharepoint_client["headers"], timeout=30
        )

        # Log the response status
        logger.info(f"Response status: {response.status_code}")

        # Check if the request was successful
        if response.status_code == 200:
            site_data = response.json()
            site_id = site_data.get("id")

            if not site_id:
                raise ValueError("Site ID not found in the response")

            logger.info(f"Retrieved site ID: {site_id}")
            return site_id
        else:
            error_message = (
                f"Error retrieving site ID: {response.status_code} - {response.text}"
            )
            logger.error(error_message)
            raise ValueError(error_message)

    except Exception as e:
        logger.error(f"Error in get_site_id_from_url: {str(e)}")
        raise ValueError(f"Failed to get site ID: {str(e)}")


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Create a new SharePoint MCP server instance.

    Args:
        user_id: The user ID to create the server for
        api_key: Optional API key for authentication

    Returns:
        An MCP Server instance configured for SharePoint operations
    """
    server = Server("sharepoint-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return the list of available SharePoint tools."""
        tools = [
            # USER MANAGEMENT TOOLS
            # Tools for managing users in Microsoft 365
            types.Tool(
                name="get_users",
                description="Get all users from Microsoft 365",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of users to return (default: 100)",
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData filter for filtering users (e.g., \"startswith(displayName,'John')\")",
                        },
                        "select": {
                            "type": "string",
                            "description": "Comma-separated list of properties to include in the response",
                        },
                        "orderby": {
                            "type": "string",
                            "description": 'Property by which to order results (e.g., "displayName asc")',
                        },
                    },
                },
            ),
            # LIST MANAGEMENT TOOLS
            # Tools for creating and retrieving SharePoint lists
            types.Tool(
                name="list_site_lists",
                description="List all lists in a SharePoint site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site for which to retrieve lists. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site for which to retrieve lists. If not provided, the SITE ID should be provided.",
                        },
                    },
                },
            ),
            types.Tool(
                name="create_list",
                description="Create a new list in SharePoint",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "display_name": {
                            "type": "string",
                            "description": "The display name of the list (required)",
                        },
                        "description": {
                            "type": "string",
                            "description": "A description of the list",
                        },
                        "template": {
                            "type": "string",
                            "description": "The template to use for the list. If not provided, a generic list will be created.",
                        },
                    },
                    "required": ["display_name"],
                },
            ),
            types.Tool(
                name="get_list",
                description="Get details of a SharePoint list by ID or title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to retrieve. Either list_id or list_title must be provided.",
                        },
                        "list_title": {
                            "type": "string",
                            "description": "The title of the list to retrieve. Either list_id or list_title must be provided.",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            # LIST-ITEM MANAGEMENT TOOLS
            # Tools for working with items in SharePoint lists
            types.Tool(
                name="create_list_item",
                description="Create a new item in a SharePoint list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list where the item will be created",
                        },
                        "fields": {
                            "type": "object",
                            "description": "The fields and values for the list item (required). This should be a JSON object with field names as keys and field values as values.",
                        },
                        "content_type": {
                            "type": "object",
                            "description": "The content type information for the item",
                        },
                    },
                    "required": ["site_id", "list_id", "fields"],
                },
            ),
            types.Tool(
                name="get_list_item",
                description="Get details of a specific item in a SharePoint list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list containing the item",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "The ID of the item to retrieve",
                        },
                    },
                    "required": ["site_id", "list_id", "item_id"],
                },
            ),
            types.Tool(
                name="get_list_items",
                description="Get all items from a SharePoint list with filtering and sorting options",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list to retrieve items from",
                        },
                        "top": {
                            "type": "integer",
                            "description": "The maximum number of items to retrieve in a single request (optional)",
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData filter to apply to the items (optional)",
                        },
                        "orderby": {
                            "type": "string",
                            "description": "OData orderby expression to sort the items (optional)",
                        },
                    },
                    "required": ["site_id", "list_id"],
                },
            ),
            types.Tool(
                name="delete_list_item",
                description="Delete a specific item from a SharePoint list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list will be created. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list will be created. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list containing the item to delete",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "The ID of the item to delete",
                        },
                    },
                    "required": ["site_id", "list_id", "item_id"],
                },
            ),
            types.Tool(
                name="update_list_item",
                description="Update fields of an existing item in a SharePoint list",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the list is located. If not provided, the SITE URL should be provided.",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site where the list is located. If not provided, the SITE ID should be provided.",
                        },
                        "list_id": {
                            "type": "string",
                            "description": "The ID of the list containing the item to update",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "The ID of the item to update",
                        },
                        "fields": {
                            "type": "object",
                            "description": "The fields and values to update in the list item. This should be a JSON object with field names as keys and new field values as values.",
                        },
                    },
                    "required": ["site_id", "list_id", "item_id", "fields"],
                },
            ),
            types.Tool(
                name="download_file",
                description="Download a file from the current user's OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "item_id": {
                            "type": "string",
                            "description": "The ID of the DriveItem (file) to download",
                        },
                        "download_path": {
                            "type": "string",
                            "description": "Local path where the file should be saved (optional). If not provided, the file content will be returned as base64 encoded string.",
                        },
                    },
                    "required": ["item_id"],
                },
            ),
            types.Tool(
                name="create_folder",
                description="Create a new folder in the current user's OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "folder_name": {
                            "type": "string",
                            "description": "Name of the folder to create",
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "ID of the parent folder where to create the new folder (optional). If not provided, the folder will be created in the root.",
                        },
                        "conflict_behavior": {
                            "type": "string",
                            "description": "Behavior if the folder already exists. Options: 'rename', 'replace', 'fail'. Default is 'rename'.",
                            "enum": ["rename", "replace", "fail"],
                        },
                    },
                    "required": ["folder_name"],
                },
            ),
            types.Tool(
                name="upload_file",
                description="Upload a file to the current user's OneDrive",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Local path of the file to upload",
                        },
                        "destination_path": {
                            "type": "string",
                            "description": "Destination path in OneDrive, including filename (e.g., 'Documents/report.docx')",
                        },
                        "conflict_behavior": {
                            "type": "string",
                            "description": "Behavior if file already exists. Options: 'rename', 'replace', 'fail'. Default is 'replace'.",
                            "enum": ["rename", "replace", "fail"],
                        },
                        "content_type": {
                            "type": "string",
                            "description": "Content type of the file (optional, e.g., 'text/plain', 'application/pdf')",
                        },
                        "parent_folder_id": {
                            "type": "string",
                            "description": "ID of the parent folder (optional, use instead of destination_path)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            types.Tool(
                name="create_site_page",
                description="Create a new SharePoint site page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the page will be created",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site (alternative to site_id)",
                        },
                        "page_name": {
                            "type": "string",
                            "description": "Name of the page to create (without .aspx extension)",
                        },
                        "page_title": {
                            "type": "string",
                            "description": "Title to display on the page",
                        },
                        "page_layout": {
                            "type": "string",
                            "description": "Layout of the page (e.g., 'article', 'home', 'singleWebPartAppPage')",
                            "enum": ["article", "home", "singleWebPartAppPage"],
                        },
                        "web_parts": {
                            "type": "array",
                            "description": "Array of web parts to add to the page (optional)",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "description": "Type of web part (e.g., 'text', 'image')",
                                    },
                                    "data": {
                                        "type": "object",
                                        "description": "Data for the web part",
                                    },
                                },
                            },
                        },
                    },
                    "required": ["page_name", "page_title"],
                },
            ),
            types.Tool(
                name="get_site_page",
                description="Get details of a specific page in a SharePoint site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site where the page is located",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site (alternative to site_id)",
                        },
                        "page_id": {
                            "type": "string",
                            "description": "The ID of the page to retrieve",
                        },
                        "page_name": {
                            "type": "string",
                            "description": "The name of the page to retrieve (alternative to page_id)",
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="list_site_pages",
                description="List all pages in a SharePoint site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site to list pages from",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site (alternative to site_id)",
                        },
                        "top": {
                            "type": "integer",
                            "description": "Maximum number of pages to return (default: 100)",
                        },
                        "filter": {
                            "type": "string",
                            "description": "OData filter for the pages (e.g., \"startswith(name,'Home')\")",
                        },
                        "orderby": {
                            "type": "string",
                            "description": 'OData orderby expression to sort the pages (e.g., "createdDateTime desc")',
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="get_site_info",
                description="Get metadata and information about a SharePoint site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "The ID of the SharePoint site to get information about",
                        },
                        "site_url": {
                            "type": "string",
                            "description": "The URL of the SharePoint site (alternative to site_id)",
                        },
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="search_sites",
                description="Search for SharePoint sites by keyword",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to find sites (e.g., 'marketing', 'project', etc.)",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]
        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent]:
        """Handle SharePoint tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        access_token = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )
        sharepoint = await create_sharepoint_client(access_token)

        if arguments is None:
            arguments = {}

        try:
            if name == "list_site_lists":
                # Extract parameters for listing all site lists
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]

                # If site_id is not provided, get it from the URL
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Build the request URL (GET /sites/{site-id}/lists)
                url = f"{GRAPH_SITES_URL}{site_id}/lists"

                logger.info(f"Making request to {url}")

                # Make the API request to get lists
                response = requests.get(url, headers=sharepoint["headers"], timeout=30)

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    lists = result.get("value", [])
                    list_count = len(lists)

                    # Format the response for readability
                    formatted_result = {
                        "totalLists": list_count,
                        "siteId": site_id,
                        "lists": lists,
                    }

                    # Check if there's a next page link
                    if "@odata.nextLink" in result:
                        formatted_result["nextLink"] = result["@odata.nextLink"]
                        formatted_result["note"] = (
                            "There are more lists available. Refine your query or use the nextLink to retrieve more."
                        )

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {list_count} lists from the SharePoint site:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving lists: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_users":
                # Extract parameters for getting users
                top = arguments.get("top", 100)  # Default to 100 users max
                filter_query = arguments.get("filter")
                select = arguments.get("select")
                orderby = arguments.get("orderby")

                # Build the request URL
                url = GRAPH_USERS_URL

                # Prepare query parameters
                params = {}

                # Add optional parameters if provided
                if top:
                    params["$top"] = top

                if filter_query:
                    params["$filter"] = filter_query

                if select:
                    params["$select"] = select

                if orderby:
                    params["$orderby"] = orderby
                logger.info(f"Making request to {url}")

                # Make the API request to get users
                response = requests.get(
                    url, headers=sharepoint["headers"], params=params, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    users = result.get("value", [])
                    user_count = len(users)

                    # Format the response for readability
                    formatted_result = {"totalUsers": user_count, "users": users}

                    # Check if there's a next page link
                    if "@odata.nextLink" in result:
                        formatted_result["nextLink"] = result["@odata.nextLink"]
                        formatted_result["note"] = (
                            "There are more users available. Refine your query or use the nextLink to retrieve more."
                        )

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {user_count} users:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving users: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_list":
                # Extract parameters for creating a list
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                display_name = arguments.get("display_name")
                description = arguments.get("description", "")
                template = arguments.get("template", None)

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not display_name:
                    return [
                        types.TextContent(
                            type="text", text="Error: display_name is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_SITES_URL}{site_id}/lists"

                # Prepare the request payload
                list_data = {"displayName": display_name, "description": description}

                # Add template if provided
                if template:
                    list_data["list"] = {"template": template}

                logger.info(f"Making request to {url}")

                # Make the API request to create the list
                response = requests.post(
                    url, headers=sharepoint["headers"], json=list_data, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created list '{display_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_list":
                # Extract parameters for getting a list
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                list_title = arguments.get("list_title")

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate parameters
                if not list_id and not list_title:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either list_id or list_title must be provided",
                        )
                    ]

                # Build the request URL
                if list_id:
                    # Get by ID
                    url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}"
                else:
                    # Get by title
                    url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_title}"
                logger.info(f"Making request to {url}")

                # Make the API request to get the list
                response = requests.get(url, headers=sharepoint["headers"], timeout=30)

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    list_name = result.get("displayName", "Unknown List")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved list '{list_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_list_item":
                # Extract parameters for creating a list item
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                fields = arguments.get("fields", {})
                content_type = arguments.get("content_type", None)

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not list_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: list_id is required"
                        )
                    ]

                if not fields:
                    return [
                        types.TextContent(
                            type="text", text="Error: fields are required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}/items"

                # Prepare the request payload
                item_data = {"fields": fields}

                # Add optional parameters if provided
                if content_type:
                    item_data["contentType"] = content_type
                logger.info(f"Making request to {url}")

                # Make the API request to create the list item
                response = requests.post(
                    url, headers=sharepoint["headers"], json=item_data, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    item_id = result.get("id", "Unknown ID")
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created list item with ID '{item_id}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_list_item":
                # Extract parameters for getting a list item
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                item_id = arguments.get("item_id")

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not list_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: list_id is required"
                        )
                    ]

                if not item_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: item_id is required"
                        )
                    ]

                # Build the request URL
                url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}/items/{item_id}"
                logger.info(f"Making request to {url}")

                # Make the API request to get the list item
                response = requests.get(url, headers=sharepoint["headers"], timeout=30)

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved list item with ID '{item_id}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_list_items":
                # Extract parameters for getting list items
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                top = arguments.get("top")
                filter_query = arguments.get("filter")
                orderby = arguments.get("orderby")

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not list_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: list_id is required"
                        )
                    ]

                # Build the base request URL
                url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}/items"

                # Prepare query parameters
                params = {}

                # Add optional parameters if provided
                if top:
                    params["$top"] = top

                if filter_query:
                    params["$filter"] = filter_query

                if orderby:
                    params["$orderby"] = orderby

                # Always expand fields to get the list item values
                params["$expand"] = "fields"
                logger.info(f"Making request to {url}")

                # Make the API request to get the list items
                response = requests.get(
                    url, headers=sharepoint["headers"], params=params, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    item_count = len(result.get("value", []))

                    # Format the response to make it more readable
                    formatted_result = {
                        "totalItems": item_count,
                        "listId": list_id,
                        "siteId": site_id,
                        "items": result.get("value", []),
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {item_count} items from list '{list_id}':\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "delete_list_item":
                # Extract parameters for deleting a list item
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                item_id = arguments.get("item_id")

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not list_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: list_id is required"
                        )
                    ]

                if not item_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: item_id is required"
                        )
                    ]

                # Build the request URL for deleting the list item
                url = f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}/items/{item_id}"
                logger.info(f"Making request to {url}")

                # Make the API request to delete the list item
                response = requests.delete(
                    url, headers=sharepoint["headers"], timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                # DELETE operations return 204 No Content when successful
                if response.status_code == 204:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully deleted list item with ID '{item_id}' from list '{list_id}'",
                        )
                    ]
                else:
                    error_message = f"Error deleting list item: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "update_list_item":
                # Extract parameters for updating a list item
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                list_id = arguments.get("list_id")
                item_id = arguments.get("item_id")
                fields = arguments.get("fields", {})

                # Validate parameters
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]
                if site_id is None:
                    site_id = await get_site_id_from_url(
                        site_url, sharepoint_client=sharepoint
                    )

                # Validate required parameters
                if not list_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: list_id is required"
                        )
                    ]

                if not item_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: item_id is required"
                        )
                    ]

                if not fields:
                    return [
                        types.TextContent(
                            type="text", text="Error: fields are required for update"
                        )
                    ]

                # Build the request URL for updating the list item
                url = (
                    f"{GRAPH_SITES_URL}{site_id}/lists/{list_id}/items/{item_id}/fields"
                )
                logger.info(f"Making request to {url}")

                # Prepare the update payload
                update_data = fields

                # Make the API request to update the list item fields
                # Using PATCH method to update only the specified fields
                response = requests.patch(
                    url, headers=sharepoint["headers"], json=update_data, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    return types.TextContent(
                        type="text",
                        text=f"Successfully updated fields for list item with ID '{item_id}':\n{json.dumps(response.json(), indent=2)}",
                    )
                else:
                    error_message = f"Error updating list item: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "download_file":
                # Extract parameters for downloading a file
                item_id = arguments.get("item_id")
                download_path = arguments.get("download_path")

                # Validate required parameters
                if not item_id:
                    return [
                        types.TextContent(
                            type="text", text="Error: item_id is required"
                        )
                    ]

                # Build the request URL for downloading the file - only using current user context
                url = f"{GRAPH_BASE_URL}me/drive/items/{item_id}/content"

                logger.info(f"Making request to {url}")

                # Make the API request to get the file content
                # Stream the response to handle potentially large files
                response = requests.get(
                    url, headers=sharepoint["headers"], stream=True, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200 or response.status_code == 302:
                    # If the response is a redirect (302), follow it
                    if response.status_code == 302:
                        redirect_url = response.headers.get("Location")
                        if not redirect_url:
                            return [
                                types.TextContent(
                                    type="text",
                                    text="Error: Redirect URL not found in response headers",
                                )
                            ]

                        logger.info(f"Following redirect to {redirect_url}")
                        # The redirect URL is pre-authenticated, so we don't need auth headers
                        response = requests.get(redirect_url, stream=True, timeout=30)

                        # Check if the redirect request was successful
                        if response.status_code != 200:
                            error_message = f"Error following redirect: {response.status_code} - {response.text}"
                            logger.error(error_message)
                            return [types.TextContent(type="text", text=error_message)]

                    # Get file name from Content-Disposition header if available
                    content_disposition = response.headers.get(
                        "Content-Disposition", ""
                    )
                    filename = None
                    if "filename=" in content_disposition:
                        filename = content_disposition.split("filename=")[1].strip(
                            "\"'"
                        )

                    # If download_path is provided, save the file
                    if download_path:
                        try:
                            # Create directory if it doesn't exist
                            os.makedirs(
                                os.path.dirname(os.path.abspath(download_path)),
                                exist_ok=True,
                            )

                            # Save the file
                            with open(download_path, "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:  # filter out keep-alive new chunks
                                        f.write(chunk)

                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Successfully downloaded file to {download_path}",
                                )
                            ]
                        except Exception as e:
                            error_message = f"Error saving file: {str(e)}"
                            logger.error(error_message)
                            return [types.TextContent(type="text", text=error_message)]
                    else:
                        # If no download path, return the content as base64
                        # Warning: This can be memory-intensive for large files
                        try:
                            import base64

                            file_content = response.content
                            encoded_content = base64.b64encode(file_content).decode(
                                "utf-8"
                            )

                            # Truncate content in the display if it's too large
                            content_length = len(encoded_content)
                            display_content = (
                                encoded_content[:1000] + "..."
                                if content_length > 1000
                                else encoded_content
                            )

                            file_info = {
                                "filename": filename,
                                "content_type": response.headers.get("Content-Type"),
                                "content_length": len(file_content),
                                "base64_content": display_content,
                                "note": (
                                    "Content truncated for display"
                                    if content_length > 1000
                                    else None
                                ),
                            }

                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Successfully retrieved file content:\n{json.dumps(file_info, indent=2)}",
                                )
                            ]
                        except Exception as e:
                            error_message = f"Error processing file content: {str(e)}"
                            logger.error(error_message)
                            return [types.TextContent(type="text", text=error_message)]
                else:
                    error_message = f"Error downloading file: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_folder":
                # Extract parameters for creating a folder
                folder_name = arguments.get("folder_name")
                parent_folder_id = arguments.get("parent_folder_id")
                conflict_behavior = arguments.get("conflict_behavior", "rename")

                # Validate required parameters
                if not folder_name:
                    return [
                        types.TextContent(
                            type="text", text="Error: folder_name is required"
                        )
                    ]

                # Validate conflict_behavior
                if conflict_behavior not in ["rename", "replace", "fail"]:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: conflict_behavior must be one of: rename, replace, fail",
                        )
                    ]

                # Build the request URL for creating a folder
                if parent_folder_id:
                    # Create in specific folder
                    url = f"{GRAPH_BASE_URL}me/drive/items/{parent_folder_id}/children"
                else:
                    # Create in root
                    url = f"{GRAPH_BASE_URL}me/drive/root/children"

                logger.info(f"Making request to {url}")

                # Prepare the request payload
                folder_data = {
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": conflict_behavior,
                }

                # Make the API request to create the folder
                response = requests.post(
                    url, headers=sharepoint["headers"], json=folder_data, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    folder_id = result.get("id", "Unknown ID")
                    folder_url = result.get("webUrl", "Unknown URL")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created folder '{folder_name}' with ID '{folder_id}':\nURL: {folder_url}\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error creating folder: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "upload_file":
                # Extract parameters for uploading a file
                file_path = arguments.get("file_path")
                destination_path = arguments.get("destination_path")
                parent_folder_id = arguments.get("parent_folder_id")
                conflict_behavior = arguments.get("conflict_behavior", "replace")
                content_type = arguments.get("content_type", "text/plain")

                # Validate required parameters
                if not file_path:
                    return [
                        types.TextContent(
                            type="text", text="Error: file_path is required"
                        )
                    ]

                # Check if file exists
                if not os.path.isfile(file_path):
                    return [
                        types.TextContent(
                            type="text", text=f"Error: File not found: {file_path}"
                        )
                    ]

                # Check if we have either destination_path or parent_folder_id
                if not destination_path and not parent_folder_id:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either destination_path or parent_folder_id must be provided",
                        )
                    ]

                # Validate conflict_behavior
                if conflict_behavior not in ["rename", "replace", "fail"]:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: conflict_behavior must be one of: rename, replace, fail",
                        )
                    ]

                try:
                    # Determine file size
                    file_size = os.path.getsize(file_path)
                    file_name = os.path.basename(file_path)

                    # Build the request URL based on provided parameters
                    if destination_path:
                        # Clean the path and ensure it starts with a / but doesn't end with one
                        clean_path = destination_path.strip("/")
                        url = f"{GRAPH_BASE_URL}me/drive/root:/{clean_path}:/content"
                    else:
                        # Use parent folder ID and include filename
                        url = f"{GRAPH_BASE_URL}me/drive/items/{parent_folder_id}/children/{file_name}/content"

                    # Add conflict behavior as a query parameter
                    url += f"?@microsoft.graph.conflictBehavior={conflict_behavior}"

                    logger.info(f"Making request to {url}")

                    # Prepare the headers with content type
                    upload_headers = sharepoint["headers"].copy()
                    upload_headers["Content-Type"] = content_type

                    # Read the file content
                    with open(file_path, "rb") as f:
                        file_content = f.read()

                    # Make the API request to upload the file
                    response = requests.put(
                        url, headers=upload_headers, data=file_content, timeout=60
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code in [200, 201]:
                        result = response.json()
                        file_id = result.get("id", "Unknown ID")
                        file_url = result.get("webUrl", "Unknown URL")

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully uploaded file '{file_name}' ({file_size} bytes) with ID '{file_id}':\nURL: {file_url}\n{json.dumps(result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error uploading file: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during file upload: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_site_page":
                # Extract parameters for creating a site page
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                page_name = arguments.get("page_name")
                page_title = arguments.get(
                    "page_title", page_name
                )  # Default to page_name if title not provided
                page_layout = arguments.get(
                    "page_layout", "article"
                )  # Default to Article layout
                web_parts = arguments.get("web_parts", [])

                # Validate required parameters
                if not page_name:
                    return [
                        types.TextContent(
                            type="text", text="Error: page_name is required"
                        )
                    ]

                # Validate site identification
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]

                # Get site_id from site_url if needed
                if site_id is None:
                    try:
                        site_id = await get_site_id_from_url(
                            site_url, sharepoint_client=sharepoint
                        )
                    except ValueError as e:
                        return [types.TextContent(type="text", text=str(e))]

                # Validate page_layout
                valid_layouts = ["article", "home", "singleWebPartAppPage"]
                if page_layout not in valid_layouts:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: page_layout must be one of: {', '.join(valid_layouts)}",
                        )
                    ]

                # Build the request URL for creating a site page
                url = f"{GRAPH_SITES_URL}{site_id}/pages"
                logger.info(f"Making request to {url}")

                # Create the request headers
                page_headers = sharepoint["headers"].copy()
                page_headers["Content-Type"] = "application/json"
                page_headers["Accept"] = "application/json;odata.metadata=none"

                # Build the page payload
                page_data = {
                    "@odata.type": "#microsoft.graph.sitePage",
                    "name": page_name,
                    "title": page_title,
                    "pageLayout": page_layout,
                }

                # Add web parts if provided
                if web_parts:
                    page_data["webParts"] = []
                    for part in web_parts:
                        part_type = part.get("type")
                        part_data = part.get("data", {})

                        # Construct web part based on type
                        if part_type == "text":
                            web_part = {
                                "type": "rte",
                                "data": {"innerHTML": part_data.get("text", "")},
                            }
                            page_data["webParts"].append(web_part)
                        elif part_type == "image":
                            web_part = {"type": "image", "data": part_data}
                            page_data["webParts"].append(web_part)
                        else:
                            # Add other supported web parts as needed
                            logger.warning(f"Unsupported web part type: {part_type}")

                try:
                    # Make the API request to create the site page
                    response = requests.post(
                        url, headers=page_headers, json=page_data, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code in [200, 201]:
                        result = response.json()
                        page_id = result.get("id", "Unknown ID")
                        page_url = result.get("webUrl", "Unknown URL")

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully created site page '{page_name}' with ID '{page_id}':\nURL: {page_url}\n{json.dumps(result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error creating site page: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during site page creation: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_site_page":
                # Extract parameters for getting a site page
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                page_id = arguments.get("page_id")
                page_name = arguments.get("page_name")

                # Validate site identification
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]

                # Get site_id from site_url if needed
                if site_id is None:
                    try:
                        site_id = await get_site_id_from_url(
                            site_url, sharepoint_client=sharepoint
                        )
                    except ValueError as e:
                        return [types.TextContent(type="text", text=str(e))]

                # Validate page identification
                if page_id is None and page_name is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either page_id or page_name must be provided",
                        )
                    ]

                # If we have page_name but not page_id, try to find the page by name
                if page_id is None and page_name:
                    # First, list all pages to find the one with matching name
                    list_url = f"{GRAPH_SITES_URL}{site_id}/pages"
                    logger.info(f"Making request to list pages: {list_url}")

                    try:
                        list_response = requests.get(
                            list_url, headers=sharepoint["headers"], timeout=30
                        )

                        if list_response.status_code == 200:
                            pages = list_response.json().get("value", [])
                            matching_pages = [
                                p for p in pages if p.get("name") == page_name
                            ]

                            if matching_pages:
                                page_id = matching_pages[0].get("id")
                                logger.info(
                                    f"Found page ID {page_id} for page name {page_name}"
                                )
                            else:
                                return [
                                    types.TextContent(
                                        type="text",
                                        text=f"Error: No page found with name '{page_name}'",
                                    )
                                ]
                        else:
                            error_message = f"Error listing pages: {list_response.status_code} - {list_response.text}"
                            logger.error(error_message)
                            return [types.TextContent(type="text", text=error_message)]
                    except Exception as e:
                        error_message = f"Error listing pages: {str(e)}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                # Build the request URL for getting the site page using the microsoft.graph.sitePage endpoint
                url = f"{GRAPH_SITES_URL}{site_id}/pages/{page_id}/microsoft.graph.sitePage"
                logger.info(f"Making request to {url}")

                # Create the request headers
                page_headers = sharepoint["headers"].copy()
                page_headers["Accept"] = "application/json;odata.metadata=none"

                try:
                    # Make the API request to get the site page
                    # No request body needed as specified
                    response = requests.get(url, headers=page_headers, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        page_title = result.get("title", "Untitled")
                        page_url = result.get("webUrl", "Unknown URL")

                        # Format the response
                        formatted_result = {
                            "page_id": page_id,
                            "title": page_title,
                            "url": page_url,
                            "details": result,
                        }

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully retrieved site page '{page_title}' with ID '{page_id}':\nURL: {page_url}\n{json.dumps(formatted_result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error retrieving site page: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during site page retrieval: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "list_site_pages":
                # Extract parameters for listing site pages
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")
                top = arguments.get("top", 100)  # Default to 100 pages max
                filter_query = arguments.get("filter")
                orderby = arguments.get("orderby")

                # Validate site identification
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]

                # Get site_id from site_url if needed
                if site_id is None:
                    try:
                        site_id = await get_site_id_from_url(
                            site_url, sharepoint_client=sharepoint
                        )
                    except ValueError as e:
                        return [types.TextContent(type="text", text=str(e))]

                # Build the request URL with the specific endpoint for site pages
                url = f"{GRAPH_SITES_URL}{site_id}/pages/microsoft.graph.sitePage"
                logger.info(f"Making request to list pages: {url}")

                # Prepare query parameters
                params = {}

                # Add optional parameters if provided
                if top:
                    params["$top"] = top

                if filter_query:
                    params["$filter"] = filter_query

                if orderby:
                    params["$orderby"] = orderby

                # Create the request headers
                page_headers = sharepoint["headers"].copy()
                page_headers["Accept"] = "application/json;odata.metadata=none"

                try:
                    # Make the API request to list site pages
                    # No request body needed as specified
                    response = requests.get(
                        url, headers=page_headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        pages = result.get("value", [])
                        page_count = len(pages)

                        # Format each page to include essential information
                        formatted_pages = []
                        for page in pages:
                            formatted_pages.append(
                                {
                                    "id": page.get("id"),
                                    "name": page.get("name"),
                                    "title": page.get("title"),
                                    "url": page.get("webUrl"),
                                    "createdDateTime": page.get("createdDateTime"),
                                    "lastModifiedDateTime": page.get(
                                        "lastModifiedDateTime"
                                    ),
                                }
                            )

                        # Format the response
                        formatted_result = {
                            "totalPages": page_count,
                            "siteId": site_id,
                            "pages": formatted_pages,
                        }

                        # Check if there's a next page link
                        if "@odata.nextLink" in result:
                            formatted_result["nextLink"] = result["@odata.nextLink"]
                            formatted_result["note"] = (
                                "There are more pages available. Refine your query or use the nextLink to retrieve more."
                            )

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully retrieved {page_count} pages from the SharePoint site:\n{json.dumps(formatted_result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error listing site pages: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during site pages listing: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_site_info":
                # Extract parameters for getting site information
                site_id = arguments.get("site_id")
                site_url = arguments.get("site_url")

                # Validate site identification
                if site_id is None and site_url is None:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: Either site_id or site_url must be provided",
                        )
                    ]

                # Get site_id from site_url if needed
                if site_id is None:
                    try:
                        site_id = await get_site_id_from_url(
                            site_url, sharepoint_client=sharepoint
                        )
                    except ValueError as e:
                        return [types.TextContent(type="text", text=str(e))]

                # Build the request URL to get site information
                url = f"{GRAPH_SITES_URL}{site_id}"
                logger.info(f"Making request to get site info: {url}")

                # Create the request headers
                site_headers = sharepoint["headers"].copy()
                site_headers["Accept"] = "application/json;odata.metadata=none"

                try:
                    # Make the API request to get site information
                    # No request body needed
                    response = requests.get(url, headers=site_headers, timeout=30)

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()

                        # Format the response to highlight important site information
                        formatted_result = {
                            "id": result.get("id"),
                            "name": result.get("name"),
                            "displayName": result.get("displayName"),
                            "description": result.get("description"),
                            "url": result.get("webUrl"),
                            "siteCollection": result.get("siteCollection"),
                            "createdDateTime": result.get("createdDateTime"),
                            "lastModifiedDateTime": result.get("lastModifiedDateTime"),
                            "root": result.get("root"),
                        }

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully retrieved information for SharePoint site:\n{json.dumps(formatted_result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error retrieving site information: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during site information retrieval: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "search_sites":
                # Extract parameters for searching sites
                search_query = arguments.get("query")

                # Validate required parameters
                if not search_query:
                    return [
                        types.TextContent(
                            type="text", text="Error: A search query must be provided"
                        )
                    ]

                # Build the request URL for site search
                url = f"{GRAPH_BASE_URL}sites"
                logger.info(f"Making request to search sites: {url}")

                # Prepare query parameters
                params = {
                    "search": search_query,
                }

                # Create the request headers
                search_headers = sharepoint["headers"].copy()
                search_headers["Accept"] = "application/json;odata.metadata=none"

                try:
                    # Make the API request to search sites
                    # No request body needed
                    response = requests.get(
                        url, headers=search_headers, params=params, timeout=30
                    )

                    # Log the response status
                    logger.info(f"Response status: {response.status_code}")

                    # Check if the request was successful
                    if response.status_code == 200:
                        result = response.json()
                        sites = result.get("value", [])
                        site_count = len(sites)

                        # Format each site to include essential information
                        formatted_sites = []
                        for site in sites:
                            formatted_sites.append(
                                {
                                    "id": site.get("id"),
                                    "name": site.get("name"),
                                    "displayName": site.get("displayName"),
                                    "description": site.get("description"),
                                    "url": site.get("webUrl"),
                                    "createdDateTime": site.get("createdDateTime"),
                                    "lastModifiedDateTime": site.get(
                                        "lastModifiedDateTime"
                                    ),
                                }
                            )

                        # Format the response
                        formatted_result = {
                            "totalSites": site_count,
                            "searchQuery": search_query,
                            "sites": formatted_sites,
                        }

                        # Check if there's a next page link
                        if "@odata.nextLink" in result:
                            formatted_result["nextLink"] = result["@odata.nextLink"]
                            formatted_result["note"] = (
                                "There are more sites available. Refine your query or use the nextLink to retrieve more."
                            )

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully found {site_count} sites matching '{search_query}':\n{json.dumps(formatted_result, indent=2)}",
                            )
                        ]
                    else:
                        error_message = f"Error searching sites: {response.status_code} - {response.text}"
                        logger.error(error_message)
                        return [types.TextContent(type="text", text=error_message)]

                except Exception as e:
                    error_message = f"Error during site search: {str(e)}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            else:
                return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error(f"Error calling SharePoint API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="sharepoint-server",
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
        print("  python main.py - Run the server")
