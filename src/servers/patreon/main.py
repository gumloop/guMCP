import os
import sys
import logging
import json
import requests
from pathlib import Path
from typing import List, Dict

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import TextContent

from src.utils.patreon.util import authenticate_and_save_credentials, get_credentials


SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "identity",
    "identity[email]",
    "identity.memberships",
    "campaigns",
    "w:campaigns.webhook",
    "campaigns.members",
    "campaigns.members[email]",
    "campaigns.members.address",
    "campaigns.posts",
]


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(SERVICE_NAME)


class PatreonClient:
    """Client for interacting with the Patreon API."""

    def __init__(self, access_token: str):
        """Initialize the Patreon client with an access token."""
        self.access_token = access_token
        self.base_url = "https://www.patreon.com/api/oauth2/v2"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, params: Dict = None) -> Dict:
        """Make a request to the Patreon API."""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method, url=url, headers=self.headers, params=params
        )
        response.raise_for_status()
        return response.json()

    def get_identity(
        self, fields: Dict[str, str] = None, includes: List[str] = None
    ) -> Dict:
        """
        Get the current user's information with optional fields and includes.

        Args:
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: User information with requested fields and includes
        """
        params = {}
        if fields:
            for resource_type, field_list in fields.items():
                params[f"fields[{resource_type}]"] = field_list
        if includes:
            params["include"] = ",".join(includes)
        return self._make_request("GET", "identity", params=params)

    def get_campaigns(
        self, fields: Dict[str, str] = None, includes: List[str] = None
    ) -> Dict:
        """
        Get campaigns owned by the authorized user.

        Args:
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: List of campaigns with requested fields and includes
        """
        params = {}
        if fields:
            for resource_type, field_list in fields.items():
                params[f"fields[{resource_type}]"] = field_list
        if includes:
            params["include"] = ",".join(includes)
        return self._make_request("GET", "campaigns", params=params)

    def get_campaign(
        self,
        campaign_id: str,
        fields: Dict[str, str] = None,
        includes: List[str] = None,
    ) -> Dict:
        """
        Get information about a single Campaign by ID.

        Args:
            campaign_id (str): The ID of the campaign
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: Campaign information with requested fields and includes
        """
        params = {}
        if fields:
            for resource_type, field_list in fields.items():
                params[f"fields[{resource_type}]"] = field_list
        if includes:
            params["include"] = ",".join(includes)
        return self._make_request("GET", f"campaigns/{campaign_id}", params=params)

    def get_campaign_members(
        self,
        campaign_id: str,
        fields: Dict[str, str] = None,
        includes: List[str] = None,
    ) -> Dict:
        """
        Get members of a specific campaign.

        Args:
            campaign_id (str): The ID of the campaign
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: List of campaign members with requested fields and includes
        """
        params = {}
        if fields:
            for resource_type, field_list in fields.items():
                params[f"fields[{resource_type}]"] = field_list
        if includes:
            params["include"] = ",".join(includes)
        return self._make_request(
            "GET", f"campaigns/{campaign_id}/members", params=params
        )

    def get_campaign_posts(
        self,
        campaign_id: str,
        fields: Dict[str, str] = None,
        includes: List[str] = None,
    ) -> Dict:
        """
        Get a list of all posts on a given campaign.

        Args:
            campaign_id (str): The ID of the campaign
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: List of campaign posts with requested fields and includes
        """
        params = {}
        if fields:
            for resource_type, field_list in fields.items():
                params[f"fields[{resource_type}]"] = field_list
        if includes:
            params["include"] = ",".join(includes)
        return self._make_request(
            "GET", f"campaigns/{campaign_id}/posts", params=params
        )

    def get_post(self, post_id: str) -> Dict:
        """
        Get details of a specific post.

        Args:
            post_id (str): The ID of the post
            fields (Dict[str, str], optional): Fields to include for each resource type
            includes (List[str], optional): Related resources to include

        Returns:
            Dict: Post details with requested fields and includes
        """

        return self._make_request(
            "GET",
            f"posts/{post_id}?fields[post]=published_at,title,content,embed_data,is_public,tiers,url",
        )


async def create_patreon_client(user_id: str, api_key: str = None) -> PatreonClient:
    """
    Create an authorized Patreon API client.

    Args:
        user_id (str): The user ID associated with the credentials
        api_key (str, optional): Optional override for authentication

    Returns:
        PatreonClient: Patreon API client with credentials initialized
    """
    token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return PatreonClient(token)


