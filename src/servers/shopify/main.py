import os
import sys
import json
import httpx
from pathlib import Path
from typing import Optional, List, Dict, Any

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.shopify.util import get_credentials, get_service_config
from src.utils.shopify.graphql_schemas import (
    PRODUCTS_GRAPHQL_QUERY,
    PRODUCT_GRAPHQL_QUERY,
    SHOP_DETAILS_GRAPHQL_QUERY,
    PRODUCT_CREATE_GRAPHQL_MUTATION,
    PRODUCT_DELETE_GRAPHQL_MUTATION,
    INVENTORY_LEVEL_GRAPHQL_QUERY,
    INVENTORY_ADJUST_GRAPHQL_MUTATION,
    INVENTORY_ITEM_UPDATE_GRAPHQL_MUTATION,
    VARIANT_INVENTORY_ITEM_GRAPHQL_QUERY,
)

SERVICE_NAME = Path(__file__).parent.name


def authenticate_and_save_credentials(user_id, scopes=None):
    if scopes is None:
        scopes = [
            "read_products",
            "write_products",
            "read_inventory",
            "write_inventory",
            "read_locations",
        ]

    from src.utils.shopify.util import authenticate_and_save_credentials as auth_save

    return auth_save(user_id, SERVICE_NAME, scopes)


async def execute_graphql_query(user_id, query, variables=None, api_key=None):
    access_token = await get_credentials(user_id, SERVICE_NAME, api_key)

    config = await get_service_config(user_id, SERVICE_NAME, api_key)
    custom_subdomain = config.get("custom_subdomain")
    api_version = config.get("api_version", "2023-10")

    if not custom_subdomain:
        raise ValueError("Missing custom_subdomain in Shopify configuration")

    graphql_url = (
        f"https://{custom_subdomain}.myshopify.com/admin/api/{api_version}/graphql.json"
    )

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": access_token,
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    async with httpx.AsyncClient() as client:
        response = await client.post(
            graphql_url, json=payload, headers=headers, timeout=30.0
        )

        result = {"_status_code": response.status_code}
        try:
            response_data = response.json()
            result.update(response_data)
        except:
            result["text"] = response.text

        return result


def format_shopify_id(id_value, resource_type):
    if not id_value.startswith("gid://"):
        return f"gid://shopify/{resource_type}/{id_value}"
    return id_value


