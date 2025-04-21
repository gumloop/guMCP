import os
import sys
import logging
import json
import time
import urllib.parse
from pathlib import Path
from typing import Optional

# ensure project root and src on PYTHONPATH
project_root = os.path.abspath(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
from src.utils.twilio.util import authenticate_and_save_credentials, get_credentials

SERVICE_NAME = Path(__file__).parent.name


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(SERVICE_NAME)


# Helper function to process Twilio resource objects
def process_resource(resource):
    if hasattr(resource, "_properties"):
        data = resource._properties
    else:
        # Get all attributes that don't start with underscore and aren't callable
        data = {
            k: v
            for k, v in vars(resource).items()
            if not k.startswith("_") and not callable(v)
        }

    # Convert datetime objects to strings
    for key, value in list(data.items()):
        if hasattr(value, "isoformat"):
            data[key] = value.isoformat()
        elif not isinstance(value, (str, int, float, bool, list, dict, type(None))):
            data[key] = str(value)

    return data


# Helper function to process a list of Twilio resources
def process_resource_list(resources):
    return [process_resource(r) for r in resources]


def create_twilio_client(creds: dict) -> Client:
    """
    Build a Twilio REST client from stored credentials.
    """
    return Client(creds["api_key_sid"], creds["api_key_secret"], creds["account_sid"])


def create_server(user_id: str, api_key: Optional[str] = None):
    server = Server("twilio-server")
    server.user_id = user_id
    server.api_key = api_key

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            # Messaging
            types.Tool(
                name="send_message",
                description="Send SMS/MMS/WhatsApp message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "from": {"type": "string"},
                        "body": {"type": "string"},
                        "media_url": {"type": "string"},
                        "channel": {"type": "string", "enum": ["sms", "whatsapp"]},
                    },
                    "required": ["to", "from"],
                },
            ),
            types.Tool(
                name="list_messages",
                description="List message history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {"type": "integer"},
                        "page_token": {"type": "string"},
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="fetch_message",
                description="Fetch a message by SID",
                inputSchema={
                    "type": "object",
                    "properties": {"message_sid": {"type": "string"}},
                    "required": ["message_sid"],
                },
            ),
            types.Tool(
                name="delete_message",
                description="Delete a message by SID",
                inputSchema={
                    "type": "object",
                    "properties": {"message_sid": {"type": "string"}},
                    "required": ["message_sid"],
                },
            ),
            # Voice
            types.Tool(
                name="make_call",
                description="Make an outbound voice call (provide either 'url' for TwiML or 'text' to speak)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "The phone number to call",
                        },
                        "from": {
                            "type": "string",
                            "description": "Your Twilio phone number",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to a TwiML document for call instructions",
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to say to the recipient (will be converted to TwiML)",
                        },
                    },
                    "required": ["to", "from"],
                },
            ),
            types.Tool(
                name="list_calls",
                description="List recent calls",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {"type": "integer"},
                        "page_token": {"type": "string"},
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="fetch_call",
                description="Fetch a call by SID",
                inputSchema={
                    "type": "object",
                    "properties": {"call_sid": {"type": "string"}},
                    "required": ["call_sid"],
                },
            ),
            # Verify
            types.Tool(
                name="list_verify_services",
                description="List all Twilio Verify services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "page_size": {
                            "type": "integer",
                            "description": "Number of services to return (optional)",
                        }
                    },
                    "required": [],
                },
            ),
            types.Tool(
                name="create_verify_service",
                description="Create a new Twilio Verify service",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "friendly_name": {
                            "type": "string",
                            "description": "Name for your Verify service",
                        },
                        "code_length": {
                            "type": "integer",
                            "description": "Length of verification codes (optional, default: 6)",
                        },
                        "lookup_enabled": {
                            "type": "boolean",
                            "description": "Enable phone number lookups (optional)",
                        },
                        "skip_sms_to_landlines": {
                            "type": "boolean",
                            "description": "Skip SMS to landlines (optional)",
                        },
                        "dtmf_input_required": {
                            "type": "boolean",
                            "description": "Require DTMF input for voice calls (optional)",
                        },
                    },
                    "required": ["friendly_name"],
                },
            ),
            types.Tool(
                name="start_verification",
                description="Start a Verify (OTP) request",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {
                            "type": "string",
                            "description": "Your Verify Service SID (starts with VA, find in Twilio Console under Verify > Services)",
                        },
                        "to": {
                            "type": "string",
                            "description": "Phone number to send verification code to",
                        },
                        "channel": {
                            "type": "string",
                            "description": "Verification channel (sms, call, email, etc.)",
                        },
                    },
                    "required": ["service_sid", "to", "channel"],
                },
            ),
            types.Tool(
                name="check_verification",
                description="Check a Verify code",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {
                            "type": "string",
                            "description": "Your Verify Service SID (starts with VA, find in Twilio Console under Verify > Services)",
                        },
                        "to": {
                            "type": "string",
                            "description": "Phone number the code was sent to",
                        },
                        "code": {
                            "type": "string",
                            "description": "Verification code entered by user",
                        },
                    },
                    "required": ["service_sid", "to", "code"],
                },
            ),
            # Lookup
            types.Tool(
                name="lookup_phone_number",
                description="Lookup phone number intelligence",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "phone_number": {"type": "string"},
                        "country_code": {"type": "string"},
                        "add_ons": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["phone_number"],
                },
            ),
            # Conversations
            types.Tool(
                name="list_conversation_services",
                description="List Conversation Services",
                inputSchema={
                    "type": "object",
                    "properties": {"page_size": {"type": "integer"}},
                    "required": [],
                },
            ),
            types.Tool(
                name="create_conversation_service",
                description="Create a Conversation Service",
                inputSchema={
                    "type": "object",
                    "properties": {"friendly_name": {"type": "string"}},
                    "required": ["friendly_name"],
                },
            ),
            types.Tool(
                name="list_conversations",
                description="List Conversations in a Service",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {"type": "string"},
                        "page_size": {"type": "integer"},
                    },
                    "required": ["service_sid"],
                },
            ),
            types.Tool(
                name="create_conversation",
                description="Create a Conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {"type": "string"},
                        "friendly_name": {"type": "string"},
                    },
                    "required": ["service_sid"],
                },
            ),
            types.Tool(
                name="add_conversation_participant",
                description="Add a Participant to a Conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {"type": "string"},
                        "conversation_sid": {"type": "string"},
                        "identity": {"type": "string"},
                    },
                    "required": ["conversation_sid", "identity"],
                },
            ),
            types.Tool(
                name="send_conversation_message",
                description="Send a Message in a Conversation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "service_sid": {"type": "string"},
                        "conversation_sid": {"type": "string"},
                        "body": {"type": "string"},
                    },
                    "required": ["conversation_sid", "body"],
                },
            ),
            # Video
            types.Tool(
                name="list_video_rooms",
                description="List Video Rooms",
                inputSchema={
                    "type": "object",
                    "properties": {"page_size": {"type": "integer"}},
                    "required": [],
                },
            ),
            types.Tool(
                name="create_video_room",
                description="Create a Video Room",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "unique_name": {"type": "string"},
                        "type": {"type": "string"},
                        "status_callback": {"type": "string"},
                    },
                    "required": ["unique_name"],
                },
            ),
            types.Tool(
                name="fetch_video_room",
                description="Fetch a Video Room",
                inputSchema={
                    "type": "object",
                    "properties": {"room_sid": {"type": "string"}},
                    "required": ["room_sid"],
                },
            ),
            types.Tool(
                name="complete_video_room",
                description="Complete (end) a Video Room",
                inputSchema={
                    "type": "object",
                    "properties": {"room_sid": {"type": "string"}},
                    "required": ["room_sid"],
                },
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None):
        logger.info(f"User {server.user_id} calling {name} with {arguments}")
        if arguments is None:
            arguments = {}

        # Load credentials & client
        creds = await get_credentials(server.user_id, SERVICE_NAME, server.api_key)
        client = create_twilio_client(creds)

        # 1. send_message
        if name == "send_message":
            msg = client.messages.create(
                to=arguments["to"],
                from_=arguments["from"],
                body=arguments.get("body"),
                media_url=(
                    [arguments["media_url"]] if arguments.get("media_url") else None
                ),
            )
            return [types.TextContent(type="text", text=str(process_resource(msg)))]

        # 2. list_messages
        if name == "list_messages":
            try:
                msgs = client.messages.list(page_size=arguments.get("page_size", 20))
                # Convert message objects to dictionaries in a way that works with the current Twilio SDK
                data = []
                for m in msgs:
                    # Try different approaches to get message data
                    try:
                        if hasattr(m, "_properties"):
                            msg_dict = m._properties
                        elif hasattr(m, "__dict__"):
                            # Filter out private attributes and functions
                            msg_dict = {
                                k: v
                                for k, v in vars(m).items()
                                if not k.startswith("_") and not callable(v)
                            }
                        else:
                            # Manually extract common message attributes
                            msg_dict = {
                                "sid": m.sid,
                                "date_created": (
                                    str(m.date_created)
                                    if hasattr(m, "date_created")
                                    else None
                                ),
                                "date_sent": (
                                    str(m.date_sent)
                                    if hasattr(m, "date_sent")
                                    else None
                                ),
                                "date_updated": (
                                    str(m.date_updated)
                                    if hasattr(m, "date_updated")
                                    else None
                                ),
                                "to": m.to if hasattr(m, "to") else None,
                                "from_": m.from_ if hasattr(m, "from_") else None,
                                "status": m.status if hasattr(m, "status") else None,
                                "body": m.body if hasattr(m, "body") else None,
                            }

                        # Convert any datetime objects to strings to make JSON serializable
                        for key, value in list(msg_dict.items()):
                            # Handle datetime objects
                            if hasattr(value, "isoformat"):
                                msg_dict[key] = value.isoformat()
                            # Handle other non-serializable objects
                            elif not isinstance(
                                value, (str, int, float, bool, list, dict, type(None))
                            ):
                                msg_dict[key] = str(value)

                        data.append(msg_dict)
                    except Exception as e:
                        # If all else fails, just include the SID
                        logger.warning(f"Error extracting message data: {e}")
                        data.append({"sid": m.sid if hasattr(m, "sid") else str(m)})

                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error listing messages: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error listing messages: {str(e)}"
                    )
                ]

        # 3. fetch_message
        if name == "fetch_message":
            try:
                m = client.messages(arguments["message_sid"]).fetch()

                # Extract message properties
                if hasattr(m, "_properties"):
                    msg_dict = m._properties
                else:
                    # Manually extract message attributes
                    msg_dict = {
                        "sid": m.sid,
                        "account_sid": (
                            m.account_sid if hasattr(m, "account_sid") else None
                        ),
                        "date_created": (
                            str(m.date_created) if hasattr(m, "date_created") else None
                        ),
                        "date_sent": (
                            str(m.date_sent) if hasattr(m, "date_sent") else None
                        ),
                        "date_updated": (
                            str(m.date_updated) if hasattr(m, "date_updated") else None
                        ),
                        "to": m.to if hasattr(m, "to") else None,
                        "from_": m.from_ if hasattr(m, "from_") else None,
                        "messaging_service_sid": (
                            m.messaging_service_sid
                            if hasattr(m, "messaging_service_sid")
                            else None
                        ),
                        "body": m.body if hasattr(m, "body") else None,
                        "status": m.status if hasattr(m, "status") else None,
                        "num_segments": (
                            m.num_segments if hasattr(m, "num_segments") else None
                        ),
                        "num_media": m.num_media if hasattr(m, "num_media") else None,
                        "direction": m.direction if hasattr(m, "direction") else None,
                        "api_version": (
                            m.api_version if hasattr(m, "api_version") else None
                        ),
                        "price": str(m.price) if hasattr(m, "price") else None,
                        "price_unit": (
                            m.price_unit if hasattr(m, "price_unit") else None
                        ),
                        "error_code": (
                            m.error_code if hasattr(m, "error_code") else None
                        ),
                        "error_message": (
                            m.error_message if hasattr(m, "error_message") else None
                        ),
                        "uri": m.uri if hasattr(m, "uri") else None,
                    }

                # Convert any datetime objects to strings to make JSON serializable
                for key, value in list(msg_dict.items()):
                    # Handle datetime objects
                    if hasattr(value, "isoformat"):
                        msg_dict[key] = value.isoformat()
                    # Handle other non-serializable objects
                    elif not isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        msg_dict[key] = str(value)

                return [
                    types.TextContent(type="text", text=json.dumps(msg_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error fetching message: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error fetching message: {str(e)}"
                    )
                ]

        # 4. delete_message
        if name == "delete_message":
            try:
                client.messages(arguments["message_sid"]).delete()
                return [
                    types.TextContent(type="text", text="Message deleted successfully")
                ]
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error deleting message: {str(e)}"
                    )
                ]

        # 5. make_call
        if name == "make_call":
            try:
                # Validate that either url or text is provided
                has_url = "url" in arguments and arguments["url"]
                has_text = "text" in arguments and arguments["text"]

                if not (has_url or has_text):
                    raise ValueError(
                        "You must provide either 'url' or 'text' parameter"
                    )

                # Check if the user provided a text message
                if has_text:
                    try:
                        # Create a TwiML response with the provided text
                        response = VoiceResponse()
                        response.say(arguments["text"])

                        # For simple TwiML, we can use the Twilio Functions API if available
                        # Otherwise, we'll fallback to creating a TwiML Bin
                        url = None

                        # Try to create a Twilio Function (if the API supports it)
                        try:
                            # This approach may not work with all Twilio accounts/plans
                            function = client.serverless.services.create(
                                unique_name=f"dynamic_twiml_{int(time.time())}"
                            )

                            # Create a function with the TwiML content
                            function_version = function.functions.create(
                                friendly_name="Dynamic Voice TwiML",
                                content=f"""
                                exports.handler = function(context, event, callback) {{
                                    const twiml = new Twilio.twiml.VoiceResponse();
                                    twiml.say('{arguments["text"]}');
                                    callback(null, twiml);
                                }};
                                """,
                            )

                            # Deploy the function
                            # Deployment is needed but we don't use the return value
                            function.deployments.create(
                                function_version=function_version.sid
                            )

                            # Get the function URL
                            url = f"https://{function.domain_name}/{function_version.path}"
                            logger.info(f"Created Twilio Function with URL: {url}")
                        except Exception as e:
                            logger.warning(f"Could not create Twilio Function: {e}")
                            url = None

                        # Fallback to TwiML Bins approach
                        if not url:
                            try:
                                # Different versions of the Twilio SDK might have different APIs
                                # for creating TwiML bins, so we'll try a few options
                                twiml_bin = None

                                # Try the new API
                                try:
                                    twiml_bin = client.twiml_bins.create(
                                        friendly_name=f"Dynamic Call TwiML {int(time.time())}",
                                        voice_method="GET",
                                        voice_twiml=str(response),
                                    )
                                except (AttributeError, TypeError) as e:
                                    logger.warning(f"Could not use twiml_bins API: {e}")

                                # Try the alternate API
                                if not twiml_bin:
                                    try:
                                        twiml_bin = client.applications.create(
                                            friendly_name=f"Dynamic Call TwiML {int(time.time())}",
                                            voice_method="GET",
                                            voice_url=None,
                                            voice_fallback_url=None,
                                            voice_application_sid=None,
                                            voice_twiml=str(response),
                                        )
                                    except (AttributeError, TypeError) as e:
                                        logger.warning(
                                            f"Could not use applications API: {e}"
                                        )

                                if twiml_bin:
                                    url = f"https://handler.twilio.com/twiml/{twiml_bin.sid}"
                                    logger.info(f"Created TwiML Bin with URL: {url}")
                                else:
                                    logger.warning(
                                        "Could not create TwiML Bin with any available API"
                                    )
                            except Exception as e:
                                logger.warning(f"Could not create TwiML Bin: {e}")

                        # If all else fails, create a simple URL with encoded TwiML
                        if not url:
                            # Encode the TwiML for direct use in URL
                            encoded_twiml = urllib.parse.quote(str(response))
                            url = f"https://twimlets.com/echo?Twiml={encoded_twiml}"
                            logger.info("Using Twimlets URL for TwiML")
                    except Exception as e:
                        logger.error(f"Error creating TwiML: {e}")
                        raise ValueError(f"Failed to create TwiML from text: {str(e)}")
                elif has_url:
                    url = arguments["url"]
                else:
                    # We should never get here due to the validation at the beginning
                    raise ValueError("Either 'url' or 'text' parameter is required")

                # Make the call with the URL
                call = client.calls.create(
                    to=arguments["to"], from_=arguments["from"], url=url
                )

                # Extract call properties using the process_resource helper
                call_dict = process_resource(call)

                return [
                    types.TextContent(type="text", text=json.dumps(call_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error making call: {e}")
                return [
                    types.TextContent(type="text", text=f"Error making call: {str(e)}")
                ]

        # 6. list_calls
        if name == "list_calls":
            try:
                calls = client.calls.list(page_size=arguments.get("page_size", 20))
                data = []
                for c in calls:
                    # Extract call properties
                    if hasattr(c, "_properties"):
                        call_dict = c._properties
                    else:
                        # Manually extract call attributes
                        call_dict = {
                            "sid": c.sid,
                            "date_created": (
                                str(c.date_created)
                                if hasattr(c, "date_created")
                                else None
                            ),
                            "date_updated": (
                                str(c.date_updated)
                                if hasattr(c, "date_updated")
                                else None
                            ),
                            "parent_call_sid": (
                                c.parent_call_sid
                                if hasattr(c, "parent_call_sid")
                                else None
                            ),
                            "account_sid": (
                                c.account_sid if hasattr(c, "account_sid") else None
                            ),
                            "to": c.to if hasattr(c, "to") else None,
                            "from_": c.from_ if hasattr(c, "from_") else None,
                            "status": c.status if hasattr(c, "status") else None,
                            "start_time": (
                                str(c.start_time)
                                if hasattr(c, "start_time") and c.start_time
                                else None
                            ),
                            "end_time": (
                                str(c.end_time)
                                if hasattr(c, "end_time") and c.end_time
                                else None
                            ),
                            "duration": c.duration if hasattr(c, "duration") else None,
                        }

                    # Convert any datetime objects to strings to make JSON serializable
                    for key, value in list(call_dict.items()):
                        # Handle datetime objects
                        if hasattr(value, "isoformat"):
                            call_dict[key] = value.isoformat()
                        # Handle other non-serializable objects
                        elif not isinstance(
                            value, (str, int, float, bool, list, dict, type(None))
                        ):
                            call_dict[key] = str(value)

                    data.append(call_dict)

                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error listing calls: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error listing calls: {str(e)}"
                    )
                ]

        # 7. fetch_call
        if name == "fetch_call":
            try:
                c = client.calls(arguments["call_sid"]).fetch()

                # Extract call properties
                if hasattr(c, "_properties"):
                    call_dict = c._properties
                else:
                    # Manually extract call attributes
                    call_dict = {
                        "sid": c.sid,
                        "date_created": (
                            str(c.date_created) if hasattr(c, "date_created") else None
                        ),
                        "date_updated": (
                            str(c.date_updated) if hasattr(c, "date_updated") else None
                        ),
                        "parent_call_sid": (
                            c.parent_call_sid if hasattr(c, "parent_call_sid") else None
                        ),
                        "account_sid": (
                            c.account_sid if hasattr(c, "account_sid") else None
                        ),
                        "to": c.to if hasattr(c, "to") else None,
                        "to_formatted": (
                            c.to_formatted if hasattr(c, "to_formatted") else None
                        ),
                        "from_": c.from_ if hasattr(c, "from_") else None,
                        "from_formatted": (
                            c.from_formatted if hasattr(c, "from_formatted") else None
                        ),
                        "status": c.status if hasattr(c, "status") else None,
                        "start_time": (
                            str(c.start_time)
                            if hasattr(c, "start_time") and c.start_time
                            else None
                        ),
                        "end_time": (
                            str(c.end_time)
                            if hasattr(c, "end_time") and c.end_time
                            else None
                        ),
                        "duration": c.duration if hasattr(c, "duration") else None,
                        "price": str(c.price) if hasattr(c, "price") else None,
                        "direction": c.direction if hasattr(c, "direction") else None,
                    }

                # Convert any datetime objects to strings to make JSON serializable
                for key, value in list(call_dict.items()):
                    # Handle datetime objects
                    if hasattr(value, "isoformat"):
                        call_dict[key] = value.isoformat()
                    # Handle other non-serializable objects
                    elif not isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        call_dict[key] = str(value)

                return [
                    types.TextContent(type="text", text=json.dumps(call_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error fetching call: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error fetching call: {str(e)}"
                    )
                ]

        # 8. list_verify_services
        if name == "list_verify_services":
            try:
                # Get list of services
                services = client.verify.services.list(
                    limit=arguments.get("page_size", 20)
                )

                # Process the services
                services_list = process_resource_list(services)

                # Add a helpful message
                result = {
                    "services": services_list,
                    "count": len(services_list),
                    "_helpMessage": "Use the service SID (starts with VA) with the start_verification and check_verification tools.",
                }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error listing Verify services: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error listing Verify services: {str(e)}"
                    )
                ]

        # 9. create_verify_service
        if name == "create_verify_service":
            try:
                # Prepare optional parameters
                kwargs = {"friendly_name": arguments["friendly_name"]}

                # Add optional parameters if provided
                if "code_length" in arguments:
                    kwargs["code_length"] = arguments["code_length"]
                if "lookup_enabled" in arguments:
                    kwargs["lookup_enabled"] = arguments["lookup_enabled"]
                if "skip_sms_to_landlines" in arguments:
                    kwargs["skip_sms_to_landlines"] = arguments["skip_sms_to_landlines"]
                if "dtmf_input_required" in arguments:
                    kwargs["dtmf_input_required"] = arguments["dtmf_input_required"]

                # Create the service
                service = client.verify.services.create(**kwargs)

                # Extract service properties
                service_dict = process_resource(service)

                # Add a helpful message
                service_dict["_helpMessage"] = (
                    f"Your new Verify Service SID is {service.sid}. Use this SID with the start_verification and check_verification tools."
                )

                return [
                    types.TextContent(
                        type="text", text=json.dumps(service_dict, indent=2)
                    )
                ]
            except Exception as e:
                logger.error(f"Error creating Verify service: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error creating Verify service: {str(e)}"
                    )
                ]

        # 10. start_verification
        if name == "start_verification":
            try:
                v = client.verify.services(
                    arguments["service_sid"]
                ).verifications.create(to=arguments["to"], channel=arguments["channel"])

                # Extract verification properties
                if hasattr(v, "_properties"):
                    v_dict = v._properties
                else:
                    # Manually extract verification attributes
                    v_dict = {
                        "sid": v.sid if hasattr(v, "sid") else None,
                        "service_sid": (
                            v.service_sid if hasattr(v, "service_sid") else None
                        ),
                        "account_sid": (
                            v.account_sid if hasattr(v, "account_sid") else None
                        ),
                        "to": v.to if hasattr(v, "to") else None,
                        "channel": v.channel if hasattr(v, "channel") else None,
                        "status": v.status if hasattr(v, "status") else None,
                        "valid": v.valid if hasattr(v, "valid") else None,
                        "date_created": (
                            str(v.date_created) if hasattr(v, "date_created") else None
                        ),
                        "date_updated": (
                            str(v.date_updated) if hasattr(v, "date_updated") else None
                        ),
                    }

                # Convert any datetime objects to strings
                for key, value in list(v_dict.items()):
                    if hasattr(value, "isoformat"):
                        v_dict[key] = value.isoformat()
                    elif not isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        v_dict[key] = str(value)

                return [
                    types.TextContent(type="text", text=json.dumps(v_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error starting verification: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error starting verification: {str(e)}"
                    )
                ]

        # 11. check_verification
        if name == "check_verification":
            try:
                chk = client.verify.services(
                    arguments["service_sid"]
                ).verification_checks.create(to=arguments["to"], code=arguments["code"])

                # Extract verification check properties
                if hasattr(chk, "_properties"):
                    chk_dict = chk._properties
                else:
                    # Manually extract verification check attributes
                    chk_dict = {
                        "sid": chk.sid if hasattr(chk, "sid") else None,
                        "service_sid": (
                            chk.service_sid if hasattr(chk, "service_sid") else None
                        ),
                        "account_sid": (
                            chk.account_sid if hasattr(chk, "account_sid") else None
                        ),
                        "to": chk.to if hasattr(chk, "to") else None,
                        "status": chk.status if hasattr(chk, "status") else None,
                        "valid": chk.valid if hasattr(chk, "valid") else None,
                        "date_created": (
                            str(chk.date_created)
                            if hasattr(chk, "date_created")
                            else None
                        ),
                        "date_updated": (
                            str(chk.date_updated)
                            if hasattr(chk, "date_updated")
                            else None
                        ),
                    }

                # Convert any datetime objects to strings
                for key, value in list(chk_dict.items()):
                    if hasattr(value, "isoformat"):
                        chk_dict[key] = value.isoformat()
                    elif not isinstance(
                        value, (str, int, float, bool, list, dict, type(None))
                    ):
                        chk_dict[key] = str(value)

                return [
                    types.TextContent(type="text", text=json.dumps(chk_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error checking verification: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error checking verification: {str(e)}"
                    )
                ]

        # 12. lookup_phone_number
        if name == "lookup_phone_number":
            try:
                num = client.lookups.phone_numbers(arguments["phone_number"]).fetch(
                    country_code=arguments.get("country_code"),
                    type=arguments.get("add_ons") and ["carrier"],
                )

                # Extract phone number lookup properties
                if hasattr(num, "_properties"):
                    num_dict = num._properties
                else:
                    # Manually extract phone number lookup attributes
                    num_dict = {
                        "phone_number": (
                            num.phone_number if hasattr(num, "phone_number") else None
                        ),
                        "national_format": (
                            num.national_format
                            if hasattr(num, "national_format")
                            else None
                        ),
                        "country_code": (
                            num.country_code if hasattr(num, "country_code") else None
                        ),
                        "carrier": num.carrier if hasattr(num, "carrier") else None,
                        "add_ons": num.add_ons if hasattr(num, "add_ons") else None,
                    }

                return [
                    types.TextContent(type="text", text=json.dumps(num_dict, indent=2))
                ]
            except Exception as e:
                logger.error(f"Error looking up phone number: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error looking up phone number: {str(e)}"
                    )
                ]

        # 13–16. Conversations
        if name == "list_conversation_services":
            try:
                svcs = client.conversations.services.list(
                    limit=arguments.get("page_size", 20)
                )
                data = process_resource_list(svcs)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error listing conversation services: {e}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error listing conversation services: {str(e)}",
                    )
                ]

        if name == "create_conversation_service":
            try:
                s = client.conversations.services.create(
                    friendly_name=arguments["friendly_name"]
                )
                data = process_resource(s)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error creating conversation service: {e}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error creating conversation service: {str(e)}",
                    )
                ]

        if name == "list_conversations":
            try:
                convs = client.conversations.services(
                    arguments["service_sid"]
                ).conversations.list(limit=arguments.get("page_size", 20))
                data = process_resource_list(convs)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error listing conversations: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error listing conversations: {str(e)}"
                    )
                ]

        if name == "create_conversation":
            try:
                c = client.conversations.services(
                    arguments["service_sid"]
                ).conversations.create(friendly_name=arguments.get("friendly_name", ""))
                data = process_resource(c)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error creating conversation: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error creating conversation: {str(e)}"
                    )
                ]
        if name == "add_conversation_participant":
            try:
                service_sid = arguments["service_sid"]
                conversation_sid = arguments["conversation_sid"]
                identity = arguments["identity"]

                participant = (
                    client.conversations.services(service_sid)
                    .conversations(conversation_sid)
                    .participants.create(identity=identity)
                )

                data = process_resource(participant)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error adding participant: {e}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error adding participant: {str(e)}",
                    )
                ]

        if name == "send_conversation_message":
            try:
                service_sid = arguments["service_sid"]
                conversation_sid = arguments["conversation_sid"]
                body = arguments["body"]

                message = (
                    client.conversations.services(service_sid)
                    .conversations(conversation_sid)
                    .messages.create(body=body)
                )

                data = process_resource(message)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error sending conversation message: {e}")
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error sending conversation message: {str(e)}",
                    )
                ]

        # 17–19. Video
        if name == "list_video_rooms":
            try:
                rooms = client.video.rooms.list(limit=arguments.get("page_size", 20))
                data = process_resource_list(rooms)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error listing video rooms: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error listing video rooms: {str(e)}"
                    )
                ]

        if name == "create_video_room":
            try:
                r = client.video.rooms.create(
                    unique_name=arguments["unique_name"],
                    type=arguments.get("type"),
                    status_callback=arguments.get("status_callback"),
                )
                data = process_resource(r)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error creating video room: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error creating video room: {str(e)}"
                    )
                ]

        if name == "fetch_video_room":
            try:
                r = client.video.rooms(arguments["room_sid"]).fetch()
                data = process_resource(r)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error fetching video room: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error fetching video room: {str(e)}"
                    )
                ]

        if name == "complete_video_room":
            try:
                r = client.video.rooms(arguments["room_sid"]).update(status="completed")
                data = process_resource(r)
                return [types.TextContent(type="text", text=json.dumps(data, indent=2))]
            except Exception as e:
                logger.error(f"Error completing video room: {e}")
                return [
                    types.TextContent(
                        type="text", text=f"Error completing video room: {str(e)}"
                    )
                ]

        raise ValueError(f"Unknown tool: {name}")

    return server


server = create_server


def get_initialization_options(server_instance: Server) -> InitializationOptions:
    return InitializationOptions(
        server_name="twilio-server",
        server_version="1.0.0",
        capabilities=server_instance.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() == "auth":
        user_id = "local"
        authenticate_and_save_credentials(user_id, SERVICE_NAME)
        print(
            f"Authentication complete for {user_id}. You can now run the Twilio server."
        )
    else:
        print("Usage:")
        print(
            "  python main.py auth    # Run authentication flow to enter and save Twilio credentials"
        )
        print("Note: To run the server normally, use the guMCP server framework.")
