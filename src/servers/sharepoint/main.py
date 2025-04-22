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
    "Sites.Read.All",
    "Sites.ReadWrite.All",
    "User.Read.All",
    "User.ReadWrite.All",
    "Directory.Read.All",
    "Sites.Manage.All",
    "Directory.ReadWrite.All",
    "Directory.AccessAsUser.All",
    "User.Read",
    "offline_access",
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
        response = requests.get(request_url, headers=sharepoint_client["headers"])

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

        # Ensure arguments is a dictionary - handle string inputs
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                arguments = {"error": "Invalid JSON input"}
                logger.error(f"Invalid arguments format: {arguments}")
                return [
                    types.TextContent(
                        type="text",
                        text="Error: Invalid arguments format. Arguments must be a valid JSON object.",
                    )
                ]

        try:
            if name == "get_users":
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

                # Log the request details
                logger.info(f"Making request to {url}")
                logger.info(f"Headers: {sharepoint['headers']}")
                logger.info(f"Params: {params}")

                # Make the API request to get users
                response = requests.get(
                    url, headers=sharepoint["headers"], params=params
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

                # Log the request details (without sensitive data)
                logger.info(f"Making request to {url}")
                logger.info(f"Data: {list_data}")

                # Make the API request to create the list
                response = requests.post(
                    url, headers=sharepoint["headers"], json=list_data
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

                # Log the request details
                logger.info(f"Making request to {url}")

                # Make the API request to get the list
                response = requests.get(url, headers=sharepoint["headers"])

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

                # Log the request details
                logger.info(f"Making request to {url}")
                logger.info(f"Headers: {sharepoint['headers']}")
                logger.info(f"Data: {item_data}")

                # Make the API request to create the list item
                response = requests.post(
                    url, headers=sharepoint["headers"], json=item_data
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

                # Log the request details
                logger.info(f"Making request to {url}")
                logger.info(f"Headers: {sharepoint['headers']}")

                # Make the API request to get the list item
                response = requests.get(url, headers=sharepoint["headers"])

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

                # Log the request details
                logger.info(f"Making request to {url}")
                logger.info(f"Headers: {sharepoint['headers']}")
                logger.info(f"Params: {params}")

                # Make the API request to get the list items
                response = requests.get(
                    url, headers=sharepoint["headers"], params=params
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

                # Log the request details
                logger.info(f"Making DELETE request to {url}")
                logger.info(f"Headers: {sharepoint['headers']}")

                # Make the API request to delete the list item
                response = requests.delete(url, headers=sharepoint["headers"])

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
