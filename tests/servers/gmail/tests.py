import pytest


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
