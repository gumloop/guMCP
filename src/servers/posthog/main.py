"""
This server provides a set of tools for interacting with the PostHog API directly without using the SDK.
"""

import os
import sys
import json
import requests
from typing import List
import logging
from pathlib import Path
from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from src.utils.posthog.util import (
    get_posthog_credentials,
    authenticate_and_save_posthog_key,
    get_project_details,
)

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id, api_key=None):
    """Create a new server instance with optional user context"""
    server = Server("posthog-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        """List available tools"""
        logger.info("Listing tools for user: %s", server.user_id)
        return [
            Tool(
                name="list_actions",
                description="List all actions in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_action",
                description="Create a new action in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the action",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the action",
                        },
                        "steps": {
                            "type": "array",
                            "description": "List of steps that define the action",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event": {
                                        "type": "string",
                                        "description": "Event name to match",
                                    },
                                    "properties": {
                                        "type": "array",
                                        "description": "Properties to match for the event",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "key": {"type": "string"},
                                                "value": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["name", "steps"],
                },
            ),
            Tool(
                name="get_action",
                description="Get details of a specific action",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action_id": {
                            "type": "integer",
                            "description": "ID of the action to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["action_id"],
                },
            ),
            Tool(
                name="update_action",
                description="Update an existing action",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action_id": {
                            "type": "integer",
                            "description": "ID of the action to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the action",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the action",
                        },
                        "steps": {
                            "type": "array",
                            "description": "Updated list of steps that define the action",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event": {
                                        "type": "string",
                                        "description": "Event name to match",
                                    },
                                    "properties": {
                                        "type": "object",
                                        "description": "Properties to match for the event",
                                    },
                                },
                            },
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["action_id"],
                },
            ),
            Tool(
                name="capture_event",
                description="Capture a custom event with properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "event": {
                            "type": "string",
                            "description": "Name of the event to capture",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for the event",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id", "event"],
                },
            ),
            Tool(
                name="identify_user",
                description="Create or update a user profile with properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "properties": {
                            "type": "object",
                            "description": "User properties to set",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id", "properties"],
                },
            ),
            Tool(
                name="check_feature_flag",
                description="Check if a feature flag is enabled for a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "flag_key": {
                            "type": "string",
                            "description": "Key of the feature flag to check",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for flag evaluation",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id", "flag_key"],
                },
            ),
            Tool(
                name="get_feature_flag_payload",
                description="Get the payload of a feature flag for a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "flag_key": {
                            "type": "string",
                            "description": "Key of the feature flag to check",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for flag evaluation",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id", "flag_key"],
                },
            ),
            Tool(
                name="get_all_flags",
                description="Get all feature flags enabled for a user",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for flag evaluation",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id"],
                },
            ),
            Tool(
                name="group_identify",
                description="Create or update a group profile with properties",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "group_type": {
                            "type": "string",
                            "description": "Type of the group (e.g., 'company', 'team')",
                        },
                        "group_key": {
                            "type": "string",
                            "description": "Unique identifier for the group",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Group properties to set",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["group_type", "group_key", "properties"],
                },
            ),
            Tool(
                name="capture_group_event",
                description="Capture an event associated with a group",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "distinct_id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "event": {
                            "type": "string",
                            "description": "Name of the event to capture",
                        },
                        "group_type": {
                            "type": "string",
                            "description": "Type of the group (e.g., 'company', 'team')",
                        },
                        "group_key": {
                            "type": "string",
                            "description": "Unique identifier for the group",
                        },
                        "properties": {
                            "type": "object",
                            "description": "Additional properties for the event",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["distinct_id", "event", "group_type", "group_key"],
                },
            ),
            Tool(
                name="list_annotations",
                description="List all annotations in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_annotation",
                description="Create a new annotation in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Content of the annotation",
                        },
                        "date_marker": {
                            "type": "string",
                            "description": "ISO formatted date for the annotation",
                        },
                        "scope": {
                            "type": "string",
                            "description": "Scope of the annotation (organization, project, or dashboard)",
                            "enum": ["organization", "project", "dashboard"],
                            "default": "project",
                        },
                        "dashboard_id": {
                            "type": "integer",
                            "description": "Dashboard ID if scope is dashboard",
                        },
                        "creation_type": {
                            "type": "string",
                            "description": "How the annotation was created",
                            "enum": ["USR", "GIT"],
                            "default": "USR",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["content", "date_marker", "creation_type", "scope"],
                },
            ),
            Tool(
                name="get_annotation",
                description="Get details of a specific annotation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "annotation_id": {
                            "type": "integer",
                            "description": "ID of the annotation to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["annotation_id"],
                },
            ),
            Tool(
                name="update_annotation",
                description="Update an existing annotation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "annotation_id": {
                            "type": "integer",
                            "description": "ID of the annotation to update",
                        },
                        "content": {
                            "type": "string",
                            "description": "New content for the annotation",
                        },
                        "date_marker": {
                            "type": "string",
                            "description": "New ISO formatted date for the annotation",
                        },
                        "scope": {
                            "type": "string",
                            "description": "New scope of the annotation",
                            "enum": ["organization", "project", "dashboard"],
                        },
                        "dashboard_id": {
                            "type": "integer",
                            "description": "New dashboard ID if scope is dashboard",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["annotation_id"],
                },
            ),
            Tool(
                name="list_cohorts",
                description="List all cohorts in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_cohort",
                description="Create a new cohort in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the cohort",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the cohort",
                        },
                        "groups": {
                            "type": "array",
                            "description": "List of filter groups that define the cohort",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "properties": {
                                        "type": "array",
                                        "description": "List of property filters",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "key": {
                                                    "type": "string",
                                                    "description": "Property key to filter on",
                                                },
                                                "value": {
                                                    "description": "Value to compare against"
                                                },
                                                "operator": {
                                                    "type": "string",
                                                    "description": "Comparison operator",
                                                    "enum": [
                                                        "exact",
                                                        "is_not",
                                                        "icontains",
                                                        "not_icontains",
                                                        "regex",
                                                        "not_regex",
                                                        "gt",
                                                        "lt",
                                                        "is_set",
                                                        "is_not_set",
                                                    ],
                                                },
                                                "type": {
                                                    "type": "string",
                                                    "description": "Type of property",
                                                    "enum": [
                                                        "person",
                                                        "event",
                                                        "cohort",
                                                    ],
                                                },
                                            },
                                            "required": [
                                                "key",
                                                "value",
                                                "operator",
                                                "type",
                                            ],
                                        },
                                    }
                                },
                                "required": ["properties"],
                            },
                        },
                        "is_static": {
                            "type": "boolean",
                            "description": "Whether this is a static cohort",
                            "default": False,
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["name", "groups"],
                },
            ),
            Tool(
                name="get_cohort",
                description="Get details of a specific cohort",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cohort_id": {
                            "type": "integer",
                            "description": "ID of the cohort to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["cohort_id"],
                },
            ),
            Tool(
                name="update_cohort",
                description="Update an existing cohort",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cohort_id": {
                            "type": "integer",
                            "description": "ID of the cohort to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the cohort",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the cohort",
                        },
                        "groups": {
                            "type": "array",
                            "description": "Updated list of filter groups",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "properties": {
                                        "type": "array",
                                        "description": "List of property filters",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "key": {
                                                    "type": "string",
                                                    "description": "Property key to filter on",
                                                },
                                                "value": {
                                                    "description": "Value to compare against"
                                                },
                                                "operator": {
                                                    "type": "string",
                                                    "description": "Comparison operator",
                                                    "enum": [
                                                        "exact",
                                                        "is_not",
                                                        "icontains",
                                                        "not_icontains",
                                                        "regex",
                                                        "not_regex",
                                                        "gt",
                                                        "lt",
                                                        "is_set",
                                                        "is_not_set",
                                                    ],
                                                },
                                                "type": {
                                                    "type": "string",
                                                    "description": "Type of property",
                                                    "enum": [
                                                        "person",
                                                        "event",
                                                        "cohort",
                                                    ],
                                                },
                                            },
                                            "required": [
                                                "key",
                                                "value",
                                                "operator",
                                                "type",
                                            ],
                                        },
                                    }
                                },
                                "required": ["properties"],
                            },
                        },
                        "is_static": {
                            "type": "boolean",
                            "description": "Whether this is a static cohort",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["cohort_id"],
                },
            ),
            Tool(
                name="delete_cohort",
                description="Delete a cohort",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "cohort_id": {
                            "type": "integer",
                            "description": "ID of the cohort to delete",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["cohort_id"],
                },
            ),
            Tool(
                name="list_dashboards",
                description="List all dashboards in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_dashboard",
                description="Create a new dashboard in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the dashboard",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the dashboard",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply to the dashboard",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="get_dashboard",
                description="Get details of a specific dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["dashboard_id"],
                },
            ),
            Tool(
                name="update_dashboard",
                description="Update an existing dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the dashboard",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the dashboard",
                        },
                        "filters": {
                            "type": "object",
                            "description": "New filters for the dashboard",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["dashboard_id"],
                },
            ),
            Tool(
                name="delete_dashboard",
                description="Delete a dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard to delete",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["dashboard_id"],
                },
            ),
            Tool(
                name="list_dashboard_collaborators",
                description="List all collaborators of a dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard",
                        },
                    },
                    "required": ["dashboard_id"],
                },
            ),
            Tool(
                name="add_dashboard_collaborator",
                description="Add a collaborator to a dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard",
                        },
                        "user_uuid": {
                            "type": "string",
                            "description": "UUID of the user to add as collaborator",
                        },
                        "level": {
                            "type": "string",
                            "description": "Access level for the collaborator",
                            "default": 21,
                        },
                    },
                    "required": ["dashboard_id", "user_uuid", "level"],
                },
            ),
            Tool(
                name="get_dashboard_sharing",
                description="Get sharing settings of a dashboard",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "dashboard_id": {
                            "type": "integer",
                            "description": "ID of the dashboard",
                        },
                    },
                    "required": ["dashboard_id"],
                },
            ),
            Tool(
                name="list_persons",
                description="List all persons in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search": {
                            "type": "string",
                            "description": "Search term to filter persons",
                        },
                        "properties": {
                            "type": "array",
                            "description": "List of property keys to filter by",
                            "items": {"type": "string"},
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="get_person",
                description="Get details of a specific person",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person_id": {
                            "type": "string",
                            "description": "ID of the person to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["person_id"],
                },
            ),
            Tool(
                name="list_experiments",
                description="List all experiments in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_experiment",
                description="Create a new experiment in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the experiment",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the experiment",
                        },
                        "feature_flag_key": {
                            "type": "string",
                            "description": "Feature flag key for the experiment",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Parameters for the experiment",
                            "properties": {
                                "recommended_sample_size": {
                                    "type": "integer",
                                    "description": "Recommended sample size for the experiment",
                                },
                                "minimum_detectable_effect": {
                                    "type": "number",
                                    "description": "Minimum detectable effect size",
                                },
                            },
                        },
                        "secondary_metrics": {
                            "type": "array",
                            "description": "List of secondary metrics for the experiment",
                            "items": {"type": "object"},
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply to the experiment",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["name", "feature_flag_key"],
                },
            ),
            Tool(
                name="get_experiment",
                description="Get details of a specific experiment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "experiment_id": {
                            "type": "integer",
                            "description": "ID of the experiment to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["experiment_id"],
                },
            ),
            Tool(
                name="update_experiment",
                description="Update an existing experiment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "experiment_id": {
                            "type": "integer",
                            "description": "ID of the experiment to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the experiment",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the experiment",
                        },
                        "parameters": {
                            "type": "object",
                            "description": "Updated parameters for the experiment",
                        },
                        "secondary_metrics": {
                            "type": "array",
                            "description": "Updated list of secondary metrics",
                            "items": {"type": "object"},
                        },
                        "filters": {
                            "type": "object",
                            "description": "Updated filters for the experiment",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["experiment_id"],
                },
            ),
            Tool(
                name="check_experiments_requiring_flag",
                description="Get experiments that require flag implementation",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="list_insights",
                description="List all insights in a PostHog project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                },
            ),
            Tool(
                name="create_insight",
                description="Create a new insight in PostHog",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the insight",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply to the insight",
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the insight",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["name", "filters"],
                },
            ),
            Tool(
                name="get_insight_sharing",
                description="Get sharing settings of a specific insight",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "integer",
                            "description": "ID of the insight",
                        },
                    },
                    "required": ["insight_id"],
                },
            ),
            Tool(
                name="get_insight",
                description="Get details of a specific insight",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "integer",
                            "description": "ID of the insight to retrieve",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["insight_id"],
                },
            ),
            Tool(
                name="update_insight",
                description="Update an existing insight",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "integer",
                            "description": "ID of the insight to update",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the insight",
                        },
                        "filters": {
                            "type": "object",
                            "description": "New filters for the insight",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the insight",
                        },
                        "project_id": {
                            "type": "integer",
                            "description": "Optional: Project ID if multiple projects exist",
                        },
                        "project_api_token": {
                            "type": "string",
                            "description": "Optional: Project API token if multiple projects exist",
                        },
                    },
                    "required": ["insight_id"],
                },
            ),
            Tool(
                name="get_insight_activity",
                description="Get activity history for a specific insight",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "integer",
                            "description": "ID of the insight",
                        },
                    },
                    "required": ["insight_id"],
                },
            ),
            Tool(
                name="mark_insight_viewed",
                description="Mark an insight as viewed",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "insight_id": {
                            "type": "integer",
                            "description": "ID of the insight",
                        },
                    },
                    "required": ["insight_id"],
                },
            ),
            Tool(
                name="get_insights_activity",
                description="Get activity history for all insights",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="get_trend_insights",
                description="Get trend insights",
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
            Tool(
                name="create_trend_insight",
                description="Create a trend insight",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the trend insight",
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters for the trend analysis",
                        },
                    },
                    "required": ["name", "filters"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool execution requests"""
        logger.info(
            "User %s calling tool: %s with arguments: %s",
            server.user_id,
            name,
            arguments,
        )

        api_key = await get_posthog_credentials(
            server.user_id, api_key=server.api_key, service_name=SERVICE_NAME
        )
        if not api_key:
            return [
                TextContent(type="text", text="Error: PostHog API key not provided")
            ]

        # Get project details
        try:
            projects = get_project_details(api_key)
            if len(projects) > 1:
                # If multiple projects exist and no project_id provided, return error
                if not arguments.get("project_id") or not arguments.get(
                    "project_api_token"
                ):
                    return [
                        TextContent(
                            type="text",
                            text="Multiple projects found. Please provide project_id and project_api_token in the request.",
                        )
                    ]
                project_id = arguments["project_id"]
                project_api_token = arguments["project_api_token"]
            else:
                # If only one project exists, use its details
                project_id = projects[0]["id"]
                project_api_token = projects[0]["api_token"]
        except Exception as e:
            return [
                TextContent(
                    type="text", text=f"Error getting project details: {str(e)}"
                )
            ]

        # Pass API key in the Authorization header instead of request body
        project_headers = {
            "Content-Type": "application/json",
        }
        private_host_headers = {
            "Authorization": f"Bearer {api_key}",
        }

        # Set up API endpoints
        host = "https://us.i.posthog.com"
        private_host = "https://us.posthog.com/api/projects/"
        decide = "/decide/"
        event = "/i/v0/e/"

        try:
            if name == "capture_event":
                distinct_id = arguments.get("distinct_id")
                event = arguments.get("event")
                properties = arguments.get("properties", {})

                if not distinct_id or not event:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Direct API call for event capture
                payload = {
                    "api_key": project_api_token,
                    "event": event,
                    "distinct_id": distinct_id,
                    "properties": properties,
                }

                response = requests.post(
                    f"{host}/capture/", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Event '{event}' captured for user '{distinct_id}'",
                        "properties": properties,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to capture event: {response.text}",
                    }

            elif name == "identify_user":
                distinct_id = arguments.get("distinct_id")
                properties = arguments.get("properties", {})

                if not distinct_id or not properties:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Direct API call for identify
                payload = {
                    "api_key": project_api_token,
                    "distinct_id": distinct_id,
                    "properties": properties,
                    "$set": properties,
                    "event": "$identify",
                }

                response = requests.post(
                    f"{host}{event}", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"User '{distinct_id}' identified with properties",
                        "properties": properties,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to identify user: {response.text}",
                    }

            elif name == "check_feature_flag":
                distinct_id = arguments.get("distinct_id")
                flag_key = arguments.get("flag_key")
                properties = arguments.get("properties", {})

                if not distinct_id or not flag_key:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Direct API call for feature flag check
                payload = {
                    "api_key": project_api_token,
                    "event": "$feature_flag_check",
                    "distinct_id": distinct_id,
                    "person_properties": properties,
                    "groups": {},
                }

                response = requests.post(
                    f"{host}{decide}", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    resp_data = response.json()
                    is_enabled = (
                        flag_key in resp_data.get("featureFlags", {})
                        and resp_data["featureFlags"][flag_key]
                    )

                    result = {
                        "status": "success",
                        "flag_key": flag_key,
                        "distinct_id": distinct_id,
                        "is_enabled": is_enabled,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to check feature flag: {response.text}",
                    }

            elif name == "get_feature_flag_payload":
                distinct_id = arguments.get("distinct_id")
                flag_key = arguments.get("flag_key")
                properties = arguments.get("properties", {})

                if not distinct_id or not flag_key:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Direct API call for feature flag payload
                payload = {
                    "distinct_id": distinct_id,
                    "person_properties": properties,
                    "groups": {},
                }

                response = requests.post(
                    f"{host}{decide}", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    resp_data = response.json()
                    payload_value = resp_data.get("featureFlagPayloads", {}).get(
                        flag_key
                    )

                    result = {
                        "status": "success",
                        "flag_key": flag_key,
                        "distinct_id": distinct_id,
                        "payload": payload_value,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get feature flag payload: {response.text}",
                    }

            elif name == "get_all_flags":
                distinct_id = arguments.get("distinct_id")
                properties = arguments.get("properties", {})

                if not distinct_id:
                    return [
                        TextContent(
                            type="text", text="Error: Missing distinct_id parameter"
                        )
                    ]

                # Direct API call for all feature flags
                payload = {
                    "api_key": project_api_token,
                    "distinct_id": distinct_id,
                    "person_properties": properties,
                    "groups": {},
                }

                response = requests.post(
                    f"{host}{decide}", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    resp_data = response.json()
                    flags = resp_data.get("featureFlags", {})

                    result = {
                        "status": "success",
                        "distinct_id": distinct_id,
                        "flags": flags,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get all flags: {response.text}",
                    }

            elif name == "group_identify":
                group_type = arguments.get("group_type")
                group_key = arguments.get("group_key")
                properties = arguments.get("properties", {})

                if not group_type or not group_key or not properties:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Direct API call for group identify
                payload = {
                    "api_key": project_api_token,
                    "event": "$groupidentify",
                    "distinct_id": "$group_identify_distinct_id",  # Placeholder distinct_id
                    "properties": {
                        "$group_type": group_type,
                        "$group_key": group_key,
                        "$group_set": properties,
                    },
                }

                response = requests.post(
                    f"{host}{event}", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Group '{group_key}' of type '{group_type}' identified with properties",
                        "properties": properties,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to identify group: {response.text}",
                    }

            elif name == "capture_group_event":
                distinct_id = arguments.get("distinct_id")
                event = arguments.get("event")
                group_type = arguments.get("group_type")
                group_key = arguments.get("group_key")
                properties = arguments.get("properties", {})

                if not distinct_id or not event or not group_type or not group_key:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameters"
                        )
                    ]

                # Add group information to properties
                group_props = properties.copy()
                group_props["$groups"] = {group_type: group_key}

                # Direct API call for group event capture
                payload = {
                    "api_key": project_api_token,
                    "event": event,
                    "distinct_id": distinct_id,
                    "properties": group_props,
                }

                response = requests.post(
                    f"{host}/capture/", json=payload, headers=project_headers
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Group event '{event}' captured for user '{distinct_id}' in group '{group_key}' of type '{group_type}'",
                        "properties": group_props,
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to capture group event: {response.text}",
                    }

            elif name == "list_actions":
                # List all actions
                response = requests.get(
                    f"{private_host}{project_id}/actions/", headers=private_host_headers
                )

                if response.status_code == 200:
                    result = {"status": "success", "actions": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list actions: {response.text}",
                    }

            elif name == "create_action":
                name = arguments.get("name")
                description = arguments.get("description", "")
                steps = arguments.get("steps", [])
                if isinstance(steps, dict):
                    steps = [steps]

                if not name or not steps:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (name, steps)",
                        )
                    ]

                payload = {"name": name, "description": description, "steps": steps}

                response = requests.post(
                    f"{private_host}{project_id}/actions/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Action '{name}' created successfully",
                        "action": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create action: {response.text}",
                    }

            elif name == "get_action":
                action_id = arguments.get("action_id")

                if not action_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (action_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/actions/{action_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "action": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get action: {response.text}",
                    }

            elif name == "update_action":
                action_id = arguments.get("action_id")
                name = arguments.get("name")
                description = arguments.get("description")
                steps = arguments.get("steps")

                if not action_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (action_id)",
                        )
                    ]

                # Build update payload with only provided fields
                payload = {}
                if name is not None:
                    payload["name"] = name
                if description is not None:
                    payload["description"] = description
                if steps is not None:
                    payload["steps"] = steps

                response = requests.patch(
                    f"{private_host}{project_id}/actions/{action_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Action {action_id} updated successfully",
                        "action": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update action: {response.text}",
                    }

            elif name == "list_annotations":
                response = requests.get(
                    f"{private_host}{project_id}/annotations/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "annotations": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list annotations: {response.text}",
                    }

            elif name == "create_annotation":
                content = arguments.get("content")
                date_marker = arguments.get("date_marker")
                scope = arguments.get("scope", "project")
                dashboard_id = arguments.get("dashboard_id")
                creation_type = arguments.get("creation_type", "USR")

                if not content or not date_marker or not creation_type:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (content, date_marker, creation_type)",
                        )
                    ]

                payload = {
                    "content": content,
                    "date_marker": date_marker,
                    "scope": scope,
                    "creation_type": creation_type,
                }

                if dashboard_id and scope == "dashboard":
                    payload["dashboard_id"] = dashboard_id

                response = requests.post(
                    f"{private_host}{project_id}/annotations/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": "Annotation created successfully",
                        "annotation": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create annotation: {response.text}",
                    }

            elif name == "get_annotation":
                annotation_id = arguments.get("annotation_id")

                if not annotation_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (annotation_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/annotations/{annotation_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "annotation": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get annotation: {response.text}",
                    }

            elif name == "update_annotation":
                annotation_id = arguments.get("annotation_id")
                content = arguments.get("content")
                date_marker = arguments.get("date_marker")
                scope = arguments.get("scope")
                dashboard_id = arguments.get("dashboard_id")

                if not annotation_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (annotation_id)",
                        )
                    ]

                # Build update payload with only provided fields
                payload = {}
                if content is not None:
                    payload["content"] = content
                if date_marker is not None:
                    payload["date_marker"] = date_marker
                if scope is not None:
                    payload["scope"] = scope
                if dashboard_id is not None:
                    payload["dashboard_id"] = dashboard_id

                response = requests.patch(
                    f"{private_host}{project_id}/annotations/{annotation_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Annotation {annotation_id} updated successfully",
                        "annotation": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update annotation: {response.text}",
                    }

            elif name == "list_cohorts":
                response = requests.get(
                    f"{private_host}{project_id}/cohorts/", headers=private_host_headers
                )

                if response.status_code == 200:
                    result = {"status": "success", "cohorts": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list cohorts: {response.text}",
                    }

            elif name == "create_cohort":
                name = arguments.get("name")
                description = arguments.get("description", "")
                groups = arguments.get("groups", [])
                is_static = arguments.get("is_static", False)

                if not name or not groups:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (name, groups)",
                        )
                    ]

                payload = {
                    "name": name,
                    "description": description,
                    "groups": groups,
                    "is_static": is_static,
                }

                response = requests.post(
                    f"{private_host}{project_id}/cohorts/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Cohort '{name}' created successfully",
                        "cohort": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create cohort: {response.text}",
                    }

            elif name == "get_cohort":
                cohort_id = arguments.get("cohort_id")

                if not cohort_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (cohort_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/cohorts/{cohort_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "cohort": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get cohort: {response.text}",
                    }

            elif name == "update_cohort":
                cohort_id = arguments.get("cohort_id")
                name = arguments.get("name")
                description = arguments.get("description")
                groups = arguments.get("groups")
                is_static = arguments.get("is_static")

                if not cohort_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (cohort_id)",
                        )
                    ]

                # Build update payload with only provided fields
                payload = {}
                if name is not None:
                    payload["name"] = name
                if description is not None:
                    payload["description"] = description
                if groups is not None:
                    payload["groups"] = groups
                if is_static is not None:
                    payload["is_static"] = is_static

                response = requests.patch(
                    f"{private_host}{project_id}/cohorts/{cohort_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Cohort {cohort_id} updated successfully",
                        "cohort": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update cohort: {response.text}",
                    }

            elif name == "delete_cohort":
                cohort_id = arguments.get("cohort_id")

                if not cohort_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (cohort_id)",
                        )
                    ]

                response = requests.patch(
                    f"{private_host}{project_id}/cohorts/{cohort_id}/",
                    headers=private_host_headers,
                    json={"deleted": True},
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Cohort {cohort_id} deleted successfully",
                    }
                else:
                    result = {"status": "error", "message": "Failed to delete cohort"}

            elif name == "list_dashboards":
                response = requests.get(
                    f"{private_host}{project_id}/dashboards/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "dashboards": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list dashboards: {response.text}",
                    }

            elif name == "create_dashboard":
                name = arguments.get("name")
                description = arguments.get("description", "")
                filters = arguments.get("filters", {})

                if not name:
                    return [
                        TextContent(
                            type="text", text="Error: Missing required parameter (name)"
                        )
                    ]

                payload = {"name": name, "description": description, "filters": filters}

                response = requests.post(
                    f"{private_host}{project_id}/dashboards/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Dashboard '{name}' created successfully",
                        "dashboard": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create dashboard: {response.text}",
                    }

            elif name == "get_dashboard":
                dashboard_id = arguments.get("dashboard_id")

                if not dashboard_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (dashboard_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "dashboard": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get dashboard: {response.text}",
                    }

            elif name == "update_dashboard":
                dashboard_id = arguments.get("dashboard_id")
                name = arguments.get("name")
                description = arguments.get("description")
                filters = arguments.get("filters")

                if not dashboard_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (dashboard_id)",
                        )
                    ]

                payload = {}
                if name is not None:
                    payload["name"] = name
                if description is not None:
                    payload["description"] = description
                if filters is not None:
                    payload["filters"] = filters

                response = requests.patch(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Dashboard {dashboard_id} updated successfully",
                        "dashboard": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update dashboard: {response.text}",
                    }

            elif name == "delete_dashboard":
                dashboard_id = arguments.get("dashboard_id")

                if not dashboard_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (dashboard_id)",
                        )
                    ]

                response = requests.patch(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/",
                    headers=private_host_headers,
                    json={"deleted": True},
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Dashboard {dashboard_id} deleted successfully",
                    }
                else:
                    result = {
                        "status": "error",
                        "message": "Failed to delete dashboard",
                    }

            elif name == "list_dashboard_collaborators":
                dashboard_id = arguments.get("dashboard_id")

                if not dashboard_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (dashboard_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/collaborators/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "collaborators": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list dashboard collaborators: {response.text}",
                    }

            elif name == "add_dashboard_collaborator":
                dashboard_id = arguments.get("dashboard_id")
                user_uuid = arguments.get("user_uuid")
                level = arguments.get("level", 21)
                logger.info(
                    f"Adding collaborator to dashboard {dashboard_id} with user {user_uuid} and level {level}"
                )

                if not dashboard_id or not user_uuid:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (dashboard_id, user_uuid)",
                        )
                    ]

                response = requests.post(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/collaborators/",
                    headers=private_host_headers,
                    json={"user_uuid": user_uuid, "level": level},
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Collaborator added to dashboard {dashboard_id} successfully with access level {level}",
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to add dashboard collaborator: {response.text}",
                    }

            elif name == "get_dashboard_sharing":
                dashboard_id = arguments.get("dashboard_id")

                if not dashboard_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (dashboard_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/dashboards/{dashboard_id}/sharing/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "sharing_settings": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get dashboard sharing settings: {response.text}",
                    }

            elif name == "list_persons":
                search = arguments.get("search", "")
                properties = arguments.get("properties", [])

                params = {}
                if search:
                    params["search"] = search
                if properties:
                    params["properties"] = properties

                response = requests.get(
                    f"{private_host}{project_id}/persons/",
                    headers=private_host_headers,
                    params=params,
                )

                if response.status_code == 200:
                    result = {"status": "success", "persons": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list persons: {response.text}",
                    }

            elif name == "get_person":
                person_id = arguments.get("person_id")

                if not person_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (person_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/persons/{person_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": "Here are the person details:",
                        "person": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get person: {response.text}",
                    }

            elif name == "list_experiments":
                response = requests.get(
                    f"{private_host}{project_id}/experiments/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "experiments": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list experiments: {response.text}",
                    }

            elif name == "create_experiment":
                name = arguments.get("name")
                description = arguments.get("description", "")
                feature_flag_key = arguments.get("feature_flag_key")
                parameters = arguments.get("parameters", {})
                secondary_metrics = arguments.get("secondary_metrics", [])
                filters = arguments.get("filters", {})

                if not name or not feature_flag_key:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (name, feature_flag_key)",
                        )
                    ]

                payload = {
                    "name": name,
                    "description": description,
                    "feature_flag_key": feature_flag_key,
                    "parameters": parameters,
                    "secondary_metrics": secondary_metrics,
                    "filters": filters,
                }

                response = requests.post(
                    f"{private_host}{project_id}/experiments/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Experiment '{name}' created successfully",
                        "experiment": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create experiment: {response.text}",
                    }

            elif name == "get_experiment":
                experiment_id = arguments.get("experiment_id")

                if not experiment_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (experiment_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/experiments/{experiment_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "experiment": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get experiment: {response.text}",
                    }

            elif name == "update_experiment":
                experiment_id = arguments.get("experiment_id")
                name = arguments.get("name")
                description = arguments.get("description")
                parameters = arguments.get("parameters", {})
                secondary_metrics = arguments.get("secondary_metrics", [])
                filters = arguments.get("filters", {})

                if not experiment_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (experiment_id)",
                        )
                    ]

                payload = {
                    "name": name,
                    "description": description,
                    "parameters": parameters,
                    "secondary_metrics": secondary_metrics,
                    "filters": filters,
                }

                response = requests.patch(
                    f"{private_host}{project_id}/experiments/{experiment_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Experiment {experiment_id} updated successfully",
                        "experiment": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update experiment: {response.text}",
                    }

            elif name == "check_experiments_requiring_flag":
                response = requests.get(
                    f"{private_host}{project_id}/experiments/requires_flag_implementation/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "experiments": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to check experiments requiring flag: {response.text}",
                    }

            elif name == "list_insights":
                response = requests.get(
                    f"{private_host}{project_id}/insights/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "insights": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to list insights: {response.text}",
                    }

            elif name == "create_insight":
                name = arguments.get("name")
                filters = arguments.get("filters")
                description = arguments.get("description", "")

                if not name or not filters:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (name, filters)",
                        )
                    ]

                payload = {"name": name, "filters": filters, "description": description}

                response = requests.post(
                    f"{private_host}{project_id}/insights/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Insight '{name}' created successfully",
                        "insight": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create insight: {response.text}",
                    }

            elif name == "get_insight_sharing":
                insight_id = arguments.get("insight_id")

                if not insight_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (insight_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/insights/{insight_id}/sharing/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    sharing_data = response.json()
                    # Ensure access_token is included in the response
                    if "access_token" not in sharing_data:
                        sharing_data["access_token"] = None

                    result = {"status": "success", "sharing_settings": sharing_data}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get insight sharing settings: {response.text}",
                    }

            elif name == "get_insight":
                insight_id = arguments.get("insight_id")

                if not insight_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (insight_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/insights/{insight_id}/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "insight": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get insight: {response.text}",
                    }

            elif name == "update_insight":
                insight_id = arguments.get("insight_id")
                name = arguments.get("name")
                filters = arguments.get("filters")
                description = arguments.get("description")

                if not insight_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (insight_id)",
                        )
                    ]

                payload = {}
                if name is not None:
                    payload["name"] = name
                if filters is not None:
                    payload["filters"] = filters
                if description is not None:
                    payload["description"] = description

                response = requests.patch(
                    f"{private_host}{project_id}/insights/{insight_id}/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = {
                        "status": "success",
                        "message": f"Insight {insight_id} updated successfully",
                        "insight": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to update insight: {response.text}",
                    }

            elif name == "get_insight_activity":
                insight_id = arguments.get("insight_id")

                if not insight_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (insight_id)",
                        )
                    ]

                response = requests.get(
                    f"{private_host}{project_id}/insights/{insight_id}/activity/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "activity": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get insight activity: {response.text}",
                    }

            elif name == "mark_insight_viewed":
                insight_id = arguments.get("insight_id")

                if not insight_id:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameter (insight_id)",
                        )
                    ]

                response = requests.post(
                    f"{private_host}{project_id}/insights/{insight_id}/viewed/",
                    headers=private_host_headers,
                )
                if response.status_code == 201:
                    result = {
                        "status": "success",
                        "message": f"Insight {insight_id} marked as viewed",
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to mark insight as viewed: {response.text}",
                    }

            elif name == "get_insights_activity":
                response = requests.get(
                    f"{private_host}{project_id}/insights/activity/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "activity": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get insights activity: {response.text}",
                    }

            elif name == "get_trend_insights":
                response = requests.get(
                    f"{private_host}{project_id}/insights/trend/",
                    headers=private_host_headers,
                )

                if response.status_code == 200:
                    result = {"status": "success", "trend_insights": response.json()}
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to get trend insights: {response.text}",
                    }

            elif name == "create_trend_insight":
                name = arguments.get("name")
                filters = arguments.get("filters")

                if not name or not filters:
                    return [
                        TextContent(
                            type="text",
                            text="Error: Missing required parameters (name, filters)",
                        )
                    ]

                payload = {"name": name, "filters": filters}

                response = requests.post(
                    f"{private_host}{project_id}/insights/trend/",
                    headers=private_host_headers,
                    json=payload,
                )

                if response.status_code in [200, 201]:
                    result = {
                        "status": "success",
                        "message": f"Trend insight '{name}' created successfully",
                        "trend": response.json(),
                    }
                else:
                    result = {
                        "status": "error",
                        "message": f"Failed to create trend insight: {response.text}",
                    }

            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        except Exception as e:
            logger.error(f"Error during PostHog API call: {str(e)}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    """Get the initialization options for the server"""
    return InitializationOptions(
        server_name="posthog-server",
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
        authenticate_and_save_posthog_key(user_id, SERVICE_NAME)
    else:
        print("Usage:")
        print(" python main.py auth - Run authentication flow for a user")
        print("Note: To run the server normally, use the MCP server framework.")
