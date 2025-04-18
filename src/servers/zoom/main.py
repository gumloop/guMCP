import os
import sys
import logging
import json
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
import requests

from src.utils.zoom.util import authenticate_and_save_credentials
from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "meeting:read:list_upcoming_meetings",
    "meeting:read:participant",
    "meeting:read:list_meetings",
    "meeting:read:meeting",
    "meeting:write:meeting",
    "meeting:write:registrant",
    "meeting:update:meeting",
    "meeting:delete:meeting",
    "meeting:write:invite_links",
    "cloud_recording:read:list_recording_files",
    "cloud_recording:read:list_user_recordings",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("zoom-server")

BASE_URL = "https://api.zoom.us/v2"


async def get_credentials(user_id, api_key=None):
    """Get stored or active credentials for Zoom API."""
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    if not credentials_data:
        raise ValueError(
            f"Credentials not found for user {user_id}. Run with 'auth' first."
        )

    access_token = credentials_data.get("access_token")
    if not access_token:
        raise ValueError(f"Valid access token not found for user {user_id}")

    # Log available scopes
    if "scope" in credentials_data:
        logger.info(f"Token has scopes: {credentials_data['scope']}")

    return credentials_data


async def create_zoom_client(user_id, api_key=None):
    """Create an authorized Zoom API client."""
    credentials = await get_credentials(user_id, api_key=api_key)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {credentials['access_token']}"})
    return session