def create_server(user_id: str, api_key: str = None) -> Server:
    """
    Initialize and configure the Patreon MCP server.

    Args:
        user_id (str): The user ID associated with the current session
        api_key (str, optional): Optional API key override

    Returns:
        Server: Configured MCP server instance
    """
    server = Server("patreon-server")

    server.user_id = user_id
    server.api_key = api_key
    server._patreon_client = None

    async def _get_patreon_client() -> PatreonClient:
        """Get or create a Patreon client."""
        if not server._patreon_client:
            server._patreon_client = await create_patreon_client(
                server.user_id, server.api_key
            )
        return server._patreon_client

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """
        Return a list of available Patreon tools.

        Returns:
            list[types.Tool]: List of tool definitions supported by this server
        """
        return [
            types.Tool(
                name="get_identity",
                description="Get the current user's information with optional fields and includes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "object",
                            "description": "Fields to include for each resource type",
                            "additionalProperties": {"type": "string"},
                        },
                        "includes": {
                            "type": "array",
                            "description": "Related resources to include",
                            "items": {"type": "string"},
                        },
                    },
                },
            ),
            types.Tool(
                name="get_campaigns",
                description="Get campaigns owned by the authorized user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "fields": {
                            "type": "object",
                            "description": "Fields to include for each resource type",
                            "additionalProperties": {"type": "string"},
                        },
                        "includes": {
                            "type": "array",
                            "description": "Related resources to include",
                            "items": {"type": "string"},
                        },
                    },
                },
            ),
            types.Tool(
                name="get_campaign",
                description="Get information about a single Campaign by ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Fields to include for each resource type",
                            "additionalProperties": {"type": "string"},
                        },
                        "includes": {
                            "type": "array",
                            "description": "Related resources to include",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="get_campaign_members",
                description="Get members of a specific campaign",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Fields to include for each resource type",
                            "additionalProperties": {"type": "string"},
                        },
                        "includes": {
                            "type": "array",
                            "description": "Related resources to include",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="get_campaign_posts",
                description="Get a list of all posts on a given campaign",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaign_id": {
                            "type": "string",
                            "description": "The ID of the campaign",
                        },
                    },
                    "required": ["campaign_id"],
                },
            ),
            types.Tool(
                name="get_post",
                description="Get details of a specific post",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "string",
                            "description": "The ID of the post",
                        },
                        "fields": {
                            "type": "object",
                            "description": "Fields to include for each resource type",
                            "additionalProperties": {"type": "string"},
                        },
                        "includes": {
                            "type": "array",
                            "description": "Related resources to include",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["post_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
        """
        Handle Patreon tool invocation from the MCP system.

        Args:
            name (str): The name of the tool being called
            arguments (dict | None): Parameters passed to the tool

        Returns:
            list[TextContent]: Output content from tool execution
        """
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        patreon = await _get_patreon_client()

        try:
            if name == "get_identity":
                result = patreon.get_identity(
                    fields=arguments.get("fields"), includes=arguments.get("includes")
                )
            elif name == "get_campaigns":
                result = patreon.get_campaigns(
                    fields=arguments.get("fields"), includes=arguments.get("includes")
                )
            elif name == "get_campaign":
                result = patreon.get_campaign(
                    campaign_id=arguments["campaign_id"],
                    fields=arguments.get("fields"),
                    includes=arguments.get("includes"),
                )
            elif name == "get_campaign_members":
                result = patreon.get_campaign_members(
                    campaign_id=arguments["campaign_id"],
                    fields=arguments.get("fields"),
                    includes=arguments.get("includes"),
                )

            elif name == "get_campaign_posts":
                result = patreon.get_campaign_posts(
                    campaign_id=arguments["campaign_id"],
                    fields=arguments.get("fields"),
                    includes=arguments.get("includes"),
                )
            elif name == "get_post":
                result = patreon.get_post(post_id=arguments["post_id"])
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Define the initialization options for the Patreon MCP server.

    Args:
        server_instance (Server): The server instance to describe

    Returns:
        InitializationOptions: MCP-compatible initialization configuration
    """
    return InitializationOptions(
        server_name="patreon-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
