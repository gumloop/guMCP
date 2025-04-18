import os
import sys
import httpx
import logging
from pathlib import Path

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

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

from src.auth.factory import create_auth_client


SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_instacart_key(user_id):
    """Authenticate with instacart and save API key"""
    logger = logging.getLogger("instacart")

    logger.info(f"Starting instacart authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Instacart API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("instacart", user_id, {"api_key": api_key})

    logger.info(
        f"Instacart API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_instacart_credentials(user_id, api_key=None):
    """Get instacart API key for the specified user"""
    logger = logging.getLogger("instacart")

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("instacart", user_id)

    def handle_missing_credentials():
        error_str = f"Instacart API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        # In the case of GumloopAuthClient, api key is returned directly
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


async def make_instacart_request(endpoint, data, api_key):
    """Make a request to the Instacart API"""
    base_url = "https://connect.instacart.com/idp/v1"
    # base_url = "https://connect.dev.instacart.tools/idp/v1" -- If using dev endpoint

    url = f"{base_url}/{endpoint}"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        )
        raise ValueError(
            f"Instacart API error: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Error making request to Instacart API: {str(e)}")
        raise ValueError(f"Error communicating with Instacart API: {str(e)}")


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("instacart-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="create_shopping_list",
                description="Create a shopping list page on Instacart",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the shopping list",
                        },
                        "image_url": {
                            "type": "string",
                            "description": "URL of the image to display on the page (Optional)",
                        },
                        "instructions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional instructions for the shopping list",
                        },
                        "line_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Product name (required)",
                                    },
                                    "quantity": {
                                        "type": "number",
                                        "description": "Product quantity (Optional, defaults to 1)",
                                    },
                                    "unit": {
                                        "type": "string",
                                        "description": "Unit of measurement (Optional, defaults to 'each')",
                                    },
                                    "display_text": {
                                        "type": "string",
                                        "description": "Display text for the product (Optional)",
                                    },
                                },
                                "required": ["name"],
                            },
                            "description": "Array of product items to include in the shopping list",
                        },
                        "partner_linkback_url": {
                            "type": "string",
                            "description": "URL to link back to your site (Optional)",
                        },
                    },
                    "required": ["title", "line_items"],
                },
            ),
            Tool(
                name="create_recipe",
                description="Create a recipe page on Instacart",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "The title of the recipe",
                        },
                        "image_url": {
                            "type": "string",
                            "description": "URL of the image to display on the page (Optional)",
                        },
                        "author": {
                            "type": "string",
                            "description": "The author of the recipe (Optional)",
                        },
                        "servings": {
                            "type": "integer",
                            "description": "The number of servings the recipe makes (Optional)",
                        },
                        "cooking_time": {
                            "type": "integer",
                            "description": "The time it takes to cook the recipe in minutes (Optional)",
                        },
                        "instructions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Step-by-step instructions for the recipe",
                        },
                        "ingredients": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Ingredient name (required)",
                                    },
                                    "display_text": {
                                        "type": "string",
                                        "description": "Display text for the ingredient (Optional)",
                                    },
                                    "quantity": {
                                        "type": "number",
                                        "description": "Ingredient quantity (Optional)",
                                    },
                                    "unit": {
                                        "type": "string",
                                        "description": "Unit of measurement (Optional)",
                                    },
                                },
                                "required": ["name"],
                            },
                            "description": "Array of ingredients for the recipe",
                        },
                        "partner_linkback_url": {
                            "type": "string",
                            "description": "URL to link back to your site (Optional)",
                        },
                        "enable_pantry_items": {
                            "type": "boolean",
                            "description": "Whether to enable pantry items feature (Optional, defaults to false)",
                        },
                    },
                    "required": ["title", "ingredients"],
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

        api_key = await get_instacart_credentials(server.user_id, server.api_key)

        if name == "create_shopping_list":
            if (
                not arguments
                or "title" not in arguments
                or "line_items" not in arguments
            ):
                return [
                    TextContent(
                        type="text",
                        text="Missing required parameters: title and line_items",
                    )
                ]

            # Prepare request data
            request_data = {"title": arguments["title"], "link_type": "shopping_list"}

            # Add optional fields if provided
            if "image_url" in arguments and arguments["image_url"]:
                request_data["image_url"] = arguments["image_url"]

            if "instructions" in arguments and arguments["instructions"]:
                request_data["instructions"] = arguments["instructions"]

            # Process line items
            line_items = []
            for item in arguments["line_items"]:
                line_item = {"name": item["name"]}

                if "quantity" in item:
                    line_item["quantity"] = item["quantity"]

                if "unit" in item:
                    line_item["unit"] = item["unit"]

                if "display_text" in item:
                    line_item["display_text"] = item["display_text"]

                line_items.append(line_item)

            request_data["line_items"] = line_items

            # Add landing page configuration if partner_linkback_url is provided
            if (
                "partner_linkback_url" in arguments
                and arguments["partner_linkback_url"]
            ):
                request_data["landing_page_configuration"] = {
                    "partner_linkback_url": arguments["partner_linkback_url"]
                }

            try:
                # Make API request to create shopping list
                response = await make_instacart_request(
                    "products/products_link", request_data, api_key
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Shopping list '{arguments['title']}' created successfully! You can access it at: {response['products_link_url']}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Error creating shopping list: {str(e)}"
                    )
                ]

        elif name == "create_recipe":
            if (
                not arguments
                or "title" not in arguments
                or "ingredients" not in arguments
            ):
                return [
                    TextContent(
                        type="text",
                        text="Missing required parameters: title and ingredients",
                    )
                ]

            # Prepare request data
            request_data = {"title": arguments["title"]}

            # Add optional fields if provided
            for field in [
                "image_url",
                "author",
                "servings",
                "cooking_time",
                "instructions",
            ]:
                if field in arguments and arguments[field]:
                    request_data[field] = arguments[field]

            # Process ingredients
            ingredients = []
            for ing in arguments["ingredients"]:
                ingredient = {"name": ing["name"]}

                if "display_text" in ing:
                    ingredient["display_text"] = ing["display_text"]

                # Handle measurements
                if "quantity" in ing and "unit" in ing:
                    ingredient["measurements"] = [
                        {"quantity": ing["quantity"], "unit": ing["unit"]}
                    ]

                ingredients.append(ingredient)

            request_data["ingredients"] = ingredients

            # Add landing page configuration
            landing_config = {}
            if (
                "partner_linkback_url" in arguments
                and arguments["partner_linkback_url"]
            ):
                landing_config["partner_linkback_url"] = arguments[
                    "partner_linkback_url"
                ]

            if "enable_pantry_items" in arguments:
                landing_config["enable_pantry_items"] = arguments["enable_pantry_items"]

            if landing_config:
                request_data["landing_page_configuration"] = landing_config

            try:
                # Make API request to create recipe
                response = await make_instacart_request(
                    "products/recipe", request_data, api_key
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Recipe '{arguments['title']}' created successfully! You can access it at: {response['products_link_url']}",
                    )
                ]
            except Exception as e:
                return [
                    TextContent(type="text", text=f"Error creating recipe: {str(e)}")
                ]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="instacart-server",
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
        authenticate_and_save_instacart_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