def create_server(user_id, api_key=None):
    server = Server("zoom-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Register all supported tools for Zoom."""
        return [
            types.Tool(
                name="create_meeting",
                description="Create a new Zoom meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Topic of the meeting",
                        },
                        "agenda": {
                            "type": "string",
                            "description": "Agenda of the meeting",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "duration": {
                            "type": "integer",
                            "description": "Duration of the meeting in minutes",
                        },
                    },
                    "required": ["topic", "start_time", "duration"],
                },
            ),
            types.Tool(
                name="update_meeting",
                description="Update an existing Zoom meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "topic": {
                            "type": "string",
                            "description": "Topic of the meeting",
                        },
                        "agenda": {
                            "type": "string",
                            "description": "Agenda of the meeting",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "duration": {
                            "type": "integer",
                            "description": "Duration of the meeting in minutes",
                        },
                    },
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="get_meeting",
                description="Get details of a Zoom meeting",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="list_meetings",
                description="List all Zoom meetings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "Meeting type: scheduled, live, upcoming",
                            "enum": ["scheduled", "live", "upcoming"],
                        },
                    },
                    "required": ["type"],
                },
            ),
            types.Tool(
                name="list_upcoming_meetings",
                description="List all upcoming Zoom meetings",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            types.Tool(
                name="list_all_recordings",
                description="List all recordings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "from_date": {
                            "type": "string",
                            "description": "From date in YYYY-MM-DD format",
                        },
                        "to_date": {
                            "type": "string",
                            "description": "To date in YYYY-MM-DD format",
                        },
                    },
                    "required": ["from_date", "to_date"],
                },
            ),
            types.Tool(
                name="get_meeting_recordings",
                description="Get recordings for a specific meeting",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="get_meeting_participant_reports",
                description="Get participant reports for a meeting",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="add_attendees",
                description="Add attendees to a Zoom meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of email addresses of attendees",
                        },
                    },
                    "required": ["meeting_id", "attendees"],
                },
            ),
            types.Tool(
                name="fetch_meetings_by_date",
                description="Fetch all Zoom meetings for a given date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in ISO format (YYYY-MM-DD)",
                        }
                    },
                    "required": ["date"],
                },
            ),
            types.Tool(
                name="delete_meeting",
                description="Delete a Zoom meeting",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        client = await create_zoom_client(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            if name == "create_meeting":
                # Ensure time has timezone if not provided
                start_time = arguments["start_time"]
                if (
                    "Z" not in start_time
                    and "+" not in start_time
                    and "-" not in start_time
                ):
                    start_time = (
                        f"{start_time}Z"  # Add UTC timezone indicator if missing
                    )

                data = {
                    "topic": arguments["topic"],
                    "type": 2,  # Scheduled meeting
                    "start_time": start_time,
                    "duration": arguments["duration"],
                    "settings": {
                        "host_video": True,
                        "participant_video": True,
                        "join_before_host": False,
                        "mute_upon_entry": True,
                        "auto_recording": "none",
                    },
                }

                if "agenda" in arguments:
                    data["agenda"] = arguments["agenda"]

                response = client.post(f"{BASE_URL}/users/me/meetings", json=data)
                response.raise_for_status()
                result = response.json()

            elif name == "update_meeting":
                data = {}

                for key in ["topic", "agenda", "start_time", "duration"]:
                    if key in arguments:
                        data[key] = arguments[key]

                response = client.patch(
                    f"{BASE_URL}/meetings/{arguments['meeting_id']}", json=data
                )

                if response.status_code == 204:
                    result = {
                        "status": "success",
                        "message": "Meeting updated successfully",
                    }
                else:
                    response.raise_for_status()
                    result = response.json()

            elif name == "get_meeting":
                response = client.get(f"{BASE_URL}/meetings/{arguments['meeting_id']}")
                response.raise_for_status()
                result = response.json()

            elif name == "list_meetings":
                response = client.get(
                    f"{BASE_URL}/users/me/meetings", params={"type": arguments["type"]}
                )
                response.raise_for_status()
                result = response.json()
                result = result.get("meetings", result)

            elif name == "list_upcoming_meetings":
                # Get scheduled meetings and filter for upcoming ones
                response = client.get(
                    f"{BASE_URL}/users/me/meetings",
                    params={"type": "scheduled", "page_size": 100},
                )
                response.raise_for_status()

                # Filter to only include meetings that haven't started yet
                result = response.json()
                meetings = result.get("meetings", [])
                now = datetime.utcnow().isoformat() + "Z"
                upcoming_meetings = [
                    meeting
                    for meeting in meetings
                    if meeting.get("start_time", "") > now
                ]
                result["meetings"] = upcoming_meetings

            elif name == "list_all_recordings":
                response = client.get(
                    f"{BASE_URL}/users/me/recordings",
                    params={"from": arguments["from_date"], "to": arguments["to_date"]},
                )
                response.raise_for_status()
                result = response.json()

            elif name == "get_meeting_recordings":
                response = client.get(
                    f"{BASE_URL}/meetings/{arguments['meeting_id']}/recordings"
                )
                response.raise_for_status()
                result = response.json()

            elif name == "get_meeting_participant_reports":
                response = client.get(
                    f"{BASE_URL}/report/meetings/{arguments['meeting_id']}/participants"
                )
                response.raise_for_status()
                result = response.json()

            elif name == "add_attendees":
                # Format attendees for Zoom API
                attendees = [{"email": email} for email in arguments["attendees"]]

                # Update the attendees
                response = client.patch(
                    f"{BASE_URL}/meetings/{arguments['meeting_id']}",
                    json={"settings": {"meeting_invitees": attendees}},
                )
                if response.status_code == 204:
                    result = {
                        "status": "success",
                        "message": "Attendees added successfully",
                    }
                else:
                    response.raise_for_status()
                    result = response.json()

            elif name == "fetch_meetings_by_date":
                # Format the date with proper time boundaries for the full day
                date = arguments["date"]
                from_time = f"{date}T00:00:00Z"
                to_time = f"{date}T23:59:59Z"

                response = client.get(
                    f"{BASE_URL}/users/me/meetings",
                    params={"type": "scheduled", "from": from_time, "to": to_time},
                )
                response.raise_for_status()
                result = response.json()

            elif name == "delete_meeting":
                response = client.delete(
                    f"{BASE_URL}/meetings/{arguments['meeting_id']}",
                    params={"schedule_for_reminder": "false"},
                )
                if response.status_code == 204:
                    result = {
                        "status": "success",
                        "message": "Meeting deleted successfully",
                    }
                else:
                    response.raise_for_status()
                    result = response.json()

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling Zoom API: {e}")
            error_details = str(e)

            # Extract more detailed error information if available
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_json = e.response.json()
                    error_details = f"{e} - Details: {json.dumps(error_json)}"
                except:
                    error_details = f"{e} - Response: {e.response.text}"

            return [types.TextContent(type="text", text=f"Error: {error_details}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="zoom-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
