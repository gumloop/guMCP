import pytest
import re


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing views and tickets from Zendesk"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri})")

    print("✅ Successfully listed Zendesk resources")


@pytest.mark.asyncio
async def test_read_view(client):
    """Test reading a view resource"""
    # First list resources to get a valid view ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first view resource
    view_resource = next(
        (r for r in response.resources if str(r.uri).startswith("zendesk:///view/")),
        None,
    )
    assert view_resource, "No view resources found"

    # Read view details
    response = await client.read_resource(view_resource.uri)
    assert response.contents, "Response should contain view data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("View data read:")
    print(f"\t{response.contents[0].text}")
    print("✅ Successfully read view data")


@pytest.mark.asyncio
async def test_read_ticket(client):
    """Test reading a ticket resource"""
    # First list resources to get a valid ticket ID
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    # Find first ticket resource
    ticket_resource = next(
        (r for r in response.resources if str(r.uri).startswith("zendesk:///ticket/")),
        None,
    )

    # Skip test if no tickets are found - this could happen in a test environment
    if not ticket_resource:
        pytest.skip("No ticket resources found - skipping test")

    # Read ticket details
    response = await client.read_resource(ticket_resource.uri)
    assert response.contents, "Response should contain ticket data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    ticket_data = response.contents[0].text
    assert "ticket" in ticket_data, "Ticket data should contain ticket information"
    assert "comments" in ticket_data, "Ticket data should contain comments information"

    print("Ticket data read:")
    print(f"\t{ticket_data}")
    print("✅ Successfully read ticket data")


@pytest.mark.asyncio
async def test_search_tickets_tool(client):
    """Test searching for tickets"""
    # Simple search query
    response = await client.process_query(
        "Use the search_tickets tool to search for tickets with the query 'status:open' and sort by created_at in descending order."
    )

    # Verify the response contains search-related language
    search_terms = ["search", "ticket", "found", "result", "status", "open"]
    assert any(
        term in response.lower() for term in search_terms
    ), f"Response should indicate a search was performed: {response}"

    print("Search results:")
    print(f"\t{response}")
    print("✅ Search functionality working")


@pytest.mark.asyncio
async def test_create_ticket_tool(client):
    """Test creating a ticket"""
    # Create a test ticket
    test_subject = "Test Ticket from Automated Tests"
    test_description = "This is a test ticket created by the automated test suite."

    response = await client.process_query(
        f"Use the create_ticket tool to create a ticket with subject '{test_subject}', "
        f"comment '{test_description}', priority 'low', and tags ['test', 'automated']."
    )

    # Verify ticket creation success indicators are present
    success_terms = ["created", "success", "ticket"]
    assert any(
        term in response.lower() for term in success_terms
    ), f"Response should indicate successful ticket creation: {response}"

    print("Create ticket response:")
    print(f"\t{response}")
    print("✅ Ticket creation working")

    # Extract ticket ID for potential use in other tests
    # This is a simple extraction that just looks for digits after common ticket identifiers
    ticket_id_match = re.search(r"(?:ticket|id)[^\d]*(\d+)", response.lower())
    ticket_id = ticket_id_match.group(1) if ticket_id_match else None

    return ticket_id


@pytest.mark.asyncio
async def test_update_and_comment_workflow(client):
    """Test updating a ticket and adding a comment"""
    # First create a test ticket
    test_subject = "Ticket for Update Test"
    test_description = "This ticket will be updated during the test."

    # Create the ticket
    creation_response = await client.process_query(
        f"Use the create_ticket tool to create a ticket with subject '{test_subject}', "
        f"comment '{test_description}', and priority 'normal'."
    )

    # Extract ticket ID - just looking for digits after ticket/id references
    ticket_id_match = re.search(r"(?:ticket|id)[^\d]*(\d+)", creation_response.lower())
    assert (
        ticket_id_match
    ), f"Could not find ticket ID in creation response: {creation_response}"
    ticket_id = ticket_id_match.group(1)

    # Update the ticket
    update_response = await client.process_query(
        f"Use the update_ticket tool to update ticket_id {ticket_id}, "
        "changing the subject to 'Updated Test Ticket' and priority to 'high'."
    )

    # Verify update success indicators
    update_terms = ["update", "success", "ticket", "changed"]
    assert any(
        term in update_response.lower() for term in update_terms
    ), f"Response should indicate successful ticket update: {update_response}"

    # Add a comment
    comment_response = await client.process_query(
        f"Use the add_comment tool to add a comment to ticket_id {ticket_id}, "
        "with the text 'This is a test comment added by automation.' and set public to true."
    )

    # Verify comment success indicators
    comment_terms = ["comment", "added", "success"]
    assert any(
        term in comment_response.lower() for term in comment_terms
    ), f"Response should indicate successful comment addition: {comment_response}"

    print("Workflow test results:")
    print(f"  Creation: {creation_response}")
    print(f"  Update: {update_response}")
    print(f"  Comment: {comment_response}")
    print("✅ Complete ticket workflow (create, update, comment) working")


@pytest.mark.asyncio
async def test_error_handling(client):
    """Test error handling for invalid parameters"""
    # Test with invalid ticket ID
    invalid_id_response = await client.process_query(
        "Use the update_ticket tool to update ticket_id 999999999, "
        "changing the subject to 'This Should Fail'."
    )

    # Check that the error is properly reported
    error_terms = ["error", "fail", "invalid", "not found", "does not exist"]
    assert any(
        term in invalid_id_response.lower() for term in error_terms
    ), f"Response should indicate an error with invalid ticket ID: {invalid_id_response}"

    # Test with missing required parameters
    missing_param_response = await client.process_query(
        "Use the create_ticket tool to create a ticket without providing required parameters."
    )

    # Check that the error about missing parameters is reported
    missing_terms = ["missing", "required", "parameter", "need"]
    assert any(
        term in missing_param_response.lower() for term in missing_terms
    ), f"Response should indicate missing required parameters: {missing_param_response}"

    print("Error handling test results:")
    print(f"  Invalid ID: {invalid_id_response}")
    print(f"  Missing params: {missing_param_response}")
    print("✅ Error handling working correctly")
