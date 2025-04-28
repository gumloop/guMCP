import pytest
import uuid

# Global variables to store created IDs
created_subscriber_id = None
created_group_id = None
created_field_id = None
created_campaign_id = None
created_webhook_id = None
subscriber_email = f"test_{uuid.uuid4()}@gmail.com"


created_form_id = ""  # Pre-existing form ID for testing form operations
from_email = ""  # Email address of the API key owner, used for campaign testing


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from MailerLite"""
    response = await client.list_resources()
    print(f"Response: {response}")
    assert response, "No response returned from list_resources"

    for i, resource in enumerate(response.resources):
        print(f"  - {i}: {resource.name} ({resource.uri}) {resource.description}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_resource(client):
    """Test reading a resource from Teams"""
    list_response = await client.list_resources()

    form_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("mailerlite://form/")
    ]

    if len(form_resource_uri) > 0:
        form_resource_uri = form_resource_uri[0]
        response = await client.read_resource(form_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for form passed.")

    campaign_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("mailerlite://campaign/")
    ]

    if len(campaign_resource_uri) > 0:
        campaign_resource_uri = campaign_resource_uri[0]
        response = await client.read_resource(campaign_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for campaign passed.")

    group_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("mailerlite://group/")
    ]

    if len(group_resource_uri) > 0:
        group_resource_uri = group_resource_uri[0]
        response = await client.read_resource(group_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for group passed.")

    webhook_resource_uri = [
        resource.uri
        for resource in list_response.resources
        if str(resource.uri).startswith("mailerlite://webhook/")
    ]

    if len(webhook_resource_uri) > 0:
        webhook_resource_uri = webhook_resource_uri[0]
        response = await client.read_resource(webhook_resource_uri)
        assert response, "No response returned from read_resource"
        print(f"Response: {response}")
        print("✅ read_resource for webhook passed.")


# Subscriber CRUD tests
@pytest.mark.asyncio
async def test_create_subscriber(client):
    """Create a new subscriber in MailerLite.

    Verifies that the subscriber is created successfully.
    Stores the created subscriber ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_subscriber_id

    fields = {"name": "Test User", "last_name": "Test Last Name"}

    response = await client.process_query(
        f"Use the create_subscriber tool to create a new subscriber with email {subscriber_email} "
        f"and fields {fields}. If successful, start your response with 'Successfully created subscriber'. "
        "Send ID of the subscriber in the response in format ID: <ID>"
    )

    assert (
        "successfully created subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_subscriber"

    # Extract subscriber ID from response
    try:
        created_subscriber_id = response.split("ID: ")[1].split()[0]
        print(f"Created subscriber ID: {created_subscriber_id}")
    except IndexError:
        pytest.fail("Could not extract subscriber ID from response")

    print(f"Response: {response}")
    print("✅ create_subscriber passed.")


@pytest.mark.asyncio
async def test_get_subscriber(client):
    """Get a subscriber's details from MailerLite.

    Verifies that a subscriber's details can be retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not subscriber_email:
        pytest.skip("No subscriber ID available - run create_subscriber test first")

    response = await client.process_query(
        f"Use the get_subscriber tool to get details of subscriber with email {subscriber_email}. "
        "If successful, start your response with 'Successfully retrieved subscriber'."
    )

    assert (
        "successfully retrieved subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_subscriber"

    print(f"Response: {response}")
    print("✅ get_subscriber passed.")


@pytest.mark.asyncio
async def test_update_subscriber(client):
    """Update a subscriber in MailerLite.

    Verifies that a subscriber can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscriber_id:
        pytest.skip("No subscriber ID available - run create_subscriber test first")

    fields = {
        "name": "Updated Test User",
        "last_name": "Updated Test Last Name",
        "email": "updated@gmail.com",
    }

    response = await client.process_query(
        f"Use the update_subscriber tool to update subscriber with ID {created_subscriber_id} "
        f"and fields {fields}. If successful, start your response with 'Successfully updated subscriber'."
    )

    assert (
        "successfully updated subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_subscriber"

    print(f"Response: {response}")
    print("✅ update_subscriber passed.")


# Group CRUD tests
@pytest.mark.asyncio
async def test_create_group(client):
    """Create a new group in MailerLite.

    Verifies that the group is created successfully.
    Stores the created group ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_group_id

    group_name = f"Test Group {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the create_group tool to create a new group with name {group_name}. "
        "If successful, start your response with 'Successfully created group'. "
        "Send ID of the group in the response in format ID: <ID>"
    )

    assert (
        "successfully created group" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_group"

    # Extract group ID from response
    try:
        created_group_id = response.split("ID: ")[1].split()[0]
        print(f"Created group ID: {created_group_id}")
    except IndexError:
        pytest.fail("Could not extract group ID from response")

    print(f"Response: {response}")
    print("✅ create_group passed.")


@pytest.mark.asyncio
async def test_list_groups(client):
    """List groups in MailerLite.

    Verifies that groups can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 10
    sort = "name"

    response = await client.process_query(
        f"Use the list_groups tool to fetch {limit} groups sorted by {sort}. "
        "If successful, start your response with 'Successfully retrieved groups'."
    )

    assert (
        "successfully retrieved groups" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_groups"

    print(f"Response: {response}")
    print("✅ list_groups passed.")


@pytest.mark.asyncio
async def test_update_group(client):
    """Update a group in MailerLite.

    Verifies that a group can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_group_id:
        pytest.skip("No group ID available - run create_group test first")

    new_name = f"Updated Test Group {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the update_group tool to update group with ID {created_group_id} "
        f"and new name {new_name}. If successful, start your response with 'Successfully updated group'."
    )

    assert (
        "successfully updated group" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_group"

    print(f"Response: {response}")
    print("✅ update_group passed.")


# Field CRUD tests
@pytest.mark.asyncio
async def test_create_field(client):
    """Create a new field in MailerLite.

    Verifies that the field is created successfully.
    Stores the created field ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_field_id

    field_name = f"Test Field {uuid.uuid4()}"
    field_type = "text"

    response = await client.process_query(
        f"Use the create_field tool to create a new field with name {field_name} "
        f"and type {field_type}. If successful, start your response with 'Successfully created field'. "
        "Send ID of the field in the response in format ID: <ID>"
    )

    assert (
        "successfully created field" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_field"

    # Extract field ID from response
    try:
        created_field_id = response.split("ID: ")[1].split()[0]
        print(f"Created field ID: {created_field_id}")
    except IndexError:
        pytest.fail("Could not extract field ID from response")

    print(f"Response: {response}")
    print("✅ create_field passed.")


@pytest.mark.asyncio
async def test_list_fields(client):
    """List fields in MailerLite.

    Verifies that fields can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 10
    sort = "name"

    response = await client.process_query(
        f"Use the list_fields tool to fetch {limit} fields sorted by {sort}. "
        "If successful, start your response with 'Successfully retrieved fields'."
    )

    assert (
        "successfully retrieved fields" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_fields"

    print(f"Response: {response}")
    print("✅ list_fields passed.")


@pytest.mark.asyncio
async def test_update_field(client):
    """Update a field in MailerLite.

    Verifies that a field can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_field_id:
        pytest.skip("No field ID available - run create_field test first")

    new_name = f"Updated Test Field {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the update_field tool to update field with ID {created_field_id} "
        f"and new name {new_name}. If successful, start your response with 'Successfully updated field'."
    )

    assert (
        "successfully updated field" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_field"

    print(f"Response: {response}")
    print("✅ update_field passed.")


# Campaign CRUD tests
@pytest.mark.asyncio
async def test_create_campaign(client):
    """Create a new campaign in MailerLite.

    Verifies that the campaign is created successfully.
    Stores the created campaign ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_campaign_id

    campaign_name = f"Test Campaign {uuid.uuid4()}"
    language_id = 1  # Assuming English language ID
    campaign_type = "regular"
    emails = [
        {
            "subject": "Test Subject",
            "from_name": "Test Sender",
            "from": from_email,
            "content": "Test email content",
        }
    ]

    response = await client.process_query(
        f"Use the create_campaign tool to create a new campaign with name {campaign_name}, "
        f"language_id {language_id}, type {campaign_type}, and emails {emails}. "
        "If successful, start your response with 'Successfully created campaign'. "
        "Send ID of the campaign in the response in format ID: <ID>"
    )

    assert (
        "successfully created campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_campaign"

    # Extract campaign ID from response
    try:
        created_campaign_id = response.split("ID: ")[1].split()[0]
        print(f"Created campaign ID: {created_campaign_id}")
    except IndexError:
        pytest.fail("Could not extract campaign ID from response")

    print(f"Response: {response}")
    print("✅ create_campaign passed.")


@pytest.mark.asyncio
async def test_list_campaigns(client):
    """List campaigns in MailerLite.

    Verifies that campaigns can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 10

    response = await client.process_query(
        f"Use the list_campaigns tool to fetch {limit} campaigns. "
        "If successful, start your response with 'Successfully retrieved campaigns'."
    )

    assert (
        "successfully retrieved campaigns" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_campaigns"

    print(f"Response: {response}")
    print("✅ list_campaigns passed.")


@pytest.mark.asyncio
async def test_get_campaign(client):
    """Get details of a specific campaign in MailerLite.

    Verifies that campaign details can be retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the get_campaign tool to get details of campaign with ID {created_campaign_id}. "
        "If successful, start your response with 'Successfully retrieved campaign'."
    )

    assert (
        "successfully retrieved campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign"

    print(f"Response: {response}")
    print("✅ get_campaign passed.")


@pytest.mark.asyncio
async def test_update_campaign(client):
    """Update a campaign in MailerLite.

    Verifies that a campaign can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    new_name = f"Updated Test Campaign {uuid.uuid4()}"
    new_emails = [
        {
            "subject": "Updated Test Subject",
            "from_name": "Updated Test Sender",
            "from": from_email,
            "content": "Updated test email content",
        }
    ]

    response = await client.process_query(
        f"Use the update_campaign tool to update campaign with ID {created_campaign_id} "
        f"with new name {new_name} and emails {new_emails}. Use language ID 7."
        "If successful, start your response with 'Successfully updated campaign'."
    )

    assert (
        "successfully updated campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_campaign"

    print(f"Response: {response}")
    print("✅ update_campaign passed.")


# Webhook CRUD tests
@pytest.mark.asyncio
async def test_create_webhook(client):
    """Create a new webhook in MailerLite.

    Verifies that the webhook is created successfully.
    Stores the created webhook ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_webhook_id

    webhook_name = f"Test Webhook {uuid.uuid4()}"
    events = ["subscriber.created", "subscriber.updated"]
    url = "https://example.com/webhook"

    response = await client.process_query(
        f"Use the create_webhook tool to create a new webhook with name {webhook_name}, "
        f"events {events}, and url {url}. If successful, start your response with 'Successfully created webhook'. "
        "Send ID of the webhook in the response in format ID: <ID>"
    )

    assert (
        "successfully created webhook" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_webhook"

    # Extract webhook ID from response
    try:
        created_webhook_id = response.split("ID: ")[1].split()[0]
        print(f"Created webhook ID: {created_webhook_id}")
    except IndexError:
        pytest.fail("Could not extract webhook ID from response")

    print(f"Response: {response}")
    print("✅ create_webhook passed.")


@pytest.mark.asyncio
async def test_list_webhooks(client):
    """List webhooks in MailerLite.

    Verifies that webhooks can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_webhooks tool to fetch all webhooks. "
        "If successful, start your response with 'Successfully retrieved webhooks'."
    )

    assert (
        "successfully retrieved webhooks" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_webhooks"

    print(f"Response: {response}")
    print("✅ list_webhooks passed.")


@pytest.mark.asyncio
async def test_get_webhook(client):
    """Get details of a specific webhook in MailerLite.

    Verifies that webhook details can be retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_webhook_id:
        pytest.skip("No webhook ID available - run create_webhook test first")

    response = await client.process_query(
        f"Use the get_webhook tool to get details of webhook with ID {created_webhook_id}. "
        "If successful, start your response with 'Successfully retrieved webhook'."
    )

    assert (
        "successfully retrieved webhook" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_webhook"

    print(f"Response: {response}")
    print("✅ get_webhook passed.")


@pytest.mark.asyncio
async def test_update_webhook(client):
    """Update a webhook in MailerLite.

    Verifies that a webhook can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_webhook_id:
        pytest.skip("No webhook ID available - run create_webhook test first")

    new_name = f"Updated Test Webhook {uuid.uuid4()}"
    new_events = ["subscriber.created", "subscriber.deleted"]
    new_url = "https://example.com/updated-webhook"

    response = await client.process_query(
        f"Use the update_webhook tool to update webhook with ID {created_webhook_id} "
        f"with new name {new_name}, events {new_events}, and url {new_url}. "
        "If successful, start your response with 'Successfully updated webhook'."
    )

    assert (
        "successfully updated webhook" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_webhook"

    print(f"Response: {response}")
    print("✅ update_webhook passed.")


# Form CRUD tests
@pytest.mark.asyncio
async def test_list_forms(client):
    """List forms in MailerLite.

    Verifies that forms can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    form_type = "popup"
    limit = 10

    response = await client.process_query(
        f"Use the list_forms tool to fetch {limit} {form_type} forms. "
        "If successful, start your response with 'Successfully retrieved forms'."
    )

    assert (
        "successfully retrieved forms" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_forms"

    print(f"Response: {response}")
    print("✅ list_forms passed.")


@pytest.mark.asyncio
async def test_get_form(client):
    """Get details of a specific form in MailerLite.

    Verifies that form details can be retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_form_id:
        pytest.skip("No form ID available")

    response = await client.process_query(
        f"Use the get_form tool to get details of form with ID {created_form_id}. "
        "If successful, start your response with 'Successfully retrieved form'."
    )

    assert (
        "successfully retrieved form" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_form"

    print(f"Response: {response}")
    print("✅ get_form passed.")


@pytest.mark.asyncio
async def test_update_form(client):
    """Update a form in MailerLite.

    Verifies that a form can be updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_form_id:
        pytest.skip("No form ID available")

    new_name = f"Updated Test Form {uuid.uuid4()}"

    response = await client.process_query(
        f"Use the update_form tool to update form with ID {created_form_id} "
        f"with new name {new_name}. If successful, start your response with 'Successfully updated form'."
    )

    assert (
        "successfully updated form" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_form"

    print(f"Response: {response}")
    print("✅ update_form passed.")


# Additional campaign operations
@pytest.mark.asyncio
async def test_schedule_campaign(client):
    """Schedule a campaign in MailerLite.

    Verifies that a campaign can be scheduled successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    date = "2024-12-31"
    hours = 12
    minutes = 0

    response = await client.process_query(
        f"Use the schedule_campaign tool to schedule campaign {created_campaign_id} "
        f"for {date} at {hours}:{minutes}. If successful, start your response with 'Successfully scheduled campaign'."
    )

    assert (
        "successfully scheduled campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from schedule_campaign"

    print(f"Response: {response}")
    print("✅ schedule_campaign passed.")


@pytest.mark.asyncio
async def test_cancel_campaign(client):
    """Cancel a scheduled campaign in MailerLite.

    Verifies that a scheduled campaign can be cancelled successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the cancel_campaign tool to cancel campaign with ID {created_campaign_id}. "
        "If successful, start your response with 'Successfully canceled campaign'."
    )

    assert (
        "successfully canceled campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from cancel_campaign"

    print(f"Response: {response}")
    print("✅ cancel_campaign passed.")


# Additional subscriber operations
@pytest.mark.asyncio
async def test_list_subscribers(client):
    """List subscribers in MailerLite.

    Verifies that subscribers can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    limit = 10
    filter_status = "active"

    response = await client.process_query(
        f"Use the list_all_subscribers tool to fetch {limit} subscribers with status {filter_status}. "
        "If successful, start your response with 'Successfully retrieved the subscribers'. "
    )

    assert (
        "successfully retrieved the subscribers" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_all_subscribers"

    print(f"Response: {response}")
    print("✅ list_subscribers passed.")


@pytest.mark.asyncio
async def test_get_group_subscribers(client):
    """Get subscribers belonging to a group in MailerLite.

    Verifies that group subscribers can be retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_group_id:
        pytest.skip("No group ID available - run create_group test first")

    limit = 10
    filter_status = "active"

    response = await client.process_query(
        f"Use the get_group_subscribers tool to fetch {limit} subscribers from group {created_group_id} "
        f"with status {filter_status}. If successful, start your response with 'Successfully retrieved subscribers'."
    )

    assert (
        "successfully retrieved subscribers" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_group_subscribers"

    print(f"Response: {response}")
    print("✅ get_group_subscribers passed.")


@pytest.mark.asyncio
async def test_assign_subscriber_to_group(client):
    """Assign a subscriber to a group in MailerLite.

    Verifies that a subscriber can be assigned to a group successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscriber_id or not created_group_id:
        pytest.skip(
            "No subscriber or group ID available - run create_subscriber and create_group tests first"
        )

    response = await client.process_query(
        f"Use the assign_subscriber_to_group tool to assign subscriber {created_subscriber_id} "
        f"to group {created_group_id}. If successful, start your response with 'Successfully assigned subscriber'."
    )

    assert (
        "successfully assigned subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from assign_subscriber_to_group"

    print(f"Response: {response}")
    print("✅ assign_subscriber_to_group passed.")


@pytest.mark.asyncio
async def test_unassign_subscriber_from_group(client):
    """Remove a subscriber from a group in MailerLite.

    Verifies that a subscriber can be removed from a group successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscriber_id or not created_group_id:
        pytest.skip(
            "No subscriber or group ID available - run create_subscriber and create_group tests first"
        )

    response = await client.process_query(
        f"Use the unassign_subscriber_from_group tool to remove subscriber {created_subscriber_id} "
        f"from group {created_group_id}. If successful, start your response with 'Successfully unassigned subscriber'."
    )

    assert (
        "successfully unassigned subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from unassign_subscriber_from_group"

    print(f"Response: {response}")
    print("✅ unassign_subscriber_from_group passed.")


# Additional campaign operations
@pytest.mark.asyncio
async def test_list_campaign_languages(client):
    """List available campaign languages in MailerLite.

    Verifies that campaign languages can be listed successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the list_campaign_languages tool to fetch all available languages. "
        "If successful, start your response with 'Successfully retrieved campaign languages'."
    )

    assert (
        "successfully retrieved campaign languages" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_campaign_languages"

    print(f"Response: {response}")
    print("✅ list_campaign_languages passed.")


# Delete operations (moved to end)
@pytest.mark.asyncio
async def test_delete_webhook(client):
    """Delete a webhook in MailerLite.

    Verifies that a webhook can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_webhook_id:
        pytest.skip("No webhook ID available - run create_webhook test first")

    response = await client.process_query(
        f"Use the delete_webhook tool to delete webhook with ID {created_webhook_id}. "
        "If successful, start your response with 'Successfully deleted webhook'."
    )

    assert (
        "successfully deleted webhook" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_webhook"

    print(f"Response: {response}")
    print("✅ delete_webhook passed.")


@pytest.mark.asyncio
async def test_delete_campaign(client):
    """Delete a campaign in MailerLite.

    Verifies that a campaign can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the delete_campaign tool to delete campaign with ID {created_campaign_id}. "
        "If successful, start your response with 'Successfully deleted campaign'."
    )

    assert (
        "successfully deleted campaign" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_campaign"

    print(f"Response: {response}")
    print("✅ delete_campaign passed.")


@pytest.mark.asyncio
async def test_delete_field(client):
    """Delete a field in MailerLite.

    Verifies that a field can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_field_id:
        pytest.skip("No field ID available - run create_field test first")

    response = await client.process_query(
        f"Use the delete_field tool to delete field with ID {created_field_id}. "
        "If successful, start your response with 'Successfully deleted field'."
    )

    assert (
        "successfully deleted field" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_field"

    print(f"Response: {response}")
    print("✅ delete_field passed.")


@pytest.mark.asyncio
async def test_delete_group(client):
    """Delete a group in MailerLite.

    Verifies that a group can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_group_id:
        pytest.skip("No group ID available - run create_group test first")

    response = await client.process_query(
        f"Use the delete_group tool to delete group with ID {created_group_id}. "
        "If successful, start your response with 'Successfully deleted group'."
    )

    assert (
        "successfully deleted group" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_group"

    print(f"Response: {response}")
    print("✅ delete_group passed.")


@pytest.mark.asyncio
async def test_delete_subscriber(client):
    """Delete a subscriber in MailerLite.

    Verifies that a subscriber can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_subscriber_id:
        pytest.skip("No subscriber ID available - run create_subscriber test first")

    response = await client.process_query(
        f"Use the delete_subscriber tool to delete subscriber with ID {created_subscriber_id}. "
        "If successful, start your response with 'Successfully deleted subscriber'."
    )

    assert (
        "successfully deleted subscriber" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_subscriber"

    print(f"Response: {response}")
    print("✅ delete_subscriber passed.")


@pytest.mark.asyncio
async def test_delete_form(client):
    """Delete a form in MailerLite.

    Verifies that a form can be deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_form_id:
        pytest.skip("No form ID available")

    response = await client.process_query(
        f"Use the delete_form tool to delete form with ID {created_form_id}. "
        "If successful, start your response with 'Successfully deleted form'."
    )

    assert (
        "successfully deleted form" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_form"

    print(f"Response: {response}")
    print("✅ delete_form passed.")
