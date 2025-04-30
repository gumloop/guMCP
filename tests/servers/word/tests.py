import pytest
import random
from tests.utils.test_tools import get_test_id, run_tool_test


RESOURCE_TESTS = [
    {
        "name": "list_resources",
        "expected_keywords": ["resources"],
        "regex_extractors": {
            "resource_uri": r'"?uri"?[:\s]+"?(word://file/[^"]+)"?',
            "resource_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "list Word document resources and extract a resource URI",
    },
    {
        "name": "read_resource",
        "args_template": 'with uri="{resource_uri}"',
        "expected_keywords": ["contents"],
        "regex_extractors": {
            "document_id": r'"?id"?[:\s]+"?([^"]+)"?',
            "document_name": r'"?name"?[:\s]+"?([^"]+)"?',
        },
        "description": "read a Word document resource and extract document details",
        "depends_on": ["resource_uri"],
    },
]

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


@pytest.mark.parametrize("test_config", RESOURCE_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_word_resource(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_word_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a Word document resource"""
    response = await client.list_resources()

    if not (response and hasattr(response, "resources") and len(response.resources)):
        pytest.skip("No Word resources found to test read_resource functionality")
        return

    word_resource = next(
        (r for r in response.resources if str(r.uri).startswith("word://file/")),
        None,
    )

    if not word_resource:
        pytest.skip("No Word resources found to test read_resource functionality")
        return

    response = await client.read_resource(word_resource.uri)
    assert response.contents, "Response should contain Word document data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    import json

    content_data = json.loads(response.contents[0].text)

    if "error" in content_data:
        pytest.fail(f"Error reading document: {content_data.get('error')}")

    assert "id" in content_data, "Response should include document ID"
    assert "name" in content_data, "Response should include document name"
    assert "webUrl" in content_data, "Response should include webUrl"
