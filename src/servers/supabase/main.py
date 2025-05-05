import sys
import logging
import json
import os
import requests
from pathlib import Path
from typing import Optional, Any, Iterable, Dict

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

# Import Supabase SDK
from supabase import create_client

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from src.utils.supabase.util import (
    get_credentials,
    authenticate_and_save_credentials,
)
from mcp.types import (
    AnyUrl,
    Resource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents

SERVICE_NAME = Path(__file__).parent.name
SUPABASE_BASE_URL = "https://api.supabase.com/v1"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)

# Global dictionary to store Supabase SDK clients per project reference
supabase_sdk_clients: Dict[str, Any] = {}


def get_or_create_supabase_sdk_client(project_ref: str, api_key: str) -> Any:
    """
    Get an existing or create a new Supabase client using the Python SDK.

    This function creates a client for a specific project and caches it for reuse.

    Args:
        project_ref: The reference ID of the Supabase project
        api_key: The Supabase API key

    Returns:
        A Supabase client instance

    Raises:
        ValueError: If the API key is invalid or connection fails
    """
    # Create a unique cache key for this project+api_key combination
    cache_key = f"{project_ref}:{api_key[:5]}..."

    # Check if we already have a client for this combination
    if cache_key in supabase_sdk_clients:
        logger.info(f"Using cached Supabase client for project {project_ref}")
        return supabase_sdk_clients[cache_key]

    # Construct the Supabase URL from the project reference
    url = f"https://{project_ref}.supabase.co"

    try:
        # Create new client
        logger.info(f"Creating new Supabase client for project {project_ref}")
        client = create_client(url, api_key)

        # Cache the client for future use
        supabase_sdk_clients[cache_key] = client

        return client
    except Exception as e:
        error_msg = f"Failed to create Supabase client for project {project_ref}: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)


