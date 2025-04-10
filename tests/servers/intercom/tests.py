import pytest
import re
import time


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from Intercom (tags, conversations, contacts)"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_contact(client):
    """Test reading a contact resource"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    contact_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("intercom:///contact/")
        ),
        None,
    )

    if not contact_resource:
        print("No contact resources found, skipping test")
        return

    response = await client.read_resource(contact_resource.uri)
    assert response.contents, "Response should contain contact data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    # Verify we have the expected contact data structure
    content_text = response.contents[0].text
    assert (
        "type" in content_text and "id" in content_text
    ), "Response should contain contact data fields"
    assert "email" in content_text, "Response should include contact email"


@pytest.mark.asyncio
async def test_read_conversation(client):
    """Test reading a conversation resource"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    conversation_resource = next(
        (
            r
            for r in response.resources
            if str(r.uri).startswith("intercom:///conversation/")
        ),
        None,
    )

    if not conversation_resource:
        print("No conversation resources found, skipping test")
        return

    response = await client.read_resource(conversation_resource.uri)
    assert response.contents, "Response should contain conversation data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Conversation data read:")
    print(f"\t{response.contents[0].text}")

    # Verify we have the expected conversation data structure
    content_text = response.contents[0].text
    assert (
        "type" in content_text and "id" in content_text
    ), "Response should contain conversation data fields"
    assert (
        "conversation_parts" in content_text
    ), "Response should include conversation parts"
    print("✅ Successfully read conversation data")


