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
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    response = await client.read_resource(event_type_resource.uri)
    assert response.contents, "Response should contain event type data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Event type data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read event type data")


@pytest.mark.asyncio
async def test_read_event(client):
    """Test reading a scheduled event resource"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    event_resource = next(
        (r for r in response.resources if str(r.uri).startswith("calendly:///event/")),
        None,
    )

    if not event_resource:
        pytest.skip("No scheduled event resources found - skipping test")

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
        "Include both active and inactive event types. "
        "If successful, start your response with 'Found event types:' and list them. "
        "If no event types are found, start with 'No event types found:'."
    )

    assert response, "No response received from list_event_types tool"
    assert any(
        ["Found event types:" in response, "No event types found:" in response]
    ), "Response must start with either 'Found event types:' or 'No event types found:'"

    if "Found event types:" in response:
        assert (
            "min" in response.lower() or "duration" in response.lower()
        ), "Response should contain event type details"
    else:
        assert (
            "no event types" in response.lower()
        ), "Response should indicate no event types found"

    print("Event types listed:")
    print(f"\t{response}")

    print("✅ Successfully listed event types")


@pytest.mark.asyncio
async def test_list_event_types_active_only(client):
    """Test listing only active event types using the list_event_types tool"""
    response = await client.process_query(
        "Use the list_event_types tool to list only active event types. "
        "Set active_only to true. "
        "If successful, start your response with 'Found active event types:' and list them. "
        "If no active event types are found, start with 'No active event types found:'."
    )

    assert response, "No response received from list_event_types tool"
    assert any(
        [
            "Found active event types:" in response,
            "No active event types found:" in response,
        ]
    ), "Response must start with either 'Found active event types:' or 'No active event types found:'"

    if "Found active event types:" in response:
        assert (
            "active" in response.lower()
        ), "Response should mention active event types"
    else:
        assert (
            "no active" in response.lower()
        ), "Response should indicate no active event types found"

    print("Active event types listed:")
    print(f"\t{response}")

    print("✅ Successfully listed active event types")


@pytest.mark.asyncio
async def test_get_availability_tool(client):
    """Test getting availability for an event type"""
    response = await client.list_resources()
    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    event_type_id = str(event_type_resource.uri).replace("calendly:///event_type/", "")

    today = datetime.now().date().isoformat()
    week_from_now = (datetime.now() + timedelta(days=7)).date().isoformat()

    response = await client.process_query(
        f"Use the get_availability tool to check available times for event type with ID '{event_type_id}' "
        f"between {today} and {week_from_now}. "
        f"If successful, start your response with 'Found available slots:' and list them. "
        f"If no slots are found, start with 'No available slots found:'."
    )

    assert response, "No response received from get_availability tool"
    assert any(
        ["Found available slots:" in response, "No available slots found:" in response]
    ), "Response must start with either 'Found available slots:' or 'No available slots found:'"

    if "Found available slots:" in response:
        assert (
            "available" in response.lower()
        ), "Response should mention available slots"
    else:
        assert (
            "no available" in response.lower()
        ), "Response should indicate no available slots"

    print("Availability results:")
    print(f"\t{response}")

    print("✅ Successfully retrieved availability")


@pytest.mark.asyncio
async def test_list_scheduled_events_tool(client):
    """Test listing scheduled events"""
    today = datetime.now().date().isoformat()
    thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()
    thirty_days_from_now = (datetime.now() + timedelta(days=30)).date().isoformat()

    response = await client.process_query(
        f"Use the list_scheduled_events tool to list all active events "
        f"between {thirty_days_ago} and {thirty_days_from_now}. "
        f"If successful, start your response with 'Found scheduled events:' and list them. "
        f"If no events are found, start with 'No scheduled events found:'."
    )

    assert response, "No response received from list_scheduled_events tool"
    assert any(
        [
            "Found scheduled events:" in response,
            "No scheduled events found:" in response,
        ]
    ), "Response must start with either 'Found scheduled events:' or 'No scheduled events found:'"

    if "Found scheduled events:" in response:
        assert "event" in response.lower(), "Response should mention events"
    else:
        assert (
            "no events" in response.lower()
        ), "Response should indicate no events found"

    print("Scheduled events:")
    print(f"\t{response}")

    print("✅ Successfully listed scheduled events")


@pytest.mark.asyncio
async def test_list_scheduled_events_with_filters(client):
    """Test listing scheduled events with status filter"""
    response = await client.process_query(
        "Use the list_scheduled_events tool to list all canceled events from the last 60 days. "
        "If successful, start your response with 'Found canceled events:' and list them. "
        "If no canceled events are found, start with 'No canceled events found:'."
    )

    assert response, "No response received from list_scheduled_events tool"
    assert any(
        ["Found canceled events:" in response, "No canceled events found:" in response]
    ), "Response must start with either 'Found canceled events:' or 'No canceled events found:'"

    if "Found canceled events:" in response:
        assert "canceled" in response.lower(), "Response should mention canceled events"
    else:
        assert (
            "no canceled" in response.lower()
        ), "Response should indicate no canceled events found"

    print("Canceled events:")
    print(f"\t{response}")

    print("✅ Successfully listed canceled events")


@pytest.mark.asyncio
async def test_create_scheduling_link_tool(client):
    """Test creating a single-use scheduling link for an event type"""
    response = await client.list_resources()
    event_type_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("calendly:///event_type/")
        ),
        None,
    )

    if not event_type_resource:
        pytest.skip("No event type resources found - skipping test")

    event_type_id = str(event_type_resource.uri).replace("calendly:///event_type/", "")

    response = await client.process_query(
        f"Use the create_scheduling_link tool to create a single-use link for event type ID '{event_type_id}'. "
        f"If successful, start your response with 'Created scheduling link:' and include the link. "
        f"If unsuccessful, start with 'Failed to create scheduling link:'."
    )

    assert response, "No response received from create_scheduling_link tool"
    assert any(
        [
            "Created scheduling link:" in response,
            "Failed to create scheduling link:" in response,
        ]
    ), "Response must start with either 'Created scheduling link:' or 'Failed to create scheduling link:'"

    if "Created scheduling link:" in response:
        assert "link" in response.lower(), "Response should contain the scheduling link"
    else:
        assert "failed" in response.lower(), "Response should indicate failure"

    print("Single-use scheduling link created:")
    print(f"\t{response}")

    print("✅ Successfully created single-use scheduling link")


@pytest.mark.asyncio
async def test_cancel_event_flow(client):
    """Test the flow of finding and canceling an event (may be skipped if no active events)"""
    response = await client.process_query(
        "Use the list_scheduled_events tool to list active events for the next 7 days. "
        "If successful, start your response with 'Found active events:' and list them. "
        "If no events are found, start with 'No active events found:'."
    )

    if "No active events found:" in response:
        pytest.skip("No active events found - skipping cancel test")

    lines = response.split("\n")
    event_id = None
    for line in lines:
        if "ID:" in line:
            event_id = line.split("ID:")[1].strip()
            break

    if not event_id:
        pytest.fail("Could not extract event ID - test failed")

    response = await client.process_query(
        f"Use the cancel_event tool to cancel the event with ID '{event_id}' "
        f"with reason 'Automated test cancellation - please ignore'. "
        f"If successful, start your response with 'Successfully canceled event:' and include the event ID. "
        f"If unsuccessful, start with 'Failed to cancel event:'."
    )

    assert response, "No response received from cancel_event tool"
    assert any(
        [
            "Successfully canceled event:" in response,
            "Failed to cancel event:" in response,
        ]
    ), "Response must start with either 'Successfully canceled event:' or 'Failed to cancel event:'"

    if "Successfully canceled event:" in response:
        assert "canceled" in response.lower(), "Response should confirm cancellation"
    else:
        assert "failed" in response.lower(), "Response should indicate failure"
    print("Event cancellation response:")
    print(f"\t{response}")

    print("✅ Completed cancel event test")
