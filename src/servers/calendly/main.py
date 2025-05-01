import os
import sys
from typing import Optional, Iterable
import json
from datetime import datetime, timedelta
import urllib.parse

# Add both project root and src directory to Python path
# Get the project root directory and add to path
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

from src.utils.calendly.utils import (
    authenticate_and_save_credentials,
    get_credentials,
    CALENDLY_API_URL,
)

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "default",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def make_calendly_request(
    method, endpoint, access_token, params=None, json_data=None
):
    """Make a request to the Calendly API"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    url = f"{CALENDLY_API_URL}/{endpoint}"

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=30.0,
        )

        if response.status_code >= 400:
            logger.error(
                f"Calendly API error: {response.status_code} - {response.text}"
            )
            response.raise_for_status()

        return response.json()


def format_event_type(event_type):
    """Format event type data for display"""
    duration = event_type.get("duration")
    duration_mins = duration // 60 if duration else 0

    # Format availability info
    scheduling_url = event_type.get("scheduling_url", "")

    return {
        "name": event_type.get("name", "Unnamed Event"),
        "description": event_type.get("description", ""),
        "duration_minutes": duration_mins,
        "scheduling_url": scheduling_url,
        "uri": f"calendly://event_type/{event_type.get('uri', '').split('/')[-1]}",
        "active": event_type.get("active", False),
    }


def format_event(event):
    """Format event data for display"""
    start_time = event.get("start_time", "")
    end_time = event.get("end_time", "")

    # Format to readable datetime
    if start_time:
        start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    if end_time:
        end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00")).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    return {
        "name": event.get("name", "Unnamed Event"),
        "status": event.get("status", ""),
        "start_time": start_time,
        "end_time": end_time,
        "location": event.get("location", {}).get("type", "Not specified"),
        "uri": f"calendly://event/{event.get('uri', '').split('/')[-1]}",
        "cancellation_url": event.get("cancellation", {}).get("cancellation_url", ""),
        "rescheduling_url": event.get("rescheduling", {}).get("reschedule_url", ""),
    }


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("calendly-server")

    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Calendly resources (event types and scheduled events)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

        resources = []

        # First get user information
        try:
            user_info = await make_calendly_request("GET", "users/me", access_token)
            user_uri = user_info.get("resource", {}).get("uri", "")

            if not user_uri:
                logger.error("Failed to get user URI")
                return resources

            # Get event types (meeting templates)
            event_types_result = await make_calendly_request(
                "GET", "/event_types", access_token, params={"user": user_uri}
            )

            event_types = event_types_result.get("collection", [])

            # Add event types to resources
            for event_type in event_types:
                event_type_id = event_type.get("uri", "").split("/")[-1]
                resources.append(
                    Resource(
                        uri=f"calendly://event_type/{event_type_id}",
                        mimeType="application/json",
                        name=f"Event Type: {event_type.get('name', 'Unnamed')} ({event_type.get('duration') // 60}min)",
                        description=event_type.get("description", ""),
                    )
                )

            # Get scheduled events
            current_time = datetime.utcnow()
            # Default to showing events from 30 days ago to 30 days in the future
            min_time = (current_time - timedelta(days=30)).isoformat() + "Z"
            max_time = (current_time + timedelta(days=30)).isoformat() + "Z"

            events_result = await make_calendly_request(
                "GET",
                "/scheduled_events",
                access_token,
                params={
                    "user": user_uri,
                    "min_start_time": min_time,
                    "max_start_time": max_time,
                    "status": "active",
                },
            )

            events = events_result.get("collection", [])

            # Add events to resources
            for event in events:
                event_id = event.get("uri", "").split("/")[-1]
                start_time = event.get("start_time", "")
                formatted_time = ""

                if start_time:
                    formatted_time = datetime.fromisoformat(
                        start_time.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M")

                resources.append(
                    Resource(
                        uri=f"calendly://event/{event_id}",
                        mimeType="application/json",
                        name=f"Meeting: {event.get('name', 'Unnamed')} ({formatted_time})",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error fetching Calendly resources: {str(e)}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a Calendly resource by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

        uri_str = str(uri)

        try:
            if uri_str.startswith("calendly://event_type/"):
                # Handle event type resource
                event_type_id = uri_str.replace("calendly://event_type/", "")

                event_type_data = await make_calendly_request(
                    "GET", f"/event_types/{event_type_id}", access_token
                )

                if not event_type_data or "resource" not in event_type_data:
                    raise ValueError(f"Event type not found: {event_type_id}")

                formatted_data = format_event_type(event_type_data.get("resource", {}))
                formatted_content = json.dumps(formatted_data, indent=2)

                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            elif uri_str.startswith("calendly://event/"):
                # Handle event resource
                event_id = uri_str.replace("calendly://event/", "")

                event_data = await make_calendly_request(
                    "GET", f"/scheduled_events/{event_id}", access_token
                )

                if not event_data or "resource" not in event_data:
                    raise ValueError(f"Event not found: {event_id}")

                # Get event invitees
                invitees_data = await make_calendly_request(
                    "GET", f"/scheduled_events/{event_id}/invitees", access_token
                )

                # Combine event data with invitees
                event_resource = event_data.get("resource", {})
                event_resource["invitees"] = invitees_data.get("collection", [])

                formatted_data = format_event(event_resource)
                formatted_content = json.dumps(formatted_data, indent=2)

                return [
                    ReadResourceContents(
                        content=formatted_content, mime_type="application/json"
                    )
                ]

            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading Calendly resource: {str(e)}")
            return [
                ReadResourceContents(content=f"Error: {str(e)}", mime_type="text/plain")
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for Calendly"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="list_event_types",
                description="List all available event types (meeting templates)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "active_only": {
                            "type": "boolean",
                            "description": "Only include active event types",
                        }
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings describing found event types, including name, duration in minutes, active status, scheduling URL, and ID.",
                    "examples": [
                        "Found 1 event types:\n\n- 30 Minute Meeting (30 min)\n  Active: Yes\n  Scheduling URL: <URL>\n  ID: <ID>\n"
                    ],
                },
            ),
            Tool(
                name="get_availability",
                description="Get available time slots for a specific event type",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_type_id": {
                            "type": "string",
                            "description": "ID of the event type",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)",
                        },
                    },
                    "required": ["event_type_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings representing available time slots per date between provided start and end dates.",
                    "examples": [
                        "Available times between <DATE> and <DATE>:\n\n<DATE>:\n  - <TIME>\n  - <TIME>\n\n<DATE>:\n  - <TIME>\n  - <TIME>\n"
                    ],
                },
            ),
            Tool(
                name="list_scheduled_events",
                description="List scheduled events in a given time range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "string",
                            "description": "Filter by status (active, canceled)",
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date (YYYY-MM-DD)",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date (YYYY-MM-DD)",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings describing scheduled events, including name, status, time range, location, and ID.",
                    "examples": [
                        "Found 1 active events:\n\n- 30 Minute Meeting\n  Status: active\n  Time: <START_TIME> to <END_TIME>\n  Location: <LOCATION>\n  ID: <ID>\n"
                    ],
                },
            ),
            Tool(
                name="cancel_event",
                description="Cancel a scheduled event",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "ID of the event to cancel",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for cancellation",
                        },
                    },
                    "required": ["event_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings confirming event cancellation or reporting status.",
                    "examples": ["Successfully canceled event: <EVENT_NAME>"],
                },
            ),
            Tool(
                name="create_scheduling_link",
                description="Create a single-use scheduling link for a specific event type",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "event_type_id": {
                            "type": "string",
                            "description": "ID of the event type",
                        },
                    },
                    "required": ["event_type_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of strings containing the single-use scheduling link.",
                    "examples": ["Scheduling link created:\n\n<URL>"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for Calendly"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)

        if arguments is None:
            arguments = {}

        try:
            # Get user information first (needed for many requests)
            user_info = await make_calendly_request("GET", "/users/me", access_token)
            user_uri = user_info.get("resource", {}).get("uri", "")

            if name == "list_event_types":
                active_only = arguments.get("active_only", False)

                # Get all event types
                event_types_result = await make_calendly_request(
                    "GET", "event_types", access_token, params={"user": user_uri}
                )

                event_types = event_types_result.get("collection", [])

                # Filter by active status if requested
                if active_only:
                    event_types = [et for et in event_types if et.get("active", False)]

                # Format event types
                formatted_event_types = []
                for event_type in event_types:
                    formatted = format_event_type(event_type)
                    formatted_event_types.append(formatted)

                # Create the response text
                if not formatted_event_types:
                    return [TextContent(type="text", text="No event types found.")]

                result_text = f"Found {len(formatted_event_types)} event types:\n\n"

                for et in formatted_event_types:
                    result_text += f"- {et['name']} ({et['duration_minutes']} min)\n"
                    result_text += f"  Active: {'Yes' if et['active'] else 'No'}\n"
                    if et["description"]:
                        result_text += f"  Description: {et['description']}\n"
                    result_text += f"  Scheduling URL: {et['scheduling_url']}\n"
                    result_text += (
                        f"  ID: {et['uri'].replace('calendly://event_type/', '')}\n\n"
                    )

                return [TextContent(type="text", text=result_text)]

            elif name == "get_availability":
                if "event_type_id" not in arguments:
                    raise ValueError("Missing required parameter: event_type_id")

                event_type_id = arguments["event_type_id"]

                # Set date range (default to next 7 days if not specified)
                today = datetime.utcnow()
                # Make start time at least 1 hour in the future to ensure it's in the future
                start_time = today + timedelta(hours=1)
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")

                if start_date:
                    # If specific date provided, use noon on that day to avoid timezone issues
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").replace(
                        hour=12, minute=0, second=0
                    )
                    # Ensure start time is in the future
                    if start_date_obj <= today:
                        start_date_obj = today + timedelta(hours=1)
                else:
                    # Default to start time with formatted date
                    start_date_obj = start_time
                    start_date = start_date_obj.date().isoformat()

                # Format start time for API
                formatted_start_time = start_date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Calculate end time - EXACTLY 7 days (minus 1 second) from start time
                # This ensures we stay within the API's 7-day limit
                end_date_obj = start_date_obj + timedelta(
                    days=6, hours=23, minutes=59, seconds=59
                )
                formatted_end_time = end_date_obj.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Get availability for the event type
                availability_result = await make_calendly_request(
                    "GET",
                    "event_type_available_times",
                    access_token,
                    params={
                        "event_type": f"{CALENDLY_API_URL}/event_types/{event_type_id}",
                        "start_time": formatted_start_time,
                        "end_time": formatted_end_time,
                    },
                )

                available_times = availability_result.get("collection", [])

                # Format the results
                if not available_times:
                    return [
                        TextContent(
                            type="text",
                            text=f"No available times found between {start_date} and {end_date}.",
                        )
                    ]

                # Group times by date
                dates_dict = {}
                for time_slot in available_times:
                    start_time = time_slot.get("start_time", "")
                    if not start_time:
                        continue

                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M")

                    if date_str not in dates_dict:
                        dates_dict[date_str] = []

                    dates_dict[date_str].append(time_str)

                # Create formatted response
                result_text = (
                    f"Available times between {start_date} and {end_date}:\n\n"
                )

                for date, times in sorted(dates_dict.items()):
                    result_text += f"{date}:\n"
                    for time in times:
                        result_text += f"  - {time}\n"
                    result_text += "\n"

                return [TextContent(type="text", text=result_text)]

            elif name == "list_scheduled_events":
                # Set date range (default to +/- 30 days if not specified)
                current_time = datetime.utcnow()
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")

                if start_date:
                    min_time = f"{start_date}T00:00:00Z"
                else:
                    min_time = (current_time - timedelta(days=30)).isoformat() + "Z"

                if end_date:
                    max_time = f"{end_date}T23:59:59Z"
                else:
                    max_time = (current_time + timedelta(days=30)).isoformat() + "Z"

                # Set status filter
                status = arguments.get("status", "active")

                # Get scheduled events
                events_result = await make_calendly_request(
                    "GET",
                    "scheduled_events",
                    access_token,
                    params={
                        "user": user_uri,
                        "min_start_time": min_time,
                        "max_start_time": max_time,
                        "status": status,
                    },
                )

                events = events_result.get("collection", [])

                # Format the results
                if not events:
                    return [
                        TextContent(
                            type="text",
                            text=f"No active events found in the specified date range.",
                        )
                    ]

                # Format events
                formatted_events = []
                for event in events:
                    formatted_events.append(format_event(event))

                # Create the response text
                result_text = f"Found {len(formatted_events)} {status} events:\n\n"

                for event in formatted_events:
                    result_text += f"- {event['name']}\n"
                    result_text += f"  Status: {event['status']}\n"
                    result_text += (
                        f"  Time: {event['start_time']} to {event['end_time']}\n"
                    )
                    result_text += f"  Location: {event['location']}\n"
                    result_text += (
                        f"  ID: {event['uri'].replace('calendly://event/', '')}\n\n"
                    )

                return [TextContent(type="text", text=result_text)]

            elif name == "cancel_event":
                if "event_id" not in arguments:
                    raise ValueError("Missing required parameter: event_id")

                event_id = arguments["event_id"]
                reason = arguments.get("reason", "Canceled via API")

                # Cancel the event
                cancel_result = await make_calendly_request(
                    "POST",
                    f"scheduled_events/{event_id}/cancellation",
                    access_token,
                    json_data={"reason": reason},
                )

                # Get updated event details to confirm cancellation
                event_data = await make_calendly_request(
                    "GET", f"scheduled_events/{event_id}", access_token
                )

                event_status = event_data.get("resource", {}).get("status")
                event_name = event_data.get("resource", {}).get("name", "Event")

                if event_status == "canceled":
                    return [
                        TextContent(
                            type="text",
                            text=f"Successfully canceled event: {event_name}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Event cancellation status: {event_status}",
                        )
                    ]

            elif name == "create_scheduling_link":
                if "event_type_id" not in arguments:
                    raise ValueError("Missing required parameter: event_type_id")

                event_type_id = arguments["event_type_id"]

                # Create a single-use scheduling link via the API
                # First get the event type URI
                event_type_data = await make_calendly_request(
                    "GET", f"event_types/{event_type_id}", access_token
                )

                event_type_uri = event_type_data.get("resource", {}).get("uri")

                if not event_type_uri:
                    return [
                        TextContent(
                            type="text",
                            text="Could not generate scheduling link: event type not found.",
                        )
                    ]

                # Request body for single-use scheduling link
                request_data = {
                    "max_event_count": 1,
                    "owner": event_type_uri,
                    "owner_type": "EventType",
                }

                # Create the scheduling link
                try:
                    scheduling_link_result = await make_calendly_request(
                        "POST", "scheduling_links", access_token, json_data=request_data
                    )

                    booking_url = scheduling_link_result.get("resource", {}).get(
                        "booking_url"
                    )

                    if not booking_url:
                        return [
                            TextContent(
                                type="text",
                                text="Error creating scheduling link: Invalid response from API.",
                            )
                        ]

                    return [
                        TextContent(
                            type="text",
                            text=f"Scheduling link created:\n\n{booking_url}",
                        )
                    ]

                except Exception as e:
                    return [
                        TextContent(
                            type="text",
                            text=f"Error creating scheduling link: {str(e)}",
                        )
                    ]

            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error executing Calendly tool: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="calendly-server",
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
        authenticate_and_save_credentials(user_id, SERVICE_NAME, SCOPES)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
