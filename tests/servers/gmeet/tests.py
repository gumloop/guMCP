import pytest
import uuid
from datetime import datetime

from tests.utils.test_tools import run_resources_test


# Global variable to store created meeting id
created_meeting_id = None
current_date = datetime.now().strftime("%Y-%m-%d")


@pytest.mark.asyncio
async def test_resources(client):
    response = await run_resources_test(client)
    return response


@pytest.mark.asyncio
async def test_create_meeting(client):
    """Create a new meeting.

    Verifies that the meeting is created successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id
    summary = "Test Meeting " + str(uuid.uuid4())
    description = (
        "This is a test meeting created by the test_create_meeting tool in guMCP."
    )
    start_time = current_date + "T10:00:00"
    end_time = current_date + "T11:00:00"

    response = await client.process_query(
        f"Use the create_meeting tool to create a new meeting with summary {summary}, description {description}, start time {start_time}, and end time {end_time}. "
        "If successful, start your response with 'Here are the meeting details' and then list them. Provide the meeting id in the response. Your response should be in the format 'ID: <meeting_id>'."
    )

    assert (
        "here are the meeting details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_meeting"

    # Extract meeting id from response
    try:
        created_meeting_id = response.lower().split("id: ")[1].split()[0]
        print(f"Created meeting ID: {created_meeting_id}")
    except IndexError:
        pytest.fail("Could not extract meeting ID from response")

    print(f"Response: {response}")
    print("✅ create_meeting passed.")


@pytest.mark.asyncio
async def test_add_attendees(client):
    """Add attendees to a meeting.

    Verifies that the attendees are added to the meeting successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id
    attendees = ["sanskar.khandelwal@cognida.ai"]

    response = await client.process_query(
        f"Use the add_attendees tool to add attendees to the meeting with id {created_meeting_id}. "
        f"The attendees are {attendees}. If successful, start your response with 'Attendees added successfully' and then list the attendees."
    )

    assert (
        "attendees added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_attendees"

    print(f"Response: {response}")
    print("✅ add_attendees passed.")


@pytest.mark.asyncio
async def test_fetch_meetings_by_date(client):
    """Fetch meetings for a specific date.

    Verifies that the meetings for a specific date are fetched successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id
    date = current_date

    response = await client.process_query(
        f"Use the fetch_meetings_by_date tool to fetch meetings for the date {date}. If successful, start your response with 'Here are the meetings' and then list them."
    )

    assert (
        "here are the meetings" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from fetch_meetings_by_date"

    print(f"Response: {response}")
    print("✅ fetch_meetings_by_date passed.")


@pytest.mark.asyncio
async def test_get_meeting_details(client):
    """Get details of a specific meeting.

    Verifies that the meeting details are fetched successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id

    response = await client.process_query(
        f"Use the get_meeting_details tool to get details for the meeting with id {created_meeting_id}. "
        "If successful, start your response with 'Here are the meeting details' and then list them."
    )

    assert (
        "here are the meeting details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ get_meeting_details passed.")


@pytest.mark.asyncio
async def test_update_meeting(client):
    """Update a specific meeting.

    Verifies that the meeting is updated successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id

    summary = "Test Meeting Updated" + str(uuid.uuid4())
    description = (
        "This is a test meeting edited by the test_update_meeting tool in guMCP."
    )
    start_time = current_date + "T11:00:00"
    end_time = current_date + "T12:00:00"

    response = await client.process_query(
        f"Use the update_meeting tool to update the meeting with id {created_meeting_id} with summary {summary}, description {description}, start time {start_time}, and end time {end_time}. "
        "If successful, start your response with 'Here are the meeting details' and then list them."
    )

    assert (
        "here are the meeting details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ update_meeting passed.")


@pytest.mark.asyncio
async def test_delete_meeting(client):
    """Delete a specific meeting.

    Verifies that the meeting is deleted successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_meeting_id

    response = await client.process_query(
        f"Use the delete_meeting tool to delete the meeting with id {created_meeting_id}. "
        "If successful, start your response with 'Meeting deleted successfully'."
    )

    assert (
        "meeting deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"

    print(f"Response: {response}")
    print("✅ delete_meeting passed.")
