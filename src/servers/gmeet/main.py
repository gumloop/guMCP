import os
import sys
import logging
import json
import uuid
from pathlib import Path

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from src.utils.google.util import authenticate_and_save_credentials
from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gmeet-server")


async def get_credentials(user_id, api_key=None):
    """Get stored or active credentials for Google Meet API."""
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials(SERVICE_NAME, user_id)

    if not credentials_data:
        raise ValueError(
            f"Credentials not found for user {user_id}. Run with 'auth' first."
        )

    token = credentials_data.get("token")
    if token:
        return Credentials.from_authorized_user_info(credentials_data)
    access_token = credentials_data.get("access_token")
    if access_token:
        return Credentials(token=access_token)

    raise ValueError(f"Valid token not found for user {user_id}")


async def create_gmeet_service(user_id, api_key=None):
    """Create an authorized Google Meet API service."""
    credentials = await get_credentials(user_id, api_key=api_key)
    return build("calendar", "v3", credentials=credentials)


def create_server(user_id, api_key=None):
    server = Server("gmeet-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Register all supported tools for Google Meet."""
        return [
            types.Tool(
                name="create_meeting",
                description="Create a new meeting",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the meeting",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the meeting",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of email addresses of attendees",
                        },
                    },
                    "required": ["title", "start_time", "end_time"],
                },
            ),
            types.Tool(
                name="add_attendees",
                description="Add attendees to a meeting.",
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
                description="Fetch all meetings for a given date.",
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
                name="get_meeting_details",
                description="Get details of a meeting by meeting id.",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="update_meeting",
                description="Update a meeting by meeting id.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "meeting_id": {"type": "string"},
                        "summary": {
                            "type": "string",
                            "description": "Summary/title of the meeting",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the meeting",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                    },
                    "required": ["meeting_id"],
                },
            ),
            types.Tool(
                name="delete_meeting",
                description="Delete a meeting by meeting id.",
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
        gm = await create_gmeet_service(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            if name == "create_meeting":
                event = {
                    "summary": arguments["title"],
                    "description": arguments.get("description", ""),
                    "start": {"dateTime": arguments["start_time"], "timeZone": "UTC"},
                    "end": {"dateTime": arguments["end_time"], "timeZone": "UTC"},
                    "conferenceData": {
                        "createRequest": {"requestId": f"meeting-{uuid.uuid4()}"}
                    },
                }

                if "attendees" in arguments:
                    event["attendees"] = [
                        {"email": email} for email in arguments["attendees"]
                    ]

                result = (
                    gm.events()
                    .insert(calendarId="primary", body=event, conferenceDataVersion=1)
                    .execute()
                )

            elif name == "add_attendees":
                # First get the existing event to preserve its data
                event = (
                    gm.events()
                    .get(calendarId="primary", eventId=arguments["meeting_id"])
                    .execute()
                )

                # Update only the attendees field
                event["attendees"] = [
                    {"email": email} for email in arguments["attendees"]
                ]

                # Send the update with the complete event data
                result = (
                    gm.events()
                    .update(
                        calendarId="primary",
                        eventId=arguments["meeting_id"],
                        body=event,
                    )
                    .execute()
                )

            elif name == "fetch_meetings_by_date":
                # Format the date with proper time boundaries for the full day
                date = arguments["date"]
                time_min = f"{date}T00:00:00Z"
                time_max = f"{date}T23:59:59Z"

                result = (
                    gm.events()
                    .list(
                        calendarId="primary",
                        timeMin=time_min,
                        timeMax=time_max,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

            elif name == "get_meeting_details":
                # For Google Meet, we need to use the calendar API to get meeting details
                # The meeting_id is actually the event ID that contains the conference data

                result = (
                    gm.events()
                    .get(
                        calendarId="primary",
                        eventId=arguments["meeting_id"],
                    )
                    .execute()
                )

            elif name == "update_meeting":
                # First get the existing event to preserve its data
                event = (
                    gm.events()
                    .get(calendarId="primary", eventId=arguments["meeting_id"])
                    .execute()
                )

                # Update the event with the provided arguments
                for key, value in arguments.items():
                    if (
                        key != "meeting_id"
                    ):  # Skip the meeting_id as it's not part of the event data
                        event[key] = value

                result = (
                    gm.events()
                    .update(
                        calendarId="primary",
                        eventId=arguments["meeting_id"],
                        body=event,
                    )
                    .execute()
                )

            elif name == "delete_meeting":
                result = (
                    gm.events()
                    .delete(calendarId="primary", eventId=arguments["meeting_id"])
                    .execute()
                )

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error calling Google Meet API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="gmeet-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