@pytest.mark.asyncio
async def test_read_tag(client):
    """Test reading a tag resource"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    tag_resource = next(
        (r for r in response.resources if str(r.uri).startswith("intercom:///tag/")),
        None,
    )

    if not tag_resource:
        print("No tag resources found, skipping test")
        return

    response = await client.read_resource(tag_resource.uri)
    assert response.contents, "Response should contain tag data"
    assert response.contents[0].mimeType == "application/json", "Expected JSON response"

    print("Tag data read:")
    print(f"\t{response.contents[0].text}")

    # Verify we have the expected tag data structure
    content_text = response.contents[0].text
    assert (
        "type" in content_text and "id" in content_text
    ), "Response should contain tag data fields"
    assert "name" in content_text, "Response should include tag name"
    print("✅ Successfully read tag data")


@pytest.mark.asyncio
async def test_search_contacts(client):
    """Test searching for contacts"""
    response = await client.process_query(
        "Use the search_contacts tool to search for contacts with email containing 'test'. If you find any contacts, list them."
    )

    print("Search contacts results:")
    print(f"\t{response}")

    assert (
        "search_contacts" in response.lower() or "found" in response.lower()
    ), "Response should indicate search was performed"
    print("✅ Search contacts functionality tested")


@pytest.mark.asyncio
async def test_create_contact(client):
    """Test creating a contact"""
    unique_email = f"test_user_{int(time.time())}@example.com"

    response = await client.process_query(
        f"Use the create_contact tool to create a new contact with email '{unique_email}' and name 'Test User'. "
        "If successful, only return the contact id"
    )

    print("Create contact response:")
    print(f"\t{response}")

    assert re.search(
        r"([a-zA-Z0-9]+)", response
    ), "Contact creation should return an ID"

    assert unique_email in response.lower(), "Response should include the created email"
    print("✅ Contact creation functionality tested")


@pytest.mark.asyncio
async def test_list_admins(client):
    """Test listing admins"""
    response = await client.process_query(
        "Use the list_admins tool to get a list of all admins/team members in the workspace. and return any one of the admin id"
    )

    assert re.search(r"([a-zA-Z0-9]+)", response), "Admin creation should return an ID"

    print("✅ List admins functionality tested")


@pytest.mark.asyncio
async def test_search_companies(client):
    """Test searching for companies"""
    response = await client.process_query(
        "Use the search_companies tool to search for companies with name containing 'test'."
    )

    print("Search companies results:")
    print(f"\t{response}")

    assert "companies" in response.lower() and (
        "found" in response.lower() or "search" in response.lower()
    ), "Response should indicate companies search was performed"
    print("✅ Search companies functionality tested")


@pytest.mark.asyncio
async def test_create_company(client):
    """Test creating a company"""
    unique_name = f"Test Company {int(time.time())}"

    response = await client.process_query(
        f"Use the create_company tool to create a new company with name '{unique_name}' and random company id"
        "industry 'Technology'. If successful, include the company ID in your response."
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", response
    ), "Company creation should return an ID"

    print("✅ Company creation functionality tested")


@pytest.mark.asyncio
async def test_conversation_workflow(client):
    """Test full conversation workflow - create, reply, tag, note"""
    unique_email = f"convo_test_{int(time.time())}@example.com"

    contact_response = await client.process_query(
        f"Use the create_contact tool to create a new contact with email '{unique_email}' and name 'Conversation Test User' and role as user. "
        "Return only the contact ID from the response."
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", contact_response
    ), "Contact creation should return an ID"

    convo_response = await client.process_query(
        f"Use the create_conversation tool to create a new conversation with contact_id '{contact_response}' and "
        "message 'Hello, this is a test conversation'. Return only the conversation ID."
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", convo_response
    ), "Conversation creation should return an ID"

    reply_response = await client.process_query(
        f"Use the reply_to_conversation tool to reply to conversation' with message 'This is a reply to the test conversation' "
        f"and user_id '{contact_response}'. This will send the reply as the contact."
    )

    assert (
        "success" in reply_response.lower() or "sent" in reply_response.lower()
    ), "Response should indicate reply was sent successfully"

    print("Conversation workflow results:")
    print(f"  Contact created: {contact_response}")
    print(f"  Conversation created: {convo_response}")
    print(f"  Reply response: {reply_response}")
    print("✅ Conversation workflow tested")


@pytest.mark.asyncio
async def test_ticket_workflow(client):
    """Test ticket workflow - create, update, comment"""
    unique_email = f"ticket_test_{int(time.time())}@example.com"

    # First create a contact
    contact_response = await client.process_query(
        f"Use the create_contact tool to create a new contact with email '{unique_email}' and name 'Ticket Test User'. "
        "Return only the contact ID from the response."
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", contact_response
    ), "Contact creation should return an ID"
    contact_id = contact_response.strip()

    # List ticket types
    ticket_types_response = await client.process_query(
        "Use the list_ticket_types tool to list all available ticket types in the Intercom workspace."
    )

    assert (
        "ticket type" in ticket_types_response.lower()
    ), "Response should contain ticket type information"

    # Create a ticket
    ticket_response = await client.process_query(
        f"Use the create_ticket tool to create a new ticket with contact_id '{contact_id}', "
        f"title 'Test Support Ticket', description 'This is a test support ticket', and fetch the ticket type id from {ticket_types_response}."
        "Return only the ticket ID from the response."
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", ticket_response
    ), "Ticket creation should return an ID"
    ticket_id = ticket_response.strip()

    # Update the ticket
    update_response = await client.process_query(
        f"Use the update_ticket tool to update ticket '{ticket_id}' with state 'in_progress'."
    )

    assert (
        "success" in update_response.lower() or "updated" in update_response.lower()
    ), "Response should indicate ticket was updated successfully"
    assert (
        "in_progress" in update_response.lower()
    ), "Response should mention updated state"

    # Get admin ID for comment
    admin_response = await client.process_query(
        "Use the list_admins tool to list all admins and return just the admin id"
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", admin_response
    ), "Admin creation should return an ID"

    # Get the ticket details
    get_response = await client.process_query(
        f"Use the get_ticket tool to get details for ticket '{ticket_id}'."
    )

    assert "status" in get_response.lower(), "Response should include ticket status"
    assert (
        "test support ticket" in get_response.lower()
    ), "Response should include the ticket title"

    print("Ticket workflow results:")
    print(f"  Contact created: {contact_id}")
    print(f"  Ticket created: {ticket_id}")
    print(f"  Update response: {update_response}")
    print(f"  Get response: {get_response}")
    print("✅ Ticket workflow tested")


@pytest.mark.asyncio
async def test_retrieve_articles(client):
    """Test retrieving articles functionality"""
    # First list articles to get an ID
    list_response = await client.process_query(
        "Use the list_articles tool to list all articles and return the ID of one of the articles"
    )

    assert re.search(
        r"([a-zA-Z0-9]+)", list_response
    ), "Article listing should return an ID"

    article_id = list_response.strip()

    # Now retrieve the specific article
    retrieve_response = await client.process_query(
        f"Use the retrieve_article tool to get the article with id {article_id}"
    )

    print("Retrieve article results:")
    print(f"\t{retrieve_response}")

    # Check for indications that article was retrieved successfully
    assert (
        "retrieved" in retrieve_response.lower()
    ), "Response should indicate article was retrieved"
    assert "article" in retrieve_response.lower(), "Response should mention the article"
    print("✅ Article retrieval functionality tested")
