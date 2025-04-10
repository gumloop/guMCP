import pytest
from datetime import datetime, timedelta

# Test data
test_contact = {
    "first_name": "Test",
    "last_name": "User",
    "organization_name": "Test Org",
    "title": "Software Engineer",
    "email": "test.user@testorg.com",
}

test_contact_updated = {
    "first_name": "Test",
    "last_name": "User Updated",
    "organization_name": "Test Org Updated",
    "title": "Senior Software Engineer",
    "email": "test.user.updated@testorg.com",
}

test_account = {
    "name": "Test Organization",
    "domain": "testorg.com",
    "phone": "+1234567890",
    "raw_address": "123 Test St, Test City, TS 12345",
}

test_account_updated = {
    "name": "Test Organization Updated",
    "domain": "testorg-updated.com",
    "phone": "+1987654321",
    "raw_address": "456 Test Ave, Test City, TS 12345",
}

test_deal = {
    "name": "Test Deal",
    "amount": "10000",
    "closed_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
}

test_deal_updated = {
    "name": "Test Deal Updated",
    "amount": "15000",
    "closed_date": (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d"),
}

test_task = {
    "priority": "high",
    "due_at": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "type": "call",
    "status": "scheduled",
    "note": "Test task for integration testing",
}

# Global variables to store IDs
contact_id = ""
account_id = ""
deal_id = ""


@pytest.mark.asyncio
async def test_list_contact_stages(client):
    """Test listing available contact stages."""
    response = await client.process_query(
        "Use the list_contact_stages tool to get available contact stages."
    )

    assert response, "No response returned from list_contact_stages"
    assert (
        "contact stages" in response.lower()
    ), f"Expected contact stages in response: {response}"

    print(f"Response: {response}")
    print("✅ list_contact_stages passed.")


@pytest.mark.asyncio
async def test_create_contact(client):
    """Test creating a new contact."""
    global contact_id

    response = await client.process_query(
        f"Use the create_contact tool to create a contact with the following details: "
        f"First Name: {test_contact['first_name']}, "
        f"Last Name: {test_contact['last_name']}, "
        f"Organization Name: {test_contact['organization_name']}, "
        f"Title: {test_contact['title']}, "
        f"Email: {test_contact['email']}. "
        "If successful, start your response with 'Contact created successfully' and return the contact ID."
        "Please return the contact ID in the format 'ID: <contact_id>'"
    )

    assert (
        "contact created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_contact"

    try:
        contact_id = response.lower().split("id:")[1].strip()
    except Exception as e:
        assert (
            False
        ), f"Error parsing contact ID from response: {response} with error: {str(e)}"

    print(f"Response: {response}")
    print("✅ create_contact passed.")


@pytest.mark.asyncio
async def test_search_contacts(client):
    """Test searching for contacts."""
    response = await client.process_query(
        f"Use the search_contacts tool to search for contacts with the following criteria: "
        f"First Name: {test_contact['first_name']}, "
        f"Last Name: {test_contact['last_name']}, "
        f"Organization Name: {test_contact['organization_name']}. "
        "If successful, start your response with 'Contacts found successfully'."
    )

    assert (
        "contacts found successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search_contacts"

    print(f"Response: {response}")
    print("✅ search_contacts passed.")


@pytest.mark.asyncio
async def test_update_contact(client):
    """Test updating an existing contact."""
    global contact_id

    response = await client.process_query(
        f"Use the update_contact tool to update the contact with the following details: "
        f"Contact ID: {contact_id}, "
        f"First Name: {test_contact_updated['first_name']}, "
        f"Last Name: {test_contact_updated['last_name']}, "
        f"Organization Name: {test_contact_updated['organization_name']}, "
        f"Title: {test_contact_updated['title']}, "
        f"Email: {test_contact_updated['email']}. "
        "If successful, start your response with 'Contact updated successfully'."
    )

    assert (
        "contact updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_contact"

    print(f"Response: {response}")
    print("✅ update_contact passed.")


@pytest.mark.asyncio
async def test_list_account_stages(client):
    """Test listing available account stages."""
    response = await client.process_query(
        "Use the list_account_stages tool to get available account stages."
    )

    assert response, "No response returned from list_account_stages"
    assert (
        "account stages" in response.lower()
    ), f"Expected account stages in response: {response}"

    print(f"Response: {response}")
    print("✅ list_account_stages passed.")


@pytest.mark.asyncio
async def test_create_account(client):
    """Test creating a new account."""
    global account_id

    response = await client.process_query(
        f"Use the create_account tool to create an account with the following details: "
        f"Name: {test_account['name']}, "
        f"Domain: {test_account['domain']}, "
        f"Phone: {test_account['phone']}, "
        f"Raw Address: {test_account['raw_address']}. "
        "If successful, start your response with 'Account created successfully' and return the account ID."
        "Please return the account ID in the format 'ID: <account_id>'"
    )

    assert (
        "account created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_account"

    try:
        account_id = response.lower().split("id:")[1].strip()
    except Exception as e:
        assert (
            False
        ), f"Error parsing account ID from response: {response} with error: {str(e)}"

    print(f"Response: {response}")
    print("✅ create_account passed.")


@pytest.mark.asyncio
async def test_search_accounts(client):
    """Test searching for accounts."""
    response = await client.process_query(
        f"Use the search_accounts tool to search for accounts with the following criteria: "
        f"Organization Name: {test_account['name']}. "
        "If successful, start your response with 'Accounts found successfully'."
    )

    assert (
        "accounts found successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from search_accounts"

    print(f"Response: {response}")
    print("✅ search_accounts passed.")


@pytest.mark.asyncio
async def test_update_account(client):
    """Test updating an existing account."""
    global account_id

    response = await client.process_query(
        f"Use the update_account tool to update the account with the following details: "
        f"Account ID: {account_id}, "
        f"Name: {test_account_updated['name']}, "
        f"Domain: {test_account_updated['domain']}, "
        f"Phone: {test_account_updated['phone']}, "
        f"Raw Address: {test_account_updated['raw_address']}. "
        "If successful, start your response with 'Account updated successfully'."
    )

    assert (
        "account updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_account"

    print(f"Response: {response}")
    print("✅ update_account passed.")


@pytest.mark.asyncio
async def test_list_deal_stages(client):
    """Test listing available deal stages."""
    response = await client.process_query(
        "Use the list_deal_stages tool to get available deal stages."
    )

    assert response, "No response returned from list_deal_stages"
    assert (
        "deal stages" in response.lower()
    ), f"Expected deal stages in response: {response}"

    print(f"Response: {response}")
    print("✅ list_deal_stages passed.")


@pytest.mark.asyncio
async def test_create_deal(client):
    """Test creating a new deal."""
    global deal_id

    response = await client.process_query(
        f"Use the create_deal tool to create a deal with the following details: "
        f"Name: {test_deal['name']}, "
        f"Account ID: {account_id}, "
        f"Amount: {test_deal['amount']}, "
        f"Closed Date: {test_deal['closed_date']}. "
        "If successful, start your response with 'Deal created successfully' and return the deal ID."
        "Please return the deal ID in the format 'ID: <deal_id>'"
    )

    assert (
        "deal created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_deal"

    try:
        deal_id = response.lower().split("id:")[1].strip()
    except Exception as e:
        assert (
            False
        ), f"Error parsing deal ID from response: {response} with error: {str(e)}"

    print(f"Response: {response}")
    print("✅ create_deal passed.")


@pytest.mark.asyncio
async def test_list_deals(client):
    """Test listing all deals."""
    response = await client.process_query("Use the list_deals tool to get all deals.")

    assert response, "No response returned from list_deals"
    assert "deals" in response.lower(), f"Expected deals in response: {response}"

    print(f"Response: {response}")
    print("✅ list_deals passed.")


@pytest.mark.asyncio
async def test_update_deal(client):
    """Test updating an existing deal."""
    global deal_id

    response = await client.process_query(
        f"Use the update_deal tool to update the deal with the following details: "
        f"Opportunity ID: {deal_id}, "
        f"Name: {test_deal_updated['name']}, "
        f"Amount: {test_deal_updated['amount']}, "
        f"Closed Date: {test_deal_updated['closed_date']}. "
        "If successful, start your response with 'Deal updated successfully'."
    )

    assert (
        "deal updated successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from update_deal"

    print(f"Response: {response}")
    print("✅ update_deal passed.")


@pytest.mark.asyncio
async def test_list_users(client):
    """Test listing all users."""
    response = await client.process_query("Use the list_users tool to get all users.")

    assert response, "No response returned from list_users"
    assert "users" in response.lower(), f"Expected users in response: {response}"

    print(f"Response: {response}")
    print("✅ list_users passed.")


@pytest.mark.asyncio
async def test_create_task(client):
    """Test creating a new task."""

    response = await client.process_query(
        f"Use the create_task tool to create a task with the following details: "
        f"User ID: 1, "
        f"Contact ID: [{contact_id}], "
        f"Priority: {test_task['priority']}, "
        f"Due At: {test_task['due_at']}, "
        f"Type: {test_task['type']}, "
        f"Status: {test_task['status']}, "
        f"Note: {test_task['note']}. "
        "If successful, start your response with 'Task created successfully'"
    )

    assert (
        "task created successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from create_task"

    print(f"Response: {response}")
    print("✅ create_task passed.")


@pytest.mark.asyncio
async def test_enrich_person(client):
    """Test enriching person data."""
    response = await client.process_query(
        f"Use the enrich_person tool to enrich data for a person with the following details: "
        f"First Name: {test_contact['first_name']}, "
        f"Last Name: {test_contact['last_name']}, "
        f"Email: {test_contact['email']}. "
        "If successful, start your response with 'Person data enriched successfully'."
    )

    assert (
        "person data enriched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from enrich_person"

    print(f"Response: {response}")
    print("✅ enrich_person passed.")


@pytest.mark.asyncio
async def test_enrich_organization(client):
    """Test enriching organization data."""
    response = await client.process_query(
        "Use the enrich_organization tool to enrich data for an organization with the following details: "
        "Domain: Gumloop.com "
        "If successful, start your response with 'Organization data enriched successfully'."
    )

    assert (
        "organization data enriched successfully" in response.lower()
    ), f"Expected success phrase not found in response: {response}"
    assert response, "No response returned from enrich_organization"

    print(f"Response: {response}")
    print("✅ enrich_organization passed.")
