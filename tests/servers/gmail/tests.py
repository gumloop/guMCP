import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing emails from Gmail"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Emails found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed emails")


@pytest.mark.asyncio
async def test_read_email(client):
    """Test reading an email"""
    # First list emails to get a valid email ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Try to read the first email
    email = response.resources[0]
    read_response = await client.read_resource(email.uri)

    assert len(
        read_response.contents[0].text
    ), f"Response should contain email contents: {read_response}"

    print("Email content:")
    print(f"\t{read_response.contents[0].text}")

    print("✅ Successfully read email")


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
