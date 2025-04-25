import re
import pytest


@pytest.mark.asyncio
async def test_list_resources(client):
    """Test listing resources from Attio"""
    response = await client.list_resources()
    assert (
        response and hasattr(response, "resources") and len(response.resources)
    ), f"Invalid list resources response: {response}"

    print("Resources found:")
    for resource in response.resources:
        print(f"  - {resource.name} ({resource.uri}) - Type: {resource.mimeType}")

    print("✅ Successfully listed resources")


@pytest.mark.asyncio
async def test_read_collections(client):
    """Test reading collections from Attio"""
    # Test reading companies collection
    companies_response = await client.read_resource("attio://collection/companies")
    assert len(
        companies_response.contents[0].text
    ), f"Response should contain companies data: {companies_response}"

    # Test reading people collection
    people_response = await client.read_resource("attio://collection/people")
    assert len(
        people_response.contents[0].text
    ), f"Response should contain people data: {people_response}"

    print("\nCompanies collection response:")
    print(companies_response.contents[0].text)

    print("\nPeople collection response:")
    print(people_response.contents[0].text)

    print("✅ Successfully read collections")


@pytest.mark.asyncio
async def test_search_companies(client):
    """Test searching for companies"""
    response = await client.process_query(
        "Use the search_companies tool to search for 'Google'. If you find any companies, start your response with 'Here are the search results' and then list them."
    )

    assert (
        "here are the search results" in response.lower()
    ), f"Search results not found in response: {response}"

    print("Search results:")
    print(f"\t{response}")

    print("✅ Search companies functionality working")


@pytest.mark.asyncio
async def test_search_contacts(client):
    """Test searching for contacts"""
    response = await client.process_query(
        "Use the search_contacts tool to search for Mark. If you find any contacts, start your response with 'Here are the contact results' and then list them."
    )

    assert (
        "here are the contact results" in response.lower()
    ), f"Contact results not found in response: {response}"

    print("Contact search results:")
    print(f"\t{response}")

    print("✅ Search contacts functionality working")


@pytest.mark.asyncio
async def test_list_lists(client):
    """Test listing Attio lists"""
    response = await client.process_query(
        "Use the list_lists tool to show me all available lists. If you find any lists, start your response with 'Available lists found' and then show them."
    )

    assert (
        "available lists found" in response.lower()
    ), f"Lists not found in response: {response}"

    print("Lists found:")
    print(f"\t{response}")

    print("✅ List lists functionality working")


@pytest.mark.asyncio
async def test_create_and_update_company(client):
    """Test creating and updating a company"""
    # Create company
    create_response = await client.process_query(
        "Use the create_company tool to create a company named 'Test Company2' with domain 'test.com'. If successful, start your response with 'Company created successfully with ID: {id}'."
    )

    assert (
        "company created successfully" in create_response.lower()
    ), f"Company creation failed: {create_response}"

    assert (
        create_response and "company created successfully" in create_response.lower()
    ), f"Company not created: {create_response}"

    # Look for the ID in the response
    id_match = re.search(r"ID: ([a-zA-Z0-9-]+)", create_response)
    company_id = id_match.group(1) if id_match else None

    # Update company
    update_response = await client.process_query(
        f"Use the update_company tool to update the company with ID '{company_id}' to add the attribute 'description' with value 'Technology'. If successful, start your response with 'Company updated successfully'."
    )

    assert (
        "company updated successfully" in update_response.lower()
    ), f"Company update failed: {update_response}"

    print("✅ Company creation and update functionality working")


@pytest.mark.asyncio
async def test_create_and_update_contact(client):
    """Test creating and updating a contact"""
    # Create contact
    create_response = await client.process_query(
        "Use the create_contact tool to create a contact with email 'test@example.com' and first_name 'Test' and last_name 'User'. If successful, start your response with 'Contact created successfully with ID: {id}'."
    )

    assert (
        "contact created successfully" in create_response.lower()
    ), f"Contact creation failed: {create_response}"

    assert (
        create_response and "contact created successfully" in create_response.lower()
    ), f"Contact not created: {create_response}"

    # Look for the ID in the response
    id_match = re.search(r"ID: ([a-zA-Z0-9-]+)", create_response)
    contact_id = id_match.group(1) if id_match else None

    # Update contact
    update_response = await client.process_query(
        f"Use the update_contact tool to update the contact with ID '{contact_id}' to add the attribute 'job_title' with value 'Software Engineer'. If successful, start your response with 'Contact updated successfully'."
    )

    assert (
        "contact updated successfully" in update_response.lower()
    ), f"Contact update failed: {update_response}"

    print("✅ Contact creation and update functionality working")
