import os
import sys
import logging
import json
import uuid
from pathlib import Path
from typing import Optional, Iterable
from datetime import datetime, timedelta

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import AnyUrl, Resource, TextContent, EmbeddedResource
from mcp.server.lowlevel.helper_types import ReadResourceContents

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


def format_meeting(event):
    """Format a calendar event with Google Meet data for display"""
    # Extract key information
    meeting_id = event.get("id", "")
    title = event.get("summary", "Untitled Meeting")
    description = event.get("description", "")

    # Get meeting link if available
    meet_link = event.get("hangoutLink", "")

    # Get start and end times
    start = event.get("start", {}).get(
        "dateTime", event.get("start", {}).get("date", "")
    )
    end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))

    # Format times
    if "T" in start:  # This is a datetime
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        start_time = start_dt.strftime("%Y-%m-%d %H:%M")
    else:  # This is a date
        start_time = start

    if "T" in end:  # This is a datetime
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        end_time = end_dt.strftime("%Y-%m-%d %H:%M")
    else:  # This is a date
        end_time = end

    # Get attendees
    attendees = []
    for attendee in event.get("attendees", []):
        attendees.append(attendee.get("email", ""))

    # Get conference data if available
    conference_data = event.get("conferenceData", {})
    conference_id = conference_data.get("conferenceId", "")

    return {
        "id": meeting_id,
        "title": title,
        "description": description,
        "start_time": start_time,
        "end_time": end_time,
        "meet_link": meet_link,
        "conference_id": conference_id,
        "attendees": attendees,
    }


def has_gmeet_link(event):
    """Check if an event has a Google Meet link"""
    return "hangoutLink" in event or "conferenceData" in event