async def create_supabase_client(access_token: str) -> Any:
    """
    Create a Supabase client instance using the provided credentials.

    Args:
        access_token: The OAuth access token

    Returns:
        dict: A dictionary containing:
            - token: The access token
            - headers: Standard HTTP headers for Supabase API requests
            - base_url: The base URL for Supabase API endpoints
    """
    # Standard headers for API requests
    standard_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    return {
        "token": access_token,
        "headers": standard_headers,
        "base_url": SUPABASE_BASE_URL,
    }


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Create a new Supabase MCP server instance.

    Args:
        user_id: The user ID to create the server for
        api_key: Optional API key for authentication

    Returns:
        An MCP Server instance configured for Supabase operations
    """
    server = Server("supabase-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Supabase resources"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        supabase_client = await create_supabase_client(credentials)

        try:
            resources = []

            # List all Supabase projects
            url = f"{SUPABASE_BASE_URL}/projects"
            logger.info(f"Making request to {url}")

            # Make the API request to get projects
            response = requests.get(url, headers=supabase_client["headers"], timeout=30)

            # Check if the request was successful
            if response.status_code == 200:
                projects = response.json()
                logger.info(f"Projects: {projects}")

                for project in projects:
                    project_id = project.get("id")
                    project_name = project.get("name", "Unknown Project")
                    region = project.get("region", "Unknown Region")
                    organization_id = project.get(
                        "organization_id", "Unknown Organization"
                    )

                    # Add project as a resource
                    resources.append(
                        Resource(
                            uri=f"supabase://project/{project_id}",
                            mimeType="application/json",
                            name=f"Project: {project_name}",
                            description=f"Supabase project (Region: {region}, Org ID: {organization_id})",
                        )
                    )

            logger.info(f"Found {len(resources)} resources")
            return resources

        except Exception as e:
            logger.error(f"Error listing Supabase resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read content from a Supabase resource"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        supabase_client = await create_supabase_client(credentials)

        uri_str = str(uri)
        if not uri_str.startswith("supabase://"):
            raise ValueError(f"Invalid Supabase URI: {uri_str}")

        try:
            if uri_str.startswith("supabase://project/"):
                # Handle project resource
                project_ref = uri_str.replace("supabase://project/", "")
                project_url = f"{SUPABASE_BASE_URL}/projects/{project_ref}"

                logger.info(f"Making request to {project_url}")

                # Make the API request to get the specific project
                response = requests.get(
                    project_url, headers=supabase_client["headers"], timeout=30
                )

                # Check if the request was successful
                if response.status_code == 200:
                    project_data = response.json()

                    # Get project settings and additional information
                    settings_url = (
                        f"{SUPABASE_BASE_URL}/projects/{project_ref}/settings"
                    )
                    settings_response = requests.get(
                        settings_url, headers=supabase_client["headers"], timeout=30
                    )

                    if settings_response.status_code == 200:
                        settings_data = settings_response.json()
                        # Combine project details with settings
                        combined_data = {
                            "project": project_data,
                            "settings": settings_data,
                        }

                        return [
                            ReadResourceContents(
                                content=json.dumps(combined_data, indent=2),
                                mime_type="application/json",
                            )
                        ]
                    else:
                        # Return just project data if settings aren't available
                        return [
                            ReadResourceContents(
                                content=json.dumps(project_data, indent=2),
                                mime_type="application/json",
                            )
                        ]
                else:
                    error_message = f"Error reading project: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [
                        ReadResourceContents(
                            content=error_message, mime_type="text/plain"
                        )
                    ]

            # Return error for unsupported resource types
            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading Supabase resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Return the list of available Supabase tools."""
        tools = [
            # ORGANIZATION MANAGEMENT TOOLS
            types.Tool(
                name="list_organizations",
                description="List all Supabase organizations the user is a member of",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","organization_id":"org123","name":"Example Organization"}]'
                    ],
                },
            ),
            # PROJECT MANAGEMENT TOOLS
            types.Tool(
                name="list_projects",
                description="Returns a list of all Supabase projects you've previously created",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","project_id":"proj123","name":"Example Project"}]'
                    ],
                },
            ),
            types.Tool(
                name="get_project",
                description="Get details of a specific Supabase project by its reference ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        }
                    },
                    "required": ["ref"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","project_id":"proj123","name":"Example Project","ref":"example-ref"}]'
                    ],
                },
            ),
            types.Tool(
                name="create_project",
                description="Create a new Supabase project in an organization",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "org_id": {
                            "type": "string",
                            "description": "The ID of the organization to create the project in (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the project (required)",
                        },
                        "db_pass": {
                            "type": "string",
                            "description": "The database password for the project (required)",
                        },
                        "region": {
                            "type": "string",
                            "description": "The region for the project (required)",
                        },
                        "plan": {
                            "type": "string",
                            "description": "The pricing plan (free or pro)",
                            "default": "free",
                        },
                    },
                    "required": ["org_id", "name", "db_pass", "region"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","project_id":"proj123","name":"Example Project","ref":"example-ref"}]'
                    ],
                },
            ),
            # DATA MANAGEMENT TOOLS
            types.Tool(
                name="read_table_data",
                description="Read data from a table in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase API key for this project (required)",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "The name of the table to read data from (required)",
                        },
                        "select": {
                            "type": "string",
                            "description": "Columns to select (default: '*' for all columns)",
                            "default": "*",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Optional filters to apply (column name as key, value to filter by as value)",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return",
                        },
                    },
                    "required": ["project_ref", "supabase_key", "table_name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"id":1,"name":"Example"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="create_table_data",
                description="Create new rows in a table in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase API key for this project (required)",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "The name of the table to insert data into (required)",
                        },
                        "data": {
                            "type": ["object", "array"],
                            "description": "The data to insert. Pass an object to insert a single row or an array to insert multiple rows (required)",
                        },
                    },
                    "required": ["project_ref", "supabase_key", "table_name", "data"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"id":1,"name":"Example"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="update_table_data",
                description="Update rows in a table in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase API key for this project (required)",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "The name of the table to update data in (required)",
                        },
                        "data": {
                            "type": "object",
                            "description": "The data to update (column/value pairs) (required)",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply to identify rows to update (column name as key, value to filter by as value) (required)",
                        },
                    },
                    "required": [
                        "project_ref",
                        "supabase_key",
                        "table_name",
                        "data",
                        "filters",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"id":1,"name":"Updated Example"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="delete_table_data",
                description="Delete rows from a table in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase API key for this project (required)",
                        },
                        "table_name": {
                            "type": "string",
                            "description": "The name of the table to delete data from (required)",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply to identify rows to delete (column name as key, value to filter by as value) (required)",
                        },
                    },
                    "required": [
                        "project_ref",
                        "supabase_key",
                        "table_name",
                        "filters",
                    ],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","data":[{"id":1,"name":"Deleted Example"}]}]'
                    ],
                },
            ),
            # DATABASE STRUCTURE TOOLS
            types.Tool(
                name="create_storage_bucket",
                description="Create a new storage bucket in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the bucket (required)",
                        },
                        "public": {
                            "type": "boolean",
                            "description": "Whether the bucket is publicly accessible",
                            "default": False,
                        },
                        "file_size_limit": {
                            "type": "integer",
                            "description": "Maximum allowed file size in bytes",
                            "default": 52428800,
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase service_role API key for this project (required, must be service_role key, not anon key)",
                        },
                    },
                    "required": ["project_ref", "name", "supabase_key"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","bucket_id":"bucket123","name":"Example Bucket"}]'
                    ],
                },
            ),
            types.Tool(
                name="list_storage_buckets",
                description="List all storage buckets in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase service_role API key for this project (required, must be service_role key, not anon key)",
                        },
                    },
                    "required": ["project_ref", "supabase_key"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","buckets":[{"id":"bucket123","name":"Example Bucket"}]}]'
                    ],
                },
            ),
            types.Tool(
                name="get_storage_bucket",
                description="Get details about a specific storage bucket in a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "bucket_id": {
                            "type": "string",
                            "description": "The ID of the bucket to retrieve (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase service_role API key for this project (required, must be service_role key, not anon key)",
                        },
                    },
                    "required": ["project_ref", "bucket_id", "supabase_key"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","bucket_id":"bucket123","name":"Example Bucket","public":false}]'
                    ],
                },
            ),
            types.Tool(
                name="delete_storage_bucket",
                description="Delete a storage bucket from a Supabase project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_ref": {
                            "type": "string",
                            "description": "The reference ID of the project (required)",
                        },
                        "bucket_id": {
                            "type": "string",
                            "description": "The ID of the bucket to delete (required)",
                        },
                        "supabase_key": {
                            "type": "string",
                            "description": "The Supabase service_role API key for this project (required, must be service_role key, not anon key)",
                        },
                    },
                    "required": ["project_ref", "bucket_id", "supabase_key"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the operation results",
                    "examples": [
                        '[{"status":"success","message":"Bucket deleted successfully"}]'
                    ],
                },
            ),
        ]
        return tools

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[types.TextContent]:
        """Handle Supabase tool invocation from the MCP system."""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        credentials = await get_credentials(
            server.user_id, SERVICE_NAME, api_key=server.api_key
        )

        supabase_client = await create_supabase_client(credentials)

        if arguments is None:
            arguments = {}

        try:
            if name == "list_organizations":
                # Build the request URL
                url = f"{SUPABASE_BASE_URL}/organizations"

                logger.info(f"Making request to {url}")

                # Make the API request to get organizations
                response = requests.get(
                    url, headers=supabase_client["headers"], timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    org_count = len(result)

                    # Format the response for readability
                    formatted_result = {
                        "totalOrganizations": org_count,
                        "organizations": result,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {org_count} organizations:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving organizations: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "list_projects":
                # Build the request URL
                url = f"{SUPABASE_BASE_URL}/projects"

                logger.info(f"Making request to {url}")

                # Make the API request to get projects
                response = requests.get(
                    url, headers=supabase_client["headers"], timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    project_count = len(result)

                    # Format the response for readability
                    formatted_result = {
                        "totalProjects": project_count,
                        "projects": result,
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved {project_count} projects:\n{json.dumps(formatted_result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving projects: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "get_project":
                # Extract parameters
                project_ref = arguments.get("ref")

                # Validate required parameters
                if not project_ref:
                    return [
                        types.TextContent(
                            type="text",
                            text="Error: project reference ID (ref) is required",
                        )
                    ]

                # Build the request URL
                url = f"{SUPABASE_BASE_URL}/projects/{project_ref}"

                logger.info(f"Making request to {url}")

                # Make the API request to get the specific project
                response = requests.get(
                    url, headers=supabase_client["headers"], timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code == 200:
                    result = response.json()
                    project_name = result.get("name", "Unknown Project")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully retrieved project '{project_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error retrieving project: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_project":
                # Extract required parameters
                org_id = arguments.get("org_id")
                name = arguments.get("name")
                db_pass = arguments.get("db_pass")
                region = arguments.get("region")
                plan = arguments.get("plan", "free")

                # Validate required parameters
                required_params = {
                    "org_id": org_id,
                    "name": name,
                    "db_pass": db_pass,
                    "region": region,
                }
                missing_params = [
                    param for param, value in required_params.items() if not value
                ]

                if missing_params:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                # Build the request URL and payload
                url = f"{SUPABASE_BASE_URL}/projects"

                payload = {
                    "name": name,
                    "organization_id": org_id,
                    "region": region,
                    "db_pass": db_pass,
                    "plan": plan,
                }

                logger.info(
                    f"Making request to {url} with payload: {json.dumps(payload, indent=2)}"
                )

                # Make the API request to create the project
                response = requests.post(
                    url, headers=supabase_client["headers"], json=payload, timeout=30
                )

                # Log the response status
                logger.info(f"Response status: {response.status_code}")

                # Check if the request was successful
                if response.status_code in [200, 201]:
                    result = response.json()
                    project_name = result.get("name", "Unknown Project")
                    project_ref = result.get("ref", "Unknown Ref")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created project '{project_name}' with reference ID '{project_ref}':\n{json.dumps(result, indent=2)}",
                        )
                    ]
                else:
                    error_message = f"Error creating project: {response.status_code} - {response.text}"
                    logger.error(error_message)
                    return [types.TextContent(type="text", text=error_message)]

            elif name == "create_storage_bucket":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                bucket_name = arguments.get("name")
                is_public = arguments.get("public", False)
                file_size_limit = arguments.get("file_size_limit", 52428800)
                supabase_key = arguments.get("supabase_key")

                # Validate required parameters
                if not project_ref or not bucket_name or not supabase_key:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not bucket_name:
                        missing_params.append("name")
                    if not supabase_key:
                        missing_params.append("supabase_key")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Create the bucket using the SDK
                    result = supabase.storage.create_bucket(
                        bucket_name,
                        options={
                            "public": is_public,
                            "file_size_limit": file_size_limit,
                        },
                    )

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully created storage bucket '{bucket_name}':\n{json.dumps(result, indent=2)}",
                        )
                    ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(
                        f"Error creating storage bucket using SDK: {error_str}"
                    )

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a service_role API key for storage operations, not an anon key. Get your service_role key from Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error creating storage bucket: {error_str}",
                        )
                    ]

            elif name == "list_storage_buckets":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                supabase_key = arguments.get("supabase_key")

                # Validate required parameters
                if not project_ref or not supabase_key:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not supabase_key:
                        missing_params.append("supabase_key")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # List all buckets using the SDK
                    result = supabase.storage.list_buckets()

                    if not result:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"No storage buckets found in project '{project_ref}'.",
                            )
                        ]

                    logger.info(f"Result: {result}")
                    # Format the response
                    buckets_info = []
                    for bucket in result:
                        # SyncBucket objects have attributes, not dictionary keys
                        buckets_info.append(
                            {
                                "id": getattr(bucket, "id", "Unknown"),
                                "name": getattr(bucket, "name", "Unknown"),
                                "public": getattr(bucket, "public", False),
                                "created_at": str(
                                    getattr(bucket, "created_at", "Unknown")
                                ),
                                "updated_at": str(
                                    getattr(bucket, "updated_at", "Unknown")
                                ),
                                "owner": getattr(bucket, "owner", "Unknown"),
                                "file_size_limit": getattr(
                                    bucket, "file_size_limit", None
                                ),
                            }
                        )

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Found {len(buckets_info)} storage buckets in project '{project_ref}':\n{json.dumps(buckets_info, indent=2)}",
                        )
                    ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(
                        f"Error listing storage buckets using SDK: {error_str}"
                    )

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a service_role API key for storage operations, not an anon key. Get your service_role key from Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error listing storage buckets: {error_str}",
                        )
                    ]

            elif name == "get_storage_bucket":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                bucket_id = arguments.get("bucket_id")
                supabase_key = arguments.get("supabase_key")

                # Validate required parameters
                if not project_ref or not bucket_id or not supabase_key:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not bucket_id:
                        missing_params.append("bucket_id")
                    if not supabase_key:
                        missing_params.append("supabase_key")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Get the specific bucket using the SDK
                    result = supabase.storage.get_bucket(bucket_id)

                    if not result:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"No storage bucket with ID '{bucket_id}' found in project '{project_ref}'.",
                            )
                        ]

                    logger.info(f"Result bucket: {result}")
                    # Format the response using attribute access for SyncBucket object
                    bucket_info = {
                        "id": getattr(result, "id", "Unknown"),
                        "name": getattr(result, "name", "Unknown"),
                        "public": getattr(result, "public", False),
                        "file_size_limit": getattr(result, "file_size_limit", None),
                        "allowed_mime_types": getattr(
                            result, "allowed_mime_types", None
                        ),
                        "created_at": str(getattr(result, "created_at", "Unknown")),
                        "updated_at": str(getattr(result, "updated_at", "Unknown")),
                        "owner": getattr(result, "owner", "Unknown"),
                    }

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Storage bucket '{bucket_id}' details:\n{json.dumps(bucket_info, indent=2)}",
                        )
                    ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error getting storage bucket using SDK: {error_str}")

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a service_role API key for storage operations, not an anon key. Get your service_role key from Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    # Check if this is a not found error
                    if (
                        "404" in error_str
                        or "not found" in error_str.lower()
                        or "not exist" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"No storage bucket with ID '{bucket_id}' found in project '{project_ref}'.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error getting storage bucket: {error_str}",
                        )
                    ]

            elif name == "delete_storage_bucket":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                bucket_id = arguments.get("bucket_id")
                supabase_key = arguments.get("supabase_key")

                # Validate required parameters
                if not project_ref or not bucket_id or not supabase_key:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not bucket_id:
                        missing_params.append("bucket_id")
                    if not supabase_key:
                        missing_params.append("supabase_key")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Delete the bucket using the SDK
                    result = supabase.storage.delete_bucket(bucket_id)

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully deleted storage bucket '{bucket_id}':\n{json.dumps(result, indent=2)}",
                        )
                    ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(
                        f"Error deleting storage bucket using SDK: {error_str}"
                    )

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a service_role API key for storage operations, not an anon key. Get your service_role key from Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error deleting storage bucket: {error_str}",
                        )
                    ]

            elif name == "read_table_data":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                supabase_key = arguments.get("supabase_key")
                table_name = arguments.get("table_name")
                select = arguments.get("select", "*")
                filters = arguments.get("filters", {})
                limit = arguments.get("limit")

                # Validate required parameters
                if not project_ref or not supabase_key or not table_name:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not supabase_key:
                        missing_params.append("supabase_key")
                    if not table_name:
                        missing_params.append("table_name")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Prepare the query
                    query = supabase.table(table_name).select(select)

                    # Apply filters if provided
                    if filters:
                        for column, value in filters.items():
                            query = query.eq(column, value)

                    # Apply limit if provided
                    if limit:
                        query = query.limit(limit)

                    # Execute the query
                    response = query.execute()

                    # Check if the request was successful
                    if response.data is not None:
                        rows = response.data
                        count = len(rows)

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully retrieved {count} rows from table '{table_name}':\n{json.dumps(rows, indent=2)}",
                            )
                        ]
                    else:
                        # Handle empty result
                        if hasattr(response, "error") and response.error:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Error reading data from table '{table_name}': {response.error.message}",
                                )
                            ]
                        else:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No data found in table '{table_name}' with the specified filters.",
                                )
                            ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error reading table data: {error_str}")

                    # Check if this is a table not found error
                    if (
                        "relation" in error_str.lower()
                        and "does not exist" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Table '{table_name}' does not exist in the database. Please create the table using the Supabase Dashboard before attempting to read data.",
                            )
                        ]

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a valid API key for data operations. Check your API key in the Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error reading data from table '{table_name}': {error_str}",
                        )
                    ]

            elif name == "create_table_data":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                supabase_key = arguments.get("supabase_key")
                table_name = arguments.get("table_name")
                data = arguments.get("data")

                # Validate required parameters
                if (
                    not project_ref
                    or not supabase_key
                    or not table_name
                    or data is None
                ):
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not supabase_key:
                        missing_params.append("supabase_key")
                    if not table_name:
                        missing_params.append("table_name")
                    if data is None:
                        missing_params.append("data")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Prepare the query
                    query = supabase.table(table_name).insert(data)

                    # Execute the query
                    response = query.execute()

                    # Check if the request was successful
                    if hasattr(response, "data") and response.data is not None:
                        rows = response.data
                        count = len(rows) if isinstance(rows, list) else 1

                        operation_type = "inserted"
                        if isinstance(data, list):
                            operation_type = f"inserted {len(data)} rows"
                        else:
                            operation_type = "inserted row"

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully {operation_type} into table '{table_name}':\n{json.dumps(rows, indent=2)}",
                            )
                        ]
                    else:
                        # Handle error or empty result
                        if hasattr(response, "error") and response.error:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Error inserting data into table '{table_name}': {response.error.message}",
                                )
                            ]
                        else:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Operation completed, but no data was returned from table '{table_name}'.",
                                )
                            ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error inserting table data: {error_str}")

                    # Check if this is a table not found error
                    if (
                        "relation" in error_str.lower()
                        and "does not exist" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Table '{table_name}' does not exist in the database. Please create the table using the Supabase Dashboard before attempting to insert data.",
                            )
                        ]

                    # Check if this is a constraint violation error (e.g., duplicate key)
                    if (
                        "duplicate key" in error_str.lower()
                        or "violates" in error_str.lower()
                        and "constraint" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: The data you're trying to insert violates a database constraint. This could be due to a duplicate unique key or other constraint violation: {error_str}",
                            )
                        ]

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a valid API key for data operations. Check your API key in the Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error inserting data into table '{table_name}': {error_str}",
                        )
                    ]

            elif name == "update_table_data":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                supabase_key = arguments.get("supabase_key")
                table_name = arguments.get("table_name")
                data = arguments.get("data")
                filters = arguments.get("filters")

                # Validate required parameters
                if (
                    not project_ref
                    or not supabase_key
                    or not table_name
                    or data is None
                    or not filters
                ):
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not supabase_key:
                        missing_params.append("supabase_key")
                    if not table_name:
                        missing_params.append("table_name")
                    if data is None:
                        missing_params.append("data")
                    if not filters:
                        missing_params.append("filters")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # Prepare the update query with data
                    query = supabase.table(table_name).update(data)

                    # Apply all filters
                    for column, value in filters.items():
                        query = query.eq(column, value)

                    # Execute the query
                    response = query.execute()

                    # Check if the request was successful
                    if hasattr(response, "data") and response.data is not None:
                        rows = response.data
                        count = len(rows) if isinstance(rows, list) else 1

                        return [
                            types.TextContent(
                                type="text",
                                text=f"Successfully updated {count} rows in table '{table_name}':\n{json.dumps(rows, indent=2)}",
                            )
                        ]
                    else:
                        # Handle error or empty result
                        if hasattr(response, "error") and response.error:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Error updating data in table '{table_name}': {response.error.message}",
                                )
                            ]
                        else:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"No rows were updated in table '{table_name}'. This could be because no rows matched your filter criteria.",
                                )
                            ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error updating table data: {error_str}")

                    # Check if this is a table not found error
                    if (
                        "relation" in error_str.lower()
                        and "does not exist" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Table '{table_name}' does not exist in the database. Please create the table using the Supabase Dashboard before attempting to update data.",
                            )
                        ]

                    # Check if this is a constraint violation error
                    if (
                        "violates" in error_str.lower()
                        and "constraint" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: The update violates a database constraint. This could be due to a foreign key violation or other constraint: {error_str}",
                            )
                        ]

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a valid API key for data operations. Check your API key in the Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error updating data in table '{table_name}': {error_str}",
                        )
                    ]

            elif name == "delete_table_data":
                # Extract required parameters
                project_ref = arguments.get("project_ref")
                supabase_key = arguments.get("supabase_key")
                table_name = arguments.get("table_name")
                filters = arguments.get("filters")

                # Validate required parameters
                if not project_ref or not supabase_key or not table_name or not filters:
                    missing_params = []
                    if not project_ref:
                        missing_params.append("project_ref")
                    if not supabase_key:
                        missing_params.append("supabase_key")
                    if not table_name:
                        missing_params.append("table_name")
                    if not filters:
                        missing_params.append("filters")

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Missing required parameters: {', '.join(missing_params)}",
                        )
                    ]

                try:
                    # Get or create a Supabase SDK client for this project
                    supabase = get_or_create_supabase_sdk_client(
                        project_ref, supabase_key
                    )

                    # For safety, require at least one filter to be specified
                    if not filters:
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: At least one filter must be specified for delete operations to prevent accidental deletion of all rows.",
                            )
                        ]

                    # Prepare the delete query
                    query = supabase.table(table_name).delete()

                    # Apply all filters
                    for column, value in filters.items():
                        query = query.eq(column, value)

                    # Execute the query
                    response = query.execute()

                    # Check if the request was successful
                    if hasattr(response, "error") and response.error:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error deleting data from table '{table_name}': {response.error.message}",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Successfully deleted data from table '{table_name}' matching the specified filters.",
                        )
                    ]

                except Exception as e:
                    error_str = str(e)
                    logger.error(f"Error deleting table data: {error_str}")

                    # Check if this is a table not found error
                    if (
                        "relation" in error_str.lower()
                        and "does not exist" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: Table '{table_name}' does not exist in the database. Please create the table using the Supabase Dashboard before attempting to delete data.",
                            )
                        ]

                    # Check if this is a constraint violation error (e.g., foreign key constraint)
                    if (
                        "violates" in error_str.lower()
                        and "constraint" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Error: The delete operation violates a database constraint. This is likely because the data you're trying to delete is referenced by other tables: {error_str}",
                            )
                        ]

                    # Check if this is likely an API key permission issue
                    if (
                        "403" in error_str
                        or "unauthorized" in error_str.lower()
                        or "invalid signature" in error_str.lower()
                    ):
                        return [
                            types.TextContent(
                                type="text",
                                text="Error: You must use a valid API key for data operations. Check your API key in the Supabase Dashboard > Project Settings > API.",
                            )
                        ]

                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error deleting data from table '{table_name}': {error_str}",
                        )
                    ]

        except Exception as e:
            logger.error(f"Error calling Supabase API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="supabase-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("  python main.py - Run the server")
