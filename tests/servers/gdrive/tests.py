import pytest
import uuid
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test

# Shared context dictionary at module level
SHARED_CONTEXT = {}

TOOL_TESTS = [
    {
        "name": "search",
        "args_template": 'with query="Gumloop"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r"file_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Search for files and return any one file id",
    },
    {
        "name": "create_folder",
        "args_template": 'with name="Test Folder {random_id}"',
        "expected_keywords": ["folder_id"],
        "regex_extractors": {"folder_id": r"folder_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Create a new test folder and return the id",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_file_from_text",
        "args_template": 'with name="Test File {random_id}.txt" content="This is a test file created by automated tests." folder_id="{folder_id}"',
        "expected_keywords": ["new_file_id"],
        "regex_extractors": {"new_file_id": r"new_file_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Create a new text file in the test folder and return the id in format 'new_file_id: <id>'",
        "depends_on": ["folder_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "update_file_folder_name",
        "args_template": 'with file_id="{new_file_id}" new_name="Updated Test File {random_id}.txt"',
        "expected_keywords": ["updated_file_id"],
        "regex_extractors": {
            "updated_file_id": r"updated_file_id:\s*([A-Za-z0-9_\-\.]+)"
        },
        "description": "Rename the test file and return its id in format 'updated_file_id: <id>'",
        "depends_on": ["new_file_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_folder",
        "args_template": 'with name="Subfolder {random_id_2}" parent_folder_id="{folder_id}"',
        "expected_keywords": ["subfolder_id"],
        "regex_extractors": {"subfolder_id": r"subfolder_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Create a subfolder in the test folder and return its id",
        "depends_on": ["folder_id"],
        "setup": lambda context: {"random_id_2": str(uuid.uuid4())[:8]},
    },
    {
        "name": "move_file",
        "args_template": 'with file_id="{updated_file_id}" folder_id="{subfolder_id}"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r"file_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "return the moved file id and ensure you return in format 'file_id: <id>'",
        "depends_on": ["updated_file_id", "subfolder_id"],
    },
    {
        "name": "retrieve_file_or_folder_by_id",
        "args_template": 'with id="{file_id}"',
        "expected_keywords": ["retrieved_file_id"],
        "regex_extractors": {
            "retrieved_file_id": r"retrieved_file_id:\s*([A-Za-z0-9_\-\.]+)"
        },
        "description": "Retrieve the test file by ID and return its id",
        "depends_on": ["file_id"],
    },
    {
        "name": "retrieve_files",
        "args_template": "with query=\"name contains 'Test'\"",
        "expected_keywords": ["files_count"],
        "regex_extractors": {"files_count": r"files_count:\s*(\d+)"},
        "description": "Retrieve files with 'Test' in the name and return count",
    },
    {
        "name": "copy_file",
        "args_template": 'with file_id="{file_id}" name="Copy of Test File {random_id}.txt"',
        "expected_keywords": ["copy_id"],
        "regex_extractors": {"copy_id": r"copy_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Create a copy of the test file and return its id in format 'copy_id: <id>'",
        "depends_on": ["file_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "add_file_sharing_preference",
        "args_template": 'with file_id="{file_id}" role="reader" type="anyone"',
        "expected_keywords": ["permission_id"],
        "regex_extractors": {"permission_id": r"permission_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Share the test file with anyone as a reader and return permission id",
        "depends_on": ["file_id"],
    },
    {
        "name": "create_shortcut",
        "args_template": 'with name="Shortcut to File {random_id}" target_id="{file_id}" folder_id="{folder_id}"',
        "expected_keywords": ["shortcut_id"],
        "regex_extractors": {"shortcut_id": r"shortcut_id:\s*([A-Za-z0-9_\-\.]+)"},
        "description": "Create a shortcut to the test file and return its id in format 'shortcut_id: <id>'",
        "depends_on": ["file_id", "folder_id"],
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "delete_file",
        "args_template": 'with file_id="{copy_id}"',
        "expected_keywords": ["deletion_status"],
        "regex_extractors": {
            "deletion_status": r"deletion_status:\s*([A-Za-z0-9_\-\.]+)"
        },
        "description": "Delete the copy of the test file and return status in format 'deletion_status: <status>'",
        "depends_on": ["copy_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_gdrive_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(
        client
    )  # Might fail if first file doesnt support read in google library
    return response
