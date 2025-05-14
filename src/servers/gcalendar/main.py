import os
import sys
from typing import Optional, Iterable
from datetime import datetime, timedelta
import json

# Add both project root and src directory to Python path
# Get the project root directory and add to path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path

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

from src.utils.google.util import authenticate_and_save_credentials, get_credentials

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SERVICE_NAME = Path(__file__).parent.name
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def create_calendar_service(user_id, api_key=None):
    """Create a new Calendar service instance for this request"""
    credentials = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
    return build("calendar", "v3", credentials=credentials)


def format_event(event):
    """Format a calendar event for display"""
    start = event.get("start", {}).get(
        "dateTime", event.get("start", {}).get("date", "N/A")
    )
    end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", "N/A"))

    # Format start time
    if "T" in start:  # This is a datetime
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        start_formatted = start_dt.strftime("%Y-%m-%d %H:%M")
    else:  # This is a date
        start_formatted = start

    # Format end time
    if "T" in end:  # This is a datetime
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        end_formatted = end_dt.strftime("%Y-%m-%d %H:%M")
    else:  # This is a date
        end_formatted = end

    return {
        "summary": event.get("summary", "No Title"),
        "start": start_formatted,
        "end": end_formatted,
        "location": event.get("location", "N/A"),
        "id": event.get("id", ""),
        "description": event.get("description", ""),
        "attendees": [a.get("email") for a in event.get("attendees", [])],
    }


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("gcalendar-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List calendars"""
        logger.info(
            f"Listing calendars for user: {server.user_id} with cursor: {cursor}"
        )

        calendar_service = await create_calendar_service(
            server.user_id, api_key=server.api_key
        )

        calendars = calendar_service.calendarList().list().execute()
        calendar_items = calendars.get("items", [])

        resources = []
        for calendar in calendar_items:
            resource = Resource(
                uri=f"gcalendar://calendar/{calendar['id']}",
                mimeType="application/json",
                name=calendar["summary"],
                description=calendar.get("description", ""),
            )
            resources.append(resource)

        return resources

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read calendar or events by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        calendar_service = await create_calendar_service(
            server.user_id, api_key=server.api_key
        )

        # Parse the URI to extract resource_type and resource_id
        uri_parts = str(uri).split("://")
        if len(uri_parts) != 2:
            return [
                ReadResourceContents(
                    content="Invalid URI format", mime_type="text/plain"
                )
            ]

        path_parts = uri_parts[1].split("/")
        if len(path_parts) < 2:
            return [
                ReadResourceContents(content="Invalid URI path", mime_type="text/plain")
            ]

        resource_type = path_parts[0]
        resource_id = path_parts[1]

        # Handle calendar resources
        try:
            if resource_type == "calendar":
                events_result = (
                    calendar_service.events()
                    .list(
                        calendarId=resource_id,
                        timeMin=datetime.utcnow().isoformat() + "Z",
                        maxResults=10,
                        singleEvents=True,
                        orderBy="startTime",
                    )
                    .execute()
                )

                events = events_result.get("items", [])
                formatted_events = [format_event(event) for event in events]

                calendar = (
                    calendar_service.calendars().get(calendarId=resource_id).execute()
                )

                content = f"Calendar: {calendar.get('summary', 'Unknown')}\n\n"
                content += "Upcoming events:\n\n"

                for i, event in enumerate(formatted_events, 1):
                    content += f"{i}. {event['summary']}\n"
                    content += f"   When: {event['start']} to {event['end']}\n"
                    if event["location"] != "N/A":
                        content += f"   Where: {event['location']}\n"
                    if event["attendees"]:
                        content += f"   Attendees: {', '.join(event['attendees'])}\n"
                    content += "\n"

                return [ReadResourceContents(content=content, mime_type="text/plain")]
            else:
                return [
                    ReadResourceContents(
                        content=f"Unsupported resource type: {resource_type}",
                        mime_type="text/plain",
                    )
                ]
        except HttpError as error:
            logger.error(f"Error reading calendar: {error}")
            return [
                ReadResourceContents(
                    content=f"Error reading calendar: {error}", mime_type="text/plain"
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="list_events",
                description="List events from Google Calendar for a specified time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start time of the time range (format: YYYY-MM-DD HH:MM or YYYY-MM-DD)",
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End time of the time range (format: YYYY-MM-DD HH:MM or YYYY-MM-DD)",
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look ahead (used if time_max is not provided)",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of events to return (default: 10)",
                        },
                        "order_by": {
                            "type": "string",
                            "enum": ["startTime", "updated"],
                            "description": "Order of events returned (default: startTime)",
                        },
                        "show_deleted": {
                            "type": "boolean",
                            "description": "Whether to include deleted events (default: false)",
                        },
                        "single_events": {
                            "type": "boolean",
                            "description": "Whether to expand recurring events (default: true)",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone for the response (default: UTC)",
                        },
                        "q": {
                            "type": "string",
                            "description": "Free text search terms to find events that match",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing an event listing with count, days, and events array with event details",
                    "examples": [
                        '{"count": 1, "days": 7, "events": [{"summary": "sdfsd", "start": "2025-05-15 15:30", "end": "2025-05-15 16:30", "location": "N/A", "id": "063f3joira2ujv8tatfdv033r0", "description": "", "attendees": []}]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
            Tool(
                name="create_event",
                description="Create a new event in Google Calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "summary": {"type": "string", "description": "Event title"},
                        "start_datetime": {
                            "type": "string",
                            "description": "Start date/time (format: YYYY-MM-DD HH:MM or YYYY-MM-DD)",
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "End date/time (format: YYYY-MM-DD HH:MM or YYYY-MM-DD)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description (optional)",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location (optional)",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee emails (optional)",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone for the event (default: UTC)",
                        },
                        "recurrence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "RRULE, EXRULE, RDATE and EXDATE rules for recurrence (e.g., ['RRULE:FREQ=DAILY;COUNT=2'])",
                        },
                        "reminders": {
                            "type": "object",
                            "properties": {
                                "use_default": {
                                    "type": "boolean",
                                    "description": "Whether to use the default reminders",
                                },
                                "overrides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {
                                                "type": "string",
                                                "enum": ["email", "popup"],
                                                "description": "Method of reminder",
                                            },
                                            "minutes": {
                                                "type": "integer",
                                                "description": "Minutes before event to trigger reminder",
                                            },
                                        },
                                    },
                                    "description": "Custom reminders to override the default",
                                },
                            },
                            "description": "Reminders settings for the event",
                        },
                        "transparency": {
                            "type": "string",
                            "enum": ["opaque", "transparent"],
                            "description": "Whether the event blocks time on the calendar (opaque) or not (transparent)",
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["default", "public", "private", "confidential"],
                            "description": "Visibility of the event (default: default)",
                        },
                        "color_id": {
                            "type": "string",
                            "description": "Color ID for the event (1-11)",
                        },
                        "send_updates": {
                            "type": "string",
                            "enum": ["all", "externalOnly", "none"],
                            "description": "Specifies who should receive confirmations (default: none)",
                        },
                    },
                    "required": ["summary", "start_datetime", "end_datetime"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the created event details with id, title, start/end times, and other fields",
                    "examples": [
                        '{"id": "event123", "title": "Test Meeting", "start": "2025-05-15 10:00", "end": "2025-05-15 11:00", "location": null, "description": null, "attendees": null, "htmlLink": "https://www.google.com/calendar/event?eid=abc123"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
            Tool(
                name="update_event",
                description="Update an existing event in Google Calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to update",
                        },
                        "summary": {
                            "type": "string",
                            "description": "New event title (optional)",
                        },
                        "start_datetime": {
                            "type": "string",
                            "description": "New start date/time (format: YYYY-MM-DD HH:MM or YYYY-MM-DD) (optional)",
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "New end date/time (format: YYYY-MM-DD HH:MM or YYYY-MM-DD) (optional)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New event description (optional)",
                        },
                        "location": {
                            "type": "string",
                            "description": "New event location (optional)",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "New list of attendee emails (optional)",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone for the event (default: UTC)",
                        },
                        "recurrence": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "RRULE, EXRULE, RDATE and EXDATE rules for recurrence (e.g., ['RRULE:FREQ=DAILY;COUNT=2'])",
                        },
                        "reminders": {
                            "type": "object",
                            "properties": {
                                "use_default": {
                                    "type": "boolean",
                                    "description": "Whether to use the default reminders",
                                },
                                "overrides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "method": {
                                                "type": "string",
                                                "enum": ["email", "popup"],
                                                "description": "Method of reminder",
                                            },
                                            "minutes": {
                                                "type": "integer",
                                                "description": "Minutes before event to trigger reminder",
                                            },
                                        },
                                    },
                                    "description": "Custom reminders to override the default",
                                },
                            },
                            "description": "Reminders settings for the event",
                        },
                        "transparency": {
                            "type": "string",
                            "enum": ["opaque", "transparent"],
                            "description": "Whether the event blocks time on the calendar (opaque) or not (transparent)",
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["default", "public", "private", "confidential"],
                            "description": "Visibility of the event",
                        },
                        "color_id": {
                            "type": "string",
                            "description": "Color ID for the event (1-11)",
                        },
                        "send_updates": {
                            "type": "string",
                            "enum": ["all", "externalOnly", "none"],
                            "description": "Specifies who should receive confirmations (default: none)",
                        },
                    },
                    "required": ["event_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the updated event details with id, title, start/end times, and other fields",
                    "examples": [
                        '{"id": "event123", "title": "Updated Test Meeting", "start": "2025-05-15 03:00", "end": "2025-05-15 04:00", "location": null, "description": "This is a test description", "attendees": null, "htmlLink": "https://www.google.com/calendar/event?eid=abc123"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
            Tool(
                name="delete_event",
                description="Delete an event from Google Calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to delete",
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "description": "Whether to send notifications to attendees (default: false)",
                        },
                        "send_updates": {
                            "type": "string",
                            "enum": ["all", "externalOnly", "none"],
                            "description": "Specifies who should receive notifications (default: none)",
                        },
                    },
                    "required": ["event_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the deletion result with success status, event ID, and event title",
                    "examples": [
                        '{"success": true, "message": "Event deleted successfully", "event_id": "event123", "event_title": "Updated Test Meeting", "calendar_id": "primary"}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
            Tool(
                name="update_attendee_status",
                description="Update an attendee's response status for an event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to update",
                        },
                        "attendee_email": {
                            "type": "string",
                            "description": "Email address of the attendee to update",
                        },
                        "response_status": {
                            "type": "string",
                            "enum": [
                                "accepted",
                                "declined",
                                "tentative",
                                "needsAction",
                            ],
                            "description": "New response status for the attendee",
                        },
                        "send_notifications": {
                            "type": "boolean",
                            "description": "Whether to send notifications to attendees (default: false)",
                        },
                        "send_updates": {
                            "type": "string",
                            "enum": ["all", "externalOnly", "none"],
                            "description": "Specifies who should receive notifications (default: none)",
                        },
                        "comment": {
                            "type": "string",
                            "description": "A comment to include with the response status",
                        },
                    },
                    "required": ["event_id", "attendee_email", "response_status"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the full Google Calendar event data with updated attendee status",
                    "examples": [
                        '{"kind": "calendar#event", "etag": "\\"3494522604616062\\"", "id": "event123", "status": "confirmed", "htmlLink": "https://www.google.com/calendar/event?eid=abc123", "created": "2025-05-14T22:21:21.000Z", "updated": "2025-05-14T22:21:42.308Z", "summary": "Updated Test Meeting", "description": "This is a test description", "creator": {"email": "user@example.com", "self": true}, "organizer": {"email": "user@example.com", "self": true}, "start": {"dateTime": "2025-05-15T03:00:00-07:00", "timeZone": "UTC"}, "end": {"dateTime": "2025-05-15T04:00:00-07:00", "timeZone": "UTC"}, "attendees": [{"email": "test@example.com", "responseStatus": "accepted"}]}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
            Tool(
                name="check_free_slots",
                description="Check for available time slots in a calendar",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "calendar_id": {
                            "type": "string",
                            "description": "Calendar ID (optional - defaults to primary)",
                        },
                        "start_datetime": {
                            "type": "string",
                            "description": "Start of time range (format: YYYY-MM-DD HH:MM)",
                        },
                        "end_datetime": {
                            "type": "string",
                            "description": "End of time range (format: YYYY-MM-DD HH:MM)",
                        },
                        "duration_minutes": {
                            "type": "integer",
                            "description": "Minimum duration of free slots in minutes (default: 30)",
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the free slots search (default: UTC)",
                        },
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {
                                        "type": "string",
                                        "description": "Calendar ID to check",
                                    }
                                },
                                "required": ["id"],
                            },
                            "description": "List of calendars to check for availability",
                        },
                        "group_exp_expand": {
                            "type": "boolean",
                            "description": "Whether to expand group members (default: false)",
                        },
                    },
                    "required": ["start_datetime", "end_datetime"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the Google Calendar freebusy response with busy periods for the specified time range",
                    "examples": [
                        '{"kind": "calendar#freeBusy", "timeMin": "2025-05-15T09:00:00.000Z", "timeMax": "2025-05-15T17:00:00.000Z", "calendars": {"primary": {"busy": [{"start": "2025-05-15T10:00:00Z", "end": "2025-05-15T11:00:00Z"}]}}}'
                    ],
                },
                requiredScopes=["https://www.googleapis.com/auth/calendar"],
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        if arguments is None:
            arguments = {}

        calendar_service = await create_calendar_service(
            server.user_id, api_key=server.api_key
        )

        try:
            if name == "list_events":
                calendar_id = arguments.get("calendar_id", "primary")
                days = int(arguments.get("days", 7))
                max_results = int(arguments.get("max_results", 10))
                order_by = arguments.get("order_by", "startTime")
                show_deleted = arguments.get("show_deleted", False)
                single_events = arguments.get("single_events", True)
                time_zone = arguments.get("time_zone", "UTC")
                q = arguments.get("q", "")

                # Process time_min and time_max parameters
                if "time_min" in arguments:
                    time_min_str = arguments["time_min"]
                    if " " in time_min_str:  # Has time component
                        time_min_dt = datetime.strptime(time_min_str, "%Y-%m-%d %H:%M")
                    else:  # Date only
                        time_min_dt = datetime.strptime(time_min_str, "%Y-%m-%d")
                    time_min = time_min_dt.isoformat() + "Z"
                else:
                    time_min = datetime.utcnow().isoformat() + "Z"

                if "time_max" in arguments:
                    time_max_str = arguments["time_max"]
                    if " " in time_max_str:  # Has time component
                        time_max_dt = datetime.strptime(time_max_str, "%Y-%m-%d %H:%M")
                    else:  # Date only
                        time_max_dt = datetime.strptime(time_max_str, "%Y-%m-%d")
                        # If only date is provided, set time to end of day
                        time_max_dt = time_max_dt.replace(hour=23, minute=59, second=59)
                    time_max = time_max_dt.isoformat() + "Z"
                else:
                    # Use days parameter for the default time_max
                    time_max = (
                        datetime.utcnow() + timedelta(days=days)
                    ).isoformat() + "Z"

                events_result = (
                    calendar_service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=max_results,
                        singleEvents=single_events,
                        orderBy=order_by,
                        showDeleted=show_deleted,
                        timeZone=time_zone,
                        q=q,
                    )
                    .execute()
                )

                events = events_result.get("items", [])
                formatted_events = [format_event(event) for event in events]

                # Create a proper JSON response
                response_data = {
                    "count": len(formatted_events),
                    "days": days,
                    "events": formatted_events,
                }

                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "create_event":
                calendar_id = arguments.get("calendar_id", "primary")
                summary = arguments["summary"]
                description = arguments.get("description", "")
                location = arguments.get("location", "")
                attendees = arguments.get("attendees", [])
                time_zone = arguments.get("time_zone", "UTC")
                recurrence = arguments.get("recurrence", [])
                reminders = arguments.get("reminders", {})
                transparency = arguments.get("transparency", "opaque")
                visibility = arguments.get("visibility", "default")
                color_id = arguments.get("color_id", "")
                send_updates = arguments.get("send_updates", "none")

                # Process start and end times
                start_datetime = arguments["start_datetime"]
                end_datetime = arguments["end_datetime"]

                # Create event dictionary
                event = {
                    "summary": summary,
                    "description": description,
                    "location": location,
                    "timeZone": time_zone,
                }

                # Handle start time
                if " " in start_datetime:  # Has time component
                    dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
                    event["start"] = {"dateTime": dt.isoformat(), "timeZone": time_zone}
                else:
                    event["start"] = {"date": start_datetime}

                # Handle end time
                if " " in end_datetime:  # Has time component
                    dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
                    event["end"] = {"dateTime": dt.isoformat(), "timeZone": time_zone}
                else:
                    event["end"] = {"date": end_datetime}

                # Add attendees if provided
                if attendees:
                    event["attendees"] = [{"email": email} for email in attendees]

                # Add recurrence if provided
                if recurrence:
                    event["recurrence"] = recurrence

                # Add reminders if provided
                if reminders:
                    event["reminders"] = reminders

                # Add transparency if provided
                if transparency:
                    event["transparency"] = transparency

                # Add visibility if provided
                if visibility:
                    event["visibility"] = visibility

                # Add color ID if provided
                if color_id:
                    event["colorId"] = color_id

                created_event = (
                    calendar_service.events()
                    .insert(
                        calendarId=calendar_id, body=event, sendUpdates=send_updates
                    )
                    .execute()
                )

                # Create a proper JSON response
                response_data = {
                    "id": created_event["id"],
                    "title": summary,
                    "start": start_datetime,
                    "end": end_datetime,
                    "location": location if location else None,
                    "description": description if description else None,
                    "attendees": attendees if attendees else None,
                    "htmlLink": created_event.get("htmlLink", None),
                }

                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "update_event":
                calendar_id = arguments.get("calendar_id", "primary")
                event_id = arguments["event_id"]
                time_zone = arguments.get("time_zone", "UTC")
                send_updates = arguments.get("send_updates", "none")

                # First get the existing event
                event = (
                    calendar_service.events()
                    .get(calendarId=calendar_id, eventId=event_id)
                    .execute()
                )

                # Update fields that were provided
                if "summary" in arguments:
                    event["summary"] = arguments["summary"]

                if "description" in arguments:
                    event["description"] = arguments["description"]

                if "location" in arguments:
                    event["location"] = arguments["location"]

                # Process start time if provided
                if "start_datetime" in arguments:
                    start_datetime = arguments["start_datetime"]
                    if " " in start_datetime:  # Has time component
                        dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
                        event["start"] = {
                            "dateTime": dt.isoformat(),
                            "timeZone": time_zone,
                        }
                    else:
                        event["start"] = {"date": start_datetime}

                # Process end time if provided
                if "end_datetime" in arguments:
                    end_datetime = arguments["end_datetime"]
                    if " " in end_datetime:  # Has time component
                        dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
                        event["end"] = {
                            "dateTime": dt.isoformat(),
                            "timeZone": time_zone,
                        }
                    else:
                        event["end"] = {"date": end_datetime}

                # Update attendees if provided
                if "attendees" in arguments:
                    event["attendees"] = [
                        {"email": email} for email in arguments["attendees"]
                    ]

                # Add or update recurrence if provided
                if "recurrence" in arguments:
                    event["recurrence"] = arguments["recurrence"]

                # Add or update reminders if provided
                if "reminders" in arguments:
                    event["reminders"] = arguments["reminders"]

                # Add or update transparency if provided
                if "transparency" in arguments:
                    event["transparency"] = arguments["transparency"]

                # Add or update visibility if provided
                if "visibility" in arguments:
                    event["visibility"] = arguments["visibility"]

                # Add or update color ID if provided
                if "color_id" in arguments:
                    event["colorId"] = arguments["color_id"]

                # Update the event
                updated_event = (
                    calendar_service.events()
                    .update(
                        calendarId=calendar_id,
                        eventId=event_id,
                        body=event,
                        sendUpdates=send_updates,
                    )
                    .execute()
                )

                formatted_event = format_event(updated_event)

                # Create a proper JSON response
                response_data = {
                    "id": updated_event["id"],
                    "title": formatted_event["summary"],
                    "start": formatted_event["start"],
                    "end": formatted_event["end"],
                    "location": (
                        formatted_event["location"]
                        if formatted_event["location"] != "N/A"
                        else None
                    ),
                    "description": (
                        formatted_event["description"]
                        if formatted_event["description"]
                        else None
                    ),
                    "attendees": (
                        formatted_event["attendees"]
                        if formatted_event["attendees"]
                        else None
                    ),
                    "htmlLink": updated_event.get("htmlLink", None),
                }

                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "delete_event":
                calendar_id = arguments.get("calendar_id", "primary")
                event_id = arguments["event_id"]

                # Optional parameters
                send_notifications = arguments.get("send_notifications", False)
                send_updates = arguments.get("send_updates", "none")

                # Get event details before deletion for response
                try:
                    event_details = (
                        calendar_service.events()
                        .get(calendarId=calendar_id, eventId=event_id)
                        .execute()
                    )

                    event_title = event_details.get("summary", "Unknown Event")
                except HttpError:
                    event_title = "Unknown Event"

                # Delete the event
                result = (
                    calendar_service.events()
                    .delete(
                        calendarId=calendar_id,
                        eventId=event_id,
                        sendNotifications=send_notifications,
                        sendUpdates=send_updates,
                    )
                    .execute()
                )

                # Create a proper JSON response (Google API often returns empty for delete)
                response_data = {
                    "success": True,
                    "message": "Event deleted successfully",
                    "event_id": event_id,
                    "event_title": event_title,
                    "calendar_id": calendar_id,
                }

                return [TextContent(type="text", text=json.dumps(response_data))]

            elif name == "update_attendee_status":
                calendar_id = arguments.get("calendar_id", "primary")
                event_id = arguments["event_id"]
                attendee_email = arguments["attendee_email"]
                response_status = arguments["response_status"]

                # Optional parameters
                send_notifications = arguments.get("send_notifications", False)
                send_updates = arguments.get("send_updates", "none")
                comment = arguments.get("comment", "")

                # First get the existing event
                event = (
                    calendar_service.events()
                    .get(calendarId=calendar_id, eventId=event_id)
                    .execute()
                )

                # Find and update the attendee
                attendees = event.get("attendees", [])
                found = False

                for attendee in attendees:
                    if attendee.get("email") == attendee_email:
                        attendee["responseStatus"] = response_status
                        # Add comment if provided
                        if comment:
                            attendee["comment"] = comment
                        found = True
                        break

                if not found:
                    # If attendee not found, add them
                    if "attendees" not in event:
                        event["attendees"] = []
                    attendee_data = {
                        "email": attendee_email,
                        "responseStatus": response_status,
                    }
                    if comment:
                        attendee_data["comment"] = comment
                    event["attendees"].append(attendee_data)

                # Update the event
                updated_event = (
                    calendar_service.events()
                    .update(
                        calendarId=calendar_id,
                        eventId=event_id,
                        body=event,
                        sendNotifications=send_notifications,
                        sendUpdates=send_updates,
                    )
                    .execute()
                )

                # Return properly formatted JSON response
                return [TextContent(type="text", text=json.dumps(updated_event))]

            elif name == "check_free_slots":
                calendar_id = arguments.get("calendar_id", "primary")
                duration_minutes = int(arguments.get("duration_minutes", 30))
                timezone = arguments.get("timezone", "UTC")
                group_exp_expand = arguments.get("group_exp_expand", False)

                # Process start and end times
                start_datetime = arguments["start_datetime"]
                end_datetime = arguments["end_datetime"]

                # Parse datetime strings
                if " " in start_datetime:
                    start_dt = datetime.strptime(start_datetime, "%Y-%m-%d %H:%M")
                else:
                    start_dt = datetime.strptime(start_datetime, "%Y-%m-%d")

                if " " in end_datetime:
                    end_dt = datetime.strptime(end_datetime, "%Y-%m-%d %H:%M")
                else:
                    end_dt = datetime.strptime(end_datetime, "%Y-%m-%d")
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)

                # Create request body
                body = {
                    "timeMin": start_dt.isoformat() + "Z",
                    "timeMax": end_dt.isoformat() + "Z",
                    "timeZone": timezone,
                    "groupExpansionMax": 100 if group_exp_expand else 1,
                }

                # Use provided items if available, otherwise use the calendar_id
                if "items" in arguments and arguments["items"]:
                    body["items"] = arguments["items"]
                else:
                    body["items"] = [{"id": calendar_id}]

                # Make freebusy query
                freebusy_response = (
                    calendar_service.freebusy().query(body=body).execute()
                )

                # Return properly formatted JSON response
                return [TextContent(type="text", text=json.dumps(freebusy_response))]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except HttpError as error:
            error_message = f"Error accessing Google Calendar: {error}"
            logger.error(error_message)
            error_response = {"error": True, "message": error_message}
            return [TextContent(type="text", text=json.dumps(error_response))]
        except Exception as e:
            error_message = f"Error executing tool {name}: {str(e)}"
            logger.error(error_message)
            error_response = {"error": True, "message": error_message}
            return [TextContent(type="text", text=json.dumps(error_response))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="gcalendar-server",
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
