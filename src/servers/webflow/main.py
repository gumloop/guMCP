import os
import sys
import httpx
import logging
import json
from pathlib import Path
from typing import Optional

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import Resource, TextContent, Tool, ImageContent, EmbeddedResource
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.webflow.utils import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
WEBFLOW_API_BASE_URL = "https://api.webflow.com/v2"
SCOPES = [
    "authorized_user:read",
    "sites:read",
    "forms:read",
    "forms:write",
    "pages:read",
    "cms:read",
    "cms:write",
    "users:read",
    "users:write",
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def make_webflow_request(
    method, endpoint, data=None, params=None, access_token=None
):
    """Execute a request against the Webflow API with improved error handling"""
    if not access_token:
        raise ValueError("Webflow access token is required")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    url = f"{WEBFLOW_API_BASE_URL}{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "post":
                response = await client.post(
                    url, json=data, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "patch":
                response = await client.patch(
                    url, json=data, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "delete":
                response = await client.delete(
                    url, headers=headers, params=params, timeout=30.0
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            response_json = response.json() if response.text else {}
            response_json["_status_code"] = response.status_code
            return response_json
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        try:
            error_details = e.response.json()
            return {"error": error_details, "_status_code": e.response.status_code}
        except:
            pass
        raise ValueError(f"Webflow API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Error making request to Webflow API: {str(e)}")
        raise ValueError(f"Error communicating with Webflow API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(cursor=None) -> list[Resource]:
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="get_authorized_user",
                description="Get information about the authorized Webflow user",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="list_sites",
                description="List all sites the provided access token is able to access",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_site",
                description="Get details of a specific site by its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="get_custom_domains",
                description="Get a list of all custom domains related to a site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="list_forms",
                description="List forms for a given site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="list_form_submissions",
                description="List form submissions for a given form",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "Unique identifier for a Form",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                    },
                    "required": ["form_id"],
                },
            ),
            Tool(
                name="get_form_submission",
                description="Get information about a specific form submission",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_submission_id": {
                            "type": "string",
                            "description": "Unique identifier for a Form Submission",
                        },
                    },
                    "required": ["form_submission_id"],
                },
            ),
            Tool(
                name="list_form_submissions_by_site",
                description="List form submissions for a given site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "element_id": {
                            "type": "string",
                            "description": "Identifier for an element",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="delete_form_submission",
                description="Delete a form submission",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_submission_id": {
                            "type": "string",
                            "description": "Unique identifier for a Form Submission",
                        },
                    },
                    "required": ["form_submission_id"],
                },
            ),
            Tool(
                name="list_pages",
                description="List all pages for a site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a specific locale. Applicable when using localization.",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="get_page_metadata",
                description="Get metadata information for a single page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Unique identifier for a Page",
                        },
                        "locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a specific locale. Applicable when using localization.",
                        },
                    },
                    "required": ["page_id"],
                },
            ),
            Tool(
                name="get_page_content",
                description="Get content from a static page",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Unique identifier for a Page",
                        },
                        "locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a specific locale. Applicable when using localization.",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                    },
                    "required": ["page_id"],
                },
            ),
            Tool(
                name="list_collections",
                description="List all Collections within a Site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="get_collection",
                description="Get the full details of a collection from its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                    },
                    "required": ["collection_id"],
                },
            ),
            Tool(
                name="delete_collection",
                description="Delete a collection using its ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                    },
                    "required": ["collection_id"],
                },
            ),
            Tool(
                name="create_collection",
                description="Create a Collection for a site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "displayName": {
                            "type": "string",
                            "description": "Name of the collection. Each collection name must be distinct.",
                        },
                        "singularName": {
                            "type": "string",
                            "description": "Singular name of each item.",
                        },
                        "slug": {
                            "type": "string",
                            "description": "Part of a URL that identifies the collection",
                        },
                        "fields": {
                            "type": "array",
                            "description": "An array of custom fields to add to the collection",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["site_id", "displayName", "singularName"],
                },
            ),
            Tool(
                name="list_collection_items_staging",
                description="List all Items within a Collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "cms_locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a CMS Locale",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Filter by the exact name of the item(s)",
                        },
                        "slug": {
                            "type": "string",
                            "description": "Filter by the exact slug of the item",
                        },
                        "last_published": {
                            "type": "object",
                            "description": "Filter by the last published date of the item(s)",
                        },
                        "sort_by": {
                            "type": "string",
                            "description": "Sort results by the provided value (lastPublished, name, slug)",
                        },
                        "sort_order": {
                            "type": "string",
                            "description": "Sorts the results by asc or desc",
                        },
                    },
                    "required": ["collection_id"],
                },
            ),
            Tool(
                name="get_collection_item_staging",
                description="Get details of a selected Collection Item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "Unique identifier for an Item",
                        },
                        "cms_locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a CMS Locale",
                        },
                    },
                    "required": ["collection_id", "item_id"],
                },
            ),
            Tool(
                name="update_collection_item_staging",
                description="Update a selected Item in a Collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "Unique identifier for an Item",
                        },
                        "cms_locale_id": {
                            "type": "string",
                            "description": "Identifier for the locale of the CMS item",
                        },
                        "is_archived": {
                            "type": "boolean",
                            "description": "Boolean determining if the Item is set to archived",
                        },
                        "is_draft": {
                            "type": "boolean",
                            "description": "Boolean determining if the Item is set to draft",
                        },
                        "field_data": {
                            "type": "object",
                            "description": "Fields to update for the item",
                        },
                    },
                    "required": ["collection_id", "item_id"],
                },
            ),
            Tool(
                name="update_collection_items_staging",
                description="Update a single item or multiple items in a Collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "items": {
                            "type": "array",
                            "description": "Array of items to update",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Unique identifier for the Item",
                                    },
                                    "cms_locale_id": {
                                        "type": "string",
                                        "description": "Identifier for the locale of the CMS item",
                                    },
                                    "is_archived": {
                                        "type": "boolean",
                                        "description": "Boolean determining if the Item is set to archived",
                                    },
                                    "is_draft": {
                                        "type": "boolean",
                                        "description": "Boolean determining if the Item is set to draft",
                                    },
                                    "field_data": {
                                        "type": "object",
                                        "description": "Fields to update for the item",
                                    },
                                },
                                "required": ["id"],
                            },
                        },
                    },
                    "required": ["collection_id", "items"],
                },
            ),
            Tool(
                name="create_collection_item_staging",
                description="Create Item in a Collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "is_archived": {
                            "type": "boolean",
                            "description": "Boolean determining if the Item is set to archived",
                        },
                        "is_draft": {
                            "type": "boolean",
                            "description": "Boolean determining if the Item is set to draft",
                        },
                        "field_data": {
                            "type": "object",
                            "description": "Fields for the new item including name and slug",
                        },
                    },
                    "required": ["collection_id", "field_data"],
                },
            ),
            Tool(
                name="delete_collection_item_staging",
                description="Delete an item from a collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "Unique identifier for an Item",
                        },
                        "cms_locale_id": {
                            "type": "string",
                            "description": "Unique identifier for a CMS Locale",
                        },
                    },
                    "required": ["collection_id", "item_id"],
                },
            ),
            Tool(
                name="delete_collection_items_staging",
                description="Delete Items from a Collection",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "collection_id": {
                            "type": "string",
                            "description": "Unique identifier for a Collection",
                        },
                        "items": {
                            "type": "array",
                            "description": "Array of items to delete",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Unique identifier for the Item",
                                    },
                                    "cms_locale_id": {
                                        "type": "string",
                                        "description": "Identifier for the locale of the CMS item",
                                    },
                                },
                                "required": ["id"],
                            },
                        },
                    },
                    "required": ["collection_id", "items"],
                },
            ),
            Tool(
                name="list_users",
                description="Get a list of users for a site",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "offset": {
                            "type": "number",
                            "description": "Offset used for pagination if the results have more than limit records",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of records to be returned (max limit: 100)",
                        },
                        "sort": {
                            "type": "string",
                            "description": "Sort string to use when ordering users (e.g., CreatedOn, Email, Status, LastLogin, UpdatedOn)",
                        },
                    },
                    "required": ["site_id"],
                },
            ),
            Tool(
                name="get_user",
                description="Get a User by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Unique identifier for a User",
                        },
                    },
                    "required": ["site_id", "user_id"],
                },
            ),
            Tool(
                name="delete_user",
                description="Delete a User by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Unique identifier for a User",
                        },
                    },
                    "required": ["site_id", "user_id"],
                },
            ),
            Tool(
                name="invite_user",
                description="Create and invite a user with an email address",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "site_id": {
                            "type": "string",
                            "description": "Unique identifier for a Site",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of user to send invite to",
                        },
                        "accessGroups": {
                            "type": "array",
                            "description": "An array of access group slugs",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["site_id", "email"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_credentials(
            user_id, SERVICE_NAME, api_key=server.api_key
        )
        arguments = arguments or {}

        endpoints = {
            "get_authorized_user": {
                "method": "get",
                "endpoint": "/token/authorized_by",
            },
            "list_sites": {"method": "get", "endpoint": "/sites"},
            "get_site": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}",
            },
            "get_custom_domains": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/custom_domains",
            },
            "list_forms": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/forms",
            },
            "list_form_submissions": {
                "method": "get",
                "endpoint": lambda args: f"/forms/{args.pop('form_id')}/submissions",
            },
            "get_form_submission": {
                "method": "get",
                "endpoint": lambda args: f"/form_submissions/{args.pop('form_submission_id')}",
            },
            "list_form_submissions_by_site": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/form_submissions",
                "param_mapping": {
                    "element_id": "elementId",
                },
            },
            "delete_form_submission": {
                "method": "delete",
                "endpoint": lambda args: f"/form_submissions/{args.pop('form_submission_id')}",
            },
            "list_pages": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/pages",
                "param_mapping": {
                    "locale_id": "localeId",
                },
            },
            "get_page_metadata": {
                "method": "get",
                "endpoint": lambda args: f"/pages/{args.pop('page_id')}",
                "param_mapping": {
                    "locale_id": "localeId",
                },
            },
            "get_page_content": {
                "method": "get",
                "endpoint": lambda args: f"/pages/{args.pop('page_id')}/dom",
                "param_mapping": {
                    "locale_id": "localeId",
                },
            },
            "list_collections": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/collections",
            },
            "get_collection": {
                "method": "get",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}",
            },
            "delete_collection": {
                "method": "delete",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}",
            },
            "create_collection": {
                "method": "post",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/collections",
            },
            "list_collection_items_staging": {
                "method": "get",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items",
                "param_mapping": {
                    "cms_locale_id": "cmsLocaleId",
                    "last_published": "lastPublished",
                    "sort_by": "sortBy",
                    "sort_order": "sortOrder",
                },
            },
            "get_collection_item_staging": {
                "method": "get",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items/{args.pop('item_id')}",
                "param_mapping": {
                    "cms_locale_id": "cmsLocaleId",
                },
            },
            "update_collection_item_staging": {
                "method": "patch",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items/{args.pop('item_id')}",
                "param_mapping": {
                    "cms_locale_id": "cmsLocaleId",
                    "is_archived": "isArchived",
                    "is_draft": "isDraft",
                    "field_data": "fieldData",
                },
            },
            "update_collection_items_staging": {
                "method": "patch",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items",
                "param_preprocessing": lambda args: (
                    {
                        "items": [
                            {
                                "id": item.get("id"),
                                "cmsLocaleId": item.get("cms_locale_id"),
                                "isArchived": item.get("is_archived"),
                                "isDraft": item.get("is_draft"),
                                "fieldData": item.get("field_data"),
                            }
                            for item in args.get("items", [])
                        ]
                    }
                    if "items" in args
                    else args
                ),
            },
            "create_collection_item_staging": {
                "method": "post",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items",
                "param_mapping": {
                    "is_archived": "isArchived",
                    "is_draft": "isDraft",
                    "field_data": "fieldData",
                },
            },
            "delete_collection_item_staging": {
                "method": "delete",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items/{args.pop('item_id')}",
                "param_mapping": {
                    "cms_locale_id": "cmsLocaleId",
                },
            },
            "delete_collection_items_staging": {
                "method": "delete",
                "endpoint": lambda args: f"/collections/{args.pop('collection_id')}/items",
                "param_preprocessing": lambda args: (
                    {
                        "items": [
                            {
                                "id": item.get("id"),
                                "cmsLocaleId": item.get("cms_locale_id"),
                            }
                            for item in args.get("items", [])
                        ]
                    }
                    if "items" in args
                    else args
                ),
            },
            "list_users": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/users",
            },
            "get_user": {
                "method": "get",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/users/{args.pop('user_id')}",
            },
            "delete_user": {
                "method": "delete",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/users/{args.pop('user_id')}",
            },
            "invite_user": {
                "method": "post",
                "endpoint": lambda args: f"/sites/{args.pop('site_id')}/users/invite",
            },
        }

        if name not in endpoints:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            endpoint_info = endpoints[name]
            method = endpoint_info["method"]

            if callable(endpoint_info["endpoint"]):
                endpoint = endpoint_info["endpoint"](arguments)
            else:
                endpoint = endpoint_info["endpoint"]

            data = arguments if method in ["post", "patch"] else None
            params = arguments if method in ["get", "delete"] else None

            if params and "param_mapping" in endpoint_info:
                mapped_params = {}
                for param_key, param_value in params.items():
                    if param_key in endpoint_info["param_mapping"]:
                        mapped_params[endpoint_info["param_mapping"][param_key]] = (
                            param_value
                        )
                    else:
                        mapped_params[param_key] = param_value
                params = mapped_params

            # Apply param_mapping to data for POST/PATCH requests
            if data and "param_mapping" in endpoint_info:
                mapped_data = {}
                for param_key, param_value in data.items():
                    if param_key in endpoint_info["param_mapping"]:
                        mapped_data[endpoint_info["param_mapping"][param_key]] = (
                            param_value
                        )
                    else:
                        mapped_data[param_key] = param_value
                data = mapped_data

            response = await make_webflow_request(
                method,
                endpoint,
                data=data,
                params=params,
                access_token=access_token,
            )

            if (
                name == "get_authorized_user"
                and "_status_code" in response
                and response["_status_code"] == 200
            ):
                formatted_response = (
                    f"Authorized User Information:\n\n"
                    f"ID: {response.get('id', 'N/A')}\n"
                    f"Email: {response.get('email', 'N/A')}\n"
                    f"First Name: {response.get('firstName', 'N/A')}\n"
                    f"Last Name: {response.get('lastName', 'N/A')}"
                )
                return [TextContent(type="text", text=formatted_response)]

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error using {name} tool: {str(e)}")]

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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
