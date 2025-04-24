import pytest
import uuid

# Global variables to store created contact IDs
created_contact_email = None
created_contact_user_id = str(uuid.uuid4())[:4]

# Replace with your transactional ID
test_transactional_id = ""


@pytest.mark.asyncio
async def test_add_contact(client):
    """Add a new contact to Loops.

    Verifies that the contact is added successfully and stores the contact details.

    Args:
        client: The test client fixture for the MCP server.
    """
    global created_contact_email, created_contact_user_id

    # Generate unique test data
    test_email = f"test_{uuid.uuid4()}@example.com"
    test_first_name = "Test"
    test_last_name = "User"

    response = await client.process_query(
        f"""Use the add_contact tool to create a new contact with:
        email: {test_email}
        created_contact_user_id: {created_contact_user_id}
        first_name: {test_first_name}
        last_name: {test_last_name}
        subscribed: true
        If successful, start your response with 'Contact added successfully'."""
    )

    assert (
        "contact added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_contact"

    # Store contact details for later tests
    created_contact_email = test_email
    print(f"Response: {response}")
    print("✅ add_contact passed.")


@pytest.mark.asyncio
async def test_add_custom_property(client):
    """Add a custom property to the contact.

    Verifies that a custom property can be added to the contact.

    Args:
        client: The test client fixture for the MCP server.
    """
    test_property = {"name": f"test_property_{uuid.uuid4()}", "type": "string"}

    response = await client.process_query(
        f"""Use the add_custom_property tool to add a custom property with:
        body: {test_property}
        If successful, start your response with 'Custom property added successfully'."""
    )

    assert (
        "custom property added successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from add_custom_property"

    print(f"Response: {response}")
    print("✅ add_custom_property passed.")


@pytest.mark.asyncio
async def test_get_contact_by_email(client):
    """Get contact details by email.

    Verifies that the contact details can be retrieved by email.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_email:
        pytest.skip("No contact email available - run add_contact test first")

    response = await client.process_query(
        f"Use the get_contact_by_email tool to fetch details for contact with email {created_contact_email}. "
        "If successful, start your response with 'Here are the contact details'."
    )

    assert (
        "here are the contact details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_contact_by_email"

    print(f"Response: {response}")
    print("✅ get_contact_by_email passed.")


@pytest.mark.asyncio
async def test_get_contact_by_user_id(client):
    """Get contact details by user ID.

    Verifies that the contact details can be retrieved by user ID.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_user_id:
        pytest.skip("No contact user ID available - run add_contact test first")

    response = await client.process_query(
        f"Use the get_contact_by_user_id tool to fetch details for contact with user ID {created_contact_user_id}. "
        "If successful, start your response with 'Here are the contact details'."
    )

    assert (
        "here are the contact details" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from get_contact_by_user_id"

    print(f"Response: {response}")
    print("✅ get_contact_by_user_id passed.")


@pytest.mark.asyncio
async def test_update_contact_by_email(client):
    """Update contact details by email.

    Verifies that the contact details can be updated by email.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_email:
        pytest.skip("No contact email available - run add_contact test first")

    new_first_name = "Updated"
    new_last_name = "Name"

    response = await client.process_query(
        f"""Use the update_contact_by_email tool to update contact with:
        email: {created_contact_email}
        body: {{"first_name": "{new_first_name}", "last_name": "{new_last_name}"}}
        If successful, start your response with 'Contact updated successfully'."""
    )

    assert (
        "contact updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_contact_by_email"

    print(f"Response: {response}")
    print("✅ update_contact_by_email passed.")


@pytest.mark.asyncio
async def test_update_contact_by_user_id(client):
    """Update contact details by user ID.

    Verifies that the contact details can be updated by user ID.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_user_id:
        pytest.skip("No contact user ID available - run add_contact test first")

    new_first_name = "Updated"
    new_last_name = "Name"

    response = await client.process_query(
        f"""Use the update_contact_by_user_id tool to update contact with:
        user_id: {created_contact_user_id}
        body: {{"first_name": "{new_first_name}", "last_name": "{new_last_name}"}}
        If successful, start your response with 'Contact updated successfully'."""
    )

    assert (
        "contact updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_contact_by_user_id"

    print(f"Response: {response}")
    print("✅ update_contact_by_user_id passed.")


@pytest.mark.asyncio
async def test_send_transactional_email(client):
    """Send a transactional email.

    Verifies that a transactional email can be sent successfully.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_email:
        pytest.skip("No contact email available - run add_contact test first")

    response = await client.process_query(
        f"""Use the send_transactional_email tool to send an email with:
        to_email: {created_contact_email}
        transactional_id: {test_transactional_id}
        add_to_audience: true
        If successful, start your response with 'Transactional email sent successfully'."""
    )

    assert (
        "transactional email sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_transactional_email"

    print(f"Response: {response}")
    print("✅ send_transactional_email passed.")


@pytest.mark.asyncio
async def test_send_event_by_email(client):
    """Send an event by email.

    Verifies that an event can be sent to a contact by email.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_email:
        pytest.skip("No contact email available - run add_contact test first")

    event_name = "test_event"
    event_properties = {"test_property": "test_value"}

    response = await client.process_query(
        f"""Use the send_event_by_email tool to send an event to {created_contact_email} with:
        event_name: {event_name}
        event_properties: {event_properties}
        If successful, start your response with 'Event sent successfully'."""
    )

    assert (
        "event sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_event_by_email"

    print(f"Response: {response}")
    print("✅ send_event_by_email passed.")


@pytest.mark.asyncio
async def test_send_event_by_user_id(client):
    """Send an event by user ID.

    Verifies that an event can be sent to a contact by user ID.

    Args:
        client: The test client fixture for the MCP server.
    """
    if not created_contact_user_id:
        pytest.skip("No contact user ID available - run add_contact test first")

    event_name = "test_event"
    event_properties = {"test_property": "test_value"}

    response = await client.process_query(
        f"""Use the send_event_by_user_id tool to send an event to user ID {created_contact_user_id} with:
        event_name: {event_name}
        event_properties: {event_properties}
        If successful, start your response with 'Event sent successfully'."""
    )

    assert (
        "event sent successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from send_event_by_user_id"

    print(f"Response: {response}")
    print("✅ send_event_by_user_id passed.")


@pytest.mark.asyncio
async def test_delete_contact_by_email(client):
    """Delete a contact by email.

    Verifies that a contact can be deleted by email.

    Args:
        client: The test client fixture for the MCP server.
    """
    # First create a new contact
    test_email = f"test_{uuid.uuid4()}@example.com"
    test_first_name = "Test"
    test_last_name = "User"

    create_response = await client.process_query(
        f"""Use the add_contact tool to create a new contact with:
        email: {test_email}
        first_name: {test_first_name}
        last_name: {test_last_name}
        subscribed: true
        If successful, start your response with 'Contact added successfully'."""
    )

    assert (
        "contact added successfully" in create_response.lower()
    ), f"Expected success phrase not found in response: {create_response}"
    assert create_response, "No response returned from add_contact"

    # Now delete the contact
    response = await client.process_query(
        f"Use the delete_contact_by_email tool to delete contact with email {test_email}. "
        "If successful, start your response with 'Contact deleted successfully'."
    )

    assert (
        "contact deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_contact_by_email"

    print(f"Response: {response}")
    print("✅ delete_contact_by_email passed.")


@pytest.mark.asyncio
async def test_delete_contact_by_user_id(client):
    """Delete a contact by user ID.

    Verifies that a contact can be deleted by user ID.

    Args:
        client: The test client fixture for the MCP server.
    """
    # First create a new contact with a user ID
    test_email = f"test_{uuid.uuid4()}@example.com"
    test_first_name = "Test"
    test_last_name = "User"
    test_user_id = f"test_user_{uuid.uuid4()}"

    create_response = await client.process_query(
        f"""Use the add_contact tool to create a new contact with:
        email: {test_email}
        user_id: {test_user_id}
        first_name: {test_first_name}
        last_name: {test_last_name}
        subscribed: true
        If successful, start your response with 'Contact added successfully'."""
    )

    assert (
        "contact added successfully" in create_response.lower()
    ), f"Expected success phrase not found in response: {create_response}"
    assert create_response, "No response returned from add_contact"

    # Now delete the contact by user ID
    response = await client.process_query(
        f"Use the delete_contact_by_user_id tool to delete contact with user ID {test_user_id}. "
        "If successful, start your response with 'Contact deleted successfully'."
    )

    assert (
        "contact deleted successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from delete_contact_by_user_id"

    print(f"Response: {response}")
    print("✅ delete_contact_by_user_id passed.")
