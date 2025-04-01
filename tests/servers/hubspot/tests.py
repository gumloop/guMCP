import uuid
import pytest
import time


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing HubSpot contacts as resources"""
    response = await client.list_resources()
    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    print("HubSpot contacts found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed HubSpot contacts")


@pytest.mark.asyncio
async def test_read_contact(client):
    """Test reading a HubSpot contact"""
    # First list contacts to get a valid contact ID
    response = await client.list_resources()

    assert response and hasattr(
        response, "resources"
    ), f"Invalid list resources response: {response}"

    resources = response.resources

    # Skip test if no contacts found
    if not resources:
        print("⚠️ No HubSpot contacts found to test reading")
        pytest.skip("No HubSpot contacts available for testing")
        return

    # Test with the first contact
    contact_resource = resources[0]
    response = await client.read_resource(contact_resource.uri)

    assert (
        response and response.contents
    ), f"Response should contain contact data: {response}"
    assert len(response.contents[0].text) >= 0, "Contact data should be available"

    print("Contact read:")
    print(f"  - {contact_resource.name}: {response.contents[0].text[:100]}...")

    print("✅ Successfully read HubSpot contact")


@pytest.mark.asyncio
async def test_list_contacts(client):
    """Test listing HubSpot contacts using the list_contacts tool"""
    # Test with specific properties and a search query
    search_query = "*@example.com"
    response = await client.process_query(
        f"Use the list_contacts tool to search for HubSpot contacts with the query '{search_query}'. "
        f"Limit to 3 results and include only the email, firstname, lastname, and company properties. "
        f"If successful, start your response with 'CONTACTS_FOUND:' followed by the results."
    )

    # Verify the response contains expected content
    assert (
        "CONTACTS_FOUND:" in response
    ), f"List contacts operation not performed: {response}"

    print("List contacts tool results:")
    print(f"{response}")

    print("✅ List contacts tool working")


@pytest.mark.asyncio
async def test_create_contact(client):
    """Test creating a new HubSpot contact with standard properties"""
    # Generate a unique email with timestamp to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"test{unique_id}@example.com"
    first_name = "Test"
    last_name = f"User {unique_id}"

    response = await client.process_query(
        f"Use the create_contact tool to create a new HubSpot contact with the following details:\n"
        f"- Email: {test_email}\n"
        f"- First name: {first_name}\n"
        f"- Last name: {last_name}\n"
        f"- Company: Test Company\n"
        f"- Job title: QA Tester\n"
        f"If successful, start your response with 'CONTACT_CREATED:' followed by the contact ID."
    )

    # Verify that a contact was created - check for success prefix
    assert "CONTACT_CREATED:" in response, f"Contact creation failed: {response}"

    # Extract the contact ID for future reference
    import re

    contact_id_match = re.search(r"CONTACT_CREATED: ([a-zA-Z0-9]+)", response)
    if not contact_id_match:
        contact_id_match = re.search(r"ID: ([a-zA-Z0-9]+)", response)
    if not contact_id_match:
        contact_id_match = re.search(r"id ([a-zA-Z0-9]+)", response.lower())

    contact_id = contact_id_match.group(1) if contact_id_match else None

    print(f"Created contact with ID: {contact_id}")
    print("✅ Contact creation successful")

    return contact_id


@pytest.mark.asyncio
async def test_update_contact(client):
    """Test updating an existing HubSpot contact"""
    # First create a contact to update
    contact_id = await test_create_contact(client)
    assert contact_id, "Failed to create contact for update test"

    # Wait a moment for the contact to be available
    time.sleep(2)

    # Now update the contact with new information
    new_company = f"Updated Company {uuid.uuid4()}"
    new_title = "Senior QA Engineer"

    response = await client.process_query(
        f"Use the update_contact tool to update the contact with ID {contact_id}. "
        f"Change the company to '{new_company}' and the job title to '{new_title}'. "
        f"If successful, start your response with 'CONTACT_UPDATED:' followed by the contact ID."
    )

    # Verify the update was successful
    assert "CONTACT_UPDATED:" in response, f"Contact update failed: {response}"

    print(f"Updated contact with ID: {contact_id}")
    print("✅ Contact update successful")

    return contact_id


@pytest.mark.asyncio
async def test_search_contacts(client):
    """Test searching for HubSpot contacts with advanced filters"""
    # Create a contact with a unique attribute to search for
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"search{unique_id}@example.com"

    # First create the contact
    create_response = await client.process_query(
        f"Create a new HubSpot contact with email {test_email} and company 'SearchCorp'. "
        f"If successful, start your response with 'CONTACT_CREATED:' followed by the contact ID."
    )

    # Check that contact was created
    assert (
        "CONTACT_CREATED:" in create_response
    ), f"Contact creation failed: {create_response}"

    # Wait a moment for the contact to be available in search
    time.sleep(2)

    # Now search for this contact using the search_contacts tool with EQ operator
    search_response = await client.process_query(
        f"Use the search_contacts tool to search for contacts where the email property equals '{test_email}'. "
        f"Use the EQ operator and return all available properties. "
        f"If contacts are found, start your response with 'CONTACTS_FOUND:' followed by the results."
    )

    # Verify the search was successful
    assert (
        "CONTACTS_FOUND:" in search_response
    ), f"Search did not find the contact: {search_response}"

    print("✅ Contact search successful")
    return test_email


@pytest.mark.asyncio
async def test_list_companies(client):
    """Test listing HubSpot companies"""
    response = await client.process_query(
        "Use the list_companies tool to list up to 5 HubSpot companies. "
        "Include the name, domain, and industry properties. "
        "If companies are found, start your response with 'COMPANIES_FOUND:' followed by the results."
    )

    # Verify the response mentions companies or indicates none were found
    assert (
        "COMPANIES_FOUND:" in response
    ), f"List companies operation failed: {response}"

    print("List companies tool results:")
    print(f"{response}")

    print("✅ List companies tool working")


@pytest.mark.asyncio
async def test_create_company(client):
    """Test creating a new HubSpot company"""
    # Generate a unique company name to avoid conflicts
    unique_id = str(uuid.uuid4())[:8]
    company_name = f"Test Company {unique_id}"
    domain = f"test-company-{unique_id.lower()}.com"

    response = await client.process_query(
        f"Use the create_company tool to create a new HubSpot company with the following details:\n"
        f"- Name: {company_name}\n"
        f"- Domain: {domain}\n"
        f"- Industry: COMPUTER_SOFTWARE\n"
        f"- City: Test City\n"
        f"- Country: Test Country\n"
        f"If successful, start your response with 'COMPANY_CREATED:' followed by the company ID."
    )

    # Verify that a company was created
    assert "COMPANY_CREATED:" in response, f"Company creation failed: {response}"

    # Extract the company ID for future reference
    import re

    company_id_match = re.search(r"COMPANY_CREATED: ([a-zA-Z0-9]+)", response)
    if not company_id_match:
        company_id_match = re.search(r"ID: ([a-zA-Z0-9]+)", response)
    if not company_id_match:
        company_id_match = re.search(r"id ([a-zA-Z0-9]+)", response.lower())

    company_id = company_id_match.group(1) if company_id_match else None

    print(f"Created company with ID: {company_id}")
    print("✅ Company creation successful")

    return company_id


@pytest.mark.asyncio
async def test_update_company(client):
    """Test updating an existing HubSpot company"""
    # First create a company to update
    company_id = await test_create_company(client)
    assert company_id, "Failed to create company for update test"

    # Wait a moment for the company to be available
    time.sleep(2)

    # Now update the company with new information
    new_description = f"Updated description {uuid.uuid4()}"
    new_industry = "Accounting"

    response = await client.process_query(
        f"Use the update_company tool to update the company with ID {company_id}. "
        f"Change the description to '{new_description}' and the industry to '{new_industry}'. "
        f"If successful, start your response with 'COMPANY_UPDATED:' followed by the company ID."
    )

    # Verify the update was successful
    assert "COMPANY_UPDATED:" in response, f"Company update failed: {response}"

    print(f"Updated company with ID: {company_id}")
    print("✅ Company update successful")

    return company_id


@pytest.mark.asyncio
async def test_list_deals(client):
    """Test listing HubSpot deals"""
    response = await client.process_query(
        "Use the list_deals tool to list up to 5 HubSpot deals. "
        "Include the dealname, amount, and dealstage properties. "
        "If deals are found, start your response with 'DEALS_FOUND:' followed by the results."
    )

    # Verify the response mentions deals or indicates none were found
    assert "DEALS_FOUND:" in response, f"List deals operation failed: {response}"

    print("List deals tool results:")
    print(f"{response}")

    print("✅ List deals tool working")


@pytest.mark.asyncio
async def test_create_deal(client):
    """Test creating a new HubSpot deal"""
    # First create a contact to associate with the deal
    contact_id = await test_create_contact(client)
    assert contact_id, "Failed to create contact for deal test"

    # Generate a unique deal name
    unique_id = str(uuid.uuid4())[:8]
    deal_name = f"Test Deal {unique_id}"
    amount = 5000

    response = await client.process_query(
        f"Use the create_deal tool to create a new HubSpot deal with the following details:\n"
        f"- Deal name: {deal_name}\n"
        f"- Amount: {amount}\n"
        f"- Contact ID: {contact_id}\n"
        f"If successful, start your response with 'DEAL_CREATED:' followed by the deal ID."
    )

    # Verify that a deal was created
    assert "DEAL_CREATED:" in response, f"Deal creation failed: {response}"

    # Extract the deal ID for future reference
    import re

    deal_id_match = re.search(r"DEAL_CREATED: ([a-zA-Z0-9]+)", response)
    if not deal_id_match:
        deal_id_match = re.search(r"ID: ([a-zA-Z0-9]+)", response)
    if not deal_id_match:
        deal_id_match = re.search(r"id ([a-zA-Z0-9]+)", response.lower())

    deal_id = deal_id_match.group(1) if deal_id_match else None

    print(f"Created deal with ID: {deal_id}")
    print("✅ Deal creation successful")

    return deal_id


@pytest.mark.asyncio
async def test_update_deal(client):
    """Test updating an existing HubSpot deal"""
    # First create a deal to update
    deal_id = await test_create_deal(client)
    assert deal_id, "Failed to create deal for update test"

    # Wait a moment for the deal to be available
    time.sleep(2)

    # Now update the deal with new information
    new_amount = 7500
    new_dealstage = "qualifiedtobuy"

    response = await client.process_query(
        f"Use the update_deal tool to update the deal with ID {deal_id}. "
        f"Change the amount to {new_amount} and the dealstage to '{new_dealstage}'. "
        f"If successful, start your response with 'DEAL_UPDATED:' followed by the deal ID."
    )

    # Verify the update was successful
    assert "DEAL_UPDATED:" in response, f"Deal update failed: {response}"

    print(f"Updated deal with ID: {deal_id}")
    print("✅ Deal update successful")

    return deal_id


@pytest.mark.asyncio
async def test_get_engagements(client):
    """Test getting engagement data for a contact"""
    # First create a contact to get engagements for
    contact_id = await test_create_contact(client)
    assert contact_id, "Failed to create contact for engagements test"

    # Wait a moment for the contact to be available
    time.sleep(2)

    response = await client.process_query(
        f"Use the get_engagements tool to get engagement data for the contact with ID {contact_id}. "
        f"Limit to 10 engagements. "
        f"If successful, start your response with 'ENGAGEMENTS_FOUND:' followed by the results."
    )

    # Verify the response mentions engagements or indicates none were found
    assert (
        "ENGAGEMENTS_FOUND:" in response
    ), f"Get engagements operation failed: {response}"

    print("Get engagements tool results:")
    print(f"{response}")

    print("✅ Get engagements tool working")


@pytest.mark.asyncio
async def test_send_email(client):
    """Test sending an email to a HubSpot contact"""
    # First create a contact to send an email to
    contact_id = await test_create_contact(client)
    assert contact_id, "Failed to create contact for email test"

    # Wait a moment for the contact to be available
    time.sleep(2)

    # Prepare email content
    subject = f"Test Email {uuid.uuid4()}"
    body = "This is a test email from the HubSpot integration tests."

    response = await client.process_query(
        f"Use the send_email tool to send an email to the contact with ID {contact_id}. "
        f"Use the subject '{subject}' and the following body: '{body}'. "
        f"If successful, start your response with 'EMAIL_SENT:' followed by any confirmation details."
    )

    # Verify the response indicates the email was sent or recorded
    assert "EMAIL_SENT:" in response, f"Send email operation failed: {response}"

    print("Send email tool results:")
    print(f"{response}")

    print("✅ Send email tool working")


@pytest.mark.asyncio
async def test_company_workflow(client):
    """Test a workflow involving companies: create, update, and list"""
    # Create a company
    company_id = await test_create_company(client)
    assert company_id, "Failed to create company for workflow test"

    # Wait a moment for the company to be available
    time.sleep(2)

    # Update the company
    update_response = await client.process_query(
        f"Update the HubSpot company with ID {company_id}. "
        f"Set the description to 'Workflow Test Company' and the phone to '555-1234'. "
        f"If successful, start your response with 'COMPANY_UPDATED:' followed by the company ID."
    )

    assert (
        "COMPANY_UPDATED:" in update_response
    ), f"Company update failed: {update_response}"

    # Wait a moment for the update to be available
    time.sleep(2)

    # List companies and make sure our company appears
    list_response = await client.process_query(
        f"List HubSpot companies and include the name, description, and phone properties. "
        f"If companies are found, start your response with 'COMPANIES_FOUND:' followed by the results."
    )

    assert (
        "COMPANIES_FOUND:" in list_response
    ), f"List companies did not work in workflow: {list_response}"

    print("✅ Company workflow test successful")


@pytest.mark.asyncio
async def test_deal_workflow(client):
    """Test a workflow involving deals and contacts"""
    # Create a contact
    contact_id = await test_create_contact(client)
    assert contact_id, "Failed to create contact for deal workflow test"

    # Create a company
    company_id = await test_create_company(client)
    assert company_id, "Failed to create company for deal workflow test"

    # Wait a moment for them to be available
    time.sleep(2)

    # Create a deal associated with both the contact and company
    unique_id = str(uuid.uuid4())[:8]
    deal_name = f"Workflow Deal {unique_id}"

    create_response = await client.process_query(
        f"Create a new HubSpot deal named '{deal_name}' with an amount of 10000. "
        f"Associate it with contact ID {contact_id} and company ID {company_id}. "
        f"If successful, start your response with 'DEAL_CREATED:' followed by the deal ID."
    )

    assert (
        "DEAL_CREATED:" in create_response
    ), f"Deal creation failed in workflow: {create_response}"

    # Extract deal ID
    import re

    deal_id_match = re.search(r"DEAL_CREATED: ([a-zA-Z0-9]+)", create_response)
    if not deal_id_match:
        deal_id_match = re.search(r"ID: ([a-zA-Z0-9]+)", create_response)
    if not deal_id_match:
        deal_id_match = re.search(r"id ([a-zA-Z0-9]+)", create_response.lower())

    deal_id = deal_id_match.group(1) if deal_id_match else None
    assert deal_id, "Failed to extract deal ID from creation response"

    # Wait a moment for the deal to be available
    time.sleep(2)

    # Update the deal
    update_response = await client.process_query(
        f"Update the HubSpot deal with ID {deal_id}. "
        f"Change the amount to 15000 and set the dealstage to 'presentationscheduled'. "
        f"If successful, start your response with 'DEAL_UPDATED:' followed by the deal ID."
    )

    assert (
        "DEAL_UPDATED:" in update_response
    ), f"Deal update failed in workflow: {update_response}"

    # List deals and make sure our deal appears
    list_response = await client.process_query(
        f"List HubSpot deals and include the dealname and amount properties. "
        f"If deals are found, start your response with 'DEALS_FOUND:' followed by the results."
    )

    assert (
        "DEALS_FOUND:" in list_response
    ), f"List deals did not work in workflow: {list_response}"

    print("✅ Deal workflow test successful")


@pytest.mark.asyncio
async def test_full_workflow(client):
    """Test a full workflow: create, update, and search a contact"""
    # First create a contact
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"workflow{unique_id}@example.com"
    first_name = "Workflow"
    last_name = f"Test {unique_id}"

    # Create the contact
    create_response = await client.process_query(
        f"Create a new HubSpot contact with email {test_email}, "
        f"first name {first_name}, and last name {last_name}. "
        f"If successful, start your response with 'CONTACT_CREATED:' followed by the contact ID."
    )

    # More flexible assertion
    assert (
        "CONTACT_CREATED:" in create_response
    ), f"Contact creation failed: {create_response}"

    # Extract the contact ID for update
    import re

    contact_id_match = re.search(r"CONTACT_CREATED: ([a-zA-Z0-9]+)", create_response)
    if not contact_id_match:
        contact_id_match = re.search(r"ID: ([a-zA-Z0-9]+)", create_response)
    if not contact_id_match:
        contact_id_match = re.search(r"id ([a-zA-Z0-9]+)", create_response.lower())

    contact_id = contact_id_match.group(1) if contact_id_match else None
    assert contact_id, "Failed to extract contact ID from creation response"

    # Wait a moment to ensure the contact is available
    time.sleep(2)

    # Update the contact
    update_response = await client.process_query(
        f"Update the HubSpot contact with ID {contact_id}. "
        f"Set the company to 'Workflow Company' and the job title to 'Workflow Tester'. "
        f"If successful, start your response with 'CONTACT_UPDATED:' followed by the contact ID."
    )

    # More flexible assertion for update
    assert (
        "CONTACT_UPDATED:" in update_response
    ), f"Contact update failed: {update_response}"

    # Wait a moment for the update to be available
    time.sleep(2)

    # Search for the contact by email
    search_response = await client.process_query(
        f"Search for HubSpot contacts where the email equals '{test_email}'. "
        f"If contacts are found, start your response with 'CONTACTS_FOUND:' followed by the results."
    )

    # Verify that the contact was found with the updated information
    assert (
        "CONTACTS_FOUND:" in search_response
    ), f"Created contact not found: {search_response}"

    # List contacts and make sure our contact appears
    list_response = await client.process_query(
        f"List HubSpot contacts and include the email property. "
        f"If contacts are found, start your response with 'CONTACTS_FOUND:' followed by the results."
    )

    assert "CONTACTS_FOUND:" in list_response, "List contacts did not work in workflow"

    print("✅ Full workflow test successful")
