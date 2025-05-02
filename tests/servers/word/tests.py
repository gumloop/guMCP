import pytest
import random
from tests.utils.test_tools import get_test_id, run_tool_test, run_resources_test


TOOL_TESTS = [
    {
        "name": "list_documents",
        "args_template": "with limit=10",
        "expected_keywords": ["document_id"],
        "regex_extractors": {"document_id": r'"?document_id"?[:\s]+([^,\s\n"]+)'},
        "description": "list Word documents from OneDrive and return the document_id of any one document and if empty set document_id to empty",
    },
    {
        "name": "create_document",
        "args_template": 'with name="Test Document-{random_id}"',
        "expected_keywords": ["created_file_id"],
        "regex_extractors": {
            "created_file_id": r'"?created_file_id"?[:\s]+"?([0-9A-Z!]+)"?',
            "is_sharepoint": r'"?is_sharepoint"?[:\s]+"?([^"]+)"?',
        },
        "description": "create a new Word document and return its file id as created_file_id and based on url return is_sharepoint as true or false",
        "setup": lambda context: {"random_id": str(random.randint(10000, 99999))},
    },
    {
        "name": "write_document",
        "args_template": 'with file_id="{created_file_id}" content="Gumloop"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+"?([0-9A-Z!]+)"?'},
        "description": "append new content to an existing Word document and return the file_id",
        "depends_on": ["created_file_id"],
    },
    {
        "name": "read_document",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["content"],
        "regex_extractors": {"content": r'"?content"?[:\s]+"([^"]*Gumloop[^"]*)"'},
        "description": "read text content from a Word document and return the content without any formatting or modifications",
        "depends_on": ["created_file_id"],
    },
    {
        "name": "search_documents",
        "args_template": 'with query="Test Document"',
        "expected_keywords": ["file_id"],
        "regex_extractors": {"file_id": r'"?file_id"?[:\s]+"?([0-9A-Z!]+)"?'},
        "description": "search for Word documents matching a query and return the file_id of any one document",
    },
    {
        "name": "download_document",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["url"],
        "description": "get a download URL for a Word document and return the url",
        "depends_on": ["created_file_id"],
    },
    {
        "name": "delete_document",
        "args_template": 'with file_id="{created_file_id}"',
        "expected_keywords": ["deleted"],
        "description": "delete a Word document from OneDrive",
        "depends_on": ["created_file_id"],
    },
]

# Shared context dictionary at module level
SHARED_CONTEXT = {}


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_word_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_resources(client, context):
    response = await run_resources_test(client)
    context["first_resource_uri"] = response.resources[0].uri
    return response
