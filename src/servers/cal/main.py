import os
import sys
import httpx
import logging
import json
from pathlib import Path

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import Resource, TextContent, Tool, ImageContent, EmbeddedResource
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
CAL_API_BASE_URL = "https://api.cal.com/v2"
DEFAULT_CAL_API_VERSION = "2024-08-13"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def authenticate_and_save_cal_key(user_id):
    logger.info(f"Starting Cal.com authentication for user {user_id}...")

    auth_client = create_auth_client()
    api_key = input("Please enter your Cal.com API key: ").strip()

    if not api_key:
        raise ValueError("API key cannot be empty")

    auth_client.save_user_credentials("cal", user_id, {"api_key": api_key})
    logger.info(
        f"Cal.com API key saved for user {user_id}. You can now run the server."
    )
    return api_key


async def get_cal_credentials(user_id, api_key=None):
    auth_client = create_auth_client(api_key=api_key)
    credentials_data = auth_client.get_user_credentials("cal", user_id)

    def handle_missing_credentials():
        error_str = f"Cal.com API key not found for user {user_id}."
        if os.environ.get("ENVIRONMENT", "local") == "local":
            error_str += " Please run authentication first."
        logging.error(error_str)
        raise ValueError(error_str)

    if not credentials_data:
        handle_missing_credentials()

    api_key = (
        credentials_data.get("api_key")
        if not isinstance(credentials_data, str)
        else credentials_data
    )
    if not api_key:
        handle_missing_credentials()

    return api_key


