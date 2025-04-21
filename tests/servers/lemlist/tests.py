import pytest
import uuid

# Global variables to store created campaign and lead IDs
created_campaign_id = None
created_lead_email = None
created_schedule_id = None


# Create operations
@pytest.mark.asyncio
async def test_create_campaign(client):
    """Create a new campaign in Lemlist.

    Verifies that the campaign is created successfully.
    Stores the created campaign ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_campaign_id
    campaign_name = f"Test Campaign {str(uuid.uuid4())}"

    response = await client.process_query(
        f"Use the create_campaign tool to create a new campaign with name {campaign_name}. "
        "If successful, start your response with 'Created campaign successfully' and then list the campaign ID in format 'ID: <campaign_id>'."
    )

    assert (
        "created campaign successfully" in response.lower()
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
async def test_create_schedule(client):
    """Create a new schedule in Lemlist.

    Verifies that the schedule is created successfully.
    Stores the created schedule ID for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_schedule_id
    schedule_data = {
        "name": f"Test Schedule {str(uuid.uuid4())}",
        "secondsToWait": 1200,
        "timezone": "UTC",
        "start": "09:00",
        "end": "17:00",
        "weekdays": [1, 2, 3, 4, 5],
    }

    response = await client.process_query(
        f"Use the create_schedule tool to create a new schedule with data {schedule_data}. "
        "If successful, start your response with 'Created schedule successfully' and then list the schedule ID in format 'ID: <schedule_id>'."
    )

    assert (
        "created schedule successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_schedule"

    # Extract schedule ID from response
    try:
        created_schedule_id = response.split("ID: ")[1].split()[0]
        print(f"Created schedule ID: {created_schedule_id}")
    except IndexError:
        pytest.fail("Could not extract schedule ID from response")

    print(f"Response: {response}")
    print("✅ create_schedule passed.")


@pytest.mark.asyncio
async def test_create_lead_in_campaign(client):
    """Create a new lead in a Lemlist campaign.

    Verifies that the lead is created successfully.
    Stores the created lead email for use in other tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_lead_email
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    lead_email = f"test_{str(uuid.uuid4())}@example.com"
    lead_data = {
        "firstName": "Test",
        "lastName": "User",
        "companyName": "Test Company",
        "email": lead_email,
    }

    response = await client.process_query(
        f"Use the create_lead_in_campaign tool to create a new lead in campaign {created_campaign_id} "
        f"with data {lead_data}. If successful, start your response with 'Created lead successfully'."
    )

    assert (
        "created lead successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_lead_in_campaign"

    created_lead_email = lead_email
    print(f"Created lead email: {created_lead_email}")
    print(f"Response: {response}")
    print("✅ create_lead_in_campaign passed.")


# Read operations
@pytest.mark.asyncio
async def test_get_team(client):
    """Get team information from Lemlist.

    Verifies that the team information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_team tool to fetch team information. "
        "If successful, start your response with 'Here is the team information' and then list it."
    )

    assert (
        "here is the team information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_team"

    print(f"Response: {response}")
    print("✅ get_team passed.")


@pytest.mark.asyncio
async def test_get_senders(client):
    """Get list of senders from Lemlist.

    Verifies that the senders list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_senders tool to fetch list of senders. "
        "If successful, start your response with 'Here are the senders' and then list them."
    )

    assert (
        "here are the senders" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_senders"

    print(f"Response: {response}")
    print("✅ get_senders passed.")


@pytest.mark.asyncio
async def test_get_credits(client):
    """Get credits information from Lemlist.

    Verifies that the credits information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_credits tool to fetch credits information. "
        "If successful, start your response with 'Here is the credits information' and then list it."
    )

    assert (
        "here is the credits information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_credits"

    print(f"Response: {response}")
    print("✅ get_credits passed.")


@pytest.mark.asyncio
async def test_get_user(client):
    """Get user information from Lemlist.

    Verifies that the user information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_user tool to fetch user information with user_id 'me'. "
        "If successful, start your response with 'Here is the user information' and then list it."
    )

    assert (
        "here is the user information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_user"

    print(f"Response: {response}")
    print("✅ get_user passed.")


@pytest.mark.asyncio
async def test_get_all_campaigns(client):
    """Get all campaigns from Lemlist.

    Verifies that the campaigns list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_all_campaigns tool to fetch all campaigns. "
        "If successful, start your response with 'Here are the campaigns' and then list them."
    )

    assert (
        "here are the campaigns" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_all_campaigns"

    print(f"Response: {response}")
    print("✅ get_all_campaigns passed.")


@pytest.mark.asyncio
async def test_get_campaign(client):
    """Get specific campaign information from Lemlist.

    Verifies that the campaign information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the get_campaign tool to fetch campaign information for campaign {created_campaign_id}. "
        "If successful, start your response with 'Here is the campaign information' and then list it."
    )

    assert (
        "here is the campaign information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign"

    print(f"Response: {response}")
    print("✅ get_campaign passed.")


@pytest.mark.asyncio
async def test_get_all_schedules(client):
    """Get all schedules from Lemlist.

    Verifies that the schedules list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_all_schedules tool to fetch all schedules. "
        "If successful, start your response with 'Here are the schedules' and then list them."
    )

    assert (
        "here are the schedules" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_all_schedules"

    print(f"Response: {response}")
    print("✅ get_all_schedules passed.")


@pytest.mark.asyncio
async def test_get_schedule(client):
    """Get specific schedule information from Lemlist.

    Verifies that the schedule information is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_schedule_id:
        pytest.skip("No schedule ID available - run create_schedule test first")

    response = await client.process_query(
        f"Use the get_schedule tool to fetch schedule information for schedule {created_schedule_id}. "
        "If successful, start your response with 'Here is the schedule information' and then list it."
    )

    assert (
        "here is the schedule information" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_schedule"

    print(f"Response: {response}")
    print("✅ get_schedule passed.")


@pytest.mark.asyncio
async def test_get_campaign_schedules(client):
    """Get schedules for a specific campaign from Lemlist.

    Verifies that the campaign schedules are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the get_campaign_schedules tool to fetch schedules for campaign {created_campaign_id}. "
        "If successful, start your response with 'Here are the campaign schedules' and then list them."
    )

    assert (
        "here are the campaign schedules" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign_schedules"

    print(f"Response: {response}")
    print("✅ get_campaign_schedules passed.")


@pytest.mark.asyncio
async def test_get_all_unsubscribes(client):
    """Get all unsubscribes from Lemlist.

    Verifies that the unsubscribes list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_all_unsubscribes tool to fetch all unsubscribes. "
        "If successful, start your response with 'Here are the unsubscribes' and then list them."
    )

    assert (
        "here are the unsubscribes" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_all_unsubscribes"

    print(f"Response: {response}")
    print("✅ get_all_unsubscribes passed.")


@pytest.mark.asyncio
async def test_get_database_filters(client):
    """Get database filters from Lemlist.

    Verifies that the database filters are retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the get_database_filters tool to fetch database filters. "
        "If successful, start your response with 'Here are the database filters' and then list them."
    )

    assert (
        "here are the database filters" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_database_filters"

    print(f"Response: {response}")
    print("✅ get_database_filters passed.")


# Update operations
@pytest.mark.asyncio
async def test_update_campaign(client):
    """Update campaign settings in Lemlist.

    Verifies that the campaign is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    campaign_name = f"Updated Campaign {str(uuid.uuid4())}"
    update_data = {
        "name": campaign_name,
        "stopOnEmailReplied": True,
        "stopOnMeetingBooked": True,
        "stopOnLinkClicked": True,
    }

    response = await client.process_query(
        f"Use the update_campaign tool to update campaign {created_campaign_id} with data {update_data}. "
        "If successful, start your response with 'Updated campaign successfully'."
    )

    assert (
        "updated campaign successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_campaign"

    print(f"Response: {response}")
    print("✅ update_campaign passed.")


@pytest.mark.asyncio
async def test_update_schedule(client):
    """Update schedule settings in Lemlist.

    Verifies that the schedule is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_schedule_id:
        pytest.skip("No schedule ID available - run create_schedule test first")

    schedule_data = {
        "name": f"Updated Schedule {str(uuid.uuid4())}",
        "secondsToWait": 1800,
        "timezone": "UTC",
        "start": "10:00",
        "end": "18:00",
        "weekdays": [1, 2, 3, 4, 5],
    }

    response = await client.process_query(
        f"Use the update_schedule tool to update schedule {created_schedule_id} with data {schedule_data}. "
        "If successful, start your response with 'Updated schedule successfully'."
    )

    assert (
        "updated schedule successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_schedule"

    print(f"Response: {response}")
    print("✅ update_schedule passed.")


@pytest.mark.asyncio
async def test_associate_schedule_with_campaign(client):
    """Associate a schedule with a campaign in Lemlist.

    Verifies that the schedule is associated with the campaign successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id or not created_schedule_id:
        pytest.skip(
            "No campaign ID or schedule ID available - run create_campaign and create_schedule tests first"
        )

    response = await client.process_query(
        f"Use the associate_schedule_with_campaign tool to associate schedule {created_schedule_id} "
        f"with campaign {created_campaign_id}. If successful, start your response with "
        "'Associated schedule with campaign successfully'."
    )

    assert (
        "associated schedule with campaign successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from associate_schedule_with_campaign"

    print(f"Response: {response}")
    print("✅ associate_schedule_with_campaign passed.")


@pytest.mark.asyncio
async def test_mark_lead_as_interested_in_campaign(client):
    """Mark a lead as interested in a campaign.

    Verifies that the lead is marked as interested successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id or not created_lead_email:
        pytest.skip(
            "No campaign ID or lead email available - run create_campaign and create_lead_in_campaign tests first"
        )

    response = await client.process_query(
        f"Use the mark_lead_as_interested_in_campaign tool to mark lead {created_lead_email} "
        f"as interested in campaign {created_campaign_id}. If successful, start your response with "
        "'Marked lead as interested successfully'."
    )

    assert (
        "marked lead as interested successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from mark_lead_as_interested_in_campaign"

    print(f"Response: {response}")
    print("✅ mark_lead_as_interested_in_campaign passed.")


@pytest.mark.asyncio
async def test_mark_lead_as_not_interested_in_campaign(client):
    """Mark a lead as not interested in a campaign.

    Verifies that the lead is marked as not interested successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id or not created_lead_email:
        pytest.skip(
            "No campaign ID or lead email available - run create_campaign and create_lead_in_campaign tests first"
        )

    response = await client.process_query(
        f"Use the mark_lead_as_not_interested_in_campaign tool to mark lead {created_lead_email} "
        f"as not interested in campaign {created_campaign_id}. If successful, start your response with "
        "'Marked lead as not interested successfully'."
    )

    assert (
        "marked lead as not interested successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from mark_lead_as_not_interested_in_campaign"

    print(f"Response: {response}")
    print("✅ mark_lead_as_not_interested_in_campaign passed.")


@pytest.mark.asyncio
async def test_mark_lead_as_interested_all_campaigns(client):
    """Mark a lead as interested in all campaigns.

    Verifies that the lead is marked as interested in all campaigns successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_lead_email:
        pytest.skip("No lead email available - run create_lead_in_campaign test first")

    response = await client.process_query(
        f"Use the mark_lead_as_interested_all_campaigns tool to mark lead {created_lead_email} "
        "as interested in all campaigns. If successful, start your response with "
        "'Marked lead as interested in all campaigns successfully'."
    )

    assert (
        "marked lead as interested in all campaigns successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from mark_lead_as_interested_all_campaigns"

    print(f"Response: {response}")
    print("✅ mark_lead_as_interested_all_campaigns passed.")


@pytest.mark.asyncio
async def test_mark_lead_as_not_interested_all_campaigns(client):
    """Mark a lead as not interested in all campaigns.

    Verifies that the lead is marked as not interested in all campaigns successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_lead_email:
        pytest.skip("No lead email available - run create_lead_in_campaign test first")

    response = await client.process_query(
        f"Use the mark_lead_as_not_interested_all_campaigns tool to mark lead {created_lead_email} "
        "as not interested in all campaigns. If successful, start your response with "
        "'Marked lead as not interested in all campaigns successfully'."
    )

    assert (
        "marked lead as not interested in all campaigns successfully"
        in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert (
        response
    ), "No response returned from mark_lead_as_not_interested_all_campaigns"

    print(f"Response: {response}")
    print("✅ mark_lead_as_not_interested_all_campaigns passed.")


@pytest.mark.asyncio
async def test_add_unsubscribe(client):
    """Add an email to the unsubscribe list in Lemlist.

    Verifies that the email is added to the unsubscribe list successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    test_email = f"test_{str(uuid.uuid4())}@example.com"

    response = await client.process_query(
        f"Use the add_unsubscribe tool to add email {test_email} to the unsubscribe list. "
        "If successful, start your response with 'Added unsubscribe successfully'."
    )

    assert (
        "added unsubscribe successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_unsubscribe"

    print(f"Response: {response}")
    print("✅ add_unsubscribe passed.")


# Delete operations
@pytest.mark.asyncio
async def test_delete_lead(client):
    """Delete a lead from a campaign.

    Verifies that the lead is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id or not created_lead_email:
        pytest.skip(
            "No campaign ID or lead email available - run create_campaign and create_lead_in_campaign tests first"
        )

    response = await client.process_query(
        f"Use the delete_lead tool to delete lead {created_lead_email} from campaign {created_campaign_id}. "
        "If successful, start your response with 'Deleted lead successfully'."
    )

    assert (
        "deleted lead successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_lead"

    print(f"Response: {response}")
    print("✅ delete_lead passed.")


@pytest.mark.asyncio
async def test_delete_schedule(client):
    """Delete a schedule from Lemlist.

    Verifies that the schedule is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_schedule_id:
        pytest.skip("No schedule ID available - run create_schedule test first")

    response = await client.process_query(
        f"Use the delete_schedule tool to delete schedule {created_schedule_id}. "
        "If successful, start your response with 'Deleted schedule successfully'."
    )

    assert (
        "deleted schedule successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_schedule"

    print(f"Response: {response}")
    print("✅ delete_schedule passed.")


@pytest.mark.asyncio
async def test_delete_unsubscribe(client):
    """Delete an email from the unsubscribe list in Lemlist.

    Verifies that the email is deleted from the unsubscribe list successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    test_email = f"test_{str(uuid.uuid4())}@example.com"

    # First add the email to unsubscribe list
    response = await client.process_query(
        f"Use the add_unsubscribe tool to add email {test_email} to the unsubscribe list. "
        "If successful, start your response with 'Added unsubscribe successfully'."
    )

    assert (
        "added unsubscribe successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    # Now delete it
    response = await client.process_query(
        f"Use the delete_unsubscribe tool to delete email {test_email} from the unsubscribe list. "
        "If successful, start your response with 'Deleted unsubscribe successfully'."
    )

    assert (
        "deleted unsubscribe successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_unsubscribe"

    print(f"Response: {response}")
    print("✅ delete_unsubscribe passed.")


# Export operations
@pytest.mark.asyncio
async def test_start_lemlist_campaign_export(client):
    """Start a campaign export in Lemlist.

    Verifies that the campaign export is started successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the start_lemlist_campaign_export tool to start export for campaign {created_campaign_id}. "
        "If successful, start your response with 'Started campaign export successfully'."
    )

    assert (
        "started campaign export successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from start_lemlist_campaign_export"

    print(f"Response: {response}")
    print("✅ start_lemlist_campaign_export passed.")


@pytest.mark.asyncio
async def test_get_campaign_export_status(client):
    """Get campaign export status from Lemlist.

    Verifies that the campaign export status is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    # First start an export
    response = await client.process_query(
        f"Use the start_lemlist_campaign_export tool to start export for campaign {created_campaign_id}. "
        "If successful, start your response with 'Started campaign export successfully'."
        "Provide export ID in format 'ID: <export_id>'."
    )

    assert (
        "started campaign export successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    # Extract export ID
    try:
        export_id = response.lower().split(": ")[1].split()[0]
        print(f"Export ID: {export_id}")
    except IndexError:
        pytest.fail("Could not extract export ID from response")

    # Now get the status
    response = await client.process_query(
        f"Use the get_campaign_export_status tool to check status for campaign {created_campaign_id} "
        f"and export {export_id}. If successful, start your response with 'Export status'."
    )

    assert (
        "export status" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_campaign_export_status"

    print(f"Response: {response}")
    print("✅ get_campaign_export_status passed.")


@pytest.mark.asyncio
async def test_export_lemlist_campaign(client):
    """Export a campaign in Lemlist.

    Verifies that the campaign export is set up successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    # First start an export
    response = await client.process_query(
        f"Use the start_lemlist_campaign_export tool to start export for campaign {created_campaign_id}. "
        "If successful, start your response with 'Started campaign export successfully'."
        "Provide export ID in format 'ID: <export_id>'."
    )

    assert (
        "started campaign export successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    # Extract export ID
    try:
        export_id = response.split("ID: ")[1].split()[0]
        print(f"Export ID: {export_id}")
    except IndexError:
        pytest.fail("Could not extract export ID from response")

    # Set email for export notification
    test_email = "test@example.com"
    response = await client.process_query(
        f"Use the export_lemlist_campaign tool to set email {test_email} for campaign {created_campaign_id} "
        f"and export {export_id}. If successful, start your response with 'Set export email successfully'."
    )

    assert (
        "set export email successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from export_lemlist_campaign"

    print(f"Response: {response}")
    print("✅ export_lemlist_campaign passed.")


@pytest.mark.asyncio
async def test_export_unsubscribes(client):
    """Export unsubscribes from Lemlist.

    Verifies that the unsubscribes export is started successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        "Use the export_unsubscribes tool to export all unsubscribes. "
        "If successful, start your response with 'Started unsubscribes export successfully'."
    )

    assert (
        "started unsubscribes export successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from export_unsubscribes"

    print(f"Response: {response}")
    print("✅ export_unsubscribes passed.")


@pytest.mark.asyncio
async def test_pause_lemlist_campaign(client):
    """Pause a campaign in Lemlist.

    Verifies that the campaign is paused successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_campaign_id:
        pytest.skip("No campaign ID available - run create_campaign test first")

    response = await client.process_query(
        f"Use the pause_lemlist_campaign tool to pause campaign {created_campaign_id}. "
        "If successful, start your response with 'Paused campaign successfully'."
    )

    assert (
        "paused campaign successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from pause_lemlist_campaign"

    print(f"Response: {response}")
    print("✅ pause_lemlist_campaign passed.")
