import uuid
import pytest
from tests.utils.test_tools import get_test_id, run_tool_test

# Generate a unique form name for testing
form_name = f"test_form_{str(uuid.uuid4())[:4]}"

TOOL_TESTS = [
    {
        "name": "list_forms",
        "args_template": "",
        "expected_keywords": ["files"],
        "regex_extractors": {
            "form_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "form_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "list all Google Forms",
    },
    {
        "name": "create_form",
        "args_template": f"title={form_name} description=Test form created by guMCP is_public=false",
        "expected_keywords": ["form_id", "response_url", "edit_url"],
        "regex_extractors": {
            "created_form_id": r'"?form_id"?[:\s]+"?([^"]+)"?',
            "response_url": r'"?response_url"?[:\s]+"?([^"]+)"?',
            "edit_url": r'"?edit_url"?[:\s]+"?([^"]+)"?',
        },
        "description": f"create a new Google Form with title={form_name}",
    },
    {
        "name": "get_form",
        "args_template": "with id={created_form_id}",
        "expected_keywords": ["formId", "info"],
        "regex_extractors": {
            "form_id": r'"?formId"?[:\s]+"?([^"]+)"?',
            "form_title": r'"?title"?[:\s]+"?([^"]+)"?',
        },
        "description": "get details of a specific Google Form",
    },
    {
        "name": "update_form",
        "args_template": "with id={created_form_id} description=Updated description for test form is_public=true",
        "expected_keywords": ["form_id", "result"],
        "regex_extractors": {
            "updated_form_id": r'"?form_id"?[:\s]+"?([^"]+)"?',
            "form_description": r'"?description"?[:\s]+"?([^"]+)"?',
        },
        "description": "update an existing Google Form",
    },
    {
        "name": "search_forms",
        "args_template": f"query={form_name}",
        "expected_keywords": ["files"],
        "regex_extractors": {
            "found_form_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "found_form_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": f"search for Google Forms with name containing {form_name}",
    },
    {
        "name": "add_question",
        "args_template": "with form_id={created_form_id} question_type=text title=Test Question required=true",
        "expected_keywords": ["replies"],
        "regex_extractors": {
            "question_id": r'"?itemId"?[:\s]+"?([^"]+)"?',
        },
        "description": "add a text question to a Google Form",
    },
    {
        "name": "delete_item",
        "args_template": "with form_id={created_form_id} item_id={question_id}",
        "expected_keywords": ["replies"],
        "regex_extractors": {
            "success": r'"?replies"?[:\s]+"?([^"]+)"?',
        },
        "description": "delete a question from a Google Form",
    },
    {
        "name": "list_responses",
        "args_template": "with form_id={created_form_id} page_size=10",
        "expected_keywords": ["responses"],
        "regex_extractors": {
            "response_count": r'"?responses"?[:\s]+"?([^"]+)"?',
            "response_id": r'"?responseId"?[:\s]+"?([^"]+)"?',
        },
        "description": "list responses for a Google Form",
    },
    {
        "name": "get_response",
        "args_template": "with form_id={created_form_id} response_id={response_id}",
        "expected_keywords": ["responseId", "answers"],
        "regex_extractors": {
            "response_id": r'"?responseId"?[:\s]+"?([^"]+)"?',
        },
        "description": "get details of a form response",
    },
    {
        "name": "move_form_to_trash",
        "args_template": "with id={created_form_id}",
        "expected_keywords": ["id"],
        "regex_extractors": {
            "trashed_form_id": r'"?id"?[:\s]+"?([^"]+)"?',
        },
        "description": "move a Google Form to trash",
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_gforms_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


# @pytest.mark.asyncio
# async def test_list_resources(client):
#     """Test listing resources from Google Forms"""
#     response = await client.list_resources()
#     print(f"Response: {response}")
#     assert response, "No response returned from list_resources"

#     for i, resource in enumerate(response.resources):
#         print(f"  - {i}: {resource.name} ({resource.uri}) {resource.description}")

#     print("✅ Successfully listed resources")

# @pytest.mark.asyncio
# async def test_read_resource(client):
#     """Test reading a resource from Google Forms"""
#     list_response = await client.list_resources()

#     form_resource_uri = [
#         resource.uri
#         for resource in list_response.resources
#         if str(resource.uri).startswith("gforms://form/")
#     ]

#     if len(form_resource_uri) > 0:
#         form_resource_uri = form_resource_uri[0]
#         response = await client.read_resource(form_resource_uri)
#         assert response, "No response returned from read_resource"
#         print(f"Response: {response}")
#         print("✅ read_resource for form passed.")