def create_server(user_id, api_key=None):
    server = Server("gmeet-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Google Meet meetings"""
        logger.info(
            f"Listing meetings for user: {server.user_id} with cursor: {cursor}"
        )

        gm = await create_gmeet_service(server.user_id, server.api_key)

        # Calculate time range (next 30 days)
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

        try:
            # List calendar events with Google Meet links
            events_result = (
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

            events = events_result.get("items", [])

            # Filter for events with Google Meet links
            meetings = [event for event in events if has_gmeet_link(event)]

            resources = []
            for meeting in meetings:
                meeting_id = meeting.get("id")
                title = meeting.get("summary", "Untitled Meeting")
                start = meeting.get("start", {}).get("dateTime", "")

                # Format start time for description
                if start:
                    try:
                        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        start_formatted = start_dt.strftime("%Y-%m-%d %H:%M")
                    except (ValueError, TypeError):
                        start_formatted = start
                else:
                    start_formatted = "Unknown time"

                description = f"Google Meet: {start_formatted}"
                if "hangoutLink" in meeting:
                    link = meeting["hangoutLink"]
                    description += f" - {link}"

                resource = Resource(
                    uri=f"gmeet://meeting/{meeting_id}",
                    mimeType="application/json",
                    name=title,
                    description=description,
                )
                resources.append(resource)

            return resources
        except Exception as e:
            logger.error(f"Error listing meetings: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a Google Meet meeting resource"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        gm = await create_gmeet_service(server.user_id, server.api_key)

        uri_str = str(uri)
        if not uri_str.startswith("gmeet://"):
            raise ValueError(f"Invalid Google Meet URI: {uri_str}")

        # Parse the URI to get resource type and ID
        parts = uri_str.replace("gmeet://", "").split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid Google Meet URI format: {uri_str}")

        resource_type, resource_id = parts

        try:
            if resource_type == "meeting":
                # Get meeting details via calendar event
                event = (
                    gm.events()
                    .get(
                        calendarId="primary",
                        eventId=resource_id,
                    )
                    .execute()
                )

                if has_gmeet_link(event):
                    meeting = format_meeting(event)

                    # Format content for display
                    content = f"# {meeting['title']}\n\n"
                    content += f"**Time**: {meeting['start_time']} to {meeting['end_time']}\n\n"

                    if meeting["description"]:
                        content += f"**Description**: {meeting['description']}\n\n"

                    if meeting["meet_link"]:
                        content += f"**Join link**: {meeting['meet_link']}\n\n"

                    if meeting["attendees"]:
                        content += f"**Attendees**:\n"
                        for attendee in meeting["attendees"]:
                            content += f"- {attendee}\n"

                    # Also provide the raw JSON
                    raw_json = json.dumps(event, indent=2)

                    return [
                        ReadResourceContents(
                            content=content, mime_type="text/markdown"
                        ),
                        ReadResourceContents(
                            content=raw_json, mime_type="application/json"
                        ),
                    ]
                else:
                    return [
                        ReadResourceContents(
                            content=f"Event {resource_id} does not have Google Meet integration.",
                            mime_type="text/plain",
                        )
                    ]
            else:
                raise ValueError(f"Unsupported resource type: {resource_type}")

        except Exception as e:
            logger.error(f"Error reading Google Meet resource: {e}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the created meeting including ID, title, time, and Google Meet link",
                    "examples": [
                        '{\n  "kind": "calendar#event",\n  "etag": "\\"3494432576239902\\"",\n  "id": "abc123xyz456",\n  "status": "confirmed",\n  "htmlLink": "https://www.google.com/calendar/event?eid=example",\n  "created": "2025-05-14T09:51:27.000Z",\n  "updated": "2025-05-14T09:51:28.119Z",\n  "summary": "Test Meeting Example",\n  "description": "This is a test meeting created by the test_create_meeting tool.",\n  "creator": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "organizer": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "start": {\n    "dateTime": "2025-05-14T03:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "end": {\n    "dateTime": "2025-05-14T04:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "iCalUID": "abc123xyz456@google.com",\n  "sequence": 0,\n  "hangoutLink": "https://meet.google.com/abc-defg-hij",\n  "conferenceData": {\n    "createRequest": {\n      "requestId": "meeting-example-id",\n      "conferenceSolutionKey": {\n        "type": "hangoutsMeet"\n      },\n      "status": {\n        "statusCode": "success"\n      }\n    },\n    "entryPoints": [\n      {\n        "entryPointType": "video",\n        "uri": "https://meet.google.com/abc-defg-hij",\n        "label": "meet.google.com/abc-defg-hij"\n      }\n    ],\n    "conferenceSolution": {\n      "key": {\n        "type": "hangoutsMeet"\n      },\n      "name": "Google Meet",\n      "iconUri": "https://fonts.gstatic.com/s/i/productlogos/meet_2020q4/v6/web-512dp/logo_meet_2020q4_color_2x_web_512dp.png"\n    },\n    "conferenceId": "abc-defg-hij"\n  },\n  "reminders": {\n    "useDefault": true\n  },\n  "eventType": "default"\n}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar.events"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Details of the updated meeting with added attendees",
                    "examples": [
                        '{\n  "kind": "calendar#event",\n  "etag": "\\"3494432592472862\\"",\n  "id": "abc123xyz456",\n  "status": "confirmed",\n  "htmlLink": "https://www.google.com/calendar/event?eid=example",\n  "created": "2025-05-14T09:51:27.000Z",\n  "updated": "2025-05-14T09:51:36.236Z",\n  "summary": "Test Meeting Example",\n  "description": "This is a test meeting.",\n  "creator": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "organizer": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "start": {\n    "dateTime": "2025-05-14T03:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "end": {\n    "dateTime": "2025-05-14T04:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "iCalUID": "abc123xyz456@google.com",\n  "sequence": 0,\n  "attendees": [\n    {\n      "email": "attendee@example.com",\n      "responseStatus": "needsAction"\n    }\n  ],\n  "hangoutLink": "https://meet.google.com/abc-defg-hij"\n}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar.events"],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of meetings for the specified date with details",
                    "examples": [
                        '{\n  "kind": "calendar#events",\n  "etag": "\\"p327qnevlquh8q0o\\"",\n  "summary": "user@example.com",\n  "updated": "2025-05-14T09:51:36.236Z",\n  "timeZone": "America/Vancouver",\n  "accessRole": "owner",\n  "items": [\n    {\n      "kind": "calendar#event",\n      "id": "abc123",\n      "status": "confirmed",\n      "summary": "Test Meeting 1",\n      "start": {\n        "dateTime": "2025-05-14T03:00:00-07:00",\n        "timeZone": "UTC"\n      },\n      "end": {\n        "dateTime": "2025-05-14T04:00:00-07:00",\n        "timeZone": "UTC"\n      }\n    },\n    {\n      "kind": "calendar#event",\n      "id": "def456",\n      "status": "confirmed",\n      "summary": "Test Meeting 2",\n      "start": {\n        "dateTime": "2025-05-14T07:00:00-07:00",\n        "timeZone": "UTC"\n      },\n      "end": {\n        "dateTime": "2025-05-14T08:00:00-07:00",\n        "timeZone": "UTC"\n      }\n    }\n  ]\n}'
                    ],
                },
                requiredScopes=[
                    "https://www.googleapis.com/auth/calendar.events.readonly"
                ],
            ),
            types.Tool(
                name="get_meeting_details",
                description="Get details of a meeting by meeting id.",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Detailed information about the specified meeting",
                    "examples": [
                        '{\n  "kind": "calendar#event",\n  "etag": "\\"3494432592472862\\"",\n  "id": "abc123xyz456",\n  "status": "confirmed",\n  "htmlLink": "https://www.google.com/calendar/event?eid=example",\n  "created": "2025-05-14T09:51:27.000Z",\n  "updated": "2025-05-14T09:51:36.236Z",\n  "summary": "Test Meeting Example",\n  "description": "This is a test meeting.",\n  "creator": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "organizer": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "start": {\n    "dateTime": "2025-05-14T03:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "end": {\n    "dateTime": "2025-05-14T04:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "hangoutLink": "https://meet.google.com/abc-defg-hij",\n  "conferenceData": {\n    "conferenceId": "abc-defg-hij"\n  }\n}'
                    ],
                },
                requiredScopes=[
                    "https://www.googleapis.com/auth/calendar.events.readonly"
                ],
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
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Updated meeting details with all changes applied",
                    "examples": [
                        '{\n  "kind": "calendar#event",\n  "etag": "\\"3494432648842942\\"",\n  "id": "abc123xyz456",\n  "status": "confirmed",\n  "htmlLink": "https://www.google.com/calendar/event?eid=example",\n  "created": "2025-05-14T09:51:27.000Z",\n  "updated": "2025-05-14T09:52:04.421Z",\n  "summary": "Updated Test Meeting Example",\n  "description": "This is an updated test meeting.",\n  "creator": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "organizer": {\n    "email": "user@example.com",\n    "self": true\n  },\n  "start": {\n    "dateTime": "2025-05-14T03:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "end": {\n    "dateTime": "2025-05-14T04:00:00-07:00",\n    "timeZone": "UTC"\n  },\n  "hangoutLink": "https://meet.google.com/abc-defg-hij"\n}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar.events"],
            ),
            types.Tool(
                name="delete_meeting",
                description="Delete a meeting by meeting id.",
                inputSchema={
                    "type": "object",
                    "properties": {"meeting_id": {"type": "string"}},
                    "required": ["meeting_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Confirmation of meeting deletion",
                    "examples": ['""'],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar.events"],
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

            if (
                name == "fetch_meetings_by_date"
                and "items" in result
                and isinstance(result["items"], list)
            ):
                return [
                    types.TextContent(type="text", text=json.dumps(item, indent=2))
                    for item in result["items"]
                ]
            else:
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

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
