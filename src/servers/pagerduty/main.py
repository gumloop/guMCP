import os
import sys
from typing import Optional, Iterable, Dict, Any, Callable
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

from src.utils.pagerduty.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name
PAGERDUTY_API_URL = "https://api.pagerduty.com"
SCOPES = [
    "write",
    "read"
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


async def make_pagerduty_request(method, endpoint, data=None, headers=None, access_token=None, params=None):
    """Make a request to the PagerDuty API"""
    if not access_token:
        raise ValueError("PagerDuty access token is required")

    url = f"{PAGERDUTY_API_URL}/{endpoint}"
    
    # Prepare headers
    request_headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json",
        "From": "jyoti@gumloop.com"
    }
    
    # Add From header if it's present in the headers dict
    # if headers and "From" in headers:
    #     request_headers["From"] = headers["From"]
        
    # Merge any additional headers
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

        # Get status code and response data without raising exceptions
        status_code = response.status_code
        response_data = response.json() if response.content else {}
        
        return status_code, response_data


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("pagerduty-server")

    server.user_id = user_id

    async def get_pagerduty_token():
        """Get PagerDuty access token for the current user"""
        access_token = await get_credentials(user_id, SERVICE_NAME, api_key=api_key)
        return access_token

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List resources from PagerDuty"""
        # For now, we're not implementing resource listing
        # This could be expanded to list incidents, services, etc.
        return []

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools for PagerDuty"""
        logger.info(f"Listing tools for user: {server.user_id}")
        return [
            Tool(
                name="create_incident",
                description="Create a new incident in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "A succinct description of the nature, symptoms, cause, or effect of the incident."
                        },
                        "service_id": {
                            "type": "string",
                            "description": "The ID of the service the incident is associated with."
                        },
                        "urgency": {
                            "type": "string",
                            "enum": ["high", "low"],
                            "description": "The urgency of the incident."
                        },
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request."
                        },
                        "incident_key": {
                            "type": "string",
                            "description": "A string which identifies the incident. Duplicate incidents with the same key will be rejected."
                        },
                        "details": {
                            "type": "string",
                            "description": "Additional details about the incident."
                        },
                        "priority_id": {
                            "type": "string",
                            "description": "The ID of the priority to use for the incident."
                        },
                        "assignments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "assignee_id": {
                                        "type": "string",
                                        "description": "The ID of the user to assign."
                                    },
                                    "assignee_type": {
                                        "type": "string",
                                        "enum": ["user"],
                                        "description": "The type of assignee (user)."
                                    }
                                },
                                "required": ["assignee_id"]
                            },
                            "description": "Assign the incident to these assignees."
                        },
                        "incident_type": {
                            "type": "string",
                            "description": "Type of incident (e.g., major_incident)."
                        },
                        "escalation_policy_id": {
                            "type": "string",
                            "description": "The ID of the escalation policy to use."
                        },
                        "conference_bridge": {
                            "type": "object",
                            "properties": {
                                "conference_number": {
                                    "type": "string",
                                    "description": "Phone number for the conference bridge."
                                },
                                "conference_url": {
                                    "type": "string",
                                    "description": "URL for the conference bridge."
                                }
                            },
                            "description": "Conference bridge information for the incident."
                        }
                    },
                    "required": ["title", "service_id", "email_from"]
                }
            ),
            Tool(
                name="list_incidents",
                description="List existing incidents from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page. Maximum of 100."
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results."
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False
                        },
                        "date_range": {
                            "type": "string",
                            "enum": ["all"],
                            "description": "When set to all, the since and until parameters and defaults are ignored."
                        },
                        "incident_key": {
                            "type": "string",
                            "description": "Incident de-duplication key."
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "acknowledgers", "agents", "assignees", "conference_bridge",
                                    "escalation_policies", "first_trigger_log_entries",
                                    "priorities", "services", "teams", "users"
                                ]
                            },
                            "description": "Array of additional details to include."
                        },
                        "service_ids": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Returns only incidents associated with these services."
                        },
                        "since": {
                            "type": "string",
                            "description": "The start of the date range over which to search."
                        },
                        "sort_by": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Fields to sort by (incident_number/created_at/resolved_at/urgency) with direction (asc/desc)."
                        },
                        "statuses": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["triggered", "acknowledged", "resolved"]
                            },
                            "description": "Return only incidents with the given statuses."
                        },
                        "team_ids": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "An array of team IDs to filter incidents by."
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered."
                        },
                        "until": {
                            "type": "string",
                            "description": "The end of the date range over which to search."
                        },
                        "urgencies": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["high", "low"]
                            },
                            "description": "Array of urgencies to filter incidents by."
                        },
                        "user_ids": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "Returns only incidents currently assigned to these users."
                        }
                    },
                    "required": ["email_from"]
                }
            ),
            Tool(
                name="create_service",
                description="Create a new service in PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request."
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the service."
                        },
                        "description": {
                            "type": "string",
                            "description": "The user-provided description of the service."
                        },
                        "escalation_policy_id": {
                            "type": "string",
                            "description": "The ID of the escalation policy to use."
                        },
                        "auto_resolve_timeout": {
                            "type": "integer",
                            "description": "Time in seconds that an incident is automatically resolved if left open for that long. Value is null if the feature is disabled."
                        },
                        "acknowledgement_timeout": {
                            "type": "integer",
                            "description": "Time in seconds that an incident changes to the Triggered State after being Acknowledged."
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "warning", "critical", "maintenance", "disabled"],
                            "description": "The current state of the Service.",
                            "default": "active"
                        },
                        "incident_urgency_rule": {
                            "type": "object",
                            "description": "The incident urgency rule for the service."
                        },
                        "support_hours": {
                            "type": "object",
                            "description": "The support hours for the service."
                        },
                        "scheduled_actions": {
                            "type": "array",
                            "description": "An array containing scheduled actions for the service."
                        },
                        "alert_creation": {
                            "type": "string",
                            "enum": ["create_incidents", "create_alerts_and_incidents"],
                            "description": "Whether a service creates only incidents, or both alerts and incidents.",
                            "default": "create_alerts_and_incidents"
                        },
                        "alert_grouping_parameters": {
                            "type": "object",
                            "description": "Defines how alerts on this service will be automatically grouped into incidents."
                        },
                        "auto_pause_notifications_parameters": {
                            "type": "object",
                            "description": "Defines how alerts on this service are automatically suspended before triggering."
                        }
                    },
                    "required": ["email_from", "name", "escalation_policy_id"]
                }
            ),
            Tool(
                name="list_services",
                description="List existing services from PagerDuty",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email_from": {
                            "type": "string",
                            "description": "The email address of a valid user making the request."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The number of results per page."
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Offset to start pagination search results."
                        },
                        "query": {
                            "type": "string",
                            "description": "Filters the result, showing only the records whose name matches the query."
                        },
                        "total": {
                            "type": "boolean",
                            "description": "Set to true to populate the total field in pagination responses.",
                            "default": False
                        },
                        "include": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [
                                    "escalation_policies", 
                                    "teams", 
                                    "integrations", 
                                    "auto_pause_notifications_parameters"
                                ]
                            },
                            "description": "Array of additional details to include."
                        },
                        "name": {
                            "type": "string",
                            "description": "Filters the results, showing only services with the specified name."
                        },
                        "sort_by": {
                            "type": "string",
                            "enum": ["name", "name:asc", "name:desc"],
                            "description": "Used to specify the field to sort the results on.",
                            "default": "name"
                        },
                        "team_ids": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "An array of team IDs to filter services by."
                        },
                        "time_zone": {
                            "type": "string",
                            "description": "Time zone in which results will be rendered."
                        }
                    },
                    "required": ["email_from"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> list[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests for PagerDuty"""
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )

        access_token = await get_pagerduty_token()
        
        # Define endpoints mapping (similar to Reducto's approach)
        endpoints = {
            "create_incident": {
                "method": "post", 
                "endpoint": "incidents",
                "prepare_data": lambda args: {
                    "incident": {
                        "type": "incident",
                        "title": args["title"],
                        "service": {
                            "id": args["service_id"],
                            "type": "service_reference"
                        },
                        **({"urgency": args["urgency"]} if "urgency" in args else {}),
                        **({"incident_key": args["incident_key"]} if "incident_key" in args else {}),
                        **({"body": {
                            "type": "incident_body",
                            "details": args["details"]
                        }} if "details" in args else {}),
                        **({"priority": {
                            "id": args["priority_id"],
                            "type": "priority_reference"
                        }} if "priority_id" in args else {}),
                        **({"assignments": [
                            {
                                "assignee": {
                                    "id": assignment["assignee_id"],
                                    "type": "user_reference"
                                }
                            } for assignment in args["assignments"]
                        ]} if "assignments" in args else {}),
                        **({"incident_type": {
                            "name": args["incident_type"]
                        }} if "incident_type" in args else {}),
                        **({"escalation_policy": {
                            "id": args["escalation_policy_id"],
                            "type": "escalation_policy_reference"
                        }} if "escalation_policy_id" in args else {}),
                        **({"conference_bridge": args["conference_bridge"]} if "conference_bridge" in args else {})
                    }
                },
                "prepare_headers": lambda args: {"From": args["email_from"]}
            },
            "list_incidents": {
                "method": "get",
                "endpoint": "incidents",
                "prepare_data": None, 
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v for k, v in {
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
                        "user_ids[]": args.get("user_ids")
                    }.items() if v is not None
                }
            },
            "create_service": {
                "method": "post",
                "endpoint": "services",
                "prepare_data": lambda args: {
                    "service": {
                        "type": "service",
                        "name": args["name"],
                        "escalation_policy": {
                            "id": args["escalation_policy_id"],
                            "type": "escalation_policy_reference"
                        },
                        **({"description": args["description"]} if "description" in args else {}),
                        **({"auto_resolve_timeout": args["auto_resolve_timeout"]} if "auto_resolve_timeout" in args else {}),
                        **({"acknowledgement_timeout": args["acknowledgement_timeout"]} if "acknowledgement_timeout" in args else {}),
                        **({"status": args["status"]} if "status" in args else {}),
                        **({"incident_urgency_rule": args["incident_urgency_rule"]} if "incident_urgency_rule" in args else {}),
                        **({"support_hours": args["support_hours"]} if "support_hours" in args else {}),
                        **({"scheduled_actions": args["scheduled_actions"]} if "scheduled_actions" in args else {}),
                        **({"alert_creation": args["alert_creation"]} if "alert_creation" in args else {}),
                        **({"alert_grouping_parameters": args["alert_grouping_parameters"]} if "alert_grouping_parameters" in args else {}),
                        **({"auto_pause_notifications_parameters": args["auto_pause_notifications_parameters"]} if "auto_pause_notifications_parameters" in args else {})
                    }
                },
                "prepare_headers": lambda args: {"From": args["email_from"]}
            },
            "list_services": {
                "method": "get",
                "endpoint": "services",
                "prepare_data": None,
                "prepare_headers": lambda args: {"From": args["email_from"]},
                "prepare_params": lambda args: {
                    k: v for k, v in {
                        "limit": args.get("limit"),
                        "offset": args.get("offset"),
                        "query": args.get("query"),
                        "total": args.get("total"),
                        "include[]": args.get("include"),
                        "name": args.get("name"),
                        "sort_by": args.get("sort_by"),
                        "team_ids[]": args.get("team_ids"),
                        "time_zone": args.get("time_zone")
                    }.items() if v is not None
                }
            }
        }

        try:
            if name in endpoints:
                endpoint_info = endpoints[name]
                method = endpoint_info["method"]
                endpoint = endpoint_info["endpoint"]
                
                # Prepare data and headers if needed
                data = None
                if "prepare_data" in endpoint_info and callable(endpoint_info["prepare_data"]):
                    data = endpoint_info["prepare_data"](arguments)
                
                headers = None
                if "prepare_headers" in endpoint_info and callable(endpoint_info["prepare_headers"]):
                    headers = endpoint_info["prepare_headers"](arguments)
                
                # Prepare query parameters if needed
                params = None
                if "prepare_params" in endpoint_info and callable(endpoint_info["prepare_params"]):
                    params = endpoint_info["prepare_params"](arguments)
                
                # Make the API request
                status_code, response = await make_pagerduty_request(
                    method=method,
                    endpoint=endpoint,
                    data=data,
                    headers=headers,
                    access_token=access_token,
                    params=params
                )
                
                formatted_response = json.dumps(response, indent=2)
                
                if 200 <= status_code < 300:
                    return [
                        TextContent(
                            type="text",
                            text=f"Request successful! Status: {status_code}\n\n{formatted_response}"
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text",
                            text=f"Request failed with status code {status_code}:\n\n{formatted_response}"
                        )
                    ]
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            logger.error(f"Error executing {name}: {str(e)}")
            return [
                TextContent(
                    type="text",
                    text=f"Error executing {name}: {str(e)}"
                )
            ]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="pagerduty-server",
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
