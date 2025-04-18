import pytest
import uuid
from datetime import datetime, timedelta

# Global variables to store created meeting IDs
created_meeting_id = None


@pytest.mark.asyncio
async def test_create_meeting(client):
    """Create a new Zoom meeting.

    Verifies that the meeting is created successfully and stores the meeting ID
    for use in subsequent tests.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id

    # Set meeting details
    topic = f"Test Meeting {uuid.uuid4()}"
    # Schedule meeting for tomorrow
    start_time = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    duration = 30
    agenda = "This is a test meeting created by the test_create_meeting tool."

    response = await client.process_query(
        f"""Use the create_meeting tool to create a new meeting
        with topic "{topic}", start time "{start_time}", duration {duration} minutes, 
        and agenda "{agenda}". If successful, start your response with 
        'Created Zoom meeting successfully' and then include the meeting ID in format 'ID: <meeting_id>'."""
    )

    assert (
        "created zoom meeting successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_meeting"

    # Extract meeting ID from response
    try:
        created_meeting_id = response.lower().split("id: ")[1].split()[0]
        print(f"Created meeting ID: {created_meeting_id}")
    except IndexError:
        pytest.fail("Could not extract meeting ID from response")

    print(f"Response: {response}")
    print("✅ create_meeting passed.")


@pytest.mark.asyncio
async def test_get_meeting(client):
    """Get details of a specific Zoom meeting.

    Verifies that the meeting details include the expected topic.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    response = await client.process_query(
        f"""Use the get_meeting tool to fetch details for meeting ID {created_meeting_id}.
        If successful, start your response with 'Here are the Zoom meeting details' and then list them."""
    )

    assert (
        "here are the zoom meeting details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_meeting"

    print(f"Response: {response}")
    print("✅ get_meeting passed.")


@pytest.mark.asyncio
async def test_update_meeting(client):
    """Update a specific Zoom meeting.

    Verifies that the meeting is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    # Set updated meeting details
    updated_topic = f"Updated Test Meeting {uuid.uuid4()}"

    response = await client.process_query(
        f"""Use the update_meeting tool to update meeting ID {created_meeting_id}
        with topic "{updated_topic}".
        If successful, start your response with 'Updated Zoom meeting successfully' and then list the details."""
    )

    assert (
        "updated zoom meeting successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_meeting"

    print(f"Response: {response}")
    print("✅ update_meeting passed.")


@pytest.mark.asyncio
async def test_list_meetings(client):
    """List all scheduled Zoom meetings.

    Verifies that the meeting list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    meeting_type = "scheduled"

    response = await client.process_query(
        f"""Use the list_meetings tool to list {meeting_type} meetings.
        If successful, start your response with 'Here are the Zoom meetings' and then list them."""
    )

    assert (
        "here are the zoom meetings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_meetings"

    print(f"Response: {response}")
    print("✅ list_meetings passed.")


@pytest.mark.asyncio
async def test_list_upcoming_meetings(client):
    """List all upcoming Zoom meetings.

    Verifies that the upcoming meeting list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    response = await client.process_query(
        """Use the list_upcoming_meetings tool to list all upcoming meetings.
        If successful, start your response with 'Here are the upcoming Zoom meetings' and then list them."""
    )

    assert (
        "here are the upcoming zoom meetings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_upcoming_meetings"

    print(f"Response: {response}")
    print("✅ list_upcoming_meetings passed.")


@pytest.mark.asyncio
async def test_fetch_meetings_by_date(client):
    """Fetch all Zoom meetings for a specific date.

    Verifies that the meeting list for the date is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    # Get tomorrow's date
    test_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    response = await client.process_query(
        f"""Use the fetch_meetings_by_date tool to fetch all meetings for date {test_date}.
        If successful, start your response with 'Here are the Zoom meetings for {test_date}' and then list them."""
    )

    assert (
        f"here are the zoom meetings for {test_date}" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_meetings_by_date"

    print(f"Response: {response}")
    print("✅ fetch_meetings_by_date passed.")


@pytest.mark.asyncio
async def test_add_attendees(client):
    """Add attendees to a specific Zoom meeting.

    Verifies that attendees are added successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    # Test email addresses
    attendees = ["test1@example.com", "test2@example.com"]

    response = await client.process_query(
        f"""Use the add_attendees tool to add the following attendees to meeting ID {created_meeting_id}:
        {', '.join(attendees)}. If successful, start your response with 'Added attendees successfully' and
        then list the updated meeting details."""
    )

    assert (
        "added attendees successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_attendees"

    print(f"Response: {response}")
    print("✅ add_attendees passed.")


@pytest.mark.asyncio
async def test_list_all_recordings(client):
    """List all Zoom recordings for a date range.

    Verifies that the recordings list is retrieved successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    # Get date range (last 30 days)
    from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    to_date = datetime.utcnow().strftime("%Y-%m-%d")

    response = await client.process_query(
        f"""Use the list_all_recordings tool to list all recordings from {from_date} to {to_date}.
        If successful, start your response with 'Here are the Zoom recordings' and then list them."""
    )

    assert (
        "here are the zoom recordings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from list_all_recordings"

    print(f"Response: {response}")
    print("✅ list_all_recordings passed.")


@pytest.mark.asyncio
async def test_get_meeting_recordings(client):
    """Get recordings for a specific Zoom meeting.

    This test may be skipped if the meeting doesn't have recordings yet.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    response = await client.process_query(
        f"""Use the get_meeting_recordings tool to fetch recordings for meeting ID {created_meeting_id}.
        If successful, start your response with 'Here are the meeting recordings' and then list them.
        If there are no recordings available, indicate so."""
    )

    # This meeting likely won't have recordings, so just check for valid response
    assert response, "No response returned from get_meeting_recordings"

    print(f"Response: {response}")
    print("✅ get_meeting_recordings passed.")


@pytest.mark.asyncio
async def test_get_meeting_participant_reports(client):
    """Get participant reports for a specific Zoom meeting.

    This test may be skipped if the meeting doesn't have participants yet.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    response = await client.process_query(
        f"""Use the get_meeting_participant_reports tool to fetch participant reports for 
        meeting ID {created_meeting_id}. If successful, start your response with 
        'Here are the meeting participant reports' and then list them.
        If there are no participants yet, indicate so."""
    )

    # This meeting likely won't have participants yet, so just check for valid response
    assert response, "No response returned from get_meeting_participant_reports"

    print(f"Response: {response}")
    print("✅ get_meeting_participant_reports passed.")


@pytest.mark.asyncio
async def test_delete_meeting(client):
    """Delete a specific Zoom meeting.

    Verifies that the meeting is deleted successfully.
    Should be run last as it removes the test meeting.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_meeting_id:
        pytest.skip("No meeting ID available - run create_meeting test first")

    response = await client.process_query(
        f"""Use the delete_meeting tool to delete meeting with ID {created_meeting_id}.
        If successful, start your response with 'Deleted Zoom meeting successfully' and then
        include the meeting ID in format 'ID: <meeting_id>'."""
    )

    assert (
        "deleted zoom meeting successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_meeting"

    print(f"Response: {response}")
    print("✅ delete_meeting passed.")
