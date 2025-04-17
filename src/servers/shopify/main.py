import os
import sys
import logging
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

from src.auth.factory import create_auth_client
from src.utils.shopify.util import get_credentials, get_service_config

SERVICE_NAME = Path(__file__).parent.name

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_credentials(user_id, scopes=None):
    """Authenticate with Shopify and save credentials"""
    if scopes is None:
        scopes = ["read_products", "write_products"]

    logger.info(f"Starting Shopify authentication for user {user_id}...")

    from src.utils.shopify.util import authenticate_and_save_credentials as auth_save

    credentials = auth_save(user_id, SERVICE_NAME, scopes)

    logger.info(f"Shopify credentials saved for user {user_id}.")
    return credentials


async def execute_graphql_query(user_id, query, variables=None, api_key=None):
    """Execute a GraphQL query against the Shopify API"""
    try:
        # Get access token
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key)

        # Get shop configuration
        config = await get_service_config(user_id, SERVICE_NAME, api_key)
        custom_subdomain = config.get("custom_subdomain")
        api_version = config.get("api_version", "2023-10")

        if not custom_subdomain:
            raise ValueError("Missing custom_subdomain in Shopify configuration")

        # Construct GraphQL endpoint
        graphql_url = f"https://{custom_subdomain}.myshopify.com/admin/api/{api_version}/graphql.json"

        # Prepare request
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        }

        payload = {"query": query}

        if variables:
            payload["variables"] = variables

        # Execute request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                graphql_url, json=payload, headers=headers, timeout=30.0
            )

            # Check status code
            response.raise_for_status()

            # Return response data
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error executing GraphQL query: {str(e)}")

        try:
            error_details = e.response.json()
            if isinstance(error_details, dict) and "errors" in error_details:
                return {"errors": error_details["errors"]}
        except:
            pass

        raise ValueError(f"Shopify GraphQL error: HTTP {e.response.status_code}")

    except Exception as e:
        logger.error(f"Error executing GraphQL query: {str(e)}")
        raise ValueError(f"Error executing Shopify GraphQL query: {str(e)}")


def create_server(user_id, api_key=None):
    server = Server("shopify-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> List[Resource]:
        logger.info(f"Listing resources for user: {server.user_id}")
        return []

    @server.list_tools()
    async def handle_list_tools() -> List[Tool]:
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="graphql",
                description="Execute a GraphQL query against the Shopify API",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The GraphQL query to execute",
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables for the GraphQL query",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: Dict[str, Any] | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        logger.info(f"User {server.user_id} calling tool: {name}")

        if name == "graphql":
            try:
                query = arguments.get("query")
                variables = arguments.get("variables")

                if not query:
                    return [
                        TextContent(
                            type="text", text="Error: GraphQL query is required"
                        )
                    ]

                # Execute GraphQL query
                result = await execute_graphql_query(
                    server.user_id, query, variables, server.api_key
                )

                # Check for errors in the GraphQL response
                if result.get("errors"):
                    return [
                        TextContent(
                            type="text",
                            text=f"GraphQL query error: {json.dumps(result['errors'], indent=2)}",
                        )
                    ]

                # Return successful result
                return [
                    TextContent(
                        type="text",
                        text=f"GraphQL query successful: {json.dumps(result, indent=2)}",
                    )
                ]

            except Exception as e:
                return [
                    TextContent(
                        type="text", text=f"Error executing GraphQL query: {str(e)}"
                    )
                ]

        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name=f"{SERVICE_NAME}-server",
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
        authenticate_and_save_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
