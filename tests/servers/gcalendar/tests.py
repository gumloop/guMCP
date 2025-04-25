import pytest
from datetime import datetime, timedelta


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
    # Use str() to convert AnyUrl to string for comparison
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
    # Try with default parameters (primary calendar, 7 days)
    response = await client.process_query(
        "Use the list_events tool to show my calendar events for the next week."
        + "\n\nIf successful, start your response with 'Found these events:'"
    )

    assert response, "No response received when listing events"
    assert "found" in response.lower(), f"Unexpected response format: {response}"

    print("List events (default parameters):")
    print(f"\t{response}")

    # Try with custom parameters
    response = await client.process_query(
        "Use the list_events tool to show me events for the next 7 days with a maximum of 5 results."
        + "\n\nIf successful, start your response with 'Found these events:'"
    )

    assert response, "No response received when listing events with custom parameters"
    assert "found" in response.lower(), f"Unexpected response format: {response}"

    print("List events (custom parameters):")
    print(f"\t{response}")

    print("✅ Successfully tested list_events tool")


@pytest.mark.asyncio
async def test_create_event_tool(client):
    """Test the create_event tool functionality"""
    # Get tomorrow's date
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Create a simple event
    response = await client.process_query(
        f"Use the create_event tool to create a meeting called 'Test Meeting' for tomorrow ({tomorrow}) at 10:00 AM, ending at 11:00 AM."
        + "\n\nIf successful, start your response with 'Event created successfully, Event ID: {event_id}\nEvent details: {event_details}'"
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

    print("Create event result:")
    print(f"\t{response}")
    print(f"\tEvent ID: {event_id}")

    print("✅ Successfully tested create_event tool")

    return event_id  # Return the event ID for use in update_event test


@pytest.mark.asyncio
async def test_update_event_tool(client):
    """Test the update_event tool functionality"""
    # First create an event to update
    event_id = await test_create_event_tool(client)

    # Now update the event
    response = await client.process_query(
        f"Use the update_event tool to update the event with ID '{event_id}'. Change the title to 'Updated Test Meeting' and the description to 'This is a test description'."
        + "\n\nIf successful, start your response with 'Event updated successfully. Updated Test Meeting: "
    )

    assert response, "No response received when updating an event"
    assert (
        "event updated successfully" in response.lower()
    ), f"Event update failed: {response}"
    assert (
        "updated test meeting" in response.lower()
    ), "Updated title not found in response"

    print("Update event result:")
    print(f"\t{response}")

    print("✅ Successfully tested update_event tool")
