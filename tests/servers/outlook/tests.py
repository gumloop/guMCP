import pytest
import uuid


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing emails from Outlook"""
    response = await client.list_resources()
    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    print("Emails found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed emails from Outlook")


@pytest.mark.asyncio
async def test_read_email(client):
    """Test reading an email from Outlook"""
    # First list emails to get a valid email ID
    response = await client.list_resources()

    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    resources = response.resources

    # Skip test if no emails found
    if not resources:
        print("⚠️ No emails found to test reading")
        pytest.skip("No emails available for testing")
        return

    # Test with the first email
    email_resource = resources[0]
    response = await client.read_resource(email_resource.uri)

    assert (
        response and response.contents
    ), f"Response should contain email contents: {response}"
    assert len(response.contents[0].text) >= 0, "Email content should be available"

    print("Email read:")
    print(f"  - {email_resource.name}: {response.contents[0].text[:100]}...")

    print("✅ Successfully read email from Outlook")


@pytest.mark.asyncio
async def test_read_emails_inbox(client):
    """Test reading emails from the inbox folder using the tool"""
    folder = "inbox"
    count = 5

    response = await client.process_query(
        f"Use the read_emails tool to fetch {count} emails from my {folder} folder. "
        f"If successful, start your response with 'Successfully fetched emails from {folder}'."
    )

    # Verify that emails were retrieved
    assert (
        "successfully fetched emails" in response.lower()
    ), f"Email retrieval failed: {response}"
    assert folder in response.lower(), f"Folder name not found in response: {response}"

    print(f"Read emails from {folder} folder")
    print(f"Response: {response}")
    print("✅ Successfully read emails from inbox")


@pytest.mark.asyncio
async def test_send_email(client):
    """Test sending an email"""
    # Generate a unique subject to identify this test email
    subject = f"Test Email"
    to_address = "rahul@gumloop.com"  # Replace with a valid test email address
    body = "This is a test email sent by the Gumloop MCP Server."

    response = await client.process_query(
        f"Use the send_email tool to send an email to {to_address} with subject '{subject}' "
        f"and the following body: '{body}'. "
        f"If successful, start your response with 'Email sent successfully'."
    )

    # Verify that email was sent
    assert (
        "email sent successfully" in response.lower()
    ), f"Email sending failed: {response}"
    assert (
        to_address in response.lower()
    ), f"Recipient address not found in response: {response}"

    print(f"Sent test email with subject: {subject}")
    print(f"Response: {response}")
    print("✅ Successfully sent email")


@pytest.mark.asyncio
async def test_send_email_with_cc_bcc(client):
    """Test sending an email with CC and BCC recipients"""
    # Generate a unique subject to identify this test email
    test_id = uuid.uuid4()
    subject = f"Test Email with CC/BCC {test_id}"
    to_address = "rahul@gumloop.com"
    cc_address = "max@gumloop.com"
    bcc_address = "daniel@gumloop.com"
    body = "This is a test email with CC and BCC recipients sent by an automated test."

    response = await client.process_query(
        f"Use the send_email tool to send an email to {to_address} with CC to {cc_address}, "
        f"BCC to {bcc_address}, subject '{subject}' and the following body: '{body}'. "
        f"If successful, start your response with 'Email sent successfully'."
    )

    # Verify that email with CC/BCC was sent
    assert (
        "email sent successfully" in response.lower()
    ), f"Email sending with CC/BCC failed: {response}"
    assert (
        to_address in response.lower()
    ), f"Recipient address not found in response: {response}"

    print(f"Sent test email with CC/BCC and subject: {subject}")
    print(f"Response: {response}")
    print("✅ Successfully sent email with CC and BCC")


@pytest.mark.asyncio
async def test_read_emails_custom_folder(client):
    """Test reading emails from a custom folder"""
    folder = "Sent Items"  # Using a common folder that should exist
    count = 3

    response = await client.process_query(
        f"Use the read_emails tool to fetch {count} emails from my '{folder}' folder. "
        f"If successful, start your response with 'Successfully fetched emails from {folder}'."
    )

    # Verify that emails from custom folder were retrieved
    assert (
        "successfully fetched emails" in response.lower()
    ), f"Custom folder email retrieval failed: {response}"
    assert (
        folder.lower() in response.lower()
    ), f"Custom folder name not found in response: {response}"

    print(f"Read emails from {folder} folder")
    print(f"Response: {response}")
    print("✅ Successfully read emails from custom folder")
