import pytest

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


@pytest.mark.asyncio
async def test_read_emails_tool(client):
    """Test the read_emails tool"""
    response = await client.process_query(
        "Use the read_emails tool to search for emails with the query 'is:unread' and limit to 3 results. If you found the emails, start your response with 'I found the emails:'"
    )

    assert (
        "i found the emails" in response.lower()
    ), f"Search results not found in response: {response}"

    print("Search results:")
    print(f"\t{response}")

    print("✅ Read emails tool working")


@pytest.mark.asyncio
async def test_send_email(client):
    """Test sending an email"""
    response = await client.process_query(
        """Use the send_email tool to send a test email with these parameters:
        to: rahul@gumloop.com
        subject: Test Email
        body: This is a test email sent from automated testing.
        If it worked successfully, start your response with 'Sent Successfsfully'"""
    )

    assert "sent successfully" in response.lower(), f"Failed to send email: {response}"

    print("Send email response:")
    print(f"\t{response}")

    print("✅ Send email tool working")


@pytest.mark.asyncio
async def test_update_email(client):
    """Test updating email labels"""
    # First get an email ID
    list_response = await client.list_resources()
    assert len(list_response.resources) > 0, "No emails found to test with"

    email_id = str(list_response.resources[0].uri).replace("gmail:///", "")

    response = await client.process_query(
        f"""Use the update_email tool to mark email {email_id} as read with these parameters:
        email_id: {email_id}
        remove_labels: ["UNREAD"]
        If it works successfuly start your response with 'Successfully updated email'"""
    )

    assert (
        "successfully updated email" in response.lower()
    ), f"Failed to update email: {response}"

    print("Update email response:")
    print(f"\t{response}")

    print("✅ Update email tool working")


SHARED_CONTEXT = {
    "test_email": "jyoti@gumloop.com",
}

TOOL_TESTS = [
    {
        "name": "create_draft",
        "args_template": 'with to="test@gumloop.com" subject="Test Email" body="This is a test email sent from automated testing."',
        "expected_keywords": ["draft_id"],
        "regex_extractors": {"draft_id": r"draft_id:\s*([a-z0-9]+)"},
        "description": "create a draft email and return its message id as draft_id, ex: draft_id: 1234567890",
    },
    {
        "name": "send_email",
        "args_template": 'with to="{test_email}" subject="Test Email" body="This is a test email sent from automated testing."',
        "expected_keywords": ["email_id"],
        "regex_extractors": {"email_id": r"email_id:\s*([a-z0-9]+)"},
        "description": "send an email and return email id",
        "depends_on": ["test_email"],
    },
    {
        "name": "forward_email",
        "args_template": 'with email_id="{email_id}" to="{test_email}"',
        "expected_keywords": ["forwarded_email_id"],
        "regex_extractors": {
            "forwarded_email_id": r"forwarded_email_id:\s*([a-z0-9]+)"
        },
        "description": "forward an email and return forwarded email id, follow the format",
        "depends_on": ["email_id"],
    },
    {
        "name": "create_label",
        "args_template": 'with name="Test Label" background_color="#000000" text_color="#FFFFFF"',
        "expected_keywords": ["label_id"],
        "regex_extractors": {"label_id": r"label_id:\s*([a-z0-9]+)"},
        "description": "create a label and return label id, follow the format",
    },
    {
        "name": "archive_email",
        "args_template": 'with email_id="{email_id}"',
        "expected_keywords": ["archived_email_id"],
        "regex_extractors": {"archived_email_id": r"archived_email_id:\s*([a-z0-9]+)"},
        "description": "archive an email and return archived email id, follow the format",
        "depends_on": ["email_id"],
    },
    {
        "name": "star_email",
        "args_template": 'with email_id="{email_id}"',
        "expected_keywords": ["starred_email_id"],
        "regex_extractors": {"starred_email_id": r"starred_email_id:\s*([a-z0-9]+)"},
        "description": "star an email and return starred email id, follow the format",
        "depends_on": ["email_id"],
    },
    {
        "name": "unstar_email",
        "args_template": 'with email_id="{email_id}"',
        "expected_keywords": ["unstarred_email_id"],
        "regex_extractors": {
            "unstarred_email_id": r"unstarred_email_id:\s*([a-z0-9]+)"
        },
        "description": "unstar an email and return unstarred email id, follow the format",
        "depends_on": ["email_id"],
    },
    {
        "name": "get_attachment_details",
        "args_template": 'with email_id="{email_id}"',
        "expected_keywords": ["attachment_details"],
        "regex_extractors": {
            "attachment_details": r"attachment_details:\s*([a-z0-9]+)"
        },
        "description": "get attachment details and return attachment details, follow the format",
        "depends_on": ["email_id"],
    },
    {
        "name": "download_attachment",
        "args_template": 'with email_id="{email_id}" attachment_id="{attachment_id}"',
        "expected_keywords": ["downloaded_attachment_id"],
        "regex_extractors": {
            "downloaded_attachment_id": r"downloaded_attachment_id:\s*([a-z0-9]+)"
        },
        "description": "download an attachment and return downloaded attachment id, follow the format",
        "depends_on": ["email_id", "attachment_id"],
    },
    {
        "name": "trash_email",
        "args_template": 'with email_id="{email_id}"',
        "expected_keywords": ["trashed_email_id"],
        "regex_extractors": {"trashed_email_id": r"trashed_email_id:\s*([a-z0-9]+)"},
        "description": "trash an email and return trashed email id, follow the format",
        "depends_on": ["email_id"],
    },
]


@pytest.fixture(scope="module")
def context():
    return SHARED_CONTEXT


@pytest.mark.parametrize("test_config", TOOL_TESTS, ids=get_test_id)
@pytest.mark.asyncio
async def test_hubspot_tool(client, context, test_config):
    return await run_tool_test(client, context, test_config)
