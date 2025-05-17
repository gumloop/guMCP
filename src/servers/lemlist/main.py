import json
import os
import sys
from pathlib import Path
import logging
from typing import List
import requests
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from mcp.types import (
    TextContent,
    Tool,
    ImageContent,
    EmbeddedResource,
)

from src.utils.lemlist.util import (
    get_lemlist_credentials,
    authenticate_and_save_lemlist_credentials,
)

SERVICE_NAME = Path(__file__).parent.name

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(SERVICE_NAME)


def create_server(user_id, api_key=None):
    server = Server("lemlist-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[Tool]:
        return [
            types.Tool(
                name="get_team",
                description="Retrieve basic information about the current Lemlist team, including user IDs, name, and beta features.",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing team data",
                    "examples": [
                        '{"_id": "tea_qWoCbAXbjTF73Bxsg", "userIds": ["usr_NJWvZsjbaz9oEJHCC"], "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:27:33.429Z", "beta": ["voip", "lemcalNewLayout", "integrationsN8nMake"], "name": "Gumloop Integrations\'s Team"}'
                    ],
                },
            ),
            types.Tool(
                name="get_senders",
                description="Retrieve all senders associated with the current Lemlist team account.",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing sender data",
                    "examples": ["[]"],
                },
            ),
            types.Tool(
                name="get_credits",
                description="Check the current credit balance for the Lemlist team account. Credits are used for various actions like email verification, enrichment, etc.",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing credit information",
                    "examples": [
                        '{"credits": 500, "details": {"remaining": {"total": 500, "freemium": 0, "subscription": 0, "gifted": 500, "paid": 0}}}'
                    ],
                },
            ),
            types.Tool(
                name="get_user",
                description="Retrieve information about a specific Lemlist user by their user ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "The ID of the user to retrieve. Use 'me' for the current user.",
                        }
                    },
                    "required": ["user_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing user data",
                    "examples": ["{}"],
                },
            ),
            types.Tool(
                name="get_all_campaigns",
                description="Retrieve all campaigns for the current Lemlist team with pagination and sorting options.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of campaigns to return per page.",
                            "default": 100,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "The number of campaigns to skip. Used if page is not provided.",
                            "default": 0,
                        },
                        "page": {
                            "type": "integer",
                            "description": "The page number to retrieve.",
                            "default": 1,
                        },
                        "sortBy": {
                            "type": "string",
                            "description": "The field to sort by: createdAt, name, or status.",
                            "default": "createdAt",
                            "enum": ["createdAt", "name", "status"],
                        },
                        "sortOrder": {
                            "type": "string",
                            "description": "The sort direction: desc for descending, asc for ascending.",
                            "default": "desc",
                            "enum": ["desc", "asc"],
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing campaign data with pagination details",
                    "examples": [
                        '{"campaigns": [{"_id": "cam_v8cz524NPmtnidwkq", "name": "Test Campaign 84909cc0-5802-4abc-8439-409a9afee8ef", "createdAt": "2025-05-17T00:35:08.903Z", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "status": "draft"}], "pagination": {"totalRecords": 1, "currentPage": 1, "nextPage": 1, "totalPage": 1}}'
                    ],
                },
            ),
            types.Tool(
                name="get_campaign",
                description="Retrieve detailed information about a specific Lemlist campaign by its campaignId.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to retrieve.",
                        }
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing detailed campaign data",
                    "examples": [
                        '{"_id": "cam_v8cz524NPmtnidwkq", "name": "Test Campaign 84909cc0-5802-4abc-8439-409a9afee8ef", "createdAt": "2025-05-17T00:35:08.903Z", "status": "draft", "creator": {"userId": "usr_NJWvZsjbaz9oEJHCC", "userEmail": "gumloop-integrations@gumloop.com"}, "senders": []}'
                    ],
                },
            ),
            types.Tool(
                name="create_campaign",
                description="Create a new campaign in Lemlist with a custom name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the campaign.",
                        }
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing data of the created campaign",
                    "examples": [
                        '{"_id": "cam_v8cz524NPmtnidwkq", "name": "Test Campaign 84909cc0-5802-4abc-8439-409a9afee8ef", "sequenceId": "seq_JWP2zXbetuc8TMKF5", "scheduleIds": ["skd_Hgd3JfLDy9i4vkhvo"], "displayedVariableKeys": ["companyName"], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:08.903Z", "state": "running", "scannedCount": 0, "reviewedCount": 0, "inSequenceLeadCount": 0, "variableKeys": [], "senders": [], "sendUsers": [], "emoji": "\\ud83d\\udc8c", "stopOnEmailReplied": true, "crmOpportunitiesOnTask": true, "unsubscribe": "campaign"}'
                    ],
                },
            ),
            types.Tool(
                name="update_campaign",
                description="Update a specific Lemlist campaign by campaignId with custom settings like name and various stop conditions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to update.",
                        },
                        "name": {
                            "type": "string",
                            "description": "New name for the campaign.",
                        },
                        "stopOnEmailReplied": {
                            "type": "boolean",
                            "description": "Whether to stop the campaign sequence when an email is replied to.",
                        },
                        "stopOnMeetingBooked": {
                            "type": "boolean",
                            "description": "Whether to stop the campaign sequence when a meeting is booked.",
                        },
                        "stopOnLinkClicked": {
                            "type": "boolean",
                            "description": "Whether to stop the campaign sequence when a link is clicked.",
                        },
                        "stopOnLinkClickedFilter": {
                            "type": "string",
                            "description": "Specify a link to stop the campaign when clicked. Set to null to unset.",
                        },
                        "leadsPausedByInterest": {
                            "type": "boolean",
                            "description": "Pause leads based on interest.",
                        },
                        "opportunityReplied": {
                            "type": "boolean",
                            "description": "Opportunity replied setting.",
                        },
                        "opportunityClicked": {
                            "type": "boolean",
                            "description": "Opportunity clicked setting.",
                        },
                        "autoLeadInterest": {
                            "type": "boolean",
                            "description": "Automatically determine lead interest.",
                        },
                        "sequenceSharing": {
                            "type": "boolean",
                            "description": "Enable or disable sequence sharing.",
                        },
                        "disableTrackOpen": {
                            "type": "boolean",
                            "description": "Disable open tracking.",
                        },
                        "disableTrackClick": {
                            "type": "boolean",
                            "description": "Disable click tracking.",
                        },
                        "disableTrackReply": {
                            "type": "boolean",
                            "description": "Disable reply tracking.",
                        },
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated campaign settings",
                    "examples": [
                        '{"name": "Updated Campaign 3be50db3-ebd4-4bbb-bfbf-72ef1a33eaa5", "stopOnEmailReplied": true, "stopOnMeetingBooked": true, "stopOnLinkClicked": true, "leadsPausedByInterest": false, "opportunityReplied": false, "opportunityClicked": false, "autoLeadInterest": false, "sequenceSharing": false, "disableTrackOpen": false, "disableTrackClick": false, "disableTrackReply": false}'
                    ],
                },
            ),
            types.Tool(
                name="pause_lemlist_campaign",
                description="Pause a specific Lemlist campaign by its campaignId. This will stop all sending activity for this campaign.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to pause.",
                        }
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing campaign pause confirmation",
                    "examples": ['{"_id": "cam_v8cz524NPmtnidwkq", "state": "paused"}'],
                },
            ),
            types.Tool(
                name="start_lemlist_campaign_export",
                description="Start an asynchronous export of all leads and statistics from a Lemlist campaign. Returns an export ID needed for checking status and downloading the result.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to export statistics from.",
                        }
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing export information and status",
                    "examples": [
                        '{"_id": "axp_EvgfS8MuubZWbKsbM", "id": "axp_EvgfS8MuubZWbKsbM", "teamId": "tea_qWoCbAXbjTF73Bxsg", "campaignId": "cam_v8cz524NPmtnidwkq", "campaignName": "Updated Campaign 3be50db3-ebd4-4bbb-bfbf-72ef1a33eaa5", "status": "pending", "startedAt": "2025-05-17T00:40:14.815Z", "progressIndex": 0, "progressTime": 1747442414815, "progressLastStepDuration": 0, "progressType": "starting", "progress": 0, "total": 0}'
                    ],
                },
            ),
            types.Tool(
                name="get_campaign_export_status",
                description="Check the status of an asynchronous campaign export in Lemlist. Returns export status and CSV URL if available.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign for which the export was started.",
                        },
                        "exportId": {
                            "type": "string",
                            "description": "The export ID returned when starting the export.",
                        },
                    },
                    "required": ["campaignId", "exportId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing export status information, including URL when complete",
                    "examples": [
                        '{"status": {"_id": "axp_TSp7asSM9rkgTubMQ", "id": "axp_TSp7asSM9rkgTubMQ", "teamId": "tea_qWoCbAXbjTF73Bxsg", "campaignId": "cam_v8cz524NPmtnidwkq", "campaignName": "Updated Campaign 3be50db3-ebd4-4bbb-bfbf-72ef1a33eaa5", "status": "done", "url": "https://api.lemlist.com/api/files/exports/fil_axp_TSp7asSM9rkgTubMQ_updated_campaign.csv"}, "csv_url": "https://api.lemlist.com/api/files/exports/fil_axp_TSp7asSM9rkgTubMQ_updated_campaign.csv"}',
                        '{"error": "{\\"ok\\":false,\\"message\\":\\"Export with id not found\\"}"}',
                    ],
                },
            ),
            types.Tool(
                name="export_lemlist_campaign",
                description="Set an email address to receive the download link for a Lemlist campaign export when it's done. Sends the export URL to the provided email when ready.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign that was exported.",
                        },
                        "exportId": {
                            "type": "string",
                            "description": "The export ID returned by the export start endpoint.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address to send the export URL to when the export is done.",
                        },
                    },
                    "required": ["campaignId", "exportId", "email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing export email delivery status",
                    "examples": [
                        '{"ok": true, "status": {"_id": "axp_TSp7asSM9rkgTubMQ", "id": "axp_TSp7asSM9rkgTubMQ", "teamId": "tea_qWoCbAXbjTF73Bxsg", "campaignId": "cam_v8cz524NPmtnidwkq", "campaignName": "Updated Campaign 3be50db3-ebd4-4bbb-bfbf-72ef1a33eaa5", "status": "done", "startedAt": "2025-05-17T00:40:49.998Z", "progressIndex": 6, "progressTime": 1747442450246, "progressLastStepDuration": 0, "progressType": "done", "progress": 0, "total": 0, "fileSize": 626, "endedAt": "2025-05-17T00:40:50.246Z", "url": "https://api.lemlist.com/api/files/exports/fil_axp_TSp7asSM9rkgTubMQ_updated_campaign_3be50db3-ebd4-4bbb-bfbf-72ef1a33eaa5.csv"}}'
                    ],
                },
            ),
            types.Tool(
                name="get_all_schedules",
                description="Retrieve all schedules associated with a Lemlist team, with pagination and sorting options.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page": {
                            "type": "integer",
                            "description": "The page number to retrieve.",
                            "default": 1,
                        },
                        "offset": {
                            "type": "integer",
                            "description": "The number of records to skip. Used if page is not provided.",
                            "default": 0,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "The maximum number of records to return.",
                            "default": 100,
                        },
                        "sortBy": {
                            "type": "string",
                            "description": "The field by which to sort the schedules. Only 'createdAt' is supported.",
                            "default": "createdAt",
                        },
                        "sortOrder": {
                            "type": "string",
                            "description": "The sort direction: 'desc' for descending, or 'asc' for ascending.",
                            "default": "desc",
                            "enum": ["desc", "asc"],
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing schedule data with pagination details",
                    "examples": [
                        '{"schedules": [{"_id": "skd_Q2vZTaN3kzmYSdkTy", "name": "Test Schedule 45713978-d710-4530-ac14-bdf642bd0a58", "secondsToWait": 1200, "timezone": "UTC", "start": "09:00", "end": "17:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:24.153Z"}, {"_id": "skd_Hgd3JfLDy9i4vkhvo", "name": "Default schedule", "secondsToWait": 1200, "timezone": "Europe/Paris", "start": "09:00", "end": "18:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:08.882Z"}], "pagination": {"totalRecords": 2, "currentPage": 1, "nextPage": 1, "totalPage": 1}}'
                    ],
                },
            ),
            types.Tool(
                name="get_schedule",
                description="Retrieve the details of a specific Lemlist schedule by its scheduleId.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scheduleId": {
                            "type": "string",
                            "description": "The ID of the schedule to retrieve.",
                        }
                    },
                    "required": ["scheduleId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing detailed schedule data",
                    "examples": [
                        '{"_id": "skd_Q2vZTaN3kzmYSdkTy", "name": "Test Schedule 45713978-d710-4530-ac14-bdf642bd0a58", "secondsToWait": 1200, "timezone": "UTC", "start": "09:00", "end": "17:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:24.153Z"}'
                    ],
                },
            ),
            types.Tool(
                name="get_campaign_schedules",
                description="Retrieve all schedule objects linked to a specific Lemlist campaign by campaignId.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to retrieve schedules for.",
                        }
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing the campaign's associated schedule data",
                    "examples": [
                        '{"_id": "skd_Hgd3JfLDy9i4vkhvo", "name": "Default schedule", "secondsToWait": 1200, "timezone": "Europe/Paris", "start": "09:00", "end": "18:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:08.882Z"}'
                    ],
                },
            ),
            types.Tool(
                name="update_schedule",
                description="Update an existing Lemlist schedule by scheduleId. Supports updating name, delay, timezone, start/end times, and weekdays.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scheduleId": {
                            "type": "string",
                            "description": "The ID of the schedule to update.",
                        },
                        "name": {
                            "type": "string",
                            "description": "The name of the schedule.",
                        },
                        "secondsToWait": {
                            "type": "number",
                            "description": "Delay in seconds between operations.",
                        },
                        "timezone": {
                            "type": "string",
                            "description": "The timezone for the schedule (e.g., 'Asia/Kolkata').",
                        },
                        "start": {
                            "type": "string",
                            "description": "Start time in HH:mm format (e.g., '09:00').",
                        },
                        "end": {
                            "type": "string",
                            "description": "End time in HH:mm format (e.g., '18:00').",
                        },
                        "weekdays": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Days of the week the schedule is active (e.g., [1, 2]).",
                        },
                    },
                    "required": ["scheduleId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated schedule data",
                    "examples": [
                        '{"_id": "skd_Q2vZTaN3kzmYSdkTy", "name": "Updated Schedule 8db8da6e-9937-44c0-b02a-6e35a118fec0", "secondsToWait": 1800, "timezone": "UTC", "start": "10:00", "end": "18:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:24.153Z"}'
                    ],
                },
            ),
            types.Tool(
                name="create_schedule",
                description="Create a new schedule in Lemlist. Supports custom name, delay, timezone, start/end times, and active weekdays.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the schedule. Defaults to 'Default schedule' if omitted.",
                        },
                        "secondsToWait": {
                            "type": "number",
                            "description": "Delay in seconds between operations. Defaults to 1200.",
                        },
                        "timezone": {
                            "type": "string",
                            "description": "Timezone for the schedule. Defaults to 'Europe/Paris'.",
                        },
                        "start": {
                            "type": "string",
                            "description": "Start time in HH:mm format. Defaults to '09:00'.",
                        },
                        "end": {
                            "type": "string",
                            "description": "End time in HH:mm format. Defaults to '18:00'.",
                        },
                        "weekdays": {
                            "type": "array",
                            "items": {"type": "number"},
                            "description": "Days of the week the schedule is active (1=Monday, ... 7=Sunday). Defaults to [1,2,3,4,5].",
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing data of the created schedule",
                    "examples": [
                        '{"_id": "skd_Q2vZTaN3kzmYSdkTy", "name": "Test Schedule 45713978-d710-4530-ac14-bdf642bd0a58", "secondsToWait": 1200, "timezone": "UTC", "start": "09:00", "end": "17:00", "weekdays": [1, 2, 3, 4, 5], "teamId": "tea_qWoCbAXbjTF73Bxsg", "createdBy": "usr_NJWvZsjbaz9oEJHCC", "createdAt": "2025-05-17T00:35:24.153Z"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_schedule",
                description="Delete a specific schedule in Lemlist by its scheduleId.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "schedule_id": {
                            "type": "string",
                            "description": "The ID of the schedule to delete.",
                        }
                    },
                    "required": ["schedule_id"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing deletion confirmation",
                    "examples": ['{"_id": "None"}'],
                },
            ),
            types.Tool(
                name="associate_schedule_with_campaign",
                description="Associate a schedule with a specific Lemlist campaign using campaignId and scheduleId.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to associate the schedule with.",
                        },
                        "scheduleId": {
                            "type": "string",
                            "description": "The ID of the schedule to associate with the campaign.",
                        },
                    },
                    "required": ["campaignId", "scheduleId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing association confirmation",
                    "examples": [
                        '{"scheduleId": "skd_Q2vZTaN3kzmYSdkTy", "campaignId": "cam_v8cz524NPmtnidwkq"}'
                    ],
                },
            ),
            types.Tool(
                name="create_lead_in_campaign",
                description=(
                    "Add a lead to a specific Lemlist campaign. "
                    "If the lead doesn't exist, it will be created and added to the campaign. "
                    "Supports deduplication, email verification, LinkedIn enrichment, phone finding, and custom lead data."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign to add the lead to.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead. Optional; can be omitted to use enrichment features.",
                        },
                        "deduplicate": {
                            "type": "boolean",
                            "description": "If true, will not insert the lead if the email address already exists in another campaign. Default is false.",
                            "default": False,
                        },
                        "linkedinEnrichment": {
                            "type": "boolean",
                            "description": "If true, will run LinkedIn enrichment to find verified email. Default is false.",
                            "default": False,
                        },
                        "findEmail": {
                            "type": "boolean",
                            "description": "If true, will attempt to find the lead's email. Default is false.",
                            "default": False,
                        },
                        "verifyEmail": {
                            "type": "boolean",
                            "description": "If true, will verify the existing email (debounce). Default is false.",
                            "default": False,
                        },
                        "findPhone": {
                            "type": "boolean",
                            "description": "If true, will attempt to find the lead's phone number. Default is false.",
                            "default": False,
                        },
                        "firstName": {
                            "type": "string",
                            "description": "First name of the lead.",
                        },
                        "lastName": {
                            "type": "string",
                            "description": "Last name of the lead.",
                        },
                        "companyName": {
                            "type": "string",
                            "description": "Company name of the lead.",
                        },
                        "icebreaker": {
                            "type": "string",
                            "description": "Icebreaker text for the lead.",
                        },
                        "phone": {
                            "type": "string",
                            "description": "Phone number of the lead.",
                        },
                        "linkedinUrl": {
                            "type": "string",
                            "description": "LinkedIn profile URL of the lead.",
                        },
                        "companyDomain": {
                            "type": "string",
                            "description": "Domain of the lead's company.",
                        },
                    },
                    "required": ["campaignId"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing data of the created lead",
                    "examples": [
                        '{"campaignId": "cam_v8cz524NPmtnidwkq", "campaignName": "Test Campaign 84909cc0-5802-4abc-8439-409a9afee8ef", "firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false}'
                    ],
                },
            ),
            types.Tool(
                name="delete_lead",
                description="Delete a lead from a specific Lemlist campaign by campaignId and leadId (email address). All information, including statistics, will be permanently deleted.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign from which to delete the lead.",
                        },
                        "leadId": {
                            "type": "string",
                            "description": "The ID of the lead to delete.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead to delete.",
                        },
                    },
                    "required": ["campaignId", "email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing deleted lead data",
                    "examples": [
                        '{"firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false, "campaignId": "cam_v8cz524NPmtnidwkq"}'
                    ],
                },
            ),
            types.Tool(
                name="mark_lead_as_interested_all_campaigns",
                description="Mark a specific lead as interested in all campaigns using their email address. This updates the lead's status to 'Interested' and stops their campaign sequence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead to mark as interested.",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing lead data from all affected campaigns",
                    "examples": [
                        '[{"firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false, "campaignId": "cam_v8cz524NPmtnidwkq"}]'
                    ],
                },
            ),
            types.Tool(
                name="mark_lead_as_not_interested_all_campaigns",
                description="Mark a specific lead as not interested in all campaigns using their email address. This updates the lead's status to 'Not Interested' and stops their campaign sequence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead to mark as not interested.",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing lead data from all affected campaigns",
                    "examples": [
                        '[{"firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false, "campaignId": "cam_v8cz524NPmtnidwkq"}]'
                    ],
                },
            ),
            types.Tool(
                name="mark_lead_as_interested_in_campaign",
                description="Mark a specific lead as interested in a specific Lemlist campaign using their email address. This updates the lead's status to 'Interested' in the given campaign and stops their campaign sequence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign where the lead should be marked as interested.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead to mark as interested.",
                        },
                    },
                    "required": ["campaignId", "email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated lead data",
                    "examples": [
                        '{"firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false, "campaignId": "cam_v8cz524NPmtnidwkq"}'
                    ],
                },
            ),
            types.Tool(
                name="mark_lead_as_not_interested_in_campaign",
                description="Mark a specific lead as not interested in a specific Lemlist campaign using their email address. This updates the lead's status to 'Not Interested' in the given campaign and stops their campaign sequence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "campaignId": {
                            "type": "string",
                            "description": "The ID of the campaign where the lead should be marked as not interested.",
                        },
                        "email": {
                            "type": "string",
                            "description": "The email address of the lead to mark as not interested.",
                        },
                    },
                    "required": ["campaignId", "email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing updated lead data",
                    "examples": [
                        '{"firstName": "Test", "lastName": "User", "companyName": "Test Company", "email": "test_62f7c495-8c57-4338-9e4a-f699d29789d8@example.com", "_id": "lea_Y2KaFkKrTAMZgBapx", "isPaused": false, "campaignId": "cam_v8cz524NPmtnidwkq"}'
                    ],
                },
            ),
            types.Tool(
                name="get_all_unsubscribes",
                description="Retrieve a paginated list of all unsubscribed people from Lemlist. Supports offset and limit for pagination.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "offset": {
                            "type": "integer",
                            "description": "Offset from the start for pagination. Default is 0.",
                            "default": 0,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of unsubscribed emails to retrieve. Default is 100, maximum is 100.",
                            "default": 100,
                        },
                    },
                    "required": [],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing unsubscribes data, empty array if none exist",
                    "examples": ["[]"],
                },
            ),
            types.Tool(
                name="export_unsubscribes",
                description="Download a CSV file containing all unsubscribed email addresses from Lemlist.",
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing unsubscribes export data in CSV format",
                    "examples": [
                        '{"export_data": "value,source,createdAt\\r\\ntest_725f4819-fd51-48a0-839e-ddd5881ea30a@example.com,api,2025-05-17T00:39:29.752Z"}'
                    ],
                },
            ),
            types.Tool(
                name="add_unsubscribe",
                description="Add an email address or domain to Lemlist's unsubscribed list. Domains must start with @ (e.g. @domain.com).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address or domain to unsubscribe (domains must start with @)",
                            "format": "email",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing created unsubscribe data",
                    "examples": [
                        '{"_id": "uns_CnQm6RsypbQthQWbd", "value": "test_725f4819-fd51-48a0-839e-ddd5881ea30a@example.com", "email": "test_725f4819-fd51-48a0-839e-ddd5881ea30a@example.com"}'
                    ],
                },
            ),
            types.Tool(
                name="delete_unsubscribe",
                description="Delete an email address or domain from Lemlist's unsubscribed list. Domains must start with @ (e.g. @domain.com).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "email": {
                            "type": "string",
                            "description": "Email address or domain to delete from unsubscribed list (domains must start with @)",
                            "format": "email",
                        }
                    },
                    "required": ["email"],
                },
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing deleted unsubscribe data",
                    "examples": [
                        '{"_id": "uns_Zatdt3xaWHDqkCL7p", "value": "test_ce371194-ab05-48ce-b9ac-fb247a9a1c62@example.com"}'
                    ],
                },
            ),
            types.Tool(
                name="get_database_filters",
                description=(
                    "Retrieve all available Lemlist database filters. "
                    "Each filter includes a filterId, description, mode (leads/companies), type, helper, and optional values or prefix. "
                    "Use these filters to construct advanced queries for leads or companies."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
                outputSchema={
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of JSON strings containing available filter definitions",
                    "examples": [
                        '{"filterId": "leadsByIds", "description": "Leads by _id", "mode": ["leads"], "type": "text", "helper": "Use free text search (to fill the in and/or out array)"}',
                        '{"filterId": "currentTitle", "description": "Current job title", "mode": ["leads"], "type": "autocomplete", "helper": ""}',
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(
        name: str, arguments: dict | None = None
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle the call to the specified tool."""
        logger.info(
            "User %s calling tool: %s with arguments: %s",
            server.user_id,
            name,
            arguments,
        )

        credential_data = get_lemlist_credentials(server.user_id, server.api_key)

        if not credential_data:
            raise ValueError(
                f"Lemlist credentials not found for user {server.user_id}. Run 'auth' first."
            )

        public_host = credential_data.get("public_host")
        token = credential_data.get("token")

        headers = {"Authorization": f"Basic {token}"}

        try:
            if name == "get_team":
                response = requests.get(f"{public_host}/team", headers=headers)

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_senders":
                response = requests.get(f"{public_host}/team/senders", headers=headers)

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_credits":
                response = requests.get(f"{public_host}/team/credits", headers=headers)

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_user":
                user_id = arguments.get("user_id")
                response = requests.get(
                    f"{public_host}/users/{user_id}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]

            elif name == "get_all_campaigns":
                limit = arguments.get("limit", 100)
                offset = arguments.get("offset", 0)
                page = arguments.get("page", 1)
                sortBy = arguments.get("sortBy", "createdAt")
                sortOrder = arguments.get("sortOrder", "desc")
                version = "v2"

                response = requests.get(
                    f"{public_host}/campaigns?limit={limit}&offset={offset}&page={page}&sortBy={sortBy}&sortOrder={sortOrder}&version={version}",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    # If data contains an array, return multiple TextContent objects
                    if isinstance(data, list):
                        return [
                            TextContent(type="text", text=json.dumps(item))
                            for item in data
                        ]
                    return [TextContent(type="text", text=json.dumps(data))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_campaign":
                campaignId = arguments.get("campaignId")
                response = requests.get(
                    f"{public_host}/campaigns/{campaignId}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "create_campaign":
                name = arguments.get("name")
                data = {
                    "name": name,
                }
                response = requests.post(
                    f"{public_host}/campaigns", headers=headers, json=data
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "update_campaign":
                campaignId = arguments.get("campaignId")
                name = arguments.get("name")
                stopOnEmailReplied = arguments.get("stopOnEmailReplied", False)
                stopOnMeetingBooked = arguments.get("stopOnMeetingBooked", False)
                stopOnLinkClicked = arguments.get("stopOnLinkClicked", False)
                stopOnLinkClickedFilter = arguments.get(
                    "stopOnLinkClickedFilter", False
                )
                leadsPausedByInterest = arguments.get("leadsPausedByInterest", False)
                opportunityReplied = arguments.get("opportunityReplied", False)
                opportunityClicked = arguments.get("opportunityClicked", False)
                autoLeadInterest = arguments.get("autoLeadInterest", False)
                sequenceSharing = arguments.get("sequenceSharing", False)
                disableTrackOpen = arguments.get("disableTrackOpen", False)
                disableTrackClick = arguments.get("disableTrackClick", False)
                disableTrackReply = arguments.get("disableTrackReply", False)

                data = {
                    "name": name,
                    "stopOnEmailReplied": stopOnEmailReplied,
                    "stopOnMeetingBooked": stopOnMeetingBooked,
                    "stopOnLinkClicked": stopOnLinkClicked,
                    "stopOnLinkClickedFilter": stopOnLinkClickedFilter,
                    "leadsPausedByInterest": leadsPausedByInterest,
                    "opportunityReplied": opportunityReplied,
                    "opportunityClicked": opportunityClicked,
                    "autoLeadInterest": autoLeadInterest,
                    "sequenceSharing": sequenceSharing,
                    "disableTrackOpen": disableTrackOpen,
                    "disableTrackClick": disableTrackClick,
                    "disableTrackReply": disableTrackReply,
                }

                response = requests.patch(
                    f"{public_host}/campaigns/{campaignId}", headers=headers, json=data
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "pause_lemlist_campaign":
                campaignId = arguments.get("campaignId")
                response = requests.post(
                    f"{public_host}/campaigns/{campaignId}/pause", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "start_lemlist_campaign_export":
                campaignId = arguments.get("campaignId")
                response = requests.get(
                    f"{public_host}/campaigns/{campaignId}/export/start",
                    headers=headers,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_campaign_export_status":
                campaignId = arguments.get("campaignId")
                exportId = arguments.get("exportId")
                response = requests.get(
                    f"{public_host}/campaigns/{campaignId}/export/{exportId}/status",
                    headers=headers,
                )

                if response.status_code == 200:
                    result = response.json()
                    url = result.get("status", {}).get("url", "URL not available")
                    result["csv_url"] = url
                    return [TextContent(type="text", text=json.dumps(result))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "export_lemlist_campaign":
                campaignId = arguments.get("campaignId")
                exportId = arguments.get("exportId")
                email = arguments.get("email")
                response = requests.put(
                    f"{public_host}/campaigns/{campaignId}/export/{exportId}/email/{email}",
                    headers=headers,
                    json={"email": email},
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_all_schedules":
                page = arguments.get("page", 1)
                offset = arguments.get("offset", 0)
                limit = arguments.get("limit", 100)
                sortBy = arguments.get("sortBy", "createdAt")
                sortOrder = arguments.get("sortOrder", "desc")

                response = requests.get(
                    f"{public_host}/schedules?page={page}&offset={offset}&limit={limit}&sortBy={sortBy}&sortOrder={sortOrder}",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    # If data contains a schedules array, return each schedule as a separate TextContent
                    if "schedules" in data and isinstance(data["schedules"], list):
                        return [
                            TextContent(type="text", text=json.dumps(item))
                            for item in data["schedules"]
                        ]
                    return [TextContent(type="text", text=json.dumps(data))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_schedule":
                scheduleId = arguments.get("scheduleId")
                response = requests.get(
                    f"{public_host}/schedules/{scheduleId}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_campaign_schedules":
                campaignId = arguments.get("campaignId")
                response = requests.get(
                    f"{public_host}/campaigns/{campaignId}/schedules", headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return [
                            TextContent(type="text", text=json.dumps(item))
                            for item in data
                        ]
                    return [TextContent(type="text", text=json.dumps(data))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "create_schedule":
                data = {}
                if "name" in arguments:
                    data["name"] = arguments.get("name", "Default schedule")
                if "secondsToWait" in arguments:
                    data["secondsToWait"] = arguments.get("secondsToWait", 1200)
                if "timezone" in arguments:
                    data["timezone"] = arguments.get("timezone", "Europe/Paris")
                if "start" in arguments:
                    data["start"] = arguments.get("start", "09:00")
                if "end" in arguments:
                    data["end"] = arguments.get("end", "18:00")
                if "weekdays" in arguments:
                    data["weekdays"] = arguments.get("weekdays", [1, 2, 3, 4, 5])
                response = requests.post(
                    f"{public_host}/schedules", headers=headers, json=data
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "update_schedule":
                scheduleId = arguments.get("scheduleId")
                data = {}
                if "name" in arguments:
                    data["name"] = arguments.get("name", "Default schedule")
                if "secondsToWait" in arguments:
                    data["secondsToWait"] = arguments.get("secondsToWait", 1200)
                if "timezone" in arguments:
                    data["timezone"] = arguments.get("timezone", "Europe/Paris")
                if "start" in arguments:
                    data["start"] = arguments.get("start", "09:00")
                if "end" in arguments:
                    data["end"] = arguments.get("end", "18:00")
                if "weekdays" in arguments:
                    data["weekdays"] = arguments.get("weekdays", [1, 2, 3, 4, 5])
                response = requests.patch(
                    f"{public_host}/schedules/{scheduleId}", headers=headers, json=data
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "delete_schedule":
                scheduleId = arguments.get("scheduleId")
                response = requests.delete(
                    f"{public_host}/schedules/{scheduleId}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "associate_schedule_with_campaign":
                scheduleId = arguments.get("scheduleId")
                campaignId = arguments.get("campaignId")
                response = requests.post(
                    f"{public_host}/campaigns/{campaignId}/schedules/{scheduleId}",
                    headers=headers,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "create_lead_in_campaign":
                campaignId = arguments.get("campaignId")
                email = arguments.get("email")
                firstName = arguments.get("firstName")
                lastName = arguments.get("lastName")
                companyName = arguments.get("companyName")
                icebreaker = arguments.get("icebreaker")
                phone = arguments.get("phone")
                linkedinUrl = arguments.get("linkedinUrl")
                companyDomain = arguments.get("companyDomain")

                data = {
                    "firstName": firstName,
                    "lastName": lastName,
                    "companyName": companyName,
                    "icebreaker": icebreaker,
                    "phone": phone,
                    "linkedinUrl": linkedinUrl,
                    "companyDomain": companyDomain,
                    "email": email,
                }

                response = requests.post(
                    f"{public_host}/campaigns/{campaignId}/leads/{email}?deduplicate=true",
                    headers=headers,
                    json=data,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "delete_lead":
                campaignId = arguments.get("campaignId")
                leadId = arguments.get("leadId")
                email = arguments.get("email")

                if not leadId and not email:
                    raise ValueError("Either 'leadId' or 'email' must be provided.")

                identifier = leadId if leadId else email
                response = requests.delete(
                    f"{public_host}/campaigns/{campaignId}/leads/{identifier}?action=remove",
                    headers=headers,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "mark_lead_as_interested_all_campaigns":
                email = arguments.get("email")
                response = requests.post(
                    f"{public_host}/leads/interested/{email}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "mark_lead_as_not_interested_all_campaigns":
                email = arguments.get("email")
                response = requests.post(
                    f"{public_host}/leads/notinterested/{email}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "mark_lead_as_interested_in_campaign":
                campaignId = arguments.get("campaignId")
                email = arguments.get("email")
                response = requests.post(
                    f"{public_host}/campaigns/{campaignId}/leads/{email}/interested",
                    headers=headers,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "mark_lead_as_not_interested_in_campaign":
                campaignId = arguments.get("campaignId")
                email = arguments.get("email")
                response = requests.post(
                    f"{public_host}/campaigns/{campaignId}/leads/{email}/notinterested",
                    headers=headers,
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "get_all_unsubscribes":
                offset = arguments.get("offset", 0)
                limit = arguments.get("limit", 5)

                response = requests.get(
                    f"{public_host}/unsubscribes?offset={offset}&limit={limit}",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return [
                            TextContent(type="text", text=json.dumps(item))
                            for item in data
                        ]
                    return [TextContent(type="text", text=json.dumps(data))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]
            elif name == "export_unsubscribes":
                response = requests.get(f"{public_host}/unsubs/export", headers=headers)
                if response.status_code == 200:
                    # For text response, wrap in JSON object
                    return [
                        TextContent(
                            type="text", text=json.dumps({"export_data": response.text})
                        )
                    ]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]

            elif name == "get_database_filters":
                response = requests.get(
                    f"{public_host}/database/filters", headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return [
                            TextContent(type="text", text=json.dumps(item))
                            for item in data
                        ]
                    return [TextContent(type="text", text=json.dumps(data))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]

            elif name == "add_unsubscribe":
                email = arguments.get("email")
                response = requests.post(
                    f"{public_host}/unsubscribes/{email}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]

            elif name == "delete_unsubscribe":
                email = arguments.get("email")
                response = requests.delete(
                    f"{public_host}/unsubscribes/{email}", headers=headers
                )

                if response.status_code == 200:
                    return [TextContent(type="text", text=json.dumps(response.json()))]
                else:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": response.text})
                        )
                    ]

            else:
                raise ValueError(f"Unkown tool: {name}")

        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="lemlist-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_lemlist_credentials(user_id)
    else:
        print("Usage:")
        print("  python main.py auth - Run authentication flow for a user")
