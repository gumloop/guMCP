import os
import sys
from typing import Optional, Iterable
import json

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx

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

from src.utils.typeform.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
TYPEFORM_API_URL = "https://api.typeform.com"
SCOPES = [
    "forms:read",
    "responses:read",
    "workspaces:read",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def execute_typeform_request(
    endpoint, method="GET", params=None, access_token=None
):
    """Execute a request against the Typeform API"""
    if not access_token:
        raise ValueError("Typeform access token is required")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    url = f"{TYPEFORM_API_URL}/{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method == "POST":
                response = await client.post(url, json=params, headers=headers)
            elif method == "PUT":
                response = await client.put(url, json=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error in API request to {endpoint}: {str(e)}")
        raise


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("typeform-server")

    server.user_id = user_id

    async def get_typeform_access_token():
        """Get Typeform access token for the current user"""
        try:
            credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
            if isinstance(credentials, dict):
                return credentials.get("access_token")
            return credentials
        except Exception as e:
            logger.error(f"Error getting Typeform credentials: {str(e)}")
            raise

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List resources from Typeform (workspaces and forms)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        try:
            access_token = await get_typeform_access_token()
            resources = []

            # Get workspaces first
            workspaces_result = await execute_typeform_request(
                "workspaces", access_token=access_token
            )

            workspaces = workspaces_result.get("items", [])

            # Add workspaces as resources
            for workspace in workspaces:
                if not workspace.get("id") or not workspace.get("name"):
                    logger.warning(
                        f"Skipping workspace with incomplete data: {workspace}"
                    )
                    continue

                resources.append(
                    Resource(
                        uri=f"typeform://workspace/{workspace['id']}",
                        mimeType="application/json",
                        name=f"Workspace: {workspace['name']}",
                    )
                )

            # Then get all forms (not filtered by workspace yet)
            params = {"page_size": 10}
            if cursor:
                params["page"] = cursor

            forms_result = await execute_typeform_request(
                "forms", params=params, access_token=access_token
            )

            forms = forms_result.get("items", [])

            # Add forms as resources
            for form in forms:
                if not form.get("id") or not form.get("title"):
                    logger.warning(f"Skipping form with incomplete data: {form}")
                    continue

                # In case workspace info is missing, provide default values
                workspace_info = form.get("workspace", {}) or {}
                workspace_id = workspace_info.get("id", "default")
                resources.append(
                    Resource(
                        uri=f"typeform://form/{form['id']}",
                        mimeType="application/json",
                        name=f"Form: {form['title']} (Workspace: {workspace_id})",
                    )
                )

            return resources

        except Exception as e:
            import traceback

            logger.error(f"Error fetching Typeform resources: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            # Return empty list instead of failing completely
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from Typeform by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        try:
            access_token = await get_typeform_access_token()

            uri_str = str(uri)

            if uri_str.startswith("typeform://workspace/"):
                # Handle workspace resource
                workspace_id = uri_str.replace("typeform://workspace/", "")

                # Get workspace details
                workspace_data = await execute_typeform_request(
                    f"workspaces/{workspace_id}", access_token=access_token
                )

                # Get forms in this workspace
                forms_result = await execute_typeform_request(
                    "forms",
                    params={"workspace_id": workspace_id, "page_size": 20},
                    access_token=access_token,
                )

                forms = forms_result.get("items", [])

                # Combine data
                result = {"workspace": workspace_data, "forms": forms}

                formatted_content = json.dumps(result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("typeform://form/"):
                # Handle form resource
                form_id = uri_str.replace("typeform://form/", "")

                # Get form details
                form_data = await execute_typeform_request(
                    f"forms/{form_id}", access_token=access_token
                )

                # Get form responses summary (limited to 10)
                responses_data = await execute_typeform_request(
                    f"forms/{form_id}/responses",
                    params={"page_size": 10},
                    access_token=access_token,
                )

                # Make sure responses_data["items"] is a list - handle potential None values
                items = responses_data.get("items", []) or []

                # Combine data
                result = {
                    "form": form_data,
                    "responses_summary": {
                        "total_items": responses_data.get("total_items", 0),
                        "response_count": len(items),
                        "latest_responses": items[
                            :5
                        ],  # Include only the 5 most recent responses
                    },
                }

                formatted_content = json.dumps(result, indent=2)
                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            import traceback

            logger.error(f"Error reading Typeform resource: {str(e)}")
            logger.error(f"Stacktrace: {traceback.format_exc()}")
            raise ValueError(f"Error reading resource: {str(e)}")

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Typeform"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="list_workspaces",
                description="List all workspaces in your Typeform account",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="list_forms_by_workspace",
                description="List forms in a specific workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "workspace_id": {
                            "type": "string",
                            "description": "ID of the workspace",
                        }
                    },
                    "required": ["workspace_id"],
                },
            ),
            Tool(
                name="search_forms",
                description="Search for forms in Typeform",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query for forms",
                        },
                        "workspace_id": {
                            "type": "string",
                            "description": "Optionally filter by workspace ID",
                        },
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_form_responses",
                description="Get responses for a specific form",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of responses to retrieve (default: 10)",
                        },
                        "since": {
                            "type": "string",
                            "description": "Get responses submitted since this date (ISO format)",
                        },
                        "fields": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific field IDs to include in the response (optional)",
                        },
                    },
                    "required": ["form_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Typeform"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        try:
            access_token = await get_typeform_access_token()

            if name == "list_workspaces":
                workspaces_result = await execute_typeform_request(
                    "workspaces", access_token=access_token
                )

                workspaces = workspaces_result.get("items", [])

                if not workspaces:
                    return [
                        TextContent(
                            type="text", text="No workspaces found in your account."
                        )
                    ]

                workspace_list = []
                for workspace in workspaces:
                    workspace_list.append(
                        f"Name: {workspace.get('name', 'Unnamed')}\n"
                        f"  ID: {workspace.get('id', 'Unknown')}\n"
                        f"  Default: {'Yes' if workspace.get('default', False) else 'No'}\n"
                        f"  Shared: {'Yes' if workspace.get('shared', False) else 'No'}"
                    )

                formatted_result = "\n\n".join(workspace_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(workspaces)} workspaces:\n\n{formatted_result}",
                    )
                ]

            elif name == "list_forms_by_workspace":
                if not arguments or "workspace_id" not in arguments:
                    raise ValueError("Missing workspace_id parameter")

                workspace_id = arguments["workspace_id"]

                # Get workspace details first to show the name
                workspace_data = await execute_typeform_request(
                    f"workspaces/{workspace_id}", access_token=access_token
                )

                workspace_name = workspace_data.get("name", "Unknown workspace")

                # Get forms in this workspace
                forms_result = await execute_typeform_request(
                    "forms",
                    params={"workspace_id": workspace_id, "page_size": 50},
                    access_token=access_token,
                )

                forms = forms_result.get("items", [])

                if not forms:
                    return [
                        TextContent(
                            type="text",
                            text=f"No forms found in workspace '{workspace_name}' (ID: {workspace_id}).",
                        )
                    ]

                form_list = []
                for form in forms:
                    form_title = form.get("title", "Untitled Form")
                    form_id = form.get("id", "Unknown")
                    form_created = form.get("created_at", "Unknown")
                    form_url = form.get("_links", {}).get("display", "No URL available")

                    form_list.append(
                        f"Title: {form_title}\n"
                        f"  ID: {form_id}\n"
                        f"  Created: {form_created}\n"
                        f"  URL: {form_url}"
                    )

                formatted_result = "\n\n".join(form_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Workspace: {workspace_name}\n\n"
                        f"Found {len(forms)} forms:\n\n{formatted_result}",
                    )
                ]

            elif name == "search_forms":
                if not arguments or "query" not in arguments:
                    raise ValueError("Missing query parameter")

                query = arguments["query"]
                workspace_id = arguments.get("workspace_id")

                # Get all forms first, optionally filtered by workspace
                params = {}
                if workspace_id:
                    params["workspace_id"] = workspace_id

                forms_result = await execute_typeform_request(
                    "forms", params=params, access_token=access_token
                )

                forms = forms_result.get("items", [])

                # Filter forms by query (client-side search since Typeform API doesn't have search endpoint)
                matching_forms = [
                    form
                    for form in forms
                    if query.lower() in form.get("title", "").lower()
                ]

                if not matching_forms:
                    workspace_msg = (
                        f" in workspace {workspace_id}" if workspace_id else ""
                    )
                    return [
                        TextContent(
                            type="text",
                            text=f"No forms found matching '{query}'{workspace_msg}.",
                        )
                    ]

                form_list = []
                for form in matching_forms:
                    workspace_info = form.get("workspace", {}) or {}
                    workspace_name = workspace_info.get("name", "Unknown workspace")
                    workspace_id = workspace_info.get("id", "Unknown")
                    form_title = form.get("title", "Untitled Form")
                    form_id = form.get("id", "Unknown")
                    form_created = form.get("created_at", "Unknown")
                    form_updated = form.get("last_updated_at", "Unknown")
                    form_url = form.get("_links", {}).get("display", "No URL available")

                    form_list.append(
                        f"Title: {form_title}\n"
                        f"  ID: {form_id}\n"
                        f"  Workspace: {workspace_name} (ID: {workspace_id})\n"
                        f"  Created: {form_created}\n"
                        f"  Last Updated: {form_updated}\n"
                        f"  URL: {form_url}"
                    )

                formatted_result = "\n\n".join(form_list)
                return [
                    TextContent(
                        type="text",
                        text=f"Found {len(matching_forms)} forms matching '{query}':\n\n{formatted_result}",
                    )
                ]

            elif name == "get_form_responses":
                if not arguments or "form_id" not in arguments:
                    raise ValueError("Missing form_id parameter")

                form_id = arguments["form_id"]
                limit = arguments.get("limit", 10)
                since = arguments.get("since")
                fields = arguments.get("fields", [])

                # Set up parameters
                params = {"page_size": limit}
                if since:
                    params["since"] = since
                if fields:
                    params["fields"] = ",".join(fields)

                # Get form responses
                responses_result = await execute_typeform_request(
                    f"forms/{form_id}/responses",
                    params=params,
                    access_token=access_token,
                )

                total_responses = responses_result.get("total_items", 0)
                responses = responses_result.get("items", []) or []

                if not responses:
                    return [
                        TextContent(
                            type="text",
                            text=f"No responses found for form with ID: {form_id}",
                        )
                    ]

                # Get form details to include the title
                form_data = await execute_typeform_request(
                    f"forms/{form_id}", access_token=access_token
                )

                form_title = form_data.get("title", "Unknown form")

                # Format responses
                response_summaries = []
                for resp in responses:
                    submission_time = resp.get("submitted_at", "Unknown")
                    answers = resp.get("answers", []) or []
                    response_id = resp.get("response_id", "Unknown")

                    answer_text = []
                    for answer in answers:
                        field = answer.get("field", {}) or {}
                        question = field.get("title", "Unknown question")
                        field_id = field.get("id", "unknown")
                        answer_type = answer.get("type", "unknown")

                        # Skip if fields filter is provided and this field is not in it
                        if fields and field_id not in fields:
                            continue

                        if answer_type == "choice":
                            choice = answer.get("choice", {}) or {}
                            answer_value = choice.get("label", "")
                        elif answer_type == "choices":
                            choices = answer.get("choices", {}) or {}
                            labels = choices.get("labels", []) or []
                            answer_value = ", ".join(
                                [c.get("label", "") for c in labels]
                            )
                        elif answer_type == "text":
                            answer_value = answer.get("text", "")
                        elif answer_type == "number":
                            answer_value = str(answer.get("number", ""))
                        elif answer_type == "email":
                            answer_value = answer.get("email", "")
                        elif answer_type == "url":
                            answer_value = answer.get("url", "")
                        elif answer_type == "date":
                            answer_value = answer.get("date", "")
                        else:
                            answer_value = json.dumps(answer)

                        answer_text.append(
                            f"{question} (ID: {field_id}): {answer_value}"
                        )

                    response_summaries.append(
                        f"Response ID: {response_id}\n"
                        f"Submitted: {submission_time}\n"
                        f"Answers:\n  " + "\n  ".join(answer_text)
                    )

                formatted_result = "\n\n" + "\n\n".join(response_summaries)
                fields_info = (
                    f"Filtered to fields: {', '.join(fields)}\n" if fields else ""
                )

                return [
                    TextContent(
                        type="text",
                        text=f"Form: {form_title}\n"
                        f"Total responses: {total_responses}\n"
                        f"{fields_info}"
                        f"Showing {len(responses)} responses (limit: {limit}):{formatted_result}",
                    )
                ]

            raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error executing tool {name}: {str(e)}")
            return [
                TextContent(type="text", text=f"Error executing {name} tool: {str(e)}")
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="typeform-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


# Main handler allows users to auth
if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        # Run authentication flow
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
