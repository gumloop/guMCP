import os
import sys
import httpx
import logging
import json
from pathlib import Path

# Add project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    TextContent,
    Tool,
)
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client


SERVICE_NAME = Path(__file__).parent.name
SERPAPI_BASE_URL = "https://serpapi.com/search"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_serpapi_key(user_id):
    auth_client = create_auth_client()

    api_key = input("Please enter your SerpAPI API key: ").strip()
    if not api_key:
        raise ValueError("API key cannot be empty")

    auth_client.save_user_credentials("serpapi", user_id, {"api_key": api_key})
    return api_key


async def get_serpapi_credentials(user_id, api_key=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("serpapi", user_id)

    if not credentials_data:
        error_str = f"SerpAPI API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        raise ValueError(error_str)

    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        raise ValueError(f"SerpAPI API key not found for user {user_id}.")

    return api_key


async def make_serpapi_request(params, api_key):
    params["api_key"] = api_key

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(SERPAPI_BASE_URL, params=params, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            result["_status_code"] = response.status_code
            return result
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error occurred: {e.response.status_code} - {e.response.text}"
        )
        return {
            "error": f"SerpAPI error: {e.response.status_code} - {e.response.text}",
            "_status_code": e.response.status_code,
        }
    except Exception as e:
        logger.error(f"Error making request to SerpAPI: {str(e)}")
        return {
            "error": f"Error communicating with SerpAPI: {str(e)}",
            "_status_code": 500,
        }


def create_server(user_id, api_key=None):
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="serpapi_search",
                description="Search Google using SerpAPI",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {
                            "type": "string",
                            "description": "The search query.",
                        },
                        "search_type": {
                            "type": "string",
                            "description": "The type of search to perform: 'web' (default), 'images', 'news', 'videos', 'shopping', 'patents', etc.",
                            "enum": [
                                "web",
                                "images",
                                "news",
                                "videos",
                                "shopping",
                                "patents",
                                "local",
                            ],
                        },
                        "location": {
                            "type": "string",
                            "description": "The location to perform the search from.",
                        },
                        "uule": {
                            "type": "string",
                            "description": "Google encoded location to use for search. Cannot be used with location parameter.",
                        },
                        "ludocid": {
                            "type": "string",
                            "description": "ID (CID) of the Google My Business listing to scrape.",
                        },
                        "lsig": {
                            "type": "string",
                            "description": "Parameter to force knowledge graph map view to show up.",
                        },
                        "kgmid": {
                            "type": "string",
                            "description": "ID of the Google Knowledge Graph listing to scrape.",
                        },
                        "si": {
                            "type": "string",
                            "description": "Cached search parameters of the Google Search to scrape.",
                        },
                        "ibp": {
                            "type": "string",
                            "description": "Parameter for rendering layouts and expansions.",
                        },
                        "uds": {
                            "type": "string",
                            "description": "Parameter to filter search.",
                        },
                        "google_domain": {
                            "type": "string",
                            "description": "The Google domain to use (defaults to google.com).",
                        },
                        "gl": {
                            "type": "string",
                            "description": "The country code for the search.",
                        },
                        "hl": {
                            "type": "string",
                            "description": "The language code for the search.",
                        },
                        "cr": {
                            "type": "string",
                            "description": "Countries to limit the search to (e.g., 'countryFR|countryDE').",
                        },
                        "lr": {
                            "type": "string",
                            "description": "Languages to limit the search to (e.g., 'lang_fr|lang_de').",
                        },
                        "tbs": {
                            "type": "string",
                            "description": "Advanced search parameters for patents, dates, news, etc.",
                        },
                        "num": {
                            "type": "integer",
                            "description": "The number of results to return (defaults to 10).",
                        },
                        "start": {
                            "type": "integer",
                            "description": "Result offset for pagination.",
                        },
                        "safe": {
                            "type": "string",
                            "description": "Safe search setting ('active' or 'off').",
                        },
                        "nfpr": {
                            "type": "integer",
                            "description": "Set to 1 to exclude results from auto-corrected queries when original query is spelled wrong.",
                        },
                        "filter": {
                            "type": "integer",
                            "description": "Set to 1 (default) to enable 'Similar Results' and 'Omitted Results' filters, or 0 to disable.",
                        },
                        "device": {
                            "type": "string",
                            "description": "Device to use: 'desktop' (default), 'tablet', or 'mobile'.",
                            "enum": ["desktop", "tablet", "mobile"],
                        },
                        "no_cache": {
                            "type": "boolean",
                            "description": "Force SerpAPI to fetch fresh results even if cached version exists.",
                        },
                        "async": {
                            "type": "boolean",
                            "description": "Submit search asynchronously to retrieve later. Cannot be used with no_cache.",
                        },
                        "output": {
                            "type": "string",
                            "description": "Output format: 'json' (default) or 'html'.",
                            "enum": ["json", "html"],
                        },
                    },
                    "required": ["q"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        if name != "serpapi_search":
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        api_key = await get_serpapi_credentials(server.user_id, server.api_key)

        # Set up base parameters for all search types
        params = {"engine": "google"}

        # Handle search type
        search_type = arguments.get("search_type", "web")
        if search_type == "images":
            params["tbm"] = "isch"
        elif search_type == "news":
            params["tbm"] = "nws"

        # Add all other valid parameters
        valid_params = [
            "q",
            "location",
            "google_domain",
            "gl",
            "hl",
            "num",
            "start",
            "safe",
            "device",
            "uule",
            "ludocid",
            "lsig",
            "kgmid",
            "si",
            "ibp",
            "uds",
            "cr",
            "lr",
            "tbs",
            "nfpr",
            "filter",
            "no_cache",
            "async",
            "output",
        ]

        for param in valid_params:
            if param in arguments:
                params[param] = arguments[param]

        try:
            response = await make_serpapi_request(params, api_key)

            # Check response status code
            status_code = response.get("_status_code", 0)
            if status_code < 200 or status_code >= 300:
                return [
                    TextContent(
                        type="text",
                        text=f"Error performing search (Status {status_code}): {response.get('error', 'Unknown error')}",
                    )
                ]

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            return [
                TextContent(
                    type="text", text=f"Unexpected error performing search: {str(e)}"
                )
            ]

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
        authenticate_and_save_serpapi_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