async def make_cal_request(
    method, endpoint, data=None, params=None, api_key=None, api_version=None
):
    if not api_key:
        raise ValueError("Cal.com API key is required")

    url = f"{CAL_API_BASE_URL}/{endpoint}"
    cal_api_version = api_version or DEFAULT_CAL_API_VERSION
    headers = {
        "Authorization": f"Bearer {api_key}",
        "cal-api-version": cal_api_version,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(
                    url, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "post":
                response = await client.post(
                    url, json=data, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "patch":
                response = await client.patch(
                    url, json=data, headers=headers, params=params, timeout=30.0
                )
            elif method.lower() == "delete":
                response = await client.delete(
                    url, headers=headers, params=params, timeout=30.0
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            response_json = response.json()
            response_json["_status_code"] = response.status_code
            return response_json
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling {endpoint}: {e.response.status_code}")
        try:
            error_details = e.response.json()
            return {"error": error_details, "_status_code": e.response.status_code}
        except:
            pass
        raise ValueError(f"Cal.com API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Error making request to Cal.com API: {str(e)}")
        raise ValueError(f"Error communicating with Cal.com API: {str(e)}")


def create_server(user_id, api_key=None):
    server = Server(f"{SERVICE_NAME}-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(cursor=None) -> list[Resource]:
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_me",
                description="Get your Cal.com user profile information",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the Cal.com user profile information",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "email": "example@example.com",\n    "timeFormat": 12,\n    "defaultScheduleId": 12345,\n    "weekStart": "Sunday",\n    "timeZone": "America/New_York",\n    "username": "example-user",\n    "organizationId": 12345\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="get_event_types",
                description="Get all event types from Cal.com",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "username": {
                            "type": "string",
                            "description": "The username of the user to get event types for. If only username provided will get all event types.",
                        },
                        "eventSlug": {
                            "type": "string",
                            "description": "Slug of event type to return. If eventSlug is provided then username must be provided too.",
                        },
                        "usernames": {
                            "type": "string",
                            "description": "Get dynamic event type for multiple usernames separated by comma. e.g usernames=alice,bob",
                        },
                        "orgSlug": {
                            "type": "string",
                            "description": "Slug of the user's organization if they are in one. orgId is not required if using this parameter.",
                        },
                        "orgId": {
                            "type": "number",
                            "description": "ID of the organization. orgSlug is not needed when using this parameter.",
                        },
                    },
                    "required": ["username"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing list of event types available for the specified user or organization",
                    "examples": [
                        '{\n  "status": "success",\n  "data": [\n    {\n      "id": 123456,\n      "slug": "meeting-30min",\n      "title": "30-minute Meeting",\n      "length": 30,\n      "description": "Short meeting to discuss projects"\n    }\n  ],\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="get_booking",
                description="Get a booking from Cal.com by its unique ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bookingUid": {
                            "type": "string",
                            "description": "The unique ID of the booking to fetch. Can be uid of a normal booking, uid of a recurring booking recurrence, or uid of a recurring booking which will return an array of all recurrences.",
                        }
                    },
                    "required": ["bookingUid"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing detailed information about a specific booking",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "30-minute Meeting between User and Attendee",\n    "status": "accepted",\n    "start": "2023-05-01T14:30:00.000Z",\n    "end": "2023-05-01T15:00:00.000Z",\n    "eventTypeId": 12345,\n    "attendees": [\n      {\n        "name": "John Doe",\n        "email": "attendee@example.com",\n        "timeZone": "America/Chicago"\n      }\n    ]\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="reschedule_booking",
                description="Reschedule an existing booking to a new time",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bookingUid": {
                            "type": "string",
                            "description": "The unique ID of the booking to reschedule.",
                        },
                        "start": {
                            "type": "string",
                            "description": "Start time in ISO 8601 format for the new booking (e.g., '2024-08-13T10:00:00Z')",
                        },
                        "rescheduledBy": {
                            "type": "string",
                            "description": "Email of the person who is rescheduling the booking (optional)",
                        },
                        "reschedulingReason": {
                            "type": "string",
                            "description": "Reason for rescheduling the booking (optional)",
                        },
                    },
                    "required": ["bookingUid", "start"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the result of the booking reschedule operation",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "Meeting Title",\n    "status": "accepted",\n    "start": "2023-05-01T15:30:00.000Z",\n    "end": "2023-05-01T16:00:00.000Z",\n    "reschedulingReason": "Testing API reschedule"\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="cancel_booking",
                description="Cancel an existing booking",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bookingUid": {
                            "type": "string",
                            "description": "The unique ID of the booking to cancel.",
                        },
                        "cancellationReason": {
                            "type": "string",
                            "description": "Reason for cancelling the booking (optional)",
                        },
                        "cancelSubsequentBookings": {
                            "type": "boolean",
                            "description": "For recurring bookings, whether to cancel subsequent bookings too (optional)",
                        },
                    },
                    "required": ["bookingUid"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the result of the booking cancellation operation",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "Meeting Title",\n    "status": "cancelled",\n    "cancellationReason": "Testing API cancellation"\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="confirm_booking",
                description="Confirm a pending booking",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bookingUid": {
                            "type": "string",
                            "description": "The unique ID of the booking to confirm.",
                        }
                    },
                    "required": ["bookingUid"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the result of the booking confirmation operation",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "Meeting Title",\n    "status": "accepted"\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="decline_booking",
                description="Decline a pending booking",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "bookingUid": {
                            "type": "string",
                            "description": "The unique ID of the booking to decline.",
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for declining the booking (optional)",
                        },
                    },
                    "required": ["bookingUid"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing the result of the booking decline operation",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "Meeting Title",\n    "status": "declined",\n    "reason": "Testing API decline"\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="create_booking",
                description="Create a booking in Cal.com. At least one event type identifier is required: eventTypeId OR (eventTypeSlug and username) OR (eventTypeSlug and teamSlug).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "start": {
                            "type": "string",
                            "description": "The start time of the booking in ISO 8601 format in UTC timezone (e.g., '2024-08-13T09:00:00Z')",
                        },
                        "attendee": {
                            "type": "object",
                            "properties": {
                                "email": {
                                    "type": "string",
                                    "description": "The attendee's email",
                                },
                                "name": {
                                    "type": "string",
                                    "description": "The attendee's name",
                                },
                                "timeZone": {
                                    "type": "string",
                                    "description": "The attendee's timezone (e.g., 'America/New_York')",
                                },
                                "phoneNumber": {
                                    "type": "string",
                                    "description": "The attendee's phone number",
                                },
                                "language": {
                                    "type": "string",
                                    "description": "The attendee's preferred language",
                                },
                            },
                            "required": ["email", "name"],
                            "description": "The attendee's details",
                        },
                        "lengthInMinutes": {
                            "type": "number",
                            "description": "If it's an event type with multiple possible lengths, specify the desired booking length here",
                        },
                        "eventTypeId": {
                            "type": "number",
                            "description": "The ID of the event type to book. Required unless eventTypeSlug and username/teamSlug are provided.",
                        },
                        "eventTypeSlug": {
                            "type": "string",
                            "description": "The slug of the event type. Required with username/teamSlug if eventTypeId not provided.",
                        },
                        "username": {
                            "type": "string",
                            "description": "The username of the event owner. Used with eventTypeSlug if eventTypeId not provided.",
                        },
                        "teamSlug": {
                            "type": "string",
                            "description": "Team slug for team that owns the event type. Used with eventTypeSlug if eventTypeId not provided.",
                        },
                        "organizationSlug": {
                            "type": "string",
                            "description": "The organization slug. Optional, used with eventTypeSlug + username or eventTypeSlug + teamSlug.",
                        },
                        "guests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of guest emails attending the event",
                        },
                        "instant": {
                            "type": "boolean",
                            "description": "Set to true to create an instant meeting (for team event types only)",
                        },
                        "location": {
                            "type": "object",
                            "description": "One of the event type locations",
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional data to store with the booking",
                        },
                        "bookingFieldsResponses": {
                            "type": "object",
                            "description": "Booking field responses with field slug as keys and user response as values",
                        },
                    },
                    "required": ["start", "attendee"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing details of the newly created booking",
                    "examples": [
                        '{\n  "status": "success",\n  "data": {\n    "id": 123456,\n    "uid": "ABCD1234efgh5678",\n    "title": "Meeting with John Doe",\n    "status": "accepted",\n    "start": "2023-05-01T10:00:00.000Z",\n    "end": "2023-05-01T10:30:00.000Z",\n    "attendees": [\n      {\n        "name": "John Doe",\n        "email": "john@example.com",\n        "timeZone": "America/New_York"\n      }\n    ]\n  },\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="get_bookings",
                description="Get all bookings from Cal.com",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "upcoming",
                                    "recurring",
                                    "past",
                                    "cancelled",
                                    "unconfirmed",
                                ],
                            },
                            "description": "Filter bookings by status",
                        },
                        "attendeeEmail": {
                            "type": "string",
                            "description": "Filter bookings by the attendee's email address",
                        },
                        "attendeeName": {
                            "type": "string",
                            "description": "Filter bookings by the attendee's name",
                        },
                        "eventTypeIds": {
                            "type": "string",
                            "description": "Filter bookings by event type ids (comma-separated)",
                        },
                        "eventTypeId": {
                            "type": "string",
                            "description": "Filter bookings by event type id",
                        },
                        "take": {
                            "type": "number",
                            "description": "The number of items to return",
                        },
                        "skip": {
                            "type": "number",
                            "description": "The number of items to skip",
                        },
                    },
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing list of bookings matching the specified filters",
                    "examples": [
                        '{\n  "status": "success",\n  "data": [\n    {\n      "id": 123456,\n      "uid": "ABCD1234efgh5678",\n      "title": "Meeting between User and Attendee",\n      "status": "accepted",\n      "start": "2023-05-01T14:30:00.000Z",\n      "end": "2023-05-01T15:00:00.000Z"\n    },\n    {\n      "id": 123457,\n      "uid": "EFGH5678ijkl9012",\n      "title": "Call between User and Client",\n      "status": "accepted",\n      "start": "2023-05-02T10:00:00.000Z",\n      "end": "2023-05-02T10:30:00.000Z"\n    }\n  ],\n  "_status_code": 200\n}'
                    ],
                },
            ),
            Tool(
                name="get_schedules",
                description="Get all schedules from the authenticated user in Cal.com",
                inputSchema={"type": "object", "properties": {}},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "JSON string containing list of availability schedules for the authenticated user",
                    "examples": [
                        '{\n  "status": "success",\n  "data": [\n    {\n      "id": 12345,\n      "name": "Working Hours",\n      "timeZone": "America/New_York",\n      "availability": [\n        {\n          "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],\n          "startTime": "09:00",\n          "endTime": "17:00"\n        }\n      ],\n      "isDefault": true\n    }\n  ],\n  "_status_code": 200\n}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        api_key = await get_cal_credentials(server.user_id, server.api_key)
        arguments = arguments or {}

        endpoints = {
            "get_me": {"method": "get", "endpoint": "me"},
            "get_event_types": {"method": "get", "endpoint": "event-types"},
            "get_booking": {
                "method": "get",
                "endpoint": lambda args: f"bookings/{args.pop('bookingUid')}",
            },
            "reschedule_booking": {
                "method": "post",
                "endpoint": lambda args: f"bookings/{args.pop('bookingUid')}/reschedule",
            },
            "cancel_booking": {
                "method": "post",
                "endpoint": lambda args: f"bookings/{args.pop('bookingUid')}/cancel",
            },
            "confirm_booking": {
                "method": "post",
                "endpoint": lambda args: f"bookings/{args.pop('bookingUid')}/confirm",
                "api_version": "2024-08-13",
            },
            "decline_booking": {
                "method": "post",
                "endpoint": lambda args: f"bookings/{args.pop('bookingUid')}/decline",
                "api_version": "2024-08-13",
            },
            "create_booking": {"method": "post", "endpoint": "bookings"},
            "get_bookings": {"method": "get", "endpoint": "bookings"},
            "get_schedules": {
                "method": "get",
                "endpoint": "schedules",
                "api_version": "2024-06-11",
            },
        }

        if name not in endpoints:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        try:
            endpoint_info = endpoints[name]
            method = endpoint_info["method"]
            api_version = endpoint_info.get("api_version")

            if callable(endpoint_info["endpoint"]):
                endpoint = endpoint_info["endpoint"](arguments)
            else:
                endpoint = endpoint_info["endpoint"]

            data = arguments if method in ["post", "patch"] else None
            params = arguments if method in ["get", "delete"] else None

            response = await make_cal_request(
                method,
                endpoint,
                data=data,
                params=params,
                api_key=api_key,
                api_version=api_version,
            )

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error using {name} tool: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
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
        user_id = "local"
        authenticate_and_save_cal_key(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the guMCP server framework.")
