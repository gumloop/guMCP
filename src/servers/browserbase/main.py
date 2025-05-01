import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from browserbase import Browserbase
from playwright.async_api import async_playwright


# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))


SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(SERVICE_NAME)

from src.utils.browserbase.util import (
    authenticate_and_save_browserbase_key,
    get_browserbase_credentials,
)


async def get_browserbase_client(
    user_id: str, api_key: Optional[str] = None
) -> tuple[Browserbase, str]:
    """
    Retrieve a Browserbase client and the project_id for this user.
    """
    creds = await get_browserbase_credentials(user_id, SERVICE_NAME, api_key)
    bb = Browserbase(api_key=creds["api_key"])
    return bb, creds["project_id"]


def create_server(user_id: str, api_key: Optional[str] = None):
    server = Server("browserbase-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="load_webpage_tool",
                description="Load a webpage URL in a headless browser using Browserbase",
                inputSchema={
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON string containing webpage content and metadata",
                    "examples": [
                        '[{"status":"success","url":"https://example.com","content":"<!DOCTYPE html><html>...</html>"}]'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        if arguments is None:
            arguments = {}

        if name == "load_webpage_tool":
            url = arguments["url"]
            bb, project_id = await get_browserbase_client(
                server.user_id, server.api_key
            )

            # Create a new Browserbase session
            session = bb.sessions.create(project_id=project_id)
            connect_url = session.connect_url

            # Connect via Playwright and navigate
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(connect_url)
                context = browser.contexts[0]
                page = context.pages[0]
                try:
                    await page.goto(url)
                    content = await page.content()
                finally:
                    await page.close()
                    await browser.close()

            result = {"status": "success", "url": url, "content": content}

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="browserbase-server",
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
        authenticate_and_save_browserbase_key(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
