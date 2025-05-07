import uuid
import pytest
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


template_name = f"test_template_{str(uuid.uuid4())[:4]}"
phone_number = ""  # TODO: Add a valid phone number


TOOL_TESTS = [
    {
        "name": "get_account_info",
        "args_template": "",
        "expected_keywords": ["id", "name"],
        "regex_extractors": {
            "waba_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "waba_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "get WhatsApp Business Account information",
    },
    {
        "name": "get_account_verification_status",
        "args_template": "",
        "expected_keywords": ["business_verification_status"],
        "regex_extractors": {
            "verification_status": r'"?business_verification_status"?[:\s]+"?([^"]+)"?',
        },
        "description": "get business verification status",
    },
    {
        "name": "list_phone_numbers",
        "args_template": "",
        "expected_keywords": ["phone_numbers"],
        "regex_extractors": {
            "phone_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "phone_number": r'"?display_phone_number"?[:\s]+"?([^"]+)"?',
        },
        "description": "list all phone numbers associated with the WABA",
    },
    {
        "name": "list_message_templates",
        "args_template": "",
        "expected_keywords": ["templates"],
        "regex_extractors": {
            "template_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "template_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "list all message templates",
    },
    {
        "name": "create_message_template",
        "args_template": "",
        "expected_keywords": ["id", "status"],
        "regex_extractors": {
            "created_template_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "template_status": r'"?status"?[:\s]+"?([^"]+)"?',
        },
        "description": f'create a new message template with name="{template_name}" category="MARKETING" language="en_US" components=[{{"type": "BODY", "text": "Hello from guMCP"}}]',
    },
    {
        "name": "get_template_preview",
        "args_template": "",
        "expected_keywords": ["preview"],
        "regex_extractors": {
            "preview_text": r'"?preview"?[:\s]+"?([^"]+)"?',
        },
        "description": f"preview a message template with name={template_name} language=en_US",
    },
    {
        "name": "get_phone_number_details",
        "args_template": "",
        "expected_keywords": ["id", "display_phone_number"],
        "regex_extractors": {
            "phone_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "phone_number": r'"?display_phone_number"?[:\s]+"?([^"]+)"?',
        },
        "description": "get detailed information about a WhatsApp business phone number",
    },
    {
        "name": "get_business_profile",
        "args_template": "",
        "expected_keywords": [
            "messaging_product",
        ],
        "regex_extractors": {
            "messaging_product": r'"?messaging_product"?[:\s]+"?([^"]+)"?',
        },
        "description": "get WhatsApp Business Profile information",
    },
    {
        "name": "get_message_template_details",
        "args_template": "with id={created_template_id}",
        "expected_keywords": ["id", "name", "status"],
        "regex_extractors": {
            "template_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "template_name": r'"?name"?[:\s]+"?([^"]+)"?',
            "template_status": r'"?status"?[:\s]+"?([^"]+)"?',
        },
        "description": "get detailed information about a specific message template",
    },
    {
        "name": "update_message_template",
        "args_template": "with id={created_template_id} category=MARKETING components=[{{type=BODY, text=Updated message from guMCP}}]",
        "expected_keywords": ["id", "status"],
        "regex_extractors": {
            "updated_template_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "template_status": r'"?status"?[:\s]+"?([^"]+)"?',
        },
        "description": "update an existing message template",
    },
    {
        "name": "send_template_message",
        "args_template": "",
        "expected_keywords": ["message_id"],
        "regex_extractors": {
            "message_id": r'"?id"?[:\s]+"?([^"]+)"?',
        },
        "description": f"send a WhatsApp message using a template with to={phone_number} template_name={template_name} language_code=en_US",
    },
    {
        "name": "delete_message_template",
        "args_template": "with id={created_template_id}",
        "expected_keywords": ["success"],
        "regex_extractors": {
            "success": r'"?success"?[:\s]+"?([^"]+)"?',
        },
        "description": f"delete a message template with template name={template_name}",
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_whatsapp_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
