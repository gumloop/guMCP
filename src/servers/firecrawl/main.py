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

from mcp.types import (
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
FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_firecrawl_key(user_id):
    """Authenticate with firecrawl and save API key"""
    logger = logging.getLogger("firecrawl")

    logger.info(f"Starting firecrawl authentication for user {user_id}...")

    # Get auth client
    auth_client = create_auth_client()

    # Prompt user for API key if running locally
    api_key = input("Please enter your Firecrawl API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    # Save API key using auth client
    auth_client.save_user_credentials("firecrawl", user_id, {"api_key": api_key})

    logger.info(
        f"Firecrawl API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_firecrawl_credentials(user_id, api_key=None):
    """Get firecrawl API key for the specified user"""
    logger = logging.getLogger("firecrawl")

    # Get auth client
    auth_client = create_auth_client(api_key=api_key)

    # Get credentials for this user
    credentials_data = auth_client.get_user_credentials("firecrawl", user_id)

    def handle_missing_credentials():
        error_str = f"Firecrawl API key not found for user {user_id}."
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


async def make_firecrawl_request(
    method, endpoint, data=None, api_key=None, params=None
):
    """Make a request to the Firecrawl API"""
    if not api_key:
        raise ValueError("Firecrawl API key is required")

    url = f"{FIRECRAWL_API_URL}/{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=60.0
                )
            elif method.lower() == "post":
                response = await client.post(
                    url, json=data, headers=headers, timeout=60.0
                )
            elif method.lower() == "delete":
                response = await client.delete(url, headers=headers, timeout=60.0)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            response_json = response.json()
            response_json["_status_code"] = response.status_code
            return response_json

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        error_message = f"Firecrawl API error: {e.response.status_code}"
        try:
            error_details = e.response.json()
            if isinstance(error_details, dict) and "error" in error_details:
                error_message = error_details["error"]
        except:
            pass
        raise ValueError(error_message)

    except Exception as e:
        logger.error(f"Error making request to Firecrawl API: {str(e)}")
        raise ValueError(f"Error communicating with Firecrawl API: {str(e)}")


def create_server(user_id, api_key=None):
    server = Server("firecrawl-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        logger.info(f"Listing resources for user: {server.user_id}")
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="scrape_url",
                description="Scrape a single URL with Firecrawl",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The URL to scrape",
                        },
                        "formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Formats to include in the output (markdown, html, rawHtml, links, screenshot, screenshot@fullPage, json, changeTracking)",
                        },
                        "onlyMainContent": {
                            "type": "boolean",
                            "description": "Only return the main content of the page excluding headers, navs, footers, etc.",
                            "default": True,
                        },
                        "waitFor": {
                            "type": "integer",
                            "description": "Specify a delay in milliseconds before fetching the content",
                            "default": 0,
                        },
                        "mobile": {
                            "type": "boolean",
                            "description": "Set to true if you want to emulate scraping from a mobile device",
                            "default": False,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds for the request",
                            "default": 30000,
                        },
                        "removeBase64Images": {
                            "type": "boolean",
                            "description": "Removes all base 64 images from the output",
                        },
                    },
                    "required": ["url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Scraped content from the requested URL in the specified formats",
                    "examples": [
                        '{"success": true, "markdown": "# Website Title\\n\\nThis is the main content of the website...\\n", "html": "<div class=\\"main-content\\">...", "url": "https://example.com", "title": "Example Website", "metadata": {"statusCode": 200, "contentType": "text/html"}}'
                    ],
                },
            ),
            Tool(
                name="batch_scrape",
                description="Scrape multiple URLs in a batch with Firecrawl. ",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The URLs to scrape",
                        },
                        "webhook": {
                            "type": "object",
                            "description": "A webhook specification object",
                        },
                        "ignoreInvalidURLs": {
                            "type": "boolean",
                            "description": "If invalid URLs are specified in the urls array, they will be ignored",
                            "default": False,
                        },
                        "formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Formats to include in the output (markdown, html, rawHtml, links, screenshot, screenshot@fullPage, json, changeTracking)",
                        },
                        "onlyMainContent": {
                            "type": "boolean",
                            "description": "Only return the main content of the page excluding headers, navs, footers, etc.",
                            "default": True,
                        },
                        "includeTags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to include in the output",
                        },
                        "excludeTags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Tags to exclude from the output",
                        },
                        "headers": {
                            "type": "object",
                            "description": "Headers to send with the request. Can be used to send cookies, user-agent, etc.",
                        },
                        "waitFor": {
                            "type": "integer",
                            "description": "Specify a delay in milliseconds before fetching the content",
                            "default": 0,
                        },
                        "mobile": {
                            "type": "boolean",
                            "description": "Set to true if you want to emulate scraping from a mobile device",
                            "default": False,
                        },
                        "skipTlsVerification": {
                            "type": "boolean",
                            "description": "Skip TLS certificate verification when making requests",
                            "default": False,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds for the request",
                            "default": 30000,
                        },
                        "jsonOptions": {
                            "type": "object",
                            "description": "Extract object for JSON extraction",
                        },
                        "actions": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Actions to perform on the page before grabbing the content",
                        },
                        "location": {
                            "type": "object",
                            "description": "Location settings for the request",
                        },
                        "removeBase64Images": {
                            "type": "boolean",
                            "description": "Removes all base 64 images from the output",
                        },
                        "blockAds": {
                            "type": "boolean",
                            "description": "Enables ad-blocking and cookie popup blocking",
                            "default": True,
                        },
                        "proxy": {
                            "type": "string",
                            "enum": ["basic", "stealth"],
                            "description": "Specifies the type of proxy to use",
                        },
                        "changeTrackingOptions": {
                            "type": "object",
                            "description": "Options for change tracking (Beta)",
                        },
                    },
                    "required": ["urls"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the initiated batch scrape job",
                    "examples": [
                        '{"success": true, "id": "batch_12345678", "status": "pending", "totalUrls": 5, "createdAt": "2023-08-15T10:30:00Z", "message": "Batch scrape job started successfully"}'
                    ],
                },
            ),
            Tool(
                name="get_batch_status",
                description="Check the status of a batch scrape job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the batch scrape job",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status information about the batch scrape job",
                    "examples": [
                        '{"id": "batch_12345678", "status": "completed", "total": 5, "completed": 5, "failed": 0, "urls": [{"url": "https://example.com", "status": "completed"}], "createdAt": "2023-08-15T10:30:00Z", "completedAt": "2023-08-15T10:31:15Z"}'
                    ],
                },
            ),
            Tool(
                name="get_batch_error",
                description="Get errors from a batch scrape job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the batch scrape job",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Error information from the batch scrape job",
                    "examples": [
                        '{"id": "batch_12345678", "errors": [{"url": "https://invalid-url.com", "error": "Failed to resolve DNS", "statusCode": 404}]}'
                    ],
                },
            ),
            Tool(
                name="crawl_website",
                description="Crawl a website starting from a base URL",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The base URL to start crawling from",
                        },
                        "maxDepth": {
                            "type": "integer",
                            "description": "Maximum depth to crawl relative to the base URL",
                            "default": 10,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of pages to crawl",
                            "default": 10000,
                        },
                        "ignoreSitemap": {
                            "type": "boolean",
                            "description": "Ignore the website sitemap when crawling",
                            "default": False,
                        },
                        "excludePaths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL pathname regex patterns that exclude matching URLs from the crawl",
                        },
                        "includePaths": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL pathname regex patterns that include matching URLs in the crawl",
                        },
                        "formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Formats to include in the output (markdown, html, rawHtml, links, screenshot, screenshot@fullPage, json, changeTracking)",
                        },
                    },
                    "required": ["url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the initiated crawl job",
                    "examples": [
                        '{"success": true, "id": "crawl_87654321", "status": "pending", "url": "https://example.com", "message": "Crawl job started successfully"}'
                    ],
                },
            ),
            Tool(
                name="get_crawl_status",
                description="Check the status of a crawl job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the crawl job",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status information about the crawl job",
                    "examples": [
                        '{"id": "crawl_87654321", "status": "in_progress", "url": "https://example.com", "pagesFound": 25, "pagesCrawled": 15, "createdAt": "2023-08-15T14:20:00Z"}'
                    ],
                },
            ),
            Tool(
                name="cancel_crawl",
                description="Cancel an ongoing crawl job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the crawl job to cancel",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Result of the crawl cancellation request",
                    "examples": [
                        '{"success": true, "id": "crawl_87654321", "status": "cancelled", "message": "Crawl job cancelled successfully"}'
                    ],
                },
            ),
            Tool(
                name="map_website",
                description="Map all URLs on a website",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The base URL to start mapping from",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search query to use for mapping",
                        },
                        "ignoreSitemap": {
                            "type": "boolean",
                            "description": "Ignore the website sitemap when mapping",
                            "default": True,
                        },
                        "sitemapOnly": {
                            "type": "boolean",
                            "description": "Only return links found in the website sitemap",
                            "default": False,
                        },
                        "includeSubdomains": {
                            "type": "boolean",
                            "description": "Include subdomains of the website",
                            "default": False,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of links to return (max 5000)",
                            "default": 5000,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in milliseconds",
                        },
                    },
                    "required": ["url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs found on the mapped website",
                    "examples": [
                        '{"success": true, "url": "https://example.com", "links": ["https://example.com/about", "https://example.com/products", "https://example.com/contact"], "total": 3}'
                    ],
                },
            ),
            Tool(
                name="extract_data",
                description="Extract structured data from URLs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "The URLs to extract data from",
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Prompt to guide the extraction process",
                        },
                        "schema": {
                            "type": "object",
                            "description": "Schema to define the structure of the extracted data",
                        },
                        "enableWebSearch": {
                            "type": "boolean",
                            "description": "When true, the extraction will use web search to find additional data",
                            "default": False,
                        },
                        "ignoreSitemap": {
                            "type": "boolean",
                            "description": "When true, sitemap.xml files will be ignored during website scanning",
                            "default": False,
                        },
                        "includeSubdomains": {
                            "type": "boolean",
                            "description": "When true, subdomains of the provided URLs will also be scanned",
                            "default": True,
                        },
                        "showSources": {
                            "type": "boolean",
                            "description": "When true, the sources used to extract the data will be included in the response",
                            "default": False,
                        },
                    },
                    "required": ["urls"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about the initiated data extraction job",
                    "examples": [
                        '{"success": true, "id": "extract_abcd1234", "status": "pending", "urls": ["https://example.com"], "message": "Data extraction job started successfully"}'
                    ],
                },
            ),
            Tool(
                name="get_extract_status",
                description="Check the status of an extract job",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the extract job",
                        },
                    },
                    "required": ["id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Status and results of the data extraction job",
                    "examples": [
                        '{"id": "extract_abcd1234", "status": "completed", "data": [{"title": "Example Product", "price": "$29.99", "description": "This is an example product description."}], "createdAt": "2023-08-15T16:45:00Z", "completedAt": "2023-08-15T16:46:30Z"}'
                    ],
                },
            ),
            Tool(
                name="search",
                description="Search the web and get full page content for search results",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (1-50)",
                            "default": 5,
                        },
                        "lang": {
                            "type": "string",
                            "description": "Language code for search results",
                            "default": "en",
                        },
                        "country": {
                            "type": "string",
                            "description": "Country code for search results",
                            "default": "us",
                        },
                        "include_content": {
                            "type": "boolean",
                            "description": "When true, returns full page content for search results",
                            "default": False,
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Search results with optional full page content",
                    "examples": [
                        '{"success": true, "query": "example search", "results": [{"title": "Example Search Result", "url": "https://example.com/result1", "snippet": "This is a snippet of the search result...", "content": "Full content of the page if include_content was true..."}], "total": 1}'
                    ],
                },
            ),
            Tool(
                name="check_credit_usage",
                description="Check your Firecrawl credit usage",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Information about credit usage for the Firecrawl account",
                    "examples": [
                        '{"plan": "Pro", "credits": {"used": 850, "total": 5000, "remaining": 4150}, "reset": {"next": "2023-09-01T00:00:00Z", "period": "monthly"}}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        logger.info(f"User {server.user_id} calling tool: {name}")
        api_key = await get_firecrawl_credentials(server.user_id, server.api_key)

        try:
            if name == "scrape_url":
                response = await make_firecrawl_request(
                    "post", "scrape", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error scraping URL (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error scraping URL (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "batch_scrape":
                response = await make_firecrawl_request(
                    "post", "batch/scrape", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting batch scrape (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting batch scrape (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "get_batch_status":
                batch_id = arguments["id"]
                response = await make_firecrawl_request(
                    "get", f"batch/scrape/{batch_id}", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error checking batch status (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(response, indent=2))]
            elif name == "get_batch_error":
                response = await make_firecrawl_request(
                    "get", f"batch/scrape/{arguments['id']}/errors", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code != 200:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error retrieving batch errors (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(response, indent=2))]
            elif name == "crawl_website":
                response = await make_firecrawl_request(
                    "post", "crawl", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting crawl (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting crawl (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "get_crawl_status":
                crawl_id = arguments["id"]
                response = await make_firecrawl_request(
                    "get", f"crawl/{crawl_id}", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error checking crawl status (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(response, indent=2))]
            elif name == "cancel_crawl":
                crawl_id = arguments["id"]
                response = await make_firecrawl_request(
                    "delete", f"crawl/{crawl_id}", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error cancelling crawl (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(response, indent=2))]
            elif name == "map_website":
                response = await make_firecrawl_request(
                    "post", "map", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error mapping website (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    # Handle links array if present
                    if isinstance(response.get("links"), list):
                        # Return multiple TextContent objects for arrays
                        return [
                            TextContent(
                                type="text", text=json.dumps(response, indent=2)
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text", text=json.dumps(response, indent=2)
                            )
                        ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error mapping website (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "extract_data":
                response = await make_firecrawl_request(
                    "post", "extract", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting data extraction (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error starting data extraction (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "get_extract_status":
                extract_id = arguments["id"]
                response = await make_firecrawl_request(
                    "get", f"extract/{extract_id}", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error checking extract status (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                # Handle data array if present
                if (
                    isinstance(response.get("data"), list)
                    and len(response.get("data", [])) > 0
                ):
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
                else:
                    return [
                        TextContent(type="text", text=json.dumps(response, indent=2))
                    ]
            elif name == "search":
                response = await make_firecrawl_request(
                    "post", "search", arguments, api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error performing search (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                if response.get("success"):
                    # Handle results array if present
                    if (
                        isinstance(response.get("results"), list)
                        and len(response.get("results", [])) > 0
                    ):
                        return [
                            TextContent(
                                type="text", text=json.dumps(response, indent=2)
                            )
                        ]
                    else:
                        return [
                            TextContent(
                                type="text", text=json.dumps(response, indent=2)
                            )
                        ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error performing search (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]
            elif name == "check_credit_usage":
                response = await make_firecrawl_request(
                    "get", "team/credit-usage", api_key=api_key
                )

                status_code = response.get("_status_code", 0)
                if status_code < 200 or status_code >= 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error checking credit usage (Status {status_code}): {response.get('error', 'Unknown error')}\nDetails: {response.get('error_detail', 'No details available')}",
                        )
                    ]

                return [TextContent(type="text", text=json.dumps(response, indent=2))]

            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="firecrawl-server",
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
        authenticate_and_save_firecrawl_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
