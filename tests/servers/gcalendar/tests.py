import pytest
from datetime import datetime, timedelta

# Global variables to store shared test data
TEST_EVENT_ID = None


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing calendars from Google Calendar"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Calendars found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed calendars")


@pytest.mark.asyncio
async def test_read_calendar(client):
    """Test reading a specific calendar"""
    # First list calendars to get a valid calendar ID
    response = await client.list_resources()

    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    resources = response.resources

    # Try to read at least one regular calendar
    regular_calendar = next((r for r in resources), None)

    if regular_calendar:
        calendar_response = await client.read_resource(regular_calendar.uri)
        assert len(
            calendar_response.contents[0].text
        ), f"Response should contain calendar events: {calendar_response}"

        print("Calendar events read:")
        print(f"\t{calendar_response.contents[0].text}")

    print("✅ Successfully read calendar resources")


@pytest.mark.asyncio
async def test_list_events_tool(client):
    """Test the list_events tool functionality"""
    # Use custom parameters for a single comprehensive test
    response = await client.process_query(
        "Use the list_events tool to show me events for the next 7 days with a maximum of 5 results."
        + "\n\nIf successful, start your response with 'Found these events:'"
    )

    assert response, "No response received when listing events"
    assert "found" in response.lower(), f"Unexpected response format: {response}"

    print("List events result:")
    print(f"\t{response}")

    print("✅ Successfully tested list_events tool")


@pytest.mark.asyncio
async def test_create_event_tool(client):
    """Test the create_event tool functionality"""
    global TEST_EVENT_ID

    # Get tomorrow's date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Create a simple event
    response = await client.process_query(
        f"Use the create_event tool to create a meeting called 'Test Meeting' for tomorrow ({tomorrow}) at 10:00 AM, ending at 11:00 AM."
        + "\n\nIf successful, start your response with 'Event created successfully and return the Event ID:'"
    )

    assert response, "No response received when creating an event"
    assert (
        "event created successfully" in response.lower()
    ), f"Event creation failed: {response}"

    # Extract the event ID for cleanup/verification
    event_id = None
    for line in response.split("\n"):
        if "Event ID:" in line:
            event_id = line.split("Event ID:")[1].strip()
            break

    assert event_id, "Could not find event ID in the response"

    # Store the event ID in the global variable for other tests
    TEST_EVENT_ID = event_id

    print("✅ Successfully tested create_event tool")


@pytest.mark.asyncio
async def test_update_event_tool(client):
    """Test the update_event tool functionality"""
    global TEST_EVENT_ID

    # Skip if no event ID is available
    if not TEST_EVENT_ID:
        # Create an event if none exists
        await test_create_event_tool(client)
        if not TEST_EVENT_ID:
            pytest.skip("Failed to create event for update test")

    # Now update the event
    response = await client.process_query(
        f"Use the update_event tool to update the event with ID '{TEST_EVENT_ID}'. Change the title to 'Updated Test Meeting' and the description to 'This is a test description'."
        + "\n\nIf successful, start your response with 'Event updated successfully'"
    )

    assert response, "No response received when updating an event"
    assert (
        "event updated successfully" in response.lower()
    ), f"Event update failed: {response}"

    print("Update event result:")
    print(f"\t{response}")

    print("✅ Successfully tested update_event tool")


@pytest.mark.asyncio
async def test_update_attendee_status_tool(client):
    """Test the update_attendee_status tool functionality"""
    # Now update the attendee status
    response = await client.process_query(
        f"Use the update_attendee_status tool to update the attendee 'test@example.com' for event with ID '{TEST_EVENT_ID}'. "
        f"Set their response status to 'accepted'."
        + "\n\nIf successful, start your response with 'Attendee status updated'"
    )

    assert response, "No response received when updating attendee status"
    assert (
        "attendee status updated" in response.lower()
    ), f"Attendee status update failed: {response}"

    print("Update attendee status result:")
    print(f"\t{response}")

    print("✅ Successfully tested update_attendee_status tool")


@pytest.mark.asyncio
async def test_check_free_slots_tool(client):
    """Test the check_free_slots tool functionality"""
    # Get dates for checking free slots
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    start_time = f"{tomorrow_str} 09:00"
    end_time = f"{tomorrow_str} 17:00"

    response = await client.process_query(
        f"Use the check_free_slots tool to find available 30-minute slots in my calendar tomorrow between 9:00 AM and 5:00 PM. "
        f"That would be from {start_time} to {end_time}."
        + "\n\nIf successful, start your response with 'Found available time slots'"
    )

    assert response, "No response received when checking free slots"
    assert (
        "found available time slots" in response.lower()
    ), f"Free slots check failed: {response}"

    print("Check free slots result:")
    print(f"\t{response}")

    print("✅ Successfully tested check_free_slots tool")


@pytest.mark.asyncio
async def test_delete_event_tool(client):
    """Test the delete_event tool functionality"""
    global TEST_EVENT_ID

    # Skip if no event ID is available
    if not TEST_EVENT_ID:
        # Create an event if none exists
        await test_create_event_tool(client)
        if not TEST_EVENT_ID:
            pytest.skip("Failed to create event for delete test")

    # Now delete the event
    response = await client.process_query(
        f"Use the delete_event tool to delete the event with ID '{TEST_EVENT_ID}'."
        + "\n\nIf successful, start your response with 'Event deleted successfully'"
    )

    assert response, "No response received when deleting an event"
    assert (
        "event deleted successfully" in response.lower()
    ), f"Event deletion failed: {response}"

    print("Delete event result:")
    print(f"\t{response}")

    print("✅ Successfully tested delete_event tool")