def create_server(user_id, api_key=None):
    server = Server("shopify-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> List[Resource]:
        return []

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        return [
            Tool(
                name="get_shop_details",
                description="Gets the details of a shop in Shopify",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="create_product",
                description="Creates a product on Shopify",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The name for the product that displays to customers",
                        },
                        "descriptionHtml": {
                            "type": "string",
                            "description": "The description of the product, with HTML tags",
                        },
                        "vendor": {
                            "type": "string",
                            "description": "The name of the product's vendor",
                        },
                        "productType": {
                            "type": "string",
                            "description": "The product type that merchants define",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "A list of searchable keywords associated with the product",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["DRAFT", "ACTIVE", "ARCHIVED"],
                            "description": "The product status, which controls visibility across all sales channels",
                        },
                        "handle": {
                            "type": "string",
                            "description": "A unique, human-readable string of the product's title used in the online store URL",
                        },
                        "giftCard": {
                            "type": "boolean",
                            "description": "Whether the product is a gift card",
                        },
                        "productOptions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the option (e.g., 'Color', 'Size')",
                                    },
                                    "values": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {"name": {"type": "string"}},
                                        },
                                        "description": "The values for the option (e.g., ['Red', 'Blue'] for a 'Color' option)",
                                    },
                                },
                                "required": ["name", "values"],
                            },
                            "description": "A list of product options and option values (max 3 options)",
                        },
                        "requiresSellingPlan": {
                            "type": "boolean",
                            "description": "Whether the product can only be purchased with a selling plan (subscription)",
                        },
                        "seo": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "SEO title",
                                },
                                "description": {
                                    "type": "string",
                                    "description": "SEO description",
                                },
                            },
                            "description": "The SEO title and description for the product",
                        },
                        "metafields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "namespace": {
                                        "type": "string",
                                        "description": "Metafield namespace",
                                    },
                                    "key": {
                                        "type": "string",
                                        "description": "Metafield key",
                                    },
                                    "value": {
                                        "type": "string",
                                        "description": "Metafield value",
                                    },
                                    "type": {
                                        "type": "string",
                                        "description": "Metafield type",
                                    },
                                },
                                "required": ["namespace", "key", "value", "type"],
                            },
                            "description": "Custom fields to associate with the product",
                        },
                        "templateSuffix": {
                            "type": "string",
                            "description": "The theme template used when customers view the product in a store",
                        },
                    },
                    "required": ["title"],
                },
            ),
            Tool(
                name="get_products",
                description="Retrieves a list of products from Shopify",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "first": {
                            "type": "integer",
                            "description": "The first n elements from the paginated list (default: 10)",
                        },
                        "query": {
                            "type": "string",
                            "description": "A search query to filter products. Supports Shopify's search syntax with filters such as title:, handle:, vendor:, product_type:, status: etc.",
                        },
                        "reverse": {
                            "type": "boolean",
                            "description": "Reverse the order of the underlying list",
                        },
                        "sortKey": {
                            "type": "string",
                            "enum": [
                                "CREATED_AT",
                                "ID",
                                "INVENTORY_TOTAL",
                                "PRODUCT_TYPE",
                                "PUBLISHED_AT",
                                "RELEVANCE",
                                "TITLE",
                                "UPDATED_AT",
                                "VENDOR",
                            ],
                            "description": "Sort the underlying list by a key",
                        },
                        "after": {
                            "type": "string",
                            "description": "Return items after this cursor",
                        },
                        "before": {
                            "type": "string",
                            "description": "Return items before this cursor",
                        },
                        "last": {
                            "type": "integer",
                            "description": "The last n elements from the paginated list",
                        },
                        "savedSearchId": {
                            "type": "string",
                            "description": "The ID of a saved search to use as the query",
                        },
                    },
                },
            ),
            Tool(
                name="get_product",
                description="Retrieves a single product from Shopify by product ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "ID of the product to retrieve",
                        },
                    },
                    "required": ["product_id"],
                },
            ),
            Tool(
                name="delete_product",
                description="Deletes a product from Shopify, including all associated variants and media",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the product to delete",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="get_inventory_level",
                description="Gets the inventory level for a specific inventory item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "inventory_item_id": {
                            "type": "string",
                            "description": "ID of the inventory item",
                        },
                        "location_id": {
                            "type": "string",
                            "description": "ID of the location (optional)",
                        },
                    },
                    "required": ["inventory_item_id"],
                },
            ),
            Tool(
                name="adjust_inventory",
                description="Adjusts inventory levels for a specific inventory item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "inventory_level_id": {
                            "type": "string",
                            "description": "ID of the inventory level to adjust",
                        },
                        "quantity_adjustment": {
                            "type": "integer",
                            "description": "Amount to adjust inventory quantity by (positive or negative)",
                        },
                    },
                    "required": [
                        "inventory_level_id",
                        "quantity_adjustment",
                    ],
                },
            ),
            Tool(
                name="update_inventory_tracking",
                description="Enable or disable inventory tracking for a specific inventory item",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "inventory_item_id": {
                            "type": "string",
                            "description": "ID of the inventory item to update",
                        },
                        "tracked": {
                            "type": "boolean",
                            "description": "Whether to enable (true) or disable (false) inventory tracking",
                        },
                    },
                    "required": [
                        "inventory_item_id",
                        "tracked",
                    ],
                },
            ),
            Tool(
                name="get_variant_inventory_item",
                description="Gets the inventory item ID for a specific product variant",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "variant_id": {
                            "type": "string",
                            "description": "ID of the product variant",
                        },
                    },
                    "required": ["variant_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        endpoints = {
            "get_products": {
                "query": PRODUCTS_GRAPHQL_QUERY,
                "variables": lambda args: {
                    "first": args.get("first", 10),
                    "query": args.get("query", ""),
                    "sortKey": args.get("sortKey", "ID"),
                    "reverse": args.get("reverse", False),
                    "after": args.get("after"),
                    "before": args.get("before"),
                    "last": args.get("last"),
                    "savedSearchId": args.get("savedSearchId"),
                },
            },
            "get_product": {
                "query": PRODUCT_GRAPHQL_QUERY,
                "variables": lambda args: {
                    "id": format_shopify_id(args["product_id"], "Product")
                },
            },
            "get_shop_details": {
                "query": SHOP_DETAILS_GRAPHQL_QUERY,
                "variables": lambda _: {},
            },
            "create_product": {
                "query": PRODUCT_CREATE_GRAPHQL_MUTATION,
                "variables": lambda args: {
                    "input": {
                        **args,
                        "bodyHtml": args.get("descriptionHtml"),
                    }
                },
            },
            "delete_product": {
                "query": PRODUCT_DELETE_GRAPHQL_MUTATION,
                "variables": lambda args: {
                    "input": {"id": format_shopify_id(args["id"], "Product")}
                },
            },
            "get_inventory_level": {
                "query": INVENTORY_LEVEL_GRAPHQL_QUERY,
                "variables": lambda args: {
                    "inventoryItemId": format_shopify_id(
                        args["inventory_item_id"], "InventoryItem"
                    ),
                    "locationId": (
                        format_shopify_id(args.get("location_id", "1"), "Location")
                        if args.get("location_id")
                        else None
                    ),
                },
            },
            "adjust_inventory": {
                "query": INVENTORY_ADJUST_GRAPHQL_MUTATION,
                "variables": lambda args: {
                    "input": {
                        "inventoryLevelId": args.get("inventory_level_id"),
                        "availableDelta": args["quantity_adjustment"],
                    }
                },
            },
            "update_inventory_tracking": {
                "query": INVENTORY_ITEM_UPDATE_GRAPHQL_MUTATION,
                "variables": lambda args: {
                    "inventoryItemId": format_shopify_id(
                        args["inventory_item_id"], "InventoryItem"
                    ),
                    "tracked": args["tracked"],
                },
            },
            "get_variant_inventory_item": {
                "query": VARIANT_INVENTORY_ITEM_GRAPHQL_QUERY,
                "variables": lambda args: {
                    "variantId": format_shopify_id(args["variant_id"], "ProductVariant")
                },
            },
        }

        arguments = arguments or {}

        if name in endpoints:
            endpoint_info = endpoints[name]
            try:
                query = endpoint_info["query"]
                if callable(query):
                    query = query(arguments)

                variables_func = endpoint_info["variables"]
                variables = (
                    variables_func(arguments)
                    if callable(variables_func)
                    else variables_func
                )

                result = await execute_graphql_query(
                    server.user_id, query, variables=variables, api_key=server.api_key
                )

                if (
                    result.get("_status_code") >= 200
                    and result.get("_status_code") < 300
                ):
                    return [
                        TextContent(
                            type="text", text=f"Success: {json.dumps(result, indent=2)}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text", text=f"Error: {json.dumps(result, indent=2)}"
                        )
                    ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Error executing {name}: {str(e)}")
                ]

        return [TextContent(type="text", text=f"Tool '{name}' is not yet implemented.")]

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
        authenticate_and_save_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
