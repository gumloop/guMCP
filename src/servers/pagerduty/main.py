import os
import sys
from typing import Optional, Iterable, Dict, Any, Callable
import json

project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import logging
from pathlib import Path
import httpx

from mcp.types import (
    Resource,
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from src.utils.pagerduty.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
PAGERDUTY_API_URL = "https://api.pagerduty.com"
SCOPES = ["write", "read"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(SERVICE_NAME)


async def make_pagerduty_request(
    method, endpoint, data=None, headers=None, access_token=None, params=None
):
    if not access_token:
        raise ValueError("PagerDuty access token is required")

    url = f"{PAGERDUTY_API_URL}/{endpoint}"

    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
    }

    if headers and "From" in headers:
        request_headers["From"] = headers["From"]

    if headers:
        for key, value in headers.items():
            request_headers[key] = value

    async with httpx.AsyncClient() as client:
        if method.lower() == "get":
            response = await client.get(url, headers=request_headers, params=params)
        elif method.lower() == "post":
            response = await client.post(url, json=data, headers=request_headers)
        elif method.lower() == "put":
            response = await client.put(url, json=data, headers=request_headers)
        elif method.lower() == "delete":
            response = await client.delete(url, headers=request_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        status_code = response.status_code
        response_data = response.json() if response.content else {}

        return status_code, response_data


def create_server(user_id, api_key=None):
    server = Server("pagerduty-server")
    server.user_id = user_id

    async def get_pagerduty_token():
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return access_token

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            Tool(
                name="get_user",
                description="Get details about an existing user in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the user to retrieve.",
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "contact_methods",
                                    "notification_rules",
                                    "teams",
                                    "subdomains",
                                ],
                            },
                            "description": "Array of additional Models to include in response.",
                        },
                    },
                    "required": ["id"],
                },
            ),
            Tool(
                name="list_incidents",
                description="List existing incidents from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page. Maximum of 100.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results.",
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False,
                        },
                        "date_range": {
                            "type": "string",
                            "enum": ["all"],
                            "description": "When set to all, the since and until parameters and defaults are ignored.",
                        },
                        "incident_key": {
                            "type": "string",
                            "description": "Incident de-duplication key.",
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "acknowledgers",
                                    "agents",
                                    "assignees",
                                    "conference_bridge",
                                    "escalation_policies",
                                    "first_trigger_log_entries",
                                    "priorities",
                                    "services",
                                    "teams",
                                    "users",
                                ],
                            },
                            "description": "Array of additional details to include.",
                        },
                        "service_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Returns only incidents associated with these services.",
                        },
                        "since": {
                            "type": "string",
                            "description": "The start of the date range over which to search.",
                        },
                        "sort_by": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Fields to sort by (incident_number/created_at/resolved_at/urgency) with direction (asc/desc).",
                        },
                        "statuses": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["triggered", "acknowledged", "resolved"],
                            },
                            "description": "Return only incidents with the given statuses.",
                        },
                        "team_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "An array of team IDs to filter incidents by.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                        "until": {
                            "type": "string",
                            "description": "The end of the date range over which to search.",
                        },
                        "urgencies": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["high", "low"]},
                            "description": "Array of urgencies to filter incidents by.",
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Returns only incidents currently assigned to these users.",
                        },
                    },
                    "required": ["email_from"],
                },
            ),
            Tool(
                name="list_services",
                description="List existing services from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Filters the result, showing only the records whose name matches the query.",
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False,
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "escalation_policies",
                                    "teams",
                                    "integrations",
                                    "auto_pause_notifications_parameters",
                                ],
                            },
                            "description": "Array of additional details to include.",
                        },
                        "name": {
                            "type": "string",
                            "description": "Filters the results, showing only services with the specified name.",
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["name", "name:asc", "name:desc"],
                            "description": "Used to specify the field to sort the results on.",
                            "default": "name",
                        },
                        "team_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "An array of team IDs to filter services by.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                    },
                    "required": ["email_from"],
                },
            ),
            Tool(
                name="list_schedules",
                description="List on-call schedules from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results.",
                        },
                        "query": {
                            "type": "string",
                            "description": "Filters the result, showing only the records whose name matches the query.",
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False,
                        },
                        "include": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["schedule_layers"]},
                            "description": "Array of additional details to include.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                    },
                    "required": ["email_from"],
                },
            ),
            Tool(
                name="create_schedule",
                description="Create a new on-call schedule in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the schedule.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "The time zone of the schedule.",
                        },
                        "description": {
                            "type": "string",
                            "description": "The description of the schedule.",
                        },
                        "schedule_layers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the schedule layer.",
                                    },
                                    "start": {
                                        "type": "string",
                                        "description": "The start time of the schedule layer.",
                                    },
                                    "rotation_virtual_start": {
                                        "type": "string",
                                        "description": "The time when the layer starts rotating.",
                                    },
                                    "rotation_turn_length_seconds": {
                                        "type": "integer",
                                        "description": "The duration of each on-call shift in seconds.",
                                    },
                                    "users": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "user": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {
                                                            "type": "string",
                                                            "description": "The ID of the user.",
                                                        },
                                                        "type": {
                                                            "type": "string",
                                                            "enum": ["user_reference"],
                                                            "description": "The type of reference.",
                                                        },
                                                    },
                                                    "required": ["id", "type"],
                                                }
                                            },
                                            "required": ["user"],
                                        },
                                        "description": "The users in the layer.",
                                    },
                                    "restrictions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "type": {
                                                    "type": "string",
                                                    "enum": [
                                                        "daily_restriction",
                                                        "weekly_restriction",
                                                    ],
                                                    "description": "The type of restriction.",
                                                },
                                                "start_time_of_day": {
                                                    "type": "string",
                                                    "description": "The time of day when the restriction starts.",
                                                },
                                                "duration_seconds": {
                                                    "type": "integer",
                                                    "description": "The duration of the restriction in seconds.",
                                                },
                                            },
                                            "required": [
                                                "type",
                                                "start_time_of_day",
                                                "duration_seconds",
                                            ],
                                        },
                                        "description": "The restrictions for the layer.",
                                    },
                                },
                                "required": [
                                    "name",
                                    "start",
                                    "rotation_virtual_start",
                                    "rotation_turn_length_seconds",
                                    "users",
                                ],
                            },
                            "description": "A list of schedule layers.",
                        },
                        "overflow": {
                            "type": "boolean",
                            "description": "If true, on-call schedule entries that pass the date range bounds will not be truncated.",
                            "default": False,
                        },
                    },
                    "required": ["email_from", "name", "time_zone", "schedule_layers"],
                },
            ),
            Tool(
                name="get_schedule",
                description="Get details about an existing schedule in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the schedule to retrieve.",
                        },
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "since": {
                            "type": "string",
                            "description": "The start of the date range over which to show schedule entries.",
                        },
                        "until": {
                            "type": "string",
                            "description": "The end of the date range over which to show schedule entries.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                        "overflow": {
                            "type": "boolean",
                            "description": "If true, on-call schedule entries that pass the date range bounds will not be truncated.",
                            "default": False,
                        },
                    },
                    "required": ["id", "email_from"],
                },
            ),
            Tool(
                name="delete_schedule",
                description="Delete an on-call schedule in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "The ID of the schedule to delete.",
                        },
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                    },
                    "required": ["id", "email_from"],
                },
            ),
            Tool(
                name="list_oncalls",
                description="List on-call entries from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results.",
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False,
                        },
                        "earliest": {
                            "type": "boolean",
                            "description": "Return only the earliest on-call for each combination of escalation policy, escalation level, and user.",
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["escalation_policies", "users", "schedules"],
                            },
                            "description": "Array of additional details to include.",
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filters the results, showing only on-calls for the specified user IDs.",
                        },
                        "escalation_policy_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filters the results, showing only on-calls for the specified escalation policy IDs.",
                        },
                        "schedule_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filters the results, showing only on-calls for the specified schedule IDs.",
                        },
                        "since": {
                            "type": "string",
                            "description": "The start of the time range over which to search.",
                        },
                        "until": {
                            "type": "string",
                            "description": "The end of the time range over which to search.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                    },
                    "required": ["email_from"],
                },
            ),
            Tool(
                name="list_notifications",
                description="List notifications from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request.",
                        },
                        "since": {
                            "type": "string",
                            "description": "The start of the date range over which to search.",
                        },
                        "until": {
                            "type": "string",
                            "description": "The end of the date range over which to search.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page.",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results.",
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False,
                        },
                        "filter": {
                            "type": "string",
                            "enum": [
                                "sms_notification",
                                "email_notification",
                                "phone_notification",
                                "push_notification",
                            ],
                            "description": "Return notification of this type only.",
                        },
                        "include": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["users"]},
                            "description": "Array of additional details to include.",
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered.",
                        },
                    },
                    "required": ["email_from", "since", "until"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        access_token = await get_pagerduty_token()

        endpoints = {
            "get_user": {
                "method": "get",
                "endpoint": lambda args: f"users/{args['id']}",
                "prepare_data": None,
                "prepare_headers": None,
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {"include[]": args.get("include")}.items()
                    if v is not None
                },
            },
            "create_incident": {
                "method": "post",
                "endpoint": "incidents",
                "prepare_data": lambda args: {
                    "incident": {
                        "type": "incident",
                        "title": args["title"],
                        "service": {
                            "id": args["service_id"],
                            "type": "service_reference",
                        },
                        **({"urgency": args["urgency"]} if "urgency" in args else {}),
                        **(
                            {"incident_key": args["incident_key"]}
                            if "incident_key" in args
                            else {}
                        ),
                        **(
                            {
                                "body": {
                                    "type": "incident_body",
                                    "details": args["details"],
                                }
                            }
                            if "details" in args
                            else {}
                        ),
                        **(
                            {
                                "priority": {
                                    "id": args["priority_id"],
                                    "type": "priority_reference",
                                }
                            }
                            if "priority_id" in args
                            else {}
                        ),
                        **(
                            {
                                "assignments": [
                                    {
                                        "assignee": {
                                            "id": assignment["assignee_id"],
                                            "type": "user_reference",
                                        }
                                    }
                                    for assignment in args["assignments"]
                                ]
                            }
                            if "assignments" in args
                            else {}
                        ),
                        **(
                            {"incident_type": {"name": args["incident_type"]}}
                            if "incident_type" in args
                            else {}
                        ),
                        **(
                            {
                                "escalation_policy": {
                                    "id": args["escalation_policy_id"],
                                    "type": "escalation_policy_reference",
                                }
                            }
                            if "escalation_policy_id" in args
                            else {}
                        ),
                        **(
                            {"conference_bridge": args["conference_bridge"]}
                            if "conference_bridge" in args
                            else {}
                        ),
                    }
                },
                "prepare_headers": lambda args: {"From": args["email_from"]},
            },
            "list_incidents": {
                "method": "get",
                "endpoint": "incidents",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "total": args.get("total"),
                        "date_range": args.get("date_range"),
                        "incident_key": args.get("incident_key"),
                        "include[]": args.get("include"),
                        "service_ids[]": args.get("service_ids"),
                        "since": args.get("since"),
                        "sort_by": args.get("sort_by"),
                        "statuses[]": args.get("statuses"),
                        "team_ids[]": args.get("team_ids"),
                        "time_zone": args.get("time_zone"),
                        "until": args.get("until"),
                        "urgencies[]": args.get("urgencies"),
                        "user_ids[]": args.get("user_ids"),
                    }.items()
                    if v is not None
                },
            },
            "list_services": {
                "method": "get",
                "endpoint": "services",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "query": args.get("query"),
                        "total": args.get("total"),
                        "include[]": args.get("include"),
                        "name": args.get("name"),
                        "sort_by": args.get("sort_by"),
                        "team_ids[]": args.get("team_ids"),
                        "time_zone": args.get("time_zone"),
                    }.items()
                    if v is not None
                },
            },
            "list_schedules": {
                "method": "get",
                "endpoint": "schedules",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "query": args.get("query"),
                        "total": args.get("total"),
                        "include[]": args.get("include"),
                        "time_zone": args.get("time_zone"),
                    }.items()
                    if v is not None
                },
            },
            "create_schedule": {
                "method": "post",
                "endpoint": "schedules",
                "prepare_data": lambda args: {
                    "schedule": {
                        "name": args["name"],
                        "type": "schedule",
                        "time_zone": args["time_zone"],
                        **(
                            {"description": args["description"]}
                            if "description" in args
                            else {}
                        ),
                        "schedule_layers": args["schedule_layers"],
                    }
                },
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    "overflow": args.get("overflow", False)
                },
            },
            "get_schedule": {
                "method": "get",
                "endpoint": lambda args: f"schedules/{args['id']}",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "since": args.get("since"),
                        "until": args.get("until"),
                        "time_zone": args.get("time_zone"),
                        "overflow": args.get("overflow"),
                    }.items()
                    if v is not None
                },
            },
            "delete_schedule": {
                "method": "delete",
                "endpoint": lambda args: f"schedules/{args['id']}",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": None,
            },
            "list_oncalls": {
                "method": "get",
                "endpoint": "oncalls",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "total": args.get("total"),
                        "earliest": args.get("earliest"),
                        "include[]": args.get("include"),
                        "user_ids[]": args.get("user_ids"),
                        "escalation_policy_ids[]": args.get("escalation_policy_ids"),
                        "schedule_ids[]": args.get("schedule_ids"),
                        "since": args.get("since"),
                        "until": args.get("until"),
                        "time_zone": args.get("time_zone"),
                    }.items()
                    if v is not None
                },
            },
            "list_notifications": {
                "method": "get",
                "endpoint": "notifications",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v
                    for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "total": args.get("total"),
                        "filter": args.get("filter"),
                        "include[]": args.get("include"),
                        "since": args.get("since"),
                        "until": args.get("until"),
                        "time_zone": args.get("time_zone"),
                    }.items()
                    if v is not None
                },
            },
        }

        try:
            if name in endpoints:
                endpoint_info = endpoints[name]
                method = endpoint_info["method"]
                endpoint = endpoint_info["endpoint"]
                if callable(endpoint):
                    endpoint = endpoint(arguments)

                data = None
                if callable(endpoint_info.get("prepare_data")):
                    data = endpoint_info["prepare_data"](arguments)

                headers = None
                if callable(endpoint_info.get("prepare_headers")):
                    headers = endpoint_info["prepare_headers"](arguments)

                params = None
                if callable(endpoint_info.get("prepare_params")):
                    params = endpoint_info["prepare_params"](arguments)

                status_code, response = await make_pagerduty_request(
                    method=method,
                    endpoint=endpoint,
                    data=data,
                    headers=headers,
                    access_token=access_token,
                    params=params,
                )

                formatted_response = json.dumps(response, indent=2)

                if 200 <= status_code < 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Request successful! Status: {status_code}\n\n{formatted_response}",
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Request failed with status code {status_code}:\n\n{formatted_response}",
                        )
                    ]
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            logger.error(f"Error executing {name}: {str(e)}")
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="pagerduty-server",
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
        print("Note: To run the server normally, use the guMCP server framework.")
