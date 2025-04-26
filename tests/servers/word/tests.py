import pytest
import re
import random
import string
from tests.utils.test_tools import get_test_id, run_tool_test


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
async def test_read_resource(client):
    """Test reading a Word document resource"""
    # First list resources to get a valid Word file
    response = await client.list_resources()

    # Skip test if no resources were returned
    if not (response and hasattr(response, "resources") and len(response.resources)):
        pytest.skip("No Word resources found to test read_resource functionality")
        return

    # Find the first Word file resource
    word_resource = next(
        (r for r in response.resources if str(r.uri).startswith("word://file/")),
        None,
    )

    if not word_resource:
        pytest.skip("No Word resources found to test read_resource functionality")
        return

    # Read Word file details
    response = await client.read_resource(word_resource.uri)
    assert response.contents, "Response should contain Word document data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    # Parse and verify JSON content
    import json

    content_data = json.loads(response.contents[0].text)

    # Check if there was an error response
    if "error" in content_data:
        pytest.fail(f"Error reading document: {content_data.get('error')}")

    # Verify basic document data
    assert "id" in content_data, "Response should include document ID"
    assert "name" in content_data, "Response should include document name"
    assert "webUrl" in content_data, "Response should include webUrl"

    print("Word document data read:")
    print(f"  - Document name: {content_data.get('name')}")
    print(f"  - Document size: {content_data.get('size')} bytes")
    print("✅ Successfully read Word document data")
