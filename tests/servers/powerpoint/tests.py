import pytest
import uuid
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

TOOL_TESTS = [
    {
        "name": "list_presentations",
        "args_template": "limit=5",
        "expected_keywords": ["success"],
        "description": "list PowerPoint presentations and extract a file ID",
    },
    {
        "name": "create_presentation",
        "args_template": 'name="Test Presentation {random_id}" title_slide="Test Presentation Created by Automated Tests"',
        "expected_keywords": ["success", "file_id"],
        "regex_extractors": {"new_file_id": r'"?file_id"?[:\s]+([^,\s\n"]+)'},
        "description": "create a new PowerPoint presentation and extract the file ID",
        "setup": lambda context: {"random_id": str(uuid.uuid4().hex[:6])},
    },
    {
        "name": "read_presentation",
        "args_template": 'file_id="{new_file_id}"',
        "expected_keywords": ["success"],
        "description": "read the contents of a PowerPoint presentation",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "add_slide",
        "args_template": 'file_id="{new_file_id}" title="Test Slide Added" content="This is a test slide content\n- Bullet point 1\n- Bullet point 2" layout="Title and Content"',
        "expected_keywords": ["success"],
        "description": "add a new slide to the presentation",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "update_slide",
        "args_template": 'file_id="{new_file_id}" slide_index=0 title="Updated Test Slide" content="This slide was updated by automated tests\n- Updated bullet point 1\n- Updated bullet point 2"',
        "expected_keywords": ["success"],
        "description": "update the contents of a slide",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "read_presentation",
        "args_template": 'file_id="{new_file_id}"',
        "expected_keywords": ["success"],
        "description": "read the updated presentation to verify changes",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "search_presentations",
        "args_template": 'query="Test Presentation" limit=5',
        "expected_keywords": ["success"],
        "description": "search for presentations with specific content",
    },
    {
        "name": "download_presentation",
        "args_template": 'file_id="{new_file_id}"',
        "expected_keywords": ["success"],
        "description": "get a download URL for the presentation",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "delete_slide",
        "args_template": 'file_id="{new_file_id}" slide_index=0',
        "expected_keywords": ["success"],
        "description": "delete a slide from the presentation",
        "depends_on": ["new_file_id"],
    },
    {
        "name": "delete_presentation",
        "args_template": 'file_id="{new_file_id}"',
        "expected_keywords": ["success"],
        "description": "delete the test presentation",
        "depends_on": ["new_file_id"],
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_powerpoint_tool(client, context, test_config):
    print(f"Running test: {test_config['name']}")
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
