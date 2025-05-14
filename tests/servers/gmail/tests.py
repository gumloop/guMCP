import pytest
import uuid

from tests.utils.test_tools import get_test_id, run_tool_test


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing Gmail labels"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Gmail labels found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed Gmail labels")


@pytest.mark.asyncio
async def test_read_label(client):
    """Test reading emails from a label"""
    # First list labels to get a valid label ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Skip test if no labels found
    if not response.resources:
        print("⚠️ No Gmail labels found to test reading")
        pytest.skip("No Gmail labels available for testing")
        return

    # Try to read the first label
    label = response.resources[0]
    read_response = await client.read_resource(label.uri)

    assert len(
        read_response.contents[0].text
    ), f"Response should contain emails from label: {read_response}"

    print("Label emails:")
    print(f"\t{read_response.contents[0].text}")

    print("✅ Successfully read emails from label")


SHARED_CONTEXT = {
    "test_email": "jyoti@gumloop.com",
}

TOOL_TESTS = [
    # Read operations first
    {
        "name": "read_emails",
        "args_template": 'with query="is:unread" max_results=3',
        "expected_keywords": ["email_id"],
        "regex_extractors": {"email_id": r"id:\s*([a-z0-9]+)"},
        "description": "search and read emails with a query and return any one of the email ids",
    },
    # Create operations
    {
        "name": "create_label",
        "args_template": 'with name="Test Label {random_id}" background_color="#0C0E13" text_color="#0C0E13"',
        "expected_keywords": ["label_id"],
        "regex_extractors": {"label_id": r"label_id:\s*([A-Za-z0-9_]+)"},
        "description": "create a label and return label id",
        "setup": lambda context: {"random_id": str(uuid.uuid4())[:8]},
    },
    {
        "name": "create_draft",
        "args_template": 'with to="test@gumloop.com" subject="Test Email" body="This is a test email sent from automated testing."',
        "expected_keywords": ["draft_id"],
        "regex_extractors": {"draft_id": r"draft_id:\s*([a-zA-Z0-9]+)"},
        "description": "create a draft email and return its id as draft_id in format draft_id: <draft_id>",
    },
    {
        "name": "send_email",
        "args_template": 'with to="{test_email}" subject="Test Email" body="This is a test email sent from automated testing."',
        "expected_keywords": ["email_thread_id"],
        "regex_extractors": {"email_thread_id": r"email_thread_id:\s*([a-z0-9]+)"},
        "description": "send an email and return email thread id in format email_thread_id: <email_thread_id>",
        "depends_on": ["test_email"],
    },
    # Modify operations on existing emails
    {
        "name": "update_email",
        "args_template": 'with email_id="{email_thread_id}" remove_labels=["UNREAD"]',
        "expected_keywords": ["updated_email_id"],
        "regex_extractors": {"updated_email_id": r"updated_email_id:\s*([a-z0-9]+)"},
        "description": "update email labels and return updated email id in format updated_email_id: <updated_email_id>",
        "depends_on": ["email_thread_id"],
    },
    {
        "name": "star_email",
        "args_template": 'with email_id="{email_thread_id}"',
        "expected_keywords": ["starred_email_id"],
        "regex_extractors": {"starred_email_id": r"starred_email_id:\s*([a-z0-9]+)"},
        "description": "star an email and return starred email thread id in format starred_email_id: <starred_email_id>",
        "depends_on": ["email_thread_id"],
    },
    {
        "name": "unstar_email",
        "args_template": 'with email_id="{email_thread_id}"',
        "expected_keywords": ["unstarred_email_id"],
        "regex_extractors": {
            "unstarred_email_id": r"unstarred_email_id:\s*([a-z0-9]+)"
        },
        "description": "unstar an email and return unstarred email thread id in format unstarred_email_id: <unstarred_email_id>",
        "depends_on": ["email_thread_id"],
    },
    {
        "name": "forward_email",
        "args_template": 'with email_id="{email_thread_id}" to="{test_email}"',
        "expected_keywords": ["forwarded_email_id"],
        "regex_extractors": {
            "forwarded_email_id": r"forwarded_email_id:\s*([a-z0-9]+)"
        },
        "description": "forward an email and return forwarded email id",
        "depends_on": ["email_thread_id", "test_email"],
    },
    {
        "name": "get_attachment_details",
        "args_template": 'with email_id="{email_thread_id}"',
        "expected_keywords": ["attachment_details"],
        "regex_extractors": {
            "attachment_details": r"attachment_details:\s*([a-z0-9]+)"
        },
        "description": "get attachment details and return attachment details",
        "depends_on": ["email_thread_id"],
    },
    {
        "name": "download_attachment",
        "args_template": 'with email_id="{email_thread_id}" attachment_id="{attachment_id}"',
        "expected_keywords": ["downloaded_attachment_id"],
        "regex_extractors": {
            "downloaded_attachment_id": r"downloaded_attachment_id:\s*([a-z0-9]+)"
        },
        "description": "download an attachment and return downloaded attachment id",
        "depends_on": ["email_thread_id", "attachment_id"],
    },
    # Final operations/cleanup actions
    {
        "name": "archive_email",
        "args_template": 'with email_id="{email_thread_id}"',
        "expected_keywords": ["archived_email_id"],
        "regex_extractors": {"archived_email_id": r"archived_email_id:\s*([a-z0-9]+)"},
        "description": "archive an email and return archived email id in format archived_email_id: <archived_email_id>",
        "depends_on": ["email_thread_id"],
    },
    {
        "name": "trash_email",
        "args_template": 'with email_id="{email_thread_id}"',
        "expected_keywords": ["trashed_email_id"],
        "regex_extractors": {"trashed_email_id": r"trashed_email_id:\s*([a-z0-9]+)"},
        "description": "trash an email and return trashed email id in format trashed_email_id: <trashed_email_id>",
        "depends_on": ["email_thread_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_gmail_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
