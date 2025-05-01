import os
import sys
import logging
import json
from pathlib import Path

# Add both project root and src directory to Python path
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from typing import Optional, Iterable
from mcp.types import Resource
from pydantic import AnyUrl

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.lowlevel.helper_types import ReadResourceContents


from src.utils.google.util import authenticate_and_save_credentials
from src.auth.factory import create_auth_client

SERVICE_NAME = Path(__file__).parent.name
SCOPES = [
    "https://www.googleapis.com/auth/forms",
    "https://www.googleapis.com/auth/forms.body",
    "https://www.googleapis.com/auth/forms.responses.readonly",
    "https://www.googleapis.com/auth/drive",
]

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gforms-server")


async def get_credentials(user_id, api_key=None):
    """Get stored or active credentials for Google Forms API."""
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


async def create_forms_service(user_id, api_key=None):
    """Create an authorized Google Forms API service."""
    credentials = await get_credentials(user_id, api_key=api_key)
    return build("forms", "v1", credentials=credentials)


async def create_drive_service(user_id, api_key=None):
    """Create an authorized Google Drive API service."""
    credentials = await get_credentials(user_id, api_key=api_key)
    return build("drive", "v3", credentials=credentials)


def create_server(user_id, api_key=None):
    server = Server("gforms-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_resources()
    async def handle_list_resources(
        cursor: Optional[str] = None,
    ) -> list[Resource]:
        """List Google Forms resources (forms)"""
        logger.info(
            f"Listing resources for user: {server.user_id} with cursor: {cursor}"
        )

        drive_service = await create_drive_service(server.user_id, server.api_key)
        try:
            resources = []

            # List all forms
            results = (
                drive_service.files()
                .list(
                    q="mimeType='application/vnd.google-apps.form'",
                    fields="files(id, name)",
                )
                .execute()
            )

            for form in results.get("files", []):
                resources.append(
                    Resource(
                        uri=f"gforms://form/{form['id']}",
                        mimeType="application/json",
                        name=f"Form: {form['name']}",
                        description="Google Form",
                    )
                )

            return resources

        except Exception as e:
            logger.error(f"Error listing Google Forms resources: {e}")
            return []

    @server.read_resource()
    async def handle_read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        """Read a resource from Google Forms by URI"""
        logger.info(f"Reading resource: {uri} for user: {server.user_id}")

        forms_service = await create_forms_service(server.user_id, server.api_key)
        try:
            uri_str = str(uri)

            if uri_str.startswith("gforms://form/"):
                # Handle form resource
                form_id = uri_str.replace("gforms://form/", "")
                form_data = forms_service.forms().get(formId=form_id).execute()
                return [
                    ReadResourceContents(
                        content=json.dumps(form_data, indent=2),
                        mime_type="application/json",
                    )
                ]

            raise ValueError(f"Unsupported resource URI: {uri_str}")

        except Exception as e:
            logger.error(f"Error reading Google Forms resource: {e}")
            return [
                ReadResourceContents(
                    content=json.dumps({"error": str(e)}),
                    mime_type="application/json",
                )
            ]

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        """Register all supported tools for Google Forms."""
        return [
            types.Tool(
                name="list_forms",
                description="List all forms.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                            },
                        }
                    },
                    "description": "List of Google Forms with their IDs and names",
                    "examples": [
                        '{"files": [{"id": "1hkvi6cSnDrHx7V", "name": "test_form_aea1"}]}'
                    ],
                },
            ),
            types.Tool(
                name="create_form",
                description="Creates a new form.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the form",
                        },
                        "description": {
                            "type": "string",
                            "description": "Optional description for the form",
                        },
                        "is_public": {
                            "type": "boolean",
                            "description": "Whether to make the form public (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["title"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {"type": "string"},
                        "response_url": {"type": "string"},
                        "edit_url": {"type": "string"},
                        "title": {"type": "string"},
                    },
                    "description": "Details of the created form including URLs",
                    "examples": [
                        '{"form_id": "YT4KTB4UlZWM", "response_url": "https://docs.google.com/forms/d/e/dhshgoasghad/viewform", "edit_url": "https://docs.google.com/forms/d/YT4KTB4UlZWM/edit", "title": "test_form_8eb8"}'
                    ],
                },
            ),
            types.Tool(
                name="get_form",
                description="Retrieves an existing form by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form to retrieve",
                        }
                    },
                    "required": ["form_id"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "formId": {"type": "string"},
                        "info": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "documentTitle": {"type": "string"},
                            },
                        },
                        "settings": {
                            "type": "object",
                            "properties": {
                                "quizSettings": {"type": "object"},
                                "emailCollectionType": {"type": "string"},
                            },
                        },
                        "revisionId": {"type": "string"},
                        "responderUri": {"type": "string"},
                        "publishSettings": {
                            "type": "object",
                            "properties": {
                                "publishState": {
                                    "type": "object",
                                    "properties": {
                                        "isPublished": {"type": "boolean"},
                                        "isAcceptingResponses": {"type": "boolean"},
                                    },
                                }
                            },
                        },
                    },
                    "description": "Complete form details including settings and publish state",
                    "examples": [
                        '{"formId": "Q4Ph8GrQZPWlYvWNtVMI8LSKObpw", "info": {"title": "test_form_aea1", "documentTitle": "test_form_aea1"}, "settings": {"quizSettings": {}, "emailCollectionType": "DO_NOT_COLLECT"}, "revisionId": "00000004", "responderUri": "https://docs.google.com/forms/d/e/dshgsdbg/viewform", "publishSettings": {"publishState": {"isPublished": true, "isAcceptingResponses": true}}}'
                    ],
                },
            ),
            types.Tool(
                name="update_form",
                description="Updates an existing form by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form to update",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description for the form",
                        },
                        "is_public": {
                            "type": "boolean",
                            "description": "Whether to make the form public (default: false)",
                            "default": False,
                        },
                    },
                    "required": ["form_id"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {"type": "string"},
                        "response_url": {"type": "string"},
                        "edit_url": {"type": "string"},
                        "result": {
                            "type": "object",
                            "properties": {
                                "formId": {"type": "string"},
                                "info": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "documentTitle": {"type": "string"},
                                    },
                                },
                                "settings": {
                                    "type": "object",
                                    "properties": {
                                        "quizSettings": {"type": "object"},
                                        "emailCollectionType": {"type": "string"},
                                    },
                                },
                                "revisionId": {"type": "string"},
                                "responderUri": {"type": "string"},
                                "publishSettings": {
                                    "type": "object",
                                    "properties": {
                                        "publishState": {
                                            "type": "object",
                                            "properties": {
                                                "isPublished": {"type": "boolean"},
                                                "isAcceptingResponses": {
                                                    "type": "boolean"
                                                },
                                            },
                                        }
                                    },
                                },
                            },
                        },
                    },
                    "description": "Updated form details including URLs and complete form information",
                    "examples": [
                        '{"form_id": "1hkvi6cSnDrHx7V", "response_url": "https://docs.google.com/forms/d/e/shfdsogsdog/viewform", "edit_url": "https://docs.google.com/forms/d/1hkvi6cSnDrHx7V/edit", "result": {"formId": "1hkvi6cSnDrHx7V", "info": {"title": "test_form_aea1", "description": "Updated description for test form", "documentTitle": "test_form_aea1"}, "settings": {"quizSettings": {}, "emailCollectionType": "DO_NOT_COLLECT"}, "revisionId": "00000006", "responderUri": "https://docs.google.com/forms/d/e/abjsflbf/viewform", "publishSettings": {"publishState": {"isPublished": true, "isAcceptingResponses": true}}}}'
                    ],
                },
            ),
            types.Tool(
                name="move_form_to_trash",
                description="Removes a form and moves it to trash.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form to move to trash",
                        }
                    },
                    "required": ["form_id"],
                },
                outputSchema={
                    "type": "string",
                    "description": "ID of the form that was moved to trash",
                    "examples": ['"1hkvi6cSnDrHx7V-Q4Ph8GrQZPWlYvWNtVMI8LSKObpw"'],
                },
            ),
            types.Tool(
                name="get_response",
                description="Retrieves the details of a response by its ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form",
                        },
                        "response_id": {
                            "type": "string",
                            "description": "ID of the response to retrieve",
                        },
                    },
                    "required": ["form_id", "response_id"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "formId": {"type": "string"},
                        "responseId": {"type": "string"},
                        "createTime": {"type": "string"},
                        "lastSubmittedTime": {"type": "string"},
                        "answers": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "object",
                                "properties": {
                                    "questionId": {"type": "string"},
                                    "textAnswers": {
                                        "type": "object",
                                        "properties": {
                                            "answers": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "value": {"type": "string"}
                                                    },
                                                },
                                            }
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "description": "Response details including answers and timestamps",
                    "examples": [
                        '{"formId": "L6vO7Mho-_yWqNWPhCU", "responseId": "Slv9FN6UMf9TFk4", "createTime": "2025-04-30T20:59:39.526Z", "lastSubmittedTime": "2025-04-30T20:59:39.526237Z", "answers": {"40a835f6": {"questionId": "40a835f6", "textAnswers": {"answers": [{"value": "HI"}]}}}}'
                    ],
                },
            ),
            types.Tool(
                name="list_responses",
                description="Retrieves a list of responses.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form",
                        },
                        "page_size": {
                            "type": "integer",
                            "description": "Number of responses to return (max 100)",
                        },
                        "page_token": {
                            "type": "string",
                            "description": "Token for pagination",
                        },
                    },
                    "required": ["form_id"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "responses": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "responseId": {"type": "string"},
                                    "createTime": {"type": "string"},
                                    "lastSubmittedTime": {"type": "string"},
                                    "answers": {
                                        "type": "object",
                                        "additionalProperties": {
                                            "type": "object",
                                            "properties": {
                                                "questionId": {"type": "string"},
                                                "textAnswers": {
                                                    "type": "object",
                                                    "properties": {
                                                        "answers": {
                                                            "type": "array",
                                                            "items": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "value": {
                                                                        "type": "string"
                                                                    }
                                                                },
                                                            },
                                                        }
                                                    },
                                                },
                                            },
                                        },
                                    },
                                },
                            },
                        }
                    },
                    "description": "List of form responses with their answers",
                    "examples": [
                        '{"responses": [{"responseId": "Slv9FN6UMf9TFk4", "createTime": "2025-04-30T20:59:39.526Z", "lastSubmittedTime": "2025-04-30T20:59:39.526237Z", "answers": {"40a835f6": {"questionId": "40a835f6", "textAnswers": {"answers": [{"value": "HI"}]}}}}]}'
                    ],
                },
            ),
            types.Tool(
                name="search_forms",
                description="Retrieves a list of forms by name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query to filter forms",
                        },
                    },
                    "required": ["query"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "name": {"type": "string"},
                                },
                            },
                        }
                    },
                    "description": "List of matching forms with their IDs and names",
                    "examples": [
                        '{"files": [{"id": "YT4KTB4UlZWM", "name": "test_form_8eb8"}]}'
                    ],
                },
            ),
            types.Tool(
                name="add_question",
                description="Add a question to an existing Google Form.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form to add the question to",
                        },
                        "question_type": {
                            "type": "string",
                            "description": "Type of question (text, paragraph, multiple_choice, checkbox)",
                            "enum": [
                                "text",
                                "paragraph",
                                "multiple_choice",
                                "checkbox",
                            ],
                        },
                        "title": {
                            "type": "string",
                            "description": "Question title/text",
                        },
                        "options": {
                            "type": "array",
                            "description": "List of options for multiple choice/checkbox questions",
                            "items": {"type": "string"},
                        },
                        "required": {
                            "type": "boolean",
                            "description": "Whether the question is required",
                            "default": False,
                        },
                    },
                    "required": ["form_id", "question_type", "title"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "replies": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "createItem": {
                                        "type": "object",
                                        "properties": {
                                            "itemId": {"type": "string"},
                                            "questionId": {
                                                "type": "array",
                                                "items": {"type": "string"},
                                            },
                                        },
                                    }
                                },
                            },
                        },
                        "writeControl": {
                            "type": "object",
                            "properties": {"requiredRevisionId": {"type": "string"}},
                        },
                    },
                    "description": "Result of adding the question including item and question IDs",
                    "examples": [
                        '{"replies": [{"createItem": {"itemId": "2fb38c9f", "questionId": ["56a918aa"]}}], "writeControl": {"requiredRevisionId": "00000006"}}'
                    ],
                },
            ),
            types.Tool(
                name="delete_item",
                description="Deletes an item (question) from an existing Google Form.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "ID of the form to delete the question from",
                        },
                        "item_id": {
                            "type": "string",
                            "description": "ID of the question item to delete",
                        },
                    },
                    "required": ["form_id", "item_id"],
                },
                outputSchema={
                    "type": "object",
                    "properties": {
                        "replies": {"type": "array", "items": {"type": "object"}},
                        "writeControl": {
                            "type": "object",
                            "properties": {"requiredRevisionId": {"type": "string"}},
                        },
                    },
                    "description": "Result of deleting the question item",
                    "examples": [
                        '{"replies": [{}], "writeControl": {"requiredRevisionId": "00000007"}}'
                    ],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(
            f"User {server.user_id} calling tool: {name} with arguments: {arguments}"
        )
        forms_service = await create_forms_service(server.user_id, server.api_key)

        if arguments is None:
            arguments = {}

        try:
            if name == "list_forms":
                drive_service = await create_drive_service(
                    server.user_id, server.api_key
                )
                results = (
                    drive_service.files()
                    .list(
                        q="mimeType='application/vnd.google-apps.form'",
                        fields="files(id, name)",
                    )
                    .execute()
                )
                files = results.get("files", [])
                return [
                    types.TextContent(type="text", text=json.dumps(file, indent=2))
                    for file in files
                ]
            elif name == "create_form":
                # Create basic form
                form_body = {
                    "info": {
                        "title": arguments["title"],
                        "documentTitle": arguments["title"],
                    }
                }

                # Create form
                form = forms_service.forms().create(body=form_body).execute()
                form_id = form["formId"]

                # If description is provided, update the form
                if "description" in arguments and arguments["description"]:
                    update_body = {
                        "requests": [
                            {
                                "updateFormInfo": {
                                    "info": {"description": arguments["description"]},
                                    "updateMask": "description",
                                }
                            }
                        ]
                    }
                    forms_service.forms().batchUpdate(
                        formId=form_id, body=update_body
                    ).execute()

                # Update form settings to make it public and collectable
                settings_body = {
                    "requests": [
                        {
                            "updateSettings": {
                                "settings": {"quizSettings": {"isQuiz": False}},
                                "updateMask": "quizSettings.isQuiz",
                            }
                        }
                    ]
                }
                forms_service.forms().batchUpdate(
                    formId=form_id, body=settings_body
                ).execute()

                # Make the form public via Drive API if is_public is True (default)
                if arguments.get("is_public", False):
                    drive_service = await create_drive_service(
                        server.user_id, server.api_key
                    )

                    # Set public permission
                    permission = {
                        "type": "anyone",
                        "role": "reader",
                        "allowFileDiscovery": True,
                    }
                    drive_service.permissions().create(
                        fileId=form_id,
                        body=permission,
                        fields="id",
                        sendNotificationEmail=False,
                    ).execute()

                # Get the form URLs
                edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
                response_url = form.get(
                    "responderUri",
                    f"https://docs.google.com/forms/d/e/{form_id}/viewform",
                )

                result = {
                    "form_id": form_id,
                    "response_url": response_url,
                    "edit_url": edit_url,
                    "title": arguments["title"],
                }
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            elif name == "get_form":
                result = (
                    forms_service.forms().get(formId=arguments["form_id"]).execute()
                )
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            elif name == "update_form":
                form_id = arguments["form_id"]

                if "description" in arguments and arguments["description"]:
                    update_body = {
                        "requests": [
                            {
                                "updateFormInfo": {
                                    "info": {"description": arguments["description"]},
                                    "updateMask": "description",
                                }
                            }
                        ]
                    }
                    forms_service.forms().batchUpdate(
                        formId=form_id, body=update_body
                    ).execute()

                # Update form settings to make it public and collectable
                settings_body = {
                    "requests": [
                        {
                            "updateSettings": {
                                "settings": {"quizSettings": {"isQuiz": False}},
                                "updateMask": "quizSettings.isQuiz",
                            }
                        }
                    ]
                }
                forms_service.forms().batchUpdate(
                    formId=form_id, body=settings_body
                ).execute()

                if "is_public" in arguments:
                    drive_service = await create_drive_service(
                        server.user_id, server.api_key
                    )

                    # Set public permission
                    permission = {
                        "type": "anyone",
                        "role": "reader",
                        "allowFileDiscovery": True,
                    }
                    drive_service.permissions().create(
                        fileId=form_id,
                        body=permission,
                        fields="id",
                        sendNotificationEmail=False,
                    ).execute()

                edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
                form = forms_service.forms().get(formId=form_id).execute()
                response_url = form.get(
                    "responderUri",
                    f"https://docs.google.com/forms/d/e/{form_id}/viewform",
                )

                result = {
                    "form_id": form_id,
                    "response_url": response_url,
                    "edit_url": edit_url,
                    "result": form,
                }
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            elif name == "move_form_to_trash":
                form_id = arguments["form_id"]
                drive_service = await create_drive_service(
                    server.user_id, server.api_key
                )
                result = (
                    drive_service.files()
                    .update(fileId=form_id, body={"trashed": True})
                    .execute()
                )
                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps(result.get("id", form_id), indent=2),
                    )
                ]
            elif name == "get_response":
                result = (
                    forms_service.forms()
                    .responses()
                    .get(
                        formId=arguments["form_id"], responseId=arguments["response_id"]
                    )
                    .execute()
                )
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            elif name == "list_responses":
                params = {"formId": arguments["form_id"]}
                if "page_size" in arguments:
                    params["pageSize"] = min(arguments["page_size"], 100)
                if "page_token" in arguments:
                    params["pageToken"] = arguments["page_token"]

                result = forms_service.forms().responses().list(**params).execute()
                responses = result.get("responses", [])
                return [
                    types.TextContent(type="text", text=json.dumps(response, indent=2))
                    for response in responses
                ]
            elif name == "search_forms":
                drive_service = await create_drive_service(
                    server.user_id, server.api_key
                )
                query = f"mimeType='application/vnd.google-apps.form' and name contains '{arguments['query']}'"
                result = (
                    drive_service.files()
                    .list(q=query, fields="files(id, name)")
                    .execute()
                )
                files = result.get("files", [])
                return [
                    types.TextContent(type="text", text=json.dumps(file, indent=2))
                    for file in files
                ]
            elif name == "add_question":
                form_id = arguments["form_id"]
                question_type = arguments["question_type"]
                title = arguments["title"]
                options = arguments.get("options", [])
                required = arguments.get("required", False)

                # Get the current form
                form = forms_service.forms().get(formId=form_id).execute()

                # Determine the item ID for the new question
                item_id = len(form.get("items", []))

                # Create base request
                request = {
                    "requests": [
                        {
                            "createItem": {
                                "item": {
                                    "title": title,
                                    "questionItem": {
                                        "question": {"required": required}
                                    },
                                },
                                "location": {"index": item_id},
                            }
                        }
                    ]
                }

                # Set up question type specific configuration
                if question_type == "text":
                    request["requests"][0]["createItem"]["item"]["questionItem"][
                        "question"
                    ]["textQuestion"] = {}

                elif question_type == "paragraph":
                    request["requests"][0]["createItem"]["item"]["questionItem"][
                        "question"
                    ]["textQuestion"] = {"paragraph": True}

                elif question_type == "multiple_choice" and options:
                    choices = [{"value": option} for option in options]
                    request["requests"][0]["createItem"]["item"]["questionItem"][
                        "question"
                    ]["choiceQuestion"] = {
                        "type": "RADIO",
                        "options": choices,
                        "shuffle": False,
                    }

                elif question_type == "checkbox" and options:
                    choices = [{"value": option} for option in options]
                    request["requests"][0]["createItem"]["item"]["questionItem"][
                        "question"
                    ]["choiceQuestion"] = {
                        "type": "CHECKBOX",
                        "options": choices,
                        "shuffle": False,
                    }

                # Execute the request
                result = (
                    forms_service.forms()
                    .batchUpdate(formId=form_id, body=request)
                    .execute()
                )
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            elif name == "delete_item":
                form_id = arguments["form_id"]
                item_id = arguments["item_id"]

                form = forms_service.forms().get(formId=form_id).execute()

                item_index = None
                for i, item in enumerate(form.get("items", [])):
                    if item.get("itemId") == item_id:
                        item_index = i
                        break
                if item_index is None:
                    raise ValueError(f"Item with ID {item_id} not found in the form.")

                request_body = {
                    "requests": [{"deleteItem": {"location": {"index": item_index}}}]
                }

                result = (
                    forms_service.forms()
                    .batchUpdate(formId=form_id, body=request_body)
                    .execute()
                )
                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            else:
                raise ValueError(f"Unknown tool: {name}")

        except Exception as e:
            logger.error(f"Error calling Google Forms API: {e}")
            return [types.TextContent(type="text", text=str(e))]

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="gforms-server",
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
