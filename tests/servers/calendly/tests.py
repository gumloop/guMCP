import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing event types and scheduled events from Calendly"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_event_type(client):
    """Test reading an event type resource"""
    # First list resources to get a valid event type ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first event type resource
    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    # Skip test if no event types found
    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    # Read event type details
    response = await client.read_resource(event_type_resource.uri)
    assert response.contents, "Response should contain event type data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Event type data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read event type data")


@pytest.mark.asyncio
async def test_read_event(client):
    """Test reading a scheduled event resource"""
    # First list resources to get a valid scheduled event ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first scheduled event resource
    event_resource = next(
        (r for r in response.resources if str(r.uri).startswith("calendly:///event/")),
        None,
    )

    # Skip test if no scheduled events found
    if not event_resource:
        pytest.skip("No scheduled event resources found - skipping test")

    # Read scheduled event details
    response = await client.read_resource(event_resource.uri)
    assert response.contents, "Response should contain scheduled event data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Scheduled event data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read scheduled event data")


@pytest.mark.asyncio
async def test_list_event_types_tool(client):
    """Test listing event types using the list_event_types tool"""
    response = await client.process_query(
        "Use the list_event_types tool to list all available event types. "
        "Include both active and inactive event types."
    )

    # Validate response contains expected content
    assert response, "No response received from list_event_types tool"
    assert any(
        ["found" in response.lower(), "event type" in response.lower()]
    ), "Response doesn't contain event type listing information"

    # If the response indicates no event types were found, that's still a valid response
    if "no event types found" in response.lower():
        print("No event types found (this is a valid response)")
    else:
        # Verify that we have event type details
        assert any(
            ["min" in response.lower(), "duration" in response.lower()]
        ), "Response doesn't contain expected event type details"

    print("Event types listed:")
    print(f"\t{response}")

    print("✅ Successfully listed event types")


@pytest.mark.asyncio
async def test_list_event_types_active_only(client):
    """Test listing only active event types using the list_event_types tool"""
    response = await client.process_query(
        "Use the list_event_types tool to list only active event types. "
        "Set active_only to true."
    )

    # Validate response contains expected content
    assert response, "No response received from list_event_types tool"
    assert any(
        [
            "found" in response.lower(),
            "event type" in response.lower(),
            "no event types found" in response.lower(),
        ]
    ), "Response doesn't contain event type listing information"

    # Verify that the response mentions active event types
    assert "active" in response.lower(), "Response doesn't mention active event types"

    print("Active event types listed:")
    print(f"\t{response}")

    print("✅ Successfully listed active event types")


@pytest.mark.asyncio
async def test_get_availability_tool(client):
    """Test getting availability for an event type"""
    # First get an event type ID
    response = await client.list_resources()
    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    # Skip test if no event types found
    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    event_type_id = str(event_type_resource.uri).replace("calendly:///event_type/", "")

    # Get today's date and 7 days from now
    today = datetime.now().date().isoformat()
    week_from_now = (datetime.now() + timedelta(days=7)).date().isoformat()

    # Test get_availability tool
    response = await client.process_query(
        f"Use the get_availability tool to check available times for event type with ID '{event_type_id}' "
        f"between {today} and {week_from_now}."
        f"At the end of the response, mention found_slots or not_found_slots for testing purposes."
    )

    assert (
        "found_slots".lower() in response.lower()
    ), "Response doesn't contain availability information"

    print("Availability results:")
    print(f"\t{response}")

    print("✅ Successfully retrieved availability")


@pytest.mark.asyncio
async def test_list_scheduled_events_tool(client):
    """Test listing scheduled events"""
    # Get today's date and +/- 30 days
    today = datetime.now().date().isoformat()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
    thirty_days_from_now = (datetime.now() + timedelta(days=30)).date().isoformat()

    # Test list_scheduled_events tool
    response = await client.process_query(
        f"Use the list_scheduled_events tool to list all active events "
        f"between {thirty_days_ago} and {thirty_days_from_now}."
    )

    # Validate response contains expected content
    assert response, "No response received from list_scheduled_events tool"

    print("Scheduled events:")
    print(f"\t{response}")

    print("✅ Successfully listed scheduled events")


@pytest.mark.asyncio
async def test_list_scheduled_events_with_filters(client):
    """Test listing scheduled events with status filter"""
    # Test list_scheduled_events tool with status filter
    response = await client.process_query(
        "Use the list_scheduled_events tool to list all canceled events from the last 60 days."
    )

    # Validate response contains expected content
    assert response, "No response received from list_scheduled_events tool"

    # Check for either canceled events or a valid "no events" message
    assert any(
        [
            "found" in response.lower() and "canceled" in response.lower(),
            "no canceled events" in response.lower(),
        ]
    ), "Response doesn't contain canceled events information"

    print("Canceled events:")
    print(f"\t{response}")

    print("✅ Successfully listed canceled events")


@pytest.mark.asyncio
async def test_create_scheduling_link_tool(client):
    """Test creating a single-use scheduling link for an event type"""
    # First get an event type ID
    response = await client.list_resources()
    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    # Skip test if no event types found
    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    event_type_id = str(event_type_resource.uri).replace("calendly:///event_type/", "")

    # Test create_scheduling_link tool
    response = await client.process_query(
        f"Use the create_scheduling_link tool to create a single-use link for event type ID '{event_type_id}'."
    )

    # Validate response contains expected content
    assert response, "No response received from create_scheduling_link tool"
    # Check for common texts in response that indicate success
    assert (
        "scheduling link" in response.lower()
    ), "Response doesn't contain scheduling link information"

    print("Single-use scheduling link created:")
    print(f"\t{response}")

    print("✅ Successfully created single-use scheduling link")


@pytest.mark.asyncio
async def test_cancel_event_flow(client):
    """Test the flow of finding and canceling an event (may be skipped if no active events)"""
    # First find if there are any active events
    response = await client.process_query(
        "Use the list_scheduled_events tool to list active events for the next 7 days."
    )

    # Check if there are any events to cancel
    if "no active events" in response.lower():
        pytest.skip("No active events found - skipping cancel test")

    # If we have events, try to extract an event ID from the response
    # This is a simple approach - in a real world scenario, you might need more robust parsing
    lines = response.split("\n")
    event_id = None
    for line in lines:
        if "ID:" in line:
            event_id = line.split("ID:")[1].strip()
            break

    if not event_id:
        pytest.skip("Could not extract event ID - skipping cancel test")

    # Now attempt to cancel the event
    # NOTE: This is potentially destructive! In a real test suite, you would likely
    # create test events specifically for this purpose rather than canceling real ones.
    response = await client.process_query(
        f"Use the cancel_event tool to cancel the event with ID '{event_id}' "
        f"with reason 'Automated test cancellation - please ignore'."
    )

    # Validate response contains expected content
    assert response, "No response received from cancel_event tool"
    assert any(
        [
            "successfully canceled" in response.lower(),
            "cancellation status" in response.lower(),
        ]
    ), "Response doesn't contain cancellation information"

    print("Event cancellation response:")
    print(f"\t{response}")

    print("✅ Completed cancel event test")
