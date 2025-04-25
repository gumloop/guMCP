import pytest
import uuid

# Global variables to store created subscriber and campaign IDs
created_subscriber_email = None
created_campaign_id = None
list_id = None

# You need to create a campaign in mailchimp to run this test
campaign_id = None


@pytest.mark.asyncio
async def test_get_audience_list(client):
    """Fetch all available audiences in Mailchimp.

    Verifies that the response contains audience information.

    Args:
        client: The test client fixture for the MCP server.
    """
    global list_id

    response = await client.process_query(
        "Use the get_audience_list tool to fetch all available audiences. "
        "If successful, start your response with 'Here are the available audiences' and then list them. "
        "Include the list id in your response in format ID: <list_id>"
    )

    assert (
        "here are the available audiences" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_audience_list"

    try:
        list_id = response.split("ID: ")[1].split()[0]
    except Exception as e:
        pytest.fail(f"Failed to extract list ID from response: {e} {response}")

    print(f"Response: {response}")
    print("✅ get_audience_list passed.")


@pytest.mark.asyncio
async def test_get_all_list(client):
    """Get all lists available in the Mailchimp account.

    Verifies that the response contains list information.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_all_list tool to fetch all available lists. "
        "If successful, start your response with 'Here are all available lists' and then list them."
    )

    assert (
        "here are all available lists" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_all_list"

    print(f"Response: {response}")
    print("✅ get_all_list passed.")


@pytest.mark.asyncio
async def test_list_all_campaigns(client):
    """List all campaigns in the Mailchimp account.

    Verifies that the response contains campaign information.

    Args:
        client: The test client fixture for the MCP server.
    """
    global campaign_id

    response = await client.process_query(
        "Use the list_all_campaigns tool to fetch all campaigns. "
        "If successful, start your response with 'Here are all campaigns' and then list them. "
        "Include the campaign id in your response in format ID: <campaign_id>"
    )

    assert (
        "here are all campaigns" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_all_campaigns"

    try:
        campaign_id = response.split("ID: ")[1].split()[0]
    except Exception as e:
        pytest.fail(f"Failed to extract campaign ID from response: {e} {response}")

    print(f"Response: {response}")
    print("✅ list_all_campaigns passed.")


@pytest.mark.asyncio
async def test_campaign_info(client):
    """Get information about a specific campaign.

    Verifies that the response contains campaign details.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        f"Use the campaign_info tool to fetch details for campaign ID {campaign_id}. "
        "If successful, start your response with 'Here are the campaign details' and then list them."
    )

    assert (
        "here are the campaign details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from campaign_info"

    print(f"Response: {response}")
    print("✅ campaign_info passed.")


@pytest.mark.asyncio
async def test_recent_activity(client):
    """Get recent activity for a specific list.

    Verifies that the response contains recent activity information.

    Args:
        client: The test client fixture for the MCP server.
    """

    response = await client.process_query(
        f"Use the recent_activity tool to fetch recent activity for list ID {list_id}. "
        "If successful, start your response with 'Here is the recent activity' and then list it."
    )

    assert (
        "here is the recent activity" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from recent_activity"

    print(f"Response: {response}")
    print("✅ recent_activity passed.")


@pytest.mark.asyncio
async def test_add_update_subscriber(client):
    """Add or update a subscriber in a Mailchimp list.

    Verifies that the subscriber is added/updated successfully.
    Stores the subscriber email for use in tag test.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_subscriber_email
    email = f"test_{uuid.uuid4()}@gmail.com"
    first_name = "Test"
    last_name = "User"

    response = await client.process_query(
        f"Use the add_update_subscriber tool to add/update a subscriber in list {list_id} "
        f"with email {email}, first name {first_name}, and last name {last_name}. "
        "If successful, start your response with 'Subscriber added/updated successfully'."
    )

    assert (
        "subscriber added/updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_update_subscriber"

    created_subscriber_email = email
    print(f"Created subscriber email: {created_subscriber_email}")
    print(f"Response: {response}")
    print("✅ add_update_subscriber passed.")


@pytest.mark.asyncio
async def test_add_subscriber_tags(client):
    """Add tags to a subscriber in a Mailchimp list.

    Verifies that the tags are added successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscriber_email:
        pytest.skip(
            "No subscriber email available - run add_update_subscriber test first"
        )

    tags = ["test_tag1", "test_tag2"]

    response = await client.process_query(
        f"Use the add_subscriber_tags tool to add tags {tags} to subscriber {created_subscriber_email} "
        f"in list {list_id}. If successful, start your response with 'Tags added successfully'."
    )

    assert (
        "tags added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_subscriber_tags"

    print(f"Response: {response}")
    print("✅ add_subscriber_tags passed.")
