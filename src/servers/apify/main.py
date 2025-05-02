import os
import sys
import json
import logging
import requests
from pathlib import Path
from typing import Optional

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.apify.util import authenticate_and_save_credentials, get_credentials

BASE_URL = "https://api.apify.com/v2"
SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id: str, api_key: Optional[str] = None) -> Server:
    """
    Creates and configures an Apify server instance with the specified tools.

    arguments:
        user_id: The user ID for authentication
        api_key: Optional API key for the authentication client

    Returns:
        Server: Configured server instance with Apify tools
    """
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            # Actors
            types.Tool(
                name="create_actor",
                description="Create a new Actor",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the actor alphanumeric characters, hyphens are allowed with no spaces",
                        },
                        "body": {"type": "object"},
                    },
                    "required": ["name"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor creation data",
                    "examples": [
                        '{"id": "actor123", "name": "My Actor", "username": "user123", "description": "A test actor"}'
                    ],
                },
            ),
            types.Tool(
                name="build_actor",
                description="Build an Actor from source code",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "actor_id": {"type": "string"},
                        "version": {"type": "string"},
                        "beta_packages": {"type": "boolean"},
                        "tag": {"type": "string"},
                        "use_cache": {"type": "boolean"},
                    },
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor build data",
                    "examples": [
                        '{"id": "build123", "actId": "actor123", "status": "READY", "buildNumber": "0.0.1"}'
                    ],
                },
            ),
            types.Tool(
                name="list_actors",
                description="List all Actors",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "offset": {"type": "integer"},
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor data",
                    "examples": [
                        '{"id": "actor123", "name": "My Actor", "username": "user123"}',
                        '{"id": "actor456", "name": "Another Actor", "username": "user456"}',
                    ],
                },
            ),
            types.Tool(
                name="get_actor",
                description="Get metadata for one Actor",
                inputSchema={
                    "type": "object",
                    "properties": {"actor_id": {"type": "string"}},
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor details",
                    "examples": [
                        '{"id": "actor123", "name": "My Actor", "username": "user123", "description": "A test actor"}'
                    ],
                },
            ),
            types.Tool(
                name="run_actor",
                description="Start an Actor run asynchronously",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "actor_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor run data",
                    "examples": [
                        '{"id": "run123", "actId": "actor123", "status": "READY", "startedAt": "2023-05-01T12:34:56.789Z"}'
                    ],
                },
            ),
            types.Tool(
                name="list_actor_runs",
                description="List runs for an Actor",
                inputSchema={
                    "type": "object",
                    "properties": {"actor_id": {"type": "string"}},
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing actor runs data",
                    "examples": [
                        '{"id": "run123", "actId": "actor123", "status": "SUCCEEDED"}',
                        '{"id": "run456", "actId": "actor123", "status": "RUNNING"}',
                    ],
                },
            ),
            types.Tool(
                name="delete_actor",
                description="Delete an Actor",
                inputSchema={
                    "type": "object",
                    "properties": {"actor_id": {"type": "string"}},
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing operation result",
                    "examples": [
                        '{"status": "success", "message": "delete_actor completed successfully"}'
                    ],
                },
            ),
            # Tasks
            types.Tool(
                name="list_tasks",
                description="List all Tasks",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing task data",
                    "examples": [
                        '{"id": "task123", "name": "My Task", "actId": "actor123"}',
                        '{"id": "task456", "name": "Another Task", "actId": "actor456"}',
                    ],
                },
            ),
            types.Tool(
                name="get_task",
                description="Get a Task",
                inputSchema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing task details",
                    "examples": [
                        '{"id": "task123", "name": "My Task", "actId": "actor123", "input": {"key": "value"}}'
                    ],
                },
            ),
            types.Tool(
                name="create_task",
                description="Create a new Task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "actor_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["actor_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing task creation data",
                    "examples": [
                        '{"id": "task123", "actId": "actor123", "name": "My Task", "username": "user123"}'
                    ],
                },
            ),
            types.Tool(
                name="update_task",
                description="Update an existing Task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["task_id", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated task data",
                    "examples": [
                        '{"id": "task123", "name": "Updated Task", "actId": "actor123", "description": "Updated description"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_task",
                description="Delete a Task",
                inputSchema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing operation result",
                    "examples": [
                        '{"status": "success", "message": "delete_task completed successfully"}'
                    ],
                },
            ),
            types.Tool(
                name="update_task_input",
                description="Update input for a Task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["task_id", "body"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated task input",
                    "examples": ['{"key1": "value1", "key2": "value2", "key3": 123}'],
                },
            ),
            types.Tool(
                name="run_task",
                description="Run a Task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "body": {"type": "object"},
                    },
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing task run data",
                    "examples": [
                        '{"id": "run123", "actId": "actor123", "actorTaskId": "task123", "status": "READY"}'
                    ],
                },
            ),
            types.Tool(
                name="list_task_runs",
                description="List runs for a Task",
                inputSchema={
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing task runs data",
                    "examples": [
                        '{"id": "run123", "actId": "actor123", "status": "SUCCEEDED"}',
                        '{"id": "run456", "actId": "actor123", "status": "RUNNING"}',
                    ],
                },
            ),
            # Datasets
            types.Tool(
                name="list_datasets",
                description="List all Datasets",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing dataset data",
                    "examples": [
                        '{"id": "dataset123", "name": "My Dataset", "itemCount": 42}',
                        '{"id": "dataset456", "name": "Another Dataset", "itemCount": 100}',
                    ],
                },
            ),
            types.Tool(
                name="delete_dataset",
                description="Delete a Dataset",
                inputSchema={
                    "type": "object",
                    "properties": {"dataset_id": {"type": "string"}},
                    "required": ["dataset_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing operation result",
                    "examples": [
                        '{"status": "success", "message": "delete_dataset completed successfully"}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        creds = await get_credentials(server.user_id, SERVICE_NAME, server.api_key)
        token = creds["token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        if not arguments:
            arguments = {}

        try:
            # Actors
            if name == "list_actors":
                response = requests.get(
                    f"{BASE_URL}/acts",
                    headers=headers,
                    params={
                        k: v
                        for k, v in (
                            ("limit", arguments.get("limit")),
                            ("offset", arguments.get("offset")),
                        )
                        if v is not None
                    },
                )

            elif name == "get_actor":
                response = requests.get(
                    f"{BASE_URL}/acts/{arguments['actor_id']}", headers=headers
                )

            elif name == "create_actor":
                body = arguments.get("body", {})
                body["name"] = arguments["name"]
                response = requests.post(f"{BASE_URL}/acts", headers=headers, json=body)

            elif name == "build_actor":
                # Always include these parameters
                params = {
                    "token": token,
                    "version": arguments.get(
                        "version", "0.0"
                    ),  # Default to 0.0 if not provided
                }

                if arguments.get("beta_packages"):
                    params["betaPackages"] = arguments["beta_packages"]
                if arguments.get("tag"):
                    params["tag"] = arguments["tag"]
                if arguments.get("use_cache"):
                    params["useCache"] = arguments["use_cache"]

                # Use the actor ID directly in the URL with no headers
                actor_id = arguments["actor_id"]
                response = requests.post(
                    f"{BASE_URL}/acts/{actor_id}/builds", params=params
                )
            elif name == "run_actor":
                response = requests.post(
                    f"{BASE_URL}/acts/{arguments['actor_id']}/runs",
                    headers=headers,
                    json=arguments.get("body", {}),
                )

            elif name == "list_actor_runs":
                response = requests.get(
                    f"{BASE_URL}/acts/{arguments['actor_id']}/runs", headers=headers
                )
            elif name == "delete_actor":
                response = requests.delete(
                    f"{BASE_URL}/acts/{arguments['actor_id']}", headers=headers
                )
            elif name == "list_tasks":
                response = requests.get(f"{BASE_URL}/actor-tasks", headers=headers)
            elif name == "get_task":
                response = requests.get(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}", headers=headers
                )
            elif name == "create_task":
                # Using camelCase "actId" here because that's the field name expected by the Apify API
                body = {"actId": arguments["actor_id"]}
                if arguments.get("body"):
                    body["body"] = arguments["body"]
                response = requests.post(
                    f"{BASE_URL}/actor-tasks", headers=headers, json=body
                )
            elif name == "update_task":
                response = requests.put(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}",
                    headers=headers,
                    json=arguments["body"],
                )
            elif name == "delete_task":
                response = requests.delete(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}", headers=headers
                )
            elif name == "update_task_input":
                response = requests.put(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}/input",
                    headers=headers,
                    json=arguments["body"],
                )
            elif name == "run_task":
                response = requests.post(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}/runs",
                    headers=headers,
                    json=arguments.get("body", {}),
                )
            elif name == "list_task_runs":
                response = requests.get(
                    f"{BASE_URL}/actor-tasks/{arguments['task_id']}/runs",
                    headers=headers,
                )
            # Datasets
            elif name == "list_datasets":
                # Add pagination parameters to ensure we get all datasets
                params = {
                    k: v
                    for k, v in (
                        ("limit", arguments.get("limit", 1000)),
                        ("offset", arguments.get("offset", 0)),
                        ("desc", arguments.get("desc", False)),
                    )
                    if v is not None
                }
                response = requests.get(
                    f"{BASE_URL}/datasets", headers=headers, params=params
                )
            elif name == "delete_dataset":
                response = requests.delete(
                    f"{BASE_URL}/datasets/{arguments['dataset_id']}", headers=headers
                )

            else:
                raise ValueError(f"Unknown tool: {name}")

            if response.status_code == 204:
                result = {
                    "status": "success",
                    "message": f"{name} completed successfully",
                }
                return [types.TextContent(type="text", text=json.dumps(result))]
            elif response.status_code in [200, 201]:
                response_json = response.json()

                # Handle response with data field containing items array
                if isinstance(response_json, dict) and "data" in response_json:
                    data = response_json["data"]

                    # If data contains items array, return each item separately
                    if (
                        isinstance(data, dict)
                        and "items" in data
                        and isinstance(data["items"], list)
                    ):
                        items = data["items"]
                        if items:
                            return [
                                types.TextContent(type="text", text=json.dumps(item))
                                for item in items
                            ]
                        else:
                            # Empty array case
                            return [types.TextContent(type="text", text=json.dumps({}))]

                    # Otherwise return data as a single item
                    return [types.TextContent(type="text", text=json.dumps(data))]

                # For update_task_input which returns the input directly
                elif name == "update_task_input":
                    return [
                        types.TextContent(type="text", text=json.dumps(response_json))
                    ]

                # Default case: return the whole response
                return [types.TextContent(type="text", text=json.dumps(response_json))]
            else:
                error = {
                    "error": {
                        "message": f"API Error: {response.text}",
                        "statusCode": response.status_code,
                    }
                }
                return [types.TextContent(type="text", text=json.dumps(error))]

        except Exception as e:
            error = {
                "error": {
                    "Exception": str(e),
                    "traceback": e.__traceback__.tb_lineno,
                }
            }
            return [types.TextContent(type="text", text=json.dumps(error))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """
    Creates initialization options for the server instance.

    arguments:
        server_instance: The server instance to create initialization options for

    Returns:
        InitializationOptions: Configured initialization options
    """
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
        authenticate_and_save_credentials("local", SERVICE_NAME)
        print(
            f"Authentication complete for local user. You can now run the {SERVICE_NAME} server."
        )
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
